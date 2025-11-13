"""
Telemetry module for earlyexit

Captures execution data for ML-driven optimization.
All data stored locally in SQLite by default.
"""

import sqlite3
import json
import os
import time
import hashlib
import re
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager

# Retry with exponential backoff for concurrent writes
try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential_jitter,
        retry_if_exception_type,
        before_sleep_log
    )
    import logging
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    retry = None


class TelemetryCollector:
    """Collects and stores telemetry data"""
    
    DEFAULT_DB_PATH = os.path.expanduser("~/.earlyexit/telemetry.db")
    
    def __init__(self, db_path: Optional[str] = None, enabled: bool = True):
        """
        Initialize telemetry collector
        
        Args:
            db_path: Path to SQLite database (default: ~/.earlyexit/telemetry.db)
            enabled: Whether telemetry is enabled
        """
        self.enabled = enabled
        if not enabled:
            self.db_path = None
            self.conn = None
            return
            
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self._ensure_db_directory()
        self.conn = None
        self._init_database()
    
    def _ensure_db_directory(self):
        """Ensure telemetry directory exists"""
        if self.db_path:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def _init_database(self):
        """Initialize database schema"""
        if not self.enabled or not self.db_path:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Enable WAL mode for better concurrent performance
        cursor.execute("PRAGMA journal_mode=WAL")
        
        # Set busy timeout for concurrent writes (5 seconds)
        conn.execute("PRAGMA busy_timeout = 5000")
        
        # Create executions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS executions (
                execution_id TEXT PRIMARY KEY,
                timestamp REAL,
                
                -- Command Information
                command TEXT,
                command_hash TEXT,
                working_directory TEXT,
                
                -- Pattern Configuration
                pattern TEXT,
                pattern_type TEXT,
                case_insensitive INTEGER,
                invert_match INTEGER,
                max_count INTEGER,
                
                -- Timeout Configuration
                overall_timeout REAL,
                idle_timeout REAL,
                first_output_timeout REAL,
                delay_exit REAL,
                
                -- Execution Results
                exit_code INTEGER,
                exit_reason TEXT,
                
                -- Timing Metrics
                total_runtime REAL,
                time_to_first_output REAL,
                time_to_first_match REAL,
                time_from_match_to_exit REAL,
                
                -- Match Information
                match_count INTEGER DEFAULT 0,
                
                -- Output Statistics
                total_lines_processed INTEGER,
                stdout_lines INTEGER,
                stderr_lines INTEGER,
                
                -- User Feedback (optional)
                user_rating INTEGER,
                should_have_exited INTEGER,
                
                -- ML Features
                project_type TEXT,
                command_category TEXT
            )
        """)
        
        # Create match_events table for detailed match information
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS match_events (
                event_id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                match_number INTEGER,
                timestamp_offset REAL,
                stream_source TEXT,
                source_file TEXT,
                line_number INTEGER,
                line_content TEXT,
                matched_substring TEXT,
                context_before TEXT,
                context_after TEXT,
                FOREIGN KEY (execution_id) REFERENCES executions (execution_id) ON DELETE CASCADE
            )
        """)
        
        # Create user_sessions table for interactive learning
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                execution_id TEXT,
                timestamp REAL,
                
                -- Session Context
                command TEXT,
                duration REAL,
                idle_time REAL,
                stop_reason TEXT,  -- 'error', 'timeout', 'hang'
                
                -- Output Metrics
                stdout_lines INTEGER,
                stderr_lines INTEGER,
                total_lines INTEGER,
                
                -- User Selections
                selected_pattern TEXT,
                pattern_confidence REAL,
                pattern_stream TEXT,  -- 'stdout', 'stderr', 'both', 'custom'
                
                -- Suggested Timeouts
                suggested_overall_timeout REAL,
                suggested_idle_timeout REAL,
                suggested_delay_exit REAL,
                
                -- Metadata
                project_type TEXT,
                working_directory TEXT,
                
                FOREIGN KEY (execution_id) REFERENCES executions (execution_id) ON DELETE CASCADE
            )
        """)
        
        # Create learned_settings table for smart suggestions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learned_settings (
                setting_id TEXT PRIMARY KEY,
                command_hash TEXT,
                project_type TEXT,
                
                -- ML Features (JSON format)
                features_json TEXT,  -- Serialized features dict
                
                -- Learned Parameters
                learned_pattern TEXT,
                pattern_confidence REAL,
                learned_timeout REAL,
                learned_idle_timeout REAL,
                learned_delay_exit REAL,
                
                -- Validation Metrics (for recommendation)
                true_positives INTEGER DEFAULT 0,
                true_negatives INTEGER DEFAULT 0,
                false_positives INTEGER DEFAULT 0,
                false_negatives INTEGER DEFAULT 0,
                user_confirmed_good INTEGER DEFAULT 0,
                user_rejected INTEGER DEFAULT 0,
                
                -- Usage Statistics
                times_used INTEGER DEFAULT 0,
                last_used_timestamp REAL,
                created_timestamp REAL,
                
                -- Metadata
                is_active INTEGER DEFAULT 1  -- Can be disabled by user
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_command_hash 
            ON executions(command_hash)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON executions(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_learned_command_hash
            ON learned_settings(command_hash)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_learned_project_type
            ON learned_settings(project_type)
        """)
        
        conn.commit()
        conn.close()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        if not self.enabled or not self.db_path:
            yield None
            return
            
        conn = sqlite3.connect(self.db_path, timeout=5.0)  # 5 second timeout for locks
        try:
            # Enable WAL mode for this connection (idempotent)
            conn.execute("PRAGMA journal_mode=WAL")
            yield conn
        finally:
            conn.close()
    
    def _scrub_pii(self, text: str) -> str:
        """Remove PII from text"""
        if not text:
            return text
            
        # Email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
                     '[EMAIL]', text, flags=re.IGNORECASE)
        
        # IP addresses
        text = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP]', text)
        
        # Passwords/tokens
        text = re.sub(r'password[=:]\s*\S+', 'password=[REDACTED]', text, flags=re.IGNORECASE)
        text = re.sub(r'token[=:]\s*\S+', 'token=[REDACTED]', text, flags=re.IGNORECASE)
        text = re.sub(r'api[_-]?key[=:]\s*\S+', 'api_key=[REDACTED]', text, flags=re.IGNORECASE)
        
        return text
    
    def _hash_command(self, command: str) -> str:
        """Create hash of command for grouping similar executions"""
        return hashlib.sha256(command.encode()).hexdigest()[:16]
    
    def _detect_project_type(self, command: str) -> str:
        """Detect project type from command"""
        command_lower = command.lower()
        
        if 'npm' in command_lower or 'node' in command_lower or 'yarn' in command_lower:
            return 'nodejs'
        elif 'python' in command_lower or 'pytest' in command_lower or 'pip' in command_lower:
            return 'python'
        elif 'cargo' in command_lower or 'rustc' in command_lower:
            return 'rust'
        elif 'go ' in command_lower or command_lower.startswith('go'):
            return 'go'
        elif 'terraform' in command_lower:
            return 'terraform'
        elif 'docker' in command_lower or 'kubectl' in command_lower:
            return 'container'
        elif 'make' in command_lower or 'cmake' in command_lower:
            return 'c/c++'
        else:
            return 'unknown'
    
    def _detect_command_category(self, command: str) -> str:
        """Detect command category"""
        command_lower = command.lower()
        
        if 'test' in command_lower or 'jest' in command_lower or 'pytest' in command_lower:
            return 'test'
        elif 'build' in command_lower or 'compile' in command_lower or 'make' in command_lower:
            return 'build'
        elif 'deploy' in command_lower or 'apply' in command_lower:
            return 'deploy'
        elif 'lint' in command_lower or 'check' in command_lower:
            return 'lint'
        else:
            return 'unknown'
    
    def _create_retry_decorator(self):
        """Create retry decorator with exponential backoff if tenacity available"""
        if not TENACITY_AVAILABLE:
            # No retry if tenacity not available
            def no_retry(func):
                return func
            return no_retry
        
        # Retry on SQLite lock/busy errors with exponential backoff + jitter
        return retry(
            retry=retry_if_exception_type((sqlite3.OperationalError, sqlite3.DatabaseError)),
            stop=stop_after_attempt(5),  # Max 5 attempts
            wait=wait_exponential_jitter(initial=0.01, max=2.0, jitter=0.5),  # 10ms to 2s with jitter
            reraise=True
        )
    
    def _execute_with_retry(self, conn, query: str, params: tuple) -> None:
        """
        Execute SQL query with retry logic
        
        Args:
            conn: Database connection
            query: SQL query string
            params: Query parameters
        """
        retry_decorator = self._create_retry_decorator()
        
        @retry_decorator
        def _do_execute():
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
        
        try:
            _do_execute()
        except (sqlite3.OperationalError, sqlite3.DatabaseError) as e:
            # If all retries failed, check if it's a lock error
            if 'database is locked' in str(e) or 'database is busy' in str(e):
                # Silently fail - telemetry should never break execution
                pass
            else:
                # Re-raise non-lock errors (schema errors, etc.)
                raise
    
    def record_execution(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Record an execution
        
        Args:
            data: Dictionary with execution data
            
        Returns:
            execution_id or None if telemetry disabled
        """
        if not self.enabled:
            return None
        
        # Generate execution ID
        execution_id = f"exec_{int(time.time() * 1000)}_{os.getpid()}"
        
        # Scrub PII from command
        command = data.get('command', '')
        scrubbed_command = self._scrub_pii(command)
        
        # Detect project type and category
        project_type = self._detect_project_type(command)
        command_category = self._detect_command_category(command)
        
        with self._get_connection() as conn:
            if conn is None:
                return None
            
            try:
                self._execute_with_retry(conn, """
                    INSERT INTO executions (
                        execution_id, timestamp,
                        command, command_hash, working_directory,
                        pattern, pattern_type, case_insensitive, invert_match, max_count,
                        overall_timeout, idle_timeout, first_output_timeout, delay_exit,
                        exit_code, exit_reason,
                        total_runtime, time_to_first_output, time_to_first_match, 
                        time_from_match_to_exit,
                        match_count,
                        total_lines_processed, stdout_lines, stderr_lines,
                        project_type, command_category
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, (
                    execution_id,
                    data.get('timestamp', time.time()),
                    scrubbed_command,
                    self._hash_command(command),
                    os.getcwd(),
                    data.get('pattern', ''),
                    data.get('pattern_type', 'python_re'),
                    1 if data.get('case_insensitive') else 0,
                    1 if data.get('invert_match') else 0,
                    data.get('max_count', 1),
                    data.get('overall_timeout'),
                    data.get('idle_timeout'),
                    data.get('first_output_timeout'),
                    data.get('delay_exit'),
                    data.get('exit_code', 0),
                    data.get('exit_reason', 'unknown'),
                    data.get('total_runtime'),
                    data.get('time_to_first_output'),
                    data.get('time_to_first_match'),
                    data.get('time_from_match_to_exit'),
                    data.get('match_count', 0),
                    data.get('total_lines_processed', 0),
                    data.get('stdout_lines', 0),
                    data.get('stderr_lines', 0),
                    project_type,
                    command_category
                ))
                return execution_id
                
            except Exception:
                # Silently fail - don't disrupt main execution
                return None
    
    def record_match_event(self, execution_id: str, match_data: Dict[str, Any]):
        """
        Record a pattern match event with line content and context
        
        Args:
            execution_id: ID of the execution this match belongs to
            match_data: Dict with match details (line_content, stream_source, etc.)
        """
        if not self.enabled or not execution_id:
            return
        
        with self._get_connection() as conn:
            if not conn:
                return
            
            try:
                event_id = f"match_{int(time.time() * 1000)}_{os.getpid()}_{match_data.get('match_number', 0)}"
                
                # Scrub PII from line content
                line_content = self._scrub_pii(match_data.get('line_content', ''))
                matched_substring = self._scrub_pii(match_data.get('matched_substring', ''))
                
                self._execute_with_retry(conn, """
                    INSERT INTO match_events (
                        event_id, execution_id, match_number, timestamp_offset,
                        stream_source, source_file, line_number, line_content, matched_substring,
                        context_before, context_after
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_id,
                    execution_id,
                    match_data.get('match_number', 0),
                    match_data.get('timestamp_offset', 0.0),
                    match_data.get('stream_source', 'stdout'),
                    match_data.get('source_file', None),
                    match_data.get('line_number', 0),
                    line_content[:1000],  # Limit length
                    matched_substring[:500],  # Limit length
                    self._scrub_pii(match_data.get('context_before', ''))[:500],
                    self._scrub_pii(match_data.get('context_after', ''))[:500]
                ))
                
            except Exception:
                # Silently fail - don't disrupt execution
                pass
    
    def record_user_session(self, session_data: Dict[str, Any]):
        """
        Record an interactive learning session
        
        Args:
            session_data: Dict with session details from interactive prompts
        """
        if not self.enabled:
            return
        
        with self._get_connection() as conn:
            if not conn:
                return
            
            try:
                session_id = f"session_{int(time.time() * 1000)}_{os.getpid()}"
                
                # Extract timeout suggestions
                timeout_suggestions = session_data.get('timeout_suggestions', {})
                
                self._execute_with_retry(conn, """
                    INSERT INTO user_sessions (
                        session_id, execution_id, timestamp,
                        command, duration, idle_time, stop_reason,
                        stdout_lines, stderr_lines, total_lines,
                        selected_pattern, pattern_confidence, pattern_stream,
                        suggested_overall_timeout, suggested_idle_timeout, suggested_delay_exit,
                        project_type, working_directory
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    session_data.get('execution_id'),
                    session_data.get('timestamp', time.time()),
                    session_data.get('command', ''),
                    session_data.get('duration', 0.0),
                    session_data.get('idle_time', 0.0),
                    session_data.get('stop_reason', 'unknown'),
                    session_data.get('line_counts', {}).get('stdout', 0),
                    session_data.get('line_counts', {}).get('stderr', 0),
                    session_data.get('line_counts', {}).get('total', 0),
                    session_data.get('selected_pattern'),
                    session_data.get('pattern_confidence', 0.0),
                    session_data.get('pattern_stream'),
                    timeout_suggestions.get('overall_timeout'),
                    timeout_suggestions.get('idle_timeout'),
                    timeout_suggestions.get('delay_exit'),
                    session_data.get('project_type', 'unknown'),
                    session_data.get('working_directory', '')
                ))
                
            except Exception:
                # Silently fail - don't disrupt execution
                pass
    
    def save_learned_setting(self, setting_data: Dict[str, Any]) -> Optional[str]:
        """
        Save or update a learned setting
        
        Args:
            setting_data: Dict with learned parameters and features
        
        Returns:
            setting_id if successful, None otherwise
        """
        if not self.enabled:
            return None
        
        with self._get_connection() as conn:
            if not conn:
                return None
            
            try:
                import json
                
                setting_id = setting_data.get('setting_id') or \
                             f"setting_{int(time.time() * 1000)}_{os.getpid()}"
                
                # Check if setting exists
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT setting_id FROM learned_settings WHERE command_hash = ? AND project_type = ?",
                    (setting_data['command_hash'], setting_data['project_type'])
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing setting
                    self._execute_with_retry(conn, """
                        UPDATE learned_settings SET
                            features_json = ?,
                            learned_pattern = ?,
                            pattern_confidence = ?,
                            learned_timeout = ?,
                            learned_idle_timeout = ?,
                            learned_delay_exit = ?,
                            last_used_timestamp = ?
                        WHERE command_hash = ? AND project_type = ?
                    """, (
                        json.dumps(setting_data.get('features', {})),
                        setting_data.get('learned_pattern'),
                        setting_data.get('pattern_confidence', 0.0),
                        setting_data.get('learned_timeout'),
                        setting_data.get('learned_idle_timeout'),
                        setting_data.get('learned_delay_exit'),
                        time.time(),
                        setting_data['command_hash'],
                        setting_data['project_type']
                    ))
                    return existing[0]
                else:
                    # Insert new setting
                    self._execute_with_retry(conn, """
                        INSERT INTO learned_settings (
                            setting_id, command_hash, project_type,
                            features_json,
                            learned_pattern, pattern_confidence,
                            learned_timeout, learned_idle_timeout, learned_delay_exit,
                            created_timestamp, last_used_timestamp,
                            is_active
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        setting_id,
                        setting_data['command_hash'],
                        setting_data['project_type'],
                        json.dumps(setting_data.get('features', {})),
                        setting_data.get('learned_pattern'),
                        setting_data.get('pattern_confidence', 0.0),
                        setting_data.get('learned_timeout'),
                        setting_data.get('learned_idle_timeout'),
                        setting_data.get('learned_delay_exit'),
                        time.time(),
                        time.time(),
                        1
                    ))
                    return setting_id
                    
            except Exception:
                # Silently fail
                return None
    
    def get_learned_setting(self, command_hash: str, project_type: str) -> Optional[Dict[str, Any]]:
        """
        Get learned setting for a command
        
        Args:
            command_hash: Hash of the command
            project_type: Type of project
        
        Returns:
            Dict with learned setting data, or None
        """
        if not self.enabled:
            return None
        
        with self._get_connection() as conn:
            if not conn:
                return None
            
            try:
                import json
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        setting_id, command_hash, project_type,
                        features_json,
                        learned_pattern, pattern_confidence,
                        learned_timeout, learned_idle_timeout, learned_delay_exit,
                        true_positives, true_negatives, false_positives, false_negatives,
                        user_confirmed_good, user_rejected,
                        times_used, last_used_timestamp, created_timestamp,
                        is_active
                    FROM learned_settings
                    WHERE command_hash = ? AND project_type = ? AND is_active = 1
                    ORDER BY last_used_timestamp DESC
                    LIMIT 1
                """, (command_hash, project_type))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return {
                    'setting_id': row[0],
                    'command_hash': row[1],
                    'project_type': row[2],
                    'features': json.loads(row[3]) if row[3] else {},
                    'learned_pattern': row[4],
                    'pattern_confidence': row[5],
                    'learned_timeout': row[6],
                    'learned_idle_timeout': row[7],
                    'learned_delay_exit': row[8],
                    'validation': {
                        'true_positives': row[9],
                        'true_negatives': row[10],
                        'false_positives': row[11],
                        'false_negatives': row[12],
                        'user_confirmed_good': row[13],
                        'user_rejected': row[14]
                    },
                    'times_used': row[15],
                    'last_used_timestamp': row[16],
                    'created_timestamp': row[17],
                    'is_active': row[18]
                }
                
            except Exception:
                return None
    
    def update_learned_setting_validation(self, setting_id: str, 
                                          outcome: str, user_feedback: Optional[str] = None):
        """
        Update validation metrics for a learned setting
        
        Args:
            setting_id: ID of the setting
            outcome: 'true_positive', 'true_negative', 'false_positive', 'false_negative'
            user_feedback: 'confirmed_good' or 'rejected'
        """
        if not self.enabled or not setting_id:
            return
        
        with self._get_connection() as conn:
            if not conn:
                return
            
            try:
                # Update outcome
                if outcome in ['true_positive', 'true_negative', 'false_positive', 'false_negative']:
                    field = outcome + 's'
                    self._execute_with_retry(conn, f"""
                        UPDATE learned_settings 
                        SET {field} = {field} + 1,
                            times_used = times_used + 1,
                            last_used_timestamp = ?
                        WHERE setting_id = ?
                    """, (time.time(), setting_id))
                
                # Update user feedback
                if user_feedback in ['confirmed_good', 'rejected']:
                    field = 'user_' + user_feedback
                    self._execute_with_retry(conn, f"""
                        UPDATE learned_settings 
                        SET {field} = {field} + 1
                        WHERE setting_id = ?
                    """, (setting_id,))
                    
            except Exception:
                # Silently fail
                pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get basic statistics"""
        if not self.enabled:
            return {"error": "Telemetry disabled"}
        
        with self._get_connection() as conn:
            if conn is None:
                return {"error": "No database"}
                
            cursor = conn.cursor()
            
            # Total executions
            cursor.execute("SELECT COUNT(*) FROM executions")
            total = cursor.fetchone()[0]
            
            # By project type
            cursor.execute("""
                SELECT project_type, COUNT(*) 
                FROM executions 
                GROUP BY project_type
            """)
            by_project = dict(cursor.fetchall())
            
            # Average runtime
            cursor.execute("SELECT AVG(total_runtime) FROM executions WHERE total_runtime IS NOT NULL")
            avg_runtime = cursor.fetchone()[0]
            
            # Learned settings count
            cursor.execute("SELECT COUNT(*) FROM learned_settings WHERE is_active = 1")
            learned_count = cursor.fetchone()[0]
            
            return {
                "total_executions": total,
                "by_project_type": by_project,
                "avg_runtime_seconds": avg_runtime,
                "learned_settings": learned_count
            }
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None


# Global instance
_telemetry_collector: Optional[TelemetryCollector] = None


def init_telemetry(enabled: bool = True, db_path: Optional[str] = None) -> TelemetryCollector:
    """Initialize global telemetry collector"""
    global _telemetry_collector
    _telemetry_collector = TelemetryCollector(db_path=db_path, enabled=enabled)
    return _telemetry_collector


def get_telemetry() -> Optional[TelemetryCollector]:
    """Get global telemetry collector"""
    return _telemetry_collector


def record_execution(data: Dict[str, Any]) -> Optional[str]:
    """Record execution using global collector"""
    collector = get_telemetry()
    if collector:
        return collector.record_execution(data)
    return None


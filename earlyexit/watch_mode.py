"""
Watch mode - Zero-config monitoring with interactive learning

This module implements the watch mode where earlyexit runs a command
without requiring a pattern, captures all output (stdout/stderr separately),
and learns from user behavior (Ctrl+C signals).
"""

import sys
import time
import signal
import subprocess
import threading
from collections import deque
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime


class OutputBuffer:
    """Circular buffer for capturing output with stream separation"""
    
    def __init__(self, maxsize: int = 1000):
        self.maxsize = maxsize
        self.stdout_lines: deque = deque(maxlen=maxsize)
        self.stderr_lines: deque = deque(maxlen=maxsize)
        self.all_lines: deque = deque(maxlen=maxsize)  # Combined for context
        self.lock = threading.Lock()
        
    def add_stdout(self, line: str, timestamp: float):
        """Add a line from stdout"""
        with self.lock:
            entry = {
                'line': line,
                'stream': 'stdout',
                'timestamp': timestamp,
                'line_number': len(self.all_lines) + 1
            }
            self.stdout_lines.append(entry)
            self.all_lines.append(entry)
    
    def add_stderr(self, line: str, timestamp: float):
        """Add a line from stderr"""
        with self.lock:
            entry = {
                'line': line,
                'stream': 'stderr',
                'timestamp': timestamp,
                'line_number': len(self.all_lines) + 1
            }
            self.stderr_lines.append(entry)
            self.all_lines.append(entry)
    
    def get_last_n_lines(self, n: int = 100) -> List[Dict[str, Any]]:
        """Get last N lines from combined output"""
        with self.lock:
            return list(self.all_lines)[-n:]
    
    def get_last_n_by_stream(self, n: int = 50) -> Tuple[List[Dict], List[Dict]]:
        """Get last N lines from each stream separately"""
        with self.lock:
            return (
                list(self.stdout_lines)[-n:],
                list(self.stderr_lines)[-n:]
            )
    
    def get_line_count_by_stream(self) -> Dict[str, int]:
        """Get line counts for each stream"""
        with self.lock:
            return {
                'stdout': len(self.stdout_lines),
                'stderr': len(self.stderr_lines),
                'total': len(self.all_lines)
            }


class WatchSession:
    """Tracks a watch mode session"""
    
    def __init__(self, command: List[str], project_path: str, project_type: str):
        self.command = command
        self.project_path = project_path
        self.project_type = project_type
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.last_output_time: Optional[float] = None
        self.output_buffer = OutputBuffer()
        self.exit_code: Optional[int] = None
        self.stop_reason: Optional[str] = None  # 'interrupt', 'complete', 'error'
        self.process: Optional[subprocess.Popen] = None
        
    def duration(self) -> float:
        """Get session duration in seconds"""
        end = self.end_time or time.time()
        return end - self.start_time
    
    def idle_time(self) -> float:
        """Get time since last output"""
        if not self.last_output_time:
            return 0.0
        return time.time() - self.last_output_time
    
    def add_output(self, line: str, stream: str):
        """Add output line to buffer"""
        timestamp = time.time()
        self.last_output_time = timestamp
        
        if stream == 'stdout':
            self.output_buffer.add_stdout(line, timestamp)
        elif stream == 'stderr':
            self.output_buffer.add_stderr(line, timestamp)
    
    def get_context_for_interrupt(self) -> Dict[str, Any]:
        """Get context information when user interrupts"""
        return {
            'duration': self.duration(),
            'idle_time': self.idle_time(),
            'line_counts': self.output_buffer.get_line_count_by_stream(),
            'last_lines': self.output_buffer.get_last_n_lines(20),
            'last_stdout': self.output_buffer.get_last_n_by_stream(20)[0],
            'last_stderr': self.output_buffer.get_last_n_by_stream(20)[1],
        }


def run_watch_mode(command: List[str], args, project_path: str = ".", 
                   project_type: str = "unknown", 
                   execution_id: Optional[str] = None) -> int:
    """
    Run command in watch mode - capture all output, learn from Ctrl+C
    
    Args:
        command: Command and arguments to execute
        args: Parsed arguments namespace
        project_path: Current project directory
        project_type: Detected project type (node, python, etc.)
    
    Returns:
        Exit code from command
    """
    # Create session
    session = WatchSession(command, project_path, project_type)
    
    # Print helpful message
    if not args.quiet:
        print("🔍 Watch mode enabled (no pattern specified)", file=sys.stderr, flush=True)
        print("   • All output is being captured and analyzed", file=sys.stderr, flush=True)
        print("   • Press Ctrl+C when you see an error to teach earlyexit", file=sys.stderr, flush=True)
        print("   • stdout/stderr are tracked separately for analysis", file=sys.stderr, flush=True)
        print("", file=sys.stderr, flush=True)
    
    # Set up SIGINT handler (will be implemented in interactive.py)
    original_sigint = signal.signal(signal.SIGINT, signal.default_int_handler)
    interrupted = [False]  # Mutable container for interrupt flag
    
    def sigint_handler(signum, frame):
        interrupted[0] = True
        if session.process:
            try:
                session.process.terminate()
            except:
                pass
    
    signal.signal(signal.SIGINT, sigint_handler)
    
    try:
        # Start process
        session.process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Monitor threads for stdout and stderr
        def monitor_stdout():
            try:
                for line in session.process.stdout:
                    line = line.rstrip('\n')
                    session.add_output(line, 'stdout')
                    if not args.quiet:
                        print(line, flush=True)
            except:
                pass
        
        def monitor_stderr():
            try:
                for line in session.process.stderr:
                    line = line.rstrip('\n')
                    session.add_output(line, 'stderr')
                    if not args.quiet:
                        print(line, file=sys.stderr, flush=True)
            except:
                pass
        
        stdout_thread = threading.Thread(target=monitor_stdout, daemon=True)
        stderr_thread = threading.Thread(target=monitor_stderr, daemon=True)
        
        stdout_thread.start()
        stderr_thread.start()
        
        # Wait for process
        session.process.wait()
        
        # Wait for threads to finish
        stdout_thread.join(timeout=1)
        stderr_thread.join(timeout=1)
        
        session.exit_code = session.process.returncode
        session.end_time = time.time()
        session.stop_reason = 'complete'
        
    except KeyboardInterrupt:
        # User pressed Ctrl+C
        session.end_time = time.time()
        session.stop_reason = 'interrupt'
        interrupted[0] = True
        
        # Kill process if still running
        if session.process and session.process.poll() is None:
            try:
                session.process.kill()
                session.process.wait(timeout=1)
            except:
                pass
        
        # Get context for interactive learning
        context = session.get_context_for_interrupt()
        
        # Call interactive learning module
        learning_result = None
        if not args.quiet:
            try:
                from earlyexit.interactive import show_interactive_prompt
                learning_result = show_interactive_prompt(session, context)
            except Exception as e:
                # Gracefully handle any errors in interactive mode
                print(f"\n⚠️  Interactive learning error: {e}", file=sys.stderr)
                print(f"⚠️  Interrupted at {context['duration']:.1f}s", file=sys.stderr, flush=True)
                print(f"   • Captured {context['line_counts']['stdout']} stdout lines", 
                      file=sys.stderr, flush=True)
                print(f"   • Captured {context['line_counts']['stderr']} stderr lines", 
                      file=sys.stderr, flush=True)
        
        # Store learning result in session for telemetry
        session.learning_result = learning_result
        
        # Save learning result to telemetry if enabled and result exists
        if learning_result and execution_id:
            try:
                from earlyexit.telemetry import get_telemetry
                from earlyexit.features import extract_features
                import hashlib
                
                telemetry_collector = get_telemetry()
                if telemetry_collector and telemetry_collector.enabled:
                    # Save user session
                    session_data = {
                        'execution_id': execution_id,
                        'timestamp': session.start_time,
                        'command': ' '.join(command),
                        'duration': context['duration'],
                        'idle_time': context['idle_time'],
                        'stop_reason': learning_result.get('stop_reason', 'unknown'),
                        'line_counts': context['line_counts'],
                        'selected_pattern': learning_result.get('selected_pattern'),
                        'pattern_confidence': learning_result.get('pattern_confidence'),
                        'pattern_stream': learning_result.get('pattern_stream'),
                        'timeout_suggestions': learning_result.get('timeout_suggestions', {}),
                        'project_type': project_type,
                        'working_directory': project_path
                    }
                    telemetry_collector.record_user_session(session_data)
                    
                    # Save learned setting if user selected a pattern
                    if learning_result.get('_should_save_learned_setting') and learning_result.get('selected_pattern'):
                        command_str = ' '.join(command)
                        command_hash = hashlib.sha256(command_str.encode()).hexdigest()[:16]
                        
                        # Extract features
                        features = extract_features(session_data)
                        
                        # Convert features to simple dict for JSON storage
                        features_dict = {name: feat.to_dict() for name, feat in features.items()}
                        
                        timeout_sugg = learning_result.get('timeout_suggestions', {})
                        
                        setting_data = {
                            'command_hash': command_hash,
                            'project_type': project_type,
                            'features': features_dict,
                            'learned_pattern': learning_result.get('selected_pattern'),
                            'pattern_confidence': learning_result.get('pattern_confidence', 0.0),
                            'learned_timeout': timeout_sugg.get('overall_timeout'),
                            'learned_idle_timeout': timeout_sugg.get('idle_timeout'),
                            'learned_delay_exit': timeout_sugg.get('delay_exit')
                        }
                        
                        telemetry_collector.save_learned_setting(setting_data)
            except Exception:
                # Silently fail - don't disrupt user experience
                pass
        
        # Return exit code 130 (128 + SIGINT=2) for interrupted
        return 130
    
    finally:
        # Restore original SIGINT handler
        signal.signal(signal.SIGINT, original_sigint)
    
    return session.exit_code if session.exit_code is not None else 1


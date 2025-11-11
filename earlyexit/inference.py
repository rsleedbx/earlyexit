#!/usr/bin/env python3
"""
earlyexit inference engine - ML-powered recommendations and auto-tuning
"""

import sqlite3
import json
import os
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from collections import defaultdict
import statistics


class InferenceEngine:
    """Analyzes telemetry data to provide intelligent recommendations"""
    
    def __init__(self, telemetry_collector):
        self.collector = telemetry_collector
    
    def _detect_context(self) -> Tuple[str, str]:
        """Detect current project type and command context"""
        cwd = os.getcwd()
        
        # Detect project type
        path = Path(cwd)
        project_type = 'unknown'
        if (path / 'package.json').exists():
            project_type = 'nodejs'
        elif (path / 'pyproject.toml').exists() or (path / 'setup.py').exists():
            project_type = 'python'
        elif (path / 'Cargo.toml').exists():
            project_type = 'rust'
        elif (path / 'go.mod').exists():
            project_type = 'go'
        elif (path / 'Dockerfile').exists():
            project_type = 'docker'
        
        return project_type, cwd
    
    def suggest_patterns(self, command: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Suggest patterns based on current context and historical effectiveness
        
        Returns list of suggestions with pattern, confidence, and rationale
        """
        if not self.collector:
            return []
        
        project_type, cwd = self._detect_context()
        
        # Detect command category from provided command
        command_category = 'other'
        if command:
            cmd_lower = command.lower()
            if 'test' in cmd_lower or 'pytest' in cmd_lower:
                command_category = 'test'
            elif 'build' in cmd_lower or 'make' in cmd_lower:
                command_category = 'build'
            elif 'deploy' in cmd_lower:
                command_category = 'deploy'
            elif 'lint' in cmd_lower:
                command_category = 'lint'
            elif 'run' in cmd_lower:
                command_category = 'run'
        
        with self.collector._get_connection() as conn:
            if not conn:
                return []
            
            cursor = conn.cursor()
            
            # Find patterns that worked well for similar contexts
            cursor.execute("""
                SELECT 
                    pattern,
                    COUNT(*) as uses,
                    SUM(CASE WHEN match_count > 0 THEN 1 ELSE 0 END) as successful_matches,
                    AVG(CASE WHEN match_count > 0 THEN total_runtime ELSE NULL END) as avg_match_time,
                    project_type,
                    command_category
                FROM executions
                WHERE pattern IS NOT NULL
                  AND (project_type = ? OR project_type = 'unknown')
                  AND (command_category = ? OR command_category = 'other')
                GROUP BY pattern
                HAVING uses >= 1
                ORDER BY 
                    (CAST(successful_matches AS REAL) / uses) DESC,
                    uses DESC
                LIMIT ?
            """, (project_type, command_category, limit * 2))
            
            results = cursor.fetchall()
            
            suggestions = []
            for pattern, uses, matches, avg_time, p_type, c_category in results:
                if pattern is None:
                    continue
                
                success_rate = (matches / uses) if uses > 0 else 0.0
                
                # Calculate confidence score (0-1)
                confidence = min(1.0, (success_rate * 0.7) + (min(uses, 10) / 10 * 0.3))
                
                # Build rationale
                rationale_parts = []
                if p_type == project_type:
                    rationale_parts.append(f"Works well for {project_type} projects")
                if c_category == command_category:
                    rationale_parts.append(f"Effective for {command_category} commands")
                rationale_parts.append(f"Success rate: {success_rate*100:.1f}% ({matches}/{uses} matches)")
                
                if avg_time is not None:
                    rationale_parts.append(f"Avg detection time: {avg_time:.1f}s")
                
                suggestions.append({
                    'pattern': pattern,
                    'confidence': confidence,
                    'uses': uses,
                    'success_rate': success_rate,
                    'rationale': ', '.join(rationale_parts),
                    'project_type': p_type,
                    'command_category': c_category
                })
            
            # Sort by confidence and return top N
            suggestions.sort(key=lambda x: x['confidence'], reverse=True)
            return suggestions[:limit]
    
    def suggest_timeouts(self, command: Optional[str] = None) -> Dict[str, Any]:
        """
        Suggest optimal timeout values based on historical data
        
        Returns dict with recommended timeout values and confidence
        """
        if not self.collector:
            return {}
        
        project_type, cwd = self._detect_context()
        
        with self.collector._get_connection() as conn:
            if not conn:
                return {}
            
            cursor = conn.cursor()
            
            # Get historical runtimes for similar contexts
            cursor.execute("""
                SELECT 
                    total_runtime,
                    overall_timeout,
                    idle_timeout,
                    delay_exit
                FROM executions
                WHERE project_type = ?
                  AND total_runtime IS NOT NULL
                  AND exit_reason != 'timeout'
                ORDER BY timestamp DESC
                LIMIT 50
            """, (project_type,))
            
            results = cursor.fetchall()
        
        if not results:
            # No historical data, use conservative defaults
            return {
                'overall_timeout': 300.0,  # 5 minutes
                'idle_timeout': 30.0,      # 30 seconds
                'delay_exit': 10.0,        # 10 seconds
                'confidence': 0.1,
                'rationale': 'No historical data available, using conservative defaults'
            }
        
        runtimes = [r[0] for r in results if r[0] is not None]
        
        if not runtimes:
            return {
                'overall_timeout': 300.0,
                'idle_timeout': 30.0,
                'delay_exit': 10.0,
                'confidence': 0.1,
                'rationale': 'Insufficient runtime data, using defaults'
            }
        
        # Calculate statistics
        avg_runtime = statistics.mean(runtimes)
        median_runtime = statistics.median(runtimes)
        stdev_runtime = statistics.stdev(runtimes) if len(runtimes) > 1 else avg_runtime * 0.5
        
        # Recommend overall timeout: mean + 2*stdev (covers ~95% of cases)
        recommended_overall = avg_runtime + (2 * stdev_runtime)
        
        # Recommend idle timeout: 10% of average runtime, or 30s minimum
        recommended_idle = max(30.0, avg_runtime * 0.1)
        
        # Recommend delay exit based on historical patterns
        delay_exits = [r[3] for r in results if r[3] is not None and r[3] > 0]
        recommended_delay = statistics.median(delay_exits) if delay_exits else 10.0
        
        confidence = min(1.0, len(runtimes) / 50.0)
        
        return {
            'overall_timeout': round(recommended_overall, 1),
            'idle_timeout': round(recommended_idle, 1),
            'delay_exit': round(recommended_delay, 1),
            'confidence': confidence,
            'rationale': f'Based on {len(runtimes)} similar executions (avg: {avg_runtime:.1f}s, median: {median_runtime:.1f}s)',
            'stats': {
                'avg_runtime': avg_runtime,
                'median_runtime': median_runtime,
                'stdev_runtime': stdev_runtime,
                'sample_size': len(runtimes)
            }
        }
    
    def auto_tune_parameters(self, command: str, pattern: Optional[str] = None) -> Dict[str, Any]:
        """
        Automatically tune earlyexit parameters for a given command
        
        Returns dict with recommended parameters and confidence scores
        """
        if not self.collector:
            return {
                'error': 'No telemetry data available',
                'confidence': 0.0
            }
        
        project_type, cwd = self._detect_context()
        
        # Get pattern suggestions
        pattern_suggestions = self.suggest_patterns(command, limit=1)
        recommended_pattern = pattern_suggestions[0] if pattern_suggestions else None
        
        # Get timeout suggestions
        timeout_suggestions = self.suggest_timeouts(command)
        
        # Determine if we should use pattern or not
        use_pattern = False
        if pattern:
            use_pattern = True
            recommended_pattern = {'pattern': pattern, 'confidence': 1.0}
        elif recommended_pattern and recommended_pattern['confidence'] > 0.5:
            use_pattern = True
        
        result = {
            'command': command,
            'project_type': project_type,
            'recommendations': {}
        }
        
        if use_pattern and recommended_pattern:
            result['recommendations']['pattern'] = {
                'value': recommended_pattern['pattern'],
                'confidence': recommended_pattern.get('confidence', 0.5),
                'rationale': recommended_pattern.get('rationale', 'Based on historical data')
            }
        
        result['recommendations']['overall_timeout'] = {
            'value': timeout_suggestions.get('overall_timeout', 300.0),
            'confidence': timeout_suggestions.get('confidence', 0.3),
            'rationale': timeout_suggestions.get('rationale', 'Conservative default')
        }
        
        result['recommendations']['idle_timeout'] = {
            'value': timeout_suggestions.get('idle_timeout', 30.0),
            'confidence': timeout_suggestions.get('confidence', 0.3),
            'rationale': 'Detects when command hangs'
        }
        
        result['recommendations']['delay_exit'] = {
            'value': timeout_suggestions.get('delay_exit', 10.0),
            'confidence': timeout_suggestions.get('confidence', 0.3),
            'rationale': 'Captures full error context after match'
        }
        
        # Calculate overall confidence (average of all confidences)
        confidences = [rec.get('confidence', 0) for rec in result['recommendations'].values()]
        result['overall_confidence'] = statistics.mean(confidences) if confidences else 0.0
        
        return result
    
    def get_similar_executions(self, command: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find similar historical executions for learning"""
        if not self.collector:
            return []
        
        project_type, cwd = self._detect_context()
        
        with self.collector._get_connection() as conn:
            if not conn:
                return []
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    execution_id,
                    command,
                    pattern,
                    exit_code,
                    exit_reason,
                    total_runtime,
                    match_count,
                    delay_exit,
                    user_rating,
                    timestamp
                FROM executions
                WHERE project_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (project_type, limit))
            
            results = cursor.fetchall()
            
            executions = []
            for row in results:
                executions.append({
                    'execution_id': row[0],
                    'command': row[1],
                    'pattern': row[2],
                    'exit_code': row[3],
                    'exit_reason': row[4],
                    'total_runtime': row[5],
                    'match_count': row[6],
                    'delay_exit': row[7],
                    'user_rating': row[8],
                    'timestamp': row[9]
                })
            
            return executions


def get_inference_engine(telemetry_collector) -> Optional[InferenceEngine]:
    """Factory function to create inference engine"""
    if not telemetry_collector or not telemetry_collector.enabled:
        return None
    return InferenceEngine(telemetry_collector)


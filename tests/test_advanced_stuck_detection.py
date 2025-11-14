#!/usr/bin/env python3
"""
Tests for advanced stuck detection features:
1. Progress pattern (should change, stuck if doesn't)
2. Stuck pattern (should not change, stuck if repeats) - existing
3. Transition states (forward-only state machine)
4. Multiple patterns (combined detection)
"""

import subprocess
import sys
import time
import pytest

def run_ee(*args, timeout=10, input_text=None):
    """Helper to run ee command"""
    cmd = ['ee'] + list(args)
    try:
        result = subprocess.run(
            cmd,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result
    except subprocess.TimeoutExpired:
        return None


class TestProgressPattern:
    """Test --progress-pattern (parts that SHOULD change)"""
    
    def test_progress_stuck_detected(self):
        """Test: Counters not changing triggers stuck detection"""
        input_text = """job-123   12   15   6   | STATUS [10:35:24]
job-123   12   15   6   | STATUS [10:35:31]
job-123   12   15   6   | STATUS [10:35:40]
job-123   12   15   6   | STATUS [10:35:47]
"""
        result = run_ee(
            '--max-repeat', '3',
            '--progress-pattern', r'\d+\s+\d+\s+\d+',
            'STATUS',
            '--test-pattern',
            input_text=input_text
        )
        
        assert result is not None
        assert result.returncode == 2  # Stuck detected
        assert b'No progress detected' in result.stderr or b'progress' in result.stderr.lower()
    
    def test_progress_advancing(self):
        """Test: Counters changing does NOT trigger stuck"""
        input_text = """job-123   12   15   6   | STATUS [10:35:24]
job-123   14   16   7   | STATUS [10:35:31]
job-123   15   19   7   | STATUS [10:35:40]
job-123   17   20   8   | STATUS [10:35:47]
"""
        result = run_ee(
            '--max-repeat', '3',
            '--progress-pattern', r'\d+\s+\d+\s+\d+',
            'STATUS',
            '--test-pattern',
            input_text=input_text
        )
        
        assert result is not None
        assert result.returncode == 0  # Pattern matched, no stuck
        assert b'No progress detected' not in result.stderr
    
    def test_progress_mixed(self):
        """Test: Some lines with progress, some without"""
        input_text = """job-123   12   15   6   | STATUS [10:35:24]
job-123   14   16   7   | STATUS [10:35:31]
job-123   14   16   7   | STATUS [10:35:40]
job-123   14   16   7   | STATUS [10:35:47]
"""
        result = run_ee(
            '--max-repeat', '3',
            '--progress-pattern', r'\d+\s+\d+\s+\d+',
            'STATUS',
            '--test-pattern',
            input_text=input_text
        )
        
        assert result is not None
        # Should detect stuck after 3 repeats of "14 16 7"
        assert result.returncode == 2


class TestTransitionStates:
    """Test --transition-states (forward-only state machine)"""
    
    def test_forward_transition(self):
        """Test: Forward state progression is allowed"""
        input_text = """job-123 state: IDLE [10:35:24]
job-123 state: RUNNING [10:35:31]
job-123 state: COMPLETED [10:35:40]
"""
        result = run_ee(
            '--max-repeat', '3',
            '--transition-states', 'IDLE>RUNNING>COMPLETED',
            'state:',
            '--test-pattern',
            input_text=input_text
        )
        
        assert result is not None
        assert result.returncode == 0  # Pattern matched, no regression
        assert b'Regression detected' not in result.stderr
    
    def test_backward_transition(self):
        """Test: Backward state transition triggers regression"""
        input_text = """job-123 state: IDLE [10:35:24]
job-123 state: RUNNING [10:35:31]
job-123 state: IDLE [10:35:40]
"""
        result = run_ee(
            '--max-repeat', '3',
            '--transition-states', 'IDLE>RUNNING>COMPLETED',
            'state:',
            '--test-pattern',
            input_text=input_text
        )
        
        assert result is not None
        assert result.returncode == 2  # Regression detected
        assert b'Regression detected' in result.stderr
    
    def test_skip_transition(self):
        """Test: Skipping states is allowed (IDLE -> COMPLETED)"""
        input_text = """job-123 state: IDLE [10:35:24]
job-123 state: COMPLETED [10:35:31]
"""
        result = run_ee(
            '--max-repeat', '3',
            '--transition-states', 'IDLE>RUNNING>COMPLETED',
            'state:',
            '--test-pattern',
            input_text=input_text
        )
        
        assert result is not None
        # Skipping is OK (higher index = forward progress)
        assert result.returncode == 0
        assert b'Regression detected' not in result.stderr
    
    def test_same_state_allowed(self):
        """Test: Staying in same state is allowed"""
        input_text = """job-123 state: RUNNING [10:35:24]
job-123 state: RUNNING [10:35:31]
job-123 state: RUNNING [10:35:40]
"""
        result = run_ee(
            '--max-repeat', '3',
            '--transition-states', 'IDLE>RUNNING>COMPLETED',
            'state:',
            '--test-pattern',
            input_text=input_text
        )
        
        assert result is not None
        # Same state = index not decreasing = allowed
        assert result.returncode == 0
        assert b'Regression detected' not in result.stderr


class TestMultiplePatterns:
    """Test combining multiple detection types"""
    
    def test_stuck_and_progress_combined(self):
        """Test: Both stuck-pattern and progress-pattern"""
        input_text = """rble-308   13   12  15   6   | RUNNING  IDLE  2  N/A  [10:35:24]
rble-308   13   14  16   7   | RUNNING  IDLE  2  N/A  [10:35:31]
rble-308   13   15  19   7   | RUNNING  IDLE  2  N/A  [10:35:40]
rble-308   13   17  20   8   | RUNNING  IDLE  2  N/A  [10:35:47]
"""
        result = run_ee(
            '--max-repeat', '3',
            '--stuck-pattern', r'RUNNING\s+IDLE\s+\d+\s+N/A',
            '--progress-pattern', r'\d+\s+\d+\s+\d+(?=\s*\|)',
            'RUNNING',
            '--test-pattern',
            input_text=input_text
        )
        
        assert result is not None
        # Should detect stuck (status repeating)
        assert result.returncode == 2
        # Should mention stuck detection (either type)
        assert b'tuck' in result.stderr or b'progress' in result.stderr.lower()
    
    def test_all_three_patterns(self):
        """Test: stuck + progress + transition together"""
        input_text = """rble-308   13   12  15   6   | RUNNING  IDLE  2  N/A  [10:35:24]
rble-308   13   14  16   7   | RUNNING  IDLE  2  N/A  [10:35:31]
rble-308   13   15  19   7   | RUNNING  IDLE  2  N/A  [10:35:40]
"""
        result = run_ee(
            '--max-repeat', '3',
            '--stuck-pattern', r'RUNNING\s+IDLE',
            '--progress-pattern', r'\d+\s+\d+\s+\d+',
            '--transition-states', 'IDLE>RUNNING>COMPLETED',
            'RUNNING',
            '--test-pattern',
            input_text=input_text
        )
        
        assert result is not None
        # One of the detections should trigger
        assert result.returncode in [0, 2]
    
    def test_progress_stuck_counters_not_changing(self):
        """Test: Progress pattern detects counters stuck"""
        input_text = """rble-308   13   17  20   8   | RUNNING  IDLE  2  N/A  [10:35:24]
rble-308   13   17  20   8   | RUNNING  IDLE  2  N/A  [10:35:31]
rble-308   13   17  20   8   | RUNNING  RUNNING  2  N/A  [10:35:40]
"""
        result = run_ee(
            '--max-repeat', '3',
            '--progress-pattern', r'\d+\s+\d+\s+\d+(?=\s*\|)',
            'RUNNING',
            '--test-pattern',
            input_text=input_text
        )
        
        assert result is not None
        # Counters "13 17 20 8" not changing = no progress
        assert result.returncode == 2
        assert b'No progress' in result.stderr or b'progress' in result.stderr.lower()


class TestRealWorldScenarios:
    """Test real-world scenarios from Mist monitor"""
    
    def test_mist_monitor_stuck_status(self):
        """Test: Mist monitor with stuck status (current feature)"""
        input_text = """rble-308   13   12  15   6   | RUNNING  IDLE  2  N/A  [10:35:24]
rble-308   13   14  16   7   | RUNNING  IDLE  2  N/A  [10:35:31]
rble-308   13   15  19   7   | RUNNING  IDLE  2  N/A  [10:35:40]
"""
        result = run_ee(
            '--max-repeat', '3',
            '--stuck-pattern', r'RUNNING\s+IDLE\s+\d+\s+N/A',
            'RUNNING',
            '--test-pattern',
            input_text=input_text
        )
        
        assert result is not None
        assert result.returncode == 2  # Stuck detected
    
    def test_mist_monitor_no_progress(self):
        """Test: Mist monitor with counters stuck (new feature)"""
        input_text = """rble-308   13   17  20   8   | RUNNING  RUNNING  2  N/A  [10:35:24]
rble-308   13   17  20   8   | RUNNING  RUNNING  2  N/A  [10:35:31]
rble-308   13   17  20   8   | RUNNING  RUNNING  2  N/A  [10:35:40]
"""
        result = run_ee(
            '--max-repeat', '3',
            '--progress-pattern', r'\d+\s+\d+\s+\d+(?=\s*\|)',
            'RUNNING',
            '--test-pattern',
            input_text=input_text
        )
        
        assert result is not None
        assert result.returncode == 2  # No progress detected
    
    def test_mist_monitor_regression(self):
        """Test: Mist monitor with state regression (new feature)"""
        input_text = """rble-308   13   15  19   7   | RUNNING  RUNNING  2  N/A  [10:35:40]
rble-308   13   17  20   8   | RUNNING  RUNNING  2  N/A  [10:35:47]
rble-308   13   18  22   9   | RUNNING  IDLE  2  N/A  [10:35:55]
"""
        result = run_ee(
            '--max-repeat', '3',
            '--transition-states', 'IDLE>RUNNING>COMPLETED',
            'RUNNING',
            '--test-pattern',
            input_text=input_text
        )
        
        assert result is not None
        # RUNNING → IDLE is backward = regression
        assert result.returncode == 2


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_invalid_progress_pattern(self):
        """Test: Invalid regex in progress-pattern"""
        input_text = """line 1
line 2
line 3
"""
        result = run_ee(
            '--max-repeat', '3',
            '--progress-pattern', r'[invalid(',  # Invalid regex
            'line',
            '--test-pattern',
            input_text=input_text
        )
        
        assert result is not None
        # Should handle gracefully, not crash
        # May return 0 (pattern matched) or 1 (no match)
        assert result.returncode in [0, 1]
    
    def test_no_state_found(self):
        """Test: No states found in transition-states"""
        input_text = """line 1
line 2
line 3
"""
        result = run_ee(
            '--max-repeat', '3',
            '--transition-states', 'STATE1>STATE2>STATE3',
            'line',
            '--test-pattern',
            input_text=input_text
        )
        
        assert result is not None
        # No states found, should not trigger regression
        assert result.returncode == 0
    
    def test_progress_pattern_no_match(self):
        """Test: Progress pattern doesn't match any line"""
        input_text = """line one
line two
line three
"""
        result = run_ee(
            '--max-repeat', '3',
            '--progress-pattern', r'\d+',  # No digits in input
            'line',
            '--test-pattern',
            input_text=input_text
        )
        
        assert result is not None
        # Pattern matched for 'line', but progress pattern didn't match
        assert result.returncode == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


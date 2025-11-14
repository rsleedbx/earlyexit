"""
Tests for stuck/no-progress detection feature
"""
import subprocess
import sys
import time


def run_ee(*args, input_text=None, timeout=10):
    """Helper to run earlyexit CLI"""
    cmd = [sys.executable, '-m', 'earlyexit.cli'] + list(args)
    result = subprocess.run(
        cmd,
        input=input_text.encode() if input_text else None,
        capture_output=True,
        timeout=timeout
    )
    return result


class TestBasicStuckDetection:
    """Test basic stuck detection without timestamp normalization"""
    
    def test_simple_repeat_detection(self):
        """Test basic repeat detection with exact matches"""
        input_lines = "line1\n" * 6  # Repeat 6 times
        result = run_ee('--max-repeat', '5', 'ERROR', input_text=input_lines)
        
        assert result.returncode == 2  # Stuck detected
        assert b'Stuck detected' in result.stderr
        assert b'repeated 5 times' in result.stderr
    
    def test_no_stuck_with_varying_lines(self):
        """Test that varying lines don't trigger stuck detection"""
        input_lines = "line1\nline2\nline3\nline4\nline5\nline6\n"
        result = run_ee('--max-repeat', '5', 'ERROR', input_text=input_lines)
        
        assert result.returncode == 1  # No match (pattern 'ERROR' not found)
        assert b'Stuck detected' not in result.stderr
    
    def test_stuck_with_higher_threshold(self):
        """Test stuck detection with higher repeat threshold"""
        input_lines = "same line\n" * 15
        result = run_ee('--max-repeat', '10', 'ERROR', input_text=input_lines)
        
        assert result.returncode == 2  # Stuck detected
        assert b'repeated 10 times' in result.stderr
    
    def test_pattern_match_before_stuck(self):
        """Test that pattern match takes precedence over stuck detection"""
        input_lines = "line1\nline1\nline1\nERROR: failed\nline1\nline1\n"
        result = run_ee('--max-repeat', '5', 'ERROR', input_text=input_lines)
        
        # Pattern matched first
        assert result.returncode == 0  # Match
        assert b'Stuck detected' not in result.stderr


class TestTimestampNormalization:
    """Test smart stuck detection with timestamp normalization"""
    
    def test_bracketed_timestamp_normalization(self):
        """Test normalization of [HH:MM:SS] timestamps"""
        input_lines = (
            "rble-308   -    0        0        0        | N/A    [09:03:45]\n"
            "rble-308   -    0        0        0        | N/A    [09:03:55]\n"
            "rble-308   -    0        0        0        | N/A    [09:04:05]\n"
            "rble-308   -    0        0        0        | N/A    [09:04:15]\n"
            "rble-308   -    0        0        0        | N/A    [09:04:25]\n"
            "rble-308   -    0        0        0        | N/A    [09:04:35]\n"
        )
        result = run_ee('--max-repeat', '5', '--stuck-ignore-timestamps', 'ERROR', 
                       input_text=input_lines)
        
        assert result.returncode == 2  # Stuck detected
        assert b'ignoring timestamps' in result.stderr
    
    def test_iso_date_normalization(self):
        """Test normalization of YYYY-MM-DD dates"""
        input_lines = (
            "2024-11-14 Status: pending\n"
            "2024-11-15 Status: pending\n"
            "2024-11-16 Status: pending\n"
            "2024-11-17 Status: pending\n"
            "2024-11-18 Status: pending\n"
            "2024-11-19 Status: pending\n"
        )
        result = run_ee('--max-repeat', '5', '--stuck-ignore-timestamps', 'ERROR',
                       input_text=input_lines)
        
        assert result.returncode == 2  # Stuck detected
    
    def test_iso8601_timestamp_normalization(self):
        """Test normalization of ISO 8601 timestamps"""
        input_lines = (
            "2024-11-14T09:03:45Z Request ID: pending\n"
            "2024-11-14T09:03:55Z Request ID: pending\n"
            "2024-11-14T09:04:05Z Request ID: pending\n"
            "2024-11-14T09:04:15Z Request ID: pending\n"
            "2024-11-14T09:04:25Z Request ID: pending\n"
            "2024-11-14T09:04:35Z Request ID: pending\n"
        )
        result = run_ee('--max-repeat', '5', '--stuck-ignore-timestamps', 'ERROR',
                       input_text=input_lines)
        
        assert result.returncode == 2  # Stuck detected
    
    def test_unix_epoch_normalization(self):
        """Test normalization of Unix epoch timestamps"""
        input_lines = (
            "1731578625 Status: waiting\n"
            "1731578635 Status: waiting\n"
            "1731578645 Status: waiting\n"
            "1731578655 Status: waiting\n"
            "1731578665 Status: waiting\n"
            "1731578675 Status: waiting\n"
        )
        result = run_ee('--max-repeat', '5', '--stuck-ignore-timestamps', 'ERROR',
                       input_text=input_lines)
        
        assert result.returncode == 2  # Stuck detected
    
    def test_without_normalization_timestamps_differ(self):
        """Test that without normalization, timestamps make lines different"""
        input_lines = (
            "Status: waiting [09:03:45]\n"
            "Status: waiting [09:03:55]\n"
            "Status: waiting [09:04:05]\n"
            "Status: waiting [09:04:15]\n"
            "Status: waiting [09:04:25]\n"
            "Status: waiting [09:04:35]\n"
        )
        # Without --stuck-ignore-timestamps
        result = run_ee('--max-repeat', '5', 'ERROR', input_text=input_lines)
        
        # Should NOT detect stuck (lines are different)
        assert result.returncode == 1  # No match
        assert b'Stuck detected' not in result.stderr


class TestStuckWithPatterns:
    """Test stuck detection with various pattern options"""
    
    def test_stuck_with_success_pattern(self):
        """Test stuck detection with success pattern"""
        input_lines = "waiting...\n" * 10
        result = run_ee('--max-repeat', '5', '--success-pattern', 'SUCCESS', 
                       input_text=input_lines)
        
        assert result.returncode == 2  # Stuck detected
    
    def test_stuck_with_exclusions(self):
        """Test stuck detection with pattern exclusions"""
        input_lines = (
            "Status: waiting\n" * 3 +
            "Status: OK (transient)\n" +  # This line excluded
            "Status: waiting\n" * 3
        )
        result = run_ee('--max-repeat', '5', '--exclude', 'OK', 'ERROR',
                       input_text=input_lines)
        
        # The excluded line doesn't break the repeat count
        assert result.returncode == 2  # Stuck detected
    
    def test_stuck_with_invert_match(self):
        """Test stuck detection with invert match"""
        input_lines = "no error here\n" * 10
        result = run_ee('--max-repeat', '5', '-v', 'ERROR', input_text=input_lines)
        
        # Invert match doesn't affect stuck detection
        assert result.returncode == 2  # Stuck detected


class TestStuckEdgeCases:
    """Test edge cases for stuck detection"""
    
    def test_empty_lines_not_stuck(self):
        """Test that empty lines don't trigger stuck detection"""
        input_lines = "\n" * 10
        result = run_ee('--max-repeat', '5', 'ERROR', input_text=input_lines)
        
        # Empty lines are normalized to empty string, which is falsy
        # So they shouldn't trigger stuck detection
        assert result.returncode == 1  # No match
    
    def test_stuck_count_exactly_threshold(self):
        """Test stuck detection at exactly the threshold"""
        input_lines = "line\n" * 5  # Exactly 5 repeats
        result = run_ee('--max-repeat', '5', 'ERROR', input_text=input_lines)
        
        assert result.returncode == 2  # Stuck detected at threshold
    
    def test_stuck_count_one_below_threshold(self):
        """Test that one below threshold doesn't trigger stuck"""
        input_lines = "line\n" * 4  # 4 repeats (threshold is 5)
        result = run_ee('--max-repeat', '5', 'ERROR', input_text=input_lines)
        
        assert result.returncode == 1  # No match, no stuck
        assert b'Stuck detected' not in result.stderr
    
    def test_stuck_reset_on_different_line(self):
        """Test that repeat count resets when line changes"""
        input_lines = (
            "line1\n" * 3 +
            "line2\n" +  # Different line resets counter
            "line1\n" * 3
        )
        result = run_ee('--max-repeat', '5', 'ERROR', input_text=input_lines)
        
        # Counter reset, so never reaches 5
        assert result.returncode == 1  # No match
        assert b'Stuck detected' not in result.stderr


class TestStuckCommandMode:
    """Test stuck detection in command mode"""
    
    def test_stuck_with_command(self):
        """Test stuck detection with actual command"""
        # Use a simple Python command that prints the same line repeatedly
        result = run_ee(
            '--max-repeat', '3', 'ERROR', '--',
            sys.executable, '-c',
            'import time; [print("stuck line") or time.sleep(0.1) for _ in range(10)]',
            timeout=5
        )
        
        assert result.returncode == 2  # Stuck detected
        assert b'Stuck detected' in result.stderr
    
    def test_stuck_with_timeout_and_command(self):
        """Test stuck detection with timeout in command mode"""
        result = run_ee(
            '-t', '10', '--max-repeat', '3', 'ERROR', '--',
            sys.executable, '-c',
            'import time; [print("stuck") or time.sleep(0.1) for _ in range(10)]',
            timeout=15
        )
        
        # Stuck should be detected before timeout
        assert result.returncode == 2  # Stuck detected
        assert b'Stuck detected' in result.stderr


class TestStuckQuietMode:
    """Test stuck detection with quiet mode"""
    
    def test_stuck_with_quiet(self):
        """Test that stuck detection works with --quiet"""
        input_lines = "line\n" * 10
        result = run_ee('--max-repeat', '5', '-q', 'ERROR', input_text=input_lines)
        
        assert result.returncode == 2  # Stuck detected
        # No message in quiet mode
        assert result.stderr == b''
    
    def test_stuck_without_quiet(self):
        """Test that stuck message appears without --quiet"""
        input_lines = "line\n" * 10
        result = run_ee('--max-repeat', '5', 'ERROR', input_text=input_lines)
        
        assert result.returncode == 2  # Stuck detected
        assert b'Stuck detected' in result.stderr


class TestStuckWithJSON:
    """Test stuck detection with JSON output"""
    
    def test_stuck_json_output(self):
        """Test JSON output includes stuck information"""
        input_lines = "line\n" * 10
        result = run_ee('--max-repeat', '5', '--json', 'ERROR', input_text=input_lines)
        
        assert result.returncode == 2  # Stuck detected
        # Should have JSON in stdout
        assert b'"exit_code"' in result.stdout
        assert b'"exit_reason"' in result.stdout
        # Message suppressed in JSON mode
        assert b'Stuck detected' not in result.stderr


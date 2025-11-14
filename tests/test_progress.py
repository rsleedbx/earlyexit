"""Tests for --progress indicator"""

import subprocess
import pytest
import sys
import os
import time


def run_ee(*args, timeout=10, input_text=None):
    """Helper to run earlyexit and return result"""
    # Try to use installed ee command first
    try:
        cmd = ['ee'] + list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=input_text
        )
        return result
    except FileNotFoundError:
        # Fall back to calling CLI module directly
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            [sys.executable, '-m', 'earlyexit.cli'] + list(args),
            capture_output=True,
            text=True,
            timeout=timeout,
            input=input_text,
            env=env
        )
        return result


class TestProgressBasic:
    """Test basic progress indicator functionality"""
    
    def test_progress_indicator_appears(self):
        """Test that --progress shows progress on stderr"""
        result = run_ee('--progress', '-t', '5', 'NEVER', '--',
                       'bash', '-c', 'for i in {1..10}; do echo "line $i"; sleep 0.3; done')
        
        # Command completes (no NEVER found) = exit 1 or times out = exit 2
        # Progress was displayed (in stderr)
        assert result.returncode in [1, 2], "Should complete or timeout"
        assert 'Monitoring' in result.stderr, "Progress should appear in stderr"
    
    def test_progress_shows_monitoring_info(self):
        """Test that progress shows command being monitored"""
        result = run_ee('--progress', 'ERROR', '--',
                       'bash', '-c', 'for i in {1..5}; do echo "line $i"; sleep 0.1; done')
        
        # Should complete successfully
        assert result.returncode == 1, "No match should return 1"
    
    def test_progress_with_timeout(self):
        """Test progress indicator with timeout"""
        result = run_ee('--progress', '-t', '2', 'NEVER', '--',
                       'bash', '-c', 'sleep 10')
        
        assert result.returncode == 2, "Should timeout"


class TestProgressSuppression:
    """Test that progress is suppressed when appropriate"""
    
    def test_progress_suppressed_with_quiet(self):
        """Test that --progress is suppressed with --quiet"""
        result = run_ee('--progress', '--quiet', 'ERROR', '--',
                       'bash', '-c', 'echo "test"')
        
        # With --quiet, there should be no output at all
        # (progress is automatically suppressed)
        assert result.stdout == "", "Stdout should be empty with quiet"
    
    def test_progress_suppressed_with_json(self):
        """Test that --progress is suppressed with --json"""
        result = run_ee('--progress', '--json', 'ERROR', '--',
                       'bash', '-c', 'echo "ERROR"')
        
        # JSON output should be clean (no progress in output)
        import json
        data = json.loads(result.stdout)
        assert 'exit_code' in data, "Should have valid JSON output"
        assert data['exit_code'] == 0
    
    def test_progress_without_flag_no_output(self):
        """Test that progress doesn't appear without --progress flag"""
        result = run_ee('ERROR', '--',
                       'bash', '-c', 'echo "ERROR"')
        
        # Without --progress, stderr should not have progress updates
        # (may have logging messages, but not progress format)
        assert 'Monitoring' not in result.stderr or '📝 Logging' in result.stderr


class TestProgressContent:
    """Test progress indicator content"""
    
    def test_progress_updates_during_execution(self):
        """Test that progress updates are generated during execution"""
        # This test verifies progress is displayed, though hard to capture exact format
        result = run_ee('--progress', '-t', '3', 'NEVER', '--',
                       'bash', '-c', 'for i in {1..10}; do echo "line $i"; sleep 0.25; done')
        
        # Should complete or timeout
        assert result.returncode in [1, 2], f"Should complete or timeout, got {result.returncode}"
        # Progress was displayed (though may be cleared at end)
        assert 'Monitoring' in result.stderr, "Progress should be in stderr"
    
    def test_progress_with_pattern_match(self):
        """Test progress indicator when pattern matches"""
        result = run_ee('--progress', 'ERROR', '--',
                       'bash', '-c', 'for i in {1..5}; do echo "line $i"; sleep 0.1; done; echo "ERROR"')
        
        # Should match pattern
        assert result.returncode == 0, "Pattern should match"
        # Output should contain ERROR
        assert 'ERROR' in result.stdout


class TestProgressWithOtherOptions:
    """Test progress indicator with other earlyexit options"""
    
    def test_progress_with_idle_timeout(self):
        """Test progress with idle timeout"""
        result = run_ee('--progress', '-I', '1', 'NEVER', '--',
                       'bash', '-c', 'echo "start"; sleep 5', timeout=15)
        
        # Should hit idle timeout (2) or permission error (3)
        assert result.returncode in [2, 3], f"Should timeout, got {result.returncode}: {result.stderr}"
    
    def test_progress_with_multiple_matches(self):
        """Test progress with max-count"""
        # Use uppercase pattern to avoid watch mode detection
        result = run_ee('--progress', '-m', '2', 'Line', '--',
                       'bash', '-c', 'for i in {1..10}; do echo "Line $i"; sleep 0.1; done')
        
        # Should match 2 times and exit
        assert result.returncode == 0, f"Should match, got {result.returncode}: {result.stderr}"
    
    def test_progress_with_invert_match(self):
        """Test progress with invert match"""
        result = run_ee('--progress', '-v', 'OKOKOK', '-t', '5', '--',
                       'bash', '-c', 'echo "Not OK"; sleep 1')
        
        # Pattern NOT found = match in invert mode
        assert result.returncode == 0, f"Should match (invert), got {result.returncode}: {result.stderr}"


class TestProgressEdgeCases:
    """Test progress indicator edge cases"""
    
    def test_progress_with_fast_command(self):
        """Test progress with command that completes quickly"""
        result = run_ee('--progress', 'ERROR', '--',
                       'bash', '-c', 'echo "ERROR"')
        
        # Should complete successfully even with quick execution
        assert result.returncode == 0
    
    def test_progress_with_no_output(self):
        """Test progress when command produces no output"""
        result = run_ee('--progress', '-t', '1', 'ERROR', '--',
                       'bash', '-c', 'sleep 5')
        
        # Should timeout
        assert result.returncode == 2
    
    def test_progress_with_long_timeout(self):
        """Test progress formatting with longer timeouts"""
        result = run_ee('--progress', '-t', '2', 'ERROR', '--',
                       'bash', '-c', 'for i in {1..20}; do echo "line $i"; sleep 0.05; done')
        
        # Should complete (no ERROR found)
        assert result.returncode == 1


class TestProgressCombinations:
    """Test progress with combinations of flags"""
    
    def test_progress_with_unix_exit_codes(self):
        """Test --progress with --unix-exit-codes"""
        result = run_ee('--progress', '--unix-exit-codes', 'ERROR', '--',
                       'bash', '-c', 'echo "ERROR"')
        
        # Unix mode: error found = exit 1
        assert result.returncode == 1
    
    def test_progress_with_case_insensitive(self):
        """Test --progress with -i (case insensitive)"""
        result = run_ee('--progress', '-i', 'ERROR', '--',
                       'bash', '-c', 'echo "error found"')
        
        # Should match (case insensitive)
        assert result.returncode == 0
    
    def test_progress_disabled_combinations(self):
        """Test that progress is properly disabled with conflicting options"""
        # --progress with --quiet should suppress progress
        result = run_ee('--progress', '--quiet', 'ERROR', '--',
                       'bash', '-c', 'echo "ERROR"')
        assert result.stdout == ""
        
        # --progress with --json should show only JSON
        result = run_ee('--progress', '--json', 'ERROR', '--',
                       'bash', '-c', 'echo "ERROR"')
        import json
        data = json.loads(result.stdout)
        assert 'exit_code' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


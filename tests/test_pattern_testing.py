"""
Tests for pattern testing mode (--test-pattern)

Pattern testing mode allows users to test patterns against existing logs
without running commands, showing matches with line numbers and statistics.
"""

import subprocess
import pytest


def run_test_pattern(*args, input_text=None, timeout=5):
    """Helper to run ee --test-pattern"""
    try:
        # Try using 'ee' directly first
        cmd = ['ee', '--test-pattern'] + list(args)
        result = subprocess.run(
            cmd,
            input=input_text.encode() if input_text else None,
            capture_output=True,
            timeout=timeout
        )
    except FileNotFoundError:
        # Fallback to python -m earlyexit.cli
        import sys
        import os
        env = os.environ.copy()
        pythonpath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env['PYTHONPATH'] = pythonpath
        cmd = [sys.executable, '-m', 'earlyexit.cli', '--test-pattern'] + list(args)
        result = subprocess.run(
            cmd,
            input=input_text.encode() if input_text else None,
            capture_output=True,
            timeout=timeout,
            env=env
        )
    
    return result


class TestBasicPatternTesting:
    """Test basic pattern testing functionality"""
    
    def test_basic_pattern_match(self):
        """Basic pattern match shows line numbers"""
        input_text = "Line 1\nERROR: Something failed\nLine 3\n"
        result = run_test_pattern('ERROR', input_text=input_text)
        
        assert result.returncode == 0  # Match found
        assert b'Matched lines:   1' in result.stderr
        assert b'Line      2:  ERROR: Something failed' in result.stderr
    
    def test_no_match(self):
        """No match returns exit code 1"""
        input_text = "Line 1\nLine 2\nLine 3\n"
        result = run_test_pattern('ERROR', input_text=input_text)
        
        assert result.returncode == 1  # No match
        assert b'No matches found' in result.stderr
    
    def test_multiple_matches(self):
        """Multiple matches are all displayed"""
        input_text = "ERROR 1\nOK\nERROR 2\nOK\nERROR 3\n"
        result = run_test_pattern('ERROR', input_text=input_text)
        
        assert result.returncode == 0
        assert b'Matched lines:   3' in result.stderr
        assert b'Line      1:  ERROR 1' in result.stderr
        assert b'Line      3:  ERROR 2' in result.stderr
        assert b'Line      5:  ERROR 3' in result.stderr
    
    def test_statistics_display(self):
        """Statistics are correctly displayed"""
        input_text = "Line 1\nLine 2\nERROR\nLine 4\n"
        result = run_test_pattern('ERROR', input_text=input_text)
        
        assert b'Total lines:     4' in result.stderr
        assert b'Matched lines:   1' in result.stderr


class TestPatternExclusions:
    """Test pattern exclusions in test mode"""
    
    def test_basic_exclusion(self):
        """Exclusion filters out matches"""
        input_text = "ERROR: Real\nERROR_OK: Expected\nERROR: Another\n"
        result = run_test_pattern('--exclude', 'ERROR_OK', 'ERROR', input_text=input_text)
        
        assert result.returncode == 0
        assert b'Matched lines:   2' in result.stderr
        assert b'Excluded lines:  1' in result.stderr
        assert b'ERROR_OK' not in result.stderr.split(b'Pattern matched')[1]  # Not in matches section
    
    def test_multiple_exclusions(self):
        """Multiple exclusions work"""
        input_text = "ERROR\nERROR_OK\nERROR_EXPECTED\nERROR_REAL\n"
        result = run_test_pattern(
            '--exclude', 'ERROR_OK',
            '--exclude', 'ERROR_EXPECTED',
            'ERROR',
            input_text=input_text
        )
        
        assert result.returncode == 0
        assert b'Matched lines:   2' in result.stderr
        assert b'Excluded lines:  2' in result.stderr
    
    def test_all_excluded(self):
        """All matches excluded results in no matches"""
        input_text = "ERROR_OK\nERROR_OK\n"
        result = run_test_pattern('--exclude', 'ERROR_OK', 'ERROR', input_text=input_text)
        
        assert result.returncode == 1  # No matches after exclusion
        assert b'No matches found' in result.stderr


class TestSuccessErrorPatterns:
    """Test success/error pattern testing"""
    
    def test_success_pattern(self):
        """Success pattern matching"""
        input_text = "Starting\nSUCCESS: Deployed\nDone\n"
        result = run_test_pattern('--success-pattern', 'SUCCESS', input_text=input_text)
        
        assert result.returncode == 0
        assert b'Matched lines:   1' in result.stderr
        assert b'Line      2:  SUCCESS: Deployed' in result.stderr
    
    def test_error_pattern(self):
        """Error pattern matching"""
        input_text = "Starting\nERROR: Failed\nDone\n"
        result = run_test_pattern('--error-pattern', 'ERROR', input_text=input_text)
        
        assert result.returncode == 0
        assert b'Matched lines:   1' in result.stderr
        assert b'Line      2:  ERROR: Failed' in result.stderr
    
    def test_dual_patterns(self):
        """Both success and error patterns"""
        input_text = "Start\nSUCCESS: OK\nERROR: Failed\nDone\n"
        result = run_test_pattern(
            '--success-pattern', 'SUCCESS',
            '--error-pattern', 'ERROR',
            input_text=input_text
        )
        
        assert result.returncode == 0
        assert b'Matched lines:   2' in result.stderr
        assert b'Success matches: 1' in result.stderr
        assert b'Error matches:   1' in result.stderr
    
    def test_dual_patterns_with_exclusions(self):
        """Dual patterns with exclusions"""
        input_text = "SUCCESS\nERROR\nERROR_OK\nSUCCESS_TEST\n"
        result = run_test_pattern(
            '--success-pattern', 'SUCCESS',
            '--error-pattern', 'ERROR',
            '--exclude', 'ERROR_OK',
            input_text=input_text
        )
        
        assert result.returncode == 0
        assert b'Matched lines:   3' in result.stderr  # SUCCESS, ERROR, SUCCESS_TEST
        assert b'Excluded lines:  1' in result.stderr


class TestCaseInsensitive:
    """Test case-insensitive matching"""
    
    def test_case_insensitive(self):
        """Case-insensitive flag works"""
        input_text = "error\nError\nERROR\n"
        result = run_test_pattern('-i', 'ERROR', input_text=input_text)
        
        assert result.returncode == 0
        assert b'Matched lines:   3' in result.stderr
    
    def test_case_sensitive_default(self):
        """Case-sensitive by default"""
        input_text = "error\nError\nERROR\n"
        result = run_test_pattern('ERROR', input_text=input_text)
        
        assert result.returncode == 0
        assert b'Matched lines:   1' in result.stderr


class TestInvertMatch:
    """Test invert match in test mode"""
    
    def test_invert_match(self):
        """Invert match shows non-matching lines"""
        input_text = "OK\nERROR\nOK\n"
        result = run_test_pattern('-v', 'ERROR', input_text=input_text)
        
        assert result.returncode == 0
        assert b'Matched lines:   2' in result.stderr  # Line 1 and 3


class TestRegexPatterns:
    """Test regex patterns"""
    
    def test_regex_pattern(self):
        """Regex patterns work"""
        input_text = "Deployed\nDeployment complete\nDeploy failed\n"
        result = run_test_pattern(r'Deploy(ed|ment)', input_text=input_text)
        
        assert result.returncode == 0
        assert b'Matched lines:   2' in result.stderr
    
    def test_invalid_regex(self):
        """Invalid regex pattern"""
        input_text = "test\n"
        result = run_test_pattern('[invalid(', input_text=input_text)
        
        # Should error or handle gracefully
        assert result.returncode == 3


class TestEdgeCases:
    """Test edge cases"""
    
    def test_empty_input(self):
        """Empty input"""
        result = run_test_pattern('ERROR', input_text="")
        
        assert result.returncode == 1  # No matches
        assert b'Total lines:     0' in result.stderr
    
    def test_long_input(self):
        """Many matches (test limit display)"""
        # Create 50 ERROR lines
        input_text = "\n".join([f"ERROR {i}" for i in range(50)])
        result = run_test_pattern('ERROR', input_text=input_text)
        
        assert result.returncode == 0
        assert b'Matched lines:   50' in result.stderr
        assert b'... and 30 more matches' in result.stderr  # Only shows first 20
    
    def test_no_command_allowed(self):
        """Cannot run command with --test-pattern"""
        result = run_test_pattern('ERROR', '--', 'echo', 'test', input_text="test")
        
        assert result.returncode == 3
        assert b'cannot run a command' in result.stderr
    
    def test_empty_pattern(self):
        """Empty pattern"""
        input_text = "test\n"
        result = run_test_pattern('', input_text=input_text)
        
        # Matches everything or errors
        assert result.returncode in [0, 1, 3]


class TestRealWorldScenarios:
    """Test real-world use cases"""
    
    def test_terraform_log(self):
        """Test against simulated Terraform log"""
        input_text = """
Terraform will perform the following actions:
  + resource.example will be created
Acquiring state lock...
Error: early error detection is enabled
Apply complete! Resources: 1 added, 0 changed, 0 destroyed.
"""
        result = run_test_pattern(
            '--exclude', 'early error detection',
            'Error|Failed',
            input_text=input_text
        )
        
        assert result.returncode == 1  # No real errors after exclusion
        assert b'Excluded lines:  1' in result.stderr
    
    def test_database_migration_log(self):
        """Test against database migration log"""
        input_text = """
Starting migrations...
Running migration 001_initial...
Running migration 002_users...
Migrations applied successfully
"""
        result = run_test_pattern(
            '--success-pattern', 'successfully',
            '--error-pattern', 'ERROR|FATAL|failed',
            input_text=input_text
        )
        
        assert result.returncode == 0
        assert b'Success matches: 1' in result.stderr
        assert b'Error matches:   0' in result.stderr
    
    def test_docker_build_log(self):
        """Test against Docker build log"""
        input_text = """
Step 1/5 : FROM ubuntu:22.04
Step 2/5 : RUN apt-get update
Step 3/5 : COPY . /app
Successfully built abc123def456
Successfully tagged myapp:latest
"""
        result = run_test_pattern('Successfully', input_text=input_text)
        
        assert result.returncode == 0
        assert b'Matched lines:   2' in result.stderr


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


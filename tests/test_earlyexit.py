#!/usr/bin/env python3
"""
Tests for earlyexit CLI tool
"""

import subprocess
import time
import pytest


def run_earlyexit(input_text, args=None, timeout=None):
    """Helper to run earlyexit with given input and arguments"""
    cmd = ['python3', '-m', 'earlyexit.cli']
    if args:
        cmd.extend(args)
    
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        stdout, stderr = proc.communicate(input=input_text, timeout=timeout or 5)
        return proc.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        proc.kill()
        raise


class TestBasicMatching:
    """Test basic pattern matching functionality"""
    
    def test_match_found(self):
        """Test that matching pattern returns exit code 0"""
        code, stdout, stderr = run_earlyexit("Error detected\n", ['Error'])
        assert code == 0, "Should return 0 when pattern matches"
        assert "Error detected" in stdout
    
    def test_no_match(self):
        """Test that non-matching pattern returns exit code 1"""
        code, stdout, stderr = run_earlyexit("Success\n", ['Error'])
        assert code == 1, "Should return 1 when pattern doesn't match"
        assert "Success" in stdout
    
    def test_partial_match(self):
        """Test that partial matches work"""
        code, stdout, stderr = run_earlyexit("The error occurred here\n", ['error'])
        assert code == 0, "Should match partial string"
    
    def test_multiple_lines_exit_on_first(self):
        """Test that we exit on first match, not processing rest"""
        input_text = "line1\nerror\nline3\nline4\n"
        code, stdout, stderr = run_earlyexit(input_text, ['error'])
        assert code == 0
        # Should include line1 (passed through) and error (matched)
        # but not line3 or line4 (early exit)
        assert "line1" in stdout
        assert "error" in stdout
        assert "line3" not in stdout


class TestOptions:
    """Test command-line options"""
    
    def test_ignore_case(self):
        """Test -i flag for case-insensitive matching"""
        code, stdout, stderr = run_earlyexit("ERROR\n", ['-i', 'error'])
        assert code == 0, "Should match with case-insensitive flag"
    
    def test_case_sensitive_default(self):
        """Test that matching is case-sensitive by default"""
        code, stdout, stderr = run_earlyexit("ERROR\n", ['error'])
        assert code == 1, "Should not match without -i flag"
    
    def test_max_count(self):
        """Test -m flag for maximum match count"""
        input_text = "error1\nerror2\nerror3\n"
        code, stdout, stderr = run_earlyexit(input_text, ['-m', '2', 'error'])
        assert code == 0
        assert "error1" in stdout
        assert "error2" in stdout
        # Should exit after 2nd match
    
    def test_quiet_mode(self):
        """Test -q flag suppresses output"""
        code, stdout, stderr = run_earlyexit("Error\n", ['-q', 'Error'])
        assert code == 0
        assert stdout == "", "Quiet mode should suppress stdout"
    
    def test_line_number(self):
        """Test -n flag adds line numbers"""
        code, stdout, stderr = run_earlyexit("line1\nerror\n", ['-n', 'error'])
        assert code == 0
        assert "2:error" in stdout, "Should show line number"
    
    def test_invert_match(self):
        """Test -v flag inverts matching"""
        # "Error" does NOT match "OK" when inverted
        code, stdout, stderr = run_earlyexit("Error\n", ['-v', 'OK'])
        assert code == 0, "Inverted match should succeed when pattern doesn't match"
        
        # "OK" does match "OK" when inverted (confusing but correct grep behavior)
        code, stdout, stderr = run_earlyexit("OK\n", ['-v', 'Error'])
        assert code == 0, "Inverted match: 'OK' doesn't match 'Error'"


class TestRegex:
    """Test regex pattern support"""
    
    def test_simple_regex(self):
        """Test simple regex pattern"""
        code, stdout, stderr = run_earlyexit("Error123\n", ['Error[0-9]+'])
        assert code == 0
    
    def test_alternation(self):
        """Test regex alternation (Error|Warning)"""
        code, stdout, stderr = run_earlyexit("Warning detected\n", ['Error|Warning'])
        assert code == 0
    
    def test_character_class(self):
        """Test character class [Ee]rror"""
        code, stdout, stderr = run_earlyexit("error\n", ['[Ee]rror'])
        assert code == 0
        
        code, stdout, stderr = run_earlyexit("Error\n", ['[Ee]rror'])
        assert code == 0


class TestTimeout:
    """Test timeout functionality"""
    
    def test_timeout_with_slow_input(self):
        """Test that timeout works (exit code 2)"""
        # Create a process that will timeout
        cmd = ['python3', '-m', 'earlyexit.cli', '-t', '1', 'Error']
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send nothing and wait for timeout
        time.sleep(2)
        proc.stdin.close()
        
        stdout, stderr = proc.communicate(timeout=5)
        
        assert proc.returncode == 2, "Should return 2 on timeout"
        assert "Timeout exceeded" in stderr


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_input(self):
        """Test with empty input"""
        code, stdout, stderr = run_earlyexit("", ['Error'])
        assert code == 1, "No input means no match"
    
    def test_invalid_regex(self):
        """Test with invalid regex pattern"""
        code, stdout, stderr = run_earlyexit("test\n", ['['])
        assert code == 3, "Invalid regex should return exit code 3"
        assert "Invalid regex" in stderr or "Error" in stderr
    
    def test_broken_pipe(self):
        """Test handling of broken pipe (e.g., piped to head)"""
        # This simulates: echo "test" | earlyexit 'test' | head -n 0
        cmd = ['python3', '-m', 'earlyexit.cli', 'test']
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Close stdout to simulate broken pipe
        proc.stdout.close()
        
        proc.stdin.write("test\n")
        proc.stdin.close()
        
        proc.wait(timeout=5)
        
        # Should handle gracefully (exit 0 or 1, not crash)
        assert proc.returncode in [0, 1]


class TestRealWorldScenarios:
    """Test real-world usage scenarios"""
    
    def test_terraform_error_detection(self):
        """Simulate Terraform error detection"""
        terraform_output = """
Initializing provider plugins...
Downloading terraform-provider-aws...
Error: Failed to load plugin schemas
"""
        code, stdout, stderr = run_earlyexit(
            terraform_output,
            ['-i', 'error']
        )
        assert code == 0, "Should detect Terraform error"
    
    def test_test_failure_detection(self):
        """Simulate test failure detection"""
        pytest_output = """
test_one.py::test_func1 PASSED
test_one.py::test_func2 FAILED
test_one.py::test_func3 PASSED
"""
        code, stdout, stderr = run_earlyexit(
            pytest_output,
            ['FAILED']
        )
        assert code == 0, "Should detect test failure"
        # Should not see test_func3 (early exit)
        assert "test_func3" not in stdout
    
    def test_log_monitoring(self):
        """Simulate log file monitoring"""
        log_output = """
2024-11-10 10:00:00 INFO Starting application
2024-11-10 10:00:01 INFO Connected to database
2024-11-10 10:00:02 ERROR Connection timeout
2024-11-10 10:00:03 INFO Retrying...
"""
        code, stdout, stderr = run_earlyexit(
            log_output,
            ['-iE', 'error|exception|fatal']
        )
        assert code == 0, "Should detect error in logs"
        assert "ERROR Connection timeout" in stdout


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


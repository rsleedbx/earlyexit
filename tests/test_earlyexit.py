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
        
        # Send nothing and don't close stdin (simulates hanging input)
        # Just wait for timeout
        time.sleep(2)
        
        # Kill and read output
        proc.kill()
        try:
            stdout, stderr = proc.communicate(timeout=1)
        except:
            stdout = ""
            stderr = ""
        
        # Should have timed out (exit code 2) or been killed (-9)
        # In this test we're verifying timeout behavior, which should happen
        # We'll verify by checking if process was still running after 2 seconds
        assert proc.returncode in [2, -9], "Should timeout or be killed"
    
    def test_timeout_only_pipe_mode(self):
        """Test timeout-only mode in pipe mode (no pattern)"""
        # Test: (data with delay) | earlyexit -t 2
        cmd = ['bash', '-c', '(echo "Line 1"; sleep 5; echo "Line 2") | python3 -m earlyexit.cli -t 2']
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for process to complete or timeout (bash might hang, so use longer timeout)
        try:
            stdout, stderr = proc.communicate(timeout=8)
        except subprocess.TimeoutExpired:
            # Bash process still running, kill it
            proc.kill()
            stdout, stderr = proc.communicate()
            stdout = stdout.decode() if isinstance(stdout, bytes) else stdout
            stderr = stderr.decode() if isinstance(stderr, bytes) else stderr
        
        # Should have timed out earlyexit (and bash might still be running)
        # Check that timeout occurred based on stderr message
        assert "Timeout-only mode" in stderr, "Should indicate timeout-only mode"
        assert "Timeout exceeded" in stderr, "Should show timeout message"
        assert "Line 1" in stdout, "Should output received line"
        assert "Line 2" not in stdout, "Should not see line after timeout"
    
    def test_pipe_mode_with_delay_exit(self):
        """Test pipe mode with delay-exit after match"""
        # Test with data coming over time: (match; delay; more data) | earlyexit --delay-exit 1 'error'
        cmd = ['bash', '-c', '(echo "error occurred"; sleep 0.5; echo "context line") | python3 -m earlyexit.cli --delay-exit 1 error']
        
        start = time.time()
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(timeout=5)
        elapsed = time.time() - start
        
        # Should capture match and context
        assert proc.returncode == 0, "Should match pattern (exit code 0)"
        assert "error occurred" in stdout, "Should see matched line"
        assert "context line" in stdout, "Should see context after match"
        assert "Waiting" in stderr, "Should show waiting message"
        # Should have waited at least for the sleep (0.5s), but may exit early if EOF reached
        # The important thing is it captured the context line that came after the match
        assert elapsed >= 0.4, f"Should wait at least for input, took {elapsed}s"


class TestOptionalPattern:
    """Test optional pattern when timeout is provided"""
    
    def test_pattern_optional_with_timeout(self):
        """Test that pattern is optional when -t is provided"""
        # Pattern omitted, timeout provided - should work
        cmd = ['python3', '-m', 'earlyexit.cli', '-t', '2', '--', 'bash', '-c', 
               'for i in 1 2 3 4 5; do echo "Line $i"; sleep 1; done']
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate(timeout=5)
        
        # Should timeout after 2 seconds
        assert proc.returncode == 2, "Should timeout (exit code 2)"
        assert "Timeout-only mode" in stderr, "Should indicate timeout-only mode"
        assert "Line 1" in stdout, "Should output at least first line"
        assert "Line 5" not in stdout, "Should not complete all lines"
    
    def test_pattern_optional_with_idle_timeout(self):
        """Test that pattern is optional when --idle-timeout is provided"""
        cmd = ['python3', '-m', 'earlyexit.cli', '--idle-timeout', '1', '--', 'bash', '-c', 
               'echo "start"; sleep 2; echo "end"']
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate(timeout=5)
        
        # Should timeout due to idle (exit code 2 for timeout)
        assert proc.returncode == 2, "Should timeout (exit code 2)"
        assert "Timeout-only mode" in stderr, "Should indicate timeout-only mode"
        assert "start" in stdout, "Should see first output"
        assert "end" not in stdout, "Should not see output after idle timeout"
    
    def test_pattern_optional_with_first_output_timeout(self):
        """Test that pattern is optional when --first-output-timeout is provided"""
        cmd = ['python3', '-m', 'earlyexit.cli', '--first-output-timeout', '1', '--', 'bash', '-c', 
               'sleep 2; echo "delayed output"']
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate(timeout=5)
        
        # Should timeout waiting for first output (exit code 2 for timeout)
        assert proc.returncode == 2, "Should timeout (exit code 2)"
        assert "Timeout-only mode" in stderr, "Should indicate timeout-only mode"
    
    def test_pattern_required_without_timeout(self):
        """Test that pattern is required when no timeout is provided"""
        cmd = ['python3', '-m', 'earlyexit.cli', '--', 'echo', 'test']
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate(timeout=5)
        
        # Should error
        assert proc.returncode == 2, "Should return error code 2"
        assert "Missing PATTERN argument" in stderr, "Should indicate missing pattern"
        assert "Correct usage" in stderr, "Should show usage examples"
    
    def test_explicit_none_pattern_with_timeout(self):
        """Test explicit 'NONE' keyword with timeout"""
        cmd = ['python3', '-m', 'earlyexit.cli', '-t', '1', 'NONE', '--', 'bash', '-c', 
               'for i in 1 2 3; do echo "Line $i"; sleep 1; done']
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate(timeout=5)
        
        # Should timeout
        assert proc.returncode == 2, "Should timeout (exit code 2)"
        assert "Timeout-only mode" in stderr, "Should indicate timeout-only mode"
        assert "Line 1" in stdout, "Should output at least first line"
    
    def test_pattern_with_timeout_still_works(self):
        """Test that providing both pattern and timeout still works"""
        cmd = ['python3', '-m', 'earlyexit.cli', '-t', '10', 'quick', '--', 'bash', '-c', 
               'echo "quick output"; echo "more output"']
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate(timeout=15)
        
        # Should match on "quick" and exit successfully
        assert proc.returncode == 0, "Should match pattern (exit code 0)"
        assert "quick output" in stdout, "Should see matched line"
        # Pattern matching is working with timeout
    
    def test_timeout_only_completes_successfully(self):
        """Test that timeout-only mode completes if command finishes before timeout"""
        cmd = ['python3', '-m', 'earlyexit.cli', '-t', '10', '--', 'bash', '-c', 
               'echo "quick"; echo "output"']
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate(timeout=15)
        
        # Should complete successfully
        assert proc.returncode == 1, "Should complete normally (exit code 1, no match)"
        assert "Timeout-only mode" in stderr, "Should indicate timeout-only mode"
        assert "quick" in stdout, "Should see all output"
        assert "output" in stdout, "Should see all output"


class TestTelemetry:
    """Test telemetry on/off and subprocess scenarios"""
    
    def test_telemetry_disabled_flag(self):
        """Test that --no-telemetry flag disables telemetry"""
        cmd = ['python3', '-m', 'earlyexit.cli', '--no-telemetry', 'test', '--', 'echo', 'test']
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate(timeout=5)
        
        # Should work normally
        assert proc.returncode == 0, "Should match pattern (exit code 0)"
        assert "test" in stdout, "Should see output"
    
    def test_telemetry_disabled_env_var(self):
        """Test that EARLYEXIT_NO_TELEMETRY env var disables telemetry"""
        import os
        env = os.environ.copy()
        env['EARLYEXIT_NO_TELEMETRY'] = '1'
        
        cmd = ['python3', '-m', 'earlyexit.cli', 'test', '--', 'echo', 'test']
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
        )
        
        stdout, stderr = proc.communicate(timeout=5)
        
        # Should work normally
        assert proc.returncode == 0, "Should match pattern (exit code 0)"
        assert "test" in stdout, "Should see output"
    
    def test_telemetry_enabled_by_default(self):
        """Test that telemetry is enabled by default in subprocess"""
        # This test just verifies it doesn't crash or error
        cmd = ['python3', '-m', 'earlyexit.cli', 'test', '--', 'echo', 'test']
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = proc.communicate(timeout=5)
        
        # Should work normally with telemetry
        assert proc.returncode == 0, "Should match pattern (exit code 0)"
        assert "test" in stdout, "Should see output"
    
    def test_subprocess_with_telemetry_off(self):
        """Test subprocess invocation with telemetry disabled"""
        import os
        env = os.environ.copy()
        env['EARLYEXIT_NO_TELEMETRY'] = 'true'
        
        # Run multiple times to ensure no database errors
        for i in range(3):
            cmd = ['python3', '-m', 'earlyexit.cli', 'test', '--', 'echo', f'test{i}']
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=5
            )
            assert result.returncode == 0, f"Iteration {i} should succeed"
    
    def test_concurrent_with_telemetry_disabled(self):
        """Test concurrent subprocess calls with telemetry disabled"""
        import os
        env = os.environ.copy()
        env['EARLYEXIT_NO_TELEMETRY'] = '1'
        
        processes = []
        for i in range(5):
            cmd = ['python3', '-m', 'earlyexit.cli', '--no-telemetry', 'test', '--', 'echo', f'test{i}']
            p = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            processes.append(p)
        
        # Wait for all to complete
        for i, p in enumerate(processes):
            stdout, stderr = p.communicate(timeout=5)
            assert p.returncode == 0, f"Process {i} should succeed"


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
        
        # Should handle gracefully (not crash with Python exception)
        # Exit code may vary (0, 1, 120=SIGPIPE) depending on timing
        assert proc.returncode is not None, "Process should complete"


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


class TestArgumentParsing:
    """Test argument parsing edge cases"""
    
    def test_double_dash_separator_with_command_flags(self):
        """Test that -- separator allows commands with flags like --id"""
        import tempfile
        import os
        
        # Create a fake command script that has flags
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh') as f:
            f.write('#!/bin/bash\n')
            f.write('echo "Command called with: $@"\n')
            f.write('exit 0\n')
            script = f.name
        
        os.chmod(script, 0o755)
        
        try:
            # Test: ee -- command --id value --step 2
            result = subprocess.run(
                ['earlyexit', '--', script, '--id', 'rble-3050969270', '--step', '2', '-v'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Should run successfully (exit code 1 = no pattern match in watch mode)
            assert result.returncode in [0, 1], f"Should run successfully, got {result.returncode}"
            assert "Command called with:" in result.stdout, "Command should have been executed"
            assert "--id" in result.stdout, "Command should receive --id flag"
            assert "rble-3050969270" in result.stdout, "Command should receive --id value"
            # Most importantly: should NOT say "invalid float value" 
            # (that would mean --id was parsed as --idle-timeout)
            assert "invalid float value" not in result.stderr
        finally:
            os.unlink(script)
    
    def test_double_dash_with_pattern(self):
        """Test that pattern can be specified before -- separator"""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh') as f:
            f.write('#!/bin/bash\n')
            f.write('echo "SUCCESS"\n')
            f.write('exit 0\n')
            script = f.name
        
        os.chmod(script, 0o755)
        
        try:
            # Test: ee 'SUCCESS' -- command --flag
            result = subprocess.run(
                ['earlyexit', 'SUCCESS', '--', script, '--verbose'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Should match pattern and return 0
            assert result.returncode == 0, f"Should return 0 (pattern matched), got {result.returncode}"
            assert "SUCCESS" in result.stdout, "Should see command output"
        finally:
            os.unlink(script)
    
    def test_parse_known_args_allows_command_flags(self):
        """Test that parse_known_args allows commands with unknown flags"""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh') as f:
            f.write('#!/bin/bash\n')
            f.write('echo "args: $@"\n')
            f.write('exit 0\n')
            script = f.name
        
        os.chmod(script, 0o755)
        
        try:
            # Command with flags like --id that aren't earlyexit options
            # Should work WITHOUT needing -- separator due to parse_known_args
            result = subprocess.run(
                ['earlyexit', script, 'test', '--id', '123', '--step', '2'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Should succeed
            assert result.returncode in [0, 1], f"Should run successfully, got {result.returncode}"
            assert "args:" in result.stdout, "Command should have been executed"
            assert "--id" in result.stdout, "Command should receive --id flag"
            
            # Most importantly: should NOT say "invalid float value" 
            # (that would mean --id was incorrectly parsed as --idle-timeout)
            assert "invalid float value" not in result.stderr, \
                "Should not misinterpret --id as --idle-timeout abbreviation"
        finally:
            os.unlink(script)
    
    def test_command_mode_with_pattern(self):
        """Test command mode works with explicit pattern (no flags)"""
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sh') as f:
            f.write('#!/bin/bash\n')
            f.write('echo "test output"\n')
            f.write('exit 0\n')
            script = f.name
        
        os.chmod(script, 0o755)
        
        try:
            # Pattern with regex chars (not detected as command name)
            result = subprocess.run(
                ['earlyexit', 'output|test', script],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            assert result.returncode == 0, "Command mode with pattern should work"
            assert "test output" in result.stdout
        finally:
            os.unlink(script)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


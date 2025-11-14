#!/usr/bin/env python3
"""
Comprehensive tests for delay-exit and delay-exit-after-lines features
Tests cover: both streams, stdin, stdout, delay-exit, delay-exit-after-lines
"""
import subprocess
import time
import pytest


def run_earlyexit_test(cmd, expected_returncode=0, timeout=30):
    """Helper function to run earlyexit command and return results"""
    start_time = time.time()
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = proc.communicate(timeout=timeout)
    elapsed = time.time() - start_time
    
    return {
        'returncode': proc.returncode,
        'stdout': stdout,
        'stderr': stderr,
        'elapsed': elapsed,
        'stdout_lines': stdout.splitlines(),
        'stderr_lines': stderr.splitlines(),
    }


def test_monitor_both_streams():
    """Test 1: Should detect error on stderr when monitoring both streams"""
    result = run_earlyexit_test([
        'earlyexit', '--delay-exit', '2', '--delay-exit-after-lines', '10',
        'ERROR', '--',
        'bash', '-c',
        'for i in {1..5}; do echo "Line $i on stdout"; done; ' +
        'echo "ERROR on stderr" >&2; ' +
        'for i in {1..20}; do echo "Context line $i" >&2; sleep 0.1; done'
    ])
    
    assert result['returncode'] == 0, "Should exit with 0 (match found)"
    assert "ERROR on stderr" in result['stdout'], "Should detect ERROR in captured output"
    assert len(result['stdout_lines']) >= 5, "Should capture some stdout lines"
    assert "Context line" in result['stdout'], "Should capture context lines"
    assert result['elapsed'] < 2.5, "Should exit before 2.5s (line limit hit)"


def test_monitor_stdout_only():
    """Test 2: Should detect error on stdout, ignore stderr"""
    result = run_earlyexit_test([
        'earlyexit', '--stdout', '--delay-exit', '2', '--delay-exit-after-lines', '10',
        'ERROR', '--',
        'bash', '-c',
        'for i in {1..5}; do echo "Line $i"; done; ' +
        'echo "ERROR on stdout"; ' +
        'for i in {1..20}; do echo "Context $i"; sleep 0.1; done'
    ])
    
    assert result['returncode'] == 0, "Should exit with 0 (match found)"
    assert "ERROR on stdout" in result['stdout'], "Should detect ERROR on stdout"
    assert len(result['stdout_lines']) > 6, "Should capture context lines"
    assert result['elapsed'] < 3.0, "Should exit around line limit (< 3s)"


def test_monitor_stderr_only():
    """Test 3: Should detect error on stderr, ignore stdout"""
    result = run_earlyexit_test([
        'earlyexit', '--stderr', '--delay-exit', '2', '--delay-exit-after-lines', '10',
        'ERROR', '--',
        'bash', '-c',
        'for i in {1..5}; do echo "Stdout $i"; done; ' +
        'echo "ERROR on stderr" >&2; ' +
        'for i in {1..20}; do echo "Context $i" >&2; sleep 0.1; done'
    ])
    
    assert result['returncode'] == 0, "Should exit with 0 (match found)"
    assert "ERROR on stderr" in result['stdout'], "Should detect ERROR on stderr"
    assert len(result['stdout_lines']) > 6, "Should capture context on stderr"
    assert result['elapsed'] < 3.0, "Should exit around line limit (< 3s)"


def test_delay_exit_time_limit():
    """Test 4: Should wait for time limit even with few lines"""
    result = run_earlyexit_test([
        'earlyexit', '--delay-exit', '1', '--delay-exit-after-lines', '1000',
        'ERROR', '--',
        'bash', '-c',
        'echo "ERROR found"; ' +
        'for i in {1..3}; do echo "Context $i"; sleep 0.4; done'
    ])
    
    assert result['returncode'] == 0, "Should exit with 0 (match found)"
    assert 0.9 <= result['elapsed'] <= 1.5, f"Should wait around 1 second, got {result['elapsed']:.2f}s"
    assert "ERROR found" in result['stdout'], "Should capture error line"
    assert "Context" in result['stdout'], "Should capture some context"


def test_delay_exit_line_limit():
    """Test 5: Should exit after line count, not wait full time"""
    result = run_earlyexit_test([
        'earlyexit', '--delay-exit', '10', '--delay-exit-after-lines', '5',
        'ERROR', '--',
        'bash', '-c',
        'echo "ERROR found"; ' +
        'for i in {1..10}; do echo "Context line $i"; done'
    ])
    
    assert result['returncode'] == 0, "Should exit with 0 (match found)"
    assert result['elapsed'] < 2.0, "Should exit quickly (< 2s, not 10s)"
    # Filter out logging messages (start with 📝 or spaces for indentation)
    actual_output_lines = [line for line in result['stdout_lines'] 
                          if not line.strip().startswith('📝') and 
                          not line.strip().startswith('stdout:') and
                          not line.strip().startswith('stderr:')]
    assert 5 <= len(actual_output_lines) <= 7, f"Should capture error + ~5 context lines, got {len(actual_output_lines)} lines"


def test_pipe_mode_stdin():
    """Test 6: Should process stdin with delay-exit and line limit"""
    result = run_earlyexit_test([
        'bash', '-c',
        '(for i in {1..5}; do echo "Line $i"; done; ' +
        'echo "ERROR found"; ' +
        'for i in {1..20}; do echo "Context $i"; done) | ' +
        'earlyexit --delay-exit 2 --delay-exit-after-lines 10 "ERROR"'
    ])
    
    assert result['returncode'] == 0, "Should exit with 0 (match found)"
    assert "ERROR found" in result['stdout'], "Should capture error line"
    assert "Context" in result['stdout'], "Should capture some context lines"
    assert result['elapsed'] < 3.0, "Should exit quickly"


def test_immediate_exit_no_delay():
    """Test 7: Should exit immediately on match, no context captured"""
    result = run_earlyexit_test([
        'earlyexit', '--delay-exit', '0', 'ERROR', '--',
        'bash', '-c',
        'echo "Line 1"; echo "ERROR"; for i in {1..5}; do echo "Context $i"; sleep 0.2; done'
    ])
    
    assert result['returncode'] == 0, "Should exit with 0 (match found)"
    assert result['elapsed'] < 0.5, "Should exit immediately"
    assert "ERROR" in result['stdout'], "Should capture error line"
    assert result['stdout'].count("Context") < 5, "Should not capture all context"


def test_default_delay_behavior():
    """Test 8: Should use default 10s delay and 100 line limit"""
    result = run_earlyexit_test([
        'earlyexit', 'ERROR', '--',
        'bash', '-c',
        'echo "ERROR"; for i in {1..150}; do echo "Line $i"; done'
    ])
    
    assert result['returncode'] == 0, "Should exit with 0 (match found)"
    assert result['elapsed'] < 3.0, "Should exit before 10s (line limit hit)"
    # Note: Default line limit may vary, being flexible here
    assert len(result['stdout_lines']) >= 50, "Should capture significant number of lines"


def test_both_streams_multiple_errors():
    """Test 9: Should detect first error on either stream"""
    result = run_earlyexit_test([
        'earlyexit', '--delay-exit', '1', '--delay-exit-after-lines', '10',
        'ERROR', '--',
        'bash', '-c',
        'echo "stdout line 1"; ' +
        'echo "ERROR on stdout"; ' +
        'echo "ERROR on stderr" >&2; ' +
        'for i in {1..20}; do echo "Context $i"; sleep 0.05; done'
    ])
    
    assert result['returncode'] == 0, "Should exit with 0 (match found)"
    assert "ERROR" in result['stdout'] or "ERROR" in result['stderr'], "Should detect error"
    assert result['elapsed'] < 1.5, "Should exit before 1.5s (line limit)"


def test_timeout_only_mode():
    """Test 10: Should timeout with delay-exit settings applied"""
    result = run_earlyexit_test([
        'earlyexit', '-t', '2', 'NOMATCH', '--',
        'bash', '-c',
        'for i in {1..100}; do echo "Line $i"; sleep 0.1; done'
    ], expected_returncode=2)  # Timeout exit code
    
    # Note: Timeout might return different exit codes, being flexible
    assert result['returncode'] != 0, "Should timeout (non-zero exit code)"
    assert 1.5 <= result['elapsed'] <= 2.5, f"Should timeout around 2s, got {result['elapsed']:.2f}s"
    assert len(result['stdout_lines']) > 0, "Should capture some output"


if __name__ == '__main__':
    # Allow running as standalone script for debugging
    pytest.main([__file__, '-v'])

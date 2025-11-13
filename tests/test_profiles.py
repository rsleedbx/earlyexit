#!/usr/bin/env python3
"""
Test profile system for earlyexit

Validates that built-in profiles work correctly
"""

import pytest
import subprocess
import sys
from pathlib import Path


def run_earlyexit_with_profile(profile_name, command, timeout=10):
    """
    Run earlyexit with a profile
    
    Returns:
        (exit_code, stdout, stderr)
    """
    cmd = [
        sys.executable, '-m', 'earlyexit.cli',
        '--profile', profile_name,
        '--'
    ] + command
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 2, '', 'Timeout'


def test_list_profiles():
    """Test that --list-profiles works"""
    cmd = [sys.executable, '-m', 'earlyexit.cli', '--list-profiles']
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    assert result.returncode == 0
    assert 'npm' in result.stderr
    assert 'pytest' in result.stderr
    assert 'cargo' in result.stderr
    assert 'terraform' in result.stderr


def test_show_profile():
    """Test that --show-profile works"""
    cmd = [sys.executable, '-m', 'earlyexit.cli', '--show-profile', 'npm']
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    assert result.returncode == 0
    assert 'npm' in result.stderr
    assert 'Pattern:' in result.stderr
    assert 'npm ERR!' in result.stderr
    assert 'F1 Score:' in result.stderr


def test_profile_applies_pattern():
    """Test that profile pattern is applied"""
    # Use echo to output pattern that matches profile
    exit_code, stdout, stderr = run_earlyexit_with_profile(
        'pytest',
        ['echo', 'Test FAILED at line 123']
    )
    
    # Should match and exit with code 0
    assert exit_code == 0
    assert 'Using profile: pytest' in stderr


def test_profile_catches_npm_error():
    """Test npm profile catches npm errors"""
    exit_code, stdout, stderr = run_earlyexit_with_profile(
        'npm',
        ['sh', '-c', 'echo "npm ERR! code ELIFECYCLE"; echo "npm ERR! errno 1"']
    )
    
    # Should match npm ERR!
    assert exit_code == 0
    assert 'Using profile: npm' in stderr


def test_profile_catches_pytest_error():
    """Test pytest profile catches pytest errors"""
    exit_code, stdout, stderr = run_earlyexit_with_profile(
        'pytest',
        ['sh', '-c', 'echo "test_auth.py::test_login FAILED"']
    )
    
    # Should match FAILED
    assert exit_code == 0


def test_profile_catches_cargo_error():
    """Test cargo profile catches cargo errors"""
    exit_code, stdout, stderr = run_earlyexit_with_profile(
        'cargo',
        ['sh', '-c', 'echo "error: could not compile"; echo "  --> src/main.rs:10:5"']
    )
    
    # Should match error:
    assert exit_code == 0


def test_profile_no_match():
    """Test profile doesn't match on success output"""
    exit_code, stdout, stderr = run_earlyexit_with_profile(
        'pytest',
        ['sh', '-c', 'echo "test_auth.py::test_login PASSED"; sleep 0.1']
    )
    
    # Should not match, exit code 1 (no match)
    assert exit_code == 1


def test_profile_override_delay():
    """Test that profile settings can be overridden"""
    cmd = [
        sys.executable, '-m', 'earlyexit.cli',
        '--profile', 'npm',
        '--delay-exit', '2',
        '--',
        'sh', '-c', 'echo "npm ERR! test"'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Should use profile but with custom delay
    assert result.returncode == 0


def test_generic_profile():
    """Test generic profile catches common errors"""
    exit_code, stdout, stderr = run_earlyexit_with_profile(
        'generic',
        ['sh', '-c', 'echo "Build failed with error code 1"']
    )
    
    # Should match "failed" and "error" (case-insensitive)
    assert exit_code == 0


def test_invalid_profile():
    """Test that invalid profile name fails gracefully"""
    cmd = [
        sys.executable, '-m', 'earlyexit.cli',
        '--profile', 'nonexistent-profile',
        '--',
        'echo', 'test'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Should exit with error code 3
    assert result.returncode == 3
    assert 'not found' in result.stderr


def test_profile_delay_exit_captures_context():
    """Test that profile delay-exit captures multiple lines"""
    # Simulate an error with multi-line output
    cmd = [
        sys.executable, '-m', 'earlyexit.cli',
        '--profile', 'pytest',
        '--',
        'sh', '-c',
        'echo "FAILED test_auth.py"; '
        'sleep 0.2; '
        'echo "  AssertionError: expected True"; '
        'sleep 0.2; '
        'echo "  at line 42"; '
        'sleep 0.2; '
        'echo "  in test_login"'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    
    # Should have captured context after match
    assert result.returncode == 0
    assert 'FAILED' in result.stdout
    assert 'AssertionError' in result.stdout or 'line 42' in result.stdout


def test_profile_with_watch_mode_protection():
    """Test that profiles work even with watch mode detection"""
    # Command that looks like watch mode but has --profile
    cmd = [
        sys.executable, '-m', 'earlyexit.cli',
        '--profile', 'npm',
        'echo', 'npm ERR! test'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Should use profile, not enter watch mode
    assert result.returncode == 0
    assert 'Using profile: npm' in result.stderr


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


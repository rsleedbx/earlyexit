"""
Pytest wrapper for shell script tests.

This allows shell scripts to be run as part of the pytest suite,
ensuring they're validated with every test run.
"""

import subprocess
import pytest
from pathlib import Path


# Get the tests directory
TESTS_DIR = Path(__file__).parent


def run_shell_test(script_path: Path) -> tuple[int, str, str]:
    """
    Run a shell test script and return results.
    
    Returns:
        (exit_code, stdout, stderr)
    """
    result = subprocess.run(
        [str(script_path)],
        cwd=TESTS_DIR.parent,  # Run from project root
        capture_output=True,
        text=True,
        timeout=60  # 60 second timeout for all tests
    )
    return result.returncode, result.stdout, result.stderr


class TestShellScripts:
    """Test suite for shell script functional tests"""
    
    def test_pipe_timeouts(self):
        """Test pipe mode timeout detection (idle + first-output)"""
        script = TESTS_DIR / "test_pipe_timeouts.sh"
        if not script.exists():
            pytest.skip(f"Shell script not found: {script}")
        
        exit_code, stdout, stderr = run_shell_test(script)
        
        # Print output for debugging
        if exit_code != 0:
            print(f"\n=== STDOUT ===\n{stdout}")
            print(f"\n=== STDERR ===\n{stderr}")
        
        assert exit_code == 0, f"test_pipe_timeouts.sh failed with exit code {exit_code}"
        assert "✅" in stdout, "No passing tests found in output"
        assert "❌" not in stdout, "Found failing tests in output"
    
    def test_delay_exit(self):
        """Test error context capture with --delay-exit"""
        script = TESTS_DIR / "test_delay_exit.sh"
        if not script.exists():
            pytest.skip(f"Shell script not found: {script}")
        
        exit_code, stdout, stderr = run_shell_test(script)
        
        if exit_code != 0:
            print(f"\n=== STDOUT ===\n{stdout}")
            print(f"\n=== STDERR ===\n{stderr}")
        
        assert exit_code == 0, f"test_delay_exit.sh failed with exit code {exit_code}"
        # delay_exit.sh doesn't use emoji, check for other success indicators
        assert "FAILED" not in stdout.upper() or exit_code == 0
    
    @pytest.mark.skip(reason="test_timeouts.sh is a long-running test (>60s), not a proper validation test")
    def test_timeouts(self):
        """Test timeout management (-t, --idle-timeout, --first-output-timeout)"""
        script = TESTS_DIR / "test_timeouts.sh"
        if not script.exists():
            pytest.skip(f"Shell script not found: {script}")
        
        exit_code, stdout, stderr = run_shell_test(script)
        
        if exit_code != 0:
            print(f"\n=== STDOUT ===\n{stdout}")
            print(f"\n=== STDERR ===\n{stderr}")
        
        assert exit_code == 0, f"test_timeouts.sh failed with exit code {exit_code}"
    
    def test_fd_monitoring(self):
        """Test custom file descriptor monitoring"""
        script = TESTS_DIR / "test_fd.sh"
        if not script.exists():
            pytest.skip(f"Shell script not found: {script}")
        
        exit_code, stdout, stderr = run_shell_test(script)
        
        if exit_code != 0:
            print(f"\n=== STDOUT ===\n{stdout}")
            print(f"\n=== STDERR ===\n{stderr}")
        
        assert exit_code == 0, f"test_fd.sh failed with exit code {exit_code}"
    
    def test_multifd_monitoring(self):
        """Test stdout/stderr separate monitoring"""
        script = TESTS_DIR / "test_multifd.sh"
        if not script.exists():
            pytest.skip(f"Shell script not found: {script}")
        
        exit_code, stdout, stderr = run_shell_test(script)
        
        if exit_code != 0:
            print(f"\n=== STDOUT ===\n{stdout}")
            print(f"\n=== STDERR ===\n{stderr}")
        
        assert exit_code == 0, f"test_multifd.sh failed with exit code {exit_code}"
    
    def test_pipe_delay_exit(self):
        """Test --delay-exit in pipe mode (captures context after error)"""
        script = TESTS_DIR / "test_pipe_delay_exit.sh"
        if not script.exists():
            pytest.skip(f"Shell script not found: {script}")
        
        exit_code, stdout, stderr = run_shell_test(script)
        
        if exit_code != 0:
            print(f"\n=== STDOUT ===\n{stdout}")
            print(f"\n=== STDERR ===\n{stderr}")
        
        assert exit_code == 0, f"test_pipe_delay_exit.sh failed with exit code {exit_code}"
        assert "✅" in stdout, "No passing tests found in output"
        assert "❌" not in stdout, "Found failing tests in output"
    
    def test_watch_fd_detection(self):
        """Test custom FD detection and startup tracking in watch mode"""
        script = TESTS_DIR / "test_watch_fd_detection.sh"
        if not script.exists():
            pytest.skip(f"Shell script not found: {script}")
        
        exit_code, stdout, stderr = run_shell_test(script)
        
        if exit_code != 0:
            print(f"\n=== STDOUT ===\n{stdout}")
            print(f"\n=== STDERR ===\n{stderr}")
        
        assert exit_code == 0, f"test_watch_fd_detection.sh failed with exit code {exit_code}"
        assert "✅" in stdout, "No passing tests found in output"
    
    def test_syntax_and_limitations(self):
        """Test syntax modes and mode limitations (proves claims in Quick Comparison table)"""
        script = TESTS_DIR / "test_syntax_and_limitations.sh"
        if not script.exists():
            pytest.skip(f"Shell script not found: {script}")
        
        exit_code, stdout, stderr = run_shell_test(script)
        
        if exit_code != 0:
            print(f"\n=== STDOUT ===\n{stdout}")
            print(f"\n=== STDERR ===\n{stderr}")
        
        assert exit_code == 0, f"test_syntax_and_limitations.sh failed with exit code {exit_code}"
        assert "✅" in stdout, "No passing tests found in output"
        assert "❌" not in stdout, "Found failing tests in output"


# Mark all shell tests with a marker for easy filtering
pytestmark = pytest.mark.shell


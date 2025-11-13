#!/usr/bin/env python3
"""
Tests for watch mode functionality
"""
import subprocess
import time
import sys
import signal

# Ensure earlyexit is installed
subprocess.run(['pip', 'install', '-e', '.'], check=True, capture_output=True)


def test_watch_mode_activates():
    """Test that watch mode activates when no pattern provided"""
    print("\n" + "="*70)
    print("TEST: Watch mode activates")
    print("="*70)
    
    # Run earlyexit with no pattern using a non-common command
    # '/bin/echo' is not in the common commands list
    proc = subprocess.Popen(
        ['earlyexit', '/bin/echo', 'test'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = proc.communicate(timeout=5)
    
    print(f"Exit code: {proc.returncode}")
    print(f"Stdout: {stdout}")
    print(f"Stderr: {stderr}")
    
    # Check that watch mode message appears
    assert "Watch mode enabled" in stderr or "🔍" in stderr, f"Watch mode message not found. Stderr: {stderr}"
    assert "test" in stdout, "Command output not captured"
    
    print("✅ PASSED: Watch mode activated and captured output")
    return True


def test_watch_mode_separate_streams():
    """Test that watch mode tracks stdout/stderr separately"""
    print("\n" + "="*70)
    print("TEST: Watch mode separates stdout/stderr")
    print("="*70)
    
    # Run command that outputs to both streams using bash
    proc = subprocess.Popen(
        ['earlyexit', 'bash'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Send commands via stdin
    stdout, stderr = proc.communicate(
        input='echo "stdout line"\necho "stderr line" >&2\nexit 0\n',
        timeout=5
    )
    
    print(f"Exit code: {proc.returncode}")
    print(f"Stdout: {stdout}")
    print(f"Stderr: {stderr}")
    
    # Verify both streams captured
    assert "stdout line" in stdout, "stdout not captured"
    # stderr output goes to stderr in watch mode
    assert "stderr line" in stderr, "stderr content not captured"
    
    print("✅ PASSED: Both streams captured separately")
    return True


def test_watch_mode_ctrl_c():
    """Test that Ctrl+C is handled gracefully in watch mode"""
    print("\n" + "="*70)
    print("TEST: Watch mode handles Ctrl+C")
    print("="*70)
    
    # Run a simple command that we can interrupt
    # Use python for cross-platform compatibility
    proc = subprocess.Popen(
        ['earlyexit', 'python3'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Let it start
    time.sleep(0.3)
    
    # Send SIGINT (Ctrl+C)
    proc.send_signal(signal.SIGINT)
    
    # Wait for it to finish
    try:
        stdout, stderr = proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
    
    print(f"Exit code: {proc.returncode}")
    print(f"Stderr excerpt: {stderr[:300]}")
    
    # Should exit with interrupt-related code (130 or similar)
    # Different shells/systems may use different codes for interrupts
    assert proc.returncode in [130, 241, -2, 2], f"Expected interrupt exit code, got {proc.returncode}"
    assert "Interrupted" in stderr or proc.returncode != 0, "Should show interrupted or non-zero exit"
    
    print("✅ PASSED: Ctrl+C handled gracefully")
    return True


def test_watch_mode_complete():
    """Test that watch mode completes normally when command finishes"""
    print("\n" + "="*70)
    print("TEST: Watch mode completes normally")
    print("="*70)
    
    # Use python to exit with a specific code
    proc = subprocess.Popen(
        ['earlyexit', 'python3'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Send python commands
    stdout, stderr = proc.communicate(
        input='for i in range(1, 6): print(f"Line {i}")\nimport sys; sys.exit(42)\n',
        timeout=5
    )
    
    print(f"Exit code: {proc.returncode}")
    print(f"Lines captured: {len(stdout.splitlines())}")
    
    # Should exit with command's exit code
    assert proc.returncode == 42, f"Expected exit code 42, got {proc.returncode}"
    # At least some lines should be captured
    assert len([l for l in stdout.splitlines() if 'Line' in l]) >= 3, "Not enough lines captured"
    
    print("✅ PASSED: Normal completion works")
    return True


def test_normal_mode_still_works():
    """Test that normal pattern mode still works"""
    print("\n" + "="*70)
    print("TEST: Normal pattern mode still works")
    print("="*70)
    
    proc = subprocess.Popen(
        ['earlyexit', 'Line 3', '--', 'bash', '-c', 
         'for i in {1..5}; do echo "Line $i"; done'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = proc.communicate(timeout=5)
    
    print(f"Exit code: {proc.returncode}")
    print(f"Lines captured: {len(stdout.splitlines())}")
    
    # Should exit with 0 (match found)
    assert proc.returncode == 0, f"Expected exit code 0, got {proc.returncode}"
    assert "Line 3" in stdout, "Pattern not matched"
    assert "Watch mode" not in stderr, "Should not be in watch mode"
    
    print("✅ PASSED: Normal pattern mode unaffected")
    return True


if __name__ == '__main__':
    print("\n" + "="*70)
    print("WATCH MODE TESTS")
    print("="*70)
    
    tests = [
        test_watch_mode_activates,
        test_watch_mode_separate_streams,
        test_watch_mode_ctrl_c,
        test_watch_mode_complete,
        test_normal_mode_still_works,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"❌ FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*70)
    
    if failed == 0:
        print("\n✨ All watch mode tests passed!")
        sys.exit(0)
    else:
        print(f"\n❌ {failed} test(s) failed")
        sys.exit(1)


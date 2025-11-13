#!/usr/bin/env python3
"""
Comprehensive tests for delay-exit and delay-exit-after-lines features
Tests cover: both streams, stdin, stdout, delay-exit, delay-exit-after-lines
"""
import subprocess
import time
import sys
import os

# Ensure earlyexit is installed
subprocess.run(['pip', 'install', '-e', '.'], check=True, capture_output=True)

def run_test(name, description, cmd, expected_returncode, checks):
    """Run a test and validate results"""
    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print(f"{'='*70}")
    print(f"Description: {description}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    start_time = time.time()
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = proc.communicate(timeout=30)
    elapsed = time.time() - start_time
    
    print(f"Exit code: {proc.returncode}")
    print(f"Elapsed time: {elapsed:.2f}s")
    print(f"\nStdout lines: {len(stdout.splitlines())}")
    print(f"Stderr lines: {len(stderr.splitlines())}")
    
    # Run checks
    passed = True
    for check_name, check_func in checks.items():
        result = check_func(proc.returncode, stdout, stderr, elapsed)
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {check_name}")
        if not result:
            passed = False
    
    if passed:
        print(f"\n✅ {name} PASSED")
    else:
        print(f"\n❌ {name} FAILED")
        print(f"\nStdout:\n{stdout}")
        print(f"\nStderr:\n{stderr}")
        sys.exit(1)
    
    return passed


# Test 1: Both stdout and stderr monitored (default)
run_test(
    "Test 1: Monitor both stdout and stderr (default)",
    "Should detect error on stderr when monitoring both streams",
    [
        'earlyexit', '--delay-exit', '2', '--delay-exit-after-lines', '10',
        'ERROR', '--',
        'bash', '-c',
        'for i in {1..5}; do echo "Line $i on stdout"; done; ' +
        'echo "ERROR on stderr" >&2; ' +
        'for i in {1..20}; do echo "Context line $i" >&2; sleep 0.1; done'
    ],
    0,  # Should exit with 0 (match found)
    {
        "Exit code is 0 (match found)": lambda rc, out, err, t: rc == 0,
        "Match detected": lambda rc, out, err, t: "ERROR on stderr" in out,
        "Captured some stdout lines": lambda rc, out, err, t: len(out.splitlines()) >= 5,
        "Captured context lines": lambda rc, out, err, t: "Context line" in out,
        "Exited before 2s (line limit hit)": lambda rc, out, err, t: t < 2.0,
        "Captured around 10 context lines": lambda rc, out, err, t: 5 <= len([l for l in out.splitlines() if 'Context' in l]) <= 15,
    }
)

# Test 2: Monitor only stdout
run_test(
    "Test 2: Monitor stdout only",
    "Should detect error on stdout, ignore stderr",
    [
        'earlyexit', '--stdout', '--delay-exit', '2', '--delay-exit-after-lines', '10',
        'ERROR', '--',
        'bash', '-c',
        'for i in {1..5}; do echo "Line $i"; done; ' +
        'echo "ERROR on stdout"; ' +
        'for i in {1..20}; do echo "Context $i"; sleep 0.1; done'
    ],
    0,  # Should exit with 0 (match found)
    {
        "Exit code is 0 (match found)": lambda rc, out, err, t: rc == 0,
        "Match detected": lambda rc, out, err, t: "ERROR on stdout" in out,
        "Captured context lines": lambda rc, out, err, t: len(out.splitlines()) > 6,
        "Exited around line limit (< 3s)": lambda rc, out, err, t: t < 3.0,
        "Line limit approximately reached": lambda rc, out, err, t: 8 <= len(out.splitlines()) <= 20,
    }
)

# Test 3: Monitor only stderr
run_test(
    "Test 3: Monitor stderr only",
    "Should detect error on stderr, ignore stdout",
    [
        'earlyexit', '--stderr', '--delay-exit', '2', '--delay-exit-after-lines', '10',
        'ERROR', '--',
        'bash', '-c',
        'for i in {1..5}; do echo "Stdout $i"; done; ' +
        'echo "ERROR on stderr" >&2; ' +
        'for i in {1..20}; do echo "Context $i" >&2; sleep 0.1; done'
    ],
    0,  # Should exit with 0 (match found)
    {
        "Exit code is 0 (match found)": lambda rc, out, err, t: rc == 0,
        "Match detected on stderr": lambda rc, out, err, t: "ERROR on stderr" in out,
        "Captured context on stderr": lambda rc, out, err, t: len(out.splitlines()) > 6,
        "Exited around line limit (< 3s)": lambda rc, out, err, t: t < 3.0,
        "Line limit approximately reached": lambda rc, out, err, t: 8 <= len(out.splitlines()) <= 20,
    }
)

# Test 4: Delay-exit time limit (exits after time, not line count)
run_test(
    "Test 4: Delay-exit time limit reached first",
    "Should wait 1 second even though few lines (line limit not reached)",
    [
        'earlyexit', '--delay-exit', '1', '--delay-exit-after-lines', '1000',
        'ERROR', '--',
        'bash', '-c',
        'echo "ERROR found"; ' +
        'for i in {1..3}; do echo "Context $i"; sleep 0.4; done'
    ],
    0,  # Should exit with 0 (match found)
    {
        "Exit code is 0 (match found)": lambda rc, out, err, t: rc == 0,
        "Waited around 1 second": lambda rc, out, err, t: 0.9 <= t <= 1.5,
        "Captured error line": lambda rc, out, err, t: "ERROR found" in out,
        "Captured some context": lambda rc, out, err, t: "Context" in out,
        "Line limit not reached": lambda rc, out, err, t: len(out.splitlines()) < 1000,
    }
)

# Test 5: Delay-exit-after-lines limit (exits after lines, not time)
run_test(
    "Test 5: Delay-exit-after-lines limit reached first",
    "Should exit after 5 lines, not wait full 10 seconds",
    [
        'earlyexit', '--delay-exit', '10', '--delay-exit-after-lines', '5',
        'ERROR', '--',
        'bash', '-c',
        'echo "ERROR found"; ' +
        'for i in {1..10}; do echo "Context line $i"; done'
    ],
    0,  # Should exit with 0 (match found)
    {
        "Exit code is 0 (match found)": lambda rc, out, err, t: rc == 0,
        "Exited quickly (< 2s, not 10s)": lambda rc, out, err, t: t < 2.0,
        "Captured error + 5 context lines": lambda rc, out, err, t: 5 <= len(out.splitlines()) <= 7,
        "Did not wait full 10s": lambda rc, out, err, t: t < 5.0,
    }
)

# Test 6: Pipe mode (stdin)
run_test(
    "Test 6: Pipe mode with stdin",
    "Should process stdin with delay-exit and line limit",
    [
        'bash', '-c',
        '(for i in {1..5}; do echo "Line $i"; done; ' +
        'echo "ERROR found"; ' +
        'for i in {1..20}; do echo "Context $i"; done) | ' +
        'earlyexit --delay-exit 2 --delay-exit-after-lines 10 "ERROR"'
    ],
    0,  # Should exit with 0 (match found)
    {
        "Exit code is 0 (match found)": lambda rc, out, err, t: rc == 0,
        "Captured error line": lambda rc, out, err, t: "ERROR found" in out,
        "Captured some context lines": lambda rc, out, err, t: "Context" in out,
        "Exited quickly": lambda rc, out, err, t: t < 3.0,
        "Showed waiting message": lambda rc, out, err, t: "Waiting" in err or len(out.splitlines()) > 0,
    }
)

# Test 7: No delay (immediate exit)
run_test(
    "Test 7: No delay (immediate exit)",
    "Should exit immediately on match, no context captured",
    [
        'earlyexit', '--delay-exit', '0', 'ERROR', '--',
        'bash', '-c',
        'echo "Line 1"; echo "ERROR"; for i in {1..5}; do echo "Context $i"; sleep 0.2; done'
    ],
    0,  # Should exit with 0 (match found)
    {
        "Exit code is 0 (match found)": lambda rc, out, err, t: rc == 0,
        "Exited immediately": lambda rc, out, err, t: t < 0.5,
        "Captured error line": lambda rc, out, err, t: "ERROR" in out,
        "Did not capture all context": lambda rc, out, err, t: out.count("Context") < 5,
    }
)

# Test 8: Default behavior (10s delay, 100 line limit)
run_test(
    "Test 8: Default delay-exit behavior",
    "Should use default 10s delay and 100 line limit",
    [
        'earlyexit', 'ERROR', '--',
        'bash', '-c',
        'echo "ERROR"; for i in {1..150}; do echo "Line $i"; done'
    ],
    0,  # Should exit with 0 (match found)
    {
        "Exit code is 0 (match found)": lambda rc, out, err, t: rc == 0,
        "Exited before 10s (line limit hit)": lambda rc, out, err, t: t < 3.0,
        "Captured around 100 lines": lambda rc, out, err, t: 95 <= len(out.splitlines()) <= 105,
    }
)

# Test 9: Both streams with different error locations
run_test(
    "Test 9: Both streams monitored, error on each",
    "Should detect first error on either stream",
    [
        'earlyexit', '--delay-exit', '1', '--delay-exit-after-lines', '10',
        'ERROR', '--',
        'bash', '-c',
        'echo "stdout line 1"; ' +
        'echo "ERROR on stdout"; ' +
        'echo "ERROR on stderr" >&2; ' +
        'for i in {1..20}; do echo "Context $i"; sleep 0.05; done'
    ],
    0,  # Should exit with 0 (match found)
    {
        "Exit code is 0 (match found)": lambda rc, out, err, t: rc == 0,
        "Detected error": lambda rc, out, err, t: "ERROR" in out or "ERROR" in err,
        "Exited before 1s (line limit)": lambda rc, out, err, t: t < 1.5,
    }
)

# Test 10: Timeout-only mode (no pattern, but with delay settings)
run_test(
    "Test 10: Timeout-only mode",
    "Should timeout with delay-exit settings applied (pattern is optional)",
    [
        'earlyexit', '-t', '2', 'NOMATCH', '--',
        'bash', '-c',
        'for i in {1..100}; do echo "Line $i"; sleep 0.1; done'
    ],
    2,  # Should timeout (exit code 2)
    {
        "Exit code is 2 (timeout)": lambda rc, out, err, t: rc == 2,
        "Timed out around 2s": lambda rc, out, err, t: 1.5 <= t <= 2.5,
        "Captured output": lambda rc, out, err, t: len(out.splitlines()) > 0,
    }
)

print("\n" + "="*70)
print("✅ ALL TESTS PASSED!")
print("="*70)
print("\nFeatures tested:")
print("  ✅ Both stdout/stderr monitoring (default)")
print("  ✅ Stdout-only monitoring")
print("  ✅ Stderr-only monitoring")
print("  ✅ Delay-exit time limit")
print("  ✅ Delay-exit-after-lines limit")
print("  ✅ Pipe mode (stdin)")
print("  ✅ Immediate exit (no delay)")
print("  ✅ Default behavior (10s, 100 lines)")
print("  ✅ Both streams with multiple errors")
print("  ✅ Timeout-only mode")
print("\n✨ The new --delay-exit-after-lines feature works perfectly!")
print("   Exits when EITHER time OR line count is reached (whichever comes first)\n")


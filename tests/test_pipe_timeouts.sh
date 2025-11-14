#!/bin/bash
#
# Test script to verify --idle-timeout and --first-output-timeout work in pipe mode

set -e

echo "Testing pipe mode timeout features..."
echo ""

# Test 1: First output timeout
echo "=== Test 1: First output timeout ==="
echo "Command: sleep 5 | ee --first-output-timeout 2 'test'"
echo "Expected: Timeout after 2 seconds (sleep produces no output)"
EXIT_CODE=0
(sleep 5 | earlyexit --first-output-timeout 2 'test' 2>&1) || EXIT_CODE=$?
if [ "${EXIT_CODE:-0}" -eq 2 ]; then
    echo "✅ Test 1 PASSED: Got exit code 2 (timeout)"
else
    echo "❌ Test 1 FAILED: Got exit code ${EXIT_CODE:-0}, expected 2"
fi
echo ""

# Test 2: First output timeout SUCCESS (output arrives in time)
echo "=== Test 2: First output arrives in time ==="
echo "Command: (echo 'line1'; sleep 5) | ee --first-output-timeout 3 'test'"
echo "Expected: No timeout (first output arrives immediately)"
EXIT_CODE=0
(bash -c 'echo "line1"; sleep 1' | earlyexit --first-output-timeout 3 'test' 2>&1) || EXIT_CODE=$?
if [ "${EXIT_CODE:-0}" -eq 1 ]; then
    echo "✅ Test 2 PASSED: Got exit code 1 (no match, but no timeout)"
else
    echo "❌ Test 2 FAILED: Got exit code ${EXIT_CODE:-0}, expected 1"
fi
echo ""

# Test 3: Idle timeout
echo "=== Test 3: Idle timeout ==="
echo "Command: (echo 'line1'; sleep 5) | ee --idle-timeout 2 'test'"
echo "Expected: Timeout after 2 seconds of no output"
EXIT_CODE=0
(bash -c 'echo "line1"; sleep 5' | earlyexit --idle-timeout 2 'test' 2>&1) || EXIT_CODE=$?
if [ "${EXIT_CODE:-0}" -eq 2 ]; then
    echo "✅ Test 3 PASSED: Got exit code 2 (timeout)"
else
    echo "❌ Test 3 FAILED: Got exit code ${EXIT_CODE:-0}, expected 2"
fi
echo ""

# Test 4: Idle timeout with continuous output
echo "=== Test 4: Continuous output (no idle timeout) ==="
echo "Command: (for i in 1 2 3; do echo line$i; sleep 0.5; done) | ee --idle-timeout 2 'test'"
echo "Expected: No timeout (output every 0.5s, idle timeout is 2s)"
EXIT_CODE=0
(bash -c 'for i in 1 2 3; do echo "line$i"; sleep 0.5; done' | earlyexit --idle-timeout 2 'test' 2>&1) || EXIT_CODE=$?
if [ "${EXIT_CODE:-0}" -eq 1 ]; then
    echo "✅ Test 4 PASSED: Got exit code 1 (no match, no timeout)"
else
    echo "❌ Test 4 FAILED: Got exit code ${EXIT_CODE:-0}, expected 1"
fi
echo ""

# Test 5: Pattern match before timeout
echo "=== Test 5: Pattern match before timeout ==="
echo "Command: echo 'ERROR found' | ee --idle-timeout 2 'ERROR'"
echo "Expected: Exit code 0 (pattern matched, no idle timeout)"
EXIT_CODE=0
(bash -c 'echo "ERROR found"' | earlyexit --idle-timeout 2 'ERROR' 2>&1) || EXIT_CODE=$?
if [ "${EXIT_CODE:-0}" -eq 0 ]; then
    echo "✅ Test 5 PASSED: Got exit code 0 (pattern matched before timeout)"
else
    echo "❌ Test 5 FAILED: Got exit code ${EXIT_CODE:-0}, expected 0"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "All tests completed!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


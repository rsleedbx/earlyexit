#!/bin/bash
# Test --delay-exit in pipe mode
# Verifies that earlyexit continues reading after a match for the specified delay period

set -e

echo "=== Testing --delay-exit in Pipe Mode ==="

EXIT_CODE=0

# Test 1: Verify delay-exit captures additional context after error
echo ""
echo "Test 1: Capture 2 seconds of context after error"
OUTPUT=$(cat <<'EOF' | ee --delay-exit 2 'ERROR' 2>&1
Line 1: Starting...
Line 2: Running...
Line 3: ERROR detected here
Line 4: Context line 1 (should be captured)
Line 5: Context line 2 (should be captured)
EOF
) || EXIT_CODE=$?

if echo "$OUTPUT" | grep -q "Line 3: ERROR detected here" && \
   echo "$OUTPUT" | grep -q "Line 4: Context line 1" && \
   echo "$OUTPUT" | grep -q "Line 5: Context line 2"; then
    echo "✅ PASSED: Captured context after error"
else
    echo "❌ FAILED: Did not capture expected context lines"
    echo "Output: $OUTPUT"
    exit 1
fi

# Test 2: Verify delay-exit works with streaming input
echo ""
echo "Test 2: Delay-exit with time-based input"
OUTPUT=$({
    echo "Start"
    echo "ERROR here"
    sleep 0.5
    echo "Context 1"
    sleep 0.5
    echo "Context 2"
    sleep 0.5
    echo "Context 3"
} | ee --delay-exit 1.2 'ERROR' 2>&1) || EXIT_CODE=$?

if echo "$OUTPUT" | grep -q "ERROR here" && \
   echo "$OUTPUT" | grep -q "Context 1" && \
   echo "$OUTPUT" | grep -q "Context 2"; then
    echo "✅ PASSED: Captured time-based context"
else
    echo "❌ FAILED: Did not capture time-based context"
    echo "Output: $OUTPUT"
    exit 1
fi

# Test 3: Verify delay-exit=0 exits immediately (backward compatible)
echo ""
echo "Test 3: delay-exit=0 exits immediately"
OUTPUT=$({
    echo "Normal line"
    echo "ERROR line"
    echo "This should not appear"
} | ee --delay-exit 0 'ERROR' 2>&1) || EXIT_CODE=$?

if echo "$OUTPUT" | grep -q "ERROR line" && \
   ! echo "$OUTPUT" | grep -q "This should not appear"; then
    echo "✅ PASSED: delay-exit=0 exits immediately"
else
    echo "❌ FAILED: delay-exit=0 did not exit immediately"
    echo "Output: $OUTPUT"
    exit 1
fi

# Test 4: Verify default behavior (no delay) when --delay-exit not specified
echo ""
echo "Test 4: Default behavior (no --delay-exit)"
OUTPUT=$({
    echo "Normal line"
    echo "ERROR line"
    echo "This should not appear"
} | ee 'ERROR' 2>&1) || EXIT_CODE=$?

if echo "$OUTPUT" | grep -q "ERROR line" && \
   ! echo "$OUTPUT" | grep -q "This should not appear"; then
    echo "✅ PASSED: Default behavior exits immediately on match"
else
    echo "❌ FAILED: Default behavior incorrect"
    echo "Output: $OUTPUT"
    exit 1
fi

# Test 5: Verify --delay-exit-after-lines works in pipe mode
echo ""
echo "Test 5: --delay-exit-after-lines captures N lines after match"
OUTPUT=$({
    echo "Line 1"
    echo "ERROR here"
    echo "Context 1"
    echo "Context 2"
    echo "Context 3"
    echo "Context 4"
    echo "Context 5"
    echo "Context 6"
} | ee --delay-exit 10 --delay-exit-after-lines 3 'ERROR' 2>&1) || EXIT_CODE=$?

if echo "$OUTPUT" | grep -q "ERROR here" && \
   echo "$OUTPUT" | grep -q "Context 1" && \
   echo "$OUTPUT" | grep -q "Context 2" && \
   echo "$OUTPUT" | grep -q "Context 3"; then
    echo "✅ PASSED: Captured correct number of lines after match"
else
    echo "❌ FAILED: Did not capture expected number of lines"
    echo "Output: $OUTPUT"
    exit 1
fi

echo ""
echo "=== All Pipe Mode --delay-exit Tests Passed ==="
exit 0





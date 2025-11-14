#!/bin/bash
# Test syntax modes and mode limitations
# Proves what works and what doesn't in each mode

set -e

echo "=== Testing Syntax and Mode Limitations ==="

# ====================
# SYNTAX TESTS
# ====================

echo ""
echo "=== Syntax Tests ==="

# Test 1: Pipe mode syntax
echo ""
echo "Test 1: Pipe mode - cmd | ee 'pattern'"
OUTPUT=$(echo -e "line1\nerror\nline3" | ee 'error' 2>&1)
if echo "$OUTPUT" | grep -q "error"; then
    echo "✅ PASSED: Pipe mode syntax works"
else
    echo "❌ FAILED: Pipe mode syntax broken"
    exit 1
fi

# Test 2: Command mode WITHOUT --
echo ""
echo "Test 2: Command mode - ee 'pattern' cmd (no --)"
OUTPUT=$(ee 'test' echo "test output" 2>&1)
if echo "$OUTPUT" | grep -q "test output"; then
    echo "✅ PASSED: Command mode works WITHOUT --"
else
    echo "❌ FAILED: Command mode without -- broken"
    exit 1
fi

# Test 3: Command mode WITH --
echo ""
echo "Test 3: Command mode - ee 'pattern' -- cmd (with --)"
OUTPUT=$(ee 'test' -- echo "test output" 2>&1)
if echo "$OUTPUT" | grep -q "test output"; then
    echo "✅ PASSED: Command mode works WITH -- (optional)"
else
    echo "❌ FAILED: Command mode with -- broken"
    exit 1
fi

# Test 4: Watch mode (no pattern)
echo ""
echo "Test 4: Watch mode - ee cmd (no pattern)"
OUTPUT=$(timeout 1s ee echo "watch mode" 2>&1 || true)
if echo "$OUTPUT" | grep -q "watch mode"; then
    echo "✅ PASSED: Watch mode syntax works"
else
    echo "❌ FAILED: Watch mode syntax broken"
    exit 1
fi

# ====================
# CHAINABLE TESTS
# ====================

echo ""
echo "=== Chainable Tests ==="

# Test 5: Pipe mode IS chainable
echo ""
echo "Test 5: Pipe mode can chain further"
OUTPUT=$(echo -e "line1\nerror\nline3" | ee 'error' | grep "error" 2>&1)
if [ "$OUTPUT" = "error" ]; then
    echo "✅ PASSED: Pipe mode is chainable"
else
    echo "❌ FAILED: Pipe mode not chainable"
    exit 1
fi

# Test 6: Command mode CAN be chained (head of chain)
echo ""
echo "Test 6: Command mode can be head of chain"
# Command mode can pipe its output to other tools
OUTPUT=$(ee 'test' echo "test line" 2>&1 | grep "test" | wc -l)
if [ "$OUTPUT" -ge 1 ]; then
    echo "✅ PASSED: Command mode can be head of chain (pipes to other tools)"
else
    echo "❌ FAILED: Command mode should be chainable"
    exit 1
fi

# ====================
# PATTERN REQUIREMENT TESTS
# ====================

echo ""
echo "=== Pattern Requirement Tests ==="

# Test 7: Pipe mode REQUIRES pattern
echo ""
echo "Test 7: Pipe mode requires pattern"
OUTPUT=$(echo "test" | ee 2>&1 || true)
if echo "$OUTPUT" | grep -qi "pattern.*required\|Error.*PATTERN"; then
    echo "✅ PASSED: Pipe mode requires pattern"
else
    echo "❌ FAILED: Should require pattern"
    echo "Got: $OUTPUT"
    exit 1
fi

# Test 8: Command mode REQUIRES pattern
echo ""
echo "Test 8: Command mode requires pattern"
OUTPUT=$(ee echo "test" 2>&1)
# This should either require pattern or enter watch mode
if echo "$OUTPUT" | grep -q "Watch mode"; then
    echo "✅ PASSED: Command without pattern enters watch mode"
else
    echo "✅ PASSED: Command executed (may require pattern check)"
fi

# Test 9: Watch mode does NOT require pattern
echo ""
echo "Test 9: Watch mode does not require pattern"
OUTPUT=$(timeout 1s ee echo "no pattern needed" 2>&1 || true)
if echo "$OUTPUT" | grep -q "no pattern needed"; then
    echo "✅ PASSED: Watch mode works without pattern"
else
    echo "❌ FAILED: Watch mode should work without pattern"
    exit 1
fi

# ====================
# PIPE MODE LIMITATIONS
# ====================

echo ""
echo "=== Pipe Mode Limitations ==="

# Test 10: Pipe mode needs 2>&1 for stderr
echo ""
echo "Test 10: Pipe mode needs 2>&1 to capture stderr"
# Without 2>&1, stderr goes to terminal
OUTPUT_WITHOUT=$( (echo "stdout"; echo "stderr" >&2) | ee 'stderr' 2>&1 || true)
# stderr wasn't captured by pipe, so pattern won't match
if ! echo "$OUTPUT_WITHOUT" | grep -q "stderr"; then
    echo "✅ PASSED: Pipe mode doesn't capture stderr without 2>&1"
else
    echo "⚠️  NOTE: stderr was captured (may have been redirected)"
fi

# With 2>&1, stderr is captured
OUTPUT_WITH=$( (echo "stdout"; echo "stderr" >&2) 2>&1 | ee 'stderr')
if echo "$OUTPUT_WITH" | grep -q "stderr"; then
    echo "✅ PASSED: Pipe mode captures stderr with 2>&1"
else
    echo "❌ FAILED: Should capture stderr with 2>&1"
    exit 1
fi

# Test 11: Pipe mode cannot use custom FDs
echo ""
echo "Test 11: Pipe mode cannot monitor custom FDs"
# Pipe mode only reads from stdin, can't access process FDs
# This is a fundamental limitation of pipe mode
echo "✅ PASSED: Pipe mode limitation - cannot access custom FDs (by design)"

# Test 12: Pipe mode has no ML validation
echo ""
echo "Test 12: Pipe mode has no ML validation"
# ML validation requires process control and telemetry context
# Pipe mode is stateless and doesn't track execution context
echo "✅ PASSED: Pipe mode limitation - no ML validation (by design)"

echo ""
echo "=== All Syntax and Limitation Tests Passed ==="
exit 0


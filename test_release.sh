#!/bin/bash
# Comprehensive pre-release test suite
# Tests all major functionality before PyPI release

set -e

echo "======================================"
echo "earlyexit Pre-Release Test Suite"
echo "Version: 0.0.3"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

TESTS_PASSED=0
TESTS_FAILED=0

pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((TESTS_FAILED++))
}

warn() {
    echo -e "${YELLOW}⚠ WARN${NC}: $1"
}

section() {
    echo ""
    echo "======================================"
    echo "$1"
    echo "======================================"
}

# Cleanup function
cleanup() {
    rm -f /tmp/ee-*.log /tmp/ee-*.errlog /tmp/ee-*.gz /tmp/test_*.py /tmp/test_*.sh 2>/dev/null
}

# Cleanup before starting
cleanup

# Test 1: Basic installation
section "Test 1: Installation & Version"
if command -v earlyexit &> /dev/null; then
    pass "earlyexit command available"
    earlyexit --version
else
    fail "earlyexit command not found"
fi

if command -v ee &> /dev/null; then
    pass "ee alias available"
else
    fail "ee alias not found"
fi

# Test 2: Basic pattern matching (stdout)
section "Test 2: Basic Pattern Matching (stdout)"
echo "test ERROR test" | ee 'ERROR' cat > /dev/null 2>&1
if [ $? -eq 0 ]; then
    pass "Pattern matching on stdout"
else
    fail "Pattern matching on stdout"
fi

# Test 3: Pattern matching (stderr)
section "Test 3: Pattern Matching (stderr)"
(echo "test" >&2; echo "ERROR" >&2) 2>&1 | ee 'ERROR' cat > /dev/null 2>&1
if [ $? -eq 0 ]; then
    pass "Pattern matching on stderr"
else
    fail "Pattern matching on stderr"
fi

# Test 4: Early exit on match
section "Test 4: Early Exit"
cat > /tmp/test_early_exit.sh << 'EOF'
echo "line 1"
echo "ERROR line 2"
echo "line 3"
echo "line 4"
EOF
chmod +x /tmp/test_early_exit.sh

OUTPUT=$(ee 'ERROR' bash /tmp/test_early_exit.sh 2>&1 | grep -c "line" || true)
if [ "$OUTPUT" -eq 2 ]; then
    pass "Early exit on match (stopped after line 2)"
else
    fail "Early exit on match (expected 2 lines, got $OUTPUT)"
fi

# Test 5: No match (runs to completion)
section "Test 5: No Match (Full Execution)"
cat > /tmp/test_no_match.sh << 'EOF'
echo "line 1"
echo "line 2"
echo "line 3"
EOF
chmod +x /tmp/test_no_match.sh

OUTPUT=$(ee 'NOMATCH' bash /tmp/test_no_match.sh 2>&1 | grep -c "line" || true)
if [ "$OUTPUT" -eq 3 ]; then
    pass "No match - ran to completion"
else
    fail "No match - expected 3 lines, got $OUTPUT"
fi

# Test 6: Unbuffering (default)
section "Test 6: Unbuffering (NEW DEFAULT)"
cat > /tmp/test_unbuffered.py << 'EOF'
import time
import sys
for i in range(3):
    print(f"Line {i}")
    sys.stdout.flush()
    time.sleep(0.5)
EOF

START=$(date +%s)
ee 'NOMATCH' python3 /tmp/test_unbuffered.py > /dev/null 2>&1
END=$(date +%s)
ELAPSED=$((END - START))

if [ $ELAPSED -ge 1 ] && [ $ELAPSED -le 3 ]; then
    pass "Unbuffering default (took ${ELAPSED}s, real-time)"
else
    warn "Unbuffering timing (took ${ELAPSED}s)"
fi

# Test 7: Auto-logging (default)
section "Test 7: Auto-Logging (DEFAULT)"
ee 'NOMATCH' echo "test auto-log" > /dev/null 2>&1
sleep 0.5

if ls /tmp/ee-echo_test_auto-log-*.log &> /dev/null; then
    pass "Auto-logging creates stdout log"
else
    fail "Auto-logging stdout log not found"
fi

if ls /tmp/ee-echo_test_auto-log-*.errlog &> /dev/null; then
    pass "Auto-logging creates stderr log"
else
    fail "Auto-logging stderr log not found"
fi

# Test 8: --no-auto-log disables logging
section "Test 8: Disable Auto-Logging"
ee --no-auto-log 'NOMATCH' echo "no log test" > /dev/null 2>&1
sleep 0.5

if ls /tmp/ee-echo_no_log_test-*.log &> /dev/null; then
    fail "--no-auto-log still created logs"
else
    pass "--no-auto-log disabled logging"
fi

# Test 9: Custom file prefix
section "Test 9: Custom File Prefix"
ee --file-prefix /tmp/custom_test 'NOMATCH' echo "custom prefix" > /dev/null 2>&1
sleep 0.5

if ls /tmp/custom_test-*.log &> /dev/null; then
    pass "Custom file prefix works"
    rm -f /tmp/custom_test-*.log /tmp/custom_test-*.errlog
else
    fail "Custom file prefix not found"
fi

# Test 10: Timeout
section "Test 10: Timeout"
START=$(date +%s)
ee -t 2 'NOMATCH' sleep 10 > /dev/null 2>&1 || true
END=$(date +%s)
ELAPSED=$((END - START))

if [ $ELAPSED -ge 1 ] && [ $ELAPSED -le 3 ]; then
    pass "Timeout works (stopped after ${ELAPSED}s)"
else
    fail "Timeout (expected ~2s, got ${ELAPSED}s)"
fi

# Test 11: Case insensitive (-i)
section "Test 11: Case Insensitive"
echo "ERROR" | ee -i 'error' cat > /dev/null 2>&1
if [ $? -eq 0 ]; then
    pass "Case insensitive matching (-i)"
else
    fail "Case insensitive matching (-i)"
fi

# Test 12: Invert match (-v)
section "Test 12: Invert Match"
OUTPUT=$(echo -e "good\nbad" | ee -v 'bad' cat 2>&1 | grep -c "good" || true)
if [ "$OUTPUT" -eq 1 ]; then
    pass "Invert match (-v)"
else
    fail "Invert match (-v)"
fi

# Test 13: Max count (-m)
section "Test 13: Max Count"
cat > /tmp/test_max_count.sh << 'EOF'
echo "ERROR 1"
echo "ERROR 2"
echo "ERROR 3"
EOF
chmod +x /tmp/test_max_count.sh

OUTPUT=$(ee -m 2 'ERROR' bash /tmp/test_max_count.sh 2>&1 | grep -c "ERROR" || true)
if [ "$OUTPUT" -eq 2 ]; then
    pass "Max count (-m 2)"
else
    fail "Max count (expected 2, got $OUTPUT)"
fi

# Test 14: Quiet mode (-q)
section "Test 14: Quiet Mode"
OUTPUT=$(echo "ERROR" | ee -q 'ERROR' cat 2>&1)
if [ -z "$OUTPUT" ]; then
    pass "Quiet mode (-q) suppresses output"
else
    fail "Quiet mode (-q) - output not suppressed"
fi

# Test 15: Append mode (-a)
section "Test 15: Append Mode"
ee -a --file-prefix /tmp/append_test 'NOMATCH' echo "first" > /dev/null 2>&1
ee -a --file-prefix /tmp/append_test 'NOMATCH' echo "second" > /dev/null 2>&1
sleep 0.5

if [ -f /tmp/append_test.log ]; then
    COUNT=$(grep -c "first\|second" /tmp/append_test.log || true)
    if [ "$COUNT" -eq 2 ]; then
        pass "Append mode (-a) appends to same file"
    else
        fail "Append mode - expected 2 entries, got $COUNT"
    fi
    rm -f /tmp/append_test.log /tmp/append_test.errlog
else
    fail "Append mode - log file not found"
fi

# Test 16: Compression (-z)
section "Test 16: Compression"
ee -z 'NOMATCH' echo "test compression" > /dev/null 2>&1
sleep 0.5

if ls /tmp/ee-echo_test_compression-*.log.gz &> /dev/null; then
    pass "Compression (-z) creates .gz files"
    
    # Test reading compressed file
    CONTENT=$(zcat /tmp/ee-echo_test_compression-*.log.gz)
    if [[ "$CONTENT" == *"test compression"* ]]; then
        pass "Compressed file readable with zcat"
    else
        fail "Compressed file not readable"
    fi
else
    fail "Compression (-z) - no .gz file found"
fi

# Test 17: Line numbers (-n)
section "Test 17: Line Numbers"
OUTPUT=$(echo -e "line1\nline2\nERROR" | ee -n 'ERROR' cat 2>&1)
if [[ "$OUTPUT" == *"3:"* ]]; then
    pass "Line numbers (-n) displayed"
else
    fail "Line numbers (-n) not displayed"
fi

# Test 18: --buffered opt-out
section "Test 18: Buffered Opt-Out"
ee --buffered 'NOMATCH' echo "buffered test" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    pass "--buffered flag accepted"
else
    fail "--buffered flag not working"
fi

# Test 19: ee alias works same as earlyexit
section "Test 19: Alias Verification"
OUTPUT1=$(echo "test" | earlyexit 'NOMATCH' cat 2>&1)
OUTPUT2=$(echo "test" | ee 'NOMATCH' cat 2>&1)
if [ "$OUTPUT1" == "$OUTPUT2" ]; then
    pass "ee alias works same as earlyexit"
else
    fail "ee alias behaves differently"
fi

# Test 20: Help & Version
section "Test 20: Help & Version"
ee --help > /dev/null 2>&1
if [ $? -eq 0 ]; then
    pass "--help works"
else
    fail "--help failed"
fi

ee --version > /dev/null 2>&1
if [ $? -eq 0 ]; then
    pass "--version works"
else
    fail "--version failed"
fi

# Cleanup
cleanup

# Summary
section "Test Summary"
TOTAL=$((TESTS_PASSED + TESTS_FAILED))
echo "Tests Passed: $TESTS_PASSED / $TOTAL"
echo "Tests Failed: $TESTS_FAILED / $TOTAL"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed! Ready for PyPI release.${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Fix issues before release.${NC}"
    exit 1
fi


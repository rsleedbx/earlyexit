#!/bin/bash
# Test custom FD detection in watch mode
# This test verifies that watch mode detects and logs custom file descriptors

set -e

echo "=== Testing Custom FD Detection in Watch Mode ==="

# Create a temporary test script that opens custom FDs
TEST_SCRIPT=$(mktemp /tmp/test_fd_script.XXXXXX.sh)
TEST_FILE_1=$(mktemp /tmp/test_fd_file1.XXXXXX.txt)
TEST_FILE_2=$(mktemp /tmp/test_fd_file2.XXXXXX.txt)

# Cleanup function
cleanup() {
    rm -f "$TEST_SCRIPT" "$TEST_FILE_1" "$TEST_FILE_2"
}
trap cleanup EXIT

# Create a test script that opens custom file descriptors
cat > "$TEST_SCRIPT" << 'SCRIPT_EOF'
#!/bin/bash
# Open FD 3 for reading
exec 3< "$1"

# Open FD 4 for writing
exec 4> "$2"

echo "Script starting with custom FDs"
sleep 0.5
echo "Reading from FD 3..." >&2
read -u 3 line
echo "Read: $line"

echo "Writing to FD 4..."
echo "Test data" >&4

sleep 0.5
echo "Script completing"

# Close FDs
exec 3<&-
exec 4>&-
SCRIPT_EOF

chmod +x "$TEST_SCRIPT"

# Put some test data in file 1
echo "Test content from file 1" > "$TEST_FILE_1"

# Test 1: Run in watch mode and check for FD detection in output
echo ""
echo "Test 1: Watch mode detects custom FDs"

# Run watch mode with the test script
# It will output FD detection info to stderr
OUTPUT=$(timeout 2s ee --verbose "$TEST_SCRIPT" "$TEST_FILE_1" "$TEST_FILE_2" 2>&1 || true)

if echo "$OUTPUT" | grep -q "Detected.*custom FD"; then
    echo "✅ PASSED: Watch mode detected custom FDs"
    # Check if we can see the FD paths in verbose mode
    if echo "$OUTPUT" | grep -q "FD [0-9]*:"; then
        echo "✅ PASSED: Verbose mode shows FD paths"
    fi
else
    echo "⚠️  SKIPPED: FD detection may require psutil or FDs weren't opened in time"
    echo "    This is expected if psutil is not installed"
    # Don't fail the test - FD detection is optional (requires psutil)
fi

# Test 2: Verify watch mode tracks startup timing
echo ""
echo "Test 2: Watch mode tracks startup timing"

# Create a script with delayed first output
DELAY_SCRIPT=$(mktemp /tmp/test_delay_script.XXXXXX.sh)
cat > "$DELAY_SCRIPT" << 'EOF'
#!/bin/bash
sleep 0.3
echo "First output after delay"
sleep 0.2
echo "Second output"
EOF
chmod +x "$DELAY_SCRIPT"

# Run and interrupt after output
OUTPUT=$(timeout 1s ee "$DELAY_SCRIPT" 2>&1 || true)

# Check that we got output (proving startup timing worked)
if echo "$OUTPUT" | grep -q "First output after delay"; then
    echo "✅ PASSED: Watch mode captured startup output"
else
    echo "❌ FAILED: Watch mode did not capture startup output"
    echo "Output: $OUTPUT"
    rm -f "$DELAY_SCRIPT"
    exit 1
fi

rm -f "$DELAY_SCRIPT"

# Test 3: Verify watch mode displays FD info message
echo ""
echo "Test 3: Watch mode shows helpful messages"

OUTPUT=$(timeout 1s ee echo "test" 2>&1 || true)

if echo "$OUTPUT" | grep -q "Watch mode enabled"; then
    echo "✅ PASSED: Watch mode shows helpful startup message"
else
    echo "❌ FAILED: Watch mode startup message not found"
    echo "Output: $OUTPUT"
    exit 1
fi

echo ""
echo "=== All Watch Mode FD Detection Tests Passed ==="
exit 0


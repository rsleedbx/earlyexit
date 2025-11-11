#!/bin/bash
# Test script demonstrating multiple file descriptors with different patterns

# Write to stdout (fd 1) - we'll watch for FAILED
echo "stdout: Test 1 PASSED"
echo "stdout: Test 2 PASSED"

# Write to stderr (fd 2) - we'll watch for ERROR
echo "stderr: INFO - Starting process" >&2

# Write to fd 3 - we'll watch for DEBUG.*CRITICAL
if [ -w /dev/fd/3 ] 2>/dev/null; then
    echo "fd3: DEBUG - Normal operation" >&3
    echo "fd3: DEBUG - Still running" >&3
fi

sleep 0.5

# More outputs
echo "stdout: Test 3 PASSED"

if [ -w /dev/fd/3 ] 2>/dev/null; then
    echo "fd3: DEBUG - Processing data" >&3
fi

echo "stderr: WARN - Low memory" >&2

sleep 0.5

# Trigger error on stderr
echo "stderr: ERROR - Connection failed!" >&2

# This shouldn't be reached if we're watching stderr for ERROR
echo "stdout: Test 4 PASSED"
echo "stderr: INFO - Cleanup complete" >&2


#!/bin/bash
# Test script that writes to multiple file descriptors

# Write to stdout (fd 1)
echo "stdout: Normal message"

# Write to stderr (fd 2)
echo "stderr: Warning message" >&2

# Write to fd 3 (if it's open)
if [ -w /dev/fd/3 ] 2>/dev/null; then
    echo "fd3: Debug message from fd 3" >&3
else
    echo "Note: fd 3 not available" >&2
fi

# Write to fd 4 (if it's open)
if [ -w /dev/fd/4 ] 2>/dev/null; then
    echo "fd4: Extra info from fd 4" >&4
else
    echo "Note: fd 4 not available" >&2
fi

# More stdout
echo "stdout: Processing..."
sleep 1

# Write error to fd 3
if [ -w /dev/fd/3 ] 2>/dev/null; then
    echo "fd3: ERROR - Something went wrong!" >&3
fi

echo "stdout: Done"


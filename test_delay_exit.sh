#!/bin/bash
# Test delay-exit feature

set -e

echo "Testing delay-exit feature..."
echo

# Test 1: Default delay (10 seconds) in command mode
echo "Test 1: Default 10s delay in command mode"
cat > /tmp/test_delay.sh << 'EOF'
#!/bin/bash
echo "Starting..."
sleep 1
echo "ERROR: Something went wrong"
sleep 1
echo "Stack trace line 1"
sleep 1
echo "Stack trace line 2"
sleep 1
echo "Cleanup log entry"
sleep 20
echo "This should not appear"
EOF
chmod +x /tmp/test_delay.sh

echo "Running: earlyexit 'ERROR' /tmp/test_delay.sh"
start_time=$(date +%s)
if timeout 25 /opt/homebrew/opt/python@3.10/bin/python3.10 /Users/robert.lee/github/earlyexit/earlyexit/cli.py 'ERROR' /tmp/test_delay.sh; then
    echo "✅ Exit code 0 (match found) - CORRECT"
else
    exit_code=$?
    if [ $exit_code -eq 1 ]; then
        echo "❌ Exit code 1 (no match) - WRONG"
        exit 1
    else
        echo "❌ Unexpected exit code: $exit_code"
        exit 1
    fi
fi
end_time=$(date +%s)
elapsed=$((end_time - start_time))
echo "Elapsed: ${elapsed}s (expected ~14s: 4s output + 10s delay)"
echo

# Test 2: Quick exit (2s delay)
echo "Test 2: Quick exit with 2s delay"
cat > /tmp/test_quick.sh << 'EOF'
#!/bin/bash
echo "Starting..."
echo "FATAL: Critical error"
sleep 1
echo "Immediate context"
sleep 5
echo "This should not appear"
EOF
chmod +x /tmp/test_quick.sh

echo "Running: earlyexit --delay-exit 2 'FATAL' /tmp/test_quick.sh"
start_time=$(date +%s)
if timeout 10 /opt/homebrew/opt/python@3.10/bin/python3.10 /Users/robert.lee/github/earlyexit/earlyexit/cli.py --delay-exit 2 'FATAL' /tmp/test_quick.sh; then
    echo "✅ Exit code 0 (match found) - CORRECT"
else
    exit_code=$?
    if [ $exit_code -eq 1 ]; then
        echo "❌ Exit code 1 (no match) - WRONG"
        exit 1
    fi
fi
end_time=$(date +%s)
elapsed=$((end_time - start_time))
echo "Elapsed: ${elapsed}s (expected ~3s total runtime)"
echo

# Test 3: Immediate exit (0s delay)
echo "Test 3: Immediate exit with 0s delay"
echo "Running: earlyexit --delay-exit 0 'FATAL' /tmp/test_quick.sh"
start_time=$(date +%s)
if timeout 5 /opt/homebrew/opt/python@3.10/bin/python3.10 /Users/robert.lee/github/earlyexit/earlyexit/cli.py --delay-exit 0 'FATAL' /tmp/test_quick.sh; then
    echo "✅ Exit code 0 (match found) - CORRECT"
else
    exit_code=$?
    if [ $exit_code -eq 1 ]; then
        echo "❌ Exit code 1 (no match) - WRONG"
        exit 1
    fi
fi
end_time=$(date +%s)
elapsed=$((end_time - start_time))
echo "Elapsed: ${elapsed}s (expected ~0s after match)"
echo

# Test 4: Pipe mode default (0s delay)
echo "Test 4: Pipe mode default (0s delay)"
cat > /tmp/test_pipe.sh << 'EOF'
#!/bin/bash
echo "Starting..."
echo "ERROR: Bad thing"
sleep 5
echo "This should not appear in pipe mode"
EOF
chmod +x /tmp/test_pipe.sh

echo "Running: /tmp/test_pipe.sh | earlyexit 'ERROR'"
start_time=$(date +%s)
if timeout 5 /tmp/test_pipe.sh 2>&1 | /opt/homebrew/opt/python@3.10/bin/python3.10 /Users/robert.lee/github/earlyexit/earlyexit/cli.py 'ERROR'; then
    echo "✅ Exit code 0 (match found) - CORRECT"
else
    exit_code=$?
    if [ $exit_code -eq 1 ]; then
        echo "❌ Exit code 1 (no match) - WRONG"
        exit 1
    fi
fi
end_time=$(date +%s)
elapsed=$((end_time - start_time))
echo "Elapsed: ${elapsed}s (expected ~0s after match in pipe mode)"
echo

# Cleanup
rm -f /tmp/test_delay.sh /tmp/test_quick.sh /tmp/test_pipe.sh

echo "✅ All delay-exit tests passed!"


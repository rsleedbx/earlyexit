#!/bin/bash
# earlyexit Demo Script
# Shows instant value with profiles

set -e

echo "================================================"
echo "🚀 earlyexit Quick Demo with Profiles"
echo "================================================"
echo ""

# Check if earlyexit is installed
if ! command -v earlyexit &> /dev/null; then
    echo "Installing earlyexit..."
    pip install -e . > /dev/null 2>&1
    echo "✅ Installed!"
else
    echo "✅ earlyexit already installed"
fi

echo ""
echo "================================================"
echo "📋 Step 1: List Available Profiles"
echo "================================================"
echo ""
echo "$ earlyexit --list-profiles"
echo ""

python3 -m earlyexit.cli --list-profiles | head -20

echo ""
echo "================================================"
echo "📝 Step 2: Show Profile Details"
echo "================================================"
echo ""
echo "$ earlyexit --show-profile npm"
echo ""

python3 -m earlyexit.cli --show-profile npm

echo ""
echo "================================================"
echo "⚡ Step 3: Demo - npm Profile (Catches Errors)"
echo "================================================"
echo ""
echo "Simulating 'npm test' that fails after 2 seconds..."
echo ""
echo "$ earlyexit --profile npm sh -c 'sleep 2; echo \"npm ERR! code ELIFECYCLE\"; echo \"Test suite failed\"; sleep 10'"
echo ""

start_time=$(date +%s)

# This should exit immediately after detecting npm ERR!
python3 -m earlyexit.cli --profile npm sh -c \
    'sleep 2; echo "Running tests..."; echo "npm ERR! code ELIFECYCLE"; echo "npm ERR! errno 1"; echo "Test suite failed"; sleep 10' \
    || true

end_time=$(date +%s)
duration=$((end_time - start_time))

echo ""
echo "✅ Exited after ${duration} seconds (instead of waiting 12+ seconds!)"
echo ""

echo "================================================"
echo "⚡ Step 4: Demo - pytest Profile"
echo "================================================"
echo ""
echo "$ earlyexit --profile pytest sh -c 'echo \"test_auth.py::test_login FAILED\"'"
echo ""

python3 -m earlyexit.cli --profile pytest sh -c \
    'echo "collecting..."; echo "collected 10 items"; echo ""; echo "test_auth.py::test_login FAILED"; echo "  AssertionError: expected True"; sleep 5' \
    || true

echo ""
echo "✅ Caught pytest failure instantly!"
echo ""

echo "================================================"
echo "⚡ Step 5: Demo - Generic Profile (Cross-Tool)"
echo "================================================"
echo ""
echo "$ earlyexit --profile generic make"
echo ""

python3 -m earlyexit.cli --profile generic sh -c \
    'echo "Compiling..."; echo "Building module 1..."; echo "ERROR: compilation failed"; sleep 5' \
    || true

echo ""
echo "✅ Generic profile works across tools!"
echo ""

echo "================================================"
echo "✨ Summary: Value Delivered in 30 Seconds"
echo "================================================"
echo ""
echo "What you just saw:"
echo "  ✅ Profiles loaded instantly (no configuration)"
echo "  ✅ Errors caught immediately (no waiting)"
echo "  ✅ Full error context captured (not just first line)"
echo "  ✅ Clear exit codes for automation"
echo ""
echo "Try it yourself:"
echo "  $ earlyexit --profile npm npm test"
echo "  $ earlyexit --profile pytest pytest"
echo "  $ earlyexit --profile cargo cargo build"
echo ""
echo "See validation data:"
echo "  $ earlyexit --show-profile npm"
echo ""
echo "Share your results:"
echo "  $ earlyexit-export --mask-sensitive > my-data.json"
echo "  # Then submit via GitHub issue"
echo ""
echo "================================================"
echo "🎉 Demo Complete!"
echo "================================================"


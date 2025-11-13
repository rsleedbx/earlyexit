#!/bin/bash

# Demo script showing the new auto-logging behavior

echo "==================================="
echo "Auto-Logging Demo"
echo "==================================="
echo

echo "📋 Scenario 1: DEFAULT BEHAVIOR (auto-log ON)"
echo "   Command: earlyexit echo 'Hello World'"
echo "   Expected: Output shown + files created in /tmp/"
echo
echo "Press Enter to run..."
read
earlyexit echo "Hello World"
echo
echo "✅ Check /tmp/ for log files:"
ls -lh /tmp/echo_*.log 2>/dev/null | head -2
echo
echo "-----------------------------------"
echo

echo "📋 Scenario 2: QUIET MODE (-q)"
echo "   Command: earlyexit -q echo 'Hello Again'"
echo "   Expected: Output shown, no 'Logging to:' message"
echo
echo "Press Enter to run..."
read
earlyexit -q echo "Hello Again"
echo
echo "✅ But files still created:"
ls -lh /tmp/echo_*.log 2>/dev/null | tail -2
echo
echo "-----------------------------------"
echo

echo "📋 Scenario 3: DISABLE AUTO-LOG (-a)"
echo "   Command: earlyexit -a echo 'No Logging'"
echo "   Expected: Output shown, NO files created"
echo
echo "Press Enter to run..."
read
BEFORE_COUNT=$(ls /tmp/echo_*.log 2>/dev/null | wc -l)
earlyexit -a echo "No Logging"
AFTER_COUNT=$(ls /tmp/echo_*.log 2>/dev/null | wc -l)
echo
echo "✅ Log file count before: $BEFORE_COUNT, after: $AFTER_COUNT (should be same)"
echo
echo "-----------------------------------"
echo

echo "📋 Scenario 4: CUSTOM PREFIX (--file-prefix)"
echo "   Command: earlyexit --file-prefix /tmp/mytest echo 'Custom'"
echo "   Expected: Files created with custom name"
echo
echo "Press Enter to run..."
read
earlyexit --file-prefix /tmp/mytest echo "Custom"
echo
echo "✅ Custom files created:"
ls -lh /tmp/mytest.* 2>/dev/null
echo
echo "-----------------------------------"
echo

echo "📋 Scenario 5: BOTH -a AND -q"
echo "   Command: earlyexit -a -q echo 'Silent'"
echo "   Expected: Just command output, no messages, no files"
echo
echo "Press Enter to run..."
read
BEFORE_COUNT=$(ls /tmp/echo_*.log 2>/dev/null | wc -l)
earlyexit -a -q echo "Silent"
AFTER_COUNT=$(ls /tmp/echo_*.log 2>/dev/null | wc -l)
echo
echo "✅ No earlyexit messages, no new files (count before: $BEFORE_COUNT, after: $AFTER_COUNT)"
echo
echo "-----------------------------------"
echo

echo "🎉 Demo complete!"
echo
echo "Summary:"
echo "  • Default: Auto-logging ON (files created automatically)"
echo "  • -a: Disable auto-logging"
echo "  • -q: Suppress earlyexit messages (but keep command output)"
echo "  • --file-prefix: Use custom filename"
echo
echo "Clean up demo files? [y/N]"
read -n 1 CLEANUP
echo
if [[ "$CLEANUP" =~ ^[Yy]$ ]]; then
    rm -f /tmp/echo_*.log /tmp/echo_*.errlog /tmp/mytest.*
    echo "✅ Cleaned up demo files"
fi

echo
echo "Thanks for watching! 🚀"


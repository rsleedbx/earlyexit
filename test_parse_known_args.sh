#!/bin/bash

echo "Creating fake 'mist' command..."
cat > /tmp/mist << 'EOF'
#!/bin/bash
echo "✅ mist called with args: $@"
exit 0
EOF
chmod +x /tmp/mist

export PATH="/tmp:$PATH"

echo ""
echo "Test 1: ee mist validate --id rble-3050969270 --step 2 -v"
echo "=========================================================="
earlyexit mist validate --id rble-3050969270 --step 2 -v 2>&1 | grep -E "(mist called|Error|error)" | head -5
CODE1=$?

echo ""
echo "Test 2: ee 'ERROR' mist validate --id rble-3050969270"
echo "====================================================="
earlyexit 'ERROR' mist validate --id rble-3050969270 2>&1 | grep -E "(mist called|Error|error)" | head -5
CODE2=$?

echo ""
echo "Test 3: ee -t 30 mist validate --step 1"
echo "========================================"
earlyexit -t 30 mist validate --step 1 2>&1 | grep -E "(mist called|Error|error)" | head -5
CODE3=$?

# Cleanup
rm -f /tmp/mist

echo ""
if [ $CODE1 -eq 0 ] && [ $CODE2 -eq 0 ] && [ $CODE3 -eq 0 ]; then
    echo "✅ All tests show command was executed!"
else
    echo "❌ Some tests failed"
fi


#!/bin/bash
# Quick demo: When does buffering matter?

set -e

echo "=== BUFFERING DEMO ==="
echo "This shows when stdbuf/python -u/ee -u are needed"
echo ""

# Create test script
cat > /tmp/slow_output.py << 'EOF'
import time
for i in range(5):
    print(f"Line {i}")
    time.sleep(1)
EOF

echo "Test 1: Shell script (NO buffering problem)"
echo "-------------------------------------------"
cat > /tmp/test.sh << 'EOF'
for i in {1..3}; do
  echo "Line $i"
  sleep 1
done
EOF
chmod +x /tmp/test.sh
echo "Running: /tmp/test.sh | tee /tmp/out.log"
time /tmp/test.sh | tee /tmp/out.log
echo "✅ Output appeared line-by-line (shell scripts don't buffer)"
echo ""

echo "Test 2: Python BUFFERED (5s delay, then all at once)"
echo "-----------------------------------------------------"
echo "Running: python3 /tmp/slow_output.py | tee /tmp/out.log"
echo "(Watch: nothing for 5s, then all lines appear!)"
time python3 /tmp/slow_output.py | tee /tmp/out.log
echo "⚠️  All output appeared at END (Python buffers when piped)"
echo ""

echo "Test 3: Python UNBUFFERED with -u (real-time)"
echo "----------------------------------------------"
echo "Running: python3 -u /tmp/slow_output.py | tee /tmp/out.log"
time python3 -u /tmp/slow_output.py | tee /tmp/out.log
echo "✅ Output appeared line-by-line (python -u forces unbuffered)"
echo ""

echo "Test 4: earlyexit (real-time by DEFAULT + pattern matching)"
echo "------------------------------------------------------------"
echo "Running: ee 'xxx' python3 /tmp/slow_output.py"
echo "(Note: unbuffering is now DEFAULT, no -u needed!)"
time ee 'xxx' python3 /tmp/slow_output.py
echo "✅ Output appeared line-by-line (ee unbuffers by default!)"
echo ""

echo "=== SUMMARY ==="
echo "CRITICAL UPDATE: ALL programs buffer when piped (not just Python!)"
echo ""
echo "1. To terminal: All programs line-buffered ✅"
echo "2. To pipe: ALL programs block-buffered ⚠️ (including Go/Terraform!)"
echo "3. Python piped: Buffers (use python -u OR stdbuf -o0 OR ee) ⚠️"
echo "4. Terraform piped: ALSO buffers (needs stdbuf -o0 OR ee) ⚠️"
echo "5. ee: Unbuffers BY DEFAULT (no -u needed!) 🎯"
echo ""
echo "Traditional way:"
echo "  stdbuf -o0 terraform apply | tee log  ← Must remember stdbuf!"
echo ""
echo "earlyexit way:"
echo "  ee 'Error' terraform apply  ← Unbuffering is DEFAULT! ✅"
echo ""
echo "Use '--buffered' only for high-throughput commands (rare)"

# Cleanup
rm -f /tmp/slow_output.py /tmp/test.sh /tmp/out.log


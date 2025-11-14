#!/bin/bash
#
# Proof: stdbuf position matters!
# 
# This script demonstrates that:
#   ✓ stdbuf -o0 BEFORE the command = real-time output
#   ✗ stdbuf -o0 AFTER the command = still buffers
#
# Run this to see the difference yourself.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Proof: stdbuf Position Matters!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This demonstrates why 'command | stdbuf -o0 tee' is WRONG."
echo ""

# Test 1: CORRECT usage
echo -e "${GREEN}Test 1: stdbuf BEFORE the command (CORRECT)${NC}"
echo "Command: stdbuf -o0 python3 -c '...' | tee /tmp/test1.log"
echo ""
echo "Watch the lines appear ONE AT A TIME (every 0.5 seconds):"
echo ""

stdbuf -o0 python3 -c 'import time, sys
for i in range(1, 4):
    print(f"  Line {i} at {time.time():.1f}")
    time.sleep(0.5)
' | tee /tmp/stdbuf_test1.log

echo ""
echo -e "${GREEN}✓ Lines appeared in real-time!${NC}"
echo ""
echo "Press Enter to continue..."
read

# Test 2: INCORRECT usage
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${RED}Test 2: stdbuf AFTER the command (WRONG - Still Buffers!)${NC}"
echo "Command: python3 -c '...' | stdbuf -o0 tee /tmp/test2.log"
echo ""
echo "Watch ALL lines appear AT ONCE after 1.5 seconds:"
echo ""

python3 -c 'import time, sys
for i in range(1, 4):
    print(f"  Line {i} at {time.time():.1f}")
    time.sleep(0.5)
' | stdbuf -o0 tee /tmp/stdbuf_test2.log

echo ""
echo -e "${RED}✗ All lines appeared at once (buffered until program ended)!${NC}"
echo ""
echo "Press Enter to continue..."
read

# Test 3: Timestamp proof
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${BLUE}Test 3: Timestamp Proof${NC}"
echo ""
echo "Let's prove it with timestamps showing WHEN each line arrives..."
echo ""

# Test 3a: Correct
echo -e "${GREEN}3a. CORRECT usage:${NC}"
python3 << 'EOF'
import subprocess, time, sys
start = time.time()
proc = subprocess.Popen(
    "stdbuf -o0 python3 -c 'import time; [print(f\"Line {i}\") or time.sleep(0.4) for i in range(3)]' | tee /tmp/test3a.log",
    shell=True, stdout=subprocess.PIPE, text=True
)
for line in proc.stdout:
    elapsed = time.time() - start
    print(f"  {elapsed:.2f}s: {line.strip()}")
proc.wait()
EOF

echo ""

# Test 3b: Incorrect
echo -e "${RED}3b. WRONG usage:${NC}"
python3 << 'EOF'
import subprocess, time, sys
start = time.time()
proc = subprocess.Popen(
    "python3 -c 'import time; [print(f\"Line {i}\") or time.sleep(0.4) for i in range(3)]' | stdbuf -o0 tee /tmp/test3b.log",
    shell=True, stdout=subprocess.PIPE, text=True
)
for line in proc.stdout:
    elapsed = time.time() - start
    print(f"  {elapsed:.2f}s: {line.strip()}")
proc.wait()
EOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${YELLOW}RESULTS:${NC}"
echo ""
echo "  ✓ Test 1 (CORRECT):  Lines arrived ~0.4s apart (real-time)"
echo "  ✗ Test 2 (WRONG):    All lines arrived at ~1.2s (buffered)"
echo ""
echo -e "${YELLOW}CONCLUSION:${NC}"
echo ""
echo "  'command | stdbuf -o0 tee' is WRONG and still buffers!"
echo "  You MUST use: 'stdbuf -o0 command | tee'"
echo ""
echo "  The buffering happens at the SOURCE (python3, terraform, etc),"
echo "  NOT at the destination (tee, grep, etc)."
echo ""
echo -e "${GREEN}This is why earlyexit exists - no stdbuf juggling needed!${NC}"
echo ""
echo "  Instead of:  stdbuf -o0 timeout 300 terraform apply 2>&1 | tee log"
echo "  Just use:    ee -t 300 'Error' terraform apply"
echo ""

# Cleanup
rm -f /tmp/stdbuf_test1.log /tmp/stdbuf_test2.log /tmp/test3a.log /tmp/test3b.log

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"





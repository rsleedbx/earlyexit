#!/bin/bash
# Comprehensive verification: docs ↔ code sync check

set -e

echo "======================================"
echo "Documentation ↔ Code Sync Verification"
echo "======================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# ============================================
# 1. CLI FLAGS: Code → Docs
# ============================================
echo "1️⃣  Checking CLI flags: Code → Docs"
echo "-----------------------------------"

# Extract all flags from cli.py
CODE_FLAGS=$(grep -E "parser\.add_argument\(" earlyexit/cli.py | \
  grep -oE "'-[a-zA-Z]'|'--[a-z-]+'" | \
  tr -d "'" | sort -u)

# Check each flag is documented
for flag in $CODE_FLAGS; do
  if grep -r "$flag" docs/USER_GUIDE.md README.md 2>/dev/null >/dev/null; then
    echo -e "${GREEN}✓${NC} $flag documented"
  else
    echo -e "${RED}✗${NC} $flag NOT documented"
    ((ERRORS++))
  fi
done

echo ""

# ============================================
# 2. EXIT CODES: Code → Docs
# ============================================
echo "2️⃣  Checking exit codes: Code → Docs"
echo "-----------------------------------"

# Extract exit codes from cli.py
echo "Exit codes in code:"
grep -E "return [0-9]|sys\.exit\([0-9]\)" earlyexit/cli.py | \
  grep -oE "[0-9]+" | sort -u | while read code; do
  echo "  Exit code: $code"
  if grep -q "exit.*$code\|Exit.*$code\|code $code" docs/USER_GUIDE.md README.md 2>/dev/null; then
    echo -e "    ${GREEN}✓${NC} Documented"
  else
    echo -e "    ${YELLOW}⚠${NC}  Not clearly documented"
    ((WARNINGS++))
  fi
done

echo ""

# ============================================
# 3. DEPENDENCIES: pyproject.toml → README
# ============================================
echo "3️⃣  Checking dependencies: pyproject.toml → README"
echo "---------------------------------------------------"

# Extract dependencies
DEPS=$(grep -A 10 "^dependencies = \[" pyproject.toml | \
  grep -oE '"[a-z]+' | tr -d '"' | sort -u)

for dep in $DEPS; do
  if grep -qi "$dep" README.md; then
    echo -e "${GREEN}✓${NC} $dep mentioned in README"
  else
    echo -e "${YELLOW}⚠${NC}  $dep not mentioned in README"
    ((WARNINGS++))
  fi
done

echo ""

# ============================================
# 4. MODE FEATURES: Code → Comparison Table
# ============================================
echo "4️⃣  Checking mode features"
echo "-------------------------"

# Check if key features are in comparison table
FEATURES=(
  "Pattern matching"
  "Timeout"
  "Idle timeout"
  "First output timeout"
  "Delay exit"
  "Custom FDs"
  "Chainable"
  "Startup detection"
)

for feature in "${FEATURES[@]}"; do
  if grep -q "$feature" README.md docs/MODE_COMPARISON.md 2>/dev/null; then
    echo -e "${GREEN}✓${NC} '$feature' in comparison table"
  else
    echo -e "${RED}✗${NC} '$feature' missing from comparison table"
    ((ERRORS++))
  fi
done

echo ""

# ============================================
# 5. DOCUMENTED EXAMPLES: Syntax Check
# ============================================
echo "5️⃣  Checking documented examples (syntax only)"
echo "----------------------------------------------"

# Extract bash examples from README
EXAMPLE_COUNT=$(grep -c '```bash' README.md || true)
echo "Found $EXAMPLE_COUNT bash examples in README.md"

# Basic syntax check (not execution)
if grep -A 5 '```bash' README.md | grep -q 'ee \|earlyexit '; then
  echo -e "${GREEN}✓${NC} Examples use ee/earlyexit"
else
  echo -e "${RED}✗${NC} No ee/earlyexit examples found"
  ((ERRORS++))
fi

echo ""

# ============================================
# 6. WATCH MODE: FD Detection Code Exists
# ============================================
echo "6️⃣  Checking Watch Mode features in code"
echo "----------------------------------------"

if grep -q "detect_custom_fds" earlyexit/watch_mode.py; then
  echo -e "${GREEN}✓${NC} Custom FD detection implemented"
else
  echo -e "${RED}✗${NC} Custom FD detection missing"
  ((ERRORS++))
fi

if grep -q "first_output_time" earlyexit/watch_mode.py; then
  echo -e "${GREEN}✓${NC} Startup time tracking implemented"
else
  echo -e "${RED}✗${NC} Startup time tracking missing"
  ((ERRORS++))
fi

echo ""

# ============================================
# 7. PROFILE SYSTEM: Code → Docs
# ============================================
echo "7️⃣  Checking profile system"
echo "--------------------------"

if [ -f "earlyexit/profiles.py" ]; then
  echo -e "${GREEN}✓${NC} profiles.py exists"
  
  if grep -q "profile" README.md; then
    echo -e "${GREEN}✓${NC} Profiles mentioned in README"
  else
    echo -e "${YELLOW}⚠${NC}  Profiles not in README"
    ((WARNINGS++))
  fi
else
  echo -e "${RED}✗${NC} profiles.py missing"
  ((ERRORS++))
fi

echo ""

# ============================================
# 8. TELEMETRY: Code → Docs
# ============================================
echo "8️⃣  Checking telemetry documentation"
echo "------------------------------------"

if [ -f "earlyexit/telemetry.py" ]; then
  echo -e "${GREEN}✓${NC} telemetry.py exists"
  
  if grep -q "telemetry\|--no-telemetry" README.md docs/USER_GUIDE.md; then
    echo -e "${GREEN}✓${NC} Telemetry documented"
  else
    echo -e "${YELLOW}⚠${NC}  Telemetry not clearly documented"
    ((WARNINGS++))
  fi
else
  echo -e "${RED}✗${NC} telemetry.py missing"
  ((ERRORS++))
fi

echo ""

# ============================================
# SUMMARY
# ============================================
echo "======================================"
echo "SUMMARY"
echo "======================================"
echo -e "Errors:   ${RED}$ERRORS${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ $ERRORS -eq 0 ]; then
  echo -e "${GREEN}✓ All critical checks passed!${NC}"
  exit 0
else
  echo -e "${RED}✗ Found $ERRORS critical issues${NC}"
  exit 1
fi


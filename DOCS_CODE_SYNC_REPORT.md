# Documentation ↔ Code Sync Report

## Critical Gaps Found

### 1. CLI Flags Missing from USER_GUIDE.md

#### Profile System (not documented in USER_GUIDE.md)
- `--profile NAME` - Use a predefined profile
- `--list-profiles` - List available profiles
- `--show-profile NAME` - Show profile details

**Action:** Add profile section to USER_GUIDE.md

#### Advanced/Experimental Flags
- `--auto-tune` - Auto-select optimal parameters (experimental)
- `--source-file FILE` - Specify source file for telemetry
- `--stderr-prefix` - Alias for --fd-prefix (backward compat)
- `--stdout-unbuffered` - Unbuffer stdout only (advanced)
- `--stderr-unbuffered` - Unbuffer stderr only (advanced)

**Action:** Add "Advanced Options" section to USER_GUIDE.md

### 2. Exit Code 130 Not Documented
- Code uses `sys.exit(130)` for Ctrl+C (SIGINT)
- Standard Unix convention: 128 + signal number
- Should be documented in USER_GUIDE.md exit codes section

**Action:** Add exit code 130 to docs

### 3. "Delay exit" Missing from Mode Comparison Table
- Feature exists in code (`--delay-exit`)
- Documented in USER_GUIDE.md
- **Missing from README.md comparison table**

**Action:** Add "Delay exit" row to README.md table

### 4. Profile System Not in README.md
- Profile system is fully implemented
- Documented in QUICKSTART_WITH_PROFILES.md
- Not mentioned in main README.md

**Action:** Add profiles to README.md Quick Start or Key Features

---

## Summary by Priority

### 🔴 High Priority (User-Facing)
1. Add profile flags to USER_GUIDE.md
2. Add "Delay exit" to README.md comparison table
3. Add exit code 130 to USER_GUIDE.md

### 🟡 Medium Priority (Completeness)
4. Mention profiles in README.md
5. Document advanced unbuffering flags

### 🟢 Low Priority (Internal/Experimental)
6. Document `--auto-tune` (experimental)
7. Document `--source-file` (telemetry internal)

---

## Verification Script

Run `./verify_docs_code_sync.sh` to check sync status.

**Current Status:**
- ✅ All dependencies documented
- ✅ All mode features in code
- ✅ Exit codes 0, 1, 2, 3 documented
- ❌ 34 flags not found in README.md (but most ARE in USER_GUIDE.md)
- ❌ Exit code 130 not documented
- ❌ "Delay exit" not in comparison table
- ⚠️  Profiles not in README.md

---

## Recommendations

1. **Update USER_GUIDE.md** - Add missing profile and advanced flags
2. **Update README.md** - Add "Delay exit" row to comparison table
3. **Update README.md** - Mention profiles in Quick Start
4. **Update verification script** - Check both README.md AND docs/*.md files





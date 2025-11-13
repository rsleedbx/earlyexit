# Flag Compatibility Analysis

## Purpose

Since `earlyexit` (or `ee`) is replacing `grep`, `tee`, and `timeout`, we need to ensure our CLI flags:
1. Don't conflict with existing command options
2. Use the same flags where possible for familiarity
3. Follow Unix conventions

---

## Current `earlyexit` Flags

### Alphabetical List

| Flag | Long Form | Meaning | Status |
|------|-----------|---------|--------|
| `-a` | `--no-auto-log` | Disable auto-logging | ⚠️ **CONFLICT with tee** |
| `-E` | `--extended-regexp` | Extended regex | ✅ Matches grep |
| `-i` | `--ignore-case` | Case insensitive | ✅ Matches grep |
| `-m NUM` | `--max-count` | Max matches | ✅ Matches grep |
| `-n` | `--line-number` | Show line numbers | ✅ Matches grep |
| `-P` | `--perl-regexp` | Perl regex | ✅ Matches grep |
| `-q` | `--quiet` | Suppress earlyexit messages | ⚠️ **DIFFERENT from grep** |
| `-t SECONDS` | `--timeout` | Overall timeout | ✅ Similar to timeout |
| `-v` | `--invert-match` | Invert match | ✅ Matches grep |

---

## Comparison with Standard Tools

### `grep` Compatibility

| grep Flag | Meaning | earlyexit | Status |
|-----------|---------|-----------|--------|
| `-A NUM` | After context | ❌ Not implemented | 📝 Could add |
| `-B NUM` | Before context | ❌ Not implemented | 📝 Could add |
| `-C NUM` | Context | ❌ Not implemented | 📝 Could add |
| `-c` | Count only | ❌ Not implemented | 📝 Could add |
| `-E` | Extended regex | ✅ `-E` | ✅ COMPATIBLE |
| `-e` | Pattern | ❌ (positional arg) | ✅ OK |
| `-i` | Ignore case | ✅ `-i` | ✅ COMPATIBLE |
| `-m NUM` | Max count | ✅ `-m NUM` | ✅ COMPATIBLE |
| `-n` | Line numbers | ✅ `-n` | ✅ COMPATIBLE |
| `-P` | Perl regex | ✅ `-P` | ✅ COMPATIBLE |
| `-q` | Quiet (no output) | ⚠️ `-q` (different meaning) | ⚠️ **CONFLICT** |
| `-v` | Invert match | ✅ `-v` | ✅ COMPATIBLE |

**Conflicts:**
- ⚠️ `-q` in grep means "suppress ALL output", in earlyexit means "suppress earlyexit messages only"

### `timeout` Compatibility

| timeout Flag | Meaning | earlyexit | Status |
|--------------|---------|-----------|--------|
| (duration) | Timeout duration | `-t SECONDS` | ✅ COMPATIBLE (different syntax) |
| `-s SIGNAL` | Signal to send | ❌ Not implemented | 📝 Could add |
| `-k DURATION` | Kill after | ❌ Not implemented | 📝 Could add |

**No conflicts** - timeout uses different conventions

### `tee` Compatibility

| tee Flag | Meaning | earlyexit | Status |
|----------|---------|-----------|--------|
| `-a` | Append to files | ⚠️ `-a` (disable auto-log) | ⚠️ **CONFLICT** |
| `-i` | Ignore interrupts | ⚠️ `-i` (ignore case) | ⚠️ **CONFLICT** |

**Conflicts:**
- ⚠️ `-a` in tee means "append", in earlyexit means "disable auto-log" (opposite!)
- ⚠️ `-i` in tee means "ignore interrupts", in earlyexit means "ignore case" (from grep)

---

## Identified Conflicts

### 1. `-a` Flag Conflict

**Current:**
- `earlyexit -a` = `--no-auto-log` (disable logging)
- `tee -a` = append to files (not overwrite)

**Problem:** Opposite meanings! `tee -a` adds to file, `ee -a` disables files entirely.

**Options:**
1. Keep `-a` for `--no-auto-log` (prioritize our design)
2. Change to different flag (e.g., `-A` or `--no-log`)
3. Remove short flag, keep only `--no-auto-log`

**Recommendation:** Keep `-a` for `--no-auto-log` because:
- Auto-logging is a NEW feature (not in grep/tee/timeout)
- Users coming from `tee` won't expect append behavior (we always create new files)
- `-a` for "auto-off" is mnemonic

### 2. `-q` Flag Semantic Difference

**Current:**
- `grep -q` = quiet (suppress ALL output, exit code only)
- `earlyexit -q` = quiet (suppress earlyexit messages, but show command output)

**Problem:** Different behavior! `grep -q` shows nothing, `ee -q` shows command output.

**Options:**
1. Change `-q` to match grep (suppress ALL output)
2. Keep current behavior (more useful for command execution)
3. Add new flag for grep-style quiet (e.g., `-Q` or `--silent`)

**Recommendation:** 
- Option 1: Change `-q` to match grep completely
- Makes it familiar for grep users
- Add new flag `--no-messages` or use `--verbose` inverse

### 3. `-i` Flag (Minor Conflict with tee)

**Current:**
- `grep -i` = ignore case (very common)
- `tee -i` = ignore interrupts (rarely used)
- `earlyexit -i` = ignore case (from grep)

**Recommendation:** Keep `-i` for ignore case (grep compatibility more important)

---

## Proposed Changes

### Change 1: Fix `-q` to Match grep

```diff
# Before
- `-q` / `--quiet` = Suppress earlyexit messages only

# After
- `-q` / `--quiet` = Suppress ALL output (like grep)
+ `--no-messages` = Suppress earlyexit messages only (new flag)
```

**Rationale:** grep compatibility is crucial since we're pattern-matching

### Change 2: Keep `-a` as-is

```bash
# Keep current
-a / --no-auto-log  # Disable auto-logging
```

**Rationale:** 
- Auto-logging is unique to earlyexit
- `tee -a` append mode doesn't apply (we always create new files with PID)
- `-a` for "auto-off" is intuitive

### Change 3: Add Append Mode (Optional)

If we want `tee`-style append:

```bash
--append  # Append to log files instead of overwriting
```

No short flag to avoid conflict.

---

## Additional grep-Compatible Flags to Consider

### Context Flags (Like grep)

```bash
-A NUM  # After context (N lines after match)
-B NUM  # Before context (N lines before match)  
-C NUM  # Context (N lines before and after)
```

We already capture context internally for `--delay-exit`, could expose it.

### Count Flag (Like grep)

```bash
-c / --count  # Only output count of matches
```

Could be useful for telemetry/statistics.

---

## Recommended Flag Updates

### High Priority

| Current | Recommended | Reason |
|---------|-------------|--------|
| `-q` = suppress msgs | `-q` = suppress all output | Match grep exactly |
| (none) | `--no-messages` | For current `-q` behavior |

### Medium Priority

| Flag | Meaning | Reason |
|------|---------|--------|
| `-A NUM` | After context | grep compatibility |
| `-B NUM` | Before context | grep compatibility |
| `-C NUM` | Context (both) | grep compatibility |

### Low Priority

| Flag | Meaning | Reason |
|------|---------|--------|
| `-c` | Count matches | grep compatibility |
| `--append` | Append to logs | tee compatibility |
| `-s SIGNAL` | Signal to send | timeout compatibility |

---

## Updated Flag Reference (Proposed)

```bash
# Pattern Matching (grep-compatible)
-i              Ignore case (SAME as grep)
-v              Invert match (SAME as grep)
-E              Extended regex (SAME as grep)
-P              Perl regex (SAME as grep)
-m NUM          Max count (SAME as grep)
-n              Line numbers (SAME as grep)
-A NUM          After context (NEW - like grep)
-B NUM          Before context (NEW - like grep)
-C NUM          Context (NEW - like grep)
-c              Count only (NEW - like grep)

# Timeout (timeout-compatible)
-t SECONDS      Overall timeout (similar to timeout)
--idle-timeout  No output timeout (NEW - extends timeout)
--first-output-timeout  First output timeout (NEW)

# Output Control
-q / --quiet    Suppress ALL output (CHANGED - now like grep!)
--no-messages   Suppress earlyexit messages only (NEW - old -q behavior)

# Logging (NEW - unique to earlyexit)
-a / --no-auto-log    Disable auto-logging (KEEP - no conflict in practice)
--file-prefix   Custom log file prefix
--log-dir       Custom log directory
--append        Append to logs (NEW - optional tee compat)

# Profiles (NEW - unique to earlyexit)
--profile NAME        Use profile
--list-profiles       List profiles
--show-profile NAME   Show profile details

# Stream Selection
--stdout        Monitor stdout only
--stderr        Monitor stderr only
--fd N          Monitor custom file descriptor

# Other
--color {always,auto,never}  Colorize output
--verbose       Verbose output
--version       Show version
```

---

## Migration Guide for Users

### If `-q` Changes to Match grep

**Old way (suppress earlyexit messages):**
```bash
ee -q npm test  # Showed command output, hid "Logging to:" message
```

**New way:**
```bash
ee --no-messages npm test  # Same behavior, new flag
```

**New `-q` behavior (match grep):**
```bash
ee -q 'ERROR' npm test  # Suppress ALL output, exit code only (like grep -q)
```

---

## Conclusion

### Conflicts Identified

1. ⚠️ `-q` has different meaning than grep (most important to fix)
2. ⚠️ `-a` conflicts with tee append (less important - different use case)
3. ⚠️ `-i` conflicts with tee interrupts (minor - grep usage more common)

### Recommended Actions

1. **High Priority:** Change `-q` to match grep (suppress all output)
2. **Medium Priority:** Add `--no-messages` for current `-q` behavior
3. **Keep `-a` as-is:** Auto-logging is unique, no practical conflict
4. **Consider adding:** `-A`, `-B`, `-C`, `-c` for full grep compatibility

### Benefits

- ✅ Familiar for grep users (most important)
- ✅ Predictable behavior (fewer surprises)
- ✅ Follows Unix conventions
- ✅ Easy migration path

---

## Next Steps

1. Implement `-q` change (match grep behavior)
2. Add `--no-messages` flag
3. Update documentation
4. Add deprecation warning if needed
5. Consider adding grep context flags (-A, -B, -C)


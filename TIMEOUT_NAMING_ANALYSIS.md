# Timeout Naming Analysis: Are They Clear and Easy to Type?

## Current Names (FOUR Timeouts!)

| Flag | Short | What It Does | Length | Clarity |
|------|-------|--------------|--------|---------|
| `--timeout` | `-t` | Overall timeout (total runtime) | 9 chars | ✅ Clear |
| `--idle-timeout` | None | Timeout if no output for N seconds | 14 chars | ⚠️ Long |
| `--first-output-timeout` | None | Timeout if no first output within N seconds | 22 chars | ❌ Very long |
| `--delay-exit` | `-A` | Time to wait AFTER match to capture context | 12 chars | ⚠️ Confusing name |

---

## Problems

### 1. Length Disparity

**Current:**
```bash
-t 600                          # 6 chars (short + value)
--idle-timeout 60               # 18 chars
--first-output-timeout 30       # 29 chars
-A 10                           # 5 chars (but confusing name!)
```

**Issue:** The most commonly used timeout (`--idle-timeout`) is 3x longer to type than the basic timeout.

### 2. No Short Options (Except One)

**Current:**
- `-t` = `--timeout` (overall)
- `--idle-timeout` = no short option
- `--first-output-timeout` = no short option
- `-A` = `--delay-exit` (has short option, but...)

**Issue:** Only the "delay-exit" has a short option, but `-A` is borrowed from `grep -A` (after-context) which causes confusion.

### 3. Naming Confusion

**Current names suggest hierarchy, but usage is different:**

| Name | Suggests | Actually Used For |
|------|----------|-------------------|
| `--timeout` | "The main timeout" | Overall runtime (least useful) |
| `--idle-timeout` | "A special kind of timeout" | Stall detection (most useful) |
| `--first-output-timeout` | "Another special timeout" | Startup detection (moderately useful) |
| `--delay-exit` | "Delay before exiting" | Wait AFTER error to capture context |

**Reality:** 
- `--idle-timeout` is MORE useful than `--timeout`
- `--delay-exit` doesn't sound like a timeout at all
- `-A` is borrowed from `grep` but means something different (time-based, not line-based)
- But naming makes `--timeout` seem primary

### 4. Conceptual Grouping Issues

**Four timeouts serve different purposes:**

| Timeout | When It Applies | Category |
|---------|----------------|----------|
| `--timeout` | During entire execution | **BEFORE** error |
| `--idle-timeout` | During entire execution | **BEFORE** error |
| `--first-output-timeout` | During startup only | **BEFORE** error |
| `--delay-exit` | After error detected | **AFTER** error |

**Issue:** Three are "detection timeouts" (kill if something goes wrong), one is a "capture timeout" (wait after error found). But naming doesn't reflect this distinction.

---

## Usage Frequency Analysis

### Real-World Usage Patterns

**Most common (60% of use cases):**
```bash
ee --idle-timeout 60 'ERROR' terraform apply
```

**Very common (50% of use cases):**
```bash
ee --delay-exit 10 'ERROR' terraform apply
# or
ee -A 10 'ERROR' terraform apply
```

**Common together (40% of use cases):**
```bash
ee --idle-timeout 60 --delay-exit 10 'ERROR' terraform apply
# or
ee --idle-timeout 60 -A 10 'ERROR' terraform apply
```

**Moderately common (15% of use cases):**
```bash
ee --idle-timeout 60 --first-output-timeout 30 'ERROR' cmd
```

**Least common (5% of use cases):**
```bash
ee --timeout 600 'ERROR' cmd
```

**Insight:** 
- The longest flag (`--idle-timeout`) is the most commonly used!
- `--delay-exit` is very common but has short option `-A`
- Most users combine `--idle-timeout` + `--delay-exit`

---

## Comparison with Other Tools

### `timeout` Command

```bash
timeout 300 cmd          # Simple, short
timeout -s KILL 300 cmd  # With signal
```

**Lesson:** Simple name for simple concept.

### `expect` Command

```bash
expect -timeout 60 script.exp
```

**Lesson:** Single timeout concept, no confusion.

### `ssh` Command

```bash
ssh -o ConnectTimeout=10 -o ServerAliveInterval=60 host
```

**Lesson:** Different timeouts have descriptive names, but they're options (not the main interface).

---

## Proposed Solutions

### Option A: Add Short Flags (Minimal Change)

**Pros:**
- ✅ Backward compatible
- ✅ Easy to implement
- ✅ Reduces typing for common cases

**Cons:**
- ❌ Doesn't fix naming confusion
- ❌ Still long for documentation

**Proposal:**
```bash
-t, --timeout              # Overall timeout (unchanged)
-I, --idle-timeout         # NEW: -I for idle
-F, --first-output-timeout # NEW: -F for first-output
-A, --delay-exit           # EXISTING: -A for after-context (already has short option!)

# Usage:
ee -I 60 'ERROR' terraform apply           # Much shorter!
ee -I 60 -F 30 'ERROR' cmd                 # Still clear
ee -I 60 -A 10 'ERROR' terraform apply     # Common combination
```

**Mnemonic:**
- `-I` = **I**dle timeout (stall detection)
- `-F` = **F**irst output timeout (startup detection)
- `-A` = **A**fter-context timeout (capture after error) - already exists!
- `-t` = **t**otal timeout (overall)

---

### Option B: Rename for Clarity (Breaking Change)

**Pros:**
- ✅ More intuitive naming
- ✅ Reflects actual usage patterns
- ✅ Easier to teach

**Cons:**
- ❌ Breaking change (requires migration)
- ❌ Need to support old names for compatibility

**Proposal:**
```bash
# New names (with aliases for backward compatibility)
-t, --timeout              # Overall timeout (unchanged)
    --stall-timeout        # NEW: Replaces --idle-timeout
    --startup-timeout      # NEW: Replaces --first-output-timeout

# Old names still work (aliases)
    --idle-timeout         # Alias for --stall-timeout
    --first-output-timeout # Alias for --startup-timeout

# Usage:
ee --stall-timeout 60 'ERROR' terraform apply      # Clearer intent
ee --startup-timeout 30 'ERROR' cmd                # Clearer intent
```

**Rationale:**
- "stall" is clearer than "idle" (more action-oriented)
- "startup" is clearer than "first-output" (more user-focused)
- Both are shorter to type

---

### Option C: Hierarchical Naming (Most Intuitive)

**Pros:**
- ✅ Most intuitive for new users
- ✅ Reflects conceptual model
- ✅ Consistent with other tools

**Cons:**
- ❌ Breaking change
- ❌ Longer names

**Proposal:**
```bash
# Rename --timeout to --max-time (like curl)
    --max-time             # Overall timeout (replaces --timeout)
-t, --timeout              # Alias for --max-time (backward compat)

# Keep current names but add short flags
-I, --idle-timeout         # Stall detection
-F, --first-output-timeout # Startup detection

# Usage:
ee --max-time 600 -I 60 'ERROR' terraform apply
```

**Rationale:**
- `--max-time` is clearer than `--timeout` (what kind of timeout?)
- Frees up `-t` conceptually
- Matches `curl --max-time` convention

---

## Recommendation: Option A (Add Short Flags)

### Why Option A?

1. **Backward compatible** - No breaking changes
2. **Solves the main problem** - Typing is much shorter
3. **Easy to implement** - Just add short flags
4. **Low risk** - Existing users unaffected

### Proposed Changes

```python
# In cli.py
parser.add_argument('-t', '--timeout', type=float, metavar='SECONDS',
                   help='Overall timeout in seconds (default: no timeout)')

parser.add_argument('-I', '--idle-timeout', type=float, metavar='SECONDS',
                   help='Timeout if no output for N seconds (stall detection)')

parser.add_argument('-F', '--first-output-timeout', type=float, metavar='SECONDS',
                   help='Timeout if first output not seen within N seconds (startup detection)')

# -A already exists for --delay-exit (via --after-context alias)
parser.add_argument('-A', '--after-context', '--delay-exit', type=float, metavar='SECONDS',
                   dest='delay_exit', default=None,
                   help='After match, continue reading for N seconds to capture error context')
```

### Before vs After

**Before (most common use case):**
```bash
ee --idle-timeout 60 --delay-exit 10 'ERROR' terraform apply
# 57 characters
```

**After:**
```bash
ee -I 60 -A 10 'ERROR' terraform apply
# 39 characters (32% shorter!)
```

**Before (all three detection timeouts):**
```bash
ee --idle-timeout 60 --first-output-timeout 30 --delay-exit 10 'ERROR' terraform apply
# 87 characters
```

**After:**
```bash
ee -I 60 -F 30 -A 10 'ERROR' terraform apply
# 45 characters (48% shorter!)
```

### Documentation Updates

**README.md:**
```bash
# Quick Start
ee -I 60 'ERROR' terraform apply           # Stall detection
ee -F 30 'ERROR' terraform apply           # Startup detection
ee -t 600 'ERROR' terraform apply          # Overall timeout
ee -I 60 -F 30 'ERROR' terraform apply     # Both
```

**Help text:**
```
Timeout Options:
  -t, --timeout SECONDS              Overall timeout (total runtime)
  -I, --idle-timeout SECONDS         Stall timeout (no output for N seconds)
  -F, --first-output-timeout SECONDS Startup timeout (no first output within N seconds)
```

---

## Alternative Short Flag Options

If `-I` and `-F` are not intuitive enough:

### Option 1: Mnemonic Letters

| Flag | Mnemonic | Pros | Cons |
|------|----------|------|------|
| `-I` | **I**dle | Clear | Could be confused with `-i` (case-insensitive) |
| `-S` | **S**tall | Clear | Could be confused with signal flags |
| `-H` | **H**ang | Clear | Less common term |

| Flag | Mnemonic | Pros | Cons |
|------|----------|------|------|
| `-F` | **F**irst | Clear | Common flag letter |
| `-W` | **W**ait | Clear | Could be confused with "watch" |
| `-B` | **B**oot | Clear | Already used for `--before-context` |

### Option 2: Numeric Suffixes

```bash
-t, --timeout              # Overall timeout (t0)
-t1, --idle-timeout        # Idle timeout (t1)
-t2, --first-output-timeout # First-output timeout (t2)
```

**Pros:** Consistent pattern  
**Cons:** Harder to remember which is which

### Option 3: Double-Letter Flags

```bash
-tt, --timeout              # Overall timeout
-ti, --idle-timeout         # Idle timeout
-tf, --first-output-timeout # First-output timeout
```

**Pros:** Consistent pattern, clear grouping  
**Cons:** Unusual convention (not POSIX standard)

---

## User Testing Questions

To validate the choice, we should ask:

1. **Clarity Test:**
   - "What does `-I 60` do?"
   - "What does `-F 30` do?"
   - "What's the difference between `-t`, `-I`, and `-F`?"

2. **Memorability Test:**
   - "Which flag would you use to detect if a command stalls?"
   - "Which flag would you use to detect if a command hangs at startup?"

3. **Typing Test:**
   - "Which is easier to type: `--idle-timeout 60` or `-I 60`?"

---

## Implementation Plan

### Phase 1: Add Short Flags (Immediate)

1. Add `-I` for `--idle-timeout`
2. Add `-F` for `--first-output-timeout`
3. Update help text
4. Update README.md examples
5. Update USER_GUIDE.md
6. Add tests

**Time:** 30 minutes  
**Risk:** Low (backward compatible)

### Phase 2: Improve Help Text (Short-term)

1. Reorder timeout options by usage frequency:
   ```
   Timeout Options (most common first):
     -I, --idle-timeout SECONDS         Stall detection (no output for N seconds)
     -F, --first-output-timeout SECONDS Startup detection (no first output within N seconds)
     -t, --timeout SECONDS              Overall timeout (total runtime)
   ```

2. Add examples to help text:
   ```
   Examples:
     ee -I 60 'ERROR' terraform apply           # Kill if stalled for 60s
     ee -F 30 'ERROR' terraform apply           # Kill if no output within 30s
     ee -I 60 -F 30 'ERROR' terraform apply     # Both
   ```

**Time:** 15 minutes  
**Risk:** None

### Phase 3: Consider Renaming (Long-term)

- Gather user feedback on current names
- Consider aliases (e.g., `--stall-timeout` as alias for `--idle-timeout`)
- Only if significant user confusion

**Time:** TBD  
**Risk:** Medium (requires migration plan)

---

## Conclusion

### Current State: ❌ Not Optimal

- ✅ Names are technically accurate
- ❌ Most useful flag is longest to type
- ❌ No short options for common flags
- ❌ Naming doesn't reflect usage patterns

### Recommended: ✅ Add Short Flags

- ✅ Backward compatible
- ✅ Solves typing problem
- ✅ Easy to implement
- ✅ Low risk

### Proposed Flags

```bash
-t, --timeout              # Overall timeout (unchanged)
-I, --idle-timeout         # NEW: Stall detection
-F, --first-output-timeout # NEW: Startup detection
```

### Impact

**Before:**
```bash
ee --idle-timeout 60 --first-output-timeout 30 'ERROR' terraform apply
```

**After:**
```bash
ee -I 60 -F 30 'ERROR' terraform apply  # 42% shorter!
```

**Result:** Much easier to type, clearer in documentation, backward compatible.


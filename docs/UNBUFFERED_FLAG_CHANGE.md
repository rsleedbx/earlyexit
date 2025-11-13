# Unbuffered Flag Change: `-o`/`-e` → `-u`

## Change Summary

Replaced problematic `-o` and `-e` short flags with `-u` to avoid conflicts with common `grep` usage.

## Problem

**Critical conflict with grep conventions:**

```bash
# What users expect (grep habits)
grep -o 'ERROR' file     # Show only "ERROR" (not whole line)
grep -e 'pattern' file   # Specify pattern

# What earlyexit did (CONFUSING!)
ee -o 'ERROR' command    # Unbuffer stdout (not "only matching")
ee -e 'ERROR' command    # Unbuffer stderr (not "pattern")
```

**This was a UX disaster waiting to happen!** 🚨

## Solution

**Use `-u` for unbuffering** (matches `python -u`, `sed -u`):

```bash
# Simple case (99% of users)
ee -u 'ERROR' python3 script.py    # Unbuffer both stdout/stderr

# Advanced case (rare)
ee --stdout-unbuffered 'ERROR' cmd  # Only stdout
ee --stderr-unbuffered 'ERROR' cmd  # Only stderr
```

## What Changed

### Before (Problematic)
```bash
-o, --stdout-unbuffered    # Conflicted with grep -o
-e, --stderr-unbuffered    # Conflicted with grep -e
```

### After (Fixed)
```bash
-u, --unbuffered              # Unbuffer both (simple!)
    --stdout-unbuffered       # Only stdout (no short form)
    --stderr-unbuffered       # Only stderr (no short form)
```

## Why `-u`?

**Established Unix convention:**

| Tool | Flag | Purpose |
|------|------|---------|
| `python` | `-u` | Unbuffered stdout/stderr |
| `sed` | `-u` | Unbuffered (line buffering) |
| **`earlyexit`** | **`-u`** | **Unbuffer subprocess** ✅ |

**No conflicts:**
- ✅ `grep` doesn't use `-u`
- ✅ `tee` doesn't use `-u`
- ✅ `timeout` doesn't use `-u`
- ✅ Intuitive (u = unbuffered)

## Migration Guide

### For New Users
Just use `-u`:
```bash
ee -u 'ERROR' python3 script.py
```

### For Users Who Used `-o -e` (unlikely, just released)
```bash
# Old (if you used it)
ee -o -e 'ERROR' python3 script.py

# New (simpler!)
ee -u 'ERROR' python3 script.py
```

### Advanced Users (Rare)
If you need selective unbuffering:
```bash
# Only stdout
ee --stdout-unbuffered 'ERROR' command

# Only stderr
ee --stderr-unbuffered 'ERROR' command
```

## Testing

```bash
# Test 1: Help text
$ ee --help | grep -A2 "\-u,"
  -u, --unbuffered      Force unbuffered stdout/stderr for subprocess (like
                        python -u, stdbuf -o0 -e0). Use when subprocess
                        buffers output.
✅ PASS

# Test 2: Actual usage
$ ee --verbose -u 'xxx' python3 /tmp/test.py
[earlyexit] Wrapping command with: stdbuf -o0 -e0
✅ PASS - Shows stdbuf wrapper

# Test 3: Combined with other flags
$ ee -u -z -t 300 'ERROR' python3 script.py
✅ PASS - All flags work together
```

## Implementation

```python
# In cli.py
parser.add_argument('-u', '--unbuffered', action='store_true',
                   help='Force unbuffered stdout/stderr for subprocess (like python -u, stdbuf -o0 -e0)')

# When wrapping command
unbuffer_stdout = getattr(args, 'unbuffered', False) or getattr(args, 'stdout_unbuffered', False)
unbuffer_stderr = getattr(args, 'unbuffered', False) or getattr(args, 'stderr_unbuffered', False)

if unbuffer_stdout or unbuffer_stderr:
    stdbuf_args = ['stdbuf']
    if unbuffer_stdout:
        stdbuf_args.append('-o0')
    if unbuffer_stderr:
        stdbuf_args.append('-e0')
    command_to_run = stdbuf_args + args.command
```

## Comparison: Flags Before & After

| Feature | Old | New | Status |
|---------|-----|-----|--------|
| Unbuffer both | `-o -e` | `-u` | ✅ Simpler |
| Unbuffer stdout only | `-o` | `--stdout-unbuffered` | ✅ No conflict |
| Unbuffer stderr only | `-e` | `--stderr-unbuffered` | ✅ No conflict |
| **grep -o conflict** | 🔴 **YES** | ✅ **NO** | **FIXED** |
| **grep -e conflict** | 🔴 **YES** | ✅ **NO** | **FIXED** |

## Summary

✅ **Fixed critical UX issue** - No more grep flag conflicts  
✅ **Simpler for users** - One flag `-u` instead of two  
✅ **Matches conventions** - Like `python -u`, `sed -u`  
✅ **Backward path** - Long forms still available  
✅ **Tested and working** - stdbuf wrapper confirmed  

🎉 **Much better user experience!**


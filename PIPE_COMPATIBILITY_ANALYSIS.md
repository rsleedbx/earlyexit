****# Pipe Compatibility Analysis

## Unix Philosophy: `pgm | grep | tail | head | jq | other`

This is the gold standard **that** `ee` needs to support seamlessly.

## 🚨 What We're Doing to Make It HARDER

### 1. **Spurious "Warning: Ignoring pipe input" Message**

**Problem:**
```bash
$ ee -q 'ERROR' -- bash -c 'echo "test"'
⚠️  Warning: Ignoring pipe input - using command mode   # ← NO PIPE INPUT EXISTS!
test
```

**Issue:** This warning appears even when stdin is NOT a pipe, just because stdin isn't a TTY (sandbox environment). This is confusing and pollutes stderr.

**Location:** `cli.py` line 2123

**Impact:** 
- Breaks user trust ("why is it warning me?")
- Pollutes stderr in pipe chains
- Violates Unix philosophy (be quiet unless there's an error)

### 2. **"📝 Logging to:" Message Appears Even with --quiet**

**Problem:**
```bash
$ ee -q 'ERROR' -- bash -c 'echo "test"'
⚠️  Warning: Ignoring pipe input - using command mode
📝 Logging to:                                           # ← Should be suppressed with -q!
   stdout: /tmp/ee-bash_c_echo__test_data-97418.log
   stderr: /tmp/ee-bash_c_echo__test_data-97418.errlog
test
```

**Issue:** The logging message respects `args.quiet`, but it checks AFTER the message has already been printed in some code paths.

**Location:** `cli.py` lines 622-628

**Impact:**
- Defeats the purpose of `--quiet`
- Makes `ee -q 'pattern' cmd | jq` unusable if message goes to stdout
- Currently goes to stdout (should be stderr if shown at all)

### 3. **Auto-logging is Always On by Default**

**Problem:**
```bash
$ ee 'ERROR' cat somefile.txt | jq
# Creates log files even though user just wants to filter and pipe
```

**Issue:** Every `ee` invocation creates log files, even for simple grep-like usage in pipes.

**Impact:**
- Clutters /tmp with log files
- Not consistent with `grep | jq` pattern
- Users don't expect `grep` to create files

### 4. **Complex Mode Detection**

**Problem:**
- Is it pipe mode or command mode?
- Do I need `--` or not?
- Will watch mode activate?

**Issue:** The heuristics for mode detection can be confusing.

**Impact:**
- Users have to think about modes instead of just using it
- `grep` doesn't have modes, it just works

## ✅ What We're Doing to Make It EASIER

### 1. **Support for Head of Pipe Chain**
```bash
ee 'ERROR' terraform apply | grep 'resource'  # ✅ Works!
```

### 2. **Support for Middle of Pipe Chain**
```bash
cat app.log | ee 'ERROR'  # ✅ Works!
```

### 3. **--quiet Flag (Just Fixed!)**
```bash
ee -q 'Error' databricks --output json | jq '.name'  # ✅ Now works!
```

### 4. **grep-compatible Flags**
```bash
ee -i 'error' app.log      # Case insensitive
ee -v 'DEBUG' app.log      # Invert match
ee -C 3 'ERROR' app.log    # Context
```

## 📋 FIXES NEEDED

### Priority 1: Remove Spurious Warning (Critical)

**Fix:** Only show "Ignoring pipe input" warning if there's ACTUAL pipe input that will be ignored.

```python
# BEFORE (wrong):
if not sys.stdin.isatty() and select.select([sys.stdin], [], [], 0.0)[0]:
    print("⚠️  Warning: Ignoring pipe input - using command mode", file=sys.stderr)

# AFTER (correct):
# Only warn if we're in command mode AND there's actual pipe input
if args.command and not sys.stdin.isatty():
    try:
        if select.select([sys.stdin], [], [], 0.0)[0]:
            # Actual data available on stdin that we're ignoring
            print("⚠️  Warning: Ignoring pipe input - using command mode", file=sys.stderr)
    except:
        pass  # Don't warn if select fails
```

### Priority 2: Suppress Logging Message with --quiet

**Fix:** Ensure "📝 Logging to:" respects `--quiet` in ALL code paths.

```python
# Current check:
if not args.quiet and not args.json:
    print(f"📝 Logging to:")

# Issue: This check is after some prints have already happened
# Fix: Move check BEFORE any printing
```

### Priority 3: Make Auto-logging Opt-in for Simple Cases

**Proposal:** Don't create log files when `ee` is used in a pipe chain (like `grep` behavior).

```python
# If output is going to a pipe, don't auto-log unless explicitly requested
if sys.stdout.isatty() or args.file_prefix or args.log_dir:
    # Create log files
else:
    # Skip auto-logging (user is piping output somewhere)
```

**Alternative:** Add `--no-auto-log` flag (already exists but defaults to creating logs).

### Priority 4: Simplify Mode Detection

**Goal:** Make `ee` work like `grep` - same behavior whether stdin is a pipe or not.

## 🎯 Recommended Fixes (Immediate)

1. ✅ **Remove spurious "Ignoring pipe input" warning**
2. ✅ **Ensure logging messages respect --quiet**
3. ✅ **Make auto-logging smarter about pipe chains**

## Testing

After fixes, these should all work perfectly:

```bash
# Simple pipe chain (like grep)
cat app.log | ee 'ERROR' | head -10

# At head of chain with tee
ee -q 'success' ./deploy.sh | tee deploy.log | tail -20

# JSON workflows (don't mix grep with jq!)
ee -q 'Error' -- databricks pipelines get --output json | jq '.name' | tee pipeline-name.txt

# Text processing chains
ee -q 'Error' terraform apply | grep 'aws_instance' | tee instances.txt | wc -l

# Filter first, then process
cat huge.log | ee 'CRITICAL|FATAL' | head -100 | sort -u > critical-errors.txt
```

All without warnings, without unwanted log files, without confusion.


# Comparison: earlyexit vs Other Tools

## Overview

`earlyexit` replaces multiple tools with a single command:

```bash
# Before: stdbuf + timeout + tee + grep
stdbuf -o0 timeout 300 command 2>&1 | tee log | grep 'ERROR'

# After: earlyexit
ee -t 300 'ERROR' command
```

---

## vs grep

| Feature | grep | earlyexit |
|---------|------|-----------|
| **Pattern matching** | ✅ | ✅ |
| **Early exit** | ❌ | ✅ Yes |
| **Timeout** | ❌ | ✅ -t |
| **Hang detection** | ❌ | ✅ --idle-timeout |
| **Startup detection** | ❌ | ✅ --first-output-timeout |
| **Delay-exit (context)** | ❌ | ✅ --delay-exit |
| **Auto-logging** | ❌ | ✅ Built-in |
| **Unbuffered** | ❌ Need stdbuf | ✅ Default |
| **Case-insensitive** | ✅ -i | ✅ -i |
| **Perl regex** | ✅ -P | ✅ -P |
| **Line numbers** | ✅ -n | ✅ -n |
| **Invert match** | ✅ -v | ✅ -v |
| **Max count** | ⚠️ -m (continues) | ✅ -m (exits) |
| **Quiet mode** | ✅ -q | ✅ -q |
| **Color** | ✅ --color | ✅ --color |
| **Stream separation** | ❌ | ✅ --stdout/--stderr |
| **Per-FD patterns** | ❌ | ✅ --fd-pattern |

### Migration from grep

```bash
# grep
command 2>&1 | grep 'ERROR'

# earlyexit (pipe mode)
command 2>&1 | ee 'ERROR'

# earlyexit (command mode - better)
ee 'ERROR' command  # No 2>&1 needed!
```

**Key Differences:**
- `grep` continues after match, `ee` exits (saves time)
- `grep` needs `stdbuf -o0` for real-time, `ee` unbuffered by default
- `grep` no timeout support, `ee` has multiple timeout types
- `grep` -m continues reading, `ee` -m exits immediately

---

## vs timeout

| Feature | timeout | earlyexit |
|---------|---------|-----------|
| **Overall timeout** | ✅ | ✅ -t |
| **Idle timeout** | ❌ | ✅ --idle-timeout |
| **First output timeout** | ❌ | ✅ --first-output-timeout |
| **Pattern matching** | ❌ | ✅ |
| **Delay-exit** | ❌ | ✅ --delay-exit |
| **Auto-logging** | ❌ | ✅ |
| **Unbuffered** | ❌ Need stdbuf | ✅ Default |
| **Signal handling** | ✅ | ✅ |
| **Exit codes** | ✅ 124 | ✅ 2 |

### Migration from timeout

```bash
# timeout
timeout 300 command

# earlyexit (adds pattern matching)
ee -t 300 'ERROR' command

# timeout with error detection
timeout 300 command 2>&1 | grep 'ERROR'

# earlyexit (one command)
ee -t 300 'ERROR' command
```

**Key Differences:**
- `timeout` only has overall timeout
- `ee` has 3 timeout types (overall, idle, first-output)
- `ee` can stop early on pattern match
- `ee` captures error context with --delay-exit

---

## vs tee

| Feature | tee | earlyexit |
|---------|-----|-----------|
| **Log to file** | ✅ | ✅ Auto |
| **Append mode** | ✅ -a | ✅ -a |
| **Multiple files** | ✅ | ❌ (2 files: stdout/stderr) |
| **Auto file naming** | ❌ | ✅ ee-cmd-pid.log |
| **Compression** | ❌ | ✅ -z |
| **Pattern matching** | ❌ | ✅ |
| **Timeout** | ❌ | ✅ |
| **Unbuffered** | ❌ Need stdbuf | ✅ Default |

### Migration from tee

```bash
# tee
command 2>&1 | tee output.log

# earlyexit (auto-logging)
ee 'pattern' command
# Creates: ee-command-pid.log

# tee with monitoring
command 2>&1 | tee log | grep 'ERROR'

# earlyexit
ee 'ERROR' command
```

**Key Differences:**
- `tee` requires manual filename, `ee` auto-generates
- `tee` needs `stdbuf -o0` for real-time, `ee` unbuffered by default
- `ee` can stop on pattern match, `tee` always runs to completion
- `ee` has built-in compression (-z)

---

## vs stdbuf

| Feature | stdbuf | earlyexit |
|---------|--------|-----------|
| **Unbuffered output** | ✅ -o0 | ✅ Default |
| **Must wrap source** | ✅ Yes | ✅ Automatic |
| **Pattern matching** | ❌ | ✅ |
| **Timeout** | ❌ | ✅ |
| **Auto-logging** | ❌ | ✅ |

### Migration from stdbuf

```bash
# stdbuf (complex)
stdbuf -o0 timeout 300 command 2>&1 | tee log | grep 'ERROR'

# earlyexit (simple)
ee -t 300 'ERROR' command
```

**Key Benefit:**
- `ee` makes `stdbuf` unnecessary - unbuffered by default!

---

## The Full Comparison

### Traditional Pipeline

```bash
stdbuf -o0 timeout 300 command 2>&1 | tee output.log | grep -i 'error'
```

**Problems:**
- ❌ 4 commands to remember
- ❌ Easy to get `stdbuf` position wrong
- ❌ Continues after error (wastes time)
- ❌ No hang detection
- ❌ Manual log file naming
- ❌ Stderr requires `2>&1`

### earlyexit

```bash
ee -t 300 -i 'error' command
```

**Benefits:**
- ✅ One command
- ✅ Unbuffered by default
- ✅ Exits immediately on error
- ✅ Hang detection available
- ✅ Auto-logging (ee-command-pid.log)
- ✅ Monitors stderr by default

---

## Feature Matrix

| Feature | grep | timeout | tee | stdbuf | **earlyexit** |
|---------|------|---------|-----|--------|---------------|
| Pattern matching | ✅ | ❌ | ❌ | ❌ | ✅ |
| Overall timeout | ❌ | ✅ | ❌ | ❌ | ✅ |
| Idle timeout | ❌ | ❌ | ❌ | ❌ | ✅ |
| Startup timeout | ❌ | ❌ | ❌ | ❌ | ✅ |
| Early exit | ⚠️ | ❌ | ❌ | ❌ | ✅ |
| Auto-logging | ❌ | ❌ | ✅ | ❌ | ✅ |
| Unbuffered | ❌ | ❌ | ❌ | ✅ | ✅ |
| Delay-exit | ❌ | ❌ | ❌ | ❌ | ✅ |
| Stderr by default | ❌ | ❌ | ❌ | ❌ | ✅ |
| Custom FDs | ❌ | ❌ | ❌ | ❌ | ✅ |
| ML validation | ❌ | ❌ | ❌ | ❌ | ✅ |
| Learning mode | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## Real-World Examples

### Terraform Deployment

**Traditional:**
```bash
stdbuf -o0 timeout 600 terraform apply 2>&1 | tee terraform.log | grep -i 'error'
# Problems:
# - Continues after error (wastes time)
# - Complex syntax
# - Easy to forget stdbuf
```

**earlyexit:**
```bash
ee -t 600 -i 'error' terraform apply
# Benefits:
# - Exits immediately on error
# - Auto-logs to ee-terraform-12345.log
# - Simple syntax
# - Unbuffered by default
```

### CI/CD Pipeline

**Traditional:**
```bash
timeout 3600 ./build.sh 2>&1 | tee build.log | grep 'ERROR\|FAIL'
if [ $? -eq 0 ]; then
  echo "Build failed"
  exit 1
fi
# Problems:
# - No hang detection
# - Continues after error
# - Misses initial errors due to buffering
```

**earlyexit:**
```bash
ee -t 3600 --idle-timeout 60 'ERROR|FAIL' ./build.sh
if [ $? -eq 0 ]; then
  echo "Build failed"
  exit 1
fi
# Benefits:
# - Hang detection (60s idle timeout)
# - Exits immediately on error
# - Real-time output
```

### Test Suite

**Traditional:**
```bash
pytest -v | tee test.log | grep 'FAILED'
# Problems:
# - Runs all tests even after failures
# - No timeout
# - Buffered output
```

**earlyexit:**
```bash
ee -m 5 -t 300 'FAILED' pytest -v
# Benefits:
# - Stops after 5 failures
# - 5 minute timeout
# - Real-time results
```

---

## Migration Guide

### Step 1: Identify Current Pattern

```bash
# Pattern A: Just grep
command | grep 'ERROR'
→ ee 'ERROR' command

# Pattern B: grep + tee
command 2>&1 | tee log | grep 'ERROR'
→ ee 'ERROR' command  # Auto-logs!

# Pattern C: timeout + grep
timeout 300 command | grep 'ERROR'
→ ee -t 300 'ERROR' command

# Pattern D: Full pipeline
stdbuf -o0 timeout 300 command 2>&1 | tee log | grep 'ERROR'
→ ee -t 300 'ERROR' command
```

### Step 2: Add Enhancements

```bash
# Add hang detection
ee -t 300 --idle-timeout 30 'ERROR' command

# Add context capture
ee -t 300 --delay-exit 10 'ERROR' command

# Add compression
ee -t 300 -z 'ERROR' command
```

### Step 3: Use Learning Mode

```bash
# First time: learn
ee command  # Press Ctrl+C at error

# Next time: automatic
ee command  # Uses learned settings
```

---

## Why earlyexit?

### Problems it Solves

1. **Output Buffering** - Unbuffered by default (no `stdbuf` needed)
2. **Time Wasted** - Exits immediately on error
3. **Complexity** - One command vs. complex pipeline
4. **Hang Detection** - Built-in idle timeout
5. **Manual Logging** - Auto-generates log files
6. **Missing Context** - Delay-exit captures full errors

### When to Use Traditional Tools

- **Use grep** if you need: Maximum compatibility, simple filtering
- **Use timeout** if you need: Just overall timeout, no pattern matching
- **Use tee** if you need: Multiple output files simultaneously
- **Use stdbuf** if you need: Fine-grained buffer control

**But for most use cases, `earlyexit` is better!**

---

## Performance Comparison

| Tool | Startup | Memory | CPU | Disk I/O |
|------|---------|--------|-----|----------|
| grep | Instant | Minimal | Minimal | None |
| timeout | Instant | Minimal | Minimal | None |
| tee | Instant | Minimal | Minimal | High |
| stdbuf | Instant | Minimal | Minimal | None |
| **earlyexit** | <10ms | Low | Low | Medium |

**Note:** earlyexit overhead is negligible for typical use cases.

---

## Summary

**Replace this:**
```bash
stdbuf -o0 timeout 300 command 2>&1 | tee log | grep -i 'error'
```

**With this:**
```bash
ee -t 300 -i 'error' command
```

**And get:**
- ✅ Real-time output
- ✅ Early exit on errors
- ✅ Auto-logging
- ✅ Hang detection
- ✅ ML-powered learning

**One command. Better results. Less complexity.**

---

For detailed usage, see [User Guide](USER_GUIDE.md).





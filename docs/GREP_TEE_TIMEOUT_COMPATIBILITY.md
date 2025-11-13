# grep / tee / timeout Compatibility Guide

## TL;DR

✅ **`earlyexit` is compatible with `grep`, `tee`, and `timeout` flags!**

Most important flags match exactly:
- `-i` = ignore case (grep)
- `-v` = invert match (grep)
- `-E` = extended regex (grep)
- `-P` = Perl regex (grep)
- `-m NUM` = max count (grep)
- `-n` = line numbers (grep)
- `-q` = quiet/suppress output (grep)
- `-t SECONDS` = timeout (timeout)

---

## Full Compatibility Matrix

### grep-Compatible Flags

| Flag | grep Meaning | earlyexit | Status |
|------|--------------|-----------|--------|
| `-E` | Extended regex | ✅ Same | ✅ COMPATIBLE |
| `-i` | Ignore case | ✅ Same | ✅ COMPATIBLE |
| `-m NUM` | Max count | ✅ Same | ✅ COMPATIBLE |
| `-n` | Line numbers | ✅ Same | ✅ COMPATIBLE |
| `-P` | Perl regex | ✅ Same | ✅ COMPATIBLE |
| `-q` | Quiet (no output) | ✅ Same | ✅ COMPATIBLE |
| `-v` | Invert match | ✅ Same | ✅ COMPATIBLE |

**Additional grep features to consider:**
- `-A NUM` - After context (could add)
- `-B NUM` - Before context (could add)
- `-C NUM` - Context both (could add)
- `-c` - Count only (could add)

### timeout-Compatible Flags

| Flag | timeout Meaning | earlyexit | Status |
|------|-----------------|-----------|--------|
| DURATION | Timeout duration | `-t SECONDS` | ✅ COMPATIBLE (different syntax) |
| `-s SIGNAL` | Signal to send | ❌ Not impl | 📝 Could add |
| `-k DURATION` | Kill after | ❌ Not impl | 📝 Could add |

**Extensions beyond timeout:**
- `--idle-timeout` - Timeout if no output
- `--first-output-timeout` - Timeout if no first output

### tee-Compatible Features

| Feature | tee | earlyexit | Status |
|---------|-----|-----------|--------|
| Write to file + screen | ✅ Core feature | ✅ Auto-logging | ✅ COMPATIBLE |
| `-a` append | For appending | `-a` = disable log | ⚠️ Different meaning |
| `-i` ignore interrupts | Ignore SIGINT | `-i` = ignore case | ⚠️ Different (grep takes priority) |

**Note:** Auto-logging is always ON by default, so `ee` behaves like `| tee` is built-in!

---

## Flag Conflicts (Minor)

###  1. `-a` Flag

**tee:** `-a` = append to files  
**earlyexit:** `-a` = `--no-auto-log` (disable logging)

**Why different:** 
- Auto-logging is unique to earlyexit
- Each run creates unique files with PID (no append needed)
- `-a` for "auto-off" is mnemonic

**Resolution:** Keep current meaning. If append mode needed, use `--append` (future feature).

### 2. `-i` Flag

**tee:** `-i` = ignore interrupts  
**grep:** `-i` = ignore case  
**earlyexit:** `-i` = ignore case (follows grep)

**Why follows grep:** Pattern matching (grep) is more common than interrupt handling (tee).

---

## Usage Examples

### Replacing grep

```bash
# grep: Search for pattern
grep 'ERROR' logfile.txt

# earlyexit: Same + auto-logging
cat logfile.txt | ee 'ERROR'

# grep: Case insensitive
grep -i 'error' logfile.txt

# earlyexit: Same
cat logfile.txt | ee -i 'error'

# grep: Invert match
grep -v 'DEBUG' logfile.txt

# earlyexit: Same
cat logfile.txt | ee -v 'DEBUG'

# grep: Quiet mode (exit code only)
grep -q 'ERROR' logfile.txt && echo "Found error"

# earlyexit: Same
cat logfile.txt | ee -q 'ERROR' && echo "Found error"
```

### Replacing timeout

```bash
# timeout: Kill after 30 seconds
timeout 30 npm test

# earlyexit: Same + pattern matching + auto-logging
ee -t 30 'ERROR' npm test

# timeout: With custom signal
timeout -s SIGTERM 30 npm test

# earlyexit: (future feature)
ee -t 30 -s SIGTERM 'ERROR' npm test
```

### Replacing tee

```bash
# tee: Write to file AND screen
npm test 2>&1 | tee /tmp/test.log

# earlyexit: Automatic! (auto-logging ON by default)
ee 'ERROR' npm test
# Creates: /tmp/ee-npm_test-<pid>.log automatically

# tee: Append mode
npm test 2>&1 | tee -a /tmp/test.log

# earlyexit: Use custom prefix for consistency
ee --file-prefix /tmp/test 'ERROR' npm test
# Note: Creates new file each run (use --append for true append, future feature)
```

### Combining All Three!

**Old way (manual):**
```bash
timeout 300 npm test 2>&1 | tee /tmp/test.log | grep -i 'error'
```

**New way (with earlyexit):**
```bash
ee -t 300 -i 'error' npm test
# Automatic:
# - 300s timeout (like timeout)
# - Case-insensitive pattern (like grep -i)
# - Auto-logging (like tee)
# - Early exit on first match
# - Full error context captured
```

---

## Migration Guide

### From grep

```bash
# grep
grep 'pattern' file.txt
grep -i 'pattern' file.txt
grep -v 'pattern' file.txt
grep -E 'regex' file.txt
grep -m 5 'pattern' file.txt

# earlyexit (pipe mode)
cat file.txt | ee 'pattern'
cat file.txt | ee -i 'pattern'
cat file.txt | ee -v 'pattern'
cat file.txt | ee -E 'regex'
cat file.txt | ee -m 5 'pattern'

# All flags work the same!
```

### From timeout

```bash
# timeout
timeout 60 command

# earlyexit
ee -t 60 'ERROR' command  # Also adds pattern matching!
```

### From tee

```bash
# tee
command 2>&1 | tee /tmp/log.log

# earlyexit (automatic!)
ee 'ERROR' command
# Auto-creates /tmp/ee-command-<pid>.log

# tee with custom filename
command 2>&1 | tee /tmp/mylog.log

# earlyexit
ee --file-prefix /tmp/mylog 'ERROR' command
```

---

## Best Practices

### 1. Use Familiar Flags

If you know grep, use the same flags:
```bash
# You know: grep -i 'error' file.txt
# Use: ee -i 'error' command
```

### 2. Combine Features

```bash
# timeout + grep + tee all in one!
ee -t 300 -i 'error' npm test
```

### 3. Take Advantage of Auto-Logging

```bash
# Old way (manual)
timeout 300 npm test 2>&1 | tee /tmp/test_$(date +%s).log

# New way (automatic)
ee -t 300 'ERROR' npm test
# Automatically creates /tmp/ee-npm_test-<pid>.log
```

### 4. Use Quiet Mode for Scripts

```bash
# Like grep -q
if ee -q 'ERROR' npm test; then
  echo "Tests passed"
else
  echo "Tests failed"
  cat /tmp/ee-npm_test-*.log  # Log file still created!
fi
```

---

## Summary

### ✅ Compatible Flags

- `-E` - Extended regex (grep)
- `-i` - Ignore case (grep)
- `-m NUM` - Max count (grep)
- `-n` - Line numbers (grep)
- `-P` - Perl regex (grep)
- `-q` - Quiet mode (grep)
- `-v` - Invert match (grep)
- `-t SECONDS` - Timeout (timeout-style)

### ⚠️ Minor Differences

- `-a` means "disable auto-log" (not "append" like tee)
  - Reason: Auto-logging is unique to earlyexit
  - Each run creates unique files anyway
  
- `-i` means "ignore case" (not "ignore interrupts" like tee)
  - Reason: grep compatibility is more important

### ✅ Enhanced Features

- **Auto-logging** - Built-in `tee` behavior
- **Pattern matching** - Built-in `grep` behavior
- **Timeout** - Built-in `timeout` behavior
- **Early exit** - Stop on first error (unique)
- **Delay-exit** - Capture error context (unique)
- **Telemetry** - Learn patterns (unique)

---

## Conclusion

`earlyexit` successfully combines `grep`, `tee`, and `timeout` with minimal conflicts:

✅ **Main grep flags work exactly the same**  
✅ **Timeout behavior is compatible**  
✅ **Auto-logging provides tee functionality**  
⚠️ Two minor differences (`-a`, `-i`) that don't impact common workflows

**Result:** Users familiar with grep/tee/timeout will feel right at home! 🎉


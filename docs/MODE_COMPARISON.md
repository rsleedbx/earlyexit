# Mode Comparison - Detailed Guide

## Three Modes at a Glance

`earlyexit` has three distinct modes of operation, each optimized for different use cases.

## Quick Decision Guide

**Choose your mode:**

```
Need to integrate with existing pipeline? → Pipe Mode
Want complete control & ML features? → Command Mode
Don't know what pattern to look for? → Watch Mode
```

## Detailed Comparison Table

| Feature | Pipe Mode | Command Mode | Watch Mode | Tests |
|---------|-----------|--------------|------------|-------|
| **Syntax** | `cmd \| ee 'pat'` | `ee 'pat' cmd` | `ee cmd` | [🧪](../tests/test_syntax_and_limitations.sh) |
| **Pattern Required** | ✅ Yes | ✅ Yes | ❌ No (learns) | [🧪](../tests/test_syntax_and_limitations.sh) |
| **Chainable** | ✅ Middle of chain | ✅ Head of chain | ❌ Terminal command | [🧪](../tests/test_syntax_and_limitations.sh) |
| **Real-time output** | ✅ Yes | ✅ Yes (unbuffered) | ✅ Yes | - |
| **Auto-logging** | ❌ No | ✅ Yes | ❌ No | [📚](AUTO_LOGGING_DESIGN.md) |
| **Monitor stderr** | ❌ Need `2>&1` | ✅ Both by default | ✅ Both by default | [🧪](../tests/test_syntax_and_limitations.sh) |
| **Idle detection** | ✅ `--idle-timeout` | ✅ `--idle-timeout` | ✅ Tracked | [🧪](../tests/test_pipe_timeouts.sh) |
| **Startup detection** | ✅ `--first-output-timeout` | ✅ `--first-output-timeout` | ✅ Tracked | [🧪](../tests/test_pipe_timeouts.sh) |
| **Error context capture** | ✅ `--delay-exit` | ✅ `--delay-exit` | ✅ Captured | [🧪](../tests/test_pipe_delay_exit.sh) |
| **Custom FDs** | ❌ Not available | ✅ `--fd 3 --fd 4` | ✅ Detected & logged | [🧪](../tests/test_fd.sh) |
| **ML Validation** | ❌ No | ✅ TP/TN/FP/FN tracked | ✅ TP/TN/FP/FN tracked | [📚](PIPE_MODE_TIMEOUTS.md) |
| **Smart Suggestions** | ❌ No | ✅ Yes (on repeat) | ✅ Yes (auto) | [📚](PIPE_MODE_TIMEOUTS.md) |
| **Learning** | ❌ No | ❌ No | ✅ Learns from Ctrl+C | [📚](PIPE_MODE_TIMEOUTS.md) |
| **Process control** | ❌ No (reads stdin) | ✅ Yes (spawns process) | ✅ Yes (spawns process) | - |
| **Like** | `grep`, `awk` | `timeout`, `stdbuf` | *New paradigm* | - |

> **Note:** `--` is optional in command mode. Both `ee 'pat' cmd` and `ee 'pat' -- cmd` work.

---

## Mode 1: Pipe Mode

### Overview

**Philosophy:** Unix pipe tradition - read from stdin, write to stdout, chainable.

**Use when:**
- Integrating with existing pipelines
- Need to chain with other tools
- Want traditional grep-like behavior
- Have log files to monitor

**Limitations:**
- Needs `2>&1` to capture stderr
- Cannot use custom FDs
- No ML validation
- No auto-logging

### Syntax

```bash
command | ee [OPTIONS] PATTERN
command 2>&1 | ee [OPTIONS] PATTERN  # With stderr
```

### Examples

#### Basic Usage

```bash
# Simple error detection
./build.sh 2>&1 | ee 'error'

# With timeout
npm test 2>&1 | ee -t 300 'ERROR|FAIL'

# Case-insensitive
terraform apply 2>&1 | ee -i 'error'
```

#### Chaining (Middle of Pipeline)

```bash
# Chain with tee for logging
make 2>&1 | tee build.log | ee 'error'

# Filter then monitor
kubectl logs -f pod | grep -v DEBUG | ee 'ERROR'

# Multiple processing stages
./app 2>&1 | tee app.log | grep -v INFO | ee -i 'error|fatal'
```

**Key:** Pipe mode reads from stdin and writes to stdout - can be in the middle of a pipeline.

#### With Delay-Exit (Context Capture)

```bash
# Capture 5 seconds of context after error
terraform apply 2>&1 | ee --delay-exit 5 'Error'

# Capture 10 seconds OR 50 lines
npm test 2>&1 | ee --delay-exit 10 --delay-exit-after-lines 50 'FAIL'
```

#### Log Monitoring

```bash
# Monitor live logs
tail -f /var/log/app.log | ee -t 300 'error|exception'

# Monitor with idle detection
tail -f app.log | ee --idle-timeout 60 'ERROR'
```

### Exit Codes

- `0` - Pattern matched (error detected)
- `1` - No match found (success)
- `2` - Timeout exceeded

---

## Mode 2: Command Mode

### Overview

**Philosophy:** One-stop solution - spawns process, monitors everything, provides complete control.

**Use when:**
- Want complete control over execution
- Need ML validation & smart suggestions
- Want auto-logging
- Need to monitor stderr separately
- Need custom FD monitoring
- Want hang detection

**Benefits:**
- Monitors stdout & stderr by default
- Auto-logging enabled
- Full timeout support
- ML tracking
- Custom FD support

### Syntax

```bash
ee [OPTIONS] PATTERN COMMAND [ARGS...]
ee [OPTIONS] PATTERN -- COMMAND [ARGS...]  # Optional --
```

### Examples

#### Basic Usage

```bash
# Simple execution
ee 'ERROR' ./app

# With timeout
ee -t 300 'Error|Failed' terraform apply

# Case-insensitive
ee -i 'error' make build
```

#### Advanced Timeouts

```bash
# Detect hangs - exit if no output for 30s
ee --idle-timeout 30 'Error' ./long-running-app

# Detect slow startup - exit if no output within 10s
ee --first-output-timeout 10 'Error' ./slow-service

# Combine all timeouts
ee -t 300 --idle-timeout 30 --first-output-timeout 10 'Error' ./app
```

#### Error Context Capture

```bash
# Default: wait 10s after error (or 100 lines)
ee 'Error' ./app

# Quick exit: wait only 5s
ee --delay-exit 5 'Error' ./app

# Comprehensive: wait 30s for full logs
ee --delay-exit 30 'Error' ./verbose-app

# Immediate exit (no delay)
ee --delay-exit 0 'FATAL' ./app

# Custom line limit
ee --delay-exit 10 --delay-exit-after-lines 200 'Error' ./app
```

#### Auto-Logging

```bash
# Default: auto-creates ee-cmd-pid.log
ee 'Error' ./deploy.sh
# Creates: ee-deploy_sh-12345.log

# Custom log prefix
ee --file-prefix /tmp/myrun 'Error' ./app
# Creates: /tmp/myrun.log and /tmp/myrun.errlog

# Append mode (like tee -a)
ee -a --file-prefix /tmp/app 'Error' ./app

# Compressed logs
ee -z 'Error' ./long-job.sh
# Creates: ee-long_job_sh-12345.log.gz

# Disable auto-logging
ee --no-log 'Error' ./app
```

#### Custom File Descriptors

```bash
# Monitor FD 3
ee --fd 3 'Error' ./app

# Monitor multiple FDs
ee --fd 3 --fd 4 --fd 5 'Error' ./app

# Different pattern per FD
ee --fd-pattern 3 'ERROR' --fd-pattern 4 'WARN' 'Error' ./app

# Label FD output
ee --fd-prefix --fd 3 'Error' ./app
# Output: [fd3] Line from descriptor 3
```

#### Stream Control

```bash
# Monitor stdout only
ee --stdout 'Error' ./app

# Monitor stderr only
ee --stderr 'Error' ./app

# Both (default)
ee 'Error' ./app
```

### Exit Codes

- `0` - Pattern matched (error detected)
- `1` - No match found (success)
- `2` - Timeout exceeded
- `3` - Other error

---

## Mode 3: Watch Mode

### Overview

**Philosophy:** Zero-config learning - no pattern needed, learns from you.

**Use when:**
- Don't know what pattern to look for
- Exploring new tools/commands
- Want ML-powered suggestions
- Want system to learn your workflows

**How it works:**
1. Run command without pattern
2. Press Ctrl+C when you see an error
3. System captures context & suggests pattern
4. Next run uses learned settings

### Syntax

```bash
ee COMMAND [ARGS...]
```

### Examples

#### First Time (Learning)

```bash
# Run without pattern
ee terraform apply

# Output shows:
# 🔍 Watch mode enabled (no pattern specified)
#    • All output is being captured and analyzed
#    • Press Ctrl+C when you see an error to teach earlyexit
#    • stdout/stderr are tracked separately for analysis

# When you see error, press Ctrl+C:
^C

# Interactive prompt appears:
# ⚠️  Interrupted at 45.3s
#    • Captured 123 stdout lines
#    • Captured 45 stderr lines
#
# Detected error patterns:
#   1. Error: (confidence: 95%)
#   2. AccessDenied (confidence: 87%)
#   3. Failed (confidence: 72%)
#
# Select pattern (1-3), or 'n' for none: 1
#
# Timeout suggestions:
#   • Overall: 300s (typical run time)
#   • Idle: 60s (max time between outputs)
#   • Delay-exit: 10s (after error)
#
# Save these settings? (y/n): y
# ✅ Settings saved for 'terraform apply'
```

#### Second Time (Applying Learned Settings)

```bash
# Run again
ee terraform apply

# Output shows:
# 💡 Using learned settings:
#    • Pattern: Error:
#    • Overall timeout: 300s
#    • Idle timeout: 60s
#    • Delay-exit: 10s
#
# [runs with learned settings automatically]
```

#### Features

**What's Tracked:**
- ✅ Startup time (first output delay)
- ✅ Idle time (gaps between outputs)
- ✅ Custom FDs (automatically detected)
- ✅ Stream separation (stdout vs stderr)
- ✅ Line counts per stream
- ✅ Error context (last 20 lines)

**ML Integration:**
- Learns typical run times
- Detects common patterns
- Suggests optimal timeouts
- Tracks false positives/negatives
- Improves over time

---

## When to Use Each Mode

### Use Case Matrix

| Use Case | Recommended Mode | Why |
|----------|------------------|-----|
| Existing pipeline integration | Pipe | Chainable, fits Unix philosophy |
| CI/CD scripts | Command | Auto-logging, full control |
| Interactive development | Watch | Learn as you go |
| Log file monitoring | Pipe | tail -f \| ee 'pattern' |
| Production deployments | Command | Hang detection, ML validation |
| Exploring new tools | Watch | No pattern needed |
| Test automation | Command | Smart suggestions on repeat |
| Quick one-offs | Pipe | Simplest syntax |

### Performance Comparison

| Aspect | Pipe Mode | Command Mode | Watch Mode |
|--------|-----------|--------------|------------|
| Startup overhead | Minimal | Low | Low |
| Memory usage | Minimal | Medium | Medium |
| CPU usage | Minimal | Low | Low |
| Disk I/O | None | Auto-logging | Buffer only |

### Feature Availability by Mode

#### Timeout Features

| Feature | Pipe | Command | Watch |
|---------|------|---------|-------|
| Overall timeout (`-t`) | ✅ | ✅ | ❌ (learns) |
| Idle timeout | ✅ | ✅ | ✅ (tracks) |
| First output timeout | ✅ | ✅ | ✅ (tracks) |

#### Output Features

| Feature | Pipe | Command | Watch |
|---------|------|---------|-------|
| Real-time output | ✅ | ✅ | ✅ |
| Auto-logging | ❌ | ✅ | ❌ |
| Stderr capture | Need `2>&1` | ✅ Default | ✅ Default |
| Custom FDs | ❌ | ✅ Explicit | ✅ Auto-detect |

#### Learning Features

| Feature | Pipe | Command | Watch |
|---------|------|---------|-------|
| Pattern learning | ❌ | ❌ | ✅ |
| Timeout learning | ❌ | ❌ | ✅ |
| Smart suggestions | ❌ | ✅ (repeat) | ✅ (auto) |
| ML validation | ❌ | ✅ | ✅ |

---

## Migration Between Modes

### From Pipe to Command

```bash
# Before (Pipe Mode)
terraform apply 2>&1 | ee 'Error'

# After (Command Mode)
ee 'Error' terraform apply
```

**Gains:**
- ✅ No need for `2>&1`
- ✅ Auto-logging enabled
- ✅ ML validation
- ✅ Hang detection available

**Loses:**
- ❌ Can't chain further

### From Command to Pipe

```bash
# Before (Command Mode)
ee 'Error' terraform apply

# After (Pipe Mode)
terraform apply 2>&1 | ee 'Error'
```

**Gains:**
- ✅ Can chain with other tools
- ✅ Simpler for quick use

**Loses:**
- ❌ No auto-logging
- ❌ No ML validation
- ❌ Must add `2>&1`

### From Any Mode to Watch

```bash
# Just remove the pattern
ee terraform apply

# System learns and suggests pattern for next time
```

---

## Best Practices by Mode

### Pipe Mode Best Practices

```bash
# ✅ Always capture stderr
cmd 2>&1 | ee 'pattern'

# ✅ Use delay-exit for context
cmd 2>&1 | ee --delay-exit 10 'ERROR'

# ✅ Combine with tee for logs
cmd 2>&1 | tee log | ee 'pattern'

# ❌ Don't forget 2>&1
cmd | ee 'pattern'  # Won't see stderr errors!
```

### Command Mode Best Practices

```bash
# ✅ Let auto-logging work
ee 'Error' terraform apply  # Auto-creates logs

# ✅ Use all timeout types
ee -t 600 --idle-timeout 30 --first-output-timeout 10 'Error' cmd

# ✅ Compress long logs
ee -z 'Error' long-running-job

# ✅ Use custom prefix for clarity
ee --file-prefix /tmp/deploy-$(date +%Y%m%d) 'Error' ./deploy.sh
```

### Watch Mode Best Practices

```bash
# ✅ Use for exploration
ee new-command --with-options

# ✅ Press Ctrl+C at error (not random time)
# Wait until you see actual error, then Ctrl+C

# ✅ Save learned settings
# Say 'y' when prompted to save

# ✅ Review suggestions
# Check recommended patterns before accepting
```

---

## Common Patterns

### CI/CD Pipeline

```bash
# Use Command Mode for full control
ee -t 600 --idle-timeout 60 'ERROR|FAIL' ./ci-script.sh

# Auto-logging captures everything
# Exit immediately on error
# Hang detection prevents stuck builds
```

### Interactive Development

```bash
# First time: Watch Mode
ee terraform apply
# Learn pattern interactively

# Subsequent runs: Command Mode
ee 'Error' terraform apply
# Uses learned settings
```

### Log Monitoring

```bash
# Pipe Mode for live monitoring
tail -f /var/log/app.log | ee -t 300 'ERROR|FATAL'

# Command Mode for one-shot analysis
ee 'ERROR' cat /var/log/app.log
```

---

## Summary

| Aspect | Pipe | Command | Watch |
|--------|------|---------|-------|
| **Complexity** | Simple | Medium | Simple |
| **Features** | Basic | Full | Learning |
| **Control** | Low | High | Adaptive |
| **Learning Curve** | Instant | 5 minutes | Instant |
| **Use Case** | Quick tasks | Production | Discovery |

**Choose based on your needs:**
- **Speed → Pipe Mode**
- **Control → Command Mode**
- **Learning → Watch Mode**

All modes work together - use the right tool for the job! 🚀


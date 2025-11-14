# earlyexit User Guide

Complete guide to using `earlyexit` (alias: `ee`) effectively.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Command-Line Options](#command-line-options)
3. [Examples by Mode](#examples-by-mode)
4. [Common Use Cases](#common-use-cases)
5. [Pattern Syntax](#pattern-syntax)
6. [Exit Codes](#exit-codes)
7. [Tips & Tricks](#tips--tricks)

---

## Quick Start

### Three Ways to Use

```bash
# 1. Pipe Mode (Unix tradition)
command 2>&1 | ee 'ERROR'

# 2. Command Mode (one-stop solution)
ee 'ERROR' command

# 3. Watch Mode (learn & discover)
ee command  # No pattern, learns from Ctrl+C
```

### First Commands

```bash
# Install
pip install earlyexit

# Basic examples
echo "test ERROR test" | ee 'ERROR'  # Match!
ee 'Error' echo "test Error test"    # Match!
ee echo "no pattern needed"           # Watch mode
```

---

## Command-Line Options

### Complete Option Reference

```
Usage:
  ee [OPTIONS] PATTERN [--] COMMAND [ARGS...]  # Command mode
  command | ee [OPTIONS] PATTERN                # Pipe mode
  ee COMMAND [ARGS...]                          # Watch mode (no pattern)

Pattern:
  PATTERN                Regular expression to match

Timeout Options:
  -t, --timeout SECONDS           Overall timeout
  -I, --idle-timeout SECONDS          Stall detection (no output for N seconds)
  -F, --first-output-timeout SECONDS  Startup detection (no output within N seconds)

Error Context Options:
  -A, --after-context SECONDS     Wait N seconds after match for context (default: 10, like grep -A but time-based)
  -B, --before-context NUM        Print NUM lines before matching lines (like grep -B)
  -C, --context NUM               Print NUM lines of context (sets both -B and -A, like grep -C)
  --delay-exit SECONDS            Alias for -A/--after-context
  --delay-exit-after-lines LINES  Exit early if N lines captured (default: 100)

Pattern Options:
  -i, --ignore-case      Case-insensitive matching
  -E, --extended-regexp  Extended regex (default)
  -P, --perl-regexp      Perl-compatible regex (requires regex module)
  -w, --word-regexp      Match whole words only (like grep -w)
  -x, --line-regexp      Match whole lines only (like grep -x)
  -v, --invert-match     Select NON-matching lines
  -m, --max-count NUM    Stop after NUM matches (default: 1)

Output Options:
  -q, --quiet            Suppress output (only exit code)
  -n, --line-number      Prefix lines with line numbers
  --color WHEN           Colorize: always, auto (default), never

Logging Options:
  --file-prefix PREFIX   Log file prefix (auto-logging enabled by default)
  -a, --append           Append to log files (like tee -a)
  -z, --gzip             Compress log files
  --no-log               Disable auto-logging
  --log-dir DIR          Log directory (default: /tmp)

Stream Options:
  --stdout               Monitor stdout only (command mode)
  --stderr               Monitor stderr only (command mode)
  --fd N                 Monitor file descriptor N (e.g., --fd 3)
  --fd-pattern FD PAT    Pattern for specific FD
  --fd-prefix            Label output with stream name

Unbuffering:
  -u, --unbuffered       Force unbuffered output (default for command mode)
  --buffered             Use buffered output (for high-throughput)

Profile System:
  --profile NAME         Use a predefined profile (e.g., --profile terraform)
  --list-profiles        List all available profiles
  --show-profile NAME    Show details about a specific profile

Advanced Options:
  --source-file FILE     Specify source file for telemetry (auto-detected)
  --stdout-unbuffered    Force unbuffered stdout only (use -u for both)
  --stderr-unbuffered    Force unbuffered stderr only (use -u for both)
  --stderr-prefix        Alias for --fd-prefix (backward compatibility)
  --auto-tune            Auto-select optimal parameters (experimental)

Other:
  --no-telemetry         Disable telemetry collection
  --verbose              Verbose output
  --version              Show version
  -h, --help             Show help

Exit Codes:
  0 - Pattern matched (error detected)
  1 - No match (success)
  2 - Timeout
  3 - Other error
  130 - Interrupted (Ctrl+C)

Environment Variables:
  EARLYEXIT_OPTIONS      Default options prepended to command line (like GREP_OPTIONS)
                         Example: export EARLYEXIT_OPTIONS='-i --color=always -B 3'
                         CLI arguments override environment defaults
```

---

## Examples by Mode

### Pipe Mode Examples

#### Basic Usage

```bash
# Simple error detection
./build.sh 2>&1 | ee 'error'

# With timeout (5 minutes)
npm test 2>&1 | ee -t 300 'ERROR|FAIL'

# Case-insensitive
terraform apply 2>&1 | ee -i 'error'
```

#### With Context Capture

```bash
# Capture 5 seconds after error (grep -A compatible)
terraform apply 2>&1 | ee -A 5 'Error'

# Capture 3 lines before error (grep -B compatible)
npm test 2>&1 | ee -B 3 'FAIL'

# Capture context before AND after (grep -C compatible)
./build.sh 2>&1 | ee -C 3 'ERROR'
# Equivalent to: -B 3 -A 3

# Match whole words only (grep -w compatible)
./app 2>&1 | ee -w 'error'
# Matches "error" but not "errors" or "terror"

# Match exact lines only (grep -x compatible)
./app 2>&1 | ee -x 'FATAL ERROR'
# Only matches lines that are exactly "FATAL ERROR"
```

#### Chaining with Other Tools

```bash
# Save logs AND monitor
make 2>&1 | tee build.log | ee 'error'

# Filter then monitor
kubectl logs -f pod | grep -v DEBUG | ee 'ERROR'

# Limit output
pytest -v | ee 'FAILED' | head -50
```

#### Log Monitoring

```bash
# Monitor live logs
tail -f /var/log/app.log | ee -t 300 'error|exception'

# With idle detection
tail -f app.log | ee -I 60 'ERROR'
```

### Command Mode Examples

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
# Hang detection - exit if no output for 30s
ee -I 30 'Error' ./long-running-app

# Slow startup detection - exit if no output within 10s
ee -F 10 'Error' ./slow-service

# All timeouts combined
ee -t 300 -I 30 -F 10 'Error' ./app
```

#### Error Context Capture

```bash
# Default: 10s or 100 lines (whichever first)
ee 'Error' ./app

# Quick exit: 5s
ee --delay-exit 5 'Error' ./app

# Comprehensive: 30s
ee --delay-exit 30 'Error' ./verbose-app

# Immediate exit
ee --delay-exit 0 'FATAL' ./app

# Custom limits
ee --delay-exit 10 --delay-exit-after-lines 200 'Error' ./app
```

#### Auto-Logging Examples

```bash
# Default: auto-creates ee-cmd-pid.log
ee 'Error' ./deploy.sh
# Creates: ee-deploy_sh-12345.log and ee-deploy_sh-12345.errlog

# Custom prefix
ee --file-prefix /tmp/myrun 'Error' ./app
# Creates: /tmp/myrun.log and /tmp/myrun.errlog

# Exact filename (ends with .log or .out)
ee --file-prefix /tmp/deployment.log 'Error' ./deploy.sh
# Creates: /tmp/deployment.log and /tmp/deployment.err

# Append mode (like tee -a)
ee -a --file-prefix /tmp/app 'Error' ./app

# Compressed logs
ee -z 'Error' ./long-job.sh
# Creates: ee-long_job_sh-12345.log.gz

# Disable logging
ee --no-log 'Error' ./app
```

#### Detach Mode

Exit without killing subprocess when pattern matches:

```bash
# Start service and detach when ready
ee -D 'Server listening on port 8080' ./start-server.sh
# Output:
# Server starting...
# Server listening on port 8080
# 🔓 Detached from subprocess (PID: 12345)
#    Subprocess continues running in background
#    Use 'kill 12345' to stop it later
# Exit code: 4

# Capture PID for cleanup
OUTPUT=$(ee -D 'Ready' ./service.sh 2>&1)
PID=$(echo "$OUTPUT" | grep "PID:" | awk '{print $NF}' | tr -d ')')

# Use in CI/CD
ee -D 'database system is ready' postgres -D /data
if [ $? -eq 4 ]; then
    pytest
    pkill postgres
fi
```

**Use cases:** Services, background jobs, daemons, CI/CD

**Exit code:** 4 (subprocess still running)

**See:** [Exit Codes Reference](EXIT_CODES.md#exit-code-4-detached-new)

#### Custom File Descriptors

```bash
# Monitor FD 3
ee --fd 3 'Error' ./app

# Multiple FDs
ee --fd 3 --fd 4 --fd 5 'Error' ./app

# Different pattern per FD
ee --fd-pattern 3 'ERROR' --fd-pattern 4 'WARN' 'Error' ./app

# Label output
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

### Watch Mode Examples

#### First Run (Learning)

```bash
# Run without pattern
ee terraform apply

# Output:
# 🔍 Watch mode enabled (no pattern specified)
#    • All output is being captured and analyzed
#    • Press Ctrl+C when you see an error to teach earlyexit

# [Terraform runs...]
# [You see error, press Ctrl+C]

^C

# Interactive prompt:
# ⚠️  Interrupted at 45.3s
#    • Captured 123 stdout lines
#    • Captured 45 stderr lines
#
# Detected patterns:
#   1. Error: (confidence: 95%)
#   2. AccessDenied (confidence: 87%)
#
# Select pattern: 1
# Save settings? (y/n): y
# ✅ Settings saved
```

#### Subsequent Runs

```bash
# Uses learned settings automatically
ee terraform apply

# Output:
# 💡 Using learned settings:
#    • Pattern: Error:
#    • Overall timeout: 300s
#    • Idle timeout: 60s
```

---

## Common Use Cases

### Terraform Deployments

```bash
# Command mode (recommended)
ee -t 600 -I 60 'Error|AccessDenied' terraform apply

# Pipe mode
terraform apply 2>&1 | ee -t 600 'Error'
```

### CI/CD Pipelines

```bash
# Full monitoring
ee -t 3600 -I 60 -F 15 'error|fatal' ./build.sh

# Exit code handling
if [ $? -eq 0 ]; then
  echo "❌ Build failed"
  exit 1
elif [ $? -eq 2 ]; then
  echo "⏱️  Build timed out"
  exit 2
else
  echo "✅ Build successful"
fi
```

### Test Suites

```bash
# Stop after first failure
pytest -v | ee 'FAILED'

# Stop after 5 failures
pytest -v | ee -m 5 'FAILED'

# With timeout and logging
ee -t 300 -z 'FAILED|ERROR' pytest -v
```

### Database Operations

```bash
# Monitor with hang detection
ee -t 1800 -I 120 'Error|Failed' \
  mist create --cloud aws --db mysql

# Handle exit codes
case $? in
  0) echo "❌ Failed"; exit 1 ;;
  1) echo "✅ Success" ;;
  2) echo "⏱️  Timeout"; exit 2 ;;
esac
```

### Docker Operations

```bash
# Build with monitoring
ee -t 1200 'ERROR|failed' docker build -t myapp .

# Run with hang detection
ee -I 30 'Error' docker run myapp
```

### Kubernetes

```bash
# Monitor pod logs
kubectl logs -f pod-name | ee 'ERROR|CrashLoopBackOff'

# Apply with monitoring
ee 'Error' kubectl apply -f deployment.yaml
```

### Long-Running Jobs

```bash
# With comprehensive logging
ee -t 7200 -I 300 -z --file-prefix /var/log/job 'Error' ./long-job.sh

# Monitor progress and errors
ee -t 7200 --delay-exit 30 'Error|Progress' ./job.sh
```

### Using Environment Defaults

```bash
# Set default options for all ee commands
export EARLYEXIT_OPTIONS='-i --color=always -B 3'

# Now all commands inherit these defaults
ee 'error' ./build.sh
# Equivalent to: ee -i --color=always -B 3 'error' ./build.sh

# CLI args override environment defaults
ee -B 5 'error' ./build.sh
# Uses -B 5 instead of -B 3

# Useful in CI/CD
export EARLYEXIT_OPTIONS='-t 1800 --no-telemetry -z'
ee 'Error' terraform apply
# Auto-applies timeout, disables telemetry, compresses logs
```

---

## Pattern Syntax

### Basic Patterns

```bash
# Literal text
ee 'ERROR' command

# Case-insensitive
ee -i 'error' command

# Multiple patterns (OR)
ee 'ERROR|FAIL|Exception' command

# Word boundaries
ee '\bERROR\b' command  # Match "ERROR" but not "ERRORLOG"
```

### Extended Regex (Default)

```bash
# Character classes
ee '[Ee]rror' command            # Error or error
ee 'ERROR[0-9]+' command         # ERROR123, ERROR456

# Quantifiers
ee 'ERR(OR)+' command            # ERROR, ERROROROR
ee 'fail(ed)?' command           # fail or failed

# Groups
ee '(ERROR|FATAL):' command      # ERROR: or FATAL:

# Anchors
ee '^ERROR' command              # ERROR at line start
ee 'ERROR$' command              # ERROR at line end
```

### Perl-Compatible Regex

```bash
# Requires: pip install earlyexit[perl]

# Lookahead
ee -P 'ERROR(?= detected)' command

# Lookbehind
ee -P '(?<=Code )ERROR' command

# Non-capturing groups
ee -P '(?:ERROR|FAIL):' command
```

### Common Patterns

```bash
# Any error
ee -i 'error|fail|exception|fatal' command

# Stack traces
ee 'Traceback|at \S+:\d+' command

# HTTP errors
ee '[45][0-9]{2}' command        # 400-599

# IP addresses
ee '\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}' command

# Timestamps with errors
ee '\d{2}:\d{2}:\d{2}.*ERROR' command
```

---

## Exit Codes

### Understanding Exit Codes

| Exit Code | Meaning | Use Case |
|-----------|---------|----------|
| `0` | Pattern matched | Error detected - take action |
| `1` | No match | Success - continue |
| `2` | Timeout | Process hung or too slow |
| `3` | Other error | Command failed to run |
| `130` | Interrupted (Ctrl+C) | User cancelled - watch mode learning |

### Handling Exit Codes

```bash
# Simple check
ee 'ERROR' command
if [ $? -eq 0 ]; then
  echo "Error detected!"
fi

# Full handling
ee 'ERROR' command
EXIT_CODE=$?

case $EXIT_CODE in
  0)
    echo "❌ Error detected"
    # Alert, rollback, etc.
    exit 1
    ;;
  1)
    echo "✅ Success"
    exit 0
    ;;
  2)
    echo "⏱️  Timeout"
    # Retry, alert, etc.
    exit 2
    ;;
  3)
    echo "⚠️  Command failed"
    exit 3
    ;;
esac
```

### Inverted Logic

```bash
# Exit 0 if NO error (success)
# Exit 1 if error found

ee 'ERROR' command
if [ $? -eq 1 ]; then
  echo "✅ No errors!"
fi
```

---

## Tips & Tricks

### Performance

```bash
# For high-throughput, use buffered output
ee --buffered 'pattern' high-throughput-command

# Disable telemetry for slight speedup
ee --no-telemetry 'pattern' command
```

### Debugging

```bash
# Verbose mode
ee --verbose 'pattern' command

# Show line numbers
ee -n 'pattern' command

# Label streams
ee --fd-prefix 'pattern' command
```

### Best Practices

```bash
# ✅ Always use 2>&1 in pipe mode
command 2>&1 | ee 'pattern'

# ✅ Use specific patterns
ee 'ERROR|FATAL' command  # Not just 'error'

# ✅ Set appropriate timeouts
ee -t 600 --idle-timeout 30 'Error' long-command

# ✅ Compress long logs
ee -z 'Error' long-running-job

# ✅ Use meaningful log prefixes
ee --file-prefix /var/log/app-$(date +%Y%m%d) 'Error' ./app
```

### Common Mistakes

```bash
# ❌ Forgot 2>&1 in pipe mode
command | ee 'ERROR'  # Won't see stderr!

# ✅ Correct
command 2>&1 | ee 'ERROR'

# ❌ Pattern too broad
ee 'e' command  # Matches almost everything!

# ✅ Specific pattern
ee '\bERROR\b|\bFAIL\b' command

# ❌ Wrong stdbuf position
command | stdbuf -o0 tee log | ee 'ERROR'  # Still buffers!

# ✅ Correct - or just use command mode
ee 'ERROR' command  # Unbuffered by default!
```

### Shortcuts

```bash
# Use 'ee' alias
ee 'ERROR' command  # Shorter than 'earlyexit'

# Combine flags
ee -it 300 'error' command  # -i -t 300

# Default delay-exit in command mode
ee 'Error' command  # Auto-waits 10s for context
```

### Integration with Other Tools

```bash
# With make
make 2>&1 | ee 'error:\s*\d+'

# With docker-compose
docker-compose up 2>&1 | ee 'ERROR|exited'

# With git
git push 2>&1 | ee 'rejected|error'

# With npm/yarn
npm run build 2>&1 | ee 'ERROR|FAIL'
```

---

## Advanced Usage

### Multiple Commands

```bash
# Sequential with error detection
ee 'ERROR' command1 && \
ee 'ERROR' command2 && \
ee 'ERROR' command3
```

### Conditional Execution

```bash
# Only if first succeeds (no error)
ee 'ERROR' ./step1.sh && ./step2.sh

# Always run second (even if first has error)
ee 'ERROR' ./step1.sh; ./step2.sh
```

### Background Jobs

```bash
# Run in background, monitor logs
ee 'ERROR' long-running-service &
tail -f /var/log/service.log | ee 'FATAL'
```

### Signal Handling

```bash
# In watch mode, Ctrl+C triggers learning
ee terraform apply  # Press Ctrl+C at error

# In other modes, Ctrl+C terminates
ee 'ERROR' long-command  # Ctrl+C stops everything
```

### Privacy & Telemetry Management

**By default, `earlyexit` stores execution data locally** to enable learning features.

#### What's Collected (Locally Only)

All data stays in `~/.earlyexit/telemetry.db` on your machine:
- Command patterns and exit codes
- Timeout settings that worked
- Error patterns you teach via Ctrl+C
- Timing statistics

**Nothing is sent anywhere.** All data is local.

#### Why Telemetry?

Powers these features:
- 🎓 **Interactive learning** - Remembers patterns you teach
- 💡 **Smart suggestions** (`ee-suggest`) - Recommends patterns
- ⚡ **Auto-tune** (`--auto-tune`) - Sets optimal timeouts

#### Disable Telemetry

```bash
# Option 1: Environment variable (recommended)
export EARLYEXIT_NO_TELEMETRY=1
# Add to ~/.bashrc or ~/.zshrc to make permanent

# Option 2: Per-command flag
ee --no-telemetry 'ERROR' terraform apply

# Option 3: Check what's stored
ee-stats                    # Show database size & statistics
ee-clear --older-than 30d   # Delete data older than 30 days
ee-clear --keep-learned     # Keep learned patterns, delete history
ee-clear --all -y           # Delete everything (no confirmation)
```

#### Database Size Management

**Auto-cleanup runs automatically:**
- Every 100 executions, old data is cleaned up
- Database stays under 100 MB
- Learned patterns are always preserved

**Manual cleanup:**
```bash
# Check current size
ee-stats
# Output shows: Database: /home/user/.earlyexit/telemetry.db
#               Size: 45.3 MB

# Clean up old data (keeps learned patterns)
ee-clear --older-than 30d

# Keep only learned patterns
ee-clear --keep-learned

# Delete everything
ee-clear --all
```

**Size warnings:**
- If database exceeds 500 MB, you'll see a warning
- Suggests cleanup commands automatically

#### Features Without Telemetry

**These still work with `--no-telemetry`:**
- ✅ Pattern matching, timeouts, auto-logging
- ✅ All grep flags (-A, -B, -C, -w, -x, etc.)
- ✅ Real-time output, early exit
- ✅ Context capture, log compression

**These require telemetry:**
- ❌ Interactive learning (won't remember patterns)
- ❌ Smart suggestions (`ee-suggest`)
- ❌ Auto-tune (`--auto-tune`)
- ❌ Statistics (`ee-stats`)

---

## Next Steps

- 📖 [Pattern Reference](REGEX_REFERENCE.md) - Comprehensive regex guide
- ⏱️ [Timeout Guide](TIMEOUT_GUIDE.md) - All timeout types explained
- 📝 [Auto-Logging Guide](AUTO_LOGGING_DESIGN.md) - Log management details
- 🧠 [Learning System](LEARNING_SYSTEM.md) - How watch mode learns
- ⚖️ [Mode Comparison](MODE_COMPARISON.md) - Detailed mode differences

---

**Questions?** Check the [FAQ](FAQ.md) or [open an issue](https://github.com/rsleedbx/earlyexit/issues).

**Star ⭐ this repo if this guide helped you!**


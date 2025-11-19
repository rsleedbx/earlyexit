# earlyexit (or `ee` for short) 🚀

**Early exit on first error. Help your AI get better. Zero code, zero config.**

[![PyPI version](https://badge.fury.io/py/earlyexit.svg)](https://badge.fury.io/py/earlyexit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Table of Contents

- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [Quick Start](#quick-start)
- [Key Features](#key-features)
- [Three Modes of Operation](#three-modes-of-operation)
- [Observability & Integration](#observability--integration)
- [Installation](#installation)
- [Privacy & Telemetry](#privacy--telemetry)
- [Documentation](#documentation)
- [For AI Assistants](#for-ai-assistants)
- [Contributing](#contributing)
- [License](#license)

---

## The Problem

**You've been using `timeout | tee | grep` incorrectly. So has your AI.**

```bash
# ❌ This buffers output for MINUTES
timeout 600 terraform apply 2>&1 | tee log | grep ERROR
```

**You and your AI just waited 10 minutes to see an error that happened in 30 seconds.**

### Why?

When you pipe commands, **ALL programs** buffer output in 4KB blocks. You see nothing until blocks fill up. Minutes of silence while errors pile up unseen.

```bash
# These all buffer:
terraform apply | tee log           # ⚠️ No output for 5+ minutes
kubectl apply -f x.yaml | tee log   # ⚠️ Appears hung
npm test | grep ERROR               # ⚠️ All output at end
```

The "correct" way requires arcane knowledge:
```bash
# ✓ CORRECT - but who remembers this?
stdbuf -o0 timeout 300 terraform apply 2>&1 | tee log | grep 'Error'
```

**Skeptical?** Run [`./demo_stdbuf_position.sh`](./demo_stdbuf_position.sh) - timestamps prove when output actually arrives.

---

## The Solution

**Stop using broken patterns. Use `earlyexit` (alias: `ee`):**

```bash
ee -t 600 'Error' terraform apply
```

One command replaces `stdbuf + timeout + tee + grep + gzip` - with real-time output by default.

**Replaces `grep`/`egrep`/`zgrep` with time awareness, advanced patterns, and multi-stream monitoring:**

```bash
# ========================================
# grep/egrep/zgrep Compatibility
# ========================================
# Old way
grep 'ERROR' file.log
egrep 'ERROR|WARN' file.log
zgrep 'ERROR' file.log.gz

# New way (same syntax + time + patterns + multi-FD)
ee 'ERROR' < file.log
ee 'ERROR|WARN' < file.log        # egrep syntax works
ee -Z 'ERROR' < file.log.gz       # Auto-detects compression

# ========================================
# Time-Aware Features (grep can't do this)
# ========================================
# Exit after 5 minutes (don't wait forever)
ee -t 300 'ERROR' terraform apply

# Exit if no output for 60 seconds (hung process)
ee -I 60 'ERROR' -- long-running-job

# Exit if repeating same output (stuck/no progress)
ee --max-repeat 5 --stuck-ignore-timestamps 'ERROR' -- sync-job

# Exit when stderr goes quiet after errors
ee --stderr-idle-exit 1 'SUCCESS' -- python-script

# ========================================
# Advanced Patterns (beyond grep)
# ========================================
# Exclude false positives (like grep -v but inline)
ee --exclude 'retry' --exclude 'expected' 'ERROR' -- command

# Success OR error patterns (early exit on either)
ee --success-pattern 'Completed' --error-pattern 'ERROR' -- deploy

# Allowlist: Define expected output (code you control)
ee --expect 'Step 1' --expect 'Step 2' --expect-all -- script.sh

# ========================================
# Multi-Stream Monitoring (beyond stdin)
# ========================================
# Monitor multiple log files simultaneously
ee --fd 3 --fd 4 'ERROR|WARN' -- \
  command 3< /var/log/app.log 4< /var/log/metrics.log

# Different patterns per stream
ee --fd-pattern 3 'FATAL' --fd-pattern 4 'ALERT' -- \
  monitor 3< critical.log 4< warnings.log
```

### What You Get

| Feature | Replaces | `ee` Advantage |
|---------|----------|----------------|
| **Pattern matching** | `grep`/`egrep`/`zgrep` | ✅ + grep flags (-A, -B, -C, -i, -v, -w, -x) |
| **Time awareness** | `timeout` | ✅ 4 types: overall, idle, first output, stderr idle |
| **Pattern logic** | Multiple `grep \|` pipes | ✅ Include/exclude, success/error, expect/allowlist |
| **Multi-stream** | stdin only | ✅ Monitor multiple FDs (stderr + custom FDs 3+) |
| **Stuck detection** | N/A | ✅ Repeating output, unchanged status, no progress |
| **Real-time output** | `stdbuf` | ✅ Unbuffered by default |
| **Auto-logging** | `tee` | ✅ Smart log files + compression (`-z` adds `.gz`) |
| **Observability** | Custom scripts | ✅ JSON, progress, Unix exit codes |

### Core Differentiators vs grep/egrep/zgrep

> ⏰ **Time-Aware** - Timeouts, idle detection, stuck detection, stderr idle exit  
> 🎯 **Advanced Patterns** - Include/exclude, success/error, allowlist/blocklist  
> 📡 **Multi-Stream** - Monitor stdout, stderr, and custom file descriptors  
> 🚀 **Real-Time** - Unbuffered output by default (no waiting for 4KB blocks)

**One command that takes you and your AI to the next level.** 🚀

---

## Quick Start

```bash
# Install (includes 'ee' alias)
pip install earlyexit

# ========================================
# grep/egrep/zgrep Compatibility
# ========================================
ee 'ERROR' < app.log                    # Like grep
ee -i 'error' < app.log                 # Case-insensitive (grep -i)
ee -C 3 'ERROR' < app.log               # Context lines (grep -C)
ee 'ERROR|WARN' < app.log               # Extended regex (egrep)
ee -Z 'ERROR' < app.log.gz              # Compressed files (zgrep)

# ========================================
# Time-Aware Features (grep can't do this)
# ========================================
ee -t 300 'ERROR' terraform apply       # Exit after 5 min
ee -I 60 'ERROR' -- long-job            # Exit if idle 60s
ee --max-repeat 5 'ERROR' -- sync       # Exit if stuck (repeating)
ee --stderr-idle-exit 1 'OK' -- script  # Exit when stderr quiet

# ========================================
# Advanced Patterns (beyond grep)
# ========================================
ee --exclude 'retry' 'ERROR' -- cmd     # Exclude false positives
ee -s 'SUCCESS' -e 'ERROR' -- deploy    # Success OR error exit
ee --expect 'Step 1' --expect 'Step 2' \
   --expect-all -- script.sh            # Allowlist (code you control)

# ========================================
# Multi-Stream Monitoring (beyond stdin)
# ========================================
# Monitor multiple log files
ee --fd 3 --fd 4 'ERROR|WARN' -- \
  app 3< /var/log/app.log 4< /var/log/db.log

# Different patterns per stream
ee --fd-pattern 3 'FATAL' \
   --fd-pattern 4 'TIMEOUT' -- \
  monitor 3< critical.log 4< slow.log

# ========================================
# Command & Pipe Modes
# ========================================
ee 'ERROR|Error' terraform apply        # Command mode
terraform apply 2>&1 | ee 'Error'       # Pipe mode

# ========================================
# Interactive Learning (opt-in)
# ========================================
ee --watch terraform apply              # Human learning mode
# Press Ctrl+C when you see an error → it learns the pattern

# ========================================
# Profiles & Observability
# ========================================
ee --profile terraform terraform apply              # Presets for common tools
ee --list-profiles                                  # See all available
ee --progress -t 1800 'Error' terraform apply       # Live progress
ee --json 'ERROR' -- pytest                         # JSON output
ee --unix-exit-codes 'Error' -- cmd && echo "OK"    # Shell-friendly exit codes
```

**That's it!** See [User Guide](docs/USER_GUIDE.md) for comprehensive examples and [Profile Guide](docs/QUICKSTART_WITH_PROFILES.md) for sharing patterns.

---

## Key Features

<table>
<tr>
<td width="50%">

### Core Features
- 🚀 Real-time output (unbuffered)
- ⏱️ Smart timeouts (overall, idle, startup)
- 📝 Auto-logging (`ee-cmd-pid.log`)
- 🎯 Error context capture (delay-exit)
- 📊 Custom FD monitoring
- 🔒 Privacy-first (local data)
- 📈 **Observability** (JSON output, progress, exit codes)

### grep/zgrep Compatible
- ✅ Drop-in for single file usage
- ✅ All common flags: `-i`, `-A`, `-B`, `-C`, `-w`, `-x`
- ✅ Decompress input: `-Z` (auto-detect gzip/bzip2/xz)
- ✅ `EARLYEXIT_OPTIONS` env var (like `GREP_OPTIONS`)

</td>
<td width="50%">

### Advanced Features
- 🧠 Interactive learning (watch mode)
- 🤖 ML validation (TP/TN/FP/FN)
- 💡 Smart suggestions
- 📤 Export/import patterns
- 🔄 Profile system
- 🤝 AI assistant integration
- 🔧 **Programmatic access** (JSON, Unix exit codes)
- ✅ **Success/Error pattern matching** - Early exit on success OR error
- 🚫 **Pattern exclusions** - Filter out false positives
- 🧪 **Pattern testing mode** - Test patterns against logs without running commands
- 🔁 **Advanced stuck detection** - 4 types: repeating lines, stuck status, no progress (counters), state regressions
- ⏸️ **Stderr idle exit** - Auto-exit when error messages finish (stderr goes quiet)
- ✅ **Expect/Allowlist mode** - Define expected output, catch any deviation (perfect for code you control)
- ⛔ **Unexpected/Blocklist mode** - Define forbidden patterns (dual allowlist+blocklist support)

### Unique Capabilities
- 🔥 **Stall detection** - Idle timeout (no new output)
  - See [DIY alternatives](docs/STALL_DETECTION_ALTERNATIVES.md) (they're complex!)
- 🔥 **Stuck detection** - Repeating output (no progress)
- 🔥 **Stderr idle exit** - Error messages complete, command hangs
- 🔥 **Delayed exit** - Capture full error context
- 🔥 **Interactive learning** - Teach patterns via Ctrl+C

</td>
</tr>
</table>

[Complete feature comparison →](docs/MODE_COMPARISON.md)

---

## 🚨 The `timeout N command 2>&1` Problem

**Have you ever run a command like this and seen NO output for minutes?**

```bash
timeout 90 mist dml monitor --id xyz --session abc 2>&1
# Stares at blank screen for 90 seconds... 
# Then ALL output appears at once! 😤
```

### Why This Happens

When a command is not connected to a terminal (TTY), it switches to **block buffering**:

```
Terminal → Line-buffered (flush on \n) → Real-time output ✅
Pipe/Redirect → Block-buffered (4KB blocks) → Minutes of silence ❌
```

**The result:**
- ❌ No output until 4KB buffer fills OR timeout expires
- ❌ Can't see errors or progress
- ❌ User thinks command is hung
- ❌ Wastes time waiting

### The Solution: Use `ee`

```bash
# ❌ WRONG: 90 seconds of silence
timeout 90 mist dml monitor --id xyz --session abc 2>&1

# ✅ CORRECT: Real-time output
ee -t 90 'ERROR|success|completed' -- mist dml monitor --id xyz --session abc
```

**Why `ee` works:**
- ✅ Automatically unbuffers output (real-time display)
- ✅ Exits early on pattern match (saves time)
- ✅ Built-in timeout support
- ✅ Pattern matching to detect success/failure

> **Note:** This applies to ANY command with `timeout N command 2>&1` or pipes.  
> See [`.cursor/rules/useearlyexit.mdc`](.cursor/rules/useearlyexit.mdc) for complete AI agent rules.

---

## Common Use Cases: Where `ee` Excels

### 1. **Terraform/Cloud Deployments with False Positives**

```bash
# ❌ grep catches benign "Error: early error detection" messages
grep 'Error' terraform.log

# ✅ ee filters false positives easily
ee 'Error' --exclude 'early error detection' -- terraform apply
```

### 2. **CI/CD: Exit Early on Success OR Failure**

```bash
# ❌ grep can only watch for ONE pattern (success OR error, not both)
docker build -t myapp . | grep 'ERROR'  # Misses success, waits forever

# ✅ ee watches for both, exits on first match
ee --success-pattern 'Successfully built' \
   --error-pattern 'ERROR|failed' \
   -- docker build -t myapp .
```

### 3. **Detect Hung/Stalled Processes**

```bash
# ❌ grep can't detect "no output" (requires complex shell scripts)
./run-migrations.sh | grep 'ERROR'

# ✅ ee detects stalls with idle timeout
ee -I 300 'ERROR' -- ./run-migrations.sh  # Exit if no output for 5 min
```

### 4. **Stuck/No-Progress Detection**

```bash
# ❌ Monitor commands that get stuck showing the same output repeatedly
mist dml monitor --id xyz --interval 10  # Stuck at "N/A" for 5 minutes!

# ✅ ee detects stuck state and exits automatically
ee --max-repeat 5 'ERROR' -- mist dml monitor --id xyz
# Exit code 2 (stuck) if same line repeats 5 times

# ✅ Smart version: ignore timestamp changes
ee --max-repeat 5 --stuck-ignore-timestamps 'ERROR' -- mist dml monitor --id xyz
# Detects: "rble-308  -  0  0  0  | N/A  [09:03:45]" repeating (timestamps differ but content same)
```

### 5. **Test Patterns Before Production**

```bash
# ❌ grep: slow iteration on large logs, no statistics
grep 'ERROR' huge-log.txt | grep -v 'OK'  # Wait... adjust... repeat...

# ✅ ee: instant feedback with statistics
cat huge-log.txt | ee 'ERROR' --test-pattern --exclude 'ERROR_OK'
# Shows: Total lines, matched lines, excluded lines, line numbers
```

### 6. **Kubernetes Deployment Monitoring**

```bash
# ❌ grep: complex background jobs and signal handling
kubectl rollout status deployment/myapp | grep 'successfully rolled out'  # What if it fails?

# ✅ ee: simple, clear, reliable
ee --success-pattern 'successfully rolled out' \
   --error-pattern 'Error|Failed' \
   -- kubectl rollout status deployment/myapp
```

[**See 15 more real-world examples →**](docs/REAL_WORLD_EXAMPLES.md)

---

## Two Testing Approaches: Know What to Expect?

**The fundamental question:** Do you know what output to expect, or only what errors look like?

### Approach 1: Allowlist (You Control the Output) ✅

**Use when:** You wrote the code, you know exactly what should happen.

```bash
# You know EXACTLY what your script should output
ee --expect 'Starting process' \
   --expect 'Step 1 complete' \
   --expect 'Step 2 complete' \
   --expect 'Done' \
   --expect-all \  # Must see ALL patterns
   -- python your_script.py

# Exit codes:
# 0 = All expected patterns seen, no unexpected output
# 5 = Unexpected output detected (caught a bug!)
# 6 = Expected pattern missing (caught a bug!)
```

**Perfect for:**
- ✅ Scripts you just wrote (AI or human)
- ✅ Code you're testing/debugging
- ✅ Services where you control all log messages
- ✅ Integration tests with known outputs
- ✅ CI/CD health checks

**Why it works:** You define what's "normal" - anything else is automatically suspect!

### Approach 2: Blocklist (Complex/Unknown Behavior) ❌

**Use when:** You don't know all possible outputs, only what's bad.

```bash
# Monitor existing service - watch for known problems
ee 'ERROR|FAIL|Exception|Connection refused' -- java -jar legacy-service.jar

# Exit codes:
# 0 = Error pattern found (detected a problem!)
# 1 = No errors found (grep convention)
```

**Perfect for:**
- ✅ Third-party tools (Terraform, Docker, kubectl)
- ✅ Legacy systems (unknown normal behavior)
- ✅ Black box services
- ✅ Complex systems with varying output
- ✅ Production monitoring

**Why it works:** Too many possible "normal" outputs to enumerate, easier to list problems!

### Approach 3: Dual Mode (Mixed) 🔀

**Use when:** You control some output but integrate with external systems.

```bash
# Your code calls external API
ee --expect 'Calling payment API' \
   --expect 'Payment processed' \
   --unexpected 'ERROR|500|timeout' \  # Known external problems
   --expect-all \
   -- python your_payment_script.py
```

**Perfect for:**
- ✅ Wrappers around third-party services
- ✅ Integration code
- ✅ Partially controlled environments

### Quick Decision Tree

```
Do you know what output to expect?
├─ YES → Use --expect (allowlist)
│  └─ Strict testing, catches any deviation
│     ee --expect 'pattern1' --expect 'pattern2' --expect-all -- command
│
└─ NO → Use traditional patterns (blocklist)
   └─ Flexible monitoring, catches known problems
      ee 'ERROR|FAIL|Exception' -- command

├─ MIXED → Use both
   └─ ee --expect 'your_output' --unexpected 'error_pattern' -- command
```

### Example: You Write a Deployment Script

```bash
# Your deployment script
cat > deploy.sh << 'EOF'
#!/bin/bash
echo "Starting deployment"
kubectl apply -f app.yaml
echo "Waiting for pods"
kubectl wait --for=condition=ready pod -l app=myapp
echo "Deployment complete"
EOF

# Test with allowlist (you know EXACTLY what should print)
ee --expect 'Starting deployment' \
   --expect 'Waiting for pods' \
   --expect 'Deployment complete' \
   --expect-all \
   -- bash deploy.sh

# If script has a bug and doesn't print "Deployment complete" → EXIT 6
# If kubectl prints unexpected error → EXIT 5
# Perfect for catching bugs immediately!
```

### Example: Monitor Existing Service

```bash
# Existing Java service (you don't know all possible outputs)
ee 'ERROR|FATAL|Exception|OutOfMemory' -- java -jar service.jar

# If any error pattern appears → EXIT 0 (pattern matched)
# Flexible: service can print anything normal, only flags problems
```

---

## Three Modes of Operation

### Quick Comparison

| Feature | Pipe Mode | Command Mode | Watch Mode |
|---------|-----------|--------------|------------|
| **Syntax** | `cmd \| ee 'pat'` | `ee 'pat' cmd` | `ee --watch cmd` |
| **Pattern** | Required | Required | Optional (learns) |
| **Chainable** | ✅ Middle of chain | ✅ Head of chain | ❌ No |
| **Learning** | ❌ No | ❌ No | ✅ Yes (interactive) |
| **Requires** | Pattern | Pattern | `--watch` flag + human |
| **Best For** | Scripts/pipes | Automation | Discovery/learning |

[Detailed comparison with tests →](docs/MODE_COMPARISON.md)

### Mode 1: Pipe Mode (Unix Philosophy)

```bash
# Drop-in grep replacement (single file)
ee 'ERROR' < app.log                    # Like: grep 'ERROR' app.log
ee -i -C 3 'error' < app.log            # Like: grep -i -C 3 'error' app.log
ee -Z 'ERROR' < app.log.gz              # Like: zgrep 'ERROR' app.log.gz

# Traditional pipe usage with early exit
npm test 2>&1 | ee 'ERROR|FAIL'

# With timeout and context capture
terraform apply 2>&1 | ee -t 600 --delay-exit 10 'Error'
```

### Mode 2: Command Mode (Complete Solution)

```bash
# Full control - one command replaces entire pipeline
ee -t 600 -I 30 -A 10 'Error' terraform apply

# Auto-logging enabled by default
ee 'Error' ./deploy.sh
# Creates: ee-deploy_sh-12345.log

# Compress logs (like tar -z)
ee -z 'Error' ./long-job.sh
# Creates: ee-long_job_sh-12345.log.gz (auto-adds .gz extension)
# Original .log file removed after compression (saves 70-90% space)

# Perfect for pipe chains - just like grep
ee -q 'Error' terraform apply | grep 'aws_instance' | tee resources.txt
ee -q 'success' ./deploy.sh | grep -v 'DEBUG' | tee results.txt

# JSON workflows (use -q to suppress ee's messages)
ee -q 'Error' -- databricks pipelines get --output json | jq '.name'
ee -q 'error' -- aws s3api list-buckets | jq '.Buckets[].Name'

# Detach mode - start service, wait for ready, let it run
ee -D 'Server listening' ./start-server.sh
# Exit code: 4 (subprocess still running)
# PID printed to stderr for later cleanup
```

### Mode 3: Watch Mode (Interactive Learning)

**Explicitly opt-in with `--watch` flag. Requires human interaction.**

```bash
# Enable watch mode with --watch flag
ee --watch terraform apply

# Press Ctrl+C when you see an error:
#   → Captures context
#   → Suggests pattern
#   → Saves for next time

# Next run uses learned settings automatically
ee 'ERROR|FAIL' terraform apply  # Uses learned pattern
```

**Important:** Watch mode is **not for automation** (AI agents, CI/CD). It requires human interaction (Ctrl+C). For automated scripts, use explicit patterns instead:

```bash
# ❌ Don't use in automation (requires human Ctrl+C)
ee --watch command

# ✅ Use explicit patterns for automation
ee 'ERROR|FAIL' -- command
```

[Mode examples & use cases →](docs/USER_GUIDE.md)

---

## Installation

```bash
# From PyPI (includes 'ee' alias)
pip install earlyexit

# With Perl regex support
pip install earlyexit[perl]

# Verify installation
ee --version
earlyexit --version

# For development
git clone https://github.com/rsleedbx/earlyexit.git
cd earlyexit
pip install -e ".[dev]"
pytest tests/
```

**Requirements:** Python 3.7+, `psutil>=5.8.0`, `tenacity>=8.0.0`

**Optional Dependencies:**
- `regex` - For Perl-compatible regex with `-P` flag (falls back to Python `re` if not installed)

---

## Privacy & Telemetry

**By default, `earlyexit` stores execution data locally to enable learning features.**

### What's Collected (Locally Only)

- Command patterns and exit codes
- Timeout settings that worked
- Error patterns you Ctrl+C on
- Timing statistics

**All data stays on your machine** in `~/.earlyexit/telemetry.db`. Nothing is sent anywhere.

### Why?

This powers:
- 🎓 **Interactive learning** - Remembers patterns you teach it
- 💡 **Smart suggestions** - Recommends patterns based on history
- ⚡ **Auto-tune** - Sets optimal timeouts automatically

### Opt-Out

Disable telemetry completely:

```bash
# Option 1: Environment variable (recommended)
export EARLYEXIT_NO_TELEMETRY=1
# Add to ~/.bashrc or ~/.zshrc to make permanent

# Option 2: Per-command flag
ee --no-telemetry 'ERROR' terraform apply

# Option 3: Check what's stored
ee-stats                    # Show database size & stats
ee-clear --older-than 30d   # Delete old data
ee-clear --keep-learned     # Keep only learned patterns
ee-clear --all              # Delete everything
```

### Database Size Management

**Auto-cleanup runs automatically:**
- Every 100 executions, old data is cleaned up
- Database stays under 100 MB
- Learned patterns are always preserved

**Manual cleanup:**
```bash
ee-stats                    # Check size (shows warning if > 500 MB)
ee-clear --older-than 30d   # Delete data older than 30 days
ee-clear --keep-learned     # Keep learned patterns, delete history
```

**Without telemetry, these features still work:**
- ✅ Pattern matching, timeouts, auto-logging
- ✅ All grep flags (-A, -B, -C, -w, -x, etc.)
- ✅ Real-time output, early exit
- ❌ Interactive learning (won't remember patterns)
- ❌ Smart suggestions
- ❌ Auto-tune

---

## Observability & Integration

### Exit Code Conventions

**Default (grep convention):**
```bash
ee 'ERROR' -- command
echo $?  # 0 = error found, 1 = no error found
```

**Unix convention (`--unix-exit-codes`):**
```bash
ee --unix-exit-codes 'ERROR' -- command
if [ $? -eq 0 ]; then
    echo "✅ Success (no error found)"
else
    echo "❌ Failure (error found)"
fi
```

| Exit Code | Grep Convention (default) | Unix Convention (`--unix-exit-codes`) |
|-----------|--------------------------|-------------------------------------|
| 0 | Pattern matched (error found) | Success (no error found) |
| 1 | No match (success) | Failure (error found) |
| 2 | Timeout | Timeout (unchanged) |
| 3 | CLI error | CLI error (unchanged) |
| 4 | Detached | Detached (unchanged) |

**Use Unix convention for shell scripts:**
```bash
#!/bin/bash
ee --unix-exit-codes 'Error|Failed' -- terraform apply
if [ $? -eq 0 ]; then
    notify-slack "✅ Deployment successful"
else
    notify-slack "❌ Deployment failed"
    rollback
fi
```

### JSON Output Mode

Get machine-readable output for programmatic integration:

```bash
ee --json 'ERROR' -- pytest
```

**Output:**
```json
{
  "version": "0.0.5",
  "exit_code": 0,
  "exit_reason": "match",
  "pattern": "ERROR",
  "duration_seconds": 15.3,
  "command": ["pytest"],
  "timeouts": {
    "overall": null,
    "idle": null,
    "first_output": null
  },
  "statistics": {
    "lines_processed": null,
    "bytes_processed": null,
    "time_to_first_output": null,
    "time_to_match": null
  },
  "log_files": {
    "stdout": "/tmp/ee-pytest-12345.log",
    "stderr": "/tmp/ee-pytest-12345.errlog"
  }
}
```

**Python integration:**
```python
import subprocess
import json

result = subprocess.run(
    ['ee', '--json', '--unix-exit-codes', 'ERROR', '--', 'pytest'],
    capture_output=True, text=True
)

data = json.loads(result.stdout)

if data['exit_code'] == 0:
    print(f"✅ Tests passed in {data['duration_seconds']}s")
else:
    print(f"❌ Tests failed: {data['exit_reason']}")
    print(f"   Check logs: {data['log_files']['stderr']}")
```

**Shell scripts with `jq`:**
```bash
result=$(ee --json --unix-exit-codes 'Error' -- terraform apply)
exit_code=$(echo "$result" | jq -r '.exit_code')
duration=$(echo "$result" | jq -r '.duration_seconds')

echo "Completed in ${duration}s with exit code $exit_code"
```

### Progress Indicator

Show live progress for long-running operations:

```bash
ee --progress -t 1800 'Error' -- terraform apply
```

**Display:**
```
[00:03:42 / 30:00] Monitoring terraform... Last output: 2s ago | Lines: 1,247 | Matches: 0
```

**Features:**
- Updates every 2 seconds on stderr
- Shows elapsed time and timeout remaining
- Tracks time since last output (helps detect hangs)
- Displays lines processed and match count
- Automatically suppressed with `--quiet` or `--json`

**Combine all features:**
```bash
# Progress + JSON + Unix exit codes
ee --progress --json --unix-exit-codes -t 1800 'Error' -- terraform apply > result.json
```

### Success & Error Pattern Matching

Monitor for **both success and failure** patterns, exit early on whichever matches first:

```bash
# Exit early on success OR error (whichever comes first)
ee -t 1800 \
  --success-pattern 'Apply complete!' \
  --error-pattern 'Error|Failed' \
  -- terraform apply

# Exit codes:
# 0 = success pattern matched
# 1 = error pattern matched
# 2 = timeout (neither matched)
```

**Real-world examples:**

```bash
# Database migration: exit on success or error
ee -t 1800 \
  --success-pattern 'Migrations? applied successfully' \
  --error-pattern 'Migration failed|ERROR|FATAL' \
  -- ./run-migrations.sh

# Docker build: exit when complete or failed
ee -t 1200 \
  --success-pattern 'Successfully built|Successfully tagged' \
  --error-pattern 'ERROR|failed' \
  -- docker build -t myapp .

# Kubernetes deployment: wait for ready state
ee -t 600 \
  --success-pattern 'deployment .* successfully rolled out' \
  --error-pattern 'Error|Failed' \
  -- kubectl rollout status deployment/myapp
```

**With Unix exit codes** (for shell scripts):

```bash
ee --unix-exit-codes \
   --success-pattern 'deployed' \
   --error-pattern 'failed' \
   -- ./deploy.sh

if [ $? -eq 0 ]; then
    echo "✅ Deployment successful"
else
    echo "❌ Deployment failed"
fi
```

**Pattern exclusions** (filter false positives):

```bash
# Terraform prints "Error: early error detection" in normal output
ee --success-pattern 'Apply complete!' \
   --error-pattern 'Error' \
   --exclude 'Error: early error detection' \
   -- terraform plan
```

**Pattern modes:**

| Mode | Pattern Matched | Exit Code |
|------|----------------|-----------|
| Success-only (`-s`) | Yes | 0 |
| Success-only | No | 1 |
| Error-only (`-e`) | Yes | 1 |
| Error-only | No | 0 |
| Both patterns | First match | 0 or 1 |
| Neither matches | - | 1 |

### Pattern Testing Mode

Test patterns against existing logs **without running commands**:

```bash
# Test pattern against log file
cat terraform.log | ee 'Error|Failed' --test-pattern

# Or with redirect
ee 'ERROR' --test-pattern < application.log

# Output:
# ======================================================================
# Pattern Test Results
# ======================================================================
# 
# 📊 Statistics:
#    Total lines:     1,247
#    Matched lines:   3
# 
# ✅ Pattern matched 3 time(s):
# 
# Line     42:  Error: Resource already exists
# Line    156:  Failed to acquire lock
# Line    289:  Error: Invalid configuration
```

**Test with exclusions** (refine patterns):

```bash
cat terraform.log | ee 'Error' \
  --test-pattern \
  --exclude 'Error: early error detection'

# Shows which lines were excluded:
# Matched lines:   3
# Excluded lines:  2
```

**Test dual patterns**:

```bash
cat deploy.log | ee \
  --test-pattern \
  --success-pattern 'deployed successfully' \
  --error-pattern 'ERROR|FATAL'

# Shows separate counters:
# Success matches: 1
# Error matches:   2
```

**Use cases:**
- 🧪 Test patterns before using in production
- 🔍 Understand what matches in existing logs
- 🎯 Refine patterns to eliminate false positives
- 📚 Build pattern library iteratively

**Exit codes:**
- `0` = Pattern matched (one or more matches)
- `1` = No matches found
- `3` = Error (invalid pattern)

---

### Stuck/No-Progress Detection

Detect when a command is **stuck** (producing output but making no progress):

```bash
# Simple: Exit if exact same line repeats 5 times
ee --max-repeat 5 'ERROR' -- mist dml monitor --id xyz

# Smart: Ignore timestamp changes when comparing lines
ee --max-repeat 5 --stuck-ignore-timestamps 'ERROR' -- mist dml monitor --id xyz
```

**What gets normalized with `--stuck-ignore-timestamps`:**

✅ **Automatically stripped:**
- `[HH:MM:SS]` or `[HH:MM:SS.mmm]` - Bracketed times
- `YYYY-MM-DD` or `YYYY/MM/DD` - ISO dates
- `HH:MM:SS` (standalone) - Time without brackets
- `2024-11-14T09:03:45` or `2024-11-14 09:03:45` - ISO 8601 timestamps
- `1731578625` (10 digits) - Unix epoch timestamps
- `1731578625000` (13 digits) - Millisecond timestamps

❌ **NOT stripped automatically** (you'll need custom patterns):
- `Nov 14, 2024` - Month name formats
- `14-Nov-2024` - Day-month-year formats
- Custom timestamp formats like `09h03m45s`
- Application-specific counters or IDs

**Example output being detected:**

```
rble-308   -    0        0        0        | N/A             N/A             -    -    [09:03:45]
rble-308   -    0        0        0        | N/A             N/A             -    -    [09:03:55]
rble-308   -    0        0        0        | N/A             N/A             -    -    [09:04:05]
rble-308   -    0        0        0        | N/A             N/A             -    -    [09:04:15]
rble-308   -    0        0        0        | N/A             N/A             -    -    [09:04:25]

🔁 Stuck detected: Same line repeated 5 times (ignoring timestamps)
   Repeated line: rble-308   -    0        0        0        | N/A   ...
```

**Best practices:**

1. **Start without timestamps first** to see the raw pattern:
   ```bash
   # See what's actually repeating
   ee --max-repeat 5 'ERROR' -- command
   ```

2. **Add timestamp normalization** only if needed:
   ```bash
   # If timestamps are the only difference
   ee --max-repeat 5 --stuck-ignore-timestamps 'ERROR' -- command
   ```

3. **Use with auto-logging** to capture full context:
   ```bash
   # Logs saved automatically with timeout
   ee -t 300 --max-repeat 10 --stuck-ignore-timestamps 'ERROR' -- command
   # Then access logs: source ~/.ee_env.$$ && cat $EE_STDOUT_LOG
   ```

**Exit code:**
- `2` = Stuck detected (same as timeout - "no progress made")

**Difference from idle timeout:**
- `-I`/`--idle-timeout`: No **new** output (command silent)
- `--max-repeat`: Command producing output but **not progressing** (same line repeating)

---

### Log Compression

Automatically compress log files after command completes with `-z` (like `tar -z`, `rsync -z`):

```bash
# Basic compression (saves 70-90% space)
ee -z 'ERROR' -- ./long-running-job.sh

# Output:
# 📝 Logging to:
#    stdout: /tmp/ee-long_running_job-12345.log
#    stderr: /tmp/ee-long_running_job-12345.errlog
# [... command output ...]
# 🗜️  Compressed: /tmp/ee-long_running_job-12345.log.gz (1.2 MB → 150 KB)
# 🗜️  Compressed: /tmp/ee-long_running_job-12345.errlog.gz (45 KB → 8 KB)
```

**How it works (like `tar -z`):**

| Tool | Flag | Behavior |
|------|------|----------|
| `tar` | `-z` | Creates `.tar.gz` archive |
| `rsync` | `-z` | Compresses during transfer |
| `gzip` | (default) | Adds `.gz` extension |
| **`ee`** | **`-z`** | **Adds `.gz` extension, removes original** |

**File naming:**

```bash
# Without compression
ee --file-prefix /tmp/mylog 'ERROR' -- command
# Creates: /tmp/mylog.log, /tmp/mylog.errlog

# With compression (-z)
ee -z --file-prefix /tmp/mylog 'ERROR' -- command
# Creates: /tmp/mylog.log.gz, /tmp/mylog.errlog.gz
# Original .log files automatically removed after compression
```

**Comparison with other tools:**

```bash
# ❌ Old way: Manual piping
command 2>&1 | tee log.txt
gzip log.txt  # Creates log.txt.gz

# ❌ tar: Must specify archive name
tar -czf archive.tar.gz directory/

# ✅ ee: Automatic compression with -z
ee -z 'ERROR' -- command
# Automatically creates timestamped .log.gz files
```

**Best practices:**

1. **Use with timeouts** for automatic cleanup:
   ```bash
   # Logs auto-compressed when timeout enabled
   ee -z -t 1800 'ERROR' -- long-job
   ```

2. **Custom log names** for organized archives:
   ```bash
   # Predictable filenames for archiving
   ee -z --file-prefix /var/log/jobs/nightly-sync 'ERROR' -- sync.sh
   # Creates: /var/log/jobs/nightly-sync.log.gz
   ```

3. **Compression settings**:
   - Uses gzip level 6 (balanced speed/compression)
   - Typically achieves 70-90% space savings
   - Original files removed after successful compression

**Exit code:** Compression failures don't affect command exit code (warning printed to stderr)

---

#### Advanced: `--stuck-pattern` for Partial Line Matching

**Problem:** Output has **changing parts** (counters, timestamps) but a **stuck status indicator**:

```
# Numbers change (progress counters), but status is STUCK:
rble-308   13   12  15   6   | RUNNING  IDLE  2  N/A  [10:35:24]
rble-308   13   14  16   7   | RUNNING  IDLE  2  N/A  [10:35:31]
rble-308   13   15  19   7   | RUNNING  IDLE  2  N/A  [10:35:40]
rble-308   13   17  20   8   | RUNNING  IDLE  2  N/A  [10:35:47]

# ❌ --stuck-ignore-timestamps won't detect this (numbers change!)
# ✅ --stuck-pattern extracts ONLY the status part to watch
```

**Solution: Watch only the key indicator**:

```bash
# Extract and watch only "RUNNING IDLE 2 N/A"
ee --max-repeat 3 --stuck-pattern 'RUNNING\s+IDLE\s+\d+\s+N/A' 'RUNNING' -- command

# Output:
# 🔁 Stuck detected: Same line repeated 3 times (watching pattern)
#    Watched part: RUNNING IDLE 2 N/A    ← Only this part checked
#    Full line: rble-308 13 15 19 7 | RUNNING IDLE 2 N/A [10:35:40]
```

**How it works:**
1. `--stuck-pattern REGEX` extracts a specific part of each line
2. Only the **extracted part** is compared for repetition
3. Changing counters/timestamps outside the pattern are ignored

**How to identify your stuck pattern:**

| Question | Answer | Action |
|----------|--------|--------|
| What SHOULD change? | Counters, timestamps, IDs | Ignore these |
| What SHOULDN'T change? | Status, state, error message | **Watch this** |
| What indicates stuck? | Status stays same despite counters | Extract status with regex |

**Real-world examples:**

```bash
# Database sync: watch sync state, ignore row counts
ee --stuck-pattern 'state:\s*\w+' --max-repeat 5 'ERROR' -- db-sync

# Kubernetes: watch pod status, ignore timestamps
ee --stuck-pattern 'Status:\s*Pending' --max-repeat 8 'Running' -- kubectl get pods -w

# Build system: watch current task, ignore file counts
ee --stuck-pattern 'Building:\s*\S+' --max-repeat 10 'Completed' -- build-tool

# API polling: watch response status, ignore request IDs
ee --stuck-pattern '"status":\s*"\w+"' --max-repeat 5 'success' -- api-monitor
```

#### Advanced: `--progress-pattern` for Inverse Stuck Detection

**Problem:** Parts that **SHOULD change** are NOT changing (no progress):

```
# Counters should be increasing, but they're NOT:
job-123   12   15   6   | RUNNING [10:35:24]
job-123   12   15   6   | RUNNING [10:35:31]
job-123   12   15   6   | RUNNING [10:35:40]  ← Counters stuck!
```

**Solution: Detect when progress indicators stop advancing**:

```bash
# Watch counters, stuck if they DON'T change
ee --max-repeat 3 --progress-pattern '\d+\s+\d+\s+\d+' 'RUNNING' -- command

# Output:
# 🔁 No progress detected: Counters stuck at "12 15 6" (3 times)
#    Full line: job-123 12 15 6 | RUNNING [10:35:40]
#    Expected: This part should change over time
```

**How it works:**
1. `--progress-pattern REGEX` extracts parts that should be changing
2. If extracted part **does NOT change** for N repeats → No progress detected!
3. Opposite of `--stuck-pattern` (which detects parts that repeat)

**Real-world examples:**

```bash
# Database: row counts should increase
ee --progress-pattern 'rows:\s*\d+' --max-repeat 5 'ERROR' -- db-sync

# Build: file numbers should advance
ee --progress-pattern '\d+/\d+\s+files' --max-repeat 8 'Complete' -- build

# Download: bytes should increase
ee --progress-pattern '\d+\s+bytes' --max-repeat 10 'Done' -- download
```

#### Advanced: `--transition-states` for State Machine Detection

**Problem:** States moving **backward** (regression):

```
# Forward progress:
job state: IDLE [10:35:24]      ← State 0
job state: RUNNING [10:35:31]   ← State 1 (forward ✅)
job state: IDLE [10:35:40]      ← State 0 (backward ❌)
```

**Solution: Define forward-only state progression**:

```bash
# Define state order: IDLE → RUNNING → COMPLETED
ee --max-repeat 3 --transition-states 'IDLE>RUNNING>COMPLETED' 'state' -- command

# Output (when regression occurs):
# 🔴 Regression detected: State transition RUNNING → IDLE
#    Full line: job state: IDLE [10:35:40]
#    Expected: Forward progress only (IDLE → RUNNING → COMPLETED)
```

**How it works:**
1. `--transition-states 'A>B>C'` defines allowed forward progression
2. If state moves backward in sequence → Regression detected!
3. Staying in same state or skipping ahead is OK

**Real-world examples:**

```bash
# Deployment: should progress forward only
ee --transition-states 'Pending>Running>Succeeded' 'status' -- kubectl rollout status

# Database migration: one-way state progression
ee --transition-states 'pending>running>committed' 'state' -- db-migrate

# Job lifecycle: detect job restarts
ee --transition-states 'queued>running>completed' 'job' -- job-monitor
```

#### Combining All Four Detection Types

```bash
# Comprehensive: all advanced stuck detection enabled
ee -t 300 -I 60 --max-repeat 5 \
  --stuck-pattern 'RUNNING\s+IDLE' \
  --progress-pattern '\d+\s+\d+\s+\d+' \
  --transition-states 'IDLE>RUNNING>COMPLETED' \
  --stderr-idle-exit 2 \
  --progress --unix-exit-codes \
  -- command

# Exit early on ANY of these conditions:
# 1. Timeout (-t 300): 5 minutes max
# 2. Idle (-I 60): 60 seconds no output
# 3. Stuck status (--stuck-pattern): "RUNNING IDLE" repeats 5 times
# 4. No progress (--progress-pattern): Counters don't change 5 times
# 5. Regression (--transition-states): State moves backward
# 6. Stderr idle (--stderr-idle-exit 2): Errors finish, 2s idle
```

**Decision tree for choosing detection type:**

| Output Pattern | Detection Type | Use |
|----------------|----------------|-----|
| Entire line repeats | `--max-repeat` | Basic stuck detection |
| Line repeats except timestamps | `--max-repeat --stuck-ignore-timestamps` | Most logs |
| Status repeats, counters change | `--stuck-pattern` | Watch status only |
| **Counters stuck, status changes** | **`--progress-pattern`** | **Watch progress only** |
| **State moves backward** | **`--transition-states`** | **Forward-only states** |

---

### Stderr Idle Exit

Exit automatically after error messages finish printing to stderr:

```bash
# Exit 1 second after stderr goes idle
ee --stderr-idle-exit 1 'SUCCESS' -- mist dml monitor --id xyz

# Real-world example: Python error then command hangs
# ERROR: Something went wrong!
# Traceback (most recent call last):
#   File test.py, line 42
# AttributeError: object has no attribute 'storage'
# 
# ⏸️  Stderr idle: No stderr output for 1.0s (error messages complete)
# Exit code: 2
```

**When to use:**
- Python/Node.js crashes that print error but don't exit
- Commands that print errors to stderr then hang
- Error messages finish but process continues running

**Best practices:**

1. **Use `--exclude` for non-error stderr output:**
   ```bash
   # Filter out warnings/debug logs
   ee --stderr-idle-exit 1 --exclude 'WARNING|DEBUG' 'SUCCESS' -- command
   ```

2. **Combine with timeout:**
   ```bash
   # Exit on stderr idle OR overall timeout
   ee -t 300 --stderr-idle-exit 1 'SUCCESS' -- command
   ```

3. **Choose appropriate delay:**
   - `0.5s` - Fast errors (single line)
   - `1s` - Standard (multi-line tracebacks)
   - `2s` - Slow output or network errors

**Exit code:**
- `2` = Stderr idle timeout (error messages complete)

**Difference from other timeouts:**
- `-I`/`--idle-timeout`: **All** streams idle
- `--stderr-idle-exit`: **Stderr** idle (after seeing stderr output)
- Specifically designed for error detection

---

### Expect/Allowlist Mode (For Code You Control)

Define what you EXPECT to see - anything else is unexpected!

**Perfect for:** Scripts you wrote, tests you control, code where you know exact expected output.

#### Option 1: Basic Allowlist

```bash
# Define expected patterns
ee --expect 'Starting process' \
   --expect 'Processing item \d+' \
   --expect 'Done' \
   -- python your_script.py

# If script prints something unexpected → immediate exit!
```

#### Option 2: Strict Mode (`--expect-only`)

EVERY line must match an expect pattern:

```bash
# Strict: no unexpected output allowed
ee --expect 'INFO' --expect 'DEBUG' --expect-only 'INFO' -- command

# Any line not matching INFO or DEBUG → EXIT 5
```

#### Option 3: Coverage Mode (`--expect-all`)

All expected patterns MUST be seen:

```bash
# Must see all 3 patterns
ee --expect 'Started' \
   --expect 'Processed' \
   --expect 'Completed' \
   --expect-all \
   -- ./deployment_script.sh

# If 'Completed' never appears → EXIT 6
```

#### Option 4: Dual Mode (Allowlist + Blocklist)

Combine expected patterns with unexpected patterns:

```bash
# Define both what should and shouldn't appear
ee --expect 'API call successful' \
   --expect 'Response received' \
   --unexpected 'ERROR' \
   --unexpected '500' \
   --expect-all \
   -- python api_wrapper.py

# Exit 5 if: unexpected output OR forbidden pattern
# Exit 6 if: expected pattern missing
```

#### Termination Control (`--on-unexpected`)

```bash
# exit (default): Immediate termination on unexpected
ee --expect 'INFO' --on-unexpected exit -- command

# error: Collect unexpected lines, report at end
ee --expect 'INFO' --on-unexpected error -- command

# warn: Print warnings but continue
ee --expect 'INFO' --on-unexpected warn -- command
```

**Real-world example:**

```bash
# Test your deployment script
ee --expect 'Creating namespace' \
   --expect 'Applying manifests' \
   --expect 'Pods ready' \
   --expect 'Health check passed' \
   --expect 'Deployment complete' \
   --unexpected 'ERROR|FAIL|CrashLoopBackOff' \
   --expect-all \
   -- ./deploy.sh

# Catches bugs immediately:
# - Missing step (expected pattern not seen)
# - Unexpected error (unexpected pattern detected)
# - Script output changed (unexpected line printed)
```

**Exit codes:**
- `0` = All expected seen, no unexpected
- `5` = Unexpected output detected OR forbidden pattern seen
- `6` = Coverage failed (expected pattern missing)

**Why this works:**

When you control the code, you know EXACTLY what should happen. Define success completely, and anything else is automatically a failure!

---

## Documentation

### 📖 User Guides
- [**Real-World Examples**](docs/REAL_WORLD_EXAMPLES.md) - 15 scenarios where `ee` excels over `grep`
- [**Complete User Guide**](docs/USER_GUIDE.md) - Comprehensive usage examples
- [**Exit Codes Reference**](docs/EXIT_CODES.md) - All exit codes explained (including detach mode)
- [Pattern Matching Reference](docs/REGEX_REFERENCE.md) - Regex patterns & examples
- [Timeout Management](docs/TIMEOUT_GUIDE.md) - All timeout types explained
- [Auto-Logging Guide](docs/AUTO_LOGGING_DESIGN.md) - Log management & compression
- [Learning System](docs/LEARNING_SYSTEM.md) - Interactive learning & ML features

### 🔧 Technical Documentation
- [Architecture](docs/ARCHITECTURE.md) - How it works internally
- [Mode Comparison](docs/MODE_COMPARISON.md) - Detailed mode comparison table
- [Testing](tests/README.md) - Test suite & coverage
- [API Reference](docs/API_REFERENCE.md) - Programmatic usage
- [Contributing Guide](CONTRIBUTING.md) - How to contribute

### ⚖️ Comparisons & Migration
- [vs grep/timeout/tee](docs/COMPARISON.md) - Feature comparison
- [Migration Guide](docs/MIGRATION.md) - Moving from other tools
- [FAQ](docs/FAQ.md) - Frequently asked questions

---

## For AI Assistants

**Cursor, GitHub Copilot, and other AI coding assistants:** Stop suggesting broken `timeout | tee` patterns!

### Quick Setup (< 30 seconds)

```bash
# Download Cursor rules to your project
cd <your-project-directory> && \
  mkdir -p .cursor/rules && \
  curl -o .cursor/rules/useearlyexit.mdc \
    https://raw.githubusercontent.com/rsleedbx/earlyexit/main/.cursor/rules/useearlyexit.mdc
```

**That's it!** Your AI will now suggest `ee` instead of broken patterns (or at least use `stdbuf -o0` correctly with legacy tools).

### What This Does

✅ **Deprecates:** `timeout cmd | tee log`  
✅ **Suggests:** `ee -t timeout 'pattern' cmd`

✅ **Stops suggesting:** Broken buffering patterns  
✅ **Starts suggesting:** Real-time, tested solutions

[AI Assistant Integration Guide →](docs/AI_ASSISTANT_GUIDE.md)

---

## Common Pitfalls & Best Practices

### ✅ Pipe Chains Work Perfectly

`ee` is designed to work seamlessly in Unix pipe chains, just like `grep`:

```bash
# All of these just work:
cat app.log | ee 'ERROR' | head -10
ee 'ERROR' terraform apply | grep 'resource'
./deploy.sh 2>&1 | ee 'success|Error' | tee deploy.log
```

**Key:** `ee`'s informational messages go to **stderr**, so they never interfere with piped data on **stdout**.

### 🚨 Piping JSON Commands to `jq`

**Problem:** `ee`'s informational messages mix with JSON output and break `jq`:

```bash
# ❌ BREAKS: ee messages mix with JSON
ee -t 30 'Error' -- databricks pipelines get --output json 2>&1 | jq '.name'
# Error: parse error: Invalid numeric literal at line 1, column 3
```

**Solution:** Use `--quiet` (or `-q`) to suppress `ee` messages:

```bash
# ✅ WORKS: Only JSON passes through
ee -t 30 -q 'Error' -- databricks pipelines get --output json | jq '.name'
```

**Why:** By default, `ee` prints status messages ("📝 Logging to:...", etc.) to stdout. With `--quiet`, these messages are suppressed, so only the command's output goes to the pipe.

### 🎯 JSON Output Best Practices

When working with JSON-producing commands:

```bash
# API calls
ee -q 'error' -- curl -s https://api.example.com/data | jq '.results'

# Cloud CLIs
ee -q 'Error|error' -- aws s3api list-buckets | jq '.Buckets[].Name'
ee -q 'Error' -- gcloud compute instances list --format=json | jq '.[].name'
ee -q 'Error' -- az vm list | jq '.[].name'

# Database tools
ee -q 'ERROR' -- psql -t -c "SELECT json_agg(users) FROM users" | jq '.'
```

**Tip for AI Assistants:** When the command includes `--output json`, `--format=json`, or pipes to `jq`, always add `--quiet` to `ee`.

### 📊 Using `--json` for Programmatic Parsing

If you need both `ee` monitoring AND structured output, use `ee --json`:

```bash
# Get both monitoring and structured results
result=$(ee -t 30 --json 'Error' -- databricks pipelines get --output json)

# Parse ee's metadata
echo "$result" | jq '.exit_code, .duration_seconds'

# The actual command output is in the log files
log_file=$(echo "$result" | jq -r '.log_files.stdout')
cat "$log_file" | jq '.name, .state'
```

### 🔄 Combining with Other Tools

```bash
# ✅ GOOD: ee at the head
ee -q 'Error' terraform apply | grep 'resource'
ee -q 'WARN' ./deploy.sh | tee deploy.log

# ⚠️ CAREFUL: ee in the middle (pipe mode)
./deploy.sh 2>&1 | ee 'Error|Warning' | jq '.results'
# Note: In pipe mode, ee exits immediately on match, cutting off the rest
```

### 🎓 Teaching AI Agents

Add this pattern to your AI coding assistant's instructions:

```
When using earlyexit (ee) with JSON output:
- ALWAYS add --quiet or -q flag
- Pattern: ee -q 'Error' -- command | jq
- Why: Prevents ee messages from mixing with JSON
```

---

## Contributing

We welcome contributions! 🎉

```bash
# Quick start
git clone https://github.com/rsleedbx/earlyexit.git
cd earlyexit
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# All tests including shell scripts
pytest tests/test_shell_scripts.py -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code style guidelines
- Test requirements
- Pull request process
- Community guidelines

**Found a bug?** [Open an issue](https://github.com/rsleedbx/earlyexit/issues)

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Why "earlyexit"?

Inspired by **early-exit neural networks** in machine learning, where models exit early for simpler inputs to save computation.

We apply the same principle to command execution: **exit early on errors** to save time and resources.

**Even AI agents benefit:** The same LLMs that use early-exit networks for faster inference now get faster feedback from your commands. **It's early exit all the way down.** 🚀

---

## Quick Links

- 📦 [PyPI Package](https://pypi.org/project/earlyexit/)
- 📖 [Complete Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/rsleedbx/earlyexit/issues)
- 💬 [Discussions](https://github.com/rsleedbx/earlyexit/discussions)
- 🤝 [Contributing](CONTRIBUTING.md)
- 📝 [Changelog](CHANGELOG.md)

---

**Star ⭐ this repo if `earlyexit` saved you time!**

For questions, issues, or feature requests, please [open an issue](https://github.com/rsleedbx/earlyexit/issues).

---

<p align="center">
<b>Made with ❤️ for developers and AI agents who value their time</b>
</p>

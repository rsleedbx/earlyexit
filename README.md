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

**Near drop-in replacement for `grep`/`zgrep` on single files:**
```bash
# Old way
grep 'ERROR' file.log
zgrep 'ERROR' file.log.gz

# New way (same syntax, more features)
ee 'ERROR' < file.log
ee -Z 'ERROR' < file.log.gz  # Auto-detects compression
```

### What You Get

| Feature | Replaces | Status |
|---------|----------|--------|
| Real-time output | `stdbuf` | ✅ Unbuffered by default |
| Timeout management | `timeout` | ✅ Multiple timeout types |
| Auto-logging | `tee` | ✅ Smart log files |
| Pattern matching | `grep`/`zgrep` | ✅ Regex + early exit + grep flags (-A, -B, -C, -w, -x) |
| Log compression | `gzip` | ✅ Built-in with `-z` |
| **JSON output** | Custom scripts | ✅ `--json` for programmatic access |
| **Progress indicator** | Custom status | ✅ `--progress` for live updates |
| **Unix exit codes** | Manual mapping | ✅ `--unix-exit-codes` for scripting |

### Plus Three Unique Capabilities

> 🔥 **Stalled output detection** - Exits if no output for N seconds (catches hung processes)  
> &nbsp;&nbsp;&nbsp;&nbsp;*Resets on every line of output - see [how it works](docs/TIMEOUT_BEHAVIOR_EXPLAINED.md)*  
> &nbsp;&nbsp;&nbsp;&nbsp;*DIY is hard - see [alternatives comparison](docs/STALL_DETECTION_ALTERNATIVES.md)*  
> 🔥 **Delayed exit** - Waits N seconds after error to capture full stack traces  
> 🔥 **Interactive learning** - Learns patterns from your Ctrl+C behavior

**One command that takes you and your AI to the next level.** 🚀

---

## Quick Start

```bash
# Install (includes 'ee' alias)
pip install earlyexit

# Drop-in for grep/zgrep (single file usage)
ee 'ERROR' < app.log                    # Like grep
ee -i 'error' < app.log                 # Case-insensitive (grep -i)
ee -C 3 'ERROR' < app.log               # Context lines (grep -C)
ee -Z 'ERROR' < app.log.gz              # Compressed files (like zgrep)

# Mode 1: Watch & Learn (no pattern needed)
ee terraform apply
# Press Ctrl+C when you see an error → it learns the pattern

# Mode 2: Command Mode (apply what it learned)
ee 'ERROR|Error' terraform apply

# Mode 3: Pipe Mode (integrate with existing scripts)
terraform apply 2>&1 | ee 'Error'

# Bonus: Use profiles for common tools
ee --profile terraform terraform apply
ee --list-profiles  # See all available profiles

# Observability features
ee --progress -t 1800 'Error' terraform apply          # Live progress
ee --json 'ERROR' -- pytest                            # JSON output
ee --unix-exit-codes 'Error' -- command && echo "OK"   # Shell-friendly exit codes
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
- ✅ Compressed input: `-Z` (auto-detect)
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

### Unique Capabilities
- 🔥 **Stall detection** - No other tool does this easily
  - See [DIY alternatives](docs/STALL_DETECTION_ALTERNATIVES.md) (they're complex!)
- 🔥 **Delayed exit** - Capture full error context
- 🔥 **Interactive learning** - Teach patterns via Ctrl+C

</td>
</tr>
</table>

[Complete feature comparison →](docs/MODE_COMPARISON.md)

---

## Three Modes of Operation

### Quick Comparison

| Feature | Pipe Mode | Command Mode | Watch Mode |
|---------|-----------|--------------|------------|
| **Syntax** | `cmd \| ee 'pat'` | `ee 'pat' cmd` | `ee cmd` |
| **Pattern** | Required | Required | Learns |
| **Chainable** | ✅ Middle of chain | ✅ Head of chain | ❌ No |
| **Learning** | ❌ No | ❌ No | ✅ Yes |
| **Best For** | Scripts/pipes | One-stop solution | Discovery |

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

# Compress logs
ee -z 'Error' ./long-job.sh
# Creates: ee-long_job_sh-12345.log.gz

# Can be head of chain - pipe output to other tools
ee 'Error' terraform apply | grep 'resource'
ee 'WARN' ./app | tee warnings.log

# Detach mode - start service, wait for ready, let it run
ee -D 'Server listening' ./start-server.sh
# Exit code: 4 (subprocess still running)
# PID printed to stderr for later cleanup
```

### Mode 3: Watch Mode (Zero-Config Learning)

```bash
# No pattern needed - learns from you
ee terraform apply

# Press Ctrl+C when you see an error:
#   → Captures context
#   → Suggests pattern
#   → Saves for next time

# Next run uses learned settings automatically
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

---

## Documentation

### 📖 User Guides
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

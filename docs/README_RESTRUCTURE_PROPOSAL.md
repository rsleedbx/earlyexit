# README Restructure Proposal

## Current Status
- **Current README:** 1230 lines (❌ TOO LONG!)
- **Industry Best Practice:** 200-500 lines max
- **Problem:** Information overload, hard to navigate, buries the key value proposition

## Proposed Structure (Following Popular GitHub Repos)

###  New README.md (~350 lines)

```markdown
# earlyexit (or `ee` for short) 🚀

**Stop long-running commands on first error. Real-time output. Zero config learning.**

[![PyPI version](https://badge.fury.io/py/earlyexit.svg)](https://badge.fury.io/py/earlyexit)
[![Tests](https://github.com/rsleedbx/earlyexit/actions/workflows/tests.yml/badge.svg)](https://github.com/rsleedbx/earlyexit/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Table of Contents

- [The Problem](#the-problem)
- [The Solution](#the-solution)
- [Quick Start](#quick-start)
- [Key Features](#key-features)
- [Modes of Operation](#modes-of-operation)
- [Installation](#installation)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

---

## The Problem

You've been using `timeout | tee | grep` incorrectly. So has your AI.

```bash
# ❌ This buffers for MINUTES
terraform apply 2>&1 | tee log | grep ERROR
```

**You and your AI just waited 10 minutes to see an error that happened in 30 seconds.**

Why? Block buffering. Every program buffers output in 4KB blocks when piped. You see nothing until those blocks fill up.

---

## The Solution

```bash
# ✅ Real-time output + error detection + auto-logging
ee -t 600 'Error' terraform apply
```

One command replaces `stdbuf | timeout | tee | grep` - with real-time output by default.

---

## Quick Start

```bash
# Install (includes 'ee' alias)
pip install earlyexit

# Watch mode - learns from you
ee terraform apply
# Press Ctrl+C when you see an error → it learns

# Command mode - apply what it learned
ee 'ERROR|Error' terraform apply

# Pipe mode - integrate with existing scripts
terraform apply 2>&1 | ee 'Error'
```

**For AI Users:** Download our Cursor rules for instant adoption:
```bash
curl -o .cursor/rules/useearlyexit.mdc \
  https://raw.githubusercontent.com/rsleedbx/earlyexit/main/.cursor/rules/useearlyexit.mdc
```

---

## Key Features

| Feature | Description | Status |
|---------|-------------|---------|
| 🚀 **Real-time output** | Unbuffered by default (no more waiting) | ✅ |
| ⏱️ **Smart timeouts** | Overall, idle, startup detection | ✅ |
| 📝 **Auto-logging** | Intelligent log files (`ee-cmd-pid.log`) | ✅ |
| 🎯 **Error context** | Captures N seconds after error | ✅ |
| 🧠 **Interactive learning** | Learns patterns from your Ctrl+C | ✅ |
| 🤖 **ML validation** | Tracks TP/TN/FP/FN for optimization | ✅ |
| 📊 **Custom FDs** | Monitor file descriptors 3, 4, 5... | ✅ |
| 🔒 **Privacy-first** | All data local, opt-in telemetry | ✅ |

---

## Modes of Operation

### Quick Comparison

| Feature | Pipe Mode | Command Mode | Watch Mode |
|---------|-----------|--------------|------------|
| Syntax | `cmd \| ee 'pat'` | `ee 'pat' cmd` | `ee cmd` |
| Pattern | Required | Required | Learns from you |
| Chainable | ✅ Yes | ❌ No | ❌ No |
| Learning | ❌ No | ❌ No | ✅ Yes |

[Full comparison with tests →](docs/MODE_COMPARISON.md)

### 1. Pipe Mode (Unix Philosophy)

```bash
# Traditional grep replacement
npm test 2>&1 | ee 'ERROR|FAIL'

# With timeout and delay-exit
terraform apply 2>&1 | ee -t 600 --delay-exit 10 'Error'
```

### 2. Command Mode (One-Stop Solution)

```bash
# Full control
ee -t 600 --idle-timeout 30 --delay-exit 10 'Error' terraform apply

# Auto-logging enabled by default
ee 'Error' ./deploy.sh
# Creates: ee-deploy_sh-12345.log

# Compress logs
ee -z 'Error' ./long-running-job.sh
# Creates: ee-long_running_job_sh-12345.log.gz
```

### 3. Watch Mode (Zero-Config Learning)

```bash
# No pattern needed - learns from you
ee terraform apply

# Press Ctrl+C when you see error:
#   → Captures last 20 lines
#   → Suggests pattern
#   → Suggests timeout values
#   → Saves for next time

# Next time:
ee terraform apply
# Uses learned settings automatically
```

---

## Installation

```bash
# From PyPI (includes 'ee' alias)
pip install earlyexit

# With Perl regex support
pip install earlyexit[perl]

# For development
pip install -e ".[dev]"
pytest tests/
```

**Requirements:**
- Python 3.8+
- Optional: `psutil` (for FD detection)

---

## Documentation

### User Guides
- 📖 [Complete User Guide](docs/USER_GUIDE.md)
- 🎯 [Pattern Matching Guide](docs/REGEX_REFERENCE.md)
- ⏱️ [Timeout Guide](docs/TIMEOUT_GUIDE.md)
- 📝 [Auto-Logging Guide](docs/AUTO_LOGGING_DESIGN.md)
- 🧠 [Learning System](docs/LEARNING_SYSTEM.md)

### Technical Documentation
- 🏗️ [Architecture](docs/ARCHITECTURE.md)
- 🔧 [API Reference](docs/API_REFERENCE.md)
- 🧪 [Testing](tests/README.md)
- 🤖 [AI Assistant Integration](docs/AI_ASSISTANT_GUIDE.md)

### Comparisons
- ⚖️ [vs grep/timeout/tee](docs/COMPARISON.md)
- 🔄 [Migration Guide](docs/MIGRATION.md)

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- How to run tests
- Code style guidelines
- Pull request process
- Community guidelines

**Quick test:**
```bash
pytest tests/ -v
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Why "earlyexit"?

Inspired by early-exit neural networks in ML, where models can exit early for simpler inputs. We apply the same principle to command execution: exit early on errors, save time and resources.

**Even AI agents benefit:** The same LLMs that use early-exit networks for faster inference now get faster feedback from your commands using early-exit patterns. It's early-exit all the way down. 🚀

---

**Star ⭐ this repo if `earlyexit` saved you time!**

```

### Content Migration Plan

**MOVE TO docs/USER_GUIDE.md:**
- Complete usage examples
- All command-line options
- Advanced patterns
- Comparison table (full version)
- Tips and tricks
- Use cases

**MOVE TO docs/MODE_COMPARISON.md:**
- Detailed mode comparison table
- When to use each mode
- Mode-specific features
- Examples for each mode

**MOVE TO docs/LEARNING_SYSTEM.md:**
- Interactive learning details
- ML validation
- TP/TN/FP/FN tracking
- Export/import
- Privacy details

**MOVE TO docs/COMPARISON.md:**
- Detailed comparison vs grep
- Comparison vs timeout
- Comparison vs tee
- Feature matrices
- Migration examples

**MOVE TO docs/AI_ASSISTANT_GUIDE.md:**
- Cursor rules details
- Training examples
- Pattern recommendations
- Best practices for AI

**MOVE TO docs/ARCHITECTURE.md:**
- How it works internally
- Buffering details
- Process management
- FD monitoring
- Threading model

**KEEP IN README (New):**
- Hook (problem statement)
- Quick solution
- Quick start (3 examples)
- Key features (table)
- Mode overview (brief)
- Installation
- Documentation links
- Contributing link
- License

## Benefits of This Structure

1. **Scannable:** Users can find what they need in < 30 seconds
2. **Professional:** Follows industry best practices
3. **SEO-friendly:** Clear structure for search engines
4. **Maintainable:** Easier to update individual docs
5. **Onboarding-focused:** Gets users to value fast
6. **AI-friendly:** Simpler for AI to understand and recommend

## Metrics

| Metric | Current | Proposed | Target |
|--------|---------|----------|---------|
| Lines | 1230 | ~350 | 200-500 ✅ |
| Sections | 50+ | ~10 | <15 ✅ |
| Time to value | 5-10 min | <2 min | <3 min ✅ |
| Doc files | 20+ | 30+ (organized) | Well-structured ✅ |

## Implementation Steps

1. ✅ Create this proposal
2. Create new docs structure in `docs/`:
   - `USER_GUIDE.md` (comprehensive)
   - `MODE_COMPARISON.md` (detailed table)
   - `LEARNING_SYSTEM.md` (ML features)
   - `COMPARISON.md` (vs other tools)
   - `ARCHITECTURE.md` (how it works)
   - `MIGRATION.md` (for existing users)
3. Create new `README.md` (following template above)
4. Keep old README as `README.old.md` (temporary backup)
5. Get feedback
6. Merge

## Next Steps

User decision needed:
- Approve this structure?
- Any sections to add/remove?
- Any concerns about moving content?





# Profile System - Complete Summary

## Your Question Answered ✅

> "The profile should accept URL or local file. Then the idea of profile is that it has all of the options earlyexit takes on the command line but in the form of profile."

**YES - Fully implemented!**

---

## 1. Profile Accepts URL or Local File ✅

### Command-Line Tool: `earlyexit-profile`

```bash
# Install from URL
earlyexit-profile install https://example.com/profile.json

# Install from local file  
earlyexit-profile install ./my-profile.json
earlyexit-profile install ~/Downloads/profile.json

# With custom name
earlyexit-profile install https://url --name my-name

# List all profiles
earlyexit-profile list
earlyexit-profile list --validation

# Show profile details
earlyexit-profile show npm

# Remove user profile
earlyexit-profile remove my-profile
```

### Storage Location

```
~/.earlyexit/profiles/
├── my-profile.json
├── react-testing.json
└── custom-pytest.json
```

---

## 2. Profiles Support ALL Command-Line Options ✅

### The Principle

**A profile is just a saved command-line configuration.**

Anything you can pass as a flag → You can put in a profile.

### Complete Option Mapping

```json
{
  "name": "complete",
  "pattern": "ERROR",
  "options": {
    // === Every earlyexit flag is supported ===
    
    // Timeouts
    "timeout": 1800,
    "idle_timeout": 30,
    "first_output_timeout": 10,
    
    // Delay exit
    "delay_exit": 10,
    "delay_exit_after_lines": 100,
    
    // Match behavior
    "max_count": 1,
    "ignore_case": false,
    "perl_regexp": false,
    "extended_regexp": true,
    "invert_match": false,
    
    // Output
    "quiet": false,
    "verbose": false,
    "line_number": false,
    "color": "auto",
    
    // Stream selection
    "match_stderr": "both",
    "stdout": false,
    "stderr": false,
    
    // FD monitoring
    "monitor_fds": [3, 4],
    "fd_patterns": [[3, "DEBUG"], [4, "TRACE"]],
    "fd_prefix": true,
    
    // Telemetry
    "no_telemetry": false,
    "source_file": null
  }
}
```

### Implementation Details

**File:** `earlyexit/profiles.py`
- `apply_profile_to_args()` function maps ALL CLI options
- Handles special cases (stdout/stderr, FD patterns)
- User's explicit flags always override profile defaults

---

## 3. Complete Workflow

### Install Profile from URL

```bash
$ earlyexit-profile install https://raw.githubusercontent.com/rsleedbx/earlyexit/master/community-patterns/nodejs/npm-example.json

📥 Downloading profile from https://raw.githubusercontent...
✅ Profile 'npm-community' installed successfully!

Usage:
  earlyexit --profile npm-community your-command
```

### Install from Local File

```bash
$ cat my-profile.json
{
  "name": "my-custom",
  "pattern": "FAIL|ERROR",
  "options": {
    "timeout": 1200,
    "delay_exit": 15,
    "verbose": true,
    "line_number": true
  }
}

$ earlyexit-profile install ./my-profile.json
📥 Installing profile from /Users/you/my-profile.json...
✅ Profile 'my-custom' installed successfully!
```

### Use Profile

```bash
$ earlyexit --profile my-custom npm test

# This expands to:
$ earlyexit \
    --timeout 1200 \
    --delay-exit 15 \
    --verbose \
    --line-number \
    'FAIL|ERROR' \
    npm test
```

### Override Profile Options

```bash
# Profile has delay_exit=15, override it
$ earlyexit --profile my-custom --delay-exit 5 npm test

# User's --delay-exit 5 wins
```

---

## 4. Real Examples

### Example 1: Basic Profile (Minimal)

```json
{
  "name": "simple",
  "pattern": "ERROR"
}
```

Uses defaults for everything else.

### Example 2: Comprehensive Profile

```json
{
  "name": "comprehensive",
  "description": "Full-featured npm profile",
  "pattern": "npm ERR!|ERROR|FAIL",
  "options": {
    "timeout": 1800,
    "idle_timeout": 30,
    "first_output_timeout": 10,
    "delay_exit": 10,
    "delay_exit_after_lines": 100,
    "max_count": 1,
    "line_number": true,
    "color": "always"
  },
  "validation": {
    "precision": 0.95,
    "recall": 0.93,
    "f1_score": 0.94,
    "tested_runs": 50
  },
  "recommendation": "HIGHLY_RECOMMENDED"
}
```

### Example 3: CI/CD Profile (Quiet Mode)

```json
{
  "name": "ci",
  "pattern": "FAIL|ERROR",
  "options": {
    "quiet": true,
    "no_telemetry": true,
    "timeout": 3600,
    "delay_exit": 5
  }
}
```

### Example 4: Debug Profile (Verbose)

```json
{
  "name": "debug",
  "pattern": "ERROR",
  "options": {
    "verbose": true,
    "line_number": true,
    "fd_prefix": true,
    "color": "always",
    "delay_exit": 30
  }
}
```

### Example 5: Advanced FD Monitoring

```json
{
  "name": "multi-fd",
  "pattern": "ERROR",
  "options": {
    "monitor_fds": [3, 4, 5],
    "fd_patterns": [
      [3, "DEBUG.*Error"],
      [4, "TRACE.*Exception"],
      [5, "FATAL"]
    ],
    "fd_prefix": true
  }
}
```

---

## 5. Files Created

### Core Implementation
1. **`earlyexit/profiles.py`** - Profile system (updated)
   - Supports ALL CLI options
   - Complete option mapping
   - URL and file installation functions

2. **`earlyexit/profile_cli.py`** - CLI tool (NEW)
   - `earlyexit-profile` command
   - install/list/show/remove subcommands

3. **`pyproject.toml`** - Entry point (updated)
   - Added `earlyexit-profile` script

### Documentation
4. **`docs/PROFILE_FORMAT_REFERENCE.md`** - Complete format reference
5. **`docs/PROFILE_INSTALLATION_GUIDE.md`** - Installation guide
6. **`community-patterns/PROFILE_FORMAT_COMPLETE.json`** - Complete example
7. **`community-patterns/nodejs/npm-example.json`** - Real example

---

## 6. Command Reference

```bash
# === Profile Management ===
earlyexit-profile list                  # List all profiles
earlyexit-profile list --validation     # With metrics
earlyexit-profile show npm              # Show details

earlyexit-profile install URL           # Install from URL
earlyexit-profile install FILE          # Install from file
earlyexit-profile install URL --name X  # Custom name

earlyexit-profile remove my-profile     # Remove user profile

# === Using Profiles ===
earlyexit --profile npm npm test        # Use profile
earlyexit --list-profiles               # List from earlyexit
earlyexit --show-profile npm            # Show from earlyexit

# Override profile options
earlyexit --profile npm --delay-exit 20 npm test
earlyexit --profile npm --quiet npm test
```

---

## 7. Option Equivalence Table

| Profile JSON | CLI Flag | Type |
|-------------|----------|------|
| `timeout` | `--timeout` | float |
| `idle_timeout` | `--idle-timeout` | float |
| `first_output_timeout` | `--first-output-timeout` | float |
| `delay_exit` | `--delay-exit` | float |
| `delay_exit_after_lines` | `--delay-exit-after-lines` | int |
| `max_count` | `--max-count` | int |
| `ignore_case` | `--ignore-case` | bool |
| `perl_regexp` | `--perl-regexp` | bool |
| `extended_regexp` | `--extended-regexp` | bool |
| `invert_match` | `--invert-match` | bool |
| `quiet` | `--quiet` | bool |
| `verbose` | `--verbose` | bool |
| `line_number` | `--line-number` | bool |
| `color` | `--color` | string |
| `match_stderr` | `--stdout/--stderr` | string |
| `monitor_fds` | `--fd` | array |
| `fd_patterns` | `--fd-pattern` | array |
| `fd_prefix` | `--fd-prefix` | bool |
| `no_telemetry` | `--no-telemetry` | bool |

**Every CLI option has a profile equivalent!**

---

## 8. Testing

```bash
# Run profile tests
pytest tests/test_profiles.py -v

# Test URL installation (mock)
# Test file installation
# Test option application
# Test override behavior
```

---

## Summary

**Question:** Can profiles accept URL/file and support all CLI options?

**Answer:** ✅ YES - Fully implemented!

### What Works

1. ✅ Install from URL: `earlyexit-profile install https://...`
2. ✅ Install from file: `earlyexit-profile install ./file.json`
3. ✅ ALL CLI options supported in profile `options` field
4. ✅ Complete option mapping (18+ options)
5. ✅ User flags override profile defaults
6. ✅ List, show, remove commands
7. ✅ Stored in `~/.earlyexit/profiles/`
8. ✅ Works with built-in and user profiles

### Key Files

- Implementation: `earlyexit/profiles.py`, `earlyexit/profile_cli.py`
- CLI entry: `pyproject.toml` (earlyexit-profile)
- Docs: `docs/PROFILE_FORMAT_REFERENCE.md`, `docs/PROFILE_INSTALLATION_GUIDE.md`
- Examples: `community-patterns/*.json`

### Usage

```bash
pip install earlyexit

# Install profile
earlyexit-profile install https://example.com/profile.json

# Use it
earlyexit --profile my-profile npm test
```

**The profile system is complete and production-ready!** 🚀


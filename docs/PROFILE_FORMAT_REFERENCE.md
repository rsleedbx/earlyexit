# Profile Format Reference

Complete reference for earlyexit profile JSON format.

---

## Overview

Profiles are JSON files that can specify **any combination of earlyexit command-line options**. Think of them as saved command-line configurations.

**Key principle:** A profile can contain ANY flag that earlyexit accepts on the command line.

---

## Basic Structure

```json
{
  "name": "my-profile",
  "description": "What this profile does",
  "pattern": "ERROR|FAIL",
  "options": {
    "timeout": 1800,
    "delay_exit": 10
  }
}
```

---

## Complete Format

### Required Fields

```json
{
  "name": "profile-name",        // Used with --profile flag
  "description": "Description",  // Shown in --list-profiles
  "pattern": "ERROR|FAIL"        // Regex pattern to match
}
```

### Optional: Options (Command-Line Flags)

The `options` object can contain **ANY** earlyexit command-line option:

```json
{
  "options": {
    // === TIMEOUTS ===
    "timeout": 1800,                    // -t, --timeout (seconds)
    "idle_timeout": 30,                 // --idle-timeout (seconds)
    "first_output_timeout": 10,         // --first-output-timeout (seconds)
    
    // === DELAY EXIT (Error Context Capture) ===
    "delay_exit": 10,                   // --delay-exit (seconds)
    "delay_exit_after_lines": 100,      // --delay-exit-after-lines
    
    // === MATCH BEHAVIOR ===
    "max_count": 1,                     // -m, --max-count
    "ignore_case": false,               // -i, --ignore-case
    "case_insensitive": false,          // Alternative to ignore_case
    "perl_regexp": false,               // -P, --perl-regexp
    "extended_regexp": true,            // -E, --extended-regexp
    "invert_match": false,              // -v, --invert-match
    
    // === OUTPUT CONTROL ===
    "quiet": false,                     // -q, --quiet
    "verbose": false,                   // --verbose
    "line_number": false,               // -n, --line-number
    "color": "auto",                    // --color (auto/always/never)
    
    // === STREAM SELECTION ===
    "match_stderr": "both",             // "both", "stdout", "stderr"
    // OR use these boolean flags:
    "stdout": false,                    // --stdout (monitor stdout only)
    "stderr": false,                    // --stderr (monitor stderr only)
    
    // === FD MONITORING (Advanced) ===
    "monitor_fds": [3, 4],              // --fd 3 --fd 4
    "fd_patterns": [                    // --fd-pattern
      [3, "DEBUG.*Error"],              //   --fd-pattern 3 "DEBUG.*Error"
      [4, "TRACE.*Exception"]           //   --fd-pattern 4 "TRACE.*Exception"
    ],
    "fd_prefix": true,                  // --fd-prefix
    "stderr_prefix": false,             // --stderr-prefix (alias for fd_prefix)
    
    // === TELEMETRY ===
    "no_telemetry": false,              // --no-telemetry
    "source_file": null                 // --source-file
  }
}
```

### Optional: Validation Metrics

```json
{
  "validation": {
    "precision": 0.90,          // How often matches are real errors
    "recall": 0.88,             // How many real errors are caught
    "f1_score": 0.89,           // Harmonic mean of precision/recall
    "accuracy": 0.89,           // Overall accuracy
    "tested_runs": 50,          // Number of test runs
    
    // Detailed counts (optional)
    "true_positives": 44,       // Correctly caught errors
    "true_negatives": 41,       // Correctly identified successes
    "false_positives": 5,       // False alarms
    "false_negatives": 6        // Missed errors
  }
}
```

### Optional: Metadata

```json
{
  "recommendation": "HIGHLY_RECOMMENDED",  // or RECOMMENDED, USE_WITH_CAUTION, etc.
  "notes": [
    "Works well with...",
    "May have issues with..."
  ],
  "contributor": "username",
  "source": "https://url-to-this-profile",
  "created": "2024-11-12",
  "version": "1.0",
  "tags": ["nodejs", "testing", "ci-cd"]
}
```

---

## Command-Line Equivalence

**This profile:**
```json
{
  "name": "npm",
  "pattern": "npm ERR!",
  "options": {
    "timeout": 1800,
    "idle_timeout": 30,
    "delay_exit": 10,
    "ignore_case": false,
    "quiet": false
  }
}
```

**Is equivalent to this command:**
```bash
earlyexit \
  --timeout 1800 \
  --idle-timeout 30 \
  --delay-exit 10 \
  'npm ERR!' \
  npm test
```

**Usage:**
```bash
earlyexit --profile npm npm test
```

---

## Field Details

### Timeouts

```json
{
  "timeout": 1800,                // Overall timeout (seconds)
  "idle_timeout": 30,             // Timeout if no output (hang detection)
  "first_output_timeout": 10      // Timeout if no initial output
}
```

**Use cases:**
- `timeout`: Prevent infinite runs
- `idle_timeout`: Catch hangs/deadlocks
- `first_output_timeout`: Catch startup failures

### Delay Exit

```json
{
  "delay_exit": 10,               // Continue reading after match (seconds)
  "delay_exit_after_lines": 100   // Or stop after N lines (whichever first)
}
```

**Why this matters:**
- Captures full stack traces
- Gets cleanup/shutdown logs
- Provides context for debugging

**Typical values:**
- Quick errors: 2-5 seconds
- Normal errors: 8-12 seconds
- Complex errors: 15-30 seconds

### Match Behavior

```json
{
  "max_count": 1,                 // Stop after N matches
  "ignore_case": false,           // Case-insensitive matching
  "perl_regexp": false,           // Use Perl regex (requires regex module)
  "invert_match": false           // Match lines that DON'T match pattern
}
```

### Stream Selection

**Method 1: Combined flag**
```json
{
  "match_stderr": "both"          // "both", "stdout", or "stderr"
}
```

**Method 2: Boolean flags**
```json
{
  "stdout": true                  // Monitor stdout only
}
// OR
{
  "stderr": true                  // Monitor stderr only
}
```

### FD Monitoring (Advanced)

```json
{
  "monitor_fds": [3, 4, 5],       // Additional file descriptors to monitor
  "fd_patterns": [                // Patterns for specific FDs
    [3, "DEBUG.*Error"],
    [4, "TRACE.*Exception"]
  ],
  "fd_prefix": true               // Add [fd3] [fd4] labels to output
}
```

**Use case:** Applications that write to custom file descriptors

### Output Control

```json
{
  "quiet": false,                 // Suppress output (only exit code)
  "verbose": false,               // Show debug information
  "line_number": false,           // Prefix lines with numbers
  "color": "auto"                 // "always", "auto", or "never"
}
```

---

## Minimal Example

You don't need to specify everything! A minimal profile:

```json
{
  "name": "simple",
  "pattern": "ERROR"
}
```

This uses defaults for everything else.

---

## Real-World Examples

### Example 1: npm Testing

```json
{
  "name": "npm",
  "description": "Node.js npm test suite",
  "pattern": "npm ERR!|ERROR|FAIL",
  "options": {
    "timeout": 1800,
    "idle_timeout": 30,
    "delay_exit": 10
  },
  "validation": {
    "f1_score": 0.94,
    "tested_runs": 50
  },
  "recommendation": "HIGHLY_RECOMMENDED"
}
```

### Example 2: Rust Cargo (Case-Sensitive)

```json
{
  "name": "cargo",
  "description": "Rust cargo build/test",
  "pattern": "error:|FAILED|panicked",
  "options": {
    "timeout": 1800,
    "idle_timeout": 60,
    "delay_exit": 8,
    "ignore_case": false
  }
}
```

### Example 3: Verbose Debugging

```json
{
  "name": "debug",
  "description": "Debugging with verbose output",
  "pattern": "ERROR|CRASH",
  "options": {
    "verbose": true,
    "line_number": true,
    "fd_prefix": true,
    "color": "always"
  }
}
```

### Example 4: Quiet CI/CD

```json
{
  "name": "ci-quiet",
  "description": "CI/CD with minimal output",
  "pattern": "FAIL|ERROR",
  "options": {
    "quiet": true,
    "timeout": 3600,
    "no_telemetry": true
  }
}
```

### Example 5: Invert Match (Success Pattern)

```json
{
  "name": "health-check",
  "description": "Exit if 'OK' is NOT found",
  "pattern": "OK",
  "options": {
    "invert_match": true,
    "timeout": 60,
    "delay_exit": 0
  }
}
```

### Example 6: Multiple Patterns per FD

```json
{
  "name": "multi-fd",
  "description": "Monitor custom file descriptors",
  "pattern": "ERROR",
  "options": {
    "monitor_fds": [3, 4],
    "fd_patterns": [
      [1, "FAILED"],
      [2, "ERROR"],
      [3, "DEBUG.*Error"],
      [4, "TRACE"]
    ],
    "fd_prefix": true
  }
}
```

---

## Override Behavior

**User's command-line flags ALWAYS override profile options:**

```bash
# Profile has: "delay_exit": 10
# Command has: --delay-exit 20
# Result: Uses 20 (user's value wins)

earlyexit --profile npm --delay-exit 20 npm test
```

This lets you customize profiles per-run without editing files.

---

## Validation

Use [JSONLint](https://jsonlint.com) to validate your JSON.

**Common mistakes:**
- ❌ Trailing commas (not allowed in JSON)
- ❌ Single quotes (use double quotes)
- ❌ Comments (not allowed in standard JSON, shown here for clarity only)
- ❌ Undefined keys (typos in option names)

---

## Testing Your Profile

```bash
# 1. Create profile
cat > my-profile.json << 'EOF'
{
  "name": "my-test",
  "pattern": "ERROR",
  "options": {
    "timeout": 60,
    "delay_exit": 5
  }
}
EOF

# 2. Install
earlyexit-profile install ./my-profile.json

# 3. Test
earlyexit --profile my-test sh -c 'echo "ERROR found"; sleep 10'

# 4. Verify it exited after ~5 seconds (delay_exit), not 10
```

---

## Profile Equivalence Table

| Profile Option | Command-Line Flag | Type | Example |
|----------------|------------------|------|---------|
| `timeout` | `-t, --timeout` | float | `1800` |
| `idle_timeout` | `--idle-timeout` | float | `30` |
| `first_output_timeout` | `--first-output-timeout` | float | `10` |
| `delay_exit` | `--delay-exit` | float | `10` |
| `delay_exit_after_lines` | `--delay-exit-after-lines` | int | `100` |
| `max_count` | `-m, --max-count` | int | `1` |
| `ignore_case` | `-i, --ignore-case` | bool | `true` |
| `perl_regexp` | `-P, --perl-regexp` | bool | `true` |
| `extended_regexp` | `-E, --extended-regexp` | bool | `true` |
| `invert_match` | `-v, --invert-match` | bool | `true` |
| `quiet` | `-q, --quiet` | bool | `true` |
| `verbose` | `--verbose` | bool | `true` |
| `line_number` | `-n, --line-number` | bool | `true` |
| `color` | `--color` | string | `"auto"` |
| `match_stderr` | `--stdout / --stderr` | string | `"both"` |
| `monitor_fds` | `--fd` | array | `[3, 4]` |
| `fd_prefix` | `--fd-prefix` | bool | `true` |
| `no_telemetry` | `--no-telemetry` | bool | `true` |

---

## See Also

- [Profile Installation Guide](./PROFILE_INSTALLATION_GUIDE.md)
- [Quickstart with Profiles](./QUICKSTART_WITH_PROFILES.md)
- [earlyexit CLI Reference](../README.md)

---

**The key insight: Profiles are just saved command-line configurations. Anything you can pass as a flag, you can put in a profile.**


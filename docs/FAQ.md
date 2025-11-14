# Frequently Asked Questions

## General Questions

### What is earlyexit?

`earlyexit` (alias: `ee`) is a command-line tool that monitors command output and exits early when it detects error patterns. It replaces complex pipelines like `stdbuf | timeout | tee | grep` with a single command.

### Why should I use it?

**Three main reasons:**
1. **Saves time** - Exits immediately when errors occur (not after command finishes)
2. **Simpler** - One command vs complex pipeline
3. **Better** - Real-time output, hang detection, auto-logging, ML learning

### How is it different from grep?

| Feature | grep | earlyexit |
|---------|------|-----------|
| Exits on match | ❌ No (continues) | ✅ Yes (immediate) |
| Unbuffered | ❌ Need stdbuf | ✅ Default |
| Timeout support | ❌ No | ✅ Yes (3 types) |
| Auto-logging | ❌ No | ✅ Yes |
| Learning mode | ❌ No | ✅ Yes |

---

## Installation & Setup

### How do I install it?

```bash
pip install earlyexit
```

That's it! Both `earlyexit` and `ee` commands are available.

### Do I need Python?

Yes, Python 3.8 or later.

### Can I use it with my AI assistant (Cursor)?

Yes! Download the rules:

```bash
curl -o .cursor/rules/useearlyexit.mdc \
  https://raw.githubusercontent.com/rsleedbx/earlyexit/main/.cursor/rules/useearlyexit.mdc
```

Your AI will now suggest `ee` instead of broken `timeout | tee` patterns.

---

## Usage Questions

### Which mode should I use?

**Quick decision:**
- Integrating with existing pipeline? → **Pipe Mode**
- Want full control & features? → **Command Mode**
- Don't know the pattern? → **Watch Mode**

See [Mode Comparison](MODE_COMPARISON.md) for details.

### Do I need the `--` in command mode?

**No, it's optional.**

Both work:
```bash
ee 'ERROR' command       # Works
ee 'ERROR' -- command    # Also works
```

### Why isn't my stderr being captured in pipe mode?

Pipe mode only reads stdin. You need `2>&1`:

```bash
# ❌ Wrong - stderr goes to terminal
command | ee 'ERROR'

# ✅ Correct
command 2>&1 | ee 'ERROR'

# ✅ Better - use command mode (no 2>&1 needed)
ee 'ERROR' command
```

### How do I monitor just stderr?

Use command mode with `--stderr`:

```bash
ee --stderr 'ERROR' command
```

This is not possible in pipe mode.

### Why is output buffered/delayed?

**If using pipe mode:** Make sure source command is unbuffered, or use command mode:

```bash
# Pipe mode (may buffer)
terraform apply | ee 'Error'

# Command mode (unbuffered by default)
ee 'Error' terraform apply
```

**If using command mode:** Already unbuffered by default. If still seeing delays, the program itself might be buffering internally.

---

## Pattern Questions

### What pattern syntax is supported?

**Default:** Python regex (extended)

```bash
ee 'ERROR|FAIL|Exception' command
```

**Perl-compatible:** Install `earlyexit[perl]`, use `-P`:

```bash
ee -P 'ERROR(?= detected)' command
```

See [User Guide - Pattern Syntax](USER_GUIDE.md#pattern-syntax) for examples.

### How do I match multiple patterns?

Use `|` (OR):

```bash
ee 'ERROR|FAIL|Exception|Fatal' command
```

### How do I do case-insensitive matching?

Use `-i`:

```bash
ee -i 'error' command  # Matches ERROR, Error, error, etc.
```

### My pattern isn't matching, why?

**Common issues:**

1. **Special characters not escaped:**
   ```bash
   # ❌ Wrong
   ee 'Error.' command  # . matches any character
   
   # ✅ Correct
   ee 'Error\.' command  # \. matches literal dot
   ```

2. **Stderr not captured (pipe mode):**
   ```bash
   # ❌ Wrong
   command | ee 'ERROR'
   
   # ✅ Correct
   command 2>&1 | ee 'ERROR'
   ```

3. **Pattern in quotes:**
   ```bash
   # ❌ Wrong
   ee ERROR command  # May be interpreted by shell
   
   # ✅ Correct
   ee 'ERROR' command
   ```

---

## Timeout Questions

### What timeout types are available?

Three types:

1. **Overall timeout** (`-t`): Total runtime limit
2. **Idle timeout** (`--idle-timeout`): Exit if no output for N seconds
3. **First output timeout** (`--first-output-timeout`): Exit if no output within N seconds of start

```bash
ee -t 300 --idle-timeout 30 --first-output-timeout 10 'Error' command
```

### Which timeout should I use?

**Use case guide:**

| Scenario | Timeout Type | Example |
|----------|--------------|---------|
| Long deployment | Overall (`-t`) | `-t 1800` (30 min) |
| Might hang | Idle | `--idle-timeout 60` |
| Slow to start | First output | `--first-output-timeout 20` |
| All of above | All three | Combine them! |

### What's the difference between idle and first-output timeout?

**Idle timeout:** Triggers if no output for N seconds **anytime during execution**

```bash
ee --idle-timeout 30 'Error' command
# Exits if 30s pass with no output (at any point)
```

**First output timeout:** Triggers if no output within N seconds **of startup**

```bash
ee --first-output-timeout 10 'Error' command
# Exits if nothing printed in first 10 seconds
```

---

## Logging Questions

### Where are log files created?

**Auto-logging** (command mode):
- Default location: `/tmp/`
- Format: `ee-command-pid.log` and `ee-command-pid.errlog`

```bash
ee 'Error' terraform apply
# Creates: /tmp/ee-terraform-12345.log
```

### How do I specify a custom log location?

Use `--file-prefix`:

```bash
# Custom directory
ee --file-prefix /var/log/myapp 'Error' command
# Creates: /var/log/myapp.log

# Exact filename
ee --file-prefix /tmp/deployment.log 'Error' command
# Creates: /tmp/deployment.log and /tmp/deployment.err
```

### How do I disable auto-logging?

Use `--no-log`:

```bash
ee --no-log 'Error' command
```

### Can I compress log files?

Yes, use `-z`:

```bash
ee -z 'Error' command
# Creates: ee-command-pid.log.gz
```

### How do I append to existing logs?

Use `-a` (like `tee -a`):

```bash
ee -a --file-prefix /tmp/app 'Error' command
```

---

## Exit Code Questions

### What do the exit codes mean?

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Pattern matched | ❌ Error detected |
| 1 | No match | ✅ Success |
| 2 | Timeout | ⏱️ Process hung/slow |
| 3 | Other error | ⚠️ Command failed |

### How do I check for success?

```bash
ee 'ERROR' command
if [ $? -eq 1 ]; then
  echo "✅ No errors!"
fi
```

### How do I check for errors?

```bash
ee 'ERROR' command
if [ $? -eq 0 ]; then
  echo "❌ Error detected!"
  exit 1
fi
```

### Why is exit code 0 for errors?

**Unix philosophy:** `grep` returns 0 when pattern matches.

`earlyexit` follows this convention:
- Exit 0 = "I found what I was looking for" (the error pattern)
- Exit 1 = "Pattern not found" (no errors = success)

---

## Performance Questions

### Does earlyexit slow down my commands?

**No.** Overhead is negligible (<10ms startup).

### Should I use buffered mode for performance?

Only for **very high throughput** (>100MB/s):

```bash
ee --buffered 'Error' high-throughput-command
```

For normal use, unbuffered (default) is fine.

### Does telemetry impact performance?

Impact is minimal. If concerned, disable it:

```bash
ee --no-telemetry 'Error' command
```

---

## Watch Mode Questions

### How does watch mode work?

1. Run command without pattern: `ee terraform apply`
2. Press Ctrl+C when you see an error
3. System suggests patterns and saves settings
4. Next run uses learned settings automatically

### Does watch mode save patterns permanently?

Yes, in a local SQLite database (`~/.earlyexit/telemetry.db`).

### Can I clear learned settings?

Delete the telemetry database:

```bash
rm ~/.earlyexit/telemetry.db
```

### Is my data sent anywhere?

**No.** All data stays local by default. Privacy-first design.

---

## Troubleshooting

### Command not found: ee

Make sure Python's bin directory is in your PATH:

```bash
# Linux/Mac
export PATH="$HOME/.local/bin:$PATH"

# Or reinstall
pip install --user earlyexit
```

### Output is still buffered

**In pipe mode:** The source command may be buffering. Use command mode instead:

```bash
# Instead of:
command | ee 'Error'

# Use:
ee 'Error' command
```

**In command mode:** Should not happen (unbuffered by default). File a bug if it does.

### Pattern not matching

1. Check if pattern is correct: Test with `echo "ERROR" | ee 'ERROR'`
2. Check if stderr is captured: Use `2>&1` in pipe mode
3. Check pattern syntax: Escape special characters

### Timeout not working

Make sure you're using correct syntax:

```bash
# ✅ Correct
ee -t 300 'Error' command

# ❌ Wrong (pattern after command)
ee command 'Error' -t 300
```

### Permission denied errors

Check log directory permissions:

```bash
# Use writable directory
ee --log-dir /tmp 'Error' command

# Or disable logging
ee --no-log 'Error' command
```

---

## Comparison Questions

### When should I use grep instead?

Use `grep` when:
- You need maximum compatibility
- You want to see ALL matches (not just first)
- You're filtering static files (not real-time monitoring)

### When should I use timeout instead?

Use `timeout` when:
- You only need overall timeout (no pattern matching)
- You need very specific signal handling

### Can I use earlyexit with grep/timeout?

Yes! They can work together:

```bash
# Use grep for filtering, ee for early exit
command | grep -v DEBUG | ee 'ERROR'

# Though usually ee alone is enough
ee 'ERROR' command
```

---

## Advanced Questions

### Can I monitor custom file descriptors?

Yes, in command mode:

```bash
ee --fd 3 --fd 4 'Error' command
```

See [User Guide - Custom FDs](USER_GUIDE.md#custom-file-descriptors) for examples.

### Can I use different patterns for different streams?

Yes:

```bash
ee --fd-pattern 1 'FAILED' --fd-pattern 2 'ERROR' command
```

### Does it work with containers?

Yes:

```bash
# Docker
ee 'ERROR' docker run myapp

# Kubernetes
kubectl logs -f pod | ee 'CrashLoop|Error'
```

### Can I use it in CI/CD?

Absolutely! It's designed for it:

```bash
ee -t 3600 --idle-timeout 60 'ERROR|FAIL' ./ci-script.sh
```

---

## Getting Help

### Where can I find more documentation?

- [User Guide](USER_GUIDE.md) - Comprehensive usage
- [Mode Comparison](MODE_COMPARISON.md) - Detailed mode differences
- [Comparison vs other tools](COMPARISON.md) - vs grep/timeout/tee

### How do I report a bug?

[Open an issue](https://github.com/rsleedbx/earlyexit/issues) with:
- Command you ran
- Expected vs actual behavior
- `ee --version` output

### How do I request a feature?

[Open an issue](https://github.com/rsleedbx/earlyexit/issues) or [discussion](https://github.com/rsleedbx/earlyexit/discussions).

### Can I contribute?

Yes! See [CONTRIBUTING.md](../CONTRIBUTING.md).

---

**Still have questions?** [Open a discussion](https://github.com/rsleedbx/earlyexit/discussions) or [issue](https://github.com/rsleedbx/earlyexit/issues).





# The `ee` Alias

## Quick Reference

`ee` is a built-in short alias for `earlyexit`. All commands work the same:

```bash
# These are identical:
earlyexit npm test
ee npm test

# All options work:
ee -a npm test           # Disable auto-log
ee -q npm test           # Quiet mode
ee --profile npm npm test   # Use profile
```

---

## Installation

After installing or upgrading `earlyexit`, the `ee` command is automatically available:

```bash
pip install earlyexit
# or
pip install --upgrade earlyexit

# Now both work:
earlyexit --version
ee --version
```

---

## Examples

### Basic Usage
```bash
# Default behavior (auto-logging ON)
ee npm test

📝 Logging to:
   stdout: /tmp/npm_test_20241112_143530.log
   stderr: /tmp/npm_test_20241112_143530.errlog
```

### With Profiles
```bash
# List profiles
ee --list-profiles

# Use a profile
ee --profile pytest pytest -v

# Show profile details
ee --show-profile npm
```

### Quick Commands
```bash
# Disable auto-log
ee -a npm test

# Quiet mode
ee -q npm test

# Custom log prefix
ee --file-prefix /tmp/mytest npm test

# Pattern matching
ee 'ERROR' npm test
```

---

## Potential Conflicts

### Easy Editor (BSD Systems)

On some BSD systems (FreeBSD, OpenBSD), there's a text editor called `ee` (Easy Editor). To check if it's installed:

```bash
which ee
# or
type ee
```

**If `ee` is already installed:**

1. **Option 1: Keep using `earlyexit` (full command)**
   ```bash
   earlyexit npm test
   ```

2. **Option 2: Create a different shell alias**
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   alias eex='earlyexit'
   alias eee='earlyexit'
   ```

3. **Option 3: Use `ee` for earlyexit, rename editor**
   ```bash
   # If you rarely use Easy Editor, you can:
   alias easy='command ee'  # Access editor as 'easy'
   ```

**Most modern systems:** On macOS and most Linux distributions, `ee` (Easy Editor) is **not** installed by default, so there's no conflict.

---

## Why `ee`?

1. **Brevity**: Typing `ee` is 70% faster than `earlyexit` (2 chars vs 9 chars)
2. **Memorable**: "Early Exit" → "EE"
3. **Convention**: Short aliases are common (e.g., `ls`, `cd`, `ps`, `df`)
4. **AI-Friendly**: Shorter commands = less prompt overhead for AI agents

---

## Comparison

| Scenario | Typing (chars) | Typing (keys) |
|----------|---------------|---------------|
| `earlyexit npm test` | 19 | 19 |
| `ee npm test` | 12 | 12 |
| **Savings** | **37%** | **37%** |

For frequent use (hundreds of times per day), this adds up!

---

## Usage Recommendations

### For Humans
Use whichever you prefer:
- `ee` for speed
- `earlyexit` for clarity

### For Scripts
Use `earlyexit` (full name) for better readability:
```bash
#!/bin/bash
# Good: Clear what this does
earlyexit --profile npm npm test

# Less clear
ee --profile npm npm test
```

### For Documentation
Use `earlyexit` (full name) for first mention, then `ee` for examples:
```markdown
Install earlyexit:

    pip install earlyexit

Then use it:

    ee npm test
```

### For AI Agents
Use `ee` to minimize token usage in prompts:
```
Run: ee --profile npm npm test
```

---

## Shell Aliases (Additional)

You can also create your own shell aliases:

```bash
# Add to ~/.bashrc or ~/.zshrc

# Even shorter for common operations
alias eet='ee --profile npm npm test'
alias eep='ee --profile pytest pytest -v'
alias eec='ee --profile cargo cargo test'

# With common flags
alias eeq='ee -q'  # Quiet mode
alias eea='ee -a'  # No auto-log
```

Then use:
```bash
eet           # runs: ee --profile npm npm test
eep           # runs: ee --profile pytest pytest -v
eeq npm test  # runs: ee -q npm test
```

---

## FAQ

### Q: Is `ee` installed automatically?

A: Yes! After `pip install earlyexit`, both `earlyexit` and `ee` are available.

### Q: Can I disable the `ee` alias?

A: The `ee` command is part of the package. If you have conflicts, you can:
1. Use full `earlyexit` command instead
2. Create a shell alias to override: `alias ee='/path/to/other/ee'`

### Q: Does `ee` work with all options?

A: Yes! `ee` is identical to `earlyexit`. All flags, options, and features work the same.

### Q: What about `earlyexit-stats`, `earlyexit-profile`, etc?

A: Those keep their full names:
- `earlyexit-stats` (no short alias)
- `earlyexit-profile` (no short alias)
- `earlyexit-export` (no short alias)

Only the main command has a short alias (`ee`).

### Q: Can I check if `ee` is already installed?

A: Yes:
```bash
which ee
# If output is empty or "ee not found", no conflict
# If output shows a path, ee is already installed
```

---

## Summary

✅ **Built-in alias**: `ee` is automatically installed with `earlyexit`
✅ **Fully compatible**: All options and features work
✅ **Time saver**: 37% less typing
✅ **Rare conflicts**: `ee` text editor only on some BSD systems
✅ **Easy to check**: Run `which ee` to check for conflicts

**Quick test:**
```bash
pip install earlyexit
ee --version
ee --help
```

🎉 You're ready to use `ee`!


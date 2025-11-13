# Auto-Logging + `ee` Alias Summary

## 🎉 What's New

Two major improvements for better user experience:

### 1. Auto-Logging ON by Default
No more manual `2>&1 | tee` commands! Just run:
```bash
ee npm test
```

Output automatically saved to intelligent timestamped files.

### 2. Short Alias `ee`
Instead of typing `earlyexit` (9 characters), use `ee` (2 characters):
```bash
ee npm test              # Instead of: earlyexit npm test
ee -q pytest -v          # Instead of: earlyexit -q pytest -v
ee --profile npm npm test   # Instead of: earlyexit --profile npm npm test
```

**37% less typing!** Perfect for humans AND AI agents.

---

## Quick Examples

### Basic Usage (Auto-Log ON)
```bash
$ ee npm test

📝 Logging to:
   stdout: /tmp/npm_test_20241112_143530.log
   stderr: /tmp/npm_test_20241112_143530.errlog

> myapp@1.0.0 test
> jest
...
```

### Quiet Mode (No earlyexit Messages)
```bash
$ ee -q npm test

> myapp@1.0.0 test
> jest
...
# (No "Logging to:" message, but files still created)
```

### Disable Auto-Log
```bash
$ ee -a npm test

> myapp@1.0.0 test
> jest
...
# (No logging, traditional behavior)
```

### With Profiles
```bash
$ ee --list-profiles
Available profiles:
  • npm - Node.js package manager
  • pytest - Python testing framework
  • cargo - Rust package manager

$ ee --profile npm npm test
# (Uses pre-configured npm patterns + auto-logging)
```

---

## Installation & Verification

```bash
# Install or upgrade
pip install --upgrade earlyexit

# Verify both commands work
earlyexit --version
ee --version

# Both should show: ee 0.0.3

# Check installation location
which ee
# Should show: /opt/homebrew/bin/ee or similar
```

---

## Conflict Check

The `ee` command could conflict with "Easy Editor" on some BSD systems. Check:

```bash
which ee

# If empty or "ee not found": ✅ No conflict
# If shows path: ⚠️  Possible conflict (see docs/EE_ALIAS.md)
```

**Note:** Easy Editor is rare on modern Linux/macOS systems, so conflicts are unlikely.

---

## Benefits

### For Humans
- **Faster typing**: `ee` vs `earlyexit` = 37% less
- **Natural alias**: "Early Exit" → "EE"
- **Auto-logging**: No more manual `tee` commands
- **Intelligent filenames**: Automatic timestamp + command-based names

### For AI Agents
- **Token efficiency**: Shorter prompts
- **Simpler commands**: Built-in logging (no shell redirection)
- **Consistent pattern**: Same command everywhere
- **Easy to parse**: Clear "Logging to:" messages

---

## Command Comparison

| Old Way (Manual) | New Way (Auto) |
|------------------|----------------|
| `cmd 2>&1 \| tee /tmp/log.log` | `ee cmd` |
| `earlyexit --auto-log npm test` | `ee npm test` |
| `earlyexit --file-prefix /tmp/x npm test` | `ee --file-prefix /tmp/x npm test` |

---

## All Commands

The `ee` alias is ONLY for the main command. Other tools keep their full names:

| Tool | Command | Purpose |
|------|---------|---------|
| **Main** | `ee` or `earlyexit` | Run commands with early exit |
| Stats | `earlyexit-stats` | View telemetry stats |
| Suggest | `earlyexit-suggest` | Get pattern suggestions |
| Export | `earlyexit-export` | Export learned patterns |
| Import | `earlyexit-import` | Import patterns |
| Profile | `earlyexit-profile` | Manage profiles |

---

## Migration Guide

### If you were typing `earlyexit`:
Just replace with `ee`:
```bash
# Before
earlyexit npm test

# After
ee npm test
```

### If you have shell aliases:
You can keep them or remove them:
```bash
# Old ~/.bashrc
alias ee='earlyexit'    # Can remove - ee is now built-in!

# Or keep for other shortcuts
alias eet='ee --profile npm npm test'
alias eep='ee --profile pytest pytest -v'
```

---

## Configuration

The alias is built into the package. No configuration needed!

**Installed via `pyproject.toml`:**
```toml
[project.scripts]
earlyexit = "earlyexit.cli:main"
ee = "earlyexit.cli:main"  # Short alias
```

**Automatically available after:**
```bash
pip install earlyexit
```

---

## Testing

Verify everything works:

```bash
# 1. Check version
ee --version
# Should show: ee 0.0.3

# 2. Check help
ee --help | head -5

# 3. Test basic command
ee echo "Hello World"
# Should show "Logging to:" message

# 4. Check log files created
ls -lh /tmp/echo_*.log
# Should show timestamped log files

# 5. Test quiet mode
ee -q echo "Silent"
# Should NOT show "Logging to:" message

# 6. Test disable auto-log
ee -a echo "No Log"
# Should NOT create log files

# 7. Test with profile
ee --list-profiles
ee --show-profile npm
```

---

## Documentation

Full documentation:
- **`docs/EE_ALIAS.md`** - Complete ee alias guide
- **`docs/AUTO_LOG_QUICK_REFERENCE.md`** - Auto-logging reference
- **`docs/AUTO_LOGGING_DESIGN.md`** - Design and implementation
- **`docs/AUTO_LOG_STATUS.md`** - Implementation status
- **`README.md`** - Main documentation

---

## Summary

✅ **`ee` alias**: Automatically installed with `earlyexit`  
✅ **Auto-logging**: ON by default in command mode  
✅ **Intelligent filenames**: Timestamp + command-based  
✅ **Easy to disable**: Use `-a` to turn off logging  
✅ **Quiet mode**: Use `-q` to suppress messages  
✅ **Profile support**: Works with `--profile`  
✅ **No conflicts**: Easy Editor rarely installed on modern systems  

**Result:** Faster, simpler, more intelligent command execution! 🚀

---

## Quick Reference Card

```
┌────────────────────────────────────────────────────────┐
│ ee - Early Exit with Auto-Logging                      │
├────────────────────────────────────────────────────────┤
│ BASIC                                                   │
│   ee npm test              # Default (auto-log ON)     │
│   ee -a npm test           # Disable auto-log          │
│   ee -q npm test           # Quiet (no messages)       │
│   ee --profile npm npm test  # Use profile             │
│                                                         │
│ CUSTOM LOGGING                                          │
│   ee --file-prefix /tmp/x npm test  # Custom prefix    │
│   ee --log-dir ~/logs npm test      # Custom directory │
│                                                         │
│ PROFILES                                                │
│   ee --list-profiles       # Show available            │
│   ee --show-profile npm    # Show details              │
│                                                         │
│ FLAGS                                                   │
│   -a / --no-auto-log       # Disable logging           │
│   -q / --quiet             # Suppress messages         │
│   --profile NAME           # Use profile               │
│   --file-prefix PREFIX     # Custom log prefix         │
│   --log-dir DIR            # Custom log directory      │
│                                                         │
│ LOG FILES (default: /tmp/)                              │
│   npm_test_YYYYMMDD_HHMMSS.log                         │
│   npm_test_YYYYMMDD_HHMMSS.errlog                      │
└────────────────────────────────────────────────────────┘
```

Copy this card for quick reference! 📋


# Auto-Export Environment Variables Feature

## Problem Solved

AI agents (and users) were making mistakes when trying to reference log file paths:
- Had to copy/paste paths like `/tmp/ee-mist_dml_monitor-12345.log`
- Easy to make typos or reference wrong PIDs
- Hard to track which log file to use across multiple commands

## Solution

`ee` now automatically exports environment variables to `~/.ee_env.$$` for easy access.

---

## How It Works

### 1. Automatic Export (No User Action)

When `ee` creates log files (with timeout), it automatically writes `~/.ee_env.{parent_pid}`:

```bash
ee -t 60 'ERROR' -- mist dml monitor --id xyz

# ee automatically creates ~/.ee_env.12345 (where 12345 is shell PID):
# export EE_STDOUT_LOG='/tmp/ee-mist_dml_monitor-67890.log'
# export EE_STDERR_LOG='/tmp/ee-mist_dml_monitor-67890.errlog'
# export EE_EXIT_CODE=1
```

### 2. Load Variables (One Command)

```bash
source ~/.ee_env.$$
```

### 3. Use Variables (No Copy/Paste!)

```bash
cat $EE_STDOUT_LOG | ee 'ERROR' --test-pattern
cat $EE_STDERR_LOG | ee 'WARNING' --test-pattern
echo "Exit code was: $EE_EXIT_CODE"
```

---

## Variables Exported

| Variable | Description | Example |
|----------|-------------|---------|
| `$EE_STDOUT_LOG` | Path to stdout log | `/tmp/ee-mist_dml_monitor-67890.log` |
| `$EE_STDERR_LOG` | Path to stderr log | `/tmp/ee-mist_dml_monitor-67890.errlog` |
| `$EE_LOG_PREFIX` | Base log filename | `/tmp/ee-mist_dml_monitor-67890` |
| `$EE_EXIT_CODE` | Last exit code | `0`, `1`, `2`, `3`, etc. |

---

## Complete Workflow Example

```bash
# Step 1: Run ee (logs auto-created, env file auto-written)
ee -t 60 'ERROR|success' -- mist dml monitor --id rble-3087789530 --session rb_le-691708f8

# Step 2: Load environment variables
source ~/.ee_env.$$

# Step 3: Analyze logs (use $EE_STDOUT_LOG instead of copy/paste)
cat $EE_STDOUT_LOG | ee 'ERROR' --test-pattern

# Step 4: Refine pattern (same variable works!)
cat $EE_STDOUT_LOG | ee 'ERROR' --test-pattern --exclude 'retry'

# Step 5: Deploy optimized pattern
ee -t 60 \
  --success-pattern 'Success' \
  --error-pattern 'ERROR' \
  --exclude 'retry' \
  -- mist dml monitor --id rble-3087789530 --session rb_le-691708f8
```

---

## Multi-Session Safety

Each shell session gets its own environment file using the shell's PID:

```bash
# Terminal 1 (bash PID 12345)
ee -t 60 'ERROR' -- command1
# Creates: ~/.ee_env.12345

source ~/.ee_env.$$  # Sources ~/.ee_env.12345
cat $EE_STDOUT_LOG   # Uses log from command1

# Terminal 2 (bash PID 67890) - INDEPENDENT
ee -t 60 'ERROR' -- command2
# Creates: ~/.ee_env.67890

source ~/.ee_env.$$  # Sources ~/.ee_env.67890 (different file!)
cat $EE_STDOUT_LOG   # Uses log from command2
```

**No conflicts!** Each shell session is completely isolated.

---

## For AI Agents (Critical)

### Pattern to Teach

**ALWAYS do this after `ee` with timeout:**

```bash
# 1. Run ee
ee -t 60 'ERROR|success' -- <command>

# 2. Load env vars (CRITICAL!)
source ~/.ee_env.$$

# 3. Use the variables
cat $EE_STDOUT_LOG | ee 'ERROR' --test-pattern
```

### Why This Prevents Mistakes

**❌ WITHOUT env vars (error-prone):**
```bash
ee -t 60 'ERROR' -- mist dml monitor ...
# AI must remember or parse: /tmp/ee-mist_dml_monitor-12345.log
# Prone to typos, wrong PIDs, stale references
cat /tmp/ee-mist_dml_monitor-12345.log | ee 'ERROR' --test-pattern
```

**✅ WITH env vars (reliable):**
```bash
ee -t 60 'ERROR' -- mist dml monitor ...
source ~/.ee_env.$$
# AI just uses the variable - always correct!
cat $EE_STDOUT_LOG | ee 'ERROR' --test-pattern
```

### Benefits for AI

1. **No path tracking** - Don't need to remember log paths
2. **No PID handling** - `$$` always resolves to current shell
3. **Standard pattern** - Same command every time
4. **Error-free** - No typos or stale references
5. **Multi-session safe** - Each shell isolated

---

## Implementation Details

### When Environment File is Created

The `~/.ee_env.$$` file is created when:
- `ee` runs in command mode
- Auto-logging is enabled (typically with `-t` timeout)
- Log files are successfully created

### When Exit Code is Updated

The `EE_EXIT_CODE` is updated automatically by `map_exit_code()` function before returning from `main()`.

### File Location

- Pattern: `~/.ee_env.{parent_shell_pid}`
- Example: `~/.ee_env.12345`
- Cleanup: Files are overwritten on each `ee` run in that shell

### Silent Failures

- If env file cannot be written (permissions, etc.), `ee` continues silently
- Logs are still created and printed
- Only the env file export fails (graceful degradation)

---

## Comparison: Before vs After

| Aspect | Before | After |
|--------|--------|-------|
| **Reference logs** | Copy/paste paths | Use `$EE_STDOUT_LOG` |
| **Track PIDs** | Yes, manually | No, automatic |
| **Multi-session** | Conflicts possible | Isolated by shell PID |
| **AI mistakes** | Common (typos, stale refs) | Rare (standard pattern) |
| **Commands needed** | 1 (ee) | 2 (ee + source) |
| **Complexity** | High | Low |

---

## Optional: Alias for Convenience

Add to `~/.bashrc` or `~/.zshrc`:

```bash
alias eel='source ~/.ee_env.$$'
```

Usage:

```bash
ee -t 60 'ERROR' -- mist dml monitor ...
eel  # Short for: source ~/.ee_env.$$
cat $EE_STDOUT_LOG | ee 'ERROR' --test-pattern
```

---

## Testing

Verified behavior:

```bash
$ ee -t 5 'NEVER' -- bash -c 'echo TEST; echo ERROR: Test'
📝 Logging to:
   stdout: /tmp/ee-bash_c-37025.log
   stderr: /tmp/ee-bash_c-37025.errlog
TEST
ERROR: Test

$ source ~/.ee_env.$$

$ echo $EE_STDOUT_LOG
/tmp/ee-bash_c-37025.log

$ cat $EE_STDOUT_LOG
TEST
ERROR: Test

$ echo $EE_EXIT_CODE
1
```

✅ All variables exported correctly!

---

## Documentation Updated

1. **`docs/REAL_WORLD_EXAMPLES.md`**
   - Problem 11: Pattern development workflow
   - All 4 steps use `$EE_STDOUT_LOG`
   - Tip added about sourcing

2. **`.cursor/rules/useearlyexit.mdc`**
   - New section: "Accessing Log Files (CRITICAL for AI Agents)"
   - Full workflow example
   - Why it matters for AI agents
   - Multi-session safety explained

3. **This document** (`ENV_EXPORT_FEATURE.md`)
   - Complete feature documentation
   - Implementation details
   - Testing results

---

## Status

- ✅ **Implemented**: `earlyexit/cli.py`
- ✅ **Tested**: Verified with multiple commands
- ✅ **Documented**: 3 files updated
- ✅ **Committed**: ed794f9
- ✅ **Pushed**: To origin/master

**Ready for use!** 🎉

---

## Future Enhancements (Optional)

Potential additions:
- `alias eel='source ~/.ee_env.$$'` in setup scripts
- `ee --show-env` to display current env file contents
- `ee --clear-env` to remove old env files
- `EE_LOG_SIZE` variable with log file size
- `EE_COMMAND` variable with command that was run

---

**Version**: Implemented November 14, 2024  
**Commit**: ed794f9  
**Status**: ✅ **Production Ready**


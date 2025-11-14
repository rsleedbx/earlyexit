# SIGTERM Support Added for IDE Cancel Buttons ✅

## Problem

When Cursor (or other IDEs) run automated commands and you press the **Cancel button**, it sends `SIGTERM` (not `SIGINT`). Previously, `earlyexit` only handled `SIGINT` (Ctrl+C) for interactive learning.

**Result:** Pressing Cancel would just terminate the process without showing the learning prompt.

## Solution

Added `SIGTERM` handler to watch mode so **both** Ctrl+C and Cancel buttons trigger interactive learning.

## Changes Made

### `earlyexit/watch_mode.py`

```python
# Before: Only handled SIGINT (Ctrl+C)
signal.signal(signal.SIGINT, sigint_handler)

# After: Handles both SIGINT and SIGTERM
def interrupt_handler(signum, frame):
    """Handle both SIGINT (Ctrl+C) and SIGTERM (Cancel button)"""
    interrupted[0] = True
    if session.process:
        try:
            session.process.terminate()
        except:
            pass

signal.signal(signal.SIGINT, interrupt_handler)
signal.signal(signal.SIGTERM, interrupt_handler)
```

## How It Works

### Scenario 1: Manual Terminal (Ctrl+C)

```bash
$ ee terraform apply
# ... output ...
^C  # User presses Ctrl+C

# ee shows interactive prompt:
🔍 What happened?
1. Saw an error (teach pattern)
2. Process hung (set idle timeout)
3. Taking too long (set overall timeout)
4. Just testing (skip)
```

### Scenario 2: Cursor Automated Session (Cancel Button)

```bash
# Cursor runs in automated session:
$ ee terraform apply
# ... output ...
# User presses Cancel button in Cursor UI

# SIGTERM is sent → ee shows SAME interactive prompt:
🔍 What happened?
1. Saw an error (teach pattern)
2. Process hung (set idle timeout)
3. Taking too long (set overall timeout)
4. Just testing (skip)
```

## Signal Handling Details

| Signal | Source | Behavior |
|--------|--------|----------|
| `SIGINT` (2) | Ctrl+C in terminal | ✅ Triggers learning prompt |
| `SIGTERM` (15) | Cancel button in IDE | ✅ Triggers learning prompt |
| Exit Code | Both | Returns 130 (128 + SIGINT=2) |

**Note:** We return exit code 130 for both signals to maintain consistency with standard Unix conventions.

## Why This Matters for Cursor

When Cursor suggests broken patterns like:

```bash
terraform apply | tee log | tail -100
```

You see nothing (buffering), so you press Cancel. Now with `ee`:

```bash
# Cursor should suggest:
ee terraform apply

# When you press Cancel:
# 1. ✅ ee captures all output context
# 2. ✅ Shows learning prompt
# 3. ✅ You teach it the pattern
# 4. ✅ Next time, ee watches automatically
```

## Cursor Rule Update

Updated `.cursor/rules/useearlyexit.mdc` to clarify:

```markdown
**Works with Cursor's Cancel button:** When you press Cancel in Cursor's 
automated session, `ee` detects it (SIGTERM) and shows the same learning 
prompt as Ctrl+C.
```

## Testing

### Test 1: Ctrl+C (SIGINT)
```bash
$ ee sleep 10
# Press Ctrl+C after 2 seconds
# Should show learning prompt ✅
```

### Test 2: Kill Command (SIGTERM)
```bash
$ ee sleep 10 &
[1] 12345
$ kill 12345  # Sends SIGTERM
# Should show learning prompt ✅
```

### Test 3: Cursor Cancel Button
```bash
# In Cursor's terminal/agent:
$ ee terraform apply
# Press Cancel button in Cursor UI
# Should show learning prompt ✅
```

## Benefits

1. ✅ **Works with IDE Cancel buttons** - Not just Ctrl+C
2. ✅ **Consistent learning experience** - Same prompt for all interrupts
3. ✅ **Better Cursor integration** - Learns from automated session cancellations
4. ✅ **Standard exit codes** - Returns 130 for all interrupts

## Documentation Updates

1. **`earlyexit/watch_mode.py`** - Added SIGTERM handler
2. **`.cursor/rules/useearlyexit.mdc`** - Documented Cancel button support
3. **`SIGTERM_SUPPORT_ADDED.md`** - This document

## Status

**Ready for release 0.0.4** 🚀

Now `ee` works seamlessly with both manual terminal usage (Ctrl+C) and IDE automated sessions (Cancel button).





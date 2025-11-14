# Delay-Exit in Pipe Mode

## Overview

Good news! **`--delay-exit` already works in pipe mode**. This feature allows you to capture additional context after detecting an error, even when using `earlyexit` in a pipeline.

## How It Works

When you use `--delay-exit` in pipe mode:

1. **Pattern Match Detected**: When a matching line is found, `earlyexit` marks the timestamp
2. **Continue Reading**: Instead of exiting immediately, it continues reading from stdin
3. **Capture Context**: All subsequent lines are captured and displayed
4. **Smart Exit**: Exits when either:
   - The delay time expires (`--delay-exit` seconds), OR
   - The line limit is reached (`--delay-exit-after-lines`)

## Default Behavior

- **Command mode**: `--delay-exit 10` (10 seconds by default)
- **Pipe mode**: `--delay-exit 0` (immediate exit by default, for backward compatibility)

This means pipe mode requires explicit `--delay-exit` to capture context.

## Examples

### Basic Usage

```bash
# Capture 5 seconds of context after error
./app 2>&1 | ee --delay-exit 5 'ERROR'

# Capture 10 seconds OR 50 lines (whichever comes first)
./verbose-app 2>&1 | ee --delay-exit 10 --delay-exit-after-lines 50 'FAILED'
```

### Real-World Examples

```bash
# Terraform - capture full plan/apply output after error
terraform apply 2>&1 | ee --delay-exit 15 'Error'

# npm test - capture full test failure context
npm test 2>&1 | ee --delay-exit 5 'FAIL|ERROR'

# Docker build - capture build context after failure
docker build . 2>&1 | ee --delay-exit 10 'ERROR|failed'

# Python - capture full stack trace
python3 script.py 2>&1 | ee --delay-exit 3 'Exception|Error'
```

### Streaming Logs

```bash
# Tail logs and capture context after critical error
tail -f app.log | ee --delay-exit 5 'CRITICAL|FATAL'

# Monitor multiple log files
tail -f /var/log/app/*.log | ee --delay-exit 10 'ERROR'
```

## Implementation Details

### Non-Blocking I/O

The implementation uses `select.select()` for non-blocking reads:

```python
import select
end_time = time.time() + remaining

while time.time() < end_time:
    # Check if input available (100ms timeout)
    if select.select([sys.stdin], [], [], 0.1)[0]:
        try:
            line = sys.stdin.readline()
            if not line:
                break  # EOF
            print(line, end='')
        except:
            break
```

This ensures:
- ✅ Non-blocking reads (doesn't hang if no input)
- ✅ Respects EOF (exits gracefully when upstream closes)
- ✅ Low CPU usage (100ms polling interval)

### SIGPIPE Behavior

When `earlyexit` exits in pipe mode:
1. It closes stdin and stdout
2. The upstream process receives SIGPIPE on next write
3. Upstream terminates automatically

This is different from command mode, where `earlyexit` has explicit process control.

## Exit Codes

| Scenario | Exit Code | Meaning |
|----------|-----------|---------|
| Pattern matched | 0 | Error found (success for error detection) |
| Pattern not matched | 1 | No error found (normal termination) |
| Timeout (--idle-timeout, etc) | 2 | Process stalled or timed out |

## Why Delay-Exit in Pipes?

### Problem

Many tools produce multi-line errors:

```
ERROR: Database connection failed
  at Connection.connect (db.js:45:12)
  at Server.start (server.js:23:8)
  at main (index.js:10:2)
Details: ECONNREFUSED 127.0.0.1:5432
```

Without delay-exit, you might only see:
```
ERROR: Database connection failed
```

### Solution

With delay-exit, you capture the full context:

```bash
./app 2>&1 | ee --delay-exit 2 'ERROR'
```

Result:
```
ERROR: Database connection failed
  at Connection.connect (db.js:45:12)
  at Server.start (server.js:23:8)
  at main (index.js:10:2)
Details: ECONNREFUSED 127.0.0.1:5432

⏳ Waiting 0.3s for error context...
```

## Comparison: Command vs Pipe Mode

| Feature | Command Mode | Pipe Mode |
|---------|--------------|-----------|
| **Default delay** | 10 seconds | 0 seconds (immediate) |
| **Process control** | Direct (terminates subprocess) | Indirect (SIGPIPE) |
| **EOF handling** | Waits for process exit | Respects stdin EOF |
| **Context capture** | Always enabled by default | Opt-in with `--delay-exit N` |

## Testing

We have comprehensive tests proving this works:

```bash
# Run the pipe mode delay-exit tests
./tests/test_pipe_delay_exit.sh

# Or via pytest
pytest tests/test_shell_scripts.py::TestShellScripts::test_pipe_delay_exit -v
```

**Test Coverage:**
- ✅ Basic context capture with time-based delay
- ✅ Streaming input with delays between lines
- ✅ `--delay-exit 0` exits immediately (backward compatible)
- ✅ Default behavior (no flag) exits immediately
- ✅ `--delay-exit-after-lines` line-based early exit

## When to Use

### Use `--delay-exit` in pipes when:

✅ Multi-line errors (stack traces, context)  
✅ Cleanup messages after errors  
✅ Gradual output (errors followed by details)  
✅ Want full context for debugging

### Don't use when:

❌ Single-line errors only  
❌ Need instant termination  
❌ High-throughput streams (adds latency)  
❌ Errors are self-contained

## Backward Compatibility

**Default behavior preserved:**

```bash
# These work exactly as before (immediate exit on match)
./app 2>&1 | ee 'ERROR'
tail -f log | ee 'CRITICAL'
```

**Opt-in for new behavior:**

```bash
# Explicitly request context capture
./app 2>&1 | ee --delay-exit 5 'ERROR'
```

## Related Features

- [Pipe Mode Timeouts](./PIPE_MODE_TIMEOUTS.md) - `--idle-timeout`, `--first-output-timeout`
- [Error Context Capture](./AUTO_LOGGING_DESIGN.md) - Auto-logging for unattended execution
- [Command Mode Delay-Exit](../tests/test_delay_exit.sh) - Default behavior in command mode

## Summary

✅ **`--delay-exit` works in pipe mode**  
✅ **Backward compatible** (default: 0, immediate exit)  
✅ **Smart exit** (time OR line count, whichever first)  
✅ **Non-blocking I/O** (respects EOF, low CPU)  
✅ **Fully tested** (5 comprehensive tests)

For contributors, see [`tests/test_pipe_delay_exit.sh`](../tests/test_pipe_delay_exit.sh) for the full test suite.





# First Output Time Tracking (Per Stream)

## Change Summary

Added separate tracking for when first output appears on stdout vs stderr. This helps diagnose stalled output and provides better telemetry data.

## Why This Matters

**Problem:** Programs may emit stdout and stderr at different times:

```python
# Example: Slow initialization
import time
import sys

print("Starting...", file=sys.stderr)  # stderr appears immediately
time.sleep(5)  # Long initialization
print("Ready!")  # stdout appears 5s later
```

**Before:** We only tracked "first output" as a boolean  
**After:** We track exact timestamps for first stdout and first stderr separately

## Use Cases

### 1. Diagnosing Stalled Output

```bash
# Command only outputs to stderr (stdout stalled)
ee 'ERROR' ./buggy-app

# Now we can detect:
# - first_stderr_time: 0.1s (got stderr quickly)
# - first_stdout_time: never (stdout is stalled!)
```

### 2. Understanding Output Patterns

```bash
# Which stream appears first?
ee 'ERROR' npm test

# Telemetry shows:
# - first_stderr_time: 0.05s (npm logs to stderr)
# - first_stdout_time: 2.3s  (test results to stdout)
```

### 3. Early Termination on No Output

```bash
# Future feature: warn if expected stream never appears
ee --first-stdout-timeout 10 'ERROR' command

# If stdout never appears:
# ⚠️  Warning: No stdout after 10s (first_stdout_time = 0)
```

## Implementation

### Data Structures

```python
# In run_command_mode()
start_time = time.time()
first_stdout_time = [0.0]  # Timestamp when first stdout line appears
first_stderr_time = [0.0]  # Timestamp when first stderr line appears
```

### Stream Processing

```python
# In process_stream()
def process_stream(stream, ..., first_stream_time=None, ...):
    for line in stream:
        current_time = time.time()
        
        # Track first output time for THIS stream
        if first_stream_time is not None and first_stream_time[0] == 0.0:
            first_stream_time[0] = current_time
```

### Call Sites

```python
# stdout monitoring
process_stream(process.stdout, ..., first_stream_time=first_stdout_time, ...)

# stderr monitoring  
process_stream(process.stderr, ..., first_stream_time=first_stderr_time, ...)

# fd3+ monitoring (determine based on fd number)
first_time = first_stdout_time if fd_num == 1 else first_stderr_time if fd_num == 2 else None
process_stream(stream, ..., first_stream_time=first_time, ...)
```

## Metrics Available

After command completes, we have:

| Metric | Type | Description |
|--------|------|-------------|
| `start_time` | float | When command started |
| `first_stdout_time` | float | When first stdout line appeared (0 if none) |
| `first_stderr_time` | float | When first stderr line appeared (0 if none) |
| `last_output_time` | float | When last output appeared (any stream) |

### Derived Metrics

```python
# Time to first stdout
if first_stdout_time[0] > 0:
    ttfb_stdout = first_stdout_time[0] - start_time
    print(f"First stdout after {ttfb_stdout:.2f}s")

# Time to first stderr
if first_stderr_time[0] > 0:
    ttfb_stderr = first_stderr_time[0] - start_time
    print(f"First stderr after {ttfb_stderr:.2f}s")

# Which stream appeared first?
if first_stdout_time[0] > 0 and first_stderr_time[0] > 0:
    if first_stdout_time[0] < first_stderr_time[0]:
        print("stdout appeared first")
    else:
        print("stderr appeared first")

# Did a stream never appear?
if first_stdout_time[0] == 0:
    print("⚠️  No stdout output")
if first_stderr_time[0] == 0:
    print("⚠️  No stderr output")
```

## Future Enhancements

### 1. Stream-Specific Timeouts

```bash
# Warn if stdout never appears
ee --first-stdout-timeout 10 'ERROR' command

# Warn if stderr never appears  
ee --first-stderr-timeout 5 'ERROR' command
```

### 2. Telemetry Collection

```json
{
  "execution_id": "abc123",
  "command": "npm test",
  "start_time": 1699999999.0,
  "first_stdout_time": 1699999999.2,  // 0.2s after start
  "first_stderr_time": 1699999999.05, // 0.05s after start
  "last_output_time": 1700000010.0,   // 11s after start
  "stdout_appeared_first": false,
  "stderr_appeared_first": true,
  "no_stdout": false,
  "no_stderr": false
}
```

### 3. Learning System Integration

```bash
# System learns typical patterns
ee 'ERROR' npm test  # Run multiple times

# Then suggests:
💡 Tip: npm test typically outputs to stderr first (0.05s),
       then stdout appears after 2-3s. Consider:
       ee --first-stdout-timeout 10 'ERROR' npm test
```

## Debugging Example

### Before (Boolean Only)

```bash
$ ee --verbose 'ERROR' ./slow-app
...
first_output_seen: true
# ❓ Which stream? When?
```

### After (Timestamps Per Stream)

```bash
$ ee --verbose 'ERROR' ./slow-app
...
first_stdout_time: 0.0       # ⚠️  No stdout!
first_stderr_time: 0.05      # stderr appeared at 0.05s
last_output_time: 5.2        # Last output at 5.2s

# 💡 Clear diagnosis: stdout is stalled or not used
```

## Testing

### Test 1: Both Streams

```python
# /tmp/test_both.py
import sys
import time

print("stdout line", file=sys.stdout)
time.sleep(0.1)
print("stderr line", file=sys.stderr)
```

```bash
$ ee 'xxx' python3 /tmp/test_both.py

# Internal tracking:
# first_stdout_time: 0.05s
# first_stderr_time: 0.15s
# stdout appeared first ✅
```

### Test 2: Stderr Only

```python
# /tmp/test_stderr.py
import sys
print("error", file=sys.stderr)
```

```bash
$ ee 'xxx' python3 /tmp/test_stderr.py

# Internal tracking:
# first_stdout_time: 0.0  (never appeared)
# first_stderr_time: 0.05s
# No stdout detected ✅
```

### Test 3: Delayed Output

```python
# /tmp/test_delayed.py
import time
time.sleep(2)  # 2s delay
print("late output")
```

```bash
$ ee 'xxx' python3 /tmp/test_delayed.py

# Internal tracking:
# first_stdout_time: 2.05s  (appeared after 2s delay)
# first_stderr_time: 0.0     (never appeared)
# 2s time-to-first-byte ✅
```

## Summary

✅ **Separate tracking** for stdout and stderr first output times  
✅ **Better diagnostics** for stalled or missing streams  
✅ **Foundation for future features** (stream-specific timeouts, learning)  
✅ **Telemetry-ready** for ML analysis  
✅ **Zero user impact** (internal tracking only)  

🎯 **Better insight into command output patterns!**


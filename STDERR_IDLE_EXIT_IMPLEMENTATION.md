# Stderr Idle Exit - Implementation Summary

## ✅ Completed

Implemented **stderr idle exit** detection to automatically exit after error messages finish printing to stderr.

## 🎯 Problem Solved

Python, Node.js, and other commands print error messages to stderr then hang instead of exiting:

```bash
# Mist command
mist dml monitor --id rble-3087789530

# Prints error:
⚠️  Error loading session: 'LakeflowConnectProvider' object has no attribute 'storage'
Traceback (most recent call last):
  File "/Users/robert.lee/github/mist/mist/cli/main.py", line 1770
AttributeError: 'LakeflowConnectProvider' object has no attribute 'storage'

# Then hangs forever! 😤
```

**Existing timeout options don't help:**
- `-I`/`--idle-timeout`: Checks **all** streams (stdout may still be active with progress bars)
- Regular timeout: Waits full 30 minutes
- Need: Detect "**stderr went quiet** after error"

## 🚀 Solution

```bash
# Exit 1 second after stderr goes idle
ee --stderr-idle-exit 1 'SUCCESS' -- mist dml monitor --id xyz

# Output:
⚠️  Error loading session: ...
Traceback (most recent call last):
  ...
AttributeError: ...

⏸️  Stderr idle: No stderr output for 1.0s (error messages complete)
⏱️  Timeout: stderr idle for 1.0s

# Exit code: 2
```

## 🔧 Implementation

### 1. New CLI Argument

**`--stderr-idle-exit SECONDS`**
- Monitor stderr specifically
- After seeing ANY stderr output, start monitoring
- If stderr is idle for SECONDS, exit with code 2
- Use with `--exclude` to filter non-error stderr (warnings, debug logs)

### 2. Tracking Logic

Added to `run_command_mode`:
```python
last_stderr_time = [0.0]  # Timestamp of last stderr output
stderr_seen = [False]     # Track if we've seen any stderr output
```

### 3. Monitoring Thread

New `check_stderr_idle()` function:
```python
def check_stderr_idle():
    """Monitor thread to check for stderr idle timeout"""
    while process.poll() is None and not timed_out[0]:
        # Wait until we've seen stderr output
        if not stderr_seen[0]:
            time.sleep(0.1)
            continue
        
        current_time = time.time()
        time_since_stderr = current_time - last_stderr_time[0]
        
        # If stderr has been idle for the specified time, exit
        if time_since_stderr >= args.stderr_idle_exit:
            timed_out[0] = True
            timeout_reason[0] = f"stderr idle for {args.stderr_idle_exit}s"
            # Terminate process...
            break
```

### 4. Stream Tracking

Updated `process_stream` to track stderr timing:
```python
# Track stderr-specific timing (for --stderr-idle-exit)
# Update if last_stderr_time is provided (indicates this is stderr stream)
if last_stderr_time is not None:
    last_stderr_time[0] = current_time
    if stderr_seen is not None:
        stderr_seen[0] = True
```

Key: We pass `last_stderr_time` and `stderr_seen` only when processing stderr (fd 2), so the tracking is automatic.

### 5. Thread Integration

Thread started if `--stderr-idle-exit` is provided:
```python
# Start stderr idle monitor thread if needed
stderr_idle_thread = None
if args.stderr_idle_exit:
    stderr_idle_thread = threading.Thread(target=check_stderr_idle, daemon=True)
    stderr_idle_thread.start()
```

## 📊 Exit Code

**Exit code: `2`** (stderr idle timeout)
- Same as regular timeout
- Semantic: "Process didn't complete successfully"
- Easy for CI/CD integration

**All exit codes:**
```bash
0 = Pattern matched (success/completion)
1 = No match
2 = Timeout (overall, idle, stderr idle, or stuck)
3 = Command failed to start
4 = Detached mode
```

## 🎓 Best Practices (Documentation)

**1. Use `--exclude` for non-error stderr:**
```bash
# Filter out warnings/debug logs
ee --stderr-idle-exit 1 --exclude 'WARNING|DEBUG' 'SUCCESS' -- command
```

**2. Combine with overall timeout:**
```bash
# Exit on stderr idle OR overall timeout
ee -t 300 --stderr-idle-exit 1 'SUCCESS' -- command
```

**3. Choose appropriate delay:**
- `0.5s` - Single-line errors
- `1s` - Standard multi-line tracebacks (recommended)
- `2s` - Slow output or network errors

## 📚 Documentation Updated

### README.md
- Added "Stderr Idle Exit" section with usage examples
- Best practices (exclude, timeouts, timing)
- When to use (Python/Node.js crashes)
- Difference from other timeouts
- Updated feature lists

### docs/REAL_WORLD_EXAMPLES.md
- **Problem 13:** Error Messages Finish But Command Hangs
- Real Mist example with exact error output
- Comparison table with all approaches
- Timing recommendations
- Real-world savings metrics
- Updated summary table (13 scenarios)

### Strong AI Agent Guidance
Documentation emphasizes:
1. **Use `--exclude` for non-error stderr** (warnings, debug, info)
2. **Choose timing based on error type** (0.5s, 1s, 2s)
3. **Combine with overall timeout** for belt-and-suspenders
4. **Exit code 2 is consistent** across all timeout types

## ✅ Tests

Manual testing confirmed:
- ✅ Stderr output tracked correctly
- ✅ Timer activates after first stderr output
- ✅ Exit triggered after specified idle time
- ✅ Process terminated cleanly
- ✅ Exit code 2 returned
- ✅ Message displayed (unless `--quiet`)

### Test Script

Created `/tmp/test_stderr_idle.py`:
```python
# Writes errors to stderr
print("ERROR: First error", file=sys.stderr)
print("Traceback...", file=sys.stderr)
# Then sleeps 5 seconds (stderr idle)
time.sleep(5)
print("This should NOT print", file=sys.stdout)
```

**Test result:**
```bash
$ ee --stderr-idle-exit 1 'SUCCESS' -- python3 /tmp/test_stderr_idle.py
ERROR: First error
Traceback...

⏸️  Stderr idle: No stderr output for 1.0s (error messages complete)

$ echo $?
2
```

✅ Command terminated after 1s idle, last line not printed!

## 📈 Real-World Impact

### Mist's Use Case
- **Before:** Error prints, command hangs forever, manual Ctrl+C or 30min timeout
- **After:** Auto-detects in ~1 second
- **Savings:** **~29 minutes 59 seconds** per error instance
- **Exit code:** Clear signal (2) for automation

### General Benefits
- ⏱️ Detects error completion automatically
- 💰 Saves significant time (minutes to hours)
- 🎯 Clear exit code for CI/CD
- 📊 Works with all other features (patterns, exclusions, JSON)
- 🔧 Specifically designed for error detection

## 🔄 Differences from Other Timeouts

| Feature | What It Detects | Streams Monitored |
|---------|----------------|-------------------|
| `-t`/`--timeout` | Overall time limit | N/A |
| `-I`/`--idle-timeout` | **All** streams idle | stdout + stderr |
| `--stderr-idle-exit` | **Stderr** idle (after stderr seen) | stderr only |
| `-F`/`--first-output-timeout` | No output at all | stdout + stderr |

**Key insight:** `--stderr-idle-exit` is stderr-specific, so it works even when stdout is still active (progress bars, heartbeats).

## 🔑 Key Design Decisions

### 1. Exit code 2 (not new code)
- **Rationale:** Consistent with other timeout types
- **Alternative:** New exit code 5 for stderr-specific
- **Chosen:** Keep exit codes simple, 2 = "timeout/no progress"

### 2. Only activate after seeing stderr
- **Rationale:** Don't exit if stderr was never active
- **Alternative:** Start timer immediately
- **Chosen:** Wait for stderr output first (makes sense for "error complete")

### 3. Tracking via `last_stderr_time` parameter
- **Rationale:** Clean, thread-safe, automatic based on stream
- **Alternative:** Check stream_name == "stderr"
- **Chosen:** Parameter-based (works regardless of labeling)

### 4. Same thread pattern as other timeouts
- **Rationale:** Consistent architecture
- **Testing:** Proven pattern, easy to maintain

## 📝 Files Changed

### Core Implementation
- **`earlyexit/cli.py`:**
  - Added `--stderr-idle-exit` argument
  - Added `last_stderr_time` and `stderr_seen` trackers
  - Added `check_stderr_idle()` monitoring function
  - Updated `process_stream()` signature and logic
  - Updated all `process_stream()` call sites
  - Started stderr idle monitoring thread

### Documentation
- **`README.md`:**
  - Added "Stderr Idle Exit" section
  - Updated feature lists
  - Changed "12 scenarios" to "13 scenarios"

- **`docs/REAL_WORLD_EXAMPLES.md`:**
  - Added Problem 13 with Mist's exact error
  - Comparison table
  - Updated summary table

### Tests
- Manual testing with `/tmp/test_stderr_idle.py`
- Verified process termination, exit code, timing

## 🚀 Ready to Use!

```bash
# Standard usage
ee --stderr-idle-exit 1 'SUCCESS' -- command

# With exclude pattern
ee --stderr-idle-exit 1 --exclude 'WARNING|DEBUG' 'SUCCESS' -- command

# With overall timeout
ee -t 300 --stderr-idle-exit 1 'SUCCESS' -- command
```

**Time saved:** ~29min 59sec per error instance
**Exit code:** Clear signal (2 = timeout)
**Works with:** All other features (patterns, exclusions, JSON, auto-logging)

## 🎉 Complete!

All changes committed and pushed to `origin master`.


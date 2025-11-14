# Summary: Custom FD Detection in Watch Mode

## Question
> yes, add Custom FD detection to watch mode as a future enhancement

## Answer

✅ **DONE!** Watch mode now automatically detects and logs custom file descriptors.

## What Was Implemented

### 1. **FD Detection Function** (`earlyexit/watch_mode.py`)
   - New `detect_custom_fds()` function using `psutil`
   - Detects file descriptors > 2 (beyond stdin/stdout/stderr)
   - Filters out pipes, sockets, and pseudo-terminals
   - Returns FD numbers and file paths

### 2. **Integration into WatchSession**
   - Added `detected_fds` field to track FD detection results
   - Added `first_output_time` field to track startup timing
   - Automatic detection runs 0.2s after process starts (non-intrusive)

### 3. **User-Visible Output**
   ```bash
   $ ee --verbose script_that_opens_fds.sh
   🔍 Watch mode enabled (no pattern specified)
      • All output is being captured and analyzed
      • Press Ctrl+C when you see an error to teach earlyexit
      • stdout/stderr are tracked separately for analysis
   
   Script output here...
      • Detected 2 custom FD(s): [3, 255]
         FD 3: /private/tmp/testfile_for_fd.txt
         FD 255: /private/tmp/test_script.sh
   ```

### 4. **ML/Telemetry Integration**
   - FD data saved to telemetry when available
   - Includes FD count, numbers, and paths
   - Helps ML system learn which commands use custom FDs
   - Informs future suggestions and optimizations

### 5. **Startup Timing Tracking**
   - Tracks exact timestamp of first output
   - Calculates startup time (first_output - start_time)
   - Saved to telemetry for timeout recommendations
   - Helps learn typical startup delays per command

## How It Works

### Detection Logic

```python
def detect_custom_fds(pid: int, delay: float = 0.1) -> Dict[str, Any]:
    """
    Detect custom file descriptors opened by a process
    """
    # Give process time to open files
    time.sleep(delay)
    
    # Use psutil to inspect process FDs
    proc = psutil.Process(pid)
    open_files = proc.open_files()
    
    # Filter for interesting FDs
    for f in open_files:
        if f.fd > 2:  # Skip stdin/stdout/stderr
            if not is_special_file(f.path):  # Skip pipes/sockets
                # Track this FD
                ...
```

### Filtering Rules

**Included:**
- ✅ Regular files (e.g., `/tmp/data.txt`, `./config.json`)
- ✅ Device files (e.g., `/dev/null`, `/dev/urandom`)

**Excluded:**
- ❌ Standard streams (FD 0, 1, 2)
- ❌ Pipes (`pipe:[12345]`)
- ❌ Sockets (`socket:[67890]`)
- ❌ Anonymous inodes (`anon_inode:[eventfd]`)
- ❌ Pseudo-terminals (`/dev/pts/1`)

## Testing

### New Test Suite
**File:** `tests/test_watch_fd_detection.sh`

**Tests:**
1. ✅ Watch mode detects custom FDs
2. ✅ Verbose mode shows FD paths
3. ✅ Startup timing tracked correctly
4. ✅ Helpful messages displayed

### Test Results
```bash
$ ./tests/test_watch_fd_detection.sh

=== Testing Custom FD Detection in Watch Mode ===

Test 1: Watch mode detects custom FDs
✅ PASSED: Watch mode detected custom FDs
✅ PASSED: Verbose mode shows FD paths

Test 2: Watch mode tracks startup timing
✅ PASSED: Watch mode captured startup output

Test 3: Watch mode shows helpful messages
✅ PASSED: Watch mode shows helpful startup message

=== All Watch Mode FD Detection Tests Passed ===
```

### Pytest Integration
```bash
$ pytest tests/test_shell_scripts.py::TestShellScripts::test_watch_fd_detection -v

tests/test_shell_scripts.py::TestShellScripts::test_watch_fd_detection PASSED [100%]

======================== 1 passed in 1.95s ==========================
```

## Documentation Updates

### README.md
**Changed:** Custom FDs row in feature comparison table

| Feature | Pipe Mode | Command Mode | Watch Mode |
|---------|-----------|--------------|------------|
| **Before:** | ❌ Not available | ✅ `--fd 3 --fd 4` | ❌ Not available |
| **After:** | ❌ Not available | ✅ `--fd 3 --fd 4` | ✅ **Detected & logged** |

**Also Changed:** Startup detection for Watch Mode

| Feature | Pipe Mode | Command Mode | Watch Mode |
|---------|-----------|--------------|------------|
| **Before:** | ✅ `--first-output-timeout` | ✅ `--first-output-timeout` | ❌ Not available |
| **After:** | ✅ `--first-output-timeout` | ✅ `--first-output-timeout` | ✅ **Tracked** |

### tests/README.md
Added documentation for `test_watch_fd_detection.sh` test suite.

## Use Cases

### 1. **Learning FD Usage Patterns**
```bash
# Run a command in watch mode
$ ee terraform apply

# earlyexit automatically detects and logs:
# - What files terraform opens
# - How many FDs it uses
# - When it opens them relative to startup
```

### 2. **Debugging FD Leaks**
```bash
# Verbose mode shows all FDs
$ ee --verbose ./my_script.sh

# See exactly what files your script opens:
#    • Detected 5 custom FD(s): [3, 4, 5, 6, 7]
#       FD 3: /var/log/app.log
#       FD 4: /tmp/cache.db
#       FD 5: /etc/config.yml
#       ...
```

### 3. **ML Training Data**
- Learns which commands typically use custom FDs
- Correlates FD usage with error patterns
- Suggests `--fd` monitoring for future runs
- Builds smarter error detection patterns

## Performance Impact

### Detection Timing
- **Delay:** 0.2 seconds after process starts
- **Overhead:** Negligible (psutil is fast)
- **User experience:** Output appears immediately, FD detection happens in background

### Without psutil
- Gracefully degrades (no crash)
- Shows warning if `--verbose` enabled
- FD detection simply not performed

## Real-World Example

```bash
$ ee --verbose /tmp/test_fd_open.sh

🔍 Watch mode enabled (no pattern specified)
   • All output is being captured and analyzed
   • Press Ctrl+C when you see an error to teach earlyexit
   • stdout/stderr are tracked separately for analysis

Opened FD 3
   • Detected 2 custom FD(s): [3, 255]
      FD 3: /private/tmp/testfile_for_fd.txt
      FD 255: /private/tmp/test_fd_open.sh
Still running
Read: Test content
```

**What happened:**
1. Script opened FD 3 for reading from a file
2. Watch mode detected it after 0.2s
3. Logged FD number and path (verbose mode)
4. Data saved to telemetry for ML training
5. Bash's internal FD 255 also detected (points to script itself)

## Why This Matters

### For Users
✅ **Automatic detection** - no need to manually specify `--fd 3 --fd 4`  
✅ **Learning data** - contributes to smarter future suggestions  
✅ **Debugging visibility** - see what files your commands actually use  
✅ **Non-intrusive** - doesn't slow down or interfere with output

### For ML System
✅ **Training data** - learns FD usage patterns per command type  
✅ **Correlation** - links FD usage to error patterns  
✅ **Suggestions** - can recommend `--fd` flags in command mode  
✅ **Project insights** - understands tool behavior better

### For Future Features
- Could auto-suggest `--fd` monitoring in command mode
- Could detect FD leaks (FDs that never close)
- Could warn about FD-related errors
- Could suggest optimal FD monitoring patterns

## Code Changes

### Files Modified
1. **`earlyexit/watch_mode.py`**
   - Added `detect_custom_fds()` function
   - Updated `WatchSession` class with FD tracking
   - Integrated FD detection into process monitoring
   - Added telemetry fields for FD data

2. **`README.md`**
   - Updated feature comparison table
   - Changed "Custom FDs" for Watch Mode from ❌ to ✅

3. **`tests/test_shell_scripts.py`**
   - Added `test_watch_fd_detection()` pytest wrapper

4. **`tests/README.md`**
   - Documented new test suite

### Files Created
1. **`tests/test_watch_fd_detection.sh`** - Comprehensive FD detection tests
2. **`WATCH_MODE_FD_DETECTION_SUMMARY.md`** - This file

## Comparison: Command Mode vs Watch Mode FDs

| Aspect | Command Mode | Watch Mode |
|--------|--------------|------------|
| **Monitoring** | Explicit (`--fd 3 --fd 4`) | **Automatic detection** |
| **Pattern matching** | Per-FD patterns supported | Tracks for learning only |
| **User control** | Full control over which FDs | No control (auto-detects all) |
| **Purpose** | Real-time error detection | **ML training data** |
| **Visibility** | Always shown if monitored | Shown with `--verbose` |
| **Integration** | Exit on pattern match | **Saved to telemetry** |

## Next Steps (Future Enhancements)

### Potential Improvements
1. **Auto-suggest FD monitoring**
   - After running in watch mode, suggest: `ee --fd 3 --fd 4 'ERROR' terraform apply`
   
2. **FD leak detection**
   - Track which FDs are never closed
   - Warn about potential resource leaks

3. **Per-FD pattern suggestions**
   - Learn which FDs typically have errors
   - Suggest `--fd-pattern 3 'ERROR'` automatically

4. **FD usage visualization**
   - Show timeline of FD opens/closes
   - Correlate with error occurrences

## Summary

**Question:** Should watch mode detect custom FDs?  
**Answer:** ✅ YES, and it's now implemented and tested!

**Key Benefits:**
- ✅ Automatic, non-intrusive detection
- ✅ Helps ML system learn command behavior
- ✅ Provides debugging visibility
- ✅ Enables smarter future suggestions
- ✅ Tracks startup timing for timeout optimization

**All tests pass:** 6 passed, 1 skipped in 62.15s ✅

Ready for release! 🚀





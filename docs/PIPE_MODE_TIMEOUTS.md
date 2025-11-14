# Pipe Mode Timeout Support

## Summary

Implemented `--idle-timeout` and `--first-output-timeout` support for **pipe mode**, addressing the technical limitation that previously restricted these features to command mode only.

## The Insight

Initially, it was thought these features couldn't work in pipe mode because `earlyexit` doesn't control the upstream process. However, as the user pointed out:

1. **Both processes start simultaneously** when the shell creates the pipeline
2. **`ee` can track elapsed time** from its own start
3. **When `ee` exits, upstream gets SIGPIPE** and terminates automatically

So while `ee` can't directly kill the upstream process, it doesn't need to - the pipe mechanism handles it!

## Implementation

### What Was Added

**In `cli.py` (pipe mode section):**
- Added timeout monitoring thread (similar to command mode)
- Track `first_output_seen` and `last_output_time`
- Monitor for:
  - **First output timeout**: No output within N seconds of start
  - **Idle timeout**: No output for N seconds after first output
- Exit with code 2 on timeout

### How It Works

```bash
terraform apply | ee --idle-timeout 60 'error'
```

1. Shell spawns both `terraform` and `ee` simultaneously
2. `ee` starts monitoring thread that checks:
   - Time since `ee` started (for first-output-timeout)
   - Time since last line received (for idle-timeout)
3. `process_stream()` updates `last_output_time` on each line
4. If timeout detected:
   - Monitoring thread sets `timed_out[0] = True`
   - After `process_stream()` returns, check flag and exit with code 2
   - Upstream process receives **SIGPIPE** and terminates

## Examples

### First Output Timeout
```bash
# Timeout if no output within 30 seconds
slow_service 2>&1 | ee --first-output-timeout 30 'error'
```

Detects:
- Slow startup
- Hung processes that never produce output
- Misconfgured commands

### Idle Timeout
```bash
# Timeout if no output for 60 seconds
terraform apply 2>&1 | ee --idle-timeout 60 'error'
```

Detects:
- Processes that hang mid-execution
- Stalled operations
- Network timeouts

### Combined
```bash
# Both timeouts
terraform apply 2>&1 | tee terraform.log | ee -t 600 --idle-timeout 60 --first-output-timeout 30 'error'
```

## What Still Differs Between Modes

| Feature | Pipe Mode | Command Mode |
|---------|-----------|--------------|
| `--idle-timeout` | ✅ Works | ✅ Works |
| `--first-output-timeout` | ✅ Works | ✅ Works |
| Process termination | SIGPIPE (abrupt) | SIGTERM then SIGKILL (graceful) |
| Can monitor custom FDs | ❌ No | ✅ Yes (`--fd 3`) |
| Can monitor stderr separately | Need `2>&1` | ✅ By default |
| Error context capture | ❌ No `--delay-exit` | ✅ Yes |

## Tests Verified

All tests pass:

1. ✅ **First output timeout** - Detects when upstream produces no output
2. ✅ **First output success** - No timeout when output arrives in time  
3. ✅ **Idle timeout** - Detects when upstream stalls
4. ✅ **Continuous output** - No idle timeout when output is regular
5. ✅ **Pattern match** - Normal pattern matching still works with timeouts

## Updated Documentation

- **README.md**: Updated pipe mode examples to show timeout features
- **README.md**: Updated mode comparison table 
- **README.md**: Added note about SIGPIPE termination

## Technical Notes

### Why This Works

The key insight is that **pipe-based process termination is sufficient**:
- When `ee` exits, the pipe closes
- Upstream gets SIGPIPE on next write attempt
- Default SIGPIPE handler terminates the process
- Shell cleans up the pipeline

### Limitations vs Command Mode

**Graceful shutdown:**
- Command mode: `ee` sends SIGTERM, waits, then SIGKILL if needed
- Pipe mode: Upstream gets SIGPIPE immediately (less graceful)

For most use cases (terraform, kubectl, build tools), this is fine. These tools handle SIGPIPE appropriately.

### Edge Cases

**If upstream ignores SIGPIPE:**
- Rare, but some programs ignore SIGPIPE
- They'll keep running but output goes nowhere
- User can Ctrl+C to force termination
- Command mode is better for these cases

## Credit

Thanks to the user for the excellent technical insight that made this feature possible! The original assumption that pipe mode couldn't support these features was based on a misunderstanding of Unix pipe semantics.

## Related Files

- `earlyexit/cli.py` - Implementation  
- `README.md` - User documentation
- `docs/COMPATIBILITY_SUMMARY.md` - Feature matrix

---

**Result:** Pipe mode now has feature parity with command mode for timeout detection!





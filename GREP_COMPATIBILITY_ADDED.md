# grep Compatibility: -A and -B Flags Added ✅

## Summary

Added full `grep`-compatible context flags to make `earlyexit` a true drop-in replacement for `grep`.

## New Flags Added

### 1. `-A` / `--after-context` (Time-Based)

**Syntax:** `-A SECONDS` or `--after-context SECONDS`

**Behavior:** After a match, continue reading for N seconds to capture error context.

```bash
# Like grep -A but time-based (better for error traces)
ee -A 10 'Error' terraform apply
# Captures 10 seconds of output after "Error" appears
```

**Aliases:**
- `-A` (grep-compatible)
- `--after-context` (grep-compatible)
- `--delay-exit` (original name, still supported)

### 2. `-B` / `--before-context` (Line-Based)

**Syntax:** `-B NUM` or `--before-context NUM`

**Behavior:** Print NUM lines of leading context before matching lines (exactly like `grep -B`).

```bash
# Print 3 lines before the error
ee -B 3 'Error' terraform apply
```

**Implementation:**
- Uses a circular buffer (`deque`) to store last N lines
- Prints buffered lines when match is found
- Line numbers use `-` separator (like `grep`: `123-` for context, `124:` for match)

## Combined Usage

```bash
# Full grep compatibility
ee -B 3 -A 10 'ERROR' ./build.sh

# Equivalent to (but better than):
./build.sh 2>&1 | grep -B 3 -A 10 'ERROR'
# (grep version buffers, ee version is real-time)
```

## Key Differences from grep

| Feature | `grep -A NUM` | `ee -A NUM` |
|---------|---------------|-------------|
| Unit | Lines | **Seconds** (time-based) |
| Why | Count lines after match | Capture full error traces |
| Buffering | ❌ Buffers in pipes | ✅ Real-time |

**Rationale:** Time-based `-A` is better for error detection because:
- Error traces don't have predictable line counts
- Stack traces vary in length
- 10 seconds captures everything, 10 lines might cut off

## Cursor Rule Updates

Updated `.cursor/rules/useearlyexit.mdc` to teach Cursor about:

1. **`grep -A/-B` replacement:**
   ```bash
   # ❌ WRONG
   cmd | tee log | grep -B 3 -A 3 "pattern"
   
   # ✅ CORRECT
   ee -B 3 -A 10 'pattern' cmd
   ```

2. **`tail -100` pattern (user cancels often):**
   ```bash
   # ❌ WRONG: User sees nothing, cancels
   terraform apply | tee log | tail -100
   
   # ✅ BETTER: Watch mode with Ctrl+C learning
   ee terraform apply
   # User presses Ctrl+C → ee asks "What pattern to watch for?"
   ```

## Watch Mode + Ctrl+C

**Your question:** "Does cancel command work with ee if ee terraform was run and kick it into training prompt?"

**Answer:** ✅ **YES!** This is exactly how watch mode works:

```bash
# Run without pattern
ee terraform apply

# Press Ctrl+C when you see an error
# ee shows interactive prompt:
#   🔍 What happened?
#   1. Saw an error (teach pattern)
#   2. Process hung (set idle timeout)
#   3. Taking too long (set overall timeout)
#   4. Just testing (skip)
#
# You choose option 1, ee suggests patterns from the output
# Next time, ee watches for that pattern automatically!
```

**Exit code:** Returns 130 (standard SIGINT code) so scripts know it was interrupted.

## Documentation Updates

1. **`docs/USER_GUIDE.md`** - Added `-A` and `-B` to Error Context Options
2. **`.cursor/rules/useearlyexit.mdc`** - Added grep compatibility section and `tail -100` guidance
3. **`earlyexit/cli.py`** - Implemented `-B` buffering and `-A` aliasing

## Code Changes

### `earlyexit/cli.py`

1. **Added arguments:**
   ```python
   parser.add_argument('-A', '--after-context', '--delay-exit', 
                      dest='delay_exit', ...)
   parser.add_argument('-B', '--before-context', type=int, ...)
   ```

2. **Implemented `-B` buffering:**
   - Uses `deque` to store last N lines
   - Prints context lines before match with `-` separator
   - Clears buffer after printing to avoid duplicates

3. **Line number format:**
   - Context lines: `123-context line`
   - Match lines: `124:matched line`
   - (Exactly like `grep -n -B`)

## Testing

```bash
# Test -B flag
echo -e "line1\nline2\nERROR here\nline4" | ee -B 2 'ERROR'
# Should print:
#   line1
#   line2
#   ERROR here

# Test -A flag (time-based)
ee -A 5 'Error' terraform apply
# Captures 5 seconds after "Error" appears

# Test combined
ee -B 3 -A 10 'FAIL' npm test
# 3 lines before, 10 seconds after
```

## Benefits

1. ✅ **Drop-in grep replacement** - familiar flags
2. ✅ **Real-time output** - no buffering delays
3. ✅ **Better error capture** - time-based `-A` gets full traces
4. ✅ **Interactive learning** - Ctrl+C teaches patterns
5. ✅ **Cursor adoption** - AI assistants can suggest `ee` instead of broken pipes

## Status

**Ready for release 0.0.4** 🚀

All grep-compatible flags implemented and documented.





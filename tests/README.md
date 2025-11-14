# Test Suite

This directory contains regression tests that validate all claimed features in the README.

## Test Index

### 🧪 Automated Test Scripts

| Test File | Feature Tested | What It Proves | Run Command |
|-----------|----------------|----------------|-------------|
| [`test_pipe_timeouts.sh`](./test_pipe_timeouts.sh) | Idle & Startup Detection (Pipe Mode) | `--idle-timeout` and `--first-output-timeout` work in pipe mode, upstream gets SIGPIPE on exit | `./tests/test_pipe_timeouts.sh` |
| [`test_delay_exit.sh`](./test_delay_exit.sh) | Error Context Capture | `--delay-exit` captures full error context after match | `./tests/test_delay_exit.sh` |
| [`test_timeouts.sh`](./test_timeouts.sh) | Timeout Management | `-t`, `--idle-timeout`, `--first-output-timeout` all work correctly | `./tests/test_timeouts.sh` |
| [`test_fd.sh`](./test_fd.sh) | Custom File Descriptors | `--fd 3 --fd 4` monitors custom file descriptors | `./tests/test_fd.sh` |
| [`test_multifd.sh`](./test_multifd.sh) | Monitor stderr | Separate monitoring of stdout and stderr with `--stdout`, `--stderr` | `./tests/test_multifd.sh` |

### 📚 Documentation Proofs

| Feature | Documentation | What It Explains |
|---------|---------------|------------------|
| ML Validation | [`docs/PIPE_MODE_TIMEOUTS.md`](../docs/PIPE_MODE_TIMEOUTS.md) | How TP/TN/FP/FN tracking works |
| Smart Suggestions | [`docs/PIPE_MODE_TIMEOUTS.md`](../docs/PIPE_MODE_TIMEOUTS.md) | How learning system provides suggestions |
| Learning System | [`docs/PIPE_MODE_TIMEOUTS.md`](../docs/PIPE_MODE_TIMEOUTS.md) | Interactive learning from Ctrl+C |
| Unbuffered Output | [`demo_stdbuf_position.sh`](../demo_stdbuf_position.sh) | Proof that `stdbuf` position matters |

## Test Details

### test_pipe_timeouts.sh

**Tests:**
1. ✅ First output timeout - Detects when upstream produces no output
2. ✅ First output success - No timeout when output arrives in time
3. ✅ Idle timeout - Detects when upstream stalls
4. ✅ Continuous output - No idle timeout when output is regular
5. ✅ Pattern match - Normal pattern matching works with timeouts

**Exit Codes Verified:**
- Exit code 2 for timeouts
- Exit code 0 for pattern match
- Exit code 1 for no match

**Proves README Claims:**
- ✅ Idle detection works in pipe mode
- ✅ Startup detection works in pipe mode  
- ✅ Upstream process receives SIGPIPE and terminates

### test_delay_exit.sh

**Tests:**
- Immediate exit without `--delay-exit`
- Delayed exit with `--delay-exit 5`
- Line count-based early exit with `--delay-exit-after-lines`
- Combined time and line limits

**Proves README Claims:**
- ✅ Error context capture works (command mode)
- ✅ Configurable delay after pattern match
- ✅ Smart exit on time OR line count

### test_pipe_delay_exit.sh

**Tests:**
- Delay-exit captures context after error in pipe mode
- Time-based context capture with streaming input
- delay-exit=0 exits immediately (backward compatible)
- Default behavior (no delay-exit) exits immediately on match
- Line count-based early exit with `--delay-exit-after-lines`

**Proves README Claims:**
- ✅ `--delay-exit` works in pipe mode
- ✅ Error context capture in pipes
- ✅ Smart exit on time OR line count in pipe mode
- ✅ Backward compatible default behavior

### test_watch_fd_detection.sh

**Tests:**
- Watch mode detects custom file descriptors (with psutil)
- Watch mode shows FD paths in verbose mode
- Watch mode tracks startup timing (first output time)
- Watch mode displays helpful startup messages

**Proves README Claims:**
- ✅ Watch mode detects and logs custom FDs
- ✅ Watch mode tracks startup detection
- ✅ FD detection integrated with ML/learning system
- ✅ Non-intrusive detection (doesn't slow down output)

### test_timeouts.sh

**Tests:**
- Overall timeout with `-t`
- Idle timeout with `--idle-timeout`
- First output timeout with `--first-output-timeout`
- Combined timeout scenarios

**Proves README Claims:**
- ✅ Multiple timeout types work
- ✅ Timeouts are independent
- ✅ Correct exit codes (2) for all timeout types

### test_fd.sh

**Tests:**
- Monitoring file descriptor 3
- Monitoring multiple FDs (3, 4, 5)
- Different patterns per FD with `--fd-pattern`
- FD prefix labeling with `--fd-prefix`

**Proves README Claims:**
- ✅ Custom FD monitoring works
- ✅ Per-FD pattern matching
- ✅ FD prefix labeling

### test_multifd.sh

**Tests:**
- Stdout-only monitoring with `--stdout`
- Stderr-only monitoring with `--stderr`
- Both streams by default
- FD prefix labeling

**Proves README Claims:**
- ✅ Separate stderr monitoring (command mode)
- ✅ Default monitors both streams
- ✅ Can select specific streams

## Running All Tests

### For Contributors

**Run everything with pytest (recommended):**

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests (Python + shell scripts)
pytest tests/

# Run only shell script tests
pytest tests/test_shell_scripts.py -v

# Run only Python unit tests
pytest tests/ --ignore=tests/test_shell_scripts.py

# Run with output visible
pytest tests/ -s
```

### Manual Testing

**Run individual shell tests:**

```bash
./tests/test_pipe_timeouts.sh
./tests/test_delay_exit.sh
./tests/test_timeouts.sh
./tests/test_fd.sh
./tests/test_multifd.sh
```

**Run all shell tests:**

```bash
for test in tests/test_*.sh; do
    echo "Running $test..."
    "$test" || echo "FAILED: $test"
done
```

### Quick Validation

```bash
# Quick check before committing
pytest tests/test_shell_scripts.py -v

# Full test suite
pytest tests/ -v
```

## Adding New Tests

When adding a new feature:

1. **Create a test script** in `tests/test_<feature>.sh`
2. **Make it executable**: `chmod +x tests/test_<feature>.sh`
3. **Follow the pattern**:
   - Test all claimed behaviors
   - Verify exit codes
   - Test edge cases
   - Print clear success/failure messages
4. **Update this README** with test details
5. **Link from main README** in the feature comparison table

## Test Conventions

- ✅ Use clear test names: `Test 1: <what it tests>`
- ✅ Print expected behavior before running
- ✅ Verify exit codes explicitly
- ✅ Use color for pass/fail (green ✅ / red ❌)
- ✅ Clean up temporary files
- ✅ Exit code 0 = all tests passed
- ✅ Print summary at the end

## CI Integration

These tests can be run in CI:

```yaml
# .github/workflows/test.yml
- name: Run functional tests
  run: |
    for test in tests/test_*.sh; do
      "$test" || exit 1
    done
```

## Maintenance

- **After each release**: Run all tests to verify no regressions
- **Before each README update**: Ensure claims have corresponding tests
- **If a test fails**: Either fix the bug or update the docs/README
- **Keep tests simple**: Easy to understand = easy to maintain

---

**These tests prove our README claims are accurate!** 🎯

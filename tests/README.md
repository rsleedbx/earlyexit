# Earlyexit Tests

This directory contains test scripts for the `earlyexit` project.

## Test Files

### Python Tests

- **`test_earlyexit.py`** - Unit tests for core earlyexit functionality
  - Run with: `pytest test_earlyexit.py`

- **`test_subprocess_telemetry.py`** - Tests telemetry from subprocess invocations
  - Verifies SQLite logging works correctly when earlyexit is spawned as subprocess
  - Tests single, concurrent, and timeout scenarios
  - Run with: `python3 test_subprocess_telemetry.py`

### Shell Scripts

#### Feature Tests

- **`test_fd.sh`** - Tests file descriptor monitoring
  - Verifies stdout/stderr/custom FD monitoring
  - Tests per-FD pattern matching
  
- **`test_multifd.sh`** - Tests multiple file descriptor monitoring
  - Concurrent monitoring of multiple streams
  - Per-FD prefix display

- **`test_timeouts.sh`** - Tests timeout functionality
  - Overall timeout (`-t`)
  - Idle timeout (`--idle-timeout`)
  - First output timeout (`--first-output-timeout`)

- **`test_delay_exit.sh`** - Tests delay-exit feature
  - Verifies delayed termination after pattern match
  - Tests error context capture

## Running Tests

### Run All Python Tests
```bash
cd tests
pytest test_earlyexit.py -v
```

### Run Specific Shell Test
```bash
cd tests
bash test_fd.sh
bash test_timeouts.sh
bash test_multifd.sh
bash test_delay_exit.sh
```

### Run All Shell Tests
```bash
cd tests
for test in test_*.sh; do
    echo "Running $test..."
    bash "$test"
    echo ""
done
```

## Test Coverage

### Core Functionality
- ✅ Pattern matching (Python regex, Perl regex)
- ✅ Pipe mode
- ✅ Command mode
- ✅ Line number display
- ✅ Color output

### Advanced Features
- ✅ File descriptor monitoring
- ✅ Multiple stream monitoring
- ✅ Per-FD pattern matching
- ✅ Overall timeout
- ✅ Idle timeout
- ✅ First output timeout
- ✅ Delay-exit feature

### Telemetry & ML
- ✅ Telemetry capture
- ✅ Match event recording
- ✅ SQLite concurrency
- ✅ Subprocess telemetry (verified 100% reliable)

## Adding New Tests

### Python Tests
Add test functions to `test_earlyexit.py`:
```python
def test_new_feature():
    """Test description"""
    # Your test code
    assert True
```

### Shell Tests
Create a new `test_feature.sh`:
```bash
#!/bin/bash
# Test new feature

echo "Testing new feature..."
earlyexit "pattern" -- command
# Verify results
echo "✅ Test passed"
```

Make it executable:
```bash
chmod +x test_feature.sh
```

## CI/CD Integration

These tests can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run Python tests
  run: |
    cd tests
    pytest test_earlyexit.py -v

- name: Run Shell tests  
  run: |
    cd tests
    for test in test_*.sh; do bash "$test"; done
```

## Notes

- Shell tests use the installed `earlyexit` command
- Ensure `earlyexit` is installed before running tests: `pip install -e .`
- Some tests may require specific system tools (timeout, etc.)


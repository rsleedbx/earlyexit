# Phase 1: Observability & Debugging Features

**Strategy:** Implement observability tools first to help debug advanced features later.

**Target:** Complete within 1 week

---

## Feature Order

1. ✅ Exit Code Convention (`--unix-exit-codes`)
2. ✅ JSON Output Mode (`--json`)
3. ✅ Progress Indicator (`--progress`)

**Total Estimated Time:** 8-11 hours

---

## 1. Exit Code Convention (`--unix-exit-codes`) ⭐⭐⭐⭐⭐

**Priority:** HIGHEST - Affects all testing and integration

### Current Behavior (grep-style)
```
0 = pattern matched (error found)
1 = no match (success)
2 = timeout
3 = CLI error
4 = detached
```

### New Behavior with `--unix-exit-codes`
```
0 = success (no error found)
1 = error found (pattern matched)
2 = timeout
3 = CLI error
4 = detached
```

### Implementation

#### 1.1 Add CLI Argument
```python
# In cli.py, around line 1300 with other flags
parser.add_argument('--unix-exit-codes', action='store_true',
                   help='Use Unix convention for exit codes: 0=success (no match), '
                        '1=failure (pattern matched). Default is grep convention: '
                        '0=match, 1=no match.')
```

#### 1.2 Create Exit Code Mapper Function
```python
# In cli.py, before main()
def map_exit_code(code: int, use_unix_convention: bool) -> int:
    """
    Map exit codes based on convention
    
    Args:
        code: Original exit code
        use_unix_convention: If True, use Unix convention (0=success)
                            If False, use grep convention (0=match)
    
    Returns:
        Mapped exit code
    """
    if not use_unix_convention:
        return code  # Keep grep convention (current behavior)
    
    # Unix convention: invert 0 and 1
    if code == 0:
        # Pattern matched (error found) → Unix failure
        return 1
    elif code == 1:
        # No match (success) → Unix success
        return 0
    else:
        # Keep other codes as-is (timeouts, errors, detached)
        return code
```

#### 1.3 Apply Mapping in main()
```python
def main():
    """Main entry point"""
    # ... existing argument parsing ...
    
    # Run the appropriate mode
    if not args.command or (sys.stdin and not sys.stdin.isatty()):
        exit_code = run_pipe_mode(args, pattern, use_color, ...)
    else:
        exit_code = run_command_mode(args, pattern, use_color, ...)
    
    # Map exit code if unix convention requested
    if hasattr(args, 'unix_exit_codes') and args.unix_exit_codes:
        exit_code = map_exit_code(exit_code, True)
    
    return exit_code
```

### Tests

```python
# tests/test_exit_codes.py (new file)
import subprocess
import pytest

def test_unix_exit_codes_match():
    """Test --unix-exit-codes when pattern matches"""
    result = subprocess.run(
        ['earlyexit', '--unix-exit-codes', 'ERROR', '--',
         'bash', '-c', 'echo "ERROR detected"'],
        capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 1, "Unix mode: error found = exit 1"
    assert "ERROR detected" in result.stdout

def test_unix_exit_codes_no_match():
    """Test --unix-exit-codes when no pattern match"""
    result = subprocess.run(
        ['earlyexit', '--unix-exit-codes', 'ERROR', '--',
         'bash', '-c', 'echo "All good"'],
        capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 0, "Unix mode: no error = exit 0"

def test_unix_exit_codes_timeout():
    """Test --unix-exit-codes preserves timeout exit code"""
    result = subprocess.run(
        ['earlyexit', '--unix-exit-codes', '-t', '1', 'NEVER', '--',
         'bash', '-c', 'sleep 10'],
        capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 2, "Unix mode: timeout still = exit 2"

def test_grep_convention_default():
    """Test default grep convention still works"""
    result = subprocess.run(
        ['earlyexit', 'ERROR', '--',
         'bash', '-c', 'echo "ERROR detected"'],
        capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 0, "Default: match = exit 0"

def test_unix_exit_codes_with_detach():
    """Test --unix-exit-codes with detach mode"""
    import tempfile
    import os
    
    pidfile = tempfile.mktemp()
    try:
        result = subprocess.run(
            ['earlyexit', '--unix-exit-codes', '-D', '--pid-file', pidfile,
             '--delay-exit', '0', 'Ready', '--',
             'bash', '-c', 'echo "Ready"; sleep 100'],
            capture_output=True, text=True, timeout=5
        )
        assert result.returncode == 4, "Unix mode: detached still = exit 4"
    finally:
        if os.path.exists(pidfile):
            with open(pidfile) as f:
                pid = int(f.read().strip())
            try:
                os.kill(pid, 9)
            except:
                pass
            os.unlink(pidfile)
```

### Documentation

Update README.md:
```markdown
## Exit Codes

### Default Behavior (grep convention)
- `0` - Pattern matched (error found) ✅ Early exit triggered
- `1` - No match (command completed without matching pattern)
- `2` - Timeout (overall, idle, or first-output)
- `3` - CLI error (invalid arguments, etc.)
- `4` - Detached (with `-D` flag)

### Unix Convention (`--unix-exit-codes`)
For integration into shell scripts that expect 0=success:

- `0` - Success (no error pattern found) ✅
- `1` - Failure (error pattern matched)
- `2` - Timeout
- `3` - CLI error
- `4` - Detached

```bash
# Example: Use in deployment scripts
ee --unix-exit-codes 'Error|Failed' -- terraform apply
if [ $? -eq 0 ]; then
    echo "✅ Deployment successful"
    notify-slack "Deploy completed"
else
    echo "❌ Deployment failed"
    rollback-deployment
fi
```

**Note:** The default follows `grep` convention for consistency with Unix tools.
Use `--unix-exit-codes` when integrating with scripts that expect 0=success.
```

**Estimated Time:** 2-3 hours

---

## 2. JSON Output Mode (`--json`) ⭐⭐⭐

**Priority:** HIGH - Enables programmatic integration

### What We Need

```bash
ee --json -t 1800 'Error' -- terraform apply
```

**Output:**
```json
{
  "version": "0.0.5",
  "exit_code": 1,
  "exit_reason": "pattern_matched",
  "pattern": "Error",
  "matched_line": "Error: Failed to load plugin schemas",
  "line_number": 42,
  "duration_seconds": 15.3,
  "command": ["terraform", "apply"],
  "timeouts": {
    "overall": 1800,
    "idle": null,
    "first_output": null
  },
  "statistics": {
    "lines_processed": 1247,
    "bytes_processed": 52847,
    "time_to_first_output": 2.1,
    "time_to_match": 15.3
  },
  "log_files": {
    "stdout": "/tmp/ee-terraform_apply-12345.log",
    "stderr": "/tmp/ee-terraform_apply-12345.errlog"
  }
}
```

### Implementation

#### 2.1 Add CLI Argument
```python
parser.add_argument('--json', action='store_true',
                   help='Output results as JSON (suppresses normal output). '
                        'Useful for programmatic parsing and integration.')
```

#### 2.2 Create JSON Output Structure
```python
# In cli.py, create data class or dict structure
def create_json_output(
    exit_code: int,
    exit_reason: str,
    pattern: str,
    matched_line: Optional[str],
    line_number: Optional[int],
    duration: float,
    command: List[str],
    timeouts: dict,
    statistics: dict,
    log_files: dict
) -> str:
    """
    Create JSON output for --json flag
    
    Returns:
        JSON string
    """
    import json
    
    output = {
        "version": "0.0.5",
        "exit_code": exit_code,
        "exit_reason": exit_reason,  # pattern_matched, no_match, timeout, error, detached
        "pattern": pattern,
        "matched_line": matched_line,
        "line_number": line_number,
        "duration_seconds": round(duration, 2),
        "command": command,
        "timeouts": timeouts,
        "statistics": statistics,
        "log_files": log_files
    }
    
    return json.dumps(output, indent=2)
```

#### 2.3 Track Statistics During Execution
```python
# In run_command_mode() and run_pipe_mode()
# Track these values:
statistics = {
    'lines_processed': 0,
    'bytes_processed': 0,
    'time_to_first_output': None,
    'time_to_match': None
}

# In process_stream(), increment:
statistics['lines_processed'] += 1
statistics['bytes_processed'] += len(line)

# On first output:
if first_output_seen and statistics['time_to_first_output'] is None:
    statistics['time_to_first_output'] = time.time() - start_time

# On match:
if match_found:
    statistics['time_to_match'] = time.time() - start_time
```

#### 2.4 Suppress Output in JSON Mode
```python
# Modify process_stream() to check args.json:
if not args.quiet and not args.json:
    print(line_stripped, flush=True)

# Suppress progress messages when --json
if not args.quiet and not args.json:
    print("🔍 Watch mode enabled", file=sys.stderr)
```

#### 2.5 Output JSON at End
```python
def main():
    # ... run mode ...
    
    if args.json:
        # Collect all data
        json_output = create_json_output(
            exit_code=exit_code,
            exit_reason=determine_exit_reason(exit_code, matched_line),
            pattern=original_pattern,
            matched_line=matched_line,
            line_number=matched_line_number,
            duration=time.time() - start_time,
            command=args.command,
            timeouts={
                'overall': args.timeout,
                'idle': args.idle_timeout,
                'first_output': args.first_output_timeout
            },
            statistics=statistics,
            log_files={
                'stdout': stdout_log_path,
                'stderr': stderr_log_path
            }
        )
        print(json_output)
    
    return exit_code
```

### Tests

```python
# tests/test_json_output.py (new file)
import subprocess
import json
import pytest

def test_json_output_format():
    """Test --json produces valid JSON"""
    result = subprocess.run(
        ['earlyexit', '--json', 'ERROR', '--',
         'bash', '-c', 'echo "line 1"; echo "ERROR found"; echo "line 3"'],
        capture_output=True, text=True, timeout=5
    )
    
    # Should be valid JSON
    data = json.loads(result.stdout)
    
    # Check required fields
    assert 'version' in data
    assert 'exit_code' in data
    assert 'exit_reason' in data
    assert 'pattern' in data
    assert 'matched_line' in data
    assert 'duration_seconds' in data
    
    # Check values
    assert data['exit_code'] == 0  # Pattern matched (grep convention)
    assert data['exit_reason'] == 'pattern_matched'
    assert data['pattern'] == 'ERROR'
    assert 'ERROR found' in data['matched_line']

def test_json_no_match():
    """Test --json when pattern doesn't match"""
    result = subprocess.run(
        ['earlyexit', '--json', 'ERROR', '--',
         'bash', '-c', 'echo "All good"'],
        capture_output=True, text=True, timeout=5
    )
    
    data = json.loads(result.stdout)
    assert data['exit_code'] == 1  # No match
    assert data['exit_reason'] == 'no_match'
    assert data['matched_line'] is None

def test_json_with_timeout():
    """Test --json with timeout"""
    result = subprocess.run(
        ['earlyexit', '--json', '-t', '1', 'NEVER', '--',
         'bash', '-c', 'sleep 10'],
        capture_output=True, text=True, timeout=5
    )
    
    data = json.loads(result.stdout)
    assert data['exit_code'] == 2
    assert data['exit_reason'] == 'timeout'
    assert data['timeouts']['overall'] == 1

def test_json_with_unix_exit_codes():
    """Test --json with --unix-exit-codes"""
    result = subprocess.run(
        ['earlyexit', '--json', '--unix-exit-codes', 'ERROR', '--',
         'bash', '-c', 'echo "ERROR found"'],
        capture_output=True, text=True, timeout=5
    )
    
    data = json.loads(result.stdout)
    assert data['exit_code'] == 1  # Unix: error = 1
    assert data['exit_reason'] == 'pattern_matched'

def test_json_suppresses_output():
    """Test --json suppresses normal output"""
    result = subprocess.run(
        ['earlyexit', '--json', 'ERROR', '--',
         'bash', '-c', 'echo "line 1"; echo "ERROR"; echo "line 3"'],
        capture_output=True, text=True, timeout=5
    )
    
    # stdout should only contain JSON, not command output
    assert '"exit_reason"' in result.stdout
    assert 'line 1' not in result.stdout
    assert 'line 3' not in result.stdout
```

### Documentation

```markdown
## JSON Output Mode

For programmatic parsing and integration:

```bash
ee --json -t 1800 'Error' -- terraform apply
```

**Output:**
```json
{
  "version": "0.0.5",
  "exit_code": 0,
  "exit_reason": "pattern_matched",
  "pattern": "Error",
  "matched_line": "Error: Failed to load plugin schemas",
  "line_number": 42,
  "duration_seconds": 15.3,
  "command": ["terraform", "apply"],
  "timeouts": {
    "overall": 1800,
    "idle": null,
    "first_output": null
  },
  "statistics": {
    "lines_processed": 1247,
    "bytes_processed": 52847,
    "time_to_first_output": 2.1,
    "time_to_match": 15.3
  },
  "log_files": {
    "stdout": "/tmp/ee-terraform_apply-12345.log",
    "stderr": "/tmp/ee-terraform_apply-12345.errlog"
  }
}
```

**Use Cases:**
```python
# Python integration
import subprocess
import json

result = subprocess.run(
    ['ee', '--json', '--unix-exit-codes', 'Error', '--', 'terraform', 'apply'],
    capture_output=True, text=True
)

data = json.loads(result.stdout)

if data['exit_code'] == 0:
    print(f"✅ Success in {data['duration_seconds']}s")
elif data['exit_reason'] == 'pattern_matched':
    print(f"❌ Error at line {data['line_number']}: {data['matched_line']}")
    # Retrieve full logs
    with open(data['log_files']['stderr']) as f:
        error_log = f.read()
elif data['exit_reason'] == 'timeout':
    print(f"⏱️  Timeout after {data['duration_seconds']}s")
```

**Exit Reasons:**
- `pattern_matched` - Pattern was found
- `no_match` - Pattern not found, command completed
- `timeout` - Overall timeout exceeded
- `idle_timeout` - No output for idle timeout period
- `first_output_timeout` - No initial output
- `error` - CLI error
- `detached` - Process detached
```

**Estimated Time:** 3-4 hours

---

## 3. Progress Indicator (`--progress`) ⭐⭐

**Priority:** MEDIUM - Improves UX for long operations

### What We Need

```bash
ee --progress -t 1800 'Error' -- terraform apply
```

**Display:**
```
[00:03:42 / 30:00] Monitoring terraform apply...
  Last output: 2s ago
  Lines processed: 1,247
  Status: Running
```

### Implementation

#### 3.1 Add CLI Argument
```python
parser.add_argument('--progress', action='store_true',
                   help='Show progress indicator (elapsed time, timeout remaining, stats). '
                        'Updates every few seconds on stderr.')
```

#### 3.2 Create Progress Display Thread
```python
def show_progress_indicator(args, start_time, last_output_time, lines_processed, 
                           match_count, stop_event):
    """
    Display progress indicator on stderr
    
    Args:
        args: Arguments namespace
        start_time: When monitoring started
        last_output_time: List with [last_output_timestamp]
        lines_processed: List with [count]
        match_count: List with [count]
        stop_event: Threading event to signal stop
    """
    import sys
    
    while not stop_event.is_set():
        elapsed = time.time() - start_time
        elapsed_str = format_duration(elapsed)
        
        if args.timeout:
            remaining = args.timeout - elapsed
            remaining_str = format_duration(remaining)
            timeout_str = f"{elapsed_str} / {format_duration(args.timeout)}"
        else:
            timeout_str = elapsed_str
        
        # Time since last output
        if last_output_time[0]:
            since_output = time.time() - last_output_time[0]
            last_output_str = format_duration(since_output) + " ago"
        else:
            last_output_str = "waiting..."
        
        # Build progress line
        command_name = args.command[0] if args.command else "stdin"
        progress = (
            f"\r[{timeout_str}] Monitoring {command_name}... "
            f"Last output: {last_output_str} | "
            f"Lines: {lines_processed[0]:,} | "
            f"Matches: {match_count[0]}"
        )
        
        # Clear line and print
        sys.stderr.write('\r' + ' ' * 120 + '\r')  # Clear line
        sys.stderr.write(progress)
        sys.stderr.flush()
        
        # Update every 2 seconds
        stop_event.wait(2)
    
    # Clear progress line when done
    sys.stderr.write('\r' + ' ' * 120 + '\r')
    sys.stderr.flush()

def format_duration(seconds):
    """Format seconds as HH:MM:SS or MM:SS"""
    if seconds < 0:
        return "00:00"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"
```

#### 3.3 Start Progress Thread
```python
def run_command_mode(...):
    # ... existing setup ...
    
    # Start progress indicator if requested
    progress_stop_event = None
    progress_thread = None
    
    if args.progress and not args.quiet and not args.json:
        progress_stop_event = threading.Event()
        progress_thread = threading.Thread(
            target=show_progress_indicator,
            args=(args, start_time, last_output_time, lines_processed_total,
                  match_count, progress_stop_event),
            daemon=True
        )
        progress_thread.start()
    
    try:
        # ... existing monitoring ...
        pass
    finally:
        # Stop progress indicator
        if progress_stop_event:
            progress_stop_event.set()
        if progress_thread:
            progress_thread.join(timeout=1)
```

### Tests

```python
# tests/test_progress.py
import subprocess
import time
import pytest

def test_progress_indicator_appears():
    """Test --progress shows progress on stderr"""
    result = subprocess.run(
        ['earlyexit', '--progress', '-t', '5', 'NEVER', '--',
         'bash', '-c', 'for i in {1..20}; do echo "line $i"; sleep 0.2; done'],
        capture_output=True, text=True, timeout=10
    )
    
    # Progress should appear in stderr
    assert 'Monitoring bash' in result.stderr or 'Lines:' in result.stderr

def test_progress_with_json_suppressed():
    """Test --progress is suppressed when --json used"""
    result = subprocess.run(
        ['earlyexit', '--progress', '--json', 'ERROR', '--',
         'bash', '-c', 'echo "ERROR"'],
        capture_output=True, text=True, timeout=5
    )
    
    # JSON should be clean (no progress in stdout)
    import json
    data = json.loads(result.stdout)
    assert 'exit_code' in data

def test_progress_shows_timeout():
    """Test progress shows timeout countdown"""
    # Just verify it doesn't crash
    result = subprocess.run(
        ['earlyexit', '--progress', '-t', '3', 'NEVER', '--',
         'bash', '-c', 'sleep 10'],
        capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 2  # Timeout
```

### Documentation

```markdown
## Progress Indicator

Show live progress for long-running operations:

```bash
ee --progress -t 1800 'Error' -- terraform apply
```

**Display:**
```
[00:03:42 / 30:00] Monitoring terraform apply...
  Last output: 2s ago | Lines: 1,247 | Matches: 0
```

**Features:**
- Elapsed time and timeout remaining
- Time since last output (helps detect hangs)
- Lines processed counter
- Match counter
- Updates every 2 seconds

**Notes:**
- Displayed on stderr (doesn't interfere with stdout)
- Automatically suppressed with `--quiet` or `--json`
- Useful for monitoring in interactive terminals
```

**Estimated Time:** 3-4 hours

---

## 🗓️ **Implementation Schedule**

### Day 1-2: Exit Codes
- Implement `--unix-exit-codes`
- Write tests
- Update documentation
- **Deliverable:** Can use `--unix-exit-codes` for testing

### Day 3-4: JSON Output
- Implement `--json`
- Track statistics
- Write tests
- Update documentation
- **Deliverable:** Programmatic output for integration tests

### Day 5: Progress & Polish
- Implement `--progress`
- Write tests
- Final documentation updates
- Integration testing

---

## ✅ **Testing Strategy**

### Manual Testing Commands

```bash
# Test exit codes
ee --unix-exit-codes 'ERROR' -- echo "ERROR"; echo $?
ee 'ERROR' -- echo "ERROR"; echo $?

# Test JSON output
ee --json 'ERROR' -- echo "ERROR" | jq .
ee --json --unix-exit-codes 'ERROR' -- echo "ERROR" | jq .exit_code

# Test progress
ee --progress -t 10 'NEVER' -- bash -c 'for i in {1..20}; do echo "line $i"; sleep 0.3; done'

# Combine features
ee --json --unix-exit-codes --progress -t 30 'Error' -- terraform plan
```

### Integration Testing

```python
# Use JSON output to test other features
import subprocess
import json

def run_with_json(pattern, command):
    result = subprocess.run(
        ['ee', '--json', '--unix-exit-codes', pattern, '--'] + command,
        capture_output=True, text=True
    )
    return json.loads(result.stdout)

# Test various scenarios
data = run_with_json('Error', ['echo', 'Error found'])
assert data['exit_code'] == 1
assert data['exit_reason'] == 'pattern_matched'
```

---

## 📊 **Success Criteria**

- [ ] `--unix-exit-codes` works correctly (0=success, 1=error)
- [ ] `--json` produces valid JSON with all required fields
- [ ] `--progress` displays live updates without breaking output
- [ ] All three work together: `ee --json --unix-exit-codes --progress ...`
- [ ] Existing tests still pass
- [ ] New tests added for each feature
- [ ] Documentation updated in README and help text

---

## 🚀 **Next Phase**

After these observability features are complete, implement advanced pattern features:
1. Pattern exclusions (`--exclude`)
2. Pattern testing (`--test-pattern`)
3. Success patterns (`--success-pattern`)
4. Multi-line matching (`--multiline`)

**The observability tools will make debugging these much easier!**

---

## 💡 **Benefits**

1. **`--unix-exit-codes`**: Makes testing and scripting easier
2. **`--json`**: Enables programmatic testing and integration
3. **`--progress`**: Provides visibility during long operations

All three together create a solid foundation for developing and testing advanced features.


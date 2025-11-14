# Detach Mode Design: Exit Without Killing Subprocess

## Current Behavior

**When `earlyexit` exits on match:**
1. Calls `process.terminate()` (sends SIGTERM)
2. Waits 1 second
3. If still running, calls `process.kill()` (sends SIGKILL)
4. Returns exit code based on reason

**Location:** `earlyexit/cli.py:723-737`

---

## Proposed Feature: `--detach` Mode

### What It Does

Exit `earlyexit` without killing the subprocess, leaving it running in the background.

### Use Cases

1. **Long-running services:** Start a service, wait for "ready" message, then detach
2. **Background jobs:** Launch a job, wait for confirmation, let it continue
3. **Daemon processes:** Start daemon, wait for initialization, detach
4. **CI/CD:** Start service for tests, detach when ready, run tests, cleanup later

### Example

```bash
# Start service, wait for "Server listening", then detach
ee --detach 'Server listening on port' ./start-server.sh

# Service continues running in background
# earlyexit exits with code 4 and prints PID
```

---

## Design

### 1. New Flag

```bash
--detach              Exit without killing subprocess when pattern matches
                      Subprocess continues running. PID is printed to stderr.
                      Exit code: 4 (detached)
```

**Short flag:** `-D` (D = Detach)

### 2. Exit Code

**New exit code: 4 = Detached (subprocess still running)**

Updated exit codes:
```
0 - Pattern matched (subprocess killed)
1 - No match found
2 - Timeout exceeded
3 - Other error
4 - Detached (subprocess still running)
130 - Interrupted (Ctrl+C)
```

### 3. Behavior

**On pattern match with `--detach`:**
1. Do NOT call `process.terminate()` or `process.kill()`
2. Print subprocess PID to stderr
3. Close file descriptors (stdout/stderr pipes)
4. Return exit code 4

**Output format:**
```
Pattern matched: "Server listening on port 8080"
🔓 Detached from subprocess (PID: 12345)
   Use 'kill 12345' to stop it later
```

### 4. Limitations

**Only works in Command Mode:**
- ✅ Command mode: `ee --detach 'pattern' command`
- ❌ Pipe mode: Not applicable (no subprocess to detach from)
- ❌ Watch mode: Not applicable (watch mode doesn't have patterns)

**Detach only on match:**
- If timeout occurs → subprocess is killed (normal behavior)
- If no match → subprocess runs to completion (normal behavior)
- If error occurs → subprocess is killed (normal behavior)

---

## Implementation

### 1. Add Flag (cli.py)

```python
parser.add_argument('-D', '--detach', action='store_true',
                   help='Exit without killing subprocess when pattern matches (command mode only). '
                        'Subprocess continues running. PID printed to stderr. Exit code: 4')
```

### 2. Modify Process Termination Logic (cli.py:723-737)

**Current code:**
```python
if should_exit:
    # Kill the process on match (after delay)
    if timeout_timer:
        timeout_timer.cancel()
    try:
        process.terminate()
    except (PermissionError, OSError):
        pass
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except (PermissionError, OSError):
            pass
    break
```

**New code:**
```python
if should_exit:
    # Cancel timeout timer
    if timeout_timer:
        timeout_timer.cancel()
    
    # Check if detach mode is enabled
    if args.detach:
        # Detach mode: Don't kill subprocess
        if not args.quiet:
            print(f"\n🔓 Detached from subprocess (PID: {process.pid})", file=sys.stderr)
            print(f"   Subprocess continues running in background", file=sys.stderr)
            print(f"   Use 'kill {process.pid}' to stop it later", file=sys.stderr)
        # Don't terminate or kill - just break out of loop
        detached_pid = process.pid
        break
    else:
        # Normal mode: Kill subprocess
        try:
            process.terminate()
        except (PermissionError, OSError):
            pass
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except (PermissionError, OSError):
                pass
        break
```

### 3. Update Return Value (cli.py:930-934)

**Current code:**
```python
if match_count[0] >= args.max_count:
    return 0  # Pattern matched - early exit
elif match_count[0] > 0:
    return 0  # At least one match found
else:
    return 1  # No match found
```

**New code:**
```python
if match_count[0] >= args.max_count:
    if args.detach and detached_pid:
        return 4  # Detached (subprocess still running)
    else:
        return 0  # Pattern matched - early exit
elif match_count[0] > 0:
    return 0  # At least one match found
else:
    return 1  # No match found
```

### 4. Update Help Text (cli.py:1043-1047)

**Current:**
```
Exit codes:
  0 - Pattern matched (error detected)
  1 - No match found (success)
  2 - Timeout exceeded
  3 - Other error
```

**New:**
```
Exit codes:
  0 - Pattern matched (subprocess terminated)
  1 - No match found (subprocess completed)
  2 - Timeout exceeded
  3 - Other error
  4 - Detached (subprocess still running, --detach mode)
  130 - Interrupted (Ctrl+C)
```

### 5. Validation

**Add validation in main():**
```python
if args.detach:
    if not args.command:
        print("❌ Error: --detach requires command mode (not pipe mode)", file=sys.stderr)
        return 3
    if not args.pattern:
        print("❌ Error: --detach requires a pattern", file=sys.stderr)
        return 3
```

---

## Examples

### Example 1: Start Web Server

```bash
# Start server, wait for ready message, detach
ee --detach 'Server listening on port 8080' ./start-server.sh

# Output:
# Starting server...
# Server listening on port 8080
# 🔓 Detached from subprocess (PID: 12345)
#    Subprocess continues running in background
#    Use 'kill 12345' to stop it later

# Exit code: 4

# Server still running in background
ps aux | grep 12345
# 12345 ... ./start-server.sh
```

### Example 2: Database Initialization

```bash
# Start database, wait for ready, detach
ee -D 'database system is ready to accept connections' postgres -D /data

# Exit code: 4
# Database continues running

# Later, stop it:
kill 12345
```

### Example 3: CI/CD Pipeline

```bash
#!/bin/bash
# Start service for testing

# Start service and wait for ready
ee -D 'Service ready' ./start-service.sh
SERVICE_EXIT=$?

if [ $SERVICE_EXIT -eq 4 ]; then
    echo "✅ Service started successfully"
    
    # Run tests
    npm test
    TEST_EXIT=$?
    
    # Cleanup: Kill service
    # (PID was printed to stderr, capture it)
    
    exit $TEST_EXIT
else
    echo "❌ Service failed to start (exit code: $SERVICE_EXIT)"
    exit 1
fi
```

### Example 4: Capture PID for Later Use

```bash
# Capture PID from stderr
OUTPUT=$(ee -D 'Ready' ./service.sh 2>&1)
PID=$(echo "$OUTPUT" | grep "PID:" | awk '{print $NF}' | tr -d ')')

echo "Service PID: $PID"

# Do work...

# Cleanup
kill $PID
```

---

## Edge Cases

### 1. Subprocess Exits Before Detach

**Scenario:** Pattern matches, but subprocess exits before detach completes.

**Behavior:**
- Still return exit code 4
- Print PID (even though process is gone)
- User's responsibility to check if process is still running

### 2. Detach with Timeout

**Scenario:** `ee -D --timeout 60 'Ready' ./service.sh`

**Behavior:**
- If pattern matches within 60s → detach (exit code 4)
- If timeout occurs → kill subprocess (exit code 2)

### 3. Detach with Delay-Exit

**Scenario:** `ee -D -A 10 'Error' ./service.sh`

**Behavior:**
- Wait 10 seconds after match
- Then detach (don't kill)
- Exit code 4

### 4. Multiple Matches

**Scenario:** `ee -D -m 3 'Ready' ./service.sh`

**Behavior:**
- Wait for 3 matches
- Then detach
- Exit code 4

---

## Testing

### Test 1: Basic Detach

```bash
# Create test script
cat > test-service.sh <<'EOF'
#!/bin/bash
echo "Starting..."
sleep 1
echo "Ready!"
sleep 10
echo "Done"
EOF
chmod +x test-service.sh

# Test detach
ee -D 'Ready' ./test-service.sh
# Should exit immediately after "Ready!"
# Exit code: 4
# Script continues running for 10 more seconds

# Verify process still running
ps aux | grep test-service.sh
```

### Test 2: PID Capture

```bash
# Capture stderr
OUTPUT=$(ee -D 'Ready' ./test-service.sh 2>&1)
echo "$OUTPUT"
# Should contain: "Detached from subprocess (PID: XXXXX)"
```

### Test 3: Pipe Mode Rejection

```bash
# Should fail
echo "test" | ee -D 'test'
# Expected: Error message about command mode only
# Exit code: 3
```

### Test 4: No Pattern Rejection

```bash
# Should fail
ee -D ./test-service.sh
# Expected: Error message about pattern required
# Exit code: 3
```

---

## Documentation Updates

### 1. README.md

Add example:
```bash
# Start service, wait for ready, detach
ee -D 'Server listening' ./start-server.sh
# Exit code: 4 (detached)
# Service continues running
```

### 2. USER_GUIDE.md

Add section:
```markdown
### Detach Mode

Exit without killing subprocess when pattern matches:

```bash
# Start service and detach when ready
ee -D 'Ready' ./service.sh

# Capture PID for later cleanup
OUTPUT=$(ee -D 'Ready' ./service.sh 2>&1)
PID=$(echo "$OUTPUT" | grep "PID:" | awk '{print $NF}' | tr -d ')')
```

**Use cases:**
- Long-running services
- Background jobs
- Daemon processes
- CI/CD pipelines

**Exit code:** 4 (subprocess still running)
```

### 3. Exit Codes Documentation

Create `docs/EXIT_CODES.md`:
```markdown
# Exit Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 0 | Success | Pattern matched, subprocess terminated |
| 1 | No match | Pattern not found, subprocess completed |
| 2 | Timeout | Timeout exceeded, subprocess terminated |
| 3 | Error | Command not found or other error |
| 4 | Detached | Pattern matched, subprocess still running (--detach mode) |
| 130 | Interrupted | User pressed Ctrl+C |

## Exit Code 4: Detached Mode

When using `--detach` mode, earlyexit exits with code 4 after pattern match,
leaving the subprocess running in the background.

**Example:**
```bash
ee -D 'Ready' ./service.sh
echo $?  # Prints: 4

# Service still running
ps aux | grep service.sh
```

**PID Output:**
The subprocess PID is printed to stderr:
```
🔓 Detached from subprocess (PID: 12345)
   Subprocess continues running in background
   Use 'kill 12345' to stop it later
```
```

---

## Alternatives Considered

### Alternative 1: `--no-kill` flag

**Rejected:** Less clear than `--detach`. "No kill" is negative phrasing.

### Alternative 2: `--background` flag

**Rejected:** Confusing with shell `&` operator. Subprocess is already in background.

### Alternative 3: `--leave-running` flag

**Rejected:** Too verbose. `--detach` is clearer and shorter.

### Alternative 4: Return PID via stdout

**Rejected:** Pollutes stdout. stderr is better for meta-information.

### Alternative 5: Write PID to file

**Considered:** Could add `--pid-file` option in future if needed.

---

## Future Enhancements

### 1. PID File Option

```bash
ee -D --pid-file /tmp/service.pid 'Ready' ./service.sh
# Writes PID to /tmp/service.pid
```

### 2. Detach on Timeout

```bash
ee -D --detach-on-timeout 'Ready' ./service.sh
# If timeout, detach instead of killing
```

### 3. Process Group Detach

```bash
ee -D --detach-group 'Ready' ./service.sh
# Detach entire process group, not just main process
```

---

## Summary

**Feature:** `--detach` / `-D` flag

**Behavior:**
- Exit without killing subprocess when pattern matches
- Print PID to stderr
- Return exit code 4

**Use cases:**
- Starting services
- Background jobs
- CI/CD pipelines

**Implementation:**
- Add flag
- Modify termination logic
- Update exit codes
- Add validation
- Document thoroughly

**Estimated time:** 2-3 hours (implementation + testing + documentation)





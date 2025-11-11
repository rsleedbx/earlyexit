# Timeout Features in earlyexit

Complete guide to timeout monitoring and hang detection.

## Overview

`earlyexit` provides three types of timeout mechanisms for comprehensive process monitoring:

1. **Overall Timeout** (`-t`) - Maximum total execution time
2. **Idle Timeout** (`--idle-timeout`) - Detects hung/frozen processes
3. **First Output Timeout** (`--first-output-timeout`) - Detects startup failures

All timeouts return exit code **2** when triggered.

## Timeout Types

### 1. Overall Timeout (-t, --timeout)

Maximum time the command is allowed to run.

**Syntax:**
```bash
earlyexit -t SECONDS 'pattern' command
```

**Use Cases:**
- Prevent runaway processes
- Enforce time limits in CI/CD
- Kill long-running jobs

**Example:**
```bash
# Timeout after 60 seconds total
earlyexit -t 60 'Error' terraform apply

# 5 minute maximum for tests
earlyexit -t 300 'FAILED' pytest -v
```

### 2. Idle Timeout (--idle-timeout)

Timeout if **no output** is produced for N seconds. Detects hung/frozen processes.

**Syntax:**
```bash
earlyexit --idle-timeout SECONDS 'pattern' command
```

**How It Works:**
- Timer resets every time ANY output is received
- Triggers if gap between outputs exceeds N seconds
- Useful for detecting frozen applications

**Use Cases:**
- Detect hung applications
- Monitor long-running processes
- Ensure continuous progress
- Watch for deadlocks

**Examples:**
```bash
# Timeout if no output for 30 seconds
earlyexit --idle-timeout 30 'Error' ./long-running-app

# Detect frozen database migration
earlyexit --idle-timeout 60 'Error' ./db-migrate

# Monitor build that should be outputting progress
earlyexit --idle-timeout 45 'error' make -j8

# Watch for frozen downloads
earlyexit --idle-timeout 30 'failed' wget https://example.com/large-file
```

**Real-World Example:**
```bash
# Application hangs after 5 minutes
./app &  # Hangs at 5min mark, no more output

# Without idle timeout - waits forever
earlyexit 'Error' ./app

# With idle timeout - detects hang
earlyexit --idle-timeout 30 'Error' ./app
# Returns exit code 2 after 30s of silence
```

### 3. First Output Timeout (--first-output-timeout)

Timeout if **first output** doesn't appear within N seconds. Detects startup failures.

**Syntax:**
```bash
earlyexit --first-output-timeout SECONDS 'pattern' command
```

**How It Works:**
- Timer starts when command begins
- Triggers if NO output received before N seconds
- Once first output seen, timer stops
- Independent of idle timeout

**Use Cases:**
- Detect startup failures
- Catch initialization hangs
- Monitor slow-starting services
- Verify quick startup

**Examples:**
```bash
# Application must start outputting within 10 seconds
earlyexit --first-output-timeout 10 'Error' ./app

# Service must respond within 5 seconds
earlyexit --first-output-timeout 5 'Error' ./start-service.sh

# Database must begin connecting within 15 seconds
earlyexit --first-output-timeout 15 'Error' ./db-connect

# Container must start logging within 30 seconds
earlyexit --first-output-timeout 30 'Error' docker run myapp
```

**Real-World Example:**
```bash
# Slow startup detection
earlyexit --first-output-timeout 10 'Error' java -jar app.jar
# If JVM doesn't output anything in 10s, exit code 2

# Compare with idle timeout
earlyexit --idle-timeout 10 'Error' java -jar app.jar
# Allows slow startup, but detects if it hangs mid-process
```

## Combining Timeouts

You can use multiple timeouts together for comprehensive monitoring:

```bash
earlyexit \
  -t 300 \
  --idle-timeout 30 \
  --first-output-timeout 10 \
  'Error' ./app
```

**Behavior:**
- **Overall:** 300s maximum total time
- **Idle:** 30s maximum gap between outputs
- **First:** 10s maximum to see first output

**Which Triggers First:**
- Whichever condition is met first will trigger
- All use same exit code (2)
- Error message indicates which timeout triggered

## Timeout Behavior Matrix

| Scenario | Overall | Idle | First | Result |
|----------|---------|------|-------|--------|
| Quick start, continuous output | ❌ | ❌ | ❌ | Success |
| Slow start (15s), then output | ❌ | ❌ | ✅ (10s) | Timeout |
| Quick start, then hangs | ❌ | ✅ (30s) | ❌ | Timeout |
| Never outputs anything | ✅ or First | ❌ | ✅ | Timeout |
| Runs for 400s continuously | ✅ (300s) | ❌ | ❌ | Timeout |

## Use Case Examples

### Example 1: Database Migration

Monitor long-running migration with hang detection:

```bash
earlyexit \
  -t 3600 \
  --idle-timeout 120 \
  --first-output-timeout 30 \
  'Error|Failed' \
  ./db-migrate.sh
```

- Overall: 1 hour max
- Idle: Detect if migration hangs for 2 minutes
- First: Must start within 30 seconds

### Example 2: Service Startup

Ensure service starts quickly and stays responsive:

```bash
earlyexit \
  --first-output-timeout 10 \
  --idle-timeout 5 \
  'Error|Fatal' \
  ./start-api-server.sh
```

- Must output something within 10s (startup check)
- Must output at least every 5s (heartbeat check)

### Example 3: Build System

Monitor build with progress indicators:

```bash
earlyexit \
  -t 1800 \
  --idle-timeout 60 \
  'error:|failed' \
  make -j8
```

- Overall: 30 minute max build time
- Idle: Detect if build freezes for 1 minute

### Example 4: Long Download

Monitor download progress:

```bash
earlyexit \
  --idle-timeout 30 \
  --first-output-timeout 10 \
  'Error|Failed' \
  wget https://example.com/large-file
```

- Must start downloading within 10s
- Must show progress at least every 30s

### Example 5: Test Suite

Comprehensive test monitoring:

```bash
earlyexit \
  -t 600 \
  --idle-timeout 45 \
  --first-output-timeout 15 \
  'FAILED|ERROR' \
  pytest -v --log-cli-level=INFO
```

- Overall: 10 minute max
- Idle: Tests must progress every 45s
- First: First test must start within 15s

### Example 6: Kubernetes Deployment

Monitor deployment with startup and progress checks:

```bash
earlyexit \
  -t 300 \
  --idle-timeout 30 \
  --first-output-timeout 10 \
  'Error|Failed|CrashLoop' \
  kubectl rollout status deployment/myapp
```

### Example 7: CI/CD Pipeline Stage

```bash
earlyexit \
  -t 900 \
  --idle-timeout 60 \
  'error:|failed' \
  ./run-integration-tests.sh
```

## Exit Codes and Detection

All timeout types return exit code **2**:

```bash
earlyexit --idle-timeout 10 'Error' ./app
case $? in
  0) echo "Error pattern matched!" ;;
  1) echo "Completed successfully" ;;
  2) echo "Timeout occurred" ;;
  *) echo "Other error" ;;
esac
```

**Timeout Messages:**

```bash
# Overall timeout
⏱️  Timeout: timeout

# Idle timeout
⏱️  Timeout: no output for 30.0s

# First output timeout
⏱️  Timeout: no first output after 10.0s
```

## Best Practices

### 1. Choose Appropriate Timeouts

```bash
# Too aggressive - may cause false positives
earlyexit --idle-timeout 5 'Error' ./slow-app

# Better - allows for normal pauses
earlyexit --idle-timeout 30 'Error' ./slow-app
```

### 2. Use First-Output for Startup, Idle for Progress

```bash
# Good combination
earlyexit \
  --first-output-timeout 10 \
  --idle-timeout 60 \
  'Error' ./app
```

### 3. Set Overall Timeout as Safety Net

```bash
# Always have a maximum time limit
earlyexit -t 3600 --idle-timeout 120 'Error' ./app
```

### 4. Monitor Logs for Tuning

```bash
# Add logging to understand timing
earlyexit --idle-timeout 30 'Error' ./app 2>&1 | tee app.log
# Review log to see typical output intervals
```

### 5. Different Timeouts for Different Environments

```bash
# Development - lenient
earlyexit --idle-timeout 60 'Error' ./app

# Production - strict
earlyexit --idle-timeout 30 'Error' ./app

# CI - very strict
earlyexit --idle-timeout 15 --first-output-timeout 5 'Error' ./app
```

## Troubleshooting

### Timeout Triggering Too Often

**Problem:** Idle timeout triggering on normal pauses

**Solution:**
```bash
# Increase timeout value
earlyexit --idle-timeout 60 'Error' ./app  # Instead of 30

# Or remove if not needed
earlyexit -t 300 'Error' ./app  # Only overall timeout
```

### First Output Never Seen

**Problem:** Application outputs to different FD or no output

**Solution:**
```bash
# Check which FD app uses
earlyexit --both --fd-prefix --first-output-timeout 10 'Error' ./app

# Or monitor specific FD
earlyexit --fd 3 --first-output-timeout 10 'Error' ./app
```

### Unclear Which Timeout Triggered

**Problem:** Need to know specific timeout reason

**Solution:**
Look at the error message:
- `"timeout"` - Overall timeout (-t)
- `"no output for Ns"` - Idle timeout
- `"no first output after Ns"` - First output timeout

## Advanced Patterns

### Conditional Timeout Based on Stage

```bash
# Strict timeout during startup, lenient after
earlyexit --first-output-timeout 5 --idle-timeout 120 'Error' ./app
```

### Per-Stream Monitoring

```bash
# Different monitoring for different streams
earlyexit \
  --both \
  --fd 3 \
  --idle-timeout 30 \
  --first-output-timeout 10 \
  --fd-pattern 2 'ERROR' \
  --fd-pattern 3 'DEBUG.*Critical' \
  'INFO' ./app
```

### Cascade Timeouts

```bash
# Start strict, get lenient
{
  earlyexit --first-output-timeout 10 'Error' ./app &
  PID=$!
  sleep 10
  # If still running after 10s, switch to idle timeout
  wait $PID || earlyexit --idle-timeout 60 'Error' ./app
}
```

## Comparison with timeout Command

| Feature | `timeout` | `earlyexit` |
|---------|-----------|-------------|
| Overall timeout | ✅ | ✅ `-t` |
| Idle/hang detection | ❌ | ✅ `--idle-timeout` |
| Startup detection | ❌ | ✅ `--first-output-timeout` |
| Pattern matching | ❌ | ✅ |
| Multiple timeout types | ❌ | ✅ |
| Detailed timeout reasons | ❌ | ✅ |

## Performance Impact

- **Overall timeout:** Negligible (single timer)
- **Idle timeout:** ~0.1% CPU (checks every 100ms)
- **First output timeout:** ~0.1% CPU (checks every 100ms)
- **Memory:** ~8KB per monitored stream

## Version History

- **0.0.1**: Initial implementation
  - Overall timeout (`-t`)
  - Idle timeout (`--idle-timeout`)
  - First output timeout (`--first-output-timeout`)

## See Also

- [README.md](README.md) - Main documentation
- [FD_MONITORING.md](FD_MONITORING.md) - File descriptor monitoring
- [REGEX_REFERENCE.md](REGEX_REFERENCE.md) - Pattern matching guide


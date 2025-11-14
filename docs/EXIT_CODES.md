# Exit Codes

`earlyexit` uses different exit codes to indicate why it terminated. This allows scripts and CI/CD pipelines to handle different scenarios appropriately.

---

## Exit Code Reference

| Code | Meaning | Description | Subprocess State |
|------|---------|-------------|------------------|
| **0** | Success | Pattern matched | Terminated |
| **1** | No match | Pattern not found | Completed normally |
| **2** | Timeout | Timeout exceeded | Terminated |
| **3** | Error | Command not found or other error | N/A or terminated |
| **4** | Detached | Pattern matched, subprocess detached | **Still running** |
| **130** | Interrupted | User pressed Ctrl+C | Terminated |

---

## Exit Code 0: Pattern Matched

**Meaning:** The pattern was found in the output, and `earlyexit` terminated the subprocess.

**Use case:** Detecting errors or specific conditions.

**Example:**
```bash
ee 'ERROR' ./deploy.sh
echo $?  # Prints: 0 (error was detected)

# In scripts
if ee 'ERROR' ./deploy.sh; then
    echo "❌ Deployment failed - error detected"
    exit 1
fi
```

**Subprocess state:** Terminated (killed by `earlyexit`)

---

## Exit Code 1: No Match Found

**Meaning:** The pattern was NOT found in the output, and the subprocess completed normally.

**Use case:** Verifying that no errors occurred.

**Example:**
```bash
ee 'ERROR' ./deploy.sh
echo $?  # Prints: 1 (no errors detected)

# In scripts
if ! ee 'ERROR' ./deploy.sh; then
    echo "✅ Deployment successful - no errors"
fi
```

**Subprocess state:** Completed normally

---

## Exit Code 2: Timeout Exceeded

**Meaning:** The specified timeout was exceeded before the pattern was found.

**Use case:** Detecting hung or slow processes.

**Example:**
```bash
ee -t 60 'Ready' ./slow-service.sh
echo $?  # Prints: 2 (timeout after 60 seconds)

# In scripts
ee -t 60 'Ready' ./service.sh
if [ $? -eq 2 ]; then
    echo "❌ Service failed to start within 60 seconds"
    exit 1
fi
```

**Subprocess state:** Terminated (killed by `earlyexit`)

**Timeout types:**
- `-t` / `--timeout`: Overall timeout
- `-I` / `--idle-timeout`: Stall detection (no output for N seconds)
- `-F` / `--first-output-timeout`: Startup detection (no first output within N seconds)

---

## Exit Code 3: Error

**Meaning:** An error occurred, such as command not found or invalid arguments.

**Use case:** Detecting configuration or setup issues.

**Example:**
```bash
ee 'ERROR' /nonexistent/command
echo $?  # Prints: 3 (command not found)

# Invalid usage
echo "test" | ee -D 'test'
echo $?  # Prints: 3 (--detach requires command mode)
```

**Subprocess state:** N/A (never started) or terminated

**Common causes:**
- Command not found
- Invalid arguments
- `--detach` used in pipe mode
- `--detach` used without pattern

---

## Exit Code 4: Detached (New!)

**Meaning:** The pattern was found, and `earlyexit` exited WITHOUT killing the subprocess. The subprocess continues running in the background.

**Use case:** Starting long-running services or daemons.

**Example:**
```bash
# Start service, wait for ready, detach
ee -D 'Server listening on port 8080' ./start-server.sh
echo $?  # Prints: 4 (detached)

# Service still running
ps aux | grep start-server.sh
# 12345 ... ./start-server.sh

# Later, stop it
kill 12345
```

**Subprocess state:** **Still running in background**

**Output:**
```
Server starting...
Server listening on port 8080
🔓 Detached from subprocess (PID: 12345)
   Subprocess continues running in background
   Use 'kill 12345' to stop it later
```

### When to Use `--detach`

1. **Starting services for testing:**
   ```bash
   ee -D 'Ready' ./start-service.sh
   SERVICE_EXIT=$?
   
   if [ $SERVICE_EXIT -eq 4 ]; then
       # Service started successfully
       npm test
       # Cleanup
       kill $(pgrep -f start-service.sh)
   fi
   ```

2. **Background jobs:**
   ```bash
   ee -D 'Job started' ./long-job.sh
   echo "Job is running in background"
   ```

3. **Daemon processes:**
   ```bash
   ee -D 'Daemon initialized' ./start-daemon.sh
   ```

4. **CI/CD pipelines:**
   ```bash
   #!/bin/bash
   # Start database for tests
   ee -D 'database system is ready' postgres -D /data
   
   if [ $? -eq 4 ]; then
       # Run tests
       pytest
       TEST_EXIT=$?
       
       # Cleanup
       pkill postgres
       
       exit $TEST_EXIT
   else
       echo "❌ Database failed to start"
       exit 1
   fi
   ```

### Capturing the PID

**Method 1: Use PID file (recommended)**
```bash
ee -D --pid-file /tmp/service.pid 'Ready' ./service.sh
PID=$(cat /tmp/service.pid)
echo "Service PID: $PID"

# Cleanup
kill $PID
```

**Method 2: Parse stderr**
```bash
OUTPUT=$(ee -D 'Ready' ./service.sh 2>&1)
PID=$(echo "$OUTPUT" | grep "PID:" | awk '{print $NF}' | tr -d ')')
echo "Service PID: $PID"
```

**Method 3: Use process name**
```bash
ee -D 'Ready' ./service.sh
PID=$(pgrep -f service.sh)
echo "Service PID: $PID"
```

### Advanced Detach Options

#### 1. `--pid-file`: Write PID to File

Automatically write the subprocess PID to a file for easy cleanup:

```bash
# Write PID to file
ee -D --pid-file /tmp/service.pid 'Ready' ./service.sh

# Later, cleanup using PID file
kill $(cat /tmp/service.pid)
rm /tmp/service.pid
```

**Use case:** CI/CD scripts that need reliable cleanup

#### 2. `--detach-on-timeout`: Detach Instead of Kill on Timeout

Normally, timeouts kill the subprocess. With `--detach-on-timeout`, the subprocess continues running:

```bash
# If pattern not found within 60s, detach anyway
ee -D --detach-on-timeout -t 60 'Ready' ./slow-service.sh
echo $?  # Prints: 4 (detached on timeout)

# Service still running even though it timed out
ps aux | grep slow-service.sh
```

**Exit code:** 4 (not 2!) when detached on timeout

**Use case:** Services that take unpredictable time to start

**Example:**
```bash
#!/bin/bash
# Start service with timeout safety
ee -D --detach-on-timeout -t 60 --pid-file /tmp/service.pid 'Ready' ./service.sh
EXIT_CODE=$?

if [ $EXIT_CODE -eq 4 ]; then
    echo "✅ Service started (or timed out but still running)"
    # Run tests
    npm test
    # Cleanup
    kill $(cat /tmp/service.pid)
else
    echo "❌ Service failed to start"
    exit 1
fi
```

#### 3. `--detach-group`: Detach Entire Process Group

For commands that spawn child processes, detach the entire process group:

```bash
# Detach process group (useful for shell scripts that spawn children)
ee -D --detach-group 'Ready' ./start-cluster.sh

# Output:
# 🔓 Detached from process group (PGID: 12345, PID: 12346)
#    Subprocess continues running in background
#    Use 'kill -- -12345' to stop process group

# Later, kill entire process group
kill -- -12345
```

**Use case:** 
- Shell scripts that spawn multiple processes
- Docker compose
- Process managers
- Cluster startup scripts

**Example:**
```bash
#!/bin/bash
# Start multi-process service
ee -D --detach-group --pid-file /tmp/cluster.pid 'Cluster ready' ./start-cluster.sh

# Run tests
pytest

# Cleanup entire process group
PGID=$(ps -o pgid= -p $(cat /tmp/cluster.pid) | tr -d ' ')
kill -- -$PGID
```

#### 4. Combining All Options

```bash
# Ultimate detach: PID file + timeout safety + process group
ee -D --detach-group --detach-on-timeout --pid-file /tmp/service.pid \
   -t 120 'Ready' ./complex-service.sh

# Service starts, writes PID, detaches on ready or timeout
# Entire process group continues running
# PID file available for cleanup
```

### Detach vs Normal Mode

| Mode | Flag | Exit Code | Subprocess State | Use Case |
|------|------|-----------|------------------|----------|
| Normal | (none) | 0 | Terminated | Detect errors, stop on failure |
| Detach | `-D` | 4 | **Still running** | Start services, background jobs |

---

## Exit Code 130: Interrupted

**Meaning:** User pressed Ctrl+C (SIGINT).

**Use case:** Manual interruption.

**Example:**
```bash
ee 'ERROR' ./long-running-app.sh
# User presses Ctrl+C
echo $?  # Prints: 130
```

**Subprocess state:** Terminated (killed by signal)

**Note:** Exit code 130 is standard for SIGINT (128 + 2).

---

## Using Exit Codes in Scripts

### Example 1: Error Detection

```bash
#!/bin/bash
ee 'ERROR|FAIL' terraform apply

case $? in
    0)
        echo "❌ Terraform apply failed - error detected"
        exit 1
        ;;
    1)
        echo "✅ Terraform apply successful - no errors"
        exit 0
        ;;
    2)
        echo "⏱️  Terraform apply timed out"
        exit 1
        ;;
    3)
        echo "❌ Terraform command not found or invalid arguments"
        exit 1
        ;;
    130)
        echo "🛑 Interrupted by user"
        exit 130
        ;;
esac
```

### Example 2: Service Startup

```bash
#!/bin/bash
# Start service and wait for ready
ee -D -t 60 'Server listening' ./start-server.sh
EXIT_CODE=$?

case $EXIT_CODE in
    4)
        echo "✅ Server started successfully (PID: $(pgrep -f start-server.sh))"
        # Run tests
        npm test
        TEST_EXIT=$?
        
        # Cleanup
        pkill -f start-server.sh
        
        exit $TEST_EXIT
        ;;
    2)
        echo "❌ Server failed to start within 60 seconds"
        exit 1
        ;;
    3)
        echo "❌ Server command not found"
        exit 1
        ;;
    *)
        echo "❌ Unexpected exit code: $EXIT_CODE"
        exit 1
        ;;
esac
```

### Example 3: Timeout Handling

```bash
#!/bin/bash
# Monitor with multiple timeouts
ee -t 300 -I 30 -F 10 'ERROR' ./app.sh
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "❌ Error detected in app"
    exit 1
elif [ $EXIT_CODE -eq 2 ]; then
    echo "⏱️  App timed out"
    # Check which timeout was hit by examining stderr
    exit 1
else
    echo "✅ App completed successfully"
    exit 0
fi
```

---

## Comparison with Other Tools

### `grep`

| Tool | Match Found | No Match | Error |
|------|-------------|----------|-------|
| `grep` | 0 | 1 | 2 |
| `earlyexit` | 0 | 1 | 3 |

**Difference:** `earlyexit` uses exit code 2 for timeout, 3 for errors.

### `timeout`

| Tool | Success | Timeout | Error |
|------|---------|---------|-------|
| `timeout` | (command exit code) | 124 | 125-127 |
| `earlyexit` | 0 or 1 | 2 | 3 |

**Difference:** `earlyexit` uses exit code 2 for timeout (not 124).

### `earlyexit` Unique Codes

| Code | Unique to `earlyexit`? | Meaning |
|------|------------------------|---------|
| 0 | No (like `grep`) | Match found |
| 1 | No (like `grep`) | No match |
| 2 | **Yes** (timeout uses 124) | Timeout |
| 3 | No (like `grep`) | Error |
| **4** | **Yes** (unique feature) | **Detached** |
| 130 | No (standard SIGINT) | Interrupted |

---

## Summary

**Key points:**
- **0 = Error detected** (pattern matched, subprocess killed)
- **1 = No error** (pattern not found, subprocess completed)
- **2 = Timeout** (subprocess killed)
- **3 = Configuration error** (command not found, invalid args)
- **4 = Detached** (subprocess still running!) ⭐ **New!**
- **130 = Interrupted** (Ctrl+C)

**Remember:**
- Exit code **0** means "error detected" (opposite of typical Unix convention)
- Exit code **4** means subprocess is **still running** (use `--detach` mode)
- Use `case` statements to handle all exit codes properly

**See also:**
- [User Guide](USER_GUIDE.md) - Comprehensive usage examples
- [README](../README.md) - Quick start and features
- [Detach Mode Design](../DETACH_MODE_DESIGN.md) - Technical details


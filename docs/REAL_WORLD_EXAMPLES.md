# Real-World Examples: Where `ee` Excels Over `grep`

## Introduction

This document shows practical examples where `earlyexit` (`ee`) solves problems that are difficult, impossible, or extremely complex with traditional `grep` alone.

---

## Problem 0: The Silent `timeout N command 2>&1` Problem

### ❌ The Problem (timeout)

You run a command with timeout and see **NO OUTPUT** for the entire duration:

```bash
# User runs this:
timeout 90 mist dml monitor --id rble-3087789530 --session rb_le-691708f8 --interval 15 2>&1

# What user sees:
# ... (blank screen for 90 seconds) ...
# 
# Then after 90 seconds, ALL output appears at once!
```

**Why this happens:**

1. When not connected to a TTY, programs switch to **block buffering** (4KB blocks)
2. Output is held in memory until:
   - 4KB buffer fills up, OR
   - Command completes/times out, OR
   - Program explicitly flushes
3. User sees **nothing** during execution
4. All output dumps at the end (too late!)

**Problems:**
- ❌ Can't see progress or errors in real-time
- ❌ User thinks command is hung
- ❌ Wastes time waiting for timeout
- ❌ Can't detect success/failure early
- ❌ No pattern matching
- ❌ Bad user experience

### ✅ The Solution (ee)

```bash
# Real-time output + pattern matching + early exit
ee -t 90 'ERROR|success|completed|failed' -- \
  mist dml monitor --id rble-3087789530 --session rb_le-691708f8 --interval 15

# Exit codes tell you what happened:
# 0 = Pattern matched (success or error detected)
# 1 = No match (if using grep convention)
# 2 = Timeout (command still running after 90 seconds)
```

**Why ee wins:**
- ✅ **Real-time output**: Automatic unbuffering
- ✅ **Early exit**: Stop on pattern match (don't waste 90 seconds)
- ✅ **Pattern matching**: Detect success OR error
- ✅ **Clear exit codes**: Know exactly what happened
- ✅ **No shell scripting**: One simple command

**Real-world impact:**
```bash
# Before (timeout): Wait 90 seconds, see nothing, output dumps at end
timeout 90 mist dml monitor 2>&1
# Time wasted: 90 seconds

# After (ee): See output immediately, exit on first error/success
ee -t 90 'ERROR|completed' -- mist dml monitor
# Time saved: Up to 90 seconds (exits early!)
```

---

## Problem 1: False Positives in Error Logs

### ❌ The Problem (grep)

Terraform and many tools print benign "Error:" strings in normal output:

```bash
# This catches both real errors AND false positives
grep 'Error' terraform.log

# Output includes:
# Error: early error detection is enabled    ← False positive (it's a feature)
# Error: Resource already exists             ← Real error
# Error: Invalid configuration                ← Real error
```

**Workarounds are messy:**
```bash
# Option 1: Negative lookhead (hard to read, easy to break)
grep 'Error' terraform.log | grep -v 'early error detection'

# Option 2: Multiple pipes (slow, brittle)
grep 'Error' terraform.log | grep -v 'detection' | grep -v 'Expected'

# Option 3: Complex regex (unreadable, unmaintainable)
grep 'Error:(?!.*(early error detection|Expected))' terraform.log  # Doesn't work in basic grep!
```

### ✅ The Solution (ee)

```bash
# Clean, readable, maintainable
ee 'Error' \
  --test-pattern \
  --exclude 'early error detection' \
  --exclude 'Expected error in test' \
  < terraform.log

# Then use in production:
ee 'Error' \
  --exclude 'early error detection' \
  --exclude 'Expected error' \
  -- terraform apply
```

**Why ee wins:**
- ✅ Clear intent: "match Error, except these"
- ✅ Multiple exclusions are easy
- ✅ Test mode validates before production
- ✅ Works with timeouts and all other features

---

## Problem 2: Monitoring for Success OR Failure

### ❌ The Problem (grep)

You want to exit early on either **success** OR **error** (whichever comes first):

```bash
# Terraform apply might take 30 minutes
# But it shows "Apply complete!" after 5 minutes
# Or "Error" if it fails early

# grep can only watch for ONE pattern
grep 'Error' terraform-output.log  # Misses success, waits 30 minutes

# You need TWO separate greps (race condition!)
(terraform apply 2>&1 | tee log.txt) &
PID=$!

# Watch for error in background
(tail -f log.txt | grep -q 'Error' && kill $PID) &
# Watch for success in background  
(tail -f log.txt | grep -q 'Apply complete' && kill $PID) &

wait $PID
# Now figure out which pattern matched? How? 🤷
```

**Problems:**
- ❌ Complex shell scripting
- ❌ Race conditions
- ❌ Can't tell which pattern matched
- ❌ Hard to maintain
- ❌ Signal handling issues

### ✅ The Solution (ee)

```bash
# Simple, clear, reliable
ee -t 1800 \
  --success-pattern 'Apply complete!' \
  --error-pattern 'Error|Failed' \
  -- terraform apply

# Exit codes tell you what happened:
# 0 = Success pattern matched (deploy succeeded)
# 1 = Error pattern matched (deploy failed)
# 2 = Timeout (still running after 30 min)
```

**Why ee wins:**
- ✅ First match wins (no race condition)
- ✅ Clear exit codes
- ✅ One simple command
- ✅ Built-in timeout handling
- ✅ Captures both stdout and stderr

---

## Problem 3: Stall/Hang Detection

### ❌ The Problem (grep)

Your database migration hangs - produces no output for 5 minutes:

```bash
# grep can't detect "no output"
./run-migrations.sh | grep 'ERROR'

# Workarounds require complex shell scripts:
./run-migrations.sh > output.log 2>&1 &
PID=$!

LAST_SIZE=0
while kill -0 $PID 2>/dev/null; do
    CURRENT_SIZE=$(stat -f%z output.log 2>/dev/null || stat -c%s output.log)
    if [ "$CURRENT_SIZE" -eq "$LAST_SIZE" ]; then
        IDLE_COUNT=$((IDLE_COUNT + 1))
        if [ "$IDLE_COUNT" -ge 60 ]; then  # 5 minutes
            kill $PID
            echo "Hung!"
            exit 1
        fi
    else
        IDLE_COUNT=0
    fi
    LAST_SIZE=$CURRENT_SIZE
    sleep 5
done
```

**Problems:**
- ❌ 20+ lines of complex shell code
- ❌ Platform-specific (`stat` differs on Linux/Mac)
- ❌ Race conditions
- ❌ Signal handling issues
- ❌ Hard to test

### ✅ The Solution (ee)

```bash
# Simple, cross-platform, reliable
ee -t 1800 -I 300 'ERROR' -- ./run-migrations.sh

# -t 1800: Overall timeout (30 minutes)
# -I 300:  Idle timeout (5 minutes no output = hung)
```

**Why ee wins:**
- ✅ One line
- ✅ Cross-platform
- ✅ Tested and reliable
- ✅ No shell scripting needed
- ✅ Combines timeout + pattern matching

---

## Problem 4: Testing Patterns Before Production

### ❌ The Problem (grep)

You have a 10GB log file. You need to find the right pattern:

```bash
# Try pattern 1
grep 'error' huge-log.txt  # Wait 2 minutes... 10,000 matches (too many!)

# Try pattern 2
grep 'ERROR' huge-log.txt  # Wait 2 minutes... 5,000 matches (still too many!)

# Try with exclusion
grep 'ERROR' huge-log.txt | grep -v 'OK'  # Wait 4 minutes... 100 matches

# Oops, need to adjust, run again
grep 'ERROR' huge-log.txt | grep -v 'OK' | grep -v 'Expected'  # Wait 6 minutes...

# After 30 minutes of iteration, you HOPE you got it right
```

**Problems:**
- ❌ Slow iteration (must scan entire file each time)
- ❌ No statistics (how many lines, how many matched, how many excluded?)
- ❌ Can't see line numbers easily
- ❌ No validation before using in production

### ✅ The Solution (ee)

```bash
# Fast iteration with immediate feedback
cat huge-log.txt | ee 'ERROR' --test-pattern

# Output:
# 📊 Statistics:
#    Total lines:     10,523,847
#    Matched lines:   5,234
# ✅ Pattern matched 5,234 times

# Add exclusion
cat huge-log.txt | ee 'ERROR' \
  --test-pattern \
  --exclude 'ERROR_OK'

# Output:
# 📊 Statistics:
#    Total lines:     10,523,847
#    Matched lines:   234
#    Excluded lines:  5,000
# ✅ Pattern matched 234 times

# Shows first 20 matches with line numbers:
# Line  42:  ERROR: Connection failed
# Line 156:  ERROR: Timeout occurred
# ...
```

**Why ee wins:**
- ✅ Statistics show exact counts
- ✅ Line numbers for easy reference
- ✅ See exclusion impact immediately
- ✅ Test dual-patterns before production
- ✅ Validate before deploying

---

## Problem 5: CI/CD Pipeline Monitoring

### ❌ The Problem (grep)

Docker build in CI/CD - need to detect success or failure, with timeout:

```bash
#!/bin/bash
# Complex CI/CD script

timeout 1200 docker build -t myapp . 2>&1 | tee build.log &
BUILD_PID=$!

# Monitor in background
(tail -f build.log | grep -q 'Successfully built' && kill $BUILD_PID) &
GREP_SUCCESS=$!
(tail -f build.log | grep -q 'ERROR' && kill $BUILD_PID) &
GREP_ERROR=$!

wait $BUILD_PID
EXIT_CODE=$?

# Figure out what happened...
if [ $EXIT_CODE -eq 124 ]; then
    echo "Build timed out"
    exit 1
elif grep -q 'ERROR' build.log; then
    echo "Build failed"  
    exit 1
elif grep -q 'Successfully built' build.log; then
    echo "Build succeeded"
    exit 0
else
    echo "Unknown status"
    exit 1
fi

# Cleanup background processes
kill $GREP_SUCCESS $GREP_ERROR 2>/dev/null
```

**Problems:**
- ❌ 30+ lines of error-prone shell
- ❌ Background job management
- ❌ Signal handling complexity
- ❌ Race conditions
- ❌ Hard to debug failures

### ✅ The Solution (ee)

```bash
#!/bin/bash
# Simple, reliable CI/CD script

ee --unix-exit-codes -t 1200 \
  --success-pattern 'Successfully built|Successfully tagged' \
  --error-pattern 'ERROR|failed' \
  -- docker build -t myapp .

EXIT_CODE=$?

case $EXIT_CODE in
    0) echo "✅ Build succeeded"; exit 0 ;;
    1) echo "❌ Build failed"; exit 1 ;;
    2) echo "⏱️  Build timed out"; exit 1 ;;
    *) echo "❓ Unknown status"; exit 1 ;;
esac
```

**Why ee wins:**
- ✅ 12 lines vs 30+ lines
- ✅ No background jobs
- ✅ No race conditions
- ✅ Clear exit codes
- ✅ Easy to debug
- ✅ Maintainable

---

## Problem 6: Multi-Pattern with Context

### ❌ The Problem (grep)

Find errors but also capture context (lines before/after):

```bash
# Need context around errors
grep -B 3 -A 3 'ERROR' app.log

# But this also matches false positives!
# So you need:
grep -B 3 -A 3 'ERROR' app.log | grep -v 'ERROR_OK'

# But now you've lost the context! grep -v removes those lines
# You need complex awk/sed scripting:
awk '/ERROR_OK/{next} /ERROR/{for(i=NR-3;i<=NR+3;i++)print lines[i%4]} {lines[NR%4]=$0}' app.log
```

**Problems:**
- ❌ Context lost with grep -v
- ❌ Requires awk/sed expertise
- ❌ Difficult to maintain
- ❌ No timeout support

### ✅ The Solution (ee)

```bash
# Exclusions don't affect context capture
ee 'ERROR' \
  -C 3 \
  --exclude 'ERROR_OK' \
  -- ./run-app.sh

# Or test first:
cat app.log | ee 'ERROR' \
  --test-pattern \
  --exclude 'ERROR_OK'

# Shows matches with line numbers,
# Then use with -C 3 in production
```

**Why ee wins:**
- ✅ Exclusions work with context
- ✅ No awk/sed needed
- ✅ Test mode validates patterns
- ✅ Works with timeouts

---

## Problem 7: Kubernetes Deployment Monitoring

### ❌ The Problem (grep)

Wait for Kubernetes deployment to be ready or fail:

```bash
# Watch kubectl output for ready state
kubectl rollout status deployment/myapp 2>&1 | grep 'successfully rolled out'

# But what if it fails? You wait forever!
# Need parallel monitoring:
kubectl rollout status deployment/myapp 2>&1 | tee deploy.log &
KUBECTL_PID=$!

(tail -f deploy.log | grep -q 'successfully rolled out' && kill $KUBECTL_PID) &
(tail -f deploy.log | grep -q 'Error\|Failed' && kill $KUBECTL_PID) &

sleep 600 && kill $KUBECTL_PID  # Manual timeout

wait $KUBECTL_PID

# Parse deploy.log to figure out what happened
if grep -q 'successfully rolled out' deploy.log; then
    echo "Success"
elif grep -q 'Error\|Failed' deploy.log; then
    echo "Failed"
else
    echo "Timed out"
fi
```

**Problems:**
- ❌ Complex background job management
- ❌ Manual timeout implementation
- ❌ Race conditions
- ❌ Signal handling
- ❌ Hard to maintain

### ✅ The Solution (ee)

```bash
ee --unix-exit-codes -t 600 \
  --success-pattern 'successfully rolled out' \
  --error-pattern 'Error|Failed|ImagePullBackOff' \
  -- kubectl rollout status deployment/myapp

# Clean exit codes:
# 0 = Deployed successfully
# 1 = Deployment failed
# 2 = Timeout (still not ready after 10 min)
```

**Why ee wins:**
- ✅ One simple command
- ✅ Built-in timeout
- ✅ Clear exit codes
- ✅ First match wins (no race)
- ✅ Easy to integrate in CI/CD

---

## Problem 8: Database Connection Retry Logic

### ❌ The Problem (grep)

Wait for database to be ready, with exponential backoff:

```bash
#!/bin/bash
MAX_ATTEMPTS=30
ATTEMPT=1

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    if pg_isready -h localhost | grep -q 'accepting connections'; then
        echo "Database ready"
        exit 0
    fi
    
    echo "Attempt $ATTEMPT: Database not ready, waiting..."
    SLEEP_TIME=$((2 ** ATTEMPT))
    sleep $SLEEP_TIME
    ATTEMPT=$((ATTEMPT + 1))
done

echo "Database failed to start"
exit 1
```

**Problems:**
- ❌ Custom retry logic
- ❌ No overall timeout
- ❌ Exponential backoff calculation
- ❌ Verbose error handling

### ✅ The Solution (ee)

```bash
# Simple: watch for "accepting connections" with timeout
ee -t 300 -I 10 'accepting connections' -- \
  bash -c 'while true; do pg_isready -h localhost; sleep 2; done'

# -t 300: Give up after 5 minutes total
# -I 10:  Consider it failed if no new output for 10 seconds
```

**Why ee wins:**
- ✅ No retry logic needed
- ✅ Built-in timeouts
- ✅ Simpler code
- ✅ Handles both overall and idle timeouts

---

## Problem 9: Log File Monitoring with Rotation

### ❌ The Problem (grep)

Monitor a log file that might rotate:

```bash
# This breaks when log rotates
tail -f app.log | grep 'ERROR'

# Need to handle rotation:
tail -F app.log | grep 'ERROR'  # -F follows by name

# But what about timeouts? Stalls? Multiple patterns?
# Gets complex fast...
```

**Problems:**
- ❌ Log rotation handling
- ❌ No timeout support
- ❌ No stall detection
- ❌ Single pattern only

### ✅ The Solution (ee)

```bash
# In pipe mode, ee handles everything
tail -F app.log | ee -t 3600 -I 300 \
  --success-pattern 'Deployment complete' \
  --error-pattern 'ERROR|FATAL' \
  --exclude 'ERROR_OK'

# Monitors for 1 hour, detects stalls (5 min idle),
# watches for success or error, filters false positives
```

**Why ee wins:**
- ✅ Works with tail -F naturally
- ✅ Timeout + idle detection
- ✅ Dual patterns
- ✅ Exclusions
- ✅ All in one command

---

## Problem 10: Jenkins/GitHub Actions Integration

### ❌ The Problem (grep)

GitHub Actions workflow monitoring:

```yaml
- name: Deploy
  run: |
    set +e  # Don't exit on error, we want to capture output
    
    ./deploy.sh 2>&1 | tee deploy.log
    
    if grep -q 'ERROR' deploy.log; then
      echo "::error::Deployment failed"
      exit 1
    elif grep -q 'Deployed successfully' deploy.log; then
      echo "::notice::Deployment succeeded"
      exit 0
    else
      echo "::warning::Deployment status unclear"
      exit 1
    fi
```

**Problems:**
- ❌ No early exit (waits for entire script)
- ❌ No timeout
- ❌ Must scan log twice (once during run, once after)
- ❌ No exclusion of false positives

### ✅ The Solution (ee)

```yaml
- name: Deploy
  run: |
    ee --unix-exit-codes -t 1800 \
      --success-pattern 'Deployed successfully' \
      --error-pattern 'ERROR|FATAL' \
      --exclude 'ERROR: early error detection' \
      -- ./deploy.sh
  
- name: Check Result
  if: failure()
  run: echo "::error::Deployment failed"
  
- name: Check Result
  if: success()
  run: echo "::notice::Deployment succeeded"
```

**Why ee wins:**
- ✅ Early exit on success (saves CI/CD minutes)
- ✅ Built-in timeout
- ✅ Clean exit codes
- ✅ False positive filtering
- ✅ Native GitHub Actions integration

---

## Problem 11: Pattern Development Without Logs

### ❌ The Problem (timeout without logs)

You run a command with timeout but forget to save logs. Now you can't test patterns:

```bash
# What was run (no logs saved)
timeout 60 mist dml monitor --id rble-3087789530 --session rb_le-691708f8 --interval 15 2>&1

# Output scrolls by... then it's gone forever
# Can't test patterns later
# Must guess patterns and try again
```

**Problems:**
- ❌ Output is lost after command completes
- ❌ Can't iterate on patterns
- ❌ Must re-run command to test new patterns
- ❌ Wastes time on trial-and-error

**Workaround:**
```bash
# Must remember to save logs manually
timeout 60 mist dml monitor 2>&1 | tee /tmp/monitor.log

# But still has the block buffering problem (silent for 60 seconds)!
```

### ✅ The Solution (ee with auto-logging)

`ee` **automatically saves logs** when you use a timeout, enabling the **Exploration → Analysis → Production** workflow:

#### Step 1: Exploration (First Run)

```bash
# Don't know what pattern to watch for yet - just explore
ee -t 60 'ERROR|success|completed' -- \
  mist dml monitor --id rble-3087789530 --session rb_le-691708f8 --interval 15

# Load the log paths (ee automatically creates ~/.ee_env.$$)
source ~/.ee_env.$$
```

**What you'll see** (ee automatically prints log locations at the start):

```
📝 Logging to:
   stdout: /tmp/ee-mist_dml_monitor-12345.log
   stderr: /tmp/ee-mist_dml_monitor-12345.errlog

Starting monitor...
Checking status...
ERROR: Connection timeout
Retrying... (attempt 1)
Retrying... (attempt 2)
Retrying... (attempt 3)
ERROR: Max retries exceeded

⏱️  Timeout: No pattern matched in 60 seconds
```

> **Tip**: After running `ee`, use `source ~/.ee_env.$$` to load `$EE_STDOUT_LOG` and `$EE_STDERR_LOG` variables. No need to copy/paste paths!

#### Step 2: Analysis (Pattern Testing)

```bash
# Now analyze the saved logs (use the environment variable!)
cat $EE_STDOUT_LOG | ee 'ERROR|error' --test-pattern
```

**Output:**

```
📊 Statistics:
   Total lines:     234
   Matched lines:   5

✅ Pattern matched 5 time(s):
Line  12: ERROR: Connection timeout
Line  45: error: retry attempt 1
Line  67: error: retry attempt 2
Line  89: error: retry attempt 3
Line 234: ERROR: Max retries exceeded
```

#### Step 3: Refinement (Exclude False Positives)

```bash
# Retries are expected (not real errors) - exclude them
cat $EE_STDOUT_LOG | ee 'ERROR|error' \
  --test-pattern \
  --exclude 'retry attempt'
```

**Output:**

```
📊 Statistics:
   Total lines:     234
   Matched lines:   2
   Excluded lines:  3

✅ Pattern matched 2 time(s):
Line  12: ERROR: Connection timeout
Line 234: ERROR: Max retries exceeded
```

#### Step 4: Production (Optimized Pattern)

```bash
# Now we know exactly what to watch for - deploy with confidence
ee -t 60 \
  --success-pattern 'Monitor started successfully' \
  --error-pattern 'Connection timeout|Max retries exceeded' \
  --exclude 'retry attempt' \
  -- mist dml monitor --id rble-3087789530 --session rb_le-691708f8 --interval 15

# Exits immediately when success or real error is detected
# Logs are still auto-saved, load with: source ~/.ee_env.$$
```

**Why ee wins:**
- ✅ **Auto-logging**: Logs saved automatically with timeout
- ✅ **Auto-export**: Environment variables created (`$EE_STDOUT_LOG`, `$EE_STDERR_LOG`)
- ✅ **Pattern testing**: Test against saved logs (no re-runs)
- ✅ **Rapid iteration**: Refine patterns in seconds
- ✅ **Production ready**: Deploy optimized patterns with confidence
- ✅ **Time saved**: Hours of trial-and-error → Minutes of analysis

**Comparison:**

| Aspect | `timeout` | `ee` with timeout |
|--------|-----------|-------------------|
| **Logs saved?** | ❌ No (unless you add `tee`) | ✅ Yes (automatic) |
| **Pattern testing?** | ❌ Can't (no logs) | ✅ Yes (against saved logs) |
| **Real-time output?** | ❌ No (block buffering) | ✅ Yes (unbuffered) |
| **Early exit?** | ❌ No (waits full timeout) | ✅ Yes (on pattern match) |
| **Log location shown?** | ❌ No | ✅ Yes (printed at start) |
| **Easy to reference?** | ❌ Must copy/paste paths | ✅ Yes (`source ~/.ee_env.$$`) |
| **Environment variables?** | ❌ No | ✅ Yes (`$EE_STDOUT_LOG`, `$EE_STDERR_LOG`) |
| **Iteration time** | ⭐ Must re-run command each time | ⭐⭐⭐⭐⭐ Test instantly against logs |

**Smart Auto-Logging Rules:**
- Command mode **with** timeout → Auto-logging **enabled** (you probably want logs)
- Command mode **without** timeout → Auto-logging **disabled** (keep it simple)
- Explicit `--log` or `--file-prefix` → Always logs

**Real-world workflow:**

```
Without ee:
Run → Output lost → Guess pattern → Run again → Wrong → Guess again → Repeat...
(Hours of trial-and-error)

With ee:
Run → Logs auto-saved → Test patterns → Refine → Deploy
(Minutes to production-ready)
```

---

## Problem 12: Stuck/No-Progress Detection

### ❌ The Problem (grep/timeout)

A monitoring command gets **stuck** showing the same output repeatedly (with only timestamps changing):

```bash
# Mist monitoring gets stuck
mist dml monitor --id rble-3087789530 --session rb_le-691708f8 --interval 15

# Output (repeating forever):
rble-308   -    0        0        0        | N/A             N/A             -    -    [09:03:45]
rble-308   -    0        0        0        | N/A             N/A             -    -    [09:03:55]
rble-308   -    0        0        0        | N/A             N/A             -    -    [09:04:05]
rble-308   -    0        0        0        | N/A             N/A             -    -    [09:04:15]
rble-308   -    0        0        0        | N/A             N/A             -    -    [09:04:25]
# ... (continues for 30 minutes!) ...
```

**Why `-I`/`--idle-timeout` doesn't help:**
- Idle timeout detects **no new output** (command silent)
- This command **is** producing output (every 10 seconds)
- But it's **not making progress** (same line, only timestamp changes)

**Problems:**
- ❌ Can't detect stuck state automatically
- ❌ Wastes time watching stuck output
- ❌ No way to differentiate "stuck" from "working"
- ❌ CI/CD pipelines timeout after 30-60 minutes

### ✅ The Solution (ee)

```bash
# Step 1: Try simple repeat detection first (see raw output)
ee -t 300 --max-repeat 5 'ERROR|Completed' -- \
  mist dml monitor --id rble-3087789530 --session rb_le-691708f8 --interval 15

# If timestamps make lines different, add smart normalization:
ee -t 300 --max-repeat 5 --stuck-ignore-timestamps 'ERROR|Completed' -- \
  mist dml monitor --id rble-3087789530 --session rb_le-691708f8 --interval 15

# Output:
rble-308   -    0        0        0        | N/A             N/A             -    -    [09:03:45]
rble-308   -    0        0        0        | N/A             N/A             -    -    [09:03:55]
rble-308   -    0        0        0        | N/A             N/A             -    -    [09:04:05]
rble-308   -    0        0        0        | N/A             N/A             -    -    [09:04:15]

🔁 Stuck detected: Same line repeated 5 times (ignoring timestamps)
   Repeated line: rble-308   -    0        0        0        | N/A   ...

# Exit code: 2 (stuck/no progress)
```

**Exit codes tell you exactly what happened:**
```bash
echo $?
# 0 = Pattern matched (success or completion detected)
# 1 = Command completed but pattern never matched
# 2 = Stuck detected (or timeout without match)
# 3 = Command failed to start
```

**Best practice: Use with auto-logging to analyze stuck state**

```bash
# Logs saved automatically with timeout
ee -t 300 --max-repeat 5 --stuck-ignore-timestamps 'ERROR|Completed' -- \
  mist dml monitor --id rble-3087789530 --session rb_le-691708f8 --interval 15

# Access logs easily (no copy/paste of PIDs!)
source ~/.ee_env.$$
cat $EE_STDOUT_LOG

# Check exit code
echo $EE_EXIT_CODE
# 2 = stuck detected
```

### Comparison

| Approach | Detects Stuck? | Time Wasted | Exit Code | Distinguishes Stuck from Timeout? |
|----------|---------------|-------------|-----------|-----------------------------------|
| **`mist dml monitor`** | ❌ No | 30+ minutes | ⚠️ 0 (always success) | ❌ No |
| **`timeout 1800 mist dml monitor`** | ❌ No | 30 minutes | ⚠️ 124 (only timeout) | ❌ No |
| **`timeout + grep`** | ❌ No | 30 minutes | ⚠️ No exit code for stuck | ❌ No |
| **`ee -I 60 'ERROR' -- mist dml monitor`** | ❌ No (idle ≠ stuck) | Varies | ⚠️ 2 (timeout, not stuck) | ❌ No |
| **`ee --max-repeat 5 --stuck-ignore-timestamps 'ERROR' -- mist dml monitor`** | ✅ Yes | ~50 seconds | ✅ 2 (stuck) | ⚠️ Same exit code |

**What `--stuck-ignore-timestamps` removes:**

✅ **Automatically stripped** (common timestamp formats):
- `[09:03:45]` or `[09:03:45.123]` - Bracketed times
- `2024-11-14` or `2024/11/14` - ISO dates
- `09:03:45` (standalone) - Time without brackets
- `2024-11-14T09:03:45Z` - ISO 8601 timestamps
- `1731578625` (10 digits) - Unix epoch
- `1731578625000` (13 digits) - Millisecond epoch

❌ **NOT stripped** (need custom logic):
- `Nov 14, 2024` - Month name formats
- `14-Nov-2024` - Day-month-year
- `09h03m45s` - Custom formats
- Request IDs or counters

**When to use simple vs. smart:**

```bash
# 1. Start simple (see what's actually repeating)
ee --max-repeat 5 'ERROR' -- command

# If it detects stuck too early (timestamps differ):
#   rble-308   -    0    | N/A    [09:03:45]
#   rble-308   -    0    | N/A    [09:03:55]
# These look different to simple comparison!

# 2. Add smart normalization
ee --max-repeat 5 --stuck-ignore-timestamps 'ERROR' -- command
# Now timestamps are ignored, content is compared
```

**Real-world savings:**
- ⏱️ Detects stuck state in ~50 seconds (5 repeats × 10s interval)
- 💰 Saves ~29 minutes per stuck instance
- 🎯 Clear exit code (2) for automation
- 📊 Logs captured automatically for debugging

---

## Summary: When to Use `ee` Over `grep`

| Scenario | Problem | ee Advantage |
|----------|---------|--------------|
| **`timeout N cmd 2>&1`** | ⭐⭐⭐⭐⭐ No output for entire timeout! | Automatic unbuffering + real-time output |
| **Pattern development** | ⭐⭐⭐⭐⭐ Lost output, trial-and-error | Auto-logging + pattern testing |
| **False positives in logs** | ⭐⭐⭐ Complex pipes | `--exclude` flag |
| **Success OR error patterns** | ⭐⭐⭐⭐⭐ Race conditions | `--success-pattern` + `--error-pattern` |
| **Stall/hang detection** | ⭐⭐⭐⭐⭐ Complex shell scripts | `-I` idle timeout |
| **Stuck/no-progress detection** | ⭐⭐⭐⭐⭐ Wasted time, no detection | `--max-repeat` with smart timestamp normalization |
| **Pattern testing** | ⭐⭐⭐⭐ Slow iteration | `--test-pattern` mode |
| **CI/CD integration** | ⭐⭐⭐⭐ Background jobs, signals | One simple command |
| **Context with exclusions** | ⭐⭐⭐⭐ Awk/sed required | `--exclude` + `-C` |
| **Kubernetes monitoring** | ⭐⭐⭐⭐ Complex scripting | Built-in dual patterns |
| **Overall timeout** | ⭐⭐⭐ Separate timeout command | `-t` flag |
| **Early exit on success** | ⭐⭐⭐⭐⭐ Not possible | Success patterns |
| **Statistics** | ⭐ Only line count | Full statistics |

---

## Measurable Benefits

### Lines of Code Reduction

Real examples from this document show consistent complexity reduction:

| Scenario | Traditional Approach | With `ee` | Reduction |
|----------|---------------------|-----------|-----------|
| Dual-pattern monitoring | 30+ lines (background jobs, signals) | 3 lines | **90%** |
| False positive filtering | 10+ lines (multiple pipes) | 1 line | **90%** |
| Stall detection | 20+ lines (custom loop, stat) | 1 line | **95%** |
| Stuck detection | 25+ lines (custom state tracking) | 1 line | **96%** |
| CI/CD integration | 15+ lines (complex scripting) | 3 lines | **80%** |

### Time Savings

- **Pattern testing**: Test against large logs instantly (no command execution needed)
- **Early exit**: Don't wait for timeout when success/error is detected early
- **Real-time output**: No silent waiting with `timeout N command 2>&1`

### Maintenance Impact

- **Fewer bugs**: Less custom shell code = fewer places for bugs
- **Easier to read**: Clear intent vs complex background job management
- **Cross-platform**: No need to handle Linux/Mac differences (stat, timeout, etc.)

---

## Getting Started

1. **Identify complex grep patterns in your scripts**
2. **Test with `--test-pattern` mode first**
3. **Add exclusions for false positives**
4. **Deploy with confidence**

See [README.md](../README.md) for installation and complete documentation.


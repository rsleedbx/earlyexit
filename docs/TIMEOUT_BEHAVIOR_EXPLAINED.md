# Timeout Behavior: How Idle and First-Output Timeouts Work

## Quick Answer

**Idle timeout resets on EVERY line of output, not just at the beginning.**

```bash
# If you set --idle-timeout 10:
ee --idle-timeout 10 'ERROR' terraform apply

# Timeline:
# 0s:  Command starts
# 5s:  First output appears → idle timer RESETS to 0
# 15s: More output appears → idle timer RESETS to 0
# 20s: More output appears → idle timer RESETS to 0
# 35s: No output for 10s → TIMEOUT (killed at 30s mark)
```

**The idle timeout is continuously checked and resets on every single line of output.**

---

## Two Different Timeouts

### 1. `--first-output-timeout` (Startup Detection)

**What it does:** Kills the command if NO output appears within N seconds from start.

**When it checks:** Only at the beginning, before any output.

**When it stops checking:** As soon as the first line of output appears (on stdout OR stderr).

**Example:**
```bash
ee --first-output-timeout 30 'ERROR' terraform apply

# Timeline:
# 0s:  Command starts → timer starts
# 10s: Still no output → timer at 10s
# 20s: Still no output → timer at 20s
# 25s: First output appears → timer STOPS (success!)
# 35s: More output → timer doesn't restart (already succeeded)
# 100s: More output → timer doesn't care anymore
```

**Use case:** Detect if a command is hung at startup (e.g., waiting for network, stuck on prompt).

---

### 2. `--idle-timeout` (Stall Detection)

**What it does:** Kills the command if no output appears for N seconds at ANY point during execution.

**When it checks:** Continuously, throughout the entire execution.

**When it resets:** On EVERY line of output (stdout OR stderr).

**Example:**
```bash
ee --idle-timeout 10 'ERROR' terraform apply

# Timeline:
# 0s:  Command starts
# 5s:  Output: "Initializing..." → idle timer RESETS to 0
# 8s:  Output: "Downloading..." → idle timer RESETS to 0
# 12s: Output: "Applying..." → idle timer RESETS to 0
# 22s: No output for 10s → TIMEOUT (killed at 22s mark)
```

**Use case:** Detect if a command stalls in the middle (e.g., network timeout, deadlock, infinite loop).

---

## How It Works Internally

### Code Location: `earlyexit/cli.py`

#### Monitoring Thread

```python
def check_output_timeouts():
    """Monitor thread to check for idle and first-output timeouts"""
    start_time = time.time()
    
    while process.poll() is None and not timed_out[0]:
        current_time = time.time()
        
        # Check first output timeout (only before first output)
        if args.first_output_timeout and not first_output_seen[0]:
            if current_time - start_time >= args.first_output_timeout:
                timeout_callback(f"no first output after {args.first_output_timeout}s")
                break
        
        # Check idle timeout (continuously, after first output)
        if args.idle_timeout:
            time_since_output = current_time - last_output_time[0]
            if time_since_output >= args.idle_timeout:
                timeout_callback(f"no output for {args.idle_timeout}s")
                break
        
        # Check every 100ms
        time.sleep(0.1)
```

**Key points:**
- Runs in a separate thread
- Checks every 100ms (0.1 seconds)
- `last_output_time[0]` is updated on EVERY line of output
- `time_since_output` is recalculated on every check

#### Output Tracking

```python
for line in stream:
    # Update output tracking
    current_time = time.time()
    if last_output_time is not None:
        last_output_time[0] = current_time  # ← RESETS on every line
    if first_output_seen is not None and not first_output_seen[0]:
        first_output_seen[0] = True  # ← Only sets once
```

**Key points:**
- `last_output_time` is updated on EVERY line
- `first_output_seen` is set only once (first line)
- Both stdout and stderr update these timers

---

## Examples

### Example 1: Command with Intermittent Output

```bash
ee --idle-timeout 5 'ERROR' ./slow-script.sh

# slow-script.sh output:
# 0s:  "Starting..."
# 3s:  "Step 1 done"
# 6s:  "Step 2 done"
# 9s:  "Step 3 done"
# 20s: (no output for 11s) → TIMEOUT at 14s
```

**Result:** Killed at 14s (9s + 5s idle timeout)

**Why:** Each line resets the idle timer, but the 11-second gap triggers the timeout.

---

### Example 2: Command with Long Startup, Then Fast Output

```bash
ee --first-output-timeout 60 --idle-timeout 10 'ERROR' terraform apply

# Timeline:
# 0s:   Command starts
# 45s:  First output: "Initializing..." → first-output timer STOPS
# 46s:  "Downloading plugins..."
# 47s:  "Configuring backend..."
# 48s:  "Planning..."
# 100s: (no output for 52s) → TIMEOUT at 58s
```

**Result:** 
- First-output timeout: SUCCESS (output appeared at 45s, within 60s limit)
- Idle timeout: TRIGGERED (no output from 48s to 100s = 52s gap > 10s limit)

**Why:** First-output timeout only checks once. Idle timeout checks continuously.

---

### Example 3: Command with Burst Output, Then Silence

```bash
ee --idle-timeout 5 'ERROR' ./burst-script.sh

# burst-script.sh output:
# 0s:  "Line 1"
# 0s:  "Line 2"
# 0s:  "Line 3"
# 0s:  "Line 4"
# 0s:  "Line 5"
# (100 lines in 1 second)
# 1s:  (last line)
# 10s: (no output for 9s) → TIMEOUT at 6s
```

**Result:** Killed at 6s (1s + 5s idle timeout)

**Why:** Even though 100 lines appeared quickly, the idle timer resets on the LAST line, then starts counting from there.

---

## Both Timeouts Together

You can use both timeouts simultaneously:

```bash
ee --first-output-timeout 30 --idle-timeout 10 'ERROR' terraform apply
```

**Behavior:**
1. **0-30s:** Check for first output
   - If no output by 30s → TIMEOUT (startup failure)
   - If output appears → first-output check stops
2. **After first output:** Check for idle timeout
   - If no output for 10s at any point → TIMEOUT (stall)
   - Resets on every line

**Use case:** Detect both startup hangs AND mid-execution stalls.

---

## Common Scenarios

### Scenario 1: Terraform Apply (Long Operations)

```bash
ee --idle-timeout 300 'Error' terraform apply
```

**Why 300s (5 minutes)?**
- Terraform can take minutes to create resources
- But it usually prints status updates
- 5 minutes of silence = probably stuck

**Behavior:**
- Resets on every "Creating...", "Modifying...", "Still creating..." message
- Triggers if Terraform hangs waiting for API response

---

### Scenario 2: Database Migration (Long Startup)

```bash
ee --first-output-timeout 60 --idle-timeout 30 'ERROR' ./migrate.sh
```

**Why both?**
- Database connection can take 60s to establish (first-output)
- But once started, migrations should print progress every 30s (idle)

**Behavior:**
- Waits up to 60s for "Connecting to database..."
- Once connected, expects output every 30s
- Kills if migration stalls mid-way

---

### Scenario 3: Test Suite (Fast Feedback)

```bash
ee --idle-timeout 10 'FAIL' npm test
```

**Why 10s?**
- Tests should run quickly
- 10s of silence = probably hung test

**Behavior:**
- Resets on every test result line
- Triggers if a single test hangs

---

## Comparison with Other Tools

### `timeout` Command

```bash
timeout 300 terraform apply
```

**Behavior:**
- Kills after 300s TOTAL runtime
- Does NOT reset on output
- Kills even if command is actively producing output

**Problem:** Can't distinguish between:
- Command taking a long time (but working)
- Command hung (no output)

### `earlyexit` Idle Timeout

```bash
ee --idle-timeout 300 'ERROR' terraform apply
```

**Behavior:**
- Resets on EVERY line of output
- Only kills if 300s of SILENCE
- Allows command to run indefinitely as long as it's producing output

**Advantage:** Distinguishes between:
- Command taking a long time (but working) → keeps running
- Command hung (no output) → kills it

---

## Technical Details

### Timer Resolution

- **Check interval:** 100ms (0.1 seconds)
- **Minimum practical timeout:** 1 second
- **Accuracy:** ±100ms

**Example:**
```bash
ee --idle-timeout 5 'ERROR' cmd
# Actual timeout: 5.0s to 5.1s (depending on check timing)
```

### Thread Safety

- Monitoring runs in a separate thread
- `last_output_time` is a shared list (thread-safe for single-element updates)
- No race conditions (Python GIL protects single-element list updates)

### Performance Impact

- **CPU usage:** Negligible (sleeps 100ms between checks)
- **Memory usage:** Negligible (single thread, minimal state)
- **Overhead:** < 0.1% of execution time

---

## FAQ

### Q: Does idle timeout check stdout and stderr separately?

**A: No, they share the same timer.**

Any output on stdout OR stderr resets the idle timer.

```bash
ee --idle-timeout 10 'ERROR' cmd

# Timeline:
# 0s:  stdout: "Starting..."
# 5s:  stderr: "Warning: slow operation"  ← Resets timer
# 10s: stdout: "Done"  ← Resets timer
# 25s: (no output for 15s) → TIMEOUT
```

### Q: What if I want different timeouts for stdout vs stderr?

**A: Not currently supported.**

The idle timeout applies to ANY output (stdout or stderr).

**Workaround:** Use custom FD monitoring (advanced feature).

### Q: Does idle timeout reset on empty lines?

**A: Yes, any line resets the timer (even empty lines).**

```bash
# This resets the timer:
echo ""
echo "   "
echo "\n"
```

### Q: What if the command produces output on custom file descriptors?

**A: Custom FDs are monitored separately (if detected).**

See [Custom FD Documentation](CUSTOM_FD_MONITORING.md) for details.

### Q: Can I disable idle timeout after first match?

**A: No, but you can use `--delay-exit` to capture context after match.**

```bash
ee --idle-timeout 10 --delay-exit 5 'ERROR' cmd
# After match: waits 5s for context, then exits
# Idle timeout still applies during delay period
```

---

## Summary

| Timeout Type | When It Checks | When It Resets | Use Case |
|--------------|----------------|----------------|----------|
| `--first-output-timeout` | Only at start | Never (one-time check) | Detect startup hangs |
| `--idle-timeout` | Continuously | On EVERY line of output | Detect mid-execution stalls |

**Key takeaway:** Idle timeout is a "dead man's switch" - it resets on every line of output, so it only triggers if the command truly stalls (no output for N seconds).





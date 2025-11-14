# Telemetry Analysis: What Requires SQLite?

## Current Behavior

**By default:** SQLite database is created at `~/.earlyexit/telemetry.db` and ALL executions are logged.

**Opt-out:** `--no-telemetry` or `EARLYEXIT_NO_TELEMETRY=1`

## What Uses Telemetry?

### 1. ✅ Core Features (Work WITHOUT SQLite)

These work perfectly fine with `--no-telemetry`:

```bash
# Pattern matching
ee 'ERROR' cmd                    # ✅ Works

# Timeouts
ee -t 300 --idle-timeout 60 'ERROR' cmd  # ✅ Works

# Auto-logging
ee -z --file-prefix /tmp/log 'ERROR' cmd  # ✅ Works

# Context capture
ee -B 3 -A 10 'ERROR' cmd         # ✅ Works

# All grep-compatible flags
ee -w -i -C 3 'error' cmd         # ✅ Works
```

**Conclusion:** ~95% of features work without SQLite.

### 2. ❌ Features That REQUIRE SQLite

Only these features need the database:

#### A. Interactive Learning (Watch Mode)
```bash
ee terraform apply  # Press Ctrl+C to learn
# Stores learned patterns in SQLite
```

**Without SQLite:** Can still run, but won't remember patterns.

#### B. Smart Suggestions
```bash
ee-suggest  # Shows pattern suggestions based on history
```

**Without SQLite:** No suggestions available.

#### C. Auto-Tune
```bash
ee --auto-tune 'ERROR' terraform apply
# Uses historical data to set optimal timeouts
```

**Without SQLite:** Falls back to defaults.

#### D. Statistics
```bash
ee-stats  # Show execution statistics
```

**Without SQLite:** No stats available.

### 3. 🤔 Hybrid Features (Degraded Without SQLite)

#### Watch Mode
- ✅ **Still works** without SQLite
- ❌ Won't save learned patterns
- ❌ Won't show suggestions next time

**Recommendation:** Prompt user to enable telemetry if they use Ctrl+C learning.

---

## Database Size Analysis

### What Gets Stored?

```sql
-- Per execution (1 row)
executions (
    execution_id, timestamp, command, pattern,
    timeouts, exit_code, duration, match_count,
    project_type, source_file, ...
)

-- Per match (N rows per execution)
match_events (
    execution_id, match_number, timestamp,
    line_content, matched_substring, context_before, context_after
)

-- Learned settings (1 row per command)
learned_settings (
    command_hash, pattern, timeouts, ...
)

-- User feedback (1 row per validation)
user_feedback (
    execution_id, feedback_type, ...
)
```

### Size Estimates

| Usage Pattern | Executions/Day | DB Size/Month | DB Size/Year |
|---------------|----------------|---------------|--------------|
| Light (10/day) | 10 | ~1 MB | ~12 MB |
| Medium (50/day) | 50 | ~5 MB | ~60 MB |
| Heavy (200/day) | 200 | ~20 MB | ~240 MB |
| CI/CD (1000/day) | 1000 | ~100 MB | ~1.2 GB |

**Worst case:** CI/CD with 1000 runs/day = 1.2 GB/year

### What Takes Up Space?

1. **`match_events` table** (70% of size)
   - Stores full line content + context
   - Can have 100s of rows per execution

2. **`executions` table** (25% of size)
   - One row per run
   - Stores command, pattern, metadata

3. **`learned_settings` table** (5% of size)
   - Small, only unique commands

---

## Solutions

### Option 1: Auto-Cleanup (RECOMMENDED)

**Implement automatic database cleanup on each run:**

```python
def cleanup_old_telemetry(db_path, days=30, max_size_mb=100):
    """
    Clean up old telemetry data
    
    Args:
        days: Delete executions older than N days
        max_size_mb: If DB exceeds this, delete oldest 50%
    """
    conn = sqlite3.connect(db_path)
    
    # Check database size
    db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
    
    if db_size_mb > max_size_mb:
        # Delete oldest 50% of executions
        conn.execute("""
            DELETE FROM executions 
            WHERE execution_id IN (
                SELECT execution_id FROM executions 
                ORDER BY timestamp 
                LIMIT (SELECT COUNT(*) / 2 FROM executions)
            )
        """)
        conn.execute("DELETE FROM match_events WHERE execution_id NOT IN (SELECT execution_id FROM executions)")
        conn.execute("VACUUM")  # Reclaim space
    else:
        # Delete old executions (keep learned_settings)
        cutoff = time.time() - (days * 86400)
        conn.execute("DELETE FROM executions WHERE timestamp < ?", (cutoff,))
        conn.execute("DELETE FROM match_events WHERE execution_id NOT IN (SELECT execution_id FROM executions)")
    
    conn.commit()
    conn.close()
```

**Trigger:** Run cleanup every 100th execution (1% overhead)

**Benefits:**
- ✅ Automatic (no user action)
- ✅ Keeps DB under 100 MB
- ✅ Preserves learned settings
- ✅ Minimal overhead (1% of runs)

### Option 2: Prompt on First Use

**On first run, show:**

```
🔍 earlyexit can learn from your usage patterns!

Telemetry stores:
  • Command patterns and exit codes
  • Timeout settings that worked
  • Error patterns you Ctrl+C on

This helps earlyexit suggest better patterns and timeouts.

All data stored locally in ~/.earlyexit/telemetry.db
No data is sent anywhere.

Enable telemetry? [Y/n]: _
```

**If user says no:**
- Set `EARLYEXIT_NO_TELEMETRY=1` in `~/.earlyexit/config`
- Never ask again

**Benefits:**
- ✅ User consent
- ✅ Explains value
- ❌ Friction on first use

### Option 3: Opt-In (Not Recommended)

**Change default to disabled:**

```bash
# Telemetry OFF by default
ee 'ERROR' cmd

# Opt-in to enable
ee --telemetry 'ERROR' cmd
export EARLYEXIT_TELEMETRY=1
```

**Benefits:**
- ✅ Privacy-first
- ❌ Kills learning features (most users won't opt-in)
- ❌ Defeats the purpose of "zero config"

### Option 4: Minimal Telemetry Mode

**Store only learned settings, no execution history:**

```bash
# New flag
ee --minimal-telemetry 'ERROR' cmd
```

**Stores:**
- ✅ Learned patterns (from Ctrl+C)
- ✅ Learned timeouts (from --auto-tune)

**Doesn't store:**
- ❌ Execution history
- ❌ Match events
- ❌ Full command text

**DB Size:** ~1 MB (even with heavy use)

**Benefits:**
- ✅ Learning still works
- ✅ Minimal storage
- ❌ No statistics/suggestions

---

## Recommendation: Hybrid Approach

### 1. Keep Opt-Out Default (Current Behavior)
```bash
# Telemetry ON by default
ee 'ERROR' cmd

# Opt-out if desired
ee --no-telemetry 'ERROR' cmd
export EARLYEXIT_NO_TELEMETRY=1
```

### 2. Add Auto-Cleanup (NEW)
```python
# Every 100th run, clean up old data
if execution_count % 100 == 0:
    cleanup_old_telemetry(
        db_path=telemetry.db_path,
        days=30,        # Keep last 30 days
        max_size_mb=100 # Cap at 100 MB
    )
```

### 3. Add Size Warning (NEW)
```bash
# If DB > 500 MB, show warning
⚠️  Telemetry database is large (523 MB)
   Run 'ee-clear --older-than 30d' to clean up
   Or disable telemetry: export EARLYEXIT_NO_TELEMETRY=1
```

### 4. Add Cleanup Commands (NEW)
```bash
# Manual cleanup
ee-clear --older-than 30d      # Delete old executions
ee-clear --keep-learned        # Delete all except learned settings
ee-clear --all                 # Delete everything

# Show size
ee-stats --db-size
# Output: Database: 45 MB (2,341 executions, 15,234 matches)
```

---

## Implementation Plan

### Phase 1: Auto-Cleanup (30 min)

```python
# In telemetry.py
def auto_cleanup(self):
    """Run periodic cleanup (every 100 executions)"""
    if not self.enabled:
        return
    
    # Check if cleanup needed
    count = self.get_execution_count()
    if count % 100 != 0:
        return
    
    # Run cleanup
    self.cleanup_old_data(days=30, max_size_mb=100)
```

### Phase 2: Cleanup Commands (30 min)

```python
# In telemetry_cli.py
def clear_command(older_than=None, keep_learned=False, all=False):
    """Clear telemetry data"""
    if all:
        # Delete everything
        telemetry.clear_all()
    elif keep_learned:
        # Delete executions, keep learned_settings
        telemetry.clear_executions()
    elif older_than:
        # Delete old executions
        telemetry.clear_older_than(older_than)
```

### Phase 3: Size Warnings (15 min)

```python
# In cli.py, before telemetry init
if telemetry_enabled:
    db_size_mb = get_db_size(telemetry.DEFAULT_DB_PATH)
    if db_size_mb > 500:
        print(f"⚠️  Telemetry database is large ({db_size_mb:.0f} MB)", file=sys.stderr)
        print("   Run 'ee-clear --older-than 30d' to clean up", file=sys.stderr)
```

---

## Summary

### What Works Without SQLite?

✅ **95% of features:**
- Pattern matching
- All timeouts
- Auto-logging
- Context capture
- All grep flags
- Real-time output
- Early exit

❌ **Only these need SQLite:**
- Interactive learning (saving patterns)
- Smart suggestions
- Auto-tune
- Statistics

### Recommended Solution

1. ✅ **Keep opt-out default** (current behavior)
2. ✅ **Add auto-cleanup** (keep DB < 100 MB)
3. ✅ **Add cleanup commands** (`ee-clear`)
4. ✅ **Add size warnings** (if > 500 MB)

**Result:**
- Users get learning features by default
- Database stays small (< 100 MB)
- Easy to disable if desired
- Easy to clean up if needed

### Implementation Time

- Auto-cleanup: 30 min
- Cleanup commands: 30 min
- Size warnings: 15 min

**Total:** ~75 minutes for complete solution





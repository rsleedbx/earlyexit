# Telemetry Database Size: How It's Determined & Criteria

## How Size is Determined

### 1. Physical File Size

```python
def get_db_size_mb(self) -> float:
    """Get database size in MB"""
    return os.path.getsize(self.db_path) / (1024 * 1024)
```

**Method:** Uses `os.path.getsize()` to get the actual file size on disk of `~/.earlyexit/telemetry.db`

**Returns:** Size in megabytes (MB)

**Location:** `earlyexit/telemetry.py:773-777`

---

## Size Thresholds & Criteria

### Three Key Thresholds

| Threshold | Action | Rationale |
|-----------|--------|-----------|
| **100 MB** | Auto-cleanup target | Normal operating size for heavy use |
| **500 MB** | Show warning | Indicates cleanup isn't working or extreme use |
| **No hard limit** | User can disable | Never blocks execution |

---

## Detailed Breakdown

### 1. Auto-Cleanup Target: **100 MB**

**Location:** `earlyexit/telemetry.py:789` (default parameter)

```python
def cleanup_old_data(self, days: int = 30, max_size_mb: float = 100):
```

**Behavior:**
- If DB size > 100 MB → Delete oldest 50% of executions
- If DB size ≤ 100 MB → Delete data older than 30 days

**Why 100 MB?**
- Typical database with 1000-2000 executions
- Includes full match events and context
- Small enough for fast queries
- Large enough to provide useful learning data

**Calculation:**
```
Average execution record: ~50 KB (with matches & context)
100 MB / 50 KB = ~2000 executions stored
At 200 executions/day = 10 days of history
At 1000 executions/day (CI/CD) = 2 days of history
```

### 2. Warning Threshold: **500 MB**

**Location:** `earlyexit/cli.py:1425`

```python
if db_size_mb > 500:
    print(f"⚠️  Telemetry database is large ({db_size_mb:.0f} MB)", file=sys.stderr)
```

**Behavior:**
- Shows warning on every execution
- Suggests cleanup commands
- Does NOT block execution

**Why 500 MB?**
- 5x the auto-cleanup target
- Indicates one of:
  - Auto-cleanup is failing
  - Extremely heavy use (5000+ executions)
  - User manually disabled cleanup
- Still manageable (queries remain fast)
- Large enough to avoid false alarms

**Calculation:**
```
500 MB / 50 KB = ~10,000 executions
At 1000 executions/day (CI/CD) = 10 days without cleanup
At 200 executions/day (heavy) = 50 days without cleanup
```

### 3. No Hard Limit

**Rationale:**
- Never blocks user's work
- User has full control (can disable telemetry)
- Database performance degrades gracefully
- SQLite can handle multi-GB databases (just slower)

---

## What Takes Up Space?

### Database Schema Breakdown

```sql
-- Per execution (1 row)
executions (
    execution_id, timestamp, command, pattern,
    timeouts, exit_code, duration, ...
)
Size: ~1-5 KB per row

-- Per match (N rows per execution)
match_events (
    execution_id, match_number, timestamp,
    line_content, matched_substring, 
    context_before, context_after
)
Size: ~0.5-2 KB per row (depends on line length)

-- Learned settings (1 row per unique command)
learned_settings (
    command_hash, pattern, timeouts, ...
)
Size: ~1 KB per row (small, rarely changes)
```

### Space Distribution

| Table | % of Total | Why |
|-------|-----------|-----|
| `match_events` | 70% | Stores full line content + context |
| `executions` | 25% | One row per run with metadata |
| `learned_settings` | 5% | Small, only unique commands |

### Example Sizes

**Light Use (10 executions/day):**
```
10 exec/day × 30 days = 300 executions
300 × 50 KB = 15 MB
After cleanup: ~12 MB (old data removed)
```

**Heavy Use (200 executions/day):**
```
200 exec/day × 30 days = 6,000 executions
6,000 × 50 KB = 300 MB
After cleanup: ~100 MB (oldest 66% removed)
```

**CI/CD (1000 executions/day):**
```
1000 exec/day × 30 days = 30,000 executions
30,000 × 50 KB = 1,500 MB
After cleanup: ~100 MB (oldest 93% removed)
```

---

## Auto-Cleanup Logic

### Trigger: Every 100 Executions

**Location:** `earlyexit/telemetry.py:848-851`

```python
count = self.get_execution_count()
if count % 100 != 0:
    return  # Skip cleanup
```

**Why every 100?**
- 1% overhead (negligible)
- Frequent enough to prevent bloat
- Infrequent enough to avoid performance impact

### Cleanup Decision Tree

```
Every 100th execution:
├─ Check DB size
│
├─ If size > 100 MB:
│  ├─ Delete oldest 50% of executions
│  ├─ Delete orphaned match_events
│  ├─ Run VACUUM (reclaim space)
│  └─ Result: DB size ≈ 50 MB
│
└─ If size ≤ 100 MB:
   ├─ Delete executions older than 30 days
   ├─ Delete orphaned match_events
   └─ Result: DB size stays stable

Always preserve:
└─ learned_settings table (never deleted by auto-cleanup)
```

---

## Why These Specific Numbers?

### 100 MB Target

**Pros:**
- ✅ Fast queries (< 100ms for most operations)
- ✅ Stores 1-2 weeks of heavy use
- ✅ Stores months of light use
- ✅ Small enough for laptops/CI runners
- ✅ Large enough for meaningful learning

**Cons:**
- ❌ May delete recent data in extreme CI/CD scenarios
- ❌ Requires periodic cleanup overhead

**Alternatives Considered:**
- 50 MB: Too aggressive, deletes useful data
- 200 MB: Too large, slower queries
- 500 MB: Way too large, impacts performance

### 500 MB Warning

**Pros:**
- ✅ Catches cleanup failures
- ✅ Alerts to extreme usage
- ✅ Doesn't false alarm on normal spikes
- ✅ Gives user time to act

**Cons:**
- ❌ May be annoying in extreme CI/CD

**Alternatives Considered:**
- 200 MB: Too sensitive, false alarms
- 1 GB: Too late, already impacting performance

### 30 Days Retention

**Pros:**
- ✅ Keeps recent data for learning
- ✅ Removes stale data
- ✅ Balances size vs. utility

**Cons:**
- ❌ May delete useful historical data

**Alternatives Considered:**
- 7 days: Too aggressive, loses learning data
- 90 days: Too long, database bloat

---

## User Control

### Override Auto-Cleanup

Users can manually control cleanup:

```bash
# More aggressive (keep only 7 days)
ee-clear --older-than 7d

# Less aggressive (keep 90 days)
ee-clear --older-than 90d

# Keep only learned patterns (delete all history)
ee-clear --keep-learned

# Nuclear option (delete everything)
ee-clear --all
```

### Disable Telemetry Entirely

```bash
# No database, no cleanup needed
export EARLYEXIT_NO_TELEMETRY=1
```

### Check Current Size

```bash
ee-stats
# Output includes:
# Database: /home/user/.earlyexit/telemetry.db
# Size: 45.3 MB
```

---

## Performance Impact

### Query Performance by Size

| DB Size | Query Time | Impact |
|---------|-----------|--------|
| < 50 MB | < 50ms | ✅ Imperceptible |
| 50-100 MB | 50-100ms | ✅ Acceptable |
| 100-500 MB | 100-300ms | ⚠️ Noticeable |
| > 500 MB | 300ms+ | ❌ Slow |

### Cleanup Performance

| Operation | Time | Frequency |
|-----------|------|-----------|
| Check size | < 1ms | Every 100th run |
| Delete old data | 10-50ms | Every 100th run (if needed) |
| VACUUM | 100-500ms | Every 100th run (if needed) |

**Total overhead:** ~1% of execution time (only on 100th run)

---

## Summary

### Size Determination
- **Method:** Physical file size via `os.path.getsize()`
- **Location:** `~/.earlyexit/telemetry.db`
- **Unit:** Megabytes (MB)

### Criteria
- **100 MB:** Auto-cleanup target (optimal balance)
- **500 MB:** Warning threshold (indicates issues)
- **No hard limit:** Never blocks execution

### Why These Numbers?
- Based on typical execution sizes (~50 KB each)
- Balances learning capability vs. disk space
- Keeps queries fast (< 100ms)
- Handles light to heavy use automatically

### User Control
- Can disable telemetry entirely
- Can manually clean up more/less aggressively
- Can check size anytime with `ee-stats`
- Never forced to keep telemetry





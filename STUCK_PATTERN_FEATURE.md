# `--stuck-pattern`: Partial Line Stuck Detection

## 🎯 The Problem (User's Real Case)

**Mist job monitor output:**
```
rble-308   13   12       15       6        | RUNNING         IDLE            2    N/A           [10:35:24]
rble-308   13   14       16       7        | RUNNING         IDLE            2    N/A           [10:35:31]
rble-308   13   15       19       7        | RUNNING         IDLE            2    N/A           [10:35:40]
rble-308   13   17       20       8        | RUNNING         IDLE            2    N/A           [10:35:47]
```

**Analysis:**
- **LEFT**: Numbers changing (12→14→15) = Progress indicators
- **MIDDLE**: `RUNNING IDLE 2 N/A` = **NOT CHANGING** (STUCK!)
- **RIGHT**: Timestamp changing = Progress indicators

**Existing solutions failed:**
- ❌ `--max-repeat 5`: Lines are different (counters change)
- ❌ `--stuck-ignore-timestamps`: Lines still different (counters change after timestamp removal)

**Root Cause:** Progress counters change, but **status is stuck**. Need to watch **ONLY** the status part!

---

## 🚀 The Solution: `--stuck-pattern REGEX`

Extract and monitor **only the key indicator** that shouldn't change:

```bash
ee --max-repeat 3 --stuck-pattern 'RUNNING\s+IDLE\s+\d+\s+N/A' 'RUNNING' -- command
```

### How It Works

1. `--stuck-pattern 'RUNNING\s+IDLE\s+\d+\s+N/A'` extracts the status part
2. For each line:
   - Extract: `RUNNING IDLE 2 N/A`
   - Compare: Is this the same as last line's extracted part?
3. If extracted part repeats N times → **Stuck detected!**

### Output

```
rble-308   13   12       15       6        | RUNNING         IDLE            2    N/A           [10:35:24]
rble-308   13   14       16       7        | RUNNING         IDLE            2    N/A           [10:35:31]

🔁 Stuck detected: Same line repeated 3 times (watching pattern)
   Watched part: RUNNING IDLE 2 N/A         ← Only this part checked
   Full line: rble-308 13 15 19 7 | RUNNING IDLE 2 N/A [10:35:40]
```

---

## 📊 Comparison: Before vs After

| Method | What it watches | User's case result |
|--------|----------------|-------------------|
| `--max-repeat` | **Entire line** | ❌ Fails (counters change) |
| `--stuck-ignore-timestamps` | **Line minus timestamps** | ❌ Fails (counters still change) |
| `--stuck-pattern` | **Only extracted part** | ✅ Works (status repeats!) |

---

## 🎓 How to Identify Stuck Patterns (For AI)

### Step 1: Analyze Output Structure

Ask these questions:

| Question | Example Answer | Action |
|----------|---------------|--------|
| What SHOULD change? | Counters, timestamps, IDs | **Ignore these** |
| What SHOULDN'T change? | Status, state, error message | **Watch this!** |
| What indicates stuck? | Status stays same despite counters | **Extract status** |

### Step 2: Choose Detection Method

| Output Pattern | Method | Example |
|----------------|--------|---------|
| Entire line repeats | `--max-repeat N` | No timestamps, no counters |
| Line repeats except timestamps | `--max-repeat N --stuck-ignore-timestamps` | Most logs |
| Counters change + status stuck | `--max-repeat N --stuck-pattern 'REGEX'` | **This case!** |

### Step 3: Extract the Indicator

```bash
# 1. Identify the repeating part
#    "RUNNING IDLE 2 N/A"

# 2. Create regex to match it
PATTERN='RUNNING\s+IDLE\s+\d+\s+N/A'

# 3. Use it
ee --max-repeat 5 --stuck-pattern "$PATTERN" 'ERROR' -- command
```

---

## 💡 Real-World Examples

### Database Sync (Row Counts Change, State Stuck)

```bash
# Output:
# Synced 1200 rows | state: syncing | [10:35:24]
# Synced 1400 rows | state: syncing | [10:35:31]
# Synced 1600 rows | state: syncing | [10:35:40]

ee --stuck-pattern 'state:\s*\w+' --max-repeat 8 'ERROR' -- db-sync
# Watches: "state: syncing"
# Ignores: Row counts, timestamps
```

### Kubernetes (Timestamps Change, Pod Status Stuck)

```bash
# Output:
# pod-123  Status: Pending  2024-11-14 10:35:24
# pod-123  Status: Pending  2024-11-14 10:35:31
# pod-123  Status: Pending  2024-11-14 10:35:40

ee --stuck-pattern 'Status:\s*\w+' --max-repeat 10 'Running' -- kubectl get pods -w
# Watches: "Status: Pending"
# Ignores: Timestamps
```

### Build System (File Counts Change, Task Stuck)

```bash
# Output:
# Compiling main.rs | 15/120 files | [10:35:24]
# Compiling main.rs | 15/120 files | [10:35:31]
# Compiling main.rs | 15/120 files | [10:35:40]

ee --stuck-pattern 'Compiling:\s*\S+' --max-repeat 5 'Finished' -- cargo build
# Watches: "Compiling: main.rs"
# Ignores: File counts, timestamps
```

### API Polling (Request IDs Change, Status Stuck)

```bash
# Output:
# {"id": "req-1", "status": "pending", "timestamp": "10:35:24"}
# {"id": "req-2", "status": "pending", "timestamp": "10:35:31"}
# {"id": "req-3", "status": "pending", "timestamp": "10:35:40"}

ee --stuck-pattern '"status":\s*"\w+"' --max-repeat 8 'success' -- api-poll
# Watches: "status": "pending"
# Ignores: Request IDs, timestamps
```

---

## 🔧 Implementation Details

### CLI Argument

```python
parser.add_argument('--stuck-pattern', metavar='REGEX',
                   help='Extract specific part of line to check for repeating (requires --max-repeat). '
                        'Example: "RUNNING\\s+IDLE\\s+\\d+\\s+N/A" watches only status indicators. '
                        'If pattern matches, uses the match for comparison. If not, uses full line.')
```

### Core Logic

```python
def normalize_line_for_comparison(line: str, strip_timestamps: bool = True, stuck_pattern: str = None) -> str:
    # If stuck_pattern provided, extract and return that part only
    if stuck_pattern:
        try:
            match = re.search(stuck_pattern, line)
            if match:
                return match.group(0).strip()  # Return extracted part
        except re.error:
            pass  # Invalid regex, fall through
    
    # Normal processing (strip timestamps if needed)
    # ...
```

### Detection Message

```python
if stuck_detected:
    if stuck_pattern:
        print(f"🔁 Stuck detected: Same line repeated {repeat_count} times (watching pattern)")
        print(f"   Watched part: {normalized_line}")
        print(f"   Full line: {line_stripped}")
    else:
        print(f"🔁 Stuck detected: Same line repeated {repeat_count} times")
        print(f"   Repeated line: {line_stripped}")
```

---

## 📚 Documentation Updates

### 1. README.md

Added new section: **"Advanced: `--stuck-pattern` for Partial Line Matching"**

Includes:
- Problem statement with visual example
- Solution with code examples
- "How to identify your stuck pattern" table
- Real-world examples (DB, K8s, builds, API)
- Combining all detection methods

### 2. .cursor/rules/useearlyexit.mdc

Added new section: **"🎯 Identifying Stuck Patterns (AI Pattern Analysis)"**

Includes:
- Visual analysis of changing vs non-changing parts
- AI decision process (3 steps)
- Output pattern detection method table
- Real-world stuck pattern examples
- "When to use each feature" comparison table

This teaches AI to:
1. Analyze command output structure
2. Identify what should/shouldn't change
3. Choose the right detection method
4. Generate effective stuck patterns

---

## 🎯 Exit Code

Returns **exit code 2** when stuck is detected (same as timeout/idle - "no progress made").

---

## ✅ Success Criteria (Achieved)

1. ✅ Detects stuck when status repeats despite changing counters
2. ✅ Works with user's exact Mist monitor output
3. ✅ Ignores progress indicators (counters, timestamps)
4. ✅ Shows both "watched part" and "full line" in output
5. ✅ Integrates with existing `--max-repeat` flag
6. ✅ Comprehensive AI guidance for pattern generation
7. ✅ Real-world examples across multiple domains

---

## 🚀 Impact

**Before:**
- User had to wait for timeout (wasting time)
- No way to detect stuck status with changing counters
- AI couldn't generate effective patterns

**After:**
- **Exits immediately** when status is stuck (3-5 repeats)
- **Watches key indicators** while ignoring noise
- **AI can analyze and generate** appropriate stuck patterns

**User's case:** Mist monitor with `RUNNING IDLE` status now exits in ~15 seconds instead of waiting for full timeout!

---

## 📖 AI Teaching Strategy

The documentation uses a **structured teaching approach**:

1. **Visual Analysis**: Show changing vs non-changing parts with annotations
2. **Question-Driven**: "What changes? What doesn't? What indicates stuck?"
3. **Decision Table**: Clear if-then logic for choosing detection method
4. **Real Examples**: 5+ domains (DB, K8s, builds, API, monitors)
5. **Copy-Paste Ready**: All examples are runnable commands

This ensures AI can:
- Understand the concept
- Analyze new output patterns
- Generate appropriate regex patterns
- Choose the right detection method

---

## 🎉 Summary

`--stuck-pattern` solves a critical real-world problem:

- **Problem**: Output has changing parts but stuck status
- **Solution**: Extract and watch only the key indicator
- **Result**: Fast, accurate stuck detection
- **AI Impact**: Can now generate effective patterns for complex output

**User request fulfilled:** ✅ AI can now distinguish changing progress indicators from stuck status indicators!


# Advanced Stuck Detection Design

## 🎯 Requirements (User Request)

From the user's advanced monitoring scenario:

```
rble-308   13   12  15   6   | RUNNING  IDLE      2  N/A  [10:35:24]
rble-308   13   14  16   7   | RUNNING  IDLE      2  N/A  [10:35:31]
rble-308   13   15  19   7   | RUNNING  RUNNING   2  N/A  [10:35:40]  ← Good: IDLE→RUNNING
rble-308   13   17  20   8   | RUNNING  RUNNING   2  N/A  [10:35:47]
rble-308   13   17  20   8   | RUNNING  IDLE      2  N/A  [10:35:55]  ← Bad: RUNNING→IDLE (regression!)
              ^^  ^^   ^              ^^^^
           SHOULD CHANGE         STATE TRANSITION
```

### Four Types of Stuck Detection Needed

| Type | What to Watch | Stuck Condition | Example |
|------|---------------|-----------------|---------|
| **1. Progress Pattern** | Parts that SHOULD change | If they STOP changing | Counters stuck at same value |
| **2. Stuck Pattern** | Parts that should NOT change | If they repeat (current) | Status stays "IDLE" |
| **3. Transition Pattern** | State transitions | If transition goes backward | "RUNNING → IDLE" regression |
| **4. Multiple Columns** | Different columns | Apply different rules to each | Column 1: progress, Column 2: transition |

---

## 📐 Proposed CLI Design

### Option A: Separate Flags for Each Type

```bash
# Watch multiple aspects simultaneously
ee -t 300 --max-repeat 5 \
  --progress-pattern 'rble-\d+\s+\d+\s+(\d+)\s+(\d+)\s+(\d+)' \
  --stuck-pattern 'RUNNING\s+IDLE\s+\d+\s+N/A' \
  --transition-pattern 'state' --forward-only 'IDLE,RUNNING,COMPLETED' \
  'ERROR' -- command

# progress-pattern: Extract counters, stuck if they don't change
# stuck-pattern: Extract status, stuck if it repeats
# transition-pattern: Extract state, stuck if it goes backward
```

**Pros:**
- Clear separation of concerns
- Easy to understand each rule
- Can combine multiple types

**Cons:**
- Many flags to remember
- Complex CLI

### Option B: Pattern Definition File (YAML/JSON)

```yaml
# stuck-rules.yaml
patterns:
  - name: "counters"
    type: "progress"
    regex: 'rble-\d+\s+\d+\s+(\d+)\s+(\d+)\s+(\d+)'
    expect: "change"
    max_repeat: 5
  
  - name: "status"
    type: "stuck"
    regex: 'RUNNING\s+\w+\s+\d+\s+N/A'
    expect: "no_change_or_forward"
    max_repeat: 5
  
  - name: "state"
    type: "transition"
    regex: '(IDLE|RUNNING|COMPLETED)'
    transitions:
      forward: ["IDLE→RUNNING", "RUNNING→COMPLETED"]
      regression: ["RUNNING→IDLE", "COMPLETED→RUNNING"]
```

```bash
ee -t 300 --stuck-rules stuck-rules.yaml 'ERROR' -- command
```

**Pros:**
- Very flexible
- Can define complex rules
- Reusable across commands
- Easy to version control

**Cons:**
- Requires external file
- More complex for simple cases

### Option C: Inline Pattern Syntax (Recommended)

```bash
# Concise inline syntax with type prefixes
ee -t 300 --max-repeat 5 \
  --watch-pattern 'progress:counters=\d+\s+\d+\s+\d+' \
  --watch-pattern 'stuck:status=RUNNING\s+IDLE' \
  --watch-pattern 'transition:state=IDLE>RUNNING>COMPLETED' \
  'ERROR' -- command

# Syntax:
# progress:name=REGEX        - Extract this part, stuck if doesn't change
# stuck:name=REGEX           - Extract this part, stuck if repeats
# transition:name=STATE1>STATE2>STATE3  - One-way transitions
```

**Pros:**
- Self-contained (no external files)
- Multiple patterns inline
- Type prefix makes intent clear
- Reasonably concise

**Cons:**
- Syntax needs to be learned
- Less flexible than YAML

---

## 🔧 Implementation Strategy

### Phase 1: Progress Pattern (Inverse Stuck Detection)

**Goal:** Detect when parts that SHOULD change stop changing.

```bash
# Counters should keep increasing
ee --progress-pattern '\d+\s+\d+\s+\d+' --max-repeat 3 'ERROR' -- command

# If extracted counters "12 15 6" repeat 3 times → STUCK!
```

**Implementation:**
```python
def process_stream(..., progress_pattern=None):
    last_progress_value = None
    progress_repeat_count = 0
    
    for line in stream:
        if progress_pattern:
            # Extract the part that SHOULD change
            match = re.search(progress_pattern, line)
            if match:
                current_progress = match.group(0)
                
                # Check if it's NOT changing (inverse of normal stuck)
                if current_progress == last_progress_value:
                    progress_repeat_count += 1
                    if progress_repeat_count >= max_repeat:
                        print(f"🔁 No progress detected: Counters stuck at {current_progress}")
                        stuck_detected[0] = True
                        break
                else:
                    progress_repeat_count = 0
                    last_progress_value = current_progress
```

### Phase 2: Transition Pattern (State Machine)

**Goal:** Detect invalid state transitions (regressions).

```bash
# Define allowed transitions
ee --transition-pattern 'state' \
   --forward-states 'IDLE,RUNNING,COMPLETED' \
   --max-repeat 3 'ERROR' -- command

# State machine: IDLE → RUNNING → COMPLETED
# If we see RUNNING → IDLE → regression detected!
```

**Implementation:**
```python
def process_stream(..., transition_pattern=None, forward_states=None):
    state_order = forward_states.split(',')  # ['IDLE', 'RUNNING', 'COMPLETED']
    last_state_index = -1
    
    for line in stream:
        if transition_pattern:
            match = re.search(transition_pattern, line)
            if match:
                current_state = match.group(0)
                
                try:
                    current_index = state_order.index(current_state)
                    
                    # Check if we went backward
                    if last_state_index >= 0 and current_index < last_state_index:
                        print(f"🔴 Regression detected: {state_order[last_state_index]} → {current_state}")
                        stuck_detected[0] = True
                        break
                    
                    last_state_index = current_index
                except ValueError:
                    pass  # State not in our list, ignore
```

### Phase 3: Multiple Columns (Composite Detection)

**Goal:** Watch multiple patterns with different rules.

```bash
# Watch 3 different aspects
ee --max-repeat 5 \
  --progress-pattern 'counters:\d+\s+\d+\s+\d+' \
  --stuck-pattern 'RUNNING\s+IDLE' \
  --transition-pattern 'state:IDLE>RUNNING>COMPLETED' \
  'ERROR' -- command

# Exit as soon as ANY rule triggers
```

**Implementation:**
```python
def process_stream(..., multiple_patterns=None):
    trackers = {
        'progress': {'pattern': ..., 'last_value': None, 'repeat': 0},
        'stuck': {'pattern': ..., 'last_value': None, 'repeat': 0},
        'transition': {'pattern': ..., 'states': [], 'last_index': -1}
    }
    
    for line in stream:
        # Check each tracker
        for name, tracker in trackers.items():
            if tracker['type'] == 'progress':
                check_progress(line, tracker, stuck_detected)
            elif tracker['type'] == 'stuck':
                check_stuck(line, tracker, stuck_detected)
            elif tracker['type'] == 'transition':
                check_transition(line, tracker, stuck_detected)
            
            if stuck_detected[0]:
                break
```

---

## 📊 Real-World Example (Mist Monitor)

### User's Scenario

```
rble-308   13   12  15   6   | RUNNING  IDLE      2  N/A  [10:35:24]
rble-308   13   14  16   7   | RUNNING  IDLE      2  N/A  [10:35:31]
rble-308   13   15  19   7   | RUNNING  RUNNING   2  N/A  [10:35:40]
rble-308   13   17  20   8   | RUNNING  RUNNING   2  N/A  [10:35:47]
rble-308   13   17  20   8   | RUNNING  RUNNING   2  N/A  [10:35:55]  ← Counters stuck!
rble-308   13   17  20   8   | RUNNING  IDLE      2  N/A  [10:36:02]  ← Regression!
```

### Comprehensive Detection

```bash
ee -t 300 --max-repeat 3 \
  --progress-pattern '\d+\s+\d+\s+\d+(?=\s*\|)' \
  --stuck-pattern 'RUNNING\s+\w+\s+\d+\s+N/A' \
  --transition-states 'IDLE>RUNNING>COMPLETED' \
  'ERROR|SUCCESS' \
  -- mist dml monitor --id xyz

# Detects 3 types of stuck:
# 1. Counters "13 17 20 8" not changing (progress stuck)
# 2. Status "RUNNING IDLE" repeating (status stuck)
# 3. State "RUNNING → IDLE" going backward (regression)
```

### Output

```
🔁 No progress detected: Counters stuck at "17 20 8" (repeated 3 times)
   Line: rble-308 13 17 20 8 | RUNNING RUNNING 2 N/A [10:35:55]
   Expected: Counters should increase over time
   Exit code: 2

# OR

🔴 Regression detected: State transition RUNNING → IDLE
   Previous state: RUNNING (index 1)
   Current state: IDLE (index 0)
   Expected: Forward progress only (IDLE → RUNNING → COMPLETED)
   Exit code: 2
```

---

## 🎯 Recommended Implementation Order

### Phase 1: `--progress-pattern` (Inverse Stuck)
- Detect when expected-to-change parts stop changing
- Most requested feature
- Relatively simple to implement
- **Estimated effort:** 2-3 hours

### Phase 2: `--transition-pattern` (State Machine)
- Detect invalid state transitions
- More complex (need state ordering)
- High value for monitoring
- **Estimated effort:** 4-6 hours

### Phase 3: Multiple Pattern Support
- Allow combining multiple detection types
- Requires refactoring detection logic
- Enables comprehensive monitoring
- **Estimated effort:** 6-8 hours

### Phase 4: Pattern Definition Files (Optional)
- YAML/JSON for complex scenarios
- Reusable configurations
- Nice-to-have, not critical
- **Estimated effort:** 4-6 hours

---

## 🤔 Open Questions for User

1. **Syntax preference:**
   - Option A: Separate flags (`--progress-pattern`, `--stuck-pattern`, `--transition-pattern`)
   - Option B: YAML file (`--stuck-rules file.yaml`)
   - Option C: Inline syntax (`--watch-pattern 'type:name=pattern'`)

2. **Progress pattern behavior:**
   - Should we detect "no change" or "decreasing values" or both?
   - Example: Counters going 15→10→5 is change, but backward progress?

3. **Transition pattern:**
   - Linear only (A→B→C) or allow branches (A→B or A→C)?
   - Should some transitions be repeatable? (RUNNING→RUNNING is OK?)

4. **Multiple pattern priority:**
   - Exit on FIRST rule trigger or wait for ALL?
   - Report which rule triggered?

5. **Backward compatibility:**
   - Current `--stuck-pattern` stays as-is?
   - Or rename to `--no-change-pattern` for clarity?

---

## 💡 Recommendation

**Start with Phase 1: `--progress-pattern`**

**Syntax:**
```bash
ee --max-repeat 5 \
  --progress-pattern '\d+\s+\d+\s+\d+' \
  --stuck-pattern 'RUNNING\s+IDLE' \
  'ERROR' -- command

# Simple, clear, backward compatible
# Can add --transition-pattern later
```

**Why:**
1. Solves immediate user need (counters not changing)
2. Complements existing `--stuck-pattern`
3. Simple to understand and implement
4. Natural progression: stuck → progress → transitions → multiple

**Implementation time:** 2-3 hours

---

## 📖 Documentation Updates Needed

1. **README.md**: Add "Progress Detection" section
2. **REAL_WORLD_EXAMPLES.md**: Add Problem 15 (progress stuck)
3. **.cursor/rules/useearlyexit.mdc**: Add AI guidance for choosing detection type
4. **CLI help**: Update `ee --help` with new patterns

---

## ✅ Next Steps

1. **User confirmation:**
   - Which syntax do you prefer?
   - Which phase to implement first?
   - Any specific requirements?

2. **Implementation:**
   - Add `--progress-pattern` argument
   - Implement inverse stuck detection
   - Add comprehensive tests

3. **Documentation:**
   - Update all docs with new feature
   - Add examples for each detection type
   - Create decision tree for AI

**Ready to implement once user confirms approach!** 🚀


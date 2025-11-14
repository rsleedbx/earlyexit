# Feature Simplification Analysis

## The Problem

Unix pipe chains follow simple patterns:
```bash
cat file | grep ERROR | head -10
command 2>&1 | tee log | grep pattern
curl api | jq '.data' | tee result.json
```

**Users expect:** Silent, composable tools with **no side effects**.

But `ee` currently creates hidden side effects that violate Unix philosophy.

---

## 🚨 Features That Fight Unix Philosophy

### 1. **Auto-Logging (Enabled by Default)**

**Current Behavior:**
```bash
$ ee 'ERROR' cmd
📝 Logging to:
   stdout: /tmp/ee-cmd-12345.log
   stderr: /tmp/ee-cmd-12345.errlog
```

**Problems:**
- ❌ Creates files in /tmp automatically (side effect)
- ❌ Clutters /tmp with logs from simple `cat file | ee 'pattern'` usage
- ❌ Users don't expect `grep` to create files, why should `ee`?
- ❌ Adds cognitive load: "Do I need to clean up /tmp?"

**Common Case:**
```bash
# User just wants to filter output
terraform apply | ee 'Error' | grep 'aws_instance'

# ee creates files in /tmp that user didn't ask for
# /tmp fills up with thousands of ee-*.log files over time
```

**Impact:** High - affects every command mode usage

**Better Approach:**
- **Default:** No auto-logging in pipes (like `grep`)
- **Opt-in:** Use `-l` or `--log` to enable logging
- **Or:** Only log when timeout/pattern makes sense (long-running commands)

---

### 2. **Telemetry (Enabled by Default)**

**Current Behavior:**
```bash
# Creates ~/.earlyexit/telemetry.db on first run
# Records EVERY execution to SQLite database
```

**Problems:**
- ❌ Hidden side effect (database created, disk writes on every run)
- ❌ Privacy concern (what's being recorded?)
- ❌ Performance overhead (even if small)
- ❌ Not expected: `grep` doesn't track your usage

**What's Recorded:**
- Command executed (with PII scrubbing)
- Working directory
- Patterns, timeouts, exit codes
- Timing metrics, match counts
- Project type, command category

**Impact:** Medium - database grows over time, ~1KB per execution

**Better Approach:**
- **Default:** Telemetry OFF (or prompt on first use)
- **Opt-in:** `--telemetry` or config file
- **Use case:** Only for users who want ML features (watch mode, auto-tune)

---

### 3. **Multiple Modes (Confusing)**

**Current Design:**
- Pipe mode: `cmd | ee 'pattern'`
- Command mode: `ee 'pattern' cmd`
- Watch mode: `ee cmd` (no pattern)

**Problems:**
- ❌ Users have to think about which mode
- ❌ Watch mode accidentally triggered when pattern looks like command
- ❌ Heuristics can guess wrong
- ❌ `grep` doesn't have modes, it just works

**Better Approach:**
- **Unified behavior:** Act like `grep` - detect stdin automatically
- **Watch mode:** Explicit flag `--watch` or `-W`
- **Simpler:** If pattern provided, match. If no pattern, error (like `grep`)

---

### 4. **Exit Code Convention (Grep vs Unix)**

**Current Default:**
- 0 = pattern found (grep convention)
- 1 = pattern not found (grep convention)
- 2 = timeout
- 3 = error
- 4 = detached

**Problems:**
- ❌ Confusing for shell scripts: `ee 'ERROR' cmd && echo success`
  - If ERROR found, exit 0, but that means failure!
- ❌ Had to add `--unix-exit-codes` flag to fix
- ❌ Cognitive load: remember which convention to use

**Better Approach:**
- **Default:** Unix convention (0=success, 1=error)
  - This is what users expect in scripts
- **Opt-in:** `--grep-exit-codes` for grep compatibility
- **Why:** Most users write shell scripts, not grep replacements

---

### 5. **Watch Mode (Interactive, Not for Pipes)**

**Current Behavior:**
```bash
$ ee terraform apply
🔍 Watch mode enabled...
Press Ctrl+C to teach earlyexit
```

**Problems:**
- ❌ Interactive feature doesn't work in pipes/scripts
- ❌ Can be accidentally triggered
- ❌ Creates SQLite database for learned patterns
- ❌ Not composable

**Better Approach:**
- **Explicit flag:** `ee --watch terraform apply` or `ee -W terraform apply`
- **Never auto-activate:** Only when user explicitly requests
- **Separate tool:** `ee-learn terraform apply` (different command)

---

## ✅ Features That Work Well

### 1. **Pattern Matching**
```bash
ee 'ERROR|FAIL' cmd  # ✅ Core functionality
```

### 2. **Timeouts**
```bash
ee -t 300 --idle-timeout 60 'ERROR' cmd  # ✅ Useful
```

### 3. **Early Exit**
```bash
ee 'success' deployment | head -10  # ✅ Saves time
```

### 4. **Context Capture**
```bash
ee -A 10 'ERROR' cmd  # ✅ Like grep -A
```

### 5. **Grep Compatibility**
```bash
ee -i -v -w -C 3 'error' cmd  # ✅ Familiar flags
```

### 6. **Detach Mode**
```bash
ee -D 'Ready' ./start-server.sh  # ✅ Specialized use case
```

---

## 📊 Usage Patterns Analysis

### Simple Filtering (80% of use cases)
```bash
# Just want to filter output
cat app.log | ee 'ERROR'
terraform apply | ee 'Error' | grep 'aws'
curl api | jq | ee 'error'
```

**Current:** Creates log files, telemetry, messages
**Ideal:** Silent, no side effects, just filter

### Long-Running Commands (15% of use cases)
```bash
# Want monitoring, timeouts, logging
ee -t 1800 'success|ERROR' ./deploy.sh
ee -t 300 --idle-timeout 60 'Ready' ./install.sh
```

**Current:** Auto-logging makes sense here
**Ideal:** Keep as-is, maybe prompt for telemetry

### Learning/Optimization (5% of use cases)
```bash
# Want ML features, suggestions
ee --watch terraform apply
ee --auto-tune 'ERROR' npm test
```

**Current:** Requires telemetry, SQLite
**Ideal:** Explicit opt-in, separate tool

---

## 🎯 Recommendations

### Priority 1: Remove Side Effects from Simple Usage

**Change 1: Auto-logging OFF by default in pipes**
```bash
# No side effects
$ cat file | ee 'ERROR'
ERROR: Connection failed

# Opt-in for logging
$ ee --log 'ERROR' terraform apply
📝 Logging to: /tmp/ee-terraform-12345.log
```

**Rationale:** 80% of usage is simple filtering, shouldn't create files

---

**Change 2: Telemetry OFF by default**
```bash
# First run: prompt user
$ ee 'ERROR' cmd
Would you like to enable telemetry to help improve earlyexit?
This tracks command patterns and timing (locally stored).
Enable? [y/N]: n

# Or environment variable
$ EARLYEXIT_TELEMETRY=0 ee 'ERROR' cmd
```

**Rationale:** Hidden side effects violate user trust

---

**Change 3: Watch mode requires explicit flag**
```bash
# No pattern? Error (like grep)
$ ee terraform apply
earlyexit: error: PATTERN is required (use --watch for interactive mode)

# Explicit watch mode
$ ee --watch terraform apply
🔍 Watch mode: Press Ctrl+C to teach patterns
```

**Rationale:** Prevent accidental activation, make behavior predictable

---

### Priority 2: Simplify Exit Codes

**Change: Default to Unix convention**
```bash
# 0 = command succeeded, no errors detected
# 1 = command failed OR errors detected
# 2+ = timeout/other

# For grep compatibility
$ ee --grep-exit-codes 'ERROR' cmd
```

**Rationale:** Shell script compatibility more important than grep compatibility

---

### Priority 3: Smart Auto-Logging (Medium Priority)

**Heuristic:**
- Pipe mode: Never auto-log (unless `--log`)
- Command mode + timeout: Auto-log (user expects monitoring)
- Command mode + no timeout: No auto-log (simple usage)

```bash
# No auto-log (simple usage)
$ ee 'ERROR' ls -la

# Auto-log (monitoring long command)
$ ee -t 300 'ERROR' deployment.sh
📝 Logging to: /tmp/ee-deployment-12345.log
```

**Rationale:** Context-aware behavior reduces surprise

---

## 🔬 Feature Usage Matrix

| Feature | Simple Usage (80%) | Monitoring (15%) | ML/Learning (5%) |
|---------|-------------------|------------------|------------------|
| **Pattern matching** | ✅ Essential | ✅ Essential | ✅ Essential |
| **Early exit** | ✅ Useful | ✅ Useful | ✅ Useful |
| **Timeouts** | ❌ Rarely | ✅ Essential | ✅ Essential |
| **Auto-logging** | ❌ Unwanted | ✅ Useful | ✅ Useful |
| **Telemetry** | ❌ Unwanted | ❌ Optional | ✅ Essential |
| **Watch mode** | ❌ Never | ❌ Never | ✅ Essential |
| **Context (-A/-B)** | ⚠️ Sometimes | ✅ Useful | ✅ Useful |
| **Grep flags** | ✅ Useful | ✅ Useful | ✅ Useful |
| **Exit codes (grep)** | ❌ Confusing | ✅ Optional | ❌ Confusing |
| **Exit codes (Unix)** | ✅ Essential | ✅ Essential | ✅ Essential |

---

## 💡 Proposed Default Behavior

### Simple Case (No Flags)
```bash
$ ee 'ERROR' cmd
# - No log files created
# - No telemetry recorded
# - No messages printed (unless match)
# - Exit 0 = no errors, Exit 1 = errors found
# - Behaves like grep
```

### With Timeout (Monitoring Mode)
```bash
$ ee -t 300 'ERROR' deployment.sh
📝 Monitoring deployment.sh (timeout: 300s)
   Logs: /tmp/ee-deployment-12345.log
# - Auto-logging enabled (makes sense for monitoring)
# - No telemetry (still off by default)
# - Show progress/status
```

### With Watch Mode (Learning Mode)
```bash
$ ee --watch terraform apply
🔍 Watch mode enabled
   Press Ctrl+C when you see errors to teach patterns
   Enable telemetry to remember patterns: ee --enable-telemetry
# - Interactive mode
# - Prompt to enable telemetry
# - Saves patterns locally (no database unless telemetry on)
```

---

## 🚀 Migration Path

### Phase 1: Make Side Effects Opt-In (Breaking Change)
- Auto-logging: OFF by default in pipes, ON with `-t` timeout
- Telemetry: OFF by default, prompt on first `--watch` usage
- Watch mode: Requires `--watch` flag
- Exit codes: Default to Unix (0=success), add `--grep-exit-codes` for old behavior

**Impact:** Existing users need to add flags, but new users get intuitive behavior

### Phase 2: Add Smart Defaults
- Detect long-running commands (> 30s runtime), offer to enable logging
- Detect repeated commands, offer to enable telemetry
- Suggest `--watch` when pattern repeatedly doesn't match

### Phase 3: Separate Tools (Optional)
- `ee` - Core filtering (like grep)
- `ee-monitor` - Full logging/timeout features (alias: `ee -l`)
- `ee-learn` - Interactive learning (alias: `ee --watch`)

---

## 📋 Summary: What to Change

### Remove These Defaults:
1. ❌ Auto-logging in simple commands
2. ❌ Telemetry by default
3. ❌ Watch mode auto-activation
4. ❌ Grep exit code convention (0=match)

### Add These Defaults:
1. ✅ Silent operation (no side effects)
2. ✅ Unix exit codes (0=success)
3. ✅ Explicit flags for features
4. ✅ Smart context-aware logging

### Keep These:
1. ✅ Pattern matching
2. ✅ Early exit
3. ✅ Timeouts
4. ✅ Grep compatibility flags
5. ✅ Pipe composability

---

## 🎯 Result

**Before:** Feature-rich but surprising
**After:** Simple by default, powerful when needed

**Unix Philosophy:** Do one thing well, compose with others, no hidden side effects.


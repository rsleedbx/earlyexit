# Response to Mist Feedback - Implementation Plan

## 🎉 **Good News: Many Features Already Exist!**

### Already Implemented ✅

1. **✅ Idle Timeout / Hang Detection** (Priority #1)
   ```bash
   ee -t 1800 --idle-timeout 180 'Error' -- terraform apply
   ee -t 1800 -I 180 'Error' -- terraform apply  # Short form
   ```
   - Exit code 2 for idle timeout
   - Documented in README and help

2. **✅ First Output Timeout** (Priority #6)
   ```bash
   ee -t 1800 --first-output-timeout 60 'Error' -- terraform init
   ee -t 1800 -F 60 'Error' -- terraform init  # Short form
   ```
   - Exit code 2 for first output timeout
   - Detects startup failures

3. **✅ Context Lines (grep-style)** (Priority #11)
   ```bash
   ee -t 1800 -C 3 'Error' -- terraform apply  # 3 lines before & after
   ee -t 1800 -B 3 'Error' -- command          # 3 lines before
   ee -t 1800 -A 10 'Error' -- command         # Wait 10s after match for context
   ```
   - Note: `-A` is time-based (seconds), not line-based (better for full error traces)

4. **✅ Log File Passthrough** (Priority #22)
   ```bash
   # Auto-logging (enabled by default in command mode)
   ee -t 1800 'Error' -- terraform apply
   # Creates: /tmp/ee-terraform_apply-PID.log and .errlog
   
   # Custom prefix
   ee -t 1800 --file-prefix terraform 'Error' -- terraform apply
   
   # Disable auto-logging
   ee --no-auto-log 'Error' -- command
   ```
   - Automatically unbuffered (no need for stdbuf)
   - Separate stdout/stderr logs

5. **✅ Multiple FD Monitoring** (Priority #20)
   ```bash
   ee --stdout 'Error' -- command      # Monitor stdout only
   ee --stderr 'FATAL' -- command      # Monitor stderr only
   ee 'Error' -- command               # Both (default)
   
   # Different patterns per stream
   ee --fd-pattern 1 'FAILED' --fd-pattern 2 'ERROR' -- command
   ```

6. **✅ Pattern Library / Presets** (Priority #10)
   ```bash
   ee --profile terraform -- terraform apply
   ee --profile npm -- npm test
   ee --profile pytest -- pytest
   
   # List available profiles
   ee --list-profiles
   
   # Show profile details
   ee --show-profile terraform
   ```
   - Built-in profiles with validated patterns
   - F1 scores showing effectiveness

7. **✅ Buffering Documentation** (Priority #6 in improvements)
   - Well documented in README
   - Auto-unbuffering in command mode (default `-u`)

---

## 🚧 **Features That Need Implementation**

### CRITICAL - High Impact

#### 1. **Exit Code Convention** ⭐⭐⭐⭐⭐
**Status:** NEEDS DISCUSSION

**Current:**
- 0 = pattern matched (error found)
- 1 = no match
- 2 = timeout
- 3 = CLI error
- 4 = detached

**Mist Feedback:** Exit code 0 for "error found" is counterintuitive

**Analysis:**
- Current behavior follows `grep` convention (0 = found, 1 = not found)
- Changing would be BREAKING CHANGE
- Many users may depend on current behavior

**Proposed Solutions:**

**Option A: Add `--invert-exit-codes` flag (Non-breaking)**
```bash
ee --invert-exit-codes 'Error' -- command
# 0 = no match (success)
# 1 = pattern matched (error found)
```

**Option B: Add `--unix-exit-codes` flag (Non-breaking)**
```bash
ee --unix-exit-codes 'Error' -- command
# Same as Option A but different name
```

**Option C: Version 1.0 Breaking Change**
- Announce in v0.x that exit codes will change in v1.0
- Give users migration time
- Add `--grep-exit-codes` to get old behavior

**Recommendation:** Option A (`--invert-exit-codes`) for backward compatibility

---

#### 2. **Negative Patterns / Exclusions** ⭐⭐⭐⭐⭐
**Status:** NOT IMPLEMENTED - HIGH PRIORITY

**What We Need:**
```bash
ee -t 1800 'Error' --exclude 'Error: early error detection' -- terraform plan
ee -t 1800 'timeout' --exclude 'timeouts \{' -- terraform plan
```

**Implementation Plan:**
1. Add `--exclude PATTERN` argument (can be repeated)
2. Check exclusions BEFORE main pattern
3. If line matches exclusion, skip it
4. Document in help and README

**Code Changes:**
- `earlyexit/cli.py`: Add `--exclude` argument
- `earlyexit/cli.py`: Check exclusions in `process_stream()`
- Tests: Add test cases for exclusions

**Estimated Effort:** 2-3 hours

---

#### 3. **Success Pattern Matching** ⭐⭐⭐⭐
**Status:** NOT IMPLEMENTED - HIGH PRIORITY

**What We Need:**
```bash
ee -t 1800 \
  --error-pattern 'Error|Failed' \
  --success-pattern 'Apply complete!' \
  -- terraform apply
```

**Exit Codes:**
- 0 = success pattern matched (early success exit)
- 1 = error pattern matched
- 2 = timeout (no pattern matched)

**Implementation Plan:**
1. Add `--success-pattern` and `--error-pattern` arguments
2. For backward compat: if neither specified, `pattern` is treated as error
3. Monitor both patterns simultaneously
4. Exit with appropriate code based on which matches first

**Code Changes:**
- Add arguments for both patterns
- Modify monitoring logic to track both
- Add tests for dual pattern matching

**Estimated Effort:** 4-6 hours

---

#### 4. **Pattern Testing / Validation Mode** ⭐⭐⭐⭐
**Status:** NOT IMPLEMENTED - HIGH PRIORITY

**What We Need:**
```bash
# Test pattern against log file
ee --test-pattern 'Error|Failed' < terraform.log

# Show matches
ee --test-pattern 'Error|Failed' --show-matches < terraform.log

# Test with exclusions
ee --test-pattern 'timeout' --exclude 'timeouts \{' < terraform.log
```

**Implementation Plan:**
1. Add `--test-pattern` flag (mode switch)
2. Read from stdin (pipe mode)
3. Apply pattern and show results
4. Report: matches found, line numbers, false positives/negatives

**Code Changes:**
- Add test mode to main()
- Create `test_pattern_mode()` function
- Show statistics and matches

**Estimated Effort:** 3-4 hours

---

#### 5. **Multi-line Pattern Matching** ⭐⭐⭐⭐
**Status:** NOT IMPLEMENTED - MEDIUM PRIORITY

**What We Need:**
```bash
ee -t 1800 --multiline 'Error:.*\n.*quota exceeded' -- terraform apply
```

**Implementation Plan:**
1. Add `--multiline` flag
2. Use regex with `re.MULTILINE | re.DOTALL`
3. Buffer N lines (configurable) for matching
4. Slide window through output

**Code Changes:**
- Add `--multiline` argument
- Modify `process_stream()` to buffer lines
- Add sliding window logic

**Estimated Effort:** 6-8 hours

**Note:** Complex feature, may want to defer to v1.0

---

#### 6. **Rate Limit Detection** ⭐⭐⭐⭐
**Status:** PARTIALLY IMPLEMENTED via profiles

**Current Workaround:**
```bash
# Can use profile pattern or custom pattern
ee --profile gcp 'quota exceeded|rate limit|429' -- gcloud sql instances create
```

**Enhancement Needed:**
- Add specific exit code for rate limits (e.g., 7)
- Add `--rate-limit-pattern` for clarity
- Parse "Retry-After" headers if available

**Estimated Effort:** 2-3 hours

---

### IMPORTANT - Would Be Very Helpful

#### 7. **Multiple Patterns with Labels** ⭐⭐⭐⭐
**Status:** NOT IMPLEMENTED

**What We Need:**
```bash
ee -t 1800 \
  --pattern 'Error' --label 'TERRAFORM_ERROR' \
  --pattern 'Permission denied' --label 'AUTH_ERROR' \
  --pattern 'Quota exceeded' --label 'QUOTA_ERROR' \
  --json \
  -- terraform apply
```

**Implementation Plan:**
1. Add `--label` argument (follows previous `--pattern`)
2. Track which labeled pattern matched
3. Include in JSON output
4. Different exit codes per label (optional)

**Estimated Effort:** 4-5 hours

---

#### 8. **JSON Output Mode** ⭐⭐⭐
**Status:** NOT IMPLEMENTED

**What We Need:**
```bash
ee -t 1800 --json 'Error' -- terraform apply
```

**Output:**
```json
{
  "exit_code": 1,
  "reason": "pattern_matched",
  "pattern": "Error",
  "label": "TERRAFORM_ERROR",
  "matched_line": "Error: Failed to load plugin schemas",
  "line_number": 42,
  "duration_seconds": 15.3,
  "timeout_seconds": 1800,
  "idle_timeout_seconds": null
}
```

**Implementation Plan:**
1. Add `--json` flag
2. Suppress normal output
3. Print JSON at end
4. Include all relevant metadata

**Estimated Effort:** 3-4 hours

---

#### 9. **Match Counter / Threshold** ⭐⭐⭐
**Status:** PARTIALLY IMPLEMENTED

**Current:**
```bash
ee -m 3 'Warning' -- command  # Exit after 3 matches
```

**Enhancement Needed:**
- Add threshold syntax: `--threshold 3`
- Show progress: `[2/3 warnings]`
- Per-pattern thresholds with labels

**Estimated Effort:** 2-3 hours (mostly already done)

---

#### 10. **Buffering Detection / Warning** ⭐⭐⭐
**Status:** NOT IMPLEMENTED

**What We Need:**
```bash
# Warn if no output for 5s (might be buffering)
ee --detect-buffering 'Error' -- python script.py
```

**Implementation Plan:**
1. Add `--detect-buffering` flag
2. Track time since last output
3. Print warning if > threshold
4. Suggest `stdbuf -o0` or similar

**Estimated Effort:** 2 hours

---

### NICE TO HAVE - Minor Improvements

#### 11. **Progress Indicator** ⭐⭐
**Status:** NOT IMPLEMENTED

**What We Need:**
```bash
ee -t 1800 --progress 'Error' -- terraform apply

# Shows:
# [00:03:42 / 30:00] Monitoring terraform apply...
#   Last output: 2s ago
#   Lines processed: 1,247
```

**Estimated Effort:** 3-4 hours

---

#### 12. **Pattern Priority / Ordered Matching** ⭐⭐⭐
**Status:** NOT IMPLEMENTED - COMPLEX

Can be achieved with labels + different thresholds:
```bash
ee -t 1800 \
  --pattern 'FATAL' --label 'FATAL' --threshold 1 \
  --pattern 'Error' --label 'ERROR' --threshold 1 \
  --pattern 'Warning' --label 'WARNING' --threshold 3 \
  -- command
```

**Estimated Effort:** 6-8 hours (depends on labels implementation)

---

## 📋 **Implementation Priority**

### Phase 1: Critical Fixes (Next Release - v0.0.5)
1. ✅ Exit code flag (`--invert-exit-codes` or `--unix-exit-codes`)
2. ✅ Negative patterns (`--exclude`)
3. ✅ Pattern testing mode (`--test-pattern`)
4. ✅ Success pattern (`--success-pattern`)

**Estimated: 12-16 hours**

### Phase 2: High-Value Features (v0.1.0)
5. ✅ JSON output mode (`--json`)
6. ✅ Multi-line matching (`--multiline`)
7. ✅ Pattern labels (`--label`)
8. ✅ Buffering detection (`--detect-buffering`)
9. ✅ Rate limit exit code

**Estimated: 18-24 hours**

### Phase 3: Nice to Have (v0.2.0)
10. ✅ Progress indicator
11. ✅ Pattern priority
12. ✅ Enhanced thresholds

**Estimated: 12-16 hours**

---

## 🎯 **Immediate Actions**

### 1. Documentation Updates (Now)
Update README with Mist's use cases:

```markdown
## Real-World Use Case: Terraform with Cloud Providers

Mist uses earlyexit for fast-failure detection in Terraform operations:

```bash
# Terraform apply with hang detection
ee -t 1800 -I 180 --profile terraform -- terraform apply -auto-approve

# What this does:
# - Max 30 min timeout (safety net)
# - Exit if hung for 3 min (idle timeout)
# - Uses Terraform error patterns
# - Auto-saves logs
```

Benefits:
- Saves 20-30 minutes on failed operations
- Detects hung operations early
- Provides faster feedback
```

### 2. Quick Wins (This Week)
1. Add `--exclude` pattern support
2. Add `--invert-exit-codes` flag  
3. Document all existing features Mist is missing

### 3. Feature Announcement
Create GitHub issues for:
- Success pattern matching
- JSON output mode
- Pattern testing mode
- Multi-line matching

---

## 📊 **What Mist Can Use TODAY**

```bash
# Ideal command with current features:
ee \
  -t 1800 \
  -I 180 \
  -F 60 \
  --profile terraform \
  --file-prefix terraform \
  -C 3 \
  -- terraform apply -auto-approve

# What this provides:
# ✅ Max 30 min timeout
# ✅ Exit if hung for 3 min (idle timeout)
# ✅ Exit if no startup in 60s (first output timeout)
# ✅ Terraform error patterns (profile)
# ✅ Auto-saved logs (file-prefix)
# ✅ 3 lines context before match
# ✅ Unbuffered output (default)
```

**Missing from ideal:**
- Success pattern (early exit on success)
- JSON output (programmatic parsing)
- Pattern exclusions (false positive filtering)

---

## 💬 **Response to Specific Points**

### "Exit Code 0 for Error is Counterintuitive"
**Agree!** But it follows `grep` convention. We'll add `--invert-exit-codes` for Unix-style behavior.

### "Idle Timeout is Critical"
**Already implemented!** `-I` / `--idle-timeout` - just needs better documentation.

### "First Output Timeout Needed"
**Already implemented!** `-F` / `--first-output-timeout`

### "Context Lines Like Grep"
**Already implemented!** `-A`, `-B`, `-C` flags

### "Log File Passthrough"
**Already implemented!** Auto-logging with `--file-prefix`

### "Pattern Presets for Tools"
**Already implemented!** `--profile` system with terraform, npm, pytest, etc.

---

## 🎉 **Summary**

**Good News:** 60-70% of requested features already exist!

**Mist is Missing:**
- Awareness of existing features (documentation issue)
- Success pattern matching (high priority)
- Pattern exclusions (high priority)
- Pattern testing mode (high priority)
- JSON output (medium priority)

**Action Plan:**
1. **Immediate:** Update docs, add `--exclude` and `--invert-exit-codes`
2. **v0.0.5 (Next 2 weeks):** Success patterns, testing mode
3. **v0.1.0 (Next month):** JSON output, multi-line matching, labels

**Timeline:** Most critical features can be delivered in 2-4 weeks.


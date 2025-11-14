# Implementation Plan: EarlyExit v0.0.5

Based on Mist feedback, focusing on critical missing features.

---

## 🎯 **Release Goals**

Fix the 4 highest-impact issues from Mist feedback:
1. Pattern exclusions (false positive filter)
2. Exit code convention option
3. Pattern testing mode
4. Success pattern matching

**Target:** Complete within 2 weeks

---

## 1. Pattern Exclusions (`--exclude`) ⭐⭐⭐⭐⭐

### Problem
Mist had multiple false positives:
- "timeout" matched Terraform config: `timeouts { create = "30m" }`
- "Error: early error detection" matched Mist's own messages

### Solution
```bash
ee -t 1800 'Error' --exclude 'Error: early error detection' -- terraform plan
ee 'timeout' --exclude 'timeouts \{' -- terraform plan
```

### Implementation

#### CLI Arguments (cli.py)
```python
parser.add_argument('--exclude', dest='exclude_patterns', action='append',
                   metavar='PATTERN',
                   help='Exclude lines matching this pattern (can be repeated). '
                        'Exclusions are checked before the main pattern.')
```

#### Pattern Matching Logic (process_stream in cli.py)
```python
def process_stream(..., exclude_patterns=None):
    # After line is read
    if isinstance(line, bytes):
        line = line.decode('utf-8', errors='replace')
    
    line_stripped = line.rstrip('\n')
    
    # Check exclusions FIRST
    if exclude_patterns:
        for exclude_pattern in exclude_patterns:
            if exclude_pattern.search(line_stripped):
                # Line matches exclusion, skip it
                if log_file:
                    log_file.write(line)  # Still log it
                if not args.quiet:
                    print(line_stripped, flush=True)  # Still show it
                continue  # Skip pattern matching
    
    # Now check main pattern
    match = pattern.search(line_stripped)
    ...
```

#### Compilation
```python
# In main(), after pattern compilation
exclude_compiled = []
if args.exclude_patterns:
    flags = re.IGNORECASE if args.ignore_case else 0
    for exclude_pat in args.exclude_patterns:
        try:
            compiled = compile_pattern(exclude_pat, flags, args.perl_regexp,
                                      args.word_regexp, args.line_regexp)
            exclude_compiled.append(compiled)
        except Exception as e:
            print(f"❌ Invalid exclusion pattern '{exclude_pat}': {e}", file=sys.stderr)
            return 3
```

### Tests
```python
def test_exclude_pattern():
    """Test that --exclude filters out false positives"""
    result = subprocess.run(
        ['earlyexit', 'timeout', '--exclude', 'timeouts \\{', '--',
         'bash', '-c', 'echo "line 1"; echo "timeouts { create=30m }"; echo "Error: timeout exceeded"'],
        capture_output=True, text=True, timeout=5
    )
    # Should match "timeout exceeded" but not "timeouts {"
    assert result.returncode == 0
    assert "timeout exceeded" in result.stdout
    assert "timeouts {" in result.stdout  # Still shown, just not matched

def test_multiple_excludes():
    """Test multiple --exclude patterns"""
    result = subprocess.run(
        ['earlyexit', 'Error', 
         '--exclude', 'Error: early detection',
         '--exclude', 'Error: informational',
         '--',
         'bash', '-c', 'echo "Error: early detection"; echo "Error: FATAL"'],
        capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 0
    assert "FATAL" in result.stdout
```

### Documentation
```markdown
## Filtering False Positives

Use `--exclude` to ignore specific matches:

```bash
# Ignore benign errors
ee 'Error' --exclude 'Error: informational' -- command

# Multiple exclusions
ee 'timeout' \
  --exclude 'timeouts \{' \
  --exclude 'connection_timeout =' \
  -- terraform plan
```

**How it works:**
- Exclusions checked before main pattern
- Excluded lines still shown and logged
- Only prevents early exit on excluded matches
```

**Estimated Time:** 3-4 hours

---

## 2. Exit Code Convention (`--unix-exit-codes`) ⭐⭐⭐⭐⭐

### Problem
Current behavior (grep-style):
- 0 = pattern matched (error found) ← counterintuitive for users
- 1 = no match (success)

Unix convention:
- 0 = success
- non-zero = failure

### Solution
```bash
ee --unix-exit-codes 'Error' -- command
# 0 = no error found (success)
# 1 = error found (pattern matched)
# 2+ = other failures
```

### Implementation

#### CLI Argument
```python
parser.add_argument('--unix-exit-codes', action='store_true',
                   help='Use Unix exit code convention: 0=success (no match), '
                        '1=error found (match). Default follows grep: '
                        '0=match, 1=no match.')
```

#### Exit Code Mapping
```python
def map_exit_code(code, unix_mode):
    """Map exit codes based on convention"""
    if not unix_mode:
        return code  # Keep current behavior
    
    # Unix mode: invert 0 and 1
    if code == 0:  # Pattern matched (error found)
        return 1   # Unix: non-zero = failure
    elif code == 1:  # No match (success)
        return 0   # Unix: zero = success
    else:
        return code  # Keep timeouts, errors as-is
```

#### Usage in main()
```python
def main():
    ...
    exit_code = run_command_mode(...)  # or run_pipe_mode()
    
    # Map exit code if unix mode
    if args.unix_exit_codes:
        exit_code = map_exit_code(exit_code, True)
    
    return exit_code
```

### Tests
```python
def test_unix_exit_codes_match():
    """Test --unix-exit-codes when pattern matches"""
    result = subprocess.run(
        ['earlyexit', '--unix-exit-codes', 'ERROR', '--',
         'bash', '-c', 'echo "ERROR detected"'],
        capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 1, "Unix mode: match = exit 1"

def test_unix_exit_codes_no_match():
    """Test --unix-exit-codes when pattern doesn't match"""
    result = subprocess.run(
        ['earlyexit', '--unix-exit-codes', 'ERROR', '--',
         'bash', '-c', 'echo "All good"'],
        capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 0, "Unix mode: no match = exit 0"

def test_unix_exit_codes_timeout():
    """Test --unix-exit-codes with timeout"""
    result = subprocess.run(
        ['earlyexit', '--unix-exit-codes', '-t', '1', 'NEVER', '--',
         'bash', '-c', 'sleep 10'],
        capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 2, "Unix mode: timeout still = exit 2"
```

### Documentation
```markdown
## Exit Codes

### Default (grep-style)
- `0` - Pattern matched (error found)
- `1` - No match (command completed successfully)
- `2` - Timeout
- `3` - CLI error
- `4` - Detached

### Unix Convention (`--unix-exit-codes`)
- `0` - No match (SUCCESS)
- `1` - Pattern matched (FAILURE)
- `2` - Timeout
- `3` - CLI error
- `4` - Detached

```bash
# For integration into scripts
ee --unix-exit-codes 'Error' -- terraform apply
if [ $? -eq 0 ]; then
    echo "Success: no errors found"
else
    echo "Failed: errors detected"
fi
```
```

**Estimated Time:** 2-3 hours

---

## 3. Pattern Testing Mode (`--test-pattern`) ⭐⭐⭐⭐

### Problem
No way to test patterns before using them in production.
False positives discovered only after long waits.

### Solution
```bash
# Test pattern against log file
ee --test-pattern 'Error|Failed' < terraform.log

# With exclusions
ee --test-pattern 'timeout' --exclude 'timeouts \{' < terraform.log

# Show matches
cat terraform.log | ee --test-pattern 'Error' --show-matches
```

### Implementation

#### CLI Arguments
```python
parser.add_argument('--test-pattern', metavar='PATTERN',
                   help='Test mode: test pattern against stdin and show results. '
                        'Does not run command.')
parser.add_argument('--show-matches', action='store_true',
                   help='In test mode, show matched lines (default: just statistics)')
```

#### Test Mode Function
```python
def run_pattern_test_mode(args, pattern, exclude_patterns=None):
    """
    Test pattern against stdin and report results
    """
    import sys
    
    matches = []
    excluded = []
    total_lines = 0
    
    print(f"🔍 Testing pattern: {args.test_pattern}", file=sys.stderr)
    if exclude_patterns:
        print(f"   Exclusions: {len(exclude_patterns)} pattern(s)", file=sys.stderr)
    print("", file=sys.stderr)
    
    for line_num, line in enumerate(sys.stdin, 1):
        total_lines += 1
        line = line.rstrip('\n')
        
        # Check exclusions first
        excluded_by = None
        if exclude_patterns:
            for i, exclude_pat in enumerate(exclude_patterns):
                if exclude_pat.search(line):
                    excluded_by = i
                    excluded.append((line_num, line))
                    break
        
        if excluded_by is not None:
            continue
        
        # Check main pattern
        if pattern.search(line):
            matches.append((line_num, line))
    
    # Print results
    print(f"\n📊 Test Results:", file=sys.stderr)
    print(f"   Total lines: {total_lines}", file=sys.stderr)
    print(f"   Matches: {len(matches)}", file=sys.stderr)
    print(f"   Excluded: {len(excluded)}", file=sys.stderr)
    print(f"   Match rate: {len(matches)/total_lines*100:.1f}%", file=sys.stderr)
    
    if args.show_matches and matches:
        print(f"\n✅ Matched lines:", file=sys.stderr)
        for line_num, line in matches:
            print(f"   Line {line_num}: {line}", file=sys.stderr)
    
    if args.show_matches and excluded:
        print(f"\n❌ Excluded lines:", file=sys.stderr)
        for line_num, line in excluded:
            print(f"   Line {line_num}: {line}", file=sys.stderr)
    
    # Suggest improvements
    if len(matches) == 0:
        print(f"\n⚠️  Warning: No matches found. Pattern may be too specific.", file=sys.stderr)
    elif len(matches) > total_lines * 0.5:
        print(f"\n⚠️  Warning: >50% match rate. Pattern may be too broad.", file=sys.stderr)
    
    return 0 if matches else 1
```

#### Integration
```python
def main():
    ...
    # Check for test mode
    if args.test_pattern:
        # Compile pattern
        flags = re.IGNORECASE if args.ignore_case else 0
        try:
            pattern = compile_pattern(args.test_pattern, flags, 
                                     args.perl_regexp, args.word_regexp, args.line_regexp)
        except Exception as e:
            print(f"❌ Invalid pattern: {e}", file=sys.stderr)
            return 3
        
        # Compile exclusions
        exclude_patterns = []
        if args.exclude_patterns:
            for exc in args.exclude_patterns:
                exclude_patterns.append(compile_pattern(exc, flags, ...))
        
        return run_pattern_test_mode(args, pattern, exclude_patterns)
    
    # Normal mode continues...
```

### Tests
```python
def test_pattern_test_mode():
    """Test --test-pattern mode"""
    test_input = "Line 1\nError: bad thing\nLine 3\nError: worse thing\n"
    result = subprocess.run(
        ['earlyexit', '--test-pattern', 'Error'],
        input=test_input,
        capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 0
    assert "Matches: 2" in result.stderr

def test_pattern_test_with_exclusion():
    """Test --test-pattern with --exclude"""
    test_input = "Error: bad\nError: informational\nError: critical\n"
    result = subprocess.run(
        ['earlyexit', '--test-pattern', 'Error', '--exclude', 'informational'],
        input=test_input,
        capture_output=True, text=True, timeout=5
    )
    assert "Matches: 2" in result.stderr
    assert "Excluded: 1" in result.stderr
```

### Documentation
```markdown
## Testing Patterns Before Use

Test your patterns against existing logs:

```bash
# Test pattern
cat terraform.log | ee --test-pattern 'Error|Failed'

# Output:
# 🔍 Testing pattern: Error|Failed
#
# 📊 Test Results:
#    Total lines: 1,247
#    Matches: 3
#    Excluded: 0
#    Match rate: 0.2%

# Show matched lines
cat terraform.log | ee --test-pattern 'Error' --show-matches

# Test with exclusions
cat terraform.log | ee --test-pattern 'timeout' --exclude 'timeouts \{'
```

**Best Practice:** Test patterns before using in production!
```

**Estimated Time:** 4-5 hours

---

## 4. Success Pattern Matching (`--success-pattern`) ⭐⭐⭐⭐

### Problem
Can only detect errors, not success.
Have to wait for full timeout even if success appears early.

### Solution
```bash
ee -t 1800 \
  --error-pattern 'Error|Failed' \
  --success-pattern 'Apply complete!' \
  -- terraform apply
```

Exit codes:
- 0 = success pattern matched (early success)
- 1 = error pattern matched
- 2 = timeout (neither matched)

### Implementation

#### CLI Arguments
```python
parser.add_argument('--error-pattern', metavar='PATTERN',
                   help='Pattern indicating error (exit early on match). '
                        'If neither --error-pattern nor --success-pattern specified, '
                        'positional pattern is treated as error.')
parser.add_argument('--success-pattern', metavar='PATTERN',
                   help='Pattern indicating success (exit early on match). '
                        'Exit code 0 when matched.')
```

#### Pattern Compilation
```python
# In main()
error_pattern = None
success_pattern = None

if args.error_pattern:
    error_pattern = compile_pattern(args.error_pattern, ...)
elif args.pattern:  # Backward compat
    error_pattern = compile_pattern(args.pattern, ...)

if args.success_pattern:
    success_pattern = compile_pattern(args.success_pattern, ...)

# Pass both to monitoring
if error_pattern or success_pattern:
    exit_code = run_command_mode(..., error_pattern, success_pattern)
```

#### Monitoring Logic
```python
def process_stream_dual_pattern(stream, error_pat, success_pat, args, ...):
    """Monitor for both error and success patterns"""
    for line in stream:
        line_stripped = line.rstrip('\n')
        
        # Check exclusions first
        if check_exclusions(line_stripped, exclude_patterns):
            continue
        
        # Check success pattern first (prioritize early success)
        if success_pat and success_pat.search(line_stripped):
            if not args.quiet:
                print(f"✅ Success pattern matched: {line_stripped}")
            return 'success', line_stripped
        
        # Check error pattern
        if error_pat and error_pat.search(line_stripped):
            if not args.quiet:
                print(f"❌ Error pattern matched: {line_stripped}")
            return 'error', line_stripped
        
        # Normal output
        if not args.quiet:
            print(line_stripped, flush=True)
    
    return None, None  # No match

# Exit code mapping
result, matched_line = process_stream_dual_pattern(...)
if result == 'success':
    return 0  # Success
elif result == 'error':
    return 1  # Error found
else:
    return 2  # Timeout/no match
```

### Tests
```python
def test_success_pattern_matches():
    """Test --success-pattern matches and exits early"""
    result = subprocess.run(
        ['earlyexit', '--success-pattern', 'SUCCESS', '--',
         'bash', '-c', 'echo "Starting"; echo "SUCCESS"; sleep 10; echo "Done"'],
        capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 0
    assert "SUCCESS" in result.stdout
    assert "Done" not in result.stdout  # Exited early

def test_dual_patterns_error_wins():
    """Test error pattern takes precedence when both match"""
    result = subprocess.run(
        ['earlyexit', 
         '--error-pattern', 'Error',
         '--success-pattern', 'Success',
         '--',
         'bash', '-c', 'echo "Error detected"'],
        capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 1  # Error

def test_dual_patterns_success_wins():
    """Test success pattern when error doesn't match"""
    result = subprocess.run(
        ['earlyexit', 
         '--error-pattern', 'Error',
         '--success-pattern', 'Success',
         '--',
         'bash', '-c', 'echo "Success!"'],
        capture_output=True, text=True, timeout=5
    )
    assert result.returncode == 0  # Success
```

### Documentation
```markdown
## Dual Pattern Matching (Success + Error)

Exit early on either success OR error:

```bash
# Terraform: exit on success or error
ee -t 1800 \
  --error-pattern 'Error|Failed|Exception' \
  --success-pattern 'Apply complete!' \
  -- terraform apply

# Database creation: exit when ready
ee -t 1800 \
  --error-pattern 'ERROR|PERMISSION_DENIED' \
  --success-pattern 'RUNNING|DONE' \
  -- gcloud sql instances create my-db
```

**Exit codes:**
- `0` - Success pattern matched (early success)
- `1` - Error pattern matched
- `2` - Timeout (neither matched)

**Backward compatibility:** If no `--error-pattern` or `--success-pattern`, 
positional pattern is treated as error (current behavior).
```

**Estimated Time:** 5-6 hours

---

## 🗓️ **Implementation Timeline**

### Week 1
- **Days 1-2:** Pattern exclusions (`--exclude`)
- **Days 3-4:** Exit code convention (`--unix-exit-codes`)
- **Day 5:** Testing + documentation

### Week 2
- **Days 1-2:** Pattern testing mode (`--test-pattern`)
- **Days 3-4:** Success pattern matching (`--success-pattern`, `--error-pattern`)
- **Day 5:** Integration testing, documentation, release prep

---

## ✅ **Definition of Done**

For each feature:
- [ ] Implementation complete
- [ ] Unit tests passing
- [ ] Integration tests added
- [ ] Documentation updated (README + help text)
- [ ] Manual testing with Mist use cases
- [ ] No regressions in existing tests

For release v0.0.5:
- [ ] All 4 features implemented
- [ ] Full test suite passing
- [ ] CHANGELOG.md updated
- [ ] Version bumped to 0.0.5
- [ ] Git tagged
- [ ] PyPI package published

---

## 📝 **Post-Release**

1. Update Mist team on new features
2. Get feedback on implementations
3. Plan v0.1.0 with JSON output, multi-line matching, labels
4. Consider GitHub issues for community feature requests

**Target Release Date:** ~2 weeks from start


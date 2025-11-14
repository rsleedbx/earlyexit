# Test Coverage Analysis for README Claims

## Quick Comparison Table - Test Coverage

| Feature | Pipe Mode | Command Mode | Watch Mode | Has Test? | Missing Test |
|---------|-----------|--------------|------------|-----------|--------------|
| **Idle detection** | ✅ | ✅ | ✅ Tracked | ✅ `test_pipe_timeouts.sh` | Command mode idle test |
| **Error context capture** | ✅ | ✅ | ✅ | ✅ `test_pipe_delay_exit.sh`, `test_delay_exit.sh` | Watch mode capture test |
| **ML Validation** | ❌ | ✅ | ✅ | ❌ | Need validation test |
| **Monitor stderr** | Need 2>&1 | ✅ | ✅ | ✅ `test_multifd.sh` | Negative test for pipe mode |
| **Smart Suggestions** | ❌ | ✅ | ✅ | ❌ | Need suggestions test |
| **Startup detection** | ✅ | ✅ | ✅ Tracked | ✅ `test_pipe_timeouts.sh` | Command/watch startup tests |
| Pattern Required | ✅ Yes | ✅ Yes | ❌ No | ❌ | Need pattern requirement tests |
| Chainable | ✅ | ❌ | ❌ | ❌ | Need chainable tests |
| Custom FDs | ❌ | ✅ | ✅ Detected | ✅ `test_fd.sh`, `test_watch_fd_detection.sh` | Negative test for pipe mode |
| Learning | ❌ | ❌ | ✅ | ❌ | Need learning test |

## Tests Needed

### 1. Positive Tests (Prove ✅ works)
- [ ] ML Validation tracking
- [ ] Smart suggestions system
- [ ] Command mode idle timeout
- [ ] Watch mode error context capture
- [ ] Command mode startup detection
- [ ] Watch mode startup tracking
- [ ] Learning system (Ctrl+C behavior)

### 2. Negative Tests (Prove ❌ doesn't work)
- [ ] Pipe mode: Cannot monitor stderr separately
- [ ] Pipe mode: No ML validation
- [ ] Pipe mode: No smart suggestions
- [ ] Pipe mode: Cannot use custom FDs
- [ ] Pipe mode: No learning
- [ ] Command mode: Not chainable
- [ ] Command mode: No learning
- [ ] Watch mode: Not chainable
- [ ] Watch mode: Pattern not required

### 3. Syntax Tests
- [ ] Pipe mode: `cmd | ee 'pat'`
- [ ] Command mode: `ee 'pat' cmd` (without `--`)
- [ ] Command mode: `ee 'pat' -- cmd` (with `--`, optional)
- [ ] Watch mode: `ee cmd` (no pattern)

## Action Items

1. **Update README Quick Comparison**
   - Remove `--` from command mode syntax (it's optional)
   - Add test links for all ✅ claims
   - Add note about negative tests

2. **Create Missing Positive Tests**
   - `tests/test_ml_validation.sh`
   - `tests/test_smart_suggestions.sh`
   - `tests/test_learning_system.sh`
   - `tests/test_command_idle_timeout.sh`
   - `tests/test_command_startup.sh`

3. **Create Negative Tests**
   - `tests/test_pipe_mode_limitations.sh`
   - `tests/test_command_mode_limitations.sh`
   - `tests/test_watch_mode_limitations.sh`

4. **Syntax Tests**
   - `tests/test_syntax_modes.sh`

## Priority

**High Priority (Core Claims):**
1. Pattern requirement tests
2. Chainable tests  
3. Syntax tests

**Medium Priority (Nice to Have):**
4. ML validation tests
5. Smart suggestions tests
6. Learning system tests

**Low Priority (Documentation):**
7. Comprehensive negative tests for all ❌ claims





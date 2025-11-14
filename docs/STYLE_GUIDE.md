# earlyexit Documentation Style Guide

## Parameter Order Convention

For consistency across all documentation and examples, always use this parameter order:

### Standard Format

```bash
ee [PATTERN] [OPTIONS] [-- COMMAND]
```

### Examples

#### ✅ CORRECT - Pattern first

```bash
# Basic pattern with command
ee 'ERROR' -- ./script.sh

# Pattern with options
ee 'ERROR' -t 300 -I 60 -- ./script.sh

# Pattern with exclusions
ee 'ERROR' --exclude 'ERROR_OK' -- ./script.sh

# Pattern with test mode (pipe)
cat log.txt | ee 'ERROR' --test-pattern --exclude 'ERROR_OK'

# Pattern with test mode (redirect)
ee 'ERROR' --test-pattern --exclude 'ERROR_OK' < log.txt

# Dual patterns
ee --success-pattern 'Success' --error-pattern 'ERROR' -- ./deploy.sh

# Dual patterns with test mode
cat log.txt | ee --test-pattern --success-pattern 'Success' --error-pattern 'ERROR'
```

#### ❌ INCORRECT - Options before pattern

```bash
# Don't do this
ee --test-pattern 'ERROR'
ee --exclude 'ERROR_OK' 'ERROR' -- ./script.sh
ee -t 300 'ERROR' -- ./script.sh
```

### Rationale

1. **Consistency with Unix tools**: Most Unix tools follow `command [options] pattern [file]`
2. **Readability**: Pattern is the most important parameter, should be prominent
3. **argparse compatibility**: Python's argparse handles this order naturally
4. **Mental model**: "What am I looking for?" (pattern) comes before "How should I look?" (options)

### Special Cases

#### Dual Patterns (No Traditional Pattern)

When using `--success-pattern` and `--error-pattern` **without** a traditional pattern:

```bash
# ✅ Options come first (no traditional pattern)
ee --success-pattern 'Success' --error-pattern 'ERROR' -- ./deploy.sh
ee --test-pattern --success-pattern 'Success' --error-pattern 'ERROR' < log.txt
```

**Why?** There's no traditional pattern argument, so options naturally come first.

#### Watch Mode (No Pattern at All)

```bash
# ✅ No pattern, command only
ee -- ./script.sh
ee ./script.sh
```

### Documentation Checklist

When writing examples, ensure:

- [ ] Pattern argument comes first (if present)
- [ ] Options come after pattern
- [ ] `--` separator before command (when needed)
- [ ] Multiline examples have consistent indentation (2 spaces)
- [ ] Each example includes a comment explaining what it does

### Multi-line Formatting

```bash
# ✅ CORRECT - Clear and readable
ee 'ERROR' \
  --exclude 'ERROR_OK' \
  --exclude 'EXPECTED_ERROR' \
  -t 300 \
  -I 60 \
  -- ./long-command.sh --with --many --flags

# ✅ Also acceptable - Group related options
ee 'ERROR' \
  --exclude 'ERROR_OK' --exclude 'EXPECTED_ERROR' \
  -t 300 -I 60 \
  -- ./long-command.sh --with --many --flags
```

### Common Patterns Quick Reference

| Use Case | Pattern Order |
|----------|---------------|
| Basic match | `ee 'pattern' -- cmd` |
| With timeout | `ee 'pattern' -t 300 -- cmd` |
| With exclusions | `ee 'pattern' --exclude 'X' -- cmd` |
| Test mode (pipe) | `cat log \| ee 'pattern' --test-pattern` |
| Test mode (file) | `ee 'pattern' --test-pattern < log` |
| Dual patterns | `ee --success-pattern 'S' --error-pattern 'E' -- cmd` |
| Dual + test | `ee --test-pattern --success-pattern 'S' --error-pattern 'E' < log` |

### Before Committing Documentation

Run this check to find potential inconsistencies:

```bash
# Find patterns that might be in wrong order
grep -n "ee --.*'.*'" docs/*.md

# Should return minimal results - most should be dual-pattern cases
```

---

**Last updated**: November 14, 2025  
**Version**: 1.0


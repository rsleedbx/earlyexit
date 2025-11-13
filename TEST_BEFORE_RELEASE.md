# Pre-Release Testing Checklist

**Version:** 0.0.3 (preparing for release)
**Date:** 2025-01-13

## Major Changes to Test

1. ✅ Unbuffering is now **DEFAULT** (no `-u` needed)
2. ✅ Added `--buffered` flag to opt-out
3. ✅ Auto-logging enabled by default
4. ✅ `ee` alias available
5. ✅ `-a` for append mode
6. ✅ `-z` for compression
7. ✅ First output time tracking (per stream)

---

## Test Plan

### 1. Basic Functionality
- [ ] Pattern matching (stdout)
- [ ] Pattern matching (stderr)
- [ ] Early exit on match
- [ ] No match (runs to completion)

### 2. Unbuffering (NEW DEFAULT)
- [ ] Default unbuffering (real-time output)
- [ ] `--buffered` opt-out works
- [ ] Python script shows real-time output
- [ ] Terraform/Go programs show real-time output

### 3. Auto-Logging (DEFAULT)
- [ ] Auto-logging creates files
- [ ] Intelligent filename generation
- [ ] Custom `--file-prefix` works
- [ ] `--no-auto-log` disables logging
- [ ] Separate stdout/stderr files

### 4. Timeouts
- [ ] `-t` (total timeout)
- [ ] `--idle-timeout`
- [ ] `--first-output-timeout`

### 5. Flags & Options
- [ ] `-i` (ignore case)
- [ ] `-v` (invert match)
- [ ] `-m` (max count)
- [ ] `-n` (line numbers)
- [ ] `-q` (quiet mode)
- [ ] `-a` (append mode)
- [ ] `-z` (compression)

### 6. Edge Cases
- [ ] Empty pattern
- [ ] No command provided
- [ ] Very long output
- [ ] Binary output
- [ ] Ctrl+C handling

### 7. Alias
- [ ] `ee` command works
- [ ] Same as `earlyexit`

---

## Quick Tests

Run these commands and verify behavior:


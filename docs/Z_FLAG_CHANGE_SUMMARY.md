# `-z` Flag Change Summary

## Overview

Changed gzip compression flag from `--gzip` (long form only) to `-z, --gzip` (short + long form) to match Unix conventions (`tar -z`, `rsync -z`).

## Changes Made

### 1. Code Changes

**File:** `earlyexit/cli.py`

```python
# Before
parser.add_argument('--gzip', action='store_true',
                   help='Compress log files with gzip after command completes (saves space)')

# After
parser.add_argument('-z', '--gzip', action='store_true',
                   help='Compress log files with gzip after command completes (like tar -z, rsync -z). Saves 70-90% space.')
```

### 2. Documentation Updates

**Updated all examples from `--gzip` to `-z`:**

1. ✅ `docs/COMPATIBILITY_SUMMARY.md` (8 occurrences)
2. ✅ `docs/APPEND_AND_GZIP_FEATURES.md` (9 occurrences)
3. ✅ `docs/GZIP_FLAG_RESEARCH.md` (9 occurrences)
4. ✅ `docs/BLOG_POST_EARLY_EXIT.md` (4 occurrences)

### 3. New Documentation

1. ✅ Created `docs/GZIP_FLAG_UPDATE.md` - Comprehensive guide for the change
2. ✅ Created `docs/Z_FLAG_CHANGE_SUMMARY.md` - This summary

## Verification

### Test 1: Basic Compression
```bash
$ ee -z 'xxx' -- echo "test"
✅ WORKS - Files compressed successfully
```

### Test 2: Multiple Flags
```bash
$ ee -t 10 -i -z 'test' echo "test message"
✅ WORKS - All flags work together
```

### Test 3: Decompression
```bash
$ gunzip -c /tmp/ee-*.log.gz
✅ WORKS - Files can be decompressed
```

### Test 4: Help Text
```bash
$ ee --help | grep -A1 "\-z"
  -z, --gzip            Compress log files with gzip after command completes
                        (like tar -z, rsync -z). Saves 70-90% space.
✅ WORKS - Help text correct
```

## Backward Compatibility

✅ **100% Backward Compatible**

Both forms work identically:
```bash
# New (recommended)
ee -z 'ERROR' npm test

# Old (still works!)
ee --gzip 'ERROR' npm test
```

## Unix Convention Alignment

| Tool | Flag | Purpose | Example |
|------|------|---------|---------|
| `tar` | `-z` | gzip compression | `tar -czf file.tar.gz` |
| `rsync` | `-z` | compression | `rsync -az src/ dest/` |
| `ssh` | `-C` | compression | `ssh -C user@host` |
| **`earlyexit`** | **`-z`** | **log compression** | **`ee -z 'ERROR' cmd`** |

## Benefits

1. **Familiar** - Unix users instantly recognize `-z` for compression
2. **Shorter** - `-z` vs `--gzip` (saves 5 characters)
3. **Consistent** - Matches `tar` and `rsync` conventions
4. **Compatible** - Long form `--gzip` still works
5. **Documented** - All docs updated with new examples

## User Impact

### For CLI Users
- **Recommended:** Use `-z` going forward (shorter, more familiar)
- **Still works:** Old `--gzip` continues to work

### For Profile Users
- **No changes needed:** Profiles use JSON with `"gzip": true`
- **Both flags work:** `-z` and `--gzip` both activate the profile option

### For Documentation
- **All updated:** Examples now use `-z` consistently
- **Compatibility noted:** Long form `--gzip` mentioned as alternative

## Summary

✅ **Changed:** Added `-z` as short form for `--gzip`  
✅ **Tested:** All functionality verified working  
✅ **Documented:** All docs updated with new examples  
✅ **Compatible:** Long form `--gzip` still works  
✅ **Aligned:** Now matches `tar -z`, `rsync -z` conventions  

**Status:** ✅ **COMPLETE** - Ready for use!

## Quick Reference

```bash
# Basic compression (like tar -z)
ee -z 'ERROR' npm test

# With timeout and compression
ee -t 300 -z 'ERROR' npm test

# Quiet mode + compression
ee -q -z 'ERROR' npm test

# Custom directory + compression
ee -z --log-dir ~/logs 'ERROR' npm test

# Reading compressed logs
gunzip -c /tmp/ee-*.log.gz | less
zgrep 'ERROR' /tmp/ee-*.log.gz
```

🎉 **Now fully aligned with Unix compression conventions!**


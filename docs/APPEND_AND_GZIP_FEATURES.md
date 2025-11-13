# Append and Gzip Features

## New Features

Two new features added for better `tee` compatibility and space savings:

1. **`-a` / `--append`** - Append to log files (like `tee -a`)
2. **`-z` / `--gzip`** - Compress log files with gzip (like `tar -z`, saves space)

---

## 1. Append Mode (`-a` / `--append`)

### Purpose

Match `tee -a` behavior: append to existing log files instead of overwriting them.

**Key Behavior:** `-a` omits the PID from auto-generated filenames so multiple runs use the **same file**:

- **Without `-a`**: Each run creates a unique file with PID → `/tmp/ee-npm_test-12345.log`
- **With `-a`**: All runs use the same file (no PID) → `/tmp/ee-npm_test.log`

This matches how `tee -a` works: it always writes to the same file and appends.

### Usage

```bash
# Without -a: New file each time (includes PID)
ee 'ERROR' npm test
📝 Logging to:
   stdout: /tmp/ee-npm_test-12345.log  # ← PID included

# With -a: Same file every time (no PID)
ee -a 'ERROR' npm test
📝 Logging to (appending):
   stdout: /tmp/ee-npm_test.log  # ← No PID!

ee -a 'ERROR' npm test  # Second run
📝 Logging to (appending):
   stdout: /tmp/ee-npm_test.log  # ← Same file!
```

### With Custom Prefix

```bash
# First run - creates new files
ee --file-prefix /tmp/test npm test

# Second run - OVERWRITES files (default)
ee --file-prefix /tmp/test npm test

# Second run - APPENDS to files (like tee -a)
ee --file-prefix /tmp/test -a npm test
```

### Examples

#### Example 1: Building a Log

```bash
# Day 1 - first deployment
ee --file-prefix /var/log/deploy npm run deploy

# Day 2 - append to same log
ee --file-prefix /var/log/deploy -a npm run deploy

# Day 3 - append again
ee --file-prefix /var/log/deploy -a npm run deploy

# View complete history
cat /var/log/deploy.log
```

#### Example 2: Continuous Integration

```bash
# Multiple test runs in same build
ee --file-prefix /tmp/ci-build-$BUILD_ID npm run lint
ee --file-prefix /tmp/ci-build-$BUILD_ID -a npm test
ee --file-prefix /tmp/ci-build-$BUILD_ID -a npm run e2e

# Single log file with all output
cat /tmp/ci-build-$BUILD_ID.log
```

#### Example 3: tee Replacement

```bash
# Old way (tee)
npm test 2>&1 | tee /tmp/test.log      # Creates/overwrites
npm test 2>&1 | tee -a /tmp/test.log   # Appends

# New way (earlyexit)
ee --file-prefix /tmp/test npm test    # Creates/overwrites
ee --file-prefix /tmp/test -a npm test # Appends (same as tee -a!)
```

### Visual Indicator

When using append mode, earlyexit shows:

```bash
$ ee --file-prefix /tmp/test -a echo "test"
📝 Logging to (appending):
   stdout: /tmp/test.log
   stderr: /tmp/test.errlog
```

Note the `(appending)` indicator!

---

## 2. Gzip Compression (`-z` / `--gzip`)

### Purpose

Automatically compress log files after command completes to save disk space.

### Usage

```bash
# Regular logging (uncompressed)
ee npm test
# Creates: /tmp/ee-npm_test-<pid>.log

# With gzip compression (like tar -z)
ee -z npm test
# Creates: /tmp/ee-npm_test-<pid>.log.gz
```

### Benefits

**Space savings:** Log files are typically very compressible (70-90% reduction).

| File Type | Typical Compression |
|-----------|-------------------|
| Text logs | 70-90% smaller |
| JSON logs | 80-95% smaller |
| Repetitive output | 90%+ smaller |

### Examples

#### Example 1: Basic Usage

```bash
$ ee -z 'ERROR' npm test

📝 Logging to:
   stdout: /tmp/ee-npm_test-12345.log
   stderr: /tmp/ee-npm_test-12345.errlog
...
🗜️  Compressed: /tmp/ee-npm_test-12345.log.gz (1,234 bytes)
🗜️  Compressed: /tmp/ee-npm_test-12345.errlog.gz (456 bytes)
```

#### Example 2: Reading Compressed Logs

```bash
# View compressed log (easiest - works like cat)
zcat /tmp/ee-npm_test-12345.log.gz | less

# Or use gunzip -c (same as zcat)
gunzip -c /tmp/ee-npm_test-12345.log.gz | less

# Decompress permanently
gunzip /tmp/ee-npm_test-12345.log.gz
# Creates: /tmp/ee-npm_test-12345.log

# Search in compressed file (like grep for .gz files)
zgrep 'ERROR' /tmp/ee-npm_test-*.log.gz

# Tail compressed logs
zcat /tmp/ee-npm_test-*.log.gz | tail -20

# Count lines in compressed log
zcat /tmp/ee-npm_test-*.log.gz | wc -l
```

#### Example 3: Space Savings Demo

```bash
# Without gzip
$ ee npm test
📝 Logging to:
   stdout: /tmp/ee-npm_test-12345.log

$ ls -lh /tmp/ee-npm_test-12345.log
-rw-r--r-- 1 user staff 45K Nov 12 16:00 /tmp/ee-npm_test-12345.log

# With gzip
$ ee -z npm test
📝 Logging to:
   stdout: /tmp/ee-npm_test-67890.log
🗜️  Compressed: /tmp/ee-npm_test-67890.log.gz (5,432 bytes)

$ ls -lh /tmp/ee-npm_test-67890.log.gz
-rw-r--r-- 1 user staff 5.3K Nov 12 16:01 /tmp/ee-npm_test-67890.log.gz

# Savings: 45K → 5.3K = 88% smaller!
```

#### Example 4: CI/CD with Gzip

```bash
# Save space on build servers
ee -z -t 600 'FAILED' npm run build

# Artifacts are automatically compressed
# Upload to artifact storage (S3, etc.)
```

---

## 3. Combining Features

### Append + Gzip

```bash
# NOT recommended - can't append to gzipped files
ee --file-prefix /tmp/test -z npm test
ee --file-prefix /tmp/test -a -z npm test  # Won't append, will create new .gz

# Recommended: Either append OR gzip, not both
ee --file-prefix /tmp/test -a npm test  # Append mode
# OR
ee -z npm test  # Gzip mode (with auto-generated names)
```

### With Other Flags

```bash
# Append + timeout + pattern
ee --file-prefix /tmp/build -a -t 300 'ERROR' npm run build

# Gzip + quiet mode
ee -z -q 'ERROR' npm test

# Gzip + custom directory
ee -z --log-dir ~/logs 'ERROR' npm test
# Creates: ~/logs/ee-npm_test-<pid>.log.gz
```

---

## 4. Comparison with tee

### Append Mode

| Feature | tee -a | earlyexit -a |
|---------|--------|--------------|
| Append to file | ✅ | ✅ |
| Separate stdout/stderr | ❌ | ✅ |
| Pattern matching | ❌ | ✅ |
| Early exit | ❌ | ✅ |
| Timeout | ❌ | ✅ |

### Examples

```bash
# tee: Append mode
npm test 2>&1 | tee -a /tmp/test.log

# earlyexit: Same + extras
ee --file-prefix /tmp/test -a 'ERROR' npm test
# ✅ Appends like tee -a
# ✅ Separate stderr log
# ✅ Pattern matching
# ✅ Early exit on error
```

---

## 5. Use Cases

### When to Use Append Mode

✅ **Good for:**
- Continuous logs (multiple runs to same file)
- Build pipelines (multiple stages)
- Daily/weekly log rotation
- Debugging sessions (accumulate output)

❌ **Not ideal for:**
- One-time runs (use default overwrite)
- When you want separate files per run

### When to Use Gzip

✅ **Good for:**
- CI/CD builds (save artifact space)
- Long-running logs (large files)
- Archival (long-term storage)
- Bandwidth savings (uploading logs)

❌ **Not ideal for:**
- Logs you need to tail/watch in real-time
- Logs you'll grep frequently (use uncompressed)
- Very small files (compression overhead)

---

## 6. Configuration

### With Profiles

You can include these options in profiles:

```json
{
  "name": "ci-gzip",
  "description": "CI builds with compression",
  "pattern": "ERROR|FAILED",
  "options": {
    "gzip": true,
    "timeout": 600,
    "log_dir": "/var/log/ci"
  }
}
```

Then use:
```bash
ee --profile ci-gzip npm run build
```

---

## 7. Technical Details

### Append Mode

- Opens files in `'a'` mode instead of `'w'` mode
- Works with both auto-generated and custom filenames
- Indicator shown in output: "Logging to (appending):"

### Gzip Compression

- Uses Python's `gzip` module
- Compression level: 6 (balanced speed/size)
- Original files are removed after successful compression
- Compressed files have `.gz` extension
- Process: Write → Close → Compress → Delete original

### File Sizes

Typical compression ratios:

| Log Type | Original | Compressed | Ratio |
|----------|----------|------------|-------|
| npm test output | 45 KB | 5 KB | 89% |
| Terraform apply | 120 KB | 15 KB | 87% |
| Docker build | 850 KB | 95 KB | 89% |
| Python pytest | 67 KB | 8 KB | 88% |

---

## 8. FAQ

### Q: Can I append to a gzipped file?

A: No, gzip files can't be appended to. Choose either append mode OR gzip, not both.

### Q: How do I read gzipped logs?

A: Use `gunzip -c file.gz` or `zcat file.gz` (on Linux) or `zgrep` to search.

### Q: Does gzip slow down the command?

A: Compression happens AFTER the command completes, so it doesn't affect command execution time.

### Q: What if compression fails?

A: earlyexit will show a warning but the original log files remain. Compression is best-effort.

### Q: Can I change the compression level?

A: Not currently, but it's hardcoded to level 6 (good balance). Could be added as `--gzip-level` option.

---

## Summary

### Append Mode (`-a`)

✅ **tee-compatible** - Works like `tee -a`  
✅ **Cumulative logs** - Build up logs over multiple runs  
✅ **Clear indicator** - Shows "(appending)" in output  

### Gzip Compression (`-z`, `--gzip`)

✅ **Space savings** - 70-90% typical reduction  
✅ **Automatic** - Compress after command completes  
✅ **No slowdown** - Doesn't affect command execution  
✅ **Size reporting** - Shows compressed file sizes  

### Usage

```bash
# Append (like tee -a)
ee --file-prefix /tmp/test -a npm test

# Gzip (save space, like tar -z)
ee -z npm test

# Both features work with all other earlyexit options!
```

🎉 **Full `tee` compatibility + space savings!**


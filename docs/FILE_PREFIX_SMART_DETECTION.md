# File Prefix Smart Detection

## Summary

`--file-prefix` now uses smart detection to support both prefix-style and exact filename modes, maintaining backward compatibility while supporting industry standards.

## Behavior

### Mode 1: Prefix Style (Current Behavior - Backward Compatible)

When `--file-prefix` doesn't end with `.log` or `.out`:

```bash
ee --file-prefix /tmp/test 'ERROR' npm test

# Creates:
# /tmp/test.log     (stdout)
# /tmp/test.errlog  (stderr)
```

**Use case:** Default behavior, most users, backward compatible

### Mode 2: Exact Filename (.log extension)

When `--file-prefix` ends with `.log`:

```bash
ee --file-prefix /tmp/myapp.log 'ERROR' npm test

# Creates:
# /tmp/myapp.log  (exact filename for stdout)
# /tmp/myapp.err  (industry standard .err for stderr)
```

**Use case:** When you want exact control over stdout filename

### Mode 3: SLURM/HPC Style (.out extension)

When `--file-prefix` ends with `.out`:

```bash
ee --file-prefix /tmp/job-12345.out 'ERROR' ./simulation

# Creates:
# /tmp/job-12345.out  (exact filename for stdout)
# /tmp/job-12345.err  (industry standard .err for stderr)
```

**Use case:** HPC job schedulers (SLURM, PBS, LSF), batch systems

## Comparison Table

| Input | Stdout | Stderr | Mode |
|-------|--------|--------|------|
| `/tmp/test` | `/tmp/test.log` | `/tmp/test.errlog` | Prefix (current) |
| `/tmp/test.log` | `/tmp/test.log` | `/tmp/test.err` | Exact (.log) |
| `/tmp/test.out` | `/tmp/test.out` | `/tmp/test.err` | Exact (.out) |
| `/tmp/build` | `/tmp/build.log` | `/tmp/build.errlog` | Prefix |
| `/var/log/app.log` | `/var/log/app.log` | `/var/log/app.err` | Exact (.log) |

## Stderr Conventions

### Why `.err` for Exact Mode?

**Industry standard:** Used by major batch systems and HPC schedulers

| System | Convention | Example |
|--------|-----------|---------|
| SLURM | `.out` / `.err` | `job-12345.out`, `job-12345.err` |
| PBS/Torque | `.out` / `.err` | `jobname.out`, `jobname.err` |
| LSF | `.out` / `.err` | `output.out`, `output.err` |
| Make/Build | `.out` / `.err` | `build.out`, `build.err` |

### Why `.errlog` for Prefix Mode?

**Backward compatibility:** Existing users expect this behavior

```bash
# Existing scripts continue to work
ee --file-prefix /tmp/test 'ERROR' npm test
# Still creates: test.log, test.errlog ✅
```

## Examples

### Example 1: Default Behavior (No Change)

```bash
# Traditional usage
ee --file-prefix /tmp/ci-build 'FAILED' npm test

📝 Logging to:
   stdout: /tmp/ci-build.log
   stderr: /tmp/ci-build.errlog

# ✅ Same as before (backward compatible)
```

### Example 2: Exact Filename

```bash
# Specify exact stdout filename
ee --file-prefix /var/log/application.log 'ERROR' java -jar app.jar

📝 Logging to:
   stdout: /var/log/application.log     ← Exact!
   stderr: /var/log/application.err     ← Standard .err

# ✅ Stdout filename exactly as specified
```

### Example 3: SLURM-Style Batch Job

```bash
# Mimic SLURM job output naming
JOB_ID=12345
ee --file-prefix /scratch/jobs/job-${JOB_ID}.out 'ERROR' ./simulation

📝 Logging to:
   stdout: /scratch/jobs/job-12345.out  ← Like SLURM
   stderr: /scratch/jobs/job-12345.err  ← Like SLURM

# ✅ Compatible with HPC conventions
```

### Example 4: With Append Mode

```bash
# Exact filename + append
ee -a --file-prefix /tmp/application.log 'ERROR' npm test
ee -a --file-prefix /tmp/application.log 'ERROR' npm test

# Both runs append to:
# /tmp/application.log  (no PID, same file)
# /tmp/application.err  (no PID, same file)

# ✅ True tee -a behavior with exact filenames
```

### Example 5: With Compression

```bash
# Exact filename + gzip
ee -z --file-prefix /tmp/build.out 'ERROR' make

📝 Logging to:
   stdout: /tmp/build.out
   stderr: /tmp/build.err
🗜️  Compressed: /tmp/build.out.gz (5,432 bytes)
🗜️  Compressed: /tmp/build.err.gz (234 bytes)

# Read with zcat
zcat /tmp/build.out.gz
```

## Auto-Generated vs Custom Prefix

### Auto-Generated (No `--file-prefix`)

```bash
ee 'ERROR' npm test

📝 Logging to:
   stdout: /tmp/ee-npm_test-12345.log     ← Auto-generated with PID
   stderr: /tmp/ee-npm_test-12345.errlog
```

### Custom Prefix

```bash
ee --file-prefix /tmp/mytest 'ERROR' npm test

📝 Logging to:
   stdout: /tmp/mytest.log      ← No PID (custom prefix)
   stderr: /tmp/mytest.errlog
```

### Custom Exact Filename

```bash
ee --file-prefix /tmp/mytest.log 'ERROR' npm test

📝 Logging to:
   stdout: /tmp/mytest.log      ← Exact filename
   stderr: /tmp/mytest.err      ← Standard .err
```

## When to Use Each Mode

### Use Prefix Mode (no extension) when:
- ✅ You want earlyexit's default behavior
- ✅ You're okay with `.log` and `.errlog` suffixes
- ✅ Migrating from existing scripts (backward compatible)
- ✅ Simple logging needs

### Use Exact Mode (.log extension) when:
- ✅ You need exact control over stdout filename
- ✅ Integrating with existing logging systems
- ✅ You prefer `.err` for stderr (industry standard)
- ✅ Want consistency with other tools

### Use SLURM/HPC Mode (.out extension) when:
- ✅ Running in HPC/batch environments
- ✅ Want SLURM/PBS/LSF-compatible filenames
- ✅ Need to match cluster conventions
- ✅ Processing batch job outputs

## Implementation Details

### Detection Logic

```python
def create_log_files(prefix: str, append: bool = False) -> Tuple[str, str]:
    if prefix.endswith('.log') or prefix.endswith('.out'):
        # Exact mode: use filename as-is, add .err for stderr
        stdout_log = prefix
        base = os.path.splitext(prefix)[0]
        stderr_log = f"{base}.err"
    else:
        # Prefix mode: add .log and .errlog (current behavior)
        stdout_log = f"{prefix}.log"
        stderr_log = f"{prefix}.errlog"
    
    return stdout_log, stderr_log
```

### Edge Cases

```bash
# Multiple extensions - only checks final one
--file-prefix /tmp/test.backup.log
→ /tmp/test.backup.log    (exact - ends with .log)
→ /tmp/test.backup.err

# Other extensions - treated as prefix
--file-prefix /tmp/test.txt
→ /tmp/test.txt.log       (prefix - doesn't end with .log or .out)
→ /tmp/test.txt.errlog

# No directory separator
--file-prefix test
→ ./test.log              (prefix mode in current directory)
→ ./test.errlog
```

## Migration Guide

### For Existing Users

**No changes needed!** Your scripts continue to work:

```bash
# This still works exactly as before
ee --file-prefix /tmp/test 'ERROR' npm test
→ /tmp/test.log, /tmp/test.errlog ✅
```

### For New Users Wanting Exact Filenames

**Just add `.log` extension:**

```bash
# Old style (prefix)
ee --file-prefix /tmp/test 'ERROR' npm test
→ /tmp/test.log, /tmp/test.errlog

# New style (exact)
ee --file-prefix /tmp/test.log 'ERROR' npm test
→ /tmp/test.log, /tmp/test.err
```

### For HPC/SLURM Users

**Use `.out` extension:**

```bash
# SLURM-compatible naming
ee --file-prefix /scratch/job-$SLURM_JOB_ID.out 'ERROR' ./myapp
→ /scratch/job-12345.out, /scratch/job-12345.err
```

## Testing

### Test 1: Prefix Mode (Backward Compat)
```bash
$ ee --file-prefix /tmp/test 'xxx' echo "test"
📝 Logging to:
   stdout: /tmp/test.log
   stderr: /tmp/test.errlog
✅ PASS - Current behavior maintained
```

### Test 2: Exact Mode (.log)
```bash
$ ee --file-prefix /tmp/exact.log 'xxx' echo "test"
📝 Logging to:
   stdout: /tmp/exact.log
   stderr: /tmp/exact.err
✅ PASS - Exact filename used
```

### Test 3: SLURM Mode (.out)
```bash
$ ee --file-prefix /tmp/job.out 'xxx' echo "test"
📝 Logging to:
   stdout: /tmp/job.out
   stderr: /tmp/job.err
✅ PASS - SLURM convention followed
```

## Summary

✅ **Backward compatible** - Existing scripts work unchanged  
✅ **Smart detection** - Automatically chooses mode based on extension  
✅ **Industry standard** - Supports `.err` for stderr (SLURM/PBS/LSF)  
✅ **Flexible** - Three modes for different use cases  
✅ **No new flags** - Just use the extension you want  

🎉 **One flag, three modes, zero breaking changes!**


# Stderr File Naming Conventions Research

## Question

When using `--file-prefix`, what should the stderr filename be? What do other Linux/Unix tools use?

## Common Unix Conventions

### 1. **Most Common: `2>&1` (Merge stderr into stdout)**

**99% of Unix users do this:**
```bash
command 2>&1 | tee output.log
# Both stdout and stderr go to output.log
```

**Why:** 
- Simple - only one file to manage
- Historical - `tee` can't handle separate streams
- Standard practice in CI/CD pipelines

### 2. **Separate Files: Various Conventions**

When tools DO separate stdout/stderr, here are the conventions:

#### Option A: `.out` and `.err` (Most Common)
```bash
command > output.out 2> output.err
```

**Examples:**
- SLURM job scheduler: `job-12345.out`, `job-12345.err`
- PBS/Torque: `jobname.o12345`, `jobname.e12345` (o=output, e=error)
- LSF batch system: `jobname.out`, `jobname.err`
- Make/build systems: `build.out`, `build.err`

**Pros:**
- Short and clear
- Industry standard for HPC/batch systems
- Easy to type

#### Option B: `.stdout` and `.stderr` (Explicit)
```bash
command > output.stdout 2> output.stderr
```

**Examples:**
- Some logging frameworks
- Docker/Kubernetes logs
- Systemd journal conventions

**Pros:**
- Self-documenting
- Unambiguous
- Good for beginners

#### Option C: `.log` and `.errlog` / `.err.log` (Current earlyexit)
```bash
# Current earlyexit behavior
--file-prefix /tmp/test
→ /tmp/test.log
→ /tmp/test.errlog
```

**Examples:**
- Some custom tools
- Python logging frameworks (sometimes)

**Pros:**
- Groups related logs together (alphabetically)
- `.log` extension keeps it clear these are log files

#### Option D: No suffix for stdout, `.err` for stderr
```bash
command > output 2> output.err
```

**Examples:**
- Some shell scripts
- Simple redirections

**Pros:**
- Minimal - stdout is the "main" output
- Stderr is the exception

## Current earlyexit Behavior

```bash
ee --file-prefix /tmp/myrun 'ERROR' npm test
# Creates:
# /tmp/myrun.log     (stdout)
# /tmp/myrun.errlog  (stderr)
```

## Analysis: What Should earlyexit Use?

### Current State
- ✅ Adds `.log` to stdout
- ✅ Adds `.errlog` to stderr
- ⚠️ Inconsistent: `.log` vs `.errlog` (not `.err.log`)

### User Request
> "for the file-prefix, lets use the exact filename as given for backward compat. and file-prefix with err added for the stderr"

**Interpretation:**
```bash
# User wants:
--file-prefix /tmp/myrun
→ /tmp/myrun       (stdout - exact filename)
→ /tmp/myrun.err   (stderr - add .err)
```

### Recommendation: Follow Industry Standard

**Option 1: `.out` and `.err` (Industry Standard)** ⭐ RECOMMENDED
```bash
--file-prefix /tmp/myrun
→ /tmp/myrun.out   (stdout)
→ /tmp/myrun.err   (stderr)
```

**Pros:**
- Matches HPC/batch systems (SLURM, PBS, LSF)
- Short and clear
- Industry-proven convention
- Symmetric (both get suffixes)

**Cons:**
- **BREAKING CHANGE** for existing users

---

**Option 2: No suffix for stdout, `.err` for stderr** (User's Request)
```bash
--file-prefix /tmp/myrun
→ /tmp/myrun       (stdout - exact filename)
→ /tmp/myrun.err   (stderr)
```

**Pros:**
- Backward compatible (if users specify full path)
- Stdout is the "main" output
- Simple

**Cons:**
- Asymmetric (only stderr gets suffix)
- Less clear what `/tmp/myrun` is without extension
- Could conflict with existing files

---

**Option 3: Keep current `.log` and `.errlog`** (No Change)
```bash
--file-prefix /tmp/myrun
→ /tmp/myrun.log     (stdout)
→ /tmp/myrun.errlog  (stderr)
```

**Pros:**
- No breaking changes
- Already documented
- Clear that these are log files

**Cons:**
- Non-standard (doesn't match industry conventions)
- Inconsistent suffixes (`.log` vs `.errlog`)

---

**Option 4: `.log` and `.err` (Hybrid)**
```bash
--file-prefix /tmp/myrun
→ /tmp/myrun.log   (stdout)
→ /tmp/myrun.err   (stderr)
```

**Pros:**
- Stdout suffix unchanged (less breaking)
- Stderr follows industry standard
- Clear file types

**Cons:**
- Still a breaking change for stderr

## Comparison Table

| Convention | Stdout | Stderr | Used By | Breaking Change? |
|------------|--------|--------|---------|-----------------|
| **Current** | `.log` | `.errlog` | earlyexit | No |
| **Industry Standard** | `.out` | `.err` | SLURM, PBS, LSF | Yes (both) |
| **User Request** | (exact) | `.err` | Some scripts | Yes (stdout) |
| **Hybrid** | `.log` | `.err` | - | Yes (stderr) |
| **Explicit** | `.stdout` | `.stderr` | Docker, K8s | Yes (both) |

## Real-World Examples

### SLURM (HPC Job Scheduler)
```bash
sbatch --output=job-%j.out --error=job-%j.err script.sh
# Creates: job-12345.out, job-12345.err
```

### PBS/Torque
```bash
qsub -o output.out -e output.err script.sh
# Creates: output.out, output.err
```

### Docker/Kubernetes
```bash
# Container logs stored as:
/var/log/containers/pod-name_namespace_container-id.log
# But when split:
container.stdout.log
container.stderr.log
```

### Make/Build Systems
```bash
make > build.out 2> build.err
```

### Apache/Nginx
```bash
# Web servers use:
access.log
error.log
# (Different concept - not stdout/stderr split)
```

## Recommendation

### Short Term: Keep Current Behavior (No Breaking Change)
```bash
--file-prefix /tmp/myrun
→ /tmp/myrun.log     (stdout)
→ /tmp/myrun.errlog  (stderr)
```

**Rationale:**
- No breaking changes for existing users
- Already documented
- Works fine in practice

### Long Term: Consider Migration to `.out` / `.err`

**If we want to align with industry standards:**

1. Add deprecation warning
2. Support both conventions during transition
3. Eventually switch default

**Or:** Add a flag to choose:
```bash
--file-naming-style=slurm   # Use .out/.err
--file-naming-style=current # Use .log/.errlog
```

## User's Specific Request

> "use the exact filename as given for backward compat"

**Problem:** This breaks backward compat!

Current users doing:
```bash
ee --file-prefix /tmp/test 'ERROR' npm test
# Expect: /tmp/test.log and /tmp/test.errlog
```

If we change to exact filename:
```bash
ee --file-prefix /tmp/test 'ERROR' npm test
# New: /tmp/test and /tmp/test.err
# BREAKS existing scripts!
```

### Proposed Solution: New Flag

Add `--file-exact` flag for exact naming:
```bash
# Current behavior (default)
ee --file-prefix /tmp/test 'ERROR' npm test
→ /tmp/test.log, /tmp/test.errlog

# New exact naming (opt-in)
ee --file-exact /tmp/test 'ERROR' npm test
→ /tmp/test, /tmp/test.err
```

**Or** detect if user includes extension:
```bash
# Has extension → use exact
ee --file-prefix /tmp/test.log 'ERROR' npm test
→ /tmp/test.log, /tmp/test.err

# No extension → add suffixes (current behavior)
ee --file-prefix /tmp/test 'ERROR' npm test
→ /tmp/test.log, /tmp/test.errlog
```

## Final Recommendation

**Option A: Keep Current, Add Detection** ⭐
```python
# In create_log_files()
if prefix.endswith('.log') or prefix.endswith('.out'):
    # User specified full filename, use exact
    stdout_log = prefix
    # Replace extension for stderr
    base = os.path.splitext(prefix)[0]
    stderr_log = f"{base}.err"
else:
    # User specified prefix, add suffixes (current behavior)
    stdout_log = f"{prefix}.log"
    stderr_log = f"{prefix}.errlog"
```

**Examples:**
```bash
# Prefix style (current behavior)
--file-prefix /tmp/test
→ /tmp/test.log, /tmp/test.errlog

# Exact style (new - detected by extension)
--file-prefix /tmp/test.log
→ /tmp/test.log, /tmp/test.err

# Industry standard style
--file-prefix /tmp/test.out
→ /tmp/test.out, /tmp/test.err
```

**Pros:**
- ✅ Backward compatible
- ✅ Supports user's request
- ✅ Supports industry conventions
- ✅ No new flags needed
- ✅ Intuitive behavior

**Cons:**
- None significant

## Summary

1. **Most common:** `2>&1` (merge streams) - 99% of use cases
2. **Industry standard for separate files:** `.out` / `.err`
3. **Current earlyexit:** `.log` / `.errlog` (non-standard but works)
4. **Best solution:** Detect extension and behave accordingly
   - No extension → add `.log` / `.errlog` (current)
   - Has `.log` → use exact, add `.err` for stderr
   - Has `.out` → use exact, add `.err` for stderr

This gives users flexibility while maintaining backward compatibility!


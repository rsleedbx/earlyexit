# Auto-Logging Feature Design

## Overview

Add automatic log file creation to earlyexit, replacing the need for manual `| tee` commands.

---

## User Requirements

### Current Pattern (Manual)
```bash
cd /Users/robert.lee/github/mist && mist create --cloud gcp --db mysql --enable-replication --create-test-schema 2>&1 | tee /tmp/mysql_replication_create.log
```

### Desired Pattern 1: Default Behavior (Auto-Log Enabled)
```bash
cd /Users/robert.lee/github/mist && earlyexit mist create --cloud gcp --db mysql --enable-replication --create-test-schema

# Output:
📝 Logging to:
   stdout: /tmp/mist_create_gcp_mysql_20241112_143022.log
   stderr: /tmp/mist_create_gcp_mysql_20241112_143022.errlog

[command runs with output to screen AND files]
```

**Note:** Auto-logging is **enabled by default** in command mode!

### Desired Pattern 2: User-Specified Prefix
```bash
cd /Users/robert.lee/github/mist && earlyexit --file-prefix /tmp/mysql_replication_create mist create --cloud gcp --db mysql --enable-replication --create-test-schema

# Output:
📝 Logging to:
   stdout: /tmp/mysql_replication_create.log
   stderr: /tmp/mysql_replication_create.errlog

[command runs with output to screen AND files]
```

### With Quiet Mode (Suppress earlyexit Messages)
```bash
earlyexit -q mist create --cloud gcp --db mysql

# Output: (no earlyexit messages)
[command runs with output to screen AND files, but no "Logging to:" message]
```

### Disable Auto-Log
```bash
earlyexit -a mist create --cloud gcp --db mysql
# OR
earlyexit --no-auto-log mist create --cloud gcp --db mysql

# Output: (no logging, no messages)
[command runs with output to screen only, like traditional earlyexit]
```

---

## Implementation Design

### 1. Command-Line Arguments

**Added to cli.py:**
```python
parser.add_argument('-a', '--no-auto-log', action='store_true',
                   help='Disable automatic log file creation (auto-log is enabled by default)')
parser.add_argument('--file-prefix', metavar='PREFIX',
                   help='Save output to PREFIX.log and PREFIX.errlog')
parser.add_argument('--log-dir', metavar='DIR', default='/tmp',
                   help='Directory for auto-generated logs (default: /tmp)')
parser.add_argument('-q', '--quiet', action='store_true',
                   help='Quiet mode - suppress earlyexit messages (command output still shown)')
```

**Key change:** Auto-logging is **ON by default** in command mode. Use `-a` to disable.

### 2. Filename Generation Logic

**Implemented in `earlyexit/auto_logging.py`:**

```python
def generate_log_prefix(command: list, log_dir: str = '/tmp') -> str:
    """Generate intelligent log filename from command"""
    # Example inputs/outputs:
    # ['mist', 'create', '--cloud', 'gcp'] 
    #   -> '/tmp/mist_create_gcp_20241112_143022'
    # ['npm', 'test'] 
    #   -> '/tmp/npm_test_20241112_143022'
    # ['terraform', 'apply', '-auto-approve'] 
    #   -> '/tmp/terraform_apply_20241112_143022'
```

**Algorithm:**
1. Extract base command (first arg)
2. Look for subcommands and important flags (cloud, db, env, target, branch)
3. Sanitize for filesystem safety
4. Add timestamp for uniqueness
5. Limit to 4 parts max

### 3. Integration Points

**In `run_command_mode()` function:**

```python
# After argument parsing, before subprocess creation
from earlyexit.auto_logging import setup_auto_logging, TeeWriter

# Setup logging
stdout_log, stderr_log = setup_auto_logging(args, args.command, args.quiet)

if stdout_log and stderr_log:
    if not args.quiet:
        print(f"📝 Logging to:", file=sys.stderr)
        print(f"   stdout: {stdout_log}", file=sys.stderr)
        print(f"   stderr: {stderr_log}", file=sys.stderr)
        print(file=sys.stderr)
    
    # Open log files
    log_files = {
        'stdout': open(stdout_log, 'w', buffering=1),
        'stderr': open(stderr_log, 'w', buffering=1)
    }
else:
    log_files = None
```

**In the stream reading thread:**

```python
def reader_thread(stream, fd_num, label, pattern_to_use):
    for line in iter(stream.readline, b''):
        # ... existing pattern matching logic ...
        
        # NEW: Write to log file if enabled
        if log_files:
            if fd_num == 1:  # stdout
                log_files['stdout'].write(line_str)
                log_files['stdout'].flush()
            elif fd_num == 2:  # stderr
                log_files['stderr'].write(line_str)
                log_files['stderr'].flush()
        
        # ... existing output logic ...
```

---

## Behavior Matrix

| Flags | Command Output | earlyexit Messages | Log Files | Use Case |
|-------|----------------|-------------------|-----------|----------|
| (none) | ✅ | ✅ | ✅ | Default - auto-log ON |
| `-a` or `--no-auto-log` | ✅ | ✅ | ❌ | Disable logging |
| `-q` or `--quiet` | ✅ | ❌ | ✅ | Suppress earlyexit messages |
| `-a -q` | ✅ | ❌ | ❌ | No logging, no messages |
| `--file-prefix X` | ✅ | ✅ | ✅ | Custom files |
| `--file-prefix X -q` | ✅ | ❌ | ✅ | Custom files, no messages |

---

## Example Outputs

### Example 1: npm test (default - auto-log enabled)

```bash
$ earlyexit npm test

📝 Logging to:
   stdout: /tmp/npm_test_20241112_143022.log
   stderr: /tmp/npm_test_20241112_143022.errlog

> myapp@1.0.0 test
> jest

 FAIL  tests/auth.test.js
  ● User auth › login

    expect(received).toBe(expected)

❌ Error detected at 3.4s
   Captured 23 lines of error context
   Exit code: 0

$ ls /tmp/npm_test_*.log
/tmp/npm_test_20241112_143022.log
/tmp/npm_test_20241112_143022.errlog
```

### Example 2: Mist provision with custom prefix

```bash
$ earlyexit --file-prefix /tmp/mysql_replication_create mist create --cloud gcp --db mysql --enable-replication

📝 Logging to:
   stdout: /tmp/mysql_replication_create.log
   stderr: /tmp/mysql_replication_create.errlog

Validating configuration...
Creating VPC...
Provisioning Cloud SQL instance...
❌ Error: Invalid VPC configuration

Captured error at 2.1 minutes
Exit code: 0

$ cat /tmp/mysql_replication_create.errlog
Error: Invalid VPC configuration
SecurityGroupNotFound: sg-xyz123 not found in VPC vpc-abc789
```

### Example 3: CI/CD with quiet mode

```bash
$ earlyexit --file-prefix /var/log/ci/build_$BUILD_ID -q npm run build

# No earlyexit messages, but command output still shows
> myapp@1.0.0 build
> webpack --mode production

...webpack output...

$ echo $?
0

$ tail /var/log/ci/build_12345.log
Build completed successfully
```

### Example 4: Disable auto-log (traditional behavior)

```bash
$ earlyexit -a npm test

# No logging, no "Logging to:" message
# Just command output and earlyexit behavior

> myapp@1.0.0 test
> jest

 PASS  tests/auth.test.js

✓ All tests passed
```

---

## File Format

### .log file (stdout)
```
Validating configuration...
Creating VPC...
Configuring security groups...
Provisioning RDS instance...
```

### .errlog file (stderr)
```
Error: Invalid VPC configuration
SecurityGroupNotFound: sg-xyz123 not found in VPC vpc-abc789
Request ID: abc-123-def
```

---

## Edge Cases

### 1. Directory Doesn't Exist
```bash
$ earlyexit --file-prefix /nonexistent/dir/mylog npm test

❌ Error: Cannot create log directory: /nonexistent/dir
    Use an existing directory or check permissions
```

### 2. File Already Exists
- **Auto-log:** Uses timestamp, so unique every time
- **Custom prefix:** Overwrites existing files (standard behavior)

### 3. Permission Denied
```bash
$ earlyexit --file-prefix /root/mylog npm test

❌ Error: Permission denied: /root/mylog.log
    Choose a writable directory
```

### 4. Disk Full
- Fails gracefully
- Shows error but continues command execution
- Files may be truncated

---

## Implementation Status

✅ **Done:**
- Command-line arguments added
- `auto_logging.py` module created
- Filename generation logic implemented
- TeeWriter class for dual output

🚧 **TODO:**
- Integrate into `run_command_mode()` function
- Add log file opening/closing
- Wire up to stream readers
- Add error handling
- Test with various commands
- Update documentation

---

## Testing Plan

### Unit Tests

```python
def test_generate_log_prefix():
    assert 'mist_create_gcp' in generate_log_prefix(
        ['mist', 'create', '--cloud', 'gcp'])
    assert 'npm_test' in generate_log_prefix(['npm', 'test'])
```

### Integration Tests

```bash
# Test auto-log
earlyexit --auto-log echo "test" 
# Verify files created in /tmp/

# Test custom prefix
earlyexit --file-prefix /tmp/mytest echo "test"
# Verify /tmp/mytest.log exists

# Test quiet mode
earlyexit --file-prefix /tmp/quiet --quiet echo "test"
# Verify no screen output but file exists
```

---

## Documentation Updates Needed

1. **README.md** - Add examples of --auto-log and --file-prefix
2. **Profile format** - Add auto_log and file_prefix to options
3. **Tutorial** - Show log file usage in Mist example
4. **Blog post** - Mention as alternative to `| tee`

---

## Benefits

### For Users
- ✅ Shorter commands (no `| tee`)
- ✅ Automatic filename generation
- ✅ Separate stdout/stderr logs
- ✅ Works with all earlyexit features
- ✅ Easy to find logs (predictable names)

### For CI/CD
- ✅ Programmatic log file naming
- ✅ Quiet mode for cleaner CI output
- ✅ Preserved logs even after early exit
- ✅ Easier debugging (separate error logs)

### For Development
- ✅ Quick iteration with logged history
- ✅ Compare runs easily (timestamped)
- ✅ Grep through logs post-run
- ✅ Share logs with team

---

## Comparison with `tee`

| Feature | `cmd 2>&1 \| tee log` | `earlyexit --auto-log cmd` |
|---------|---------------------|--------------------------|
| **Command length** | Long | Short |
| **Stdout/stderr separate** | ❌ | ✅ |
| **Auto filename** | ❌ | ✅ |
| **Works with early exit** | ⚠️ Partial | ✅ Full |
| **Quiet mode** | ❌ | ✅ |
| **Profile support** | ❌ | ✅ |

---

## Next Steps

1. Complete integration in `run_command_mode()`
2. Add tests
3. Update documentation
4. Add to profiles (optional field)
5. Release in next version

---

**Status:** Design complete, partial implementation done, integration pending.


# Auto-Logging Quick Reference

## TL;DR

**Auto-logging is ON by default** in command mode. Your command output is saved to timestamped files in `/tmp/`.

**Pro tip:** Use the short alias `ee` instead of `earlyexit` for 37% less typing!
```bash
ee npm test    # Same as: earlyexit npm test
```

---

## Default Behavior (No Flags)

```bash
$ earlyexit mist create --cloud gcp --db mysql
# OR use short alias:
$ ee mist create --cloud gcp --db mysql

📝 Logging to:
   stdout: /tmp/mist_create_gcp_mysql_20241112_143530.log
   stderr: /tmp/mist_create_gcp_mysql_20241112_143530.errlog

[command runs, output to screen AND files]
```

---

## Common Scenarios

### Scenario 1: Default (Auto-Log ON)
```bash
earlyexit mist create --cloud gcp --db mysql
```
- ✅ Shows command output on screen
- ✅ Shows "Logging to:" message
- ✅ Saves to auto-generated files

### Scenario 2: Quiet Mode (Suppress earlyexit Messages)
```bash
earlyexit -q mist create --cloud gcp --db mysql
```
- ✅ Shows command output on screen
- ❌ Hides "Logging to:" message
- ✅ Saves to auto-generated files

### Scenario 3: Custom Filename
```bash
earlyexit --file-prefix /tmp/mysql_replication_create mist create --cloud gcp --db mysql
```
- ✅ Shows command output on screen
- ✅ Shows "Logging to:" message
- ✅ Saves to /tmp/mysql_replication_create.log and .errlog

### Scenario 4: Disable Auto-Log
```bash
earlyexit -a mist create --cloud gcp --db mysql
# OR
earlyexit --no-auto-log mist create --cloud gcp --db mysql
```
- ✅ Shows command output on screen
- ❌ No "Logging to:" message
- ❌ No log files created

### Scenario 5: Disable Auto-Log + Quiet
```bash
earlyexit -a -q mist create --cloud gcp --db mysql
```
- ✅ Shows command output on screen
- ❌ No earlyexit messages at all
- ❌ No log files created
- (Like traditional earlyexit behavior)

---

## Flag Quick Reference

| Flag | Purpose | Default |
|------|---------|---------|
| `-a` or `--no-auto-log` | Disable auto-logging | OFF (logging enabled) |
| `-q` or `--quiet` | Suppress earlyexit messages | OFF (messages shown) |
| `--file-prefix /path/to/file` | Custom log file prefix | (auto-generated) |
| `--log-dir /path/to/dir` | Directory for auto-logs | `/tmp` |

---

## Comparison with Old Behavior

### Old Way (Manual)
```bash
cd /Users/robert.lee/github/mist && \
  mist create --cloud gcp --db mysql 2>&1 | tee /tmp/mysql_replication_create.log
```

### New Way (Automatic)
```bash
cd /Users/robert.lee/github/mist && \
  earlyexit mist create --cloud gcp --db mysql

# Files automatically saved with intelligent naming:
# /tmp/mist_create_gcp_mysql_20241112_143530.log
# /tmp/mist_create_gcp_mysql_20241112_143530.errlog
```

**Benefits:**
- ✅ Shorter command
- ✅ Automatic filename generation
- ✅ Separate stdout/stderr logs
- ✅ Timestamp included
- ✅ Works with all earlyexit features

---

## Filename Generation Logic

The auto-generated filename includes:
1. **Base command** (e.g., `mist`)
2. **Subcommand** (e.g., `create`)
3. **Important flags** (e.g., `gcp`, `mysql`)
4. **Timestamp** (e.g., `20241112_143530`)

### Examples

| Command | Generated Filename |
|---------|-------------------|
| `mist create --cloud gcp` | `mist_create_gcp_YYYYMMDD_HHMMSS.log` |
| `npm test` | `npm_test_YYYYMMDD_HHMMSS.log` |
| `terraform apply` | `terraform_apply_YYYYMMDD_HHMMSS.log` |
| `pytest -v` | `pytest_YYYYMMDD_HHMMSS.log` |
| `docker build -t myapp` | `docker_build_YYYYMMDD_HHMMSS.log` |

---

## File Locations

### Default Location
```
/tmp/
├── mist_create_gcp_mysql_20241112_143530.log
├── mist_create_gcp_mysql_20241112_143530.errlog
├── npm_test_20241112_144020.log
├── npm_test_20241112_144020.errlog
└── ...
```

### Custom Directory
```bash
earlyexit --log-dir /var/log/myapp mist create --cloud gcp
```

Files saved to:
```
/var/log/myapp/
├── mist_create_gcp_20241112_143530.log
└── mist_create_gcp_mysql_20241112_143530.errlog
```

### Custom Prefix
```bash
earlyexit --file-prefix /var/log/myapp/deploy mist create --cloud gcp
```

Files saved to:
```
/var/log/myapp/
├── deploy.log
└── deploy.errlog
```

---

## Pipe Mode (stdin) Behavior

Auto-logging is **OFF by default** in pipe mode (when reading from stdin).

```bash
# This does NOT create log files (pipe mode)
some_command | earlyexit 'ERROR'

# To enable logging in pipe mode, use --file-prefix
some_command | earlyexit --file-prefix /tmp/mylog 'ERROR'
```

**Why?** Pipe mode is typically used in existing pipelines where users already control logging with `tee` or redirection.

---

## FAQs

### Q: Can I disable auto-logging permanently?

A: Add an alias to your shell config:

```bash
# ~/.bashrc or ~/.zshrc
alias earlyexit='earlyexit --no-auto-log'
```

### Q: Where are my log files?

A: By default in `/tmp/`. Look for files matching your command name:

```bash
ls -lt /tmp/mist_*.log | head -5
ls -lt /tmp/npm_*.log | head -5
```

### Q: Can I change the default directory?

A: Yes, use `--log-dir`:

```bash
earlyexit --log-dir ~/logs mist create --cloud gcp
```

Or create an alias:

```bash
alias earlyexit='earlyexit --log-dir ~/logs'
```

### Q: Do log files get cleaned up automatically?

A: No. `/tmp/` is typically cleaned on reboot, but you may want to periodically clean old logs:

```bash
# Delete logs older than 7 days
find /tmp -name "mist_*.log" -mtime +7 -delete
find /tmp -name "npm_*.log" -mtime +7 -delete
```

### Q: Does auto-logging work with profiles?

A: Yes! Profiles can include `no_auto_log` option:

```json
{
  "name": "mist-no-log",
  "pattern": "Error:",
  "options": {
    "no_auto_log": true
  }
}
```

---

## Summary

**Before (manual):**
```bash
cmd 2>&1 | tee /tmp/logfile.log
```

**After (automatic):**
```bash
earlyexit cmd
```

**Disable if needed:**
```bash
earlyexit -a cmd
```

**That's it!** Auto-logging makes earlyexit work like `tee` is built in. 🎉


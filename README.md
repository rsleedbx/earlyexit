# earlyexit 🚀

**Early exit pattern matching for command output** - Exit immediately when a pattern is matched, with timeout support.

Implements the **early error detection pattern** for faster feedback during long-running commands, CI/CD pipelines, and log monitoring.

## 🎯 Purpose

Traditional `grep` processes the entire input stream. `earlyexit` exits **immediately** on the first match, saving time and providing instant feedback for errors.

Perfect for:
- 🔧 Long-running build processes
- 🧪 Test suites
- 🚀 Deployment pipelines
- 📊 Log monitoring
- ⏱️ Time-sensitive operations

## 📦 Installation

```bash
# Install from PyPI (when published)
pip install earlyexit

# Install from source
git clone https://github.com/rsleedbx/earlyexit
cd earlyexit
pip install -e .

# With Perl-compatible regex support
pip install -e ".[perl]"
```

## 🚀 Quick Start

```bash
# Exit immediately on first error (with 30s timeout)
long_running_command | earlyexit -t 30 'Error|Failed'

# Monitor Terraform apply
terraform apply | earlyexit -t 600 -i 'error'

# Stop after 3 test failures
pytest | earlyexit -m 3 'FAILED'

# Check if service is healthy (invert match)
health_check_loop | earlyexit -v 'OK' -t 10
```

## 📚 Usage

```
earlyexit [OPTIONS] PATTERN

Arguments:
  PATTERN                Regular expression pattern to match

Options:
  -t, --timeout SECONDS  Timeout in seconds (default: no timeout)
  -m, --max-count NUM    Stop after NUM matches (default: 1)
  -i, --ignore-case      Case-insensitive matching
  -E, --extended-regexp  Extended regex (Python re module, default)
  -P, --perl-regexp      Perl-compatible regex (requires regex module)
  -v, --invert-match     Invert match - select non-matching lines
  -q, --quiet            Quiet mode - suppress output, only exit code
  -n, --line-number      Prefix output with line number
  --color WHEN           Colorize output: always, auto (default), never
  --version              Show version
  -h, --help             Show help message

Exit Codes:
  0 - Pattern matched (error detected)
  1 - No match found (success)
  2 - Timeout exceeded
  3 - Other error
```

## 💡 Examples

### Example 1: Terraform Operations

```bash
# Exit immediately on error, 10min timeout
terraform apply -auto-approve 2>&1 | \
  stdbuf -o0 tee terraform.log | \
  earlyexit -t 600 -i 'error'

if [ $? -eq 0 ]; then
  echo "❌ Terraform failed - check terraform.log"
  exit 1
elif [ $? -eq 2 ]; then
  echo "⏱️  Terraform timed out after 10 minutes"
  exit 2
else
  echo "✅ Terraform completed successfully"
fi
```

### Example 2: Database Provisioning

```bash
# Monitor database creation, fail fast on errors
vapordb create --cloud aws --db mysql 2>&1 | \
  tee /tmp/db_create.log | \
  earlyexit -t 1800 'Error|Failed|Exception'

case $? in
  0) echo "❌ Database creation failed"; exit 1 ;;
  1) echo "✅ Database created successfully" ;;
  2) echo "⏱️  Creation timed out after 30 minutes"; exit 2 ;;
esac
```

### Example 3: Test Suite Monitoring

```bash
# Stop after 5 test failures
pytest -v | earlyexit -m 5 'FAILED'

if [ $? -eq 0 ]; then
  echo "❌ Tests failed - stopping early"
  exit 1
fi
```

### Example 4: CI/CD Pipeline

```bash
# Monitor build output for errors
./build.sh 2>&1 | \
  stdbuf -o0 tee build.log | \
  earlyexit -t 3600 -iE '(error|fatal|exception)'

exit $?  # Propagate exit code
```

### Example 5: Log Monitoring

```bash
# Monitor application logs in real-time
tail -f /var/log/app.log | \
  earlyexit -t 300 -i 'error|exception|fatal'

if [ $? -eq 0 ]; then
  echo "🚨 Error detected in logs!"
  # Send alert, trigger remediation, etc.
fi
```

### Example 6: Health Check

```bash
# Ensure service stays healthy for 60 seconds
# Exit if "OK" stops appearing (invert match)
while true; do
  curl -s http://localhost:8080/health
  sleep 1
done | earlyexit -v 'OK' -t 60

if [ $? -eq 0 ]; then
  echo "❌ Health check failed - 'OK' not found"
  exit 1
fi
```

### Example 7: Multiple Patterns

```bash
# Match any of several error conditions
app_command | earlyexit -E '(ERROR|FATAL|EXCEPTION|SEGFAULT|PANIC)'
```

### Example 8: With Line Numbers

```bash
# Show line numbers for matched errors
long_log_file | earlyexit -n -i 'error'
# Output: 1234:ERROR: Connection failed
```

## 🔍 Pattern Syntax

### Extended Regex (-E, default)

Uses Python's `re` module (similar to `grep -E`):

```bash
# Multiple alternatives
earlyexit 'error|warning|fatal'

# Character classes
earlyexit '[Ee]rror'

# Quantifiers
earlyexit 'fail(ed|ure)?'

# Word boundaries
earlyexit '\berror\b'
```

### Perl-Compatible Regex (-P)

Requires `regex` module (`pip install earlyexit[perl]`):

```bash
# Lookaheads/lookbehinds
earlyexit -P '(?<=ERROR: ).*'

# Named groups
earlyexit -P '(?P<level>ERROR|WARN): (?P<msg>.*)'

# Recursive patterns
earlyexit -P '\(((?:[^()]++|(?R))*+)\)'
```

## 🎯 Use Cases

### 1. **Fast Feedback in CI/CD**

Stop the build immediately on first error instead of waiting for full completion:

```yaml
# GitLab CI example
script:
  - make build 2>&1 | earlyexit -t 3600 'error' || exit 1
```

### 2. **Cost Optimization**

Save compute costs by stopping failed cloud operations early:

```bash
# Stop provisioning if errors detected in first 5 minutes
terraform apply | earlyexit -t 300 'Error:' && terraform destroy -auto-approve
```

### 3. **Development Workflow**

Get instant feedback during development:

```bash
# Watch for compilation errors
npm run watch | earlyexit 'ERROR'
```

### 4. **Monitoring & Alerting**

Detect issues in production logs:

```bash
# Alert on first critical error
kubectl logs -f pod-name | earlyexit 'CRITICAL' && send-alert
```

## ⚡ Performance Comparison

| Tool | Behavior | Time to Detect Error |
|------|----------|---------------------|
| `grep` | Processes entire input | After full completion |
| `grep -m 1` | Stops after first match | Immediate (but no timeout) |
| **`earlyexit`** | Stops after first match + timeout | **Immediate + safety net** |

### Real-World Example

```bash
# Command that takes 30 minutes but fails at 5 minutes

# grep: Waits full 30 minutes
command | grep 'Error'  # 30 minutes wasted

# earlyexit: Exits at 5 minutes
command | earlyexit -t 1800 'Error'  # Saves 25 minutes!
```

## 🔧 Integration with Other Tools

### With `tee` (save logs + monitor)

```bash
command 2>&1 | stdbuf -o0 tee output.log | earlyexit -t 300 'Error'
```

### With `timeout` (double safety)

```bash
timeout 600 bash << 'EOF'
  command 2>&1 | stdbuf -o0 tee log.txt | earlyexit -t 300 'Error'
EOF
```

### With `stdbuf` (unbuffered output)

```bash
command 2>&1 | stdbuf -o0 tee log.txt | earlyexit 'Error'
```

## 🧪 Testing

```bash
# Test success (no match)
echo "Starting..." | earlyexit 'Error'  # Exit 1

# Test match (immediate exit)
echo "Error detected" | earlyexit 'Error'  # Exit 0

# Test timeout
sleep 10 | earlyexit -t 2 'Error'  # Exit 2 after 2 seconds

# Test case-insensitive
echo "ERROR" | earlyexit -i 'error'  # Exit 0

# Test max count
printf "Error\nError\nError\n" | earlyexit -m 2 'Error'  # Exit 0 after 2 matches

# Test invert match
echo "OK" | earlyexit -v 'Error'  # Exit 1 (OK is not Error)
echo "Error" | earlyexit -v 'OK'  # Exit 0 (Error doesn't match OK)
```

## 📊 Exit Codes

| Exit Code | Meaning | Use Case |
|-----------|---------|----------|
| **0** | Pattern matched | Error detected - fail fast |
| **1** | No match | Success - continue |
| **2** | Timeout | Command took too long |
| **3** | Error | Invalid pattern, broken pipe, etc. |
| **130** | Interrupted | Ctrl+C pressed |

## 🔄 Comparison with grep

| Feature | grep | grep -m 1 | **earlyexit** |
|---------|------|-----------|--------------|
| Pattern matching | ✅ | ✅ | ✅ |
| Extended regex | ✅ -E | ✅ -E | ✅ -E |
| Perl regex | ✅ -P | ✅ -P | ✅ -P (with regex module) |
| Stop on first match | ❌ | ✅ | ✅ |
| Timeout | ❌ | ❌ | ✅ -t |
| Exit code clarity | ⚠️ Complex | ⚠️ Complex | ✅ Simple (0/1/2/3) |
| Max count | ❌ | ✅ -m | ✅ -m |
| Invert match | ✅ -v | ✅ -v | ✅ -v |
| Color output | ✅ | ✅ | ✅ --color |
| Line numbers | ✅ -n | ✅ -n | ✅ -n |

## 🐛 Troubleshooting

### Pattern not matching?

```bash
# Test your pattern separately
echo "test string" | earlyexit 'pattern'

# Enable line numbers to see what's being processed
command | earlyexit -n 'pattern'

# Use -i for case-insensitive if needed
command | earlyexit -i 'pattern'
```

### Timeout not working?

```bash
# Ensure timeout is numeric
earlyexit -t 10 'pattern'  # ✅ Correct
earlyexit -t 10s 'pattern'  # ❌ Wrong - no 's' suffix
```

### Buffering issues?

```bash
# Use stdbuf to disable buffering
command 2>&1 | stdbuf -o0 tee log.txt | earlyexit 'pattern'
```

## 🎓 Best Practices

1. **Always use timeout** for long-running commands:
   ```bash
   command | earlyexit -t 600 'Error'  # ✅ Good
   command | earlyexit 'Error'          # ⚠️ Risky - no timeout
   ```

2. **Save logs with tee**:
   ```bash
   command 2>&1 | stdbuf -o0 tee log.txt | earlyexit -t 300 'Error'
   ```

3. **Use case-insensitive** for error detection:
   ```bash
   earlyexit -i 'error'  # Matches Error, ERROR, error
   ```

4. **Multiple patterns** with extended regex:
   ```bash
   earlyexit -E '(error|warning|fatal|exception)'
   ```

5. **Check exit codes** properly:
   ```bash
   command | earlyexit 'Error'
   case $? in
     0) echo "Error detected"; exit 1 ;;
     1) echo "Success" ;;
     2) echo "Timeout"; exit 2 ;;
     *) echo "Unexpected error"; exit 3 ;;
   esac
   ```

## 📝 License

MIT License - see LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please open an issue or PR on GitHub.

## 🔗 Related Projects

- **timeout** - Command timeout utility (part of GNU coreutils)
- **stdbuf** - Modify buffering of streams (part of GNU coreutils)
- **ripgrep (rg)** - Fast grep alternative in Rust

## 📮 Contact

Robert Lee - robert.lee@databricks.com

---

**Made with ❤️ for developers who value fast feedback**


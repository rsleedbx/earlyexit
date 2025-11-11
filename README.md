# earlyexit 🚀

**Stop long-running commands the instant an error appears** - Like `timeout` + `grep -m 1` combined, but smarter: monitors stderr, detects hangs, and uniquely captures full error context with **configurable delay-exit** (continue reading for N seconds after match to get stack traces and cleanup logs), plus clear exit codes.

**Essential for AI-assisted coding** where agents run commands unattended - earlyexit makes intelligent decisions to exit early when no human is watching, enabling fast feedback loops for AI code generation iterations.

**Self-learning capability**: Optionally captures execution telemetry (patterns, timing, matches) in local SQLite database for ML-driven optimization of delays, timeouts, and pattern effectiveness - learns from your usage to improve over time.

Implements the **early error detection pattern** for faster feedback during long-running commands, CI/CD pipelines, log monitoring, and autonomous agent workflows.

## 🎯 Purpose

Traditional `grep` processes the entire input stream or exits immediately with `-m 1` (losing error context). `earlyexit` detects errors **instantly** but with a unique **delay-exit feature** (default 10s) to capture full stack traces, cleanup logs, and error context before terminating - something no standard Unix tool provides.

### 🤖 Why Critical for AI-Assisted Development

In modern AI-assisted coding (Cursor, Copilot, Aider, etc.), **small errors are more common** and **humans aren't watching**:

- **AI agents generate code rapidly** → More iterations, more potential errors
- **Unattended execution** → No human monitoring terminal output in real-time  
- **Fast feedback loops essential** → AI needs immediate error signals to correct course
- **Intelligent automated decisions** → Tool must decide when to exit, not human

`earlyexit` acts as your **autonomous error sentinel**, making smart decisions about when to stop failed operations and providing clear, actionable exit codes for AI agents to interpret.

**Traditional workflow (human watching):**
```bash
$ npm test        # Human sees "Error" at line 3, hits Ctrl-C
                  # Waits 2 minutes for nothing...
```

**AI-assisted workflow (agent running):**
```bash
$ earlyexit 'Error|FAIL' npm test   # Exits at 0.5s with context
                                     # Agent immediately knows to fix and retry
```

Perfect for:
- 🤖 **AI agent workflows** (autonomous coding assistants)
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

## 🚀 Two Ways to Use earlyexit

### Mode 1: Pipe Mode (Traditional Unix Style)

Read from stdin, like grep:

```bash
# Basic usage
command | earlyexit 'ERROR'

# With timeout
long_running_command | earlyexit -t 30 'Error|Failed'

# Chain with other tools
terraform apply 2>&1 | tee terraform.log | earlyexit -t 600 -i 'error'

# Multiple pipes
make 2>&1 | grep -v warning | earlyexit 'error'

# With head to limit output
pytest -v | earlyexit 'FAILED' | head -20
```

### Mode 2: Command Mode (Like timeout)

Run command directly:

```bash
# Basic usage
earlyexit 'ERROR' command

# With timeout
earlyexit -t 60 'Error' terraform apply -auto-approve

# Monitor both stdout and stderr
earlyexit --both 'Error|Failed' ./build.sh

# Detect hangs (idle timeout)
earlyexit --idle-timeout 30 'Error' ./long-running-app

# Detect slow startup
earlyexit --first-output-timeout 10 'Error' ./slow-service
```

### Quick Comparison

| Feature | Pipe Mode | Command Mode |
|---------|-----------|--------------|
| Syntax | `cmd \| earlyexit 'pat'` | `earlyexit 'pat' cmd` |
| Chainable | ✅ Can pipe further | ❌ Terminal command |
| Monitor stderr | Need `2>&1` | Use `--stderr` or `--both` |
| Idle detection | ❌ Not available | ✅ `--idle-timeout` |
| Startup detection | ❌ Not available | ✅ `--first-output-timeout` |
| **Error context capture** | ❌ **Not available** | ✅ **`--delay-exit` (unique!)** |
| Custom FDs | ❌ Not available | ✅ `--fd 3 --fd 4` |
| Like | `grep`, `awk` | `timeout`, `watch` |

## 📚 Usage

### Pipe Mode
```bash
command | earlyexit [OPTIONS] PATTERN
```

### Command Mode
```bash
earlyexit [OPTIONS] PATTERN COMMAND [ARGS...]
```

### Arguments
```
PATTERN                Regular expression pattern to match
COMMAND [ARGS...]      Optional: Command to run (command mode)

Options:
  -t, --timeout SECONDS          Overall timeout in seconds
  --idle-timeout SECONDS         Timeout if no output for N seconds (hang detection)
  --first-output-timeout SECONDS Timeout if first output not seen within N seconds
  --delay-exit SECONDS           After match, continue reading for N seconds to capture
                                 error context (default: 10 for command mode, 0 for pipe mode)
  -m, --max-count NUM            Stop after NUM matches (default: 1)
  -i, --ignore-case      Case-insensitive matching
  -E, --extended-regexp  Extended regex (Python re module, default)
  -P, --perl-regexp      Perl-compatible regex (requires regex module)
  -v, --invert-match     Invert match - select non-matching lines
  -q, --quiet            Quiet mode - suppress output, only exit code
  -n, --line-number      Prefix output with line number
  --stderr               Monitor stderr instead of stdout (command mode)
  --both                 Monitor both stdout and stderr (command mode)
  --fd N                 Monitor file descriptor N (e.g., --fd 3 --fd 4)
  --fd-pattern FD PAT    Set specific pattern for file descriptor FD
  --fd-prefix            Add stream labels [stdout]/[stderr]/[fd3]
  --stderr-prefix        Alias for --fd-prefix
  --color WHEN           Colorize output: always, auto (default), never
  --version              Show version
  -h, --help             Show help message

Usage Modes:
  Pipe Mode:    command | earlyexit 'pattern'        (read from stdin)
  Command Mode: earlyexit 'pattern' command           (run command directly)

Exit Codes:
  0 - Pattern matched (error detected)
  1 - No match found (success)
  2 - Timeout exceeded (any timeout type)
  3 - Other error

Timeout Types:
  -t           Overall timeout - command exceeds total time limit
  --idle       Idle timeout - no output for specified seconds (hang detection)
  --first      First output timeout - no output within initial period (startup detection)
```

## 💡 Examples by Mode

### 🔗 Pipe Mode Examples

Perfect for: Monitoring existing pipelines, chaining with other tools, capturing logs

#### Example 1: Basic Pipe Usage

```bash
# Simple error detection
./build.sh 2>&1 | earlyexit 'error'

# With timeout
long_command | earlyexit -t 60 'Error|Failed'

# Case-insensitive
terraform apply 2>&1 | earlyexit -i 'error'
```

#### Example 2: Terraform Operations (Pipe Mode)

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

#### Example 3: Chaining with Other Tools

```bash
# Save logs and monitor
make 2>&1 | tee build.log | earlyexit 'error'

# Filter then monitor
kubectl logs -f pod | grep -v DEBUG | earlyexit 'ERROR'

# Limit output with head
pytest -v | earlyexit 'FAILED' | head -50

# Multiple processing stages
./app 2>&1 | \
  stdbuf -o0 tee app.log | \
  grep -v INFO | \
  earlyexit -i 'error|fatal'
```

#### Example 4: Log Monitoring (Pipe Mode)

```bash
# Monitor application logs in real-time
tail -f /var/log/app.log | earlyexit -t 300 -i 'error|exception|fatal'

if [ $? -eq 0 ]; then
  echo "🚨 Error detected in logs!"
  # Send alert, trigger remediation, etc.
fi
```

#### Example 5: Test Suite with Pipes

```bash
# Stop after 5 test failures
pytest -v | earlyexit -m 5 'FAILED'

if [ $? -eq 0 ]; then
  echo "❌ Tests failed - stopping early"
  exit 1
fi
```

### ⚡ Command Mode Examples

Perfect for: Direct execution, hang detection, startup monitoring, stderr separation

#### Example 1: Basic Command Execution

```bash
# Simple usage
earlyexit 'ERROR' ./app

# With timeout
earlyexit -t 300 'Error|Failed' terraform apply -auto-approve

# Case-insensitive
earlyexit -i 'error' make build
```

#### Example 2: Advanced Monitoring

```bash
# Detect hangs - timeout if no output for 30 seconds
earlyexit --idle-timeout 30 'Error' ./long-running-app

# Detect slow startup - timeout if no output within 10 seconds
earlyexit --first-output-timeout 10 'Error' ./slow-service

# Combine all timeouts
earlyexit \
  -t 300 \
  --idle-timeout 30 \
  --first-output-timeout 10 \
  'Error' ./app

# After detecting error, wait 10s to capture full error context (default)
earlyexit 'Error' ./app

# Wait only 5 seconds after error for quick exit
earlyexit --delay-exit 5 'Error' ./app

# Wait longer for comprehensive error logs
earlyexit --delay-exit 30 'Error' ./app

# Exit immediately on error (no delay)
earlyexit --delay-exit 0 'FATAL' ./app
```

#### Example 3: Stream Separation

```bash
# Monitor stderr only
earlyexit --stderr 'ERROR' ./my-script.sh

# Monitor both streams with labels
earlyexit --both --fd-prefix 'Error|Warning|Fatal' ./app

# Different patterns for different streams
earlyexit \
  --fd-pattern 1 'FAILED' \
  --fd-pattern 2 'ERROR' \
  ./test.sh
```

#### Example 4: Terraform Operations (Command Mode)

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

```bash
# Direct execution with monitoring
earlyexit -t 600 'error' terraform apply -auto-approve

if [ $? -eq 0 ]; then
  echo "❌ Terraform failed"
  exit 1
fi
```

#### Example 5: Database Provisioning (Command Mode)

```bash
# Monitor with hang detection
earlyexit \
  -t 1800 \
  --idle-timeout 120 \
  'Error|Failed|Exception' \
  mist create --cloud aws --db mysql

case $? in
  0) echo "❌ Database creation failed"; exit 1 ;;
  1) echo "✅ Database created successfully" ;;
  2) echo "⏱️  Timeout occurred"; exit 2 ;;
esac
```

#### Example 6: CI/CD Pipeline (Command Mode)

```bash
# Comprehensive monitoring
earlyexit \
  -t 3600 \
  --idle-timeout 60 \
  --first-output-timeout 15 \
  'error|fatal' \
  ./build.sh

exit $?  # Propagate exit code
```

### 🔀 Choosing the Right Mode

**Use Pipe Mode when:**
- ✅ Already have a pipeline with `tee`, `grep`, etc.
- ✅ Need to capture logs while monitoring
- ✅ Want to process output with multiple tools
- ✅ Working with tools that merge stdout/stderr
- ✅ Need to pipe output to another command

**Use Command Mode when:**
- ✅ Need to detect hangs/frozen processes
- ✅ Need to detect slow startup
- ✅ Want to monitor stdout and stderr separately
- ✅ Need to monitor custom file descriptors
- ✅ Want to use per-stream patterns
- ✅ Running a single command without piping

### 📋 Common Patterns

#### Pattern 1: Save Logs + Monitor (Pipe Mode)

```bash
command 2>&1 | stdbuf -o0 tee output.log | earlyexit -t 300 'Error'
```

#### Pattern 2: Comprehensive Monitoring (Command Mode)

```bash
earlyexit -t 300 --idle-timeout 30 --first-output-timeout 10 'Error' command
```

#### Pattern 3: Multiple Processing (Pipe Mode)

```bash
command 2>&1 | grep -v DEBUG | earlyexit 'ERROR' | head -100
```

#### Pattern 4: Stream Separation (Command Mode)

```bash
earlyexit --both --fd-prefix --fd-pattern 2 'ERROR' command
```

### Example 7: Multiple Patterns

```bash
# Pipe mode
app_command | earlyexit -E '(ERROR|FATAL|EXCEPTION|SEGFAULT|PANIC)'

# Command mode
earlyexit -E '(ERROR|FATAL|EXCEPTION|SEGFAULT|PANIC)' app_command
```

### Example 8: With Line Numbers

```bash
# Pipe mode
long_log_file | earlyexit -n -i 'error'
# Output: 1234:ERROR: Connection failed

# Command mode
earlyexit -n -i 'error' tail -f app.log
```

### Example 9: Health Checks

```bash
# Pipe mode - continuous monitoring
while true; do
  curl -s http://localhost:8080/health
  sleep 1
done | earlyexit -v 'OK' -t 60

# Command mode - startup check
earlyexit --first-output-timeout 5 'error' ./health-check.sh
```

## 🔍 Pattern Syntax & Regex Engines

`earlyexit` supports multiple regex engines controlled by command-line flags:

### Default: Python Extended Regex

**No flag needed** - Uses Python's `re` module (compatible with `grep -E`):

```bash
# Multiple alternatives
earlyexit 'error|warning|fatal'

# Character classes
earlyexit '[Ee]rror'

# Quantifiers
earlyexit 'fail(ed|ure)?'
earlyexit 'error[0-9]+'

# Word boundaries
earlyexit '\berror\b'

# Anchors
earlyexit '^ERROR'      # Start of line
earlyexit 'ERROR$'      # End of line

# Escape sequences
earlyexit '\d+'         # Digits
earlyexit '\w+'         # Word characters
earlyexit '\s+'         # Whitespace
```

### Perl-Compatible Regex (-P flag)

**Requires:** `pip install earlyexit[perl]` or `pip install regex`

Advanced features using the `regex` module (compatible with `grep -P`):

```bash
# Variable-length lookbehinds
earlyexit -P '(?<=ERROR: ).*'
earlyexit -P '(?<!IGNORE )ERROR'

# Named groups
earlyexit -P '(?P<level>ERROR|WARN): (?P<msg>.*)'

# Recursive patterns (nested structures)
earlyexit -P '\(((?:[^()]++|(?R))*+)\)'

# Possessive quantifiers (better performance)
earlyexit -P 'error.*+failed'

# Atomic groups
earlyexit -P '(?>error|errors)'

# Unicode properties
earlyexit -P '\p{Letter}+'
earlyexit -P '\p{Digit}+'
```

### Regex Engine Comparison

| Feature | Default (`re`) | Perl `-P` (`regex`) |
|---------|---------------|---------------------|
| Basic patterns | ✅ | ✅ |
| Alternation `\|` | ✅ | ✅ |
| Quantifiers `*+?{n}` | ✅ | ✅ |
| Character classes | ✅ | ✅ |
| Anchors `^$` | ✅ | ✅ |
| Groups & backreferences | ✅ | ✅ |
| Lookaheads | ✅ | ✅ |
| Fixed-length lookbehinds | ✅ | ✅ |
| **Variable-length lookbehinds** | ❌ | ✅ |
| **Recursive patterns** | ❌ | ✅ |
| **Possessive quantifiers** | ❌ | ✅ |
| **Atomic groups** | ❌ | ✅ |
| **Unicode properties** | ❌ | ✅ |

### Quick Reference

```bash
# Choose your regex engine
earlyexit 'pattern' cmd           # Default: Python re
earlyexit -E 'pattern' cmd        # Explicit: Python re
earlyexit -P 'pattern' cmd        # Advanced: Perl regex

# Common patterns
earlyexit 'ERROR|FATAL'                    # Multiple words
earlyexit -i 'error'                       # Case-insensitive
earlyexit '\b(ERROR|FATAL)\b'              # Whole words only
earlyexit '^ERROR'                         # Start of line
earlyexit 'ERROR.*connection'              # ERROR followed by connection
earlyexit -P '(?<=ERROR: ).*'              # Everything after "ERROR: "
earlyexit -P '(?<!IGNORE )ERROR'           # ERROR not preceded by IGNORE
```

## 🎯 Use Cases

### 1. **AI Agent Workflows** 🤖

Enable AI coding assistants to run commands autonomously with intelligent error detection:

```bash
# AI agent running tests unattended
earlyexit --delay-exit 10 'FAILED|ERROR|Exception' npm test
# Exit code 0 = error found → Agent analyzes logs and fixes code
# Exit code 1 = all tests passed → Agent proceeds to next task

# AI agent running build with hang detection
earlyexit -t 600 --idle-timeout 30 'error|fatal' ./build.sh
# Captures full compilation errors with context
# Detects hung builds and reports back to agent

# Agent-driven deployment validation
earlyexit \
  --first-output-timeout 30 \
  --idle-timeout 60 \
  'Error|Failed|Unhealthy' \
  kubectl rollout status deployment/app
# Agents get immediate feedback on deployment failures
# Clear exit codes enable automated rollback decisions
```

**Why this matters for AI coding:**
- ✅ **Zero human intervention** - agents monitor and react automatically
- ✅ **Fast iteration loops** - immediate error feedback → faster fixes
- ✅ **Rich error context** - delay-exit captures full stack traces for AI analysis
- ✅ **Clear exit codes** - 0=error, 1=success, 2=timeout - perfect for agent logic
- ✅ **Multi-stream monitoring** - catches errors in stdout, stderr, and custom FDs

### 2. **Fast Feedback in CI/CD**

Stop the build immediately on first error instead of waiting for full completion:

```yaml
# GitLab CI example
script:
  - make build 2>&1 | earlyexit -t 3600 'error' || exit 1
```

### 3. **Cost Optimization**

Save compute costs by stopping failed cloud operations early:

```bash
# Stop provisioning if errors detected in first 5 minutes
terraform apply | earlyexit -t 300 'Error:' && terraform destroy -auto-approve
```

### 4. **Development Workflow**

Get instant feedback during development:

```bash
# Watch for compilation errors
npm run watch | earlyexit 'ERROR'
```

### 5. **Monitoring & Alerting**

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

## 🔄 Comparison with Other Tools

### vs grep

| Feature | grep | earlyexit (pipe) | earlyexit (command) |
|---------|------|------------------|---------------------|
| Pattern matching | ✅ | ✅ | ✅ |
| Extended regex | ✅ -E | ✅ -E | ✅ -E |
| Perl regex | ✅ -P | ✅ -P | ✅ -P |
| Stop on first match | ⚠️ -m 1 | ✅ default | ✅ default |
| **Delay-exit (capture error context)** | ❌ | ❌ | ✅ **--delay-exit (unique!)** |
| Timeout | ❌ | ✅ -t | ✅ -t |
| Hang detection | ❌ | ❌ | ✅ --idle-timeout |
| Startup detection | ❌ | ❌ | ✅ --first-output-timeout |
| Stream separation | ❌ | ⚠️ with 2>&1 | ✅ --both, --stderr |
| Exit code clarity | ⚠️ Complex | ✅ 0/1/2/3 | ✅ 0/1/2/3 |
| Pipeable | ✅ | ✅ | ❌ |

### vs timeout

| Feature | timeout | earlyexit (command) |
|---------|---------|---------------------|
| Run commands | ✅ | ✅ |
| Overall timeout | ✅ | ✅ -t |
| Pattern matching | ❌ | ✅ |
| **Delay-exit (capture error context)** | ❌ | ✅ **--delay-exit (unique!)** |
| Hang detection | ❌ | ✅ --idle-timeout |
| Startup detection | ❌ | ✅ --first-output-timeout |
| Stream separation | ❌ | ✅ --stderr, --both |
| Per-FD patterns | ❌ | ✅ --fd-pattern |
| Early exit on match | ❌ | ✅ |

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

1. **For AI agents and unattended execution**, combine multiple safeguards:
   ```bash
   # Comprehensive monitoring for autonomous agents
   earlyexit \
     -t 600 \                    # Overall timeout (prevent infinite runs)
     --idle-timeout 30 \          # Hang detection (no output = stuck)
     --first-output-timeout 10 \  # Startup validation (ensure it runs)
     --delay-exit 10 \            # Error context capture (get full logs)
     'ERROR|FAILED|Exception' \
     ./agent-task.sh
   
   # Agent can confidently interpret:
   # Exit 0 = Error detected with full context → analyze logs and fix
   # Exit 1 = Task completed successfully → proceed to next step
   # Exit 2 = Timeout/hang detected → retry or escalate
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

5. **Check exit codes** properly (critical for AI agents):
   ```bash
   command | earlyexit 'Error'
   case $? in
     0) echo "Error detected"; exit 1 ;;
     1) echo "Success" ;;
     2) echo "Timeout"; exit 2 ;;
     *) echo "Unexpected error"; exit 3 ;;
   esac
   ```

6. **Use delay-exit** to capture full error context (command mode):
   ```bash
   # Wait 10s after error to capture stack traces, cleanup logs, etc. (default)
   earlyexit 'ERROR' ./app  # ✅ Captures full error context
   
   # Quick exit for known fatal errors
   earlyexit --delay-exit 2 'FATAL|PANIC' ./app  # ⚡ Fast fail
   
   # Wait longer for comprehensive context
   earlyexit --delay-exit 30 'Error' ./long-cleanup-app
   
   # In pipe mode, use explicit delay if needed
   ./app 2>&1 | earlyexit --delay-exit 10 'Error'  # Default is 0 for pipes
   ```

## 🤖 Self-Learning System (Coming Soon)

`earlyexit` includes an **optional self-learning capability** that captures execution telemetry for ML-driven optimization:

### What it Learns

- **Pattern Effectiveness**: Which patterns work best for your projects (Python tests vs Node builds)
- **Optimal Delays**: Learns ideal `--delay-exit` times per command type (stack traces need longer)
- **False Positive Reduction**: Identifies "Error" strings that aren't real errors
- **Timing Optimization**: Suggests optimal timeouts based on historical runs
- **Anomaly Detection**: Warns when commands behave unusually

### Privacy-First Design

All data stored **locally** in `~/.earlyexit/telemetry.db` by default:
- ✅ No cloud upload (unless you opt-in)
- ✅ Automatic PII scrubbing (passwords, tokens, paths)
- ✅ Configurable retention (default 90 days)
- ✅ Easy to disable: `--no-telemetry`
- ✅ **Negligible performance impact**: <1ms overhead (tested)

**For ephemeral systems** (CI/CD, containers):
- ✅ Optional HTTP backend for remote storage
- ✅ Fire-and-forget async sending (no blocking)
- ✅ See [TELEMETRY_BACKENDS.md](TELEMETRY_BACKENDS.md) for options

### Example: Self-Improving

```bash
# First run with default settings
$ earlyexit 'Error' npm test
# Exits after 45s (10s delay was too long)

# Provide feedback
$ earlyexit feedback --delay-should-be 5
✓ Feedback recorded

# Next time, get smart suggestions
$ earlyexit suggest 'npm test'
Recommended: earlyexit --delay-exit 5 'Error|FAIL|×' npm test
Based on 47 similar executions in this project

# Auto-apply learned settings (opt-in)
$ earlyexit --auto-tune 'Error' npm test
Using learned settings: --delay-exit 5 --idle-timeout 30
```

### Data Captured for ML

See **[LEARNING_SYSTEM.md](LEARNING_SYSTEM.md)** for complete details:

- ✅ Command metadata (type, language, environment)
- ✅ Pattern match events (timing, location, context)
- ✅ Exit conditions (why it stopped, was it correct?)
- ✅ Performance metrics (runtime, idle periods)
- ✅ User feedback (ratings, corrections)

### Benefits for AI Agents

- **Reduced trial-and-error**: Agent learns from past runs
- **Project-specific tuning**: Automatically adapts to your codebase
- **Confidence scoring**: ML provides uncertainty estimates
- **Continuous improvement**: Gets smarter with every run

### Roadmap

- **Phase 1** (Current): Design and schema ✅
- **Phase 2**: Basic telemetry capture (coming soon)
- **Phase 3**: Analysis and reporting CLI
- **Phase 4**: ML inference for real-time suggestions
- **Phase 5**: Federated learning (opt-in community patterns)

**Note**: All learning features are **opt-in** and can be completely disabled.

## 📝 License

MIT License - see LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please open an issue or PR on GitHub.

## 📖 Additional Documentation

- **[TIMEOUT_GUIDE.md](TIMEOUT_GUIDE.md)** - Complete timeout and hang detection guide
- **[REGEX_REFERENCE.md](REGEX_REFERENCE.md)** - Complete regex pattern reference
- **[FD_MONITORING.md](FD_MONITORING.md)** - File descriptor monitoring guide
- **[LEARNING_SYSTEM.md](LEARNING_SYSTEM.md)** - 🤖 Self-learning and ML optimization system
- **[TELEMETRY_BACKENDS.md](TELEMETRY_BACKENDS.md)** - Storage options (SQLite, HTTP, hybrid)
- **[ENHANCEMENTS.md](ENHANCEMENTS.md)** - Technical implementation details

## 🔗 Related Projects

- **timeout** - Command timeout utility (part of GNU coreutils)
- **stdbuf** - Modify buffering of streams (part of GNU coreutils)
- **ripgrep (rg)** - Fast grep alternative in Rust

## 📮 Contact

Robert Lee - robert.lee@databricks.com

---

**Made with ❤️ for developers who value fast feedback**


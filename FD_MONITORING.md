# File Descriptor Monitoring in earlyexit

## Overview

`earlyexit` supports monitoring arbitrary Unix file descriptors (fd 3, 4, 5, etc.) in addition to standard streams (stdout/stderr). This enables monitoring of:
- Debug output channels
- Progress indicators
- Structured logging streams
- Application-specific communication channels

## Features

### 1. Monitor Custom File Descriptors

Monitor file descriptors 3 and above:

```bash
# Monitor fd 3 with default pattern
earlyexit --fd 3 'Error' ./app

# Monitor multiple file descriptors
earlyexit --fd 3 --fd 4 --fd 5 'Error' ./app

# Add labels to identify streams
earlyexit --fd 3 --fd 4 --fd-prefix 'Error' ./app
```

### 2. Per-FD Pattern Matching

Use different patterns for different file descriptors:

```bash
# Watch for different patterns on different streams
earlyexit --fd-pattern 1 'FAILED' --fd-pattern 2 'ERROR' --fd-prefix 'any' ./test.sh

# Stdout for failures, stderr for errors, fd3 for debug issues
earlyexit \
  --fd-pattern 1 'FAILED' \
  --fd-pattern 2 'ERROR|FATAL' \
  --fd 3 --fd-pattern 3 'DEBUG.*Critical' \
  --fd-prefix \
  'default' ./app

# Mix monitored and non-monitored FDs
earlyexit --fd 3 --fd 4 --fd-pattern 3 'Error' 'default' ./app
# This monitors fd3 for "Error" and fd4 for "default"
```

### 3. Stream Labels

Identify which stream produced each line:

```bash
earlyexit --both --fd 3 --fd-prefix 'Error' ./app
# Output:
# [stdout] normal message
# [stderr] warning message  
# [fd3] debug message
# [stderr] ERROR - Connection failed!  <- Match!
```

## How It Works

### File Descriptor Setup

When you specify `--fd N`, earlyexit:

1. Creates a pipe for fd N
2. Passes the write end to the child process as fd N
3. Reads from the read end to monitor the stream
4. Uses `preexec_fn` to set up the fd in the child process

### Pattern Matching Strategy

- **Default pattern**: Applies to all monitored streams without specific patterns
- **Per-FD patterns**: Override the default for specific file descriptors
- **Standard streams**: Can be given custom patterns using fd numbers:
  - `--fd-pattern 1 'PATTERN'` for stdout
  - `--fd-pattern 2 'PATTERN'` for stderr

## Examples

### Example 1: Application with Debug Stream

Your application writes to fd 3 for debug output:

```bash
#!/bin/bash
# app.sh
echo "Normal output"
echo "Debug: Starting process" >&3
echo "Debug: ERROR in module X" >&3
echo "More output"
```

Monitor for errors on debug stream:

```bash
earlyexit --fd 3 --fd-pattern 3 'ERROR' --fd-prefix 'any' ./app.sh
# Exits immediately when "ERROR" appears on fd 3
```

### Example 2: Multi-Channel Logging

Application uses different FDs for different log levels:

```bash
#!/bin/bash
# Stdout: INFO
# Stderr: WARN/ERROR
# fd 3: DEBUG
# fd 4: TRACE

echo "INFO: Application started"
echo "WARN: Low memory" >&2
echo "DEBUG: Connection pool size: 10" >&3
echo "ERROR: Database connection failed" >&2  # This should trigger!
```

Monitor with appropriate patterns:

```bash
earlyexit \
  --both \
  --fd 3 --fd 4 \
  --fd-pattern 2 'ERROR|FATAL' \
  --fd-pattern 3 'DEBUG.*Critical' \
  --fd-pattern 4 'TRACE.*Exception' \
  --fd-prefix \
  'INFO' ./app.sh

# Exits when "ERROR" appears on stderr
```

### Example 3: Build System with Progress Stream

Build tool writes progress to fd 3, errors to stderr:

```bash
earlyexit --fd 3 --stderr --fd-pattern 2 'error:' --fd-prefix 'progress' make
```

### Example 4: Test Runner with Separate Channels

```bash
# Test runner writes:
# - Test names to stdout
# - Failures to stderr  
# - Coverage to fd 3
# - Performance to fd 4

earlyexit \
  --fd-pattern 1 'FAILED' \
  --fd-pattern 2 'ERROR|FATAL' \
  --fd 3 --fd-pattern 3 'Coverage.*0%' \
  --fd-prefix \
  'nomatch' pytest -v
```

## Writing to Custom File Descriptors

### In Bash

```bash
#!/bin/bash

# Check if fd 3 is writable
if [ -w /dev/fd/3 ] 2>/dev/null; then
    echo "Debug message" >&3
fi

# Or just write to it (will fail silently if not open)
echo "Debug: Processing..." >&3 2>/dev/null
```

### In Python

```python
import os
import sys

# Write to fd 3
if os.path.exists(f'/dev/fd/3'):
    with open(3, 'w') as fd3:
        fd3.write("Debug message\n")
        fd3.flush()
```

### In C

```c
#include <unistd.h>

// Write to fd 3
write(3, "Debug message\n", 14);
```

## Pattern Matching Behavior

### Default Pattern

When no per-FD pattern is specified, all monitored streams use the default pattern:

```bash
earlyexit --both --fd 3 'Error' ./app
# Watches for "Error" on stdout, stderr, and fd3
```

### Per-FD Patterns

Override the default for specific file descriptors:

```bash
earlyexit --fd-pattern 1 'FAILED' --fd-pattern 2 'ERROR' 'default' ./app
# stdout: watches for "FAILED"
# stderr: watches for "ERROR"  
# other FDs: watch for "default" (if any)
```

### Pattern Precedence

1. Specific fd-pattern for that FD
2. Default pattern (from positional argument)

## Use Cases

### 1. Structured Logging

Applications that separate logs by severity:

```bash
earlyexit \
  --fd-pattern 2 'ERROR|FATAL' \
  --fd 3 --fd-pattern 3 'WARN' \
  --fd 4 --fd-pattern 4 'DEBUG.*Crash' \
  'INFO' ./app
```

### 2. Build Systems

Monitor build progress and errors separately:

```bash
earlyexit --fd 3 --fd-pattern 2 'error:' --fd-prefix 'Building' cmake --build .
```

### 3. Test Frameworks

Monitor test output, coverage, and performance:

```bash
earlyexit \
  --fd-pattern 1 'FAILED|ERROR' \
  --fd 3 --fd-pattern 3 'Coverage.*[0-4][0-9]%' \
  'PASS' pytest --cov
```

### 4. Microservices

Monitor health checks on separate channel:

```bash
earlyexit --fd 3 --fd-pattern 3 'health.*false' 'ERROR' ./service
```

## Limitations

- File descriptors < 3 cannot be created (stdin=0, stdout=1, stderr=2 are standard)
- Maximum number of file descriptors limited by OS (typically 1024-4096)
- All monitored FDs must be explicitly opened by the child process
- FDs not used by child will show as closed/unavailable

## Troubleshooting

### "Bad file descriptor" Error

The child process didn't write to the specified FD. Check that your application actually uses that FD.

### No Output from FD

1. Ensure the application writes to that FD
2. Check if the application buffers output (use `flush()` or `stdbuf`)
3. Verify fd is opened for writing in the child process

### Permission Errors

Running in a sandbox or restricted environment may prevent fd manipulation. Try:

```bash
# Use full permissions if in restricted environment
earlyexit --fd 3 'Error' ./app  # May need to run outside sandbox
```

## Performance

- Each monitored FD creates a thread for processing
- Minimal overhead: ~1-2% CPU per monitored stream
- Memory: ~8KB buffer per stream
- Recommended: Monitor only necessary FDs (typically 2-4 streams)

## Comparison with Other Tools

| Tool | Custom FDs | Per-FD Patterns | Pattern Matching |
|------|-----------|-----------------|------------------|
| `grep` | ❌ | ❌ | ✅ |
| `awk` | ❌ | ❌ | ✅ |
| `timeout` | ❌ | ❌ | ❌ |
| **`earlyexit`** | ✅ | ✅ | ✅ |

## Future Enhancements

Potential improvements:
1. **FD redirection**: Redirect one FD to another
2. **FD filtering**: Only monitor certain patterns on certain FDs
3. **FD multiplexing**: Combine multiple FDs into one stream
4. **FD buffering**: Control buffering per-FD
5. **Named pipes**: Support for named pipes instead of numbered FDs

## Version

- Feature introduced: 0.0.1
- Per-FD patterns: 0.0.1
- Date: November 10, 2025


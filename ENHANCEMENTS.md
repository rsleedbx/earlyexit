# earlyexit Enhancements - Command Mode

## Overview

Enhanced `earlyexit` to support **command mode** execution, similar to the `timeout` command, while maintaining full backward compatibility with pipe mode.

## New Features

### 1. Command Mode Execution

Run commands directly through earlyexit, monitoring their output for pattern matches:

```bash
# Basic usage
earlyexit -t 60 'Error' sleep 120

# Real-world example
earlyexit -t 300 'FAILED' pytest -v
```

### 2. Separate stdout/stderr Monitoring

Monitor stdout and stderr streams separately or together:

```bash
# Monitor stderr only
earlyexit --stderr 'Error' ./build.sh

# Monitor both streams
earlyexit --both 'Error|Warning' ./app

# Add stream labels to output
earlyexit --both --stderr-prefix 'Error' ./app
```

### 3. Improved Timeout Handling

- Timeout now works in both pipe mode and command mode
- Uses threading.Timer for command mode to avoid signal conflicts
- Gracefully handles sandbox/restricted environments
- Properly terminates subprocesses on timeout

## Architecture Changes

### Mode Detection

- **Command Mode**: Activated when command arguments are provided
- **Pipe Mode**: Activated when reading from stdin (no command args)
- Command mode takes precedence if both are detected

### Stream Processing

- Refactored line processing into `process_stream()` function
- Supports multiple streams concurrently using threads
- Handles both text and binary stream data
- Proper error handling for broken pipes and timeouts

### Threading Model

When monitoring both streams (`--both`):
- Creates separate daemon threads for stdout and stderr
- Shares match counter across threads
- Terminates subprocess when pattern is matched
- Joins threads gracefully on completion or timeout

## Usage Examples

### Command Mode

```bash
# Timeout example
earlyexit -t 2 'nomatch' sleep 10
# Returns: Exit code 2 (timeout)

# Pattern match example
earlyexit 'test' echo 'this is a test'
# Returns: Exit code 0 (match found)

# No match example
earlyexit 'error' echo 'success'
# Returns: Exit code 1 (no match)

# Monitor stderr
earlyexit --stderr 'ERROR' ./script.sh 2>&1

# Monitor both with labels
earlyexit --both --stderr-prefix 'Error' ./app
```

### Pipe Mode (Backward Compatible)

```bash
# Traditional pipe usage still works
echo "error message" | earlyexit 'error'
# Returns: Exit code 0 (match found)

# With timeout
long_command | earlyexit -t 60 'Error'

# Multiple patterns
app_log | earlyexit -E '(Error|Warning|Fatal)'
```

## Comparison with `timeout`

| Feature | timeout | earlyexit |
|---------|---------|-----------|
| Run commands | ✅ | ✅ |
| Timeout support | ✅ | ✅ |
| Pattern matching | ❌ | ✅ |
| Separate stderr monitoring | ❌ | ✅ |
| Early exit on match | ❌ | ✅ |
| Pipe mode | ❌ | ✅ |
| Regex support | ❌ | ✅ (Extended & Perl) |

## Exit Codes

- **0**: Pattern matched (error detected, early exit)
- **1**: No match found (success)
- **2**: Timeout exceeded
- **3**: Other error (invalid pattern, command not found, etc.)
- **130**: Interrupted (Ctrl+C)

## Implementation Details

### New Functions

1. **`process_stream()`**: Unified stream processing for both modes
2. **`run_command_mode()`**: Handles subprocess execution and monitoring
3. **`timeout_callback()`**: Thread-safe timeout handler for command mode

### New Arguments

- `command`: Positional argument (nargs='*') for command to run
- `--stderr`: Monitor stderr instead of stdout
- `--both`: Monitor both stdout and stderr
- `--stderr-prefix`: Add stream labels to output

### Technical Considerations

- Uses `subprocess.Popen` with separate `stdout` and `stderr` pipes
- Threading for concurrent stream monitoring
- Signal-based timeout for pipe mode (SIGALRM)
- Timer-based timeout for command mode (threading.Timer)
- Graceful handling of permission errors in sandboxed environments
- Proper cleanup of subprocesses and threads

## Testing

### Manual Tests

```bash
# Test timeout
earlyexit -t 2 'nomatch' sleep 10  # Should timeout after 2s

# Test pattern match
earlyexit 'test' echo 'test message'  # Should match and exit 0

# Test no match
earlyexit 'error' echo 'success'  # Should exit 1

# Test pipe mode
echo "test" | earlyexit 'test'  # Should match and exit 0
```

### Automated Tests

Existing test suite (`tests/test_earlyexit.py`) should be updated to include:
- Command mode tests
- Stderr monitoring tests
- Both-streams monitoring tests
- Timeout in command mode tests

## Future Enhancements

Potential improvements for future versions:

1. **Shell command support**: Add `--shell` flag to run commands through shell
2. **Signal forwarding**: Forward signals (SIGTERM, SIGINT) to subprocess
3. **Return code preservation**: Option to return subprocess exit code
4. **Stream buffering control**: Options for line/block buffering
5. **Multiple patterns**: Support different patterns for stdout/stderr
6. **JSON output**: Structured output for CI/CD integration

## Backward Compatibility

✅ All existing pipe mode functionality is preserved
✅ All existing command-line flags work as before
✅ Exit codes remain consistent
✅ Existing scripts and integrations are unaffected

## Documentation Updates

- ✅ README.md updated with command mode examples
- ✅ Help text updated with new options
- ✅ Usage section expanded to cover both modes
- ✅ Examples reorganized and expanded

## Version

- Current version: 0.0.1
- Feature: Command mode execution
- Date: November 10, 2025


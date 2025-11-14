#!/usr/bin/env python3
"""
earlyexit - Early exit pattern matching for command output

Stop long-running commands the instant an error appears.
Like 'timeout' + 'grep -m 1' combined, but with hang detection, stderr monitoring,
configurable delay to capture full error context, and per-FD pattern matching.
Implements the early error detection pattern for faster feedback.
"""

import sys
import re
import argparse
import signal
import subprocess
import select
import threading
import os
import time
from typing import Optional, Pattern, IO, Dict, List
from pathlib import Path

# psutil for inspecting subprocess file descriptors (optional)
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

# Telemetry (optional, fails gracefully)
try:
    from . import telemetry
    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False
    telemetry = None


class TimeoutError(Exception):
    """Raised when timeout is exceeded"""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout"""
    raise TimeoutError("Timeout exceeded")


def normalize_line_for_comparison(line: str, strip_timestamps: bool = True, stuck_pattern: str = None) -> str:
    """
    Normalize a line for comparison to detect stuck/repeated output.
    
    Args:
        line: Input line to normalize
        strip_timestamps: If True, remove common timestamp patterns
        stuck_pattern: If provided, extract only the part matching this regex
    
    Returns:
        Normalized line with timestamps removed and whitespace collapsed,
        or extracted pattern match if stuck_pattern is provided
    """
    import re
    
    # If stuck_pattern provided, extract and return that part only
    if stuck_pattern:
        try:
            match = re.search(stuck_pattern, line)
            if match:
                # Return the matched part (what we're watching for repetition)
                return match.group(0).strip()
            else:
                # Pattern didn't match, use full line
                pass
        except re.error:
            # Invalid regex, fall through to normal processing
            pass
    
    # Normal processing
    if not strip_timestamps:
        return line.strip()
    
    # Strip common timestamp patterns
    normalized = line
    
    # [HH:MM:SS] or [HH:MM:SS.mmm]
    normalized = re.sub(r'\[\d{2}:\d{2}:\d{2}(?:\.\d+)?\]', '', normalized)
    
    # YYYY-MM-DD or YYYY/MM/DD
    normalized = re.sub(r'\d{4}[-/]\d{2}[-/]\d{2}', '', normalized)
    
    # HH:MM:SS (not in brackets)
    normalized = re.sub(r'\b\d{2}:\d{2}:\d{2}\b', '', normalized)
    
    # Timestamps like "2024-11-14T09:03:45" or "2024-11-14 09:03:45"
    normalized = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?', '', normalized)
    
    # Unix epoch timestamps (10 digits)
    normalized = re.sub(r'\b\d{10}\b', '', normalized)
    
    # Millisecond timestamps (13 digits)
    normalized = re.sub(r'\b\d{13}\b', '', normalized)
    
    # Collapse multiple spaces to single space
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized.strip()


def update_ee_env_exit_code(exit_code: int):
    """Update the exit code in the environment file for the current shell session."""
    try:
        parent_pid = os.getppid()
        ee_env_file = os.path.expanduser(f"~/.ee_env.{parent_pid}")
        # Only update if file exists (log files were created)
        if os.path.exists(ee_env_file):
            # Read existing content
            with open(ee_env_file, 'r') as f:
                lines = f.readlines()
            # Update or add exit code
            with open(ee_env_file, 'w') as f:
                exit_code_written = False
                for line in lines:
                    if line.startswith('export EE_EXIT_CODE='):
                        f.write(f"export EE_EXIT_CODE={exit_code}\n")
                        exit_code_written = True
                    else:
                        f.write(line)
                if not exit_code_written:
                    f.write(f"export EE_EXIT_CODE={exit_code}\n")
    except Exception:
        pass  # Silent failure


def map_exit_code(code: int, use_unix_convention: bool) -> int:
    """
    Map exit codes based on convention.
    
    Args:
        code: Original exit code (grep convention)
        use_unix_convention: If True, use Unix convention (0=success)
                           If False, use grep convention (0=match)
    
    Returns:
        Mapped exit code
    
    Exit code mappings:
        Grep convention (default):     Unix convention (--unix-exit-codes):
        0 = pattern matched            0 = success (no error found)
        1 = no match                   1 = error found (pattern matched)
        2 = timeout                    2 = timeout (unchanged)
        3 = CLI error                  3 = CLI error (unchanged)
        4 = detached                   4 = detached (unchanged)
        130 = interrupted              130 = interrupted (unchanged)
    """
    # Update environment file with exit code
    update_ee_env_exit_code(code)
    
    if not use_unix_convention:
        return code  # Keep grep convention (current behavior)
    
    # Unix convention: swap 0 and 1 only
    if code == 0:
        # Pattern matched (error found) → Unix failure
        return 1
    elif code == 1:
        # No match (success) → Unix success
        return 0
    else:
        # Keep other codes as-is (timeouts, errors, detached, interrupted)
        return code


def create_json_output(
    exit_code: int,
    exit_reason: str,
    pattern: Optional[str],
    matched_line: Optional[str],
    line_number: Optional[int],
    duration: float,
    command: List[str],
    timeouts: dict,
    statistics: dict,
    log_files: dict
) -> str:
    """
    Create JSON output for --json flag.
    
    Args:
        exit_code: Final exit code (after mapping if --unix-exit-codes used)
        exit_reason: Reason for exit (pattern_matched, no_match, timeout, etc.)
        pattern: Regular expression pattern used
        matched_line: The line that matched (if any)
        line_number: Line number of match (if any)
        duration: Total execution duration in seconds
        command: Command that was executed
        timeouts: Dictionary of timeout settings
        statistics: Dictionary of execution statistics
        log_files: Dictionary of log file paths
    
    Returns:
        JSON string
    """
    import json
    
    output = {
        "version": "0.0.5",
        "exit_code": exit_code,
        "exit_reason": exit_reason,
        "pattern": pattern,
        "matched_line": matched_line,
        "line_number": line_number,
        "duration_seconds": round(duration, 2),
        "command": command,
        "timeouts": timeouts,
        "statistics": statistics,
        "log_files": log_files
    }
    
    return json.dumps(output, indent=2)


def format_duration(seconds: float) -> str:
    """
    Format seconds as HH:MM:SS or MM:SS.
    
    Args:
        seconds: Duration in seconds
    
    Returns:
        Formatted string (HH:MM:SS or MM:SS)
    """
    if seconds < 0:
        return "00:00"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def show_progress_indicator(args, start_time: float, last_output_time: list, 
                            lines_processed: list, match_count: list, 
                            stop_event: threading.Event):
    """
    Display progress indicator on stderr.
    
    Args:
        args: Arguments namespace
        start_time: When monitoring started (timestamp)
        last_output_time: List with [last_output_timestamp]
        lines_processed: List with [line_count]
        match_count: List with [match_count]
        stop_event: Threading event to signal stop
    """
    while not stop_event.is_set():
        elapsed = time.time() - start_time
        elapsed_str = format_duration(elapsed)
        
        # Build timeout display
        if args.timeout:
            remaining = args.timeout - elapsed
            if remaining < 0:
                remaining = 0
            timeout_str = f"{elapsed_str} / {format_duration(args.timeout)}"
        else:
            timeout_str = elapsed_str
        
        # Time since last output
        if last_output_time[0] and last_output_time[0] > 0:
            since_output = time.time() - last_output_time[0]
            last_output_str = format_duration(since_output) + " ago"
        else:
            last_output_str = "waiting..."
        
        # Command name
        command_name = args.command[0] if args.command else "stdin"
        
        # Build progress line
        progress = (
            f"\r[{timeout_str}] Monitoring {command_name}... "
            f"Last output: {last_output_str} | "
            f"Lines: {lines_processed[0]:,} | "
            f"Matches: {match_count[0]}"
        )
        
        # Clear line and print (overwrite previous progress)
        sys.stderr.write('\r' + ' ' * 120)  # Clear line
        sys.stderr.write(progress)
        sys.stderr.flush()
        
        # Update every 2 seconds
        stop_event.wait(2)
    
    # Clear progress line when done
    sys.stderr.write('\r' + ' ' * 120 + '\r')
    sys.stderr.flush()


def inspect_process_fds(pid: int, delay: float = 0.1) -> List[str]:
    """
    Inspect a process's open file descriptors to find regular files
    
    Args:
        pid: Process ID to inspect
        delay: Initial delay before inspection (to let process open files)
        
    Returns:
        List of regular file paths opened by the process
    """
    if not PSUTIL_AVAILABLE:
        return []
    
    # Give the process a moment to open its files
    if delay > 0:
        time.sleep(delay)
    
    try:
        proc = psutil.Process(pid)
        open_files = []
        
        for f in proc.open_files():
            # f is a named tuple: (path, fd, position, mode, flags)
            path = f.path
            
            # Filter out system files, pipes, sockets
            if not path:
                continue
            
            # Skip common non-source file paths
            skip_patterns = [
                '/dev/', '/proc/', '/sys/', '/tmp/',
                '.so', '.dylib', '.dll',  # Libraries
                '/lib/', '/usr/lib/',
                'site-packages/',
                '__pycache__/',
            ]
            
            if any(pattern in path for pattern in skip_patterns):
                continue
            
            # Check if it's a real file (not directory, socket, etc.)
            try:
                if os.path.isfile(path):
                    # Convert to relative path if possible
                    try:
                        rel_path = os.path.relpath(path)
                        if not rel_path.startswith('..'):
                            open_files.append(rel_path)
                        else:
                            open_files.append(path)
                    except ValueError:
                        # Different drives on Windows, keep absolute
                        open_files.append(path)
            except (OSError, FileNotFoundError):
                pass
        
        return open_files
        
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return []


def compile_pattern(pattern: str, flags: int = 0, perl_style: bool = False, 
                   word_regexp: bool = False, line_regexp: bool = False) -> Pattern:
    """
    Compile regex pattern with appropriate flags
    
    Args:
        pattern: Regex pattern string
        flags: re module flags
        perl_style: Use regex module for Perl-compatible patterns
        word_regexp: Match whole words only (like grep -w)
        line_regexp: Match whole lines only (like grep -x)
        
    Returns:
        Compiled pattern object
    """
    # Apply word/line boundaries (like grep -w/-x)
    if word_regexp:
        pattern = r'\b' + pattern + r'\b'
    if line_regexp:
        pattern = r'^' + pattern + r'$'
    
    if perl_style:
        try:
            import regex
            return regex.compile(pattern, flags)
        except ImportError:
            print("⚠️  Warning: 'regex' module not installed. Install with: pip install regex", 
                  file=sys.stderr)
            print("   Falling back to standard 're' module", file=sys.stderr)
            return re.compile(pattern, flags)
    else:
        return re.compile(pattern, flags)


def process_stream(stream: IO, pattern: Optional[Pattern], args, line_number_offset: int, 
                   match_count: list, use_color: bool, stream_name: str = "",
                   last_output_time: Optional[list] = None, first_output_seen: Optional[list] = None,
                   first_stream_time: Optional[list] = None,
                   match_timestamp: Optional[list] = None, telemetry_collector=None, 
                   execution_id: Optional[str] = None, start_time: Optional[float] = None,
                   source_file_container: Optional[list] = None, post_match_lines: Optional[list] = None,
                   log_file=None, lines_processed: Optional[list] = None,
                   success_pattern: Optional[Pattern] = None, match_type: Optional[list] = None,
                   stuck_detected: Optional[list] = None,
                   last_stderr_time: Optional[list] = None, stderr_seen: Optional[list] = None):
    """
    Process a stream (stdout or stderr) line by line
    
    Args:
        stream: File-like object to read from
        pattern: Compiled regex pattern (can be None if no pattern for this stream)
        args: Argument namespace
        line_number_offset: Starting line number
        match_count: List with single element tracking match count (mutable)
        use_color: Whether to use color output
        stream_name: Name of stream for debugging ("stdout" or "stderr")
        last_output_time: List with timestamp of last output (mutable)
        first_output_seen: List with boolean if first output seen (mutable)
        first_stream_time: List with timestamp when first output seen on THIS stream (mutable)
        match_timestamp: List with timestamp of first match (mutable)
        telemetry_collector: Telemetry collector instance for recording match events
        execution_id: Execution ID for telemetry
        start_time: Start time of execution for timestamp offsets
        source_file_container: List containing source file (mutable, for dynamic detection)
        post_match_lines: List with count of lines captured after match (mutable)
        
    Returns:
        Number of lines processed
    """
    # If no pattern provided for this stream, just pass through
    if pattern is None:
        try:
            for line in stream:
                if isinstance(line, bytes):
                    line = line.decode('utf-8', errors='replace')
                
                # Update output tracking
                current_time = time.time()
                if last_output_time is not None:
                    last_output_time[0] = current_time
                if first_output_seen is not None and not first_output_seen[0]:
                    first_output_seen[0] = True
                # Track first output time for this specific stream
                if first_stream_time is not None and first_stream_time[0] == 0.0:
                    first_stream_time[0] = current_time
                
                # Write to log file if enabled
                if log_file:
                    log_file.write(line)
                    log_file.flush()
                
                # Always print command output (--quiet only suppresses ee's messages, not command output)
                # Exception: --json mode, which sets its own output suppression
                if not args.json:
                    print(line.rstrip('\n'), flush=True)
        except:
            pass
        return 0
    RED = '\033[01;31m' if use_color else ''
    YELLOW = '\033[01;33m' if use_color else ''
    RESET = '\033[0m' if use_color else ''
    
    line_number = line_number_offset
    
    # Stuck detection: track repeated lines
    repeat_count = 0
    last_normalized_line = None
    max_repeat = getattr(args, 'max_repeat', None)
    strip_timestamps = getattr(args, 'stuck_ignore_timestamps', False)
    stuck_pattern = getattr(args, 'stuck_pattern', None)
    
    # Context buffer for capturing lines before matches (like grep -B)
    context_buffer = []
    context_size = getattr(args, 'before_context', 0)  # Number of lines to keep
    
    # Try to get filename from stream handle itself
    if source_file_container and not source_file_container[0]:
        try:
            stream_name_attr = getattr(stream, 'name', None)
            if stream_name_attr and isinstance(stream_name_attr, str):
                # Valid if it's not a generic stream name or file descriptor number
                if (stream_name_attr not in ['<stdin>', '<stdout>', '<stderr>'] and 
                    not stream_name_attr.isdigit()):
                    source_file_container[0] = stream_name_attr
        except:
            pass
    
    try:
        for line in stream:
            if isinstance(line, bytes):
                line = line.decode('utf-8', errors='replace')
            
            # Update output tracking
            current_time = time.time()
            if last_output_time is not None:
                last_output_time[0] = current_time
            if first_output_seen is not None and not first_output_seen[0]:
                first_output_seen[0] = True
            # Track first output time for this specific stream
            if first_stream_time is not None and first_stream_time[0] == 0.0:
                first_stream_time[0] = current_time
            
            # Track stderr-specific timing (for --stderr-idle-exit)
            # Update if last_stderr_time is provided (indicates this is stderr stream)
            if last_stderr_time is not None:
                last_stderr_time[0] = current_time
                if stderr_seen is not None:
                    stderr_seen[0] = True
            
            line_number += 1
            line_stripped = line.rstrip('\n')
            
            # Track lines for progress indicator
            if lines_processed is not None:
                lines_processed[0] += 1
            
            # Stuck detection: check if line is repeating
            if max_repeat:
                # Normalize line for comparison
                normalized_line = normalize_line_for_comparison(line_stripped, strip_timestamps, stuck_pattern)
                
                if normalized_line == last_normalized_line and normalized_line:
                    repeat_count += 1
                    if repeat_count >= max_repeat:
                        # Stuck detected!
                        if not args.quiet:
                            detection_msg = []
                            if stuck_pattern:
                                detection_msg.append("watching pattern")
                            if strip_timestamps:
                                detection_msg.append("ignoring timestamps")
                            context = f" ({', '.join(detection_msg)})" if detection_msg else ""
                            print(f"\n🔁 Stuck detected: Same line repeated {repeat_count} times{context}", file=sys.stderr)
                            if stuck_pattern:
                                print(f"   Watched part: {normalized_line}", file=sys.stderr)
                            print(f"   Full line: {line_stripped}", file=sys.stderr)
                        # Set stuck flag and break
                        if stuck_detected is not None:
                            stuck_detected[0] = True
                        break
                else:
                    repeat_count = 1
                    last_normalized_line = normalized_line
            
            # Maintain context buffer (ring buffer of last N lines) for -B/--before-context
            if context_size > 0:
                context_buffer.append((line_number, line_stripped))
                if len(context_buffer) > context_size:
                    context_buffer.pop(0)
            
            # Check exclusion patterns first (if any)
            excluded = False
            if hasattr(args, 'exclude_patterns') and args.exclude_patterns:
                for exclude_pattern_str in args.exclude_patterns:
                    try:
                        # Compile exclusion pattern with same flags as main pattern
                        flags = re.IGNORECASE if args.ignore_case else 0
                        exclude_pattern = re.compile(exclude_pattern_str, flags)
                        if exclude_pattern.search(line_stripped):
                            excluded = True
                            break
                    except re.error:
                        # Invalid exclusion pattern - skip it
                        pass
            
            # If line is excluded, skip pattern matching
            if excluded:
                continue
            
            # Check for success pattern first (if provided)
            if success_pattern:
                success_match = success_pattern.search(line_stripped)
                if success_match:
                    # Success pattern matched! Mark as success (first match wins)
                    if match_type is not None and match_type[0] == 'none':
                        match_type[0] = 'success'
                    match_count[0] += 1
                    current_time = time.time()
                    
                    # Record first match timestamp
                    if match_timestamp is not None and match_timestamp[0] == 0:
                        match_timestamp[0] = current_time
                    
                    # Use success_match as the match object for highlighting/recording
                    match = success_match
                    is_match = True
                    # Skip to output handling below
                    # Note: Don't check invert_match for success patterns
                else:
                    # No success match, check error pattern
                    match = pattern.search(line_stripped) if pattern else None
                    is_match = match is not None
                    
                    # Invert if requested (only applies to error pattern)
                    if args.invert_match:
                        is_match = not is_match
                    
                    # Mark as error (first match wins)
                    if is_match and match_type is not None and match_type[0] == 'none':
                        match_type[0] = 'error'
            else:
                # Traditional mode or error-only mode: check main pattern
                match = pattern.search(line_stripped)
                is_match = match is not None
                
                # Invert if requested
                if args.invert_match:
                    is_match = not is_match
                
                # Mark as error in traditional mode (first match wins)
                if is_match and match_type is not None and match_type[0] == 'none':
                    match_type[0] = 'error'
            
            if is_match:
                match_count[0] += 1
                current_time = time.time()
                
                # Record first match timestamp for delay-exit
                if match_timestamp is not None and match_timestamp[0] == 0:
                    match_timestamp[0] = current_time
                
                # Record match event to telemetry
                if telemetry_collector and execution_id and not args.invert_match and match:
                    try:
                        # Get current source file (may have been updated dynamically)
                        current_source_file = source_file_container[0] if source_file_container else None
                        
                        match_data = {
                            'match_number': match_count[0],
                            'timestamp_offset': current_time - start_time if start_time else 0,
                            'stream_source': stream_name or 'stdin',
                            'source_file': current_source_file,
                            'line_number': line_number,
                            'line_content': line_stripped,
                            'matched_substring': match.group(0) if match else '',
                            'context_before': '\n'.join(context_buffer[:-1]) if len(context_buffer) > 1 else '',
                            'context_after': ''  # Will be filled by subsequent lines if needed
                        }
                        telemetry_collector.record_match_event(execution_id, match_data)
                    except Exception:
                        # Silently fail - don't disrupt execution
                        pass
                
                # Write to log file if enabled (always write, even if quiet)
                if log_file:
                    log_file.write(line)
                    log_file.flush()
                
                # Output the line (--quiet only suppresses ee's messages, not command output)
                if not args.json:
                    # Print context lines before the match (like grep -B)
                    if context_size > 0 and len(context_buffer) > 0:
                        # Print all buffered lines except the current one (which we'll print below)
                        for ctx_line_num, ctx_line in context_buffer[:-1]:
                            ctx_prefix = ""
                            if args.line_number:
                                ctx_prefix = f"{ctx_line_num}-"  # Use '-' for context lines like grep
                            if stream_name and args.fd_prefix:
                                ctx_prefix += f"{YELLOW}[{stream_name}]{RESET} "
                            print(f"{ctx_prefix}{ctx_line}", flush=True)
                        # Clear buffer after printing to avoid reprinting on next match
                        context_buffer.clear()
                    
                    prefix = ""
                    if args.line_number:
                        prefix = f"{line_number}:"
                    if stream_name and args.fd_prefix:
                        prefix += f"{YELLOW}[{stream_name}]{RESET} "
                    
                    # Highlight matched text (only for non-inverted matches)
                    if not args.invert_match and match and use_color:
                        start, end = match.span()
                        highlighted = (line_stripped[:start] + RED + 
                                     line_stripped[start:end] + RESET + 
                                     line_stripped[end:])
                        print(f"{prefix}{highlighted}", flush=True)
                    else:
                        print(f"{prefix}{line_stripped}", flush=True)
                
                # Check if we've reached max matches
                if match_count[0] >= args.max_count:
                    # In command mode with delay, let the main loop handle termination
                    # In pipe mode or with 0 delay, exit immediately
                    if args.delay_exit is None or args.delay_exit == 0:
                        # No delay, exit immediately
                        return line_number - line_number_offset
                    elif match_timestamp and match_timestamp[0] > 0:
                        # Check if delay has expired OR if we've captured enough lines
                        elapsed = time.time() - match_timestamp[0]
                        if elapsed >= args.delay_exit:
                            # Delay expired, stop reading
                            return line_number - line_number_offset
                        if post_match_lines and post_match_lines[0] >= args.delay_exit_after_lines:
                            # Captured enough lines, stop reading
                            return line_number - line_number_offset
                    # Otherwise continue reading (still within delay period)
            else:
                # Non-matching line - write to log and pass through if not quiet
                # Write to log file if enabled
                if log_file:
                    log_file.write(line)
                    log_file.flush()
                
                # Increment post-match line counter if we've matched
                if match_count[0] >= args.max_count and post_match_lines is not None:
                    post_match_lines[0] += 1
                    # Check if we've exceeded line limit
                    if post_match_lines[0] >= args.delay_exit_after_lines:
                        if not args.json:
                            prefix = ""
                            if args.line_number:
                                prefix = f"{line_number}:"
                            if stream_name and args.fd_prefix:
                                prefix += f"{YELLOW}[{stream_name}]{RESET} "
                            print(f"{prefix}{line_stripped}", flush=True)
                        return line_number - line_number_offset
                
                if not args.json:
                    prefix = ""
                    if args.line_number:
                        prefix = f"{line_number}:"
                    if stream_name and args.fd_prefix:
                        prefix += f"{YELLOW}[{stream_name}]{RESET} "
                    print(f"{prefix}{line_stripped}", flush=True)
    
    except TimeoutError:
        # Re-raise timeout errors so they can be handled by main()
        raise
    except Exception as e:
        if not args.quiet:
            print(f"❌ Error processing {stream_name}: {e}", file=sys.stderr, flush=True)
    
    return line_number - line_number_offset


def write_pid_file(pid: int, pid_file_path: str, quiet: bool = False):
    """Write PID to file for cleanup scripts"""
    try:
        with open(pid_file_path, 'w') as f:
            f.write(str(pid))
        if not quiet:
            print(f"   PID file: {pid_file_path}", file=sys.stderr)
    except Exception as e:
        if not quiet:
            print(f"⚠️  Warning: Could not write PID file: {e}", file=sys.stderr)


def get_process_group_id(pid: int) -> Optional[int]:
    """Get process group ID for a PID"""
    try:
        import os
        return os.getpgid(pid)
    except:
        return None


def kill_process_group(pgid: int):
    """Kill entire process group"""
    try:
        import os
        import signal
        os.killpg(pgid, signal.SIGTERM)
        time.sleep(1)
        try:
            os.killpg(pgid, signal.SIGKILL)
        except:
            pass
    except:
        pass


def run_command_mode(args, default_pattern: Pattern, use_color: bool, telemetry_collector=None, 
                     execution_id: Optional[str] = None, telemetry_start_time: Optional[float] = None,
                     initial_source_file: Optional[str] = None, success_pattern: Optional[Pattern] = None,
                     error_pattern: Optional[Pattern] = None):
    """
    Run earlyexit in command mode - execute a command and monitor its output
    
    Args:
        args: Argument namespace
        default_pattern: Default compiled regex pattern (used when no specific pattern for a stream)
        use_color: Whether to use color output
        telemetry_collector: Telemetry collector for recording match events
        execution_id: Execution ID for telemetry
        telemetry_start_time: Start time for telemetry timestamp offsets
        initial_source_file: Initial source file (can be updated dynamically)
        
    Returns:
        Exit code
    """
    # Setup auto-logging
    from earlyexit.auto_logging import setup_auto_logging
    stdout_log_path, stderr_log_path = setup_auto_logging(args, args.command, is_command_mode=True)
    
    # Open log files if auto-logging is enabled
    stdout_log_file = None
    stderr_log_file = None
    if stdout_log_path:
        try:
            # Open in append mode if requested (like tee -a)
            file_mode = 'a' if getattr(args, 'append', False) else 'w'
            stdout_log_file = open(stdout_log_path, file_mode)
            stderr_log_file = open(stderr_log_path, file_mode)
            
            # Display "Logging to:" message unless quiet or JSON mode
            if not args.quiet and not args.json:
                mode_msg = " (appending)" if file_mode == 'a' else ""
                print(f"📝 Logging to{mode_msg}:", file=sys.stderr)
                print(f"   stdout: {stdout_log_path}", file=sys.stderr)
                print(f"   stderr: {stderr_log_path}", file=sys.stderr)
            
            # Write environment variables to ~/.ee_env.$$ for easy access
            # Each shell session gets its own env file (isolated by parent PID)
            try:
                parent_pid = os.getppid()
                ee_env_file = os.path.expanduser(f"~/.ee_env.{parent_pid}")
                with open(ee_env_file, 'w') as f:
                    f.write("# earlyexit environment variables (auto-generated)\n")
                    f.write("# Load with: source ~/.ee_env.$$\n")
                    f.write(f"export EE_STDOUT_LOG='{stdout_log_path}'\n")
                    f.write(f"export EE_STDERR_LOG='{stderr_log_path}'\n")
                    if log_prefix:
                        f.write(f"export EE_LOG_PREFIX='{log_prefix}'\n")
            except Exception:
                pass  # Silent failure if can't write env file
                
        except Exception as e:
            if not args.quiet:
                print(f"⚠️  Warning: Could not create log files: {e}", file=sys.stderr)
            stdout_log_file = None
            stderr_log_file = None
    
    match_count = [0]  # Use list to make it mutable across threads
    match_type = ['none']  # Track which type matched: 'success', 'error', or 'none'
    post_match_lines = [0]  # Track lines captured after match
    timed_out = [False]  # Track if we timed out
    timeout_reason = [""]  # Track why we timed out
    detached_pid = [None]  # Track PID if we detach from subprocess
    stuck_detected = [False]  # Track if stuck detection triggered
    
    # Track output timing
    start_time = telemetry_start_time or time.time()
    last_output_time = [start_time]  # Shared across all streams
    first_output_seen = [False]
    first_stdout_time = [0.0]  # Timestamp when first stdout line occurs
    first_stderr_time = [0.0]  # Timestamp when first stderr line occurs
    last_stderr_time = [0.0]  # Timestamp of last stderr output
    stderr_seen = [False]  # Track if we've seen any stderr output
    match_timestamp = [0]  # Timestamp of first match (for delay-exit)
    
    # Source file container (mutable, can be updated from output)
    source_file_container = [initial_source_file]
    
    # Statistics for JSON output
    statistics = {
        'lines_processed': [0],  # Total lines
        'bytes_processed': [0],  # Total bytes
        'time_to_first_output': [None],  # Time to first line
        'time_to_match': [None],  # Time to first match
        'matched_line': [None],  # The line that matched
        'matched_line_number': [None],  # Line number of match
    }
    
    # Track pipes and file descriptors for cleanup
    pipes_to_close = []
    
    # Build pattern map: fd_num -> compiled pattern
    fd_patterns: Dict[int, Pattern] = {}
    
    # Parse fd-specific patterns
    if args.fd_patterns:
        flags = re.IGNORECASE if args.ignore_case else 0
        for fd_num, pattern_str in args.fd_patterns:
            try:
                fd_patterns[fd_num] = compile_pattern(pattern_str, flags, args.perl_regexp, 
                                                      args.word_regexp, args.line_regexp)
            except Exception as e:
                print(f"❌ Invalid regex pattern for fd {fd_num}: {e}", file=sys.stderr)
                return 3
    
    def timeout_callback(reason="timeout"):
        """Called when timeout expires"""
        timed_out[0] = True
        timeout_reason[0] = reason
        if process.poll() is None:  # Process still running
            # Check if detach-on-timeout is enabled
            if args.detach and args.detach_on_timeout:
                # Detach instead of killing
                detached_pid[0] = process.pid
                if not args.quiet:
                    if args.detach_group:
                        pgid = get_process_group_id(process.pid)
                        print(f"\n⏱️  Timeout - Detached from process group (PGID: {pgid}, PID: {process.pid})", file=sys.stderr)
                    else:
                        print(f"\n⏱️  Timeout - Detached from subprocess (PID: {process.pid})", file=sys.stderr)
                    print(f"   Subprocess continues running in background", file=sys.stderr)
                    if args.detach_group:
                        pgid = get_process_group_id(process.pid)
                        print(f"   Use 'kill -- -{pgid}' to stop process group", file=sys.stderr)
                    else:
                        print(f"   Use 'kill {process.pid}' to stop it later", file=sys.stderr)
                # Write PID file if requested
                if args.pid_file:
                    write_pid_file(process.pid, args.pid_file, args.quiet)
            else:
                # Normal timeout: kill subprocess
                try:
                    process.terminate()
                    try:
                        process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        process.kill()
                except (PermissionError, OSError):
                    # In sandbox or restricted environment, try kill directly
                    try:
                        process.kill()
                    except:
                        pass  # Process may have already exited
    
    def check_output_timeouts():
        """Monitor thread to check for idle and first-output timeouts"""
        start_time = time.time()
        
        while process.poll() is None and not timed_out[0]:
            current_time = time.time()
            
            # Check first output timeout
            if args.first_output_timeout and not first_output_seen[0]:
                if current_time - start_time >= args.first_output_timeout:
                    timeout_callback(f"no first output after {args.first_output_timeout}s")
                    break
            
            # Check idle timeout
            if args.idle_timeout:
                time_since_output = current_time - last_output_time[0]
                if time_since_output >= args.idle_timeout:
                    timeout_callback(f"no output for {args.idle_timeout}s")
                    break
            
            # Check every 100ms
            time.sleep(0.1)
    
    def check_stderr_idle():
        """Monitor thread to check for stderr idle timeout"""
        while process.poll() is None and not timed_out[0]:
            # Wait until we've seen stderr output
            if not stderr_seen[0]:
                time.sleep(0.1)
                continue
            
            current_time = time.time()
            time_since_stderr = current_time - last_stderr_time[0]
            
            # If stderr has been idle for the specified time, exit
            if time_since_stderr >= args.stderr_idle_exit:
                timed_out[0] = True
                timeout_reason[0] = f"stderr idle for {args.stderr_idle_exit}s"
                if not args.quiet:
                    print(f"\n⏸️  Stderr idle: No stderr output for {args.stderr_idle_exit}s (error messages complete)", file=sys.stderr)
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        process.kill()
                break
            
            # Check every 100ms
            time.sleep(0.1)
    
    try:
        # Set up file descriptors for monitoring
        # Standard: stdout=1, stderr=2
        # Custom: any fd >= 3
        fd_pipes: Dict[int, tuple] = {}  # fd_num -> (read_fd, write_fd)
        fd_streams: Dict[int, IO] = {}   # fd_num -> file object for reading
        
        # Create pipes for custom file descriptors
        if args.monitor_fds:
            for fd_num in args.monitor_fds:
                if fd_num >= 3:  # Only allow fd 3 and above
                    read_fd, write_fd = os.pipe()
                    fd_pipes[fd_num] = (read_fd, write_fd)
                    pipes_to_close.append(read_fd)
                    pipes_to_close.append(write_fd)
                    # Create file object for reading
                    fd_streams[fd_num] = os.fdopen(read_fd, 'r', errors='replace')
        
        # Prepare pass_fds for subprocess - include write ends of custom pipes
        pass_fds = [write_fd for _, write_fd in fd_pipes.values()]
        
        # Build subprocess kwargs
        subprocess_kwargs = {
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
            'shell': False,
        }
        
        # If we have custom FDs, we need to use preexec_fn to set them up
        if fd_pipes:
            def setup_fds():
                """Setup custom file descriptors in child process"""
                for fd_num, (read_fd, write_fd) in fd_pipes.items():
                    # Close read end in child
                    try:
                        os.close(read_fd)
                    except:
                        pass
                    # Duplicate write_fd to fd_num
                    try:
                        if write_fd != fd_num:
                            os.dup2(write_fd, fd_num)
                            os.close(write_fd)
                    except:
                        pass
            
            subprocess_kwargs['preexec_fn'] = setup_fds
            subprocess_kwargs['pass_fds'] = pass_fds
        
        # Wrap command with stdbuf if unbuffered flags are set
        command_to_run = args.command
        unbuffer_stdout = getattr(args, 'unbuffered', False) or getattr(args, 'stdout_unbuffered', False)
        unbuffer_stderr = getattr(args, 'unbuffered', False) or getattr(args, 'stderr_unbuffered', False)
        
        if unbuffer_stdout or unbuffer_stderr:
            stdbuf_args = ['stdbuf']
            if unbuffer_stdout:
                stdbuf_args.append('-o0')
            if unbuffer_stderr:
                stdbuf_args.append('-e0')
            command_to_run = stdbuf_args + args.command
            if args.verbose:
                print(f"[earlyexit] Wrapping command with: {' '.join(stdbuf_args)}", file=sys.stderr)
        
        # Start the subprocess
        process = subprocess.Popen(command_to_run, **subprocess_kwargs)
        
        # Close write ends of pipes in parent process
        for fd_num, (read_fd, write_fd) in fd_pipes.items():
            try:
                os.close(write_fd)
                pipes_to_close.remove(write_fd)
            except:
                pass
        
        # Inspect subprocess file descriptors to auto-detect source files
        # FD inspection is the most accurate method, so it overrides command arg inference
        if PSUTIL_AVAILABLE:
            # Give process a brief moment to open files, then inspect
            open_files = inspect_process_fds(process.pid, delay=0.05)
            if open_files:
                # Prefer FD inspection over command arg inference
                if not source_file_container[0]:
                    source_file_container[0] = open_files[0]
                    if args.verbose:
                        print(f"[earlyexit] Detected source file from subprocess FDs: {open_files[0]}", file=sys.stderr)
                else:
                    # Check if FD inspection found a different (better) file
                    # Prefer data files (.txt, .csv, .json) over scripts (.py, .js)
                    script_exts = ['.py', '.js', '.sh', '.rb', '.pl']
                    data_exts = ['.txt', '.csv', '.json', '.xml', '.yaml', '.yml', '.log']
                    
                    current_is_script = any(source_file_container[0].endswith(ext) for ext in script_exts)
                    fd_is_data = any(open_files[0].endswith(ext) for ext in data_exts)
                    
                    if current_is_script and fd_is_data:
                        # Override script with data file
                        if args.verbose:
                            print(f"[earlyexit] Overriding {source_file_container[0]} with FD-detected data file: {open_files[0]}", file=sys.stderr)
                        source_file_container[0] = open_files[0]
                    elif args.verbose and open_files[0] != source_file_container[0]:
                        print(f"[earlyexit] FD inspection found {open_files[0]}, keeping {source_file_container[0]}", file=sys.stderr)
        
        # Set up timeout timer if requested
        timeout_timer = None
        if args.timeout:
            timeout_timer = threading.Timer(args.timeout, lambda: timeout_callback("timeout"))
            timeout_timer.start()
        
        # Start output timeout monitor thread if needed
        output_timeout_thread = None
        if args.idle_timeout or args.first_output_timeout:
            output_timeout_thread = threading.Thread(target=check_output_timeouts, daemon=True)
            output_timeout_thread.start()
        
        # Start stderr idle monitor thread if needed
        stderr_idle_thread = None
        if args.stderr_idle_exit:
            stderr_idle_thread = threading.Thread(target=check_stderr_idle, daemon=True)
            stderr_idle_thread.start()
        
        # Monitor streams based on configuration
        threads = []
        
        # Determine which streams to monitor
        # Each entry: (stream, fd_num, label, pattern)
        streams_to_monitor = []
        
        if args.match_stderr == 'both':
            streams_to_monitor.extend([
                (process.stdout, 1, "stdout" if args.fd_prefix else "", 
                 fd_patterns.get(1, default_pattern)),
                (process.stderr, 2, "stderr" if args.fd_prefix else "", 
                 fd_patterns.get(2, default_pattern))
            ])
        elif args.match_stderr == 'stderr':
            streams_to_monitor.append((process.stderr, 2, "stderr" if args.fd_prefix else "", 
                                      fd_patterns.get(2, default_pattern)))
        else:  # stdout only
            streams_to_monitor.append((process.stdout, 1, "stdout" if args.fd_prefix else "", 
                                      fd_patterns.get(1, default_pattern)))
        
        # Add custom file descriptors to monitor
        if fd_streams:
            for fd_num, stream in fd_streams.items():
                fd_label = f"fd{fd_num}" if args.fd_prefix else ""
                # Use fd-specific pattern if available, otherwise use default
                pattern = fd_patterns.get(fd_num, default_pattern)
                streams_to_monitor.append((stream, fd_num, fd_label, pattern))
        
        # Create monitoring threads for all streams
        if len(streams_to_monitor) > 1 or fd_streams:
            # Multiple streams - use threads
            for stream, fd_num, label, pattern in streams_to_monitor:
                def make_monitor(s, fn, lbl, pat):
                    # Determine which log file to use based on fd_num
                    log_f = stdout_log_file if fn == 1 else stderr_log_file if fn == 2 else None
                    # Determine which first-time tracker to use
                    first_time = first_stdout_time if fn == 1 else first_stderr_time if fn == 2 else None
                    # Determine stderr tracking (only for fd 2)
                    stderr_time = last_stderr_time if fn == 2 else None
                    stderr_flag = stderr_seen if fn == 2 else None
                    def monitor():
                        try:
                            process_stream(s, pat, args, 0, match_count, use_color, lbl,
                                         last_output_time, first_output_seen, first_time,
                                         match_timestamp,
                                         telemetry_collector, execution_id, start_time, source_file_container,
                                         post_match_lines, log_f, statistics['lines_processed'],
                                         success_pattern, match_type, stuck_detected,
                                         stderr_time, stderr_flag)
                        except:
                            pass
                    return monitor
                
                thread = threading.Thread(
                    target=make_monitor(stream, fd_num, label, pattern),
                    daemon=True
                )
                thread.start()
                threads.append(thread)
            
            # Also create threads to drain non-monitored streams
            if args.match_stderr == 'stdout':
                # Drain stderr
                def drain_stderr():
                    try:
                        for line in process.stderr:
                            # Write to stderr log if enabled
                            if stderr_log_file:
                                stderr_log_file.write(line.decode('utf-8', errors='replace'))
                                stderr_log_file.flush()
                            if not args.json:
                                print(line.decode('utf-8', errors='replace'), end='', file=sys.stderr, flush=True)
                    except:
                        pass
                t = threading.Thread(target=drain_stderr, daemon=True)
                t.start()
                threads.append(t)
            
            elif args.match_stderr == 'stderr':
                # Drain stdout
                def drain_stdout():
                    try:
                        for line in process.stdout:
                            # Write to stdout log if enabled
                            if stdout_log_file:
                                stdout_log_file.write(line.decode('utf-8', errors='replace'))
                                stdout_log_file.flush()
                            if not args.json:
                                print(line.decode('utf-8', errors='replace'), end='', flush=True)
                    except:
                        pass
                t = threading.Thread(target=drain_stdout, daemon=True)
                t.start()
                threads.append(t)
            
            # Start progress indicator if requested
            progress_stop_event = None
            progress_thread = None
            if args.progress and not args.quiet and not args.json:
                progress_stop_event = threading.Event()
                progress_thread = threading.Thread(
                    target=show_progress_indicator,
                    args=(args, start_time, last_output_time, statistics['lines_processed'],
                          match_count, progress_stop_event),
                    daemon=True
                )
                progress_thread.start()
            
            # Wait for threads to complete or match to be found
            while any(t.is_alive() for t in threads):
                # Check for stuck detection
                if stuck_detected[0]:
                    # Stuck detected - cleanup and return
                    if timeout_timer:
                        timeout_timer.cancel()
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            process.kill()
                    return 2, 'stuck'
                
                if match_count[0] >= args.max_count:
                    # Check if delay-exit period has expired OR if enough lines captured
                    should_exit = False
                    if args.delay_exit and args.delay_exit > 0 and match_timestamp[0] > 0:
                        elapsed = time.time() - match_timestamp[0]
                        if elapsed >= args.delay_exit:
                            should_exit = True
                        elif post_match_lines[0] >= args.delay_exit_after_lines:
                            should_exit = True
                    elif args.delay_exit == 0 or match_timestamp[0] == 0:
                        # No delay or no match timestamp recorded yet, exit immediately
                        should_exit = True
                    
                    if should_exit:
                        # Cancel timeout timer
                        if timeout_timer:
                            timeout_timer.cancel()
                        
                        # Check if detach mode is enabled
                        if args.detach:
                            # Detach mode: Don't kill subprocess
                            detached_pid[0] = process.pid
                            if not args.quiet:
                                if args.detach_group:
                                    pgid = get_process_group_id(process.pid)
                                    print(f"\n🔓 Detached from process group (PGID: {pgid}, PID: {process.pid})", file=sys.stderr)
                                else:
                                    print(f"\n🔓 Detached from subprocess (PID: {process.pid})", file=sys.stderr)
                                print(f"   Subprocess continues running in background", file=sys.stderr)
                                if args.detach_group:
                                    pgid = get_process_group_id(process.pid)
                                    print(f"   Use 'kill -- -{pgid}' to stop process group", file=sys.stderr)
                                else:
                                    print(f"   Use 'kill {process.pid}' to stop it later", file=sys.stderr)
                            # Write PID file if requested
                            if args.pid_file:
                                write_pid_file(process.pid, args.pid_file, args.quiet)
                            # Don't terminate or kill - just break out of loop
                            break
                        else:
                            # Normal mode: Kill subprocess
                            if args.detach_group:
                                # Kill process group
                                pgid = get_process_group_id(process.pid)
                                if pgid:
                                    kill_process_group(pgid)
                                else:
                                    # Fallback to single process
                                    try:
                                        process.terminate()
                                    except (PermissionError, OSError):
                                        pass
                                    try:
                                        process.wait(timeout=1)
                                    except subprocess.TimeoutExpired:
                                        try:
                                            process.kill()
                                        except (PermissionError, OSError):
                                            pass
                            else:
                                try:
                                    process.terminate()
                                except (PermissionError, OSError):
                                    pass
                                try:
                                    process.wait(timeout=1)
                                except subprocess.TimeoutExpired:
                                    try:
                                        process.kill()
                                    except (PermissionError, OSError):
                                        pass
                            break
                if timed_out[0]:
                    break
                # Wait a bit (check frequently for delay expiration)
                time.sleep(0.1)
            
            # After threads complete, check one more time if we found a match and should detach
            # (Threads might have completed before we entered the while loop above)
            if match_count[0] >= args.max_count and args.detach and not detached_pid[0]:
                # Pattern matched and detach mode is enabled
                detached_pid[0] = process.pid
                if not args.quiet:
                    if args.detach_group:
                        pgid = get_process_group_id(process.pid)
                        print(f"\n🔓 Detached from process group (PGID: {pgid}, PID: {process.pid})", file=sys.stderr)
                    else:
                        print(f"\n🔓 Detached from subprocess (PID: {process.pid})", file=sys.stderr)
                    print(f"   Subprocess continues running in background", file=sys.stderr)
                    if args.detach_group:
                        pgid = get_process_group_id(process.pid)
                        print(f"   Use 'kill -- -{pgid}' to stop process group", file=sys.stderr)
                    else:
                        print(f"   Use 'kill {process.pid}' to stop it later", file=sys.stderr)
                # Write PID file if requested
                if args.pid_file:
                    write_pid_file(process.pid, args.pid_file, args.quiet)
        
        elif streams_to_monitor:
            # Single stream - use thread to allow delay monitoring
            stream, fd_num, label, pattern = streams_to_monitor[0]
            # Determine which log file to use based on fd_num
            log_file_for_stream = stdout_log_file if fd_num == 1 else stderr_log_file if fd_num == 2 else None
            # Determine which first-time tracker to use
            first_time_for_stream = first_stdout_time if fd_num == 1 else first_stderr_time if fd_num == 2 else None
            
            def monitor_single():
                try:
                    process_stream(stream, pattern, args, 0, match_count, use_color, label,
                                 last_output_time, first_output_seen, first_time_for_stream,
                                 match_timestamp,
                                 telemetry_collector, execution_id, start_time, source_file_container,
                                 post_match_lines, log_file_for_stream, statistics['lines_processed'],
                                 success_pattern, match_type)
                except:
                    pass
            
            monitor_thread = threading.Thread(target=monitor_single, daemon=True)
            monitor_thread.start()
            
            # Start progress indicator if requested
            progress_stop_event = None
            progress_thread = None
            if args.progress and not args.quiet and not args.json:
                progress_stop_event = threading.Event()
                progress_thread = threading.Thread(
                    target=show_progress_indicator,
                    args=(args, start_time, last_output_time, statistics['lines_processed'],
                          match_count, progress_stop_event),
                    daemon=True
                )
                progress_thread.start()
            
            # Monitor for match and delay expiration
            while monitor_thread.is_alive():
                if match_count[0] >= args.max_count:
                    # Check if delay-exit period has expired OR if enough lines captured
                    should_exit = False
                    if args.delay_exit and args.delay_exit > 0 and match_timestamp[0] > 0:
                        elapsed = time.time() - match_timestamp[0]
                        if elapsed >= args.delay_exit:
                            should_exit = True
                        elif post_match_lines[0] >= args.delay_exit_after_lines:
                            should_exit = True
                    elif args.delay_exit == 0 or match_timestamp[0] == 0:
                        # No delay or no match timestamp recorded yet, exit immediately
                        should_exit = True
                    
                    if should_exit:
                        # Cancel timeout timer
                        if timeout_timer:
                            timeout_timer.cancel()
                        
                        # Check if detach mode is enabled
                        if args.detach:
                            # Detach mode: Don't kill subprocess
                            detached_pid[0] = process.pid
                            if not args.quiet:
                                if args.detach_group:
                                    pgid = get_process_group_id(process.pid)
                                    print(f"\n🔓 Detached from process group (PGID: {pgid}, PID: {process.pid})", file=sys.stderr)
                                else:
                                    print(f"\n🔓 Detached from subprocess (PID: {process.pid})", file=sys.stderr)
                                print(f"   Subprocess continues running in background", file=sys.stderr)
                                if args.detach_group:
                                    pgid = get_process_group_id(process.pid)
                                    print(f"   Use 'kill -- -{pgid}' to stop process group", file=sys.stderr)
                                else:
                                    print(f"   Use 'kill {process.pid}' to stop it later", file=sys.stderr)
                            # Write PID file if requested
                            if args.pid_file:
                                write_pid_file(process.pid, args.pid_file, args.quiet)
                            # Don't terminate or kill - just break out of loop
                            break
                        else:
                            # Normal mode: Kill subprocess
                            if args.detach_group:
                                # Kill process group
                                pgid = get_process_group_id(process.pid)
                                if pgid:
                                    kill_process_group(pgid)
                                else:
                                    # Fallback to single process
                                    try:
                                        process.terminate()
                                    except (PermissionError, OSError):
                                        pass
                                    try:
                                        process.wait(timeout=1)
                                    except subprocess.TimeoutExpired:
                                        try:
                                            process.kill()
                                        except (PermissionError, OSError):
                                            pass
                            else:
                                try:
                                    process.terminate()
                                except (PermissionError, OSError):
                                    pass
                                try:
                                    process.wait(timeout=1)
                                except subprocess.TimeoutExpired:
                                    try:
                                        process.kill()
                                    except (PermissionError, OSError):
                                        pass
                            break
                if timed_out[0]:
                    break
                # Wait a bit (check frequently for delay expiration)
                time.sleep(0.1)
            
            # After thread completes, check one more time if we found a match and should detach
            # (Thread might have completed before we entered the while loop above)
            if match_count[0] >= args.max_count and args.detach and not detached_pid[0]:
                # Pattern matched and detach mode is enabled
                detached_pid[0] = process.pid
                if not args.quiet:
                    if args.detach_group:
                        pgid = get_process_group_id(process.pid)
                        print(f"\n🔓 Detached from process group (PGID: {pgid}, PID: {process.pid})", file=sys.stderr)
                    else:
                        print(f"\n🔓 Detached from subprocess (PID: {process.pid})", file=sys.stderr)
                    print(f"   Subprocess continues running in background", file=sys.stderr)
                    if args.detach_group:
                        pgid = get_process_group_id(process.pid)
                        print(f"   Use 'kill -- -{pgid}' to stop process group", file=sys.stderr)
                    else:
                        print(f"   Use 'kill {process.pid}' to stop it later", file=sys.stderr)
                # Write PID file if requested
                if args.pid_file:
                    write_pid_file(process.pid, args.pid_file, args.quiet)
            
            # If no match found, drain the other stream
            if match_count[0] < args.max_count:
                if args.match_stderr == 'stdout' and not args.json:
                    try:
                        for line in process.stderr:
                            print(line.decode('utf-8', errors='replace'), end='', file=sys.stderr, flush=True)
                    except:
                        pass
                elif args.match_stderr == 'stderr' and not args.json:
                    try:
                        for line in process.stdout:
                            print(line.decode('utf-8', errors='replace'), end='', flush=True)
                    except:
                        pass
        
        # Old code below - DISABLED (replaced by threaded monitoring above)
        if False:
            # This entire block is disabled - all monitoring now uses the threaded approach above
            # Kept for reference only, will be removed in future cleanup
            if args.match_stderr == 'both':
                # Monitor both streams in parallel
                stdout_lines = [0]
                stderr_lines = [0]
                
                def monitor_stdout():
                    try:
                        stdout_lines[0] = process_stream(
                            process.stdout, pattern, args, 0, match_count, use_color, "stdout",
                            None, None, first_stdout_time,
                            None, telemetry_collector, execution_id, start_time, source_file_container,
                            post_match_lines, stdout_log_file, statistics['lines_processed'],
                            success_pattern, match_type
                        )
                    except:
                        pass
                
                def monitor_stderr():
                    try:
                        stderr_lines[0] = process_stream(
                            process.stderr, pattern, args, 0, match_count, use_color, "stderr",
                            None, None, first_stderr_time,
                            None, telemetry_collector, execution_id, start_time, source_file_container,
                            post_match_lines, stderr_log_file, statistics['lines_processed'],
                            success_pattern, match_type
                        )
                    except:
                        pass
                
                stdout_thread = threading.Thread(target=monitor_stdout, daemon=True)
                stderr_thread = threading.Thread(target=monitor_stderr, daemon=True)
                
                stdout_thread.start()
                stderr_thread.start()
                
                # Wait for threads to complete or match to be found
                while stdout_thread.is_alive() or stderr_thread.is_alive():
                    if match_count[0] >= args.max_count:
                        # Kill the process on match
                        if timeout_timer:
                            timeout_timer.cancel()
                        process.terminate()
                        try:
                            process.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            process.kill()
                        break
                    if timed_out[0]:
                        break
                    stdout_thread.join(timeout=0.1)
                    if stderr_thread.is_alive():
                        stderr_thread.join(timeout=0.1)
                
            elif args.match_stderr == 'stderr':
                # Only monitor stderr
                try:
                    process_stream(process.stderr, pattern, args, 0, match_count, use_color, "stderr",
                                 None, None, first_stderr_time,
                                 None, telemetry_collector, execution_id, start_time, source_file_container,
                                 post_match_lines, stderr_log_file, statistics['lines_processed'],
                                 success_pattern, match_type, stuck_detected,
                                 last_stderr_time, stderr_seen)
                except:
                    pass
                # Drain stdout
                try:
                    for line in process.stdout:
                        # Write to stdout log if enabled
                        if stdout_log_file:
                            stdout_log_file.write(line.decode('utf-8', errors='replace'))
                            stdout_log_file.flush()
                        if not args.json:
                            print(line.decode('utf-8', errors='replace'), end='', flush=True)
                except:
                    pass
            else:
                # Only monitor stdout (default)
                try:
                    process_stream(process.stdout, pattern, args, 0, match_count, use_color, "stdout",
                                 None, None, first_stdout_time,
                                 None, telemetry_collector, execution_id, start_time, source_file_container,
                                 post_match_lines, stdout_log_file, statistics['lines_processed'],
                                 success_pattern, match_type, stuck_detected,
                                 None, None)
                except:
                    pass
                # Drain stderr (only if we didn't detach)
                if not (args.detach and detached_pid[0]):
                    try:
                        for line in process.stderr:
                            # Write to stderr log if enabled
                            if stderr_log_file:
                                stderr_log_file.write(line.decode('utf-8', errors='replace'))
                                stderr_log_file.flush()
                            if not args.json:
                                print(line.decode('utf-8', errors='replace'), end='', file=sys.stderr, flush=True)
                    except:
                        pass
        
        # Cancel timeout if still running
        if timeout_timer:
            timeout_timer.cancel()
        
        # If we detached, don't wait for process - return immediately
        if args.detach and detached_pid[0]:
            # Close our end of the pipes so subprocess can continue independently
            try:
                process.stdout.close()
            except:
                pass
            try:
                process.stderr.close()
            except:
                pass
            return 4  # Detached (subprocess still running)
        
        # Wait for process to complete (only if we didn't detach)
        try:
            return_code = process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            return_code = process.wait()
        
        # Check if we timed out
        if timed_out[0]:
            # Check if we detached on timeout
            if args.detach and args.detach_on_timeout and detached_pid[0]:
                return 4  # Detached on timeout (subprocess still running)
            else:
                if not args.quiet:
                    if timeout_reason[0]:
                        print(f"\n⏱️  Timeout: {timeout_reason[0]}", file=sys.stderr)
                    else:
                        print(f"\n⏱️  Timeout exceeded", file=sys.stderr)
                return 2
        
        # Determine exit code based on match type
        # Check if user explicitly specified dual-pattern mode via args
        using_dual_patterns = bool(getattr(args, 'success_pattern', None) or 
                                   getattr(args, 'error_pattern', None))
        
        if using_dual_patterns:
            # Dual-pattern mode: success/error patterns specified
            if match_type[0] == 'success':
                return 0  # Success pattern matched
            elif match_type[0] == 'error':
                return 1  # Error pattern matched
            elif match_type[0] == 'none':
                # No match in dual-pattern mode
                if success_pattern and not error_pattern:
                    # Success-pattern only: no success found = failure
                    return 1
                elif error_pattern and not success_pattern:
                    # Error-pattern only: no error found = success
                    return 0
                else:
                    # Both patterns specified, neither matched
                    return 1
        else:
            # Traditional grep mode: use grep exit code convention
            if match_count[0] >= args.max_count:
                return 0  # Pattern matched - max count reached
            elif match_count[0] > 0:
                return 0  # At least one match found
            else:
                return 1  # No match found
            
    except FileNotFoundError:
        print(f"❌ Command not found: {args.command[0]}", file=sys.stderr)
        return 3
    except TimeoutError:
        # Timeout - check if we should detach
        if args.detach and args.detach_on_timeout:
            # Detach mode: don't kill, just exit
            # Note: process is still running at this point
            if not args.quiet:
                if args.detach_group:
                    try:
                        pgid = get_process_group_id(process.pid)
                        print(f"\n⏱️  Timeout - Detached from process group (PGID: {pgid}, PID: {process.pid})", file=sys.stderr)
                        print(f"   Use 'kill -- -{pgid}' to stop process group", file=sys.stderr)
                    except:
                        print(f"\n⏱️  Timeout - Detached from subprocess (PID: {process.pid})", file=sys.stderr)
                        print(f"   Use 'kill {process.pid}' to stop it later", file=sys.stderr)
                else:
                    print(f"\n⏱️  Timeout - Detached from subprocess (PID: {process.pid})", file=sys.stderr)
                    print(f"   Use 'kill {process.pid}' to stop it later", file=sys.stderr)
                print(f"   Subprocess continues running in background", file=sys.stderr)
            # Write PID file if requested
            if args.pid_file:
                write_pid_file(process.pid, args.pid_file, args.quiet)
            return 4  # Detached on timeout (subprocess still running)
        else:
            # Normal timeout: show message and return 2
            if not args.quiet:
                print(f"⏱️  Timeout exceeded", file=sys.stderr)
            return 2
    except Exception as e:
        print(f"❌ Error running command: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 3
    finally:
        # Stop progress indicator if it was started
        if 'progress_stop_event' in locals() and progress_stop_event:
            progress_stop_event.set()
        if 'progress_thread' in locals() and progress_thread:
            progress_thread.join(timeout=1)
        
        # Clean up log files
        if stdout_log_file:
            try:
                stdout_log_file.close()
            except:
                pass
        if stderr_log_file:
            try:
                stderr_log_file.close()
            except:
                pass
        
        # Gzip log files if requested
        if getattr(args, 'gzip', False) and stdout_log_path:
            try:
                from earlyexit.auto_logging import gzip_log_files
                gzip_log_files(stdout_log_path, stderr_log_path, quiet=args.quiet)
            except Exception:
                pass  # Silently fail - don't disrupt execution
        
        # Clean up any remaining open file descriptors
        for fd in pipes_to_close:
            try:
                os.close(fd)
            except:
                pass


def test_pattern_mode(args, pattern: Pattern, success_pattern: Optional[Pattern] = None, 
                      error_pattern: Optional[Pattern] = None, use_color: bool = False):
    """
    Test pattern mode: Read from stdin, show matches with line numbers and statistics
    
    Args:
        args: Argument namespace
        pattern: Compiled regex pattern (may be None if using success/error patterns)
        success_pattern: Compiled success pattern (optional)
        error_pattern: Compiled error pattern (optional)
        use_color: Whether to use color output
        
    Returns:
        Exit code: 0 if matches found, 1 if no matches
    """
    import sys
    
    # Statistics
    total_lines = 0
    matched_lines = []  # List of (line_num, line_text, match_type)
    excluded_lines = 0
    success_matches = 0
    error_matches = 0
    
    # Read from stdin
    try:
        for line_num, line in enumerate(sys.stdin, 1):
            total_lines += 1
            line_stripped = line.rstrip('\n\r')
            
            # Check exclusion patterns first
            excluded = False
            if hasattr(args, 'exclude_patterns') and args.exclude_patterns:
                for exclude_pattern_str in args.exclude_patterns:
                    try:
                        flags = re.IGNORECASE if args.ignore_case else 0
                        exclude_pattern = re.compile(exclude_pattern_str, flags)
                        if exclude_pattern.search(line_stripped):
                            excluded = True
                            excluded_lines += 1
                            break
                    except re.error:
                        pass
            
            if excluded:
                continue
            
            # Check patterns
            match_type = None
            matched = False
            
            # Check success pattern first (if provided)
            if success_pattern:
                if success_pattern.search(line_stripped):
                    matched = True
                    match_type = 'success'
                    success_matches += 1
            
            # Check error pattern (if provided and no success match)
            if not matched and error_pattern:
                if error_pattern.search(line_stripped):
                    matched = True
                    match_type = 'error'
                    error_matches += 1
            
            # Check traditional pattern (if no dual-pattern match)
            if not matched and pattern and not (success_pattern or error_pattern):
                if pattern.search(line_stripped):
                    matched = True
                    match_type = 'match'
            
            # Apply invert match if requested (only for traditional patterns)
            if args.invert_match and not (success_pattern or error_pattern) and pattern:
                matched = not matched
                match_type = 'invert_match' if matched else None
            
            # Record match
            if matched:
                matched_lines.append((line_num, line_stripped, match_type))
    
    except KeyboardInterrupt:
        pass  # Allow graceful exit with Ctrl+C
    
    # Display results
    print(file=sys.stderr)
    print("=" * 70, file=sys.stderr)
    print("Pattern Test Results", file=sys.stderr)
    print("=" * 70, file=sys.stderr)
    print(file=sys.stderr)
    
    # Display statistics
    print(f"📊 Statistics:", file=sys.stderr)
    print(f"   Total lines:     {total_lines:,}", file=sys.stderr)
    print(f"   Matched lines:   {len(matched_lines):,}", file=sys.stderr)
    if excluded_lines > 0:
        print(f"   Excluded lines:  {excluded_lines:,}", file=sys.stderr)
    if success_pattern and error_pattern:
        print(f"   Success matches: {success_matches:,}", file=sys.stderr)
        print(f"   Error matches:   {error_matches:,}", file=sys.stderr)
    print(file=sys.stderr)
    
    # Display matched lines
    if matched_lines:
        print(f"✅ Pattern matched {len(matched_lines)} time(s):", file=sys.stderr)
        print(file=sys.stderr)
        
        # Show up to 20 matches (to avoid flooding output)
        display_limit = 20
        for i, (line_num, line_text, match_type) in enumerate(matched_lines[:display_limit]):
            # Color code based on match type
            if use_color:
                if match_type == 'success':
                    prefix = f"\033[32mLine {line_num:6d}\033[0m:"  # Green
                elif match_type == 'error':
                    prefix = f"\033[31mLine {line_num:6d}\033[0m:"  # Red
                else:
                    prefix = f"\033[33mLine {line_num:6d}\033[0m:"  # Yellow
            else:
                prefix = f"Line {line_num:6d}:"
            
            print(f"{prefix}  {line_text}", file=sys.stderr)
        
        if len(matched_lines) > display_limit:
            print(file=sys.stderr)
            print(f"... and {len(matched_lines) - display_limit} more matches", file=sys.stderr)
        
        print(file=sys.stderr)
        print(f"💡 Tip: Use with --exclude to filter false positives", file=sys.stderr)
        return 0  # Pattern matched
    else:
        print(f"❌ No matches found", file=sys.stderr)
        print(file=sys.stderr)
        print(f"💡 Tips:", file=sys.stderr)
        print(f"   - Check pattern syntax (use -i for case-insensitive)", file=sys.stderr)
        print(f"   - Try a broader pattern", file=sys.stderr)
        print(f"   - Verify input contains expected text", file=sys.stderr)
        return 1  # No match


def main():
    """Main entry point"""
    # Support EARLYEXIT_OPTIONS environment variable (like GREP_OPTIONS)
    # Insert env options at the beginning so CLI args can override them
    env_options = os.getenv('EARLYEXIT_OPTIONS', '').strip()
    if env_options:
        import shlex
        env_args = shlex.split(env_options)
        # Insert after program name but before user args
        sys.argv[1:1] = env_args
    
    parser = argparse.ArgumentParser(
        description='''Early exit pattern matching - exit immediately when pattern matches

Like grep + timeout combined, but with hang detection, stderr monitoring, stuck detection,
pattern exclusions, success/error patterns, and more.

📚 For comprehensive examples and use cases:
   GitHub: https://github.com/rsleedbx/earlyexit
   Real-world examples: https://github.com/rsleedbx/earlyexit/blob/master/docs/REAL_WORLD_EXAMPLES.md''',
        allow_abbrev=False,  # Prevent --id from matching --idle-timeout, etc.
        epilog="""
Examples:
  # Pipe mode (read from stdin)
  long_running_command | earlyexit -t 30 'Error|Failed'
  terraform apply | earlyexit -i -t 600 'error'
  
  # Command mode (run command directly, like timeout)
  earlyexit -t 60 'Error' sleep 120
  earlyexit -t 300 'FAILED' pytest -v
  earlyexit -t 600 'error' terraform apply -auto-approve
  
  # Use -- separator when command has flags (recommended)
  earlyexit -- mist validate --id 123 --step 2
  earlyexit 'ERROR' -- kubectl get pods --all-namespaces
  
  # Monitor both stdout and stderr (default)
  earlyexit 'Error' -- ./app
  
  # Monitor only stderr
  earlyexit --stderr 'Error' -- ./build.sh
  
  # Monitor only stdout
  earlyexit --stdout 'Error' -- ./build.sh
  
  # Monitor custom file descriptors (fd 3, 4, etc.)
  earlyexit --fd 3 'Error' ./app
  earlyexit --fd 3 --fd 4 --fd-prefix 'Warning' ./app
  
  # Different patterns for different file descriptors
  earlyexit --fd-pattern 1 'FAILED' --fd-pattern 2 'ERROR' ./test.sh
  earlyexit --fd 3 --fd-pattern 3 'DEBUG.*Error' --fd-prefix 'Error' ./app
  
  # Timeout if no output for 30 seconds (stall detection)
  earlyexit -I 30 'Error' ./long-running-app
  
  # Timeout if app doesn't start outputting within 10 seconds
  earlyexit -F 10 'Error' ./slow-startup-app
  
  # Combine timeouts: overall 300s, idle 30s, first output 10s
  earlyexit -t 300 -I 30 -F 10 'Error' ./app
  
  # After error match, wait 10s for error context (default in command mode)
  earlyexit 'Error' ./app
  
  # Quick exit (2s delay)
  earlyexit --delay-exit 2 'FATAL' ./app
  
  # Disable delay (exit immediately on match)
  earlyexit --delay-exit 0 'Error' ./app
  
  # Match up to 3 errors then exit
  pytest | earlyexit -m 3 'FAILED'
  
  # Invert match - exit when pattern DOESN'T match
  health_check | earlyexit -v 'OK' -t 10
  
  # Stuck detection - exit if same line repeats
  earlyexit --max-repeat 5 'ERROR' -- mist dml monitor --id xyz
  earlyexit --max-repeat 5 --stuck-ignore-timestamps 'ERROR' -- command
  
  # Stderr idle exit - exit after error messages finish
  earlyexit --stderr-idle-exit 1 'SUCCESS' -- python script.py
  earlyexit --stderr-idle-exit 1 --exclude 'WARNING|DEBUG' 'SUCCESS' -- command
  
  # Pattern exclusions - filter false positives
  earlyexit 'Error' --exclude 'Error: early error detection' -- terraform apply
  
  # Success/error patterns - exit on first match
  earlyexit --success-pattern 'deployed' --error-pattern 'ERROR|FAIL' -- command
  
  # Pattern testing - test against logs without running command
  cat terraform.log | earlyexit 'Error' --test-pattern
  
  # Access logs automatically (with timeout, auto-logging enabled)
  earlyexit -t 300 --max-repeat 5 'ERROR' -- command
  source ~/.ee_env.$$ && cat $EE_STDOUT_LOG

📚 More Examples:
  GitHub: https://github.com/rsleedbx/earlyexit
  Real-world examples: https://github.com/rsleedbx/earlyexit/blob/master/docs/REAL_WORLD_EXAMPLES.md
  13 scenarios where ee excels over grep/timeout

Exit codes (grep convention, default):
  0 - Pattern matched (error found, subprocess terminated)
  1 - No match found (success, subprocess completed normally)
  2 - Timeout exceeded (subprocess terminated, unless --detach-on-timeout)
  3 - Command not found or other error
  4 - Detached (subprocess still running, --detach or --detach-on-timeout)
  130 - Interrupted (Ctrl+C)

Exit codes (Unix convention, --unix-exit-codes):
  0 - Success (no error pattern found, subprocess completed normally)
  1 - Failure (error pattern matched, subprocess terminated)
  2 - Timeout exceeded (unchanged)
  3 - Command not found or other error (unchanged)
  4 - Detached (unchanged)
  130 - Interrupted (Ctrl+C, unchanged)
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Positional arguments
    parser.add_argument('pattern', nargs='?', default=None,
                       help='Regular expression pattern to match (optional if -t/-I/-F provided)')
    parser.add_argument('command', nargs='*',
                       help='Command to run (if not reading from stdin). Use -- to separate earlyexit flags from command flags.')
    
    # === Arguments in alphabetical order (by long form) ===
    
    parser.add_argument('-a', '--append', action='store_true',
                       help='Append to log files instead of overwriting (like tee -a)')
    parser.add_argument('-l', '--log', dest='force_logging', action='store_true',
                       help='Force logging to files (enabled automatically with timeouts)')
    parser.add_argument('--no-auto-log', '--no-log', action='store_true',
                       help='Disable automatic log file creation')
    parser.add_argument('--auto-tune', action='store_true',
                       help='Automatically select optimal parameters based on telemetry (experimental)')
    parser.add_argument('--color', choices=['always', 'auto', 'never'], default='auto',
                       help='Colorize matched text (default: auto)')
    parser.add_argument('--unix-exit-codes', action='store_true',
                       help='Use Unix exit code convention: 0=success (no error found), 1=error found (pattern matched). '
                            'Default uses grep convention: 0=match, 1=no match. Exit codes 2-4 unchanged.')
    parser.add_argument('--json', action='store_true',
                       help='Output results as JSON (suppresses normal output). '
                            'Includes exit code, pattern match details, duration, and statistics. '
                            'Useful for programmatic parsing and integration.')
    parser.add_argument('--progress', action='store_true',
                       help='Show progress indicator with elapsed time, lines processed, and last output time. '
                            'Updates every 2 seconds on stderr. Automatically disabled with --quiet or --json.')
    parser.add_argument('-A', '--after-context', '--delay-exit', type=float, metavar='SECONDS', 
                       dest='delay_exit', default=None,
                       help='After match, continue reading for N seconds to capture error context (like grep -A but time-based, default: 10 for command mode, 0 for pipe mode)')
    parser.add_argument('-B', '--before-context', type=int, metavar='NUM', default=0,
                       help='Print NUM lines of leading context before matching lines (like grep -B)')
    parser.add_argument('-C', '--context', type=int, metavar='NUM', default=None,
                       help='Print NUM lines of output context (sets both -B and -A, like grep -C)')
    parser.add_argument('--delay-exit-after-lines', type=int, metavar='LINES', default=100,
                       help='After match, exit early if N lines captured (default: 100). Whichever comes first: time or lines.')
    parser.add_argument('-D', '--detach', action='store_true',
                       help='Exit without killing subprocess when pattern matches (command mode only). '
                            'Subprocess continues running. PID printed to stderr. Exit code: 4')
    parser.add_argument('--detach-group', action='store_true',
                       help='Detach entire process group (requires --detach). Useful for commands that spawn child processes.')
    parser.add_argument('--detach-on-timeout', action='store_true',
                       help='Detach instead of killing on timeout (requires --detach). Exit code: 4 instead of 2.')
    parser.add_argument('-E', '--extended-regexp', action='store_true',
                       help='Extended regex (default Python re module)')
    parser.add_argument('--pid-file', metavar='PATH',
                       help='Write subprocess PID to file (requires --detach). Useful for cleanup scripts.')
    parser.add_argument('-w', '--word-regexp', action='store_true',
                       help='Match whole words only (like grep -w, wraps pattern with \\b)')
    parser.add_argument('-x', '--line-regexp', action='store_true',
                       help='Match whole lines only (like grep -x, wraps pattern with ^$)')
    parser.add_argument('--fd', dest='monitor_fds', action='append', type=int, metavar='N',
                       help='Monitor file descriptor N (can be used multiple times, e.g., --fd 3 --fd 4)')
    parser.add_argument('--fd-pattern', dest='fd_patterns', action='append', nargs=2, 
                       metavar=('FD', 'PATTERN'),
                       help='Set specific pattern for file descriptor FD (e.g., --fd-pattern 3 "ERROR" --fd-pattern 2 "FATAL")')
    parser.add_argument('--fd-prefix', action='store_true',
                       help='Prefix output with stream labels [stdout]/[stderr]/[fd3] etc.')
    parser.add_argument('--file-prefix', metavar='PREFIX',
                       help='Save output to log files. Behavior: (1) No extension → PREFIX.log/PREFIX.errlog, '
                            '(2) Ends with .log or .out → exact filename + .err for stderr. '
                            'Examples: /tmp/test → test.log/test.errlog; /tmp/test.log → test.log/test.err')
    parser.add_argument('-F', '--first-output-timeout', type=float, metavar='SECONDS',
                       help='Timeout if first output not seen within N seconds (startup detection)')
    parser.add_argument('-z', '--gzip', action='store_true',
                       help='Compress log files with gzip after command completes (like tar -z, rsync -z). Saves 70-90% space.')
    parser.add_argument('-i', '--ignore-case', action='store_true',
                       help='Case-insensitive matching')
    parser.add_argument('-X', '--exclude', action='append', metavar='PATTERN', dest='exclude_patterns',
                       help='Exclude lines matching this pattern (can be repeated for multiple exclusions)')
    parser.add_argument('-s', '--success-pattern', metavar='PATTERN', dest='success_pattern',
                       help='Pattern indicating successful completion (exits with code 0)')
    parser.add_argument('-e', '--error-pattern', metavar='PATTERN', dest='error_pattern',
                       help='Pattern indicating error/failure (exits with code 1)')
    parser.add_argument('-I', '--idle-timeout', type=float, metavar='SECONDS',
                       help='Timeout if no output for N seconds (stall detection)')
    parser.add_argument('-v', '--invert-match', action='store_true',
                       help='Invert match - select non-matching lines')
    parser.add_argument('-n', '--line-number', action='store_true',
                       help='Prefix output with line number')
    parser.add_argument('--list-profiles', action='store_true',
                       help='List available profiles and exit')
    parser.add_argument('--log-dir', metavar='DIR', default='/tmp',
                       help='Directory for auto-generated logs (default: /tmp, used with --auto-log)')
    parser.add_argument('-m', '--max-count', type=int, default=1, metavar='NUM',
                       help='Stop after NUM matches (default: 1, like grep -m)')
    parser.add_argument('--max-repeat', type=int, metavar='NUM',
                       help='Exit if the same line repeats NUM times consecutively (stuck detection). '
                            'Use with --stuck-ignore-timestamps to ignore timestamp changes.')
    parser.add_argument('--stuck-ignore-timestamps', action='store_true',
                       help='Strip common timestamp patterns when checking for repeated lines (requires --max-repeat). '
                            'Normalizes timestamps like [HH:MM:SS], YYYY-MM-DD, etc.')
    parser.add_argument('--stuck-pattern', metavar='REGEX',
                       help='Extract specific part of line to check for repeating (requires --max-repeat). '
                            'Example: "RUNNING\\s+IDLE\\s+\\d+\\s+N/A" watches only status indicators. '
                            'If pattern matches, uses the match for comparison. If not, uses full line.')
    parser.add_argument('--stderr-idle-exit', type=float, metavar='SECONDS',
                       help='Exit after stderr has been idle for N seconds (after seeing stderr output). '
                            'Useful for detecting when error messages have finished printing. '
                            'Use --exclude to filter out non-error stderr output (warnings, debug logs).')
    parser.add_argument('--no-telemetry', action='store_true',
                       help='Disable telemetry collection (also: EARLYEXIT_NO_TELEMETRY=1). No SQLite database created when disabled.')
    parser.add_argument('-P', '--perl-regexp', action='store_true',
                       help='Perl-compatible regex (requires regex module)')
    parser.add_argument('--profile', metavar='NAME',
                       help='Use a predefined profile (e.g., --profile npm, --profile pytest). Use --list-profiles to see available profiles.')
    parser.add_argument('-q', '--quiet', action='store_true',
                       help='Quiet mode - suppress all output to terminal (like grep -q). Log files still created if auto-logging enabled.')
    parser.add_argument('--show-profile', metavar='NAME',
                       help='Show details about a profile and exit')
    parser.add_argument('--source-file', metavar='FILE',
                       help='Source file being processed (for telemetry, auto-detected if possible)')
    parser.add_argument('--stderr', dest='match_stderr', action='store_const',
                       const='stderr', default='both',
                       help='Match pattern against stderr only (command mode only)')
    parser.add_argument('--stderr-prefix', dest='fd_prefix', action='store_true',
                       help='Alias for --fd-prefix (for backward compatibility)')
    parser.add_argument('--test-pattern', action='store_true',
                       help='Test pattern mode: read from stdin, show matches with line numbers and statistics (does not run a command)')
    parser.add_argument('--stdout', dest='match_stderr', action='store_const', 
                       const='stdout', default='both',
                       help='Match pattern against stdout only (command mode only)')
    parser.add_argument('-t', '--timeout', type=float, metavar='SECONDS',
                       help='Overall timeout in seconds (default: no timeout)')
    parser.add_argument('-u', '--unbuffered', action='store_true', default=True,
                       help='Force unbuffered stdout/stderr for subprocess (DEFAULT, like stdbuf -o0 -e0). Ensures real-time output.')
    parser.add_argument('--buffered', dest='unbuffered', action='store_false',
                       help='Allow subprocess to use default buffering (disables real-time output, useful for high-throughput commands)')
    parser.add_argument('--stdout-unbuffered', action='store_true',
                       help='Force unbuffered stdout only for subprocess (advanced, use -u for both)')
    parser.add_argument('--stderr-unbuffered', action='store_true',
                       help='Force unbuffered stderr only for subprocess (advanced, use -u for both)')
    parser.add_argument('--verbose', action='store_true',
                       help='Verbose output (show debug information)')
    parser.add_argument('--version', action='version', version='%(prog)s 0.0.4')
    
    # Pre-process sys.argv to handle optional pattern with '--' separator
    # If '--' separator is present but no pattern before it, insert 'NONE'
    import sys as sys_module
    argv = sys_module.argv[1:]  # Skip program name
    
    # Check if any timeout option is present
    has_timeout_option = any(opt in argv for opt in ['-t', '--timeout', '-I', '--idle-timeout', '-F', '--first-output-timeout'])
    
    # Check if '--' is present and is the first positional argument (no pattern before it)
    # Positional args come after all options
    if '--' in argv:
        # Find the position of '--'
        separator_idx = argv.index('--')
        
        # Check if everything before '--' is an option (starts with '-') or option value
        # We need to determine if there's a pattern before '--'
        is_first_positional = True
        skip_next = False
        for i in range(separator_idx):
            arg = argv[i]
            if skip_next:
                skip_next = False
                continue
            if arg.startswith('-'):
                # It's an option
                # Check if this option takes a value (not a flag)
                if arg in ['-t', '--timeout', '-I', '--idle-timeout', '-F', '--first-output-timeout', 
                          '-m', '--max-count', '--delay-exit', '--fd', '--source-file', '--pid-file',
                          '--file-prefix', '--log-dir', '--profile', '--fd-pattern', '-A', '-B', '-C',
                          '--delay-exit-after-lines', '-s', '--success-pattern', '-e', '--error-pattern',
                          '-X', '--exclude'] or \
                   (arg.startswith('-') and '=' in arg):
                    # This option takes a value
                    if '=' not in arg:
                        skip_next = True  # Next arg is the value
                continue
            else:
                # Non-option argument before '--' - this is the pattern
                is_first_positional = False
                break
        
        if is_first_positional:
            # No pattern before '--', insert 'NONE' 
            # This allows: ee -- command (timeout only mode)
            # Or: ee -t 30 -- command (explicit timeout with no pattern)
            argv.insert(separator_idx, 'NONE')
    
    # Use parse_known_args to allow commands with their own flags (like --id, --step)
    # Any unknown options will be treated as part of the command
    args, unknown = parser.parse_known_args(argv)
    
    # Add unknown arguments to the command list
    # This allows: ee mist validate --id 123 --step 2
    # Where --id and --step are treated as part of the command, not earlyexit options
    if unknown:
        if args.command is None:
            args.command = []
        args.command.extend(unknown)
    
    # Set default for match_stderr if not specified (parse_known_args doesn't set defaults properly for store_const)
    if not hasattr(args, 'match_stderr') or args.match_stderr is None:
        args.match_stderr = 'both'
    
    # Automatically enable quiet mode when JSON output is requested
    # (JSON output should be the only thing on stdout)
    if hasattr(args, 'json') and args.json:
        args.quiet = True
    
    # Handle profile-related flags first (before other validation)
    if hasattr(args, 'list_profiles') and args.list_profiles:
        try:
            from earlyexit.profiles import print_profile_list
            print_profile_list(show_validation=True)
        except ImportError:
            print("❌ Profiles module not available", file=sys.stderr)
        return 0
    
    if hasattr(args, 'show_profile') and args.show_profile:
        try:
            from earlyexit.profiles import print_profile_details
            print_profile_details(args.show_profile)
        except ImportError:
            print("❌ Profiles module not available", file=sys.stderr)
        return 0
    
    # Apply profile if specified
    if hasattr(args, 'profile') and args.profile:
        try:
            from earlyexit.profiles import get_profile, apply_profile_to_args
            profile = get_profile(args.profile)
            if not profile:
                print(f"❌ Profile '{args.profile}' not found", file=sys.stderr)
                print("\nAvailable profiles (use --list-profiles for details):", file=sys.stderr)
                from earlyexit.profiles import list_profiles
                for name in sorted(list_profiles().keys()):
                    print(f"  • {name}", file=sys.stderr)
                return 3
            
            # Convert 'NONE' to None before applying profile (so profile pattern can be applied)
            if args.pattern == 'NONE':
                args.pattern = None
            
            # Show which profile is being used
            if not (hasattr(args, 'quiet') and args.quiet):
                print(f"📋 Using profile: {args.profile}", file=sys.stderr)
                if profile.get('validation'):
                    f1 = profile['validation'].get('f1_score', 0)
                    print(f"   F1 Score: {f1:.2%} | {profile.get('recommendation', 'N/A')}", file=sys.stderr)
            
            # Apply profile settings
            args = apply_profile_to_args(profile, args)
        except ImportError:
            print("❌ Profiles module not available", file=sys.stderr)
            return 3
    
    # Validate arguments
    # Handle missing pattern - default to timeout-only mode if timeout options provided
    no_pattern_mode = False
    original_pattern = args.pattern
    
    # Treat 'NONE' (from -- preprocessing) as None
    if args.pattern == 'NONE':
        args.pattern = None
    
    if args.pattern is None:
        # Pattern not provided - check if timeout options are present or dual patterns are used
        has_timeout = args.timeout or args.idle_timeout or args.first_output_timeout
        has_command = len(args.command) > 0
        has_dual_patterns = bool(getattr(args, 'success_pattern', None) or getattr(args, 'error_pattern', None))
        
        if has_dual_patterns:
            # Using dual-pattern mode (success/error patterns) - set dummy pattern to avoid watch mode
            args.pattern = '__DUAL_PATTERN_MODE__'
            original_pattern = '__DUAL_PATTERN_MODE__'
        elif has_timeout:
            # Timeout provided, pattern optional - use timeout-only mode
            no_pattern_mode = True
            args.pattern = '(?!.*)'  # Negative lookahead that always fails
            original_pattern = 'NONE'
            if not args.quiet:
                # Show which timeout is active
                timeout_info = []
                if args.timeout:
                    timeout_info.append(f"overall: {args.timeout}s")
                if args.idle_timeout:
                    timeout_info.append(f"idle: {args.idle_timeout}s")
                if args.first_output_timeout:
                    timeout_info.append(f"first-output: {args.first_output_timeout}s")
                print(f"ℹ️  Timeout-only mode (no pattern specified) - {', '.join(timeout_info)}", file=sys.stderr)
        elif not has_command:
            # No pattern, no timeout, no command (pipe mode without input) - this is an error
            print("❌ Error: PATTERN is required", file=sys.stderr)
            print("", file=sys.stderr)
            print("Provide either:", file=sys.stderr)
            print("  1. A pattern: earlyexit 'ERROR' -- command", file=sys.stderr)
            print("  2. A timeout: earlyexit -t 30 -- command", file=sys.stderr)
            print("  3. A command to watch: earlyexit command (watch mode, learns from you)", file=sys.stderr)
            print("", file=sys.stderr)
            print("Run 'earlyexit --help' for more information.", file=sys.stderr)
            return 2
        # else: has_command but no pattern/timeout - will enter watch mode below
    
    # Handle special "no pattern" keywords
    if args.pattern in ['-', 'NONE', 'NOPATTERN']:
        # User explicitly wants timeout/monitoring only, no pattern matching
        no_pattern_mode = True
        # Use a pattern that will never match anything
        args.pattern = '(?!.*)'  # Negative lookahead that always fails
        if not args.quiet:
            # Show which timeout is active
            timeout_info = []
            if args.timeout:
                timeout_info.append(f"overall: {args.timeout}s")
            if args.idle_timeout:
                timeout_info.append(f"idle: {args.idle_timeout}s")
            if args.first_output_timeout:
                timeout_info.append(f"first-output: {args.first_output_timeout}s")
            if timeout_info:
                print(f"ℹ️  Timeout-only mode (no pattern matching) - {', '.join(timeout_info)}", file=sys.stderr)
            else:
                print("ℹ️  Timeout-only mode (no pattern matching)", file=sys.stderr)
    
    # Check if pattern looks like it might be the separator (this shouldn't happen with preprocessing)
    if args.pattern == '--':
        print("❌ Error: Missing PATTERN argument before '--' separator", file=sys.stderr)
        print("", file=sys.stderr)
        print("Usage:", file=sys.stderr)
        print("  earlyexit 'PATTERN' -- COMMAND [args...]    # With pattern", file=sys.stderr)
        print("  earlyexit -- COMMAND [args...]              # No pattern (watch mode)", file=sys.stderr)
        print("  earlyexit -t SECS -- COMMAND [args...]      # Timeout only, no pattern", file=sys.stderr)
        print("", file=sys.stderr)
        print("Examples:", file=sys.stderr)
        print("  earlyexit 'ERROR' -- ./my-script.sh", file=sys.stderr)
        print("  earlyexit -- mist validate --id 123 --step 2", file=sys.stderr)
        print("  earlyexit -t 30 -- ./long-script.sh", file=sys.stderr)
        print("", file=sys.stderr)
        print("Run 'earlyexit --help' for more information.", file=sys.stderr)
        return 2
    
    # Check if this looks like watch mode (no pattern specified, just command)
    # Pattern is None and we have a command → watch mode
    # OR pattern looks like a command name
    common_commands = ['echo', 'cat', 'grep', 'ls', 'python', 'python3', 'node', 'bash', 'sh', 
                       'npm', 'yarn', 'make', 'cmake', 'cargo', 'go', 'java', 'perl', 'ruby',
                       'pytest', 'jest', 'mocha', 'terraform', 'docker', 'kubectl', 'git',
                       'mist', 'aws', 'gcloud', 'az', 'curl', 'wget']
    
    # Also check if pattern looks like a path to an executable
    # Or if it's a simple lowercase word (not all caps like ERROR/FAIL) with command args
    import re as re_module
    simple_word = args.pattern and re_module.match(r'^[a-z0-9_-]+$', args.pattern)  # lowercase only
    has_command_args = args.command and len(args.command) > 0
    
    # Check if using new dual-pattern mode (success/error patterns)
    has_dual_patterns = bool(getattr(args, 'success_pattern', None) or getattr(args, 'error_pattern', None))
    
    looks_like_command = (
        (args.pattern is None and has_command_args and not has_dual_patterns) or  # ee -- command (but not with dual patterns)
        args.pattern in common_commands or
        (args.pattern and ('/' in args.pattern or args.pattern.startswith('.'))) or
        (simple_word and has_command_args)  # Lowercase word + args = likely a command, not ERROR/FAIL pattern
    )
    
    if looks_like_command:
        # Pattern looks like a command → This is watch mode!
        # Reconstruct the full command from pattern + command args
        if args.pattern:
            full_command = [args.pattern] + args.command
        else:
            # Pattern is None (from `ee -- command`), command is already complete
            full_command = args.command
        
        # Enter watch mode
        try:
            from earlyexit.watch_mode import run_watch_mode
            
            # Detect project type (telemetry not initialized yet, so do it manually)
            project_type = 'unknown'
            try:
                if TELEMETRY_AVAILABLE:
                    from earlyexit.telemetry import TelemetryCollector
                    temp_collector = TelemetryCollector()
                    project_type = temp_collector._detect_project_type(' '.join(full_command))
            except:
                pass
            
            telemetry_start_time = time.time()
            
            # Generate execution ID for telemetry
            execution_id = None
            env_no_telemetry = os.environ.get('EARLYEXIT_NO_TELEMETRY', '').lower() in ('1', 'true', 'yes')
            telemetry_enabled = TELEMETRY_AVAILABLE and not args.no_telemetry and not env_no_telemetry
            
            if telemetry_enabled:
                try:
                    execution_id = f"exec_{int(telemetry_start_time * 1000)}_{os.getpid()}"
                except:
                    pass
            
            # Check for smart suggestions (if telemetry enabled)
            suggested_setting_id = None
            if telemetry_enabled:
                try:
                    from earlyexit.telemetry import get_telemetry
                    from earlyexit.suggestions import check_and_offer_suggestion
                    
                    telemetry_collector = get_telemetry()
                    if telemetry_collector:
                        suggested_setting_id = check_and_offer_suggestion(
                            args, full_command, telemetry_collector
                        )
                except Exception:
                    # Silently fail - don't disrupt user
                    pass
            
            exit_code = run_watch_mode(full_command, args, os.getcwd(), project_type, execution_id)
            
            # Record to telemetry if enabled
            if telemetry_enabled:
                try:
                    from earlyexit.telemetry import get_telemetry
                    telemetry_collector = get_telemetry()
                    if telemetry_collector and telemetry_collector.enabled:
                        telemetry_data = {
                            'command': ' '.join(full_command),
                            'pattern': '<watch mode>',
                            'exit_code': exit_code,
                            'exit_reason': 'watch_mode_interrupt' if exit_code == 130 else 'watch_mode_complete',
                            'total_runtime': time.time() - telemetry_start_time,
                            'timestamp': telemetry_start_time,
                            'project_type': project_type,
                        }
                        # Record execution with the same execution_id used in watch mode
                        if execution_id:
                            telemetry_data['execution_id'] = execution_id
                        telemetry_collector.record_execution(telemetry_data)
                except:
                    pass
            
            # Apply exit code mapping if requested
            exit_code = map_exit_code(exit_code, args.unix_exit_codes)
            return exit_code
        except Exception as e:
            print(f"❌ Error in watch mode: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            exit_code = 1
            exit_code = map_exit_code(exit_code, args.unix_exit_codes)
            return exit_code
    
    # Initialize telemetry (opt-out, enabled by default)
    # Can be disabled via --no-telemetry flag or EARLYEXIT_NO_TELEMETRY env var
    env_no_telemetry = os.environ.get('EARLYEXIT_NO_TELEMETRY', '').lower() in ('1', 'true', 'yes')
    telemetry_enabled = TELEMETRY_AVAILABLE and not args.no_telemetry and not env_no_telemetry
    telemetry_collector = None
    telemetry_start_time = time.time()
    telemetry_data = {
        'command': ' '.join(args.command) if args.command else '<pipe mode>',
        'pattern': original_pattern if no_pattern_mode else args.pattern,
        'pattern_type': 'perl_regex' if args.perl_regexp else 'python_re',
        'case_insensitive': args.ignore_case,
        'invert_match': args.invert_match,
        'max_count': args.max_count,
        'overall_timeout': args.timeout,
        'idle_timeout': args.idle_timeout,
        'first_output_timeout': args.first_output_timeout,
        'delay_exit': args.delay_exit,
        'match_count': 0,
        'exit_code': 0,
        'exit_reason': 'unknown'
    }
    
    if telemetry_enabled:
        try:
            telemetry_collector = telemetry.init_telemetry(enabled=True)
            
            # Check database size and show warning if large
            if telemetry_collector and telemetry_collector.enabled:
                db_size_mb = telemetry_collector.get_db_size_mb()
                if db_size_mb > 500:
                    print(f"⚠️  Telemetry database is large ({db_size_mb:.0f} MB)", file=sys.stderr)
                    print("   Run 'ee-clear --older-than 30d' to clean up old data", file=sys.stderr)
                    print("   Or disable telemetry: export EARLYEXIT_NO_TELEMETRY=1", file=sys.stderr)
                
                # Run auto-cleanup (every 100th execution)
                try:
                    telemetry_collector.auto_cleanup()
                except Exception:
                    # Silently ignore cleanup errors
                    pass
        except Exception:
            # Silently disable if init fails
            telemetry_enabled = False
            telemetry_collector = None
    
    # Apply auto-tune if requested
    if args.auto_tune:
        if not telemetry_collector:
            print("⚠️  Warning: Auto-tune requires telemetry, but it's unavailable. Using defaults.", 
                  file=sys.stderr)
        else:
            try:
                from . import inference
                engine = inference.get_inference_engine(telemetry_collector)
                
                if engine:
                    # Get command string for analysis
                    command_str = ' '.join(args.command) if args.command else None
                    
                    if not command_str:
                        print("⚠️  Warning: Auto-tune works best with command mode. Using pattern-based tuning.", 
                              file=sys.stderr)
                    
                    # Get recommendations
                    recommendations = engine.auto_tune_parameters(command_str or '', pattern=args.pattern)
                    
                    print("🤖 Auto-tuning parameters based on telemetry...", file=sys.stderr)
                    print(f"   Project Type: {recommendations.get('project_type', 'unknown')}", file=sys.stderr)
                    print(f"   Confidence: {recommendations.get('overall_confidence', 0)*100:.1f}%", file=sys.stderr)
                    
                    # Apply recommendations (only if not explicitly set by user)
                    rec = recommendations.get('recommendations', {})
                    
                    # Pattern recommendation (only if pattern was provided as positional arg without explicit value)
                    if 'pattern' in rec and rec['pattern']['confidence'] > 0.5:
                        suggested_pattern = rec['pattern']['value']
                        if args.pattern != suggested_pattern:
                            print(f"   Using pattern: {suggested_pattern}", file=sys.stderr)
                            args.pattern = suggested_pattern
                    
                    # Timeout recommendations (only if not explicitly set)
                    if args.timeout is None and 'overall_timeout' in rec:
                        args.timeout = rec['overall_timeout']['value']
                        print(f"   Setting overall timeout: {args.timeout:.0f}s", file=sys.stderr)
                    
                    if args.idle_timeout is None and 'idle_timeout' in rec:
                        args.idle_timeout = rec['idle_timeout']['value']
                        print(f"   Setting idle timeout: {args.idle_timeout:.0f}s", file=sys.stderr)
                    
                    if args.delay_exit is None and 'delay_exit' in rec:
                        args.delay_exit = rec['delay_exit']['value']
                        print(f"   Setting delay exit: {args.delay_exit:.0f}s", file=sys.stderr)
                    
                    print("", file=sys.stderr)  # Empty line for readability
                    
            except ImportError:
                print("⚠️  Warning: Inference engine unavailable. Install required dependencies.", 
                      file=sys.stderr)
            except Exception as e:
                print(f"⚠️  Warning: Auto-tune failed: {e}. Using provided/default parameters.", 
                      file=sys.stderr)
    
    # Create execution ID for telemetry match events
    execution_id = None
    if telemetry_enabled and telemetry_collector:
        try:
            # Pre-generate execution ID for this run
            execution_id = f"exec_{int(telemetry_start_time * 1000)}_{os.getpid()}"
        except:
            pass
    
    # Use explicit source file for telemetry (or will be detected via FD inspection)
    source_file = args.source_file
    
    def record_telemetry(exit_code: int, exit_reason: str, match_count: int = 0):
        """Helper to record telemetry data"""
        if not telemetry_enabled or not telemetry_collector:
            return
        try:
            telemetry_data['exit_code'] = exit_code
            telemetry_data['exit_reason'] = exit_reason
            telemetry_data['match_count'] = match_count
            telemetry_data['total_runtime'] = time.time() - telemetry_start_time
            telemetry_data['timestamp'] = telemetry_start_time
            telemetry_collector.record_execution(telemetry_data)
        except Exception:
            # Silently fail - don't disrupt main execution
            pass
    
    # Convert fd_patterns from list of [fd, pattern] to list of (int(fd), pattern)
    if args.fd_patterns:
        try:
            args.fd_patterns = [(int(fd), pattern) for fd, pattern in args.fd_patterns]
        except ValueError as e:
            print(f"❌ Invalid file descriptor number: {e}", file=sys.stderr)
            record_telemetry(3, 'invalid_fd')
            return 3
    
    # Apply -C/--context flag (sets both -B and -A)
    if args.context is not None:
        if args.before_context == 0:  # Only set if user didn't specify -B
            args.before_context = args.context
        if args.delay_exit is None:  # Only set if user didn't specify -A
            args.delay_exit = args.context  # Time-based for -A
    
    # Set default delay-exit based on mode
    if args.delay_exit is None:
        # Will determine based on mode later (command vs pipe)
        args.delay_exit = None  # Keep as None for now
    
    # Compile patterns (support both traditional and dual-pattern modes)
    flags = re.IGNORECASE if args.ignore_case else 0
    pattern = None
    success_pattern = None
    error_pattern = None
    
    # Check if using new dual-pattern mode
    if getattr(args, 'success_pattern', None) or getattr(args, 'error_pattern', None):
        # New dual-pattern mode
        try:
            if args.success_pattern:
                success_pattern = compile_pattern(args.success_pattern, flags, args.perl_regexp,
                                                 args.word_regexp, args.line_regexp)
            if args.error_pattern:
                error_pattern = compile_pattern(args.error_pattern, flags, args.perl_regexp,
                                               args.word_regexp, args.line_regexp)
            # Set pattern to error_pattern for backward compatibility with code that expects it
            # If only success_pattern, use that; if no success or error, use a never-match pattern
            if error_pattern:
                pattern = error_pattern
            elif success_pattern:
                pattern = success_pattern
            else:
                pattern = re.compile('(?!.*)')  # Never matches
        except re.error as e:
            print(f"❌ Invalid regex pattern: {e}", file=sys.stderr)
            record_telemetry(3, 'invalid_pattern')
            return 3
        except Exception as e:
            print(f"❌ Error compiling pattern: {e}", file=sys.stderr)
            record_telemetry(3, 'pattern_error')
            return 3
    elif args.pattern == '__DUAL_PATTERN_MODE__':
        # Dummy pattern set to avoid watch mode - use never-match pattern
        pattern = re.compile('(?!.*)')  # Never matches
    else:
        # Traditional mode: single pattern
        try:
            pattern = compile_pattern(args.pattern, flags, args.perl_regexp,
                                     args.word_regexp, args.line_regexp)
        except re.error as e:
            print(f"❌ Invalid regex pattern: {e}", file=sys.stderr)
            record_telemetry(3, 'invalid_pattern')
            return 3
        except Exception as e:
            print(f"❌ Error compiling pattern: {e}", file=sys.stderr)
            record_telemetry(3, 'pattern_error')
            return 3
    
    # Determine if we should colorize
    use_color = (args.color == 'always' or 
                 (args.color == 'auto' and sys.stdout.isatty()))
    
    # Check if test pattern mode is requested
    if args.test_pattern:
        # Test pattern mode: read from stdin, show matches and statistics
        if len(args.command) > 0:
            print("❌ Error: --test-pattern mode reads from stdin, cannot run a command", file=sys.stderr)
            return 3
        
        # Run test pattern mode
        exit_code = test_pattern_mode(args, pattern, success_pattern, error_pattern, use_color)
        return map_exit_code(exit_code, args.unix_exit_codes)
    
    # Determine mode: command mode or pipe mode
    # Command mode takes precedence if a command is provided
    is_command_mode = len(args.command) > 0
    
    # Validate detach mode
    if args.detach:
        if not is_command_mode:
            print("❌ Error: --detach requires command mode (not pipe mode)", file=sys.stderr)
            return 3
        # Check if any pattern is provided (traditional, success, or error)
        has_any_pattern = (args.pattern or 
                          getattr(args, 'success_pattern', None) or
                          getattr(args, 'error_pattern', None))
        if not has_any_pattern:
            print("❌ Error: --detach requires a pattern", file=sys.stderr)
            return 3
    
    # Validate detach-related options
    if args.detach_group and not args.detach:
        print("❌ Error: --detach-group requires --detach", file=sys.stderr)
        return 3
    if args.detach_on_timeout and not args.detach:
        print("❌ Error: --detach-on-timeout requires --detach", file=sys.stderr)
        return 3
    if args.pid_file and not args.detach:
        print("❌ Error: --pid-file requires --detach", file=sys.stderr)
        return 3
    
    # Only allow pipe mode if no command is specified
    if is_command_mode:
        # Warn if trying to pipe data while using command mode
        # Only warn if quiet is not set AND there's actual data being piped
        if not args.quiet:
            try:
                import select
                # More robust check: stdin is a pipe AND has data AND not from a TTY
                if not sys.stdin.isatty():
                    readable, _, _ = select.select([sys.stdin], [], [], 0.0)
                    if readable:
                        # Verify it's actually a pipe with data, not just a closed/redirected stdin
                        # In practice, this warning causes more confusion than help, so skip it
                        pass  # Don't warn - it's usually a false positive in various environments
            except:
                pass  # Ignore if select not available
    
    # Set up timeout if requested
    if args.timeout:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(args.timeout))
    
    try:
        if is_command_mode:
            # Command mode: run the command and monitor its output
            # Set default delay-exit for command mode
            if args.delay_exit is None:
                args.delay_exit = 10  # 10 seconds default for command mode
            
            exit_code = run_command_mode(args, pattern, use_color, telemetry_collector, 
                                        execution_id, telemetry_start_time, source_file, success_pattern, error_pattern)
            
            # Cancel timeout on completion
            if args.timeout:
                signal.alarm(0)
            
            # Determine exit reason for telemetry
            if exit_code == 0:
                exit_reason = 'match'
            elif exit_code == 2:
                exit_reason = 'timeout'
            else:
                exit_reason = 'completed'
            record_telemetry(exit_code, exit_reason)
            
            # Apply exit code mapping if requested
            original_exit_code = exit_code
            exit_code = map_exit_code(exit_code, args.unix_exit_codes)
            
            # Output JSON if requested (before returning)
            if args.json:
                duration = time.time() - telemetry_start_time
                # Get log paths from auto_logging
                from earlyexit.auto_logging import setup_auto_logging
                stdout_log_path, stderr_log_path = setup_auto_logging(args, args.command, is_command_mode=True)
                
                json_output = create_json_output(
                    exit_code=exit_code,
                    exit_reason=exit_reason,
                    pattern=original_pattern,
                    matched_line=None,  # Not tracked in current implementation
                    line_number=None,  # Not tracked in current implementation
                    duration=duration,
                    command=args.command if args.command else [],
                    timeouts={
                        'overall': args.timeout,
                        'idle': args.idle_timeout,
                        'first_output': args.first_output_timeout
                    },
                    statistics={
                        'lines_processed': None,  # Future enhancement
                        'bytes_processed': None,  # Future enhancement
                        'time_to_first_output': None,  # Future enhancement
                        'time_to_match': None  # Future enhancement
                    },
                    log_files={
                        'stdout': stdout_log_path,
                        'stderr': stderr_log_path
                    }
                )
                print(json_output)
            
            return exit_code
        else:
            # Pipe mode: process stdin (original behavior)
            # Set default delay-exit for pipe mode
            if args.delay_exit is None:
                args.delay_exit = 0  # No delay by default in pipe mode (backward compatible)
            
            match_count = [0]  # Use list for consistency with command mode
            post_match_lines = [0]  # Track lines captured after match
            match_timestamp = [0]  # Track match time for delay
            source_file_container = [source_file]  # Mutable container for dynamic detection
            
            # Set up timeout monitoring for pipe mode
            timed_out = [False]
            first_output_seen = [False]
            last_output_time = [time.time()]  # Initialize to start time
            stop_reading = [False]  # Signal to stop reading
            stuck_detected = [False]  # Track stuck detection for pipe mode
            
            def timeout_callback(reason):
                """Handle timeout in pipe mode"""
                timed_out[0] = True
                stop_reading[0] = True
                if not args.quiet:
                    print(f"\n⏱️  Timeout: {reason}", file=sys.stderr, flush=True)
            
            def check_output_timeouts():
                """Monitor thread to check for idle and first-output timeouts in pipe mode"""
                start_time = time.time()
                
                while not timed_out[0] and not stop_reading[0]:
                    current_time = time.time()
                    
                    # Check first output timeout
                    if args.first_output_timeout and not first_output_seen[0]:
                        if current_time - start_time >= args.first_output_timeout:
                            timeout_callback(f"no first output after {args.first_output_timeout}s")
                            break
                    
                    # Check idle timeout
                    if args.idle_timeout and first_output_seen[0]:
                        time_since_output = current_time - last_output_time[0]
                        if time_since_output >= args.idle_timeout:
                            timeout_callback(f"no output for {args.idle_timeout}s")
                            break
                    
                    # Check every 100ms
                    time.sleep(0.1)
            
            # Start output timeout monitor thread if needed
            output_timeout_thread = None
            if args.idle_timeout or args.first_output_timeout:
                output_timeout_thread = threading.Thread(target=check_output_timeouts, daemon=True)
                output_timeout_thread.start()
            
            match_type = ['none']  # For pipe mode
            lines_processed = process_stream(sys.stdin, pattern, args, 0, match_count, use_color, 
                                            "stdin", last_output_time, first_output_seen, None,
                                            match_timestamp,
                                            telemetry_collector, execution_id, telemetry_start_time, source_file_container,
                                            post_match_lines, None, None, 
                                            success_pattern=None, match_type=match_type, stuck_detected=stuck_detected,
                                            last_stderr_time=None, stderr_seen=None)
            
            # Stop monitoring thread
            stop_reading[0] = True
            if output_timeout_thread:
                output_timeout_thread.join(timeout=0.5)
            
            # Check if stuck was detected
            if stuck_detected[0]:
                record_telemetry(2, 'stuck')
                exit_code = 2
                exit_code = map_exit_code(exit_code, args.unix_exit_codes)
                return exit_code
            
            # Check if we timed out
            if timed_out[0]:
                # Cancel overall timeout
                if args.timeout:
                    signal.alarm(0)
                record_telemetry(2, 'timeout')
                return 2
            
            # Handle delay-exit in pipe mode if match was found
            if match_count[0] > 0 and args.delay_exit and args.delay_exit > 0 and match_timestamp[0] > 0:
                elapsed = time.time() - match_timestamp[0]
                remaining = args.delay_exit - elapsed
                
                if remaining > 0:
                    if not args.quiet:
                        print(f"\n⏳ Waiting {remaining:.1f}s for error context...", file=sys.stderr)
                    
                    # Continue reading for the delay period
                    import select
                    end_time = time.time() + remaining
                    
                    while time.time() < end_time:
                        # Check if there's input available (non-blocking)
                        if select.select([sys.stdin], [], [], 0.1)[0]:
                            try:
                                line = sys.stdin.readline()
                                if not line:
                                    break  # EOF
                                if not args.quiet:
                                    if use_color:
                                        print(line, end='')
                                    else:
                                        print(line, end='')
                            except:
                                break
                        else:
                            # No input available, just wait
                            pass
            
            # Cancel timeout on completion
            if args.timeout:
                signal.alarm(0)
            
            exit_code = 1 if match_count[0] == 0 else 0
            exit_reason = 'no_match' if match_count[0] == 0 else 'match'
            record_telemetry(exit_code, exit_reason, match_count[0])
            # Apply exit code mapping if requested
            exit_code = map_exit_code(exit_code, args.unix_exit_codes)
            
            # Output JSON if requested (pipe mode)
            if args.json:
                duration = time.time() - telemetry_start_time
                json_output = create_json_output(
                    exit_code=exit_code,
                    exit_reason=exit_reason,
                    pattern=original_pattern,
                    matched_line=None,  # Not tracked in pipe mode
                    line_number=None,  # Not tracked in pipe mode
                    duration=duration,
                    command=[],  # Pipe mode has no command
                    timeouts={
                        'overall': args.timeout,
                        'idle': args.idle_timeout,
                        'first_output': args.first_output_timeout
                    },
                    statistics={
                        'lines_processed': None,  # Future enhancement
                        'bytes_processed': None,  # Future enhancement
                        'time_to_first_output': None,  # Future enhancement
                        'time_to_match': None  # Future enhancement
                    },
                    log_files={
                        'stdout': None,  # Pipe mode doesn't create log files
                        'stderr': None
                    }
                )
                print(json_output)
            
            return exit_code
        
    except TimeoutError:
        if not args.quiet:
            print(f"\n⏱️  Timeout exceeded ({args.timeout}s)", file=sys.stderr)
            # Check if stdin is a pipe (not a TTY) - if so, upstream process may still be running
            try:
                is_pipe = not sys.stdin.isatty()
            except:
                is_pipe = True  # Assume it's a pipe if we can't check
            
            if is_pipe:
                # We're in a pipeline - the upstream process might still be running
                # This is expected behavior - the shell waits for the entire pipeline to complete
                print("💡 Tip: If prompt doesn't return, press Ctrl+D (EOF) or Ctrl+C", file=sys.stderr)
            sys.stderr.flush()
        record_telemetry(2, 'timeout')
        # Close stdin to unblock any pending reads and force exit
        try:
            sys.stdin.close()
        except:
            pass
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except:
            pass
        # Force exit to ensure we don't hang
        os._exit(2)
    
    except KeyboardInterrupt:
        if not args.quiet:
            print("\n^C", file=sys.stderr)
        record_telemetry(130, 'interrupted')
        exit_code = 130  # Standard exit code for SIGINT
        exit_code = map_exit_code(exit_code, args.unix_exit_codes)
        return exit_code
    
    except BrokenPipeError:
        # Gracefully handle broken pipe (e.g., when piped to head)
        record_telemetry(0, 'broken_pipe')
        exit_code = 0
        exit_code = map_exit_code(exit_code, args.unix_exit_codes)
        return exit_code
    
    except Exception as e:
        if not args.quiet:
            print(f"❌ Error: {e}", file=sys.stderr)
        record_telemetry(3, 'error')
        exit_code = 3
        exit_code = map_exit_code(exit_code, args.unix_exit_codes)
        return exit_code


if __name__ == '__main__':
    sys.exit(main())


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


def compile_pattern(pattern: str, flags: int = 0, perl_style: bool = False) -> Pattern:
    """
    Compile regex pattern with appropriate flags
    
    Args:
        pattern: Regex pattern string
        flags: re module flags
        perl_style: Use regex module for Perl-compatible patterns
        
    Returns:
        Compiled pattern object
    """
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
                   log_file=None):
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
                
                if not args.quiet:
                    print(line.rstrip('\n'), flush=True)
        except:
            pass
        return 0
    RED = '\033[01;31m' if use_color else ''
    YELLOW = '\033[01;33m' if use_color else ''
    RESET = '\033[0m' if use_color else ''
    
    line_number = line_number_offset
    
    # Context buffer for capturing lines before/after matches
    context_buffer = []
    context_size = 3  # Capture 3 lines before and after
    
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
            
            line_number += 1
            line_stripped = line.rstrip('\n')
            
            # Maintain context buffer (ring buffer of last N lines)
            context_buffer.append(line_stripped)
            if len(context_buffer) > context_size:
                context_buffer.pop(0)
            
            # Check for match
            match = pattern.search(line_stripped)
            is_match = match is not None
            
            # Invert if requested
            if args.invert_match:
                is_match = not is_match
            
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
                
                # Output the line if not quiet
                if not args.quiet:
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
                        if not args.quiet:
                            prefix = ""
                            if args.line_number:
                                prefix = f"{line_number}:"
                            if stream_name and args.fd_prefix:
                                prefix += f"{YELLOW}[{stream_name}]{RESET} "
                            print(f"{prefix}{line_stripped}", flush=True)
                        return line_number - line_number_offset
                
                if not args.quiet:
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


def run_command_mode(args, default_pattern: Pattern, use_color: bool, telemetry_collector=None, 
                     execution_id: Optional[str] = None, telemetry_start_time: Optional[float] = None,
                     initial_source_file: Optional[str] = None):
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
            
            # Display "Logging to:" message unless quiet
            if not args.quiet:
                mode_msg = " (appending)" if file_mode == 'a' else ""
                print(f"📝 Logging to{mode_msg}:")
                print(f"   stdout: {stdout_log_path}")
                print(f"   stderr: {stderr_log_path}")
        except Exception as e:
            if not args.quiet:
                print(f"⚠️  Warning: Could not create log files: {e}", file=sys.stderr)
            stdout_log_file = None
            stderr_log_file = None
    
    match_count = [0]  # Use list to make it mutable across threads
    post_match_lines = [0]  # Track lines captured after match
    timed_out = [False]  # Track if we timed out
    timeout_reason = [""]  # Track why we timed out
    
    # Track output timing
    start_time = telemetry_start_time or time.time()
    last_output_time = [start_time]  # Shared across all streams
    first_output_seen = [False]
    first_stdout_time = [0.0]  # Timestamp when first stdout line occurs
    first_stderr_time = [0.0]  # Timestamp when first stderr line occurs
    match_timestamp = [0]  # Timestamp of first match (for delay-exit)
    
    # Source file container (mutable, can be updated from output)
    source_file_container = [initial_source_file]
    
    # Track pipes and file descriptors for cleanup
    pipes_to_close = []
    
    # Build pattern map: fd_num -> compiled pattern
    fd_patterns: Dict[int, Pattern] = {}
    
    # Parse fd-specific patterns
    if args.fd_patterns:
        flags = re.IGNORECASE if args.ignore_case else 0
        for fd_num, pattern_str in args.fd_patterns:
            try:
                fd_patterns[fd_num] = compile_pattern(pattern_str, flags, args.perl_regexp)
            except Exception as e:
                print(f"❌ Invalid regex pattern for fd {fd_num}: {e}", file=sys.stderr)
                return 3
    
    def timeout_callback(reason="timeout"):
        """Called when timeout expires"""
        timed_out[0] = True
        timeout_reason[0] = reason
        if process.poll() is None:  # Process still running
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
                    def monitor():
                        try:
                            process_stream(s, pat, args, 0, match_count, use_color, lbl,
                                         last_output_time, first_output_seen, first_time,
                                         match_timestamp,
                                         telemetry_collector, execution_id, start_time, source_file_container,
                                         post_match_lines, log_f)
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
                            if not args.quiet:
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
                            if not args.quiet:
                                print(line.decode('utf-8', errors='replace'), end='', flush=True)
                    except:
                        pass
                t = threading.Thread(target=drain_stdout, daemon=True)
                t.start()
                threads.append(t)
            
            # Wait for threads to complete or match to be found
            while any(t.is_alive() for t in threads):
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
                        # Kill the process on match (after delay)
                        if timeout_timer:
                            timeout_timer.cancel()
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
                                 post_match_lines, log_file_for_stream)
                except:
                    pass
            
            monitor_thread = threading.Thread(target=monitor_single, daemon=True)
            monitor_thread.start()
            
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
                        # Kill the process on match (after delay)
                        if timeout_timer:
                            timeout_timer.cancel()
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
            
            # If no match found, drain the other stream
            if match_count[0] < args.max_count:
                if args.match_stderr == 'stdout' and not args.quiet:
                    try:
                        for line in process.stderr:
                            print(line.decode('utf-8', errors='replace'), end='', file=sys.stderr, flush=True)
                    except:
                        pass
                elif args.match_stderr == 'stderr' and not args.quiet:
                    try:
                        for line in process.stdout:
                            print(line.decode('utf-8', errors='replace'), end='', flush=True)
                    except:
                        pass
        
        # Old code below - keeping for reference but will be removed
        if False and args.match_stderr == 'both':
            # Monitor both streams in parallel
            stdout_lines = [0]
            stderr_lines = [0]
            
            def monitor_stdout():
                try:
                    stdout_lines[0] = process_stream(
                        process.stdout, pattern, args, 0, match_count, use_color, "stdout",
                        None, None, first_stdout_time,
                        None, telemetry_collector, execution_id, start_time, source_file_container,
                        post_match_lines, stdout_log_file
                    )
                except:
                    pass
            
            def monitor_stderr():
                try:
                    stderr_lines[0] = process_stream(
                        process.stderr, pattern, args, 0, match_count, use_color, "stderr",
                        None, None, first_stderr_time,
                        None, telemetry_collector, execution_id, start_time, source_file_container,
                        post_match_lines, stderr_log_file
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
                             post_match_lines, stderr_log_file)
            except:
                pass
            # Drain stdout
            try:
                for line in process.stdout:
                    # Write to stdout log if enabled
                    if stdout_log_file:
                        stdout_log_file.write(line.decode('utf-8', errors='replace'))
                        stdout_log_file.flush()
                    if not args.quiet:
                        print(line.decode('utf-8', errors='replace'), end='', flush=True)
            except:
                pass
        else:
            # Only monitor stdout (default)
            try:
                process_stream(process.stdout, pattern, args, 0, match_count, use_color, "stdout",
                             None, None, first_stdout_time,
                             None, telemetry_collector, execution_id, start_time, source_file_container,
                             post_match_lines, stdout_log_file)
            except:
                pass
            # Drain stderr
            try:
                for line in process.stderr:
                    # Write to stderr log if enabled
                    if stderr_log_file:
                        stderr_log_file.write(line.decode('utf-8', errors='replace'))
                        stderr_log_file.flush()
                    if not args.quiet:
                        print(line.decode('utf-8', errors='replace'), end='', file=sys.stderr, flush=True)
            except:
                pass
        
        # Cancel timeout if still running
        if timeout_timer:
            timeout_timer.cancel()
        
        # Wait for process to complete
        try:
            return_code = process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            return_code = process.wait()
        
        # Check if we timed out
        if timed_out[0]:
            if not args.quiet:
                if timeout_reason[0]:
                    print(f"\n⏱️  Timeout: {timeout_reason[0]}", file=sys.stderr)
                else:
                    print(f"\n⏱️  Timeout exceeded", file=sys.stderr)
            return 2
        
        # Determine exit code based on match
        if match_count[0] >= args.max_count:
            return 0  # Pattern matched - early exit
        elif match_count[0] > 0:
            return 0  # At least one match found
        else:
            return 1  # No match found
            
    except FileNotFoundError:
        print(f"❌ Command not found: {args.command[0]}", file=sys.stderr)
        return 3
    except TimeoutError:
        # Timeout - show clean message without traceback
        if not args.quiet:
            print(f"⏱️  Timeout exceeded", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"❌ Error running command: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 3
    finally:
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


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Early exit pattern matching - exit immediately when pattern matches',
        epilog="""
Examples:
  # Pipe mode (read from stdin)
  long_running_command | earlyexit -t 30 'Error|Failed'
  terraform apply | earlyexit -i -t 600 'error'
  
  # Command mode (run command directly, like timeout)
  earlyexit -t 60 'Error' sleep 120
  earlyexit -t 300 'FAILED' pytest -v
  earlyexit -t 600 'error' terraform apply -auto-approve
  
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
  
  # Timeout if no output for 30 seconds (hang detection)
  earlyexit --idle-timeout 30 'Error' ./long-running-app
  
  # Timeout if app doesn't start outputting within 10 seconds
  earlyexit --first-output-timeout 10 'Error' ./slow-startup-app
  
  # Combine timeouts: overall 300s, idle 30s, first output 10s
  earlyexit -t 300 --idle-timeout 30 --first-output-timeout 10 'Error' ./app
  
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

Exit codes:
  0 - Pattern matched (error detected)
  1 - No match found (success)
  2 - Timeout exceeded
  3 - Other error
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Positional arguments
    parser.add_argument('pattern', nargs='?', default=None,
                       help='Regular expression pattern to match (optional if -t/--idle-timeout/--first-output-timeout provided)')
    parser.add_argument('command', nargs='*',
                       help='Command to run (if not reading from stdin)')
    
    # === Arguments in alphabetical order (by long form) ===
    
    parser.add_argument('-a', '--append', action='store_true',
                       help='Append to log files instead of overwriting (like tee -a)')
    parser.add_argument('--no-auto-log', '--no-log', action='store_true',
                       help='Disable automatic log file creation (auto-log is enabled by default in command mode)')
    parser.add_argument('--auto-tune', action='store_true',
                       help='Automatically select optimal parameters based on telemetry (experimental)')
    parser.add_argument('--color', choices=['always', 'auto', 'never'], default='auto',
                       help='Colorize matched text (default: auto)')
    parser.add_argument('--delay-exit', type=float, metavar='SECONDS', default=None,
                       help='After match, continue reading for N seconds to capture error context (default: 10 for command mode, 0 for pipe mode)')
    parser.add_argument('--delay-exit-after-lines', type=int, metavar='LINES', default=100,
                       help='After match, exit early if N lines captured (default: 100). Whichever comes first: time or lines.')
    parser.add_argument('-E', '--extended-regexp', action='store_true',
                       help='Extended regex (default Python re module)')
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
    parser.add_argument('--first-output-timeout', type=float, metavar='SECONDS',
                       help='Timeout if first output not seen within N seconds')
    parser.add_argument('-z', '--gzip', action='store_true',
                       help='Compress log files with gzip after command completes (like tar -z, rsync -z). Saves 70-90% space.')
    parser.add_argument('-i', '--ignore-case', action='store_true',
                       help='Case-insensitive matching')
    parser.add_argument('--idle-timeout', type=float, metavar='SECONDS',
                       help='Timeout if no output for N seconds (idle/hang detection)')
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
                       const='stderr',
                       help='Match pattern against stderr only (command mode only)')
    parser.add_argument('--stderr-prefix', dest='fd_prefix', action='store_true',
                       help='Alias for --fd-prefix (for backward compatibility)')
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
    parser.add_argument('--version', action='version', version='%(prog)s 0.0.3')
    
    # Pre-process sys.argv to handle optional pattern when timeout is provided
    # If we have timeout options and '--' separator but no pattern before it, insert 'NONE'
    import sys as sys_module
    argv = sys_module.argv[1:]  # Skip program name
    
    # Check if any timeout option is present
    has_timeout_option = any(opt in argv for opt in ['-t', '--timeout', '--idle-timeout', '--first-output-timeout'])
    
    # Check if '--' is present and is the first positional argument (no pattern before it)
    # Positional args come after all options
    if has_timeout_option and '--' in argv:
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
                if arg in ['-t', '--timeout', '--idle-timeout', '--first-output-timeout', 
                          '-m', '--max-count', '--delay-exit', '--fd', '--source-file'] or \
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
            argv.insert(separator_idx, 'NONE')
    
    args = parser.parse_args(argv)
    
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
    
    if args.pattern is None:
        # Pattern not provided - check if timeout options are present
        has_timeout = args.timeout or args.idle_timeout or args.first_output_timeout
        has_command = len(args.command) > 0
        
        if has_timeout:
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
        else:
            # No pattern, no timeout, no command (pipe mode) - this is an error
            print("❌ Error: PATTERN is required", file=sys.stderr)
            print("", file=sys.stderr)
            print("Provide either:", file=sys.stderr)
            print("  1. A pattern: earlyexit 'ERROR' -- command", file=sys.stderr)
            print("  2. A timeout: earlyexit -t 30 -- command", file=sys.stderr)
            print("  3. A command to watch: earlyexit command (watch mode, learns from you)", file=sys.stderr)
            print("", file=sys.stderr)
            print("Run 'earlyexit --help' for more information.", file=sys.stderr)
            return 2
    
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
    
    # Check if pattern looks like it might be the separator (user forgot pattern)
    if args.pattern == '--':
        print("❌ Error: Missing PATTERN argument", file=sys.stderr)
        print("", file=sys.stderr)
        print("Usage: earlyexit PATTERN [options] -- COMMAND [args...]", file=sys.stderr)
        print("       earlyexit [options] -- COMMAND [args...]  (with -t/--idle-timeout)", file=sys.stderr)
        print("", file=sys.stderr)
        print("Examples:", file=sys.stderr)
        print("  earlyexit 'ERROR' -- ./my-script.sh", file=sys.stderr)
        print("  earlyexit -t 30 -- ./long-script.sh  (timeout-only, no pattern)", file=sys.stderr)
        print("  cat file.log | earlyexit 'CRITICAL'", file=sys.stderr)
        print("", file=sys.stderr)
        print("Run 'earlyexit --help' for more information.", file=sys.stderr)
        return 2
    
    # Check if pattern looks like a command name
    # This could be watch mode: earlyexit npm test (no pattern specified)
    common_commands = ['echo', 'cat', 'grep', 'ls', 'python', 'python3', 'node', 'bash', 'sh', 
                       'npm', 'yarn', 'make', 'cmake', 'cargo', 'go', 'java', 'perl', 'ruby',
                       'pytest', 'jest', 'mocha', 'terraform', 'docker', 'kubectl', 'git']
    
    # Also check if pattern looks like a path to an executable
    looks_like_command = (
        args.pattern in common_commands or
        (args.pattern and ('/' in args.pattern or args.pattern.startswith('.')))
    )
    
    if looks_like_command:
        # Pattern looks like a command → This is watch mode!
        # Reconstruct the full command from pattern + command args
        full_command = [args.pattern] + args.command
        
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
            
            return exit_code
        except Exception as e:
            print(f"❌ Error in watch mode: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 1
    
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
    
    # Set default delay-exit based on mode
    if args.delay_exit is None:
        # Will determine based on mode later (command vs pipe)
        args.delay_exit = None  # Keep as None for now
    
    # Compile default pattern
    flags = re.IGNORECASE if args.ignore_case else 0
    try:
        pattern = compile_pattern(args.pattern, flags, args.perl_regexp)
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
    
    # Determine mode: command mode or pipe mode
    # Command mode takes precedence if a command is provided
    is_command_mode = len(args.command) > 0
    
    # Only allow pipe mode if no command is specified
    if is_command_mode:
        # Warn if trying to pipe data while using command mode
        # Check if there's actually data being piped (not just running in a terminal)
        try:
            import select
            if not sys.stdin.isatty() and select.select([sys.stdin], [], [], 0.0)[0]:
                print("⚠️  Warning: Ignoring pipe input - using command mode", file=sys.stderr)
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
                                        execution_id, telemetry_start_time, source_file)
            
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
            lines_processed = process_stream(sys.stdin, pattern, args, 0, match_count, use_color, 
                                            "stdin", None, None, None,
                                            match_timestamp,
                                            telemetry_collector, execution_id, telemetry_start_time, source_file_container,
                                            post_match_lines)
            
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
        return 130  # Standard exit code for SIGINT
    
    except BrokenPipeError:
        # Gracefully handle broken pipe (e.g., when piped to head)
        record_telemetry(0, 'broken_pipe')
        return 0
    
    except Exception as e:
        if not args.quiet:
            print(f"❌ Error: {e}", file=sys.stderr)
        record_telemetry(3, 'error')
        return 3


if __name__ == '__main__':
    sys.exit(main())


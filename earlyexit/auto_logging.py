#!/usr/bin/env python3
"""
Automatic logging for earlyexit

Generates intelligent log filenames and handles tee-like output to files.
"""

import os
import re
import time
from pathlib import Path
from typing import Tuple, Optional


def sanitize_filename(s: str, max_length: int = 50) -> str:
    """
    Convert a string to a safe filename
    
    Args:
        s: Input string
        max_length: Maximum length of result
    
    Returns:
        Sanitized filename component
    """
    # Remove/replace unsafe characters
    s = re.sub(r'[^\w\s-]', '_', s)
    # Replace spaces with underscores
    s = re.sub(r'[-\s]+', '_', s)
    # Remove leading/trailing underscores
    s = s.strip('_')
    # Truncate if too long
    if len(s) > max_length:
        s = s[:max_length]
    return s.lower()


def generate_log_prefix(command: list, log_dir: str = '/tmp', append: bool = False) -> str:
    """
    Generate intelligent log filename prefix from command and all options
    
    Includes the full command up to ~32 characters (can go up to 42 to avoid
    breaking word boundaries).
    
    Args:
        command: Command list (e.g., ['mist', 'create', '--cloud', 'gcp'])
        log_dir: Directory for logs
        append: If True, omit PID for tee -a compatibility (same file each run)
    
    Returns:
        Full path prefix (without .log/.errlog extension)
    
    Examples:
        Without append (default):
        ['ls', '-la', '/tmp'] -> '/tmp/ee-ls-la-tmp-<pid>'
        ['npm', 'test'] -> '/tmp/ee-npm-test-<pid>'
        
        With append (like tee -a):
        ['npm', 'test'], append=True -> '/tmp/ee-npm-test' (no PID!)
    """
    if not command:
        if append:
            return os.path.join(log_dir, 'ee-command')
        pid = os.getpid()
        return os.path.join(log_dir, f'ee-command-{pid}')
    
    # Build parts from entire command (all arguments and options)
    parts = []
    target_length = 32  # Target character count (excluding "ee-" and "-<pid>")
    current_length = 0
    
    for arg in command:
        # Clean up the argument
        if arg.startswith('--'):
            # Long flag: remove '--' prefix
            clean_arg = arg[2:]
        elif arg.startswith('-'):
            # Short flag: remove '-' prefix
            clean_arg = arg[1:]
        else:
            # Regular argument (command, subcommand, or value)
            clean_arg = os.path.basename(arg)  # Remove path if it's a file path
        
        # Sanitize the argument
        sanitized = sanitize_filename(clean_arg, max_length=40)
        
        if not sanitized:
            continue
        
        # Check if adding this part would exceed our target
        # Account for underscores between parts
        part_length = len(sanitized) + (1 if parts else 0)  # +1 for underscore
        
        if current_length + part_length <= target_length:
            # Fits within target, add it
            parts.append(sanitized)
            current_length += part_length
        elif not parts:
            # First part, always include even if long (truncate if needed)
            parts.append(sanitized[:target_length])
            current_length = len(parts[0])
            break
        else:
            # Would exceed target - check if we should include anyway
            # Allow up to 10 chars overflow to avoid breaking word boundary
            if current_length + part_length <= target_length + 10:
                parts.append(sanitized)
                current_length += part_length
            # Otherwise, stop here (don't break at arbitrary point)
            break
    
    # Join parts with underscores
    cmd_name = '_'.join(parts) if parts else 'command'
    
    # Add PID to make unique (unless appending, then omit for tee -a compatibility)
    if append:
        # No PID - same file for all runs (like tee -a)
        filename = f"ee-{cmd_name}"
    else:
        # Add PID - unique file per run (default)
        pid = os.getpid()
        filename = f"ee-{cmd_name}-{pid}"
    
    return os.path.join(log_dir, filename)


def create_log_files(prefix: str, append: bool = False) -> Tuple[str, str]:
    """
    Create log file paths and ensure directory exists
    
    Args:
        prefix: Path prefix (e.g., '/tmp/myrun')
        append: If True, append mode (files won't be overwritten)
    
    Returns:
        Tuple of (stdout_log_path, stderr_log_path)
    
    Behavior:
        - If prefix ends with .log or .out → use exact filename, add .err for stderr
        - Otherwise → add .log and .errlog (current behavior)
    
    Examples:
        '/tmp/test' → '/tmp/test.log', '/tmp/test.errlog'
        '/tmp/test.log' → '/tmp/test.log', '/tmp/test.err'
        '/tmp/test.out' → '/tmp/test.out', '/tmp/test.err'
    
    Note: append parameter is tracked but actual file opening happens in cli.py
    """
    # Ensure directory exists
    log_dir = os.path.dirname(prefix)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # Smart detection: if user provided exact filename with extension, use it
    if prefix.endswith('.log') or prefix.endswith('.out'):
        # User provided full filename → use exact, add .err for stderr (industry standard)
        stdout_log = prefix
        base = os.path.splitext(prefix)[0]
        stderr_log = f"{base}.err"
    else:
        # User provided prefix → add extensions (current behavior, backward compatible)
        stdout_log = f"{prefix}.log"
        stderr_log = f"{prefix}.errlog"
    
    return stdout_log, stderr_log


def gzip_log_files(stdout_log_path: str = None, stderr_log_path: str = None, quiet: bool = False):
    """
    Compress log files with gzip
    
    Args:
        stdout_log_path: Path to stdout log file
        stderr_log_path: Path to stderr log file
        quiet: Suppress messages
    
    Returns:
        Tuple of (stdout_gz_path, stderr_gz_path) or (None, None) if failed
    """
    import gzip
    import shutil
    
    stdout_gz = None
    stderr_gz = None
    
    try:
        if stdout_log_path and os.path.exists(stdout_log_path):
            stdout_gz = f"{stdout_log_path}.gz"
            with open(stdout_log_path, 'rb') as f_in:
                with gzip.open(stdout_gz, 'wb', compresslevel=6) as f_out:
                    shutil.copyfileobj(f_in, f_out)
            # Remove original file after successful compression
            os.remove(stdout_log_path)
            if not quiet:
                # Get file sizes for reporting
                import sys
                gz_size = os.path.getsize(stdout_gz)
                print(f"🗜️  Compressed: {stdout_gz} ({gz_size:,} bytes)", file=sys.stderr)
    except Exception as e:
        if not quiet:
            import sys
            print(f"⚠️  Warning: Could not gzip {stdout_log_path}: {e}", file=sys.stderr)
    
    try:
        if stderr_log_path and os.path.exists(stderr_log_path):
            stderr_gz = f"{stderr_log_path}.gz"
            with open(stderr_log_path, 'rb') as f_in:
                with gzip.open(stderr_gz, 'wb', compresslevel=6) as f_out:
                    shutil.copyfileobj(f_in, f_out)
            # Remove original file after successful compression
            os.remove(stderr_log_path)
            if not quiet:
                import sys
                gz_size = os.path.getsize(stderr_gz)
                print(f"🗜️  Compressed: {stderr_gz} ({gz_size:,} bytes)", file=sys.stderr)
    except Exception as e:
        if not quiet:
            import sys
            print(f"⚠️  Warning: Could not gzip {stderr_log_path}: {e}", file=sys.stderr)
    
    return stdout_gz, stderr_gz


class TeeWriter:
    """
    Writer that outputs to both a file and original stream (like tee)
    """
    
    def __init__(self, filename: str, original_stream, mode='w'):
        """
        Initialize TeeWriter
        
        Args:
            filename: Path to log file
            original_stream: Original stream (sys.stdout or sys.stderr)
            mode: File open mode
        """
        self.filename = filename
        self.original_stream = original_stream
        self.file = open(filename, mode, buffering=1)  # Line buffered
    
    def write(self, data: str):
        """Write to both file and original stream"""
        if data:
            self.file.write(data)
            self.file.flush()
            if self.original_stream:
                self.original_stream.write(data)
                self.original_stream.flush()
    
    def flush(self):
        """Flush both streams"""
        self.file.flush()
        if self.original_stream:
            self.original_stream.flush()
    
    def close(self):
        """Close file (but not original stream)"""
        if self.file:
            self.file.close()
    
    def fileno(self):
        """Return file descriptor of original stream"""
        if self.original_stream:
            return self.original_stream.fileno()
        return self.file.fileno()


def setup_auto_logging(args, command: list, is_command_mode: bool = True):
    """
    Setup automatic logging based on arguments
    
    Smart auto-logging rules:
    - Pipe mode: Never auto-log (unless --log or --file-prefix)
    - Command mode + --log: Always log
    - Command mode + --no-auto-log: Never log
    - Command mode + timeout: Auto-log (monitoring use case)
    - Command mode + no timeout: No auto-log (simple filtering)
    
    Args:
        args: Parsed arguments
        command: Command list
        is_command_mode: If True, applies command mode rules
    
    Returns:
        Tuple of (stdout_log_path, stderr_log_path) or (None, None) if disabled
    """
    # Check if logging is explicitly disabled
    if hasattr(args, 'no_auto_log') and args.no_auto_log:
        return None, None
    
    # Check if logging is explicitly enabled
    force_logging = getattr(args, 'force_logging', False)
    
    # Check if user provided explicit prefix
    has_explicit_prefix = bool(args.file_prefix)
    
    # Check if any timeout is configured (indicates monitoring use case)
    has_timeout = any([
        getattr(args, 'timeout', None),
        getattr(args, 'idle_timeout', None),
        getattr(args, 'first_output_timeout', None)
    ])
    
    # Determine if we should log
    should_log = False
    
    if force_logging or has_explicit_prefix:
        # Explicit logging requested
        should_log = True
    elif is_command_mode and has_timeout:
        # Command mode with timeout = monitoring use case = auto-log
        should_log = True
    elif not is_command_mode and has_explicit_prefix:
        # Pipe mode with explicit prefix
        should_log = True
    else:
        # Simple filtering use case - no logging
        should_log = False
    
    if not should_log:
        return None, None
    
    # Determine log file prefix
    if args.file_prefix:
        # User explicitly provided prefix
        prefix = args.file_prefix
    else:
        # Auto-generate from command
        log_dir = getattr(args, 'log_dir', '/tmp')
        append_mode = getattr(args, 'append', False)
        # Pass append flag so we don't add PID when appending (tee -a compat)
        prefix = generate_log_prefix(command, log_dir, append=append_mode)
    
    # Create log file paths
    append_mode = getattr(args, 'append', False)
    stdout_log, stderr_log = create_log_files(prefix, append=append_mode)
    
    return stdout_log, stderr_log


if __name__ == '__main__':
    # Test filename generation
    test_cases = [
        (['mist', 'create', '--cloud', 'gcp', '--db', 'mysql'], '/tmp'),
        (['npm', 'test'], '/tmp'),
        (['terraform', 'apply', '-auto-approve'], '/tmp'),
        (['pytest', '-v', 'tests/'], '/tmp'),
        (['docker', 'build', '-t', 'myapp', '.'], '/tmp'),
    ]
    
    for cmd, log_dir in test_cases:
        prefix = generate_log_prefix(cmd, log_dir)
        stdout_log, stderr_log = create_log_files(prefix)
        print(f"Command: {' '.join(cmd)}")
        print(f"  Stdout: {stdout_log}")
        print(f"  Stderr: {stderr_log}")
        print()


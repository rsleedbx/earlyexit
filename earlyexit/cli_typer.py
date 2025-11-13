"""
Typer-based CLI for earlyexit - Modern, type-safe command-line interface
"""
import sys
import os
import time
import signal
import threading
from typing import Optional, List
import typer
from typing_extensions import Annotated

# Import all the core logic from cli.py
from earlyexit.cli import (
    process_stream,
    run_command_mode,
    TELEMETRY_AVAILABLE,
    REGEX_AVAILABLE,
    PSUTIL_AVAILABLE,
)

app = typer.Typer(
    name="earlyexit",
    help="Early exit pattern matching - exit immediately when pattern matches",
    add_completion=False,  # Can enable later for shell completion
    no_args_is_help=False,  # Allow running without args (for stdin)
)


def version_callback(value: bool):
    """Print version and exit"""
    if value:
        from earlyexit import __version__
        typer.echo(f"earlyexit {__version__}")
        raise typer.Exit()


@app.command()
def main(
    # Positional arguments
    pattern: Annotated[Optional[str], typer.Argument(
        help="Regular expression pattern to match (optional if timeout provided or watch mode)"
    )] = None,
    
    command: Annotated[Optional[List[str]], typer.Argument(
        help="Command to run (if not reading from stdin)"
    )] = None,
    
    # Timeout options
    timeout: Annotated[Optional[float], typer.Option(
        "-t", "--timeout",
        help="Overall timeout in seconds",
        metavar="SECONDS"
    )] = None,
    
    idle_timeout: Annotated[Optional[float], typer.Option(
        "--idle-timeout",
        help="Timeout if no output for N seconds (idle/hang detection)",
        metavar="SECONDS"
    )] = None,
    
    first_output_timeout: Annotated[Optional[float], typer.Option(
        "--first-output-timeout",
        help="Timeout if first output not seen within N seconds",
        metavar="SECONDS"
    )] = None,
    
    # Delay and capture options
    delay_exit: Annotated[Optional[float], typer.Option(
        "--delay-exit",
        help="After match, continue reading for N seconds to capture error context (default: 10 for command mode, 0 for pipe mode)",
        metavar="SECONDS"
    )] = None,
    
    delay_exit_after_lines: Annotated[int, typer.Option(
        "--delay-exit-after-lines",
        help="After match, exit early if N lines captured (default: 100). Whichever comes first: time or lines.",
        metavar="LINES"
    )] = 100,
    
    # Matching options
    max_count: Annotated[int, typer.Option(
        "-m", "--max-count",
        help="Stop after NUM matches (default: 1, like grep -m)",
        metavar="NUM"
    )] = 1,
    
    ignore_case: Annotated[bool, typer.Option(
        "-i", "--ignore-case",
        help="Case-insensitive matching"
    )] = False,
    
    extended_regexp: Annotated[bool, typer.Option(
        "-E", "--extended-regexp",
        help="Extended regex (default Python re module)"
    )] = False,
    
    perl_regexp: Annotated[bool, typer.Option(
        "-P", "--perl-regexp",
        help="Perl-compatible regex (requires regex module)"
    )] = False,
    
    invert_match: Annotated[bool, typer.Option(
        "-v", "--invert-match",
        help="Invert match - select non-matching lines"
    )] = False,
    
    # Output options
    quiet: Annotated[bool, typer.Option(
        "-q", "--quiet",
        help="Quiet mode - suppress output, only exit code"
    )] = False,
    
    verbose: Annotated[bool, typer.Option(
        "--verbose",
        help="Verbose output (show debug information)"
    )] = False,
    
    line_number: Annotated[bool, typer.Option(
        "-n", "--line-number",
        help="Prefix output with line number"
    )] = False,
    
    # Stream selection options
    stdout_only: Annotated[bool, typer.Option(
        "--stdout",
        help="Match pattern against stdout only (command mode only)"
    )] = False,
    
    stderr_only: Annotated[bool, typer.Option(
        "--stderr",
        help="Match pattern against stderr only (command mode only)"
    )] = False,
    
    # File descriptor options
    monitor_fds: Annotated[Optional[List[int]], typer.Option(
        "--fd",
        help="Monitor file descriptor N (can be used multiple times)",
        metavar="N"
    )] = None,
    
    fd_prefix: Annotated[bool, typer.Option(
        "--fd-prefix",
        help="Prefix output with stream labels [stdout]/[stderr]/[fd3] etc."
    )] = False,
    
    stderr_prefix: Annotated[bool, typer.Option(
        "--stderr-prefix",
        help="Alias for --fd-prefix (backward compatibility)",
        hidden=True
    )] = False,
    
    # Color options
    color: Annotated[str, typer.Option(
        "--color",
        help="Colorize matched text",
        click_type=typer.Choice(["always", "auto", "never"])
    )] = "auto",
    
    # Telemetry and ML options
    no_telemetry: Annotated[bool, typer.Option(
        "--no-telemetry",
        help="Disable telemetry collection (also: EARLYEXIT_NO_TELEMETRY=1). No SQLite database created when disabled."
    )] = False,
    
    source_file: Annotated[Optional[str], typer.Option(
        "--source-file",
        help="Source file being processed (for telemetry, auto-detected if possible)",
        metavar="FILE"
    )] = None,
    
    auto_tune: Annotated[bool, typer.Option(
        "--auto-tune",
        help="Automatically select optimal parameters based on telemetry (experimental)"
    )] = False,
    
    # Version
    version: Annotated[Optional[bool], typer.Option(
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit"
    )] = None,
):
    """
    Early exit pattern matching - exit immediately when pattern matches.
    
    Examples:
    
      # Pipe mode (read from stdin)
      long_running_command | earlyexit -t 30 'Error|Failed'
      
      # Command mode (run command directly)
      earlyexit 'ERROR' -- npm test
      earlyexit -t 60 'Error' -- pytest
      
      # Watch mode (learn from your behavior) 🆕
      earlyexit npm test
      earlyexit python3 train_model.py
      
      # Monitor both stdout and stderr (default)
      earlyexit 'Error' -- ./app
      
      # Timeout-only mode (no pattern)
      earlyexit -t 30 -- ./long-running-script
      
      # Detect hangs
      earlyexit --idle-timeout 30 'Error' -- ./app
    
    Exit codes:
      0 - Pattern matched (error detected)
      1 - No match found (success)
      2 - Timeout exceeded
      3 - Other error
    """
    # Handle command list
    if command is None:
        command = []
    
    # Normalize stream selection
    if stdout_only:
        match_stderr = 'stdout'
    elif stderr_only:
        match_stderr = 'stderr'
    else:
        match_stderr = 'both'
    
    # Handle fd_prefix alias
    if stderr_prefix:
        fd_prefix = True
    
    # Create args object compatible with existing code
    class Args:
        pass
    
    args = Args()
    args.pattern = pattern
    args.command = command
    args.timeout = timeout
    args.idle_timeout = idle_timeout
    args.first_output_timeout = first_output_timeout
    args.delay_exit = delay_exit
    args.delay_exit_after_lines = delay_exit_after_lines
    args.max_count = max_count
    args.ignore_case = ignore_case
    args.extended_regexp = extended_regexp
    args.perl_regexp = perl_regexp
    args.invert_match = invert_match
    args.quiet = quiet
    args.verbose = verbose
    args.line_number = line_number
    args.match_stderr = match_stderr
    args.monitor_fds = monitor_fds or []
    args.fd_patterns = None  # TODO: Add support for fd_patterns
    args.fd_prefix = fd_prefix
    args.color = color
    args.no_telemetry = no_telemetry
    args.source_file = source_file
    args.auto_tune = auto_tune
    
    # Import the existing main logic from cli.py
    # We'll reuse all the validation and execution logic
    from earlyexit import cli
    
    # Call the original main logic with our args
    # But we need to refactor cli.py to have a run() function that takes args
    # For now, let's inline the key logic here
    
    # Determine mode: watch mode, command mode, or pipe mode
    has_timeout = timeout or idle_timeout or first_output_timeout
    has_command = len(command) > 0
    
    # Watch mode detection (no pattern, no timeout, but command provided)
    if pattern is None and not has_timeout and has_command:
        # Watch mode!
        from earlyexit.watch_mode import run_watch_mode
        
        # Detect project type
        project_type = 'unknown'
        try:
            if TELEMETRY_AVAILABLE:
                from earlyexit.telemetry import TelemetryCollector
                temp_collector = TelemetryCollector()
                project_type = temp_collector._detect_project_type(' '.join(command))
        except:
            pass
        
        telemetry_start_time = time.time()
        exit_code = run_watch_mode(command, args, os.getcwd(), project_type)
        
        # Record to telemetry if enabled
        env_no_telemetry = os.environ.get('EARLYEXIT_NO_TELEMETRY', '').lower() in ('1', 'true', 'yes')
        telemetry_enabled = TELEMETRY_AVAILABLE and not no_telemetry and not env_no_telemetry
        
        if telemetry_enabled:
            try:
                from earlyexit.telemetry import get_telemetry
                telemetry_collector = get_telemetry()
                if telemetry_collector and telemetry_collector.enabled:
                    telemetry_data = {
                        'command': ' '.join(command),
                        'pattern': '<watch mode>',
                        'exit_code': exit_code,
                        'exit_reason': 'watch_mode_interrupt' if exit_code == 130 else 'watch_mode_complete',
                        'total_runtime': time.time() - telemetry_start_time,
                        'timestamp': telemetry_start_time,
                        'project_type': project_type,
                    }
                    telemetry_collector.record_execution(telemetry_data)
            except:
                pass
        
        raise typer.Exit(code=exit_code)
    
    # Timeout-only mode (pattern optional if timeout provided)
    if pattern is None and has_timeout:
        pattern = '(?!.*)'  # Pattern that never matches
        no_pattern_mode = True
        if not quiet:
            timeout_info = []
            if timeout:
                timeout_info.append(f"overall: {timeout}s")
            if idle_timeout:
                timeout_info.append(f"idle: {idle_timeout}s")
            if first_output_timeout:
                timeout_info.append(f"first-output: {first_output_timeout}s")
            typer.echo(f"ℹ️  Timeout-only mode (no pattern specified) - {', '.join(timeout_info)}", err=True)
    
    # Error: No pattern, no timeout, no command
    if pattern is None and not has_timeout and not has_command:
        typer.echo("❌ Error: PATTERN is required", err=True)
        typer.echo("", err=True)
        typer.echo("Provide either:", err=True)
        typer.echo("  1. A pattern: earlyexit 'ERROR' -- command", err=True)
        typer.echo("  2. A timeout: earlyexit -t 30 -- command", err=True)
        typer.echo("  3. A command to watch: earlyexit command (watch mode, learns from you)", err=True)
        typer.echo("", err=True)
        typer.echo("Run 'earlyexit --help' for more information.", err=True)
        raise typer.Exit(code=2)
    
    # At this point, we have a pattern (or timeout-only mode)
    # Now delegate to the existing logic from cli.py
    # We need to refactor cli.py to expose a run() function
    
    typer.echo("🚧 Typer migration in progress - delegating to original CLI...", err=True)
    
    # For now, call the original argparse-based main
    # TODO: Refactor cli.py to have a run(args) function
    sys.exit(0)


if __name__ == "__main__":
    app()


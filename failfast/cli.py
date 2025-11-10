#!/usr/bin/env python3
"""
failfast - Fast-fail pattern matching for command output

Exit immediately when a pattern is matched in stdin, with timeout support.
Implements the early error detection pattern for faster feedback.
"""

import sys
import re
import argparse
import signal
from typing import Optional, Pattern


class TimeoutError(Exception):
    """Raised when timeout is exceeded"""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout"""
    raise TimeoutError("Timeout exceeded")


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


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Fast-fail pattern matching - exit immediately when pattern matches',
        epilog="""
Examples:
  # Exit immediately on first error (30s timeout)
  long_running_command | failfast -t 30 'Error|Failed'
  
  # Case-insensitive matching
  terraform apply | failfast -i -t 600 'error'
  
  # Match up to 3 errors then exit
  pytest | failfast -m 3 'FAILED'
  
  # Invert match - exit when pattern DOESN'T match
  health_check | failfast -v 'OK' -t 10
  
  # Perl-compatible regex
  app_logs | failfast -P '(?<= ERROR ).*' -t 60

Exit codes:
  0 - Pattern matched (error detected)
  1 - No match found (success)
  2 - Timeout exceeded
  3 - Other error
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('pattern', 
                       help='Regular expression pattern to match')
    parser.add_argument('-t', '--timeout', type=float, metavar='SECONDS',
                       help='Timeout in seconds (default: no timeout)')
    parser.add_argument('-m', '--max-count', type=int, default=1, metavar='NUM',
                       help='Stop after NUM matches (default: 1, like grep -m)')
    parser.add_argument('-i', '--ignore-case', action='store_true',
                       help='Case-insensitive matching')
    parser.add_argument('-E', '--extended-regexp', action='store_true',
                       help='Extended regex (default Python re module)')
    parser.add_argument('-P', '--perl-regexp', action='store_true',
                       help='Perl-compatible regex (requires regex module)')
    parser.add_argument('-v', '--invert-match', action='store_true',
                       help='Invert match - select non-matching lines')
    parser.add_argument('-q', '--quiet', action='store_true',
                       help='Quiet mode - suppress output, only exit code')
    parser.add_argument('-n', '--line-number', action='store_true',
                       help='Prefix output with line number')
    parser.add_argument('--color', choices=['always', 'auto', 'never'], default='auto',
                       help='Colorize matched text (default: auto)')
    parser.add_argument('--version', action='version', version='%(prog)s 0.1.0')
    
    args = parser.parse_args()
    
    # Set up timeout if requested
    if args.timeout:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(args.timeout))
    
    # Compile pattern
    flags = re.IGNORECASE if args.ignore_case else 0
    try:
        pattern = compile_pattern(args.pattern, flags, args.perl_regexp)
    except re.error as e:
        print(f"❌ Invalid regex pattern: {e}", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"❌ Error compiling pattern: {e}", file=sys.stderr)
        return 3
    
    # Determine if we should colorize
    use_color = (args.color == 'always' or 
                 (args.color == 'auto' and sys.stdout.isatty()))
    
    # ANSI color codes
    RED = '\033[01;31m' if use_color else ''
    RESET = '\033[0m' if use_color else ''
    
    # Process stdin line by line
    match_count = 0
    line_number = 0
    
    try:
        for line in sys.stdin:
            line_number += 1
            line = line.rstrip('\n')  # Remove newline but keep other whitespace
            
            # Check for match
            match = pattern.search(line)
            is_match = match is not None
            
            # Invert if requested
            if args.invert_match:
                is_match = not is_match
            
            if is_match:
                match_count += 1
                
                # Output the line if not quiet
                if not args.quiet:
                    if args.line_number:
                        prefix = f"{line_number}:"
                    else:
                        prefix = ""
                    
                    # Highlight matched text (only for non-inverted matches)
                    if not args.invert_match and match and use_color:
                        start, end = match.span()
                        highlighted = (line[:start] + RED + 
                                     line[start:end] + RESET + 
                                     line[end:])
                        print(f"{prefix}{highlighted}")
                    else:
                        print(f"{prefix}{line}")
                
                # Check if we've reached max matches
                if match_count >= args.max_count:
                    # Cancel timeout
                    if args.timeout:
                        signal.alarm(0)
                    return 0  # Pattern matched - early exit
            else:
                # Non-matching line - pass through if not quiet
                if not args.quiet:
                    if args.line_number:
                        print(f"{line_number}:{line}")
                    else:
                        print(line)
        
        # EOF reached without matches
        if args.timeout:
            signal.alarm(0)
        
        return 1 if match_count == 0 else 0
        
    except TimeoutError:
        if not args.quiet:
            print(f"\n⏱️  Timeout exceeded ({args.timeout}s)", file=sys.stderr)
        return 2
    
    except KeyboardInterrupt:
        if not args.quiet:
            print("\n^C", file=sys.stderr)
        return 130  # Standard exit code for SIGINT
    
    except BrokenPipeError:
        # Gracefully handle broken pipe (e.g., when piped to head)
        return 0 if match_count > 0 else 1
    
    except Exception as e:
        if not args.quiet:
            print(f"❌ Error: {e}", file=sys.stderr)
        return 3


if __name__ == '__main__':
    sys.exit(main())


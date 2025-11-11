#!/usr/bin/env python3
"""
Telemetry CLI for earlyexit

Subcommands for analyzing and managing telemetry data.
"""

import sys
import argparse
from . import commands


def main():
    """Main entry point for telemetry commands"""
    import os
    
    # Detect which command was used based on argv[0]
    prog_name = os.path.basename(sys.argv[0])
    
    # If called directly as earlyexit-<command>, route to that command
    if prog_name.startswith('earlyexit-'):
        command = prog_name.replace('earlyexit-', '')
        
        if command == 'stats':
            parser = argparse.ArgumentParser(
                prog=prog_name,
                description='Show earlyexit execution statistics'
            )
            args = parser.parse_args()
            return commands.cmd_stats(args)
        
        elif command == 'analyze':
            parser = argparse.ArgumentParser(
                prog=prog_name,
                description='Analyze earlyexit telemetry data'
            )
            parser.add_argument('type', choices=['patterns', 'timing'],
                              help='What to analyze')
            args = parser.parse_args()
            
            if args.type == 'patterns':
                return commands.cmd_analyze_patterns(args)
            else:
                return commands.cmd_analyze_timing(args)
        
        elif command == 'feedback':
            parser = argparse.ArgumentParser(
                prog=prog_name,
                description='Provide feedback on last execution'
            )
            parser.add_argument('--rating', type=int, metavar='1-5',
                              help='Rate the execution (1-5 stars)')
            parser.add_argument('--should-have-exited', action='store_true',
                              help='Whether it should have exited')
            args = parser.parse_args()
            return commands.cmd_feedback(args)
        
        elif command == 'export':
            parser = argparse.ArgumentParser(
                prog=prog_name,
                description='Export telemetry data'
            )
            parser.add_argument('--format', choices=['json', 'csv', 'jsonl'],
                              default='json',
                              help='Export format (default: json)')
            args = parser.parse_args()
            return commands.cmd_export(args)
        
        elif command == 'clear':
            parser = argparse.ArgumentParser(
                prog=prog_name,
                description='Clear telemetry data'
            )
            parser.add_argument('--older-than', metavar='DAYS',
                              help='Delete records older than N days (e.g., 30d)')
            parser.add_argument('--all', action='store_true',
                              help='Delete all telemetry data')
            parser.add_argument('--yes', '-y', action='store_true',
                              help='Skip confirmation prompt')
            args = parser.parse_args()
            return commands.cmd_clear(args)
        
        elif command == 'suggest':
            parser = argparse.ArgumentParser(
                prog=prog_name,
                description='Suggest optimal patterns and parameters'
            )
            parser.add_argument('command', nargs='?',
                              help='Command to get suggestions for (optional)')
            args = parser.parse_args()
            return commands.cmd_suggest(args)
    
    # Fallback: show help
    print("earlyexit telemetry commands:")
    print("  earlyexit-stats             Show execution statistics")
    print("  earlyexit-analyze patterns  Analyze pattern effectiveness")
    print("  earlyexit-analyze timing    Analyze timing patterns")
    print("  earlyexit-feedback          Provide feedback on last execution")
    print("  earlyexit-export            Export telemetry data")
    print("  earlyexit-clear             Clear telemetry data")
    print("  earlyexit-suggest [command] Get intelligent suggestions")
    return 0


if __name__ == '__main__':
    sys.exit(main())


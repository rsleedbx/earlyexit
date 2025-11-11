"""
CLI commands for telemetry analysis and management

Provides stats, analysis, feedback, and export functionality.
"""

import sys
import json
import csv
from typing import Optional
from . import telemetry
from . import inference


def cmd_stats(args):
    """Show execution statistics"""
    collector = telemetry.get_telemetry()
    if not collector:
        # Initialize telemetry if not already done
        collector = telemetry.init_telemetry(enabled=True)
    
    if not collector or not collector.enabled:
        print("❌ Telemetry is disabled or unavailable.", file=sys.stderr)
        return 1
    
    stats = collector.get_stats()
    
    if "error" in stats:
        print(f"❌ {stats['error']}", file=sys.stderr)
        return 1
    
    print("=" * 60)
    print("📊 earlyexit Telemetry Statistics")
    print("=" * 60)
    print(f"\nTotal Executions: {stats['total_executions']}")
    
    if stats['by_project_type']:
        print("\nBy Project Type:")
        for ptype, count in sorted(stats['by_project_type'].items(), 
                                   key=lambda x: x[1], reverse=True):
            print(f"  {ptype:12s}: {count:3d}")
    
    if stats['avg_runtime_seconds']:
        print(f"\nAverage Runtime: {stats['avg_runtime_seconds']:.2f}s")
    
    # Additional stats
    with collector._get_connection() as conn:
        if conn:
            cursor = conn.cursor()
            
            # By exit reason
            cursor.execute("""
                SELECT exit_reason, COUNT(*) 
                FROM executions 
                GROUP BY exit_reason 
                ORDER BY COUNT(*) DESC
            """)
            by_reason = cursor.fetchall()
            
            if by_reason:
                print("\nBy Exit Reason:")
                for reason, count in by_reason:
                    print(f"  {reason:15s}: {count:3d}")
            
            # Match statistics
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN match_count > 0 THEN 1 ELSE 0 END) as with_matches,
                    AVG(match_count) as avg_matches
                FROM executions
            """)
            match_stats = cursor.fetchone()
            if match_stats[0]:
                print(f"\nMatches:")
                print(f"  Executions with matches: {match_stats[0]}")
                print(f"  Average matches:         {match_stats[1]:.2f}")
            
            # Timing statistics
            cursor.execute("""
                SELECT 
                    AVG(time_to_first_match),
                    MIN(total_runtime),
                    MAX(total_runtime)
                FROM executions
                WHERE time_to_first_match IS NOT NULL
            """)
            timing = cursor.fetchone()
            if timing[0]:
                print(f"\nTiming:")
                print(f"  Avg time to match: {timing[0]:.2f}s")
                print(f"  Min runtime:       {timing[1]:.2f}s")
                print(f"  Max runtime:       {timing[2]:.2f}s")
    
    print("\n" + "=" * 60)
    print(f"Database: {collector.db_path}")
    print("=" * 60)
    
    return 0


def cmd_analyze_patterns(args):
    """Analyze pattern effectiveness"""
    collector = telemetry.get_telemetry()
    if not collector:
        collector = telemetry.init_telemetry(enabled=True)
    
    if not collector or not collector.enabled:
        print("❌ Telemetry is disabled or unavailable.", file=sys.stderr)
        return 1
    
    with collector._get_connection() as conn:
        if not conn:
            print("❌ No telemetry database found.", file=sys.stderr)
            return 1
        
        cursor = conn.cursor()
        
        # Pattern usage and effectiveness
        cursor.execute("""
            SELECT 
                pattern,
                COUNT(*) as uses,
                SUM(CASE WHEN exit_reason = 'match' THEN 1 ELSE 0 END) as matches,
                AVG(total_runtime) as avg_runtime,
                AVG(time_to_first_match) as avg_match_time
            FROM executions
            GROUP BY pattern
            ORDER BY uses DESC
            LIMIT 20
        """)
        patterns = cursor.fetchall()
        
        print("=" * 80)
        print("🔍 Pattern Effectiveness Analysis")
        print("=" * 80)
        
        if not patterns:
            print("\n⚠️  No patterns found in telemetry data yet.")
            print("Run some commands with earlyexit to collect data.")
            return 0
        
        print(f"\n{'Pattern':<40} {'Uses':>6} {'Matches':>8} {'Rate':>8} {'Avg Time':>10}")
        print("-" * 80)
        
        for pattern, uses, matches, avg_runtime, avg_match_time in patterns:
            match_rate = (matches / uses * 100) if uses > 0 else 0
            pattern_display = pattern[:37] + "..." if len(pattern) > 40 else pattern
            runtime_display = f"{avg_runtime:.2f}s" if avg_runtime else "N/A"
            
            print(f"{pattern_display:<40} {uses:>6} {matches:>8} {match_rate:>7.1f}% {runtime_display:>10}")
        
        # Top patterns by success rate
        cursor.execute("""
            SELECT 
                pattern,
                COUNT(*) as uses,
                SUM(CASE WHEN exit_reason = 'match' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
            FROM executions
            WHERE exit_reason IN ('match', 'no_match')
            GROUP BY pattern
            HAVING uses >= 2
            ORDER BY success_rate DESC
            LIMIT 5
        """)
        top_patterns = cursor.fetchall()
        
        if top_patterns:
            print("\n" + "=" * 80)
            print("⭐ Most Effective Patterns (minimum 2 uses):")
            print("-" * 80)
            for i, (pattern, uses, rate) in enumerate(top_patterns, 1):
                pattern_display = pattern[:60] + "..." if len(pattern) > 63 else pattern
                print(f"{i}. {pattern_display}")
                print(f"   Success rate: {rate:.1f}% ({uses} uses)")
    
    print("\n" + "=" * 80)
    
    return 0


def cmd_analyze_timing(args):
    """Analyze timing patterns"""
    collector = telemetry.get_telemetry()
    if not collector:
        collector = telemetry.init_telemetry(enabled=True)
    
    if not collector or not collector.enabled:
        print("❌ Telemetry is disabled or unavailable.", file=sys.stderr)
        return 1
    
    with collector._get_connection() as conn:
        if not conn:
            return 1
        
        cursor = conn.cursor()
        
        print("=" * 80)
        print("⏱️  Timing Analysis")
        print("=" * 80)
        
        # By project type
        cursor.execute("""
            SELECT 
                project_type,
                COUNT(*) as count,
                AVG(total_runtime) as avg_runtime,
                AVG(delay_exit) as avg_delay
            FROM executions
            WHERE project_type != 'unknown'
            GROUP BY project_type
            ORDER BY count DESC
        """)
        by_project = cursor.fetchall()
        
        if by_project:
            print(f"\n{'Project Type':<15} {'Count':>8} {'Avg Runtime':>15} {'Avg Delay':>12}")
            print("-" * 80)
            for ptype, count, runtime, delay in by_project:
                runtime_str = f"{runtime:.2f}s" if runtime else "N/A"
                delay_str = f"{delay:.1f}s" if delay else "N/A"
                print(f"{ptype:<15} {count:>8} {runtime_str:>15} {delay_str:>12}")
        
        # Timeout analysis
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN exit_reason = 'timeout' THEN 1 ELSE 0 END) as timeouts,
                AVG(CASE WHEN exit_reason = 'timeout' THEN overall_timeout END) as avg_timeout_limit
            FROM executions
        """)
        timeout_stats = cursor.fetchone()
        
        if timeout_stats[1] and timeout_stats[1] > 0:
            print(f"\n⏰ Timeouts:")
            print(f"  Timed out: {timeout_stats[1]} / {timeout_stats[0]} ({timeout_stats[1]/timeout_stats[0]*100:.1f}%)")
            if timeout_stats[2]:
                print(f"  Average timeout limit: {timeout_stats[2]:.1f}s")
    
    print("\n" + "=" * 80)
    return 0


def cmd_feedback(args):
    """Record user feedback for last execution"""
    collector = telemetry.get_telemetry()
    if not collector:
        collector = telemetry.init_telemetry(enabled=True)
    
    if not collector or not collector.enabled:
        print("❌ Telemetry is disabled or unavailable.", file=sys.stderr)
        return 1
    
    with collector._get_connection() as conn:
        if not conn:
            return 1
        
        cursor = conn.cursor()
        
        # Get last execution
        cursor.execute("""
            SELECT execution_id, command, pattern, exit_code, exit_reason
            FROM executions
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        last = cursor.fetchone()
        
        if not last:
            print("⚠️  No executions found in telemetry data.", file=sys.stderr)
            return 1
        
        exec_id, command, pattern, exit_code, exit_reason = last
        
        print(f"📝 Providing feedback for last execution:")
        print(f"   Command: {command}")
        print(f"   Pattern: {pattern}")
        print(f"   Exit: {exit_code} ({exit_reason})")
        print()
        
        # Update with feedback
        updates = []
        values = []
        
        if args.rating:
            if not 1 <= args.rating <= 5:
                print("❌ Rating must be between 1 and 5", file=sys.stderr)
                return 1
            updates.append("user_rating = ?")
            values.append(args.rating)
        
        if args.should_have_exited is not None:
            updates.append("should_have_exited = ?")
            values.append(1 if args.should_have_exited else 0)
        
        if not updates:
            print("⚠️  No feedback provided. Use --rating or --should-have-exited", file=sys.stderr)
            return 1
        
        values.append(exec_id)
        cursor.execute(f"""
            UPDATE executions
            SET {', '.join(updates)}
            WHERE execution_id = ?
        """, values)
        
        conn.commit()
        
        print("✅ Feedback recorded!")
        print(f"   Execution ID: {exec_id}")
        if args.rating:
            print(f"   Rating: {'⭐' * args.rating}")
        if args.should_have_exited is not None:
            print(f"   Should have exited: {'Yes' if args.should_have_exited else 'No'}")
        
    return 0


def cmd_export(args):
    """Export telemetry data"""
    collector = telemetry.get_telemetry()
    if not collector:
        collector = telemetry.init_telemetry(enabled=True)
    
    if not collector or not collector.enabled:
        print("❌ Telemetry is disabled or unavailable.", file=sys.stderr)
        return 1
    
    with collector._get_connection() as conn:
        if not conn:
            return 1
        
        cursor = conn.cursor()
        
        # Get all executions
        cursor.execute("""
            SELECT 
                execution_id, timestamp, command, command_hash, working_directory,
                pattern, pattern_type, case_insensitive, invert_match, max_count,
                overall_timeout, idle_timeout, first_output_timeout, delay_exit,
                exit_code, exit_reason,
                total_runtime, time_to_first_output, time_to_first_match, time_from_match_to_exit,
                match_count,
                total_lines_processed, stdout_lines, stderr_lines,
                user_rating, should_have_exited,
                project_type, command_category
            FROM executions
            ORDER BY timestamp
        """)
        
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        
        if not rows:
            print("⚠️  No data to export.", file=sys.stderr)
            return 1
        
        if args.format == 'json':
            data = []
            for row in rows:
                data.append(dict(zip(columns, row)))
            print(json.dumps(data, indent=2))
            
        elif args.format == 'csv':
            writer = csv.writer(sys.stdout)
            writer.writerow(columns)
            writer.writerows(rows)
            
        elif args.format == 'jsonl':
            for row in rows:
                print(json.dumps(dict(zip(columns, row))))
        
        else:
            print(f"❌ Unknown format: {args.format}", file=sys.stderr)
            return 1
    
    return 0


def cmd_clear(args):
    """Clear telemetry data"""
    collector = telemetry.get_telemetry()
    if not collector:
        collector = telemetry.init_telemetry(enabled=True)
    
    if not collector or not collector.enabled:
        print("❌ Telemetry is disabled or unavailable.", file=sys.stderr)
        return 1
    
    import os
    from datetime import datetime, timedelta
    
    if args.older_than:
        # Parse duration (e.g., "30d", "7d", "90d")
        try:
            if args.older_than.endswith('d'):
                days = int(args.older_than[:-1])
            else:
                days = int(args.older_than)
            
            cutoff_time = (datetime.now() - timedelta(days=days)).timestamp()
            
            with collector._get_connection() as conn:
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM executions WHERE timestamp < ?", (cutoff_time,))
                    count = cursor.fetchone()[0]
                    
                    if count == 0:
                        print(f"⚠️  No records older than {days} days found.")
                        return 0
                    
                    print(f"⚠️  This will delete {count} records older than {days} days.")
                    
                    if not args.yes:
                        response = input("Continue? [y/N] ")
                        if response.lower() != 'y':
                            print("Cancelled.")
                            return 0
                    
                    cursor.execute("DELETE FROM executions WHERE timestamp < ?", (cutoff_time,))
                    conn.commit()
                    
                    print(f"✅ Deleted {count} old records.")
        
        except ValueError:
            print(f"❌ Invalid duration: {args.older_than}", file=sys.stderr)
            print("Use format like: 30d, 7d, 90d", file=sys.stderr)
            return 1
    
    elif args.all:
        with collector._get_connection() as conn:
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM executions")
                count = cursor.fetchone()[0]
                
                if count == 0:
                    print("⚠️  No records to delete.")
                    return 0
                
                print(f"⚠️  This will delete ALL {count} telemetry records.")
                
                if not args.yes:
                    response = input("Continue? [y/N] ")
                    if response.lower() != 'y':
                        print("Cancelled.")
                        return 0
                
                cursor.execute("DELETE FROM executions")
                conn.commit()
                
                print(f"✅ Deleted all {count} records.")
    
    else:
        print("❌ Specify --older-than or --all", file=sys.stderr)
        return 1
    
    return 0


def cmd_suggest(args):
    """Suggest optimal patterns and parameters for a command"""
    collector = telemetry.get_telemetry()
    if not collector:
        collector = telemetry.init_telemetry(enabled=True)
    
    if not collector or not collector.enabled:
        print("❌ Telemetry is disabled or unavailable.", file=sys.stderr)
        return 1
    
    # Create inference engine
    engine = inference.get_inference_engine(collector)
    if not engine:
        print("❌ Inference engine unavailable.", file=sys.stderr)
        return 1
    
    command = args.command if hasattr(args, 'command') else None
    
    print("=" * 80)
    print("🤖 earlyexit Intelligent Suggestions")
    print("=" * 80)
    
    if command:
        print(f"\nCommand: {command}")
    
    # Get project context
    project_type, cwd = engine._detect_context()
    print(f"Project Type: {project_type}")
    print(f"Working Directory: {cwd}")
    
    # Get pattern suggestions
    print("\n" + "─" * 80)
    print("📋 Recommended Patterns:")
    print("─" * 80)
    
    pattern_suggestions = engine.suggest_patterns(command, limit=5)
    
    if not pattern_suggestions:
        print("\n⚠️  No pattern recommendations available yet.")
        print("Run some commands with earlyexit to build up telemetry data.")
    else:
        for i, suggestion in enumerate(pattern_suggestions, 1):
            confidence_bar = "█" * int(suggestion['confidence'] * 10)
            print(f"\n{i}. Pattern: {suggestion['pattern']}")
            print(f"   Confidence: {confidence_bar} {suggestion['confidence']*100:.1f}%")
            print(f"   {suggestion['rationale']}")
    
    # Get timeout suggestions
    print("\n" + "─" * 80)
    print("⏱️  Recommended Timeouts:")
    print("─" * 80)
    
    timeout_suggestions = engine.suggest_timeouts(command)
    
    if timeout_suggestions:
        print(f"\nOverall Timeout:  {timeout_suggestions.get('overall_timeout', 300):.1f}s")
        print(f"Idle Timeout:     {timeout_suggestions.get('idle_timeout', 30):.1f}s")
        print(f"Delay Exit:       {timeout_suggestions.get('delay_exit', 10):.1f}s")
        print(f"\nConfidence: {timeout_suggestions.get('confidence', 0)*100:.1f}%")
        print(f"Rationale: {timeout_suggestions.get('rationale', 'Based on defaults')}")
    
    # Generate example command
    if pattern_suggestions and command:
        best_pattern = pattern_suggestions[0]
        print("\n" + "─" * 80)
        print("💡 Suggested Command:")
        print("─" * 80)
        
        cmd_parts = ["earlyexit"]
        cmd_parts.append(f'--pattern "{best_pattern["pattern"]}"')
        cmd_parts.append(f'--timeout {timeout_suggestions.get("overall_timeout", 300):.0f}')
        cmd_parts.append(f'--idle-timeout {timeout_suggestions.get("idle_timeout", 30):.0f}')
        cmd_parts.append(f'--delay-exit {timeout_suggestions.get("delay_exit", 10):.0f}')
        cmd_parts.append(f'-- {command}')
        
        print(f"\n{' '.join(cmd_parts)}")
    
    print("\n" + "=" * 80)
    
    return 0


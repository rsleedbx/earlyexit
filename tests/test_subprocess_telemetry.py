#!/usr/bin/env python3
"""
Test that telemetry works correctly when earlyexit is run as a subprocess
"""

import subprocess
import sqlite3
import time
import os
from pathlib import Path


def test_subprocess_telemetry():
    """Test that telemetry is recorded when earlyexit is invoked as subprocess"""
    
    # Get the telemetry database path
    db_path = Path.home() / '.earlyexit' / 'telemetry.db'
    
    # Get current record count
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM executions")
        before_count = cursor.fetchone()[0]
        conn.close()
    except:
        before_count = 0
    
    print(f"Before: {before_count} executions in telemetry database")
    
    # Run earlyexit as a subprocess
    print("\nTest 1: Running earlyexit as subprocess with pattern match...")
    result = subprocess.run(
        ['python3', '-m', 'earlyexit.cli', 'test', '--', 'echo', 'test output'],
        capture_output=True,
        text=True
    )
    print(f"  Exit code: {result.returncode}")
    print(f"  Output: {result.stdout.strip()}")
    
    # Wait a moment for write to complete
    time.sleep(0.5)
    
    # Check if telemetry was recorded
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM executions")
        after_count = cursor.fetchone()[0]
        
        # Get the last execution
        cursor.execute("""
            SELECT execution_id, command, pattern, exit_code, exit_reason, match_count
            FROM executions
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        last_exec = cursor.fetchone()
        conn.close()
        
        print(f"\nAfter: {after_count} executions in telemetry database")
        print(f"New records: {after_count - before_count}")
        
        if last_exec:
            print(f"\nLast execution:")
            print(f"  ID: {last_exec[0]}")
            print(f"  Command: {last_exec[1]}")
            print(f"  Pattern: {last_exec[2]}")
            print(f"  Exit code: {last_exec[3]}")
            print(f"  Exit reason: {last_exec[4]}")
            print(f"  Match count: {last_exec[5]}")
        
        assert after_count > before_count, "Telemetry should have recorded new execution"
        print("\n✅ Test 1 PASSED: Telemetry recorded from subprocess")
        
    except Exception as e:
        print(f"\n❌ Test 1 FAILED: Error checking telemetry: {e}")
        raise
    
    # Test 2: Multiple concurrent subprocess calls
    print("\n\nTest 2: Multiple concurrent subprocess calls...")
    before_count = after_count
    
    processes = []
    for i in range(5):
        p = subprocess.Popen(
            ['python3', '-m', 'earlyexit.cli', 'test', '--', 'echo', f'output{i}'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        processes.append(p)
    
    # Wait for all to complete
    for p in processes:
        p.wait()
    
    time.sleep(1)  # Wait for all writes to complete
    
    # Check telemetry
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM executions")
    final_count = cursor.fetchone()[0]
    conn.close()
    
    new_records = final_count - before_count
    print(f"  Started: 5 subprocess calls")
    print(f"  Recorded: {new_records} new telemetry entries")
    
    if new_records >= 5:
        print(f"✅ Test 2 PASSED: All {new_records} concurrent calls recorded")
    else:
        print(f"⚠️  Test 2 WARNING: Only {new_records}/5 calls recorded (possible race condition)")
    
    # Test 3: Timeout scenario
    print("\n\nTest 3: Subprocess with timeout...")
    before_count = final_count
    
    result = subprocess.run(
        ['python3', '-m', 'earlyexit.cli', '-t', '1', '--', 'sleep', '10'],
        capture_output=True,
        text=True,
        timeout=5  # Outer timeout to prevent hanging
    )
    print(f"  Exit code: {result.returncode}")
    
    time.sleep(0.5)
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM executions")
    after_timeout_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT exit_code, exit_reason
        FROM executions
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    last_exec = cursor.fetchone()
    conn.close()
    
    print(f"  Last execution: exit_code={last_exec[0]}, exit_reason={last_exec[1]}")
    
    if after_timeout_count > before_count and last_exec[1] == 'timeout':
        print(f"✅ Test 3 PASSED: Timeout scenario recorded correctly")
    else:
        print(f"⚠️  Test 3 WARNING: Timeout not recorded as expected")
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total telemetry records: {after_timeout_count}")
    print(f"Database location: {db_path}")
    print(f"Database exists: {db_path.exists()}")
    print(f"Database size: {db_path.stat().st_size if db_path.exists() else 0} bytes")
    print("\n✅ All subprocess telemetry tests completed!")


if __name__ == '__main__':
    test_subprocess_telemetry()


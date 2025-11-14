#!/usr/bin/env python3
"""
Test telemetry cleanup functionality
"""

import os
import sys
import time
import tempfile
import sqlite3
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from earlyexit.telemetry import TelemetryCollector


def test_auto_cleanup():
    """Test that auto-cleanup runs every 100 executions"""
    print("Test 1: Auto-cleanup triggers every 100 executions")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        collector = TelemetryCollector(db_path=db_path, enabled=True)
        
        # Add 99 executions (should not trigger cleanup)
        for i in range(99):
            collector.record_execution({
                'command': f'test-{i}',
                'pattern': 'ERROR',
                'exit_code': 0,
                'timestamp': time.time() - (100 - i) * 86400  # Old data
            })
        
        count_before = collector.get_execution_count()
        print(f"   Added {count_before} executions")
        
        # This should not trigger cleanup (99 % 100 != 0)
        collector.auto_cleanup()
        count_after = collector.get_execution_count()
        
        if count_after == count_before:
            print(f"   ✅ No cleanup at 99 executions (still {count_after})")
        else:
            print(f"   ❌ FAIL: Unexpected cleanup at 99 executions")
            return False
        
        # Add one more (100th execution should trigger cleanup)
        collector.record_execution({
            'command': 'test-100',
            'pattern': 'ERROR',
            'exit_code': 0,
            'timestamp': time.time()  # Recent
        })
        
        count_before = collector.get_execution_count()
        print(f"   Now have {count_before} executions")
        
        # This should trigger cleanup (100 % 100 == 0)
        collector.auto_cleanup()
        count_after = collector.get_execution_count()
        
        if count_after < count_before:
            print(f"   ✅ Cleanup triggered at 100 executions ({count_before} → {count_after})")
        else:
            print(f"   ❌ FAIL: No cleanup at 100 executions")
            return False
        
        collector.close()
    
    return True


def test_cleanup_old_data():
    """Test that cleanup_old_data removes old executions"""
    print("\nTest 2: cleanup_old_data removes old executions")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        collector = TelemetryCollector(db_path=db_path, enabled=True)
        
        # Add old executions (40 days ago)
        for i in range(10):
            collector.record_execution({
                'command': f'old-{i}',
                'pattern': 'ERROR',
                'exit_code': 0,
                'timestamp': time.time() - (40 * 86400)
            })
        
        # Add recent executions (5 days ago)
        for i in range(10):
            collector.record_execution({
                'command': f'recent-{i}',
                'pattern': 'ERROR',
                'exit_code': 0,
                'timestamp': time.time() - (5 * 86400)
            })
        
        count_before = collector.get_execution_count()
        print(f"   Added {count_before} executions (10 old, 10 recent)")
        
        # Clean up data older than 30 days
        collector.cleanup_old_data(days=30, max_size_mb=1000)  # High limit to test days only
        
        count_after = collector.get_execution_count()
        print(f"   After cleanup: {count_after} executions")
        
        if count_after == 10:
            print(f"   ✅ Removed old data (20 → 10)")
        else:
            print(f"   ❌ FAIL: Expected 10, got {count_after}")
            return False
        
        collector.close()
    
    return True


def test_cleanup_by_size():
    """Test that cleanup_old_data removes oldest 50% when size exceeds limit"""
    print("\nTest 3: cleanup_old_data removes oldest 50% when size limit exceeded")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        collector = TelemetryCollector(db_path=db_path, enabled=True)
        
        # Add many executions to make database large
        for i in range(100):
            collector.record_execution({
                'command': f'test-{i}' * 100,  # Long command to increase size
                'pattern': 'ERROR' * 100,
                'exit_code': 0,
                'timestamp': time.time() - (100 - i) * 100  # Oldest first
            })
        
        count_before = collector.get_execution_count()
        size_before = collector.get_db_size_mb()
        print(f"   Added {count_before} executions, size: {size_before:.1f} MB")
        
        # Set a very low size limit to trigger size-based cleanup
        collector.cleanup_old_data(days=1000, max_size_mb=0.1)  # 100 KB limit
        
        count_after = collector.get_execution_count()
        size_after = collector.get_db_size_mb()
        print(f"   After cleanup: {count_after} executions, size: {size_after:.1f} MB")
        
        if count_after <= count_before / 2:
            print(f"   ✅ Removed oldest 50% ({count_before} → {count_after})")
        else:
            print(f"   ❌ FAIL: Expected ~{count_before // 2}, got {count_after}")
            return False
        
        collector.close()
    
    return True


def test_clear_executions_only():
    """Test that clear_executions_only keeps learned settings"""
    print("\nTest 4: clear_executions_only preserves learned settings")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        collector = TelemetryCollector(db_path=db_path, enabled=True)
        
        # Add executions
        for i in range(10):
            collector.record_execution({
                'command': f'test-{i}',
                'pattern': 'ERROR',
                'exit_code': 0,
                'timestamp': time.time()
            })
        
        # Add learned settings
        for i in range(5):
            collector.save_learned_setting({
                'command_hash': f'hash-{i}',
                'pattern': f'ERROR-{i}',
                'timeout': 300
            })
        
        exec_count_before = collector.get_execution_count()
        
        with collector._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM learned_settings WHERE is_active = 1")
            learned_count_before = cursor.fetchone()[0]
        
        print(f"   Before: {exec_count_before} executions, {learned_count_before} learned settings")
        
        # Clear executions only
        collector.clear_executions_only()
        
        exec_count_after = collector.get_execution_count()
        
        with collector._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM learned_settings WHERE is_active = 1")
            learned_count_after = cursor.fetchone()[0]
        
        print(f"   After: {exec_count_after} executions, {learned_count_after} learned settings")
        
        if exec_count_after == 0 and learned_count_after == learned_count_before:
            print(f"   ✅ Cleared executions, kept learned settings")
        else:
            print(f"   ❌ FAIL: Expected 0 executions and {learned_count_before} learned, got {exec_count_after} and {learned_count_after}")
            return False
        
        collector.close()
    
    return True


def test_clear_all_data():
    """Test that clear_all_data removes everything"""
    print("\nTest 5: clear_all_data removes everything")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        collector = TelemetryCollector(db_path=db_path, enabled=True)
        
        # Add executions and learned settings
        for i in range(10):
            collector.record_execution({
                'command': f'test-{i}',
                'pattern': 'ERROR',
                'exit_code': 0,
                'timestamp': time.time()
            })
        
        for i in range(5):
            collector.save_learned_setting({
                'command_hash': f'hash-{i}',
                'pattern': f'ERROR-{i}',
                'timeout': 300
            })
        
        exec_count_before = collector.get_execution_count()
        
        with collector._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM learned_settings WHERE is_active = 1")
            learned_count_before = cursor.fetchone()[0]
        
        print(f"   Before: {exec_count_before} executions, {learned_count_before} learned settings")
        
        # Clear all data
        collector.clear_all_data()
        
        exec_count_after = collector.get_execution_count()
        
        with collector._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM learned_settings WHERE is_active = 1")
            learned_count_after = cursor.fetchone()[0]
        
        print(f"   After: {exec_count_after} executions, {learned_count_after} learned settings")
        
        if exec_count_after == 0 and learned_count_after == 0:
            print(f"   ✅ Cleared everything")
        else:
            print(f"   ❌ FAIL: Expected 0 and 0, got {exec_count_after} and {learned_count_after}")
            return False
        
        collector.close()
    
    return True


def test_get_db_size():
    """Test that get_db_size_mb returns correct size"""
    print("\nTest 6: get_db_size_mb returns correct size")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        collector = TelemetryCollector(db_path=db_path, enabled=True)
        
        size_empty = collector.get_db_size_mb()
        print(f"   Empty database: {size_empty:.3f} MB")
        
        # Add data
        for i in range(100):
            collector.record_execution({
                'command': f'test-{i}' * 100,
                'pattern': 'ERROR' * 100,
                'exit_code': 0,
                'timestamp': time.time()
            })
        
        size_with_data = collector.get_db_size_mb()
        print(f"   With 100 executions: {size_with_data:.3f} MB")
        
        if size_with_data > size_empty:
            print(f"   ✅ Size increased as expected")
        else:
            print(f"   ❌ FAIL: Size did not increase")
            return False
        
        collector.close()
    
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Telemetry Cleanup Functionality")
    print("=" * 60)
    
    tests = [
        test_auto_cleanup,
        test_cleanup_old_data,
        test_cleanup_by_size,
        test_clear_executions_only,
        test_clear_all_data,
        test_get_db_size
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   ❌ EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())





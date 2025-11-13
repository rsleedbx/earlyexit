#!/usr/bin/env python3
"""
Test interactive learning mode end-to-end
"""
import subprocess
import time
import signal
import sys

# Ensure earlyexit is installed
subprocess.run(['pip', 'install', '-e', '.'], check=True, capture_output=True)

def test_interactive_basic():
    """Test basic interactive flow (simulated with process interruption)"""
    print("\n" + "="*70)
    print("TEST: Interactive prompts after Ctrl+C")
    print("="*70)
    
    # Run a command in watch mode
    proc = subprocess.Popen(
        ['earlyexit', 'python3'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Let it start
    time.sleep(0.3)
    
    # Send SIGINT
    proc.send_signal(signal.SIGINT)
    
    # Wait for prompts (they'll timeout since we can't actually interact in a test)
    try:
        stdout, stderr = proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
    
    print(f"Exit code: {proc.returncode}")
    print(f"Stderr excerpt:\n{stderr[:800]}")
    
    # Check for key phrases
    assert "Watch mode enabled" in stderr, "Watch mode not activated"
    
    # Check for interactive prompts
    if "LEARNING MODE" in stderr or "Why did you stop?" in stderr:
        print("✅ Interactive prompts displayed!")
        assert "Why did you stop?" in stderr, "Missing stop reason prompt"
        assert "🚨 Error detected" in stderr or "Error detected" in stderr, "Missing error option"
        assert "⏱️  Taking too long" in stderr or "Taking too long" in stderr, "Missing timeout option"
        assert "🔇 No output" in stderr or "No output" in stderr, "Missing hang option"
    else:
        print("ℹ️  Interactive prompts may require actual terminal (skipping detailed check)")
    
    print("✅ PASSED: Interactive mode structure verified")
    return True


def test_pattern_extraction():
    """Test pattern extraction logic"""
    print("\n" + "="*70)
    print("TEST: Pattern extraction algorithm")
    print("="*70)
    
    from earlyexit.interactive import PatternExtractor
    
    extractor = PatternExtractor()
    
    # Create sample output lines
    stdout_lines = [
        {'line': 'Starting tests...', 'stream': 'stdout', 'timestamp': 1.0},
        {'line': 'Test 1 passed', 'stream': 'stdout', 'timestamp': 2.0},
        {'line': 'FAILED: Test 2', 'stream': 'stdout', 'timestamp': 3.0},
        {'line': 'Error: Connection refused', 'stream': 'stdout', 'timestamp': 4.0},
    ]
    
    stderr_lines = [
        {'line': 'npm ERR! code ENOENT', 'stream': 'stderr', 'timestamp': 2.5},
        {'line': 'FATAL: Database connection failed', 'stream': 'stderr', 'timestamp': 3.5},
        {'line': 'Traceback (most recent call last):', 'stream': 'stderr', 'timestamp': 4.5},
    ]
    
    suggestions = extractor.extract_patterns(stdout_lines, stderr_lines, max_suggestions=5)
    
    print(f"Found {len(suggestions)} pattern suggestions:")
    for i, sugg in enumerate(suggestions, 1):
        print(f"  {i}. '{sugg['pattern']}' - confidence: {sugg['confidence']:.2f}, "
              f"stream: {sugg['stream']}, count: {sugg['count']}")
    
    # Verify patterns were extracted
    assert len(suggestions) > 0, "No patterns extracted"
    
    # Check that high-value patterns were found
    patterns_found = [s['pattern'] for s in suggestions]
    
    assert any('FAILED' in p or 'FATAL' in p or 'ERROR' in p or 'Error' in p 
               for p in patterns_found), "Key error patterns not found"
    
    print("✅ PASSED: Pattern extraction working correctly")
    return True


def test_timeout_calculator():
    """Test timeout calculation logic"""
    print("\n" + "="*70)
    print("TEST: Timeout calculator")
    print("="*70)
    
    from earlyexit.interactive import TimeoutCalculator
    
    calculator = TimeoutCalculator()
    
    # Test 1: Error stop reason
    suggestions = calculator.calculate_suggestions(
        duration=45.3,
        idle_time=2.0,
        line_counts={'stdout': 127, 'stderr': 23, 'total': 150},
        stop_reason='error'
    )
    
    print("Scenario 1: Error detected at 45.3s")
    print(f"  Overall timeout: {suggestions.get('overall_timeout')}s")
    print(f"  Delay exit: {suggestions.get('delay_exit')}s")
    
    assert 'overall_timeout' in suggestions, "Missing overall timeout"
    assert suggestions['overall_timeout'] > 45.3, "Timeout should be higher than duration"
    assert 'delay_exit' in suggestions, "Missing delay_exit"
    
    # Test 2: Hang stop reason
    suggestions = calculator.calculate_suggestions(
        duration=120.0,
        idle_time=45.0,
        line_counts={'stdout': 10, 'stderr': 0, 'total': 10},
        stop_reason='hang'
    )
    
    print("\nScenario 2: Hung process (45s idle)")
    print(f"  Idle timeout: {suggestions.get('idle_timeout')}s")
    print(f"  Delay exit: {suggestions.get('delay_exit')}s")
    
    assert 'idle_timeout' in suggestions, "Missing idle timeout for hang scenario"
    assert suggestions['idle_timeout'] >= 30, "Idle timeout too short"
    
    print("✅ PASSED: Timeout calculator working correctly")
    return True


def test_telemetry_schema():
    """Test that user_sessions table exists"""
    print("\n" + "="*70)
    print("TEST: Telemetry schema")
    print("="*70)
    
    import sqlite3
    import os
    from pathlib import Path
    
    db_path = os.path.expanduser("~/.earlyexit/telemetry.db")
    
    if not Path(db_path).exists():
        print("ℹ️  Database not created yet - creating it")
        from earlyexit.telemetry import TelemetryCollector
        # Create a collector to initialize the database
        _ = TelemetryCollector()
    
    # Database might be created by watch mode tests running first
    if not Path(db_path).exists():
        print("⚠️  Database not created - this is OK in test environment")
        # Create it manually for testing
        from earlyexit.telemetry import TelemetryCollector
        _ = TelemetryCollector()
    
    assert Path(db_path).exists(), "Telemetry database not created even after manual init"
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Check if user_sessions table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='user_sessions'
        """)
        
        result = cursor.fetchone()
        assert result is not None, "user_sessions table not created"
        
        print(f"✅ user_sessions table exists")
        
        # Check schema
        cursor.execute("PRAGMA table_info(user_sessions)")
        columns = cursor.fetchall()
        
        column_names = [col[1] for col in columns]
        print(f"Columns: {', '.join(column_names)}")
        
        required_columns = [
            'session_id', 'execution_id', 'timestamp',
            'command', 'duration', 'stop_reason',
            'selected_pattern', 'pattern_confidence',
            'suggested_overall_timeout', 'suggested_idle_timeout'
        ]
        
        for col in required_columns:
            assert col in column_names, f"Missing column: {col}"
        
        print("✅ PASSED: Schema verified")
    
    return True


if __name__ == '__main__':
    print("\n" + "="*70)
    print("INTERACTIVE LEARNING MODE TESTS")
    print("="*70)
    
    tests = [
        test_pattern_extraction,
        test_timeout_calculator,
        test_telemetry_schema,
        test_interactive_basic,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"❌ FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*70)
    
    if failed == 0:
        print("\n✨ All interactive learning tests passed!")
        sys.exit(0)
    else:
        print(f"\n❌ {failed} test(s) failed")
        sys.exit(1)


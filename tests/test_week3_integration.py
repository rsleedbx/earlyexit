#!/usr/bin/env python3
"""
Week 3 Integration Test - Smart Suggestions End-to-End
"""
import os
import sys
import sqlite3
import json
from pathlib import Path

def test_learned_settings_table():
    """Test that learned_settings table is created correctly"""
    print("\n" + "="*70)
    print("TEST: Learned Settings Table Schema")
    print("="*70)
    
    # Remove old database for fresh start
    db_path = os.path.expanduser("~/.earlyexit/telemetry.db")
    if Path(db_path).exists():
        os.remove(db_path)
    
    # Initialize database
    from earlyexit.telemetry import TelemetryCollector
    collector = TelemetryCollector()
    
    assert Path(db_path).exists(), "Database not created"
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Check if learned_settings table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='learned_settings'
        """)
        assert cursor.fetchone() is not None, "learned_settings table not found"
        
        # Check schema
        cursor.execute("PRAGMA table_info(learned_settings)")
        columns = {col[1] for col in cursor.fetchall()}
        
        required_columns = {
            'setting_id', 'command_hash', 'project_type',
            'features_json', 'learned_pattern', 'pattern_confidence',
            'learned_timeout', 'learned_idle_timeout', 'learned_delay_exit',
            'true_positives', 'true_negatives', 'false_positives', 'false_negatives',
            'user_confirmed_good', 'user_rejected',
            'times_used', 'last_used_timestamp', 'created_timestamp',
            'is_active'
        }
        
        missing = required_columns - columns
        assert not missing, f"Missing columns: {missing}"
        
        print(f"✅ learned_settings table has {len(columns)} columns")
        print(f"   Columns: {', '.join(sorted(columns))}")
    
    print("✅ PASSED: Schema verified")
    return True


def test_save_and_retrieve_learned_setting():
    """Test saving and retrieving a learned setting"""
    print("\n" + "="*70)
    print("TEST: Save and Retrieve Learned Setting")
    print("="*70)
    
    from earlyexit.telemetry import TelemetryCollector
    
    collector = TelemetryCollector()
    
    # Create test setting
    setting_data = {
        'command_hash': 'abc123test',
        'project_type': 'python',
        'features': {
            'duration': {'name': 'duration', 'value': 45.3, 'sensitivity': 'public'},
            'project_type': {'name': 'project_type', 'value': 'python', 'sensitivity': 'public'}
        },
        'learned_pattern': 'ERROR.*failed',
        'pattern_confidence': 0.85,
        'learned_timeout': 60.0,
        'learned_idle_timeout': 30.0,
        'learned_delay_exit': 10.0
    }
    
    # Save setting
    setting_id = collector.save_learned_setting(setting_data)
    assert setting_id is not None, "Failed to save setting"
    print(f"✅ Saved setting: {setting_id}")
    
    # Retrieve setting
    retrieved = collector.get_learned_setting('abc123test', 'python')
    assert retrieved is not None, "Failed to retrieve setting"
    assert retrieved['learned_pattern'] == 'ERROR.*failed'
    assert retrieved['learned_timeout'] == 60.0
    assert retrieved['pattern_confidence'] == 0.85
    
    print(f"✅ Retrieved setting:")
    print(f"   Pattern: {retrieved['learned_pattern']}")
    print(f"   Timeout: {retrieved['learned_timeout']}s")
    print(f"   Confidence: {retrieved['pattern_confidence']}")
    
    # Test update (save again)
    setting_data['learned_pattern'] = 'FAILED.*test'
    setting_data['learned_timeout'] = 90.0
    
    setting_id2 = collector.save_learned_setting(setting_data)
    print(f"✅ Updated setting: {setting_id2}")
    
    # Retrieve updated
    retrieved2 = collector.get_learned_setting('abc123test', 'python')
    assert retrieved2['learned_pattern'] == 'FAILED.*test'
    assert retrieved2['learned_timeout'] == 90.0
    
    print(f"✅ Updated pattern: {retrieved2['learned_pattern']}")
    print(f"✅ Updated timeout: {retrieved2['learned_timeout']}s")
    
    print("✅ PASSED: Save and retrieve working")
    return True


def test_validation_update():
    """Test updating validation metrics"""
    print("\n" + "="*70)
    print("TEST: Validation Metrics Update")
    print("="*70)
    
    from earlyexit.telemetry import TelemetryCollector
    
    collector = TelemetryCollector()
    
    # Get existing setting
    retrieved = collector.get_learned_setting('abc123test', 'python')
    assert retrieved is not None
    
    setting_id = retrieved['setting_id']
    
    print(f"Initial validation:")
    print(f"   TP: {retrieved['validation']['true_positives']}")
    print(f"   TN: {retrieved['validation']['true_negatives']}")
    print(f"   FP: {retrieved['validation']['false_positives']}")
    print(f"   FN: {retrieved['validation']['false_negatives']}")
    
    # Update validation metrics
    collector.update_learned_setting_validation(setting_id, 'true_positive')
    collector.update_learned_setting_validation(setting_id, 'true_positive')
    collector.update_learned_setting_validation(setting_id, 'true_negative')
    collector.update_learned_setting_validation(setting_id, 'false_positive')
    
    # Update user feedback
    collector.update_learned_setting_validation(setting_id, 'true_positive', 'confirmed_good')
    collector.update_learned_setting_validation(setting_id, 'true_positive', 'rejected')
    
    # Retrieve updated
    updated = collector.get_learned_setting('abc123test', 'python')
    
    print(f"\nUpdated validation:")
    print(f"   TP: {updated['validation']['true_positives']} (should be 4)")
    print(f"   TN: {updated['validation']['true_negatives']} (should be 1)")
    print(f"   FP: {updated['validation']['false_positives']} (should be 1)")
    print(f"   User Confirmed: {updated['validation']['user_confirmed_good']} (should be 1)")
    print(f"   User Rejected: {updated['validation']['user_rejected']} (should be 1)")
    print(f"   Times Used: {updated['times_used']} (should be > 0)")
    
    assert updated['validation']['true_positives'] == 4
    assert updated['validation']['true_negatives'] == 1
    assert updated['validation']['false_positives'] == 1
    assert updated['validation']['user_confirmed_good'] == 1
    assert updated['validation']['user_rejected'] == 1
    
    print("✅ PASSED: Validation updates working")
    return True


def test_validation_metrics_calculation():
    """Test that validation metrics calculate recommendation correctly"""
    print("\n" + "="*70)
    print("TEST: Validation Metrics Calculation")
    print("="*70)
    
    from earlyexit.features import ValidationMetrics
    
    # Scenario 1: Excellent performance
    metrics1 = ValidationMetrics(
        true_positives=18,
        true_negatives=32,
        false_positives=2,
        false_negatives=1
    )
    
    rec1 = metrics1.get_recommendation()
    print(f"\nScenario 1: Excellent (F1={metrics1.f1_score:.2f})")
    print(f"   Recommendation: {rec1['recommendation']}")
    print(f"   Should Use: {rec1['should_use']}")
    
    assert rec1['should_use'] == True, "Should recommend for excellent performance"
    assert rec1['recommendation'] == 'HIGHLY_RECOMMENDED'
    
    # Scenario 2: Too many false alarms
    metrics2 = ValidationMetrics(
        true_positives=5,
        true_negatives=10,
        false_positives=15,
        false_negatives=3
    )
    
    rec2 = metrics2.get_recommendation()
    print(f"\nScenario 2: Poor (F1={metrics2.f1_score:.2f})")
    print(f"   Recommendation: {rec2['recommendation']}")
    print(f"   Should Use: {rec2['should_use']}")
    
    assert rec2['should_use'] == False, "Should NOT recommend for poor performance"
    
    # Scenario 3: Not enough data
    metrics3 = ValidationMetrics(
        true_positives=2,
        true_negatives=1
    )
    
    rec3 = metrics3.get_recommendation()
    print(f"\nScenario 3: Insufficient data (only {metrics3.total_runs} runs)")
    print(f"   Recommendation: {rec3['recommendation']}")
    
    assert rec3['recommendation'] == 'COLLECT_MORE_DATA'
    
    print("✅ PASSED: Recommendations calculated correctly")
    return True


def test_feature_extraction_and_json():
    """Test feature extraction and JSON storage"""
    print("\n" + "="*70)
    print("TEST: Feature Extraction and JSON")
    print("="*70)
    
    from earlyexit.features import extract_features, Feature, FeatureSensitivity
    
    session_data = {
        'project_type': 'python',
        'command_category': 'test',
        'duration': 45.3,
        'idle_time': 2.5,
        'line_counts': {'stdout': 127, 'stderr': 23, 'total': 150},
        'selected_pattern': 'ERROR',
        'pattern_stream': 'stderr',
        'stop_reason': 'error',
        'working_directory': '/Users/test/project'
    }
    
    features = extract_features(session_data)
    
    print(f"Extracted {len(features)} features")
    
    # Check key features
    assert 'project_type' in features
    assert features['project_type'].sensitivity == FeatureSensitivity.PUBLIC
    
    assert 'stderr_ratio' in features
    assert features['stderr_ratio'].value == 0.15  # 23/150
    
    assert 'working_directory_hash' in features
    assert features['working_directory_hash'].sensitivity == FeatureSensitivity.PRIVATE
    
    # Test JSON serialization
    features_dict = {name: feat.to_dict(mask_sensitive=True) for name, feat in features.items()}
    json_str = json.dumps(features_dict, indent=2)
    
    print(f"\n✅ JSON serialization successful ({len(json_str)} bytes)")
    print("Sample features:")
    for name in list(features.keys())[:5]:
        feat = features[name]
        print(f"   {name}: {feat.value} ({feat.sensitivity.value})")
    
    print("✅ PASSED: Feature extraction and JSON working")
    return True


if __name__ == '__main__':
    print("\n" + "="*70)
    print("WEEK 3 INTEGRATION TESTS")
    print("="*70)
    
    tests = [
        test_learned_settings_table,
        test_save_and_retrieve_learned_setting,
        test_validation_update,
        test_validation_metrics_calculation,
        test_feature_extraction_and_json,
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
        print("\n✨ All Week 3 integration tests passed!")
        sys.exit(0)
    else:
        print(f"\n❌ {failed} test(s) failed")
        sys.exit(1)


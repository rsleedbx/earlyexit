#!/usr/bin/env python3
"""
Test ML feature system with validation metrics
"""
import json
import sys

# Test imports
from earlyexit.features import (
    Feature, FeatureSensitivity, ValidationMetrics, LearnedSetting,
    extract_features
)

def test_feature_sensitivity():
    """Test feature sensitivity and masking"""
    print("\n" + "="*70)
    print("TEST: Feature Sensitivity & Masking")
    print("="*70)
    
    # Create features with different sensitivity levels
    public_feature = Feature(
        name="project_type",
        value="python",
        sensitivity=FeatureSensitivity.PUBLIC,
        description="Project type"
    )
    
    private_feature = Feature(
        name="working_dir",
        value="/Users/john/projects/secret-project",
        sensitivity=FeatureSensitivity.PRIVATE,
        description="Working directory"
    )
    
    sensitive_feature = Feature(
        name="custom_pattern",
        value="my-secret-error-pattern",
        sensitivity=FeatureSensitivity.SENSITIVE,
        description="Custom error pattern"
    )
    
    print("\n📊 Without masking:")
    print(f"  Public: {public_feature.to_dict(mask_sensitive=False)['value']}")
    print(f"  Private: {private_feature.to_dict(mask_sensitive=False)['value']}")
    print(f"  Sensitive: {sensitive_feature.to_dict(mask_sensitive=False)['value']}")
    
    print("\n🔒 With masking (for community sharing):")
    print(f"  Public: {public_feature.to_dict(mask_sensitive=True)['value']}")
    print(f"  Private: {private_feature.to_dict(mask_sensitive=True)['value']} (hashed)")
    print(f"  Sensitive: {sensitive_feature.to_dict(mask_sensitive=True)['value']} (masked)")
    
    print("\n✅ PASSED: Feature masking works correctly")
    return True


def test_validation_metrics_excellent():
    """Test validation with excellent performance"""
    print("\n" + "="*70)
    print("TEST: Validation Metrics - Excellent Performance")
    print("="*70)
    
    metrics = ValidationMetrics(
        true_positives=18,    # Caught 18 real errors
        true_negatives=32,    # Correctly identified 32 successful runs
        false_positives=2,    # Only 2 false alarms
        false_negatives=1,    # Missed 1 error
        user_confirmed_good=15,
        user_rejected=1
    )
    
    print(f"\n📊 Outcomes:")
    print(f"  ✅ True Positives:  {metrics.true_positives} (caught real errors)")
    print(f"  ✅ True Negatives:  {metrics.true_negatives} (correctly identified success)")
    print(f"  ⚠️  False Positives: {metrics.false_positives} (false alarms)")
    print(f"  ❌ False Negatives: {metrics.false_negatives} (missed errors)")
    print(f"\n📈 Computed Metrics:")
    print(f"  Precision: {metrics.precision:.1%}")
    print(f"  Recall:    {metrics.recall:.1%}")
    print(f"  Accuracy:  {metrics.accuracy:.1%}")
    print(f"  F1 Score:  {metrics.f1_score:.2f}")
    print(f"  User Satisfaction: {metrics.user_satisfaction:.1%}")
    
    recommendation = metrics.get_recommendation()
    print(f"\n💡 Recommendation: {recommendation['recommendation']}")
    print(f"   Confidence: {recommendation['confidence']}")
    print(f"   Should Use: {recommendation['should_use']}")
    print(f"   Message: {recommendation['message']}")
    print(f"\n   Reasons:")
    for reason in recommendation['reasons']:
        print(f"     {reason}")
    
    assert recommendation['should_use'] == True, "Should recommend use for excellent performance"
    print("\n✅ PASSED: Excellent performance recommended")
    return True


def test_validation_metrics_poor():
    """Test validation with poor performance (many false alarms)"""
    print("\n" + "="*70)
    print("TEST: Validation Metrics - Poor Performance (False Alarms)")
    print("="*70)
    
    metrics = ValidationMetrics(
        true_positives=5,     # Caught 5 real errors
        true_negatives=10,    # Correctly identified 10 successful runs
        false_positives=15,   # 15 false alarms!
        false_negatives=3,    # Missed 3 errors
        user_confirmed_good=2,
        user_rejected=8
    )
    
    print(f"\n📊 Outcomes:")
    print(f"  ✅ True Positives:  {metrics.true_positives}")
    print(f"  ✅ True Negatives:  {metrics.true_negatives}")
    print(f"  ⚠️  False Positives: {metrics.false_positives} ⚠️  TOO MANY!")
    print(f"  ❌ False Negatives: {metrics.false_negatives}")
    print(f"\n📈 Computed Metrics:")
    print(f"  Precision: {metrics.precision:.1%} ⚠️  LOW!")
    print(f"  Recall:    {metrics.recall:.1%}")
    print(f"  F1 Score:  {metrics.f1_score:.2f}")
    
    recommendation = metrics.get_recommendation()
    print(f"\n💡 Recommendation: {recommendation['recommendation']}")
    print(f"   Should Use: {recommendation['should_use']}")
    print(f"   Message: {recommendation['message']}")
    print(f"\n   Reasons:")
    for reason in recommendation['reasons']:
        print(f"     {reason}")
    
    assert recommendation['should_use'] == False, "Should NOT recommend use for poor performance"
    print("\n✅ PASSED: Poor performance correctly identified")
    return True


def test_validation_metrics_needs_data():
    """Test validation with insufficient data"""
    print("\n" + "="*70)
    print("TEST: Validation Metrics - Insufficient Data")
    print("="*70)
    
    metrics = ValidationMetrics(
        true_positives=2,
        true_negatives=1,
        false_positives=0,
        false_negatives=0
    )
    
    print(f"\n📊 Outcomes: Only {metrics.total_runs} runs")
    
    recommendation = metrics.get_recommendation()
    print(f"\n💡 Recommendation: {recommendation['recommendation']}")
    print(f"   Message: {recommendation['message']}")
    
    assert recommendation['recommendation'] == 'COLLECT_MORE_DATA'
    print("\n✅ PASSED: Insufficient data correctly identified")
    return True


def test_learned_setting_json():
    """Test JSON export/import with validation"""
    print("\n" + "="*70)
    print("TEST: JSON Export/Import")
    print("="*70)
    
    # Create features
    features = {
        'project_type': Feature('project_type', 'python', FeatureSensitivity.PUBLIC),
        'duration': Feature('duration', 45.3, FeatureSensitivity.PUBLIC),
        'working_dir': Feature('working_dir', '/secret/path', FeatureSensitivity.PRIVATE),
        'custom_pattern': Feature('custom_pattern', 'MY-ERROR', FeatureSensitivity.SENSITIVE)
    }
    
    # Create validation metrics
    validation = ValidationMetrics(
        true_positives=18,
        true_negatives=32,
        false_positives=2,
        false_negatives=1
    )
    
    # Create learned setting
    setting = LearnedSetting(
        setting_id='test-001',
        command_hash='abc123',
        project_type='python',
        features=features,
        learned_pattern='ERROR.*failed',
        pattern_confidence=0.85,
        learned_timeout=60.0,
        validation=validation
    )
    
    # Test public export (masked)
    print("\n🔒 Public Export (masked for community):")
    public_json = setting.to_json(mask_sensitive=True, include_validation=True)
    public_data = json.loads(public_json)
    
    print(f"  Project Type: {public_data['features']['project_type']['value']}")
    print(f"  Duration: {public_data['features']['duration']['value']}")
    print(f"  Working Dir: {public_data['features']['working_dir']['value']} (hashed)")
    print(f"  Custom Pattern: {public_data['features']['custom_pattern']['value']} (masked)")
    print(f"\n  Validation:")
    print(f"    Precision: {public_data['validation']['metrics']['precision']}")
    print(f"    Recall: {public_data['validation']['metrics']['recall']}")
    print(f"    F1 Score: {public_data['validation']['metrics']['f1_score']}")
    print(f"\n  Recommendation: {public_data['recommendation']['recommendation']}")
    print(f"    Should Use: {public_data['recommendation']['should_use']}")
    
    # Test private export (unmasked)
    print("\n📄 Private Export (full data for personal use):")
    private_json = setting.to_json(mask_sensitive=False, include_validation=True)
    private_data = json.loads(private_json)
    print(f"  Custom Pattern: {private_data['features']['custom_pattern']['value']} (unmasked)")
    
    # Test import
    imported_setting = LearnedSetting.from_json(public_json)
    print(f"\n📥 Imported setting:")
    print(f"  Setting ID: {imported_setting.setting_id}")
    print(f"  Pattern: {imported_setting.learned_pattern}")
    print(f"  Confidence: {imported_setting.pattern_confidence}")
    
    print("\n✅ PASSED: JSON export/import working")
    return True


def test_feature_extraction():
    """Test feature extraction from session data"""
    print("\n" + "="*70)
    print("TEST: Feature Extraction")
    print("="*70)
    
    session_data = {
        'project_type': 'node',
        'command_category': 'test',
        'duration': 45.3,
        'idle_time': 2.5,
        'line_counts': {'stdout': 127, 'stderr': 23, 'total': 150},
        'selected_pattern': 'npm ERR!',
        'pattern_stream': 'stderr',
        'stop_reason': 'error',
        'working_directory': '/Users/john/project'
    }
    
    features = extract_features(session_data)
    
    print(f"\n📊 Extracted {len(features)} features:")
    for name, feat in features.items():
        sensitivity_icon = {
            'public': '🌐',
            'private': '🔒',
            'sensitive': '🔐'
        }[feat.sensitivity.value]
        print(f"  {sensitivity_icon} {name}: {feat.value} ({feat.sensitivity.value})")
    
    # Verify key features
    assert 'project_type' in features
    assert 'stderr_ratio' in features
    assert features['stderr_ratio'].value == 0.15  # 23/150
    
    print("\n✅ PASSED: Feature extraction working")
    return True


if __name__ == '__main__':
    print("\n" + "="*70)
    print("ML FEATURES & VALIDATION SYSTEM TESTS")
    print("="*70)
    
    tests = [
        test_feature_sensitivity,
        test_validation_metrics_excellent,
        test_validation_metrics_poor,
        test_validation_metrics_needs_data,
        test_learned_setting_json,
        test_feature_extraction,
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
        print("\n✨ All ML feature tests passed!")
        sys.exit(0)
    else:
        print(f"\n❌ {failed} test(s) failed")
        sys.exit(1)





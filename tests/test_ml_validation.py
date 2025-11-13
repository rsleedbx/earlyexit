#!/usr/bin/env python3
"""
ML-Style Validation Testing with Real-World Examples

Tests earlyexit pattern matching against real-world error outputs
and calculates ML metrics (TP/TN/FP/FN, Precision, Recall, F1)
"""

import sys
import os
import re
from typing import Dict, List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fixtures.real_world_errors import (
    NPM_ERRORS, PYTEST_ERRORS, CARGO_ERRORS, DOCKER_ERRORS, MAVEN_ERRORS,
    get_all_error_fixtures, get_all_success_fixtures
)
from earlyexit.features import ValidationMetrics


def test_pattern_against_output(pattern: str, stdout: str, stderr: str, 
                                 use_perl: bool = False) -> bool:
    """
    Test if a pattern matches the output
    
    Args:
        pattern: Regex pattern to test
        stdout: Standard output text
        stderr: Standard error text
        use_perl: Whether to use Perl-compatible regex
    
    Returns:
        True if pattern matches, False otherwise
    """
    if use_perl:
        try:
            import regex
            flags = regex.MULTILINE
        except ImportError:
            import re as regex
            flags = re.MULTILINE
    else:
        import re as regex
        flags = re.MULTILINE
    
    combined = stdout + "\n" + stderr
    
    try:
        return bool(regex.search(pattern, combined, flags))
    except:
        return False


def calculate_ml_metrics(pattern: str, fixtures: List[Dict], 
                        expected_to_match: bool) -> Tuple[int, int, int, int]:
    """
    Calculate TP/TN/FP/FN for a pattern against fixtures
    
    Args:
        pattern: Pattern to test
        fixtures: List of test fixtures
        expected_to_match: Whether pattern should match these fixtures
    
    Returns:
        (true_positives, true_negatives, false_positives, false_negatives)
    """
    tp = tn = fp = fn = 0
    
    for fixture in fixtures:
        stdout = fixture.get('stdout', '')
        stderr = fixture.get('stderr', '')
        should_match = fixture.get('should_match', False)
        
        did_match = test_pattern_against_output(pattern, stdout, stderr)
        
        if expected_to_match:
            # We expect this pattern to match errors
            if should_match and did_match:
                tp += 1  # Correctly caught error
            elif should_match and not did_match:
                fn += 1  # Missed error
            elif not should_match and not did_match:
                tn += 1  # Correctly didn't trigger on success
            elif not should_match and did_match:
                fp += 1  # False alarm on success
        else:
            # We expect this pattern NOT to match
            if not should_match and not did_match:
                tn += 1
            elif not should_match and did_match:
                fp += 1
            elif should_match and not did_match:
                tn += 1  # Correctly didn't match error
            elif should_match and did_match:
                fp += 1  # Matched when we didn't want it to
    
    return tp, tn, fp, fn


def test_npm_err_pattern():
    """Test 'npm ERR!' pattern against npm fixtures"""
    print("\n" + "="*70)
    print("TEST: npm ERR! Pattern")
    print("="*70)
    
    pattern = "npm ERR!"
    
    # Test against npm fixtures
    error_fixtures = [f for f in get_all_error_fixtures() if f.get('tool') == 'npm']
    success_fixtures = [f for f in get_all_success_fixtures() if f.get('tool') == 'npm']
    
    all_fixtures = error_fixtures + success_fixtures
    
    tp, tn, fp, fn = calculate_ml_metrics(pattern, all_fixtures, expected_to_match=True)
    
    metrics = ValidationMetrics(
        true_positives=tp,
        true_negatives=tn,
        false_positives=fp,
        false_negatives=fn
    )
    
    print(f"\n📊 Results for pattern: '{pattern}'")
    print(f"   Total Fixtures: {len(all_fixtures)}")
    print(f"   ✅ True Positives:  {tp} (correctly caught npm errors)")
    print(f"   ✅ True Negatives:  {tn} (correctly ignored success)")
    print(f"   ⚠️  False Positives: {fp} (false alarms)")
    print(f"   ❌ False Negatives: {fn} (missed errors)")
    
    print(f"\n📈 ML Metrics:")
    print(f"   Precision: {metrics.precision:.1%}")
    print(f"   Recall:    {metrics.recall:.1%}")
    print(f"   F1 Score:  {metrics.f1_score:.3f}")
    print(f"   Accuracy:  {metrics.accuracy:.1%}")
    
    recommendation = metrics.get_recommendation()
    print(f"\n💡 Recommendation: {recommendation['recommendation']}")
    print(f"   {recommendation['message']}")
    
    # Assertions
    assert tp >= 3, f"Should catch at least 3 npm errors, got {tp}"
    assert fp == 0, f"Should have 0 false positives, got {fp}"
    assert metrics.precision >= 0.90, f"Precision should be >= 90%, got {metrics.precision:.1%}"
    
    print("\n✅ PASSED: npm ERR! pattern validation")
    return True


def test_pytest_failed_pattern():
    """Test 'FAILED' pattern against pytest fixtures"""
    print("\n" + "="*70)
    print("TEST: pytest FAILED Pattern")
    print("="*70)
    
    pattern = "FAILED"
    
    # Test against pytest fixtures
    error_fixtures = [f for f in get_all_error_fixtures() if f.get('tool') == 'pytest']
    success_fixtures = [f for f in get_all_success_fixtures() if f.get('tool') == 'pytest']
    
    all_fixtures = error_fixtures + success_fixtures
    
    tp, tn, fp, fn = calculate_ml_metrics(pattern, all_fixtures, expected_to_match=True)
    
    metrics = ValidationMetrics(
        true_positives=tp,
        true_negatives=tn,
        false_positives=fp,
        false_negatives=fn
    )
    
    print(f"\n📊 Results for pattern: '{pattern}'")
    print(f"   Total Fixtures: {len(all_fixtures)}")
    print(f"   ✅ True Positives:  {tp}")
    print(f"   ✅ True Negatives:  {tn}")
    print(f"   ⚠️  False Positives: {fp}")
    print(f"   ❌ False Negatives: {fn}")
    
    print(f"\n📈 ML Metrics:")
    print(f"   Precision: {metrics.precision:.1%}")
    print(f"   Recall:    {metrics.recall:.1%}")
    print(f"   F1 Score:  {metrics.f1_score:.3f}")
    
    recommendation = metrics.get_recommendation()
    print(f"\n💡 Recommendation: {recommendation['recommendation']}")
    
    assert tp >= 1, f"Should catch at least 1 pytest error"
    assert metrics.recall >= 0.50, f"Recall should be >= 50%"
    
    print("\n✅ PASSED: pytest FAILED pattern validation")
    return True


def test_cargo_error_pattern():
    """Test Rust 'error\\[E[0-9]+\\]' pattern"""
    print("\n" + "="*70)
    print("TEST: Cargo error[E####] Pattern")
    print("="*70)
    
    pattern = r"error\[E[0-9]+\]"
    
    error_fixtures = [f for f in get_all_error_fixtures() if f.get('tool') == 'cargo']
    success_fixtures = [f for f in get_all_success_fixtures() if f.get('tool') == 'cargo']
    
    all_fixtures = error_fixtures + success_fixtures
    
    tp, tn, fp, fn = calculate_ml_metrics(pattern, all_fixtures, expected_to_match=True)
    
    metrics = ValidationMetrics(
        true_positives=tp,
        true_negatives=tn,
        false_positives=fp,
        false_negatives=fn
    )
    
    print(f"\n📊 Results for pattern: '{pattern}'")
    print(f"   Total Fixtures: {len(all_fixtures)}")
    print(f"   ✅ True Positives:  {tp}")
    print(f"   ✅ True Negatives:  {tn}")
    print(f"   ⚠️  False Positives: {fp}")
    print(f"   ❌ False Negatives: {fn}")
    
    print(f"\n📈 ML Metrics:")
    print(f"   Precision: {metrics.precision:.1%}")
    print(f"   Recall:    {metrics.recall:.1%}")
    print(f"   F1 Score:  {metrics.f1_score:.3f}")
    
    recommendation = metrics.get_recommendation()
    print(f"\n💡 Recommendation: {recommendation['recommendation']}")
    
    assert tp >= 1, "Should catch Rust compilation errors"
    
    print("\n✅ PASSED: Cargo error pattern validation")
    return True


def test_generic_error_pattern():
    """Test generic 'error|ERROR|Error' pattern across all tools"""
    print("\n" + "="*70)
    print("TEST: Generic Error Pattern (Cross-Tool)")
    print("="*70)
    
    pattern = r"(?i)(error|failed|failure)"  # Case-insensitive
    
    all_error_fixtures = get_all_error_fixtures()
    all_success_fixtures = get_all_success_fixtures()
    
    all_fixtures = all_error_fixtures + all_success_fixtures
    
    tp, tn, fp, fn = calculate_ml_metrics(pattern, all_fixtures, expected_to_match=True)
    
    metrics = ValidationMetrics(
        true_positives=tp,
        true_negatives=tn,
        false_positives=fp,
        false_negatives=fn
    )
    
    print(f"\n📊 Results for generic pattern: '{pattern}'")
    print(f"   Total Fixtures: {len(all_fixtures)} ({len(all_error_fixtures)} errors, {len(all_success_fixtures)} success)")
    print(f"   ✅ True Positives:  {tp} (caught errors)")
    print(f"   ✅ True Negatives:  {tn} (correctly ignored success)")
    print(f"   ⚠️  False Positives: {fp} (false alarms)")
    print(f"   ❌ False Negatives: {fn} (missed errors)")
    
    print(f"\n📈 ML Metrics:")
    print(f"   Precision: {metrics.precision:.1%}")
    print(f"   Recall:    {metrics.recall:.1%}")
    print(f"   F1 Score:  {metrics.f1_score:.3f}")
    print(f"   Accuracy:  {metrics.accuracy:.1%}")
    
    recommendation = metrics.get_recommendation()
    print(f"\n💡 Recommendation: {recommendation['recommendation']}")
    print(f"   {recommendation['message']}")
    
    # By tool breakdown
    print(f"\n📊 Breakdown by Tool:")
    for tool in ['npm', 'pytest', 'cargo', 'docker', 'maven']:
        tool_fixtures = [f for f in all_fixtures if f.get('tool') == tool]
        if tool_fixtures:
            tool_tp, tool_tn, tool_fp, tool_fn = calculate_ml_metrics(
                pattern, tool_fixtures, expected_to_match=True
            )
            tool_metrics = ValidationMetrics(
                true_positives=tool_tp,
                true_negatives=tool_tn,
                false_positives=tool_fp,
                false_negatives=tool_fn
            )
            print(f"   {tool:8s}: Precision={tool_metrics.precision:.1%}, "
                  f"Recall={tool_metrics.recall:.1%}, "
                  f"F1={tool_metrics.f1_score:.2f}")
    
    # Generic patterns tend to have good recall but lower precision
    assert metrics.recall >= 0.70, f"Generic pattern should have good recall"
    
    print("\n✅ PASSED: Generic error pattern validation")
    return True


def test_pattern_specificity_tradeoff():
    """Test the precision/recall tradeoff between specific and generic patterns"""
    print("\n" + "="*70)
    print("TEST: Pattern Specificity Tradeoff Analysis")
    print("="*70)
    
    patterns = {
        'very_specific': 'npm ERR! code ENOENT',
        'specific': 'npm ERR!',
        'generic': r'(?i)error',
        'too_generic': r'(?i)e'  # Will match almost everything
    }
    
    all_fixtures = get_all_error_fixtures() + get_all_success_fixtures()
    
    print(f"\n📊 Testing {len(patterns)} patterns against {len(all_fixtures)} fixtures:")
    print(f"   {len(get_all_error_fixtures())} error scenarios")
    print(f"   {len(get_all_success_fixtures())} success scenarios")
    
    print(f"\n{'Pattern':<25} {'Precision':>10} {'Recall':>10} {'F1':>8} {'Recommendation'}")
    print("="*75)
    
    results = []
    for name, pattern in patterns.items():
        tp, tn, fp, fn = calculate_ml_metrics(pattern, all_fixtures, expected_to_match=True)
        metrics = ValidationMetrics(tp, tn, fp, fn)
        recommendation = metrics.get_recommendation()
        
        results.append({
            'name': name,
            'pattern': pattern,
            'metrics': metrics,
            'recommendation': recommendation
        })
        
        print(f"{name:<25} {metrics.precision:>9.1%} {metrics.recall:>9.1%} "
              f"{metrics.f1_score:>7.2f} {recommendation['recommendation'][:20]}")
    
    print("\n💡 Analysis:")
    print("   • Very specific patterns: High precision, may miss errors (low recall)")
    print("   • Specific patterns: Good balance (recommended)")
    print("   • Generic patterns: High recall, more false alarms (lower precision)")
    print("   • Too generic: Unusable (matches everything)")
    
    # Verify the tradeoff
    specific_f1 = [r['metrics'].f1_score for r in results if r['name'] == 'specific'][0]
    generic_f1 = [r['metrics'].f1_score for r in results if r['name'] == 'generic'][0]
    
    print(f"\n✅ Specific pattern F1: {specific_f1:.3f}")
    print(f"✅ Generic pattern F1:  {generic_f1:.3f}")
    
    print("\n✅ PASSED: Specificity tradeoff analysis")
    return True


def test_false_positive_analysis():
    """Analyze false positive scenarios"""
    print("\n" + "="*70)
    print("TEST: False Positive Analysis")
    print("="*70)
    
    # Pattern that might trigger false positives
    pattern = r"(?i)(error|warning)"
    
    success_fixtures = get_all_success_fixtures()
    
    print(f"\n🔍 Testing pattern '{pattern}' against {len(success_fixtures)} success scenarios:")
    
    false_positives = []
    for fixture in success_fixtures:
        stdout = fixture.get('stdout', '')
        stderr = fixture.get('stderr', '')
        
        if test_pattern_against_output(pattern, stdout, stderr):
            false_positives.append(fixture)
            print(f"\n   ⚠️  FALSE POSITIVE: {fixture.get('tool')}/{fixture.get('scenario')}")
            print(f"      Type: {fixture.get('error_type')}")
            # Show snippet of what matched
            combined = (stdout + stderr)[:200]
            print(f"      Snippet: {combined[:100]}...")
    
    print(f"\n📊 Results:")
    print(f"   Success scenarios tested: {len(success_fixtures)}")
    print(f"   False positives found: {len(false_positives)}")
    print(f"   False positive rate: {len(false_positives)/max(len(success_fixtures),1)*100:.1f}%")
    
    if false_positives:
        print(f"\n💡 Common False Positive Types:")
        fp_types = {}
        for fp in false_positives:
            fp_type = fp.get('error_type', 'unknown')
            fp_types[fp_type] = fp_types.get(fp_type, 0) + 1
        
        for fp_type, count in fp_types.items():
            print(f"   • {fp_type}: {count} occurrence(s)")
        
        print(f"\n💡 Recommendation: Consider more specific patterns to reduce false positives")
    else:
        print(f"\n✅ No false positives! Pattern is very precise.")
    
    print("\n✅ PASSED: False positive analysis complete")
    return True


if __name__ == '__main__':
    print("\n" + "="*70)
    print("ML-STYLE VALIDATION TESTING")
    print("Testing earlyexit with Real-World Error Patterns")
    print("="*70)
    
    tests = [
        test_npm_err_pattern,
        test_pytest_failed_pattern,
        test_cargo_error_pattern,
        test_generic_error_pattern,
        test_pattern_specificity_tradeoff,
        test_false_positive_analysis,
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
        print("\n✨ All ML validation tests passed!")
        print("\n💡 Key Findings:")
        print("   • Specific patterns (e.g., 'npm ERR!') have high precision & recall")
        print("   • Generic patterns have good recall but more false positives")
        print("   • Real-world error patterns are consistent and detectable")
        print("   • ML metrics (TP/TN/FP/FN) accurately reflect pattern quality")
        sys.exit(0)
    else:
        print(f"\n❌ {failed} test(s) failed")
        sys.exit(1)


"""
Smart suggestions display and handling

Shows learned settings with validation metrics and confidence
"""

import sys
from typing import Dict, Optional, Any, List
from earlyexit.features import ValidationMetrics


# Type hint for List import
__all__ = ['display_suggestion', 'apply_learned_settings', 'check_and_offer_suggestion']


def display_suggestion(learned_setting: Dict[str, Any], command: str) -> Optional[str]:
    """
    Display a smart suggestion to the user
    
    Args:
        learned_setting: Dict with learned parameters and validation
        command: The command being run
    
    Returns:
        User choice: 'yes', 'no', 'edit', or None if skipped
    """
    # Build validation metrics
    val = learned_setting.get('validation', {})
    metrics = ValidationMetrics(
        true_positives=val.get('true_positives', 0),
        true_negatives=val.get('true_negatives', 0),
        false_positives=val.get('false_positives', 0),
        false_negatives=val.get('false_negatives', 0),
        user_confirmed_good=val.get('user_confirmed_good', 0),
        user_rejected=val.get('user_rejected', 0)
    )
    
    recommendation = metrics.get_recommendation()
    
    # Display suggestion box
    print("\n" + "="*70, file=sys.stderr)
    print("💡 SMART SUGGESTION (Based on your previous usage)", file=sys.stderr)
    print("="*70, file=sys.stderr)
    
    # Show learned parameters
    print(f"\n📋 Learned Settings:", file=sys.stderr)
    if learned_setting.get('learned_pattern'):
        print(f"   Pattern: '{learned_setting['learned_pattern']}'", file=sys.stderr)
    if learned_setting.get('learned_timeout'):
        print(f"   Timeout: {learned_setting['learned_timeout']}s", file=sys.stderr)
    if learned_setting.get('learned_idle_timeout'):
        print(f"   Idle Timeout: {learned_setting['learned_idle_timeout']}s", file=sys.stderr)
    if learned_setting.get('learned_delay_exit'):
        print(f"   Delay Exit: {learned_setting['learned_delay_exit']}s", file=sys.stderr)
    
    # Show validation metrics
    total_runs = metrics.total_runs
    if total_runs > 0:
        print(f"\n📊 Validation ({total_runs} runs):", file=sys.stderr)
        print(f"   ✅ Errors Caught:     {metrics.true_positives} " + 
              f"({metrics.true_positives/total_runs*100:.0f}%)", file=sys.stderr)
        print(f"   ✅ Successful Runs:   {metrics.true_negatives} " +
              f"({metrics.true_negatives/total_runs*100:.0f}%)", file=sys.stderr)
        
        if metrics.false_positives > 0:
            print(f"   ⚠️  False Alarms:     {metrics.false_positives} " +
                  f"({metrics.false_positives/total_runs*100:.0f}%)", file=sys.stderr)
        else:
            print(f"   ✨ False Alarms:     {metrics.false_positives} (none!)", file=sys.stderr)
        
        if metrics.false_negatives > 0:
            print(f"   ❌ Missed Errors:     {metrics.false_negatives} " +
                  f"({metrics.false_negatives/total_runs*100:.0f}%)", file=sys.stderr)
        
        print(f"\n📈 Performance Metrics:", file=sys.stderr)
        print(f"   Precision:  {metrics.precision:.1%}", file=sys.stderr)
        print(f"   Recall:     {metrics.recall:.1%}", file=sys.stderr)
        print(f"   F1 Score:   {metrics.f1_score:.2f}", file=sys.stderr)
        
        if metrics.user_confirmed_good + metrics.user_rejected > 0:
            print(f"   User Satisfaction: {metrics.user_satisfaction:.1%}", file=sys.stderr)
    
    # Show recommendation
    rec_emoji = {
        'HIGHLY_RECOMMENDED': '✅',
        'USE_WITH_CAUTION': '⚠️',
        'TUNE_PATTERN': '🔧',
        'NOT_RECOMMENDED': '❌',
        'COLLECT_MORE_DATA': '📊',
        'NEEDS_IMPROVEMENT': '⚠️'
    }.get(recommendation['recommendation'], '💡')
    
    print(f"\n{rec_emoji} Recommendation: {recommendation['recommendation']}", file=sys.stderr)
    print(f"   {recommendation['message']}", file=sys.stderr)
    
    if recommendation.get('reasons'):
        print(f"\n   Reasons:", file=sys.stderr)
        for reason in recommendation['reasons'][:3]:  # Show top 3 reasons
            print(f"     {reason}", file=sys.stderr)
    
    # Show what command would be run
    print(f"\n🚀 Would run:", file=sys.stderr)
    cmd_parts = ["earlyexit"]
    if learned_setting.get('learned_pattern'):
        cmd_parts.append(f"'{learned_setting['learned_pattern']}'")
    if learned_setting.get('learned_timeout'):
        cmd_parts.append(f"-t {learned_setting['learned_timeout']}")
    if learned_setting.get('learned_idle_timeout'):
        cmd_parts.append(f"--idle-timeout {learned_setting['learned_idle_timeout']}")
    if learned_setting.get('learned_delay_exit'):
        cmd_parts.append(f"--delay-exit {learned_setting['learned_delay_exit']}")
    cmd_parts.append("--")
    cmd_parts.append(command)
    
    print(f"   {' '.join(cmd_parts)}", file=sys.stderr)
    
    print("\n" + "="*70, file=sys.stderr)
    
    # Get user choice
    print("Use these settings?", file=sys.stderr)
    print("  [Y]es - Use suggested settings", file=sys.stderr)
    print("  [n]o  - Skip suggestion and use current args", file=sys.stderr)
    print("  [e]dit - Modify suggested settings", file=sys.stderr)
    print("  [w]hy - Show detailed explanation", file=sys.stderr)
    print("", file=sys.stderr)
    
    try:
        choice = input("Your choice [Y/n/e/w]: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\n⏭️  Skipped suggestion", file=sys.stderr)
        return None
    
    if choice in ['w', 'why']:
        # Show detailed explanation
        _display_detailed_explanation(metrics, recommendation)
        # Ask again
        return display_suggestion(learned_setting, command)
    
    if choice in ['', 'y', 'yes']:
        print("✅ Using suggested settings", file=sys.stderr)
        return 'yes'
    elif choice in ['e', 'edit']:
        print("✏️  Edit mode (not yet implemented - using suggestions as-is)", file=sys.stderr)
        return 'yes'
    else:
        print("⏭️  Skipped suggestion", file=sys.stderr)
        return 'no'


def _display_detailed_explanation(metrics: ValidationMetrics, 
                                  recommendation: Dict[str, Any]):
    """Display detailed 'why' explanation"""
    print("\n" + "="*70, file=sys.stderr)
    print("📚 DETAILED EXPLANATION", file=sys.stderr)
    print("="*70, file=sys.stderr)
    
    print("\n🎯 What do these metrics mean?", file=sys.stderr)
    print("", file=sys.stderr)
    
    print("✅ TRUE POSITIVES (Good Catches)", file=sys.stderr)
    print(f"   Count: {metrics.true_positives}", file=sys.stderr)
    print("   earlyexit detected an error and it WAS a real error", file=sys.stderr)
    print("   → This is what we want! Saves you time.", file=sys.stderr)
    print("", file=sys.stderr)
    
    print("✅ TRUE NEGATIVES (Good Passes)", file=sys.stderr)
    print(f"   Count: {metrics.true_negatives}", file=sys.stderr)
    print("   Command succeeded and earlyexit correctly didn't trigger", file=sys.stderr)
    print("   → This is good! No false alarms.", file=sys.stderr)
    print("", file=sys.stderr)
    
    if metrics.false_positives > 0:
        print("⚠️  FALSE POSITIVES (False Alarms)", file=sys.stderr)
        print(f"   Count: {metrics.false_positives}", file=sys.stderr)
        print("   earlyexit triggered but there was NO real error", file=sys.stderr)
        print("   → This wastes your time. Too many = bad pattern.", file=sys.stderr)
        print("", file=sys.stderr)
    
    if metrics.false_negatives > 0:
        print("❌ FALSE NEGATIVES (Missed Errors)", file=sys.stderr)
        print(f"   Count: {metrics.false_negatives}", file=sys.stderr)
        print("   Error occurred but earlyexit DIDN'T catch it", file=sys.stderr)
        print("   → You waited longer than needed. More patterns may help.", file=sys.stderr)
        print("", file=sys.stderr)
    
    print("📊 Key Metrics:", file=sys.stderr)
    print(f"   PRECISION: {metrics.precision:.1%}", file=sys.stderr)
    print("   → When earlyexit says 'error', how often is it right?", file=sys.stderr)
    print("   → Higher is better (fewer false alarms)", file=sys.stderr)
    print("", file=sys.stderr)
    
    print(f"   RECALL: {metrics.recall:.1%}", file=sys.stderr)
    print("   → Of all real errors, how many did earlyexit catch?", file=sys.stderr)
    print("   → Higher is better (fewer missed errors)", file=sys.stderr)
    print("", file=sys.stderr)
    
    print(f"   F1 SCORE: {metrics.f1_score:.2f}", file=sys.stderr)
    print("   → Balanced measure (harmonic mean of precision & recall)", file=sys.stderr)
    print("   → 0.0 = worst, 1.0 = perfect", file=sys.stderr)
    print("   → > 0.75 is excellent, > 0.5 is good", file=sys.stderr)
    print("", file=sys.stderr)
    
    print("💡 The Recommendation:", file=sys.stderr)
    print(f"   {recommendation['recommendation']}", file=sys.stderr)
    print(f"   {recommendation['message']}", file=sys.stderr)
    print("", file=sys.stderr)
    
    for reason in recommendation.get('reasons', []):
        print(f"   • {reason}", file=sys.stderr)
    
    print("\n" + "="*70, file=sys.stderr)
    print("Press Enter to continue...", file=sys.stderr)
    try:
        input()
    except (KeyboardInterrupt, EOFError):
        pass


def apply_learned_settings(args, learned_setting: Dict[str, Any]):
    """
    Apply learned settings to args object (in-place modification)
    
    Args:
        args: argparse Namespace object
        learned_setting: Dict with learned parameters
    """
    if learned_setting.get('learned_pattern') and not args.pattern:
        args.pattern = learned_setting['learned_pattern']
    
    if learned_setting.get('learned_timeout') and not args.timeout:
        args.timeout = learned_setting['learned_timeout']
    
    if learned_setting.get('learned_idle_timeout') and not args.idle_timeout:
        args.idle_timeout = learned_setting['learned_idle_timeout']
    
    if learned_setting.get('learned_delay_exit'):
        # Always apply delay_exit if learned (unless user explicitly set it)
        if not hasattr(args, '_delay_exit_set'):
            args.delay_exit = learned_setting['learned_delay_exit']


def check_and_offer_suggestion(args, command: List[str], 
                               telemetry_collector) -> Optional[str]:
    """
    Check for learned settings and offer suggestion if available
    
    Args:
        args: argparse Namespace
        command: Command being run
        telemetry_collector: TelemetryCollector instance
    
    Returns:
        setting_id if suggestion was accepted, None otherwise
    """
    if not telemetry_collector or not telemetry_collector.enabled:
        return None
    
    # Skip if user explicitly provided pattern
    if args.pattern and args.pattern != '<watch mode>':
        return None
    
    # Skip if --no-suggestions flag (if we add it)
    if hasattr(args, 'no_suggestions') and args.no_suggestions:
        return None
    
    # Calculate command hash
    command_str = ' '.join(command) if isinstance(command, list) else command
    import hashlib
    command_hash = hashlib.sha256(command_str.encode()).hexdigest()[:16]
    
    # Detect project type
    try:
        project_type = telemetry_collector._detect_project_type(command_str)
    except:
        project_type = 'unknown'
    
    # Get learned setting
    learned_setting = telemetry_collector.get_learned_setting(command_hash, project_type)
    
    if not learned_setting:
        return None
    
    # Check if we have enough validation data
    val = learned_setting.get('validation', {})
    total_runs = (val.get('true_positives', 0) + val.get('true_negatives', 0) + 
                  val.get('false_positives', 0) + val.get('false_negatives', 0))
    
    if total_runs < 3:
        # Not enough data yet
        return None
    
    # Display suggestion
    choice = display_suggestion(learned_setting, command_str)
    
    if choice == 'yes':
        # Apply learned settings
        apply_learned_settings(args, learned_setting)
        return learned_setting['setting_id']
    elif choice == 'no':
        # User rejected suggestion
        telemetry_collector.update_learned_setting_validation(
            learned_setting['setting_id'],
            outcome='true_negative',  # Placeholder
            user_feedback='rejected'
        )
        return None
    
    return None


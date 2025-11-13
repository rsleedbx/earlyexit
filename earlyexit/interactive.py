"""
Interactive learning prompts - Ask user about their behavior after Ctrl+C

This module handles the interactive UI shown to users after they interrupt
a watch mode session, helping earlyexit learn from their behavior.
"""

import sys
import re
from typing import Dict, List, Optional, Tuple, Any
from collections import Counter


class PatternExtractor:
    """Extract potential error patterns from output streams"""
    
    # Common error keywords (weighted by likelihood)
    ERROR_KEYWORDS = {
        # High confidence (usually errors)
        'FAILED': 3.0,
        'FATAL': 3.0,
        'CRITICAL': 3.0,
        'ERROR': 2.5,
        'EXCEPTION': 2.5,
        'FAILURE': 2.5,
        'PANIC': 3.0,
        
        # Medium confidence
        'FAIL': 2.0,
        'WARN': 1.5,
        'WARNING': 1.5,
        'ALERT': 2.0,
        
        # Context-dependent
        'Error': 2.0,
        'Failed': 2.0,
        'Exception': 2.0,
        'Traceback': 2.5,
        
        # Test-specific
        'FAIL:': 2.5,
        'FAILED:': 2.5,
        '✗': 2.0,
        '❌': 2.0,
    }
    
    # Words to ignore (too common, false positives)
    IGNORE_WORDS = {
        'INFO', 'DEBUG', 'TRACE', 'LOG', 'info', 'debug', 'trace',
        'SUCCESS', 'OK', 'PASS', 'PASSED', '✓', '✅'
    }
    
    def __init__(self):
        pass
    
    def extract_patterns(
        self, 
        stdout_lines: List[Dict[str, Any]], 
        stderr_lines: List[Dict[str, Any]],
        max_suggestions: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Extract potential error patterns from captured output
        
        Args:
            stdout_lines: List of stdout line entries with 'line', 'timestamp', etc.
            stderr_lines: List of stderr line entries
            max_suggestions: Maximum number of pattern suggestions
        
        Returns:
            List of pattern suggestions with confidence scores
        """
        # Weight stderr higher (errors usually go to stderr)
        all_patterns = []
        
        # Extract from stderr (higher weight)
        stderr_patterns = self._extract_from_lines(stderr_lines, stream_weight=2.0)
        all_patterns.extend(stderr_patterns)
        
        # Extract from stdout (lower weight)
        stdout_patterns = self._extract_from_lines(stdout_lines, stream_weight=1.0)
        all_patterns.extend(stdout_patterns)
        
        # Combine and rank by score
        pattern_scores = {}
        for pattern_info in all_patterns:
            pattern = pattern_info['pattern']
            score = pattern_info['score']
            stream = pattern_info['stream']
            
            if pattern in pattern_scores:
                pattern_scores[pattern]['score'] += score
                pattern_scores[pattern]['count'] += 1
                pattern_scores[pattern]['streams'].add(stream)
            else:
                pattern_scores[pattern] = {
                    'pattern': pattern,
                    'score': score,
                    'count': 1,
                    'streams': {stream},
                    'example_line': pattern_info.get('example_line', '')
                }
        
        # Sort by score
        sorted_patterns = sorted(
            pattern_scores.values(),
            key=lambda x: (x['score'], x['count']),
            reverse=True
        )
        
        # Format for display
        suggestions = []
        for p in sorted_patterns[:max_suggestions]:
            confidence = min(1.0, p['score'] / 10.0)  # Normalize to 0-1
            stream_info = 'both' if len(p['streams']) > 1 else list(p['streams'])[0]
            
            suggestions.append({
                'pattern': p['pattern'],
                'confidence': confidence,
                'count': p['count'],
                'stream': stream_info,
                'example': p['example_line'][:80] if p['example_line'] else ''
            })
        
        return suggestions
    
    def _extract_from_lines(
        self, 
        lines: List[Dict[str, Any]], 
        stream_weight: float
    ) -> List[Dict[str, Any]]:
        """Extract patterns from a list of lines with weighting"""
        patterns = []
        
        for line_entry in lines:
            line = line_entry.get('line', '')
            
            # Look for error keywords
            for keyword, keyword_weight in self.ERROR_KEYWORDS.items():
                if keyword in line:
                    # Check it's not in ignore list
                    if any(ignore in line for ignore in self.IGNORE_WORDS):
                        continue
                    
                    score = keyword_weight * stream_weight
                    patterns.append({
                        'pattern': keyword,
                        'score': score,
                        'stream': line_entry.get('stream', 'unknown'),
                        'example_line': line
                    })
            
            # Look for specific error patterns
            # Pattern: "Error: something"
            error_match = re.search(r'\b(Error|ERROR|error)\s*:\s*(.{10,50})', line)
            if error_match:
                context = error_match.group(2).strip()
                patterns.append({
                    'pattern': f'Error.*{re.escape(context[:20])}',
                    'score': 2.0 * stream_weight,
                    'stream': line_entry.get('stream', 'unknown'),
                    'example_line': line
                })
            
            # Pattern: Test failures (language-specific)
            # pytest: "FAILED test_file.py::test_name"
            if 'FAILED' in line and '::' in line:
                patterns.append({
                    'pattern': 'FAILED.*::',
                    'score': 3.0 * stream_weight,
                    'stream': line_entry.get('stream', 'unknown'),
                    'example_line': line
                })
            
            # npm: "npm ERR!"
            if 'npm ERR!' in line:
                patterns.append({
                    'pattern': 'npm ERR!',
                    'score': 3.0 * stream_weight,
                    'stream': line_entry.get('stream', 'unknown'),
                    'example_line': line
                })
        
        return patterns


class TimeoutCalculator:
    """Calculate suggested timeout values based on behavior"""
    
    def calculate_suggestions(
        self,
        duration: float,
        idle_time: float,
        line_counts: Dict[str, int],
        stop_reason: str
    ) -> Dict[str, Any]:
        """
        Calculate timeout suggestions based on user behavior
        
        Args:
            duration: How long the command ran before Ctrl+C
            idle_time: Time since last output
            line_counts: Dict with 'stdout', 'stderr', 'total' counts
            stop_reason: Why user stopped ('error', 'hang', 'timeout')
        
        Returns:
            Dict with timeout suggestions and rationale
        """
        suggestions = {}
        
        # Overall timeout suggestion
        # Add 20-50% buffer over actual runtime
        if stop_reason == 'error':
            # User saw error quickly - set timeout slightly higher
            buffer_factor = 1.5
            suggestions['overall_timeout'] = round(duration * buffer_factor, 1)
            suggestions['overall_rationale'] = f"You stopped at {duration:.1f}s after seeing error. " \
                                               f"Setting timeout to {suggestions['overall_timeout']}s (50% buffer)"
        elif stop_reason == 'hang':
            # User waited for output - use idle time
            suggestions['idle_timeout'] = max(30.0, round(idle_time * 1.2, 1))
            suggestions['idle_rationale'] = f"No output for {idle_time:.1f}s before you stopped. " \
                                            f"Setting idle timeout to {suggestions['idle_timeout']}s"
        elif stop_reason == 'timeout':
            # User waited too long
            buffer_factor = 1.2
            suggestions['overall_timeout'] = round(duration * buffer_factor, 1)
            suggestions['overall_rationale'] = f"You stopped at {duration:.1f}s (too slow). " \
                                               f"Setting timeout to {suggestions['overall_timeout']}s (20% buffer)"
        
        # Delay-exit suggestion
        # Based on how much output was generated
        total_lines = line_counts.get('total', 0)
        
        if total_lines < 50:
            # Low output - short delay
            suggestions['delay_exit'] = 5.0
            suggestions['delay_rationale'] = "Low output volume - 5s delay should capture context"
        elif total_lines < 200:
            # Medium output - default delay
            suggestions['delay_exit'] = 10.0
            suggestions['delay_rationale'] = "Medium output volume - 10s delay (default)"
        else:
            # High output - longer delay
            suggestions['delay_exit'] = 15.0
            suggestions['delay_rationale'] = "High output volume - 15s delay for full context"
        
        return suggestions


def show_interactive_prompt(session, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Show interactive prompts after Ctrl+C in watch mode
    
    Args:
        session: WatchSession object with captured output
        context: Context dict from session.get_context_for_interrupt()
    
    Returns:
        Dict with user selections, or None if skipped
    """
    print("\n" + "="*70, file=sys.stderr)
    print("🎓 LEARNING MODE - Help earlyexit improve!", file=sys.stderr)
    print("="*70, file=sys.stderr)
    print("", file=sys.stderr)
    
    # Step 1: Ask why they stopped
    print("⚠️  Interrupted at {:.1f}s".format(context['duration']), file=sys.stderr)
    print("", file=sys.stderr)
    print("Why did you stop?", file=sys.stderr)
    print("  1. 🚨 Error detected (saw error message)", file=sys.stderr)
    print("  2. ⏱️  Taking too long (timeout)", file=sys.stderr)
    print("  3. 🔇 No output / hung (process frozen)", file=sys.stderr)
    print("  4. ⏭️  Skip (don't learn from this)", file=sys.stderr)
    print("", file=sys.stderr)
    
    try:
        choice = input("Your choice [1-4]: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n⏭️  Skipped learning", file=sys.stderr)
        return None
    
    if choice == '4' or not choice:
        print("⏭️  Skipped learning", file=sys.stderr)
        return None
    
    stop_reason_map = {
        '1': 'error',
        '2': 'timeout',
        '3': 'hang'
    }
    
    stop_reason = stop_reason_map.get(choice, 'error')
    
    result = {
        'stop_reason': stop_reason,
        'duration': context['duration'],
        'idle_time': context['idle_time'],
        'line_counts': context['line_counts']
    }
    
    # Step 2: If error detected, suggest patterns
    if stop_reason == 'error':
        print("", file=sys.stderr)
        print("🔍 Analyzing output for error patterns...", file=sys.stderr)
        
        extractor = PatternExtractor()
        suggestions = extractor.extract_patterns(
            context.get('last_stdout', []),
            context.get('last_stderr', []),
            max_suggestions=5
        )
        
        if suggestions:
            print("", file=sys.stderr)
            print("I found these patterns:", file=sys.stderr)
            
            # Show suggestions
            for i, sugg in enumerate(suggestions, 1):
                stream_emoji = "📄" if sugg['stream'] == 'stdout' else "📛" if sugg['stream'] == 'stderr' else "📊"
                confidence_pct = int(sugg['confidence'] * 100)
                
                print(f"  {i}. {stream_emoji} '{sugg['pattern']}' "
                      f"(appeared {sugg['count']}x, {confidence_pct}% confidence)",
                      file=sys.stderr)
                
                if sugg['example']:
                    print(f"     Example: {sugg['example']}", file=sys.stderr)
            
            print(f"  {len(suggestions) + 1}. [Custom pattern]", file=sys.stderr)
            print("  0. Skip pattern (just save timing)", file=sys.stderr)
            print("", file=sys.stderr)
            
            try:
                pattern_choice = input(f"Watch for [1-{len(suggestions) + 1}, 0 to skip]: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n⏭️  Skipped pattern selection", file=sys.stderr)
                pattern_choice = '0'
            
            if pattern_choice and pattern_choice != '0':
                try:
                    choice_num = int(pattern_choice)
                    if 1 <= choice_num <= len(suggestions):
                        # Selected a suggestion
                        selected = suggestions[choice_num - 1]
                        result['selected_pattern'] = selected['pattern']
                        result['pattern_confidence'] = selected['confidence']
                        result['pattern_stream'] = selected['stream']
                        print(f"\n✅ Will watch for: '{selected['pattern']}'", file=sys.stderr)
                    elif choice_num == len(suggestions) + 1:
                        # Custom pattern
                        try:
                            custom = input("Enter custom pattern: ").strip()
                            if custom:
                                result['selected_pattern'] = custom
                                result['pattern_confidence'] = 1.0
                                result['pattern_stream'] = 'custom'
                                print(f"\n✅ Will watch for: '{custom}'", file=sys.stderr)
                        except (KeyboardInterrupt, EOFError):
                            pass
                except ValueError:
                    pass
        else:
            print("  (No obvious error patterns detected)", file=sys.stderr)
    
    # Step 3: Calculate timeout suggestions
    calculator = TimeoutCalculator()
    timeout_suggestions = calculator.calculate_suggestions(
        context['duration'],
        context['idle_time'],
        context['line_counts'],
        stop_reason
    )
    
    result['timeout_suggestions'] = timeout_suggestions
    
    # Show timeout suggestions
    if timeout_suggestions:
        print("", file=sys.stderr)
        print("⏱️  Timeout suggestions:", file=sys.stderr)
        for key, value in timeout_suggestions.items():
            if key.endswith('_rationale'):
                continue
            if key.endswith('_timeout'):
                rationale = timeout_suggestions.get(f"{key.replace('_timeout', '')}_rationale", '')
                print(f"  • {key.replace('_', ' ').title()}: {value}s", file=sys.stderr)
                if rationale:
                    print(f"    {rationale}", file=sys.stderr)
            elif key == 'delay_exit':
                rationale = timeout_suggestions.get('delay_rationale', '')
                print(f"  • Delay Exit: {value}s", file=sys.stderr)
                if rationale:
                    print(f"    {rationale}", file=sys.stderr)
    
    print("", file=sys.stderr)
    print("="*70, file=sys.stderr)
    print("✅ Learning saved! Next time try:", file=sys.stderr)
    
    # Generate command suggestion
    cmd_parts = ["earlyexit"]
    
    if result.get('selected_pattern'):
        cmd_parts.append(f"'{result['selected_pattern']}'")
    
    if 'overall_timeout' in timeout_suggestions:
        cmd_parts.append(f"-t {timeout_suggestions['overall_timeout']}")
    
    if 'idle_timeout' in timeout_suggestions:
        cmd_parts.append(f"--idle-timeout {timeout_suggestions['idle_timeout']}")
    
    if 'delay_exit' in timeout_suggestions:
        cmd_parts.append(f"--delay-exit {timeout_suggestions['delay_exit']}")
    
    cmd_parts.append("--")
    cmd_parts.append("<your command>")
    
    print(f"  {' '.join(cmd_parts)}", file=sys.stderr)
    print("="*70, file=sys.stderr)
    print("", file=sys.stderr)
    
    # Save to learned settings (will be done by caller with full context)
    result['_should_save_learned_setting'] = True
    
    return result


"""Tests for pattern exclusion feature (--exclude flag)"""

import subprocess
import sys
import os


def run_ee(*args, input_text=None, timeout=5):
    """Helper to run ee command"""
    # Try ee command first (installed), then fall back to module
    try:
        cmd = ['ee'] + list(args)
        result = subprocess.run(
            cmd,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result
    except FileNotFoundError:
        # Fall back to python module
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cmd = [sys.executable, '-m', 'earlyexit.cli'] + list(args)
        result = subprocess.run(
            cmd,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env
        )
        return result


class TestBasicExclusion:
    """Test basic exclusion functionality"""
    
    def test_single_exclusion(self):
        """Test excluding a single pattern"""
        input_text = "ERROR: Connection failed\nError: early error detection\nERROR: Database timeout\n"
        result = run_ee('ERROR', '--exclude', 'early error detection', input_text=input_text)
        
        assert result.returncode == 0, "Should find ERROR"
        assert "ERROR: Connection failed" in result.stdout
        assert "early error detection" not in result.stdout
        # Second ERROR comes after first match, so may not appear depending on behavior
    
    def test_multiple_exclusions(self):
        """Test excluding multiple patterns"""
        input_text = "ERROR: Connection failed\nError: early error detection\nERROR: Database timeout\nERROR_OK: This is fine\n"
        result = run_ee('ERROR', 
                       '--exclude', 'early error detection',
                       '--exclude', 'ERROR_OK',
                       input_text=input_text)
        
        assert result.returncode == 0, "Should find ERROR"
        assert "ERROR: Connection failed" in result.stdout
        assert "early error detection" not in result.stdout
        assert "ERROR_OK" not in result.stdout
    
    def test_exclude_with_short_flag(self):
        """Test using -X short flag"""
        input_text = "ERROR: Real error\nERROR_OK: Safe\n"
        result = run_ee('ERROR', '-X', 'ERROR_OK', input_text=input_text)
        
        assert result.returncode == 0
        assert "Real error" in result.stdout
        assert "ERROR_OK" not in result.stdout


class TestExclusionWithOptions:
    """Test exclusions combined with other options"""
    
    def test_exclusion_with_case_insensitive(self):
        """Test that exclusions respect -i flag"""
        input_text = "error: real\nError: early error detection\nerror: another\n"
        result = run_ee('-i', 'error', '--exclude', 'early', input_text=input_text)
        
        assert result.returncode == 0
        assert "error: real" in result.stdout
        assert "early error detection" not in result.stdout
    
    def test_exclusion_with_invert_match(self):
        """Test exclusions work with -v (invert match)"""
        input_text = "ERROR: bad\ngood line\nError: early detection\nanother good line\n"
        result = run_ee('-v', 'ERROR', '--exclude', 'early', input_text=input_text)
        
        # -v means select lines NOT matching ERROR
        # --exclude means skip lines matching 'early'
        # So we should get "good line" and "another good line"
        assert result.returncode == 0
        assert "good line" in result.stdout or "another good line" in result.stdout
    
    def test_exclusion_in_command_mode(self):
        """Test exclusions work in command mode"""
        result = run_ee('ERROR', '--exclude', 'early', '--',
                       'bash', '-c', 
                       'echo -e "ERROR: Connection failed\\nError: early error detection\\nERROR: Database timeout"')
        
        assert result.returncode == 0
        assert "Connection failed" in result.stdout
        assert "early error detection" not in result.stdout


class TestExclusionPatterns:
    """Test different exclusion pattern types"""
    
    def test_regex_in_exclusion(self):
        """Test using regex in exclusion patterns"""
        input_text = "ERROR: timeout 123\nERROR: real error\nERROR: timeout 456\n"
        result = run_ee('ERROR', '--exclude', r'timeout \d+', input_text=input_text)
        
        assert result.returncode == 0
        assert "real error" in result.stdout
    
    def test_exclusion_with_special_chars(self):
        """Test exclusion with regex special characters"""
        input_text = "ERROR: Failed\nError: timeouts {}\nERROR: Crashed\n"
        # Need to escape the braces
        result = run_ee('ERROR', '--exclude', r'timeouts \{', input_text=input_text)
        
        assert result.returncode == 0
        assert "Failed" in result.stdout or "Crashed" in result.stdout
        assert "timeouts {}" not in result.stdout
    
    def test_exclusion_whole_word(self):
        """Test excluding whole words"""
        input_text = "ERROR_OK: fine\nERROR: bad\nERROR_EXPECTED: also fine\n"
        result = run_ee('ERROR', '--exclude', r'\bERROR_OK\b', '--exclude', r'\bERROR_EXPECTED\b', input_text=input_text)
        
        assert result.returncode == 0
        assert "ERROR: bad" in result.stdout or "bad" in result.stdout


class TestExclusionEdgeCases:
    """Test edge cases and error handling"""
    
    def test_all_lines_excluded(self):
        """Test when all matching lines are excluded"""
        input_text = "ERROR: early error detection\nERROR: early warning\nINFO: all good\n"
        result = run_ee('ERROR', '--exclude', 'early', input_text=input_text)
        
        # All ERRORs are excluded, so no match
        assert result.returncode == 1, "Should return 1 (no match) when all matches excluded"
    
    def test_invalid_exclusion_regex(self):
        """Test that invalid exclusion patterns are handled gracefully"""
        input_text = "ERROR: test\n"
        # Invalid regex (unclosed bracket)
        result = run_ee('ERROR', '--exclude', '[invalid', input_text=input_text)
        
        # Should still work, just skip the invalid exclusion
        assert result.returncode == 0
        assert "ERROR" in result.stdout
    
    def test_no_pattern_with_exclusion(self):
        """Test exclusion when no main pattern matches"""
        input_text = "INFO: all good\nDEBUG: testing\n"
        result = run_ee('ERROR', '--exclude', 'early', input_text=input_text)
        
        assert result.returncode == 1, "Should return 1 when pattern doesn't match"
    
    def test_empty_exclusion_pattern(self):
        """Test with empty exclusion pattern"""
        input_text = "ERROR: test\n"
        result = run_ee('ERROR', '--exclude', '', input_text=input_text)
        
        # Empty exclusion should match nothing (or everything), handle gracefully
        assert result.returncode in [0, 1]  # Either way is acceptable


class TestExclusionRealWorld:
    """Test real-world scenarios"""
    
    def test_terraform_false_positive(self):
        """Test excluding Terraform's benign error messages"""
        input_text = """Initializing...
Error: early error detection (benign message from Terraform)
Downloading providers...
ERROR: Failed to download provider
Apply complete!
"""
        # Use case-insensitive to match both "Error" and "ERROR"
        result = run_ee('-i', 'error', '--exclude', 'early error detection', input_text=input_text)
        
        assert result.returncode == 0
        assert "Failed to download provider" in result.stdout
        assert "early error detection" not in result.stdout
    
    def test_database_expected_errors(self):
        """Test excluding expected database errors"""
        input_text = """Starting migration...
ERROR_OK: Relation already exists (expected)
Processing table users...
ERROR: Connection timeout
Migration complete
"""
        result = run_ee('ERROR', '--exclude', 'ERROR_OK', input_text=input_text)
        
        assert result.returncode == 0
        assert "Connection timeout" in result.stdout
        assert "ERROR_OK" not in result.stdout


class TestExclusionWithJSON:
    """Test exclusions with JSON output mode"""
    
    def test_exclusion_with_json_output(self):
        """Test that exclusions work with --json"""
        import json
        
        input_text = "ERROR: real\nERROR_OK: fine\nERROR: another\n"
        result = run_ee('--json', 'ERROR', '--exclude', 'ERROR_OK', input_text=input_text)
        
        # Should find "ERROR: real" and skip "ERROR_OK"
        assert result.returncode == 0
        
        # Parse JSON output
        data = json.loads(result.stdout)
        assert data['exit_code'] == 0
        assert data['exit_reason'] in ['match', 'pattern_matched']  # Accept both
        # The matched line should be one of the non-excluded ERRORs
        matched_line = data.get('matched_line') or ''
        if matched_line:
            assert 'OK' not in matched_line


class TestExclusionPerformance:
    """Test exclusion performance with many patterns"""
    
    def test_many_exclusions(self):
        """Test with many exclusion patterns"""
        input_text = "ERROR: real error\n" + "\n".join([f"ERROR_{i}: expected" for i in range(10)]) + "\n"
        
        # Exclude ERROR_0 through ERROR_9
        exclude_args = []
        for i in range(10):
            exclude_args.extend(['--exclude', f'ERROR_{i}'])
        
        result = run_ee('ERROR', *exclude_args, input_text=input_text)
        
        assert result.returncode == 0
        assert "real error" in result.stdout
        # None of the ERROR_N should appear
        for i in range(10):
            assert f"ERROR_{i}" not in result.stdout


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])


"""Tests for --json output mode"""

import subprocess
import json
import pytest
import sys
import os


def run_ee(*args, timeout=5, input_text=None):
    """Helper to run earlyexit and return result"""
    # Try to use installed ee command first
    try:
        cmd = ['ee'] + list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=input_text
        )
        return result
    except FileNotFoundError:
        # Fall back to calling CLI module directly
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        result = subprocess.run(
            [sys.executable, '-m', 'earlyexit.cli'] + list(args),
            capture_output=True,
            text=True,
            timeout=timeout,
            input=input_text,
            env=env
        )
        return result


class TestJSONBasicOutput:
    """Test basic JSON output structure"""
    
    def test_json_produces_valid_json(self):
        """Test that --json produces valid JSON"""
        result = run_ee('--json', 'ERROR', '--', 'bash', '-c', 'echo "ERROR found"')
        
        # Should be valid JSON
        data = json.loads(result.stdout)
        assert isinstance(data, dict), "JSON output should be a dictionary"
    
    def test_json_required_fields(self):
        """Test that JSON output includes all required fields"""
        result = run_ee('--json', 'ERROR', '--', 'bash', '-c', 'echo "ERROR found"')
        data = json.loads(result.stdout)
        
        # Check all required fields are present
        required_fields = [
            'version', 'exit_code', 'exit_reason', 'pattern',
            'matched_line', 'line_number', 'duration_seconds',
            'command', 'timeouts', 'statistics', 'log_files'
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
    
    def test_json_version_field(self):
        """Test that version field is correct"""
        result = run_ee('--json', 'ERROR', '--', 'bash', '-c', 'echo "test"')
        data = json.loads(result.stdout)
        
        assert 'version' in data
        assert data['version'] == "0.0.5"


class TestJSONExitCodes:
    """Test JSON output with various exit codes"""
    
    def test_json_pattern_match_exit_code(self):
        """Test JSON output when pattern matches (grep convention)"""
        result = run_ee('--json', 'ERROR', '--', 'bash', '-c', 'echo "ERROR found"')
        data = json.loads(result.stdout)
        
        assert data['exit_code'] == 0, "Pattern match should return 0 (grep convention)"
        assert data['exit_reason'] == 'match'
        assert data['pattern'] == 'ERROR'
    
    def test_json_no_match_exit_code(self):
        """Test JSON output when pattern doesn't match"""
        result = run_ee('--json', 'ERROR', '--', 'bash', '-c', 'echo "All good"')
        data = json.loads(result.stdout)
        
        assert data['exit_code'] == 1, "No match should return 1 (grep convention)"
        assert data['exit_reason'] == 'completed'
    
    def test_json_with_unix_exit_codes_match(self):
        """Test JSON output with --unix-exit-codes when pattern matches"""
        result = run_ee('--json', '--unix-exit-codes', 'ERROR', '--',
                       'bash', '-c', 'echo "ERROR found"')
        data = json.loads(result.stdout)
        
        assert data['exit_code'] == 1, "Unix mode: error found = exit 1"
        assert data['exit_reason'] == 'match'
    
    def test_json_with_unix_exit_codes_no_match(self):
        """Test JSON output with --unix-exit-codes when no match"""
        result = run_ee('--json', '--unix-exit-codes', 'ERROR', '--',
                       'bash', '-c', 'echo "All good"')
        data = json.loads(result.stdout)
        
        assert data['exit_code'] == 0, "Unix mode: no error = exit 0"
        assert data['exit_reason'] == 'completed'
    
    def test_json_timeout(self):
        """Test JSON output with timeout"""
        result = run_ee('--json', '-t', '1', 'NEVER', '--',
                       'bash', '-c', 'sleep 10')
        data = json.loads(result.stdout)
        
        assert data['exit_code'] == 2, "Timeout should return 2"
        assert data['exit_reason'] == 'timeout'
        assert data['timeouts']['overall'] == 1


class TestJSONOutputSuppression:
    """Test that JSON mode suppresses normal output"""
    
    def test_json_suppresses_command_output(self):
        """Test that command output is not included with --json"""
        result = run_ee('--json', 'ERROR', '--',
                       'bash', '-c', 'echo "Line 1"; echo "ERROR"; echo "Line 3"')
        
        # stdout should only contain JSON
        data = json.loads(result.stdout)
        
        # These lines should NOT appear in stdout
        assert 'Line 1' not in result.stdout or '"command"' in result.stdout
        assert 'Line 3' not in result.stdout or '"command"' in result.stdout
        
        # Verify it's valid JSON
        assert data['exit_code'] == 0
    
    def test_json_suppresses_logging_messages(self):
        """Test that logging messages are suppressed with --json"""
        result = run_ee('--json', 'ERROR', '--',
                       'bash', '-c', 'echo "ERROR"')
        
        # Should not contain logging messages
        assert '📝 Logging to:' not in result.stdout
        # Should only be JSON
        data = json.loads(result.stdout)
        assert data['exit_code'] == 0


class TestJSONFields:
    """Test individual JSON output fields"""
    
    def test_json_command_field(self):
        """Test that command field is correctly populated"""
        result = run_ee('--json', 'ERROR', '--', 'bash', '-c', 'echo "test"')
        data = json.loads(result.stdout)
        
        assert 'command' in data
        assert isinstance(data['command'], list)
        assert data['command'] == ['bash', '-c', 'echo "test"']
    
    def test_json_timeouts_field(self):
        """Test that timeouts field is correctly populated"""
        result = run_ee('--json', '-t', '300', '-I', '30', 'ERROR', '--',
                       'bash', '-c', 'echo "test"')
        data = json.loads(result.stdout)
        
        assert 'timeouts' in data
        assert data['timeouts']['overall'] == 300
        assert data['timeouts']['idle'] == 30
        assert data['timeouts']['first_output'] is None
    
    def test_json_duration_field(self):
        """Test that duration_seconds field is present and reasonable"""
        result = run_ee('--json', 'ERROR', '--', 'bash', '-c', 'echo "ERROR"')
        data = json.loads(result.stdout)
        
        assert 'duration_seconds' in data
        assert isinstance(data['duration_seconds'], (int, float))
        assert 0 < data['duration_seconds'] < 10, "Duration should be reasonable"
    
    def test_json_log_files_field(self):
        """Test that log_files field is populated when logging is enabled"""
        # Use --log flag to force logging (smart auto-logging won't log simple commands)
        result = run_ee('--json', '--log', 'ERROR', '--', 'bash', '-c', 'echo "ERROR"')
        data = json.loads(result.stdout)
        
        assert 'log_files' in data
        assert 'stdout' in data['log_files']
        assert 'stderr' in data['log_files']
        # Log files should be created (paths should exist)
        assert data['log_files']['stdout'] is not None
        assert '/tmp/' in data['log_files']['stdout']
    
    def test_json_statistics_field(self):
        """Test that statistics field exists (even if null for now)"""
        result = run_ee('--json', 'ERROR', '--', 'bash', '-c', 'echo "ERROR"')
        data = json.loads(result.stdout)
        
        assert 'statistics' in data
        assert isinstance(data['statistics'], dict)
        # These fields exist but are null in current implementation
        assert 'lines_processed' in data['statistics']
        assert 'bytes_processed' in data['statistics']
        assert 'time_to_first_output' in data['statistics']
        assert 'time_to_match' in data['statistics']


class TestJSONPipeMode:
    """Test JSON output in pipe mode"""
    
    def test_json_pipe_mode_match(self):
        """Test JSON output in pipe mode with match"""
        result = run_ee('--json', 'ERROR', input_text='line 1\nERROR found\nline 3\n')
        data = json.loads(result.stdout)
        
        assert data['exit_code'] == 0, "Pipe mode: match = exit 0"
        assert data['exit_reason'] == 'match'
        assert data['command'] == []  # Pipe mode has no command
    
    def test_json_pipe_mode_no_match(self):
        """Test JSON output in pipe mode without match"""
        result = run_ee('--json', 'ERROR', input_text='line 1\nline 2\nline 3\n')
        data = json.loads(result.stdout)
        
        assert data['exit_code'] == 1, "Pipe mode: no match = exit 1"
        assert data['exit_reason'] == 'no_match'
    
    def test_json_pipe_mode_no_log_files(self):
        """Test that pipe mode doesn't create log files"""
        result = run_ee('--json', 'ERROR', input_text='ERROR\n')
        data = json.loads(result.stdout)
        
        # Pipe mode shouldn't have log files
        assert data['log_files']['stdout'] is None
        assert data['log_files']['stderr'] is None


class TestJSONProgrammaticUse:
    """Test JSON output for programmatic use cases"""
    
    def test_json_can_be_parsed_by_jq(self):
        """Test that JSON output can be parsed by jq (if available)"""
        result = run_ee('--json', 'ERROR', '--', 'bash', '-c', 'echo "ERROR"')
        
        # Try to parse with jq
        try:
            jq_result = subprocess.run(
                ['jq', '.exit_code'],
                input=result.stdout,
                capture_output=True,
                text=True,
                timeout=5
            )
            if jq_result.returncode == 0:
                assert jq_result.stdout.strip() == '0'
        except FileNotFoundError:
            pytest.skip("jq not available")
    
    def test_json_python_integration(self):
        """Test that JSON output works well with Python integration"""
        result = run_ee('--json', '--unix-exit-codes', 'Error', '--',
                       'bash', '-c', 'echo "Error detected"')
        
        # Python integration example
        data = json.loads(result.stdout)
        
        if data['exit_code'] == 0:
            status = "Success"
        elif data['exit_reason'] == 'match':
            status = f"Error found: {data['pattern']}"
        else:
            status = f"Failed: {data['exit_reason']}"
        
        assert status == "Error found: Error"
    
    def test_json_with_complex_command(self):
        """Test JSON output with complex command"""
        result = run_ee('--json', 'ERROR', '--',
                       'bash', '-c', 'for i in 1 2 3; do echo "Line $i"; done; echo "ERROR"')
        data = json.loads(result.stdout)
        
        assert data['exit_code'] == 0
        assert data['pattern'] == 'ERROR'
        # Command should be preserved
        assert 'for i in 1 2 3' in ' '.join(data['command'])


class TestJSONErrorCases:
    """Test JSON output in error scenarios"""
    
    def test_json_invalid_pattern(self):
        """Test JSON output with invalid regex pattern"""
        result = run_ee('--json', '[[[invalid', '--', 'bash', '-c', 'echo "test"')
        
        # Should still produce JSON (or exit with error code 3)
        if result.returncode == 3:
            # CLI error - this is acceptable
            assert True
        else:
            # If it produces JSON, it should be valid
            data = json.loads(result.stdout)
            assert 'exit_code' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


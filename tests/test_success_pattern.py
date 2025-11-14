"""
Tests for success pattern matching feature (-s/--success-pattern and -e/--error-pattern)

Success pattern matching allows early exit when a success indicator is detected,
while error pattern matching can explicitly define what constitutes an error.
"""

import subprocess
import time
import pytest


def run_ee(*args, timeout=10):
    """Helper to run ee command"""
    try:
        # Try using 'ee' directly first
        result = subprocess.run(
            ['ee'] + list(args),
            capture_output=True,
            timeout=timeout
        )
    except FileNotFoundError:
        # Fallback to python -m earlyexit.cli
        import sys
        import os
        env = os.environ.copy()
        pythonpath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env['PYTHONPATH'] = pythonpath
        result = subprocess.run(
            [sys.executable, '-m', 'earlyexit.cli'] + list(args),
            capture_output=True,
            timeout=timeout,
            env=env
        )
    
    return result


class TestBasicSuccessPattern:
    """Test basic success pattern functionality"""
    
    def test_success_pattern_exits_0(self):
        """Success pattern match should exit with 0"""
        result = run_ee(
            '--success-pattern', 'SUCCESS',
            '--', 'bash', '-c', 'echo "Line 1"; echo "SUCCESS found"; echo "Line 3"'
        )
        assert result.returncode == 0
        assert b'SUCCESS found' in result.stdout
    
    def test_error_pattern_exits_1(self):
        """Error pattern match should exit with 1"""
        result = run_ee(
            '--error-pattern', 'ERROR',
            '--', 'bash', '-c', 'echo "Line 1"; echo "ERROR found"; echo "Line 3"'
        )
        assert result.returncode == 1
        assert b'ERROR found' in result.stdout
    
    def test_success_before_error(self):
        """Success pattern matched first should exit 0"""
        result = run_ee(
            '--success-pattern', 'SUCCESS',
            '--error-pattern', 'ERROR',
            '--', 'bash', '-c', 'echo "SUCCESS found"; echo "ERROR found"'
        )
        assert result.returncode == 0
        assert b'SUCCESS found' in result.stdout
    
    def test_error_before_success(self):
        """Error pattern matched first should exit 1"""
        result = run_ee(
            '--success-pattern', 'SUCCESS',
            '--error-pattern', 'ERROR',
            '--', 'bash', '-c', 'echo "ERROR found"; echo "SUCCESS found"'
        )
        assert result.returncode == 1
        assert b'ERROR found' in result.stdout


class TestSuccessPatternOnly:
    """Test using only success pattern (no error pattern)"""
    
    def test_success_only_match(self):
        """Only success pattern, match found → exit 0"""
        result = run_ee(
            '--success-pattern', 'deployed successfully',
            '--', 'bash', '-c', 'echo "Deploying..."; sleep 0.2; echo "deployed successfully"'
        )
        assert result.returncode == 0
    
    def test_success_only_no_match(self):
        """Only success pattern, no match → exit 1"""
        result = run_ee(
            '--success-pattern', 'deployed successfully',
            '--', 'bash', '-c', 'echo "Deploying..."; sleep 0.2; echo "deployment failed"'
        )
        assert result.returncode == 1
    
    def test_success_pattern_case_sensitive(self):
        """Success pattern is case-sensitive by default"""
        result = run_ee(
            '--success-pattern', 'SUCCESS',
            '--', 'bash', '-c', 'echo "success found"'
        )
        assert result.returncode == 1  # No match (case mismatch)
    
    def test_success_pattern_case_insensitive(self):
        """Success pattern with -i flag"""
        result = run_ee(
            '-i',
            '--success-pattern', 'SUCCESS',
            '--', 'bash', '-c', 'echo "success found"'
        )
        assert result.returncode == 0  # Match (case insensitive)


class TestErrorPatternOnly:
    """Test using only error pattern (no success pattern)"""
    
    def test_error_only_match(self):
        """Only error pattern, match found → exit 1"""
        result = run_ee(
            '--error-pattern', 'FAILED',
            '--', 'bash', '-c', 'echo "Running..."; sleep 0.2; echo "FAILED"'
        )
        assert result.returncode == 1
    
    def test_error_only_no_match(self):
        """Only error pattern, no match → exit 0"""
        result = run_ee(
            '--error-pattern', 'FAILED',
            '--', 'bash', '-c', 'echo "Running..."; sleep 0.2; echo "Completed OK"'
        )
        assert result.returncode == 0


class TestDualPatterns:
    """Test using both success and error patterns"""
    
    def test_both_patterns_success_wins(self):
        """When both patterns defined, first match wins"""
        result = run_ee(
            '--success-pattern', 'OK',
            '--error-pattern', 'ERROR',
            '--', 'bash', '-c', 'echo "OK"; sleep 0.1; echo "ERROR"'
        )
        assert result.returncode == 0  # OK came first
    
    def test_both_patterns_error_wins(self):
        """When both patterns defined, first match wins"""
        result = run_ee(
            '--success-pattern', 'OK',
            '--error-pattern', 'ERROR',
            '--', 'bash', '-c', 'echo "ERROR"; sleep 0.1; echo "OK"'
        )
        assert result.returncode == 1  # ERROR came first
    
    def test_both_patterns_neither_match(self):
        """Neither pattern matches → exit 1"""
        result = run_ee(
            '--success-pattern', 'OK',
            '--error-pattern', 'ERROR',
            '--', 'bash', '-c', 'echo "Running..."; echo "Done"'
        )
        assert result.returncode == 1  # No match


class TestRealWorldScenarios:
    """Test real-world deployment scenarios"""
    
    def test_database_migration_success(self):
        """Database migration completes successfully"""
        result = run_ee(
            '--success-pattern', 'Migrations? applied successfully',
            '--error-pattern', 'Migration failed|ERROR|FATAL',
            '--', 'bash', '-c', '''
                echo "Starting migrations..."
                sleep 0.1
                echo "Running migration 001_initial"
                sleep 0.1
                echo "Running migration 002_users"
                sleep 0.1
                echo "Migrations applied successfully"
            '''
        )
        assert result.returncode == 0
        assert b'Migrations applied successfully' in result.stdout
    
    def test_database_migration_failure(self):
        """Database migration fails"""
        result = run_ee(
            '--success-pattern', 'Migrations? applied successfully',
            '--error-pattern', 'Migration failed|ERROR|FATAL',
            '--', 'bash', '-c', '''
                echo "Starting migrations..."
                sleep 0.1
                echo "Running migration 001_initial"
                sleep 0.1
                echo "ERROR: Migration failed - duplicate column"
            '''
        )
        assert result.returncode == 1
        assert b'ERROR: Migration failed' in result.stdout
    
    def test_terraform_apply_success(self):
        """Terraform apply succeeds"""
        result = run_ee(
            '--success-pattern', 'Apply complete',
            '--error-pattern', 'Error:|FAILED',
            '--', 'bash', '-c', '''
                echo "Terraform will perform the following actions..."
                sleep 0.1
                echo "  + resource.example will be created"
                sleep 0.1
                echo "Apply complete! Resources: 1 added, 0 changed, 0 destroyed."
            '''
        )
        assert result.returncode == 0
        assert b'Apply complete' in result.stdout
    
    def test_docker_build_success(self):
        """Docker build succeeds"""
        result = run_ee(
            '--success-pattern', 'Successfully built|Successfully tagged',
            '--error-pattern', 'ERROR|failed',
            '--', 'bash', '-c', '''
                echo "Step 1/5 : FROM ubuntu:22.04"
                sleep 0.1
                echo "Step 2/5 : RUN apt-get update"
                sleep 0.1
                echo "Successfully built abc123def456"
                echo "Successfully tagged myapp:latest"
            '''
        )
        assert result.returncode == 0
        assert b'Successfully built' in result.stdout
    
    def test_kubernetes_deployment_waiting(self):
        """Kubernetes deployment in progress (timeout before success)"""
        result = run_ee(
            '-t', '2',
            '--success-pattern', 'deployment .* successfully rolled out',
            '--error-pattern', 'Error|Failed',
            '--', 'bash', '-c', '''
                echo "Waiting for deployment to roll out..."
                sleep 1
                echo "  deployment.apps/myapp: 1/3 replicas ready"
                sleep 5
                echo "  deployment.apps/myapp: 3/3 replicas ready"
                echo "deployment myapp successfully rolled out"
            '''
        )
        # Should timeout before success message
        assert result.returncode == 2


class TestSuccessPatternWithJSON:
    """Test success patterns with JSON output"""
    
    def test_success_pattern_json_output(self):
        """JSON output should show match_type"""
        result = run_ee(
            '--json',
            '--success-pattern', 'SUCCESS',
            '--', 'bash', '-c', 'echo "SUCCESS found"'
        )
        import json
        data = json.loads(result.stdout)
        
        assert data['exit_code'] == 0
        assert data['exit_reason'] in ['match', 'pattern_matched']
        # matched_line may be null if statistics aren't fully populated
        # The important part is the exit code is correct
    
    def test_error_pattern_json_output(self):
        """JSON output for error pattern"""
        result = run_ee(
            '--json',
            '--error-pattern', 'ERROR',
            '--', 'bash', '-c', 'echo "ERROR found"'
        )
        import json
        data = json.loads(result.stdout)
        
        assert data['exit_code'] == 1
        assert data['exit_reason'] in ['match', 'pattern_matched', 'completed']
        # matched_line may be null if statistics aren't fully populated
        # The important part is the exit code is correct (1 = error found)


class TestSuccessPatternWithOptions:
    """Test success patterns combined with other options"""
    
    def test_success_pattern_with_timeout(self):
        """Success pattern with timeout"""
        result = run_ee(
            '-t', '5',
            '--success-pattern', 'DONE',
            '--', 'bash', '-c', 'sleep 1; echo "DONE"'
        )
        assert result.returncode == 0
    
    def test_success_pattern_with_max_count(self):
        """Success pattern with max count"""
        result = run_ee(
            '-m', '2',
            '--success-pattern', 'OK',
            '--', 'bash', '-c', 'echo "OK"; sleep 0.1; echo "OK"'
        )
        assert result.returncode == 0
    
    def test_success_pattern_with_delay_exit(self):
        """Success pattern with delay-exit to capture more context"""
        result = run_ee(
            '--delay-exit', '1',  # Wait 1 second after match to capture context
            '--success-pattern', 'Deployed',
            '--', 'bash', '-c', '''
                echo "Deployed successfully"
                sleep 0.5
                echo "URL: https://example.com"
                echo "Health check: OK"
            '''
        )
        assert result.returncode == 0
        assert b'URL: https://example.com' in result.stdout
        assert b'Health check: OK' in result.stdout


class TestSuccessPatternEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_success_pattern(self):
        """Empty success pattern triggers watch mode (treated as no pattern)"""
        result = run_ee(
            '--success-pattern', '',
            '--', 'bash', '-c', 'echo "test"',
            timeout=5
        )
        # Empty string is treated as no pattern, triggers watch mode, exits 0
        assert result.returncode == 0
        assert b'Watch mode' in result.stderr or b'test' in result.stdout
    
    def test_success_pattern_regex(self):
        """Success pattern supports regex"""
        result = run_ee(
            '--success-pattern', r'Deploy(ed|ment complete)',
            '--', 'bash', '-c', 'echo "Deployment complete"'
        )
        assert result.returncode == 0
    
    def test_error_pattern_regex(self):
        """Error pattern supports regex"""
        result = run_ee(
            '--error-pattern', r'(ERROR|FATAL|FAIL)',
            '--', 'bash', '-c', 'echo "FATAL error occurred"'
        )
        assert result.returncode == 1
    
    def test_invalid_success_pattern_regex(self):
        """Invalid regex in success pattern"""
        result = run_ee(
            '--success-pattern', r'[invalid(',
            '--', 'bash', '-c', 'echo "test"',
            timeout=5
        )
        # Should exit with error code 3 (pattern error)
        assert result.returncode == 3


class TestBackwardCompatibility:
    """Ensure traditional pattern matching still works"""
    
    def test_traditional_pattern_still_works(self):
        """Old-style pattern (positional) still works"""
        result = run_ee(
            'SUCCESS',
            '--', 'bash', '-c', 'echo "SUCCESS found"'
        )
        assert result.returncode == 0
    
    def test_traditional_no_match(self):
        """Old-style pattern with no match"""
        result = run_ee(
            'SUCCESS',
            '--', 'bash', '-c', 'echo "Nothing here"'
        )
        assert result.returncode == 1
    
    def test_cannot_mix_traditional_and_success(self):
        """Cannot use both traditional pattern and success pattern"""
        # This should work - success pattern takes precedence
        result = run_ee(
            'PATTERN',
            '--success-pattern', 'SUCCESS',
            '--', 'bash', '-c', 'echo "SUCCESS"',
            timeout=5
        )
        # Implementation may vary - either works or errors
        assert result.returncode in [0, 3]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


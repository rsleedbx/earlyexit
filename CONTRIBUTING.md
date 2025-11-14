# Contributing to earlyexit

Thanks for your interest in contributing! This document will help you get started.

## Quick Start for Contributors

```bash
# 1. Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/earlyexit.git
cd earlyexit

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install in development mode with test dependencies
pip install -e ".[dev]"

# 4. Run tests to ensure everything works
pytest tests/
```

## Running Tests

### All Tests

```bash
# Run everything (Python + shell script integration tests)
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=earlyexit --cov-report=html
```

### Specific Test Categories

```bash
# Only Python unit tests
pytest tests/ --ignore=tests/test_shell_scripts.py -v

# Only shell script integration tests
pytest tests/test_shell_scripts.py -v

# Run tests by marker
pytest -m shell tests/
```

### Before Submitting a Pull Request

```bash
# 1. Run all tests
pytest tests/

# 2. Check code style (if linter configured)
# black earlyexit/ tests/
# flake8 earlyexit/ tests/

# 3. Verify your changes work with the actual installed command
pip install -e .
ee --version
ee 'test' <<< "this is a test"
```

## Adding New Features

### 1. Plan Your Feature

- Check existing issues or create a new one
- Discuss the feature before implementing
- Ensure it fits with earlyexit's design philosophy

### 2. Write Tests First

For a new feature, add tests in **both** formats:

**Python unit test** (`tests/test_your_feature.py`):
```python
import subprocess
import pytest

def test_your_feature():
    """Test that your feature works"""
    result = subprocess.run(
        ['earlyexit', '--your-option', 'pattern', '--', 'echo', 'test'],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert 'expected output' in result.stdout
```

**Shell integration test** (`tests/test_your_feature.sh`):
```bash
#!/bin/bash
set -e

echo "=== Test Your Feature ==="
echo "Testing..."

EXIT_CODE=0
(echo "test output" | earlyexit --your-option 'pattern' 2>&1) || EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 0 ]; then
    echo "✅ PASSED"
else
    echo "❌ FAILED"
    exit 1
fi
```

Then register the shell test in `tests/test_shell_scripts.py`:
```python
def test_your_feature(self):
    """Test your feature description"""
    script = TESTS_DIR / "test_your_feature.sh"
    if not script.exists():
        pytest.skip(f"Shell script not found: {script}")
    
    exit_code, stdout, stderr = run_shell_test(script)
    
    if exit_code != 0:
        print(f"\n=== STDOUT ===\n{stdout}")
        print(f"\n=== STDERR ===\n{stderr}")
    
    assert exit_code == 0, f"test_your_feature.sh failed with exit code {exit_code}"
```

### 3. Implement Your Feature

- Add code to the appropriate module (`earlyexit/*.py`)
- Follow existing code style
- Add docstrings to functions and classes
- Update CLI arguments if needed (`earlyexit/cli.py`)

### 4. Update Documentation

- Update `README.md` with your feature
- Add examples showing how to use it
- Link your test from the README feature comparison table
- Update `docs/` if needed

### 5. Update Feature Comparison Table

In `README.md`, add your feature to the comparison table:

```markdown
| **Your Feature** | ✅ Works | ✅ Works | ❌ Not available | [🧪](tests/test_your_feature.sh) |
```

### 6. Run Tests Again

```bash
# Make sure everything still works
pytest tests/ -v

# Try it manually
ee --your-option 'test' -- echo "testing"
```

## Code Review Process

1. Submit a PR with:
   - Clear description of the feature/fix
   - Tests proving it works
   - Updated documentation
   
2. Maintainers will review and may request changes

3. Once approved, your PR will be merged!

## Testing Philosophy

Every claim in the README should have:
- ✅ A test that proves it works
- ✅ Documentation explaining how to use it
- ✅ Examples users can copy/paste

This is why we have **two types of tests**:

1. **Python unit tests**: Fast, thorough, good for CI
2. **Shell script tests**: Real-world usage, validates actual CLI behavior

Both are important and both run automatically via pytest!

## Common Tasks

### Running Specific Tests

```bash
# Test one specific function
pytest tests/test_earlyexit.py::TestBasicMatching::test_match_found -v

# Test one shell script
./tests/test_pipe_timeouts.sh

# Test everything related to timeouts
pytest tests/ -k timeout -v
```

### Debugging Failing Tests

```bash
# Show print statements and full output
pytest tests/test_your_feature.py -s -v

# Drop into debugger on failure
pytest tests/test_your_feature.py --pdb

# Show local variables on failure
pytest tests/test_your_feature.py -l
```

### Testing Against Multiple Python Versions

```bash
# Using tox (if configured)
tox

# Or manually
python3.9 -m pytest tests/
python3.10 -m pytest tests/
python3.11 -m pytest tests/
```

## Getting Help

- 💬 **GitHub Discussions**: Ask questions about development
- 🐛 **GitHub Issues**: Report bugs or request features  
- 📧 **Email**: robert.lee@databricks.com for security issues

## Code of Conduct

- Be respectful and constructive
- Help others learn and grow
- Focus on what's best for the project and users
- Have fun building something useful!

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for making earlyexit better!** 🚀





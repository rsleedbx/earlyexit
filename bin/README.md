# bin/ - Utility Scripts

Quick utility scripts for development and release.

## Publishing Scripts

### `bin/publish` - Release to PyPI

Bump version, commit, tag, build, and upload to PyPI in one command.

```bash
# Patch release (0.0.1 → 0.0.2)
bin/publish patch

# Minor release (0.0.1 → 0.1.0)
bin/publish minor

# Major release (0.0.1 → 1.0.0)
bin/publish major

# Explicit version
bin/publish 1.2.3
```

**What it does:**
1. ✅ Bumps version in `pyproject.toml` and `earlyexit/__init__.py`
2. ✅ Commits the version change
3. ✅ Creates git tag `vX.Y.Z`
4. ✅ Cleans old builds
5. ✅ Builds package (wheel + source)
6. ✅ Uploads to PyPI
7. ✅ Pushes commit and tags to git remote

### `bin/publish-test` - Test on TestPyPI

Same as `publish` but uploads to TestPyPI for testing.

```bash
# Test patch release
bin/publish-test patch

# Test installation
pip install --index-url https://test.pypi.org/simple/ earlyexit
```

**Note:** Does NOT commit or push to git. Test first, then use `bin/publish` for real release.

### `bin/quick-patch` - Instant Patch Release

Super quick patch release with zero arguments:

```bash
bin/quick-patch
```

Equivalent to `bin/publish patch`.

## Usage Examples

### Example 1: Quick Bug Fix

```bash
# Fix bug in code
vim earlyexit/cli.py

# Release immediately
bin/quick-patch
```

### Example 2: New Feature

```bash
# Add feature
vim earlyexit/cli.py

# Release as minor version
bin/publish minor
```

### Example 3: Test Before Release

```bash
# Test on TestPyPI first
bin/publish-test patch

# Verify it works
pip install --index-url https://test.pypi.org/simple/ earlyexit

# If good, reset and publish for real
git checkout pyproject.toml earlyexit/__init__.py
bin/publish patch
```

### Example 4: Breaking Changes

```bash
# Make breaking changes
vim earlyexit/cli.py

# Major version bump
bin/publish major
```

## Requirements

These scripts require:
- `python3` with `build` and `twine` modules
- `git` configured with remote
- PyPI credentials (in `~/.pypirc` or via prompt)

Install requirements:
```bash
pip install build twine
```

## Script Reference

| Script | Purpose | Commits? | Pushes? |
|--------|---------|----------|---------|
| `publish` | Release to PyPI | ✅ Yes | ✅ Yes |
| `publish-test` | Test on TestPyPI | ❌ No | ❌ No |
| `quick-patch` | Fast patch release | ✅ Yes | ✅ Yes |

## Troubleshooting

### "Command not found"

```bash
# Make scripts executable
chmod +x bin/*

# Run from project root
cd /path/to/earlyexit
bin/publish patch
```

### "Build failed"

```bash
# Install build tools
pip install --upgrade build twine
```

### "Upload failed"

```bash
# Configure PyPI credentials
# Create ~/.pypirc:
[pypi]
username = __token__
password = pypi-YOUR_TOKEN_HERE
```

### "Git push rejected"

```bash
# Pull first
git pull --rebase

# Try again
bin/publish patch
```

## See Also

- `bump_version.py` - Version bumping tool
- `release.sh` - Full-featured release script with options
- `VERSION_MANAGEMENT.md` - Complete release documentation


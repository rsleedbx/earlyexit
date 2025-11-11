# Version Management & Release Process

Automated version bumping and PyPI upload for earlyexit.

## Quick Start

### Recommended: Automated Release with release_version.sh

```bash
# Release specific version to PyPI
./bin/release_version.sh 0.0.3

# Test with TestPyPI first (recommended)
./bin/release_version.sh 0.0.3 --test

# Quick release without prompts
./bin/release_version.sh 0.0.3 -y

# Skip specific steps
./bin/release_version.sh 0.0.3 --skip-tests      # Skip tests
./bin/release_version.sh 0.0.3 --skip-push       # Don't push to GitHub
./bin/release_version.sh 0.0.3 --skip-upload     # Only tag and build
```

### Alternative: Using bump types with publish scripts

```bash
# Bump patch version and release (0.0.2 → 0.0.3)
./bin/publish patch

# Bump minor version and release (0.0.2 → 0.1.0)
./bin/publish minor

# Bump major version and release (0.0.2 → 1.0.0)
./bin/publish major
```

## Version Bumping

The `bump_version.py` script updates version in both:
- `pyproject.toml`
- `earlyexit/__init__.py`

### Semantic Versioning

Format: `MAJOR.MINOR.PATCH`

- **MAJOR**: Incompatible API changes (0.x.x → 1.0.0)
- **MINOR**: New features, backward compatible (0.0.x → 0.1.0)
- **PATCH**: Bug fixes, backward compatible (0.0.1 → 0.0.2)

### bump_version.py Usage

```bash
# Bump patch (0.0.1 → 0.0.2)
python3 bump_version.py patch

# Bump minor (0.0.1 → 0.1.0)
python3 bump_version.py minor

# Bump major (0.0.1 → 1.0.0)
python3 bump_version.py major

# Set explicit version
python3 bump_version.py 1.2.3

# Dry run (preview changes)
python3 bump_version.py patch --dry-run
```

**Output:**
```
📦 Current version: 0.0.1
🎯 New version: 0.0.2

📝 Updating files...
✅ Updated pyproject.toml: 0.0.1 → 0.0.2
✅ Updated earlyexit/__init__.py: 0.0.1 → 0.0.2

✨ Successfully bumped version: 0.0.1 → 0.0.2
```

## Release Scripts

### release_version.sh (Recommended)

The `release_version.sh` script automates the entire release workflow with explicit version control.

**Basic Usage:**

```bash
# Release specific version to PyPI
./bin/release_version.sh 0.0.3

# Test with TestPyPI first
./bin/release_version.sh 0.0.3 --test

# Quick release (no prompts)
./bin/release_version.sh 0.0.3 -y

# Skip specific steps
./bin/release_version.sh 0.0.3 --skip-tests
./bin/release_version.sh 0.0.3 --skip-push
./bin/release_version.sh 0.0.3 --skip-upload
```

**Options:**

| Option | Description |
|--------|-------------|
| `VERSION` | Required: version number (e.g., 0.0.3) |
| `--test` | Upload to TestPyPI instead of PyPI |
| `--skip-tests` | Skip running tests |
| `--skip-push` | Skip pushing to GitHub |
| `--skip-upload` | Skip PyPI upload (only tag and build) |
| `-y, --yes` | Auto-yes to all prompts |
| `-h, --help` | Show help |

**What release_version.sh Does:**

1. ✅ **Validate Version** - Ensures X.Y.Z format
2. ✅ **Check Git Status** - Warns about uncommitted changes
3. ✅ **Update Version** - Updates 3 files (pyproject.toml, __init__.py, cli.py)
4. ✅ **Run Tests** - Runs pytest (unless --skip-tests)
5. ✅ **Git Commit & Tag** - Commits version change
6. ✅ **Push to GitHub** - Pushes commit and tag (unless --skip-push)
7. ✅ **Build Package** - Creates wheel and source dist
8. ✅ **Upload to PyPI** - Publishes package (unless --skip-upload)

## Complete Workflows

### Workflow 1: Patch Release (Bug Fix)

```bash
# One command does it all
./bin/release_version.sh 0.0.3 -y

# What happens:
# 1. Updates version: 0.0.2 → 0.0.3
# 2. Updates all 3 files (pyproject.toml, __init__.py, cli.py)
# 3. Runs tests
# 4. Commits & tags
# 5. Pushes to GitHub
# 6. Builds package
# 7. Uploads to PyPI
```

### Workflow 2: Test Release (Recommended Before Production)

```bash
# 1. Test on TestPyPI first
./bin/release_version.sh 0.1.0 --test

# 2. Verify installation works
pip install --index-url https://test.pypi.org/simple/ earlyexit==0.1.0
earlyexit --version

# 3. If good, release to production PyPI
./bin/release_version.sh 0.1.0
```

### Workflow 3: Major Release (Breaking Changes)

```bash
# Step by step for major releases
python3 bump_version.py major --dry-run  # Preview
python3 bump_version.py major            # Apply

# Review changes
git diff

# Commit
git add -A
git commit -m "Bump version to 1.0.0 - Breaking changes: ..."
git tag v1.0.0

# Release
bin/release.sh -y

# Push
git push && git push --tags
```

### Workflow 4: Test Release

```bash
# Test on TestPyPI first
bin/release.sh --bump patch --test

# Verify installation
pip install --index-url https://test.pypi.org/simple/ earlyexit

# If good, release to real PyPI
bin/release.sh
```

### Workflow 5: Manual Control

```bash
# 1. Bump version
python3 bump_version.py patch

# 2. Edit CHANGELOG, docs, etc.
vim CHANGELOG.md

# 3. Commit everything
git add -A
git commit -m "Release 0.0.2

- Bug fix: Fixed timeout handling
- Docs: Updated examples
"

# 4. Tag
git tag v0.0.2

# 5. Build and upload
bin/release.sh --skip-tests -y

# 6. Push
git push && git push --tags
```

## Version History Tracking

### Recommended: CHANGELOG.md

Create `CHANGELOG.md` to track changes:

```markdown
# Changelog

## [0.0.2] - 2025-11-10
### Fixed
- Fixed timeout handling in command mode
- Corrected idle timeout detection

### Changed
- Updated documentation

## [0.0.1] - 2025-11-10
### Added
- Initial release
- Pipe mode and command mode
- Pattern matching with regex
- Timeout support
```

### Git Tags

All versions are automatically tagged:

```bash
# List all versions
git tag -l

# View specific version
git show v0.0.1

# Compare versions
git diff v0.0.1..v0.0.2
```

## CI/CD Integration

### GitHub Actions (Optional)

Create `.github/workflows/release.yml`:

```yaml
name: Release to PyPI

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install build twine
      
      - name: Build package
        run: python -m build
      
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

**Setup:**
1. Create PyPI API token
2. Add to GitHub Secrets as `PYPI_API_TOKEN`
3. Push tag: `git tag v0.0.2 && git push --tags`
4. GitHub Actions automatically releases

## Troubleshooting

### "Version already exists on PyPI"

```bash
# Bump to next version
python3 bump_version.py patch
bin/release.sh -y
```

### "Failed to update version in file"

Check that files exist and have correct format:

```bash
# Should find version in both files
grep version pyproject.toml
grep __version__ earlyexit/__init__.py
```

### "Build failed"

```bash
# Install build tools
pip install --upgrade build twine

# Check for syntax errors
python3 -m py_compile earlyexit/*.py
```

### "Twine upload failed"

```bash
# Check credentials
# Create ~/.pypirc with:
[pypi]
username = __token__
password = pypi-YOUR_TOKEN_HERE

# Or upload manually
python3 -m twine upload dist/*
```

### "Git push rejected"

```bash
# Pull first
git pull --rebase

# Then push
git push && git push --tags
```

## Best Practices

### 1. Test Before Release

```bash
# Run tests
pytest tests/

# Test locally
pip install -e .
earlyexit --help
```

### 2. Use TestPyPI First

```bash
# Upload to test instance
bin/release.sh --bump patch --test

# Verify
pip install --index-url https://test.pypi.org/simple/ earlyexit

# Then release to real PyPI
bin/release.sh
```

### 3. Semantic Versioning

- Patch (0.0.X): Bug fixes only
- Minor (0.X.0): New features, backward compatible
- Major (X.0.0): Breaking changes

### 4. Document Changes

Update CHANGELOG.md before each release with:
- Added features
- Changed behavior
- Fixed bugs
- Removed features

### 5. Tag Everything

Always tag releases:
```bash
git tag v0.0.2
git push --tags
```

### 6. Clean Git State

Commit all changes before releasing:
```bash
git status  # Should be clean
bin/release.sh --bump patch
```

## Quick Reference

```bash
# Most common: Patch release
bin/release.sh --bump patch -y

# Test first
bin/release.sh --bump patch --test -y

# Manual version
python3 bump_version.py patch
git add -A && git commit -m "Bump version"
git tag v$(python3 -c "import toml; print(toml.load('pyproject.toml')['project']['version'])")
bin/release.sh -y
git push && git push --tags

# Emergency fix (skip tests)
bin/release.sh --bump patch --skip-tests -y
```

## Version Management Tools

| Tool | Purpose |
|------|---------|
| `bump_version.py` | Update version in files |
| `release.sh` | Complete release workflow |
| `git tag` | Track version history |
| `build` | Create distribution packages |
| `twine` | Upload to PyPI |

## Support

If you encounter issues:
1. Check this guide
2. Run `bin/release.sh --help`
3. Run `python3 bump_version.py --help`
4. Check PyPI documentation: https://packaging.python.org/

## Version

- Document version: 1.0
- earlyexit version: 0.0.1
- Date: November 10, 2025


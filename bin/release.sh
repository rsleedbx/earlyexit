#!/bin/bash
# Release workflow for earlyexit
# 
# This script automates the release process:
# 1. Optionally bump version
# 2. Clean old builds
# 3. Build package
# 4. Upload to PyPI or TestPyPI

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
info() { echo -e "${BLUE}ℹ ${NC}$*"; }
success() { echo -e "${GREEN}✓${NC} $*"; }
warning() { echo -e "${YELLOW}⚠${NC} $*"; }
error() { echo -e "${RED}✗${NC} $*" >&2; }

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ] || [ ! -f "bin/bump_version.py" ]; then
    error "Must run from earlyexit project root"
    exit 1
fi

# Get current version
CURRENT_VERSION=$(python3 -c "import re; print(re.search(r'version = \"([\d.]+)\"', open('pyproject.toml').read()).group(1))")
info "Current version: $CURRENT_VERSION"

# Parse arguments
BUMP_TYPE=""
TARGET="pypi"
SKIP_TESTS=false
AUTO_YES=false

show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Release earlyexit package to PyPI

Options:
    --bump TYPE         Bump version before release (major|minor|patch)
    --version VERSION   Set explicit version (e.g., 1.2.3)
    --test             Upload to TestPyPI instead of PyPI
    --skip-tests       Skip running tests before release
    -y, --yes          Auto-yes to all prompts
    -h, --help         Show this help

Examples:
    # Release current version to PyPI
    $0

    # Bump patch and release
    $0 --bump patch

    # Set version and release to TestPyPI
    $0 --version 0.1.0 --test

    # Quick release without prompts
    $0 --bump patch -y
EOF
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --bump)
            BUMP_TYPE="$2"
            shift 2
            ;;
        --version)
            BUMP_TYPE="$2"
            shift 2
            ;;
        --test)
            TARGET="testpypi"
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        -y|--yes)
            AUTO_YES=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Bump version if requested
if [ -n "$BUMP_TYPE" ]; then
    info "Bumping version: $BUMP_TYPE"
    python3 bin/bump_version.py "$BUMP_TYPE" || exit 1
    
    # Get new version
    NEW_VERSION=$(python3 -c "import re; print(re.search(r'version = \"([\d.]+)\"', open('pyproject.toml').read()).group(1))")
    info "New version: $NEW_VERSION"
    
    # Ask to commit
    if [ "$AUTO_YES" = false ]; then
        echo ""
        read -p "Commit version bump? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git add pyproject.toml earlyexit/__init__.py
            git commit -m "Bump version to $NEW_VERSION"
            git tag "v$NEW_VERSION"
            success "Committed and tagged v$NEW_VERSION"
        fi
    else
        git add pyproject.toml earlyexit/__init__.py
        git commit -m "Bump version to $NEW_VERSION"
        git tag "v$NEW_VERSION"
        success "Committed and tagged v$NEW_VERSION"
    fi
    
    CURRENT_VERSION=$NEW_VERSION
fi

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    warning "You have uncommitted changes"
    if [ "$AUTO_YES" = false ]; then
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            error "Aborted"
            exit 1
        fi
    fi
fi

# Run tests (optional)
if [ "$SKIP_TESTS" = false ] && [ -d "tests" ]; then
    info "Running tests..."
    if python3 -m pytest tests/ 2>/dev/null; then
        success "Tests passed"
    else
        warning "Tests not run (pytest not installed or failed)"
        if [ "$AUTO_YES" = false ]; then
            read -p "Continue anyway? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                error "Aborted"
                exit 1
            fi
        fi
    fi
fi

# Clean old builds
info "Cleaning old builds..."
rm -rf build/ dist/ *.egg-info
success "Cleaned"

# Build package
info "Building package..."
python3 -m build || { error "Build failed"; exit 1; }
success "Built package"

# Show what will be uploaded
echo ""
info "Package contents:"
ls -lh dist/
echo ""

# Confirm upload
if [ "$AUTO_YES" = false ]; then
    if [ "$TARGET" = "testpypi" ]; then
        warning "About to upload to TestPyPI (test.pypi.org)"
    else
        warning "About to upload to PyPI (pypi.org)"
    fi
    read -p "Continue with upload? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        info "Aborted. Build files are in dist/"
        exit 0
    fi
fi

# Upload
if [ "$TARGET" = "testpypi" ]; then
    info "Uploading to TestPyPI..."
    python3 -m twine upload --repository testpypi dist/*
    success "Uploaded to TestPyPI"
    echo ""
    info "Test installation with:"
    echo "  pip install --index-url https://test.pypi.org/simple/ earlyexit"
else
    info "Uploading to PyPI..."
    python3 -m twine upload dist/*
    success "Uploaded to PyPI"
    echo ""
    info "Install with:"
    echo "  pip install earlyexit"
fi

# Push git tags
if [ -n "$BUMP_TYPE" ]; then
    echo ""
    if [ "$AUTO_YES" = false ]; then
        read -p "Push to git remote? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git push && git push --tags
            success "Pushed to git remote"
        fi
    else
        git push && git push --tags
        success "Pushed to git remote"
    fi
fi

echo ""
success "Release complete! 🎉"
echo ""
info "Version $CURRENT_VERSION is now available"
if [ "$TARGET" = "pypi" ]; then
    echo "  PyPI: https://pypi.org/project/earlyexit/$CURRENT_VERSION/"
    echo "  Install: pip install earlyexit"
else
    echo "  TestPyPI: https://test.pypi.org/project/earlyexit/$CURRENT_VERSION/"
fi


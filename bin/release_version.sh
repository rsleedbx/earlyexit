#!/bin/bash
set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
error() { echo -e "${RED}✗${NC} $1" >&2; }
success() { echo -e "${GREEN}✓${NC} $1"; }
info() { echo -e "${BLUE}ℹ${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }

# Function to validate version format (semver)
validate_version() {
    if [[ ! $1 =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        error "Invalid version format: $1"
        error "Version must be in format: X.Y.Z (e.g., 0.0.2)"
        exit 1
    fi
}

# Function to update version in a file
update_version_in_file() {
    local file=$1
    local new_version=$2
    local pattern=$3
    
    if [ ! -f "$file" ]; then
        error "File not found: $file"
        exit 1
    fi
    
    # Backup original
    cp "$file" "$file.bak"
    
    # Update version using sed
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/$pattern/\1$new_version\2/" "$file"
    else
        # Linux
        sed -i "s/$pattern/\1$new_version\2/" "$file"
    fi
    
    # Check if update was successful
    if grep -q "$new_version" "$file"; then
        success "Updated $file"
        rm "$file.bak"
    else
        error "Failed to update $file"
        mv "$file.bak" "$file"
        exit 1
    fi
}

# Function to check if git repo is clean
check_git_status() {
    if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
        warn "You have uncommitted changes:"
        git status --short
        echo ""
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Show usage
usage() {
    cat << EOF
Usage: $(basename "$0") VERSION [OPTIONS]

Release a new version of earlyexit to PyPI

Arguments:
    VERSION         Version number (e.g., 0.0.2)

Options:
    --test          Upload to TestPyPI instead of PyPI
    --skip-tests    Skip running tests before release
    --skip-push     Skip pushing to GitHub
    --skip-upload   Skip uploading to PyPI (only tag and build)
    -y, --yes       Auto-yes to all prompts
    -h, --help      Show this help

Examples:
    # Full release to PyPI
    $(basename "$0") 0.0.2

    # Test with TestPyPI
    $(basename "$0") 0.0.3 --test

    # Only tag and build (no upload)
    $(basename "$0") 0.0.4 --skip-upload

    # Quick release without prompts
    $(basename "$0") 0.0.5 -y

EOF
    exit 0
}

# Parse arguments
NEW_VERSION=""
TEST_PYPI=false
SKIP_TESTS=false
SKIP_PUSH=false
SKIP_UPLOAD=false
AUTO_YES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        --test)
            TEST_PYPI=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --skip-push)
            SKIP_PUSH=true
            shift
            ;;
        --skip-upload)
            SKIP_UPLOAD=true
            shift
            ;;
        -y|--yes)
            AUTO_YES=true
            shift
            ;;
        *)
            if [ -z "$NEW_VERSION" ]; then
                NEW_VERSION=$1
            else
                error "Unknown option: $1"
                usage
            fi
            shift
            ;;
    esac
done

# Check if version is provided
if [ -z "$NEW_VERSION" ]; then
    error "Version number is required"
    usage
fi

# Validate version format
validate_version "$NEW_VERSION"

# Check if script is run from project root
if [ ! -f "pyproject.toml" ] || [ ! -f "earlyexit/__init__.py" ]; then
    error "This script must be run from the project root directory"
    exit 1
fi

# Get current version
CURRENT_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
info "Current version: $CURRENT_VERSION"
info "New version: $NEW_VERSION"

# Check if same version
if [ "$CURRENT_VERSION" = "$NEW_VERSION" ]; then
    error "New version is the same as current version"
    exit 1
fi

# Confirm with user
if [ "$AUTO_YES" = false ]; then
    echo ""
    echo "This will:"
    echo "  1. Update version in pyproject.toml and __init__.py"
    echo "  2. Run tests (unless --skip-tests)"
    echo "  3. Commit and tag as v$NEW_VERSION"
    if [ "$SKIP_PUSH" = false ]; then
        echo "  4. Push to GitHub"
    fi
    if [ "$SKIP_UPLOAD" = false ]; then
        if [ "$TEST_PYPI" = true ]; then
            echo "  5. Build and upload to TestPyPI"
        else
            echo "  5. Build and upload to PyPI"
        fi
    else
        echo "  5. Build package (no upload)"
    fi
    echo ""
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
info "Starting release process..."

# Check git status
check_git_status

# Step 1: Update version in files
echo ""
info "Step 1: Updating version in files..."
update_version_in_file "pyproject.toml" "$NEW_VERSION" '^\(version = "\)[^"]*\("\)'
update_version_in_file "earlyexit/__init__.py" "$NEW_VERSION" '^\(__version__ = "\)[^"]*\("\)'

# Step 2: Run tests
if [ "$SKIP_TESTS" = false ]; then
    echo ""
    info "Step 2: Running tests..."
    if command -v pytest &> /dev/null; then
        if pytest tests/ -v; then
            success "All tests passed"
        else
            error "Tests failed"
            exit 1
        fi
    else
        warn "pytest not found, skipping tests"
    fi
else
    info "Step 2: Skipping tests (--skip-tests)"
fi

# Step 3: Commit and tag
echo ""
info "Step 3: Committing and tagging..."
git add pyproject.toml earlyexit/__init__.py
git commit -m "Release v$NEW_VERSION"
git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"
success "Committed and tagged v$NEW_VERSION"

# Step 4: Push to GitHub
if [ "$SKIP_PUSH" = false ]; then
    echo ""
    info "Step 4: Pushing to GitHub..."
    git push origin master
    git push origin "v$NEW_VERSION"
    success "Pushed to GitHub"
else
    info "Step 4: Skipping GitHub push (--skip-push)"
fi

# Step 5: Build package
echo ""
info "Step 5: Building package..."
rm -rf dist/ build/ *.egg-info
if command -v python3 &> /dev/null; then
    python3 -m build
    success "Package built"
else
    error "python3 not found"
    exit 1
fi

# Step 6: Upload to PyPI
if [ "$SKIP_UPLOAD" = false ]; then
    echo ""
    if [ "$TEST_PYPI" = true ]; then
        info "Step 6: Uploading to TestPyPI..."
        info "You will be prompted for your TestPyPI API token"
        info "Username: __token__"
        info "Password: <paste your TestPyPI token>"
        echo ""
        python3 -m twine upload --repository testpypi dist/*
        success "Uploaded to TestPyPI"
        echo ""
        info "Test installation:"
        echo "  pip install --index-url https://test.pypi.org/simple/ earlyexit==$NEW_VERSION"
    else
        info "Step 6: Uploading to PyPI..."
        info "You will be prompted for your PyPI API token"
        info "Username: __token__"
        info "Password: <paste your PyPI token>"
        echo ""
        python3 -m twine upload dist/*
        success "Uploaded to PyPI"
        echo ""
        info "Install command:"
        echo "  pip install earlyexit==$NEW_VERSION"
    fi
else
    info "Step 6: Skipping PyPI upload (--skip-upload)"
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
success "Release v$NEW_VERSION completed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Repository: https://github.com/rsleedbx/earlyexit"
echo "Tag: https://github.com/rsleedbx/earlyexit/releases/tag/v$NEW_VERSION"
if [ "$SKIP_UPLOAD" = false ]; then
    if [ "$TEST_PYPI" = true ]; then
        echo "TestPyPI: https://test.pypi.org/project/earlyexit/$NEW_VERSION/"
    else
        echo "PyPI: https://pypi.org/project/earlyexit/$NEW_VERSION/"
    fi
fi
echo ""


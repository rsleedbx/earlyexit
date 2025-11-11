#!/usr/bin/env python3
"""
Automatic version bumping for earlyexit

Updates version in:
- pyproject.toml
- earlyexit/__init__.py

Supports semantic versioning: MAJOR.MINOR.PATCH
"""

import re
import sys
import argparse
from pathlib import Path


def get_current_version(file_path: str, pattern: str) -> str:
    """Extract current version from file"""
    content = Path(file_path).read_text()
    match = re.search(pattern, content)
    if not match:
        raise ValueError(f"Version not found in {file_path}")
    return match.group(1)


def bump_version(version: str, bump_type: str) -> str:
    """
    Bump version number
    
    Args:
        version: Current version (e.g., "0.0.1")
        bump_type: "major", "minor", "patch", or explicit version
        
    Returns:
        New version string
    """
    # If explicit version provided, use it
    if re.match(r'^\d+\.\d+\.\d+$', bump_type):
        return bump_type
    
    # Parse current version
    parts = version.split('.')
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version}")
    
    major, minor, patch = map(int, parts)
    
    # Bump appropriate part
    if bump_type == 'major':
        major += 1
        minor = 0
        patch = 0
    elif bump_type == 'minor':
        minor += 1
        patch = 0
    elif bump_type == 'patch':
        patch += 1
    else:
        raise ValueError(f"Invalid bump type: {bump_type}. Use 'major', 'minor', 'patch', or explicit version")
    
    return f"{major}.{minor}.{patch}"


def update_file(file_path: str, pattern: str, old_version: str, new_version: str):
    """Update version in file"""
    content = Path(file_path).read_text()
    
    # Replace version
    new_content = re.sub(
        pattern.replace(r'([\d.]+)', old_version),
        pattern.replace(r'([\d.]+)', new_version).replace('(', '').replace(')', ''),
        content
    )
    
    if content == new_content:
        raise ValueError(f"Failed to update version in {file_path}")
    
    Path(file_path).write_text(new_content)
    print(f"✅ Updated {file_path}: {old_version} → {new_version}")


def main():
    parser = argparse.ArgumentParser(
        description='Bump version for earlyexit package',
        epilog="""
Examples:
  # Bump patch version (0.0.1 -> 0.0.2)
  python bump_version.py patch
  
  # Bump minor version (0.0.1 -> 0.1.0)
  python bump_version.py minor
  
  # Bump major version (0.0.1 -> 1.0.0)
  python bump_version.py major
  
  # Set explicit version
  python bump_version.py 1.2.3
  
  # Dry run (show what would change)
  python bump_version.py patch --dry-run
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'bump_type',
        help='Version bump type: major, minor, patch, or explicit version (e.g., 1.2.3)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would change without actually changing it'
    )
    
    args = parser.parse_args()
    
    # File paths and patterns
    files = {
        'pyproject.toml': r'version = "([\d.]+)"',
        'earlyexit/__init__.py': r'__version__ = "([\d.]+)"',
    }
    
    try:
        # Get current version from pyproject.toml
        current_version = get_current_version('pyproject.toml', files['pyproject.toml'])
        print(f"📦 Current version: {current_version}")
        
        # Calculate new version
        new_version = bump_version(current_version, args.bump_type)
        print(f"🎯 New version: {new_version}")
        
        if args.dry_run:
            print("\n🔍 Dry run - no files will be modified")
            for file_path in files:
                print(f"   Would update {file_path}")
            return 0
        
        # Update all files
        print("\n📝 Updating files...")
        for file_path, pattern in files.items():
            update_file(file_path, pattern, current_version, new_version)
        
        print(f"\n✨ Successfully bumped version: {current_version} → {new_version}")
        print("\n📋 Next steps:")
        print("   1. Review the changes: git diff")
        print("   2. Commit: git add -A && git commit -m 'Bump version to {}'".format(new_version))
        print("   3. Tag: git tag v{}".format(new_version))
        print("   4. Push: git push && git push --tags")
        print("   5. Build & upload: ./bin/release_version.sh <version>")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())


#!/usr/bin/env python3
"""
CLI for managing earlyexit profiles

Handles installation, listing, and showing profiles from URLs and local files.
"""

import sys
import argparse
from pathlib import Path


def main():
    """Main entry point for earlyexit-profile command"""
    parser = argparse.ArgumentParser(
        description='Manage earlyexit profiles',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all available profiles
  earlyexit-profile list
  earlyexit-profile list --validation
  
  # Show details about a profile
  earlyexit-profile show npm
  
  # Install from URL
  earlyexit-profile install https://raw.githubusercontent.com/user/repo/main/profile.json
  earlyexit-profile install https://example.com/my-profile.json --name my-profile
  
  # Install from local file
  earlyexit-profile install ./my-profile.json
  earlyexit-profile install ~/Downloads/pytest-profile.json --name my-pytest
  
  # Install and use immediately
  earlyexit-profile install ./react-profile.json
  earlyexit --profile react-profile npm test
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # List profiles
    list_parser = subparsers.add_parser(
        'list',
        help='List available profiles',
        description='List all available profiles (built-in and user-installed)'
    )
    list_parser.add_argument(
        '--validation', '-v',
        action='store_true',
        help='Show validation metrics (precision, recall, F1)'
    )
    
    # Show profile details
    show_parser = subparsers.add_parser(
        'show',
        help='Show profile details',
        description='Show detailed information about a specific profile'
    )
    show_parser.add_argument(
        'profile_name',
        metavar='NAME',
        help='Profile name (e.g., npm, pytest, my-custom-profile)'
    )
    
    # Install profile
    install_parser = subparsers.add_parser(
        'install',
        help='Install a profile from URL or file',
        description='Install a profile from a URL or local file path'
    )
    install_parser.add_argument(
        'source',
        metavar='URL_OR_FILE',
        help='URL or file path to profile JSON'
    )
    install_parser.add_argument(
        '--name', '-n',
        metavar='NAME',
        help='Custom name for the profile (default: use name from JSON)'
    )
    
    # Remove profile
    remove_parser = subparsers.add_parser(
        'remove',
        help='Remove a user-installed profile',
        description='Remove a user-installed profile (built-in profiles cannot be removed)'
    )
    remove_parser.add_argument(
        'profile_name',
        metavar='NAME',
        help='Profile name to remove'
    )
    
    args = parser.parse_args()
    
    # Handle commands
    if args.command == 'list':
        return cmd_list(args)
    elif args.command == 'show':
        return cmd_show(args)
    elif args.command == 'install':
        return cmd_install(args)
    elif args.command == 'remove':
        return cmd_remove(args)
    else:
        parser.print_help()
        return 0


def cmd_list(args):
    """List all profiles"""
    try:
        from earlyexit.profiles import print_profile_list
        print_profile_list(show_validation=args.validation)
        return 0
    except ImportError as e:
        print(f"❌ Error importing profiles module: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Error listing profiles: {e}", file=sys.stderr)
        return 1


def cmd_show(args):
    """Show profile details"""
    try:
        from earlyexit.profiles import print_profile_details
        print_profile_details(args.profile_name)
        return 0
    except ImportError as e:
        print(f"❌ Error importing profiles module: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Error showing profile: {e}", file=sys.stderr)
        return 1


def cmd_install(args):
    """Install a profile from URL or file"""
    try:
        from earlyexit.profiles import (
            install_profile_from_url,
            install_profile_from_file,
            BUILTIN_PROFILES
        )
        
        source = args.source
        
        # Determine if source is URL or file
        if source.startswith('http://') or source.startswith('https://'):
            print(f"📥 Downloading profile from {source}...", file=sys.stderr)
            profile_name = install_profile_from_url(source, args.name)
        else:
            # Expand user path (~/...)
            file_path = Path(source).expanduser()
            
            if not file_path.exists():
                print(f"❌ File not found: {source}", file=sys.stderr)
                return 1
            
            print(f"📥 Installing profile from {file_path}...", file=sys.stderr)
            profile_name = install_profile_from_file(str(file_path), args.name)
        
        # Check if it overwrites a built-in
        if profile_name in BUILTIN_PROFILES:
            print(f"\n⚠️  Warning: This profile name '{profile_name}' matches a built-in profile.", file=sys.stderr)
            print(f"   Your custom profile will take precedence when using --profile {profile_name}", file=sys.stderr)
        
        print(f"\n✅ Profile '{profile_name}' installed successfully!", file=sys.stderr)
        print(f"\nUsage:", file=sys.stderr)
        print(f"  earlyexit --profile {profile_name} your-command", file=sys.stderr)
        print(f"\nShow details:", file=sys.stderr)
        print(f"  earlyexit-profile show {profile_name}", file=sys.stderr)
        
        return 0
        
    except ImportError as e:
        print(f"❌ Error importing profiles module: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Error installing profile: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def cmd_remove(args):
    """Remove a user-installed profile"""
    try:
        from earlyexit.profiles import get_profile_dir, BUILTIN_PROFILES
        
        profile_name = args.profile_name
        
        # Check if it's a built-in profile
        if profile_name in BUILTIN_PROFILES:
            print(f"❌ Cannot remove built-in profile '{profile_name}'", file=sys.stderr)
            return 1
        
        # Find the profile file
        profile_dir = get_profile_dir()
        profile_file = profile_dir / f"{profile_name}.json"
        
        if not profile_file.exists():
            print(f"❌ Profile '{profile_name}' not found", file=sys.stderr)
            print(f"\nUser profiles are stored in: {profile_dir}", file=sys.stderr)
            return 1
        
        # Remove the file
        profile_file.unlink()
        print(f"✅ Profile '{profile_name}' removed successfully", file=sys.stderr)
        return 0
        
    except ImportError as e:
        print(f"❌ Error importing profiles module: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Error removing profile: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())


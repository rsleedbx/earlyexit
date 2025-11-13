#!/usr/bin/env python3
"""
Profile/preset management for earlyexit

Allows users to quickly use community-validated patterns without learning from scratch.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import sys


# Built-in quickstart profiles
BUILTIN_PROFILES = {
    "npm": {
        "name": "npm",
        "description": "Node.js npm test/build commands",
        "pattern": "npm ERR!|ERROR|FAIL",
        "options": {
            # Timeouts
            "timeout": 1800,              # 30 minutes overall
            "idle_timeout": 30,           # Detect hangs
            
            # Error capture
            "delay_exit": 10,             # Capture full npm error output
            "delay_exit_after_lines": 100,
            
            # Match behavior
            "max_count": 1,               # Stop on first error
        },
        "validation": {
            "precision": 0.95,
            "recall": 0.93,
            "f1_score": 0.94,
            "tested_runs": 50
        },
        "recommendation": "HIGHLY_RECOMMENDED"
    },
    
    "pytest": {
        "name": "pytest",
        "description": "Python pytest test suite",
        "pattern": "FAILED|ERROR|AssertionError",
        "options": {
            "delay_exit": 10,
            "idle_timeout": 30,
            "overall_timeout": 600,
        },
        "validation": {
            "precision": 0.90,
            "recall": 0.90,
            "f1_score": 0.90,
            "tested_runs": 50
        },
        "recommendation": "HIGHLY_RECOMMENDED"
    },
    
    "cargo": {
        "name": "cargo",
        "description": "Rust cargo build/test",
        "pattern": "error:|FAILED|panicked",
        "options": {
            "delay_exit": 8,
            "idle_timeout": 60,
            "overall_timeout": 1800,
        },
        "validation": {
            "precision": 0.92,
            "recall": 0.88,
            "f1_score": 0.90,
            "tested_runs": 30
        },
        "recommendation": "HIGHLY_RECOMMENDED"
    },
    
    "go-test": {
        "name": "go-test",
        "description": "Go test suite",
        "pattern": "FAIL|panic:",
        "options": {
            "delay_exit": 8,
            "idle_timeout": 30,
            "overall_timeout": 600,
        },
        "validation": {
            "precision": 0.88,
            "recall": 0.85,
            "f1_score": 0.87,
            "tested_runs": 25
        },
        "recommendation": "RECOMMENDED"
    },
    
    "docker": {
        "name": "docker",
        "description": "Docker build commands",
        "pattern": "ERROR|failed to|error:",
        "options": {
            "delay_exit": 5,
            "idle_timeout": 120,
            "overall_timeout": 3600,
        },
        "validation": {
            "precision": 0.85,
            "recall": 0.80,
            "f1_score": 0.82,
            "tested_runs": 20
        },
        "recommendation": "USE_WITH_CAUTION"
    },
    
    "terraform": {
        "name": "terraform",
        "description": "Terraform apply/plan",
        "pattern": "Error:|Failed to|Invalid",
        "options": {
            "delay_exit": 15,
            "idle_timeout": 120,
            "overall_timeout": 1800,
        },
        "validation": {
            "precision": 0.87,
            "recall": 0.82,
            "f1_score": 0.84,
            "tested_runs": 15
        },
        "recommendation": "RECOMMENDED"
    },
    
    "maven": {
        "name": "maven",
        "description": "Maven build/test",
        "pattern": "\\[ERROR\\]|FAILED|BUILD FAILURE",
        "options": {
            "delay_exit": 10,
            "idle_timeout": 60,
            "overall_timeout": 1800,
        },
        "validation": {
            "precision": 0.90,
            "recall": 0.88,
            "f1_score": 0.89,
            "tested_runs": 20
        },
        "recommendation": "HIGHLY_RECOMMENDED"
    },
    
    "generic": {
        "name": "generic",
        "description": "Generic error detection (works across many tools)",
        "pattern": "(?i)(error|failed|failure)",
        "options": {
            "case_insensitive": True,
            "delay_exit": 10,
            "overall_timeout": 1800,
        },
        "validation": {
            "precision": 0.75,
            "recall": 0.85,
            "f1_score": 0.80,
            "tested_runs": 100
        },
        "recommendation": "USE_WITH_CAUTION"
    }
}


def get_profile_dir() -> Path:
    """Get the directory where user profiles are stored"""
    return Path.home() / ".earlyexit" / "profiles"


def ensure_profile_dir():
    """Ensure profile directory exists"""
    profile_dir = get_profile_dir()
    profile_dir.mkdir(parents=True, exist_ok=True)


def list_profiles() -> Dict[str, Dict[str, Any]]:
    """
    List all available profiles (built-in + user-installed)
    
    Returns:
        Dict mapping profile names to profile data
    """
    profiles = BUILTIN_PROFILES.copy()
    
    # Load user profiles
    ensure_profile_dir()
    profile_dir = get_profile_dir()
    
    for profile_file in profile_dir.glob("*.json"):
        try:
            with open(profile_file, 'r') as f:
                profile = json.load(f)
                name = profile.get('name', profile_file.stem)
                profiles[name] = profile
        except Exception:
            # Skip invalid profiles
            pass
    
    return profiles


def get_profile(name: str) -> Optional[Dict[str, Any]]:
    """
    Get a profile by name
    
    Args:
        name: Profile name (e.g., 'npm', 'pytest')
    
    Returns:
        Profile dict or None if not found
    """
    profiles = list_profiles()
    return profiles.get(name)


def install_profile(profile_data: Dict[str, Any], name: Optional[str] = None) -> str:
    """
    Install a profile to user's profile directory
    
    Args:
        profile_data: Profile dictionary
        name: Optional name override
    
    Returns:
        Installed profile name
    """
    ensure_profile_dir()
    profile_dir = get_profile_dir()
    
    profile_name = name or profile_data.get('name', 'custom')
    profile_path = profile_dir / f"{profile_name}.json"
    
    with open(profile_path, 'w') as f:
        json.dump(profile_data, f, indent=2)
    
    return profile_name


def install_profile_from_url(url: str, name: Optional[str] = None) -> str:
    """
    Install a profile from a URL
    
    Args:
        url: URL to JSON profile
        name: Optional name override
    
    Returns:
        Installed profile name
    """
    try:
        import urllib.request
        with urllib.request.urlopen(url) as response:
            profile_data = json.loads(response.read())
        return install_profile(profile_data, name)
    except Exception as e:
        raise ValueError(f"Failed to download profile: {e}")


def install_profile_from_file(path: str, name: Optional[str] = None) -> str:
    """
    Install a profile from a local file
    
    Args:
        path: Path to JSON profile file
        name: Optional name override
    
    Returns:
        Installed profile name
    """
    with open(path, 'r') as f:
        profile_data = json.load(f)
    return install_profile(profile_data, name)


def print_profile_list(show_validation: bool = False):
    """Print formatted list of available profiles"""
    profiles = list_profiles()
    
    if not profiles:
        print("No profiles available.", file=sys.stderr)
        return
    
    print("Available profiles:\n", file=sys.stderr)
    
    for name, profile in sorted(profiles.items()):
        builtin = " [built-in]" if name in BUILTIN_PROFILES else " [user]"
        desc = profile.get('description', 'No description')
        pattern = profile.get('pattern', 'No pattern')
        
        print(f"  {name}{builtin}", file=sys.stderr)
        print(f"    {desc}", file=sys.stderr)
        print(f"    Pattern: {pattern}", file=sys.stderr)
        
        if show_validation:
            validation = profile.get('validation', {})
            if validation:
                f1 = validation.get('f1_score', 0)
                runs = validation.get('tested_runs', 0)
                rec = profile.get('recommendation', 'UNKNOWN')
                print(f"    F1: {f1:.2f} | Runs: {runs} | {rec}", file=sys.stderr)
        
        print(file=sys.stderr)


def print_profile_details(name: str):
    """Print detailed information about a profile"""
    profile = get_profile(name)
    
    if not profile:
        print(f"❌ Profile '{name}' not found", file=sys.stderr)
        print("\nAvailable profiles:", file=sys.stderr)
        print_profile_list()
        sys.exit(1)
    
    builtin = " (built-in)" if name in BUILTIN_PROFILES else " (user-installed)"
    
    print(f"\n📋 Profile: {name}{builtin}\n", file=sys.stderr)
    print(f"Description: {profile.get('description', 'N/A')}", file=sys.stderr)
    print(f"Pattern: {profile.get('pattern', 'N/A')}", file=sys.stderr)
    
    print(f"\nOptions:", file=sys.stderr)
    options = profile.get('options', {})
    for key, value in options.items():
        print(f"  --{key.replace('_', '-')}: {value}", file=sys.stderr)
    
    validation = profile.get('validation', {})
    if validation:
        print(f"\nValidation:", file=sys.stderr)
        print(f"  Precision: {validation.get('precision', 0):.2%}", file=sys.stderr)
        print(f"  Recall: {validation.get('recall', 0):.2%}", file=sys.stderr)
        print(f"  F1 Score: {validation.get('f1_score', 0):.2%}", file=sys.stderr)
        print(f"  Tested on: {validation.get('tested_runs', 0)} runs", file=sys.stderr)
    
    recommendation = profile.get('recommendation', 'UNKNOWN')
    print(f"\nRecommendation: {recommendation}", file=sys.stderr)
    
    notes = profile.get('notes', [])
    if notes:
        print(f"\nNotes:", file=sys.stderr)
        for note in notes:
            print(f"  • {note}", file=sys.stderr)
    
    print(f"\nUsage:", file=sys.stderr)
    print(f"  earlyexit --profile {name} your-command", file=sys.stderr)
    print()


def apply_profile_to_args(profile: Dict[str, Any], args):
    """
    Apply profile settings to argparse namespace
    
    Applies ALL profile options that map to CLI flags. User's explicit
    command-line arguments always take precedence over profile defaults.
    
    Args:
        profile: Profile dictionary
        args: argparse Namespace object
    
    Returns:
        Modified args
    """
    # Apply pattern if not already set
    if not args.pattern:
        args.pattern = profile.get('pattern')
    
    # Apply options if not already set
    options = profile.get('options', {})
    
    # Map of profile option names to argparse attribute names
    # (handles underscores vs dashes, special cases)
    option_mapping = {
        # Timeouts
        'timeout': 'timeout',
        'overall_timeout': 'timeout',
        'idle_timeout': 'idle_timeout',
        'first_output_timeout': 'first_output_timeout',
        
        # Delay exit
        'delay_exit': 'delay_exit',
        'delay_exit_after_lines': 'delay_exit_after_lines',
        
        # Match behavior
        'max_count': 'max_count',
        'ignore_case': 'ignore_case',
        'case_insensitive': 'ignore_case',  # Alias
        'perl_regexp': 'perl_regexp',
        'extended_regexp': 'extended_regexp',
        'invert_match': 'invert_match',
        
        # Output control
        'quiet': 'quiet',
        'verbose': 'verbose',
        'line_number': 'line_number',
        'color': 'color',
        
        # Stream selection
        'match_stderr': 'match_stderr',  # 'both', 'stdout', 'stderr'
        'stdout': 'match_stderr',  # If true, set to 'stdout'
        'stderr': 'match_stderr',  # If true, set to 'stderr'
        
        # FD monitoring
        'monitor_fds': 'monitor_fds',  # List of FD numbers
        'fd_prefix': 'fd_prefix',
        'stderr_prefix': 'fd_prefix',  # Alias
        
        # Advanced
        'source_file': 'source_file',
        'no_telemetry': 'no_telemetry',
    }
    
    for profile_key, value in options.items():
        # Get the argparse attribute name
        arg_key = option_mapping.get(profile_key, profile_key)
        
        # Special handling for stdout/stderr options
        if profile_key == 'stdout' and value is True:
            if not hasattr(args, 'match_stderr') or getattr(args, 'match_stderr') == 'both':
                setattr(args, 'match_stderr', 'stdout')
            continue
        elif profile_key == 'stderr' and value is True:
            if not hasattr(args, 'match_stderr') or getattr(args, 'match_stderr') == 'both':
                setattr(args, 'match_stderr', 'stderr')
            continue
        
        # Apply if not already set by user
        if not hasattr(args, arg_key):
            setattr(args, arg_key, value)
        elif getattr(args, arg_key) is None:
            setattr(args, arg_key, value)
        elif isinstance(getattr(args, arg_key), bool) and not getattr(args, arg_key):
            # For boolean flags, only apply if currently False
            if value:
                setattr(args, arg_key, value)
    
    # Handle fd_patterns specially (list of tuples)
    if 'fd_patterns' in options:
        if not hasattr(args, 'fd_patterns') or not args.fd_patterns:
            args.fd_patterns = options['fd_patterns']
    
    return args


def create_quickstart_profile(tool: str, pattern: str, **kwargs) -> Dict[str, Any]:
    """
    Create a quickstart profile from basic parameters
    
    Args:
        tool: Tool name (e.g., 'my-npm-project')
        pattern: Regex pattern
        **kwargs: Additional options
    
    Returns:
        Profile dictionary
    """
    return {
        "name": tool,
        "description": kwargs.get('description', f'Custom profile for {tool}'),
        "pattern": pattern,
        "options": {
            "delay_exit": kwargs.get('delay_exit', 10),
            "idle_timeout": kwargs.get('idle_timeout', 30),
            "overall_timeout": kwargs.get('overall_timeout', 1800),
        },
        "validation": kwargs.get('validation', {}),
        "recommendation": kwargs.get('recommendation', 'CUSTOM'),
        "notes": kwargs.get('notes', [])
    }


if __name__ == '__main__':
    # CLI for profile management
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage earlyexit profiles')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # List profiles
    list_parser = subparsers.add_parser('list', help='List available profiles')
    list_parser.add_argument('--validation', action='store_true',
                            help='Show validation metrics')
    
    # Show profile details
    show_parser = subparsers.add_parser('show', help='Show profile details')
    show_parser.add_argument('name', help='Profile name')
    
    # Install profile
    install_parser = subparsers.add_parser('install', help='Install a profile')
    install_parser.add_argument('source', help='URL or file path')
    install_parser.add_argument('--name', help='Profile name')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        print_profile_list(show_validation=args.validation)
    elif args.command == 'show':
        print_profile_details(args.name)
    elif args.command == 'install':
        if args.source.startswith('http://') or args.source.startswith('https://'):
            name = install_profile_from_url(args.source, args.name)
        else:
            name = install_profile_from_file(args.source, args.name)
        print(f"✅ Profile '{name}' installed successfully")
    else:
        parser.print_help()


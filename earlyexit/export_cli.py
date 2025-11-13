#!/usr/bin/env python3
"""
CLI commands for exporting/importing learned settings

Usage:
    earlyexit-export [--mask-sensitive] [--format json] > settings.json
    earlyexit-import settings.json
"""

import sys
import json
import argparse
from typing import List, Dict, Any
from pathlib import Path


def export_learned_settings(mask_sensitive: bool = True, 
                            format_type: str = 'json',
                            project_type: str = None) -> str:
    """
    Export learned settings to JSON
    
    Args:
        mask_sensitive: If True, mask sensitive features
        format_type: Output format (currently only 'json')
        project_type: Filter by project type (optional)
    
    Returns:
        JSON string
    """
    from earlyexit.telemetry import get_telemetry
    import sqlite3
    import os
    
    telemetry = get_telemetry()
    if not telemetry or not telemetry.enabled:
        print("❌ Telemetry is disabled. No settings to export.", file=sys.stderr)
        return json.dumps({'error': 'Telemetry disabled'})
    
    db_path = os.path.expanduser("~/.earlyexit/telemetry.db")
    if not Path(db_path).exists():
        print("❌ No telemetry database found.", file=sys.stderr)
        return json.dumps({'error': 'No database'})
    
    # Query all learned settings
    settings = []
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        query = """
            SELECT 
                setting_id, command_hash, project_type,
                features_json,
                learned_pattern, pattern_confidence,
                learned_timeout, learned_idle_timeout, learned_delay_exit,
                true_positives, true_negatives, false_positives, false_negatives,
                user_confirmed_good, user_rejected,
                times_used, last_used_timestamp, created_timestamp,
                is_active
            FROM learned_settings
            WHERE is_active = 1
        """
        
        params = []
        if project_type:
            query += " AND project_type = ?"
            params.append(project_type)
        
        query += " ORDER BY last_used_timestamp DESC"
        
        cursor.execute(query, params)
        
        for row in cursor.fetchall():
            features = json.loads(row[3]) if row[3] else {}
            
            # Mask sensitive features if requested
            if mask_sensitive:
                for feat_name, feat_data in features.items():
                    if feat_data.get('sensitivity') == 'sensitive':
                        feat_data['value'] = '<masked>'
                    elif feat_data.get('sensitivity') == 'private':
                        import hashlib
                        feat_data['value'] = hashlib.sha256(str(feat_data['value']).encode()).hexdigest()[:16]
            
            # Calculate validation metrics
            from earlyexit.features import ValidationMetrics
            metrics = ValidationMetrics(
                true_positives=row[9],
                true_negatives=row[10],
                false_positives=row[11],
                false_negatives=row[12],
                user_confirmed_good=row[13],
                user_rejected=row[14]
            )
            
            recommendation = metrics.get_recommendation()
            
            setting = {
                'setting_id': row[0],
                'command_hash': row[1] if not mask_sensitive else row[1][:8] + '...',
                'project_type': row[2],
                'features': features,
                'learned_parameters': {
                    'pattern': row[4] if not mask_sensitive else '<masked>',
                    'pattern_confidence': round(row[5], 3) if row[5] else 0.0,
                    'timeout': row[6],
                    'idle_timeout': row[7],
                    'delay_exit': row[8]
                },
                'validation': {
                    'counts': {
                        'true_positives': row[9],
                        'true_negatives': row[10],
                        'false_positives': row[11],
                        'false_negatives': row[12],
                        'total_runs': metrics.total_runs
                    },
                    'metrics': {
                        'precision': round(metrics.precision, 3),
                        'recall': round(metrics.recall, 3),
                        'accuracy': round(metrics.accuracy, 3),
                        'f1_score': round(metrics.f1_score, 3),
                        'user_satisfaction': round(metrics.user_satisfaction, 3)
                    },
                    'user_feedback': {
                        'confirmed_good': row[13],
                        'rejected': row[14]
                    }
                },
                'recommendation': recommendation,
                'metadata': {
                    'times_used': row[15],
                    'last_used': row[16],
                    'created': row[17]
                }
            }
            
            settings.append(setting)
    
    output = {
        'version': '1.0',
        'export_timestamp': __import__('time').time(),
        'total_settings': len(settings),
        'masked_sensitive': mask_sensitive,
        'settings': settings
    }
    
    return json.dumps(output, indent=2)


def import_learned_settings(json_data: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    Import learned settings from JSON
    
    Args:
        json_data: JSON string with settings
        dry_run: If True, validate but don't save
    
    Returns:
        Import result summary
    """
    from earlyexit.telemetry import get_telemetry
    
    telemetry = get_telemetry()
    if not telemetry or not telemetry.enabled:
        return {'error': 'Telemetry disabled', 'imported': 0}
    
    data = json.loads(json_data)
    
    if data.get('version') != '1.0':
        return {'error': f"Unsupported version: {data.get('version')}", 'imported': 0}
    
    settings = data.get('settings', [])
    imported = 0
    skipped = 0
    errors = []
    
    for setting in settings:
        if dry_run:
            # Just validate
            imported += 1
            continue
        
        try:
            setting_data = {
                'command_hash': setting['command_hash'],
                'project_type': setting['project_type'],
                'features': setting.get('features', {}),
                'learned_pattern': setting['learned_parameters'].get('pattern'),
                'pattern_confidence': setting['learned_parameters'].get('pattern_confidence', 0.0),
                'learned_timeout': setting['learned_parameters'].get('timeout'),
                'learned_idle_timeout': setting['learned_parameters'].get('idle_timeout'),
                'learned_delay_exit': setting['learned_parameters'].get('delay_exit')
            }
            
            telemetry.save_learned_setting(setting_data)
            imported += 1
            
        except Exception as e:
            skipped += 1
            errors.append(f"Setting {setting.get('setting_id', 'unknown')}: {str(e)}")
    
    return {
        'imported': imported,
        'skipped': skipped,
        'errors': errors,
        'total': len(settings)
    }


def main_export():
    """Main entry point for earlyexit-export"""
    parser = argparse.ArgumentParser(
        description='Export learned settings from earlyexit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Export with sensitive data masked (for community sharing)
    earlyexit-export --mask-sensitive > my-settings.json
    
    # Export private settings (for personal backup)
    earlyexit-export --no-mask > my-private-settings.json
    
    # Export only Python project settings
    earlyexit-export --project-type python > python-settings.json
        """
    )
    
    parser.add_argument(
        '--mask-sensitive',
        action='store_true',
        default=True,
        help='Mask sensitive features (default: True)'
    )
    
    parser.add_argument(
        '--no-mask',
        action='store_true',
        help='Do not mask sensitive features'
    )
    
    parser.add_argument(
        '--project-type',
        type=str,
        default=None,
        help='Filter by project type (python, node, etc.)'
    )
    
    parser.add_argument(
        '--format',
        type=str,
        default='json',
        choices=['json'],
        help='Output format (default: json)'
    )
    
    args = parser.parse_args()
    
    mask = args.mask_sensitive and not args.no_mask
    
    result = export_learned_settings(
        mask_sensitive=mask,
        format_type=args.format,
        project_type=args.project_type
    )
    
    print(result)


def main_import():
    """Main entry point for earlyexit-import"""
    parser = argparse.ArgumentParser(
        description='Import learned settings into earlyexit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Import settings from file
    earlyexit-import my-settings.json
    
    # Dry run (validate without importing)
    earlyexit-import --dry-run my-settings.json
    
    # Import from stdin
    cat my-settings.json | earlyexit-import -
        """
    )
    
    parser.add_argument(
        'file',
        type=str,
        help='JSON file to import (use "-" for stdin)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate without importing'
    )
    
    args = parser.parse_args()
    
    # Read input
    if args.file == '-':
        json_data = sys.stdin.read()
    else:
        with open(args.file, 'r') as f:
            json_data = f.read()
    
    # Import
    result = import_learned_settings(json_data, dry_run=args.dry_run)
    
    # Display results
    if 'error' in result:
        print(f"❌ Error: {result['error']}", file=sys.stderr)
        sys.exit(1)
    
    if args.dry_run:
        print(f"✅ Validation successful:", file=sys.stderr)
        print(f"   {result['total']} settings would be imported", file=sys.stderr)
    else:
        print(f"✅ Import complete:", file=sys.stderr)
        print(f"   Imported: {result['imported']}", file=sys.stderr)
        if result['skipped'] > 0:
            print(f"   Skipped: {result['skipped']}", file=sys.stderr)
        if result['errors']:
            print(f"\n⚠️  Errors:", file=sys.stderr)
            for error in result['errors']:
                print(f"   {error}", file=sys.stderr)


if __name__ == '__main__':
    if 'export' in sys.argv[0]:
        main_export()
    else:
        main_import()


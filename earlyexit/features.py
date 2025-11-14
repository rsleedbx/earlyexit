"""
Feature engineering and ML format for earlyexit

Provides JSON-based feature format compatible with ML systems,
with privacy controls for community sharing.
"""

import json
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class FeatureSensitivity(Enum):
    """Sensitivity level for features"""
    PUBLIC = "public"           # Safe to share (e.g., project type, pattern types)
    PRIVATE = "private"         # Should be hashed (e.g., working directory)
    SENSITIVE = "sensitive"     # Never share (e.g., file paths, custom patterns)


@dataclass
class Feature:
    """Individual feature with metadata"""
    name: str
    value: Any
    sensitivity: FeatureSensitivity = FeatureSensitivity.PUBLIC
    description: Optional[str] = None
    
    def to_dict(self, mask_sensitive: bool = False) -> Dict[str, Any]:
        """Convert to dict, optionally masking sensitive values"""
        if mask_sensitive:
            if self.sensitivity == FeatureSensitivity.SENSITIVE:
                value = "<masked>"
            elif self.sensitivity == FeatureSensitivity.PRIVATE:
                # Hash private values for anonymity but consistency
                value = hashlib.sha256(str(self.value).encode()).hexdigest()[:16]
            else:
                value = self.value
        else:
            value = self.value
        
        return {
            'name': self.name,
            'value': value,
            'sensitivity': self.sensitivity.value,
            'description': self.description
        }


@dataclass
class ValidationMetrics:
    """Validation metrics showing positive and negative outcomes"""
    
    # Positive outcomes (successes)
    true_positives: int = 0      # Pattern matched, was actually an error
    true_negatives: int = 0      # No match, correctly identified non-error
    
    # Negative outcomes (failures)
    false_positives: int = 0     # Pattern matched, but wasn't an error
    false_negatives: int = 0     # Missed error (pattern didn't match)
    
    # Timing outcomes
    avg_detection_time: float = 0.0       # Average time to detect error
    avg_false_alarm_overhead: float = 0.0  # Time wasted on false alarms
    
    # User feedback
    user_confirmed_good: int = 0   # User said "yes, good suggestion"
    user_rejected: int = 0         # User said "no, bad suggestion"
    
    @property
    def total_runs(self) -> int:
        return self.true_positives + self.true_negatives + self.false_positives + self.false_negatives
    
    @property
    def precision(self) -> float:
        """Precision: When we say error, how often is it correct?"""
        tp_fp = self.true_positives + self.false_positives
        return self.true_positives / tp_fp if tp_fp > 0 else 0.0
    
    @property
    def recall(self) -> float:
        """Recall: Of all actual errors, how many did we catch?"""
        tp_fn = self.true_positives + self.false_negatives
        return self.true_positives / tp_fn if tp_fn > 0 else 0.0
    
    @property
    def accuracy(self) -> float:
        """Accuracy: Overall correctness"""
        total = self.total_runs
        return (self.true_positives + self.true_negatives) / total if total > 0 else 0.0
    
    @property
    def f1_score(self) -> float:
        """F1: Harmonic mean of precision and recall"""
        p, r = self.precision, self.recall
        return 2 * (p * r) / (p + r) if (p + r) > 0 else 0.0
    
    @property
    def user_satisfaction(self) -> float:
        """User satisfaction rate"""
        total_feedback = self.user_confirmed_good + self.user_rejected
        return self.user_confirmed_good / total_feedback if total_feedback > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict with computed metrics"""
        return {
            'counts': {
                'true_positives': self.true_positives,
                'true_negatives': self.true_negatives,
                'false_positives': self.false_positives,
                'false_negatives': self.false_negatives,
                'total_runs': self.total_runs
            },
            'metrics': {
                'precision': round(self.precision, 3),
                'recall': round(self.recall, 3),
                'accuracy': round(self.accuracy, 3),
                'f1_score': round(self.f1_score, 3),
                'user_satisfaction': round(self.user_satisfaction, 3)
            },
            'timing': {
                'avg_detection_time_seconds': round(self.avg_detection_time, 2),
                'avg_false_alarm_overhead_seconds': round(self.avg_false_alarm_overhead, 2)
            },
            'user_feedback': {
                'confirmed_good': self.user_confirmed_good,
                'rejected': self.user_rejected
            }
        }
    
    def get_recommendation(self) -> Dict[str, Any]:
        """Get smart recommendation based on validation metrics"""
        
        # Decision thresholds
        MIN_RUNS = 5
        GOOD_PRECISION = 0.80
        GOOD_RECALL = 0.70
        GOOD_F1 = 0.75
        ACCEPTABLE_FALSE_POSITIVE_RATE = 0.10
        
        total = self.total_runs
        fp_rate = self.false_positives / total if total > 0 else 0.0
        
        # Not enough data
        if total < MIN_RUNS:
            return {
                'recommendation': 'COLLECT_MORE_DATA',
                'confidence': 'low',
                'message': f'Only {total} runs recorded. Need at least {MIN_RUNS} to provide reliable recommendations.',
                'should_use': None,
                'reasons': ['Insufficient data for accurate recommendation']
            }
        
        # Excellent performance
        if self.f1_score >= GOOD_F1 and self.precision >= GOOD_PRECISION and fp_rate <= ACCEPTABLE_FALSE_POSITIVE_RATE:
            return {
                'recommendation': 'HIGHLY_RECOMMENDED',
                'confidence': 'high',
                'message': f'Excellent performance! F1={self.f1_score:.2f}, Precision={self.precision:.2f}',
                'should_use': True,
                'reasons': [
                    f'✅ High precision ({self.precision:.1%}) - low false alarms',
                    f'✅ Good recall ({self.recall:.1%}) - catches most errors',
                    f'✅ Low false positive rate ({fp_rate:.1%})',
                    f'✅ F1 score of {self.f1_score:.2f}'
                ]
            }
        
        # Good precision but low recall
        if self.precision >= GOOD_PRECISION and self.recall < GOOD_RECALL:
            return {
                'recommendation': 'USE_WITH_CAUTION',
                'confidence': 'medium',
                'message': f'High precision ({self.precision:.1%}) but misses {(1-self.recall):.1%} of errors',
                'should_use': True,
                'reasons': [
                    f'✅ High precision ({self.precision:.1%}) - reliable when it matches',
                    f'⚠️  Low recall ({self.recall:.1%}) - might miss some errors',
                    f'💡 Consider: Add more patterns or use as backup check'
                ]
            }
        
        # Good recall but low precision (many false alarms)
        if self.recall >= GOOD_RECALL and self.precision < GOOD_PRECISION:
            return {
                'recommendation': 'TUNE_PATTERN',
                'confidence': 'medium',
                'message': f'Catches errors ({self.recall:.1%}) but too many false alarms ({fp_rate:.1%})',
                'should_use': False,
                'reasons': [
                    f'⚠️  Low precision ({self.precision:.1%}) - many false positives',
                    f'✅ Good recall ({self.recall:.1%}) - catches most real errors',
                    f'💡 Action: Refine pattern to be more specific',
                    f'📊 {self.false_positives} false alarms in {total} runs'
                ]
            }
        
        # Poor performance overall
        if self.f1_score < 0.50:
            return {
                'recommendation': 'NOT_RECOMMENDED',
                'confidence': 'high',
                'message': f'Poor performance (F1={self.f1_score:.2f}). Consider different approach.',
                'should_use': False,
                'reasons': [
                    f'❌ Low F1 score ({self.f1_score:.2f})',
                    f'❌ Precision: {self.precision:.1%}',
                    f'❌ Recall: {self.recall:.1%}',
                    f'💡 Try: Different pattern, timeout-only mode, or manual monitoring'
                ]
            }
        
        # Mediocre performance
        return {
            'recommendation': 'NEEDS_IMPROVEMENT',
            'confidence': 'medium',
            'message': f'Moderate performance (F1={self.f1_score:.2f}). Can be improved.',
            'should_use': None,  # User should decide
            'reasons': [
                f'⚠️  Moderate precision ({self.precision:.1%})',
                f'⚠️  Moderate recall ({self.recall:.1%})',
                f'💡 Consider: Refine pattern or collect more training data',
                f'📊 {total} runs recorded'
            ]
        }


@dataclass
class LearnedSetting:
    """Learned setting with features and validation"""
    
    # Identification
    setting_id: str
    command_hash: str
    project_type: str
    
    # Features (ML-friendly format)
    features: Dict[str, Feature]
    
    # Learned parameters
    learned_pattern: Optional[str] = None
    pattern_confidence: float = 0.0
    learned_timeout: Optional[float] = None
    learned_idle_timeout: Optional[float] = None
    learned_delay_exit: Optional[float] = None
    
    # Validation metrics
    validation: Optional[ValidationMetrics] = None
    
    # Metadata
    times_used: int = 0
    last_used_timestamp: float = 0.0
    created_timestamp: float = 0.0
    
    def to_json(self, mask_sensitive: bool = False, include_validation: bool = True) -> str:
        """
        Export to JSON format
        
        Args:
            mask_sensitive: If True, mask sensitive features
            include_validation: If True, include validation metrics
        """
        data = {
            'setting_id': self.setting_id,
            'command_hash': self.command_hash if not mask_sensitive else self.command_hash[:16],
            'project_type': self.project_type,
            
            'features': {
                name: feat.to_dict(mask_sensitive=mask_sensitive)
                for name, feat in self.features.items()
            },
            
            'learned_parameters': {
                'pattern': self.learned_pattern if not mask_sensitive else '<masked>',
                'pattern_confidence': round(self.pattern_confidence, 3),
                'timeout': self.learned_timeout,
                'idle_timeout': self.learned_idle_timeout,
                'delay_exit': self.learned_delay_exit
            },
            
            'metadata': {
                'times_used': self.times_used,
                'last_used': self.last_used_timestamp,
                'created': self.created_timestamp
            }
        }
        
        if include_validation and self.validation:
            data['validation'] = self.validation.to_dict()
            data['recommendation'] = self.validation.get_recommendation()
        
        return json.dumps(data, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'LearnedSetting':
        """Import from JSON format"""
        data = json.loads(json_str)
        
        # Reconstruct features
        features = {}
        for name, feat_data in data.get('features', {}).items():
            features[name] = Feature(
                name=feat_data['name'],
                value=feat_data['value'],
                sensitivity=FeatureSensitivity(feat_data.get('sensitivity', 'public')),
                description=feat_data.get('description')
            )
        
        # Reconstruct validation if present
        validation = None
        if 'validation' in data:
            val_data = data['validation']['counts']
            validation = ValidationMetrics(
                true_positives=val_data['true_positives'],
                true_negatives=val_data['true_negatives'],
                false_positives=val_data['false_positives'],
                false_negatives=val_data['false_negatives']
            )
        
        learned = data.get('learned_parameters', {})
        metadata = data.get('metadata', {})
        
        return cls(
            setting_id=data['setting_id'],
            command_hash=data['command_hash'],
            project_type=data['project_type'],
            features=features,
            learned_pattern=learned.get('pattern'),
            pattern_confidence=learned.get('pattern_confidence', 0.0),
            learned_timeout=learned.get('timeout'),
            learned_idle_timeout=learned.get('idle_timeout'),
            learned_delay_exit=learned.get('delay_exit'),
            validation=validation,
            times_used=metadata.get('times_used', 0),
            last_used_timestamp=metadata.get('last_used', 0.0),
            created_timestamp=metadata.get('created', 0.0)
        )


def extract_features(session_data: Dict[str, Any]) -> Dict[str, Feature]:
    """
    Extract ML features from a user session
    
    Returns dict of feature name -> Feature object
    """
    features = {}
    
    # Project/context features (PUBLIC)
    features['project_type'] = Feature(
        name='project_type',
        value=session_data.get('project_type', 'unknown'),
        sensitivity=FeatureSensitivity.PUBLIC,
        description='Type of project (node, python, etc.)'
    )
    
    # Command features (PRIVATE - hash for anonymity)
    features['command_category'] = Feature(
        name='command_category',
        value=session_data.get('command_category', 'other'),
        sensitivity=FeatureSensitivity.PUBLIC,
        description='Category of command (test, build, etc.)'
    )
    
    # Timing features (PUBLIC - aggregated stats)
    features['duration'] = Feature(
        name='duration',
        value=round(session_data.get('duration', 0.0), 1),
        sensitivity=FeatureSensitivity.PUBLIC,
        description='Command duration in seconds'
    )
    
    features['idle_time'] = Feature(
        name='idle_time',
        value=round(session_data.get('idle_time', 0.0), 1),
        sensitivity=FeatureSensitivity.PUBLIC,
        description='Idle time before interrupt'
    )
    
    # Output features (PUBLIC - counts only)
    line_counts = session_data.get('line_counts', {})
    features['stdout_lines'] = Feature(
        name='stdout_lines',
        value=line_counts.get('stdout', 0),
        sensitivity=FeatureSensitivity.PUBLIC,
        description='Number of stdout lines'
    )
    
    features['stderr_lines'] = Feature(
        name='stderr_lines',
        value=line_counts.get('stderr', 0),
        sensitivity=FeatureSensitivity.PUBLIC,
        description='Number of stderr lines'
    )
    
    features['stderr_ratio'] = Feature(
        name='stderr_ratio',
        value=round(line_counts.get('stderr', 0) / max(line_counts.get('total', 1), 1), 2),
        sensitivity=FeatureSensitivity.PUBLIC,
        description='Ratio of stderr to total output'
    )
    
    # Pattern features (SENSITIVE - user-specific patterns)
    if session_data.get('selected_pattern'):
        features['pattern_type'] = Feature(
            name='pattern_type',
            value='custom' if session_data.get('pattern_stream') == 'custom' else 'suggested',
            sensitivity=FeatureSensitivity.PUBLIC,
            description='Whether pattern was suggested or custom'
        )
        
        features['pattern_stream'] = Feature(
            name='pattern_stream',
            value=session_data.get('pattern_stream', 'both'),
            sensitivity=FeatureSensitivity.PUBLIC,
            description='Which stream(s) pattern applies to'
        )
    
    # Stop reason (PUBLIC)
    features['stop_reason'] = Feature(
        name='stop_reason',
        value=session_data.get('stop_reason', 'unknown'),
        sensitivity=FeatureSensitivity.PUBLIC,
        description='Why user stopped (error/timeout/hang)'
    )
    
    # Working directory (PRIVATE - hash only)
    if session_data.get('working_directory'):
        features['working_directory_hash'] = Feature(
            name='working_directory_hash',
            value=session_data['working_directory'],
            sensitivity=FeatureSensitivity.PRIVATE,
            description='Hashed working directory for consistency'
        )
    
    return features





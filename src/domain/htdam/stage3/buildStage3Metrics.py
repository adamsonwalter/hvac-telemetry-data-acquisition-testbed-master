"""
Stage 3 Domain Function: Build Stage 3 Metrics

Pure function - NO side effects, NO logging, NO I/O.
Constructs Stage 3 metrics JSON output.

Reference: htdam/stage-3-timestamp-sync/HTDAM v2.0 Stage 3_ Timestamp Synchronization.md
"""

from datetime import datetime
from typing import Dict, List
from collections import Counter


def build_stage3_metrics(
    timestamp_start: datetime,
    timestamp_end: datetime,
    grid_points: int,
    t_nominal_seconds: int,
    per_stream_stats: Dict[str, Dict],
    row_classification_counts: Dict[str, int],
    total_grid_points: int,
    jitter_stats: Dict[str, float],
    coverage_penalty: float,
    jitter_penalty: float,
    stage2_confidence: float,
    warnings: List[str],
    errors: List[str],
    halt: bool
) -> Dict:
    """
    Build Stage 3 metrics JSON output.
    
    Assembles all Stage 3 statistics and metadata into the final metrics
    structure conforming to the Stage 3 JSON schema.
    
    Args:
        timestamp_start: Analysis start timestamp
        timestamp_end: Analysis end timestamp
        grid_points: Number of grid points generated
        t_nominal_seconds: Grid step size in seconds
        per_stream_stats: Dict mapping stream_id to alignment statistics:
            {
                'stream_id': {
                    'total_raw_records': int,
                    'aligned_exact_count': int,
                    'aligned_close_count': int,
                    'aligned_interp_count': int,
                    'missing_count': int,
                    'exact_pct': float,
                    'close_pct': float,
                    'interp_pct': float,
                    'missing_pct': float,
                    'mean_align_distance_s': float,
                    'max_align_distance_s': float,
                    'status': str ('OK' | 'PARTIAL' | 'NOT_PROVIDED')
                }
            }
        row_classification_counts: Dict with counts per gap type:
            {
                'VALID_count': int,
                'COV_CONSTANT_count': int,
                'COV_MINOR_count': int,
                'SENSOR_ANOMALY_count': int,
                'EXCLUDED_count': int,
                'GAP_count': int
            }
        total_grid_points: Total grid points (for percentage calculation)
        jitter_stats: Dict with jitter analysis:
            {
                'interval_mean_s': float,
                'interval_std_s': float,
                'interval_cv_pct': float
            }
        coverage_penalty: Coverage-based penalty (-0.10 to 0.0)
        jitter_penalty: Jitter-based penalty
        stage2_confidence: Confidence from Stage 2
        warnings: List of warning messages
        errors: List of error messages
        halt: Whether pipeline should halt
        
    Returns:
        Metrics dict matching Stage 3 JSON schema:
        {
            "stage": "SYNC",
            "timestamp_start": str,
            "timestamp_end": str,
            "grid": {...},
            "per_stream_alignment": {...},
            "row_classification": {...},
            "jitter": {...},
            "penalty": float,
            "stage3_confidence": float,
            "warnings": [...],
            "errors": [...],
            "halt": bool
        }
        
    Example:
        >>> metrics = build_stage3_metrics(
        ...     timestamp_start=datetime(2024, 9, 18, 3, 30, 0),
        ...     timestamp_end=datetime(2025, 9, 19, 3, 15, 0),
        ...     grid_points=35136,
        ...     t_nominal_seconds=900,
        ...     per_stream_stats={'CHWST': {...}},
        ...     row_classification_counts={'VALID_count': 32959, ...},
        ...     total_grid_points=35136,
        ...     jitter_stats={'interval_mean_s': 900.0, ...},
        ...     coverage_penalty=-0.05,
        ...     jitter_penalty=0.0,
        ...     stage2_confidence=0.93,
        ...     warnings=[],
        ...     errors=[],
        ...     halt=False
        ... )
        >>> metrics['stage']
        'SYNC'
        >>> metrics['stage3_confidence']
        0.88  # 0.93 - 0.05
    """
    # Compute total penalty
    total_penalty = coverage_penalty + jitter_penalty
    
    # Compute Stage 3 confidence
    stage3_confidence = stage2_confidence + total_penalty
    
    # Compute row classification percentages
    row_classification = {}
    for key, count in row_classification_counts.items():
        row_classification[key] = count
        # Add percentage version
        pct_key = key.replace('_count', '_pct')
        if total_grid_points > 0:
            pct = (count / total_grid_points) * 100.0
            row_classification[pct_key] = round(pct, 1)
        else:
            row_classification[pct_key] = 0.0
    
    # Add mean and median confidence if we have valid rows
    valid_count = row_classification_counts.get('VALID_count', 0)
    if valid_count > 0:
        # For simplicity, use stage3_confidence as proxy
        # (Hook can compute exact mean/median if needed)
        row_classification['confidence_mean'] = round(stage3_confidence, 2)
        row_classification['confidence_median'] = round(stage3_confidence, 2)
    else:
        row_classification['confidence_mean'] = 0.00
        row_classification['confidence_median'] = 0.00
    
    # Assemble metrics JSON
    metrics = {
        "stage": "SYNC",
        "timestamp_start": timestamp_start.isoformat() if timestamp_start else None,
        "timestamp_end": timestamp_end.isoformat() if timestamp_end else None,
        "grid": {
            "t_nominal_seconds": t_nominal_seconds,
            "grid_points": grid_points,
            "coverage_seconds": grid_points * t_nominal_seconds
        },
        "per_stream_alignment": per_stream_stats,
        "row_classification": row_classification,
        "jitter": jitter_stats,
        "penalties": {
            "coverage_penalty": coverage_penalty,
            "jitter_penalty": jitter_penalty,
            "total_penalty": total_penalty
        },
        "stage3_confidence": round(stage3_confidence, 2),
        "warnings": warnings,
        "errors": errors,
        "halt": halt
    }
    
    return metrics

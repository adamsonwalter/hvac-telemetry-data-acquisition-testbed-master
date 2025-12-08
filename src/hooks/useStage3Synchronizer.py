"""
Stage 3 Orchestration Hook: Timestamp Synchronization

Hook - ALL side effects, logging, error handling.
Orchestrates 8 pure domain functions to synchronize unsynchronized signals.

Reference: htdam/stage-3-timestamp-sync/HTDAM v2.0 Stage 3_ Timestamp Synchronization.md
"""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from collections import Counter
import pandas as pd
import numpy as np

from src.domain.htdam.constants import (
    T_NOMINAL_SECONDS,
    SYNC_TOLERANCE_SECONDS,
    MANDATORY_STREAMS,
    OPTIONAL_STREAMS,
    ALIGN_EXACT,
    ALIGN_CLOSE,
    ALIGN_INTERP,
    ALIGN_MISSING,
    GAP_TYPE_VALID,
    JITTER_CV_TOLERANCE_PCT,
)

# Import domain functions
from src.domain.htdam.stage3.buildMasterGrid import build_master_grid
from src.domain.htdam.stage3.alignStreamToGrid import align_stream_to_grid
from src.domain.htdam.stage3.deriveRowGapTypeAndConfidence import derive_row_gap_type_and_confidence
from src.domain.htdam.stage3.computeCoveragePenalty import compute_coverage_penalty
from src.domain.htdam.stage3.buildStage3AnnotatedDataFrame import build_stage3_annotated_dataframe
from src.domain.htdam.stage3.buildStage3Metrics import build_stage3_metrics

# Configure logger
logger = logging.getLogger(__name__)


def use_stage3_synchronizer(
    signals: Dict[str, pd.DataFrame],
    exclusion_windows: List[Dict],
    stage2_confidence: float,
    t_nominal: int = T_NOMINAL_SECONDS,
    tolerance: int = SYNC_TOLERANCE_SECONDS,
    timestamp_col: str = "timestamp",
    value_col: str = "value"
) -> Tuple[pd.DataFrame, Dict]:
    """
    Orchestrate Stage 3 timestamp synchronization.
    
    This hook orchestrates all Stage 3 domain functions with logging and
    error handling. It creates a uniform master grid and aligns all raw
    streams using nearest-neighbor selection (NO interpolation).
    
    Args:
        signals: Dict mapping signal_id (uppercase) to DataFrame from Stage 2
                Example: {'CHWST': df_chwst, 'CHWRT': df_chwrt, ...}
        exclusion_windows: List of approved exclusion windows from Stage 2
                Example: [{'window_id': 'EXW_001', 'start_ts': ..., 'end_ts': ...}]
        stage2_confidence: Confidence score from Stage 2 (typically 0.90-0.95)
        t_nominal: Grid step size in seconds (default: 900 = 15 minutes)
        tolerance: Maximum alignment distance in seconds (default: 1800 = 30 minutes)
        timestamp_col: Name of timestamp column in DataFrames
        value_col: Name of value column in DataFrames
        
    Returns:
        Tuple of (df_synchronized, metrics):
        - df_synchronized: Synchronized DataFrame with all streams on common grid
        - metrics: Stage 3 metrics JSON dict
        
    Workflow:
        1. Validate inputs (mandatory streams present, valid time range)
        2. Determine time span across all streams
        3. Build master grid
        4. For each stream: align to grid using nearest-neighbor
        5. For each grid row: derive gap type and confidence
        6. Compute jitter statistics
        7. Compute coverage penalty
        8. Build synchronized DataFrame
        9. Build metrics JSON
        10. Check HALT conditions
        
    Error Handling:
        - Missing mandatory streams → HALT
        - Invalid time span (start >= end) → HALT
        - Empty datasets → HALT
        - Entire dataset excluded → HALT
        - Coverage <50% → HALT
        - Sparse streams (>50% missing) → WARNING, continue
        
    Logging:
        - INFO: Grid construction, alignment progress, coverage stats
        - WARNING: Sparse streams, jitter issues, low coverage
        - CRITICAL: HALT conditions
        
    Example:
        >>> signals = {
        ...     'CHWST': df_chwst,  # From Stage 2
        ...     'CHWRT': df_chwrt,
        ...     'CDWRT': df_cdwrt,
        ...     'FLOW': df_flow,
        ...     'POWER': df_power
        ... }
        >>> exclusion_windows = []
        >>> stage2_confidence = 0.93
        >>> df_sync, metrics = use_stage3_synchronizer(
        ...     signals, exclusion_windows, stage2_confidence
        ... )
        >>> metrics['grid']['grid_points']
        35136
        >>> metrics['stage3_confidence']
        0.88
    """
    logger.info("=" * 80)
    logger.info("Stage 3: Timestamp Synchronization - Starting")
    logger.info("=" * 80)
    
    warnings = []
    errors = []
    halt = False
    
    # ========================================================================
    # STEP 1: Validate Inputs
    # ========================================================================
    logger.info("Step 1: Validating inputs...")
    
    # Check mandatory streams present
    missing_mandatory = []
    for stream in MANDATORY_STREAMS:
        if stream not in signals:
            missing_mandatory.append(stream)
    
    if missing_mandatory:
        error_msg = f"HALT: Missing mandatory streams: {missing_mandatory}"
        logger.critical(error_msg)
        errors.append(error_msg)
        halt = True
        
        # Return empty results with HALT
        return pd.DataFrame(), {
            "stage": "SYNC",
            "errors": errors,
            "warnings": warnings,
            "halt": True,
            "stage3_confidence": 0.0
        }
    
    logger.info(f"Mandatory streams present: {MANDATORY_STREAMS}")
    
    # Check which optional streams are available
    available_optional = [s for s in OPTIONAL_STREAMS if s in signals]
    if available_optional:
        logger.info(f"Optional streams present: {available_optional}")
    else:
        logger.warning("No optional streams (FLOW, POWER) provided")
        warnings.append("No optional streams (FLOW, POWER) provided - COP analysis will not be possible")
    
    # ========================================================================
    # STEP 2: Determine Time Span
    # ========================================================================
    logger.info("Step 2: Determining time span...")
    
    t_start = None
    t_end = None
    
    for stream_id, df in signals.items():
        if df.empty:
            logger.warning(f"Stream {stream_id} is empty, skipping")
            continue
        
        stream_start = df[timestamp_col].min()
        stream_end = df[timestamp_col].max()
        
        if t_start is None or stream_start < t_start:
            t_start = stream_start
        if t_end is None or stream_end > t_end:
            t_end = stream_end
    
    if t_start is None or t_end is None:
        error_msg = "HALT: All streams are empty or invalid"
        logger.critical(error_msg)
        errors.append(error_msg)
        
        return pd.DataFrame(), {
            "stage": "SYNC",
            "errors": errors,
            "warnings": warnings,
            "halt": True,
            "stage3_confidence": 0.0
        }
    
    if t_end <= t_start:
        error_msg = f"HALT: Invalid time span: start={t_start}, end={t_end}"
        logger.critical(error_msg)
        errors.append(error_msg)
        
        return pd.DataFrame(), {
            "stage": "SYNC",
            "errors": errors,
            "warnings": warnings,
            "halt": True,
            "stage3_confidence": 0.0
        }
    
    time_span_days = (t_end - t_start).total_seconds() / 86400
    logger.info(f"Time span: {t_start} to {t_end} ({time_span_days:.1f} days)")
    
    # ========================================================================
    # STEP 3: Build Master Grid
    # ========================================================================
    logger.info(f"Step 3: Building master grid (t_nominal={t_nominal}s)...")
    
    try:
        grid = build_master_grid(t_start, t_end, t_nominal)
        M = len(grid)
        logger.info(f"Master grid created: {M} points")
        logger.info(f"Grid start: {grid[0]}")
        logger.info(f"Grid end: {grid[-1]}")
    except Exception as e:
        error_msg = f"HALT: Grid construction failed: {str(e)}"
        logger.critical(error_msg)
        errors.append(error_msg)
        
        return pd.DataFrame(), {
            "stage": "SYNC",
            "errors": errors,
            "warnings": warnings,
            "halt": True,
            "stage3_confidence": 0.0
        }
    
    # ========================================================================
    # STEP 4: Align Each Stream to Grid
    # ========================================================================
    logger.info("Step 4: Aligning streams to grid (nearest-neighbor, O(N+M))...")
    
    aligned_streams = {}
    per_stream_stats = {}
    
    all_streams = MANDATORY_STREAMS + OPTIONAL_STREAMS
    
    for stream_id in all_streams:
        if stream_id not in signals:
            # Stream not provided
            per_stream_stats[stream_id] = {
                'status': 'NOT_PROVIDED',
                'total_raw_records': 0,
                'aligned_exact_count': 0,
                'aligned_close_count': 0,
                'aligned_interp_count': 0,
                'missing_count': M,
                'exact_pct': 0.0,
                'close_pct': 0.0,
                'interp_pct': 0.0,
                'missing_pct': 100.0,
                'mean_align_distance_s': 0.0,
                'max_align_distance_s': 0.0
            }
            continue
        
        df_stream = signals[stream_id]
        N = len(df_stream)
        
        logger.info(f"  Aligning {stream_id}: {N} raw points → {M} grid points")
        
        # Sort by timestamp (should already be sorted from Stage 2)
        df_stream = df_stream.sort_values(timestamp_col).reset_index(drop=True)
        
        # Extract timestamps and values
        timestamps_raw = df_stream[timestamp_col]
        values_raw = df_stream[value_col]
        
        # Call domain function: align_stream_to_grid
        try:
            aligned_values, align_qualities, align_distances = align_stream_to_grid(
                timestamps_raw, values_raw, grid, tolerance
            )
        except Exception as e:
            error_msg = f"Alignment failed for {stream_id}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            continue
        
        # Store aligned stream data
        aligned_streams[stream_id] = {
            'values': aligned_values,
            'qualities': align_qualities,
            'distances': align_distances
        }
        
        # Compute alignment statistics
        quality_counts = Counter(align_qualities)
        exact_count = quality_counts.get(ALIGN_EXACT, 0)
        close_count = quality_counts.get(ALIGN_CLOSE, 0)
        interp_count = quality_counts.get(ALIGN_INTERP, 0)
        missing_count = quality_counts.get(ALIGN_MISSING, 0)
        
        # Compute distances statistics (excluding None)
        valid_distances = [d for d in align_distances if d is not None]
        if valid_distances:
            mean_distance = np.mean(valid_distances)
            max_distance = np.max(valid_distances)
        else:
            mean_distance = 0.0
            max_distance = 0.0
        
        # Determine status
        missing_pct = (missing_count / M) * 100.0
        if missing_pct > 50.0:
            status = 'PARTIAL'
            warning_msg = f"{stream_id}: {missing_pct:.1f}% missing (sparse data)"
            logger.warning(warning_msg)
            warnings.append(warning_msg)
        else:
            status = 'OK'
        
        per_stream_stats[stream_id] = {
            'status': status,
            'total_raw_records': N,
            'aligned_exact_count': exact_count,
            'aligned_close_count': close_count,
            'aligned_interp_count': interp_count,
            'missing_count': missing_count,
            'exact_pct': round((exact_count / M) * 100.0, 1),
            'close_pct': round((close_count / M) * 100.0, 1),
            'interp_pct': round((interp_count / M) * 100.0, 1),
            'missing_pct': round(missing_pct, 1),
            'mean_align_distance_s': round(mean_distance, 1),
            'max_align_distance_s': round(max_distance, 1)
        }
        
        logger.info(f"    EXACT: {exact_count} ({per_stream_stats[stream_id]['exact_pct']}%)")
        logger.info(f"    CLOSE: {close_count} ({per_stream_stats[stream_id]['close_pct']}%)")
        logger.info(f"    INTERP: {interp_count} ({per_stream_stats[stream_id]['interp_pct']}%)")
        logger.info(f"    MISSING: {missing_count} ({per_stream_stats[stream_id]['missing_pct']}%)")
    
    # ========================================================================
    # STEP 5: Derive Row-Level Gap Type and Confidence
    # ========================================================================
    logger.info("Step 5: Deriving row-level gap types and confidence...")
    
    row_gap_types = []
    row_confidences = []
    row_exclusion_window_ids = []
    
    # Create exclusion window lookup (grid_time → window_id)
    exclusion_lookup = {}
    for window in exclusion_windows:
        start_ts = window['start_ts']
        end_ts = window['end_ts']
        window_id = window['window_id']
        
        for k, g in enumerate(grid):
            if start_ts <= g <= end_ts:
                exclusion_lookup[k] = window_id
    
    for k in range(M):
        # Build align_qualities dict for this row
        align_qualities_row = {}
        for stream_id in all_streams:
            if stream_id in aligned_streams:
                align_qualities_row[stream_id] = aligned_streams[stream_id]['qualities'][k]
        
        # Check exclusion window
        exclusion_id = exclusion_lookup.get(k, None)
        
        # Call domain function: derive_row_gap_type_and_confidence
        gap_type, confidence = derive_row_gap_type_and_confidence(
            align_qualities_row,
            exclusion_id,
            stage2_semantic=None  # TODO: lookup from Stage 2 if needed
        )
        
        row_gap_types.append(gap_type)
        row_confidences.append(confidence)
        row_exclusion_window_ids.append(exclusion_id)
    
    # Count row classifications
    row_classification_counts = Counter(row_gap_types)
    valid_count = row_classification_counts.get(GAP_TYPE_VALID, 0)
    coverage_pct = (valid_count / M) * 100.0
    
    logger.info(f"Row classification summary:")
    for gap_type, count in row_classification_counts.most_common():
        pct = (count / M) * 100.0
        logger.info(f"  {gap_type}: {count} ({pct:.1f}%)")
    logger.info(f"Coverage: {coverage_pct:.1f}% VALID")
    
    # ========================================================================
    # STEP 6: Compute Jitter Statistics
    # ========================================================================
    logger.info("Step 6: Computing jitter statistics...")
    
    # Grid should have perfectly uniform intervals
    if M > 1:
        intervals = []
        for i in range(1, M):
            dt = (grid[i] - grid[i-1]).total_seconds()
            intervals.append(dt)
        
        interval_mean = np.mean(intervals)
        interval_std = np.std(intervals)
        interval_cv_pct = (interval_std / interval_mean * 100.0) if interval_mean > 0 else 0.0
    else:
        interval_mean = 0.0
        interval_std = 0.0
        interval_cv_pct = 0.0
    
    jitter_stats = {
        'interval_mean_s': round(interval_mean, 1),
        'interval_std_s': round(interval_std, 3),
        'interval_cv_pct': round(interval_cv_pct, 2)
    }
    
    logger.info(f"Jitter: mean={jitter_stats['interval_mean_s']}s, std={jitter_stats['interval_std_s']}s, CV={jitter_stats['interval_cv_pct']}%")
    
    # Check jitter tolerance
    jitter_penalty = 0.0
    if interval_cv_pct > JITTER_CV_TOLERANCE_PCT:
        jitter_penalty = -0.02
        warning_msg = f"High jitter detected: CV={interval_cv_pct:.2f}% (tolerance={JITTER_CV_TOLERANCE_PCT}%)"
        logger.warning(warning_msg)
        warnings.append(warning_msg)
    
    # ========================================================================
    # STEP 7: Compute Coverage Penalty
    # ========================================================================
    logger.info("Step 7: Computing coverage penalty...")
    
    # Call domain function: compute_coverage_penalty
    coverage_penalty = compute_coverage_penalty(coverage_pct)
    logger.info(f"Coverage penalty: {coverage_penalty}")
    
    # Check for catastrophic coverage
    if coverage_pct < 50.0:
        error_msg = f"HALT: Coverage too low ({coverage_pct:.1f}%) - unreliable for analysis"
        logger.critical(error_msg)
        errors.append(error_msg)
        halt = True
    
    # Check if entire dataset excluded
    excluded_count = row_classification_counts.get('EXCLUDED', 0)
    if excluded_count == M:
        error_msg = "HALT: Entire dataset excluded by exclusion windows"
        logger.critical(error_msg)
        errors.append(error_msg)
        halt = True
    
    # ========================================================================
    # STEP 8: Build Synchronized DataFrame
    # ========================================================================
    logger.info("Step 8: Building synchronized DataFrame...")
    
    try:
        # Call domain function: build_stage3_annotated_dataframe
        df_sync = build_stage3_annotated_dataframe(
            grid,
            aligned_streams,
            row_gap_types,
            row_confidences,
            row_exclusion_window_ids
        )
        logger.info(f"Synchronized DataFrame created: {len(df_sync)} rows × {len(df_sync.columns)} columns")
    except Exception as e:
        error_msg = f"HALT: DataFrame construction failed: {str(e)}"
        logger.critical(error_msg)
        errors.append(error_msg)
        halt = True
        
        return pd.DataFrame(), {
            "stage": "SYNC",
            "errors": errors,
            "warnings": warnings,
            "halt": True,
            "stage3_confidence": 0.0
        }
    
    # ========================================================================
    # STEP 9: Build Metrics JSON
    # ========================================================================
    logger.info("Step 9: Building metrics JSON...")
    
    # Call domain function: build_stage3_metrics
    metrics = build_stage3_metrics(
        timestamp_start=t_start,
        timestamp_end=t_end,
        grid_points=M,
        t_nominal_seconds=t_nominal,
        per_stream_stats=per_stream_stats,
        row_classification_counts=dict(row_classification_counts),
        total_grid_points=M,
        jitter_stats=jitter_stats,
        coverage_penalty=coverage_penalty,
        jitter_penalty=jitter_penalty,
        stage2_confidence=stage2_confidence,
        warnings=warnings,
        errors=errors,
        halt=halt
    )
    
    logger.info(f"Stage 3 confidence: {metrics['stage3_confidence']}")
    
    # ========================================================================
    # STEP 10: Final Status
    # ========================================================================
    if halt:
        logger.critical("=" * 80)
        logger.critical("Stage 3: HALT - Cannot proceed to Stage 4")
        logger.critical(f"Errors: {errors}")
        logger.critical("=" * 80)
    else:
        logger.info("=" * 80)
        logger.info("Stage 3: Timestamp Synchronization - Complete")
        logger.info(f"Grid: {M} points, Coverage: {coverage_pct:.1f}%, Confidence: {metrics['stage3_confidence']}")
        if warnings:
            logger.info(f"Warnings: {len(warnings)}")
        logger.info("=" * 80)
    
    return df_sync, metrics

"""
Stage 2 Orchestration Hook: Gap Detection & Classification

Hook with side effects - logging, error handling, orchestration.
Runs gap analysis on unsynchronized signals BEFORE Stage 3 synchronization.

Reference: htdam/stage-3-timestamp-sync/HTDAM_Reorder_Gap-First.md
"""

import logging
import pandas as pd
from typing import Dict, Tuple, List
from collections import Counter

from src.domain.htdam.stage2.computeInterSampleIntervals import compute_inter_sample_intervals
from src.domain.htdam.stage2.classifyGap import classify_gap
from src.domain.htdam.stage2.detectGapSemantic import detect_gap_semantic
from src.domain.htdam.stage2.validatePhysicsAtGap import validate_physics_at_gap
from src.domain.htdam.stage2.detectExclusionWindowCandidates import detect_exclusion_window_candidates
from src.domain.htdam.stage2.computeGapPenalties import compute_gap_penalties
from src.domain.htdam.stage2.buildStage2AnnotatedDataFrame import build_stage2_annotated_dataframe
from src.domain.htdam.stage2.buildStage2Metrics import build_stage2_metrics
from src.domain.htdam.constants import (
    T_NOMINAL_SECONDS,
    GAP_CLASS_NORMAL,
    GAP_CLASS_MINOR,
    GAP_CLASS_MAJOR,
)

logger = logging.getLogger(__name__)


def use_stage2_gap_detector(
    signals: Dict[str, pd.DataFrame],
    stage1_confidence: float = 1.0,
    t_nominal: float = T_NOMINAL_SECONDS,
    timestamp_col: str = "timestamp",
    value_col: str = "value"
) -> Tuple[Dict[str, pd.DataFrame], Dict]:
    """
    Stage 2 Hook: Detect and classify gaps in unsynchronized signals.
    
    This hook runs BEFORE Stage 3 synchronization to preserve COV semantics.
    
    Args:
        signals: Dict mapping signal_id (e.g., "CHWST") to DataFrame with columns:
                 - timestamp: Unix epoch seconds or datetime
                 - value: Signal value (temperatures in °C, flow in m³/s, power in kW)
                 - (other Stage 1 columns like unit_confidence, etc.)
        stage1_confidence: Confidence from Stage 1 (default: 1.0)
        t_nominal: Nominal interval in seconds (default: 900 = 15 min)
        timestamp_col: Name of timestamp column
        value_col: Name of value column
        
    Returns:
        Tuple of:
        - gap_annotated_signals: Dict[signal_id, DataFrame] with 6 new gap metadata columns
        - metrics: Stage 2 metrics dict with gap summary, exclusion windows, confidence
        
    Side effects:
        - Logs gap detection progress, warnings, errors
        - Logs human approval decision point if exclusion windows detected
        
    Example:
        >>> signals = {
        ...     "CHWST": pd.DataFrame({"timestamp": [...], "value": [...]}),
        ...     "CHWRT": pd.DataFrame({"timestamp": [...], "value": [...]})
        ... }
        >>> annotated_signals, metrics = use_stage2_gap_detector(signals)
        >>> metrics["stage2_confidence"]
        0.93
        >>> metrics["human_approval_required"]
        True
    """
    logger.info(f"Stage 2: Gap detection starting on {len(signals)} signals")
    
    # Per-signal analysis
    per_signal_summaries = {}
    per_signal_gaps = {}
    gap_annotated_signals = {}
    warnings = []
    errors = []
    
    for signal_id, df in signals.items():
        try:
            logger.info(f"  Analyzing {signal_id}: {len(df)} records")
            
            # 1. Compute inter-sample intervals
            intervals, sorted_values = compute_inter_sample_intervals(
                timestamps=df[timestamp_col],
                values=df[value_col]
            )
            
            if len(intervals) == 0:
                warnings.append(f"{signal_id}: No intervals (single point or empty)")
                continue
            
            # 2. Classify gaps
            gap_classes = [classify_gap(interval, t_nominal) for interval in intervals]
            
            # 3. Detect gap semantics
            gap_semantics = []
            value_changes_pct = []
            
            for i in range(len(intervals)):
                value_before = sorted_values.iloc[i]
                value_after = sorted_values.iloc[i + 1]
                gap_class = gap_classes[i]
                
                semantic = detect_gap_semantic(value_before, value_after, gap_class)
                gap_semantics.append(semantic)
                
                # Compute relative change
                if abs(value_before) > 1e-6:
                    rel_change = abs(value_after - value_before) / abs(value_before) * 100.0
                else:
                    rel_change = 0.0
                value_changes_pct.append(rel_change)
            
            # 4. Physics validation (for temperature signals)
            # Note: Would need cross-signal access for full physics validation
            # For now, just track gaps for exclusion window detection
            
            # 5. Build gap summary for this signal
            gap_class_counts = Counter(gap_classes)
            gap_semantic_counts = Counter(gap_semantics)
            
            total_intervals = len(intervals)
            interval_stats = {
                "normal_count": gap_class_counts.get(GAP_CLASS_NORMAL, 0),
                "normal_pct": gap_class_counts.get(GAP_CLASS_NORMAL, 0) / total_intervals * 100.0,
                "minor_gap_count": gap_class_counts.get(GAP_CLASS_MINOR, 0),
                "minor_gap_pct": gap_class_counts.get(GAP_CLASS_MINOR, 0) / total_intervals * 100.0,
                "major_gap_count": gap_class_counts.get(GAP_CLASS_MAJOR, 0),
                "major_gap_pct": gap_class_counts.get(GAP_CLASS_MAJOR, 0) / total_intervals * 100.0,
            }
            
            # Compute stream penalty
            stream_penalty = compute_gap_penalties(gap_semantics)
            stream_confidence = stage1_confidence + stream_penalty
            
            per_signal_summaries[signal_id] = {
                "total_records": len(df),
                "total_intervals": total_intervals,
                "interval_stats": interval_stats,
                "gap_semantics": gap_semantic_counts,
                "stream_penalty": stream_penalty,
                "stream_confidence": stream_confidence,
            }
            
            # Store gaps for exclusion window detection
            gaps_list = []
            sorted_timestamps = df[timestamp_col].sort_values().values
            
            for i in range(len(intervals)):
                if gap_classes[i] != GAP_CLASS_NORMAL:
                    gaps_list.append({
                        "gap_class": gap_classes[i],
                        "start_ts": sorted_timestamps[i],
                        "end_ts": sorted_timestamps[i + 1],
                        "duration_seconds": intervals.iloc[i],
                        "gap_semantic": gap_semantics[i],
                    })
            
            per_signal_gaps[signal_id] = gaps_list
            
            # 6. Build annotated DataFrame (temporary - no exclusion windows yet)
            # We'll update this after detecting exclusion windows
            gap_confidences = [0.95] * len(intervals)  # Placeholder
            
            df_annotated = build_stage2_annotated_dataframe(
                df=df,
                intervals=intervals,
                gap_classes=gap_classes,
                gap_semantics=gap_semantics,
                gap_confidences=gap_confidences,
                value_changes_pct=value_changes_pct,
                exclusion_windows=[],  # Will update after detection
                timestamp_col=timestamp_col
            )
            
            gap_annotated_signals[signal_id] = df_annotated
            
            logger.info(
                f"    {signal_id}: {interval_stats['normal_pct']:.1f}% NORMAL, "
                f"{interval_stats['minor_gap_pct']:.1f}% MINOR, "
                f"{interval_stats['major_gap_pct']:.1f}% MAJOR"
            )
            logger.info(
                f"    Semantics: {dict(gap_semantic_counts)}"
            )
            
        except Exception as e:
            error_msg = f"{signal_id}: Gap analysis failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            continue
    
    # 7. Detect exclusion windows (multi-stream analysis)
    logger.info("  Detecting exclusion windows (multi-stream MAJOR_GAPs)")
    exclusion_windows = detect_exclusion_window_candidates(per_signal_gaps)
    
    if exclusion_windows:
        logger.info(f"  Found {len(exclusion_windows)} exclusion window(s):")
        for window in exclusion_windows:
            logger.info(
                f"    {window['window_id']}: {window['duration_hours']:.1f} hours, "
                f"affecting {window['affecting_streams']}"
            )
        logger.warning("  ⚠️  HUMAN APPROVAL REQUIRED for exclusion windows")
    else:
        logger.info("  No exclusion windows detected")
    
    # 8. Update annotated DataFrames with exclusion window IDs
    for signal_id, df_annotated in gap_annotated_signals.items():
        if exclusion_windows:
            # Re-mark exclusion windows in annotated DataFrames
            timestamps = df_annotated[timestamp_col].values
            exclusion_ids = [None] * len(df_annotated)
            
            for window in exclusion_windows:
                if signal_id in window["affecting_streams"]:
                    window_id = window["window_id"]
                    start_ts = window["start_ts"]
                    end_ts = window["end_ts"]
                    
                    for i, ts in enumerate(timestamps):
                        if start_ts <= ts <= end_ts:
                            exclusion_ids[i] = window_id
            
            df_annotated["exclusion_window_id"] = exclusion_ids
    
    # 9. Compute aggregate penalty and build metrics
    aggregate_penalty = sum(s["stream_penalty"] for s in per_signal_summaries.values())
    
    if not per_signal_summaries:
        warnings.append("No signals successfully analyzed")
        aggregate_penalty = 0.0
    
    metrics = build_stage2_metrics(
        per_signal_summaries=per_signal_summaries,
        exclusion_windows=exclusion_windows,
        stage1_confidence=stage1_confidence,
        aggregate_penalty=aggregate_penalty,
        warnings=warnings,
        errors=errors
    )
    
    logger.info(
        f"Stage 2 complete: confidence={metrics['stage2_confidence']:.3f} "
        f"(penalty={aggregate_penalty:.3f})"
    )
    
    if metrics["human_approval_required"]:
        logger.warning(
            "⚠️  Pipeline paused: Human approval required for exclusion windows"
        )
    
    return gap_annotated_signals, metrics

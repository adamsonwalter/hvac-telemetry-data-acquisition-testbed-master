"""
Stage 2 Domain Function: Build Annotated DataFrame

Pure function - NO side effects, NO logging, NO I/O.
Adds gap analysis metadata columns to the original signal DataFrame.

Reference: htdam/stage-2-gap-detection/HTAM Stage 2/HTDAM_Stage2_Impl_Guide.md
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from src.domain.htdam.constants import (
    COL_GAP_BEFORE_DURATION_S,
    COL_GAP_BEFORE_CLASS,
    COL_GAP_BEFORE_SEMANTIC,
    COL_GAP_BEFORE_CONFIDENCE,
    COL_VALUE_CHANGED_RELATIVE_PCT,
    COL_EXCLUSION_WINDOW_ID,
)


def build_stage2_annotated_dataframe(
    df: pd.DataFrame,
    intervals: pd.Series,
    gap_classes: List[str],
    gap_semantics: List[str],
    gap_confidences: List[float],
    value_changes_pct: List[float],
    exclusion_windows: List[Dict],
    timestamp_col: str = "timestamp"
) -> pd.DataFrame:
    """
    Build gap-annotated DataFrame with metadata columns.
    
    Adds 6 new columns:
    - gap_before_duration_s: Time interval to previous record (seconds)
    - gap_before_class: NORMAL | MINOR_GAP | MAJOR_GAP
    - gap_before_semantic: COV_CONSTANT | COV_MINOR | SENSOR_ANOMALY | N/A
    - gap_before_confidence: Confidence in gap classification (0.0-1.0)
    - value_changed_relative_pct: Relative change from previous value (%)
    - exclusion_window_id: EXW_xxx if in exclusion window, else None
    
    Args:
        df: Original signal DataFrame (must have timestamp_col and value column)
        intervals: Series of interval durations (length N-1)
        gap_classes: List of gap classifications (length N-1)
        gap_semantics: List of gap semantics (length N-1)
        gap_confidences: List of gap confidences (length N-1)
        value_changes_pct: List of relative value changes (length N-1)
        exclusion_windows: List of exclusion window dicts with start_ts, end_ts, window_id
        timestamp_col: Name of timestamp column in df
        
    Returns:
        Annotated DataFrame with 6 additional columns
        
    Algorithm:
        1. Copy original DataFrame
        2. Add gap metadata columns (pad first row with NaN/None)
        3. Mark rows in exclusion windows with window_id
        4. Return annotated DataFrame
        
    Example:
        >>> df = pd.DataFrame({"timestamp": [1000, 1015, 1090], "value": [6.8, 6.8, 7.0]})
        >>> intervals = pd.Series([15, 75])
        >>> gap_classes = ["NORMAL", "MAJOR_GAP"]
        >>> gap_semantics = ["N/A", "COV_CONSTANT"]
        >>> result = build_stage2_annotated_dataframe(df, intervals, gap_classes, gap_semantics, [0.95, 0.92], [0.0, 2.9], [])
        >>> result.columns.tolist()
        ['timestamp', 'value', 'gap_before_duration_s', 'gap_before_class', ...]
    """
    # Copy original DataFrame
    df_annotated = df.copy()
    
    # Pad gap metadata to match DataFrame length (N records, N-1 intervals)
    # First row has no "gap before" - use NaN/None
    n_records = len(df)
    
    gap_durations_padded = [np.nan] + intervals.tolist()
    gap_classes_padded = [None] + gap_classes
    gap_semantics_padded = [None] + gap_semantics
    gap_confidences_padded = [np.nan] + gap_confidences
    value_changes_padded = [np.nan] + value_changes_pct
    
    # Add gap metadata columns
    df_annotated[COL_GAP_BEFORE_DURATION_S] = gap_durations_padded
    df_annotated[COL_GAP_BEFORE_CLASS] = gap_classes_padded
    df_annotated[COL_GAP_BEFORE_SEMANTIC] = gap_semantics_padded
    df_annotated[COL_GAP_BEFORE_CONFIDENCE] = gap_confidences_padded
    df_annotated[COL_VALUE_CHANGED_RELATIVE_PCT] = value_changes_padded
    
    # Mark rows in exclusion windows
    exclusion_ids = [None] * n_records
    
    if timestamp_col in df_annotated.columns:
        timestamps = df_annotated[timestamp_col].values
        
        for window in exclusion_windows:
            window_id = window["window_id"]
            start_ts = window["start_ts"]
            end_ts = window["end_ts"]
            
            # Find rows within exclusion window
            for i, ts in enumerate(timestamps):
                if start_ts <= ts <= end_ts:
                    exclusion_ids[i] = window_id
    
    df_annotated[COL_EXCLUSION_WINDOW_ID] = exclusion_ids
    
    return df_annotated

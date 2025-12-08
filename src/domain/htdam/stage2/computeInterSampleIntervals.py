"""
Stage 2 Domain Function: Compute Inter-Sample Intervals

Pure function - NO side effects, NO logging, NO I/O.
Computes time differences between consecutive measurements for gap detection.

Reference: htdam/stage-2-gap-detection/HTAM Stage 2/HTDAM_Stage2_Impl_Guide.md
"""

import pandas as pd
import numpy as np
from typing import Tuple


def compute_inter_sample_intervals(
    timestamps: pd.Series,
    values: pd.Series
) -> Tuple[pd.Series, pd.Series]:
    """
    Compute time intervals between consecutive measurements.
    
    This function calculates delta_t[i] = t[i+1] - t[i] for all i in [0, N-2].
    
    Args:
        timestamps: Series of Unix epoch timestamps (seconds) or datetime objects
        values: Series of signal values (same length as timestamps)
        
    Returns:
        Tuple of:
        - intervals: Series of interval durations in seconds (length N-1)
        - sorted_values: Series of values sorted by timestamp (length N)
        
    Algorithm:
        1. Sort data by timestamp
        2. Compute time deltas between consecutive timestamps
        3. Return intervals (excluding first NaN) and sorted values
        
    Example:
        >>> timestamps = pd.Series([1000, 1015, 1020, 1090])
        >>> values = pd.Series([6.8, 6.8, 6.5, 7.0])
        >>> intervals, sorted_vals = compute_inter_sample_intervals(timestamps, values)
        >>> intervals.tolist()
        [15, 5, 70]  # seconds between measurements
    """
    # Validate inputs
    if len(timestamps) != len(values):
        raise ValueError(
            f"timestamps and values must have same length: "
            f"{len(timestamps)} != {len(values)}"
        )
    
    if len(timestamps) == 0:
        # Empty input - return empty series
        return pd.Series(dtype=float), pd.Series(dtype=float)
    
    if len(timestamps) == 1:
        # Single point - no intervals
        return pd.Series(dtype=float), values
    
    # Convert timestamps to numeric (Unix epoch seconds) if needed
    if pd.api.types.is_datetime64_any_dtype(timestamps):
        ts_numeric = timestamps.astype('int64') / 1e9  # nanoseconds to seconds
    else:
        ts_numeric = timestamps.astype(float)
    
    # Sort by timestamp
    sorted_idx = ts_numeric.argsort()
    ts_sorted = ts_numeric.iloc[sorted_idx].reset_index(drop=True)
    vals_sorted = values.iloc[sorted_idx].reset_index(drop=True)
    
    # Compute deltas (diff() creates N-1 intervals with first value NaN)
    deltas = ts_sorted.diff()
    
    # Return intervals (skip first NaN) and sorted values
    intervals = deltas.iloc[1:].reset_index(drop=True)
    
    return intervals, vals_sorted

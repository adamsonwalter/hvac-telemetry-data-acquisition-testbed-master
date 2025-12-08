"""
HTDAM Stage 1.5: Common Timestamp Detection

Pure function for finding timestamp intersection across multiple time-series.
ZERO side effects - no logging, no file I/O, no global state.

Purpose: Identify which timestamps are present across all required signals
to enable synchronized physics calculations (e.g., COP = cooling / power).
"""

from typing import Dict, List, Set
import pandas as pd
import numpy as np


def detect_common_timestamps(
    signal_dataframes: Dict[str, pd.DataFrame],
    required_signals: List[str],
    timestamp_col: str = "timestamp",
    tolerance_seconds: float = 0.0,
) -> pd.Series:
    """
    Pure function: Find timestamps present across all required signals.
    
    Args:
        signal_dataframes: Dict of signal_name -> DataFrame with timestamp column
        required_signals: List of signal names that must all have data
        timestamp_col: Name of timestamp column (default: "timestamp")
        tolerance_seconds: Allow timestamps within ±tolerance to match (default: exact match)
    
    Returns:
        pd.Series of common timestamps (sorted, deduplicated)
        
    Example:
        >>> dfs = {
        ...     "CHWST": pd.DataFrame({"timestamp": [100, 200, 300]}),
        ...     "CHWRT": pd.DataFrame({"timestamp": [100, 200, 400]}),
        ...     "POWER": pd.DataFrame({"timestamp": [100, 150, 200, 250, 300]})
        ... }
        >>> common = detect_common_timestamps(dfs, required_signals=["CHWST", "CHWRT"])
        >>> list(common)
        [100, 200]  # Intersection of CHWST and CHWRT (POWER not required)
    """
    if not required_signals:
        raise ValueError("required_signals must contain at least one signal name")
    
    # Collect timestamp sets for each required signal
    timestamp_sets: List[Set] = []
    
    for signal_name in required_signals:
        if signal_name not in signal_dataframes:
            raise ValueError(f"Required signal '{signal_name}' not found in signal_dataframes")
        
        df = signal_dataframes[signal_name]
        
        if timestamp_col not in df.columns:
            raise ValueError(f"Signal '{signal_name}' missing timestamp column '{timestamp_col}'")
        
        # Get non-null timestamps
        timestamps = df[timestamp_col].dropna().unique()
        timestamp_sets.append(set(timestamps))
    
    # Find intersection
    if tolerance_seconds == 0.0:
        # Exact match (fast path)
        common_timestamps = set.intersection(*timestamp_sets)
    else:
        # Approximate match with tolerance (slower)
        common_timestamps = _find_timestamps_with_tolerance(
            timestamp_sets, tolerance_seconds
        )
    
    # Return as sorted Series
    result = pd.Series(sorted(common_timestamps), dtype=float)
    return result


def _find_timestamps_with_tolerance(
    timestamp_sets: List[Set[float]],
    tolerance_seconds: float
) -> Set[float]:
    """
    Helper: Find timestamps present in all sets within tolerance.
    
    Uses first set as reference, checks if other sets have matching timestamps.
    """
    if not timestamp_sets:
        return set()
    
    reference = timestamp_sets[0]
    other_sets = timestamp_sets[1:]
    
    common = set()
    
    for ref_ts in reference:
        # Check if all other sets have a timestamp within tolerance
        matched_all = True
        
        for other_set in other_sets:
            # Check if any timestamp in other_set is within tolerance
            matched_this_set = any(
                abs(ref_ts - other_ts) <= tolerance_seconds
                for other_ts in other_set
            )
            
            if not matched_this_set:
                matched_all = False
                break
        
        if matched_all:
            common.add(ref_ts)
    
    return common


def compute_synchronization_metrics(
    signal_dataframes: Dict[str, pd.DataFrame],
    common_timestamps: pd.Series,
    timestamp_col: str = "timestamp",
) -> Dict:
    """
    Pure function: Compute metrics about timestamp synchronization quality.
    
    Args:
        signal_dataframes: Dict of signal_name -> DataFrame
        common_timestamps: Series of common timestamps (from detect_common_timestamps)
        timestamp_col: Name of timestamp column
    
    Returns:
        Dict with synchronization metrics:
        {
            "n_common_timestamps": int,
            "per_signal_coverage": {signal_name: coverage_pct, ...},
            "overall_data_retention": float,  # % of total samples retained
            "sync_quality": str,  # "excellent" | "good" | "fair" | "poor"
        }
    """
    n_common = len(common_timestamps)
    
    per_signal_coverage = {}
    total_samples = 0
    
    for signal_name, df in signal_dataframes.items():
        if timestamp_col not in df.columns:
            continue
        
        n_signal_samples = len(df[timestamp_col].dropna())
        total_samples += n_signal_samples
        
        if n_signal_samples > 0:
            coverage_pct = (n_common / n_signal_samples) * 100.0
        else:
            coverage_pct = 0.0
        
        per_signal_coverage[signal_name] = round(coverage_pct, 2)
    
    # Overall retention: common timestamps × n_signals / total samples
    n_signals = len(signal_dataframes)
    overall_retention = 0.0
    if total_samples > 0:
        overall_retention = (n_common * n_signals / total_samples) * 100.0
    
    # Quality assessment
    avg_coverage = np.mean(list(per_signal_coverage.values())) if per_signal_coverage else 0.0
    
    if avg_coverage >= 80.0:
        sync_quality = "excellent"
    elif avg_coverage >= 60.0:
        sync_quality = "good"
    elif avg_coverage >= 40.0:
        sync_quality = "fair"
    else:
        sync_quality = "poor"
    
    return {
        "n_common_timestamps": n_common,
        "per_signal_coverage": per_signal_coverage,
        "overall_data_retention": round(overall_retention, 2),
        "sync_quality": sync_quality,
    }

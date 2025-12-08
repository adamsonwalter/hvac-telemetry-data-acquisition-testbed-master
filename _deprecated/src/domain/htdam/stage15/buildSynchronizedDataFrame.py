"""
HTDAM Stage 1.5: Synchronized DataFrame Builder

Pure function for building a synchronized DataFrame from per-signal data.
ZERO side effects - no logging, no file I/O, no global state.

Purpose: Merge validated signals at common timestamps for physics calculations.
"""

from typing import Dict, Optional
import pandas as pd


def build_synchronized_dataframe(
    signal_dataframes: Dict[str, pd.DataFrame],
    common_timestamps: pd.Series,
    timestamp_col: str = "timestamp",
    value_col: str = "value",
    method: str = "exact",
) -> pd.DataFrame:
    """
    Pure function: Build synchronized DataFrame with all signals at common timestamps.
    
    Args:
        signal_dataframes: Dict of signal_name -> DataFrame(timestamp, value, ...)
        common_timestamps: Series of timestamps to synchronize to (from detect_common_timestamps)
        timestamp_col: Name of timestamp column (default: "timestamp")
        value_col: Name of value column (default: "value")
        method: Synchronization method:
            - "exact": Only keep rows with exact timestamp matches (default)
            - "nearest": Use nearest timestamp within tolerance (future)
            - "interpolate": Linear interpolation (future)
    
    Returns:
        pd.DataFrame with columns: [timestamp, signal1, signal2, ...]
        Rows correspond to common_timestamps (sorted)
        
    Example:
        >>> signal_dfs = {
        ...     "CHWST": pd.DataFrame({"timestamp": [100, 200, 300], "value": [10.0, 11.0, 12.0]}),
        ...     "POWER": pd.DataFrame({"timestamp": [100, 150, 200], "value": [50.0, 75.0, 100.0]})
        ... }
        >>> common_ts = pd.Series([100, 200])
        >>> df_sync = build_synchronized_dataframe(signal_dfs, common_ts)
        >>> df_sync
           timestamp  CHWST  POWER
        0        100   10.0   50.0
        1        200   11.0  100.0
    """
    if method not in ["exact"]:
        raise ValueError(f"Unsupported synchronization method: {method}. Supported: 'exact'")
    
    if len(common_timestamps) == 0:
        # No common timestamps - return empty DataFrame with signal columns
        cols = [timestamp_col] + list(signal_dataframes.keys())
        return pd.DataFrame(columns=cols)
    
    # Start with common timestamps as base
    df_sync = pd.DataFrame({timestamp_col: common_timestamps})
    
    # Merge each signal
    for signal_name, df_signal in signal_dataframes.items():
        if timestamp_col not in df_signal.columns:
            raise ValueError(f"Signal '{signal_name}' missing timestamp column '{timestamp_col}'")
        
        # Determine value column name
        if value_col in df_signal.columns:
            signal_value_col = value_col
        elif signal_name.lower() in df_signal.columns:
            signal_value_col = signal_name.lower()
        else:
            # Use second column as value if available
            if len(df_signal.columns) >= 2:
                signal_value_col = df_signal.columns[1]
            else:
                raise ValueError(
                    f"Signal '{signal_name}' has no recognizable value column. "
                    f"Expected '{value_col}' or '{signal_name.lower()}'"
                )
        
        # Extract timestamp and value
        df_signal_subset = df_signal[[timestamp_col, signal_value_col]].copy()
        df_signal_subset = df_signal_subset.rename(columns={signal_value_col: signal_name})
        
        # Inner join on timestamp (keeps only common timestamps)
        df_sync = df_sync.merge(df_signal_subset, on=timestamp_col, how="inner")
    
    # Sort by timestamp
    df_sync = df_sync.sort_values(timestamp_col).reset_index(drop=True)
    
    return df_sync


def compute_coverage_per_signal(
    df_synchronized: pd.DataFrame,
    timestamp_col: str = "timestamp",
) -> Dict[str, Dict]:
    """
    Pure function: Compute data coverage statistics for each signal.
    
    Args:
        df_synchronized: Output from build_synchronized_dataframe
        timestamp_col: Name of timestamp column
    
    Returns:
        Dict with per-signal coverage:
        {
            "CHWST": {
                "total_rows": 1000,
                "non_null_rows": 980,
                "null_rows": 20,
                "coverage_pct": 98.0,
            },
            ...
        }
    """
    coverage = {}
    
    signal_cols = [col for col in df_synchronized.columns if col != timestamp_col]
    total_rows = len(df_synchronized)
    
    for signal_name in signal_cols:
        non_null = df_synchronized[signal_name].notna().sum()
        null = total_rows - non_null
        coverage_pct = (non_null / total_rows * 100.0) if total_rows > 0 else 0.0
        
        coverage[signal_name] = {
            "total_rows": total_rows,
            "non_null_rows": int(non_null),
            "null_rows": int(null),
            "coverage_pct": round(coverage_pct, 2),
        }
    
    return coverage


def validate_synchronization_quality(
    df_synchronized: pd.DataFrame,
    min_rows: int = 100,
    min_coverage_pct: float = 80.0,
) -> Dict:
    """
    Pure function: Validate if synchronized data meets quality thresholds.
    
    Args:
        df_synchronized: Output from build_synchronized_dataframe
        min_rows: Minimum number of synchronized rows required
        min_coverage_pct: Minimum non-null coverage per signal (%)
    
    Returns:
        Dict with validation results:
        {
            "valid": bool,
            "n_rows": int,
            "violations": [list of violation messages],
            "warnings": [list of warning messages],
        }
    """
    violations = []
    warnings = []
    
    n_rows = len(df_synchronized)
    
    # Check row count
    if n_rows < min_rows:
        violations.append(
            f"Insufficient synchronized rows: {n_rows} < {min_rows} minimum"
        )
    elif n_rows < min_rows * 2:
        warnings.append(
            f"Low synchronized row count: {n_rows} (recommended: >{min_rows * 2})"
        )
    
    # Check per-signal coverage
    coverage = compute_coverage_per_signal(df_synchronized)
    
    for signal_name, stats in coverage.items():
        cov_pct = stats["coverage_pct"]
        
        if cov_pct < min_coverage_pct:
            violations.append(
                f"{signal_name}: coverage {cov_pct:.1f}% < {min_coverage_pct:.1f}% minimum"
            )
        elif cov_pct < 95.0:
            warnings.append(
                f"{signal_name}: coverage {cov_pct:.1f}% (some missing data)"
            )
    
    return {
        "valid": len(violations) == 0,
        "n_rows": n_rows,
        "violations": violations,
        "warnings": warnings,
    }

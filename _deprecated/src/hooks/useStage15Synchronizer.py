"""
HTDAM Stage 1.5: Timestamp Synchronization Hook

Hook for orchestrating timestamp alignment across multiple signals.
ALL side effects here - logging, progress tracking, error handling.

Calls pure functions from domain layer for business logic.
"""

import logging
from typing import Dict, List, Tuple
import pandas as pd

# Import pure functions from domain layer
from src.domain.htdam.stage15.detectCommonTimestamps import (
    detect_common_timestamps,
    compute_synchronization_metrics,
)
from src.domain.htdam.stage15.buildSynchronizedDataFrame import (
    build_synchronized_dataframe,
    compute_coverage_per_signal,
    validate_synchronization_quality,
)

# Set up logger (side effect)
logger = logging.getLogger(__name__)


class Stage15InsufficientDataException(Exception):
    """Exception raised when synchronized data fails quality thresholds."""
    pass


def use_stage15_synchronizer(
    signal_dataframes: Dict[str, pd.DataFrame],
    required_signals: List[str],
    timestamp_col: str = "timestamp",
    value_col: str = "value",
    min_rows: int = 100,
    min_coverage_pct: float = 80.0,
    halt_on_insufficient_data: bool = True,
) -> Tuple[pd.DataFrame, Dict]:
    """
    Hook: Orchestrate Stage 1.5 timestamp synchronization.
    
    This hook contains ALL side effects:
    - Logging
    - Progress tracking
    - Error handling
    - Exception raising (for insufficient data)
    
    Business logic is delegated to pure functions in domain layer.
    
    Args:
        signal_dataframes: Dict of signal_name -> DataFrame(timestamp, value, ...)
        required_signals: List of signal names that must be present for sync
        timestamp_col: Name of timestamp column (default: "timestamp")
        value_col: Name of value column (default: "value")
        min_rows: Minimum synchronized rows required (default: 100)
        min_coverage_pct: Minimum non-null coverage per signal (default: 80%)
        halt_on_insufficient_data: Raise exception if quality thresholds not met
    
    Returns:
        (df_synchronized, metrics_dict)
        
    Raises:
        Stage15InsufficientDataException: If halt_on_insufficient_data=True and quality fails
        
    Example:
        >>> signal_dfs = {
        ...     "CHWST": df_chwst_validated,
        ...     "CHWRT": df_chwrt_validated,
        ...     "POWER": df_power_validated
        ... }
        >>> df_sync, metrics = use_stage15_synchronizer(
        ...     signal_dfs,
        ...     required_signals=["CHWST", "CHWRT", "POWER"]
        ... )
    """
    logger.info("=" * 80)
    logger.info("HTDAM Stage 1.5: Timestamp Synchronization")
    logger.info("=" * 80)
    logger.info(f"Input signals: {list(signal_dataframes.keys())}")
    logger.info(f"Required for sync: {required_signals}")
    
    for signal_name, df in signal_dataframes.items():
        n_samples = len(df) if timestamp_col not in df.columns else len(df[timestamp_col].dropna())
        logger.info(f"  {signal_name}: {n_samples} samples")
    
    # Step 1: Detect common timestamps
    logger.info("\n" + "-" * 80)
    logger.info("Step 1: Detecting Common Timestamps")
    logger.info("-" * 80)
    
    try:
        common_timestamps = detect_common_timestamps(
            signal_dataframes,
            required_signals,
            timestamp_col=timestamp_col,
        )
        
        logger.info(f"  Common timestamps found: {len(common_timestamps)}")
        
        if len(common_timestamps) == 0:
            logger.error("  ❌ No common timestamps found across required signals")
            raise Stage15InsufficientDataException(
                "No common timestamps found across required signals"
            )
    
    except Exception as e:
        logger.error(f"Common timestamp detection failed: {e}")
        raise
    
    # Step 2: Compute synchronization metrics
    logger.info("\n" + "-" * 80)
    logger.info("Step 2: Computing Synchronization Metrics")
    logger.info("-" * 80)
    
    try:
        sync_metrics = compute_synchronization_metrics(
            signal_dataframes,
            common_timestamps,
            timestamp_col=timestamp_col,
        )
        
        logger.info(f"  Synchronization quality: {sync_metrics['sync_quality'].upper()}")
        logger.info(f"  Overall data retention: {sync_metrics['overall_data_retention']:.1f}%")
        logger.info("  Per-signal coverage:")
        
        for signal_name, coverage_pct in sync_metrics["per_signal_coverage"].items():
            if coverage_pct >= 80.0:
                logger.info(f"    {signal_name}: {coverage_pct:.1f}% ✓")
            elif coverage_pct >= 60.0:
                logger.warning(f"    {signal_name}: {coverage_pct:.1f}% ⚠")
            else:
                logger.error(f"    {signal_name}: {coverage_pct:.1f}% ❌")
    
    except Exception as e:
        logger.error(f"Synchronization metrics computation failed: {e}")
        raise
    
    # Step 3: Build synchronized DataFrame
    logger.info("\n" + "-" * 80)
    logger.info("Step 3: Building Synchronized DataFrame")
    logger.info("-" * 80)
    
    try:
        df_synchronized = build_synchronized_dataframe(
            signal_dataframes,
            common_timestamps,
            timestamp_col=timestamp_col,
            value_col=value_col,
            method="exact",
        )
        
        logger.info(f"  Synchronized shape: {df_synchronized.shape}")
        logger.info(f"  Columns: {list(df_synchronized.columns)}")
        
        # Compute per-signal coverage in synchronized data
        coverage = compute_coverage_per_signal(df_synchronized, timestamp_col=timestamp_col)
        
        logger.info("  Signal coverage in synchronized data:")
        for signal_name, stats in coverage.items():
            logger.info(
                f"    {signal_name}: {stats['non_null_rows']}/{stats['total_rows']} "
                f"({stats['coverage_pct']:.1f}%)"
            )
    
    except Exception as e:
        logger.error(f"Synchronized DataFrame building failed: {e}")
        raise
    
    # Step 4: Validate synchronization quality
    logger.info("\n" + "-" * 80)
    logger.info("Step 4: Validating Synchronization Quality")
    logger.info("-" * 80)
    
    try:
        validation = validate_synchronization_quality(
            df_synchronized,
            min_rows=min_rows,
            min_coverage_pct=min_coverage_pct,
        )
        
        if validation["valid"]:
            logger.info("  ✓ Synchronization quality meets thresholds")
        else:
            logger.error("  ❌ Synchronization quality FAILED")
            for violation in validation["violations"]:
                logger.error(f"    - {violation}")
        
        if validation["warnings"]:
            logger.warning("  Warnings:")
            for warning in validation["warnings"]:
                logger.warning(f"    - {warning}")
        
        if not validation["valid"] and halt_on_insufficient_data:
            error_msg = "Stage 1.5 HALT: " + "; ".join(validation["violations"])
            logger.error(f"\nRaising exception: {error_msg}")
            raise Stage15InsufficientDataException(error_msg)
    
    except Stage15InsufficientDataException:
        raise
    except Exception as e:
        logger.error(f"Synchronization quality validation failed: {e}")
        raise
    
    # Build final metrics
    metrics = {
        "stage": "SYNC",
        "n_input_signals": len(signal_dataframes),
        "n_required_signals": len(required_signals),
        "n_common_timestamps": len(common_timestamps),
        "n_synchronized_rows": len(df_synchronized),
        "synchronization_metrics": sync_metrics,
        "signal_coverage": coverage,
        "validation": validation,
        "warnings": validation["warnings"],
        "errors": validation["violations"] if not validation["valid"] else [],
    }
    
    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("Stage 1.5 Complete")
    logger.info("=" * 80)
    logger.info(f"✓ Common timestamps: {len(common_timestamps)}")
    logger.info(f"✓ Synchronized rows: {len(df_synchronized)}")
    logger.info(f"✓ Synchronization quality: {sync_metrics['sync_quality']}")
    logger.info(f"✓ Overall retention: {sync_metrics['overall_data_retention']:.1f}%")
    
    if metrics['warnings']:
        logger.warning(f"\n⚠ {len(metrics['warnings'])} warnings - review metrics for details")
    
    if metrics['errors']:
        logger.error(f"\n❌ {len(metrics['errors'])} errors - review metrics for details")
    
    logger.info("=" * 80)
    
    return df_synchronized, metrics

#!/usr/bin/env python3
"""
Hook: Orchestrate BMS percentage signal decoding.

This module contains ALL side effects:
- File I/O (CSV read/write)
- Logging
- Error handling
- Progress reporting

Pure functions are called from domain layer.
"""

import logging
import pandas as pd
from typing import Tuple, Dict, Optional

# Import pure functions
from ..domain.decoder.normalizePercentSignal import normalize_percent_signal
from ..domain.decoder.formatDecoderReport import format_decoder_report

logger = logging.getLogger(__name__)


def use_bms_percent_decoder(
    filepath: str,
    signal_name: Optional[str] = None,
    timestamp_col: str = "save_time",
    value_col: str = "value"
) -> Tuple[pd.DataFrame, Dict]:
    """
    Hook: Load, decode, and return BMS percentage signal.
    
    ORCHESTRATION HOOK - CONTAINS SIDE EFFECTS
    - File I/O: loads CSV
    - Logging: progress and results
    - Error handling: validates inputs
    
    Args:
        filepath: Path to BMS CSV file
        signal_name: Name for logging (auto-detected from filename if None)
        timestamp_col: Name of timestamp column
        value_col: Name of value column
    
    Returns:
        Tuple of (decoded_dataframe, metadata_dict)
    
    Raises:
        ValueError: If required columns not found
        FileNotFoundError: If filepath doesn't exist
    
    Examples:
        >>> # Load and decode BMS signal
        >>> df, metadata = use_bms_percent_decoder('pump_vsd.csv')
        >>> df['normalized'].max()
        1.0
    """
    # Side effect: Log start
    logger.info(f"Loading BMS signal from {filepath}")
    
    try:
        # Side effect: Load CSV file
        df = pd.read_csv(filepath)
        logger.info(f"Loaded {len(df)} rows")
        
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        raise
    except Exception as e:
        logger.error(f"Failed to load CSV: {e}")
        raise
    
    # Validate columns
    if timestamp_col not in df.columns or value_col not in df.columns:
        logger.error(f"Required columns not found: {timestamp_col}, {value_col}")
        logger.error(f"Available columns: {df.columns.tolist()}")
        raise ValueError(f"Required columns not found: {timestamp_col}, {value_col}")
    
    # Side effect: Convert timestamp
    logger.info(f"Converting timestamp column: {timestamp_col}")
    df["timestamp"] = pd.to_datetime(df[timestamp_col], unit='s')
    
    # Auto-detect signal name from filename
    if signal_name is None:
        signal_name = filepath.split("/")[-1].replace(".csv", "")
        logger.info(f"Auto-detected signal name: {signal_name}")
    
    # Call pure function: normalize signal
    logger.info(f"Decoding signal: {signal_name}")
    normalized, metadata = normalize_percent_signal(
        df[value_col],
        signal_name=signal_name
    )
    
    # Side effect: Log detection results
    logger.info(f"✓ Detected type: {metadata['detected_type']}")
    logger.info(f"✓ Confidence: {metadata['confidence']}")
    logger.info(f"✓ Scaling factor: {metadata['scaling_factor']:.2f}")
    
    if metadata['confidence'] == 'low':
        logger.warning(f"⚠️  Low confidence detection - verify results manually")
    
    # Add results to DataFrame
    df["normalized"] = normalized
    df["raw_value"] = df[value_col]
    
    # Add metadata columns
    for key, val in metadata.items():
        df[f"meta_{key}"] = val
    
    logger.info(f"Decoding complete: {len(df)} points normalized")
    
    return df, metadata


def save_decoded_file(df: pd.DataFrame, output_path: str) -> None:
    """
    Hook: Save decoded DataFrame to CSV.
    
    ORCHESTRATION HOOK - CONTAINS SIDE EFFECTS
    - File I/O: writes CSV
    - Logging: progress
    
    Args:
        df: Decoded DataFrame
        output_path: Path to save CSV
    
    Raises:
        IOError: If file cannot be written
    
    Examples:
        >>> save_decoded_file(df, 'output_decoded.csv')
    """
    logger.info(f"Saving decoded data to {output_path}")
    
    try:
        # Side effect: Write CSV file
        df.to_csv(output_path, index=False)
        logger.info(f"✓ Saved {len(df)} rows to {output_path}")
        
    except Exception as e:
        logger.error(f"Failed to save file: {e}")
        raise IOError(f"Failed to save file: {e}")


def decode_and_report(
    filepath: str,
    signal_name: Optional[str] = None,
    save_output: bool = True,
    output_path: Optional[str] = None
) -> str:
    """
    Hook: Complete workflow - decode file and generate report.
    
    ORCHESTRATION HOOK - CONTAINS SIDE EFFECTS
    - File I/O: loads and optionally saves CSV
    - Logging: full workflow
    - Report generation: calls pure function
    
    Args:
        filepath: Path to BMS CSV file
        signal_name: Name for logging
        save_output: Whether to save decoded CSV
        output_path: Path for output (auto-generated if None)
    
    Returns:
        Formatted report string
    
    Examples:
        >>> report = decode_and_report('pump.csv')
        >>> print(report)
    """
    logger.info("=" * 80)
    logger.info("Starting BMS Percent Decoder workflow")
    logger.info("=" * 80)
    
    # Hook: Decode file
    df, metadata = use_bms_percent_decoder(filepath, signal_name)
    
    # Pure function: Generate report
    report = format_decoder_report(df, metadata)
    
    # Hook: Save output if requested
    if save_output:
        if output_path is None:
            output_path = filepath.replace(".csv", "_decoded.csv")
        save_decoded_file(df, output_path)
    
    logger.info("=" * 80)
    logger.info("Workflow complete")
    logger.info("=" * 80)
    
    return report

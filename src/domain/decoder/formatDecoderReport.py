#!/usr/bin/env python3
"""
Pure function: Format decoder detection report.

This module contains ZERO side effects:
- NO logging
- NO file I/O
- NO global state
- Pure string formatting only
"""

import pandas as pd
from typing import Dict


def format_decoder_report(df: pd.DataFrame, metadata: Dict = None) -> str:
    """
    Generate human-readable detection report from decoded DataFrame.
    
    PURE FUNCTION - NO SIDE EFFECTS
    - Deterministic: same input → same output
    - No logging or file I/O
    - Just string formatting
    
    Args:
        df: Decoded DataFrame with metadata columns
        metadata: Optional metadata dict (extracted from df if None)
    
    Returns:
        Formatted report string
    
    Examples:
        >>> import pandas as pd
        >>> df = pd.DataFrame({
        ...     'normalized': [0.0, 0.5, 1.0],
        ...     'meta_signal_name': ['test'] * 3,
        ...     'meta_detected_type': ['counts_10000_0.01pct'] * 3,
        ...     'meta_confidence': ['high'] * 3,
        ...     'meta_scaling_factor': [10000.0] * 3
        ... })
        >>> report = format_decoder_report(df)
        >>> 'UNIVERSAL BMS PERCENT DECODER' in report
        True
    """
    report = []
    report.append("=" * 80)
    report.append("UNIVERSAL BMS PERCENT DECODER - DETECTION REPORT")
    report.append("=" * 80)
    
    # Extract metadata from DataFrame if not provided
    if metadata is None:
        meta_cols = [c for c in df.columns if c.startswith("meta_")]
        if not meta_cols:
            report.append("No metadata available")
            return "\n".join(report)
        
        # Get first row metadata (should be consistent)
        metadata = {c.replace("meta_", ""): df[c].iloc[0] for c in meta_cols}
    
    report.append(f"\nSignal Name:       {metadata.get('signal_name', 'unknown')}")
    report.append(f"Detected Type:     {metadata.get('detected_type', 'unknown')}")
    report.append(f"Confidence:        {metadata.get('confidence', 'unknown')}")
    report.append(f"Scaling Factor:    {metadata.get('scaling_factor', 1.0):.2f}")
    
    if metadata.get('p995') is not None:
        report.append(f"P99.5:             {metadata['p995']:.2f}")
    if metadata.get('p005') is not None:
        report.append(f"P00.5:             {metadata['p005']:.2f}")
    
    report.append(f"\nOriginal Signal:")
    report.append(f"  Min:    {metadata.get('original_min', 0):.2f}")
    report.append(f"  Max:    {metadata.get('original_max', 0):.2f}")
    report.append(f"  Mean:   {metadata.get('original_mean', 0):.2f}")
    report.append(f"  Count:  {metadata.get('original_count', 0)}")
    
    if "normalized" in df.columns:
        norm_stats = df["normalized"].describe()
        report.append(f"\nNormalized (0-1):")
        report.append(f"  Min:    {norm_stats['min']:.4f}")
        report.append(f"  Max:    {norm_stats['max']:.4f}")
        report.append(f"  Mean:   {norm_stats['mean']:.4f}")
        report.append(f"  Median: {norm_stats['50%']:.4f}")
    
    report.append("\n" + "=" * 80)
    return "\n".join(report)

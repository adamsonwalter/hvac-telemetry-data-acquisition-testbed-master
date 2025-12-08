"""
Stage 2 Domain Function: Classify Gap Intervals

Pure function - NO side effects, NO logging, NO I/O.
Classifies time intervals as NORMAL, MINOR_GAP, or MAJOR_GAP based on thresholds.

Reference: htdam/stage-2-gap-detection/HTAM Stage 2/HTDAM_Stage2_Impl_Guide.md
"""

from src.domain.htdam.constants import (
    T_NOMINAL_SECONDS,
    NORMAL_MAX_FACTOR,
    MINOR_GAP_UPPER_FACTOR,
    MAJOR_GAP_LOWER_FACTOR,
    GAP_CLASS_NORMAL,
    GAP_CLASS_MINOR,
    GAP_CLASS_MAJOR,
)


def classify_gap(
    interval_seconds: float,
    t_nominal: float = T_NOMINAL_SECONDS
) -> str:
    """
    Classify a time interval as NORMAL, MINOR_GAP, or MAJOR_GAP.
    
    Classification thresholds (relative to t_nominal):
    - NORMAL: interval <= 1.5 × t_nominal (e.g., <=22.5 min for 15-min logging)
    - MINOR_GAP: 1.5 × t_nominal < interval <= 4.0 × t_nominal (e.g., <=60 min)
    - MAJOR_GAP: interval > 4.0 × t_nominal (e.g., >60 min)
    
    Args:
        interval_seconds: Time interval in seconds between consecutive measurements
        t_nominal: Nominal interval in seconds (default: 900s = 15 minutes)
        
    Returns:
        Gap classification: "NORMAL" | "MINOR_GAP" | "MAJOR_GAP"
        
    Algorithm:
        1. Compute threshold bounds from t_nominal
        2. Compare interval to thresholds
        3. Return classification label
        
    Example:
        >>> classify_gap(900)   # 15 minutes
        'NORMAL'
        >>> classify_gap(1800)  # 30 minutes
        'MINOR_GAP'
        >>> classify_gap(7200)  # 2 hours
        'MAJOR_GAP'
    """
    # Compute threshold bounds
    normal_max = t_nominal * NORMAL_MAX_FACTOR
    minor_gap_upper = t_nominal * MINOR_GAP_UPPER_FACTOR
    
    # Classify interval
    if interval_seconds <= normal_max:
        return GAP_CLASS_NORMAL
    elif interval_seconds <= minor_gap_upper:
        return GAP_CLASS_MINOR
    else:
        return GAP_CLASS_MAJOR

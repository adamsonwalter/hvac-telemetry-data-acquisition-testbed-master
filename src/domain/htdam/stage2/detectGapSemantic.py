"""
Stage 2 Domain Function: Detect Gap Semantic

Pure function - NO side effects, NO logging, NO I/O.
Determines if a gap represents COV (Change-of-Value) behavior or a sensor anomaly.

Reference: htdam/stage-2-gap-detection/HTAM Stage 2/HTDAM_Stage2_Impl_Guide.md
"""

from src.domain.htdam.constants import (
    COV_TOLERANCE_RELATIVE_PCT,
    SENSOR_ANOMALY_JUMP_THRESHOLD,
    GAP_CLASS_NORMAL,
    GAP_SEMANTIC_COV_CONSTANT,
    GAP_SEMANTIC_COV_MINOR,
    GAP_SEMANTIC_SENSOR_ANOMALY,
    GAP_SEMANTIC_NA,
)


def detect_gap_semantic(
    value_before: float,
    value_after: float,
    gap_class: str
) -> str:
    """
    Detect the semantic meaning of a gap based on value change.
    
    Gap semantics:
    - COV_CONSTANT: Value held constant (change <0.5%), benign
    - COV_MINOR: Slow drift triggered COV (change 0.5-5°C), benign
    - SENSOR_ANOMALY: Large jump (>5°C) or physics violation, suspicious
    - N/A: Not applicable (NORMAL intervals have no semantic meaning)
    
    Args:
        value_before: Signal value immediately before the gap
        value_after: Signal value immediately after the gap
        gap_class: Gap classification from classify_gap() ("NORMAL", "MINOR_GAP", "MAJOR_GAP")
        
    Returns:
        Gap semantic: "COV_CONSTANT" | "COV_MINOR" | "SENSOR_ANOMALY" | "N/A"
        
    Algorithm:
        1. If gap_class is NORMAL, return N/A (no semantic analysis needed)
        2. Compute absolute and relative value change
        3. If absolute change >5°C → SENSOR_ANOMALY
        4. If relative change <0.5% → COV_CONSTANT
        5. Otherwise → COV_MINOR
        
    Example:
        >>> detect_gap_semantic(17.56, 17.61, "MAJOR_GAP")
        'COV_CONSTANT'  # 0.28% change
        >>> detect_gap_semantic(12.3, 7.8, "MAJOR_GAP")
        'SENSOR_ANOMALY'  # 4.5°C jump
        >>> detect_gap_semantic(6.8, 6.8, "NORMAL")
        'N/A'  # NORMAL intervals don't need semantic analysis
    """
    # NORMAL intervals don't need semantic analysis
    if gap_class == GAP_CLASS_NORMAL:
        return GAP_SEMANTIC_NA
    
    # Compute value changes
    absolute_change = abs(value_after - value_before)
    
    # Avoid division by zero for relative change
    if abs(value_before) < 1e-6:
        # If value_before is near zero, use absolute change only
        relative_change_pct = absolute_change * 100.0  # Treat as 100% per unit
    else:
        relative_change_pct = (absolute_change / abs(value_before)) * 100.0
    
    # Classify semantic based on thresholds
    
    # Large jump → SENSOR_ANOMALY
    if absolute_change > SENSOR_ANOMALY_JUMP_THRESHOLD:
        return GAP_SEMANTIC_SENSOR_ANOMALY
    
    # Very small change → COV_CONSTANT (setpoint held)
    if relative_change_pct < COV_TOLERANCE_RELATIVE_PCT:
        return GAP_SEMANTIC_COV_CONSTANT
    
    # Moderate change → COV_MINOR (slow drift)
    return GAP_SEMANTIC_COV_MINOR

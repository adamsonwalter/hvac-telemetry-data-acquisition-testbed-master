"""
Stage 2 Domain Function: Compute Gap Penalties

Pure function - NO side effects, NO logging, NO I/O.
Computes confidence penalties based on gap semantic types.

Reference: htdam/stage-2-gap-detection/HTAM Stage 2/HTDAM_Stage2_Impl_Guide.md
"""

from typing import List
from src.domain.htdam.constants import GAP_PENALTIES


def compute_gap_penalties(gap_semantics: List[str]) -> float:
    """
    Compute total confidence penalty from gap semantics.
    
    Penalty values by semantic type:
    - COV_CONSTANT: 0.0 (benign, setpoint held)
    - COV_MINOR: -0.02 (benign, slow drift)
    - SENSOR_ANOMALY: -0.05 (suspicious, large jump or physics violation)
    - EXCLUDED: -0.03 (data excluded by user)
    - UNKNOWN: -0.01 (cannot classify)
    
    Args:
        gap_semantics: List of gap semantic labels
        
    Returns:
        Total penalty (sum of individual penalties)
        
    Algorithm:
        1. Iterate through gap_semantics list
        2. Look up penalty for each semantic type
        3. Sum all penalties
        4. Return total
        
    Example:
        >>> compute_gap_penalties(["COV_CONSTANT", "COV_CONSTANT", "COV_MINOR"])
        -0.02  # 0.0 + 0.0 + (-0.02)
        
        >>> compute_gap_penalties(["SENSOR_ANOMALY", "COV_MINOR", "COV_CONSTANT"])
        -0.07  # (-0.05) + (-0.02) + 0.0
        
        >>> compute_gap_penalties([])
        0.0  # No gaps, no penalty
    """
    if not gap_semantics:
        return 0.0
    
    total_penalty = sum(GAP_PENALTIES.get(semantic, 0.0) for semantic in gap_semantics)
    
    return total_penalty

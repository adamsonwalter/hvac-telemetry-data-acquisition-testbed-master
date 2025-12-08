"""
Stage 3 Domain Function: Get Alignment Confidence

Pure function - NO side effects, NO logging, NO I/O.
Maps alignment quality tier to confidence score.

Reference: htdam/stage-3-timestamp-sync/HTDAM v2.0 Stage 3_ Timestamp Synchronization.md
"""

from src.domain.htdam.constants import (
    ALIGN_EXACT,
    ALIGN_CLOSE,
    ALIGN_INTERP,
    ALIGN_MISSING,
)


def get_alignment_confidence(align_quality: str) -> float:
    """
    Map alignment quality tier to confidence score.
    
    This function defines the confidence degradation for increasing alignment
    distances. The values are calibrated based on typical COV logging behavior.
    
    Args:
        align_quality: Alignment quality ('EXACT', 'CLOSE', 'INTERP', 'MISSING')
        
    Returns:
        Confidence score (0.00-0.95)
        
    Mapping:
        - EXACT (<60s): 0.95 - Very high confidence, nearly simultaneous
        - CLOSE (60-300s): 0.90 - High confidence, within typical COV window
        - INTERP (300-1800s): 0.85 - Moderate confidence, extended hold period
        - MISSING (>1800s or no match): 0.00 - No confidence, no valid data
        
    Rationale:
        - EXACT: Within 1 minute of grid point → minimal drift
        - CLOSE: Within 5 minutes → acceptable for 15-min COV logging
        - INTERP: Within 30 minutes → possible but degraded quality
        - MISSING: Beyond 30 minutes or no point → unreliable
        
    Example:
        >>> get_alignment_confidence('EXACT')
        0.95
        >>> get_alignment_confidence('CLOSE')
        0.90
        >>> get_alignment_confidence('INTERP')
        0.85
        >>> get_alignment_confidence('MISSING')
        0.0
        >>> get_alignment_confidence('INVALID')  # Unknown quality
        0.0
    """
    confidence_map = {
        ALIGN_EXACT: 0.95,
        ALIGN_CLOSE: 0.90,
        ALIGN_INTERP: 0.85,
        ALIGN_MISSING: 0.00,
    }
    
    # Return mapped confidence, default to 0.00 for unknown quality
    return confidence_map.get(align_quality, 0.00)

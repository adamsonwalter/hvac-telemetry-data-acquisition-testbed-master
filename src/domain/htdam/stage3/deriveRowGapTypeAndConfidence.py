"""
Stage 3 Domain Function: Derive Row Gap Type and Confidence

Pure function - NO side effects, NO logging, NO I/O.
Combines per-stream alignment qualities into row-level classification.

Reference: htdam/stage-3-timestamp-sync/HTDAM v2.0 Stage 3_ Timestamp Synchronization.md
"""

from typing import Dict, Optional, Tuple
from src.domain.htdam.constants import (
    MANDATORY_STREAMS,
    ALIGN_MISSING,
    GAP_TYPE_VALID,
    GAP_TYPE_EXCLUDED,
    GAP_TYPE_COV_CONSTANT,
    GAP_TYPE_COV_MINOR,
    GAP_TYPE_SENSOR_ANOMALY,
    GAP_TYPE_GAP,
    GAP_SEMANTIC_COV_CONSTANT,
    GAP_SEMANTIC_COV_MINOR,
    GAP_SEMANTIC_SENSOR_ANOMALY,
)
from src.domain.htdam.stage3.getAlignmentConfidence import get_alignment_confidence


def derive_row_gap_type_and_confidence(
    align_qualities: Dict[str, str],
    exclusion_window_id: Optional[str],
    stage2_semantic: Optional[str] = None
) -> Tuple[str, float]:
    """
    Derive row-level gap type and confidence from per-stream alignment qualities.
    
    This function implements the row classification logic that determines whether
    a grid row is VALID for analysis or should be classified as a gap/exclusion.
    
    **Decision Hierarchy:**
    1. Exclusion windows checked FIRST (highest priority)
    2. Mandatory stream coverage (CHWST, CHWRT, CDWRT required)
    3. If any mandatory missing → use Stage 2 gap semantic
    4. All mandatory present → VALID with minimum confidence across streams
    
    Args:
        align_qualities: Dict mapping stream_id → alignment quality
                        Example: {'CHWST': 'EXACT', 'CHWRT': 'CLOSE', 'CDWRT': 'INTERP'}
        exclusion_window_id: Window ID if in approved exclusion, else None
        stage2_semantic: Optional Stage 2 gap semantic near this grid time
                        ('COV_CONSTANT', 'COV_MINOR', 'SENSOR_ANOMALY', etc.)
        
    Returns:
        Tuple of (gap_type, confidence):
        - gap_type: 'VALID' | 'EXCLUDED' | 'COV_CONSTANT' | 'COV_MINOR' | 
                   'SENSOR_ANOMALY' | 'GAP'
        - confidence: 0.00-0.95 (minimum across mandatory streams if VALID, else 0.00)
        
    Algorithm:
        1. If exclusion_window_id is not None:
           → Return ('EXCLUDED', 0.00)
        
        2. Check mandatory stream coverage:
           - Get qualities for CHWST, CHWRT, CDWRT
           - If any is 'MISSING':
             a. If stage2_semantic available → return (semantic, 0.00)
             b. Otherwise → return ('GAP', 0.00)
        
        3. All mandatory streams present:
           - Compute confidence for each mandatory stream
           - Return ('VALID', min(confidences))
        
    Note on Optional Streams:
        Flow and Power quality do NOT affect row VALID status. A row can be VALID
        for temperature analysis even if Flow/Power are MISSING. Stage 4 will
        handle COP-specific confidence adjustments.
        
    Example:
        >>> # All mandatory present
        >>> derive_row_gap_type_and_confidence(
        ...     {'CHWST': 'EXACT', 'CHWRT': 'EXACT', 'CDWRT': 'CLOSE'},
        ...     None, None
        ... )
        ('VALID', 0.90)  # Min confidence is CLOSE (0.90)
        
        >>> # Exclusion window (highest priority)
        >>> derive_row_gap_type_and_confidence(
        ...     {'CHWST': 'EXACT', 'CHWRT': 'EXACT', 'CDWRT': 'EXACT'},
        ...     'EXW_001', None
        ... )
        ('EXCLUDED', 0.0)
        
        >>> # Missing mandatory with Stage 2 semantic
        >>> derive_row_gap_type_and_confidence(
        ...     {'CHWST': 'MISSING', 'CHWRT': 'EXACT', 'CDWRT': 'EXACT'},
        ...     None, 'COV_CONSTANT'
        ... )
        ('COV_CONSTANT', 0.0)
        
        >>> # Missing mandatory without Stage 2 semantic
        >>> derive_row_gap_type_and_confidence(
        ...     {'CHWST': 'MISSING', 'CHWRT': 'EXACT', 'CDWRT': 'EXACT'},
        ...     None, None
        ... )
        ('GAP', 0.0)
    """
    # Priority 1: Check exclusion window
    if exclusion_window_id is not None:
        return (GAP_TYPE_EXCLUDED, 0.00)
    
    # Priority 2: Check mandatory stream coverage
    mandatory_qualities = []
    for stream in MANDATORY_STREAMS:
        quality = align_qualities.get(stream, ALIGN_MISSING)
        mandatory_qualities.append(quality)
    
    # If any mandatory stream is MISSING
    if any(q == ALIGN_MISSING for q in mandatory_qualities):
        # Use Stage 2 gap semantic if available
        if stage2_semantic == GAP_SEMANTIC_COV_CONSTANT:
            return (GAP_TYPE_COV_CONSTANT, 0.00)
        elif stage2_semantic == GAP_SEMANTIC_COV_MINOR:
            return (GAP_TYPE_COV_MINOR, 0.00)
        elif stage2_semantic == GAP_SEMANTIC_SENSOR_ANOMALY:
            return (GAP_TYPE_SENSOR_ANOMALY, 0.00)
        else:
            # Generic gap (no semantic available)
            return (GAP_TYPE_GAP, 0.00)
    
    # Priority 3: All mandatory streams present → VALID
    # Compute confidence as minimum across mandatory streams
    confidences = [get_alignment_confidence(q) for q in mandatory_qualities]
    row_confidence = min(confidences)
    
    return (GAP_TYPE_VALID, row_confidence)

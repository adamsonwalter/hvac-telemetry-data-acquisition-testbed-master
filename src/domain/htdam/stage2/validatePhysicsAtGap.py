"""
Stage 2 Domain Function: Validate Physics at Gap

Pure function - NO side effects, NO logging, NO I/O.
Validates thermodynamic relationships at gap boundaries.

Reference: htdam/stage-2-gap-detection/HTAM Stage 2/HTDAM_Stage2_Impl_Guide.md
"""

from typing import Dict, List, Optional


def validate_physics_at_gap(
    chwst_before: Optional[float] = None,
    chwst_after: Optional[float] = None,
    chwrt_before: Optional[float] = None,
    chwrt_after: Optional[float] = None,
    cdwrt_before: Optional[float] = None,
    cdwrt_after: Optional[float] = None,
) -> Dict:
    """
    Validate physics relationships at gap boundaries.
    
    Physics checks:
    1. Delta-T must be non-negative: CHWRT >= CHWST
    2. Delta-T must be sane: Delta-T <= 20°C
    3. Condenser must be hotter than evaporator: CDWRT > CHWST
    
    Args:
        chwst_before: Chilled water supply temp (°C) before gap
        chwst_after: Chilled water supply temp (°C) after gap
        chwrt_before: Chilled water return temp (°C) before gap
        chwrt_after: Chilled water return temp (°C) after gap
        cdwrt_before: Condenser water return temp (°C) before gap
        cdwrt_after: Condenser water return temp (°C) after gap
        
    Returns:
        Dict with:
        - physics_valid: bool (True if all checks pass)
        - violations: List[str] (list of violation descriptions)
        
    Algorithm:
        1. Check Delta-T before gap (if CHWST and CHWRT available)
        2. Check Delta-T after gap
        3. Check condenser relationship before gap
        4. Check condenser relationship after gap
        5. Return summary
        
    Example:
        >>> validate_physics_at_gap(
        ...     chwst_before=6.8, chwst_after=6.5,
        ...     chwrt_before=12.3, chwrt_after=12.1,
        ...     cdwrt_before=28.5, cdwrt_after=28.2
        ... )
        {'physics_valid': True, 'violations': []}
        
        >>> validate_physics_at_gap(
        ...     chwst_before=12.3, chwst_after=12.1,
        ...     chwrt_before=6.8, chwrt_after=6.5,  # CHWRT < CHWST!
        ... )
        {'physics_valid': False, 'violations': ['Negative Delta-T detected before gap', ...]}
    """
    violations: List[str] = []
    
    # Check Delta-T before gap
    if chwst_before is not None and chwrt_before is not None:
        delta_t_before = chwrt_before - chwst_before
        
        if delta_t_before < 0:
            violations.append(
                f"Negative Delta-T detected before gap: "
                f"CHWRT ({chwrt_before:.2f}°C) < CHWST ({chwst_before:.2f}°C)"
            )
        
        if delta_t_before > 20.0:
            violations.append(
                f"Unrealistic Delta-T before gap: {delta_t_before:.2f}°C (>20°C)"
            )
    
    # Check Delta-T after gap
    if chwst_after is not None and chwrt_after is not None:
        delta_t_after = chwrt_after - chwst_after
        
        if delta_t_after < 0:
            violations.append(
                f"Negative Delta-T detected after gap: "
                f"CHWRT ({chwrt_after:.2f}°C) < CHWST ({chwst_after:.2f}°C)"
            )
        
        if delta_t_after > 20.0:
            violations.append(
                f"Unrealistic Delta-T after gap: {delta_t_after:.2f}°C (>20°C)"
            )
    
    # Check condenser relationship before gap
    if cdwrt_before is not None and chwst_before is not None:
        if cdwrt_before <= chwst_before:
            violations.append(
                f"Condenser temp <= evaporator temp before gap: "
                f"CDWRT ({cdwrt_before:.2f}°C) <= CHWST ({chwst_before:.2f}°C)"
            )
    
    # Check condenser relationship after gap
    if cdwrt_after is not None and chwst_after is not None:
        if cdwrt_after <= chwst_after:
            violations.append(
                f"Condenser temp <= evaporator temp after gap: "
                f"CDWRT ({cdwrt_after:.2f}°C) <= CHWST ({chwst_after:.2f}°C)"
            )
    
    return {
        "physics_valid": len(violations) == 0,
        "violations": violations,
    }

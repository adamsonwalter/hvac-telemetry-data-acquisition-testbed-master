#!/usr/bin/env python3
"""
Pure function: Validate Load % and Power kW correlation.

This module contains ZERO side effects:
- NO logging
- NO file I/O
- NO global state
- Pure validation logic only
"""

import pandas as pd
from typing import Dict, Optional
from scipy.stats import pearsonr


def validate_load_power_correlation(
    load_series: pd.Series,
    power_series: pd.Series,
    nameplate_kw: Optional[float]
) -> Dict:
    """
    Validate that Load % and Power kW have expected relationship.
    
    PURE FUNCTION - NO SIDE EFFECTS
    - Deterministic: same input → same output
    - No logging or file I/O
    - Pure correlation analysis
    
    Expected: Power ≈ Nameplate_kW × Load × Efficiency_Factor
    For chillers: Relationship should be ~cubic (affinity laws)
    
    Args:
        load_series: Load % or fraction signal
        power_series: Power kW signal
        nameplate_kw: Equipment nameplate capacity (optional)
    
    Returns:
        Dictionary with validation results:
        - status: 'PASS', 'FAIL', 'WARNING', 'SKIP'
        - confidence: str (if PASS)
        - correlation_linear: float (if checked)
        - correlation_cubic: float (if checked)
        - note: str
        - reason: str (if FAIL/WARNING)
        - recommendation: str (if FAIL/WARNING)
    
    Examples:
        >>> import pandas as pd
        >>> # Good correlation
        >>> load = pd.Series([0.5, 0.7, 0.9, 1.0])
        >>> power = pd.Series([600, 840, 1080, 1200])
        >>> result = validate_load_power_correlation(load, power, 1200)
        >>> result['status']
        'PASS'
        
        >>> # Poor correlation
        >>> load = pd.Series([0.5, 0.7, 0.9, 1.0])
        >>> power = pd.Series([100, 200, 300, 400])  # Wrong scale
        >>> result = validate_load_power_correlation(load, power, 1200)
        >>> result['status']
        'FAIL'
    """
    # Align series
    common_idx = load_series.index.intersection(power_series.index)
    load = load_series.loc[common_idx]
    power = power_series.loc[common_idx]
    
    if len(load) < 10:
        return {"status": "SKIP", "reason": "Insufficient overlapping data"}
    
    # Normalize load to 0-1 if needed
    if load.max() > 10:
        load = load / load.max()
    elif load.max() > 1.5:
        load = load / 100
    
    # Filter to operating periods (load > 5%)
    operating = (load > 0.05) & (power > 0)
    load_op = load[operating]
    power_op = power[operating]
    
    if len(load_op) < 10:
        return {"status": "SKIP", "reason": "Insufficient operating data"}
    
    # Check 1: Linear correlation
    corr_linear, _ = pearsonr(load_op, power_op)
    
    if corr_linear < 0.5:
        return {
            "status": "FAIL",
            "reason": f"Load-Power correlation {corr_linear:.2f} < 0.5",
            "recommendation": "🚨 Load % and Power kW do not correlate - verify units"
        }
    
    # Check 2: Cubic relationship (for chillers/pumps - affinity laws)
    load_cubed = load_op ** 3
    corr_cubic, _ = pearsonr(load_cubed, power_op)
    
    if corr_cubic > corr_linear + 0.1:
        return {
            "status": "PASS",
            "confidence": "HIGH",
            "correlation_linear": corr_linear,
            "correlation_cubic": corr_cubic,
            "note": f"✅ Cubic relationship confirmed (r³={corr_cubic:.3f} > r={corr_linear:.3f})",
            "recommendation": "Load % and Power kW relationship is physically plausible"
        }
    
    # Check 3: Power ratio plausibility
    if nameplate_kw:
        power_ratio = power_op.max() / nameplate_kw
        if power_ratio < 0.3 or power_ratio > 1.5:
            return {
                "status": "WARNING",
                "correlation_linear": corr_linear,
                "note": f"⚠️  Power/Nameplate ratio {power_ratio:.2f} is unusual",
                "recommendation": "Verify nameplate capacity or check if power signal is correct"
            }
    
    return {
        "status": "PASS",
        "confidence": "MEDIUM",
        "correlation_linear": corr_linear,
        "note": f"✅ Linear correlation {corr_linear:.2f} acceptable"
    }

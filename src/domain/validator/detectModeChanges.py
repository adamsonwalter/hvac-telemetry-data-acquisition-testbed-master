#!/usr/bin/env python3
"""
Pure function: Detect if Load > 100% indicates mode change.

This module contains ZERO side effects:
- NO logging
- NO file I/O
- NO global state
- Pure detection logic only
"""

import numpy as np
import pandas as pd
from typing import Dict


def detect_mode_changes(series: pd.Series, signal_name: str) -> Dict:
    """
    Detect if Load > 100% indicates mode change.
    
    PURE FUNCTION - NO SIDE EFFECTS
    - Deterministic: same input → same output
    - No logging or file I/O
    - Pure detection logic
    
    Some chillers switch from % → RT (tons) → capacity index beyond 100%.
    
    Args:
        series: Signal data (cleaned, no NaN)
        signal_name: Name for context (not used in logic, only for metadata)
    
    Returns:
        Dictionary with detection results:
        - has_mode_changes: bool
        - description: str (if mode changes detected)
        - recommendations: List[str] (if mode changes detected)
    
    Examples:
        >>> import pandas as pd
        >>> # Signal with mode change
        >>> signal = pd.Series([50, 80, 100, 120, 150, 180])
        >>> result = detect_mode_changes(signal, 'Chiller_Load')
        >>> result['has_mode_changes']
        True
        
        >>> # Normal signal
        >>> signal = pd.Series([20, 50, 80, 95])
        >>> result = detect_mode_changes(signal, 'Pump_Speed')
        >>> result['has_mode_changes']
        False
    """
    mx = series.max()
    p99 = np.percentile(series, 99)
    
    # Count samples > 100 (assuming some normalization happened)
    if mx > 100:
        over_100_count = (series > 100).sum()
        over_100_pct = over_100_count / len(series) * 100
        
        if over_100_pct > 1:  # More than 1% of samples
            return {
                "has_mode_changes": True,
                "description": f"🚨 MODE CHANGE DETECTED: {over_100_pct:.1f}% of samples > 100",
                "recommendations": [
                    "   → Signal likely switches units beyond 100%",
                    "   → Common: % → Refrigerant Tons (RT) → Capacity Index",
                    "   → Split analysis: [0-100] vs [>100] separately",
                    "   → Contact vendor for unit documentation"
                ]
            }
    
    # Detect sudden step changes (possible mode shifts)
    diffs = series.diff().abs()
    large_steps = (diffs > 50).sum()  # Steps > 50 units
    
    if large_steps > len(series) * 0.005:  # >0.5% of samples
        return {
            "has_mode_changes": True,
            "description": f"⚠️  {large_steps} large step changes detected (>50 unit jumps)",
            "recommendations": [
                "   → Possible unit changes mid-stream",
                "   → Review time-series plot for discontinuities",
                "   → Verify BMS configuration changes"
            ]
        }
    
    return {"has_mode_changes": False}

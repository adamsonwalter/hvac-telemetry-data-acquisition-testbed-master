#!/usr/bin/env python3
"""
Pure function: Detect if signal is Load % or Real kW.

This module contains ZERO side effects:
- NO logging
- NO file I/O
- NO global state
- Pure detection logic only
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional


def detect_load_vs_kw(
    series: pd.Series, 
    nameplate_kw: Optional[float], 
    equipment_type: str
) -> Dict:
    """
    Detect if signal is Load % or Real kW.
    
    PURE FUNCTION - NO SIDE EFFECTS
    - Deterministic: same input → same output
    - No logging or file I/O
    - Pure detection logic
    
    Key insight: Load % should not correlate with nameplate,
    but real kW will be bounded by nameplate.
    
    Args:
        series: Signal data (cleaned, no NaN)
        nameplate_kw: Equipment nameplate capacity (optional)
        equipment_type: 'chiller', 'pump', 'fan', 'tower', etc.
    
    Returns:
        Dictionary with detection results:
        - likely_unit: 'REAL_KW', 'LOAD_PERCENT', 'LOAD_FRACTION', etc.
        - confidence: 'high', 'medium', 'low'
        - issues: List of warning messages
        - recommendations: List of recommended actions
    
    Examples:
        >>> import pandas as pd
        >>> # Real kW signal
        >>> kw_signal = pd.Series([100, 500, 1200])
        >>> result = detect_load_vs_kw(kw_signal, 1200, 'chiller')
        >>> result['likely_unit']
        'REAL_KW'
        
        >>> # Load % signal
        >>> pct_signal = pd.Series([0, 50, 100])
        >>> result = detect_load_vs_kw(pct_signal, 1200, 'chiller')
        >>> result['likely_unit']
        'LOAD_PERCENT'
    """
    mn, mx, mean = series.min(), series.max(), series.mean()
    p995 = np.percentile(series, 99.5)
    
    result = {
        "likely_unit": "UNKNOWN",
        "confidence": "low",
        "issues": [],
        "recommendations": []
    }
    
    # Check 1: Value range alignment with nameplate
    if nameplate_kw:
        # If max is close to nameplate → likely real kW
        if 0.6 * nameplate_kw < mx < 1.4 * nameplate_kw:
            result["likely_unit"] = "REAL_KW"
            result["confidence"] = "high"
            result["recommendations"].append(
                f"✅ Detected as REAL kW: Max ({mx:.0f}) aligns with nameplate ({nameplate_kw:.0f} kW)"
            )
            result["recommendations"].append(
                "🚫 DO NOT NORMALIZE - Use raw values for power calculations"
            )
            return result
        
        # If max is 0-1 or 0-100 → likely Load %
        if mx <= 1.05:
            result["likely_unit"] = "LOAD_FRACTION"
            result["confidence"] = "high"
        elif mx <= 110:
            result["likely_unit"] = "LOAD_PERCENT"
            result["confidence"] = "high"
    
    # Check 2: Unrealistic average for load signal
    if mean / (mx + 0.001) > 0.7:  # Mean > 70% of max
        result["issues"].append(
            f"⚠️  SUSPICIOUS: Average ({mean:.1f}) is {mean/(mx+0.001)*100:.0f}% of max"
        )
        result["issues"].append(
            "   Equipment rarely operates >70% average load"
        )
        result["recommendations"].append(
            "   → Verify if this is actually kW, not Load %"
        )
        result["confidence"] = "low"
    
    # Check 3: kW range check for specific equipment
    kw_ranges = {
        "chiller": (50, 5000),    # Chillers typically 50-5000 kW
        "pump": (5, 500),         # Pumps typically 5-500 kW
        "fan": (5, 200),          # Fans typically 5-200 kW
        "tower": (10, 300),       # Cooling tower fans 10-300 kW
    }
    
    if equipment_type in kw_ranges:
        kw_min, kw_max = kw_ranges[equipment_type]
        if kw_min < mx < kw_max:
            if not nameplate_kw:  # No nameplate to contradict
                result["likely_unit"] = "POSSIBLE_REAL_KW"
                result["confidence"] = "medium"
                result["recommendations"].append(
                    f"⚠️  Max ({mx:.0f}) falls in typical {equipment_type} kW range ({kw_min}-{kw_max})"
                )
                result["recommendations"].append(
                    "   → Verify with BMS documentation or nameplate"
                )
    
    return result

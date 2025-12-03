#!/usr/bin/env python3
"""
Pure function: Detect kW vs kWh confusion.

This module contains ZERO side effects:
- NO logging
- NO file I/O
- NO global state
- Pure detection logic only
"""

import pandas as pd
from typing import Dict, Optional
from scipy.stats import pearsonr


def detect_kwh_confusion(
    signal_series: pd.Series,
    power_series: Optional[pd.Series],
    signal_name: str
) -> Dict:
    """
    Detect kW vs kWh (instantaneous vs cumulative) confusion.
    
    PURE FUNCTION - NO SIDE EFFECTS
    - Deterministic: same input → same output
    - No logging or file I/O
    - Pure detection logic
    
    Key insight:
    - kWh (cumulative) should be monotonic increasing
    - kW (instantaneous) should vary up/down
    
    Args:
        signal_series: Signal data to check
        power_series: Reference power signal (optional, for correlation check)
        signal_name: Name for context
    
    Returns:
        Dictionary with detection results:
        - is_confused: bool
        - description: str (if confused)
        - recommendations: List[str] (if confused)
    
    Examples:
        >>> import pandas as pd
        >>> # Cumulative kWh mislabeled as kW
        >>> kwh_signal = pd.Series([0, 100, 200, 300, 400])
        >>> result = detect_kwh_confusion(kwh_signal, None, 'Chiller_kW')
        >>> result['is_confused']
        True
        
        >>> # True instantaneous kW
        >>> kw_signal = pd.Series([100, 150, 120, 180, 90])
        >>> result = detect_kwh_confusion(kw_signal, None, 'Chiller_kW')
        >>> result['is_confused']
        False
    """
    s = signal_series.dropna()
    
    if len(s) == 0:
        return {"is_confused": False}
    
    # Check 1: Monotonicity (cumulative signals always increase)
    diffs = s.diff().dropna()
    negative_diffs = (diffs < -0.01).sum()  # Allow tiny floating point errors
    negative_pct = negative_diffs / len(diffs) * 100
    
    if negative_pct < 1:  # <1% negative diffs → likely cumulative
        # But is it labeled as kW?
        if "kw" in signal_name.lower() and "kwh" not in signal_name.lower():
            return {
                "is_confused": True,
                "description": "🚨 kW/kWh CONFUSION: Signal is monotonic (cumulative) but labeled as kW",
                "recommendations": [
                    "   → This is kWh (cumulative), NOT kW (instantaneous)",
                    "   → DO NOT integrate - differentiate instead",
                    "   → kW = diff(kWh) / diff(time_hours)",
                    "   → Fix BMS point label"
                ]
            }
    
    # Check 2: Variance (instantaneous signals vary more)
    cv = s.std() / (s.mean() + 0.001)  # Coefficient of variation
    
    if cv < 0.05:  # Very low variation
        if s.mean() > 0 and s.max() / s.mean() < 1.2:
            return {
                "is_confused": True,
                "description": "⚠️  Signal shows very low variation - possible cumulative counter",
                "recommendations": [
                    "   → CV < 0.05 suggests cumulative kWh, not instantaneous kW",
                    "   → Verify with time-series plot",
                    "   → Check if values always increase"
                ]
            }
    
    # Check 3: Cross-check with another power signal
    if power_series is not None:
        # If this signal is cumulative, its diff should correlate with power_series
        s_diff = s.diff()
        
        # Align indices
        common_idx = s_diff.dropna().index.intersection(power_series.index)
        if len(common_idx) > 10:
            corr, _ = pearsonr(
                s_diff.loc[common_idx],
                power_series.loc[common_idx]
            )
            
            if corr > 0.7:
                return {
                    "is_confused": True,
                    "description": f"✅ Signal is cumulative kWh (diff correlates {corr:.2f} with kW)",
                    "recommendations": [
                        "   → Differentiate to get instantaneous kW",
                        "   → kW = diff(kWh) / diff(time_hours)"
                    ]
                }
    
    return {"is_confused": False}

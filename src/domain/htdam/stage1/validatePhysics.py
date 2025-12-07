"""
HTDAM Stage 1: Physics Validation

Pure functions for validating physics constraints on BMD signals.
ZERO side effects - no logging, no file I/O, no global state.

Physics constraints:
1. Temperature ranges: CHWST (3-20°C), CHWRT (5-30°C), CDWRT (15-45°C)
2. Temperature relationships: CHWRT ≥ CHWST, CDWRT > CHWST
3. Non-negative values: Flow ≥ 0, Power ≥ 0
"""

from typing import Dict, Tuple, List
import pandas as pd
import numpy as np

from ..constants import (
    # Temperature ranges
    CHWST_VALID_MIN_C,
    CHWST_VALID_MAX_C,
    CHWRT_VALID_MIN_C,
    CHWRT_VALID_MAX_C,
    CDWRT_VALID_MIN_C,
    CDWRT_VALID_MAX_C,
    # Flow and power ranges
    FLOW_VALID_MIN_m3s,
    FLOW_VALID_MAX_m3s,
    POWER_VALID_MIN_kW,
    POWER_VALID_MAX_kW,
    # Halt thresholds
    HALT_THRESHOLD_PHYSICS_VIOLATION_PCT,
    HALT_THRESHOLD_NEGATIVE_VALUES_PCT,
)


def validate_temperature_range(
    series: pd.Series,
    signal_name: str,
    valid_min: float,
    valid_max: float,
) -> Dict:
    """
    Pure function: Validate temperature is within valid range.
    
    Args:
        series: Temperature data (in °C)
        signal_name: Name of signal (for metadata)
        valid_min: Minimum valid temperature (°C)
        valid_max: Maximum valid temperature (°C)
    
    Returns:
        Dict with validation results:
        {
            "signal_name": str,
            "violations_count": int,
            "violations_pct": float,
            "outside_range_indices": list,
            "valid_min": float,
            "valid_max": float,
            "actual_min": float,
            "actual_max": float,
        }
    
    Examples:
        >>> temps = pd.Series([6, 8, 10, 12, 14])
        >>> result = validate_temperature_range(temps, "CHWST", 3.0, 20.0)
        >>> result["violations_count"]
        0
        
        >>> temps_bad = pd.Series([2, 8, 10, 25])  # 2°C too low, 25°C too high
        >>> result = validate_temperature_range(temps_bad, "CHWST", 3.0, 20.0)
        >>> result["violations_count"]
        2
        >>> result["violations_pct"]
        50.0
    """
    # Find violations
    outside_range = (series < valid_min) | (series > valid_max)
    violations_count = int(outside_range.sum())
    total_count = len(series.dropna())
    violations_pct = (violations_count / total_count * 100) if total_count > 0 else 0.0
    
    # Get indices of violations
    outside_range_indices = series[outside_range].index.tolist()
    
    # Calculate actual range
    actual_min = float(series.min())
    actual_max = float(series.max())
    
    return {
        "signal_name": signal_name,
        "violations_count": violations_count,
        "violations_pct": violations_pct,
        "outside_range_indices": outside_range_indices,
        "valid_min": valid_min,
        "valid_max": valid_max,
        "actual_min": actual_min,
        "actual_max": actual_max,
    }


def validate_temperature_relationships(
    chwst: pd.Series,
    chwrt: pd.Series,
    cdwrt: pd.Series,
) -> Dict:
    """
    Pure function: Validate temperature relationships.
    
    Physics constraints:
    - CHWRT must be ≥ CHWST (return temp must be warmer than supply)
    - CDWRT must be > CHWST (condenser return must be warmer than chilled water supply)
    
    Args:
        chwst: Chilled Water Supply Temperature (°C)
        chwrt: Chilled Water Return Temperature (°C)
        cdwrt: Condenser Water Return Temperature (°C)
    
    Returns:
        Dict with validation results for both relationships
        
    Examples:
        >>> chwst = pd.Series([6, 8, 10])
        >>> chwrt = pd.Series([12, 14, 16])
        >>> cdwrt = pd.Series([20, 22, 24])
        >>> result = validate_temperature_relationships(chwst, chwrt, cdwrt)
        >>> result["chwrt_lt_chwst_count"]
        0
        >>> result["cdwrt_lte_chwst_count"]
        0
    """
    total_count = len(chwst.dropna())
    
    # Check CHWRT < CHWST (violation)
    chwrt_lt_chwst = chwrt < chwst
    chwrt_lt_chwst_count = int(chwrt_lt_chwst.sum())
    chwrt_lt_chwst_pct = (chwrt_lt_chwst_count / total_count * 100) if total_count > 0 else 0.0
    chwrt_lt_chwst_indices = chwst[chwrt_lt_chwst].index.tolist()
    
    # Check CDWRT ≤ CHWST (violation)
    cdwrt_lte_chwst = cdwrt <= chwst
    cdwrt_lte_chwst_count = int(cdwrt_lte_chwst.sum())
    cdwrt_lte_chwst_pct = (cdwrt_lte_chwst_count / total_count * 100) if total_count > 0 else 0.0
    cdwrt_lte_chwst_indices = chwst[cdwrt_lte_chwst].index.tolist()
    
    return {
        "chwrt_lt_chwst_count": chwrt_lt_chwst_count,
        "chwrt_lt_chwst_pct": chwrt_lt_chwst_pct,
        "chwrt_lt_chwst_indices": chwrt_lt_chwst_indices,
        "cdwrt_lte_chwst_count": cdwrt_lte_chwst_count,
        "cdwrt_lte_chwst_pct": cdwrt_lte_chwst_pct,
        "cdwrt_lte_chwst_indices": cdwrt_lte_chwst_indices,
        "total_samples": total_count,
    }


def validate_non_negative(
    series: pd.Series,
    signal_name: str,
) -> Dict:
    """
    Pure function: Validate signal has no negative values.
    
    Used for Flow and Power, which must be ≥ 0.
    
    Args:
        series: Signal data
        signal_name: Name of signal (for metadata)
    
    Returns:
        Dict with validation results:
        {
            "signal_name": str,
            "negative_count": int,
            "negative_pct": float,
            "negative_indices": list,
            "actual_min": float,
        }
        
    Examples:
        >>> flow = pd.Series([0.05, 0.08, 0.10])
        >>> result = validate_non_negative(flow, "FLOW")
        >>> result["negative_count"]
        0
        
        >>> power_bad = pd.Series([100, 150, -10, 200])
        >>> result = validate_non_negative(power_bad, "POWER")
        >>> result["negative_count"]
        1
        >>> result["negative_pct"]
        25.0
    """
    # Find negative values
    negative = series < 0
    negative_count = int(negative.sum())
    total_count = len(series.dropna())
    negative_pct = (negative_count / total_count * 100) if total_count > 0 else 0.0
    
    # Get indices of negative values
    negative_indices = series[negative].index.tolist()
    
    # Calculate actual minimum
    actual_min = float(series.min())
    
    return {
        "signal_name": signal_name,
        "negative_count": negative_count,
        "negative_pct": negative_pct,
        "negative_indices": negative_indices,
        "actual_min": actual_min,
    }


def validate_all_physics(
    df: pd.DataFrame,
    signal_mappings: Dict[str, str],
) -> Dict:
    """
    Pure function: Validate all physics constraints for BMD signals.
    
    Args:
        df: DataFrame with converted signals (chwst, chwrt, cdwrt, flow_m3s, power_kw)
        signal_mappings: Dict mapping BMD channels to original column names
    
    Returns:
        Dict with all validation results:
        {
            "temperature_ranges": {...},
            "temperature_relationships": {...},
            "non_negative": {...},
            "halt_required": bool,
            "halt_reasons": list,
        }
        
    Example:
        >>> df = pd.DataFrame({
        ...     "chwst": [6, 8, 10],
        ...     "chwrt": [12, 14, 16],
        ...     "cdwrt": [20, 22, 24],
        ...     "flow_m3s": [0.05, 0.08, 0.10],
        ...     "power_kw": [100, 150, 200]
        ... })
        >>> result = validate_all_physics(df, {})
        >>> result["halt_required"]
        False
    """
    validations = {
        "temperature_ranges": {},
        "temperature_relationships": {},
        "non_negative": {},
        "halt_required": False,
        "halt_reasons": [],
    }
    
    # Validate temperature ranges
    if "chwst" in df.columns:
        validations["temperature_ranges"]["CHWST"] = validate_temperature_range(
            df["chwst"], "CHWST", CHWST_VALID_MIN_C, CHWST_VALID_MAX_C
        )
    
    if "chwrt" in df.columns:
        validations["temperature_ranges"]["CHWRT"] = validate_temperature_range(
            df["chwrt"], "CHWRT", CHWRT_VALID_MIN_C, CHWRT_VALID_MAX_C
        )
    
    if "cdwrt" in df.columns:
        validations["temperature_ranges"]["CDWRT"] = validate_temperature_range(
            df["cdwrt"], "CDWRT", CDWRT_VALID_MIN_C, CDWRT_VALID_MAX_C
        )
    
    # Validate temperature relationships
    if all(col in df.columns for col in ["chwst", "chwrt", "cdwrt"]):
        validations["temperature_relationships"] = validate_temperature_relationships(
            df["chwst"], df["chwrt"], df["cdwrt"]
        )
    
    # Validate non-negative (flow and power)
    if "flow_m3s" in df.columns:
        validations["non_negative"]["FLOW"] = validate_non_negative(
            df["flow_m3s"], "FLOW"
        )
    
    if "power_kw" in df.columns:
        validations["non_negative"]["POWER"] = validate_non_negative(
            df["power_kw"], "POWER"
        )
    
    # Check HALT conditions
    halt_reasons = []
    
    # Check temperature range violations (>1%)
    for signal, result in validations["temperature_ranges"].items():
        if result["violations_pct"] > HALT_THRESHOLD_PHYSICS_VIOLATION_PCT:
            halt_reasons.append(
                f"{signal} has {result['violations_pct']:.1f}% samples outside valid range "
                f"({result['valid_min']}-{result['valid_max']}°C)"
            )
    
    # Check temperature relationship violations (>1%)
    temp_rel = validations["temperature_relationships"]
    if temp_rel:
        if temp_rel["chwrt_lt_chwst_pct"] > HALT_THRESHOLD_PHYSICS_VIOLATION_PCT:
            halt_reasons.append(
                f"CHWRT < CHWST in {temp_rel['chwrt_lt_chwst_pct']:.1f}% of samples "
                f"(violates physics: return temp must be ≥ supply temp)"
            )
        
        if temp_rel["cdwrt_lte_chwst_pct"] > HALT_THRESHOLD_PHYSICS_VIOLATION_PCT:
            halt_reasons.append(
                f"CDWRT ≤ CHWST in {temp_rel['cdwrt_lte_chwst_pct']:.1f}% of samples "
                f"(violates physics: condenser return must be > chilled water supply)"
            )
    
    # Check negative values (ANY negative = HALT)
    for signal, result in validations["non_negative"].items():
        if result["negative_pct"] > HALT_THRESHOLD_NEGATIVE_VALUES_PCT:
            halt_reasons.append(
                f"{signal} has {result['negative_count']} negative values "
                f"({result['negative_pct']:.1f}% of samples)"
            )
    
    validations["halt_required"] = len(halt_reasons) > 0
    validations["halt_reasons"] = halt_reasons
    
    return validations


def compute_physics_confidence(
    validation_results: Dict,
) -> Tuple[float, bool, List[str]]:
    """
    Pure function: Compute overall physics confidence score.
    
    Confidence formula:
    - Start at 1.0
    - Subtract 0.10 for each 1% of physics violations
    - HALT if violations > 1%
    
    Args:
        validation_results: Output from validate_all_physics()
    
    Returns:
        (confidence_score, should_halt, halt_reasons)
        
    Examples:
        >>> # Perfect physics
        >>> results = {
        ...     "temperature_ranges": {
        ...         "CHWST": {"violations_pct": 0.0},
        ...         "CHWRT": {"violations_pct": 0.0}
        ...     },
        ...     "temperature_relationships": {
        ...         "chwrt_lt_chwst_pct": 0.0,
        ...         "cdwrt_lte_chwst_pct": 0.0
        ...     },
        ...     "non_negative": {
        ...         "FLOW": {"negative_pct": 0.0},
        ...         "POWER": {"negative_pct": 0.0}
        ...     },
        ...     "halt_required": False,
        ...     "halt_reasons": []
        ... }
        >>> confidence, halt, reasons = compute_physics_confidence(results)
        >>> confidence
        1.0
        >>> halt
        False
    """
    confidence = 1.0
    
    # Check for HALT conditions
    if validation_results.get("halt_required", False):
        return (0.0, True, validation_results.get("halt_reasons", []))
    
    # Calculate penalty from violations
    total_violation_pct = 0.0
    
    # Temperature range violations
    for signal, result in validation_results.get("temperature_ranges", {}).items():
        total_violation_pct += result.get("violations_pct", 0.0)
    
    # Temperature relationship violations
    temp_rel = validation_results.get("temperature_relationships", {})
    if temp_rel:
        total_violation_pct += temp_rel.get("chwrt_lt_chwst_pct", 0.0)
        total_violation_pct += temp_rel.get("cdwrt_lte_chwst_pct", 0.0)
    
    # Non-negative violations
    for signal, result in validation_results.get("non_negative", {}).items():
        total_violation_pct += result.get("negative_pct", 0.0)
    
    # Apply penalty: -0.10 for each 1% violation
    penalty = total_violation_pct / 100.0 * 0.10
    confidence = max(0.0, confidence - penalty)
    
    return (confidence, False, [])

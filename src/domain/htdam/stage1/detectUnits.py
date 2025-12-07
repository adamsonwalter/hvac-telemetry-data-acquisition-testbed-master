"""
HTDAM Stage 1: Unit Detection

Pure functions for detecting units from signal data.
ZERO side effects - no logging, no file I/O, no global state.

Detection strategy:
1. Check metadata (column names, headers) for explicit unit strings
2. Use range analysis on 99.5th percentile for robust outlier handling
3. Return (unit_string, confidence_score)
"""

from typing import Dict, Optional, Tuple
import pandas as pd
import numpy as np

from ..constants import (
    # Temperature constants
    TEMP_C_RANGE_MIN,
    TEMP_C_RANGE_MAX,
    TEMP_F_RANGE_MIN,
    TEMP_F_RANGE_MAX,
    TEMP_K_RANGE_MIN,
    TEMP_K_RANGE_MAX,
    # Flow constants
    FLOW_M3S_RANGE_MAX,
    FLOW_LS_RANGE_MAX,
    FLOW_M3H_RANGE_MAX,
    FLOW_GPM_RANGE_MAX,
    # Power constants
    POWER_W_RANGE_MIN,
    POWER_KW_RANGE_MIN,
    POWER_KW_RANGE_MAX,
    POWER_MW_RANGE_MAX,
    # General
    PERCENTILE_ROBUST,
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
    CONFIDENCE_UNKNOWN,
    UNIT_NORMALIZATION,
)


def _parse_unit_from_metadata(
    signal_name: str,
    metadata: Optional[Dict] = None,
) -> Optional[str]:
    """
    Pure function: Extract unit string from signal name or metadata.
    
    Args:
        signal_name: Name of the signal (e.g., "CHWST_degC", "Flow_GPM")
        metadata: Optional dict with additional metadata (e.g., {"unit": "°C"})
    
    Returns:
        Normalized unit string or None if not found
        
    Examples:
        >>> _parse_unit_from_metadata("CHWST_degC")
        'C'
        >>> _parse_unit_from_metadata("Flow_GPM")
        'GPM'
        >>> _parse_unit_from_metadata("Power", {"unit": "kW"})
        'kW'
    """
    # Check metadata first
    if metadata and "unit" in metadata:
        unit_str = str(metadata["unit"]).strip()
        if unit_str in UNIT_NORMALIZATION:
            return UNIT_NORMALIZATION[unit_str]
    
    # Check signal name for common patterns
    signal_upper = signal_name.upper()
    
    # Temperature patterns
    if "DEGC" in signal_upper or "_C" in signal_upper or "°C" in signal_name:
        return "C"
    if "DEGF" in signal_upper or "_F" in signal_upper or "°F" in signal_name:
        return "F"
    if "KELVIN" in signal_upper or "_K" in signal_upper:
        return "K"
    
    # Flow patterns
    if "M3/S" in signal_upper or "M3S" in signal_upper:
        return "m3/s"
    if "L/S" in signal_upper or "LPS" in signal_upper or "LS" in signal_upper:
        return "L/s"
    if "GPM" in signal_upper:
        return "GPM"
    if "M3/H" in signal_upper or "M3H" in signal_upper:
        return "m3/h"
    
    # Power patterns
    if "_KW" in signal_upper or "KW_" in signal_upper or signal_upper.endswith("KW"):
        return "kW"
    if "_MW" in signal_upper or "MW_" in signal_upper or signal_upper.endswith("MW"):
        return "MW"
    if "_W" in signal_upper or signal_upper.endswith("_WATT"):
        return "W"
    
    return None


def detect_temperature_unit(
    series: pd.Series,
    signal_name: str = "",
    metadata: Optional[Dict] = None,
) -> Tuple[Optional[str], float]:
    """
    Pure function: Detect temperature unit (C, F, or K).
    
    Strategy:
    1. Check metadata/signal name for explicit unit
    2. Use 99.5th percentile for range analysis (robust to outliers)
    3. Match against expected ranges
    
    Args:
        series: Temperature signal data
        signal_name: Name of signal (for metadata parsing)
        metadata: Optional dict with unit info
    
    Returns:
        (unit_string, confidence_score)
        unit_string: "C", "F", "K", or None
        confidence: 0.0-1.0
        
    Examples:
        >>> series = pd.Series([6, 8, 10, 12, 14])  # Typical CHWST in °C
        >>> detect_temperature_unit(series, "CHWST")
        ('C', 0.95)
        
        >>> series = pd.Series([43, 46, 50, 54, 57])  # Typical CHWST in °F
        >>> detect_temperature_unit(series, "CHWST_degF")
        ('F', 1.0)  # High confidence from metadata + range
    """
    # Check metadata first
    metadata_unit = _parse_unit_from_metadata(signal_name, metadata)
    if metadata_unit in ("C", "F", "K"):
        return (metadata_unit, CONFIDENCE_HIGH)
    
    # Calculate robust percentile (not max, to handle outliers)
    p995 = np.percentile(series.dropna(), PERCENTILE_ROBUST)
    p05 = np.percentile(series.dropna(), 100 - PERCENTILE_ROBUST)
    
    # Check Celsius range (most common for HVAC)
    if TEMP_C_RANGE_MIN <= p05 <= TEMP_C_RANGE_MAX and TEMP_C_RANGE_MIN <= p995 <= TEMP_C_RANGE_MAX:
        return ("C", CONFIDENCE_MEDIUM)
    
    # Check Fahrenheit range
    if TEMP_F_RANGE_MIN <= p05 <= TEMP_F_RANGE_MAX and TEMP_F_RANGE_MIN <= p995 <= TEMP_F_RANGE_MAX:
        return ("F", CONFIDENCE_MEDIUM)
    
    # Check Kelvin range
    if TEMP_K_RANGE_MIN <= p05 <= TEMP_K_RANGE_MAX and TEMP_K_RANGE_MIN <= p995 <= TEMP_K_RANGE_MAX:
        return ("K", CONFIDENCE_MEDIUM)
    
    # Unable to determine
    return (None, CONFIDENCE_UNKNOWN)


def detect_flow_unit(
    series: pd.Series,
    signal_name: str = "",
    metadata: Optional[Dict] = None,
) -> Tuple[Optional[str], float]:
    """
    Pure function: Detect flow unit (m3/s, L/s, GPM, m3/h).
    
    Strategy:
    1. Check metadata/signal name for explicit unit
    2. Use 99.5th percentile for magnitude analysis
    3. Match against expected ranges
    
    Args:
        series: Flow signal data
        signal_name: Name of signal
        metadata: Optional dict with unit info
    
    Returns:
        (unit_string, confidence_score)
        unit_string: "m3/s", "L/s", "GPM", "m3/h", or None
        confidence: 0.0-1.0
        
    Examples:
        >>> series = pd.Series([0.05, 0.08, 0.10, 0.12])  # m³/s
        >>> detect_flow_unit(series, "CHWF")
        ('m3/s', 0.80)
        
        >>> series = pd.Series([50, 80, 100, 120])  # L/s
        >>> detect_flow_unit(series, "Flow_LPS")
        ('L/s', 0.95)
    """
    # Check metadata first
    metadata_unit = _parse_unit_from_metadata(signal_name, metadata)
    if metadata_unit in ("m3/s", "L/s", "GPM", "m3/h"):
        return (metadata_unit, CONFIDENCE_HIGH)
    
    # Calculate robust percentile
    p995 = np.percentile(series.dropna(), PERCENTILE_ROBUST)
    
    # Check m³/s range (smallest magnitude)
    if p995 < FLOW_M3S_RANGE_MAX:
        return ("m3/s", CONFIDENCE_MEDIUM)
    
    # Check L/s range
    if p995 < FLOW_LS_RANGE_MAX:
        return ("L/s", CONFIDENCE_MEDIUM)
    
    # Check m³/h range
    if p995 < FLOW_M3H_RANGE_MAX:
        return ("m3/h", CONFIDENCE_MEDIUM)
    
    # Check GPM range (largest magnitude)
    if p995 < FLOW_GPM_RANGE_MAX:
        return ("GPM", CONFIDENCE_LOW)  # Lower confidence (wide range)
    
    # Unable to determine
    return (None, CONFIDENCE_UNKNOWN)


def detect_power_unit(
    series: pd.Series,
    signal_name: str = "",
    metadata: Optional[Dict] = None,
) -> Tuple[Optional[str], float]:
    """
    Pure function: Detect power unit (W, kW, or MW).
    
    Strategy:
    1. Check metadata/signal name for explicit unit
    2. Use 99.5th percentile for magnitude analysis
    3. Match against expected ranges
    
    Args:
        series: Power signal data
        signal_name: Name of signal
        metadata: Optional dict with unit info
    
    Returns:
        (unit_string, confidence_score)
        unit_string: "W", "kW", "MW", or None
        confidence: 0.0-1.0
        
    Examples:
        >>> series = pd.Series([50, 100, 200, 300])  # kW
        >>> detect_power_unit(series, "Chiller_Power")
        ('kW', 0.80)
        
        >>> series = pd.Series([50000, 100000, 200000])  # W
        >>> detect_power_unit(series, "Power_W")
        ('W', 0.95)
    """
    # Check metadata first
    metadata_unit = _parse_unit_from_metadata(signal_name, metadata)
    if metadata_unit in ("W", "kW", "MW"):
        return (metadata_unit, CONFIDENCE_HIGH)
    
    # Calculate robust percentile and minimum
    p995 = np.percentile(series.dropna(), PERCENTILE_ROBUST)
    p05 = np.percentile(series.dropna(), 5.0)  # Lower bound
    
    # Check if values are in Watts (very large numbers)
    if p05 > POWER_W_RANGE_MIN:
        return ("W", CONFIDENCE_MEDIUM)
    
    # Check if values are in MW (very small numbers)
    if p995 < POWER_MW_RANGE_MAX:
        return ("MW", CONFIDENCE_LOW)  # Lower confidence (could be kW)
    
    # Check if values are in kW (most common for chillers)
    if POWER_KW_RANGE_MIN <= p05 and p995 <= POWER_KW_RANGE_MAX:
        return ("kW", CONFIDENCE_MEDIUM)
    
    # Default to kW for typical chiller range
    if POWER_KW_RANGE_MIN <= p995 <= POWER_KW_RANGE_MAX * 2:
        return ("kW", CONFIDENCE_LOW)
    
    # Unable to determine
    return (None, CONFIDENCE_UNKNOWN)


def detect_all_units(
    df: pd.DataFrame,
    signal_mappings: Dict[str, str],
    metadata: Optional[Dict] = None,
) -> Dict[str, Tuple[Optional[str], float]]:
    """
    Pure function: Detect units for all BMD signals in DataFrame.
    
    Args:
        df: DataFrame with raw signals
        signal_mappings: Dict mapping BMD channels to column names
            e.g., {"CHWST": "Chiller_1_CHWST", "CHWRT": "Chiller_1_CHWRT", ...}
        metadata: Optional dict with per-signal metadata
            e.g., {"Chiller_1_CHWST": {"unit": "°C"}}
    
    Returns:
        Dict mapping BMD channel to (detected_unit, confidence)
        e.g., {"CHWST": ("C", 0.95), "CHWRT": ("C", 0.95), ...}
        
    Example:
        >>> df = pd.DataFrame({
        ...     "CHWST": [6, 8, 10],
        ...     "CHWRT": [12, 14, 16],
        ...     "CDWRT": [20, 22, 24],
        ...     "Flow": [0.05, 0.08, 0.10],
        ...     "Power": [100, 150, 200]
        ... })
        >>> mappings = {
        ...     "CHWST": "CHWST",
        ...     "CHWRT": "CHWRT",
        ...     "CDWRT": "CDWRT",
        ...     "FLOW": "Flow",
        ...     "POWER": "Power"
        ... }
        >>> detect_all_units(df, mappings)
        {
            'CHWST': ('C', 0.80),
            'CHWRT': ('C', 0.80),
            'CDWRT': ('C', 0.80),
            'FLOW': ('m3/s', 0.80),
            'POWER': ('kW', 0.80)
        }
    """
    results = {}
    
    for bmd_channel, col_name in signal_mappings.items():
        if col_name not in df.columns:
            results[bmd_channel] = (None, CONFIDENCE_UNKNOWN)
            continue
        
        series = df[col_name]
        signal_metadata = metadata.get(col_name) if metadata else None
        
        # Detect based on channel type
        if bmd_channel in ("CHWST", "CHWRT", "CDWRT"):
            unit, confidence = detect_temperature_unit(series, col_name, signal_metadata)
        elif bmd_channel == "FLOW":
            unit, confidence = detect_flow_unit(series, col_name, signal_metadata)
        elif bmd_channel == "POWER":
            unit, confidence = detect_power_unit(series, col_name, signal_metadata)
        else:
            unit, confidence = None, CONFIDENCE_UNKNOWN
        
        results[bmd_channel] = (unit, confidence)
    
    return results

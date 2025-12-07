"""
HTDAM Stage 1: Unit Conversion

Pure functions for converting units to standard SI units.
ZERO side effects - no logging, no file I/O, no global state.

Standard units:
- Temperature: °C
- Flow: m³/s
- Power: kW
"""

from typing import Dict, Tuple
import pandas as pd
import numpy as np

from ..constants import (
    # Conversion functions and factors
    convert_fahrenheit_to_celsius,
    convert_kelvin_to_celsius,
    FLOW_LS_TO_M3S,
    FLOW_GPM_TO_M3S,
    FLOW_M3H_TO_M3S,
    POWER_W_TO_KW,
    POWER_MW_TO_KW,
)


def convert_temperature(
    series: pd.Series,
    from_unit: str,
    to_unit: str = "C",
) -> Tuple[pd.Series, Dict]:
    """
    Pure function: Convert temperature from one unit to another.
    
    Args:
        series: Temperature data
        from_unit: Source unit ("C", "F", "K")
        to_unit: Target unit (default: "C")
    
    Returns:
        (converted_series, metadata_dict)
        
    Examples:
        >>> temps_f = pd.Series([32, 68, 212])
        >>> converted, meta = convert_temperature(temps_f, "F", "C")
        >>> list(converted)
        [0.0, 20.0, 100.0]
        >>> meta['conversion_applied']
        True
        >>> meta['conversion_factor']
        'F_to_C'
    """
    metadata = {
        "from_unit": from_unit,
        "to_unit": to_unit,
        "conversion_applied": False,
        "conversion_factor": None,
    }
    
    # Normalize unit strings
    from_unit = from_unit.upper().replace("°", "")
    to_unit = to_unit.upper().replace("°", "")
    
    # No conversion needed
    if from_unit == to_unit:
        metadata["conversion_applied"] = False
        return series.copy(), metadata
    
    # Apply conversion
    converted = series.copy()
    
    if from_unit == "F" and to_unit == "C":
        converted = converted.apply(convert_fahrenheit_to_celsius)
        metadata["conversion_applied"] = True
        metadata["conversion_factor"] = "F_to_C"
    
    elif from_unit == "K" and to_unit == "C":
        converted = converted.apply(convert_kelvin_to_celsius)
        metadata["conversion_applied"] = True
        metadata["conversion_factor"] = "K_to_C"
    
    elif from_unit == "C" and to_unit == "F":
        # Reverse conversion (rare in HVAC)
        converted = converted * (9.0 / 5.0) + 32.0
        metadata["conversion_applied"] = True
        metadata["conversion_factor"] = "C_to_F"
    
    elif from_unit == "C" and to_unit == "K":
        # Reverse conversion (rare in HVAC)
        converted = converted + 273.15
        metadata["conversion_applied"] = True
        metadata["conversion_factor"] = "C_to_K"
    
    else:
        # Unsupported conversion
        metadata["conversion_applied"] = False
        metadata["error"] = f"Unsupported conversion: {from_unit} to {to_unit}"
    
    return converted, metadata


def convert_flow(
    series: pd.Series,
    from_unit: str,
    to_unit: str = "m3/s",
) -> Tuple[pd.Series, Dict]:
    """
    Pure function: Convert flow rate from one unit to another.
    
    Args:
        series: Flow data
        from_unit: Source unit ("m3/s", "L/s", "GPM", "m3/h")
        to_unit: Target unit (default: "m3/s")
    
    Returns:
        (converted_series, metadata_dict)
        
    Examples:
        >>> flow_ls = pd.Series([50, 80, 100])
        >>> converted, meta = convert_flow(flow_ls, "L/s", "m3/s")
        >>> list(converted)
        [0.05, 0.08, 0.1]
        >>> meta['conversion_factor']
        0.001
    """
    metadata = {
        "from_unit": from_unit,
        "to_unit": to_unit,
        "conversion_applied": False,
        "conversion_factor": None,
    }
    
    # Normalize unit strings
    from_unit_norm = from_unit.lower().replace("³", "3").replace("/", "")
    to_unit_norm = to_unit.lower().replace("³", "3").replace("/", "")
    
    # No conversion needed
    if from_unit_norm == to_unit_norm:
        metadata["conversion_applied"] = False
        return series.copy(), metadata
    
    # Apply conversion to m³/s
    converted = series.copy()
    
    if to_unit_norm == "m3s":
        if from_unit_norm == "ls" or from_unit.upper() == "L/S":
            converted = converted * FLOW_LS_TO_M3S
            metadata["conversion_applied"] = True
            metadata["conversion_factor"] = FLOW_LS_TO_M3S
        
        elif from_unit.upper() == "GPM" or from_unit_norm == "gpm":
            converted = converted * FLOW_GPM_TO_M3S
            metadata["conversion_applied"] = True
            metadata["conversion_factor"] = FLOW_GPM_TO_M3S
        
        elif from_unit_norm == "m3h" or from_unit.upper() == "M3/H":
            converted = converted * FLOW_M3H_TO_M3S
            metadata["conversion_applied"] = True
            metadata["conversion_factor"] = FLOW_M3H_TO_M3S
        
        else:
            metadata["conversion_applied"] = False
            metadata["error"] = f"Unsupported flow unit: {from_unit}"
    
    else:
        # Other target units not currently supported
        metadata["conversion_applied"] = False
        metadata["error"] = f"Unsupported target unit: {to_unit}"
    
    return converted, metadata


def convert_power(
    series: pd.Series,
    from_unit: str,
    to_unit: str = "kW",
) -> Tuple[pd.Series, Dict]:
    """
    Pure function: Convert power from one unit to another.
    
    Args:
        series: Power data
        from_unit: Source unit ("W", "kW", "MW")
        to_unit: Target unit (default: "kW")
    
    Returns:
        (converted_series, metadata_dict)
        
    Examples:
        >>> power_w = pd.Series([50000, 100000, 200000])
        >>> converted, meta = convert_power(power_w, "W", "kW")
        >>> list(converted)
        [50.0, 100.0, 200.0]
        >>> meta['conversion_factor']
        0.001
    """
    metadata = {
        "from_unit": from_unit,
        "to_unit": to_unit,
        "conversion_applied": False,
        "conversion_factor": None,
    }
    
    # Normalize unit strings
    from_unit_norm = from_unit.upper().replace(" ", "")
    to_unit_norm = to_unit.upper().replace(" ", "")
    
    # No conversion needed
    if from_unit_norm == to_unit_norm:
        metadata["conversion_applied"] = False
        return series.copy(), metadata
    
    # Apply conversion to kW
    converted = series.copy()
    
    if to_unit_norm == "KW":
        if from_unit_norm == "W" or from_unit_norm == "WATT":
            converted = converted * POWER_W_TO_KW
            metadata["conversion_applied"] = True
            metadata["conversion_factor"] = POWER_W_TO_KW
        
        elif from_unit_norm == "MW" or from_unit_norm == "MEGAWATT":
            converted = converted * POWER_MW_TO_KW
            metadata["conversion_applied"] = True
            metadata["conversion_factor"] = POWER_MW_TO_KW
        
        else:
            metadata["conversion_applied"] = False
            metadata["error"] = f"Unsupported power unit: {from_unit}"
    
    else:
        # Other target units not currently supported
        metadata["conversion_applied"] = False
        metadata["error"] = f"Unsupported target unit: {to_unit}"
    
    return converted, metadata


def convert_all_units(
    df: pd.DataFrame,
    signal_mappings: Dict[str, str],
    detected_units: Dict[str, Tuple[str, float]],
) -> Tuple[pd.DataFrame, Dict]:
    """
    Pure function: Convert all BMD signals to standard units.
    
    Args:
        df: DataFrame with raw signals
        signal_mappings: Dict mapping BMD channels to column names
        detected_units: Dict from detect_all_units()
            e.g., {"CHWST": ("F", 0.95), "FLOW": ("GPM", 0.90), ...}
    
    Returns:
        (df_with_converted_columns, conversions_metadata)
        
    Example:
        >>> df = pd.DataFrame({
        ...     "CHWST": [50, 55, 60],  # °F
        ...     "Flow": [100, 150, 200],  # GPM
        ... })
        >>> mappings = {"CHWST": "CHWST", "FLOW": "Flow"}
        >>> units = {"CHWST": ("F", 0.95), "FLOW": ("GPM", 0.90)}
        >>> df_converted, meta = convert_all_units(df, mappings, units)
        >>> df_converted.columns.tolist()
        ['CHWST', 'Flow', 'chwst', 'flow_m3s']
    """
    df_result = df.copy()
    conversions = {}
    
    for bmd_channel, col_name in signal_mappings.items():
        if col_name not in df.columns:
            conversions[bmd_channel] = {
                "status": "missing",
                "error": f"Column {col_name} not found in DataFrame",
            }
            continue
        
        detected_unit, detection_conf = detected_units.get(bmd_channel, (None, 0.0))
        
        if detected_unit is None:
            conversions[bmd_channel] = {
                "status": "no_unit_detected",
                "error": "Could not detect unit from data or metadata",
            }
            continue
        
        series = df[col_name]
        
        # Convert based on channel type
        if bmd_channel in ("CHWST", "CHWRT", "CDWRT"):
            converted, meta = convert_temperature(series, detected_unit, "C")
            new_col_name = bmd_channel.lower()
        
        elif bmd_channel == "FLOW":
            converted, meta = convert_flow(series, detected_unit, "m3/s")
            new_col_name = "flow_m3s"
        
        elif bmd_channel == "POWER":
            converted, meta = convert_power(series, detected_unit, "kW")
            new_col_name = "power_kw"
        
        else:
            conversions[bmd_channel] = {
                "status": "unsupported_channel",
                "error": f"Unknown BMD channel: {bmd_channel}",
            }
            continue
        
        # Add converted column to DataFrame
        df_result[new_col_name] = converted
        
        # Store conversion metadata
        conversions[bmd_channel] = {
            "status": "success" if meta.get("conversion_applied") else "no_conversion_needed",
            "from_unit": detected_unit,
            "to_unit": meta["to_unit"],
            "conversion_applied": meta["conversion_applied"],
            "conversion_factor": meta.get("conversion_factor"),
            "detection_confidence": detection_conf,
            "new_column": new_col_name,
        }
    
    return df_result, conversions

"""
HTDAM Stage 1 Constants

Pure constants file - NO code execution, NO side effects.
All physics validation ranges, unit conversion factors, and confidence penalties.

Reference: htdam/stage-1-unit-verification/HTAM Stage 1 Assets/HTDAM_Stage1_Impl_Guide.md
"""

from typing import Dict, Tuple

# ============================================================================
# WATER PROPERTIES (SI Units)
# ============================================================================

WATER_DENSITY_kg_m3: float = 1000.0
"""Water density in kg/m³ at typical chilled water temperatures (10-15°C)"""

WATER_SPECIFIC_HEAT_kJ_kg_K: float = 4.186
"""Water specific heat capacity in kJ/(kg·K)"""

# ============================================================================
# PHYSICS VALIDATION RANGES (Temperature in °C, Flow in m³/s, Power in kW)
# ============================================================================

# Chilled Water Supply Temperature (CHWST)
CHWST_VALID_MIN_C: float = 3.0
"""Minimum valid CHWST in °C (absolute physical limit)"""

CHWST_VALID_MAX_C: float = 20.0
"""Maximum valid CHWST in °C (absolute physical limit)"""

CHWST_TYPICAL_MIN_C: float = 6.0
"""Typical minimum CHWST in °C (efficient operation)"""

CHWST_TYPICAL_MAX_C: float = 15.0
"""Typical maximum CHWST in °C (efficient operation)"""

# Chilled Water Return Temperature (CHWRT)
CHWRT_VALID_MIN_C: float = 5.0
"""Minimum valid CHWRT in °C (absolute physical limit)"""

CHWRT_VALID_MAX_C: float = 30.0
"""Maximum valid CHWRT in °C (absolute physical limit)"""

CHWRT_TYPICAL_MIN_C: float = 11.0
"""Typical minimum CHWRT in °C (efficient operation)"""

CHWRT_TYPICAL_MAX_C: float = 25.0
"""Typical maximum CHWRT in °C (efficient operation)"""

# Condenser Water Return Temperature (CDWRT)
CDWRT_VALID_MIN_C: float = 15.0
"""Minimum valid CDWRT in °C (absolute physical limit)"""

CDWRT_VALID_MAX_C: float = 45.0
"""Maximum valid CDWRT in °C (absolute physical limit)"""

CDWRT_TYPICAL_MIN_C: float = 18.0
"""Typical minimum CDWRT in °C (efficient operation)"""

CDWRT_TYPICAL_MAX_C: float = 40.0
"""Typical maximum CDWRT in °C (efficient operation)"""

# Chilled Water Flow (CHWF)
FLOW_VALID_MIN_m3s: float = 0.0
"""Minimum valid flow in m³/s (must be non-negative)"""

FLOW_VALID_MAX_m3s: float = 0.2
"""Maximum valid flow in m³/s (typical chiller range)"""

FLOW_TYPICAL_MIN_m3s: float = 0.01
"""Typical minimum flow in m³/s during operation"""

FLOW_TYPICAL_MAX_m3s: float = 0.15
"""Typical maximum flow in m³/s during operation"""

# Chiller Power (POWER)
POWER_VALID_MIN_kW: float = 0.0
"""Minimum valid power in kW (must be non-negative)"""

POWER_VALID_MAX_kW: float = 1000.0
"""Maximum valid power in kW (typical chiller range)"""

POWER_TYPICAL_MIN_kW: float = 10.0
"""Typical minimum power in kW during operation"""

POWER_TYPICAL_MAX_kW: float = 800.0
"""Typical maximum power in kW during operation"""

# ============================================================================
# UNIT CONVERSION FACTORS
# ============================================================================

# Temperature conversions (all to °C)
TEMP_F_TO_C_OFFSET: float = 32.0
TEMP_F_TO_C_SCALE: float = 5.0 / 9.0
TEMP_K_TO_C_OFFSET: float = 273.15

def convert_fahrenheit_to_celsius(temp_f: float) -> float:
    """Convert °F to °C: (T_°F - 32) × 5/9"""
    return (temp_f - TEMP_F_TO_C_OFFSET) * TEMP_F_TO_C_SCALE

def convert_kelvin_to_celsius(temp_k: float) -> float:
    """Convert K to °C: T_K - 273.15"""
    return temp_k - TEMP_K_TO_C_OFFSET

# Flow conversions (all to m³/s)
FLOW_LS_TO_M3S: float = 0.001
"""Liters per second to m³/s"""

FLOW_GPM_TO_M3S: float = 0.0000630902
"""Gallons per minute to m³/s"""

FLOW_M3H_TO_M3S: float = 1.0 / 3600.0
"""m³/hour to m³/s"""

# Power conversions (all to kW)
POWER_W_TO_KW: float = 0.001
"""Watts to kilowatts"""

POWER_MW_TO_KW: float = 1000.0
"""Megawatts to kilowatts"""

# ============================================================================
# UNIT CONVERSION MAPPINGS
# ============================================================================

TEMPERATURE_UNITS: Tuple[str, ...] = ("C", "F", "K", "°C", "°F", "celsius", "fahrenheit", "kelvin")
"""Valid temperature unit strings"""

FLOW_UNITS: Tuple[str, ...] = ("m3/s", "m³/s", "L/s", "l/s", "GPM", "gpm", "m3/h", "m³/h")
"""Valid flow unit strings"""

POWER_UNITS: Tuple[str, ...] = ("W", "kW", "MW", "w", "kw", "mw", "watt", "kilowatt", "megawatt")
"""Valid power unit strings"""

# Unit normalization mapping (input → canonical)
UNIT_NORMALIZATION: Dict[str, str] = {
    # Temperature
    "C": "C",
    "°C": "C",
    "celsius": "C",
    "F": "F",
    "°F": "F",
    "fahrenheit": "F",
    "K": "K",
    "kelvin": "K",
    # Flow
    "m3/s": "m3/s",
    "m³/s": "m3/s",
    "L/s": "L/s",
    "l/s": "L/s",
    "GPM": "GPM",
    "gpm": "GPM",
    "m3/h": "m3/h",
    "m³/h": "m3/h",
    # Power
    "W": "W",
    "w": "W",
    "watt": "W",
    "kW": "kW",
    "kw": "kW",
    "kilowatt": "kW",
    "MW": "MW",
    "mw": "MW",
    "megawatt": "MW",
}

# ============================================================================
# CONFIDENCE PENALTY VALUES
# ============================================================================

PENALTY_MISSING_UNIT: float = -0.30
"""Penalty when unit is missing and must be inferred"""

PENALTY_AMBIGUOUS_UNIT: float = -0.20
"""Penalty when unit detection is ambiguous (confidence < 0.8)"""

PENALTY_MANUAL_UNIT: float = -0.10
"""Penalty when unit was manually specified (not detected)"""

PENALTY_OUT_OF_RANGE: float = -0.05
"""Penalty per 1% of samples outside valid range"""

PENALTY_PHYSICS_VIOLATION: float = 0.10
"""Penalty multiplier for physics violations (e.g., CHWRT < CHWST)"""

# Stage 1 overall penalty thresholds
PENALTY_STAGE1_HIGH_CONFIDENCE: float = -0.00
"""No penalty if confidence ≥ 0.95"""

PENALTY_STAGE1_MEDIUM_CONFIDENCE: float = -0.02
"""Penalty if 0.80 ≤ confidence < 0.95"""

PENALTY_STAGE1_LOW_CONFIDENCE: float = -0.05
"""Penalty if confidence < 0.80"""

# ============================================================================
# HALT CONDITION THRESHOLDS
# ============================================================================

HALT_THRESHOLD_PHYSICS_VIOLATION_PCT: float = 1.0
"""HALT if >1% of samples violate physics constraints"""

HALT_THRESHOLD_NEGATIVE_VALUES_PCT: float = 0.0
"""HALT if ANY negative values in flow or power (>0%)"""

HALT_THRESHOLD_MISSING_BMD_CHANNELS: int = 0
"""HALT if ANY BMD channels are missing (all 5 required)"""

# ============================================================================
# UNIT DETECTION HEURISTICS
# ============================================================================

# Temperature detection ranges
TEMP_C_RANGE_MIN: float = 3.0
TEMP_C_RANGE_MAX: float = 30.0
"""If values are in this range, likely Celsius"""

TEMP_F_RANGE_MIN: float = 37.0
TEMP_F_RANGE_MAX: float = 86.0
"""If values are in this range, likely Fahrenheit"""

TEMP_K_RANGE_MIN: float = 276.0
TEMP_K_RANGE_MAX: float = 303.0
"""If values are in this range, likely Kelvin"""

# Flow detection ranges
FLOW_M3S_RANGE_MAX: float = 0.2
"""If max < 0.2, likely m³/s"""

FLOW_LS_RANGE_MAX: float = 200.0
"""If max < 200, likely L/s"""

FLOW_M3H_RANGE_MAX: float = 720.0
"""If max < 720, likely m³/h"""

FLOW_GPM_RANGE_MAX: float = 3000.0
"""If max < 3000, likely GPM"""

# Power detection ranges
POWER_W_RANGE_MIN: float = 10000.0
"""If min > 10,000, likely Watts (not kW)"""

POWER_KW_RANGE_MIN: float = 10.0
POWER_KW_RANGE_MAX: float = 1000.0
"""If values in this range, likely kW"""

POWER_MW_RANGE_MAX: float = 1.5
"""If max < 1.5, likely MW"""

# ============================================================================
# CONFIDENCE THRESHOLDS
# ============================================================================

CONFIDENCE_HIGH: float = 0.95
"""High confidence threshold (≥95%)"""

CONFIDENCE_MEDIUM: float = 0.80
"""Medium confidence threshold (≥80%)"""

CONFIDENCE_LOW: float = 0.60
"""Low confidence threshold (≥60%)"""

CONFIDENCE_UNKNOWN: float = 0.0
"""Unknown/failed detection (0%)"""

# ============================================================================
# OUTPUT COLUMN NAMES
# ============================================================================

# BMD signal column suffixes
SUFFIX_ORIG: str = "_orig"
SUFFIX_ORIG_UNIT: str = "_orig_unit"
SUFFIX_UNIT_CONFIDENCE: str = "_unit_confidence"
SUFFIX_PHYSICS_VIOLATIONS_COUNT: str = "_physics_violations_count"
SUFFIX_PHYSICS_VIOLATIONS_PCT: str = "_physics_violations_pct"

# Specific BMD columns (after conversion)
COL_CHWST: str = "chwst"
COL_CHWRT: str = "chwrt"
COL_CDWRT: str = "cdwrt"
COL_FLOW: str = "flow_m3s"
COL_POWER: str = "power_kw"

# Overall Stage 1 columns
COL_STAGE1_CONFIDENCE: str = "stage1_overall_confidence"
COL_STAGE1_PHYSICS_VALID: str = "stage1_physics_valid"
COL_STAGE1_PENALTY: str = "stage1_penalty"

# ============================================================================
# BMD CHANNEL DEFINITIONS
# ============================================================================

BMD_CHANNELS: Tuple[str, ...] = ("CHWST", "CHWRT", "CDWRT", "FLOW", "POWER")
"""5 mandatory BMD channels for baseline hypothesis testing"""

BMD_CHANNEL_DISPLAY_NAMES: Dict[str, str] = {
    "CHWST": "Chilled Water Supply Temperature",
    "CHWRT": "Chilled Water Return Temperature",
    "CDWRT": "Condenser Water Return Temperature",
    "FLOW": "Chilled Water Flow Rate",
    "POWER": "Chiller Electrical Power",
}

BMD_CHANNEL_UNITS: Dict[str, str] = {
    "CHWST": "°C",
    "CHWRT": "°C",
    "CDWRT": "°C",
    "FLOW": "m³/s",
    "POWER": "kW",
}

# ============================================================================
# PERCENTILE FOR ROBUST DETECTION
# ============================================================================

PERCENTILE_ROBUST: float = 99.5
"""Use 99.5th percentile instead of max for robust outlier handling"""

# ============================================================================
# METADATA KEYS
# ============================================================================

KEY_DETECTED_UNIT: str = "detected_unit"
KEY_DETECTION_CONFIDENCE: str = "detection_confidence"
KEY_CONVERSION_APPLIED: str = "conversion_applied"
KEY_CONVERSION_FACTOR: str = "conversion_factor"
KEY_UNIT_CONFIDENCE: str = "unit_confidence"
KEY_PHYSICS_CONFIDENCE: str = "physics_confidence"
KEY_OVERALL_CONFIDENCE: str = "overall_confidence"
KEY_PENALTY: str = "penalty"
KEY_VIOLATIONS_COUNT: str = "violations_count"
KEY_VIOLATIONS_PCT: str = "violations_pct"
KEY_HALT: str = "halt"
KEY_HALT_REASON: str = "halt_reason"
KEY_WARNINGS: str = "warnings"
KEY_ERRORS: str = "errors"

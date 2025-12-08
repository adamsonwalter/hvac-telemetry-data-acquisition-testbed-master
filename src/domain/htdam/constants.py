"""
HTDAM Stage 1 Constants

Pure constants file - NO code execution, NO side effects.
All physics validation ranges, unit conversion factors, and confidence penalties.

Reference: htdam/stage-1-unit-verification/HTAM Stage 1 Assets/HTDAM_Stage1_Impl_Guide.md
"""

from typing import Dict, List, Tuple

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
# OPERATIONAL STATE THRESHOLDS
# ============================================================================

# Minimum Delta-T (°C) to consider chiller ACTIVE (validated data-driven knee at 0.76°C)
DELTA_T_ACTIVE_MIN_C: float = 0.76
"""Delta-T threshold in °C separating ACTIVE from STANDBY for chillers (30.3% classification rate)."""

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

# ============================================================================
# STAGE 2: GAP DETECTION & CLASSIFICATION CONSTANTS
# ============================================================================

# Nominal interval for COV logging (typical: 15 minutes)
T_NOMINAL_SECONDS: float = 900.0
"""Nominal time interval in seconds between measurements (15 minutes for typical COV logging)"""

# Gap classification thresholds (relative to T_NOMINAL)
NORMAL_MAX_FACTOR: float = 1.5
"""Intervals ≤ 1.5 × T_NOMINAL are classified as NORMAL (≤22.5 min for 15-min logging)"""

MINOR_GAP_UPPER_FACTOR: float = 4.0
"""Intervals ≤ 4.0 × T_NOMINAL are classified as MINOR_GAP (≤60 min for 15-min logging)"""

MAJOR_GAP_LOWER_FACTOR: float = 4.0
"""Intervals > 4.0 × T_NOMINAL are classified as MAJOR_GAP (>60 min for 15-min logging)"""

# Gap semantic detection thresholds
COV_TOLERANCE_RELATIVE_PCT: float = 0.5
"""Relative change threshold (%) to classify gap as COV_CONSTANT vs COV_MINOR"""

SENSOR_ANOMALY_JUMP_THRESHOLD: float = 5.0
"""Absolute value jump threshold (°C) to classify gap as SENSOR_ANOMALY"""

# Exclusion window detection criteria
EXCLUSION_MIN_OVERLAP_STREAMS: int = 2
"""Minimum number of streams required to have overlapping MAJOR_GAPs for exclusion window"""

EXCLUSION_MIN_DURATION_HOURS: float = 8.0
"""Minimum duration (hours) of overlapping MAJOR_GAPs to propose exclusion window"""

# Gap penalty values
GAP_PENALTIES: Dict[str, float] = {
    "COV_CONSTANT": 0.0,      # Benign: setpoint held constant, no penalty
    "COV_MINOR": -0.02,       # Benign: slow drift triggered COV, small penalty
    "SENSOR_ANOMALY": -0.05,  # Suspicious: large jump or physics violation
    "EXCLUDED": -0.03,        # Data excluded by user approval, modest penalty
    "UNKNOWN": -0.01,         # Cannot classify, minimal penalty
}
"""Confidence penalties by gap semantic type"""

# Stage 2 output column names
COL_GAP_BEFORE_DURATION_S: str = "gap_before_duration_s"
COL_GAP_BEFORE_CLASS: str = "gap_before_class"
COL_GAP_BEFORE_SEMANTIC: str = "gap_before_semantic"
COL_GAP_BEFORE_CONFIDENCE: str = "gap_before_confidence"
COL_VALUE_CHANGED_RELATIVE_PCT: str = "value_changed_relative_pct"
COL_EXCLUSION_WINDOW_ID: str = "exclusion_window_id"

# Gap classification labels
GAP_CLASS_NORMAL: str = "NORMAL"
GAP_CLASS_MINOR: str = "MINOR_GAP"
GAP_CLASS_MAJOR: str = "MAJOR_GAP"

# Gap semantic labels
GAP_SEMANTIC_COV_CONSTANT: str = "COV_CONSTANT"
GAP_SEMANTIC_COV_MINOR: str = "COV_MINOR"
GAP_SEMANTIC_SENSOR_ANOMALY: str = "SENSOR_ANOMALY"
GAP_SEMANTIC_UNKNOWN: str = "UNKNOWN"
GAP_SEMANTIC_NA: str = "N/A"

# ============================================================================
# STAGE 3: TIMESTAMP SYNCHRONIZATION CONSTANTS
# ============================================================================

# Grid construction (must match Stage 2 T_NOMINAL_SECONDS)
# T_NOMINAL_SECONDS is already defined in Stage 2 section above

# Alignment tolerance and thresholds
SYNC_TOLERANCE_SECONDS: int = 1800
"""Maximum distance (±30 minutes) for nearest-neighbor alignment"""

ALIGN_EXACT_THRESHOLD: int = 60
"""Distance threshold (seconds) for EXACT alignment quality (<60s → confidence 0.95)"""

ALIGN_CLOSE_THRESHOLD: int = 300
"""Distance threshold (seconds) for CLOSE alignment quality (60-300s → confidence 0.90)"""

ALIGN_INTERP_THRESHOLD: int = 1800
"""Distance threshold (seconds) for INTERP alignment quality (300-1800s → confidence 0.85)"""

# Coverage quality thresholds (percentage of VALID grid points)
COVERAGE_EXCELLENT_PCT: float = 95.0
"""Coverage ≥95% is excellent (no penalty)"""

COVERAGE_GOOD_PCT: float = 90.0
"""Coverage ≥90% is good (small penalty -0.02)"""

COVERAGE_FAIR_PCT: float = 80.0
"""Coverage ≥80% is fair (moderate penalty -0.05)"""

# Coverage <80% is poor (large penalty -0.10 or HALT)

# Jitter tolerance
JITTER_CV_TOLERANCE_PCT: float = 5.0
"""Maximum acceptable coefficient of variation (%) for grid interval consistency"""

# Stream classification
MANDATORY_STREAMS: List[str] = ['CHWST', 'CHWRT', 'CDWRT']
"""Streams required for VALID row classification (temperature analysis)"""

OPTIONAL_STREAMS: List[str] = ['FLOW', 'POWER']
"""Streams optional for VALID row (COP analysis requires these but temp analysis does not)"""

# Alignment quality labels
ALIGN_EXACT: str = "EXACT"
"""Alignment quality: raw point <60s from grid point (confidence 0.95)"""

ALIGN_CLOSE: str = "CLOSE"
"""Alignment quality: raw point 60-300s from grid point (confidence 0.90)"""

ALIGN_INTERP: str = "INTERP"
"""Alignment quality: raw point 300-1800s from grid point (confidence 0.85)"""

ALIGN_MISSING: str = "MISSING"
"""Alignment quality: no raw point within tolerance (confidence 0.00)"""

# Row gap type labels (Stage 3 synchronized grid)
GAP_TYPE_VALID: str = "VALID"
"""Row has all mandatory streams present with acceptable alignment quality"""

GAP_TYPE_COV_CONSTANT: str = "COV_CONSTANT"
"""Row missing mandatory streams due to COV constant (setpoint held)"""

GAP_TYPE_COV_MINOR: str = "COV_MINOR"
"""Row missing mandatory streams due to COV minor (slow drift)"""

GAP_TYPE_SENSOR_ANOMALY: str = "SENSOR_ANOMALY"
"""Row missing mandatory streams due to sensor anomaly (large jump)"""

GAP_TYPE_GAP: str = "GAP"
"""Row missing mandatory streams due to generic gap (unknown cause)"""

GAP_TYPE_EXCLUDED: str = "EXCLUDED"
"""Row in approved exclusion window (maintenance period, user-approved)"""

# Stage 3 output column suffixes
COL_SUFFIX_ALIGN_QUALITY: str = "_align_quality"
"""Column suffix for alignment quality (e.g., 'chwst_align_quality')"""

COL_SUFFIX_ALIGN_DISTANCE: str = "_align_distance_s"
"""Column suffix for alignment distance in seconds (e.g., 'chwst_align_distance_s')"""

# Stage 3 DataFrame columns (row-level)
COL_GRID_TIMESTAMP: str = "timestamp"
"""Master grid timestamp column"""

COL_ROW_GAP_TYPE: str = "gap_type"
"""Row-level gap type classification column"""

COL_ROW_CONFIDENCE: str = "confidence"
"""Row-level confidence score column (0.00-0.95)"""

COL_ROW_EXCLUSION_WINDOW_ID: str = "exclusion_window_id"
"""Row-level exclusion window ID column (string or null)"""

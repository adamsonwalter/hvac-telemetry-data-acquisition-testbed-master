# HTDAM Stage 1 Extensions
## Additional Requirements Beyond Base Integration Plan

**Date**: December 7, 2025  
**Status**: Approved by user - ready for implementation  
**Purpose**: Document extended requirements for Stage 1 beyond base INTEGRATION_PLAN.md

---

## Overview

Based on user feedback, Stage 1 now includes four major extensions:

1. **XLSX Multi-Column File Parsing** (Monash-style datasets)
2. **ASHRAE Terminology Normalization** (flexible pattern matching)
3. **Percentage Signal Verification** (extend to ALL HVAC sensors)
4. **Adaptive Grid Interval** (preparation for Stage 3)

---

## Extension 1: XLSX Multi-Column File Parsing

### Requirement

Support XLSX files with multiple sensor columns per sheet (like Monash University datasets), not just individual CSV files.

### Specifications

**File Structure**:
- One sheet per chiller train (e.g., "chiller 1 2025.xls")
- Header row may be in rows 0, 1, or 2 (investigate first 3 rows)
- Timestamp in named column (conventionally first column)
- Multiple sensor columns (CHWST, CHWRT, power, flow, etc.)

**Example (Monash Chiller 1 2025)**:
```
Row 0: "Chiller 1", NaN, NaN, ...              → Title row
Row 1: "Location:", "Monash University...",    → Metadata row
Row 2: "Date", "Actual Line Current", "CHWST", ... → HEADER ROW ✓
Row 3: 2025-09-03 23:00:00, 0, 6.8, ...        → Data rows
```

### Pure Function Required

**File**: `src/domain/htdam/stage1/parseHvacXlsx.py`

```python
def parse_hvac_xlsx(
    filepath: str,
    sheet_name: str = "2025"
) -> Tuple[pd.DataFrame, Dict]:
    """
    Pure function: Parse HVAC XLSX with flexible header detection.
    
    ZERO SIDE EFFECTS
    
    Args:
        filepath: Path to XLSX file
        sheet_name: Sheet name (default: "2025" for most recent year)
    
    Returns:
        Tuple of:
        - normalized_df: DataFrame with ASHRAE column names
        - metadata: Dict with detection details
    
    Process:
    1. Load XLSX sheet
    2. Detect header row (investigate rows 0-2)
    3. Normalize column names to ASHRAE standard
    4. Detect and validate timestamp column
    5. Return normalized DataFrame + metadata
    
    Header Detection Rules:
    - Header row has ≥50% non-null values
    - Contains sensor-like keywords (temp, flow, power, vane)
    - NOT all dates (that's data row)
    - NOT all numeric (that's data row)
    - NOT units-only (e.g., "°C", "L/s", "kW")
    
    Timestamp Detection:
    - Patterns: "Date", "Time", "Timestamp", "DateTime"
    - Validate: monotonic, reasonable range (2020-2030)
    - Default: first column if no name match
    """
    pass
```

### Hook Integration

**Updated**: `src/hooks/htdam/useUnitVerification.py`

```python
def use_unit_verification(
    filepath: str,  # NEW: support XLSX file path
    stream_mapping: Optional[Dict] = None,  # NEW: optional column mapping
    nameplate_kw: Optional[float] = None,
    expected_ranges: Optional[Dict] = None
) -> Tuple[Dict[str, pd.DataFrame], Dict]:
    """
    Hook: Orchestrate HTDAM Stage 1 Unit Verification.
    
    Now supports:
    - Individual CSV files (original)
    - Multi-column XLSX files (NEW)
    
    Workflow:
    1. Detect file type (CSV vs XLSX)
    2. If XLSX: call parse_hvac_xlsx (pure function)
    3. Normalize column names to ASHRAE
    4. Split into per-sensor streams
    5. Verify each stream (temperature/flow/power/percentage)
    6. Validate physics ranges
    7. Calculate Stage 1 score
    """
    pass
```

### CLI Extension

**Updated**: `src/orchestration/htdam/Stage1CLI.py`

```python
def main():
    parser = argparse.ArgumentParser(description='HTDAM Stage 1: Unit Verification')
    
    # Original: individual CSV files
    parser.add_argument('--chwst', help='CHWST CSV file')
    parser.add_argument('--chwrt', help='CHWRT CSV file')
    # ... other individual files
    
    # NEW: multi-column XLSX file
    parser.add_argument('--xlsx', help='Multi-column XLSX file')
    parser.add_argument('--sheet', default='2025', help='Sheet name')
    
    # If --xlsx provided, use XLSX workflow
    # Else use individual CSV workflow
```

---

## Extension 2: ASHRAE Terminology Normalization

### Requirement

Flexible pattern matching to normalize vendor-specific column names to ASHRAE standard terminology.

### Specifications

See complete documentation in: **`htdam/ASHRAE_TERMINOLOGY.md`**

### Key Features

**1. Flexible Pattern Matching**:
- Exact match (case-insensitive): "CHWST" → CHWST
- Regex match: "CHW Supply Temp" → CHWST
- Fuzzy match (Levenshtein ≤2): "CHWS" → CHWST
- Keyword intersection: "Chilled Water Temperature Supply" → CHWST

**2. Confidence Scoring**:
- Exact: 1.0
- Regex: 0.95
- Fuzzy: 0.85
- Keyword: 0.75
- Ambiguous (<0.7): flag for manual review

**3. Core BMD Mappings**:

| ASHRAE | Alternative Names | Regex Pattern |
|--------|-------------------|---------------|
| CHWST | CHW Supply Temp, Leaving Chilled Water Temp, LWT | `(?i)(chw\|chilled.*water).*(supply\|leaving\|st)` |
| CHWRT | CHW Return Temp, Entering Chilled Water Temp, EWT | `(?i)(chw\|chilled.*water).*(return\|entering\|rt)` |
| CDWST | CDW Supply Temp, CW Supply, Entering Condenser Water | `(?i)(cdw\|cw\|cond.*water).*(supply\|entering\|st)` |
| CDWRT | CDW Return Temp, CW Return, Leaving Condenser Water | `(?i)(cdw\|cw\|cond.*water).*(return\|leaving\|rt)` |
| CHWF | CHW Flow, Flow Rate, GPM, L/s, Evaporator Flow | `(?i)(chw\|chilled.*water\|evap).*(flow\|gpm\|l/s)` |
| POWER | Demand Kilowatts, kW, Electrical Power, Chiller Power | `(?i)(power\|kilowatt\|kw\|demand.*kw)` |

**4. Extended Parameters** (Stage 4+):
- GUIDE_VANE, VFD_SPEED, VALVE_POS (control signals)
- COMP_DISCHARGE_TEMP, COMP_MOTOR_TEMP, COMP_CURRENT (compressor)
- EVAP_REFRIG_PRESS, COND_REFRIG_PRESS (refrigerant)
- EVAP_APPROACH, COND_APPROACH, SETPOINT (performance)

### Pure Function Required

**File**: `src/domain/htdam/stage1/normalizeColumnNames.py`

```python
def normalize_column_names(
    columns: List[str],
    mapping_table: Dict[str, List[str]]
) -> Tuple[Dict[str, str], Dict]:
    """
    Pure function: Map raw column names to ASHRAE standard.
    
    ZERO SIDE EFFECTS
    
    Args:
        columns: List of raw column names from XLSX/CSV
        mapping_table: ASHRAE terminology lookup table
    
    Returns:
        Tuple of:
        - column_mapping: Dict[original_name, ashrae_name]
        - metadata: Dict with:
            - confidence_scores: Dict[ashrae_name, float]
            - ambiguous_columns: List[str] (confidence < 0.7)
            - unmatched_columns: List[str]
    
    Algorithm:
    1. For each column:
       a. Try exact match (case-insensitive)
       b. Try regex pattern match
       c. Try fuzzy string match (Levenshtein ≤ 2)
       d. Try keyword intersection (≥3 keywords)
    2. Assign highest confidence match
    3. Flag ambiguous (<0.7) for manual review
    """
    pass
```

### Validation Rules

**Post-Normalization Checks**:

1. **Temperature Consistency**:
   - If CHWST and CHWRT present → CHWRT > CHWST for ≥95% of time
   - If CDWRT present → CDWRT > CHWST for ≥95% (positive lift)

2. **Range Plausibility**:
   - CHWST: 3-20°C (typical chiller range)
   - CHWRT: 5-25°C
   - CDWRT: 15-35°C (ambient dependent)
   - CHWF: >0, typically 10-500 L/s for commercial chillers
   - POWER: >0, typically 50-5000 kW for commercial chillers

3. **BMD Completeness**:
   - Required: CHWST, CHWRT, CDWRT, CHWF, POWER
   - If missing → flag + severe penalty
   - Report: which parameters present/missing

---

## Extension 3: Percentage Signal Verification

### Requirement

Stage 1 must handle percentage signals (guide vanes, valves, VFDs) in addition to BMD parameters, making it universal for ALL HVAC sensors.

### Rationale

**User requirement**: "yes - because this is setting up for being able to handle all HVAC sensors in the future."

### Integration Strategy

**Reuse Existing Decoder**: Call `normalizePercentSignal.py` (no changes needed!)

**Extended Stage 1 Scope**:
- Temperature (°C, °F, K) → °C
- Flow (L/s, GPM, m³/h) → m³/s
- Power (W, kW, MW) → kW
- **Percentage** (0-1, 0-100%, 0-10k counts, etc.) → 0-1 fraction

### Implementation

**In `use UnitVerification.py` hook**:

```python
from ...domain.decoder.normalizePercentSignal import normalize_percent_signal

def use_unit_verification(...):
    ...
    
    # After normalizing column names to ASHRAE
    for col in normalized_columns:
        if col in ['CHWST', 'CHWRT', 'CDWRT', 'CDWST']:
            # Temperature verification
            result = verify_temperature_unit(df[col], col)
        
        elif col in ['CHWF', 'CDWF']:
            # Flow verification
            result = verify_flow_unit(df[col])
        
        elif col == 'POWER':
            # Power verification
            result = verify_power_unit(df[col])
        
        elif col in ['GUIDE_VANE', 'VFD_SPEED', 'VALVE_POS']:
            # Percentage verification (REUSE existing decoder!)
            normalized, metadata = normalize_percent_signal(
                df[col],
                signal_name=col
            )
            df[f'{col}_normalized'] = normalized
            # Add to Stage 1 report
        
        else:
            # Unknown parameter type - flag for review
            logger.warning(f"Unknown parameter type: {col}")
```

### Benefits

1. **Universal HVAC sensor handling** - not just BMD
2. **Zero code duplication** - reuses battle-tested decoder (99%+ success)
3. **Consistent architecture** - same hook-first pattern
4. **Future-proof** - ready for Stage 4+ extended parameters

---

## Extension 4: Adaptive Grid Interval (Stage 3 Preparation)

### Requirement

**CRITICAL**: Timestamp synchronization grid interval must be **data-driven**, not hardcoded to 15-min.

### Rationale

**User feedback**: "we are subject to whatever telemetry data we receive and although 15 minute intervals may be common for some sensors and some BMS other's may use different 'most common' intervals, so the synchronisation alignment interval should surely be calculated for optimality on the fly in response to the data?"

**User decision**: **Option B (Adaptive Grid) - Approved**

### Benefits of Adaptive Approach

**Pros**:
- ✅ Preserves all data - grid matches actual logging frequency
- ✅ Optimal alignment - minimal interpolation needed
- ✅ Mixed-frequency handling - GCD finds common denominator
- ✅ Honest representation - doesn't create false precision

**Example**: If one sensor logs every 15 min and another every 5 min, adaptive grid uses 5 min (GCD) to preserve both.

### Specifications

**Pure Function** (for Stage 3, documented now):

**File**: `src/domain/htdam/stage3/calculateOptimalGridInterval.py`

```python
def calculate_optimal_grid_interval(
    streams: Dict[str, pd.Series]
) -> Tuple[int, Dict]:
    """
    Pure function: Calculate optimal synchronization grid interval from data.
    
    ZERO SIDE EFFECTS
    
    Args:
        streams: Dict of raw timestamp series per stream
    
    Returns:
        Tuple of:
        - optimal_interval_seconds: int (e.g., 300, 600, 900, 1800)
        - metadata: Dict with detection details
    
    Detection Strategy:
    1. Per stream: compute inter-sample intervals
    2. Find mode (most common interval) per stream
    3. For COV logging: detect underlying nominal rate
    4. Find GCD (greatest common divisor) across all stream modes
    5. Select nearest standard interval: 1min, 5min, 10min, 15min, 30min, 60min
    6. Validate: ensure ≥80% of samples align within tolerance
    7. If confidence <0.7 → fallback to 15-min (safety net)
    
    Examples:
        >>> # Stream A logs every 15 min, Stream B every 5 min
        >>> streams = {'A': timestamps_15min, 'B': timestamps_5min}
        >>> interval, meta = calculate_optimal_grid_interval(streams)
        >>> interval
        300  # 5 minutes (GCD of 15 and 5)
        >>> meta['detected_intervals']
        {'A': 900, 'B': 300}
        >>> meta['confidence']
        0.95
    
    COV Handling:
    - COV logging creates irregular intervals
    - Detect "nominal" rate: most common non-zero interval
    - Ignore large gaps (>4× nominal) when calculating mode
    
    Mixed-Frequency Example:
    - Temperatures: 15 min
    - Flow: 5 min
    - Power: 1 min
    - GCD: 1 min (preserves all data)
    - But if power has <70% confidence → exclude from GCD calculation
    
    Fallback:
    - If confidence <0.7 → use 15-min (ASHRAE standard)
    - Log warning: "Adaptive grid confidence low, using standard 15-min"
    """
    pass
```

### Integration with Stage 3

**In `src/hooks/htdam/useTimestampSynchronization.py`** (future):

```python
def use_timestamp_synchronization(
    streams: Dict[str, pd.DataFrame],
    gap_metadata: Dict  # From Stage 2
) -> Tuple[pd.DataFrame, Dict]:
    """
    Hook: Orchestrate Stage 3 Timestamp Synchronization.
    
    Workflow:
    1. Extract timestamp series from all streams
    2. Calculate optimal grid interval (call pure function)
    3. If confidence ≥0.7: use adaptive interval
    4. Else: fallback to 15-min
    5. Construct master grid with optimal interval
    6. Align each stream to grid (nearest-neighbor)
    7. Preserve gap metadata from Stage 2
    8. Return synchronized DataFrame + metadata
    """
    pass
```

### Metadata Output

**Stage 3 will report**:
```json
{
  "grid_interval_seconds": 300,
  "grid_interval_minutes": 5,
  "detection_method": "adaptive_gcd",
  "per_stream_intervals": {
    "CHWST": 900,
    "CHWRT": 900,
    "CDWRT": 900,
    "FLOW": 300,
    "POWER": 300
  },
  "gcd": 300,
  "confidence": 0.92,
  "fallback_used": false,
  "grid_points": 35136,
  "coverage_pct": {
    "CHWST": 98.5,
    "CHWRT": 98.7,
    "FLOW": 99.2,
    "POWER": 99.1
  }
}
```

---

## Updated File Structure

**New files added to base INTEGRATION_PLAN.md**:

```
src/
├── domain/
│   └── htdam/
│       ├── stage1/
│       │   ├── verifyTemperatureUnit.py      # Base plan
│       │   ├── verifyFlowUnit.py             # Base plan
│       │   ├── verifyPowerUnit.py            # Base plan
│       │   ├── validatePhysicsRanges.py      # Base plan
│       │   ├── calculateStage1Score.py       # Base plan
│       │   ├── parseHvacXlsx.py              # NEW - Extension 1
│       │   └── normalizeColumnNames.py       # NEW - Extension 2
│       └── stage3/
│           └── calculateOptimalGridInterval.py  # NEW - Extension 4
├── hooks/
│   └── htdam/
│       └── useUnitVerification.py            # UPDATED - supports XLSX + percentage
└── orchestration/
    └── htdam/
        └── Stage1CLI.py                      # UPDATED - supports --xlsx option

htdam/
├── ASHRAE_TERMINOLOGY.md                     # NEW - Extension 2 reference
└── STAGE1_EXTENSIONS.md                      # THIS FILE
```

---

## Updated Lines of Code Estimate

**Original estimate** (base plan): ~1780 lines

**Extensions added**:
- `parseHvacXlsx.py`: 200 lines
- `normalizeColumnNames.py`: 180 lines
- `calculateOptimalGridInterval.py`: 150 lines (Stage 3 prep)
- ASHRAE_TERMINOLOGY.md: 327 lines (reference)
- STAGE1_EXTENSIONS.md: 350 lines (this doc)
- Updated hooks/CLI: +100 lines

**New total estimate**: ~3087 lines for complete Stage 1 implementation with all extensions

**Breakdown**:
- Pure functions: 950 lines (was 750)
- Hooks: 350 lines (was 250)
- CLI: 230 lines (was 180)
- Tests: 800 lines (was 600)
- Documentation: 677 lines (new)

---

## Testing Extensions

**Additional Tests Required**:

1. `test_parseHvacXlsx.py`:
   - Test header detection (rows 0, 1, 2)
   - Test Monash XLSX format
   - Test column normalization
   - Test timestamp detection

2. `test_normalizeColumnNames.py`:
   - Test exact match
   - Test regex match
   - Test fuzzy match
   - Test ambiguity detection
   - Test confidence scoring

3. `test_calculateOptimalGridInterval.py` (Stage 3):
   - Test single-frequency streams
   - Test mixed-frequency streams (GCD)
   - Test COV logging patterns
   - Test fallback to 15-min
   - Test confidence calculation

4. Integration tests with Monash XLSX:
   - Load "chiller 1 2025.xlsx"
   - Detect header row 2
   - Normalize ASHRAE column names
   - Verify temperature/power units
   - Generate Stage 1 report

---

## Success Criteria (Extended)

**Original 6 criteria** (from base plan) PLUS:

7. ✅ XLSX multi-column files load correctly (Monash format)
8. ✅ ASHRAE column name normalization works with confidence ≥0.85
9. ✅ Percentage signals verified using existing decoder (no regression)
10. ✅ Adaptive grid interval calculation ready for Stage 3 integration
11. ✅ All extensions documented in ASHRAE_TERMINOLOGY.md
12. ✅ Integration tests pass with real Monash XLSX data

---

## Implementation Priority

**Phase 1 (Week 1)**: Core pure functions (as per base plan)
- Temperature, Flow, Power verification
- Unit tests

**Phase 1.5 (Week 1)**: Extensions
- `parseHvacXlsx.py` (XLSX parsing)
- `normalizeColumnNames.py` (ASHRAE terminology)
- Integration with existing percentage decoder
- Unit tests for extensions

**Phase 2 (Week 2)**: Validation & Scoring (as per base plan)
- `validatePhysicsRanges.py`
- `calculateStage1Score.py`
- Updated tests

**Phase 3 (Week 3)**: Orchestration (as per base plan + extensions)
- `useUnitVerification.py` (updated with XLSX support)
- `Stage1CLI.py` (updated with --xlsx option)
- Integration tests with Monash data

**Phase 3.5 (Week 3)**: Stage 3 Preparation
- `calculateOptimalGridInterval.py` (Stage 3 prep)
- Documentation for adaptive grid approach
- Tests for grid interval calculation

**Phase 4 (Week 4)**: Documentation & Validation (as per base plan)
- Stage 1 specification
- Examples with Monash data
- BarTech + Monash integration tests

---

## User Approval Status

**All extensions approved by user** (2025-12-07):

1. ✅ XLSX Multi-Column Parsing - Approved
   - Flexible header detection (rows 0-2)
   - ASHRAE terminology normalization
   - Monash dataset format support

2. ✅ Percentage Signal Verification - Approved
   - "yes - because this is setting up for being able to handle all HVAC sensors in the future"

3. ✅ Adaptive Grid Interval - Approved
   - "Option B" (Adaptive - Recommended)
   - Data-driven grid calculation
   - 15-min fallback if confidence <0.7

4. ✅ Output Format - Approved
   - Match existing sample reports
   - Plus improvements: graphs, comparisons, before/after charts

---

## Next Actions

**Immediate** (Option A confirmed by user):
1. Update INTEGRATION_PLAN.md with reference to this extensions document
2. Commit all documentation (ASHRAE_TERMINOLOGY.md + STAGE1_EXTENSIONS.md)
3. Push to GitHub
4. **Begin Phase 1 implementation** with pure functions

**Documentation Complete**: ✅  
**Ready to Code**: ✅  
**User Approval**: ✅

---

**Last Updated**: 2025-12-07  
**Approved By**: User  
**Status**: Ready for implementation

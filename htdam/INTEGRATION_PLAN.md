# HTDAM Stage 1 Integration Plan
## Merging Unit Verification with Existing Decoder

**Date**: December 7, 2025  
**Purpose**: Define integration strategy for HTDAM Stage 1 (Unit Verification) with existing Universal BMS Decoder system  
**Scope**: Stage 1 only - remaining stages are new functionality

---

## Executive Summary

**Good News**: Stage 1 has ~70% overlap with existing decoder system. We can **extend, not replace**.

**Strategy**: 
1. **Reuse** existing `normalizePercentSignal.py` for percentage detection (8 rules, battle-tested)
2. **Extend** with new temperature/flow/power unit verification
3. **Add** physics range checks and confidence scoring
4. **Wrap** in new `useUnitVerification.py` hook following HTDAM spec

**Outcome**: Preserve all existing functionality while adding HTDAM Stage 1 capabilities.

---

## Current System Analysis

### What We Have (Existing Decoder)

**Pure Functions** (`src/domain/decoder/`):
- ✅ `normalizePercentSignal.py` - 8 BMS encoding detection rules (167 lines)
  - Handles: 0-1, 0-100%, 0-1k, 0-10k, 0-50k, 0-65k, 0-100k, analog unscaled
  - Uses p995 for robust outlier handling
  - Returns normalized 0-1 fraction + metadata
  - **99%+ success rate, battle-tested in 180+ buildings**

- ✅ `detectLoadVsKw.py` - Load % vs Real kW detection (126 lines)
  - Compares against nameplate capacity
  - Equipment-specific kW ranges
  - Returns confidence + recommendations

**Hooks** (`src/hooks/`):
- ✅ `useBmsPercentDecoder.py` - File I/O, logging, CSV handling
  - Loads CSV, calls pure functions, saves results
  - Complete orchestration workflow

**What It Does Well**:
- ✅ Percentage signal normalization (all equipment types)
- ✅ Robust outlier handling (p995)
- ✅ Unit confusion detection (Load % vs kW)
- ✅ Clean separation: pure functions vs hooks

**What It Doesn't Do (Yet)**:
- ❌ Temperature unit verification (°F → °C)
- ❌ Flow unit conversion (L/s, GPM, m³/h)
- ❌ Power unit normalization (W, kW, MW)
- ❌ Physics range validation (CHWRT > CHWST, positive lift)
- ❌ Confidence scoring per HTDAM spec
- ❌ Multi-stream batch processing

---

## HTDAM Stage 1 Requirements

### What HTDAM Stage 1 Needs

**Per HTDAM v2 Update.md (lines 133-188)**:

#### 1.1 Unit Checking
- **Temperature**: CHWST, CHWRT, CDWRT
  - Expect °C (SI standard)
  - Accept °F → convert: `T_°C = (T_°F - 32) × 5/9`
  - Flag non-temperature units
  
- **Flow**: CHW Flow Rate
  - Accept L/s, m³/h, GPM
  - Convert to m³/s internally (maintain original for display)
  - Flag invalid units
  
- **Power**: Electrical Power
  - Accept kW (standard)
  - Convert W, MW as needed
  - Flag invalid units

**Self-verification**:
- Unit matrix: `(reported_unit, canonical_unit, conversion_applied)`
- Ambiguous unit → score penalty + manual override required

#### 1.2 Physics Range Checks
- **Temperature**:
  - CHWST in 3-20°C (configurable)
  - CHWRT ≥ CHWST for ≥99% of records (thermodynamics)
  - CDWRT ≥ CHWST for ≥99% (positive lift)

- **Flow & Power**:
  - Never negative
  - Within `[0, max_design × factor]`
  - Flag outliers

#### 1.3 Metrics & Penalties
- **Unit Confidence**: [0, 1] per point
- **Stage 1 Penalty Components**:
  - Missing unit: -0.05 per core channel
  - Ambiguous/manual override: -0.02
  - Severe physics violation (e.g., CHWRT < CHWST >5%): -0.10

#### 1.4 Required Outputs
1. **Temperature Range Chart** - Boxplots per stream with design bands
2. **Physics Violations Table** - `% CHWRT < CHWST`, `% lift ≤ 0`
3. **Unit Verification Table** - Per point: reported unit, canonical unit, conversion, confidence

---

## Integration Strategy

### Principle: Extend, Don't Replace

**Core Insight**: Our existing decoder handles **percentage signals** (valves, dampers, loads). HTDAM Stage 1 needs **all physical units** (temperatures, flows, powers) for BMD.

**Solution**: Create new pure functions for temperature/flow/power, orchestrate everything through new hook.

### Architecture Pattern

```
HTDAM Stage 1 (New Hook)
├── Temperature Verification (NEW pure function)
│   ├── Detect unit (°C, °F, K)
│   ├── Convert to SI (°C)
│   └── Validate physics ranges
├── Flow Verification (NEW pure function)
│   ├── Detect unit (L/s, GPM, m³/h)
│   ├── Convert to m³/s
│   └── Validate non-negative
├── Power Verification (NEW pure function)
│   ├── Detect unit (W, kW, MW)
│   ├── Convert to kW
│   └── Validate non-negative
├── Percentage Verification (REUSE existing)
│   └── normalizePercentSignal.py (no changes!)
└── Physics Cross-Checks (NEW pure function)
    ├── CHWRT > CHWST validation
    ├── Positive lift validation
    └── Penalty calculation
```

### File Structure (New)

```
src/
├── domain/
│   ├── decoder/
│   │   ├── normalizePercentSignal.py        # EXISTING - no changes
│   │   └── formatDecoderReport.py           # EXISTING - no changes
│   ├── validator/
│   │   ├── detectLoadVsKw.py                # EXISTING - no changes
│   │   ├── detectModeChanges.py             # EXISTING - no changes
│   │   └── ... (other existing validators)
│   └── htdam/                                # NEW FOLDER
│       └── stage1/                           # NEW FOLDER
│           ├── verifyTemperatureUnit.py      # NEW - Temperature unit detection + conversion
│           ├── verifyFlowUnit.py             # NEW - Flow unit detection + conversion
│           ├── verifyPowerUnit.py            # NEW - Power unit detection + conversion
│           ├── validatePhysicsRanges.py      # NEW - Cross-stream physics checks
│           └── calculateStage1Score.py       # NEW - Confidence scoring
├── hooks/
│   ├── useBmsPercentDecoder.py              # EXISTING - no changes
│   ├── useSignalValidator.py                # EXISTING - no changes
│   └── htdam/                                # NEW FOLDER
│       └── useUnitVerification.py            # NEW - HTDAM Stage 1 orchestration
└── orchestration/
    ├── DecoderCLI.py                        # EXISTING - no changes
    └── htdam/                                # NEW FOLDER
        └── Stage1CLI.py                      # NEW - HTDAM Stage 1 CLI

htdam/
├── stage-1-unit-verification/
│   ├── Stage1_Specification.md              # NEW - Complete Stage 1 spec
│   └── Stage1_Examples.md                   # NEW - Example outputs
└── ...
```

---

## Implementation Plan

### Phase 1: Pure Functions (Domain Layer)

#### 1. Temperature Unit Verification

**File**: `src/domain/htdam/stage1/verifyTemperatureUnit.py`

```python
def verify_temperature_unit(
    series: pd.Series,
    stream_name: str,
    expected_range: Tuple[float, float] = (3.0, 20.0)
) -> Dict:
    """
    Pure function: Detect and convert temperature units.
    
    ZERO SIDE EFFECTS - pure detection + conversion logic only.
    
    Args:
        series: Raw temperature data
        stream_name: 'CHWST', 'CHWRT', 'CDWRT'
        expected_range: Valid °C range (default: 3-20°C for CHW)
    
    Returns:
        Dict with:
        - detected_unit: '°C', '°F', 'K', or 'UNKNOWN'
        - canonical_unit: '°C'
        - converted_series: pd.Series in °C
        - conversion_applied: bool
        - confidence: float [0, 1]
        - issues: List[str]
    
    Detection Rules:
    1. If mean in [3, 50] → likely °C
    2. If mean in [37, 120] → likely °F
    3. If mean in [273, 323] → likely K (Kelvin)
    4. Use percentiles for robust detection
    
    Examples:
        >>> temps_f = pd.Series([50, 60, 70])  # °F
        >>> result = verify_temperature_unit(temps_f, 'CHWST')
        >>> result['detected_unit']
        '°F'
        >>> result['converted_series'].mean()
        15.56  # Converted to °C
    """
    pass
```

#### 2. Flow Unit Verification

**File**: `src/domain/htdam/stage1/verifyFlowUnit.py`

```python
def verify_flow_unit(
    series: pd.Series,
    equipment_type: str = 'chiller'
) -> Dict:
    """
    Pure function: Detect and convert flow rate units.
    
    ZERO SIDE EFFECTS
    
    Args:
        series: Raw flow data
        equipment_type: 'chiller', 'pump', etc. (for expected range)
    
    Returns:
        Dict with:
        - detected_unit: 'L/s', 'GPM', 'm³/h', 'm³/s'
        - canonical_unit: 'm³/s'
        - converted_series: pd.Series in m³/s
        - conversion_applied: bool
        - confidence: float [0, 1]
    
    Detection Rules:
    1. If max < 1 → likely m³/s
    2. If 10 < max < 500 → likely L/s (typical chiller range)
    3. If 50 < max < 2000 → likely GPM (US systems)
    4. If 500 < max < 10000 → likely m³/h
    
    Conversions:
    - L/s → m³/s: divide by 1000
    - GPM → m³/s: multiply by 0.00006309
    - m³/h → m³/s: divide by 3600
    """
    pass
```

#### 3. Power Unit Verification

**File**: `src/domain/htdam/stage1/verifyPowerUnit.py`

```python
def verify_power_unit(
    series: pd.Series,
    nameplate_kw: Optional[float] = None
) -> Dict:
    """
    Pure function: Detect and convert power units.
    
    ZERO SIDE EFFECTS
    
    Args:
        series: Raw power data
        nameplate_kw: Equipment nameplate (helps detection)
    
    Returns:
        Dict with:
        - detected_unit: 'W', 'kW', 'MW'
        - canonical_unit: 'kW'
        - converted_series: pd.Series in kW
        - conversion_applied: bool
        - confidence: float [0, 1]
    
    Detection Rules:
    1. If nameplate provided and max ~= nameplate → kW confirmed
    2. If max < 10 → likely MW (1-5 MW for large chillers)
    3. If 50 < max < 5000 → likely kW (typical range)
    4. If max > 10000 → likely W (needs conversion)
    """
    pass
```

#### 4. Physics Range Validation

**File**: `src/domain/htdam/stage1/validatePhysicsRanges.py`

```python
def validate_physics_ranges(
    chwst: pd.Series,
    chwrt: pd.Series,
    cdwrt: pd.Series,
    flow: Optional[pd.Series] = None,
    power: Optional[pd.Series] = None
) -> Dict:
    """
    Pure function: Cross-stream physics validation.
    
    ZERO SIDE EFFECTS - pure validation logic
    
    Args:
        chwst, chwrt, cdwrt: Temperature streams (in °C)
        flow: Flow rate (in m³/s, optional)
        power: Power (in kW, optional)
    
    Returns:
        Dict with:
        - chwrt_gt_chwst_pct: float (% of time CHWRT > CHWST)
        - positive_lift_pct: float (% of time CDWRT > CHWST)
        - flow_negative_pct: float (if flow provided)
        - power_negative_pct: float (if power provided)
        - violations: List[Dict] - detailed violation records
        - pass_threshold: bool (>99% compliance)
    
    Physics Rules:
    1. CHWRT ≥ CHWST (return > supply, always true for chillers)
    2. CDWRT ≥ CHWST (positive lift, thermodynamics)
    3. Flow ≥ 0 (physical constraint)
    4. Power ≥ 0 (physical constraint)
    
    Thresholds:
    - Pass: ≥99% compliance
    - Warning: 95-99% compliance
    - Fail: <95% compliance
    """
    pass
```

#### 5. Stage 1 Confidence Scoring

**File**: `src/domain/htdam/stage1/calculateStage1Score.py`

```python
def calculate_stage1_score(
    temp_results: Dict,
    flow_result: Dict,
    power_result: Dict,
    physics_result: Dict
) -> Dict:
    """
    Pure function: Calculate HTDAM Stage 1 confidence score.
    
    ZERO SIDE EFFECTS
    
    Args:
        temp_results: Dict of temperature verification results (CHWST, CHWRT, CDWRT)
        flow_result: Flow verification result
        power_result: Power verification result
        physics_result: Physics validation result
    
    Returns:
        Dict with:
        - base_score: 1.0 (start)
        - penalties: Dict[str, float] - itemized penalties
        - final_score: float [0, 1]
        - confidence_level: 'high' | 'medium' | 'low'
    
    Penalty Rules (per HTDAM spec):
    - Missing unit: -0.05 per core channel
    - Ambiguous unit: -0.02
    - Physics violation (>5% CHWRT < CHWST): -0.10
    - Flow missing (BMD requirement): severe penalty
    - Power missing (BMD requirement): severe penalty
    
    Confidence Levels:
    - High: score ≥ 0.90
    - Medium: 0.75 ≤ score < 0.90
    - Low: score < 0.75
    """
    pass
```

---

### Phase 2: Orchestration Hook

**File**: `src/hooks/htdam/useUnitVerification.py`

```python
def use_unit_verification(
    streams: Dict[str, pd.DataFrame],
    nameplate_kw: Optional[float] = None,
    expected_ranges: Optional[Dict] = None
) -> Tuple[Dict[str, pd.DataFrame], Dict]:
    """
    Hook: Orchestrate HTDAM Stage 1 Unit Verification.
    
    ORCHESTRATION HOOK - CONTAINS SIDE EFFECTS
    - Logging: progress and results
    - Calls pure functions
    - Assembles results
    
    Args:
        streams: Dict mapping stream names to DataFrames
                 Expected keys: 'CHWST', 'CHWRT', 'CDWRT', 'FLOW', 'POWER'
        nameplate_kw: Chiller nameplate capacity (optional, helps validation)
        expected_ranges: Custom physics ranges (optional)
    
    Returns:
        Tuple of:
        - verified_streams: Dict[str, pd.DataFrame] with verified/converted data
        - stage1_metadata: Complete Stage 1 report dict
    
    Workflow:
    1. Log start
    2. Verify each temperature stream (call pure functions)
    3. Verify flow (if present)
    4. Verify power (if present)
    5. Validate physics ranges across streams
    6. Calculate Stage 1 confidence score
    7. Log results (confidence, penalties, issues)
    8. Return verified data + metadata
    
    Example:
        >>> streams = {
        ...     'CHWST': df_chwst,
        ...     'CHWRT': df_chwrt,
        ...     'CDWRT': df_cdwrt,
        ...     'FLOW': df_flow,
        ...     'POWER': df_power
        ... }
        >>> verified, metadata = use_unit_verification(streams, nameplate_kw=1200)
        >>> metadata['final_score']
        0.95
    """
    pass
```

---

### Phase 3: CLI Tool

**File**: `src/orchestration/htdam/Stage1CLI.py`

```python
#!/usr/bin/env python3
"""
CLI Tool: HTDAM Stage 1 - Unit Verification

Usage:
    python -m src.orchestration.htdam.Stage1CLI \\
        --chwst data/chwst.csv \\
        --chwrt data/chwrt.csv \\
        --cdwrt data/cdwrt.csv \\
        --flow data/flow.csv \\
        --power data/power.csv \\
        --nameplate 1200 \\
        --output results/
"""

def main():
    parser = argparse.ArgumentParser(description='HTDAM Stage 1: Unit Verification')
    parser.add_argument('--chwst', required=True, help='CHWST CSV file')
    parser.add_argument('--chwrt', required=True, help='CHWRT CSV file')
    parser.add_argument('--cdwrt', required=True, help='CDWRT CSV file')
    parser.add_argument('--flow', help='Flow CSV file (optional)')
    parser.add_argument('--power', help='Power CSV file (optional)')
    parser.add_argument('--nameplate', type=float, help='Nameplate kW')
    parser.add_argument('--output', default='./htdam_stage1_results/', help='Output directory')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Load streams
    # Call use_unit_verification hook
    # Save results (verified CSVs + JSON metadata + charts)
    # Print report to console
    pass
```

---

## Reuse Strategy - Existing Decoder

### How Existing Decoder Fits

**Use Case**: When processing **percentage signals** (valves, dampers, VFDs, chiller load %) within HTDAM pipeline.

**Integration Point**: HTDAM Stage 1 can **call existing decoder** for percentage streams:

```python
# In useUnitVerification.py

from ...domain.decoder.normalizePercentSignal import normalize_percent_signal

def use_unit_verification(streams: Dict[str, pd.DataFrame], ...):
    ...
    
    # For percentage signals (e.g., guide vane position, valve %)
    if 'GUIDE_VANE' in streams:
        logger.info("Detected percentage signal: GUIDE_VANE")
        normalized, metadata = normalize_percent_signal(
            streams['GUIDE_VANE']['value'],
            signal_name='GUIDE_VANE'
        )
        streams['GUIDE_VANE']['normalized'] = normalized
        # Add metadata to Stage 1 report
    
    # Temperature streams use new temperature verification
    if 'CHWST' in streams:
        temp_result = verify_temperature_unit(streams['CHWST']['value'], 'CHWST')
        ...
```

**Result**: 
- Existing decoder continues to work standalone (CLI, hooks, etc.)
- HTDAM Stage 1 **augments** by adding temperature/flow/power verification
- Percentage signals within HTDAM can leverage battle-tested 8-rule decoder

---

## Testing Strategy

### Unit Tests (No Mocks!)

**New Tests** (`tests/domain/htdam/stage1/`):

1. `test_verifyTemperatureUnit.py`
   - Test °F → °C conversion
   - Test K → °C conversion
   - Test °C pass-through
   - Test ambiguous detection

2. `test_verifyFlowUnit.py`
   - Test L/s, GPM, m³/h conversions
   - Test unit detection from value ranges

3. `test_verifyPowerUnit.py`
   - Test W, kW, MW conversions
   - Test nameplate-based detection

4. `test_validatePhysicsRanges.py`
   - Test CHWRT > CHWST validation
   - Test positive lift validation
   - Test negative value detection

5. `test_calculateStage1Score.py`
   - Test penalty calculations
   - Test confidence levels

**Integration Tests** (`tests/hooks/htdam/`):

1. `test_useUnitVerification.py`
   - Test complete Stage 1 workflow
   - Test with real BarTech data
   - Test missing streams handling

**Reuse Existing Tests**:
- All tests in `tests/domain/test_normalizePercentSignal.py` continue to pass (no changes to existing code)

---

## Migration Path

### Step-by-Step Implementation

**Week 1: Pure Functions**
1. Create `src/domain/htdam/stage1/` folder structure
2. Implement `verifyTemperatureUnit.py` (150 lines)
3. Implement `verifyFlowUnit.py` (120 lines)
4. Implement `verifyPowerUnit.py` (120 lines)
5. Write unit tests for each (no mocks!)

**Week 2: Validation & Scoring**
6. Implement `validatePhysicsRanges.py` (180 lines)
7. Implement `calculateStage1Score.py` (100 lines)
8. Write unit tests
9. Integration tests with synthetic data

**Week 3: Orchestration**
10. Implement `useUnitVerification.py` hook (250 lines)
11. Implement `Stage1CLI.py` (180 lines)
12. Integration tests with real BarTech data

**Week 4: Documentation & Validation**
13. Create `Stage1_Specification.md` in `htdam/stage-1-unit-verification/`
14. Create `Stage1_Examples.md` with sample outputs
15. Run against BarTech dataset (validation)
16. Update root README with HTDAM Stage 1 section

### Backward Compatibility

**Guarantee**: Existing decoder CLI and hooks remain unchanged.

**Test**:
```bash
# Existing functionality must continue to work
python -m src.orchestration.DecoderCLI test-data/synthetic/Chiller_Load_Test.csv
# Expected: Same output as before

# New HTDAM Stage 1 functionality
python -m src.orchestration.htdam.Stage1CLI --chwst ... --chwrt ... --cdwrt ...
# Expected: New Stage 1 report
```

---

## Success Criteria

### Stage 1 Integration Complete When:

1. ✅ All new pure functions pass unit tests (no mocks)
2. ✅ `useUnitVerification` hook orchestrates correctly
3. ✅ CLI tool produces HTDAM-spec outputs:
   - Temperature Range Chart
   - Physics Violations Table
   - Unit Verification Table
   - Stage 1 confidence score (0-1)
4. ✅ Existing decoder tests still pass (no regression)
5. ✅ Integration test with BarTech data produces expected results:
   - Final score: 0.95-1.00 (all SI units, no violations)
   - All temperatures in °C
   - CHWRT > CHWST: 100%
   - Positive lift: 100%
6. ✅ Documentation complete:
   - `Stage1_Specification.md`
   - `Stage1_Examples.md`
   - Updated root README

---

## Next Steps After Stage 1

Once Stage 1 is complete and validated:

1. **Stage 2: Gap Detection** (NEW - no existing overlap)
   - Pure functions: gap classification (COV_CONSTANT, COV_MINOR, etc.)
   - Hook: gap resolution workflow
   - This is where HTDAM v2.0 reordering innovation happens

2. **Stage 3: Timestamp Synchronization** (NEW - no existing overlap)
   - Pure functions: master grid construction, nearest-neighbor alignment
   - Hook: synchronization with gap metadata preservation
   - Critical: must run AFTER Stage 2

3. **Stage 4: Signal Preservation** (NEW - partial overlap with existing validators)
   - Reuse: existing `detectModeChanges.py`, `detectKwhConfusion.py`
   - New: FFT hunting detection, diurnal pattern analysis

4. **Stage 5: Transformation Recommendation** (NEW - no overlap)
   - Export format selection
   - Use-case matrix
   - Material penalty score breakdown

---

## Questions for User

Before proceeding with implementation, please confirm:

1. **Scope**: Should I start with Stage 1 implementation immediately, or do you want to review this plan first?

2. **Test Data**: Should I use the BarTech dataset (`test-data/real-installations/bartech/`) for integration testing?

3. **Naming**: Are you comfortable with `src/domain/htdam/stage1/` folder structure, or prefer different organization?

4. **Percentage Signals**: Do you want HTDAM Stage 1 to also handle percentage signals (guide vanes, valves), or should those remain separate from BMD processing?

5. **Output Format**: For Stage 1 CLI, should outputs match the sample reports in `htdam/docs/illustrations/`, or create new format?

---

## Summary

**Integration Strategy**: Extend existing decoder with new temperature/flow/power verification, following same hook-first architecture.

**Code Reuse**: 
- 100% reuse of `normalizePercentSignal.py` (no changes)
- 100% reuse of existing validators (no changes)
- New pure functions for temperature/flow/power
- New hook for Stage 1 orchestration

**Outcome**: 
- Stage 1 complete and HTDAM-spec compliant
- Existing decoder continues to work
- Foundation ready for Stages 2-5
- All existing tests pass (no regression)

**Lines of Code Estimate**:
- Pure functions: ~750 lines
- Hook: ~250 lines
- CLI: ~180 lines
- Tests: ~600 lines
- **Total: ~1780 lines** for complete Stage 1 implementation

Ready to proceed when you approve the plan! 🚀

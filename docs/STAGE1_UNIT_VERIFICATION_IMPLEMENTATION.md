# Stage 1: Unit Verification & Physics Baseline Implementation
## Overview
Implement HTDAM Stage 1 following "State lives in hooks; App orchestrates" architecture to verify units and validate physics for 5 BMD sensors (CHWST, CHWRT, CDWRT, Flow, Power).
## Architecture Pattern
**Domain Layer** (Pure Functions):
* ZERO side effects (no logging, no file I/O, no global state)
* All business logic: unit detection, conversion, physics validation
* Easy to test (no mocks needed)
**Hooks Layer** (Orchestration):
* ALL side effects (logging, progress tracking, error handling)
* Calls pure functions from domain layer
* Requires mocks for testing
## Implementation Steps
### Step 1: Constants Definition
**File**: `src/domain/htdam/constants.py`
**Type**: Pure constants (no code execution)
**Content**:
* Physics validation ranges (CHWST: 3-20°C, CHWRT: 5-30°C, etc.)
* Unit conversion factors (°F→°C, GPM→m³/s, W→kW)
* Confidence penalty values (-0.30 missing, -0.20 ambiguous, etc.)
* HALT condition thresholds (>1% physics violations)
* Water properties (density: 1000 kg/m³, specific heat: 4.186 kJ/kg·K)
**Why First**: All other functions depend on these constants
### Step 2: Unit Detection (Pure Functions)
**File**: `src/domain/htdam/stage1/detectUnits.py`
**Functions**:
1. `detect_temperature_unit(series, signal_name, metadata)` → (unit_string, confidence)
    * Heuristics: Range analysis (3-20°C vs 37-68°F vs 276-293K)
    * Metadata parsing (column names, headers)
    * Returns: ("C"|"F"|"K"|None, confidence 0-1)
2. `detect_flow_unit(series, signal_name, metadata)` → (unit_string, confidence)
    * Heuristics: Magnitude analysis (0-100 L/s vs 0-1000 GPM)
    * Metadata parsing
    * Returns: ("L/s"|"m3/s"|"m3/h"|"GPM"|None, confidence)
3. `detect_power_unit(series, signal_name, metadata)` → (unit_string, confidence)
    * Heuristics: Magnitude analysis (50-500 kW vs 50000-500000 W)
    * Metadata parsing
    * Returns: ("W"|"kW"|"MW"|None, confidence)
**Key**: ZERO side effects, pure logic only
### Step 3: Unit Conversion (Pure Functions)
**File**: `src/domain/htdam/stage1/convertUnits.py`
**Functions**:
1. `convert_temperature(series, from_unit, to_unit="C")` → (converted_series, metadata)
    * Handles: °F→°C, K→°C, °C→°C (passthrough)
    * Returns: Tuple of (converted values, conversion metadata)
2. `convert_flow(series, from_unit, to_unit="m3/s")` → (converted_series, metadata)
    * Handles: L/s, GPM, m³/h → m³/s
    * Returns: Tuple of (converted values, conversion metadata)
3. `convert_power(series, from_unit, to_unit="kW")` → (converted_series, metadata)
    * Handles: W, MW → kW
    * Returns: Tuple of (converted values, conversion metadata)
**Key**: Uses constants from Step 1, pure transformations
### Step 4: Physics Validation (Pure Functions)
**File**: `src/domain/htdam/stage1/validatePhysics.py`
**Functions**:
1. `validate_temperature_range(series, signal_name, valid_min, valid_max)` → Dict
    * Returns: {violations_count, violations_pct, outside_range_indices}
2. `validate_temperature_relationships(chwst, chwrt, cdwrt)` → Dict
    * Checks: CHWRT ≥ CHWST, CDWRT > CHWST
    * Returns: {chwrt_lt_chwst_count, chwrt_lt_chwst_pct, cdwrt_lte_chwst_count, ...}
3. `validate_non_negative(series, signal_name)` → Dict
    * Checks: Flow ≥ 0, Power ≥ 0
    * Returns: {negative_count, negative_pct, negative_indices}
4. `compute_physics_confidence(validation_results, halt_thresholds)` → Tuple
    * Input: Validation results dict
    * Returns: (confidence_score, should_halt, halt_reason)
**Key**: All validation logic pure, no decisions about halting (that's orchestration)
### Step 5: Confidence Scoring (Pure Functions)
**File**: `src/domain/htdam/stage1/computeConfidence.py`
**Functions**:
1. `compute_unit_confidence(detected_unit, detection_confidence, conversion_applied)` → float
    * Formula: 1.0 × (1 - penalty_sum)
    * Penalties from constants: missing (-0.30), ambiguous (-0.20), etc.
2. `compute_physics_confidence(violations_pct, violation_type)` → float
    * Formula: 1.0 - (violations_pct / 100 × 0.10)
3. `compute_stage1_confidence(channel_confidences)` → float
    * Formula: min(chwst_conf, chwrt_conf, cdwrt_conf, flow_conf, power_conf)
4. `compute_stage1_penalty(stage1_confidence)` → float
    * Returns: -0.00 (≥0.95), -0.02 (0.80-0.95), -0.05 (<0.80)
**Key**: Pure math, uses constants from Step 1
### Step 6: Orchestration Hook
**File**: `src/hooks/useStage1Verifier.py`
**Function**: `use_stage1_verifier(df, signal_mappings, config)`
**Orchestration Flow**:
1. Log start (side effect)
2. For each BMD signal:
   a. Call `detect_units()` (pure function)
   b. Log detection result (side effect)
   c. Call `convert_units()` (pure function)
   d. Log conversion (side effect)
   e. Call `validate_physics()` (pure function)
   f. Log violations (side effect)
3. Call `compute_confidence()` for all channels (pure function)
4. Check HALT conditions (orchestration decision)
5. If HALT: Log error, raise exception (side effects)
6. Build output DataFrame with dual columns (orchestration)
7. Build metrics dict (orchestration)
8. Log completion (side effect)
9. Return (df_enriched, metrics)
**Key**: ALL side effects here, calls pure functions for logic
### Step 7: Output DataFrame Builder (Pure Function)
**File**: `src/domain/htdam/stage1/buildOutputDataFrame.py`
**Function**: `build_stage1_output_dataframe(df_input, conversions, validations)` → DataFrame
**Adds columns**:
* `chwst_orig`, `chwst_orig_unit`, `chwst`, `chwst_unit_confidence`
* `chwrt_orig`, `chwrt_orig_unit`, `chwrt`, `chwrt_unit_confidence`
* `cdwrt_orig`, `cdwrt_orig_unit`, `cdwrt`, `cdwrt_unit_confidence`
* `flow_orig`, `flow_orig_unit`, `flow_m3s`, `flow_unit_confidence`
* `power_orig`, `power_orig_unit`, `power_kw`, `power_unit_confidence`
* `stage1_overall_confidence`
* `stage1_physics_valid`
**Key**: Pure function - takes data, returns new DataFrame, no side effects
### Step 8: Metrics Builder (Pure Function)
**File**: `src/domain/htdam/stage1/buildMetrics.py`
**Function**: `build_stage1_metrics(conversions, validations, confidences)` → Dict
**Returns JSON-serializable dict**:
```python
{
  "stage": "UNITS",
  "total_records": int,
  "unit_conversions": {...},
  "physics_violations": {...},
  "confidence_scores": {...},
  "penalty": float,
  "final_score": float,
  "warnings": [...],
  "errors": [...],
  "halt": bool
}
```
**Key**: Pure function - assembles data, no side effects
### Step 9: Unit Tests - Domain Layer
**File**: `tests/domain/htdam/stage1/test_detectUnits.py`
**Tests**: Unit detection heuristics (NO MOCKS)
* Test temperature detection (3-20°C → "C", 37-68°F → "F")
* Test flow detection (0-100 L/s → "L/s", 0-1000 GPM → "GPM")
* Test power detection (50-500 kW → "kW", 50000-500000 W → "W")
**File**: `tests/domain/htdam/stage1/test_convertUnits.py`
**Tests**: Unit conversions (NO MOCKS)
* Test °F→°C: 32°F = 0°C, 68°F = 20°C
* Test K→°C: 273.15K = 0°C
* Test GPM→m³/s, L/s→m³/s
* Test W→kW, MW→kW
**File**: `tests/domain/htdam/stage1/test_validatePhysics.py`
**Tests**: Physics validation (NO MOCKS)
* Test CHWST range: 3-20°C valid, outside flagged
* Test CHWRT ≥ CHWST: violations counted
* Test CDWRT > CHWST: violations counted
* Test non-negative: Flow/Power < 0 flagged
**File**: `tests/domain/htdam/stage1/test_computeConfidence.py`
**Tests**: Confidence scoring (NO MOCKS)
* Test unit confidence with penalties
* Test physics confidence from violation %
* Test stage1 confidence = min(all channels)
* Test penalty calculation
**Key**: Pure functions need NO MOCKS
### Step 10: Unit Tests - Hooks Layer
**File**: `tests/hooks/test_useStage1Verifier.py`
**Tests**: Orchestration with side effects (WITH MOCKS)
* Mock logger, verify logging calls
* Mock file I/O if needed
* Test HALT conditions trigger exceptions
* Test output format (DataFrame + metrics)
* Verify pure functions called with correct args
**Key**: Hooks require mocks for side effects
### Step 11: Integration Test
**File**: `tests/integration/test_stage1_integration.py`
**Test**: End-to-end with real BarTech data
* Load test-data/real-installations/bartech/ files
* Run Stage 1 verification
* Verify all temps in °C (no conversion)
* Verify confidence scores = 1.0 (clean data)
* Verify no HALT conditions
* Verify output format matches spec
**Key**: Real data, no mocks, full pipeline
### Step 12: Architecture Compliance Tests
**File**: `tests/architecture/test_stage1_architecture.py`
**Tests**:
1. Verify domain layer has NO logging imports
2. Verify hooks layer HAS logging imports
3. Verify constants file is pure (no code execution)
4. Verify all domain functions are pure (no side effects)
5. Verify hook calls domain functions (not vice versa)
**Key**: Enforce "State lives in hooks; App orchestrates"
## File Structure Summary
```warp-runnable-command
src/
├── domain/
│   └── htdam/
│       ├── constants.py                    # Step 1
│       └── stage1/
│           ├── detectUnits.py              # Step 2
│           ├── convertUnits.py             # Step 3
│           ├── validatePhysics.py          # Step 4
│           ├── computeConfidence.py        # Step 5
│           ├── buildOutputDataFrame.py     # Step 7
│           └── buildMetrics.py             # Step 8
└── hooks/
    └── useStage1Verifier.py                # Step 6
tests/
├── domain/htdam/stage1/
│   ├── test_detectUnits.py                 # Step 9
│   ├── test_convertUnits.py                # Step 9
│   ├── test_validatePhysics.py             # Step 9
│   └── test_computeConfidence.py           # Step 9
├── hooks/
│   └── test_useStage1Verifier.py           # Step 10
├── integration/
│   └── test_stage1_integration.py          # Step 11
└── architecture/
    └── test_stage1_architecture.py         # Step 12
```
## Testing Strategy
**Domain Layer**: ~50+ tests, NO MOCKS
**Hooks Layer**: ~15 tests, WITH MOCKS
**Integration**: 1 comprehensive test, real data
**Architecture**: 5 compliance tests
## Success Criteria
* ✅ All 5 BMD sensors detected and converted
* ✅ Physics validation working (CHWRT ≥ CHWST, etc.)
* ✅ HALT conditions enforced (negative values, >1% violations)
* ✅ Confidence scoring accurate
* ✅ Output format matches spec (dual columns)
* ✅ Metrics JSON-serializable
* ✅ Architecture compliance verified
* ✅ Real BarTech data scores 1.0 confidence
## Dependencies
* Phase 0: Complete ✅
* Test data: Available ✅
* Specifications: Complete ✅
* Architecture: Established ✅
## Estimated Effort
* Pure functions: ~800 lines
* Hook: ~200 lines
* Tests: ~600 lines
* Total: ~1600 lines
## Next Stage
After Stage 1 complete → Stage 2: Gap Detection (COV vs sensor failure)
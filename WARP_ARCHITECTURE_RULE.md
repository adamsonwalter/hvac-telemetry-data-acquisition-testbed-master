# WARP Architecture Rule: Hooks vs Functions (Orchestration vs Pure Logic)

**Status**: MANDATORY - All code must comply  
**Priority**: CRITICAL - "Most strategic work" per user directive  
**Enforcement**: No exceptions unless explicitly justified

---

## Core Principle

> **"State lives in hooks; App orchestrates"**

All production code must maintain a strict separation between:
1. **Pure Functions** (domain/business logic)
2. **Hooks** (orchestration/side-effects)

---

## The Two-Layer Architecture

### Layer 1: Pure Functions (Domain Logic)
**Location**: `src/domain/[equipment]/` folders

**Characteristics**:
- ✅ Deterministic: same input → same output
- ✅ Stateless: no internal state
- ✅ Testable: easy unit testing
- ✅ Contains: physics, math, ASHRAE curves, scaling logic
- ❌ NO filesystem access
- ❌ NO database/API calls
- ❌ NO logger calls
- ❌ NO global state
- ❌ NO React hooks

**Examples**:
```python
# Good - Pure function
def normalize_percent_signal(series: pd.Series, expected_max: float) -> Tuple[pd.Series, Dict]:
    """Takes raw signal, returns normalized 0-1 fraction + metadata."""
    # Pure math/logic only
    mn, mx = series.min(), series.max()
    if mx <= 1.05:
        return series.clip(0, 1.0), {"type": "fraction_0_1"}
    # ... more pure detection rules
```

```python
# Bad - Mixed concerns
def normalize_percent_signal(series: pd.Series, expected_max: float):
    logger.info(f"Processing {len(series)} points")  # ❌ Side effect
    save_to_db(series)  # ❌ Side effect
    return series / 100
```

### Layer 2: Hooks (Orchestration)
**Location**: `src/hooks/` folder

**Characteristics**:
- ✅ Manages all side-effects
- ✅ Handles context, retries, progress
- ✅ Contains file I/O, database, API, logging
- ✅ One-way flow: gather data → call pure functions → write results
- ❌ NO physics/math calculations
- ❌ NO business logic

**Examples**:
```python
# Good - Hook orchestrates pure functions
def use_bms_ingest(filepath: str):
    """Hook: orchestrate BMS CSV ingestion."""
    logger.info(f"Loading {filepath}")  # ✅ Side effect in hook
    df = pd.read_csv(filepath)  # ✅ File I/O in hook
    
    # Call pure function
    normalized, metadata = normalize_percent_signal(df['value'])
    
    logger.info(f"Detected: {metadata['type']}")  # ✅ Side effect in hook
    save_to_db(normalized)  # ✅ Side effect in hook
    return normalized, metadata
```

---

## Three Critical Rules

### Rule 1: One-Way Flow (Hooks → Functions → Hooks)
```
[Hook] Load data → [Pure Function] Process → [Hook] Save results
   ↓                      ↓                        ↓
File I/O            Math/Logic              Write/Log
```

**Never**: Pure functions call hooks or do I/O

### Rule 2: Domain Separation
Each major domain gets its own hook family + pure functions:
- `useChillerPlant()` → `domain/chiller/calculateChillerPower.ts`
- `usePumpSystem()` → `domain/pump/calculatePumpPower.ts`
- `useBmsIngest()` → `domain/decoder/normalizePercentSignal.ts`

### Rule 3: Error Boundaries at Hook Level Only
- Pure functions return `Result<T, Error>` or throw exceptions
- Hooks catch errors, log them, retry, or alert user

---

## Required Folder Structure

```
src/
 ├─ hooks/
 │    ├─ useBmsIngest.py              # Orchestrates BMS CSV loading
 │    ├─ useSignalValidation.py       # Orchestrates validation pipeline
 │    ├─ useChillerPlant.py           # Orchestrates chiller calculations
 │    └─ useSyntheticOutput.py        # Orchestrates test data generation
 │
 ├─ domain/
 │    ├─ decoder/
 │    │    ├─ normalizePercentSignal.py    # Pure: 8 detection rules
 │    │    ├─ detectSignalEncoding.py      # Pure: encoding detection
 │    │    └─ signalStatistics.py          # Pure: p995, stats
 │    │
 │    ├─ validator/
 │    │    ├─ detectLoadVsKw.py            # Pure: unit confusion logic
 │    │    ├─ detectModeChanges.py         # Pure: >100% detection
 │    │    ├─ detectKwhConfusion.py        # Pure: cumulative detection
 │    │    └─ validateLoadPowerCorr.py     # Pure: correlation checks
 │    │
 │    ├─ chiller/
 │    │    ├─ calculateChillerPower.py     # Pure: chiller calculations
 │    │    └─ ashraeCurves.py              # Pure: ASHRAE physics
 │    │
 │    └─ pump/
 │         ├─ calculatePumpPower.py        # Pure: pump calculations
 │         └─ affinityLaws.py              # Pure: pump physics
 │
 └─ orchestration/
      ├─ SignalProcessingPipeline.py       # Main orchestrator
      └─ TelemetryIngestPipeline.py        # Batch processing
```

---

## Current Codebase Violations

### Critical Issues Found:

#### 1. **`universal_bms_percent_decoder.py`** (275 lines)
**Violations**:
- Lines 23-24: `logger` instantiated at module level (global state)
- Line 64: `logger.warning()` inside pure function `normalize_percent_signal()`
- Lines 86, 95, 104, 113, 122, 131, 141, 152, 160: Multiple logger calls in pure function
- Lines 183-275: File I/O (`pd.read_csv`, `df.to_csv`) mixed with logic
- Lines 164-210: `decode_telemetry_file()` mixes I/O + calling pure function

**Required Refactoring**:
- Extract pure function: `domain/decoder/normalizePercentSignal.py` (NO logging)
- Extract pure function: `domain/decoder/detectSignalType.py` (8 detection rules)
- Create hook: `hooks/useBmsPercentDecoder.py` (handles file I/O + logging)
- Create orchestrator: `orchestration/DecoderPipeline.py` (CLI entry point)

#### 2. **`signal_unit_validator.py`** (437 lines)
**Violations**:
- Lines 15-18: `logger` instantiated at module level
- Class `SignalUnitValidator` mixes pure validation logic with orchestration
- Lines 27-107: `validate_load_signal()` is monolithic (should be split)
- Pure detection methods (`_detect_load_vs_kw`, `_detect_mode_changes`) are OK but trapped in class
- Lines 375-421: Report generation mixed with validation

**Required Refactoring**:
- Extract pure functions:
  - `domain/validator/detectLoadVsKw.py`
  - `domain/validator/detectModeChanges.py`
  - `domain/validator/detectKwhConfusion.py`
  - `domain/validator/validateLoadPowerCorrelation.py`
- Create hook: `hooks/useSignalValidator.py` (orchestrates validation pipeline)
- Create pure function: `domain/validator/generateValidationReport.py` (pure string formatting)

#### 3. **`generate_hvac_test_data.py`** (259 lines)
**Violations**:
- File I/O mixed with data generation logic
- No separation between pure generation and file writing

**Required Refactoring**:
- Extract pure functions: `domain/synthetic/generateEquipmentData.py`
- Create hook: `hooks/useSyntheticDataExport.py` (handles file writing)

---

## Migration Plan

### Phase 1: Extract Pure Functions (Priority)
1. Create `src/domain/decoder/` folder
2. Extract `normalize_percent_signal()` → `normalizePercentSignal.py` (remove all logging)
3. Extract 8 detection rules → separate functions in `detectSignalType.py`
4. Create `src/domain/validator/` folder
5. Extract all `_detect_*` methods → standalone pure functions

### Phase 2: Create Hooks (Orchestration)
1. Create `src/hooks/` folder
2. Build `useBmsPercentDecoder.py` that:
   - Loads CSV (file I/O)
   - Calls pure `normalizePercentSignal()`
   - Logs results
   - Saves output CSV
3. Build `useSignalValidator.py` that:
   - Loads data
   - Calls pure validator functions
   - Logs validation results
   - Generates report

### Phase 3: Create Orchestrators (Entry Points)
1. Create `src/orchestration/` folder
2. Build `DecoderPipeline.py` (CLI tool using hooks)
3. Build `ValidationPipeline.py` (CLI tool using hooks)

### Phase 4: Testing & Validation
1. Write unit tests for all pure functions (easy - no mocks needed)
2. Write integration tests for hooks (test with real files)
3. Validate that all functionality is preserved
4. Update documentation

---

## Testing Strategy

### Pure Functions (Easy)
```python
# No mocks needed - pure input/output
def test_normalize_percent_signal():
    input_series = pd.Series([0, 5000, 10000])
    output, metadata = normalize_percent_signal(input_series)
    assert output.max() == 1.0
    assert metadata['detected_type'] == 'counts_10000_0.01pct'
```

### Hooks (Need Mocks)
```python
# Mock file system, logger, etc.
def test_use_bms_decoder(mock_csv, mock_logger):
    result = use_bms_decoder("test.csv")
    mock_logger.info.assert_called()
    assert result is not None
```

---

## Why This Matters

### Current Problems (Monolithic Code):
- ❌ **Hard to test**: Can't test math without mocking file system
- ❌ **Hard to debug**: Side effects everywhere
- ❌ **Hard to reuse**: Can't use `normalize_percent_signal()` without logger
- ❌ **Hard to maintain**: Changes cascade across concerns

### Benefits (Hooks vs Functions):
- ✅ **Easy testing**: Pure functions need no mocks
- ✅ **Clear debugging**: Side effects isolated to hooks
- ✅ **High reusability**: Pure functions work anywhere
- ✅ **Low maintenance**: Changes stay local to layer

---

## Exceptions (Rare)

The only valid exceptions:
1. **Performance-critical logging**: If logging in hot loop causes bottleneck, may inline
2. **External library constraints**: If 3rd party forces side effects
3. **Prototypes/experiments**: Clearly marked as non-production

**All exceptions must be documented and justified.**

---

## Enforcement

### Pre-Commit Checklist:
1. ❌ Is logic scattered in orchestration? → Extract to pure functions
2. ❌ Are there logger/file calls in domain functions? → Move to hooks
3. ❌ Is testing difficult? → Separate concerns
4. ✅ Do pure functions have zero side effects?
5. ✅ Do hooks only orchestrate, not calculate?

### Code Review:
- Reject any PR that mixes concerns
- Require justification for exceptions
- Validate folder structure compliance

---

## Summary

> **Hooks orchestrate. Functions calculate.**
> **Never mix side-effects with business logic.**
> **This is non-negotiable for production code.**

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-XX  
**Author**: WARP Agent (per user directive)  
**Status**: ACTIVE - All code must comply immediately

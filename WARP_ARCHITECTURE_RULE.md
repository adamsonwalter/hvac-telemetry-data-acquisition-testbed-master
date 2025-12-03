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

## Lessons Learned: Real Restructuring Experience

### Successfully Restructured: hvac-telemetry-data-acquisition-testbed (Dec 2025)

**Context**: Transformed 3 monolithic files (971 lines) → 17 modular files (1,598 lines)  
**Result**: 100% architectural compliance, zero breaking changes, trivially testable code

---

## 🎓 Critical Lessons for Future Refactoring

### 1. **Start with Pure Functions First (Phase 1)**

**Why**: Pure functions are the foundation. Get these right before touching orchestration.

**Trap**: Trying to refactor hooks and pure functions simultaneously  
**Solution**: Extract pure functions FIRST, leave old orchestration intact temporarily

**Real Example**:
```python
# WRONG: Trying to do both at once
# def use_decoder(filepath):  # ❌ New hook
#     normalized = normalize_signal(...)  # ❌ New pure function
#     # Chaos - nothing works yet!

# RIGHT: Pure functions first
# Step 1: Extract pure function, test it independently
def normalize_percent_signal(series, signal_name=""):
    # Pure logic only - NO side effects
    return normalized, metadata

# Step 2: Test pure function (no mocks!)
def test_normalize():
    result, meta = normalize_percent_signal(test_series)
    assert result.max() == 1.0  # Easy!

# Step 3: THEN create hook that uses it
def use_bms_decoder(filepath):
    df = pd.read_csv(filepath)  # Side effect
    normalized, meta = normalize_percent_signal(df['value'])  # Pure call
    return df, meta
```

**Key Insight**: Pure functions can be validated in isolation BEFORE integrating into hooks.

---

### 2. **String Formatting is a Pure Function**

**Trap**: Leaving report generation in hooks because "it just formats output"  
**Lesson**: Report generation is business logic (format decisions), not a side effect

**Real Example**:
```python
# WRONG: Report formatting in hook
def use_validator(signal):
    result = validate(signal)
    # ❌ Business logic in hook
    report = f"Signal: {result['name']}\nStatus: {result['status']}"  
    logger.info(report)  # Side effect
    return report

# RIGHT: Pure formatting function
def format_validation_report(results):
    """Pure function: format report string."""
    # Deterministic string formatting - NO side effects
    lines = []
    lines.append("VALIDATION REPORT")
    lines.append(f"Status: {results['status']}")
    return "\n".join(lines)

def use_validator(signal):
    result = validate(signal)  # Pure call
    report = format_validation_report(result)  # Pure call
    logger.info(report)  # Side effect ONLY in hook
    return result
```

**Key Insight**: If it makes decisions about WHAT to output, it's business logic → pure function.

---

### 3. **Metadata is Return Data, Not Logging**

**Trap**: Replacing logger calls with print statements in "pure" functions  
**Lesson**: Pure functions return metadata; hooks decide what to log

**Real Example**:
```python
# WRONG: Prints in pure function
def normalize_signal(series):
    if max <= 1.05:
        print("Detected: fraction_0_1")  # ❌ Side effect!
        return series

# WRONG: Even returning a "log message" is coupling
def normalize_signal(series):
    if max <= 1.05:
        log_msg = "Detected: fraction_0_1"  # ❌ Forces hook to log
        return series, log_msg

# RIGHT: Return structured metadata
def normalize_signal(series):
    metadata = {
        "detected_type": "fraction_0_1",
        "confidence": "high",
        "scaling_factor": 1.0
    }
    return series, metadata  # Hook decides what to log

def use_decoder(filepath):
    normalized, meta = normalize_signal(df['value'])
    # Hook controls logging format and level
    logger.info(f"Detected: {meta['detected_type']} (conf: {meta['confidence']})")
    return normalized, meta
```

**Key Insight**: Pure functions return data; hooks format and log it.

---

### 4. **Don't Extract Classes - Extract Functions**

**Trap**: Creating `SignalValidator` class with pure methods, thinking "it's organized"  
**Lesson**: Classes with state belong in hooks; pure logic should be standalone functions

**Real Example**:
```python
# WRONG: Class with pure methods (still hard to test)
class SignalValidator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)  # ❌ Side effect trapped
    
    def _detect_mode_changes(self, series):  # Pure logic
        return {"has_changes": False}
    
    def validate(self, series):
        result = self._detect_mode_changes(series)
        self.logger.info(result)  # ❌ Mixed concerns
        return result

# RIGHT: Pure functions + orchestration hook
def detect_mode_changes(series: pd.Series) -> Dict:
    """Pure function: detect mode changes."""
    # Pure logic only
    return {"has_changes": False}

def use_signal_validator(series):
    """Hook: orchestrate validation."""
    logger.info("Starting validation")
    result = detect_mode_changes(series)  # Pure call
    logger.info(f"Result: {result}")
    return result
```

**Key Insight**: Classes create coupling. Prefer standalone pure functions + orchestration hooks.

---

### 5. **Deprecate Safely - Don't Delete Immediately**

**Trap**: Deleting old code before new code is validated  
**Lesson**: Move to `_deprecated/` folder, keep for reference during transition

**Real Strategy**:
```bash
# Safe deprecation workflow
mkdir _deprecated
mv old_monolith.py _deprecated/
echo "See src/hooks/ and src/domain/ for new architecture" > _deprecated/README.md
git commit -m "refactor: deprecate old monolith, add migration guide"

# Keep deprecated code until:
# 1. All tests pass with new code
# 2. CLI functionality validated
# 3. Documentation complete
# THEN schedule deletion (30-90 days later)
```

**Key Insight**: Deprecated code is documentation of "what we had before."

---

### 6. **Test Pure Functions Immediately**

**Trap**: Extracting pure functions but not testing them until "everything is done"  
**Lesson**: Write tests as you extract each pure function - they're trivial to test!

**Real Workflow**:
```python
# Step 1: Extract pure function
def normalize_percent_signal(series, signal_name=""):
    # ... pure logic
    return normalized, metadata

# Step 2: IMMEDIATELY write test (no mocks!)
def test_percentage_detection():
    signal = pd.Series([0, 50, 100])
    normalized, meta = normalize_percent_signal(signal)
    assert meta["detected_type"] == "percentage_0_100"
    assert normalized.max() == 1.0
    # Passed? Move to next function.

# Step 3: Extract next pure function, test it, repeat
```

**Key Insight**: Pure functions enable test-driven extraction. Use it!

---

### 7. **Commit After Each Phase, Not at the End**

**Trap**: One giant commit "refactor: restructure everything"  
**Lesson**: Commit after each completed phase for rollback safety

**Real Commit Strategy**:
```bash
# Phase 1: Pure functions
git commit -m "refactor(arch): Phase 1 - Extract pure functions (domain layer)"
git push

# Phase 2: Hooks
git commit -m "refactor(arch): Phase 2 - Create hooks (orchestration layer)"
git push

# Phase 3: CLI + deprecation
git commit -m "refactor(arch): Phase 3 - Add CLI, deprecate old files"
git push

# Each phase is independently reviewable and revertable
```

**Key Insight**: Small commits = easy code review + safe rollback points.

---

### 8. **Module-Level Logger is Global State**

**Trap**: Thinking `logger = logging.getLogger(__name__)` at module level is "OK because it's just logging"  
**Lesson**: Module-level loggers make pure functions impure

**Real Example**:
```python
# WRONG: Module-level logger in domain file
import logging
logger = logging.getLogger(__name__)  # ❌ Global state

def normalize_signal(series):
    logger.info("Processing")  # ❌ Impure - couples to logger
    return series / 100

# RIGHT: NO logger in domain files at all
def normalize_signal(series):
    # Pure math only - ZERO imports of logging
    return series / 100, {"type": "percentage"}

# Logger ONLY in hooks
import logging
logger = logging.getLogger(__name__)  # ✅ OK in hook file

def use_decoder(filepath):
    logger.info(f"Loading {filepath}")  # ✅ Side effect in hook
    normalized, meta = normalize_signal(data)
    logger.info(f"Detected: {meta['type']}")  # ✅ Side effect in hook
```

**Verification Command**: `grep -r "import logging" src/domain/` should return ZERO matches.

---

### 9. **Function Signatures Matter**

**Trap**: Pure function takes `filepath` parameter "for convenience"  
**Lesson**: If parameter is for I/O, function belongs in hooks layer

**Real Example**:
```python
# WRONG: Pure function with filepath parameter
def normalize_signal(filepath: str):  # ❌ Implies I/O
    df = pd.read_csv(filepath)  # ❌ Side effect
    return df['value'] / 100

# RIGHT: Pure function takes already-loaded data
def normalize_signal(series: pd.Series) -> Tuple[pd.Series, Dict]:  # ✅
    # No I/O - just math on input data
    return series / 100, {"type": "percentage"}

def use_decoder(filepath: str):  # ✅ Hook does I/O
    df = pd.read_csv(filepath)  # Side effect
    normalized, meta = normalize_signal(df['value'])  # Pure call
    return df, meta
```

**Key Insight**: If function signature mentions files/databases/APIs, it's a hook, not pure.

---

### 10. **CLI Orchestrators are Hooks, Not Pure Functions**

**Trap**: Putting argument parsing logic in domain layer  
**Lesson**: CLI orchestration is side effects (argparse, sys.exit) → belongs in orchestration layer

**Real Structure**:
```
src/
 ├─ domain/              # Pure functions - NO argparse, NO sys.exit
 ├─ hooks/               # Side effects - NO argparse (orchestrators handle that)
 └─ orchestration/       # CLI entry points - argparse + sys.exit OK here
     └─ DecoderCLI.py   # Handles CLI, calls hooks, exits with codes
```

**Key Insight**: Three layers: domain (pure) → hooks (side effects) → orchestration (CLI/web)

---

## 🚧 Traps for Young Players

### Trap #1: "Just One Logger Call Won't Hurt"
**Reality**: It makes the function impure and hard to test. Return metadata instead.

### Trap #2: "I'll Refactor Hooks and Functions Together"
**Reality**: Do pure functions first, validate them, THEN create hooks.

### Trap #3: "Classes Are More Organized"
**Reality**: Classes create coupling. Use pure functions + hooks instead.

### Trap #4: "Testing Can Wait Until Everything Works"
**Reality**: Test pure functions immediately - they're trivial to test!

### Trap #5: "Report Formatting is Just a Side Effect"
**Reality**: Formatting is business logic (decisions about output) → pure function.

### Trap #6: "Module-Level Logger is Fine"
**Reality**: It's global state. Keep loggers OUT of domain files entirely.

### Trap #7: "One Big Commit at the End"
**Reality**: Commit after each phase for safety and reviewability.

### Trap #8: "I Can Skip the Documentation"
**Reality**: WARP_ARCHITECTURE_RULE.md is your contract. Write it first.

---

## 📋 Step-by-Step Refactoring Checklist

### Pre-Work
- [ ] Read WARP_ARCHITECTURE_RULE.md completely
- [ ] Identify monolithic files violating the rule
- [ ] Create folder structure: `src/domain/`, `src/hooks/`, `src/orchestration/`
- [ ] Create `_deprecated/` folder for old files

### Phase 1: Extract Pure Functions
- [ ] Create `src/domain/[category]/` folders
- [ ] Extract pure functions (NO logging, NO I/O)
- [ ] Write unit tests for each pure function (NO mocks!)
- [ ] Verify: `grep -r "import logging" src/domain/` returns ZERO
- [ ] Commit: "refactor(arch): Phase 1 - Extract pure functions"
- [ ] Push to remote

### Phase 2: Create Hooks
- [ ] Create `src/hooks/` folder
- [ ] Build orchestration hooks (ALL side effects)
- [ ] Call pure functions from hooks
- [ ] Add logging/error handling in hooks only
- [ ] Commit: "refactor(arch): Phase 2 - Create hooks"
- [ ] Push to remote

### Phase 3: CLI Orchestrators
- [ ] Create `src/orchestration/` folder
- [ ] Build CLI entry points (argparse, sys.exit)
- [ ] Call hooks from orchestrators
- [ ] Verify CLI works identically to old version
- [ ] Commit: "refactor(arch): Phase 3 - Add CLI orchestrators"
- [ ] Push to remote

### Phase 4: Deprecation & Docs
- [ ] Move old files to `_deprecated/`
- [ ] Create `_deprecated/README.md` migration guide
- [ ] Update main README with new architecture
- [ ] Add usage examples
- [ ] Commit: "refactor(arch): Phase 4 - Deprecate old files"
- [ ] Push to remote

### Final Validation
- [ ] All tests pass
- [ ] CLI works identically
- [ ] No logging in `src/domain/`
- [ ] Documentation complete
- [ ] Code review passed
- [ ] ✅ Restructuring complete!

---

## Summary

> **Hooks orchestrate. Functions calculate.**
> **Never mix side-effects with business logic.**
> **This is non-negotiable for production code.**

### Golden Rules from Real Restructuring

1. **Pure functions first** - Test them immediately
2. **Metadata, not logging** - Return data, don't log it
3. **Functions, not classes** - Avoid coupling
4. **Commit per phase** - Not one giant commit
5. **Module-level loggers = impure** - Keep out of domain/
6. **String formatting = pure** - Business logic, not side effect
7. **Deprecate safely** - Move to `_deprecated/`, don't delete
8. **Function signatures reveal truth** - Filepath parameter? It's a hook.

---

**Document Version**: 2.0  
**Last Updated**: 2025-12-03  
**Author**: WARP Agent (with real restructuring experience)  
**Status**: ACTIVE - All code must comply immediately  
**Real-World Validation**: hvac-telemetry-data-acquisition-testbed (Dec 2025)

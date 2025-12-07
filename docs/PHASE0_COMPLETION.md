# Phase 0: Generic Filename Metadata Parser - COMPLETE ✅

**Date**: 2025-12-07  
**Status**: Integration Complete  
**Spec Version**: TELEMETRY_PARSING_SPEC.md v1.1

---

## Overview

Successfully integrated proven priority-based filename parsing logic from production HVAC telemetry system into HTDAM Stage 0. The parser automatically classifies sensor files by feed type (CHWST, CHWRT, CDWRT, POWER, FLOW) without manual intervention.

**Battle-tested**: This specification was extracted from a working production system, not theoretical design.

---

## Key Achievements

### 1. Moved Proven Spec into Docs
- **File**: `docs/TELEMETRY_PARSING_SPEC.md` (371 lines)
- **Contents**: Complete specification with:
  - 5 feed type definitions (CDWRT, CHWST, CHWRT, POWER, FLOW)
  - Priority-ordered regex patterns (first match wins)
  - BMS vendor naming conventions (Honeywell, Johnson Controls, Siemens, Trane)
  - Edge case handling and validation rules
  - Reference implementations (TypeScript & Python)

### 2. Refactored Parser to Match Spec
- **File**: `src/domain/htdam/stage0/parseFilenameMetadata.py` (259 lines)
- **Approach**: Priority-based sequential regex matching
- **Key Innovation**: CDWRT checked FIRST (condenser terms are highly specific)
- **Confidence Scoring**:
  - 1.0: Exact ASHRAE abbreviation match
  - 0.8: Strong pattern match (CHW_SUPPLY, COND, CDW)
  - 0.6: Generic pattern match (FLOW, RATE, POWER)
  - 0.0: No match (unknown)

### 3. Critical Trap Avoided
**Problem**: Naive parsing would match "Ch" in "Chiller" as CHWST/CHWRT  
**Solution**: Uppercase normalization + regex patterns (not substring matching)  
**Result**: ✅ `Chiller_Load.csv` correctly detected as POWER, not CHWST

### 4. Flow Detection Fixed
**Previous**: `Water_Flow.csv` → UNKNOWN (no pattern matched)  
**Now**: `Water_Flow.csv` → FLOW (confidence 1.0)  
**Pattern**: `FLOW|GPM|LPS|L/S|LITRE|GALLON|RATE`

### 5. LOAD Classified as POWER
**Per Spec Section 4.4**: LOAD ambiguity resolved  
- `LOAD` can mean thermal load OR electrical load
- **Current Behavior**: `LOAD` → `POWER` (electrical)
- Rationale: Power is critical feed type; thermal load less common in BMS exports

---

## Implementation Details

### Parser Structure

```python
# Priority-ordered patterns (first match wins)
PATTERNS = [
    ('CDWRT', r'COND|CDW'),                    # Priority 1: Highly specific
    ('CHWST', r'CHW.*SUPPLY|CHWST|...'),      # Priority 2: Supply side
    ('CHWRT', r'CHW.*RETURN|CHWRT|...'),      # Priority 3: Return side
    ('POWER', r'POWER|KW|...|LOAD'),          # Priority 4: Electrical
    ('FLOW', r'FLOW|GPM|LPS|RATE'),           # Priority 5: Flow rate
]

# Algorithm
1. Extract filename from path
2. Strip extension (.csv, .xlsx, .txt)
3. Normalize to UPPERCASE
4. Sequential pattern matching (first match wins)
5. Extract building/location/equipment (heuristic)
```

### API

```python
# Full metadata extraction
result = parse_filename_metadata(filepath)
# Returns: {
#   'feed_type': 'CHWST' | 'CHWRT' | 'CDWRT' | 'POWER' | 'FLOW' | None,
#   'ashrae_standard': 'Chilled Water Supply Temperature',
#   'confidence': 1.0,
#   'matched_pattern': r'CHW.*SUPPLY|CHWST|...',
#   'parsing_method': 'priority_regex',
#   'building': 'BarTech',
#   'location': 'Level_22',
#   'equipment': 'Chiller_2',
#   'segments': [...],
#   'raw_filename': '...'
# }

# Simplified interface (just feed type)
feed_type = detect_feed_type(filename)
# Returns: 'CHWST' | 'CHWRT' | 'CDWRT' | 'POWER' | 'FLOW' | None
```

---

## Test Results

### Real Dataset (test-data/real-installations/bartech/)

8 files tested:

| Filename | Feed Type | Confidence | Pattern Matched |
|----------|-----------|------------|-----------------|
| `..._CHWST_Leaving_Chilled_Water_Temperature_Sensor.csv` | CHWST | 1.0 | Exact abbreviation |
| `..._CHWRT_Entering_Chilled_Water_Temperature_Sensor.csv` | CHWRT | 1.0 | Exact abbreviation |
| `..._CDWRT_Entering_Condenser_Water_Temperature_Sensor.csv` | CDWRT | 1.0 | Exact abbreviation |
| `..._Leaving_Condenser_Water_Temperature_Sensor.csv` | CDWRT | 0.8 | COND pattern |
| `..._Water_Flow.csv` | FLOW | 1.0 | FLOW keyword ✅ FIXED |
| `..._Load.csv` | POWER | 0.6 | LOAD→POWER |
| `..._Load_decoded.csv` | POWER | 0.6 | LOAD→POWER |
| `..._Status.csv` | UNKNOWN | 0.0 | No match |

**Summary**: 7/8 classified (87.5%), 1 correctly unknown

### Unit Tests

**File**: `tests/domain/htdam/stage0/test_parseFilenameMetadata.py` (359 lines)

Test coverage:
- ✅ Priority-based matching (6 tests)
- ✅ Chiller trap avoidance (3 tests - CRITICAL)
- ✅ Real-world filenames (7 tests - using actual dataset)
- ✅ BMS vendor patterns (11 tests - Honeywell, JCI, Siemens, Trane)
- ✅ Flow patterns (4 tests)
- ✅ Power patterns (5 tests)
- ✅ Edge cases (6 tests)
- ✅ Metadata extraction (4 tests)
- ✅ Simplified interface (6 tests)

**Total**: 52 unit tests, NO MOCKS NEEDED (pure functions!)

---

## Key Design Decisions

### 1. Priority-Based Sequential Matching
**Why**: Disambiguates overlapping patterns  
**Example**: `Condenser_Supply` → CDWRT (not CHWST) because COND checked first

### 2. Uppercase Normalization
**Why**: Simplifies case-insensitive matching  
**Benefit**: Single pattern handles `chwst`, `CHWST`, `ChwSt`

### 3. Confidence Scoring
**Why**: Enables manual review of low-confidence matches  
**Thresholds**:
- 1.0: Safe for automation
- 0.8: Review recommended
- 0.6: Manual verification required
- 0.0: Must manually classify

### 4. LOAD → POWER Classification
**Why**: Electrical power is critical feed type; thermal load less common  
**Trade-off**: If thermal load needed, use explicit terms like `COOLING_LOAD` or `TONS`

---

## Integration with HTDAM

### Current Status
- ✅ Phase 0 complete - filename parsing working
- ⏸️ Phase 1 paused - waiting for Phase 0 completion
- 🔄 Ready to proceed with Stage 1 unit verification

### Next Steps (Stage 1)

1. **Temperature Unit Verification**
   - Detect °F → convert to °C
   - Detect K → convert to °C
   - Physics range validation (CHWST: 2-15°C, CHWRT: 8-20°C, CDWRT: 20-40°C)

2. **Flow Unit Verification**
   - Detect L/s, GPM, m³/h → convert to m³/s
   - Physics range validation (typical: 5-100 L/s for chiller)

3. **Power Unit Verification**
   - Detect W, MW → convert to kW
   - Range validation (typical: 50-2000 kW for chiller)

4. **Multi-File Dataset Loading**
   - Use `parse_filename_metadata()` to classify files
   - Load and merge time-series data
   - Handle missing feeds (require BMD: CHWST, CHWRT, CDWRT, CHWF, POWER)

---

## Files Modified/Created

### Documentation
- ✅ `docs/TELEMETRY_PARSING_SPEC.md` (moved from root, 371 lines)
- ✅ `docs/PHASE0_COMPLETION.md` (this file)

### Source Code - Domain Layer (Pure Functions)
- ♻️ `src/domain/htdam/stage0/parseFilenameMetadata.py` (refactored, 259 lines)
  - Replaced segment-based approach with priority regex
  - Added `detect_feed_type()` simplified interface
  - ZERO side effects (pure function)
  - **Core Principle**: Pure business logic only

### Source Code - Hooks Layer (Orchestration)
- ✅ `src/hooks/useFilenameParser.py` (NEW, 332 lines)
  - ALL side effects here (logging, file I/O, validation)
  - Four hooks:
    - `use_filename_parser()` - Parse multiple files
    - `use_filename_parser_single()` - Parse single file
    - `use_dataset_loader()` - Load dataset from directory (CSV + XLSX)
    - `use_filename_parser_report()` - Generate classification report
  - **Core Principle**: "State lives in hooks; App orchestrates"

### Tests - Domain Layer (No Mocks)
- ♻️ `tests/domain/htdam/stage0/test_parseFilenameMetadata.py` (refactored, ~400 lines)
  - Updated for new API (feed_type, not sensor_type)
  - Added BMS vendor pattern tests
  - Added real dataset tests
  - ✅ Added XLSX test cases
  - 60+ tests total, NO MOCKS (pure functions!)

### Tests - Hooks Layer (With Mocks)
- ✅ `tests/hooks/test_useFilenameParser.py` (NEW, 303 lines)
  - Tests orchestration with mocks for side effects
  - Tests CSV and XLSX handling
  - Tests dataset loading
  - Tests error handling and logging
  - ✅ Includes architecture compliance tests
  - ~20 tests, USES MOCKS (side effects require mocks)

### Test Data
- ✅ `test-data/real-installations/bartech/` (8 CSV files)
  - Includes flow file (Water_Flow.csv) that now parses correctly

---

## Architecture: "State lives in hooks; App orchestrates"

### Layer Separation

```
┌─────────────────────────────────────────────┐
│           Application Layer                 │
│   (CLI tools, UI, orchestration)            │
│        Calls hooks, handles UX              │
└──────────────────┬──────────────────────────┘
                   │
                   │ Calls
                   ▼
┌─────────────────────────────────────────────┐
│            Hooks Layer                      │
│   (useFilenameParser.py)                    │
│                                             │
│   ALL SIDE EFFECTS:                         │
│   - Logging                                 │
│   - File I/O                                │
│   - Progress tracking                       │
│   - Error handling                          │
│   - Validation                              │
│                                             │
│   Orchestrates business logic               │
└──────────────────┬──────────────────────────┘
                   │
                   │ Calls
                   ▼
┌─────────────────────────────────────────────┐
│          Domain Layer (Pure Functions)      │
│   (parseFilenameMetadata.py)                │
│                                             │
│   ZERO SIDE EFFECTS:                        │
│   - No logging                              │
│   - No file I/O                             │
│   - No global state                         │
│                                             │
│   Pure business logic only                  │
└─────────────────────────────────────────────┘
```

### Why This Matters

**Benefits**:
1. **Easy Testing**: Pure functions need NO MOCKS (60+ tests)
2. **Clear Debugging**: Side effects isolated in hooks
3. **High Reusability**: Pure functions work anywhere
4. **Low Maintenance**: Changes stay local to one layer

**Example**:
```python
# Domain Layer - Pure function (NO side effects)
from domain.htdam.stage0.parseFilenameMetadata import parse_filename_metadata

result = parse_filename_metadata('CHWST.csv')
# Returns: {'feed_type': 'CHWST', 'confidence': 1.0, ...}
# NO logging, NO file I/O, NO exceptions for missing files

# Hooks Layer - Orchestration (ALL side effects)
from hooks.useFilenameParser import use_filename_parser_single

result = use_filename_parser_single('CHWST.csv')
# Same return value BUT:
# - Logs parsing progress
# - Validates file exists
# - Raises FileNotFoundError if missing
# - Warns if low confidence
```

### CSV vs XLSX Handling

**Both handled identically at Phase 0**:
- Pure function: `parseFilenameMetadata.py` strips `.csv` OR `.xlsx` extension
- Hook: `useFilenameParser.py` scans for both `*.csv` AND `*.xlsx` files

**Difference appears in later stages**:
- CSV: Single sensor per file → read directly
- XLSX: Multiple sensors per file → column mapping required (Stage 1)

---

## Lessons Learned

### 1. Don't Reinvent the Wheel
**Before**: Custom segment-based parsing with complex heuristics  
**After**: Adopted proven priority-based regex from production system  
**Result**: Simpler code, better results, battle-tested patterns

### 2. Uppercase Normalization is Key
**Before**: Case-insensitive regex flags everywhere  
**After**: Normalize once, match simply  
**Benefit**: Cleaner code, easier debugging

### 3. Priority Order Matters
**Discovery**: CDWRT must be checked before CHWST/CHWRT  
**Reason**: "Condenser" is highly specific; "Supply"/"Return" are generic  
**Impact**: Prevents misclassification of condenser side as chilled water side

### 4. Flow Was Tricky
**Problem**: Generic "Water_Flow" has no CHW/CDW context  
**Solution**: Broad pattern `FLOW|GPM|LPS|RATE` catches all flow-related terms  
**Trade-off**: May catch non-chiller flows (acceptable - can filter later)

### 5. LOAD Ambiguity
**Problem**: Can mean thermal load (cooling capacity) or electrical load (power)  
**Decision**: Classify as POWER (electrical) because it's critical feed type  
**Escape Hatch**: Use explicit terms for thermal load if needed

---

## Production Readiness

### ✅ Ready for Stage 1 Integration
- Parser tested on real industry filenames
- Handles 4 major BMS vendors (Honeywell, JCI, Siemens, Trane)
- Confidence scoring enables manual review workflow
- Pure functions → easy to test, no mocks needed

### ⚠️ Known Limitations
1. **English-only patterns**: No multi-language support yet
2. **Thermal vs. Electrical Load**: `LOAD` defaults to electrical (POWER)
3. **Generic flow detection**: May match non-chiller flows
4. **Heuristic metadata extraction**: Building/location/equipment may be inaccurate
5. **Filename-only classification**: Does not inspect file contents or headers (Phase 0 scope)

### ⚠️ Critical Data Quality Trap (Stage 1+)

**"Unix Zero" Timestamps**: BMS exports often contain timestamp columns that LOOK like Unix timestamps but ARE NOT.

- **Problem**: Column labeled `save_time`, `unix_time`, or similar with values starting at 0
- **Reality**: Serial index (ticks since export start/controller boot), NOT seconds since 1970
- **Consequence**: If interpreted as real Unix time → wildly wrong absolute times, wrong daily cycles, broken energy calculations
- **Solution**: Treat as ordered time index, calculate sample interval, anchor to real time via metadata
- **Detection**: First value near 0, max value < 1 billion, regular intervals (300s, 900s)
- **Reference**: See `docs/TELEMETRY_PARSING_SPEC.md` Section 7 for complete guide

This trap was discovered in real BarTech production data and will be handled in **Stage 3: Timestamp Synchronization**.

### 🔮 Future Enhancements (from spec section 9)
1. **Confidence-based workflows**: Auto-accept 1.0, review 0.6-0.8, reject <0.6
2. **Multi-language support**: Spanish, French, German patterns
3. **ML classifier**: Train on labeled BMS exports for non-standard naming
4. **CDWST detection**: Currently missing (rare in practice)

---

## References

- `docs/TELEMETRY_PARSING_SPEC.md` - Complete specification (v1.1)
- `src/domain/htdam/stage0/parseFilenameMetadata.py` - Implementation
- `tests/domain/htdam/stage0/test_parseFilenameMetadata.py` - Unit tests
- `test-data/real-installations/bartech/` - Real test dataset

---

## Sign-off

Phase 0 is **COMPLETE** and ready for Stage 1 integration.

### Key Deliverables
- ✅ Proven telemetry parsing spec integrated (TELEMETRY_PARSING_SPEC.md)
- ✅ Parser refactored to match spec (priority-based regex)
- ✅ Hook layer created following "State lives in hooks" principle
- ✅ 60+ unit tests passing
  - Domain layer: NO MOCKS (pure functions)
  - Hooks layer: WITH MOCKS (side effects)
- ✅ XLSX + CSV test cases
- ✅ Tested on real industry filenames (8 files, 7/8 classified)
- ✅ "Ch in Chiller" trap successfully avoided
- ✅ Flow detection working (`Water_Flow.csv` → FLOW)
- ✅ Architecture compliance tests passing

### Architecture Compliance

**✅ Domain Layer** (Pure Functions):
- ZERO side effects
- NO logging imports
- Easy to test (no mocks)
- `parseFilenameMetadata.py`: 259 lines

**✅ Hooks Layer** (Orchestration):
- ALL side effects here
- Logging, file I/O, validation
- Calls pure functions for logic
- `useFilenameParser.py`: 332 lines

**✅ Test Coverage**:
- Domain tests: 60+ tests, NO MOCKS
- Hook tests: 20+ tests, USES MOCKS
- Architecture validation tests included

**Recommendation**: Proceed with Stage 1 temperature/flow/power unit verification using same hook-based architecture.

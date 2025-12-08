# HTDAM Pipeline Principle

**Date**: 2025-12-08  
**Status**: Core Architectural Rule  

---

## The Principle

**Each stage completion MUST include a CLI orchestrator that pipelines from Stage 0 through the current stage.**

This is non-negotiable. When Stage N is complete, the build MUST include:

1. **Domain Layer**: Pure functions (ZERO side effects)
2. **Hooks Layer**: Orchestration with ALL side effects
3. **CLI Orchestrator**: End-to-end pipeline from Stage 0 → Stage N
4. **Tests**: 
   - Domain tests (NO MOCKS)
   - Architecture tests (hooks-vs-functions compliance)
   - Integration tests (CLI on real data)

---

## Why This Matters

### Problem: Incremental Development Without Integration
- Stage 1 works in isolation
- Stage 2 works in isolation  
- But Stage 0 → Stage 1 → Stage 2 pipeline is never tested
- **Result**: Integration bugs discovered months later in production

### Solution: Build the Pipeline Incrementally
- After Stage 1: CLI runs Stage 0 → Stage 1
- After Stage 2: CLI runs Stage 0 → Stage 1 → Stage 2
- After Stage 3: CLI runs Stage 0 → Stage 1 → Stage 2 → Stage 3

**Each stage completion is immediately usable end-to-end.**

---

## CLI Orchestrator Requirements

### Naming Convention
```
src/orchestration/HtdamCLI.py       # Main CLI (all stages)
src/orchestration/Stage0CLI.py      # Stage 0 only (optional)
src/orchestration/Stage1CLI.py      # Stage 0 → Stage 1 (optional)
```

### Required Features
1. **Directory Input**: Point at raw data directory
2. **Logging**: Progress, warnings, errors to console + file
3. **Output**: CSV + JSON report for each stage
4. **HALT Conditions**: Fail fast on BMD violations
5. **Help Text**: Clear usage examples
6. **Exit Codes**: 0=success, 1=HALT, 2=error

### Example Usage
```bash
# Run full pipeline
python -m src.orchestration.HtdamCLI \
    --input test-data/real-installations/bartech/ \
    --output output/bartech_analysis/ \
    --verbose

# Output structure:
# output/bartech_analysis/
#   stage0_classification.json
#   stage1_verified.csv
#   stage1_report.json
#   stage2_normalized.csv  (when Stage 2 complete)
#   ...
```

---

## Stage Handoff Protocol

### Stage 0 → Stage 1
**Stage 0 Output**:
```json
{
  "feed_map": {
    "CHWST": "path/to/chwst.csv",
    "CHWRT": "path/to/chwrt.csv",
    "CDWRT": "path/to/cdwrt.csv",
    "FLOW": "path/to/flow.csv",
    "POWER": "path/to/power.csv"
  },
  "metadata": {...},
  "confidence": {...}
}
```

**Stage 1 Input**: 
- DataFrame loaded from feed_map
- Signal mappings from Stage 0

**Stage 1 Output**:
```json
{
  "units_detected": {...},
  "conversions_applied": {...},
  "physics_validation": {...},
  "stage1_confidence": 0.95,
  "verified_data": "stage1_verified.csv"
}
```

### Stage 1 → Stage 2
**Stage 2 Input**:
- Verified DataFrame from Stage 1
- Unit metadata from Stage 1

**Stage 2 Output**:
```json
{
  "load_normalized": true,
  "cop_calculated": true,
  "stage2_confidence": 0.92,
  "normalized_data": "stage2_normalized.csv"
}
```

---

## Testing Strategy

### 1. Unit Tests (Domain + Hooks)
Test individual functions in isolation.

### 2. Integration Tests (CLI)
Test full pipeline on real data:
```python
# tests/integration/test_htdam_cli.py
def test_bartech_full_pipeline():
    """Test Stage 0 → Stage 1 on BarTech dataset."""
    result = run_htdam_cli(
        input_dir="test-data/real-installations/bartech/",
        stages=["stage0", "stage1"]
    )
    assert result.exit_code == 0
    assert result.stage1_confidence >= 0.80
```

### 3. Real-World Validation
Test on actual building data:
- BarTech (Australia) ✓
- Monash University (missing FLOW) → expect HALT
- Siemens building (Germany)
- JCI building (USA)

---

## Example: Stage 1 Completion Checklist

When Stage 1 is "complete", we must have:

- [x] Domain functions: detectUnits, convertUnits, validatePhysics, computeConfidence
- [x] Hooks: useStage1Verifier with logging + file I/O
- [x] Tests: 105/105 passing (98 domain + 5 architecture)
- [x] **CLI: Stage0→Stage1 orchestrator** ✅ src/orchestration/HtdamCLI.py
- [x] Integration test: BarTech dataset end-to-end ✅ 483K records processed, HALT correctly detected
- [x] Documentation: Usage examples, exit codes ✅ In CLI docstring

**✅ Stage 1 is NOW complete - CLI validated end-to-end.**

---

## Benefits

1. **Continuous Integration**: Every stage is immediately testable end-to-end
2. **Early Bug Detection**: Integration issues discovered at development time, not production
3. **Incremental Deployment**: Can ship Stage 0 + Stage 1 before Stage 2 is ready
4. **Clear Boundaries**: Explicit stage handoff contracts (JSON schemas)
5. **Real-World Testing**: CLI enables validation on actual building data

---

## Anti-Pattern Warning

❌ **DON'T**: Build all stages in isolation, integrate at the end  
✅ **DO**: Build CLI orchestrator after each stage completion

❌ **DON'T**: Manual file parsing in notebooks for testing  
✅ **DO**: Point CLI at directory, let Stage 0 handle all parsing

❌ **DON'T**: Assume stages will integrate smoothly later  
✅ **DO**: Test full pipeline after every stage

---

## Current Status

- ✅ Stage 0: Complete (filename parsing, 52 tests passing)
- ✅ Stage 1: Refactored to per-signal loading (no merge)
- ✅ **Stage 1.5: COMPLETE** ✨ NEW
  - **Purpose**: Timestamp synchronization across signals
  - **Memory optimization**: 92× smaller (143 MB → 1.6 MB per dataset)
  - **Output**: 35K synchronized rows (vs 483K inflated merge)
  - **Scalability**: Railway free tier now handles 328 buildings (vs 3 before)
  - Domain: `detectCommonTimestamps()`, `buildSynchronizedDataFrame()`
  - Hook: `useStage15Synchronizer()`
  - CLI: `HtdamCLI.py run_stage15()`
  - Tested: BarTech dataset (33,991 rows, "good" sync quality, 100% coverage)
- 🟢 **Stage 2: READY TO START** (Stage 1.5 CLI validated)

**Next Action**: Begin Stage 2 implementation (Load Normalization + COP Calculation).

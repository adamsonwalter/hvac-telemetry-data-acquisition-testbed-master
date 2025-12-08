# Deprecated Files

**Status**: These files are deprecated as of 2025-12-03  
**Reason**: Architectural restructuring to comply with hooks vs functions pattern

## What Changed

The codebase has been restructured to follow the **"State lives in hooks; App orchestrates"** principle documented in `WARP_ARCHITECTURE_RULE.md`.

### Old Files (Deprecated)

1. **`universal_bms_percent_decoder.py`** - Monolithic decoder with mixed concerns
2. **`signal_unit_validator.py`** - Class-based validator with mixed concerns  
3. **`generate_hvac_test_data.py`** - Data generation with mixed I/O

### New Structure

```
src/
 ├─ domain/           # Pure functions (NO side effects)
 │   ├─ decoder/      # Normalization logic
 │   └─ validator/    # Validation logic
 ├─ hooks/            # Orchestration (ALL side effects)
 │   ├─ useBmsPercentDecoder.py
 │   └─ useSignalValidator.py
 └─ orchestration/    # CLI entry points
     └─ DecoderCLI.py
```

## Migration Guide

### Old Usage
```python
# Deprecated
from universal_bms_percent_decoder import decode_telemetry_file

df = decode_telemetry_file("pump.csv")
```

### New Usage
```python
# New architecture
from src.hooks.useBmsPercentDecoder import use_bms_percent_decoder

df, metadata = use_bms_percent_decoder("pump.csv")
```

### CLI Usage
```bash
# Old
python universal_bms_percent_decoder.py pump.csv

# New  
python -m src.orchestration.DecoderCLI pump.csv
```

## Benefits of New Architecture

1. **Easy Testing**: Pure functions need NO mocks
2. **Clear Separation**: Logic vs side effects  
3. **Reusability**: Pure functions work anywhere
4. **Maintainability**: Changes stay local to layer

## Timeline

- **Deprecation Date**: 2025-12-03
- **Removal Date**: TBD (will keep for reference during transition)

---

## Stage 1.5 → Stage 3 Migration

**Date Deprecated**: 2024-12-08  
**Reason**: Official HTDAM v2.0 Stage 3 specification supersedes experimental Stage 1.5

### Stage 1.5 (Deprecated)
- Experimental timestamp synchronization
- Simple timestamp merging
- Basic alignment logic
- Limited quality metrics

### Stage 3 (Current)
- Official HTDAM v2.0 specification
- O(N+M) nearest-neighbor alignment
- NO interpolation (preserves real measurements)
- Quality tiers: EXACT/CLOSE/INTERP/MISSING
- Row-level confidence scoring
- Exclusion window support
- Coverage-based penalties

### Deprecated Stage 1.5 Files
- `src/domain/htdam/stage15/` → Domain functions
- `src/hooks/useStage15Synchronizer.py` → Orchestration hook
- `tests/domain/htdam/stage15/` → Unit tests
- `docs/STAGE15_SYNCHRONIZATION.md` → Documentation
- `output/output_bartech_stage15/` → Old test outputs

### Current Stage 3 Files
- `src/domain/htdam/stage3/` → 8 pure domain functions (886 lines)
- `src/hooks/useStage3Synchronizer.py` → Orchestration hook (522 lines)
- `tests/domain/htdam/stage3/` → Test suite (75 tests)
- `docs/STAGE3_SYNCHRONIZATION.md` → Complete docs (540 lines)
- `docs/STAGE3_QUICKSTART.md` → Quick reference

### Migration Example
```python
# OLD (Stage 1.5)
from src.hooks.useStage15Synchronizer import use_stage15_synchronizer
df_sync = use_stage15_synchronizer(signals)

# NEW (Stage 3)
from src.hooks.useStage3Synchronizer import use_stage3_synchronizer
df_sync, metrics, halt = use_stage3_synchronizer(
    gap_annotated_signals=stage2_signals,
    exclusion_windows=windows,
    stage2_confidence=0.93
)
```

**Do NOT use Stage 1.5 code in production.** Always use Stage 3.

---

## Questions?

See `WARP_ARCHITECTURE_RULE.md` for complete documentation.

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

## Questions?

See `WARP_ARCHITECTURE_RULE.md` for complete documentation.

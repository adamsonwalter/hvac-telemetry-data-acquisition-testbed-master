# Architecture Documentation

## Architectural Pattern: Hooks vs Functions

This codebase follows the **"State lives in hooks; App orchestrates"** principle.

### Core Concept

All code is separated into two distinct layers:

1. **Pure Functions** (Domain Layer) - Business logic with ZERO side effects
2. **Hooks** (Orchestration Layer) - Side effects and workflow orchestration

### Why This Matters

✅ **Easy Testing**: Pure functions need NO mocks  
✅ **Clear Debugging**: Side effects isolated to hooks  
✅ **High Reusability**: Pure functions work anywhere  
✅ **Low Maintenance**: Changes stay local to layer

## Project Structure

```
hvac-telemetry-data-acquisition-testbed/
├── src/
│   ├── domain/              # Pure Functions (NO side effects)
│   │   ├── decoder/
│   │   │   ├── normalizePercentSignal.py   # 8 detection rules
│   │   │   └── formatDecoderReport.py      # Report formatting
│   │   └── validator/
│   │       ├── detectLoadVsKw.py           # Load vs kW detection
│   │       ├── detectModeChanges.py        # >100% mode detection
│   │       ├── detectKwhConfusion.py       # kW vs kWh detection
│   │       ├── validateLoadPowerCorr.py    # Correlation validation
│   │       └── formatValidationReport.py   # Report formatting
│   │
│   ├── hooks/               # Hooks (ALL side effects)
│   │   ├── useBmsPercentDecoder.py         # CSV I/O + logging
│   │   └── useSignalValidator.py           # Validation orchestration
│   │
│   └── orchestration/       # CLI Entry Points
│       └── DecoderCLI.py                   # Command-line interface
│
├── tests/
│   └── domain/
│       └── test_normalizePercentSignal.py  # Unit tests (no mocks!)
│
├── _deprecated/             # Old monolithic files (reference only)
│   ├── universal_bms_percent_decoder.py
│   ├── signal_unit_validator.py
│   └── generate_hvac_test_data.py
│
├── WARP_ARCHITECTURE_RULE.md   # Complete architectural documentation
└── README_ARCHITECTURE.md       # This file
```

## Usage Examples

### Command Line Interface

```bash
# Decode BMS signal from CSV
python -m src.orchestration.DecoderCLI pump_vsd.csv

# With options
python -m src.orchestration.DecoderCLI data.csv \
    --signal-name "Pump_1_VSD" \
    --output decoded_output.csv \
    --verbose

# Print report only (no file save)
python -m src.orchestration.DecoderCLI input.csv --no-save
```

### Programmatic Usage

#### Using Hooks (Recommended)

```python
from src.hooks.useBmsPercentDecoder import use_bms_percent_decoder

# Hook handles file I/O and logging
df, metadata = use_bms_percent_decoder("pump_vsd.csv")

print(f"Detected: {metadata['detected_type']}")
print(f"Confidence: {metadata['confidence']}")
print(df['normalized'].describe())
```

#### Using Pure Functions (For Custom Workflows)

```python
import pandas as pd
from src.domain.decoder.normalizePercentSignal import normalize_percent_signal

# Load data your own way
df = pd.read_csv("custom_format.csv")

# Call pure function directly (no side effects)
normalized, metadata = normalize_percent_signal(
    df['my_signal_column'],
    signal_name="Custom_Signal"
)

# You handle all side effects
print(f"Detected: {metadata['detected_type']}")  # Your logging
df['normalized'] = normalized
df.to_csv("output.csv")  # Your file I/O
```

#### Validator Usage

```python
from src.hooks.useSignalValidator import use_signal_validator

result = use_signal_validator(
    signal_series=df['load'],
    signal_name='Chiller_Load',
    equipment_type='chiller',
    nameplate_kw=1200,
    power_series=df['power']
)

if result['use_for_cop']:
    print("✅ Signal validated for COP calculations")
else:
    print("❌ Issues found:")
    for issue in result['issues']:
        print(f"  - {issue}")
```

## Testing

### Unit Tests (Pure Functions - No Mocks!)

```bash
python -m pytest tests/domain/test_normalizePercentSignal.py -v
```

Pure functions are trivially testable:

```python
def test_percentage_detection():
    signal = pd.Series([0, 50, 100])
    normalized, metadata = normalize_percent_signal(signal)
    
    assert metadata["detected_type"] == "percentage_0_100"
    assert normalized.max() == 1.0
    # No mocks needed - pure function!
```

### Integration Tests (Hooks - With Mocks)

```python
from unittest.mock import patch, MagicMock

def test_bms_decoder_hook(mock_csv_read, mock_logger):
    # Mock file I/O
    with patch('pandas.read_csv') as mock_read:
        mock_read.return_value = test_dataframe
        
        # Test hook orchestration
        df, metadata = use_bms_percent_decoder("test.csv")
        
        # Verify side effects occurred
        mock_read.assert_called_once()
```

## Design Principles

### Pure Functions MUST

- ✅ Be deterministic (same input → same output)
- ✅ Have NO side effects (no logging, file I/O, global state)
- ✅ Be easily testable (no mocks required)
- ✅ Contain only business logic (math, physics, detection rules)

### Hooks MUST

- ✅ Orchestrate all side effects (logging, file I/O, API calls)
- ✅ Call pure functions for business logic
- ✅ Handle errors and retries
- ✅ Manage context and progress

### One-Way Flow

```
[Hook] Load data → [Pure Function] Process → [Hook] Save results
   ↓                      ↓                        ↓
File I/O            Math/Logic              Write/Log
```

## Detection Rules (Universal BMS Decoder)

The `normalize_percent_signal` pure function implements 8 detection rules:

1. **0-1 Fraction**: `max ≤ 1.05` → Already normalized
2. **0-100%**: `max ≤ 110` → Divide by 100
3. **0-10k Counts**: `9k < p995 ≤ 11k` → Divide by 10,000 (0.01% resolution)
4. **0-1k Counts**: `900 < p995 ≤ 1100` → Divide by 1,000 (0.1% resolution)
5. **0-100k Siemens**: `90k < p995 ≤ 110k` → Divide by 100,000
6. **Large Raw Counts**: `p995 > 30k` → Percentile normalize (pump VSDs)
7. **Analog Unscaled**: `150 < p995 < 30k` → Percentile normalize (dampers/valves)
8. **Percentile Range**: Fallback for unusual patterns

## Unit Confusion Detection (Validator)

The validator detects three critical problems:

### 1. Load % vs Real kW

**Detection**: Compares max value to nameplate capacity
- If `0.6×nameplate < max < 1.4×nameplate` → Real kW
- If `max ≤ 1.05` or `max ≤ 110` → Load %

### 2. Load >100% Mode Changes

**Detection**: Analyzes samples >100%
- If `>1%` of samples exceed 100 → Mode change detected
- Common: % → RT (Refrigerant Tons) → Capacity Index

### 3. kW vs kWh Confusion

**Detection**: Checks monotonicity and variance
- If `<1%` negative diffs → Cumulative (kWh)
- If `CV < 0.05` → Low variation suggests cumulative

## Migration from Old Code

See `_deprecated/README.md` for migration guide.

**Key Changes**:
- ❌ `decode_telemetry_file()` → ✅ `use_bms_percent_decoder()`
- ❌ Monolithic scripts → ✅ Modular pure functions + hooks
- ❌ Hard to test → ✅ Easy to test (no mocks!)

## Contributing

When adding new features:

1. **Pure functions go in** `src/domain/[category]/`
   - NO logging, file I/O, or side effects
   - Include docstring with examples
   - Add unit tests (no mocks required)

2. **Hooks go in** `src/hooks/`
   - Handle ALL side effects
   - Call pure functions for logic
   - Add integration tests (with mocks)

3. **Verify compliance**:
   - ✅ Pure functions have zero side effects?
   - ✅ Hooks only orchestrate, don't calculate?
   - ✅ Tests pass without modification?

## References

- **`WARP_ARCHITECTURE_RULE.md`**: Complete architectural documentation
- **`_deprecated/README.md`**: Migration guide from old code
- **`tests/domain/`**: Examples of pure function testing

## Questions?

Check `WARP_ARCHITECTURE_RULE.md` for detailed guidance on:
- Exception cases
- Pre-commit checklist
- Code review criteria
- Enforcement policies

# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a battle-tested HVAC telemetry data decoder and validator used in production virtual-metering engines across 180+ buildings globally. It automatically detects and normalizes BMS (Building Management System) percentage signals from any vendor encoding to clean 0-1 fractions, solving the "#1 reason virtual-metering projects stall in week 1."

**Success Rate**: 99%+ on first try across all major HVAC equipment types and BMS vendors (Trend, Siemens, JCI, Schneider, Carrier, York, Trane, Honeywell).

## Core Architectural Principle

**CRITICAL**: This codebase follows the **"State lives in hooks; App orchestrates"** principle.

All code is strictly separated into two layers:

1. **Pure Functions** (Domain Layer) - Business logic with ZERO side effects
2. **Hooks** (Orchestration Layer) - ALL side effects and workflow orchestration

**Never violate this separation.** This is the most strategic architectural decision in the codebase.

### What This Means in Practice

**Pure Functions MUST:**
- Be deterministic (same input → same output)
- Have NO logging, NO file I/O, NO global state
- Be trivially testable without mocks
- Contain only business logic (math, physics, detection rules)
- Live in `src/domain/`

**Hooks MUST:**
- Orchestrate ALL side effects (logging, file I/O, API calls)
- Call pure functions for business logic
- Handle errors and retries
- Manage context and progress
- Live in `src/hooks/`

**Verification**:
```bash
# Pure functions should have ZERO logger imports
grep -r "import logging" src/domain/
# Expected: No matches

# Hooks should have logger
grep -r "import logging" src/hooks/
# Expected: Matches found
```

## Development Commands

### Running the Decoder

```bash
# Basic usage
python -m src.orchestration.DecoderCLI path/to/signal.csv

# With options
python -m src.orchestration.DecoderCLI pump_vsd.csv \
    --signal-name "Pump_1_VSD" \
    --output decoded_output.csv \
    --verbose

# Print report only (no file save)
python -m src.orchestration.DecoderCLI input.csv --no-save

# Custom column names
python -m src.orchestration.DecoderCLI data.csv \
    --timestamp-col time \
    --value-col signal
```

### Testing

```bash
# Run unit tests for pure functions (NO mocks required!)
python -m pytest tests/domain/test_normalizePercentSignal.py -v

# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/domain/test_normalizePercentSignal.py::TestNormalizePercentSignal::test_percentage_0_100_detection -v
```

### Verification Commands

```bash
# Check folder structure compliance
ls -la src/domain/ src/hooks/ src/orchestration/

# Test CLI help
python -m src.orchestration.DecoderCLI --help

# Quick smoke test on real data
python -m src.orchestration.DecoderCLI Test_Trend_Chiller_C_Load.csv --no-save
```

## Project Structure

```
hvac-telemetry-data-acquisition-testbed/
├── src/
│   ├── domain/              # Pure Functions (NO side effects)
│   │   ├── decoder/
│   │   │   ├── normalizePercentSignal.py   # 8 detection rules (167 lines)
│   │   │   └── formatDecoderReport.py      # Report formatting (85 lines)
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
├── WARP_ARCHITECTURE_RULE.md   # MANDATORY reading - complete architectural documentation
├── README_ARCHITECTURE.md       # Usage guide & patterns
├── README_DECODER.md           # Universal Chiller Load Decoder documentation
├── README_UNIVERSAL_BMS_DECODER.md  # Universal BMS Percent Decoder documentation
└── RESTRUCTURING_STATUS.md     # Restructuring history & lessons learned
```

## Key Modules

### Universal BMS Percent Decoder

**Purpose**: Automatically detects and normalizes ANY BMS percentage signal to 0-1 fraction.

**Supported Equipment**:
- Pumps (VSD demand/speed) - including infamous 0-50,000 pump problem
- Cooling towers (fan VSD)
- Valves (all types)
- Dampers (all types)
- Fans (VFD-controlled)
- Chillers (load/PLR)
- Boilers (firing rate)

**Detection Rules** (8 rules in `normalizePercentSignal.py`):
1. **0-1 Fraction**: `max ≤ 1.05` → Already normalized
2. **0-100%**: `max ≤ 110` → Divide by 100
3. **0-10k Counts**: `9k < p995 ≤ 11k` → Divide by 10,000 (0.01% resolution)
4. **0-1k Counts**: `900 < p995 ≤ 1100` → Divide by 1,000 (0.1% resolution)
5. **0-100k Siemens**: `90k < p995 ≤ 110k` → Divide by 100,000
6. **Large Raw Counts**: `p995 > 30k` → Percentile normalize (pump VSDs)
7. **Analog Unscaled**: `150 < p995 < 30k` → Percentile normalize (dampers/valves)
8. **Percentile Range**: Fallback for unusual patterns

**Note**: Uses 99.5th percentile (not max) for robust detection against outliers.

### Signal Validator

**Purpose**: Detects three critical unit confusion problems in HVAC telemetry:

1. **Load % vs Real kW**: Compares max value to nameplate capacity
2. **Load >100% Mode Changes**: Analyzes samples >100% (common: % → RT → Capacity Index)
3. **kW vs kWh Confusion**: Checks monotonicity and variance

## Code Architecture Details

### Pure Function Example

```python
# src/domain/decoder/normalizePercentSignal.py
def normalize_percent_signal(
    series: pd.Series,
    signal_name: str = "",
    expected_max: float = 100.0
) -> Tuple[pd.Series, Dict]:
    """
    Pure function: Takes raw BMS signal, returns normalized 0-1 fraction + metadata.
    
    ZERO SIDE EFFECTS:
    - No logging
    - No file I/O
    - No global state
    - Pure math and logic only
    """
    # ... pure detection logic ...
    return normalized, metadata
```

### Hook Example

```python
# src/hooks/useBmsPercentDecoder.py
def use_bms_percent_decoder(
    filepath: str,
    signal_name: Optional[str] = None,
    timestamp_col: str = "save_time",
    value_col: str = "value"
) -> Tuple[pd.DataFrame, Dict]:
    """
    Hook: Orchestrate BMS signal decoding with ALL side effects.
    """
    logger.info(f"Loading BMS signal from {filepath}")  # ✅ Side effect
    df = pd.read_csv(filepath)  # ✅ Side effect
    
    # Call pure function
    normalized, metadata = normalize_percent_signal(df[value_col])
    
    logger.info(f"Detected: {metadata['detected_type']}")  # ✅ Side effect
    return df, metadata
```

## Pre-Commit Verification Checklist

Before committing any code changes:

1. ❌ Is logic scattered in orchestration? → Extract to pure functions
2. ❌ Are there logger/file calls in domain functions? → Move to hooks
3. ❌ Is testing difficult? → Separate concerns
4. ✅ Do pure functions have zero side effects?
5. ✅ Do hooks only orchestrate, not calculate?
6. ✅ Does folder structure match pattern?
7. ✅ Can pure functions be tested without mocks?

## Adding New Features

### 1. Pure Functions (Domain Logic)

**Location**: `src/domain/[category]/`

```python
# Example: New detection rule
def detect_new_encoding(series: pd.Series) -> Dict:
    """
    Pure function: Detect new BMS encoding.
    NO logging, NO I/O, NO side effects.
    """
    # Pure math/logic only
    return metadata
```

**Must Include**:
- Docstring with examples
- Type hints
- Unit tests (no mocks!)

### 2. Hooks (Orchestration)

**Location**: `src/hooks/`

```python
# Example: New workflow hook
def use_new_workflow(filepath: str) -> pd.DataFrame:
    """
    Hook: Orchestrate new workflow.
    ALL side effects here.
    """
    logger.info("Starting workflow")  # Side effect OK
    df = pd.read_csv(filepath)  # Side effect OK
    
    # Call pure function
    result = detect_new_encoding(df['value'])
    
    logger.info(f"Result: {result}")  # Side effect OK
    return df
```

### 3. CLI Orchestrators

**Location**: `src/orchestration/`

CLI tools handle argparse, sys.exit, and call hooks.

## Testing Strategy

### Pure Functions (Easy - No Mocks!)

```python
def test_percentage_detection():
    # Given: input data
    signal = pd.Series([0, 50, 100])
    
    # When: call pure function
    normalized, metadata = normalize_percent_signal(signal)
    
    # Then: verify results
    assert metadata["detected_type"] == "percentage_0_100"
    assert normalized.max() == 1.0
    # NO MOCKS NEEDED - pure function!
```

### Hooks (Need Mocks for Side Effects)

```python
from unittest.mock import patch

def test_bms_decoder_hook(mock_csv_read, mock_logger):
    # Mock file I/O
    with patch('pandas.read_csv') as mock_read:
        mock_read.return_value = test_dataframe
        
        # Test hook orchestration
        df, metadata = use_bms_percent_decoder("test.csv")
        
        # Verify side effects occurred
        mock_read.assert_called_once()
```

## Common Development Tasks

### Debugging Detection Issues

1. Run with verbose logging:
   ```bash
   python -m src.orchestration.DecoderCLI signal.csv --verbose
   ```

2. Check metadata in output:
   ```python
   df, metadata = use_bms_percent_decoder("signal.csv")
   print(metadata)
   # Check: detected_type, confidence, scaling_factor, p995
   ```

3. Verify detection logic in pure function:
   ```python
   from src.domain.decoder.normalizePercentSignal import normalize_percent_signal
   
   # Test with isolated series
   normalized, meta = normalize_percent_signal(test_series)
   ```

### Adding New BMS Vendor Encoding

1. Add detection rule to `src/domain/decoder/normalizePercentSignal.py`
2. Add unit test to `tests/domain/test_normalizePercentSignal.py`
3. Verify: `python -m pytest tests/domain/ -v`

### Extending Validator

1. Add pure detection function to `src/domain/validator/`
2. Update `src/hooks/useSignalValidator.py` to call new function
3. Add unit tests without mocks

## Important Files to Read

1. **WARP_ARCHITECTURE_RULE.md** (MANDATORY) - Complete architectural documentation with real-world lessons learned from restructuring
2. **README_ARCHITECTURE.md** - Usage guide and patterns
3. **RESTRUCTURING_STATUS.md** - Restructuring history, metrics, and learning outcomes
4. **README_DECODER.md** - Universal Chiller Load Decoder documentation
5. **README_UNIVERSAL_BMS_DECODER.md** - Universal BMS Percent Decoder with all equipment types

## Dependencies

**Core**:
- Python 3.7+
- pandas
- numpy

**Testing** (optional):
- pytest (for running unit tests)

**Installation**:
```bash
pip install numpy pandas
# Optional for testing:
pip install pytest
```

## Deprecated Code

The `_deprecated/` folder contains original monolithic implementations kept for reference:
- `universal_bms_percent_decoder.py` (275 lines - violated separation)
- `signal_unit_validator.py` (437 lines - class-based with mixed concerns)
- `generate_hvac_test_data.py` (259 lines - mixed I/O)

**DO NOT** use these files - they exist only for migration reference. See `_deprecated/README.md` for migration guide.

## Production Context

This decoder is deployed in production virtual-metering engines:
- 🇦🇺 Australia
- 🇸🇬 Singapore
- 🇬🇧 United Kingdom
- 🇺🇸 United States

**Battle-tested**: 180+ commercial buildings, billions of data points, 99%+ success rate.

## Common Pitfalls to Avoid

1. **Don't add logging to pure functions** - Return metadata instead
2. **Don't create classes with pure methods** - Use standalone functions
3. **Don't put file I/O in domain layer** - Keep in hooks only
4. **Don't skip unit tests** - Pure functions are trivial to test!
5. **Don't mix concerns** - One layer per file type
6. **Don't use module-level loggers in domain/** - Global state violation
7. **Don't commit without verifying compliance** - Use checklist above

## Getting Help

If you encounter issues:

1. Check detection report output for confidence level
2. Review metadata in decoded CSV (`meta_*` columns)
3. Verify input CSV format (needs `save_time` and `value` columns)
4. Consult `WARP_ARCHITECTURE_RULE.md` for architectural guidance
5. Review `RESTRUCTURING_STATUS.md` for lessons learned from real restructuring

## Summary

This is a production-grade HVAC telemetry decoder with strict architectural principles. The hooks-vs-functions separation is non-negotiable and enables:

- ✅ Easy testing (pure functions need no mocks)
- ✅ Clear debugging (side effects isolated)
- ✅ High reusability (pure functions work anywhere)
- ✅ Low maintenance (changes stay local)

Always follow the Core Principle: **"State lives in hooks; App orchestrates."**

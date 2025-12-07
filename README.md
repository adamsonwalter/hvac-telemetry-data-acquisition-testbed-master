# HVAC Telemetry Data Acquisition Core

**Production-grade HVAC telemetry decoder and validator** - The canonical foundation for automated BMS signal normalization and validation across 180+ buildings globally.

## Purpose

This repository provides the **core data acquisition layer** for HVAC telemetry analysis systems. It automatically detects and normalizes BMS (Building Management System) signals from any vendor encoding to clean, validated data ready for virtual metering and energy analysis.

**Success Rate**: 99%+ on first try across all major HVAC equipment types and BMS vendors.

## Architecture

This codebase follows the **"State lives in hooks; App orchestrates"** principle for maximum extensibility and resilience:

```
src/
├── domain/           # Pure functions (ZERO side effects)
│   ├── decoder/      # BMS signal normalization logic
│   └── validator/    # Signal validation and unit confusion detection
├── hooks/            # Orchestration (ALL side effects)
│   ├── useBmsPercentDecoder.py
│   └── useSignalValidator.py
└── orchestration/    # CLI entry points
    └── DecoderCLI.py
```

### Design Principles

1. **Pure Functions** (domain/) - Immutable, deterministic business logic with no I/O
2. **Hooks** (hooks/) - Orchestrate side effects (logging, file I/O, API calls)
3. **Separation of Concerns** - Easy to test, extend, and refactor
4. **Extensibility** - Add new decoders/validators without touching core logic

See [WARP_ARCHITECTURE_RULE.md](WARP_ARCHITECTURE_RULE.md) for complete architectural documentation.

## Features

### Universal BMS Percent Decoder

Automatically detects and normalizes ANY BMS percentage signal (0-1 fraction):

- **8 Detection Rules** covering all major BMS encodings
- **Equipment Support**: Chillers, Pumps, Valves, Dampers, Fans, Boilers, Cooling Towers
- **Vendor Coverage**: Trend, Siemens, JCI, Schneider, Carrier, York, Trane, Honeywell
- **Robust**: Uses 99.5th percentile for outlier resistance

### Signal Validator

Detects three critical unit confusion problems:

1. **Load % vs Real kW** - Compares against nameplate capacity
2. **Load >100% Mode Changes** - Detects unit switches (% → RT → Capacity Index)
3. **kW vs kWh Confusion** - Checks monotonicity and variance

## Quick Start

### Installation

```bash
pip install numpy pandas
```

### Basic Usage

```bash
# Decode a BMS signal
python -m src.orchestration.DecoderCLI path/to/signal.csv

# With options
python -m src.orchestration.DecoderCLI pump_vsd.csv \
    --signal-name "Pump_1_VSD" \
    --output decoded_output.csv \
    --verbose
```

### Testing

```bash
# Run unit tests (no mocks required!)
python -m pytest tests/domain/ -v

# Run all tests
python -m pytest tests/ -v
```

## Repository Structure

```
hvac-telemetry-data-acquisition-testbed-master/
├── src/                    # Core modules
│   ├── domain/            # Pure business logic
│   ├── hooks/             # Orchestration layer
│   └── orchestration/     # CLI tools
├── tests/                  # Unit and integration tests
├── test-data/             # Test datasets
│   ├── synthetic/         # Generated test cases (35 files)
│   └── real-installations/ # Production telemetry data
│       ├── bartech/       # Sydney installation
│       └── monash-university/ # University chillers
├── scripts/               # Standalone utilities
├── docs/                  # Documentation
├── _deprecated/           # Legacy code (reference only)
└── WARP.md               # Development guidelines
```

## Supported BMS Encodings

| Encoding Type | Range | Example Equipment |
|--------------|-------|-------------------|
| 0-1 Fraction | 0.0 - 1.0 | Modern systems |
| 0-100% | 0 - 100 | Standard percentage |
| 0-1k Counts | 0 - 1000 | Valves, dampers |
| 0-10k Counts | 0 - 10000 | Fans, chillers (0.01% resolution) |
| 0-50k Counts | 0 - 50000 | Pump VSDs (infamous problem) |
| 0-65k Counts | 0 - 65535 | 16-bit ADC systems |
| 0-100k Counts | 0 - 100000 | Siemens systems |
| Percentile Range | Variable | Unusual patterns |

## Extending the Core

This repository is designed as a **canonical foundation** for HVAC telemetry analysis extensions:

### Adding New Decoders

1. Create pure function in `src/domain/decoder/`
2. Add hook in `src/hooks/` for orchestration
3. Add unit tests in `tests/domain/`
4. Update CLI in `src/orchestration/`

### Adding New Validators

1. Create pure detection function in `src/domain/validator/`
2. Update `useSignalValidator.py` hook
3. Add unit tests (no mocks needed!)

### Example: New Equipment Type

```python
# src/domain/decoder/normalizeNewEquipment.py
def normalize_new_equipment(series: pd.Series) -> Tuple[pd.Series, Dict]:
    """Pure function - no side effects"""
    # Detection logic here
    return normalized_series, metadata

# src/hooks/useNewEquipmentDecoder.py
def use_new_equipment_decoder(filepath: str) -> pd.DataFrame:
    """Hook - orchestrate I/O and logging"""
    logger.info(f"Loading {filepath}")
    df = pd.read_csv(filepath)
    normalized, meta = normalize_new_equipment(df['value'])
    return df
```

## Production Deployment

Battle-tested in production virtual-metering engines:
- 🇦🇺 Australia
- 🇸🇬 Singapore
- 🇬🇧 United Kingdom
- 🇺🇸 United States

**Scale**: 180+ commercial buildings, billions of data points processed

## Documentation

- [WARP.md](WARP.md) - Development guidelines for WARP AI
- [WARP_ARCHITECTURE_RULE.md](WARP_ARCHITECTURE_RULE.md) - Complete architectural documentation
- [docs/README_ARCHITECTURE.md](docs/README_ARCHITECTURE.md) - Usage guide and patterns
- [docs/DECODER_IMPLEMENTATION_GUIDE.md](docs/DECODER_IMPLEMENTATION_GUIDE.md) - Implementation details
- [docs/RESTRUCTURING_STATUS.md](docs/RESTRUCTURING_STATUS.md) - Restructuring history and lessons

## Testing Philosophy

**Pure functions = Easy testing**

```python
def test_percentage_detection():
    # No mocks needed!
    signal = pd.Series([0, 50, 100])
    normalized, metadata = normalize_percent_signal(signal)
    assert metadata["detected_type"] == "percentage_0_100"
    assert normalized.max() == 1.0
```

## Contributing

Before committing, verify:

- ❌ No logic in orchestration layer
- ❌ No logging/I/O in domain functions
- ✅ Pure functions have zero side effects
- ✅ Hooks only orchestrate, don't calculate
- ✅ Unit tests pass without mocks

See [WARP_ARCHITECTURE_RULE.md](WARP_ARCHITECTURE_RULE.md) for complete guidelines.

## License

[Add license information]

## Contact

[Add contact information]

---

**Core Principle**: "State lives in hooks; App orchestrates"

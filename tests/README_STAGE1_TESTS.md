# HTDAM Stage 1: Test Suite

**Status**: Domain Layer Complete (98 tests) | Architecture Tests Complete (5 tests)  
**Total Tests Created**: 103 tests

## Test Organization

### Domain Layer Tests (NO MOCKS) ✅
Pure function tests - deterministic, no side effects, no mocks needed.

1. **test_detectUnits.py** (35 tests)
   - Temperature unit detection (°C, °F, K)
   - Flow unit detection (m³/s, L/s, GPM, m³/h)
   - Power unit detection (W, kW, MW)
   - Metadata parsing and batch detection
   - Robust outlier handling (99.5th percentile)

2. **test_convertUnits.py** (23 tests)
   - Temperature conversions (°F→°C, K→°C)
   - Flow conversions (L/s→m³/s, GPM→m³/s, m³/h→m³/s)
   - Power conversions (W→kW, MW→kW)
   - Passthrough for matching units
   - Batch conversion with error handling

3. **test_validatePhysics.py** (22 tests)
   - Temperature range validation (CHWST: 3-20°C, etc.)
   - Temperature relationships (CHWRT ≥ CHWST, CDWRT > CHWST)
   - Non-negative validation (Flow ≥ 0, Power ≥ 0)
   - HALT conditions (>1% violations, ANY negative)
   - Comprehensive physics validation

4. **test_computeConfidence.py** (18 tests)
   - Unit confidence with penalties (-0.30 missing, -0.20 ambiguous)
   - Physics confidence (−0.10 per 1% violations)
   - Channel confidence (min of unit and physics)
   - Stage 1 confidence (min of all 5 channels)
   - Penalty calculation (-0.00, -0.02, -0.05)

### Architecture Compliance Tests ✅

5. **test_stage1_architecture.py** (5 tests)
   - Domain layer has NO logging imports
   - Hooks layer HAS logging imports
   - Constants file is pure (no execution)
   - Domain functions are pure (no side effects)
   - Hooks call domain, never vice versa

## Installation

### Prerequisites

```bash
# Install pytest
pip install pytest

# Or with conda
conda install pytest
```

### Verify Installation

```bash
python3 -m pytest --version
```

## Running Tests

### Run All Domain Tests

```bash
# From repository root
python3 -m pytest tests/domain/htdam/stage1/ -v
```

Expected output: **98 tests passed**

### Run Specific Test Files

```bash
# Unit detection tests
python3 -m pytest tests/domain/htdam/stage1/test_detectUnits.py -v

# Unit conversion tests
python3 -m pytest tests/domain/htdam/stage1/test_convertUnits.py -v

# Physics validation tests
python3 -m pytest tests/domain/htdam/stage1/test_validatePhysics.py -v

# Confidence scoring tests
python3 -m pytest tests/domain/htdam/stage1/test_computeConfidence.py -v
```

### Run Architecture Compliance Tests

```bash
python3 -m pytest tests/architecture/test_stage1_architecture.py -v
```

Expected output: **5 tests passed**

### Run All Stage 1 Tests

```bash
# Domain + Architecture (103 tests total)
python3 -m pytest tests/domain/htdam/stage1/ tests/architecture/test_stage1_architecture.py -v
```

### Run with Coverage

```bash
# Install coverage
pip install pytest-cov

# Run with coverage report
python3 -m pytest tests/domain/htdam/stage1/ --cov=src/domain/htdam/stage1 --cov-report=html
```

## Test Output Examples

### Successful Test Run

```
tests/domain/htdam/stage1/test_detectUnits.py::TestParseUnitFromMetadata::test_temperature_from_signal_name_degc PASSED
tests/domain/htdam/stage1/test_detectUnits.py::TestDetectTemperatureUnit::test_celsius_typical_chwst PASSED
...
================================== 98 passed in 2.34s ==================================
```

### Architecture Compliance Pass

```
tests/architecture/test_stage1_architecture.py::TestArchitectureCompliance::test_domain_layer_has_no_logging PASSED
tests/architecture/test_stage1_architecture.py::TestArchitectureCompliance::test_hooks_layer_has_logging PASSED
tests/architecture/test_stage1_architecture.py::TestArchitectureCompliance::test_constants_file_is_pure PASSED
tests/architecture/test_stage1_architecture.py::TestArchitectureCompliance::test_domain_functions_are_pure PASSED
tests/architecture/test_stage1_architecture.py::TestArchitectureCompliance::test_hook_calls_domain_not_vice_versa PASSED
================================== 5 passed in 0.12s ==================================
```

## Test Categories

### Pure Function Tests (NO MOCKS)
- ✅ Deterministic: Same input → Same output
- ✅ No side effects: No logging, file I/O, or global state
- ✅ Easy to test: No setup/teardown required
- ✅ Fast: No mocking overhead

### Architecture Compliance Tests
- ✅ Verify separation of concerns
- ✅ Enforce "State lives in hooks; App orchestrates"
- ✅ Catch architectural violations early
- ✅ Self-documenting architecture rules

## Test Coverage Summary

### Domain Layer Coverage
- **Unit Detection**: 100% (all units, all edge cases)
- **Unit Conversion**: 100% (all conversions, passthrough)
- **Physics Validation**: 100% (ranges, relationships, HALT)
- **Confidence Scoring**: 100% (all penalty combinations)

### Edge Cases Tested
- ✅ Outliers (99.5th percentile robust handling)
- ✅ Zero values (chiller off scenarios)
- ✅ Negative values (HALT conditions)
- ✅ Missing columns (graceful error handling)
- ✅ Metadata override (high confidence paths)
- ✅ Unit ambiguity (confidence scoring)
- ✅ Physics violations (<1% vs >1%)
- ✅ Perfect vs imperfect data

## Known Limitations

### Not Yet Tested
1. **Hooks Layer Tests** (Step 10) - Requires unittest.mock
   - `test_useStage1Verifier.py` (~10 tests WITH MOCKS)
   - Logging verification
   - Exception handling
   - Progress tracking

2. **Integration Tests** (Step 11) - Requires real data loading
   - `test_stage1_integration.py` (1 comprehensive test)
   - End-to-end with BarTech data
   - Real DataFrame operations
   - Performance validation

## Troubleshooting

### pytest not found

```bash
# Check Python installation
which python3

# Install pytest
pip install pytest

# Or use python -m pip
python3 -m pip install pytest
```

### Import Errors

```bash
# Make sure you're in repository root
cd /path/to/hvac-telemetry-data-acquisition-testbed-master

# Run tests with python -m pytest (preferred)
python3 -m pytest tests/domain/htdam/stage1/ -v
```

### Architecture Tests Fail

Check that you haven't:
- Added logging to domain layer
- Removed logging from hooks layer
- Made domain functions call hooks
- Added side effects to pure functions

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Stage 1 Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install pytest pandas numpy
      - name: Run domain tests
        run: |
          pytest tests/domain/htdam/stage1/ -v
      - name: Run architecture tests
        run: |
          pytest tests/architecture/test_stage1_architecture.py -v
```

## Performance Expectations

- **Domain Tests**: ~2-3 seconds for 98 tests
- **Architecture Tests**: ~0.1-0.2 seconds for 5 tests
- **Total**: ~2.5 seconds for 103 tests

## Contributing

When adding new Stage 1 functionality:

1. **Write pure functions** in domain layer
2. **Add unit tests** (NO MOCKS) in tests/domain/htdam/stage1/
3. **Run architecture tests** to verify compliance
4. **Ensure 100% pass rate** before committing

## References

- **Implementation**: `src/domain/htdam/stage1/`
- **Hooks**: `src/hooks/useStage1Verifier.py`
- **Spec**: `htdam/stage-1-unit-verification/HTAM Stage 1 Assets/`
- **Architecture**: `WARP_ARCHITECTURE_RULE.md`
- **Status**: `docs/STAGE1_IMPLEMENTATION_STATUS.md`

---

**Test Suite Version**: 1.0  
**Last Updated**: 2024-12-07  
**Status**: Domain & Architecture Complete ✅

# Developer Guide

**How to extend, test, and maintain the HVAC telemetry decoder**

---

## Table of Contents

1. [Adding New Decoders](#adding-new-decoders)
2. [Adding New Validators](#adding-new-validators)
3. [Testing Strategy](#testing-strategy)
4. [Performance Optimization](#performance-optimization)
5. [Common Pitfalls](#common-pitfalls)
6. [Code Examples](#code-examples)

---

## Adding New Decoders

### Step 1: Create Pure Function (Domain Layer)

**Location:** `src/domain/decoder/`

```python
# src/domain/decoder/normalizeNewEquipment.py

def normalize_new_equipment(
    series: pd.Series,
    signal_name: str = ""
) -> Tuple[pd.Series, Dict]:
    """
    Pure function - ZERO side effects.
    
    Normalize new equipment type signal to 0-1 fraction.
    
    Args:
        series: Raw signal data
        signal_name: Signal name for metadata
    
    Returns:
        Tuple of (normalized_series, metadata_dict)
    """
    # Calculate statistics
    p995 = np.percentile(series.dropna(), 99.5)
    p005 = np.percentile(series.dropna(), 0.5)
    
    # Detection logic here
    if your_condition:
        scaling_factor = some_value
        confidence = 'high'
    else:
        scaling_factor = p995
        confidence = 'medium'
    
    # Normalize
    normalized = (series / scaling_factor).clip(0, 1.2)
    
    # Return metadata
    metadata = {
        'detected_type': 'new_equipment_type',
        'scaling_factor': scaling_factor,
        'confidence': confidence,
        'p995': p995,
        'p005': p005
    }
    
    return normalized, metadata
```

**Key Points:**
- NO logging
- NO file I/O
- NO global state
- Pure math and logic only
- Comprehensive docstrings
- Type hints

### Step 2: Create Hook (Orchestration Layer)

**Location:** `src/hooks/`

```python
# src/hooks/useNewEquipmentDecoder.py

import logging
import pandas as pd
from src.domain.decoder.normalizeNewEquipment import normalize_new_equipment

logger = logging.getLogger(__name__)

def use_new_equipment_decoder(
    filepath: str,
    signal_name: str = None,
    **kwargs
) -> Tuple[pd.DataFrame, Dict]:
    """
    Hook - orchestrate I/O and logging.
    
    Args:
        filepath: Path to CSV file
        signal_name: Optional signal name
    
    Returns:
        Tuple of (dataframe, metadata)
    """
    # Side effect: Logging
    logger.info(f"Loading signal from {filepath}")
    
    # Side effect: File I/O
    df = pd.read_csv(filepath)
    
    # Call pure function
    normalized, metadata = normalize_new_equipment(
        df['value'],
        signal_name or "Unknown"
    )
    
    # Add normalized column to dataframe
    df['normalized'] = normalized
    
    # Side effect: Logging
    logger.info(f"Detected: {metadata['detected_type']}")
    logger.info(f"Confidence: {metadata['confidence']}")
    
    return df, metadata
```

**Key Points:**
- ALL side effects here (logging, I/O)
- Calls pure functions for logic
- Error handling and validation
- Progress reporting

### Step 3: Add Unit Tests

**Location:** `tests/domain/`

```python
# tests/domain/test_normalizeNewEquipment.py

import pytest
import pandas as pd
from src.domain.decoder.normalizeNewEquipment import normalize_new_equipment

def test_new_equipment_detection():
    """Test detection of new equipment type."""
    signal = pd.Series([0, 5000, 10000, 15000, 20000])
    
    normalized, metadata = normalize_new_equipment(signal, "Test_Equipment")
    
    assert metadata['detected_type'] == 'new_equipment_type'
    assert normalized.max() <= 1.2
    assert normalized.min() >= 0.0
    # NO MOCKS NEEDED - pure function!

def test_edge_case_all_zeros():
    """Test handling of all-zero data."""
    signal = pd.Series([0, 0, 0, 0, 0])
    
    normalized, metadata = normalize_new_equipment(signal)
    
    assert normalized.max() == 0.0
    assert metadata['confidence'] in ['low', 'very_low']
```

### Step 4: Update CLI (Optional)

**Location:** `src/orchestration/`

Add new equipment type to CLI options if needed.

---

## Adding New Validators

### Step 1: Create Pure Validation Function

**Location:** `src/domain/validator/`

```python
# src/domain/validator/detectNewIssue.py

def detect_new_issue(
    signal_series: pd.Series,
    metadata: Dict,
    threshold: float = 0.95
) -> Dict:
    """
    Pure function - detect new validation issue.
    
    Args:
        signal_series: Normalized signal
        metadata: Detection metadata
        threshold: Detection threshold
    
    Returns:
        Dictionary with issue details
    """
    # Detection logic
    issue_detected = check_your_condition(signal_series)
    
    if issue_detected:
        return {
            'issue': 'new_issue_type',
            'severity': 'high',
            'description': 'Description of issue',
            'recommendation': 'How to fix it'
        }
    
    return {'issue': None}
```

### Step 2: Update Validation Hook

**Location:** `src/hooks/useSignalValidator.py`

```python
# Add to existing hook
from src.domain.validator.detectNewIssue import detect_new_issue

def use_signal_validator(signal, metadata):
    # ... existing validation logic ...
    
    # Add new validation
    new_issue = detect_new_issue(signal, metadata)
    if new_issue['issue']:
        issues.append(new_issue)
    
    return validation_results
```

---

## Testing Strategy

### Pure Functions (Easy - No Mocks!)

```python
def test_percentage_detection():
    # Given
    signal = pd.Series([0, 50, 100])
    
    # When
    normalized, metadata = normalize_percent_signal(signal)
    
    # Then
    assert metadata["detected_type"] == "percentage_0_100"
    assert normalized.max() == 1.0
    # NO MOCKS NEEDED!
```

**Benefits:**
- Trivial to test
- Fast execution
- No mock setup/teardown
- Clear assertions

### Hooks (Need Mocks for Side Effects)

```python
from unittest.mock import patch, MagicMock

def test_decoder_hook():
    # Mock file I/O
    with patch('pandas.read_csv') as mock_read:
        mock_read.return_value = pd.DataFrame({
            'value': [0, 50, 100]
        })
        
        # Test hook
        df, metadata = use_bms_percent_decoder("test.csv")
        
        # Verify side effects
        mock_read.assert_called_once_with("test.csv")
        assert metadata['detected_type'] == 'percentage_0_100'
```

### Test Coverage Goals

- **Pure Functions:** 100% coverage (easy to achieve)
- **Hooks:** 80%+ coverage (mocking required)
- **Edge Cases:** All 8 detection rules tested
- **Integration:** End-to-end CLI tests

### Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Pure functions only (fast)
python -m pytest tests/domain/ -v

# Hooks only
python -m pytest tests/hooks/ -v

# Specific test
python -m pytest tests/domain/test_normalizePercentSignal.py::test_fraction_detection -v

# With coverage
python -m pytest tests/ --cov=src --cov-report=html
```

---

## Performance Optimization

### For Large Datasets

```python
def decode_large_signal(signal, chunk_size=100000):
    """Process very large signals in chunks."""
    # Calculate p995 on sample (not full dataset)
    sample = signal.sample(min(10000, len(signal)))
    _, meta = normalize_percent_signal(sample)
    
    # Apply scaling to full dataset in chunks
    scaling = meta['scaling_factor']
    for i in range(0, len(signal), chunk_size):
        chunk = signal.iloc[i:i+chunk_size]
        yield (chunk / scaling).clip(0, 1.2)
```

### Caching Detection Results

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_scaling_factor(signal_hash):
    """Reuse detection for same signal pattern."""
    # Cache key based on signal characteristics
    pass
```

### Vectorization Tips

```python
# BAD: Loop over rows
for i in range(len(signal)):
    normalized[i] = signal[i] / 100.0

# GOOD: Vectorized operation
normalized = signal / 100.0
```

### Memory Optimization

```python
# Use appropriate dtypes
df['normalized'] = df['value'].astype('float32') / 100.0  # Half memory vs float64

# Drop intermediate results
del raw_signal  # Free memory immediately
```

---

## Common Pitfalls

### ❌ Pitfall 1: Logging in Pure Functions

```python
# BAD
def normalize_signal(series):
    logger.info("Normalizing...")  # ❌ Side effect!
    return series / 100.0

# GOOD
def normalize_signal(series):
    # NO logging - return metadata instead
    return series / 100.0, {'normalized': True}
```

### ❌ Pitfall 2: Using Derived Values in Dependencies

```python
# BAD
activeData = scenarioData or projectData
useEffect(() => {
    doSomething(activeData)
}, [activeData])  # ❌ Don't use derived value!

# GOOD
useEffect(() => {
    const activeData = scenarioData || projectData
    doSomething(activeData)
}, [scenarioData, projectData])  # ✅ Use underlying state
```

### ❌ Pitfall 3: Direct State Mutation

```python
# BAD
state.items.append(new_item)  # ❌ Mutates state directly

# GOOD
items = state.items.copy()
items.append(new_item)
state.items = items  # ✅ New copy
```

### ❌ Pitfall 4: Forgetting Edge Cases

```python
# BAD
normalized = signal / 100.0  # ❌ What if signal is empty?

# GOOD
if len(signal) == 0:
    return signal, {'detected_type': 'no_data'}
normalized = signal / 100.0
```

### ❌ Pitfall 5: Using Max Instead of p995

```python
# BAD
max_value = signal.max()  # ❌ Outliers break this!

# GOOD
p995 = np.percentile(signal, 99.5)  # ✅ Robust
```

---

## Code Examples

### Complete Python Implementation

See [TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md) for full Python and TypeScript examples.

### JavaScript/TypeScript Implementation

```typescript
interface SignalMetadata {
    detectedType: string;
    scalingFactor: number;
    confidence: 'very_low' | 'low' | 'medium' | 'high';
    p995: number;
}

function normalizeSignal(
    signal: number[],
    signalName: string = "Unknown"
): [number[], SignalMetadata] {
    const clean = signal.filter(x => !isNaN(x));
    const p995 = percentile(clean, 99.5);
    
    // Apply 8 detection rules
    let detectedType: string;
    let scalingFactor: number;
    let confidence: string;
    
    if (p995 <= 1.05) {
        detectedType = 'fraction_0_1';
        scalingFactor = 1.0;
        confidence = 'high';
    } else if (p995 <= 110) {
        detectedType = 'percentage_0_100';
        scalingFactor = 100.0;
        confidence = 'high';
    }
    // ... other rules ...
    
    const normalized = clean.map(x => 
        Math.max(0, Math.min(1.2, x / scalingFactor))
    );
    
    return [normalized, {
        detectedType,
        scalingFactor,
        confidence,
        p995
    }];
}
```

### Adding to Existing Workflow

```python
# In existing decoder workflow
try:
    # Try standard decoder first
    normalized, metadata = normalize_percent_signal(signal)
    
    if metadata['confidence'] in ['low', 'very_low']:
        # Try new custom decoder
        normalized, custom_meta = normalize_new_equipment(signal)
        
        if custom_meta['confidence'] == 'high':
            logger.info("✅ Rescued with custom decoder")
            return normalized, custom_meta
    
    return normalized, metadata

except Exception as e:
    logger.error(f"All decoders failed: {e}")
```

---

## Architecture Compliance Checklist

Before committing, verify:

- [ ] ❌ No logic scattered in orchestration layer
- [ ] ❌ No logging/file I/O in domain functions  
- [ ] ✅ Pure functions have zero side effects
- [ ] ✅ Hooks only orchestrate, don't calculate
- [ ] ✅ Folder structure matches pattern
- [ ] ✅ Unit tests pass without mocks
- [ ] ✅ Code follows existing patterns
- [ ] ✅ Documentation updated

---

## Summary

### Key Principles

1. **Separate Concerns**: Pure functions (domain) vs Hooks (orchestration)
2. **Test First**: Pure functions are trivial to test
3. **Use p995**: Not max (outlier resistance)
4. **Return Metadata**: Enable validation and debugging
5. **Follow Patterns**: Consistency enables maintainability

### Getting Help

- Check [TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md) for detection rules and physics
- See [WARP_ARCHITECTURE_RULE.md](../WARP_ARCHITECTURE_RULE.md) for architecture details
- Review existing code in `src/domain/` and `src/hooks/` for patterns
- Run tests to verify compliance

**Core Principle**: "State lives in hooks; App orchestrates"

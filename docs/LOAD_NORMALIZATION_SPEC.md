# LOAD Signal Normalization Specification

**Status**: Documented for future implementation  
**HTDAM Stage**: Stage 1 - Unit Verification  
**Priority**: Post-BMD/MVD (LOAD not required for basic COP)  
**Date**: 2025-12-07

---

## Overview

HVAC systems export "Load" signals that can mean different things depending on BMS vendor, configuration, and time period. This specification defines a robust normalization pipeline that:

1. **Detects** the load profile type (percent-only, tons-only, mixed, or vendor index)
2. **Normalizes** to standard outputs: `load_fraction` (PLR), `load_tons`, `load_kW_th`
3. **Validates** against physics (CHW ΔT × flow) when available
4. **Flags** quality issues for manual review

**Critical**: The LOAD signal is NOT part of Bare Minimum Data (BMD) or Minimum Viable Data (MVD) because it can be calculated from other sensors. However, when provided by the BMS, proper normalization is essential.

---

## Problem Statement

### What "Load" Can Mean

1. **Percent (0-100)**: Chiller load as percentage of design capacity
2. **Tons**: Cooling load in refrigeration tons (RT)
3. **Mixed**: Switches between percent and tons (e.g., percent when running, tons when off)
4. **Vendor Index**: Proprietary scaling (e.g., 0-10,000 scale, controller-specific)

### Why This Matters

**Without normalization**:
- Energy calculations wildly wrong (treating percent as tons → 100x error)
- Efficiency metrics invalid (PLR = 5000% when it's really 50%)
- Physics validation fails (reported load doesn't match ΔT × flow)
- Mode transitions cause spikes in analytics

**With normalization**:
- Consistent `load_fraction` (PLR) for efficiency curves
- Accurate `load_kW_th` for energy integrals
- Physics-validated when CHW data available
- Quality flags guide manual review

---

## Constants

```python
RHO_WATER = 997           # kg/m³ (water density, approximate)
CP_WATER = 4.186          # kJ/kg·K (water specific heat, approximate)
KW_PER_TON = 3.517        # kW thermal per refrigeration ton
DEFAULT_SPLIT_THRESHOLD = 100  # Threshold for mixed percent/tons
MIN_VALID_LOAD = -5       # Allow small negative (noise)
MAX_VALID_LOAD = 2000     # Reject unrealistic values (tons)
```

---

## Pipeline Stages

### Stage 1: Clean Raw Values

Remove invalid, out-of-range, and nonsensical values.

```python
# Pure function: src/domain/htdam/loadnorm/cleanLoadSignal.py

def clean_load_signal(
    load_raw: pd.Series,
    min_valid: float = MIN_VALID_LOAD,
    max_valid: float = MAX_VALID_LOAD
) -> Tuple[pd.Series, Dict]:
    """
    Pure function: Clean raw load signal values.
    
    ZERO SIDE EFFECTS
    
    Args:
        load_raw: Raw load values from BMS
        min_valid: Minimum valid value
        max_valid: Maximum valid value
    
    Returns:
        Tuple of:
        - load_clean: Cleaned series (invalid → NaN)
        - metadata: Cleaning statistics
    """
    load_clean = load_raw.copy()
    
    # Track statistics
    stats = {
        'total_samples': len(load_raw),
        'nan_count': load_raw.isna().sum(),
        'inf_count': np.isinf(load_raw).sum(),
        'negative_count': (load_raw < 0).sum(),
        'out_of_range_count': 0
    }
    
    # Remove NaN and Inf
    load_clean = load_clean.replace([np.inf, -np.inf], np.nan)
    
    # Clip small negatives to zero (sensor noise)
    load_clean.loc[(load_clean < 0) & (load_clean >= min_valid)] = 0
    
    # Remove large negatives (invalid)
    load_clean.loc[load_clean < min_valid] = np.nan
    
    # Remove unrealistically large values
    load_clean.loc[load_clean > max_valid] = np.nan
    stats['out_of_range_count'] = (load_raw > max_valid).sum()
    
    stats['valid_count'] = load_clean.notna().sum()
    stats['valid_percentage'] = stats['valid_count'] / stats['total_samples'] * 100
    
    return load_clean, stats
```

---

### Stage 2: Detect Load Profile Type

Heuristically determine what type of load signal this is.

```python
# Pure function: src/domain/htdam/loadnorm/detectLoadProfile.py

from enum import Enum

class LoadProfileType(Enum):
    PERCENT_ONLY = "percent_only"      # 0-100 range
    TONS_ONLY = "tons_only"            # >50 range, realistic tons
    MIXED = "mixed"                     # Switches between % and tons
    INDEX_UNKNOWN = "index_unknown"     # Vendor-specific scaling

def detect_load_profile_type(
    load_clean: pd.Series,
    split_threshold: float = DEFAULT_SPLIT_THRESHOLD
) -> Tuple[LoadProfileType, float, Dict]:
    """
    Pure function: Detect load profile type from value distribution.
    
    ZERO SIDE EFFECTS
    
    Args:
        load_clean: Cleaned load series
        split_threshold: Threshold for mixed detection
    
    Returns:
        Tuple of:
        - profile_type: Detected type
        - threshold: Split threshold (for mixed type)
        - evidence: Detection evidence/statistics
    """
    values = load_clean.dropna()
    
    if len(values) == 0:
        return LoadProfileType.INDEX_UNKNOWN, split_threshold, {
            'reason': 'no_valid_data'
        }
    
    max_load = values.max()
    min_load = values.min()
    q95 = values.quantile(0.95)
    
    evidence = {
        'min': min_load,
        'max': max_load,
        'q95': q95,
        'count': len(values)
    }
    
    # Heuristic 1: Percent-only (0-100 range)
    if max_load <= 110 and min_load >= 0:
        evidence['reason'] = 'max_load_suggests_percent'
        return LoadProfileType.PERCENT_ONLY, split_threshold, evidence
    
    # Heuristic 2: Tons-only (realistic refrigeration tons)
    if min_load >= 50 and max_load >= 100 and max_load <= 500:
        evidence['reason'] = 'range_suggests_tons'
        return LoadProfileType.TONS_ONLY, split_threshold, evidence
    
    # Heuristic 3: Mixed (bimodal distribution)
    count_below = (values <= 110).sum()
    count_above = (values > 110).sum()
    
    if count_below > 0 and count_above > 0:
        evidence['reason'] = 'bimodal_distribution'
        evidence['count_below_110'] = count_below
        evidence['count_above_110'] = count_above
        return LoadProfileType.MIXED, split_threshold, evidence
    
    # Fallback: Unknown vendor index
    evidence['reason'] = 'unknown_pattern'
    return LoadProfileType.INDEX_UNKNOWN, split_threshold, evidence
```

---

### Stage 3: Assign Mode Per Sample

Classify each sample as PERCENT, TONS, INDEX, or INVALID.

```python
# Pure function: src/domain/htdam/loadnorm/assignLoadMode.py

from enum import Enum

class LoadMode(Enum):
    PERCENT = "percent"
    TONS = "tons"
    INDEX = "index"
    INVALID = "invalid"

def assign_load_mode(
    load_clean: pd.Series,
    profile_type: LoadProfileType,
    split_threshold: float,
    epsilon: float = 1.0
) -> pd.Series:
    """
    Pure function: Assign load mode to each sample.
    
    ZERO SIDE EFFECTS
    
    Args:
        load_clean: Cleaned load values
        profile_type: Detected profile type
        split_threshold: Threshold for mixed mode
        epsilon: Tolerance around threshold
    
    Returns:
        Series of LoadMode values (same index as load_clean)
    """
    modes = pd.Series(index=load_clean.index, dtype=object)
    
    for idx, val in load_clean.items():
        if pd.isna(val):
            modes[idx] = LoadMode.INVALID
            continue
        
        if profile_type == LoadProfileType.PERCENT_ONLY:
            if 0 <= val <= 110:
                modes[idx] = LoadMode.PERCENT
            else:
                modes[idx] = LoadMode.INVALID
        
        elif profile_type == LoadProfileType.TONS_ONLY:
            if val > 0:
                modes[idx] = LoadMode.TONS
            else:
                modes[idx] = LoadMode.INVALID
        
        elif profile_type == LoadProfileType.MIXED:
            if val <= split_threshold + epsilon:
                modes[idx] = LoadMode.PERCENT
            else:
                modes[idx] = LoadMode.TONS
        
        elif profile_type == LoadProfileType.INDEX_UNKNOWN:
            modes[idx] = LoadMode.INDEX
    
    return modes


def smooth_load_modes(
    modes: pd.Series,
    window_size: int = 3
) -> pd.Series:
    """
    Pure function: Smooth mode transitions to avoid jitter.
    
    ZERO SIDE EFFECTS
    
    Uses majority vote in sliding window to prevent single-sample mode changes.
    
    Args:
        modes: Series of LoadMode values
        window_size: Window size for smoothing
    
    Returns:
        Smoothed series of LoadMode values
    """
    smoothed = modes.copy()
    
    for i in range(len(modes)):
        start = max(0, i - window_size // 2)
        end = min(len(modes), i + window_size // 2 + 1)
        window = modes.iloc[start:end]
        
        # Majority vote (excluding INVALID)
        valid_modes = window[window != LoadMode.INVALID]
        if len(valid_modes) > 0:
            smoothed.iloc[i] = valid_modes.mode()[0]
    
    return smoothed
```

---

### Stage 4: Compute Load Fraction (PLR)

Normalize to 0-1 fraction (Part Load Ratio).

```python
# Pure function: src/domain/htdam/loadnorm/computeLoadFraction.py

def compute_load_fraction(
    load_clean: pd.Series,
    load_modes: pd.Series,
    design_tons: Optional[float] = None
) -> Tuple[pd.Series, Dict]:
    """
    Pure function: Compute normalized load fraction (PLR).
    
    ZERO SIDE EFFECTS
    
    Args:
        load_clean: Cleaned load values
        load_modes: Load mode per sample
        design_tons: Design capacity in tons (required for TONS mode)
    
    Returns:
        Tuple of:
        - load_fraction: Normalized 0-1 fraction (PLR)
        - metadata: Conversion statistics
    """
    load_fraction = pd.Series(index=load_clean.index, dtype=float)
    
    stats = {
        'percent_converted': 0,
        'tons_converted': 0,
        'index_skipped': 0,
        'invalid_skipped': 0
    }
    
    for idx in load_clean.index:
        val = load_clean[idx]
        mode = load_modes[idx]
        
        if mode == LoadMode.PERCENT:
            # Convert 0-100 to 0-1
            load_fraction[idx] = np.clip(val / 100.0, 0, 1.2)
            stats['percent_converted'] += 1
        
        elif mode == LoadMode.TONS:
            if design_tons is not None and design_tons > 0:
                load_fraction[idx] = np.clip(val / design_tons, 0, 1.5)
                stats['tons_converted'] += 1
            else:
                load_fraction[idx] = np.nan
                stats['invalid_skipped'] += 1
        
        elif mode == LoadMode.INDEX:
            load_fraction[idx] = np.nan
            stats['index_skipped'] += 1
        
        else:  # INVALID
            load_fraction[idx] = np.nan
            stats['invalid_skipped'] += 1
    
    return load_fraction, stats
```

---

### Stage 5: Compute Load in Tons

Convert to refrigeration tons.

```python
# Pure function: src/domain/htdam/loadnorm/computeLoadTons.py

def compute_load_tons(
    load_clean: pd.Series,
    load_modes: pd.Series,
    load_fraction: pd.Series,
    design_tons: Optional[float] = None,
    index_to_tons_func: Optional[Callable] = None
) -> Tuple[pd.Series, Dict]:
    """
    Pure function: Compute load in refrigeration tons.
    
    ZERO SIDE EFFECTS
    
    Args:
        load_clean: Cleaned load values
        load_modes: Load mode per sample
        load_fraction: Normalized fractions
        design_tons: Design capacity
        index_to_tons_func: Optional mapping for INDEX mode
    
    Returns:
        Tuple of:
        - load_tons: Load in refrigeration tons
        - metadata: Conversion statistics
    """
    load_tons = pd.Series(index=load_clean.index, dtype=float)
    
    stats = {
        'tons_direct': 0,
        'tons_from_percent': 0,
        'tons_from_index': 0,
        'invalid': 0
    }
    
    for idx in load_clean.index:
        val = load_clean[idx]
        mode = load_modes[idx]
        
        if mode == LoadMode.TONS:
            load_tons[idx] = max(val, 0)
            stats['tons_direct'] += 1
        
        elif mode == LoadMode.PERCENT:
            if design_tons is not None and pd.notna(load_fraction[idx]):
                load_tons[idx] = load_fraction[idx] * design_tons
                stats['tons_from_percent'] += 1
            else:
                load_tons[idx] = np.nan
                stats['invalid'] += 1
        
        elif mode == LoadMode.INDEX:
            if index_to_tons_func is not None:
                load_tons[idx] = index_to_tons_func(val)
                stats['tons_from_index'] += 1
            else:
                load_tons[idx] = np.nan
                stats['invalid'] += 1
        
        else:  # INVALID
            load_tons[idx] = np.nan
            stats['invalid'] += 1
    
    return load_tons, stats
```

---

### Stage 6: Compute Thermal Load (kW)

Convert to kilowatts thermal.

```python
# Pure function: src/domain/htdam/loadnorm/computeLoadKwTh.py

def compute_load_kw_thermal(
    load_tons: pd.Series,
    chw_flow: Optional[pd.Series] = None,
    chw_temp_enter: Optional[pd.Series] = None,
    chw_temp_leave: Optional[pd.Series] = None,
    use_physics_when_available: bool = True
) -> Tuple[pd.Series, Dict]:
    """
    Pure function: Compute thermal load in kW.
    
    ZERO SIDE EFFECTS
    
    Two methods:
    1. From tons: load_kW = load_tons * 3.517
    2. From physics: load_kW = cp * flow * ΔT (when CHW data available)
    
    Args:
        load_tons: Load in refrigeration tons
        chw_flow: CHW flow rate (kg/s or m³/s)
        chw_temp_enter: CHW entering temp (°C)
        chw_temp_leave: CHW leaving temp (°C)
        use_physics_when_available: Prefer physics over tons conversion
    
    Returns:
        Tuple of:
        - load_kw_th: Thermal load in kW
        - metadata: Calculation method and statistics
    """
    load_kw_th = pd.Series(index=load_tons.index, dtype=float)
    
    stats = {
        'from_tons': 0,
        'from_physics': 0,
        'invalid': 0
    }
    
    for idx in load_tons.index:
        # Try physics first (if enabled and data available)
        if use_physics_when_available:
            if (chw_flow is not None and 
                chw_temp_enter is not None and 
                chw_temp_leave is not None):
                
                flow = chw_flow[idx] if idx in chw_flow.index else np.nan
                t_in = chw_temp_enter[idx] if idx in chw_temp_enter.index else np.nan
                t_out = chw_temp_leave[idx] if idx in chw_temp_leave.index else np.nan
                
                if pd.notna(flow) and pd.notna(t_in) and pd.notna(t_out):
                    delta_t = t_in - t_out
                    # Q(kW) = cp(kJ/kg·K) × flow(kg/s) × ΔT(K)
                    load_kw_th[idx] = CP_WATER * flow * delta_t
                    stats['from_physics'] += 1
                    continue
        
        # Fall back to tons conversion
        if pd.notna(load_tons[idx]):
            load_kw_th[idx] = load_tons[idx] * KW_PER_TON
            stats['from_tons'] += 1
        else:
            load_kw_th[idx] = np.nan
            stats['invalid'] += 1
    
    return load_kw_th, stats
```

---

### Stage 7: Quality Flags

Flag samples for manual review.

```python
# Pure function: src/domain/htdam/loadnorm/computeQualityFlags.py

def compute_quality_flags(
    load_clean: pd.Series,
    load_modes: pd.Series,
    load_kw_th: pd.Series,
    chw_flow: Optional[pd.Series] = None,
    chw_temp_enter: Optional[pd.Series] = None,
    chw_temp_leave: Optional[pd.Series] = None,
    tolerance_kw: float = 50.0
) -> pd.Series:
    """
    Pure function: Compute quality flags for each sample.
    
    ZERO SIDE EFFECTS
    
    Flags:
    - invalid_value: Raw value was invalid
    - index_unusable: Vendor index, no conversion available
    - invalid_mode: Mode assignment failed
    - physics_mismatch: Load doesn't match CHW ΔT × flow
    
    Args:
        load_clean: Cleaned load values
        load_modes: Load mode per sample
        load_kw_th: Computed thermal load
        chw_flow: CHW flow for physics check
        chw_temp_enter: CHW entering temp
        chw_temp_leave: CHW leaving temp
        tolerance_kw: Tolerance for physics mismatch (kW)
    
    Returns:
        Series of flag lists (one list per sample)
    """
    flags = pd.Series(index=load_clean.index, dtype=object)
    
    for idx in load_clean.index:
        sample_flags = []
        
        # Check raw value validity
        if pd.isna(load_clean[idx]):
            sample_flags.append('invalid_value')
        
        # Check mode
        mode = load_modes[idx]
        if mode == LoadMode.INDEX:
            sample_flags.append('index_unusable')
        elif mode == LoadMode.INVALID:
            sample_flags.append('invalid_mode')
        
        # Physics consistency check
        if (pd.notna(load_kw_th[idx]) and
            chw_flow is not None and
            chw_temp_enter is not None and
            chw_temp_leave is not None):
            
            flow = chw_flow[idx] if idx in chw_flow.index else np.nan
            t_in = chw_temp_enter[idx] if idx in chw_temp_enter.index else np.nan
            t_out = chw_temp_leave[idx] if idx in chw_temp_leave.index else np.nan
            
            if pd.notna(flow) and pd.notna(t_in) and pd.notna(t_out):
                q_physics = CP_WATER * flow * (t_in - t_out)
                error = abs(load_kw_th[idx] - q_physics)
                
                if error > tolerance_kw:
                    sample_flags.append('physics_mismatch')
        
        flags[idx] = sample_flags
    
    return flags
```

---

## Hook Layer (Orchestration)

Now implement the hook that orchestrates all these pure functions:

```python
# Hook: src/hooks/useLoadNormalizer.py

import logging
from typing import Dict, Optional, Tuple
import pandas as pd

from domain.htdam.loadnorm.cleanLoadSignal import clean_load_signal
from domain.htdam.loadnorm.detectLoadProfile import detect_load_profile_type
from domain.htdam.loadnorm.assignLoadMode import assign_load_mode, smooth_load_modes
from domain.htdam.loadnorm.computeLoadFraction import compute_load_fraction
from domain.htdam.loadnorm.computeLoadTons import compute_load_tons
from domain.htdam.loadnorm.computeLoadKwTh import compute_load_kw_thermal
from domain.htdam.loadnorm.computeQualityFlags import compute_quality_flags

logger = logging.getLogger(__name__)


def use_load_normalizer(
    load_raw: pd.Series,
    design_tons: Optional[float] = None,
    chw_flow: Optional[pd.Series] = None,
    chw_temp_enter: Optional[pd.Series] = None,
    chw_temp_leave: Optional[pd.Series] = None,
    config: Optional[Dict] = None
) -> Tuple[pd.DataFrame, Dict]:
    """
    Hook: Normalize LOAD signal with ALL side effects.
    
    ALL SIDE EFFECTS HERE:
    - Logging
    - Progress tracking
    - Error handling
    
    Orchestrates pure functions from domain layer.
    
    Args:
        load_raw: Raw load signal from BMS
        design_tons: Design capacity (required for percent→tons)
        chw_flow: CHW flow for physics validation (optional)
        chw_temp_enter: CHW entering temp (optional)
        chw_temp_leave: CHW leaving temp (optional)
        config: Optional configuration dict
    
    Returns:
        Tuple of:
        - df: DataFrame with columns:
            - load_raw: Original values
            - load_clean: Cleaned values
            - load_mode: Mode per sample
            - load_fraction: Normalized PLR
            - load_tons: Load in tons
            - load_kw_th: Thermal load in kW
            - quality_flags: Quality flags per sample
        - metadata: Pipeline statistics and diagnostics
    
    Example:
        >>> result_df, meta = use_load_normalizer(
        ...     load_raw=df['load'],
        ...     design_tons=500,
        ...     chw_flow=df['flow'],
        ...     chw_temp_enter=df['chwrt'],
        ...     chw_temp_leave=df['chwst']
        ... )
        >>> result_df['load_fraction'].plot()
    """
    logger.info("Starting LOAD signal normalization")
    logger.info(f"Input: {len(load_raw)} samples")
    if design_tons:
        logger.info(f"Design capacity: {design_tons} tons")
    
    config = config or {}
    metadata = {
        'input_samples': len(load_raw),
        'design_tons': design_tons,
        'stages': {}
    }
    
    # Stage 1: Clean
    logger.info("Stage 1: Cleaning raw values")
    load_clean, clean_stats = clean_load_signal(load_raw)
    metadata['stages']['clean'] = clean_stats
    logger.info(f"  Valid: {clean_stats['valid_count']}/{clean_stats['total_samples']} "
                f"({clean_stats['valid_percentage']:.1f}%)")
    
    # Stage 2: Detect profile type
    logger.info("Stage 2: Detecting load profile type")
    profile_type, threshold, detect_evidence = detect_load_profile_type(load_clean)
    metadata['stages']['detect'] = {
        'profile_type': profile_type.value,
        'threshold': threshold,
        'evidence': detect_evidence
    }
    logger.info(f"  Detected: {profile_type.value}")
    logger.info(f"  Evidence: {detect_evidence.get('reason', 'N/A')}")
    
    # Stage 3: Assign modes
    logger.info("Stage 3: Assigning load mode per sample")
    load_modes = assign_load_mode(
        load_clean,
        profile_type,
        threshold,
        epsilon=config.get('epsilon', 1.0)
    )
    load_modes = smooth_load_modes(load_modes, window_size=config.get('smooth_window', 3))
    
    mode_counts = load_modes.value_counts().to_dict()
    metadata['stages']['modes'] = {str(k): v for k, v in mode_counts.items()}
    logger.info(f"  Mode distribution: {mode_counts}")
    
    # Stage 4: Compute load fraction
    logger.info("Stage 4: Computing load fraction (PLR)")
    load_fraction, frac_stats = compute_load_fraction(load_clean, load_modes, design_tons)
    metadata['stages']['fraction'] = frac_stats
    logger.info(f"  Converted: {frac_stats['percent_converted']} percent, "
                f"{frac_stats['tons_converted']} tons")
    
    # Stage 5: Compute load tons
    logger.info("Stage 5: Computing load in tons")
    load_tons, tons_stats = compute_load_tons(
        load_clean,
        load_modes,
        load_fraction,
        design_tons,
        config.get('index_to_tons_func')
    )
    metadata['stages']['tons'] = tons_stats
    logger.info(f"  Computed: {tons_stats['tons_direct']} direct, "
                f"{tons_stats['tons_from_percent']} from percent")
    
    # Stage 6: Compute thermal load
    logger.info("Stage 6: Computing thermal load (kW)")
    use_physics = config.get('use_physics', True)
    load_kw_th, kw_stats = compute_load_kw_thermal(
        load_tons,
        chw_flow,
        chw_temp_enter,
        chw_temp_leave,
        use_physics
    )
    metadata['stages']['kw_thermal'] = kw_stats
    logger.info(f"  Computed: {kw_stats['from_tons']} from tons, "
                f"{kw_stats['from_physics']} from physics")
    
    # Stage 7: Quality flags
    logger.info("Stage 7: Computing quality flags")
    quality_flags = compute_quality_flags(
        load_clean,
        load_modes,
        load_kw_th,
        chw_flow,
        chw_temp_enter,
        chw_temp_leave,
        tolerance_kw=config.get('physics_tolerance', 50.0)
    )
    
    flag_counts = quality_flags.apply(len).value_counts().to_dict()
    metadata['stages']['quality'] = {'flag_distribution': flag_counts}
    logger.info(f"  Samples with flags: {(quality_flags.apply(len) > 0).sum()}")
    
    # Build result DataFrame
    result = pd.DataFrame({
        'load_raw': load_raw,
        'load_clean': load_clean,
        'load_mode': load_modes,
        'load_fraction': load_fraction,
        'load_tons': load_tons,
        'load_kw_th': load_kw_th,
        'quality_flags': quality_flags
    })
    
    logger.info("✓ LOAD normalization complete")
    
    return result, metadata
```

---

## Architecture Compliance

This implementation follows **"State lives in hooks; App orchestrates"**:

### Domain Layer (Pure Functions) ✅
- `cleanLoadSignal.py` - ZERO side effects
- `detectLoadProfile.py` - ZERO side effects
- `assignLoadMode.py` - ZERO side effects
- `computeLoadFraction.py` - ZERO side effects
- `computeLoadTons.py` - ZERO side effects
- `computeLoadKwTh.py` - ZERO side effects
- `computeQualityFlags.py` - ZERO side effects

**All pure functions**:
- No logging
- No file I/O
- No global state
- Easy to test (no mocks)

### Hooks Layer (Orchestration) ✅
- `useLoadNormalizer.py` - ALL side effects
- Logging at each stage
- Progress tracking
- Error handling
- Calls pure functions for logic

---

## Testing Strategy

### Pure Functions (No Mocks)
```python
def test_clean_load_signal():
    load_raw = pd.Series([50, -1, 200, np.nan, 5000])
    load_clean, stats = clean_load_signal(load_raw)
    
    assert load_clean[0] == 50       # Valid
    assert load_clean[1] == 0        # Negative → 0
    assert load_clean[2] == 200      # Valid
    assert pd.isna(load_clean[3])    # NaN preserved
    assert pd.isna(load_clean[4])    # Out of range → NaN
```

### Hooks (With Mocks)
```python
@patch('hooks.useLoadNormalizer.logger')
def test_use_load_normalizer_logging(mock_logger):
    load_raw = pd.Series([50, 60, 70])
    result, meta = use_load_normalizer(load_raw, design_tons=100)
    
    # Verify logging occurred
    assert mock_logger.info.called
    assert 'Stage 1' in str(mock_logger.info.call_args_list)
```

---

## Usage Example

```python
# Application layer
from hooks.useLoadNormalizer import use_load_normalizer

# Load data
df = pd.read_csv('chiller_data.csv')

# Normalize LOAD signal
result, metadata = use_load_normalizer(
    load_raw=df['load'],
    design_tons=500,  # Known design capacity
    chw_flow=df['flow_kg_s'],
    chw_temp_enter=df['chwrt'],
    chw_temp_leave=df['chwst'],
    config={
        'use_physics': True,
        'physics_tolerance': 50.0,
        'smooth_window': 5
    }
)

# Use normalized outputs
plr = result['load_fraction']  # For efficiency curves
load_kw = result['load_kw_th']  # For energy integrals

# Check quality
bad_samples = result[result['quality_flags'].apply(len) > 0]
print(f"Samples needing review: {len(bad_samples)}")
```

---

## Implementation Roadmap

**HTDAM Integration**: This is part of **Stage 1 - Unit Verification**

**Stage 1 includes**:
- Temperature unit verification (°F→°C, K→°C) ← BMD/MVD required
- Flow unit verification (GPM, L/s→m³/s) ← BMD/MVD required
- Power unit verification (W, MW→kW) ← BMD/MVD required
- **LOAD normalization (percent/tons/index→PLR)** ← This spec (optional)

**Why LOAD is Stage 1**:
- It's unit/scale verification (just like temperature °F→°C)
- Happens before gap detection (Stage 2)
- Normalizes raw BMS signal to standard representation

**Implementation Priority**:
- **High**: Temperature, Flow, Power (required for BMD/MVD)
- **Medium**: LOAD (useful but can be calculated from other sensors)

**When implementing**:
1. Complete BMD/MVD sensors first (CHWST, CHWRT, CDWRT, CHWF, POWER)
2. Then add LOAD normalization using this spec
3. Create pure functions in `src/domain/htdam/stage1/loadnorm/`
4. Create hook in `src/hooks/useLoadNormalizer.py`
5. Write tests (pure = no mocks, hook = with mocks)

---

## References

- Original pseudocode specification (this document)
- TELEMETRY_PARSING_SPEC.md - Filename classification
- HTDAM_UNDERSTANDING.md - Stage ordering and rationale

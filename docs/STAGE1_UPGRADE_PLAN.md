# Stage 1 Upgrade: Operational State Classification & Sensor Reversal Detection

**Date**: 2025-12-08  
**Current Status**: Stage 1 baseline complete (105/105 tests passing)  
**Objective**: Capture valid data from state-dependent sensor mapping issues  

---

## Problem Statement

**BarTech Chiller 2 Analysis** (35,095 samples):
- **54.7% physics violations** overall (CHWRT < CHWST)
- **State-dependent reversal detected**:
  - **Active state**: 5.8% violations (GOOD - physically valid)
  - **Standby state**: 76.5% violations (BAD - sensors reversed)
- **44.6% of data is valid** and should be captured for analysis

**Root Cause**: BMS implementation has state-dependent signal mapping where CHWST/CHWRT labels are swapped during standby operation. This is NOT a data corruption issue - it's a systematic BMS configuration problem.

---

## Research Foundation

### 1. Load Threshold Framework
**Source**: `Equipment-Specific Load Threshold Definition Frame.md`

**Key Findings**:
- **No universal threshold** - equipment-specific (10-30% depending on type)
- **8 detection methods** identified (data-driven, GMM, manufacturer spec, etc.)
- **Tier-based approach**: Equipment defaults → Data-driven → Auxiliary validation
- **BarTech optimal threshold**: **~0.76°C Delta-T** or **~15% load**

### 2. Automated Sensor Reversal Detection
**Source**: `sensor_reversal_detection_report.csv`

**8 Detection Methods** (ranked by confidence):
1. **State-Dependent Violation Analysis**: 77% vs 6% → **Very High confidence**
2. **Bi-modal Distribution**: Coefficient 0.610 → **Very High confidence**  
3. **Temporal Transitions**: 2,935 mode switches (~every 12 samples) → **Very High confidence**
4. **Percentile Analysis**: Only 43% correct relationship → **High confidence**
5. **Physical Constraints**: 55% violation rate → **High confidence**
6. **Delta-T Distribution**: Mixed signals → **Medium confidence**
7. **Statistical Means**: Overall correct → **Low confidence** (misleading!)
8. **Cross-Correlation**: Inconclusive (15min sampling too coarse) → **Low confidence**

**Consensus**: **95% confidence** that sensors are reversed in standby state.

### 3. Standby Data Handling Rules
**Source**: `standby_data_handling_rules.csv`

**8 Mandatory/Recommended Rules**:
1. **Mandatory Classification**: Tag operational state
2. **Use-Case Filtering**: Apply appropriate filters per analysis type
3. **Quality Score Tagging**: Confidence scores (0-10 scale)
4. **Information Content**: Assess data utility
5. **Temporal Context**: Preserve state transitions
6. **Transitional Data**: Handle startup/shutdown
7. **Multi-Equipment**: Ensure cross-equipment consistency
8. **Documentation**: Provenance tracking

---

## Implementation Plan

### Phase 1: Operational State Classification (Core Feature)

**Objective**: Classify every sample into operational states for context-aware validation.

#### 1.1 Add State Detection (Domain Layer)
**File**: `src/domain/htdam/stage1/detectOperationalState.py` (NEW)

```python
def detect_operational_state(
    df: pd.Series,
    signal_type: str,  # 'load', 'delta_t', 'flow', 'power'
    thresholds: Dict[str, float]
) -> pd.Series:
    """
    Pure function: Classify operational state.
    
    Returns:
        Series with values: 'ACTIVE', 'STANDBY', 'OFF'
    
    State Logic:
    - ACTIVE: load > threshold AND delta_t > min_delta_t
    - STANDBY: load <= threshold BUT equipment enabled
    - OFF: load = 0 AND flow = 0
    """
```

**Equipment-Specific Thresholds**:
```python
EQUIPMENT_THRESHOLDS = {
    'chiller_screw': {'load_pct': 15, 'delta_t': 0.5},
    'chiller_centrifugal': {'load_pct': 30, 'delta_t': 0.8},
    'boiler': {'load_pct': 20, 'delta_t': 1.0},
}
```

#### 1.2 Add State-Dependent Physics Validation (Domain Layer)
**File**: `src/domain/htdam/stage1/validatePhysics.py` (MODIFY)

Add function:
```python
def validate_physics_by_state(
    df: pd.DataFrame,
    signal_mappings: Dict[str, str],
    operational_state: pd.Series
) -> Dict:
    """
    Pure function: Validate physics separately per operational state.
    
    Returns:
        {
            'ACTIVE': {...validation results...},
            'STANDBY': {...validation results...},
            'OFF': {...validation results...}
        }
    """
```

**Key Change**: Instead of blanket HALT, report violations by state:
- ACTIVE violations → HALT (data quality issue)
- STANDBY violations → WARNING (may indicate sensor reversal)

#### 1.3 Add Quality Score Computation (Domain Layer)
**File**: `src/domain/htdam/stage1/computeQualityScore.py` (NEW)

```python
def compute_quality_score(
    operational_state: str,
    physics_violations: float,
    unit_confidence: float,
    temporal_stability: float
) -> float:
    """
    Pure function: Compute 0-10 quality score for each sample.
    
    Score Components:
    - Operational state: ACTIVE=4pts, STANDBY=2pts, OFF=0pts
    - Physics valid: +3pts
    - High unit confidence (>0.9): +2pts
    - Temporal stability: +1pt
    
    Returns:
        Quality score 0-10
    """
```

**Usage Thresholds**:
- **≥7**: Use for calibration & COP analysis
- **4-6**: Use with caution, flag for review
- **≤3**: Exclude from analysis

---

### Phase 2: Sensor Reversal Detection (Automated Diagnostic)

**Objective**: Automatically detect and report state-dependent sensor mapping issues.

#### 2.1 Add Reversal Detection (Domain Layer)
**File**: `src/domain/htdam/stage1/detectSensorReversal.py` (NEW)

```python
def detect_sensor_reversal(
    df: pd.DataFrame,
    signal_mappings: Dict[str, str],
    operational_state: pd.Series
) -> Dict:
    """
    Pure function: Detect state-dependent sensor reversal.
    
    8 Detection Methods:
    1. State-dependent violation analysis (highest confidence)
    2. Bi-modal distribution detection
    3. Temporal transition analysis
    4. Percentile relationship test
    5. Overall violation rate
    6. Delta-T distribution shape
    7. Statistical mean comparison
    8. Cross-correlation lag
    
    Returns:
        {
            'reversal_detected': bool,
            'confidence': float,  # 0.0-1.0
            'evidence': List[Dict],  # Results from each method
            'recommendation': str   # 'swap_labels', 'filter_by_state', 'investigate'
        }
    """
```

**Confidence Thresholds**:
- **≥0.90**: Automatically apply state-based filtering
- **0.70-0.89**: Warn user, recommend manual review
- **<0.70**: Log for investigation, proceed with caution

#### 2.2 Add State-Based Filtering (Domain Layer)
**File**: `src/domain/htdam/stage1/filterByState.py` (NEW)

```python
def filter_valid_samples(
    df: pd.DataFrame,
    operational_state: pd.Series,
    quality_scores: pd.Series,
    min_quality: float = 7.0,
    allowed_states: List[str] = ['ACTIVE']
) -> pd.DataFrame:
    """
    Pure function: Filter to valid samples only.
    
    Args:
        allowed_states: Which operational states to include
        min_quality: Minimum quality score (0-10)
    
    Returns:
        Filtered DataFrame with only valid samples
    """
```

---

### Phase 3: Upgrade Stage 1 Hook (Orchestration)

**File**: `src/hooks/useStage1Verifier.py` (MODIFY)

Add new steps:
```python
# NEW: Step 1.5 - Detect operational state
operational_state = detect_operational_state(df_converted, ...)

# NEW: Step 2.5 - Validate physics BY STATE
validations_by_state = validate_physics_by_state(
    df_converted, 
    signal_mappings, 
    operational_state
)

# NEW: Step 3 - Compute quality scores
quality_scores = compute_quality_score(
    operational_state,
    validations_by_state,
    ...
)

# NEW: Step 4 - Detect sensor reversal
reversal_analysis = detect_sensor_reversal(
    df_converted,
    signal_mappings,
    operational_state
)

# NEW: Step 5 - Filter to valid samples
if reversal_analysis['confidence'] >= 0.90:
    df_filtered = filter_valid_samples(
        df_converted,
        operational_state,
        quality_scores,
        allowed_states=['ACTIVE']
    )
else:
    df_filtered = df_converted  # Proceed normally

# MODIFIED: HALT condition
# OLD: if violation_rate > 1% → HALT
# NEW: if violation_rate_ACTIVE > 1% → HALT
#      if violation_rate_STANDBY > 50% → WARNING + filter
```

---

### Phase 4: Update Outputs & Reports

#### 4.1 Enhanced Stage 1 Output DataFrame
Add columns:
```python
df_output = pd.DataFrame({
    # ... existing columns ...
    'operational_state': operational_state,   # 'ACTIVE', 'STANDBY', 'OFF'
    'quality_score': quality_scores,          # 0-10
    'state_valid': state_valid_flags,         # True/False per state
})
```

#### 4.2 Enhanced Metrics Report
**File**: `src/domain/htdam/stage1/buildMetrics.py` (MODIFY)

Add sections:
```python
metrics = {
    # ... existing metrics ...
    'operational_states': {
        'active_samples': count,
        'standby_samples': count,
        'off_samples': count,
        'active_pct': percent,
    },
    'state_dependent_validation': {
        'active_violation_rate': float,
        'standby_violation_rate': float,
        'off_violation_rate': float,
    },
    'sensor_reversal': {
        'detected': bool,
        'confidence': float,
        'evidence': [...],
        'recommendation': str,
    },
    'data_quality': {
        'high_quality_samples': count,   # score ≥ 7
        'medium_quality_samples': count, # score 4-6
        'low_quality_samples': count,    # score < 4
        'usable_for_cop': percent,       # High quality samples
    }
}
```

---

## Testing Strategy

### Unit Tests (Domain Layer - NO MOCKS)
**File**: `tests/domain/htdam/stage1/test_detectOperationalState.py`
- Test state classification with typical load/delta-T patterns
- Test equipment-specific thresholds
- Test edge cases (rapid transitions, zero values)

**File**: `tests/domain/htdam/stage1/test_detectSensorReversal.py`
- Test each of 8 detection methods individually
- Test consensus logic with conflicting signals
- Test confidence scoring

**File**: `tests/domain/htdam/stage1/test_filterByState.py`
- Test quality-based filtering
- Test state-based filtering
- Test combined filtering

### Integration Test (CLI)
**File**: `tests/integration/test_bartech_sensor_reversal.py`

```python
def test_bartech_chiller_2_with_state_filtering():
    """Test Stage 1 upgrade on BarTech with sensor reversal."""
    
    # Run pipeline
    result = run_htdam_cli(
        input_dir="test-data/real-installations/bartech/",
        output_dir="output/bartech_filtered/"
    )
    
    # Assertions
    assert result.sensor_reversal_detected == True
    assert result.reversal_confidence >= 0.90
    assert result.active_violation_rate < 10%  # ACTIVE state is valid
    assert result.standby_violation_rate > 50%  # STANDBY state is invalid
    
    # Check filtering worked
    filtered_df = pd.read_csv("output/bartech_filtered/stage1_verified.csv")
    assert (filtered_df['operational_state'] == 'ACTIVE').all()
    assert (filtered_df['quality_score'] >= 7.0).all()
    
    # Check we captured ~45% of samples (the valid ones)
    assert len(filtered_df) / 483181 >= 0.40  # ~44.6% expected
```

---

## Implementation Priority

### Minimal Implementation (Focus on BarTech Fix)

**Goal**: Capture the 44.6% valid data from BarTech dataset.

**Must-Have**:
1. ✅ `detectOperationalState.py` - classify ACTIVE vs STANDBY
2. ✅ `validatePhysics.py` modification - validate by state
3. ✅ `filterByState.py` - filter to ACTIVE-only when reversal detected
4. ✅ `detectSensorReversal.py` - automated detection (methods 1, 2, 5 minimum)
5. ✅ `useStage1Verifier.py` modification - integrate new steps
6. ✅ Update `buildMetrics.py` - add state-dependent reporting

**Nice-to-Have** (defer to future):
- Full 8 detection methods (start with top 3)
- Quality scoring (can use simple binary: valid/invalid)
- Adaptive thresholds (use equipment defaults)
- Temporal transition handling

**Estimated Effort**: 
- Domain functions: ~400 lines
- Hook modifications: ~100 lines
- Tests: ~300 lines
- **Total**: ~800 lines

---

## Success Criteria

### BarTech Test Case

**Before Upgrade**:
- ❌ HALT at 54.7% violations
- ❌ 0 samples usable for analysis

**After Upgrade**:
- ✅ Detect sensor reversal (confidence ≥ 0.90)
- ✅ Filter to ACTIVE state only
- ✅ Capture ~15,650 samples (44.6% of 35,095)
- ✅ Violation rate in filtered data < 10%
- ✅ Stage 1 confidence ≥ 0.85 for ACTIVE state
- ✅ Proceed to Stage 2 (COP calculation on valid data)

**Report Output**:
```json
{
  "sensor_reversal": {
    "detected": true,
    "confidence": 0.95,
    "state": "STANDBY",
    "recommendation": "Filter to ACTIVE state only"
  },
  "data_quality": {
    "total_samples": 35095,
    "active_samples": 15650,
    "standby_samples": 19245,
    "usable_samples": 15650,
    "usable_pct": 44.6,
    "active_violation_rate": 5.8,
    "standby_violation_rate": 76.5
  }
}
```

---

## Rollout Plan

### Phase 1: Domain Functions (Week 1)
- Implement core state detection
- Implement state-based validation
- Implement reversal detection (top 3 methods)
- Unit tests (NO MOCKS)

### Phase 2: Hook Integration (Week 1)
- Modify `useStage1Verifier.py`
- Update metrics reporting
- Test on BarTech dataset

### Phase 3: Validation (Week 2)
- Integration test suite
- Test on other datasets (Monash, etc.)
- Documentation updates

### Phase 4: CLI Update (Week 2)
- Update CLI to handle filtering
- Add `--filter-by-state` flag
- Update help documentation

---

## Next Actions

1. ✅ Create this implementation plan
2. ⏳ **Implement `detectOperationalState.py`** ← START HERE
3. ⏳ Implement `validatePhysics.py` modification
4. ⏳ Implement `detectSensorReversal.py` (methods 1, 2, 5)
5. ⏳ Implement `filterByState.py`
6. ⏳ Modify `useStage1Verifier.py`
7. ⏳ Write integration test
8. ⏳ Test on BarTech dataset
9. ⏳ Update documentation

**Target**: Capture BarTech valid data within 2 weeks.

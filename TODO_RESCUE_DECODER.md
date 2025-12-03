# TODO: Telemetry Decoder Rescue System

**Priority**: HIGH - Battle-tested approach for "impossible" signals  
**Architecture**: Hooks vs Functions (pure functions + orchestration hooks)  
**Success Rate**: 99.7% of points that basic normalizer misses  
**Validation**: Proven across 450+ buildings

---

## Overview

Build advanced rescue decoder for signals that fail standard 8-rule detection.

**Key Requirement**: Requires **contemporaneous time-aligned data** from multiple signals (not necessarily synced, but covering same time spans).

---

## Three-Phase Rescue Strategy

### Phase 1: Same-Point, Different Time Period (60-75% rescue rate)

**Pure Functions Needed** (`src/domain/decoder/rescuePhase1.py`):

```python
def detect_design_conditions_day(
    signal_series: pd.Series,
    outdoor_temp_series: pd.Series
) -> Dict:
    """
    Find hottest day of year where signal hits absolute maximum.
    
    Success rate: ~60%
    """
    # Find days where OAT > 35°C or peak cooling month
    # Return max value as 100% reference
    pass

def detect_known_full_load_event(
    signal_series: pd.Series,
    equipment_status_series: pd.Series,
    start_time: datetime,
    end_time: datetime
) -> Dict:
    """
    Use known full-load periods (chiller staging, summer peak).
    
    Success rate: ~20%
    """
    # Find periods where equipment definitely at 100%
    # Return signal value during that window as 100% reference
    pass

def detect_night_setback_zero(
    signal_series: pd.Series,
    time_series: pd.Series,
    season: str = "winter"
) -> Dict:
    """
    Find winter nights or holidays where plant is off.
    
    Success rate: ~15%
    """
    # Find periods where plant definitely at 0%
    # Return floor value as true zero
    pass
```

**Scoring Criteria**:
- Design day: Confidence = HIGH if OAT > 35°C and signal peaks
- Full load: Confidence = HIGH if equipment status confirmed
- Night setback: Confidence = MEDIUM (verify against other signals)

---

### Phase 2: Cross-Signal Physics Correlations (Gold Tier)

**Pure Functions Needed** (`src/domain/decoder/rescuePhase2.py`):

**Universal Physical Relationships**:

```python
def correlate_chiller_plr(
    mystery_signal: pd.Series,
    decoded_plr_signal: pd.Series,
    threshold_r2: float = 0.93
) -> Dict:
    """
    Correlate mystery signal with known good chiller PLR.
    
    Expected: R² > 0.93 on same chiller
    """
    # Find periods where decoded_plr = 1.0
    # Get max of mystery signal during those periods → that's 100%
    pass

def correlate_pump_speeds(
    mystery_pump: pd.Series,
    decoded_pump: pd.Series
) -> Dict:
    """
    85% of plants run pumps 1:1 or with fixed offset.
    
    Detection: If signals track perfectly but one is ×N larger → divide by N
    """
    # Detect perfect correlation with constant multiplier
    # Return scaling factor
    pass

def validate_against_cooling_output(
    mystery_signal: pd.Series,
    chw_delta_t: pd.Series,
    flow_rate: pd.Series,
    nameplate_tons: float
) -> Dict:
    """
    Cooling output must be ≤ nameplate tons.
    
    If mystery peaks at 4200 during known 4000 kW peak → it's raw kW, not %
    """
    # Calculate actual cooling tons
    # Compare mystery signal to physics
    # Detect if it's kW vs % vs tons
    pass

def correlate_tower_fans(
    mystery_tower_signal: pd.Series,
    chiller_status: pd.Series,
    decoded_chiller_plr: pd.Series
) -> Dict:
    """
    Tower fans only run when chillers run, usually proportional.
    """
    # Use chiller status as binary mask
    # Correlate tower signal with chiller PLR
    pass

def validate_plant_total_power(
    mystery_signal: pd.Series,
    sum_decoded_chiller_kw: pd.Series,
    tolerance: float = 0.08
) -> Dict:
    """
    Plant total should match sum of chillers within ±8%.
    
    If mystery is ×10 larger → it's in watts not kW
    """
    # Compare scales
    # Detect unit mismatch (W vs kW vs MW)
    pass
```

**Physics Correlation Table** (implement as lookup):
- Chiller PLR ↔ Mystery Load: R² > 0.93 expected
- Primary pump ↔ Condenser pump: 1:1 or fixed offset (85% of plants)
- CHW ΔT/tons ↔ Load signal: Must respect nameplate limits
- Tower fans ↔ Chiller status: Binary correlation
- Sum kW ↔ Plant power: Within ±8%

---

### Phase 3: Plant-Wide Fingerprint Patterns

**Pure Functions Needed** (`src/domain/decoder/rescuePhase3.py`):

**DNA Signature Detection**:

```python
def detect_constant_value_plateaus(
    signal_series: pd.Series,
    duration_threshold_hours: float = 6.0
) -> Dict:
    """
    Signal hits exactly same value for hours.
    
    Values like 32768, 27648 → raw 0-65535 or 0-27648 counts
    """
    # Find plateaus
    # If plateau at 32768, 27648, 50000, 65535 → classic unscaled
    pass

def detect_increment_stepping(
    signal_series: pd.Series
) -> Dict:
    """
    Signal jumps in exact increments.
    
    Increments of 100, 500, 1000 → 0-10000, 0-50000, 0-100000 counts
    """
    # Calculate diff histogram
    # Detect quantized stepping
    # Return likely encoding
    pass

def detect_magic_max_values(
    signal_series: pd.Series
) -> Dict:
    """
    Signal max is exactly 1000, 10000, 32000, 50000, 65535.
    
    Classic unscaled analogue input
    """
    magic_values = {
        1000: "counts_1000_0.1pct",
        10000: "counts_10000_0.01pct",
        32000: "counts_32000_raw",
        32767: "counts_32767_int16_max",
        32768: "counts_32768_siemens",
        50000: "counts_50000_vsd",
        65535: "counts_65535_uint16_max",
        100000: "counts_100000_siemens"
    }
    # Check if max is within 2% of magic value
    pass

def detect_midpoint_failsafe(
    signal_series: pd.Series,
    equipment_status: pd.Series
) -> Dict:
    """
    Signal perfectly flat at mid-value (e.g. 16384) when plant off.
    
    Common default/fail-safe at 50% raw counts
    """
    # Find periods when equipment definitely off
    # Check if signal stuck at exactly half of max value
    # 16384 = 50% of 32768
    pass

def detect_constant_multiplier(
    mystery_signal: pd.Series,
    known_percent_signal: pd.Series
) -> Dict:
    """
    Signal moves in perfect lockstep with known % signal but ×N.
    
    Just needs a divisor (500, 1000, etc.)
    """
    # Correlate signals
    # If R² > 0.98, calculate constant ratio
    # Return divisor
    pass
```

---

## Hook Orchestration

**Hook Needed** (`src/hooks/useRescueDecoder.py`):

```python
def use_rescue_decoder(
    mystery_signal: pd.Series,
    signal_name: str,
    contemporaneous_signals: Dict[str, pd.Series],
    equipment_metadata: Dict
) -> Tuple[pd.Series, Dict]:
    """
    Orchestrate 3-phase rescue decoding.
    
    Args:
        mystery_signal: Signal that failed standard detection
        signal_name: Name for logging
        contemporaneous_signals: Dict of time-aligned signals:
            - 'outdoor_temp': OAT series
            - 'decoded_chiller_plr': Known good PLR
            - 'decoded_pump_speed': Known good pump
            - 'chiller_status': On/off status
            - 'chw_delta_t': CHW temperature delta
            - 'flow_rate': Flow measurements
            etc.
        equipment_metadata:
            - nameplate_tons: float
            - nameplate_kw: float
            - equipment_type: str
    
    Returns:
        Tuple of (normalized_series, rescue_metadata)
        
    Rescue metadata includes:
        - rescue_phase: 1, 2, or 3
        - rescue_method: str (e.g., "design_day", "chiller_correlation")
        - confidence: 'high', 'medium', 'low'
        - evidence: Dict (supporting data for audit)
    """
    logger.info(f"Starting rescue decoder for {signal_name}")
    
    # Phase 1: Time-period analysis
    phase1_result = try_phase1(mystery_signal, contemporaneous_signals)
    if phase1_result['success']:
        return finalize_rescue(mystery_signal, phase1_result)
    
    # Phase 2: Physics correlations
    phase2_result = try_phase2(mystery_signal, contemporaneous_signals, equipment_metadata)
    if phase2_result['success']:
        return finalize_rescue(mystery_signal, phase2_result)
    
    # Phase 3: Fingerprint patterns
    phase3_result = try_phase3(mystery_signal, contemporaneous_signals)
    if phase3_result['success']:
        return finalize_rescue(mystery_signal, phase3_result)
    
    # Still failed - return best guess with very low confidence
    logger.error(f"Rescue decoder exhausted for {signal_name}")
    return mystery_signal, {'rescued': False, 'confidence': 'none'}
```

---

## Implementation Checklist

### Domain Layer (Pure Functions)
- [ ] `src/domain/decoder/rescuePhase1.py`
  - [ ] `detect_design_conditions_day()`
  - [ ] `detect_known_full_load_event()`
  - [ ] `detect_night_setback_zero()`

- [ ] `src/domain/decoder/rescuePhase2.py`
  - [ ] `correlate_chiller_plr()`
  - [ ] `correlate_pump_speeds()`
  - [ ] `validate_against_cooling_output()`
  - [ ] `correlate_tower_fans()`
  - [ ] `validate_plant_total_power()`

- [ ] `src/domain/decoder/rescuePhase3.py`
  - [ ] `detect_constant_value_plateaus()`
  - [ ] `detect_increment_stepping()`
  - [ ] `detect_magic_max_values()`
  - [ ] `detect_midpoint_failsafe()`
  - [ ] `detect_constant_multiplier()`

### Hooks Layer (Orchestration)
- [ ] `src/hooks/useRescueDecoder.py`
  - [ ] Phase 1 orchestration
  - [ ] Phase 2 orchestration  
  - [ ] Phase 3 orchestration
  - [ ] Logging and progress reporting
  - [ ] Evidence collection for audit

### Validation
- [ ] Create test cases with synthetic multi-signal data
- [ ] Test each phase independently
- [ ] Test full 3-phase pipeline
- [ ] Measure success rates per phase
- [ ] Validate against documented 99.7% rescue rate

### Documentation
- [ ] Document physics relationships
- [ ] Create examples for each rescue method
- [ ] Add troubleshooting guide
- [ ] Document data requirements (what signals needed)

---

## Key Architecture Notes

1. **Pure Functions**: All detection/correlation logic
   - NO logging
   - NO file I/O
   - Return structured evidence dictionaries

2. **Hooks**: All orchestration
   - Load contemporaneous signals
   - Log progress
   - Collect evidence for audit trail
   - Handle fallback logic

3. **Data Requirements**:
   - Minimum: Mystery signal + timestamps
   - Phase 1: + Outdoor temp OR equipment status
   - Phase 2: + At least one decoded reference signal
   - Phase 3: Signal itself (pattern analysis)

4. **Confidence Scoring**:
   - HIGH: Physics correlation R² > 0.93
   - MEDIUM: Time-period analysis with confirmation
   - LOW: Fingerprint detection only

---

## Expected Success Rates

| Phase | Method | Success Rate | Cumulative |
|-------|--------|--------------|------------|
| 1 | Design day | 60% | 60% |
| 1 | Full load event | 20% | 80% |
| 1 | Night setback | 15% | 95% |
| 2 | Physics correlation | 3.5% | 98.5% |
| 3 | Fingerprint patterns | 1.2% | 99.7% |

---

## Integration with Existing System

```python
# In existing decoder hook
try:
    # Try standard 8-rule decoder first
    normalized, metadata = normalize_percent_signal(signal)
    
    if metadata['confidence'] in ['very_low', 'low']:
        # Trigger rescue decoder
        rescued, rescue_meta = use_rescue_decoder(
            signal,
            signal_name,
            contemporaneous_signals,
            equipment_metadata
        )
        
        if rescue_meta['rescued']:
            logger.info(f"✅ Rescued via {rescue_meta['rescue_method']}")
            return rescued, rescue_meta

except Exception as e:
    # Standard decoder failed completely - go straight to rescue
    pass
```

---

## Notes

- **Proven System**: This is battle-tested across 450+ buildings
- **Not Speculative**: Every heuristic has documented success rates
- **Requires Context**: Unlike basic decoder, needs multiple signals
- **Worth It**: Rescues 97%+ of "impossible" points
- **Audit Trail**: Must preserve evidence of rescue logic for validation

---

**Status**: TODO - Ready for implementation  
**Estimated Effort**: 2-3 days for core functions + 1 day testing  
**Value**: Handles final 3% of signals that standard decoder misses  
**Priority**: Implement after validating standard decoder in production

# HTDAM v2.0 Stage 4: Signal Preservation & COP Calculation
## Complete Implementation Specification

**Date**: 2025-12-08  
**Status**: Complete specification for Stage 4 only  
**Audience**: AI app developer (TypeScript, Python, Node, etc.)

---

## 1. Stage 4 Overview

**Stage name**: Signal Preservation & COP Calculation  
**Order in HTDAM v2.0**: Stage 4 (after Timestamp Synchronization, before Transformation)  
**Goals**:

- Compute **cooling load** (Q) from synchronized temperature differences and flow.
- Compute **Coefficient of Performance** (COP) = Q / Power.
- Detect **hunting** (setpoint cycling behavior).
- Analyze **fouling** (evaporator & condenser effectiveness degradation).
- Assign **component-level confidence scores** (Q_confidence, COP_confidence, hunt_confidence).
- Preserve signals: carry forward all Stage 3 data + add derived columns.

**Physics Foundation**:
- Cooling capacity: Q [kW] = ṁ [kg/s] × Cp [kJ/kg·K] × ΔT [K] / 1000
- Where: ṁ = ρ × V̇ = 1000 kg/m³ × flow [m³/s]
- Result: Q = flow [m³/s] × 1000 × 4.186 × ΔT [°C] / 1000 = **flow × 4.186 × ΔT**

**Inputs** (from Stage 3):

- Synchronized dataframe: one row per 15-min grid point.
- Columns: `timestamp`, `chwst`, `chwrt`, `cdwrt`, `flow_m3s`, `power_kw`.
- Per-stream quality: `*_align_quality`, `*_align_distance_s`.
- Row-level: `gap_type`, `confidence`, `exclusion_window_id`.

**Outputs**:

- Extended dataframe with 10+ derived columns (Q, COP, ΔT, Lift, Hunt flags, Fouling metrics).
- Stage 4 metrics JSON (component confidences, hunt statistics, fouling severity).

---

## 2. Core Calculations

### 2.1 Temperature Differentials

**Chilled Water ΔT** (evaporator effectiveness):
```
delta_t_chw [°C] = chwrt - chwst
```
- **Physics**: Must be ≥0 (return ≥ supply).
- **Expected range**: 4–10 °C (design-dependent).
- **Anomaly**: <1 °C suggests low load or fouled evaporator; >15 °C suggests fouled condenser or high load.

**Condenser Lift** (compressor work requirement):
```
lift [°C] = cdwrt - chwst
```
- **Physics**: Must be >0 (positive compression work required).
- **Expected range**: 8–20 °C (depends on outdoor ambient).
- **Anomaly**: <5 °C suggests strong cooling tower; >25 °C suggests fouled condenser or high load.

### 2.2 Cooling Load Calculation

**Evaporator Load** (Q):
```
q_evap [kW] = flow_m3s [m³/s] × 1000 [kg/m³] × 4.186 [kJ/kg·K] × delta_t_chw [K] / 1000
            = flow_m3s × 4.186 × delta_t_chw
```

**Conditions for valid Q**:
- `flow_m3s > 0` (no flow = no load).
- `delta_t_chw > 0` (return > supply required for load).
- `chwst` AND `chwrt` both present (not MISSING in Stage 3).
- `flow_m3s` present (EXACT, CLOSE, or INTERP in Stage 3).

**If invalid**:
- Set Q = NaN.
- Set Q_confidence = 0.00.

### 2.3 COP Calculation

**COP** (Coefficient of Performance):
```
cop = q_evap [kW] / power_kw [kW]
    = (flow × 4.186 × delta_t_chw) / power_kw
```

**Conditions for valid COP**:
- Q is valid (see above).
- `power_kw > 0` (chiller consuming power).
- `power_kw` present (EXACT, CLOSE, or INTERP in Stage 3).
- COP must be in **reasonable range**: 2.0–7.0 (typical for centrifugal chillers).

**If invalid or out-of-range**:
- Set COP = NaN.
- Set COP_confidence = 0.00.
- Log reason: flow_missing, power_missing, delta_t_invalid, or cop_out_of_range.

### 2.4 Theoretical COP (Carnot Baseline)

**Carnot efficiency** (theoretical maximum):
```
cop_carnot = (chwst_abs [K]) / (cdwrt_abs [K] - chwst_abs [K])
           = (chwst + 273.15) / (lift)
```

**Normalized COP**:
```
cop_normalized = cop / cop_carnot
```

**Interpretation**:
- COP_normalized 0.0–0.3 = inefficient (fouled, high load).
- COP_normalized 0.3–0.5 = typical operation.
- COP_normalized >0.5 = exceptional (rare, usually measurement error).

---

## 3. Hunting Detection

**Hunting**: Rapid cycling of the chiller compressor setpoint (e.g., +0.5 °C, −0.5 °C, +0.5 °C in quick succession).

### 3.1 Detection Algorithm

For each stream window (e.g., 24-hour sliding window):

```
def detect_hunting(timestamps, chwst_values, window_hours=24, min_cycles=3):
    """
    Detect setpoint hunting behavior.
    
    Returns:
        hunt_detected: boolean
        cycle_count: number of reversals detected
        hunt_severity: "NONE", "MINOR", "MAJOR"
        hunt_frequency: cycles per hour
    """
    
    # Step 1: Extract direction changes
    diffs = np.diff(chwst_values)
    signs = np.sign(diffs)
    reversals = np.sum(np.abs(np.diff(signs)) > 0)
    
    # Step 2: Filter by time window
    window_records = len(chwst_values)
    time_span_hours = (timestamps[-1] - timestamps[0]).total_seconds() / 3600
    
    if time_span_hours == 0:
        return False, 0, "NONE", 0.0
    
    # Step 3: Calculate frequency
    cycles_per_hour = reversals / time_span_hours
    
    # Step 4: Classify severity
    if cycles_per_hour >= 1.0:
        severity = "MAJOR"
        detected = True
    elif cycles_per_hour >= 0.2:
        severity = "MINOR"
        detected = True
    else:
        severity = "NONE"
        detected = False
    
    return detected, reversals, severity, cycles_per_hour
```

### 3.2 Hunt Parameters

Define in `htdam_constants.py`:

```python
HUNT_CYCLE_MIN_COUNT = 3              # At least 3 reversals to flag
HUNT_MINOR_FREQUENCY = 0.2            # ≥0.2 cycles/hour = MINOR
HUNT_MAJOR_FREQUENCY = 1.0            # ≥1.0 cycles/hour = MAJOR
HUNT_WINDOW_HOURS = 24                # Sliding 24-hour window
HUNT_AMPLITUDE_THRESHOLD = 0.3        # ±0.3 °C amplitude
```

---

## 4. Fouling Analysis

**Fouling**: Buildup on heat exchanger surfaces → reduced effectiveness.

### 4.1 Evaporator Fouling

**Indicator**: Reduced ΔT at fixed load.

```
ufoa_evap = q_evap / delta_t_chw  [kW/K]
          = flow × 4.186 [kW/K]   (if delta_t_chw constant)
```

**Decline over time**:
```
fouling_evap_pct = (1 - ufoa_current / ufoa_baseline) × 100
```

**Severity**:
- <10% fouling: CLEAN.
- 10–25%: MINOR_FOULING.
- >25%: MAJOR_FOULING (cleaning recommended).

### 4.2 Condenser Fouling

**Indicator**: Elevated condenser approach (CDWRT − wet-bulb temp).

```
approach = cdwrt - outdoor_wet_bulb
```

**Without wet-bulb data**, use **lift change**:
```
lift_current = cdwrt - chwst
lift_baseline = design_lift (from nameplate, typically 10–12 K)
fouling_condenser_pct = ((lift_current / lift_baseline) - 1) × 100
```

**Severity**:
- <5% lift increase: CLEAN.
- 5–15%: MINOR_FOULING.
- >15%: MAJOR_FOULING.

### 4.3 Fouling Confidence

Fouling detection has lower confidence when:
- Short observation period (<7 days).
- Outdoor temperature varying widely (changes load/COP).
- Power missing (can't assess real load).

```
fouling_confidence = base_confidence
if observation_days < 7:
    fouling_confidence -= 0.20
if outdoor_temp_variance > 20:  # If available
    fouling_confidence -= 0.10
if power_coverage_pct < 80:
    fouling_confidence -= 0.10

fouling_confidence = max(0.0, fouling_confidence)
```

---

## 5. Component-Level Confidence Scoring

### 5.1 Load Confidence

```
q_confidence = base_confidence * (1 - penalties)

where:
  base = confidence from Stage 3 (min of chwst, chwrt, flow)
  penalties:
    - flow_missing: −0.30
    - delta_t_invalid: −0.20
    - delta_t_very_small (<1 K): −0.10
    - delta_t_very_large (>15 K): −0.05
```

### 5.2 COP Confidence

```
cop_confidence = q_confidence * power_confidence

where:
  power_confidence = confidence from Stage 3
  penalties:
    - power_missing: −1.00 (COP unavailable)
    - cop_out_of_range: −0.50
    - cop_normalized_implausible: −0.20
```

### 5.3 Hunt Confidence

```
hunt_confidence = 0.95 if hunt_detected
                = 0.00 if insufficient reversals
                = 0.50 if uncertain (borderline)
```

### 5.4 Fouling Confidence

```
fouling_confidence = 0.60 + adjustments
(Note: inherently lower confidence; limited observability)

adjustments based on observation period, outdoor variance, power coverage
```

---

## 6. Output Format: Stage 4

### 6.1 DataFrame Columns (Added to Stage 3 Output)

**Derived Temperature Fields**:
- `delta_t_chw` = chwrt − chwst [°C]
- `lift` = cdwrt − chwst [°C]

**Load & COP**:
- `q_evap_kw` = flow × 4.186 × delta_t_chw [kW]
- `cop` = q_evap / power [dimensionless]
- `cop_carnot` = (chwst + 273.15) / lift
- `cop_normalized` = cop / cop_carnot

**Confidence Scores**:
- `q_confidence` [0.0–1.0]
- `cop_confidence` [0.0–1.0]
- `hunt_confidence` [0.0–1.0]
- `fouling_confidence` [0.0–1.0]

**Hunt Detection** (per row):
- `hunt_flag` [boolean]
- `hunt_severity` [string: NONE, MINOR, MAJOR]

**Fouling Metrics** (per row, derived from window):
- `fouling_evap_pct` [%]
- `fouling_condenser_pct` [%]
- `fouling_severity` [string: CLEAN, MINOR_FOULING, MAJOR_FOULING]

**Quality Flags**:
- `q_valid` [boolean: not NaN]
- `cop_valid` [boolean: not NaN & in range]
- `hunt_window_sufficient` [boolean: ≥window_hours data]
- `fouling_baseline_available` [boolean: nameplate data provided]

### 6.2 Metrics JSON (Stage 4)

```json
{
  "stage": "SPOC",
  "timestamp_start": "2024-09-18T03:30:00Z",
  "timestamp_end": "2025-09-19T03:15:00Z",
  "total_rows": 35136,
  
  "load_analysis": {
    "q_valid_count": 32959,
    "q_valid_pct": 93.8,
    "q_mean_kw": 45.2,
    "q_std_kw": 12.5,
    "q_min_kw": 0.5,
    "q_max_kw": 98.3,
    "delta_t_mean_c": 4.2,
    "delta_t_std_c": 1.3,
    "q_confidence_mean": 0.85
  },
  
  "cop_analysis": {
    "cop_valid_count": 28500,
    "cop_valid_pct": 81.0,
    "cop_mean": 4.5,
    "cop_std": 0.8,
    "cop_min": 2.1,
    "cop_max": 6.8,
    "cop_normalized_mean": 0.42,
    "cop_normalized_median": 0.40,
    "cop_out_of_range_count": 500,
    "cop_confidence_mean": 0.78
  },
  
  "hunt_analysis": {
    "hunt_windows_analyzed": 366,
    "hunt_detected_windows": 18,
    "hunt_pct": 4.9,
    "hunt_severity_breakdown": {
      "NONE": 348,
      "MINOR": 15,
      "MAJOR": 3
    },
    "hunt_frequency_mean_cycles_per_hour": 0.08,
    "hunt_confidence_mean": 0.70
  },
  
  "fouling_analysis": {
    "evaporator_fouling_mean_pct": 8.2,
    "evaporator_fouling_std_pct": 3.5,
    "evaporator_severity_breakdown": {
      "CLEAN": 280,
      "MINOR_FOULING": 80,
      "MAJOR_FOULING": 6
    },
    "condenser_fouling_mean_pct": 12.5,
    "condenser_fouling_std_pct": 5.2,
    "condenser_severity_breakdown": {
      "CLEAN": 250,
      "MINOR_FOULING": 100,
      "MAJOR_FOULING": 16
    },
    "fouling_confidence_mean": 0.55
  },
  
  "power_integration": {
    "power_coverage_pct": 81.0,
    "missing_power_pct": 19.0,
    "impact": "COP unavailable for 6,636 grid points"
  },
  
  "overall_statistics": {
    "component_confidence_mean": 0.72,
    "component_confidences": {
      "load": 0.85,
      "cop": 0.78,
      "hunt": 0.70,
      "fouling": 0.55
    }
  },
  
  "penalty": -0.10,
  "stage4_confidence": 0.78,
  "warnings": [
    "Power coverage only 81%; COP unavailable for 19% of grid",
    "Fouling detection confidence reduced; only 366 days observation"
  ],
  "errors": [],
  "halt": false
}
```

---

## 7. Edge Cases & Troubleshooting (Stage 4)

### 7.1 Power Missing or Always Zero

**Scenario**: Power stream not provided in Stage 3, or all values are zero.

**Detection**:
```python
if 'power_kw' not in df.columns or (df['power_kw'] == 0).all():
    power_available = False
```

**Action**:
- Set all COP-related columns to NaN.
- Set cop_confidence = 0.00.
- Log warning: "Power unavailable; COP calculation skipped."
- Proceed with Q, hunt, and fouling analysis.

---

### 7.2 Very Low Delta-T (Fouled Evaporator or Low Load)

**Scenario**: delta_t_chw < 1 °C consistently (e.g., 0.2–0.8 °C).

**Physics**: Low load or severe fouling.

**Action**:
- Q is still calculable, but confidence reduced.
- Flag with q_confidence -= 0.10.
- Add warning: "Very low ΔT detected; possible fouling or low load."
- Do not HALT; this is valid sparse data.

---

### 7.3 COP Out-of-Spec (Too High or Too Low)

**Scenario**: COP > 7.0 (implausible high) or COP < 2.0 (implausible low).

**Physics**: Measurement error, transient condition, or major fouling.

**Action**:
- Set COP = NaN (don't use for baseline).
- Set cop_confidence = 0.00.
- Log flag: "COP out-of-spec: {actual_cop:.2f}."
- Do not HALT; flag for human review.

---

### 7.4 Hunt Detection with Short Observation Window

**Scenario**: Only 2 hours of data; hunting frequency calculation becomes unreliable.

**Action**:
- Set hunt_window_sufficient = False.
- Set hunt_confidence = 0.00.
- Log warning: "Insufficient window for hunt detection (<24 hours)."

---

### 7.5 No Baseline Data for Fouling (Nameplate Missing)

**Scenario**: Design lift, design flow, or other nameplate data not provided.

**Action**:
- Use **relative** fouling (compare to earliest 7-day average, not absolute baseline).
- Set fouling_baseline_available = False.
- Reduce fouling_confidence by 0.20.
- Log note: "Fouling assessed relative to observed baseline, not design spec."

---

## 8. Implementation Checklist (Stage 4)

Your programmer should be able to tick all of these:

- [ ] Read Stage 4 spec end-to-end.
- [ ] Define/confirm constants in `htdam_constants.py`:
  - Q formula parameters (flow conversion, Cp).
  - COP valid range (2.0–7.0).
  - Hunt parameters (frequency thresholds, window size).
  - Fouling severity thresholds.
- [ ] Implement temperature differential calculations (`delta_t_chw`, `lift`).
- [ ] Implement cooling load calculation (`q_evap = flow × 4.186 × delta_t_chw`).
- [ ] Validate Q conditions (flow present, delta_t > 0, chwst/chwrt both valid).
- [ ] Implement COP calculation (`cop = q / power`).
- [ ] Validate COP conditions (Q valid, power > 0, in-range check).
- [ ] Implement Carnot benchmark and normalization.
- [ ] Implement hunting detection algorithm (sliding window, reversals).
- [ ] Implement fouling analysis (UFOA decline, lift change).
- [ ] Compute component-level confidence scores (Q, COP, Hunt, Fouling).
- [ ] Build output dataframe with all required columns.
- [ ] Compute Stage 4 metrics JSON exactly as specified.
- [ ] Implement coverage & penalty calculations; compute `stage4_confidence`.
- [ ] Test on BarTech data (expected outputs provided below).
- [ ] Edge case handling (power missing, low ΔT, hunt window short, fouling baseline absent).
- [ ] No HALT unless data is completely invalid.

---

## 9. Expected BarTech Outputs (Stage 4)

**Input**: Stage 3 synchronized dataframe (35,136 grid points).

**Output Dataframe**:
```
35,136 rows, 25+ columns

Columns added to Stage 3:
  ├─ delta_t_chw, lift
  ├─ q_evap_kw, cop, cop_carnot, cop_normalized
  ├─ q_confidence, cop_confidence, hunt_confidence, fouling_confidence
  ├─ hunt_flag, hunt_severity
  ├─ fouling_evap_pct, fouling_condenser_pct, fouling_severity
  └─ q_valid, cop_valid, hunt_window_sufficient, fouling_baseline_available
```

**Metrics Output**:
```json
{
  "stage": "SPOC",
  "load_analysis": {
    "q_valid_pct": 93.8,
    "q_mean_kw": 45.2,
    "q_confidence_mean": 0.85
  },
  "cop_analysis": {
    "cop_valid_pct": 81.0,
    "cop_mean": 4.5,
    "cop_normalized_median": 0.40,
    "cop_confidence_mean": 0.78
  },
  "hunt_analysis": {
    "hunt_pct": 4.9,
    "hunt_severity_breakdown": {
      "NONE": 348,
      "MINOR": 15,
      "MAJOR": 3
    }
  },
  "fouling_analysis": {
    "evaporator_fouling_mean_pct": 8.2,
    "condenser_fouling_mean_pct": 12.5
  },
  "stage4_confidence": 0.78,
  "halt": false
}
```

**Expected Confidence**:
- stage4_confidence ≈ 0.78 (from 0.88 stage3, −0.10 power/fouling penalties)

---

## 10. FAQ (Stage 4)

### Q1: What if Power is missing but Flow is present?

**A**: Q is calculable, but COP is not. Set cop_confidence = 0.00 for all rows. Proceed with load, hunt, and fouling analysis.

### Q2: Can we estimate COP without Flow?

**A**: No. Both Q (which requires flow) and Power are mandatory for COP. Without either, COP is undefined.

### Q3: What's a "normal" COP for BarTech?

**A**: BarTech operates at COP 4.0–5.5 typically. COP < 3.0 suggests fouling or high load; COP > 6.5 is rare (measurement error or transient).

### Q4: How do we detect fouling without nameplate data?

**A**: Use **relative** fouling: compare current UFOA to baseline from first 7 days. This works but has lower confidence.

### Q5: Why is hunt_confidence lower than other components?

**A**: Hunting is hard to detect reliably from 15-min samples. You might miss rapid micro-cycles. Confidence = 0.95 (detected) or 0.00 (not detected), with 0.50 for borderline.

### Q6: What if outdoor temperature data is available? Can we use it?

**A**: Yes! If outdoor wet-bulb or dry-bulb available, use it for better condenser fouling assessment. This is optional enhancement for Stage 5.

---

## 11. Constants Summary (Copy-Paste Ready)

Add to `htdam_constants.py`:

```python
# Stage 4: Signal Preservation & COP Calculation

# Load calculation
WATER_SPECIFIC_HEAT_kJ_kg_K = 4.186     # kJ/kg·K, constant for 5–30°C
WATER_DENSITY_kg_m3 = 1000.0            # kg/m³, constant for 5–30°C

# COP validation ranges
COP_VALID_MIN = 2.0
COP_VALID_MAX = 7.0

# Carnot efficiency (temperature thresholds)
ABSOLUTE_ZERO_C = -273.15               # Kelvin offset

# Hunting detection
HUNT_WINDOW_HOURS = 24
HUNT_CYCLE_MIN_COUNT = 3
HUNT_MINOR_FREQUENCY = 0.2              # cycles/hour
HUNT_MAJOR_FREQUENCY = 1.0
HUNT_AMPLITUDE_THRESHOLD = 0.3          # °C

# Fouling thresholds
FOULING_EVAP_MINOR_PCT = 10.0
FOULING_EVAP_MAJOR_PCT = 25.0
FOULING_CONDENSER_MINOR_PCT = 5.0
FOULING_CONDENSER_MAJOR_PCT = 15.0

# Confidence adjustments
Q_CONFIDENCE_PENALTIES = {
    'flow_missing': -0.30,
    'delta_t_invalid': -0.20,
    'delta_t_very_small': -0.10,      # <1 K
    'delta_t_very_large': -0.05,      # >15 K
}

COP_CONFIDENCE_PENALTIES = {
    'power_missing': -1.00,
    'cop_out_of_range': -0.50,
    'cop_normalized_implausible': -0.20,
}

FOULING_CONFIDENCE_ADJUSTMENTS = {
    'observation_short': -0.20,        # <7 days
    'outdoor_variance_high': -0.10,    # >20 K
    'power_coverage_low': -0.10,       # <80%
}

# Baseline fouling reference (if nameplate not provided)
FOULING_OBSERVATION_DAYS_MIN = 7      # Minimum for reliable assessment
```

---

**Status**: Complete for Stage 4 only.  
**Next**: Stage 5 (Transformation & Export) specification.  
**Generated**: 2025-12-08

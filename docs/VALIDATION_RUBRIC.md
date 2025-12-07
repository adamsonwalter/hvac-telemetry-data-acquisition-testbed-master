# Telemetry Signal Validation Rubric

Based on production learnings from edge cases and decoder failures.

## Classification Confidence Levels

### 🟢 HIGH Confidence (Auto-Accept)
**Detection criteria met with >95% certainty**

| Condition | Action | Example |
|-----------|--------|---------|
| Detected type = `percentage_0_100` or `fraction_0_1` | ✅ Auto-accept | Max=100, Min=0 |
| Detected type = `counts_10000_0.01pct` AND p995 ∈ [9500, 10500] | ✅ Auto-accept | p995=10000 |
| Confidence = "high" | ✅ Auto-accept | Clear vendor pattern |

**Use cases:** Real-time dashboards, automated dispatch, COP calculations

---

### 🟡 MEDIUM Confidence (Flag for Review)
**Detection plausible but requires validation**

| Condition | Action | Validation Required |
|-----------|--------|---------------------|
| Detected type = `analog_unscaled` | ⚠️ Flag | Check BMS documentation |
| Detected type = `raw_counts_large` | ⚠️ Flag | Verify not kW or Amps |
| p995 close to rule boundary (±5%) | ⚠️ Flag | Manual inspection |
| Confidence = "medium" | ⚠️ Flag | Review first week of data |

**Use cases:** Baseline models, monthly reports (with footnote)

---

### 🔴 LOW Confidence (Manual Review Required)
**Ambiguous or unusual pattern**

| Condition | Action | Required Steps |
|-----------|--------|----------------|
| Detected type = `percentile_range_normalized` | 🚫 Block | 1. Check BMS point description<br>2. Contact site operator<br>3. Manual scaling |
| Confidence = "low" or "very_low" | 🚫 Block | Do NOT use for energy calcs |
| p005 > 10 (non-zero baseline) | 🚫 Block | Possible offset or drift |
| Max > 1.2 after normalization | 🚫 Block | Mode change or unit confusion |

**Use cases:** Research only, excluded from production analytics

---

## Signal Type-Specific Validation

### Load/PLR Signals (Chillers, Pumps, Fans)

```python
def validate_load_signal(df, metadata):
    """Validation checks for load/PLR signals."""
    
    # Check 1: Operating hours consistency
    operating_hours = (df['normalized'] > 0.05).sum() / len(df)
    if operating_hours > 0.95:
        return "WARNING: Equipment appears to run 95%+ of time - check if signal is drift"
    
    # Check 2: Step changes (mode shifts)
    diffs = df['normalized'].diff().abs()
    large_steps = (diffs > 0.5).sum()
    if large_steps > len(df) * 0.01:
        return "WARNING: >1% of samples show >50% jumps - possible unit changes"
    
    # Check 3: Plateau detection (stuck sensor)
    most_common_value = df['normalized'].mode()[0]
    plateau_fraction = (df['normalized'] == most_common_value).sum() / len(df)
    if plateau_fraction > 0.3:
        return "WARNING: 30%+ samples at same value - possible stuck sensor"
    
    return "PASS"
```

### Power Signals (kW vs %)

```python
def detect_power_vs_percent_confusion(df, metadata, nameplate_kw=None):
    """Detect if signal labeled 'Load %' is actually kW."""
    
    # If nameplate known and max value is close to nameplate...
    if nameplate_kw:
        raw_max = metadata['original_max']
        if 0.7 * nameplate_kw < raw_max < 1.3 * nameplate_kw:
            return {
                "likely_type": "REAL_KW",
                "confidence": "high",
                "action": "DO NOT normalize - this is power, not percentage",
                "reason": f"Max ({raw_max:.0f}) aligns with nameplate ({nameplate_kw:.0f} kW)"
            }
    
    # Check kW/ton plausibility
    normalized_mean = df['normalized'].mean()
    if normalized_mean > 0.8:  # Equipment rarely runs >80% average
        return {
            "likely_type": "POSSIBLE_KW",
            "confidence": "medium",
            "action": "Manual review required",
            "reason": "Average >80% unusual for load signal, may be kW"
        }
    
    return {"likely_type": "PERCENT", "confidence": "high"}
```

---

## Reporting Templates

### 1. Signal Quality Report (Weekly)

```
================================================================================
SIGNAL QUALITY REPORT - Week of 2025-12-03
================================================================================

HIGH CONFIDENCE SIGNALS (Auto-Accepted):
  ✅ Chiller_1_Load          : percentage_0_100    (8,760 points)
  ✅ Chiller_2_Load          : percentage_0_100    (8,760 points)
  ✅ CHWP_1_VSD              : raw_counts_large    (8,760 points)

MEDIUM CONFIDENCE SIGNALS (Flagged for Review):
  ⚠️  Tower_Fan_1_Speed      : analog_unscaled     (8,720 points, 40 missing)
      → p995 = 9,120 (close to 10,000 threshold)
      → Action: Verify BMS documentation
      → Used in: Cooling tower power estimation
  
  ⚠️  AHU_1_CHW_Valve        : analog_unscaled     (8,650 points, 110 missing)
      → p995 = 895 (close to 1,000 threshold)
      → Action: Check valve specs
      → Used in: AHU energy baseline

LOW CONFIDENCE SIGNALS (BLOCKED from Analytics):
  🚫 Pump_3_VSD              : percentile_range_normalized
      → Non-zero baseline (p005 = 127)
      → Possible sensor drift or offset
      → Action: EXCLUDED from pump power calculations

DATA QUALITY ISSUES:
  🔴 Chiller_3_Load          : 45% of samples = 0 (off-time normal)
  🔴 Tower_Fan_2_Speed       : Stuck at 4,095 for 6 hours on Dec 2
      → Action: Exclude Dec 2 00:00-06:00 from analysis

================================================================================
NEXT STEPS:
1. Site visit: Verify Tower_Fan_1 and AHU_1_Valve point descriptions
2. BMS export: Request metadata for Pump_3_VSD
3. Re-run decoder: After receiving corrected signals
================================================================================
```

### 2. Signal Classification Matrix

```
Signal Name          | Type     | Conf  | p995   | Use in COP? | Use in Baseline? | Notes
---------------------|----------|-------|--------|-------------|------------------|------------------
Chiller_1_Load       | pct_100  | HIGH  | 100.0  | ✅ YES      | ✅ YES           | -
Chiller_1_Power_kW   | real_kw  | HIGH  | 1247.3 | ✅ YES      | ✅ YES           | Submetered
CHWP_1_VSD           | raw_65k  | MED   | 62450  | ⚠️ REVIEW   | ✅ YES           | Verify not Amps
Tower_Fan_1_Speed    | analog   | MED   | 9120   | ⚠️ REVIEW   | ⚠️ REVIEW        | Close to 10k
Pump_3_VSD           | p_range  | LOW   | 42780  | 🚫 NO       | 🚫 NO            | Non-zero baseline
```

---

## Decision Tree for Critical Analytics

```
┌─────────────────────────────────┐
│ Using signal for COP/Energy?   │
└────────────┬────────────────────┘
             │
             ├─ Confidence = HIGH? ──────────────────────> ✅ PROCEED
             │
             ├─ Confidence = MEDIUM? 
             │    └─> Manual review → Validated? ─> YES ─> ✅ PROCEED
             │                                    └─> NO ──> 🚫 BLOCK
             │
             └─ Confidence = LOW? ───────────────────────> 🚫 BLOCK
```

---

## Auto-Validation Rules

### Rule 1: Cross-Check with Expected Ranges

```python
EXPECTED_RANGES = {
    "chiller_load_plr": (0.0, 1.1),      # 0-110% acceptable
    "pump_speed_fraction": (0.0, 1.0),   # Pumps don't exceed 100%
    "valve_position": (0.0, 1.0),        # Valves 0-100%
    "damper_position": (0.0, 1.0),       # Dampers 0-100%
    "tower_fan_speed": (0.0, 1.0),       # Fans 0-100%
}

def auto_validate(signal_type, normalized_series):
    """Auto-validate against expected ranges."""
    if signal_type not in EXPECTED_RANGES:
        return "UNKNOWN_TYPE"
    
    min_exp, max_exp = EXPECTED_RANGES[signal_type]
    actual_max = normalized_series.max()
    
    if actual_max > max_exp * 1.05:  # 5% tolerance
        return f"FAIL: Max {actual_max:.2f} exceeds expected {max_exp}"
    
    return "PASS"
```

### Rule 2: Correlation Checks (Multi-Signal)

```python
def validate_chiller_signals(load_series, power_series):
    """Validate chiller load vs power correlation."""
    correlation = load_series.corr(power_series)
    
    if correlation < 0.7:
        return {
            "status": "FAIL",
            "reason": f"Load-Power correlation {correlation:.2f} < 0.7",
            "action": "Check if Load is % or if Power is correct unit"
        }
    
    # Check if relationship is ~cubic (expected for chillers)
    from scipy.stats import pearsonr
    load_cubed = load_series ** 3
    r_cubic, _ = pearsonr(load_cubed, power_series)
    
    if r_cubic > correlation:
        return {
            "status": "PASS",
            "confidence": "HIGH",
            "note": f"Cubic relationship detected (r={r_cubic:.3f})"
        }
    
    return {
        "status": "PASS",
        "confidence": "MEDIUM",
        "note": "Linear relationship - verify load is actual % not kW"
    }
```

---

## Summary

**Edge cases teach us:**

1. **Confidence matters more than detection type** - Always report it
2. **Ambiguity is reality** - Build workflows for human validation
3. **Context is critical** - Equipment type, nameplate, and correlations validate detection
4. **Progressive validation** - HIGH → auto, MEDIUM → flag, LOW → block

**Key insight:** The decoder should be **step 1 of 3**:
1. Auto-detect (decoder)
2. Validate (rubric)
3. Certify (human review for critical signals)

# Unit Confusion Solutions - 3 Critical Problems Solved

## Overview

These 3 unit confusion problems destroy 90% of HVAC analytics projects. This document explains each problem, detection method, and solution.

---

## Problem #1: "Load %" vs Real Power (kW) Confusion

### The Problem

**Symptom:** BMS exports label a signal "Chiller_Load" or "Chiller_%", but it's actually real electrical power (kW), not % load.

**Impact:**
- COP calculations collapse: `COP = Cooling_Output / Real_Power`
- If you treat kW as %, COP values become nonsense (e.g., COP = 0.5 instead of 5.0)
- kW/ton regressions fail completely
- Optimization dispatch makes wrong decisions

**Why It Happens:**
- BMS integrators mislab

el points
- Power meters log directly but field gets called "Load"
- Some controllers use "load" to mean power draw, not % effort

### Detection Method

```python
def detect_load_vs_kw(signal, nameplate_kw):
    """
    Key insight: Real kW will be bounded by nameplate capacity.
    Load % will not correlate with absolute nameplate value.
    """
    
    # Test 1: Range check
    if 0.6 * nameplate_kw < signal.max() < 1.4 * nameplate_kw:
        return "REAL_KW"  # Max aligns with nameplate
    
    # Test 2: Average check
    if signal.mean() / signal.max() > 0.7:
        return "SUSPICIOUS_POSSIBLY_KW"  # Equipment rarely runs >70% average load
    
    # Test 3: Value range
    if signal.max() <= 1.05:
        return "LOAD_FRACTION"
    elif signal.max() <= 110:
        return "LOAD_PERCENT"
    
    # Test 4: Cross-validation with known power signal
    if power_signal_available:
        corr = signal.corr(power_signal)
        if corr > 0.95:
            return "REAL_KW"  # Too correlated to be independent %
```

### Solution

**DO NOT NORMALIZE signals detected as kW:**

```python
from signal_unit_validator import SignalUnitValidator

validator = SignalUnitValidator()

result = validator.validate_load_signal(
    chiller_signal,
    "Chiller_1_Load",
    equipment_type="chiller",
    nameplate_kw=1200
)

if result["likely_unit"] == "REAL_KW":
    print("🚫 DO NOT NORMALIZE - Use raw kW values")
    power_kw = chiller_signal  # Use as-is
else:
    print("✅ Normalize to 0-1 fraction")
    normalized = normalize_percent_signal(chiller_signal)
```

### Validation Rule

```python
# For COP calculations
if signal_unit == "REAL_KW":
    cop = cooling_tons * 3.517 / signal_raw  # Use raw kW
elif signal_unit == "LOAD_PERCENT":
    estimated_kw = nameplate_kw * (signal_normalized ** 3)  # Affinity laws
    cop = cooling_tons * 3.517 / estimated_kw
else:
    raise ValueError("Cannot calculate COP - unit uncertain")
```

---

## Problem #2: Load > 100% as Mode Change (Not Fault)

### The Problem

**Symptom:** Chiller "Load %" shows values like 120%, 150%, 180% during normal operation.

**Impact:**
- Junior engineers flag as sensor fault
- Anomaly detection algorithms generate false alarms
- Operating mode classification fails
- Clustering algorithms produce garbage results

**Why It Happens:**
- Some chillers switch units beyond 100%:
  - 0-100% = Percentage load (compressor effort)
  - 100-200 = Refrigerant Tons (RT)
  - 200+ = Capacity Index (proprietary)
- BMS exports single column with multiple unit modes

### Detection Method

```python
def detect_mode_changes(signal):
    """
    Key insights:
    - True faults are rare spikes
    - Mode changes show sustained periods >100%
    - Step changes indicate unit switches
    """
    
    # Test 1: Sustained >100%
    over_100_pct = (signal > 100).sum() / len(signal) * 100
    if over_100_pct > 1:  # >1% of samples
        return {
            "mode_change": True,
            "description": f"{over_100_pct:.1f}% of samples > 100"
        }
    
    # Test 2: Large step changes
    diffs = signal.diff().abs()
    large_steps = (diffs > 50).sum()
    if large_steps > len(signal) * 0.005:  # >0.5% of samples
        return {
            "mode_change": True,
            "description": "Multiple 50+ unit jumps detected"
        }
    
    return {"mode_change": False}
```

### Solution

**Split analysis by operating mode:**

```python
# Detect mode boundaries
mode_1_mask = (signal >= 0) & (signal <= 100)
mode_2_mask = (signal > 100) & (signal <= 200)
mode_3_mask = (signal > 200)

# Analyze each mode separately
mode_1_data = signal[mode_1_mask]  # % Load
mode_2_data = signal[mode_2_mask]  # RT (convert: RT = (value - 100))
mode_3_data = signal[mode_3_mask]  # Capacity Index (vendor doc needed)

# For analytics
if mode_2_mask.any() or mode_3_mask.any():
    logger.warning("Multi-mode signal detected - using mode 1 only")
    signal_clean = signal[mode_1_mask]
```

### Validation Rule

```python
# Flag but don't block
if max(signal) > 110:
    print("⚠️  MODE CHANGE WARNING:")
    print("   Signal exceeds 100% - likely unit switch")
    print("   Contact vendor for mode documentation")
    print("   Split analysis: [0-100] vs [>100]")
    
    # Still usable for modes 0-100
    if (signal <= 100).sum() > len(signal) * 0.5:
        print("   ✅ >50% of data in [0-100] - proceed with caution")
```

---

## Problem #3: kW vs kWh (Instantaneous vs Cumulative) Confusion

### The Problem

**Symptom:** BMS labels point "Power_kW" but it's actually cumulative "Energy_kWh" counter, or vice versa.

**Impact:**
- **If you integrate cumulative kWh:** Get exponential curves (nonsense)
- **If you use instantaneous kW as cumulative:** Energy appears near-zero
- Destroys:
  - Hourly energy modeling
  - EUI calculations
  - Baseline estimation
  - 15-minute interval analysis for RL training

**Why It Happens:**
- BMS integrators confuse instantaneous vs cumulative
- Some power meters output both, labels get swapped
- Legacy systems relabel points during upgrades

### Detection Method

```python
def detect_kwh_confusion(signal, signal_name):
    """
    Key insights:
    - kWh (cumulative) is monotonic increasing
    - kW (instantaneous) varies up/down
    - Cumulative has very low coefficient of variation
    """
    
    # Test 1: Monotonicity
    diffs = signal.diff()
    negative_pct = (diffs < -0.01).sum() / len(diffs) * 100
    
    if negative_pct < 1:  # <1% negative → cumulative
        if "kw" in signal_name.lower() and "kwh" not in signal_name.lower():
            return {
                "confused": True,
                "actual_unit": "kWh (cumulative)",
                "labeled_as": "kW (instantaneous)"
            }
    
    # Test 2: Coefficient of Variation
    cv = signal.std() / (signal.mean() + 0.001)
    
    if cv < 0.05:  # Very low variation
        if signal.mean() > 0:
            return {
                "confused": True,
                "actual_unit": "Likely kWh (cumulative)",
                "reason": "CV < 0.05 - too stable for instantaneous power"
            }
    
    # Test 3: Cross-check with another signal
    if power_signal_available:
        signal_diff = signal.diff()
        corr = signal_diff.corr(power_signal)
        if corr > 0.7:
            return {
                "confused": True,
                "actual_unit": "kWh (cumulative)",
                "proof": f"diff(signal) correlates {corr:.2f} with kW"
            }
    
    return {"confused": False}
```

### Solution

**Differentiate cumulative to get instantaneous:**

```python
from signal_unit_validator import SignalUnitValidator

validator = SignalUnitValidator()

result = validator.validate_load_signal(
    signal,
    "Chiller_Power",
    equipment_type="chiller",
    power_series=reference_kw_signal  # If available for cross-check
)

if "kWh" in result["likely_unit"] or result.get("issues"):
    # Signal is cumulative - differentiate it
    time_diff_hours = df['timestamp'].diff().dt.total_seconds() / 3600
    power_kw = signal.diff() / time_diff_hours
    
    # Clean up first value (NaN from diff)
    power_kw = power_kw.fillna(0)
    
    print("✅ Converted kWh → kW via differentiation")
else:
    power_kw = signal
    print("✅ Signal is instantaneous kW - use as-is")
```

### Validation Rule

```python
# For 15-minute interval analysis
if is_cumulative(signal):
    print("🚨 CUMULATIVE SIGNAL DETECTED")
    print("   DO NOT integrate - differentiate instead")
    print("   kW = diff(kWh) / diff(time_hours)")
    
    # Auto-convert
    signal_kw = convert_cumulative_to_instantaneous(signal, timestamps)
    
elif is_instantaneous(signal):
    print("✅ INSTANTANEOUS SIGNAL")
    print("   Can integrate for total energy: kWh = sum(kW * dt)")
    
    # For energy calculations
    time_delta_hours = timestamps.diff().dt.total_seconds() / 3600
    total_kwh = (signal * time_delta_hours).sum()
```

---

## Comprehensive Validation Workflow

```python
from signal_unit_validator import SignalUnitValidator

# Initialize validator
validator = SignalUnitValidator()

# Validate all signals
results = []

# Chiller load signal
chiller_load_result = validator.validate_load_signal(
    df['Chiller_1_Load'],
    "Chiller_1_Load",
    equipment_type="chiller",
    nameplate_kw=1200,
    power_series=df['Chiller_1_Power_kW']  # Cross-validation
)
results.append(chiller_load_result)

# Chiller power signal
chiller_power_result = validator.validate_load_signal(
    df['Chiller_1_Power'],
    "Chiller_1_Power",
    equipment_type="chiller",
    nameplate_kw=1200
)
results.append(chiller_power_result)

# Generate report
report = validator.generate_validation_report(results)
print(report)

# Take action based on validation
for result in results:
    signal_name = result['signal_name']
    
    if not result['use_for_cop']:
        print(f"🚫 BLOCK {signal_name} from COP calculations")
    
    if not result['use_for_energy']:
        print(f"🚫 BLOCK {signal_name} from energy modeling")
    
    if result['issues']:
        print(f"⚠️  {signal_name} has issues:")
        for issue in result['issues']:
            print(f"   {issue}")
```

---

## Decision Matrix

| Detected Unit | Use for COP? | Use for Energy? | Action |
|---------------|--------------|-----------------|--------|
| **LOAD_PERCENT** | ✅ YES | 🚫 NO (estimate) | Normalize to 0-1 |
| **LOAD_FRACTION** | ✅ YES | 🚫 NO (estimate) | Use as-is (0-1) |
| **REAL_KW** | 🚫 NO | ✅ YES | DO NOT normalize |
| **CUMULATIVE_KWH** | 🚫 NO | ✅ YES (diff) | Differentiate first |
| **MODE_CHANGE** | ⚠️ SPLIT | ⚠️ SPLIT | Analyze [0-100] only |
| **UNKNOWN** | 🚫 NO | 🚫 NO | Manual review required |

---

## Integration with Universal Decoder

The universal decoder handles **encoding detection** (0-100, 0-10000, etc.).  
The unit validator handles **semantic validation** (% vs kW vs kWh).

**Combined workflow:**

```python
from universal_bms_percent_decoder import normalize_percent_signal
from signal_unit_validator import SignalUnitValidator

# Step 1: Decode encoding
normalized, metadata = normalize_percent_signal(raw_signal, "Chiller_Load")

# Step 2: Validate semantics
validator = SignalUnitValidator()
validation = validator.validate_load_signal(
    raw_signal,  # Use raw for validation
    "Chiller_Load",
    equipment_type="chiller",
    nameplate_kw=1200
)

# Step 3: Decide usage
if validation["likely_unit"] == "REAL_KW":
    # Don't use normalized version
    final_signal = raw_signal
    use_for = "energy_only"
    
elif validation["use_for_cop"]:
    # Use normalized version
    final_signal = normalized
    use_for = "cop_and_baseline"
    
else:
    # Block from critical analytics
    final_signal = None
    use_for = "manual_review_required"

print(f"Signal: {use_for}")
print(f"Confidence: {metadata['confidence']} (encoding), {validation['confidence']} (semantic)")
```

---

## Files Created

1. **`signal_unit_validator.py`** - Detects all 3 unit confusion problems
2. **`UNIT_CONFUSION_SOLUTIONS.md`** - This document
3. **`telemetry_validation_rubric.md`** - Validation workflows and reporting

---

## Summary

| Problem | Detection | Solution | Impact |
|---------|-----------|----------|--------|
| **Load % vs kW** | Nameplate alignment + average check | Don't normalize kW signals | Fixes COP calculations |
| **Load > 100% mode change** | Sustained >100% + step changes | Split analysis by mode | Eliminates false alarms |
| **kW vs kWh** | Monotonicity + CV + correlation | Differentiate cumulative signals | Fixes energy modeling |

**Bottom line:** These 3 checks should run **before** using any signal for COP, energy, or optimization analytics.

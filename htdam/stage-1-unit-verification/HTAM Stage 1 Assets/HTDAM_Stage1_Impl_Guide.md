# HTDAM v2.0 Stage 1: Unit Verification & Physics Checks
## Developer Implementation Guide

**Date**: 2025-12-07  
**Status**: Complete specification for Stage 1 only  
**Audience**: AI app developer (TypeScript, Python, Node, etc.)

---

## 1. Physics Validation Ranges (Confirmed)

These ranges are **equipment-specific to centrifugal chiller systems** operating in buildings per ASHRAE 90.1 and 30-2019. They assume standard HVAC water-cooled chiller operation. **Adjust per your customer's equipment nameplate.**

### 1.1 Chilled Water Supply Temperature (CHWST)

**Physics range**: 3–20 °C  
**Typical operating band**: 6–15 °C  
**Rationale**: 
- Below 3 °C: risks ice formation in evaporator.
- Above 20 °C: ineffective for comfort cooling; chiller likely off or failed.

**Threshold for penalty**:
- If <5% of data outside [3, 20] °C: +0.00 penalty (acceptable).
- If 5–10% outside: −0.02 penalty (flag).
- If >10% outside: −0.10 penalty + HALT (likely sensor failure).

**Icepoint check** (critical):
- If CHWST < 0 °C AND CHWRT > 1 °C for same timestamp: likely sensor error or data corruption.
- Mark as SENSOR_ANOMALY in Stage 2.

---

### 1.2 Chilled Water Return Temperature (CHWRT)

**Physics constraint**: CHWRT ≥ CHWST (always). [file:155]  
**Typical operating band**: 11–25 °C  
**Expected ΔT (CHWRT − CHWST)**: 4–10 °C

**Rationale**:
- ΔT < 2 °C: suggests very low load or fouled evaporator. Not invalid, but noteworthy.
- ΔT > 15 °C: suggests fouled condenser, very high load, or sensor error.

**Threshold for penalty**:
- If CHWRT < CHWST for >1% of records: −0.10 penalty + HALT (physics violation). [file:155]
- If CHWRT < CHWST for 0–1% of records: −0.05 penalty (likely isolated sensor spike; drop those rows).
- If ΔT frequently < 1 °C AND ΔT frequently > 15 °C in same dataset: suspicious; flag for manual review.

---

### 1.3 Condenser Water Return Temperature (CDWRT)

**Physics constraint**: CDWRT > CHWST (always; positive lift required). [file:155]  
**Typical operating band**: 18–40 °C  
**Expected lift (CDWRT − CHWST)**: 8–20 °C

**Rationale**:
- Lift < 5 °C: compressor struggling (high outdoor temp or fouled condenser).
- Lift > 25 °C: very high lift, suggests part-load or fouled chiller.
- CDWRT follows outdoor ambient; see seasonal range below.

**Threshold for penalty**:
- If CDWRT ≤ CHWST for >1% of records: −0.10 penalty + HALT (negative lift). [file:155]
- If CDWRT > 45 °C persistently: −0.05 penalty (outdoor temp or fouling; not invalid).
- If CDWRT < 15 °C: unusual for condenser; check if chiller is idle or winter operation.

**Seasonal expectation**:
- Summer peak: CDWRT can reach 32–40 °C (outdoor ambient + approach).
- Winter low: CDWRT can drop to 10–20 °C (cold outdoor air / cooling tower operation).

---

### 1.4 CHW Flow Rate

**Physics constraint**: Never negative; must be > 0 L/s when chiller active. [file:155]  
**Typical operating band**: 10–100 L/s (design-dependent). [file:155]  
**Unit acceptance**: L/s, m³/h, GPM → convert to m³/s internally.

**Threshold for penalty**:
- If any flow < 0: −0.10 penalty + HALT (data corruption). [file:155]
- If flow = 0 for >30% of dataset: suspicious (chiller idle?); document and continue (confidence −0.10).
- If flow > 1.5 × design max: −0.05 penalty (likely sensor error or bypass valve open).

**Why flow is mandatory** [file:155]:
- Without flow, **cooling load \( \dot{Q} \) cannot be computed**.
- Without load, **COP cannot be computed**.
- Without COP, **baseline hypothesis cannot be proved or rejected**.

---

### 1.5 Electrical Power Input

**Physics constraint**: Never negative; must be ≥ 0 kW. [file:155]  
**Typical operating band**: 50–500 kW (design-dependent, huge variation). [file:155]  
**Unit acceptance**: W, kW, MW → convert to kW internally.

**Threshold for penalty**:
- If any power < 0: −0.10 penalty + HALT (data corruption). [file:155]
- If power = 0 for >30% of dataset: acceptable (chiller idle/off); document and continue.
- If power > 1.5 × design nameplate: −0.05 penalty (likely spike or secondary loads).

**Why power is mandatory** [file:155]:
- Without power, **COP = \( \dot{Q} \) / Power cannot be computed**.
- Without COP, **7% savings hypothesis cannot be rigorously tested**.

---

## 2. Unit Conversion Rules

### 2.1 Canonical Internal Units

Store and compute in these units throughout HTDAM:

| Quantity | Canonical | Conversion |
|----------|-----------|-----------|
| Temperature | °C | From °F: \( T_°C = (T_°F - 32) \times 5/9 \) |
| Flow | m³/s | From L/s: × 0.001 / From m³/h: ÷ 3600 / From GPM: × 0.0000630902 |
| Power | kW | From W: ÷ 1000 / From MW: × 1000 |
| Specific heat (water) | kJ/kg·K | Always 4.186 (fixed constant) |
| Water density (water) | kg/m³ | Always 1000 (fixed constant, 5–30°C range) |

### 2.2 Storage Strategy: Dual Columns

**Recommended approach** (preserves traceability):

Store **both** original and converted:

```
Input CSV columns (user-supplied):
  CHWST [reported_unit]
  
Output Stage 1 dataframe columns:
  CHWST_orig = original value from CSV
  CHWST_orig_unit = reported unit (string: "C", "F", "K")
  CHWST = converted to canonical (°C)
  CHWST_unit_confidence = 0.95 (if unit was unambiguous) or 0.00 (if inferred/manual)
```

This allows:
- **Auditability**: You can always revert to original.
- **Error tracking**: If conversion was wrong, redo it.
- **Compliance**: Show what the BMS reported vs. what you used.

---

## 3. Confidence Scoring: Formula & Thresholds

### 3.1 Unit Confidence Per Channel

For each of the 5 mandatory channels:

```
unit_confidence[channel] = base * (1 - penalties_sum)

where:
  base = 1.00 (start here)
  
  penalties:
    - Missing unit string: −0.30
    - Ambiguous unit (e.g., "T" could be K or °C): −0.20
    - Non-SI unit requiring conversion (e.g., °F): −0.00 (acceptable)
    - Manual override needed (human confirmed): −0.10
    - Data outside documented sensor range (mfr. spec): −0.05
```

**Examples**:

- CHWST = 15.5, unit = "C" → confidence = 1.00 × (1 − 0) = **1.00** ✓
- CHWRT = 68, unit = "F" → confidence = 1.00 × (1 − 0) = **1.00** ✓ (convert to 20°C)
- CDWRT = 25, unit = "K" (ambiguous) → confidence = 1.00 × (1 − 0.20) = **0.80** ⚠️
- Power = 120, unit = null (missing) → confidence = 1.00 × (1 − 0.30) = **0.70** ⚠️

### 3.2 Physics Confidence Per Channel

For each channel, after unit conversion, compute **physics_confidence**:

```
physics_confidence[channel] = 1.00 − (violations_pct / 100 * 0.10)

where:
  violations_pct = % of records outside acceptable physics range
  
  formula: If 5% violate → 1.00 − (5/100 * 0.10) = 0.995 (tiny penalty)
           If 15% violate → 1.00 − (15/100 * 0.10) = 0.985 (small penalty)
           If >50% violate → HALT, do not proceed
```

### 3.3 Final Unit Confidence for Stage 1

```
stage1_confidence = min(
  unit_confidence[CHWST],
  unit_confidence[CHWRT],
  unit_confidence[CDWRT],
  unit_confidence[Flow],
  unit_confidence[Power]
)
```

This ensures **all 5 bare-minimum channels must be high-confidence** for the stage to pass. [file:155]

**Stage 1 penalty** (added to finalScore):

```
if stage1_confidence >= 0.95:
  penalty = −0.00
elif stage1_confidence >= 0.80:
  penalty = −0.02
else:
  penalty = −0.05 (or HALT if <0.50)
```

---

## 4. Physics Violation Thresholds: Actions

### 4.1 Hard Stops (HALT – do not proceed to Stage 2)

- [ ] **Any negative flow or power**: HALT immediately. [file:155]
- [ ] **CHWRT < CHWST for >1% of records**: HALT (thermodynamic violation). [file:155]
- [ ] **CDWRT ≤ CHWST for >1% of records**: HALT (negative lift). [file:155]
- [ ] **All 5 bare-minimum channels not present and unambiguously parseable**: HALT (COP unprovable). [file:155]

**Output on HALT**:
- Log error message: `"Stage 1 HALT: [specific reason]"`.
- Return context with `errors: [...]` and `finalScore = 0.00`.
- Expose human review hook (let user decide to override).

### 4.2 Soft Penalties (Reduce confidence, continue)

| Condition | % of Records | Penalty |
|-----------|--------------|---------|
| CHWST outside [3, 20] °C | 1–5% | −0.02 |
| CHWST outside [3, 20] °C | 5–10% | −0.05 |
| ΔT < 2 °C (low load) | Any % | −0.00 (informational, not a penalty) |
| ΔT > 15 °C (high load) | Any % | −0.00 (informational, not a penalty) |
| CDWRT > 45 °C (very hot) | >20% | −0.03 |
| Isolated outliers (1–2 points) | <0.1% | −0.00 (drop silently) |

---

## 5. Output Format: Stage 1

### 5.1 Data Output

**Input**: Raw dataframe or dict of streams (from Stage 0 ingestion).

**Output**: Enriched dataframe with new columns (do NOT replace originals):

```
Columns added by Stage 1:

chwst_orig (original value, any unit)
chwst_orig_unit (string: "C" | "F" | "K")
chwst (canonical, °C)
chwst_unit_confidence (0.0–1.0)
chwst_physics_violations_count (integer)

chwrt_orig, chwrt_orig_unit, chwrt, chwrt_unit_confidence, ...
cdwrt_orig, cdwrt_orig_unit, cdwrt, cdwrt_unit_confidence, ...
flow_orig, flow_orig_unit, flow_m3s, flow_unit_confidence, ...
power_orig, power_orig_unit, power_kw, power_unit_confidence, ...

stage1_overall_confidence (float, 0.0–1.0)
stage1_physics_valid (boolean: True if no hard-stops)
```

### 5.2 Metrics Output

Return as dict (JSON-serializable):

```json
{
  "stage": "UNITS",
  "timestamp_start": "2024-09-18T03:30:00Z",
  "timestamp_end": "2025-09-19T03:15:05Z",
  "total_records": 35574,
  
  "unit_conversions": {
    "chwst": { "reported_unit": "C", "converted_to": "C", "conversion_factor": 1.0 },
    "chwrt": { "reported_unit": "C", "converted_to": "C", "conversion_factor": 1.0 },
    "flow": { "reported_unit": "L/s", "converted_to": "m3/s", "conversion_factor": 0.001 },
    "power": { "reported_unit": "kW", "converted_to": "kW", "conversion_factor": 1.0 }
  },
  
  "physics_violations": {
    "chwst": { "outside_range_count": 12, "outside_range_pct": 0.034, "penalty": -0.00 },
    "chwrt_less_than_chwst_count": 0,
    "chwrt_less_than_chwst_pct": 0.0,
    "cdwrt_lte_chwst_count": 0,
    "cdwrt_lte_chwst_pct": 0.0,
    "flow_negative_count": 0,
    "power_negative_count": 0
  },
  
  "confidence_scores": {
    "chwst_unit_confidence": 1.00,
    "chwrt_unit_confidence": 1.00,
    "cdwrt_unit_confidence": 1.00,
    "flow_unit_confidence": 1.00,
    "power_unit_confidence": 1.00,
    "stage1_overall_confidence": 1.00
  },
  
  "penalty": -0.00,
  "final_score": 1.00,
  
  "warnings": [],
  "errors": [],
  "halt": false
}
```

### 5.3 CSV Export (Optional)

If you want to export Stage 1 output as CSV for human review:

```
timestamp,chwst_orig,chwst_orig_unit,chwst,chwst_unit_confidence,chwst_physics_valid,
chwrt_orig,chwrt,chwrt_unit_confidence,chwrt_physics_valid,
cdwrt_orig,cdwrt,cdwrt_unit_confidence,cdwrt_physics_valid,
flow_orig,flow_orig_unit,flow_m3s,flow_unit_confidence,flow_physics_valid,
power_orig,power_orig_unit,power_kw,power_unit_confidence,power_physics_valid,
stage1_overall_confidence

2024-09-18T03:30:00,17.56,C,17.56,1.00,true,17.39,17.39,1.00,true,22.11,22.11,1.00,true,0.001234,L/s,0.001234,1.00,true,45.2,kW,45.2,1.00,true,1.00
```

---

## 6. Physics Constants: Storage & Access

### 6.1 Constants Definition

Create a single **domain-level constants file** (not app-specific):

**`htdam_constants.py` (or `.ts` / `.js`)**:

```python
# HVAC Physics Constants (SI units)

# Water properties (5–30°C range, typical for chilled water)
WATER_DENSITY_kg_m3 = 1000.0        # kg/m³
WATER_SPECIFIC_HEAT_kJ_kg_K = 4.186  # kJ/kg·K (or 4186 J/kg·K)

# Temperature validation ranges (°C)
CHWST_VALID_MIN = 3.0
CHWST_VALID_MAX = 20.0
CHWRT_VALID_MIN = 5.0   # Allow slightly lower than CHWST for edge cases
CHWRT_VALID_MAX = 30.0
CDWRT_VALID_MIN = 15.0
CDWRT_VALID_MAX = 45.0

# Flow validation (m³/s)
FLOW_VALID_MIN = 0.0
FLOW_VALID_MAX = 0.2      # Adjust per your chiller max (typical 50–100 L/s = 0.05–0.1 m³/s)

# Power validation (kW)
POWER_VALID_MIN = 0.0
POWER_VALID_MAX = 1000.0  # Adjust per your chiller nameplate

# Unit conversion factors
UNIT_CONVERSIONS = {
    "temperature": {
        "C": 1.0,
        "F": lambda t: (t - 32) * 5/9,
        "K": lambda t: t - 273.15,
    },
    "flow": {
        "L/s": 0.001,           # to m³/s
        "m3/s": 1.0,
        "m3/h": 1.0 / 3600.0,
        "GPM": 0.0000630902,
    },
    "power": {
        "W": 0.001,             # to kW
        "kW": 1.0,
        "MW": 1000.0,
    }
}

# Confidence thresholds
UNIT_CONFIDENCE_THRESHOLDS = {
    "missing_unit": -0.30,
    "ambiguous_unit": -0.20,
    "requires_conversion": -0.00,
    "manual_override": -0.10,
    "outside_sensor_range": -0.05,
}

PHYSICS_CONFIDENCE_VIOLATION_FACTOR = 0.10  # 1% violation → 0.001 penalty

# Stage 1 halt conditions
HALT_CONDITIONS = {
    "negative_flow": True,
    "negative_power": True,
    "chwrt_less_than_chwst_pct_threshold": 0.01,  # >1% → halt
    "cdwrt_lte_chwst_pct_threshold": 0.01,        # >1% → halt
    "missing_bare_minimum_channels": True,
}
```

### 6.2 Access Pattern

In your Stage 1 function:

```python
from htdam_constants import CHWST_VALID_MIN, CHWST_VALID_MAX, WATER_SPECIFIC_HEAT_kJ_kg_K

def verify_units_and_physics(ctx):
    # Use constants:
    if ctx.chwst < CHWST_VALID_MIN or ctx.chwst > CHWST_VALID_MAX:
        violations += 1
    
    # Constants also used in Stage 4 (load calc):
    load_kW = mass_flow_kg_s * WATER_SPECIFIC_HEAT_kJ_kg_K * delta_t_celsius / 1000.0
```

This ensures **physics constants are defined once, used everywhere**.

---

## 7. Design Capacity Data: Why Your Programmer Is Asking

### 7.1 The Question

> "Do we have design capacity data (flow envelope, power envelope)?"

### 7.2 Answer: Not Required for Stage 1, But Useful

**Design capacity is OPTIONAL for Stage 1**, but answers an important question:

- **With design data**: You can validate against **equipment specs**. Example:
  - Chiller nameplate: 100 L/s, 200 kW @ full load.
  - If measured flow > 150 L/s or power > 300 kW, flag as out-of-design.

- **Without design data**: Use **generic physics ranges** (listed above).

### 7.3 Where Design Data Comes From

If available, add to context:

```python
design_data = {
    "chiller_model": "Trane CenTraVac",
    "chiller_capacity_tons": 300,
    "chiller_capacity_kw": 1055,       # 300 tons × 3.517 kW/ton
    "design_chw_flow_L_s": 95,         # @ design load
    "design_condenser_approach": 2.8,
    "design_lift_K": 10.5,
}

# In Stage 1, you can use these to tighten the envelope:
FLOW_DESIGN_MAX = design_data["design_chw_flow_L_s"] * 1.25  # Allow 25% overage
POWER_DESIGN_MAX = design_data["chiller_capacity_kw"] * 1.25
```

**If you don't have design data, your programmer should ask the customer** (BMS system owner) for the chiller nameplate specs. But Stage 1 can run without it.

---

## 8. FAQ for Your Programmer

### Q1: Do we store both original AND converted, or just converted?

**Answer**: **Store both**. You need the original for:
- Audit trails ("BMS reported 68 °F").
- Error recovery ("Conversion was wrong, let me redo it").
- Traceability ("User supplied unit was ambiguous").

### Q2: What format is the Stage 1 output?

**Answer**: 
- **Data**: Enhanced dataframe (add columns, do NOT replace).
- **Metrics**: Dict / JSON object (serializable, for logging).
- **CSV export**: Optional, for human review.

### Q3: When do we HALT vs continue?

**Answer**:
- **HALT**: Negative flow/power, CHWRT < CHWST >1%, missing bare-minimum channels. [file:155]
- **Continue with penalty**: Physics violations <1%, ambiguous units (confidence reduced).

### Q4: Where do constants live?

**Answer**: Single `htdam_constants.py` (or `.ts`) in the domain layer. Import everywhere.

### Q5: Do we need design capacity data?

**Answer**: No, but it's nice-to-have. Ask customer for chiller nameplate if available. Stage 1 works without it.

### Q6: What's the confidence formula?

**Answer**: 
```
unit_confidence = 1.00 × (1 − penalty_sum)
physics_confidence = 1.00 − (violations_pct / 100 × 0.10)
stage1_confidence = min(all channels)
```

### Q7: Should we export Stage 1 as CSV or just pass DataFrame?

**Answer**: Pass DataFrame to Stage 2. Optionally export CSV for human review / debugging.

---

## 9. Checklist for Implementation

- [ ] Define `CHWST`, `CHWRT`, `CDWRT`, `Flow`, `Power` valid ranges in constants file.
- [ ] Implement unit converter for Temperature (°C, °F, K), Flow (L/s, m³/h, GPM), Power (W, kW, MW).
- [ ] Add new columns to dataframe: `_orig`, `_orig_unit`, canonical value, `_unit_confidence`, `_physics_valid`.
- [ ] Compute per-channel `unit_confidence` and `physics_confidence`.
- [ ] Implement hard-stop checks (negative, CHWRT < CHWST >1%, missing channels).
- [ ] Compute `stage1_overall_confidence = min(all channels)`.
- [ ] Apply penalty: −0.00 if conf ≥0.95, −0.02 if 0.80–0.95, −0.05 if <0.80.
- [ ] Return enriched dataframe + metrics dict.
- [ ] Log all violations and confidence scores to stdout/file.
- [ ] Test with BarTech CSVs (all temps in °C, no conversion needed, should score 1.00).

---

**Status**: Complete for Stage 1 only.  
**Next**: Stage 2 (Gap Detection) specification.  
**Generated**: 2025-12-07


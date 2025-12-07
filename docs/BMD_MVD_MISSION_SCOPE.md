# BMD vs MVD: Mission Scope & Data Requirements

**Purpose**: Define the distinction between BMD and MVD missions, data requirements, and repository scope  
**Date**: 2025-12-07  
**Status**: Reference Document

---

## Quick Reference

| Aspect | BMD | MVD |
|--------|-----|-----|
| **Mission** | Prove/reject baseline hypothesis | Complete HVAC health check & efficiency report |
| **Scope** | Chiller performance only | Whole HVAC system + building context |
| **Sensors** | 5 measured parameters | 15+ parameters (with proxies) |
| **Rigor** | Physics-validated COP required | Confidence-adjusted with fallbacks |
| **Use Case** | Investment decision (≥7% savings?) | Ongoing optimization & monitoring |

---

## BMD (Bare Minimum Data)

### Mission Statement

**Hypothesis to Test**:
> "In the future it is not possible to save at least 7% in the chiller system using standard efficiency improvements due to the system's current mechanical and thermal limitations."

**Goal**: Prove or reject this hypothesis with **physically rigorous** analysis.

### Data Requirements

**5 Measured Parameters** (all mandatory):

| Parameter | Symbol | Unit | Critical For |
|-----------|--------|------|--------------|
| CHW Supply Temp | CHWST | °C | ΔT calculation |
| CHW Return Temp | CHWRT | °C | ΔT calculation |
| CHW Flow Rate | V̇_chw | L/s, GPM, m³/s | **MANDATORY** for cooling capacity |
| Electrical Power | W_input | kW | **MANDATORY** for COP |
| Condenser Return Temp | CDWRT | °C | Lift & part-load performance |

**3 Derived Parameters**:
- **ΔT** = CHWRT - CHWST
- **Load (Q̇)** = ṁ × c_p × ΔT (kW)
- **COP** = Q̇ / W_input

### Physics Foundation

**Cooling Capacity**:
```
Q̇ = ṁ × c_p × ΔT

Where:
- ṁ = mass flow (kg/s) = V̇ × ρ
- V̇ = volumetric flow (m³/s)
- ρ ≈ 1000 kg/m³ (water density)
- c_p ≈ 4.186 kJ/kg·K (specific heat of water)
- ΔT = CHWRT - CHWST (°C)
```

**COP**:
```
COP = Q̇ / W_input

To test "≥7% improvement", must be able to:
1. Compute present COP at given operating points
2. Compare against baseline/design COP
3. Quantify improvement in COP after standard measures
```

### Critical Constraint

**Without FLOW or POWER**: The baseline hypothesis **cannot be proven or rejected** in a physically rigorous way.

**No Proxies**: BMD requires actual measured data for CHWF and POWER. No fallbacks or estimates allowed for hypothesis testing.

---

## MVD (Minimum Viable Data)

### Mission Statement

**Goal**: Enable complete HVAC health check and efficiency report **without asking for huge number of telemetry feeds**.

**Purpose**: AI-driven HVAC optimization with:
- Baseline load profiling
- Operational modeling
- Real-time COP calculation (with confidence adjustments)
- System-wide efficiency analysis
- Fault detection and diagnostics

### Data Requirements

**Expanded Set** (15+ parameters with proxy/fallback logic):

#### 1. Energy
| Data Type | Source | Sampling | Purpose | If Missing/Faulty |
|-----------|--------|----------|---------|-------------------|
| Chiller power (kW) | BMS / Energy Meter | 5–15 min | COP denominator; baseline load | ±8% derate if uncalibrated |
| AHU / FCU fan energy (kW) | BMS / Meter | 15 min | VFD tuning; part-load optimization | Cap savings if VFD forced to manual |
| Cooling tower power (kW) | BMS / Meter | 5–15 min | Evaporator/condenser shift analysis | Use utility kWh proxy if missing |
| Building-level energy (kWh) | Utility Meter | Hourly | Sanity check, model reconciliation | ±3% adjustment if no bill alignment |

#### 2. COP Components
| Data Type | Source | Sampling | Purpose | If Missing/Faulty |
|-----------|--------|----------|---------|-------------------|
| CHW supply temp (°C) | BMS Sensor | 5–15 min | ΔT for cooling load | Use spot probe ±1.5°C if not available |
| CHW return temp (°C) | BMS Sensor | 5–15 min | ΔT for cooling load | Add ±6% band if >1°C sensor drift |
| CHW flow rate (L/s, m³/h) | BMS / Pump | 5–15 min | Total cooling output | Use design flow or VFD RPM proxy (confidence drop) |

#### 3. Environment
| Data Type | Source | Sampling | Purpose | If Missing/Faulty |
|-----------|--------|----------|---------|-------------------|
| Outdoor dry-bulb / RH | Weather API / BMS | 15 min | Load forecasting; control model | ±6% derate if sensor drift >1°C |
| Indoor zone temperatures | Thermostat / BMS | 5–15 min | Comfort zone validation; zoning | Use Wi-Fi or manual probes if not available |

#### 4. Operational
| Data Type | Source | Sampling | Purpose | If Missing/Faulty |
|-----------|--------|----------|---------|-------------------|
| Equipment setpoints & fan speeds | BMS | 5 min | AI control; override detection | Flag persistent overrides; reduce reliability |
| Occupancy (optional) | CO₂ / counters | 5–15 min | Demand-based control tuning | Mark model as static if unavailable |

#### 5. Diagnostics
| Data Type | Source | Sampling | Purpose | If Missing/Faulty |
|-----------|--------|----------|---------|-------------------|
| Fault / Event logs | BMS | Event-based | Predictive maintenance | Flag and derate if >10% unresolved alarms |
| Service logs | Manual / FM | Monthly | De-biasing model, historical check | Mark as "high uncertainty" if missing |

### COP Calculation with Proxies

**Standard Formula**:
```
COP = Cooling Output (kW) / Chiller Electrical Input (kW)

Where:
Cooling Output (kW) = CHW Flow Rate × ΔT × 4.186 / 3600
```

**Proxy Logic**:

| Condition | Proxy / Mitigation | Derate Applied | Confidence Impact |
|-----------|-------------------|----------------|-------------------|
| No CHW ΔT sensors | Manual probe / temp logs | Add ±1.5°C band to cooling output | -1 tier |
| No CHW flow meter | Use design flow + VSD RPM estimate | Drop COP confidence one tier | -1 tier |
| Uncalibrated chiller power meter | Cross-check with utility bill | ±8% adjustment | -1 tier |
| CHW sensor drift >1°C | Spot-check with handheld logger | ±6% derate | -1 tier |
| Persistent overrides on setpoints | Enforce auto-revert policies | Confidence reduced | Flag as unreliable |
| VFD in manual / bypass mode | Require keypad photo or fault log | Cap energy savings at 60% | Mark as constrained |

### Key Difference from BMD

**MVD allows degraded operation** with proxy data and confidence derating:
- Missing sensors? Use proxies with reduced confidence
- Uncalibrated meters? Apply adjustment factors
- Sensor drift? Apply uncertainty bands

**BMD requires perfect data** for hypothesis testing:
- All 5 sensors must be present and accurate
- No proxies or fallbacks allowed
- Physics must be rigorously validated

---

## Repository Mission Scope

### Current Mission: BMD Focus

**This Repository** (`hvac-telemetry-data-acquisition-testbed-master`) is currently focused on **BMD mission**:

✅ **In Scope**:
- HTDAM 5-stage pipeline for BMD sensors
- Phase 0: Filename parsing (CSV/XLSX)
- Stage 1: Unit verification (CHWST, CHWRT, CDWRT, CHWF, POWER)
- Stage 2: Gap detection (COV vs sensor failure)
- Stage 3: Timestamp synchronization (15-min grid)
- Stage 4: Physics validation (ΔT, Load, COP)
- Stage 5: Export specs for COP calculation

✅ **BMD Sensors Only**:
- Temperature: CHWST, CHWRT, CDWRT
- Flow: CHW flow rate
- Power: Chiller electrical power

❌ **Out of Scope** (for now):
- AHU/FCU fan energy
- Cooling tower power
- Building-level energy
- Outdoor temperature/RH
- Indoor zone temperatures
- Occupancy sensors
- Fault logs beyond basic detection
- Service log integration

### Future Extension: MVD Mission

**When/If Extended to MVD Mission**:

📋 **Would Add**:
- Additional sensor types (AHU, CT, weather, occupancy)
- Proxy/fallback logic for missing sensors
- Confidence scoring system with derating
- System-wide health check reports
- Fault detection and diagnostics
- Predictive maintenance inputs
- Control optimization recommendations

📋 **Architecture Changes**:
- Expand Stage 1 to handle 15+ sensor types
- Add confidence adjustment framework
- Implement proxy detection logic
- Add system-wide validation (not just chiller)
- Integrate with fault log parsing
- Add occupancy pattern detection

📋 **New Documentation**:
- MVD sensor mapping guide
- Proxy selection algorithms
- Confidence derating calculation
- System health scoring methodology
- Fault pattern recognition

---

## LOAD Signal: Where Does It Fit?

### Neither BMD nor MVD Core

**LOAD signal is NOT required** for either BMD or MVD core missions because:
- Can be calculated from BMD sensors: Q̇ = ṁ × c_p × ΔT
- Physics-based calculation is more reliable than BMS-reported load
- BMS "Load" has ambiguous units (percent, tons, vendor index)

### When LOAD is Useful

**LOAD becomes valuable** when:
1. **Physics validation**: Compare BMS-reported load vs calculated load
2. **Sensor failure detection**: Mismatch indicates flow/temp sensor issue
3. **Historical analysis**: When BMD sensors missing, LOAD may be only record
4. **Cross-vendor compatibility**: Some BMS provide LOAD but not flow

### Implementation Status

**LOAD Normalization**:
- ✅ Specified: `docs/LOAD_NORMALIZATION_SPEC.md`
- ✅ Architecture: Hook-based (follows "State lives in hooks")
- ⏸️ Implementation: Stage 1 extension (after BMD sensors complete)
- 🎯 Priority: Medium (useful but not critical)

**When to Implement**:
1. Complete BMD sensors first (CHWST, CHWRT, CDWRT, CHWF, POWER)
2. Validate physics-based load calculation works
3. Then add LOAD normalization as validation cross-check

---

## Mission Evolution Path

### Phase 1: BMD Foundation (Current)
**Goal**: Rigorous COP calculation for hypothesis testing  
**Sensors**: 5 BMD sensors only  
**Output**: Physics-validated COP dataset  
**Status**: Phase 0 complete, Stage 1 in planning

### Phase 2: BMD Extensions (Optional)
**Goal**: Enhance BMD with validation signals  
**Additions**: LOAD normalization, CDWST (condenser supply temp)  
**Output**: BMD + validation cross-checks  
**Status**: Documented, not scheduled

### Phase 3: MVD Migration (Future)
**Goal**: Complete HVAC health check & efficiency report  
**Additions**: 10+ additional sensors, proxy logic, confidence framework  
**Output**: System-wide optimization recommendations  
**Status**: Not started, would be separate mission

---

## Decision Guide: BMD or MVD?

### Choose BMD When:
- ✅ Need to prove/reject specific savings hypothesis
- ✅ Have access to all 5 sensors (no proxies)
- ✅ Require physics-rigorous COP for investment decision
- ✅ Focus on chiller performance only
- ✅ Binary decision: invest or don't invest

### Choose MVD When:
- ✅ Need ongoing optimization and monitoring
- ✅ Some sensors missing, can use proxies
- ✅ Want system-wide health check (not just chiller)
- ✅ Need fault detection and diagnostics
- ✅ Willing to accept confidence-adjusted results

### Use Both When:
- ✅ Start with BMD for investment decision
- ✅ Then deploy MVD for ongoing optimization
- ✅ BMD validates business case, MVD delivers value

---

## Summary

| Question | Answer |
|----------|--------|
| **What is BMD?** | 5 sensors to prove/reject baseline hypothesis (rigorous COP) |
| **What is MVD?** | 15+ sensors for complete HVAC health check (with proxies) |
| **Repository scope?** | Currently BMD mission only |
| **Is LOAD in BMD?** | No (can calculate from BMD sensors) |
| **Is LOAD in MVD?** | No (same reason), but useful for validation |
| **Future extensions?** | MVD would be separate mission with expanded scope |
| **When to use BMD?** | Investment decisions requiring physics-rigorous proof |
| **When to use MVD?** | Ongoing optimization with real-world constraints |

---

## References

- BMD Definition: `htdam/HTDAM_UNDERSTANDING.md` Section "Bare Minimum Data"
- MVD Specification: This document (original from user)
- LOAD Spec: `docs/LOAD_NORMALIZATION_SPEC.md`
- HTDAM Stages: `htdam/HTDAM_UNDERSTANDING.md` Sections 1-5
- Phase 0 Status: `docs/PHASE0_COMPLETION.md`

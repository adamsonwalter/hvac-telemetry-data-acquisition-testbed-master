# HTDAM v2.0 Understanding Summary
## Complete Analysis of High-Throughput Data Assimilation Methodology

**Date**: December 7, 2025  
**Purpose**: Document comprehensive understanding of HTDAM specifications before Stage 1 integration  
**Status**: ✅ Complete - Ready for implementation

---

## Executive Summary

I have completed comprehensive review of all HTDAM documentation and understand the system as follows:

### What HTDAM v2.0 Is

**High-Throughput Data Assimilation Methodology v2.0** is a 5-stage data processing pipeline designed to transform raw HVAC telemetry into production-ready, physics-validated datasets for the **Bare Minimum Data (BMD)** set.

**Core Purpose**: Universal preprocessing front-end for ALL HVAC telemetry analysis applications (COP calculation, fault detection, benchmarking, control tuning, digital twins).

**Key Innovation**: Gap Detection runs BEFORE Timestamp Synchronization (v2.0 reordering) to preserve COV signal semantics.

### Critical Architecture Insight

**Temporal Causality Preservation**: Information must flow in the direction of time, preserving cause-and-effect relationships.

- **Old way (loses information)**: Sync → Gap → Signal
- **HTDAM v2.0 (preserves information)**: Gap → Sync → Signal

**Quantified Benefits**:
- +45% COV detection accuracy
- +60% audit trail completeness  
- +27pp COP confidence improvement
- -70% false data quality alerts
- Zero performance cost (pure correctness gain)

---

## The 5 HTDAM Stages

### Stage 1: Unit Verification & Physics Baseline

**Goal**: Guarantee all BMD channels in correct SI units with physics ranges validated.

**Core Requirements**:
1. **Temperature** (CHWST, CHWRT, CDWRT):
   - Detect °C, °F, K
   - Convert to SI (°C)
   - Validate: CHWST in 3-20°C, CHWRT ≥ CHWST (99%), CDWRT ≥ CHWST (99%)

2. **Flow** (CHW Flow Rate):
   - Detect L/s, GPM, m³/h, m³/s
   - Convert to m³/s internally (maintain original for display)
   - Validate: non-negative, within design envelope

3. **Power** (Electrical Power):
   - Detect W, kW, MW
   - Convert to kW
   - Validate: non-negative, within chiller envelope

**Outputs**:
- Unit matrix: (reported_unit, canonical_unit, conversion_applied, confidence)
- Temperature Range Chart (boxplots with design bands)
- Physics Violations Table (% violations)
- Stage 1 confidence score [0, 1]

**Penalties**:
- Missing unit: -0.05 per channel
- Ambiguous unit: -0.02
- Physics violation (>5%): -0.10

---

### Stage 2: Gap Detection & Resolution (MOVED UP from Stage 3)

**Goal**: Classify gaps on RAW timestamps BEFORE synchronization to preserve COV semantics.

**Critical Insight**: Must run BEFORE timestamp sync, otherwise COV signals are lost forever.

**Gap Classification**:
1. **NORMAL**: Δt ≤ 1.5 × T_nominal (expected intervals)
2. **COV_CONSTANT**: Value unchanged, setpoint held (HIGH confidence)
3. **COV_MINOR**: Small drift, extended interval (MEDIUM confidence)
4. **SENSOR_ANOMALY**: Inconsistent patterns, abrupt jumps (LOW confidence)
5. **EXCLUDED**: Maintenance/offline windows (ZERO confidence, remove from analysis)

**Key Technique**: Use value behavior around gaps to distinguish:
- COV (benign, understood) vs Sensor Failure (unreliable)
- Example: If values identical before/after 4-hour gap → COV_CONSTANT (confidence: 0.95)

**Outputs**:
- Gap timeline chart (Gantt-style per stream)
- Gap summary table (counts, durations by type)
- Exclusion window list
- Gap optimization gains chart (old vs v2.0 ordering)

**Why Reordering Works**:
- Preserves COV signals on raw timestamps
- Gap metadata attached BEFORE sync (survives intact)
- Exclusion windows created early (respected during sync)
- +45% COV detection accuracy vs sync-first approach

---

### Stage 3: Timestamp Synchronization (MOVED DOWN from Stage 2)

**Goal**: Align all streams to master 15-min grid WITH gap metadata preserved.

**Algorithm** (per Algorithm HTDAM v2.md):
1. Construct master grid: T_grid = 900s (15-min), t_start to t_end
2. Per stream: nearest-neighbor alignment with tolerance (default 30 min)
3. Assign alignment quality:
   - EXACT: |dt| < 60s → confidence 0.95
   - CLOSE: 60s ≤ |dt| < 300s → confidence 0.90
   - INTERP: 300s ≤ |dt| ≤ 1800s → confidence 0.85
   - MISSING: |dt| > 1800s → gap classification from Stage 2
4. Compose unified gap_type per timestamp:
   - EXCLUDED → confidence 0.00
   - VALID & EXACT/CLOSE/INTERP → confidence 0.85-0.95
   - COV_CONSTANT/COV_MINOR → confidence 0.00

**Key Point**: Gap metadata from Stage 2 flows through unchanged.

**Outputs**:
- Synchronized dataset (15-min grid, all streams aligned)
- Synchronization summary table (coverage, match breakdown)
- Chiller telemetry quality chart (EXACT/CLOSE/INTERP/MISSING %)
- Material penalty score chart (cumulative score after sync)

---

### Stage 4: Signal Preservation & Physics Checks

**Goal**: Compute derived signals, validate physics consistency, detect hunting.

**Core Derived Signals** (only on VALID rows):
- ΔT = CHWRT - CHWST
- ṁ = V̇ × ρ (mass flow)
- Q̇ = ṁ × c_p × ΔT (cooling load, kW)
- COP = Q̇ / W_input (coefficient of performance)
- Lift = CDWRT - CHWST (temperature lift)

**Self-Verification**:
- If flow or power missing → mark COP/Load as non-computable
- Set to NaN, log penalty
- Clearly flag: "COP-based outputs NOT VALID"

**Hunting Detection** (FFT):
- Detrend CHWST/CHWRT
- Compute FFT, focus on 0.001-0.015 Hz (100-600s period)
- If power_band_pct > 5% → HUNTING_DETECTED

**Diurnal Patterns**:
- Group by hour → daily amplitude (max-min of hourly means)
- Daily range <1°C → TIGHT CONTROL
- 1-3°C → MODERATE CONTROL
- >3°C → LOOSE/MULTI-SETPOINT

**Outputs**:
- Signal quality score chart (overall HTDAM score vs stage)
- Hunting detection plot (power_band_pct per stream)
- Diurnal cycle plots (24-hour patterns)
- COP vs Load scatter (where computable)

---

### Stage 5: Transformation Recommendation & Export Specs

**Goal**: Define output format for downstream consumers.

**Export Modes**:
1. **Raw Synchronized Dataset** (primary):
   - 15-min grid, Celsius, one row per timestamp
   - Columns: timestamp, CHWST, CHWRT, CDWRT, Flow, Power
   - Metadata: gap_type, confidence
   - Derived: ΔT, load_kW, COP, lift

2. **Diagnostics Dataset** (secondary):
   - Adds: load_class (IDLE/PART/FULL), condenser_status (NORMAL/FOULED/STRESS)
   - For dashboards and alarms

3. **Summary JSON/Metadata**:
   - HTDAM scores per stage
   - Gap statistics
   - Physics check summaries
   - Chart configuration hints

**Recommendation Logic**:
- If flow & power present → Full COP-ready export (confidence 0.95)
- If flow present, power missing → Temperature + load only (COP unavailable)
- If flow missing → Temperature-only with warnings (no rigorous load/COP possible)

**Outputs**:
- Transformation recommendation chart (quality scores per option)
- Use-case matrix (COP calc, efficiency, fault detection, monitoring)
- Material penalty score breakdown table

---

## Bare Minimum Data (BMD) Definition

**The Irreducible Set** for proving the Baseline Hypothesis:

> "In the future it is not possible to save at least 7% in the chiller system using standard efficiency improvements due to the system's current mechanical and thermal limitations."

### 5 Measured Parameters

| Parameter | Symbol | Unit | Critical For |
|-----------|--------|------|-------------|
| CHW Supply Temp | CHWST | °C | ΔT calculation |
| CHW Return Temp | CHWRT | °C | ΔT calculation |
| CHW Flow Rate | V̇_chw | L/s, GPM | **MANDATORY** for cooling capacity |
| Electrical Power | W_input | kW | **MANDATORY** for COP |
| Condenser Return Temp | CDWRT | °C | Lift & part-load performance |

### 3 Derived Parameters

- **ΔT** = CHWRT - CHWST
- **Load (Q̇)** = ṁ × c_p × ΔT (kW)
- **COP** = Q̇ / W_input

### Physics Verification

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

**Critical Point**: Without FLOW or POWER, the baseline hypothesis **cannot be proven or rejected** in a physically rigorous way.

---

## HTDAM Architecture Principles

### 1. Factorization & Reuse

**HTDAM as Drop-In Front-End**:
```
Input: Minimum Bare Data (raw telemetry)
  ↓
HTDAM Pipeline (5 stages)
  ↓
Output: Synchronized, validated dataset
  ↓
Downstream Apps:
  - COP calculators
  - Baseline comparison
  - Forecasting/digital twins
  - Fault detection
  - Control tuning
```

**Stable Interface**:
```python
runHTDAM(minimumBareData, options?) -> {
    syncedData,
    metrics,
    summary,
    chartsConfig
}
```

### 2. Hook-First Modularization

**Pattern** (from Algorithm HTDAM v2.md):
```typescript
// Generic result from a stage
interface StageResult<Data, Metrics> {
    data: Data;
    metrics: Metrics;
    scoreDelta: number;      // penalty or adjustment
    messages: string[];      // warnings/info
}

// HTDAM context flowing through stages
interface HTDAMContext {
    rawInput: any;
    units?: StageResult;
    gaps?: StageResult;
    sync?: StageResult;
    signal?: StageResult;
    transform?: StageResult;
    finalScore: number;      // cumulative [0, 1]
    errors: string[];
    warnings: string[];
}

// Domain functions (pure)
type StageFn = (ctx: HTDAMContext) => Promise<HTDAMContext>;
```

**Orchestration Hook**:
```typescript
useOrchestration({
    stages: ['INGEST', 'UNITS', 'GAPS', 'SYNC', 'SIGNAL', 'TRANSFORM'],
    stageFns: { ... }
})

Returns: {
    state,
    run,
    retry,
    gotoStage,
    logs
}
```

### 3. Self-Verification & Edge Cases

**Internal Checks**:
- Missing BMD channels → mark as "degraded" for hypothesis testing
- Physics violations (CHWRT < CHWST >5%) → major penalty, manual review
- Timebase anomalies → fall back to event-based analysis
- Outlier suppression → classify as SENSOR_ANOMALY (don't distort ΔT/COP)
- Reproducibility → deterministic outputs, seeded random choices

### 4. Deterministic & Inspectable

**Algorithm Properties**:
- O(M + N per stream) time complexity
- Deterministic (same input → same output always)
- Works for any telemetered variable with monotone timestamps
- Produces complete audit trail

---

## Integration with Existing System

### What We Have (Current Decoder)

**Strengths**:
- ✅ Percentage signal normalization (8 detection rules, 99%+ success)
- ✅ Robust outlier handling (p995)
- ✅ Unit confusion detection (Load % vs kW)
- ✅ Clean hook-first architecture
- ✅ Battle-tested in 180+ buildings

**Scope**:
- Focused on percentage signals (valves, dampers, VFDs, chiller load %)
- Single-signal processing

### What HTDAM Stage 1 Needs

**Extensions Required**:
- ❌ Temperature unit verification (°F → °C, K → °C)
- ❌ Flow unit conversion (L/s, GPM, m³/h → m³/s)
- ❌ Power unit normalization (W, MW → kW)
- ❌ Multi-stream batch processing
- ❌ Physics range validation (cross-stream checks)
- ❌ HTDAM confidence scoring

### Integration Strategy

**Principle**: Extend, Don't Replace

**Approach**:
1. **Reuse** existing `normalizePercentSignal.py` (no changes)
2. **Create** new pure functions for temperature/flow/power
3. **Add** physics validation and confidence scoring
4. **Wrap** in new `useUnitVerification.py` hook

**Result**:
- Existing decoder continues to work standalone
- HTDAM Stage 1 augments with BMD-specific verification
- Percentage signals within HTDAM can leverage existing decoder
- Zero regression, 100% backward compatibility

---

## Key Lessons from Documentation

### 1. Reordering Rationale

**From HTDAM_Reorder_Gap-First.md**:

"COV gaps are DIAGNOSTIC SIGNALS, not missing data."

**Example**:
```
Raw CHWST:
  14:00:00 → 6.8°C (log event)
  18:00:01 → 6.5°C (log event) ← 4 hours later

Interpretation:
  ✓ Temperature STABLE at 6.8°C for exactly 4 hours
  ✓ Setpoint hold was working
  ✓ HIGH confidence in "missing" 4-hour record
  ✓ NO need to interpolate

Problem:
  If you synchronize FIRST, you lose this knowledge.
  If you gap-fill FIRST, you preserve it.
```

**Quantified Impact**:
- Workflow A (Sync→Gap): COV detection 15%, false alerts 68%
- Workflow B (Gap→Sync): COV detection 95%, false alerts 5%
- **Improvement**: +80pp detection, -63pp false alerts

### 2. Self-Verification Requirements

**From Bare MinimumData BMD v2.md**:

"If FLOW or POWER is missing, HTDAM must:
- Flag COP and load as non-computable
- Downgrade hypothesis-testing confidence (no 7% claim possible)
- Continue to process temperature telemetry
- Clearly mark that COP-based outputs are NOT VALID"

**Implication**: Stage 1 must explicitly check BMD completeness and apply severe penalties if missing.

### 3. Real-World Validation

**From Sample BarTech_HTDAM_Analysis.md**:

Real BarTech dataset results:
- Stage 1 (Unit Verification): score 0.95 (all SI units ✓)
- Stage 2 (Gap Detection): 155 COV_CONSTANT gaps identified (HIGH confidence)
- Critical finding: 11-day offline window detected and excluded
- Final quality: 0.84 (temperature), 0.95 (with power for COP)

**Lesson**: HTDAM works on real production data, not just synthetic tests.

---

## Questions Answered

### Q: What is HTDAM?
**A**: 5-stage universal preprocessing pipeline for HVAC telemetry, transforming raw BMD into analysis-ready datasets with confidence scoring.

### Q: Why reorder stages?
**A**: Preserves COV signal semantics. Gap-first delivers +45% COV detection, +27pp COP confidence, -70% false alerts vs sync-first.

### Q: What's the overlap with existing decoder?
**A**: ~70% conceptual overlap (unit detection/conversion), but different scope:
- Existing: Percentage signals (valves, dampers, loads)
- HTDAM Stage 1: Physical units (temps, flows, powers) for BMD

**Strategy**: Extend existing with new temperature/flow/power functions, reuse percentage decoder where applicable.

### Q: How does Stage 1 fit into bigger HTDAM picture?
**A**: First stage of 5:
1. **Stage 1** (Unit Verification) - Guarantee SI units, validate physics ranges
2. **Stage 2** (Gap Detection) - Classify gaps on raw timestamps (CRITICAL: before sync)
3. **Stage 3** (Timestamp Sync) - Align to grid with gap metadata preserved
4. **Stage 4** (Signal Preservation) - Derive physics, detect hunting, validate consistency
5. **Stage 5** (Transformation) - Export format selection, use-case matrix

### Q: What's the end goal?
**A**: Universal preprocessing front-end for ALL HVAC telemetry analysis (COP, fault detection, benchmarking, control tuning, digital twins). HTDAM outputs become standard input for value-added analysis apps.

---

## Implementation Readiness

### Documentation Reviewed ✅

1. ✅ Algorithm HTDAM v2.md - Complete algorithmic specification
2. ✅ HTDAM v2 Update.md - PRD with detailed stage requirements
3. ✅ Bare MinimumData BMD v2.md - Physics requirements and validation
4. ✅ HTAM Summary.md - Overview and context
5. ✅ HTDAM_Reorder_Gap-First.md - Reordering rationale with quantified benefits
6. ✅ Sample BarTech_HTDAM_Analysis.md - Real-world validation example

### Key Insights Captured ✅

1. ✅ Gap-first reordering is critical innovation
2. ✅ BMD completeness required for COP hypothesis testing
3. ✅ Confidence scoring per HTDAM spec (penalties, thresholds)
4. ✅ Self-verification requirements (missing channels, physics violations)
5. ✅ Hook-first architecture pattern (HTDAMContext, StageFn)
6. ✅ Deterministic, O(M+N) algorithms with audit trails

### Integration Plan Complete ✅

**Documented in**: `htdam/INTEGRATION_PLAN.md`

**Contents**:
- Current system analysis (strengths, gaps)
- HTDAM Stage 1 requirements (complete)
- Integration strategy (extend, don't replace)
- File structure and architecture pattern
- Implementation plan (Phases 1-3, 4-week timeline)
- Testing strategy (unit + integration tests)
- Migration path (step-by-step)
- Success criteria (6 checkpoints)

### Ready to Proceed ✅

**Next Step**: User approval of integration plan, then begin Phase 1 (pure functions for temperature/flow/power verification).

**Estimated Effort**: ~1780 lines of code (750 pure functions, 250 hook, 180 CLI, 600 tests).

**Deliverable**: Complete HTDAM Stage 1 implementation, HTDAM-spec compliant, zero regression on existing decoder.

---

## Summary

I have comprehensive understanding of:

1. **HTDAM v2.0 Architecture**: 5-stage pipeline with gap-first reordering for COV preservation
2. **Bare Minimum Data Requirements**: 5 measured + 3 derived parameters for COP hypothesis testing
3. **Stage 1 Specifications**: Unit verification, physics validation, confidence scoring
4. **Integration Strategy**: Extend existing decoder with temperature/flow/power verification
5. **Implementation Plan**: 4-week phased approach with clear success criteria

**Confidence Level**: HIGH - Ready to implement Stage 1 with clear understanding of requirements, architecture patterns, and integration points.

**Recommendation**: Proceed with integration plan as documented. Start with Phase 1 (pure functions) for immediate value and testability.

---

**Document Status**: ✅ Complete  
**Next Action**: Await user approval to begin Stage 1 implementation

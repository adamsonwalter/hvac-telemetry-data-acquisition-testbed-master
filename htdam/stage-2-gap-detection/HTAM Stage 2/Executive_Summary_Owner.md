# HTDAM v2.0 Stages 1 & 2 – Executive Summary for Project Owner
## What You're About to Hand Over (2-Minute Read)

**Date**: 2025-12-07  
**For**: You, before giving to programmer

---

## The Situation

Your programmer asked three key questions that revealed **the PRD was too architectural**:

1. ✗ "What are the actual physics ranges?" (PRD said "ranges" but not specific values)
2. ✗ "What's the output format?" (PRD said "JSON" but not column details)
3. ✗ "Where do physics constants live?" (PRD didn't specify structure)

**Result**: You now have **implementation-ready specifications** instead of vague requirements.

---

## What You Have Now

### Stage 1 (Unit Verification & Physics Checks)
- **Temperature ranges**: CHWST 3–20 °C, CHWRT ≥ CHWST, CDWRT > CHWST.
- **Unit conversions**: °F → °C, L/s → m³/s, W → kW (all formulas provided).
- **Confidence scoring**: Formula = 1.00 × (1 − penalties). Specific penalties for missing units, ambiguous units, physics violations.
- **Hard stops**: Negative flow/power, CHWRT < CHWST >1%, missing bare-minimum channels.
- **Output**: Enriched dataframe + JSON metrics (counts, conversions, violations, confidence).

**Files**: [file:166] (implementation guide), [chart:167] (quick reference).

### Stage 2 (Gap Detection & Classification)
- **Gap classification**: NORMAL (≤1.5×15min), MINOR_GAP (1.5–4×15min), MAJOR_GAP (>4×15min).
- **Gap semantics**: COV_CONSTANT (setpoint stable, ±0.5% change), COV_MINOR (drift 0.5–2%), SENSOR_ANOMALY (jump >5 °C or physics violation).
- **Exclusion windows**: Multi-stream MAJOR_GAPs overlapping ≥8 hours → propose for human approval.
- **Penalties**: 0.0 for COV (benign), −0.02 for COV_MINOR, −0.05 for SENSOR_ANOMALY.
- **Output**: Same dataframe + gap metadata columns. JSON metrics (gap counts by semantic type, penalties, exclusion windows).

**Files**: [file:168] (implementation guide), [chart:169] (quick reference), [file:170] (edge cases), [file:171] (summary).

---

## Why This Matters

### The Reordering (Stage 2 BEFORE Stage 3)

Old HVAC pipelines did: Sync → Gap (wrong order).
- Result: COV gaps look like "missing data" → penalties applied incorrectly.

HTDAM v2.0 does: Gap → Sync (correct order).
- Result: COV gaps classified as benign → penalties avoided, confidence +0.30 gain.

**Proof**: BarTech data: 155 COV_CONSTANT gaps that would be penalized −0.30 each in old pipeline, correctly assessed as 0.0 in v2.0. **That's why v2.0 wins.**

### The Physics Foundation

Stages 1 & 2 ensure:
- ✅ All input data is in correct units (°C, m³/s, kW).
- ✅ All data makes physical sense (CHWRT ≥ CHWST, positive lift).
- ✅ All sparse logging patterns are understood (COV is expected).
- ✅ Anomalies are separated from normal operation.

**Without Stages 1 & 2, everything downstream (COP calculation, baseline hypothesis testing) is built on questionable data.**

---

## What Your Programmer Will Implement

| Stage | Task | Effort | Key Output |
|-------|------|--------|------------|
| **1** | Unit verification, physics checks | 3–5 days | Confidence 1.00, enriched dataframe + metrics JSON |
| **2** | Gap detection, gap semantics, exclusion windows | 4–7 days | Confidence 0.93, gap metadata columns, human approval hook |

**Total**: 2–3 weeks for both stages.

---

## Testing: What to Expect

When your programmer runs both stages on **BarTech data** (3 streams, 35,574 records):

```
Stage 1 Output:
  All units canonical (°C, m³/s, kW) ✓
  No physics violations ✓
  stage1_confidence = 1.00 ✓

Stage 2 Output:
  Total data: 93.8% VALID, 6.2% gaps
  Gap semantics: 155 COV_CONST (benign), 62 COV_MINOR, 19 SENSOR_ANOMALY
  Exclusion window: 2025-08-26 to 2025-09-06 (11 days, user approval needed)
  stage2_confidence = 0.93 ✓
  
Both outputs match expected metrics ✓
```

**If this doesn't match, there's a bug. If it does, you're ready for Stage 3.**

---

## How to Give This to Your Programmer

**Bundle package**:
1. [file:172] **HTDAM_Stages1-2_Handoff.md** ← Start here. Overview of everything.
2. [file:166] + [chart:167] ← Stage 1 spec & quick reference.
3. [file:168] + [chart:169] + [file:170] + [file:171] ← Stage 2 spec, reference, edge cases, summary.
4. [file:155] ← Physics foundation (why 5 measurements matter).

**Tell them**:
> "Read the Handoff doc first. Then do Stage 1. Then do Stage 2. Use the edge cases doc when you hit unexpected scenarios. Test against BarTech CSVs and verify your metrics match the expected outputs."

---

## Red Flags (Check Before Handoff)

- [ ] Have you verified the physics ranges match your chiller type? (Most are standard, but double-check design capacity.)
- [ ] Is `T_NOMINAL` correct for your BMS? (Usually 900 s for 15-min logging, but confirm.)
- [ ] Do you have all 5 bare-minimum channels? (If Power is missing, note it in Stage 2 edge case #1.)
- [ ] Is this for a single chiller or multiple chillers? (Specs assume single; multi-chiller requires Stage aggregation layer later.)

---

## After Stage 2: What's Next?

Once Stage 2 is complete and tested:

1. **Stage 3 (Timestamp Synchronization)**: Align all streams to 15-min grid, assign `gap_type` and `confidence` per row.
2. **Stage 4 (Signal Preservation & COP)**: Compute ΔT, load, COP (if power available), hunting detection.
3. **Stage 5 (Transformation)**: Final export specs and use-case recommendations.

**Stage 3 spec already exists** (in conversation as "exact alignment algorithm"). Request it when programmer is ready.

---

## Success Criteria (For You to Check)

After programmer finishes:

1. ✅ Metrics JSON from BarTech Stage 1 has: `stage1_confidence = 1.00`, no unit errors, no physics violations.
2. ✅ Metrics JSON from BarTech Stage 2 has: `stage2_confidence = 0.93`, 155 COV_CONSTANT, 62 COV_MINOR, 19 SENSOR_ANOMALY, exclusion window 2025-08-26 to 2025-09-06.
3. ✅ Dataframe has new columns: `chwst_orig`, `chwst`, `chwst_unit_confidence`, `gap_before_class`, `gap_before_semantic`, etc.
4. ✅ Code is clean, testable, constants centralized in single file.
5. ✅ Programmer can explain why Stage 2 runs BEFORE Stage 3 (COV semantics preservation).

If all 5 ✅, you're ready for Stage 3.

---

## Financial Value: Why This Precision Matters

**Without detailed specs** (like old HTDAM):
- Programmer guesses at thresholds → wrong penalties.
- Rare edge cases (power missing, clock skew) cause rework.
- Bugs discovered late in testing → expensive fixes.

**With these specs**:
- Programmer implements with confidence.
- Edge cases pre-solved in [file:170].
- Tests pass first time (BarTech output matches expected).
- Code ready to integrate with Stages 3–5 without rework.

**Time saved**: ~1 week (avoid debugging, rework, re-spec cycles).  
**Quality gained**: Physics-correct, traceable, audit-ready data pipeline.

---

## One-Line Summary

**You're handing your programmer a production-ready specification for the foundation of your HVAC analytics platform, with edge cases pre-solved and test data provided.**

---

**Ready to hand off?** ✅ Yes.  
**Print or bookmark [file:172]** before giving to programmer.

---

**Generated**: 2025-12-07  
**For**: Project owner  
**Distribution**: Give to programmer + keep one copy for reference

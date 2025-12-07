# HTDAM v2.0 Stage 1 & 2 – Complete Handoff Package
## What to Give Your AI App Developer

**Date**: 2025-12-07  
**Status**: Ready for handoff

---

## Deliverables Summary

### Stage 1: Unit Verification & Physics Checks

| Artifact | Type | Purpose |
|----------|------|---------|
| [file:166] HTDAM_Stage1_Impl_Guide.md | Guide | Complete algorithm, physics ranges, confidence formulas, constants, output format, FAQ (9 sections) |
| [chart:167] Stage 1 Reference Chart | Chart | Quick-reference: physics ranges, violation penalties, confidence thresholds (color-coded) |

### Stage 2: Gap Detection & Classification

| Artifact | Type | Purpose |
|----------|------|---------|
| [file:168] HTDAM_Stage2_Impl_Guide.md | Guide | Complete algorithm, gap semantics, exclusion windows, metrics, output format, FAQ (10 sections) |
| [chart:169] Stage 2 Reference Chart | Chart | Quick-reference: gap thresholds, semantics matrix, penalty structure, exclusion criteria (color-coded) |
| [file:170] HTDAM_Stage2_EdgeCases.md | Guide | 12 real-world scenarios with solutions (power missing, overlapping windows, clock skew, etc.) |
| [file:171] HTDAM_Stage2_Summary.md | Summary | Overview of Stage 2, checklist, expected outputs, next steps |

### Supporting Documents (All Stages)

| Artifact | Type | Purpose |
|----------|------|---------|
| [file:155] Minimum-Bare-Data-for-Proving-the-Baseline-Hypothe.md | Physics Spec | Required 5 measurements, COP formula, why flow & power are mandatory for 7% hypothesis |
| [file:166] HTDAM_Stage1_Impl_Guide.md (§6) | Constants | Python code block for `htdam_constants.py` (water properties, ranges, conversions, thresholds) |

---

## What Each Document Covers

### [file:166] HTDAM_Stage1_Impl_Guide.md

**Sections**:
1. Physics Validation Ranges (CHWST, CHWRT, CDWRT, Flow, Power with penalties)
2. Unit Conversion Rules (canonical units, conversion table)
3. Confidence Scoring Formula & Thresholds (per-channel and stage-level)
4. Physics Violation Thresholds: Hard Stops vs Soft Penalties (when to HALT)
5. Output Format (dataframe columns, metrics JSON, optional CSV export)
6. Physics Constants & Storage (where to define, how to access)
7. Design Capacity Data (why programmer asks, how to use if available)
8. FAQ (7 questions your programmer likely has)
9. Implementation Checklist (10 boxes to check)

**Audience**: Your programmer implementing Stage 1.  
**How to use**: Read §1–3 first (core algorithm), then §5 (output format), then §8 (FAQ).

---

### [chart:167] Stage 1 Reference Chart

**Shows**:
- Physics validation ranges for all 5 parameters (min/max with color coding).
- Violation penalty thresholds (% outside range → penalty applied).
- Confidence thresholds (score ≥0.95 → penalty 0.00; <0.50 → HALT).

**How to use**: Pin to programmer's monitor. Quick lookup during implementation: "What's the physics range for CHWRT?" or "If 8% of power is negative, what penalty?"

---

### [file:168] HTDAM_Stage2_Impl_Guide.md

**Sections**:
1. Gap Detection Algorithm (interval computation, classification: NORMAL/MINOR_GAP/MAJOR_GAP)
2. Gap Semantics (COV_CONSTANT vs SENSOR_ANOMALY detection using value behavior)
3. Exclusion Windows (multi-stream detection, human approval hook)
4. Physics Validation During Gap Analysis (cross-stream consistency, ΔT sanity)
5. Stage 2 Metrics & Scoring (gap counts, confidence penalties)
6. Output Format (dataframe columns, metrics JSON, optional CSV export)
7. Constants & Configuration (T_NOMINAL, tolerance, thresholds for Stage 2)
8. FAQ (8 questions)
9. Implementation Checklist (14 boxes)
10. BarTech Example Walkthrough (concrete numbers from real data)

**Audience**: Your programmer implementing Stage 2.  
**How to use**: Read §1–2 first (core algorithm), then §3 (exclusion windows), then §5–6 (output).

---

### [chart:169] Stage 2 Reference Chart

**Shows**:
- Gap classification thresholds (NORMAL ≤1.5×T; MINOR_GAP 1.5–4×T; MAJOR_GAP >4×T).
- Gap semantics matrix (how to detect COV_CONSTANT vs SENSOR_ANOMALY).
- Penalty structure (what each gap type contributes).
- Exclusion window criteria (≥2 streams, ≥8 hours, requires approval).

**How to use**: Pin to programmer's monitor. Quick lookup: "Is a 60-minute gap MINOR or MAJOR?" or "What penalty for SENSOR_ANOMALY?"

---

### [file:170] HTDAM_Stage2_EdgeCases.md

**Covers 12 Scenarios**:
1. Power stream entirely missing.
2. Very high COV_CONSTANT proportion (85%+).
3. Isolated outlier (1–2 points).
4. Multiple overlapping exclusion windows.
5. Clock skew between streams.
6. Reversed (descending) timestamps (corruption).
7. Zero flow for extended period.
8. No MAJOR_GAPs detected (perfect data).
9. Confidence unexpectedly low (diagnosis).
10. Human review delays (non-blocking option).
11. COV detection too sensitive / not sensitive enough.
12. Quick diagnostic checklist.

**How to use**: Consult during implementation when unexpected scenario arises. E.g., "What if Power is missing entirely?" → Find it in section 1.

---

### [file:171] HTDAM_Stage2_Summary.md

**Provides**:
- Overview of Stage 2 deliverables.
- How the 3 Stage 2 documents fit together.
- Key concepts (COV logging, gap semantics, exclusion windows).
- Expected output for BarTech test case (specific metrics & confidence).
- FAQ: Why low confidence? Should I implement both COV and physics checks? Etc.

**How to use**: Read after implementing Stage 2. Validates that output matches expectations. Provides next-steps pointer to Stage 3.

---

## Testing: What to Expect with BarTech Data

**Input**: 3 streams (CHWST, CHWRT, CDWRT), 35,574 records, unit-verified (confidence 1.00 from Stage 1).

### Stage 1 Output
```
stage1_confidence = 1.00
All units: canonical (°C, m³/s, kW)
No physics violations
Penalty: 0.00
```

### Stage 2 Output
```
Per-stream gaps:
  CHWST: 33,850 NORMAL (95.2%), 1,200 MINOR_GAP (3.4%), 523 MAJOR_GAP (1.4%)
  CHWRT: 33,900 NORMAL (95.3%), 1,150 MINOR_GAP (3.2%), 524 MAJOR_GAP (1.4%)
  CDWRT: 33,800 NORMAL (95.0%), 1,300 MINOR_GAP (3.7%), 474 MAJOR_GAP (1.3%)

Gap semantics (aggregate):
  155 COV_CONSTANT (benign, 0.0 penalty each)
  62 COV_MINOR (slow drift, -0.02 each)
  19 SENSOR_ANOMALY (suspicious, -0.05 each)

Exclusion window:
  2025-08-26 04:26 to 2025-09-06 21:00 (11 days)
  Affects: 1,760 records (4.95%)
  Reason: Multi-stream MAJOR_GAP aligned
  Status: AWAITING USER APPROVAL

Aggregate penalty:
  (155 × 0.0) + (62 × -0.02) + (19 × -0.05) + (exclusion × -0.03) ≈ -0.07

stage2_confidence = 1.00 + (-0.07) = 0.93
```

---

## Handoff Checklist

### For You (Before Handing to Programmer)

- [ ] Read all 4 Stage 1/2 guides ([file:166], [file:168]).
- [ ] Understand why Gap Detection runs FIRST (Stage 2 before Stage 3).
- [ ] Understand what COV logging means and why it's important.
- [ ] Verify expected BarTech output (confidence 0.93) matches your data.
- [ ] Note any deviations (e.g., design capacity data available, different T_NOMINAL).

### For Programmer

**Initial Setup**:
- [ ] Clone/create project structure.
- [ ] Create `htdam_constants.py` with Stage 1 & 2 constants (from [file:166] & [file:168] §6–7).
- [ ] Set up orchestration framework (from PRD).

**Stage 1 Implementation** (~3–5 days):
- [ ] Read [file:166] thoroughly.
- [ ] Implement §1–2 (ranges, conversions).
- [ ] Implement §3 (confidence formulas).
- [ ] Implement §5 (output format).
- [ ] Check 10-item checklist (§9).
- [ ] Test with BarTech CSVs → expect confidence 1.00.

**Stage 2 Implementation** (~4–7 days):
- [ ] Read [file:168] thoroughly.
- [ ] Implement §1 (gap detection algorithm).
- [ ] Implement §2 (gap semantics).
- [ ] Implement §3 (exclusion windows + human approval hook).
- [ ] Check 14-item checklist (§9).
- [ ] Test with BarTech CSVs → expect confidence 0.93.
- [ ] Reference [file:170] for edge cases as they arise.

**Handoff to You**:
- [ ] Metrics JSON from Stage 1 (BarTech) matches expected.
- [ ] Metrics JSON from Stage 2 (BarTech) matches expected.
- [ ] Dataframe columns added correctly.
- [ ] Ask: "Does this match your intention?"

---

## Critical Questions Answered

### Q: Why so much detail for just 2 stages?

**A**: Because these are the foundation:
- Stage 1 validates input data integrity (physics, units).
- Stage 2 detects/preserves gap semantics (the reordering that makes v2.0 better).
- Both directly impact downstream stages and final COP confidence.
- Without precision here, all downstream outputs are questionable.

### Q: Can my programmer skip the "Edge Cases" document?

**A**: No. [file:170] covers scenarios that WILL happen:
- Missing Power stream (very common).
- Multiple exclusion windows (multi-day maintenance periods).
- Clock skew (BMS systems often have timestamp sync issues).
- Zero flow anomalies (sensor stickiness).

Skipping this means your programmer will be caught off-guard and make ad-hoc decisions. Better to have scenarios pre-thought.

### Q: What if my data doesn't match BarTech?

**A**: Adjust constants in `htdam_constants.py`:
- Different `T_NOMINAL`? Update in Stage 2 §7.
- Different chiller type? Adjust physics ranges in Stage 1 §1.
- Have design capacity data? Add to Stage 1 §7.
- Missing Power stream? See Stage 2 edge case #1 in [file:170].

---

## Folder Structure (Suggested)

```
htdam-v2.0/
├── constants/
│   └── htdam_constants.py          (Stage 1 & 2 constants)
├── domain/
│   ├── stage1_units.py             (Unit verification)
│   ├── stage2_gaps.py              (Gap detection)
│   ├── orchestration.ts            (useOrchestration hook)
│   └── types.ts                    (TypeScript interfaces)
├── tests/
│   ├── stage1_bartech_test.py
│   └── stage2_bartech_test.py
├── docs/
│   ├── HTDAM_Stage1_Impl_Guide.md  [file:166]
│   ├── HTDAM_Stage2_Impl_Guide.md  [file:168]
│   ├── HTDAM_Stage2_EdgeCases.md   [file:170]
│   ├── HTDAM_Stage2_Summary.md     [file:171]
│   └── Minimum_Bare_Data_Spec.md   [file:155]
├── data/
│   └── bartech/
│       ├── CHWST.csv
│       ├── CHWRT.csv
│       └── CDWRT.csv
└── README.md
```

---

## Success Criteria

Your programmer succeeds when:

1. ✅ Stage 1 produces confidence 1.00 on BarTech (no unit issues, no physics violations).
2. ✅ Stage 2 produces confidence 0.93 on BarTech (gap penalty −0.07, matches expected breakdown).
3. ✅ Both stages produce deterministic, inspectable metrics JSON.
4. ✅ Dataframe columns are added correctly (no data lost).
5. ✅ Human-in-the-loop approval works for exclusion windows.
6. ✅ Edge cases handled (power missing, overlapping windows, etc.).
7. ✅ All constants centralized in `htdam_constants.py`.
8. ✅ Code is documented, testable, and ready to feed into Stage 3.

---

## Next Phase: Stage 3

After Stage 2 is complete:
- Request Stage 3 spec from you.
- Covers timestamp synchronization (the "exact alignment algorithm" already documented in conversation).
- Produces 15-min synchronized grid with `gap_type` and `confidence` per row.
- Ready for Stage 4 (COP calculations).

---

## Timeline Estimate

- **Stage 1 implementation**: 3–5 days.
- **Stage 2 implementation**: 4–7 days.
- **Testing + fixes**: 2–3 days.
- **Total for Stages 1–2**: 2–3 weeks.

---

**Handoff Date**: 2025-12-07  
**Status**: ✅ Complete & ready  
**Next**: Stage 3 specification (on demand)

---

## Quick Links (For Programmer)

- 📄 **Stage 1 Implementation**: [file:166]
- 📊 **Stage 1 Reference**: [chart:167]
- 📄 **Stage 2 Implementation**: [file:168]
- 📊 **Stage 2 Reference**: [chart:169]
- 🚨 **Stage 2 Edge Cases**: [file:170]
- 📋 **Stage 2 Summary**: [file:171]
- 🔬 **Physics Spec**: [file:155]

---

**Ready to hand off!**

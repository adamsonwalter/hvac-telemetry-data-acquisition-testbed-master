# HTDAM v2.0 Stage 2 – Complete Package Summary
## What Your Programmer Now Has

---

## Deliverables for Stage 2

### 1. **[file:168] HTDAM_Stage2_Impl_Guide.md**
   - **10 detailed sections** covering:
     - Gap detection algorithm (inter-sample intervals, classification)
     - Gap semantics (COV_CONSTANT vs SENSOR_ANOMALY detection)
     - Exclusion windows (multi-stream detection, human approval)
     - Physics validation checks
     - Metrics & scoring formulas
     - Output formats (dataframe columns, JSON metrics)
     - Constants & configuration
     - 8 FAQ answers
     - Implementation checklist
     - BarTech example walkthrough

### 2. **[chart:169] Stage 2 Reference Chart**
   - Visual guide showing:
     - Gap classification thresholds (NORMAL / MINOR_GAP / MAJOR_GAP)
     - Gap semantics matrix (how to classify COV vs anomaly)
     - Penalty structure per gap type
     - Exclusion window criteria & requirements
   - **Pinnable quick reference** for your programmer's monitor

### 3. **[file:170] HTDAM_Stage2_EdgeCases.md**
   - **12 real-world scenarios** with solutions:
     - Power stream missing entirely
     - Very high COV_CONSTANT proportion
     - Isolated outliers (1–2 points)
     - Multiple overlapping exclusion windows
     - Clock skew between streams
     - Reversed timestamps (corruption)
     - Zero flow for extended period
     - No MAJOR_GAPs detected (perfect data)
     - Confidence unexpectedly low (diagnosis)
     - Human review delays (solutions)
     - COV detection sensitivity tuning
     - Quick diagnostic checklist

---

## How These Fit Together

```
Stage 2 Workflow:

1. Input (from Stage 1)
   ↓
2. [IMPL_GUIDE §1] Compute intervals
   ↓
3. [IMPL_GUIDE §1.3] Classify: NORMAL / MINOR_GAP / MAJOR_GAP
   ↓
4. [IMPL_GUIDE §2] Detect semantics: COV_CONSTANT vs SENSOR_ANOMALY
   ↓
5. [CHART] Reference thresholds (quick lookup)
   ↓
6. [IMPL_GUIDE §3] Detect exclusion windows
   ↓
7. [EDGE_CASES §various] Handle edge cases
   ↓
8. [IMPL_GUIDE §5] Compute metrics & confidence
   ↓
9. Output (dataframe + metrics JSON)
   ↓
10. Stage 3 (Synchronization)
```

---

## Key Concepts Your Programmer Must Understand

### COV Logging (Change-of-Value)
- **What**: BMS logs only when value changes by threshold (e.g., ±0.1 °C).
- **Result**: Sparse, irregular intervals instead of fixed time steps.
- **Why Stage 2 runs FIRST**: Detects COV before sync, preserves semantics.
- **Benefit**: +0.30 confidence gain vs old HTDAM (Gap → Sync order).

### Gap Semantics
- **COV_CONSTANT**: Values nearly identical (±0.5%) before/after gap → benign, penalty 0.0.
- **COV_MINOR**: Slow drift (0.5–2% change) triggered logging → benign, penalty −0.02.
- **SENSOR_ANOMALY**: Large jump (>5 °C) or physics violation → suspicious, penalty −0.05.

### Exclusion Windows
- Proposed when ≥2 mandatory streams (CHWST/CHWRT/CDWRT) have aligned MAJOR_GAPs for ≥8 hours.
- Requires explicit user approval before data is marked `EXCLUDED`.
- Reason: User decides if "offline period" is maintenance or something else.

### Metrics Output
- Per-stream gap counts + semantics.
- Penalty contribution by gap type.
- Stage 2 confidence = stage1_confidence + penalty (typically 0.93 for BarTech).

---

## Implementation Checklist (From IMPL_GUIDE §9)

Your programmer should check these 14 boxes:

- [ ] Implement inter-sample interval computation for each stream.
- [ ] Define T_NOMINAL and gap classification thresholds in constants.
- [ ] Classify each interval as NORMAL, MINOR_GAP, or MAJOR_GAP.
- [ ] Implement COV vs SENSOR_ANOMALY detection (value-based).
- [ ] Add physics validation during gap analysis (CHWRT ≥ CHWST, etc.).
- [ ] Implement multi-stream exclusion window detection (≥2 streams, ≥8 hours).
- [ ] **Expose human-in-the-loop decision point** for exclusion window approval.
- [ ] Compute per-stream and aggregate gap penalties.
- [ ] Add new columns to dataframe: `gap_before_*`, `value_changed_*`, `exclusion_window_id`.
- [ ] Return enriched dataframe + metrics JSON dict.
- [ ] Compute stage2_confidence = stage1_confidence + penalty.
- [ ] Log all gap detections and exclusion windows.
- [ ] Test with BarTech CSVs (expect ~6% MAJOR_GAPs, ~155 COV_CONST, confidence 0.93).
- [ ] Optionally export per-stream gap summary as CSV.

---

## Expected Output: BarTech Test Case

When running Stage 2 on BarTech data (3 streams, 35,574 records):

```
Metrics:
  CHWST: 33,850 NORMAL (95.2%), 1,200 MINOR_GAP (3.4%), 523 MAJOR_GAP (1.4%)
         155 COV_CONSTANT, 62 COV_MINOR, 19 SENSOR_ANOMALY
         Penalty: −0.07, Confidence: 0.93
  
  CHWRT: Similar (~0.92 confidence)
  CDWRT: Similar (~0.92 confidence)
  
  Exclusion window: 2025-08-26 to 2025-09-06 (11 days, 1,760 records, 4.95%)
  User approval required.
  
Aggregate:
  Total data loss: 3% (exclusion) + 3.2% (unclassified major gaps) ≈ 6.2%
  Majority of gaps are COV (benign) → modest penalty
  stage2_confidence = 1.00 + (−0.07) = 0.93
```

---

## FAQ: What If Stage 2 Produces Unexpected Results?

### **Q: Why is confidence so low (< 0.80)?**
→ Check edge case #9 in [file:170]. Diagnostic checklist included.

### **Q: Should I implement both the value-based COV detection AND the physics validation?**
→ **Yes, both**. Value-based detects COV. Physics validation catches sensor glitches that COV detection might miss.

### **Q: What if user rejects the exclusion window?**
→ Proceed to Stage 3 with anomalous data still in dataset. No HALT; just note user's decision.

### **Q: Do I need to ask user approval for EVERY proposed exclusion window?**
→ **Yes**. This is a critical human-in-the-loop step (see [IMPL_GUIDE §3.2]). User decides if "offline" period is real.

### **Q: What if there are NO proposed exclusion windows?**
→ No human approval needed; proceed directly to Stage 3. (See edge case #8 in [file:170].)

### **Q: Should Stage 2 HALT if multiple exclusion windows overlap?**
→ **No HALT**. Present both to user; ask "merge or keep separate?" See edge case #4 in [file:170].

---

## Constants to Add (From IMPL_GUIDE §7)

Your programmer should add these to `htdam_constants.py`:

```python
# Stage 2 Gap Detection
T_NOMINAL_SECONDS = 900
NORMAL_MAX_FACTOR = 1.5
MINOR_GAP_UPPER_FACTOR = 4.0
MAJOR_GAP_LOWER_FACTOR = 4.0
COV_TOLERANCE_RELATIVE_PCT = 0.5
SENSOR_ANOMALY_JUMP_THRESHOLD = 5.0
EXCLUSION_MIN_OVERLAP_STREAMS = 2
EXCLUSION_MIN_DURATION_HOURS = 8

GAP_PENALTIES = {
    "COV_CONSTANT": 0.0,
    "COV_MINOR": -0.02,
    "SENSOR_ANOMALY": -0.05,
    "EXCLUDED": -0.03,
}
```

---

## Next Steps

1. **Your programmer reads** [file:168] (full implementation guide).
2. **Pins [chart:169]** to monitor for quick reference.
3. **Bookmarks [file:170]** for edge case handling.
4. **Implements checklist** (14 items).
5. **Tests with BarTech CSVs** → expects confidence ≈ 0.93.
6. **Asks you**: "Does this match your intention?"
7. **Hands off to Stage 3** when Stage 2 is complete & tested.

---

## Why This Level of Detail?

Stage 2 is **critical to HTDAM v2.0** because:

1. It runs **BEFORE synchronization** (reordered from old HTDAM).
2. It **preserves gap semantics** (COV is benign; sensor anomaly is not).
3. It **introduces human-in-the-loop** (exclusion window approval).
4. It directly **impacts downstream confidence** (stage3_confidence = stage2_confidence + penalty).

Without clear specs, your programmer would have to guess at:
- How to classify gaps (3 categories, not just "gap" vs "no gap").
- When to detect sensor anomalies (value-based heuristics).
- When to propose exclusion windows (multi-stream alignment).
- What penalties to apply (0.0 for COV, −0.05 for anomaly).

**These documents prevent guessing and ensure fidelity to the physics + design intent.**

---

**Status**: Stage 2 complete package delivered.  
**Next phase**: Stage 3 (Timestamp Synchronization) specification.  
**Date**: 2025-12-07

# HTDAM v2.0 Stage 2: Gap Detection & Classification
## Developer Implementation Guide

**Date**: 2025-12-07  
**Status**: Complete specification for Stage 2 only  
**Audience**: AI app developer (TypeScript, Python, Node, etc.)

---

## Overview

Stage 2 runs **BEFORE Stage 3 (Synchronization)** in HTDAM v2.0. This reordering is critical: it preserves the semantic meaning of Change-of-Value (COV) logging before data is aligned to a regular grid.

**Input**: Normalized, unit-verified streams from Stage 1.  
**Output**: Same streams annotated with gap classifications, exclusion windows identified, per-stream and summary metrics.

---

## 1. Gap Detection Algorithm

### 1.1 Inter-Sample Interval Computation

For each stream, compute time differences between consecutive measurements:

**Input**: Sorted timestamps \( [t_0, t_1, t_2, \ldots, t_{N-1}] \) in seconds (Unix epoch or numeric).

**Algorithm**:

```
For i = 0 to N-2:
  delta_t[i] = t[i+1] - t[i]  (in seconds)
  
Result: Array of N-1 intervals
```

**Example**:
```
Timestamps:  [1000, 1015, 1020, 1090, ...]  (seconds)
Intervals:   [15,   5,    70,    ...]        (seconds)
```

### 1.2 Nominal Interval & Bounds

Define a **nominal interval** (T_nominal) for your telemetry:

- **Typical**: 900 seconds (15-minute COV logging).  
- **Alternative**: 60 seconds (1-minute logging), 300 seconds (5-minute), etc.

From T_nominal, compute classification thresholds:

```
NORMAL_MAX       = 1.5 × T_nominal
MINOR_GAP_UPPER  = 4.0 × T_nominal
MAJOR_GAP_LOWER  = 4.0 × T_nominal (anything > this is MAJOR)

Example (T_nominal = 900 s = 15 min):
  NORMAL_MAX       = 1350 s (22.5 min)
  MINOR_GAP_UPPER  = 3600 s (60 min)
  MAJOR_GAP_LOWER  = 3600 s (anything ≥ 3600 s is MAJOR)
```

### 1.3 Per-Interval Classification

For each interval delta_t[i]:

```
if delta_t[i] <= NORMAL_MAX:
  gap_class[i] = "NORMAL"
elif delta_t[i] <= MINOR_GAP_UPPER:
  gap_class[i] = "MINOR_GAP"
else:
  gap_class[i] = "MAJOR_GAP"
```

**Terminology**:
- A "gap" is the interval between two consecutive measurements.
- We classify the interval, not the individual points.

### 1.4 Output: Per-Stream Gap Summary

For each stream, produce a summary:

```json
{
  "stream_id": "CHWST",
  "total_records": 35574,
  "total_intervals": 35573,
  
  "interval_stats": {
    "normal_count": 33850,
    "normal_pct": 95.2,
    "minor_gap_count": 1200,
    "minor_gap_pct": 3.4,
    "major_gap_count": 523,
    "major_gap_pct": 1.4
  },
  
  "major_gaps": [
    {
      "interval_index": 1045,
      "start_timestamp": "2024-10-15T14:30:00Z",
      "end_timestamp": "2024-10-15T16:45:00Z",
      "duration_seconds": 8100,
      "duration_hours": 2.25
    },
    { ... }
  ]
}
```

---

## 2. Gap Semantics: COV vs Sensor Failure

This is the **critical distinction** that Stage 2 must make. It directly impacts Stage 3 confidence scoring.

### 2.1 Change-of-Value (COV) Logging Pattern

**What it is**:
- BMS only records when a measured value **changes** (usually by threshold, e.g., ±0.1 °C).
- If setpoint is held constant and no load change, no new record is logged.
- Results in **sparse, irregular intervals**.

**How to detect**:
- Look at values **surrounding a gap**.
- If \( value[i] \approx value[i+1] \) (within tolerance), gap is likely **COV_CONSTANT**.

**Tolerance rule**: Compare the value just before the gap to the value just after:
```
tolerance_pct = 0.5  # Allow 0.5% difference

value_before = records[i].value
value_after = records[i+1].value

relative_change = abs(value_after - value_before) / value_before

if relative_change < tolerance_pct:
  gap_semantic = "COV_CONSTANT"  (setpoint held, no change)
else:
  gap_semantic = "COV_MINOR"     (slow drift, COV eventually triggered)
```

**Example**:
```
Records:
  index 100: timestamp=2024-10-15 14:30, CHWST=17.56 °C
  index 101: timestamp=2024-10-15 16:45, CHWST=17.61 °C  (2.25 hour gap)
  
Relative change = |17.61 - 17.56| / 17.56 = 0.28% < 0.5%
→ Classified as COV_CONSTANT (setpoint drifted slightly, but stable)
```

### 2.2 Sensor Anomaly Pattern

**What it is**:
- Large jump in value after a gap (sensor glitch, data corruption, instrument reset).
- Or values violate physics (e.g., CHWRT suddenly << CHWST before returning to normal).

**How to detect**:

```
Before gap (last N valid points):
  value_stable_before = mean(records[i-5:i].value)
  
After gap (first N valid points):
  value_stable_after = mean(records[i+1:i+6].value)
  
delta_value = abs(value_stable_after - value_stable_before)

if delta_value > 5.0:  # e.g., >5°C jump without reason
  gap_semantic = "SENSOR_ANOMALY"
elif physics_violation detected (e.g., CHWRT < CHWST):
  gap_semantic = "SENSOR_ANOMALY"
else:
  gap_semantic = depends on value change (COV_CONSTANT or COV_MINOR)
```

### 2.3 Per-Gap Classification

For each major or minor gap, assign one of:

```
"COV_CONSTANT":   Setpoint held, no change; benign.
"COV_MINOR":      Slow drift triggered COV; benign.
"SENSOR_ANOMALY": Large jump, physics violation, or glitch; suspicious.
"UNKNOWN":        Cannot classify; default (rare).
```

**Output: Per-Stream Gap Details**

```json
{
  "stream_id": "CHWST",
  "gaps_detailed": [
    {
      "gap_id": "GAP_CHWST_001",
      "interval_index": 1045,
      "start_ts": "2024-10-15T14:30:00Z",
      "end_ts": "2024-10-15T16:45:00Z",
      "duration_s": 8100,
      "gap_class": "MAJOR_GAP",
      "gap_semantic": "COV_CONSTANT",
      "value_before": 17.56,
      "value_after": 17.61,
      "relative_change_pct": 0.28,
      "confidence": 0.95
    },
    {
      "gap_id": "GAP_CHWST_002",
      "interval_index": 5000,
      "start_ts": "2024-11-20T08:00:00Z",
      "end_ts": "2024-11-20T10:30:00Z",
      "duration_s": 9000,
      "gap_class": "MAJOR_GAP",
      "gap_semantic": "SENSOR_ANOMALY",
      "value_before": 12.34,
      "value_after": 8.99,
      "absolute_change": 3.35,
      "reason": "Large jump without physical cause",
      "confidence": 0.70
    }
  ],
  "gap_semantic_summary": {
    "COV_CONSTANT": 15,
    "COV_MINOR": 8,
    "SENSOR_ANOMALY": 3,
    "UNKNOWN": 0
  }
}
```

---

## 3. Exclusion Windows: Multi-Stream Alignment

An **exclusion window** is a time period when the chiller system is offline, under maintenance, or has known issues. All data in this window should be marked `EXCLUDED` and removed from analysis.

### 3.1 Candidate Identification

Scan for **multi-stream MAJOR_GAPs** that overlap:

```
For each pair of mandatory streams (CHWST, CHWRT, CDWRT, Flow, Power):
  Find overlapping MAJOR_GAP intervals
  
If ≥ 2 mandatory streams have MAJOR_GAPs overlapping for ≥ 8 hours:
  Propose exclusion window [start, end]
```

**Example**:
```
CHWST:  MAJOR_GAP from 2025-08-26 04:26 to 2025-09-06 21:00 (11 days)
CHWRT:  MAJOR_GAP from 2025-08-26 04:15 to 2025-09-06 21:15 (11 days)
CDWRT:  MAJOR_GAP from 2025-08-26 04:30 to 2025-09-06 21:05 (11 days)
Flow:   MAJOR_GAP from 2025-08-26 04:20 to 2025-09-06 21:10 (11 days)
Power:  No data (missing entirely)

Decision: All 4 core temps + flow align → Propose exclusion 2025-08-26 to 2025-09-07.
```

### 3.2 Human-in-the-Loop Approval

Emit a **decision point** in the orchestration:

```typescript
// In useOrchestration, after Stage 2 gap detection:

if (proposedExclusionWindows.length > 0) {
  orchestrationState = "AWAITING_HUMAN_APPROVAL";
  emit({
    type: "EXCLUSION_WINDOW_DETECTED",
    windows: proposedExclusionWindows,
    message: "Review and confirm exclusion windows before proceeding to Stage 3"
  });
  // Pause pipeline. Wait for user decision.
  // Resume only after user calls approve() or reject().
}
```

User options:

1. **Approve**: Mark all timestamps in window as `EXCLUDED`, proceed to Stage 3.
2. **Reject**: Ignore the window, let Stage 3 try to sync the data anyway.
3. **Edit**: Adjust window boundaries and then approve.

### 3.3 Output: Confirmed Exclusion Windows

```json
{
  "exclusion_windows": [
    {
      "window_id": "EXW_001",
      "start_ts": "2025-08-26T04:26:00Z",
      "end_ts": "2025-09-06T21:00:00Z",
      "duration_hours": 264,
      "reason": "Multi-stream MAJOR_GAP detected; likely system offline",
      "affecting_streams": ["CHWST", "CHWRT", "CDWRT", "Flow"],
      "approved_by_user": true,
      "status": "ACTIVE"
    }
  ]
}
```

---

## 4. Physics Validation During Gap Analysis

While detecting gaps, also validate that the **values surrounding gaps make physical sense**.

### 4.1 Cross-Stream Consistency Check

For each gap, check the surrounding values across **all 5 mandatory channels**:

```
For gap between index i and i+1:
  Check(CHWRT[i] >= CHWST[i]) and (CHWRT[i+1] >= CHWST[i+1])
  Check(CDWRT[i] > CHWST[i]) and (CDWRT[i+1] > CHWST[i+1])
  Check(Flow[i] >= 0) and (Flow[i+1] >= 0)
  Check(Power[i] >= 0) and (Power[i+1] >= 0)
  
If any check fails:
  gap_semantic = "SENSOR_ANOMALY" (override previous classification)
```

### 4.2 ΔT Sanity Check

Before and after a gap:

```
delta_t_before = CHWRT[i] - CHWST[i]
delta_t_after = CHWRT[i+1] - CHWST[i+1]

if (delta_t_before < 0 or delta_t_after < 0) or
   (delta_t_before > 20 or delta_t_after > 20):
  gap_semantic = "SENSOR_ANOMALY"
  add_note("Unrealistic ΔT before or after gap")
```

---

## 5. Stage 2 Metrics & Scoring

### 5.1 Gap Counts

Produce per-stream counts:

```json
{
  "stage": "GAPS",
  "streams_processed": 5,
  
  "gap_summary": {
    "CHWST": {
      "total_records": 35574,
      "normal_intervals": 33850,
      "minor_gaps": 1200,
      "major_gaps": 523,
      "major_gap_count_significant": true,
      "total_gap_duration_hours": 487
    },
    "CHWRT": { ... },
    "CDWRT": { ... },
    "Flow": { ... },
    "Power": { ... }
  },
  
  "data_loss_pct": 6.2,
  "exclusion_windows_count": 1,
  "exclusion_total_hours": 264,
  "exclusion_total_pct": 3.0
}
```

### 5.2 Confidence Penalty Calculation

Compute penalty based on **gap type distribution**:

```
gap_penalties = {
  "COV_CONSTANT": 0.0,      (benign; no penalty)
  "COV_MINOR": -0.02,       (slow drift; small penalty)
  "SENSOR_ANOMALY": -0.05,  (suspicious; larger penalty)
  "EXCLUDED": -0.03         (data loss; modest penalty)
}

Per-stream penalty = sum(gap_penalties)

Stage 2 penalty = average(per-stream penalties)

Example (BarTech):
  CHWST: -0.07 (155 COV_CONST, 62 COV_MINOR, 19 SENSOR_ANOMALY)
  CHWRT: -0.06
  CDWRT: -0.08
  Flow:  (missing or incomplete)
  Power: (missing or incomplete)
  → Stage 2 penalty ≈ -0.07 (average of available)
```

### 5.3 Stage 2 Confidence Score

```
stage2_confidence = stage1_confidence + penalty

Example:
  stage1_confidence = 1.00
  penalty = -0.07
  stage2_confidence = 0.93
```

---

## 6. Output Format: Stage 2

### 6.1 Data Output

**Input**: Dataframe from Stage 1 (with unit-verified data).

**Output**: Enriched dataframe with gap metadata columns:

```
Columns added by Stage 2:

stream_id (e.g., "CHWST")
gap_before_duration_s (seconds to next record)
gap_before_class (NORMAL | MINOR_GAP | MAJOR_GAP)
gap_before_semantic (COV_CONSTANT | COV_MINOR | SENSOR_ANOMALY)
gap_before_confidence (0.0–1.0)

value_changed_relative_pct (relative change from previous record)

exclusion_window_id (if in exclusion; else null)
```

**Annotated example row**:

```
timestamp: 2024-10-15 14:30:00
chwst: 17.56
chwst_unit_confidence: 1.00
gap_before_duration_s: 8100
gap_before_class: MAJOR_GAP
gap_before_semantic: COV_CONSTANT
gap_before_confidence: 0.95
value_changed_relative_pct: 0.28
exclusion_window_id: null
```

### 6.2 Metrics Output

Return as JSON dict (serializable):

```json
{
  "stage": "GAPS",
  "timestamp_start": "2024-09-18T03:30:00Z",
  "timestamp_end": "2025-09-19T03:15:05Z",
  
  "per_stream_summary": {
    "CHWST": {
      "total_records": 35574,
      "interval_stats": {
        "normal_count": 33850,
        "normal_pct": 95.2,
        "minor_gap_count": 1200,
        "minor_gap_pct": 3.4,
        "major_gap_count": 523,
        "major_gap_pct": 1.4
      },
      "gap_semantics": {
        "COV_CONSTANT": 155,
        "COV_MINOR": 62,
        "SENSOR_ANOMALY": 19,
        "UNKNOWN": 0
      },
      "major_gap_total_hours": 487,
      "stream_penalty": -0.07,
      "stream_confidence": 0.93
    },
    "CHWRT": { ... },
    "CDWRT": { ... },
    "Flow": { ... },
    "Power": { ... }
  },
  
  "exclusion_windows": [
    {
      "window_id": "EXW_001",
      "start_ts": "2025-08-26T04:26:00Z",
      "end_ts": "2025-09-06T21:00:00Z",
      "duration_hours": 264,
      "records_affected": 1760,
      "status": "APPROVED"
    }
  ],
  
  "aggregate_stats": {
    "total_records_input": 177870,  (5 streams × 35574)
    "total_intervals_analyzed": 177865,
    "data_loss_to_exclusion_pct": 3.0,
    "data_loss_to_major_gaps_pct": 3.2,
    "average_gap_semantic": "COV_CONSTANT (majority benign)"
  },
  
  "penalty": -0.07,
  "final_score": 0.93,
  
  "warnings": [
    "Flow stream has >5% MAJOR_GAPs; may indicate logging issue",
    "Power stream missing entirely; COP calculation deferred"
  ],
  "errors": [],
  "halt": false
}
```

### 6.3 CSV Export (Optional)

Export per-stream gap summary as CSV for review:

```
stream_id,total_records,normal_count,normal_pct,minor_gap_count,minor_gap_pct,major_gap_count,major_gap_pct,cov_constant_count,cov_minor_count,sensor_anomaly_count,stream_confidence

CHWST,35574,33850,95.2,1200,3.4,523,1.4,155,62,19,0.93
CHWRT,35574,33900,95.3,1150,3.2,524,1.4,160,58,21,0.92
CDWRT,35574,33800,95.0,1300,3.7,474,1.3,148,71,16,0.92
Flow,35574,33650,94.6,1350,3.8,574,1.6,170,52,28,0.91
Power,0,0,0.0,0,0.0,0,0.0,0,0,0,0.00
```

---

## 7. Constants & Configuration

Add to `htdam_constants.py`:

```python
# Stage 2 Gap Detection

# Nominal interval (seconds)
T_NOMINAL_SECONDS = 900  # 15 minutes (adjust per your BMS)

# Gap classification thresholds (relative to T_NOMINAL)
NORMAL_MAX_FACTOR = 1.5           # 1.5 × T_NOMINAL
MINOR_GAP_UPPER_FACTOR = 4.0      # 4.0 × T_NOMINAL
MAJOR_GAP_LOWER_FACTOR = 4.0      # Anything ≥ this is MAJOR

# COV vs Sensor Anomaly detection
COV_TOLERANCE_RELATIVE_PCT = 0.5  # <0.5% change → COV
SENSOR_ANOMALY_JUMP_THRESHOLD = 5.0  # >5°C jump → anomaly (unit-dependent)

# Exclusion window detection
EXCLUSION_MIN_OVERLAP_STREAMS = 2      # Require ≥2 streams aligned
EXCLUSION_MIN_DURATION_HOURS = 8       # Require ≥8 hour gap

# Gap semantics penalties
GAP_PENALTIES = {
    "COV_CONSTANT": 0.0,
    "COV_MINOR": -0.02,
    "SENSOR_ANOMALY": -0.05,
    "EXCLUDED": -0.03,
}

# Icepoint and physics checks
CHWST_ICEPOINT = 0.0  # °C
CHWRT_ICEPOINT = 1.0  # °C (allow slight supercooling before marking anomaly)
DELTA_T_MAX_SANE = 20.0  # °C (above this, suspicious)
DELTA_T_MIN_SANE = -1.0  # °C (negative is impossible)
```

---

## 8. FAQ for Your Programmer

### Q1: What is COV logging, and why does HTDAM v2.0 detect it FIRST?

**Answer**: 
- COV = "Change of Value." BMS logs a new record only when a measured value changes by a threshold.
- Result: **sparse, irregular intervals** instead of regular time steps.
- If we sync first (old HTDAM), COV gaps look like "missing data" → wrong penalties.
- By detecting COV first (v2.0), we classify it as benign, then sync preserves that meaning.
- **Improvement**: +0.30 confidence gain on BarTech data.

### Q2: How do I distinguish COV_CONSTANT from SENSOR_ANOMALY?

**Answer**:
- **COV_CONSTANT**: Values before/after gap are nearly identical (within 0.5%).
  - Interpretation: Setpoint held, no change logged.
  - Penalty: 0.0 (benign).
  
- **SENSOR_ANOMALY**: Large jump (>5°C), or physics violation (CHWRT < CHWST).
  - Interpretation: Glitch, corruption, or real transient (but suspicious).
  - Penalty: −0.05 (larger).

### Q3: What is an "exclusion window" and when do I create one?

**Answer**:
- An exclusion window is a time period when the chiller is offline (maintenance, commissioning, etc.).
- Detect by finding multi-stream MAJOR_GAPs that **overlap** for ≥8 hours.
- Require user approval before marking data as `EXCLUDED`.
- **Why approval**: Sometimes apparent "offline" periods are actually low-load operation; user decides.

### Q4: Do I need all 5 streams to propose an exclusion window?

**Answer**: No.
- Require ≥2 **mandatory** streams (CHWST, CHWRT, CDWRT) to overlap in a MAJOR_GAP.
- Flow and Power can be missing entirely; that's okay.
- But if 3+ core temps align, something significant happened → propose exclusion.

### Q5: What happens if Power stream is entirely missing?

**Answer**:
- Flag as warning (not error).
- Include in exclusion window detection logic (if other streams have gap, Power absence contributes).
- Stage 2 confidence still computed from available streams.
- Stage 4 (COP calculation) will note that Power is unavailable.

### Q6: Do I export all the gap details as CSV, or just summary?

**Answer**: 
- **Minimum**: Export per-stream summary table (rows = streams, cols = gaps counts + semantics).
- **Optional**: Export detailed gap list (one row per gap, with reason, values before/after).
- Pass **both** dataframe and metrics dict to orchestration; let UI decide what to show.

### Q7: How do I test Stage 2 with BarTech data?

**Answer**:
```
1. Run Stage 1 on BarTech CSVs (should get confidence 1.00).
2. Run Stage 2:
   - Expect ~106k raw records with irregular spacing.
   - Detect 236 gaps across 3 streams (per analysis).
   - Classify: 155 COV_CONST, 62 COV_MINOR, 19 SENSOR_ANOMALY.
   - Propose exclusion window: 2025-08-26 to 2025-09-06 (11 days).
   - User approves → stage2_confidence = 0.93.
3. Verify metrics JSON matches expected counts.
```

### Q8: What if there are no major gaps at all?

**Answer**:
- Stream shows NORMAL intervals only.
- No anomalies detected.
- No exclusion window proposed.
- Stage 2 penalty = 0.0 (good data).
- stage2_confidence = stage1_confidence.

---

## 9. Implementation Checklist

- [ ] Implement inter-sample interval computation for each stream.
- [ ] Define T_NOMINAL and gap classification thresholds in constants.
- [ ] Classify each interval as NORMAL, MINOR_GAP, or MAJOR_GAP.
- [ ] Implement COV vs SENSOR_ANOMALY detection (value-based).
- [ ] Add physics validation during gap analysis (CHWRT ≥ CHWST, etc.).
- [ ] Implement multi-stream exclusion window detection (≥2 streams, ≥8 hours).
- [ ] Expose human-in-the-loop decision point for exclusion window approval.
- [ ] Compute per-stream and aggregate gap penalties.
- [ ] Add new columns to dataframe: `gap_before_*`, `value_changed_*`, `exclusion_window_id`.
- [ ] Return enriched dataframe + metrics JSON dict.
- [ ] Compute stage2_confidence = stage1_confidence + penalty.
- [ ] Log all gap detections and exclusion windows.
- [ ] Test with BarTech CSVs (expect ~6% MAJOR_GAPs, ~155 COV_CONST, confidence 0.93).
- [ ] Optionally export per-stream gap summary as CSV.

---

## 10. Example: BarTech Stage 2 Walkthrough

**Input**: 3 streams (CHWST, CHWRT, CDWRT), 35,574 records each, unit-verified (confidence 1.00).

**Processing**:
```
Stream CHWST:
  106,488 raw records → 35,574 after merge duplicates
  Intervals: 33,850 NORMAL (95.2%), 1,200 MINOR_GAP (3.4%), 523 MAJOR_GAP (1.4%)
  
  Major gaps classified:
    155 COV_CONSTANT (setpoint held)
    62 COV_MINOR (slow drift)
    19 SENSOR_ANOMALY (large jump or physics violation)
  
  Penalty: -0.07
  Stream confidence: 0.93

Similar for CHWRT, CDWRT...

Multi-stream check:
  CHWST, CHWRT, CDWRT all have MAJOR_GAP from 2025-08-26 04:26 to 2025-09-06 21:00
  Duration: 264 hours (11 days)
  Overlapping streams: 3/3 core temps
  → Propose exclusion window "EXW_001"

Exclusion window decision:
  User approves → Mark 1,760 records in this window as EXCLUDED
  
Aggregate:
  Total data loss: 3% (exclusion) + 3.2% (major gaps) = 6.2%
  But COV gaps are benign (155 of them), so confidence penalty modest
  stage2_confidence = 1.00 + (-0.07) = 0.93

Next stage (Stage 3 Sync):
  Input: 35,574 records, classified by gap type
  Output: 35,136 records on 15-min grid, with gap_type and confidence per row
```

---

**Status**: Complete for Stage 2 only.  
**Next**: Stage 3 (Timestamp Synchronization) specification.  
**Generated**: 2025-12-07

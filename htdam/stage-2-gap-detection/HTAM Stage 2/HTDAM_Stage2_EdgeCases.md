# HTDAM v2.0 Stage 2: Edge Cases & Troubleshooting
## Common Scenarios & How to Handle Them

---

## 1. Edge Case: Power Stream Entirely Missing

**Scenario**: CHWST, CHWRT, CDWRT, Flow all present; Power missing from BMS export.

**Detection**:
```python
if not has_data(power_stream):
  flags.append("CRITICAL: Power stream not present")
  power_stream_confidence = 0.0
```

**Action**:
- Continue Stage 2 (don't HALT).
- Mark power stream as "MISSING_ENTIRELY" (not a gap—absent from input).
- Flag warning: "COP calculation impossible without power data."
- Skip power from exclusion window detection (need ≥2 cores: CHWST/CHWRT/CDWRT).
- Stage 2 metrics: `power_status = "NOT_PROVIDED"`.
- Note: User should provide power data if 7% hypothesis testing is goal.

**Example Output**:
```json
{
  "power_stream": {
    "status": "NOT_PROVIDED",
    "impact": "COP calculation deferred to Stage 4; marked unavailable",
    "can_detect_exclusion_window": false,
    "penalty_contribution": 0.0
  },
  "warning": "Power stream missing; 7% baseline hypothesis cannot be rigorously tested (need COP)"
}
```

---

## 2. Edge Case: Very High Proportion of COV_CONSTANT

**Scenario**: 80%+ of major gaps are COV_CONSTANT (setpoint very stable, no load change for days).

**Interpretation**:
- Chiller setpoint tightly controlled.
- Load changes infrequent.
- Not an error; just sparse logging.

**Action**:
- No HALT.
- Note in metrics: "System exhibits stable setpoint behavior; COV gaps expected and benign."
- Penalty: 0.0 per COV_CONSTANT gap.
- Stage 2 penalty is **low** (mostly COV penalties are zero).
- Continue to Stage 3; sync will insert NaN for missing grid points, confidence marked as `COV_CONSTANT`.

**Example Output**:
```json
{
  "observation": "Sparse COV logging detected",
  "cov_constant_pct": 85.0,
  "interpretation": "Setpoint stable; system not changing load",
  "action": "Benign; proceed to sync stage with confidence reduced by data gaps only"
}
```

---

## 3. Edge Case: Isolated Outlier (1–2 Points)

**Scenario**: Single temperature spike (CHWST jumps 10 °C for one record, then returns to normal).

**Detection**:
```
value_before = records[i-1].CHWST = 17.56
value_spike = records[i].CHWST = 27.8
value_after = records[i+1].CHWST = 17.59

relative_jump_before = |27.8 - 17.56| / 17.56 = 58% (huge)
relative_jump_after = |17.59 - 27.8| / 27.8 = 37% (huge)
```

**Action**:
- Mark the spike record as `SENSOR_ANOMALY`.
- Drop it silently (don't include in downstream analysis).
- Count in metrics: `sensor_anomalies_isolated = 1`.
- Do NOT create an exclusion window (only 1 point, not a multi-stream gap).
- Penalty: −0.05 for this one anomaly (absorbed by aggregate).

**Example Output**:
```json
{
  "anomaly_detected": {
    "stream": "CHWST",
    "timestamp": "2024-10-20T08:15:00Z",
    "value_before": 17.56,
    "spike_value": 27.8,
    "value_after": 17.59,
    "reason": "Isolated spike; dropped from analysis",
    "action": "Remove from dataframe; log as anomaly"
  }
}
```

---

## 4. Edge Case: Multiple Overlapping Exclusion Windows

**Scenario**: Two separate multi-stream MAJOR_GAPs detected that partially overlap (not same window).

**Example**:
```
Window 1: 2025-08-26 to 2025-09-06 (11 days, all 3 core temps)
Window 2: 2025-09-05 to 2025-09-15 (10 days, only CHWST + CDWRT)
Overlap:  2025-09-05 to 2025-09-06 (2 days)
```

**Detection**:
```python
proposed_windows = [
  (2025-08-26, 2025-09-06, ["CHWST", "CHWRT", "CDWRT"]),
  (2025-09-05, 2025-09-15, ["CHWST", "CDWRT"])
]

# Check for overlap
overlap = max(w1.start, w2.start) < min(w1.end, w2.end)
if overlap:
  prompt user: merge or keep separate?
```

**Action**:
- Expose both windows to user for approval.
- User options:
  1. **Merge**: Create single window 2025-08-26 to 2025-09-15.
  2. **Keep separate**: Approve both independently.
  3. **Reject**: Ignore anomaly; proceed anyway.
- Common choice: **Merge** (maintenance period likely extended).

**Example Output**:
```json
{
  "exclusion_windows_proposed": 2,
  "windows_overlap": true,
  "recommendation": "Merge into single window 2025-08-26 to 2025-09-15",
  "user_decision_needed": true
}
```

---

## 5. Edge Case: Clock Skew Between Streams

**Scenario**: BMS records CHWST at clock time T, but CHWRT at T+30 seconds. Clocks not synchronized.

**Detection** (harder to spot):
```
Per interval, compute timestamps across streams:
  CHWST timestamps: [1000, 1900, 2800, ...]
  CHWRT timestamps: [1030, 1930, 2830, ...]  (consistently 30s behind)
  
Compute cross-stream timestamp offset:
  mean_offset = mean(CHWRT_timestamps - CHWST_timestamps) = +30 s
  std_offset = stdev(...) ≈ 0
  
If std_offset is very small and consistent offset non-zero:
  flag: "Clock skew detected"
```

**Action**:
- Log warning: "Streams have consistent timestamp offset of +30 s."
- Option 1: Adjust all timestamps by offset before Stage 3 sync.
- Option 2: Continue with offset; Stage 3 sync will tolerate ±30 min anyway.
- No penalty; just note in metrics.

**Example Output**:
```json
{
  "clock_skew_detected": true,
  "offset_seconds": 30,
  "affected_streams": ["CHWRT"],
  "action": "Tolerated by Stage 3 sync (±30 min tolerance); continue",
  "severity": "INFO"
}
```

---

## 6. Edge Case: Reversed (Descending) Timestamps

**Scenario**: A stream's timestamps go backwards (data corruption or ingestion error).

**Example**:
```
CHWST timestamps: [1000, 1900, 1800, 2700, ...]  (1800 < 1900, reversed)
```

**Detection**:
```python
for i in range(len(timestamps) - 1):
  if timestamps[i+1] < timestamps[i]:
    errors.append(f"Timestamp reversal at index {i}")
    halt = True
```

**Action**:
- **HALT immediately**.
- Return error: `"Stage 2 HALT: Timestamp reversal detected. Data corrupted or ingestion error."`
- Require user to re-export or fix upstream.
- Do NOT attempt to auto-sort (loses data provenance).

**Example Output**:
```json
{
  "error": "HALT: Timestamp reversal at index 5042",
  "timestamp_before": "2024-10-15T14:30:00Z",
  "timestamp_after": "2024-10-15T14:28:00Z",
  "action": "Re-export from BMS and verify data integrity"
}
```

---

## 7. Edge Case: Zero Flow for Extended Period

**Scenario**: Flow stream shows 0 L/s for 48 hours straight, then resumes normal values.

**Question**: Is this MAJOR_GAP or chiller offline?

**Analysis**:
```
Flow:    [50, 55, 0, 0, 0, ..., 0, 52, 48]  (48 hours of zeros)
CHWST:   [17.5, 17.4, 17.3, 17.2, ..., 17.0, 17.5, 17.6]  (still changing!)
CDWRT:   [22, 22.1, 22.05, 22, ...]  (still normal)

Physics check:
  - If CHWST/CHWRT still changing → load still present → flow can't be truly zero
  - Conclusion: Flow sensor error or stuck at zero

Action:
  - Mark flow records as SENSOR_ANOMALY during zero period
  - Don't create exclusion window (other temps are normal)
  - Penalty: -0.05 per affected record (modest)
```

**Alternative** (chiller truly idle):
```
Flow:    [0, 0, 0, ...]  (entire 48 hours)
CHWST:   [null, null, ...]  (no change, no measurement)
CDWRT:   [null, null, ...]  (no change, no measurement)

Interpretation:
  - Chiller is OFF (no load, no flow, no condenser water movement)
  - This is expected; propose exclusion window if aligns with maintenance schedule
```

---

## 8. Edge Case: No MAJOR_GAPs Detected

**Scenario**: All intervals are NORMAL; dataset is perfectly regular (every 900 ± 5 seconds).

**Action**:
- Congratulations! Data logging is excellent.
- No exclusion windows to propose.
- Stage 2 penalty: 0.0.
- stage2_confidence = stage1_confidence (no gap penalty).
- Proceed to Stage 3 with high confidence.

**Example Output**:
```json
{
  "gaps_detected": false,
  "all_intervals": "NORMAL",
  "gap_penalty": 0.0,
  "stage2_confidence": 1.0,
  "message": "Perfect regular logging; excellent data quality"
}
```

---

## 9. Troubleshooting: Stage 2 Confidence Unexpectedly Low

**Symptom**: `stage2_confidence = 0.30` (much lower than expected).

**Diagnosis Checklist**:

1. **Are there many SENSOR_ANOMALY gaps?**
   ```
   SENSOR_ANOMALY_count >> COV_CONSTANT_count
   → Check for sensor calibration issues or corruption
   ```

2. **Is exclusion window very large?**
   ```
   exclusion_pct > 20%
   → Data loss itself reduces confidence; also indicates system problem
   ```

3. **Are physics violations common?**
   ```
   "CHWRT < CHWST for 5% of gap boundaries"
   → Sensor malfunction; consider HALT
   ```

4. **Are there multiple missing streams?**
   ```
   Power missing entirely + Flow missing = can't compute COP
   → stage2_confidence inherently limited
   ```

5. **Did user reject exclusion window?**
   ```
   Proposed window rejected → anomalous data remains in dataset
   → Higher confidence than if approved (user's choice)
   ```

**Solution Path**:
- Review the metrics JSON (not just confidence score).
- Check which streams contribute to low score.
- Ask user: "Is this expected? Do you want to exclude more data?"
- Or: "Sensor malfunction suspected; validate with BMS team."

---

## 10. Troubleshooting: Human Review Takes Too Long

**Symptom**: User approval of exclusion windows is delayed; pipeline stalled.

**Solution**:
- Provide a **"Proceed without approval"** option:
  - Mark potential exclusion windows as "PENDING" (don't exclude yet).
  - Continue to Stage 3; treat PENDING windows as COV_CONSTANT gaps.
  - User can approve later; Stage 3 output will be updated retroactively.

**Implementation**:
```typescript
if (exclusionWindowsProposed.length > 0) {
  // Option 1: Wait for approval (blocking)
  await waitForUserApproval();
  
  // Option 2: Continue without approval (non-blocking)
  if (user.chooseNonBlocking()) {
    for (const window of exclusionWindowsProposed) {
      window.status = "PENDING";  // Not yet excluded
    }
    proceedToNextStage();
  }
}
```

---

## 11. Troubleshooting: COV Detection Too Sensitive / Not Sensitive Enough

**Symptom 1: Too many gaps classified as COV_MINOR**
- Increase `COV_TOLERANCE_RELATIVE_PCT` (e.g., from 0.5% to 1.0%).
- More gaps will be COV_CONSTANT; fewer will be COV_MINOR.

**Symptom 2: Too few gaps classified as COV_CONSTANT**
- Decrease `COV_TOLERANCE_RELATIVE_PCT` (e.g., from 0.5% to 0.2%).
- Stricter matching; more will be COV_MINOR.

**Recommended**: Start with 0.5%, test on BarTech data (should detect ~155 COV_CONSTANT), adjust if needed.

---

## 12. Quick Diagnostic: Did Stage 2 Run Correctly?

**Checklist**:

```
□ All 5 streams processed (or document if Power missing)
□ Per-stream interval counts sum to N-1 (no gaps in counting)
□ Gap semantics distribution makes sense:
  - Most are COV_CONSTANT? → Good (sparse logging is normal)
  - Many SENSOR_ANOMALY? → Investigate sensors
□ Exclusion window (if proposed) aligns with known maintenance
□ stage2_confidence within expected range (0.80–1.00 for good data)
□ Metrics JSON well-formed and serializable
□ Dataframe has new gap_* columns added
□ No HALT unless physics violation detected (CHWRT < CHWST >1%)
```

---

**Status**: Edge cases & troubleshooting for Stage 2.  
**Use**: Reference during implementation and debugging.  
**Generated**: 2025-12-07

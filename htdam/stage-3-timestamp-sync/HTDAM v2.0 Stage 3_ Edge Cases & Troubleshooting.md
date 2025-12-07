<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# HTDAM v2.0 Stage 3: Edge Cases \& Troubleshooting

## Common Synchronization Scenarios \& How to Handle Them

**Date**: 2025-12-08
**Status**: Complete for Stage 3 only

***

## 1. Edge Case: Empty or Invalid Time Span

**Scenario**: Stage 2 dataframe has `timestamp_start == timestamp_end` (single record), or `timestamp_start > timestamp_end` (data corruption).

**Detection**:

```python
if df['timestamp'].min() == df['timestamp'].max():
    error = "Only one timestamp present; cannot build grid"
    halt = True
elif df['timestamp'].max() < df['timestamp'].min():
    error = "Corrupted timestamps: end < start"
    halt = True
elif df['timestamp'].nunique() < 2:
    error = "Less than 2 unique timestamps; grid construction impossible"
    halt = True
```

**Action**:

- **HALT immediately**.
- Log error: `"Stage 3 HALT: Invalid time span. Check Stage 2 input data."`
- Do not proceed; require re-export from BMS.

**Example Output**:

```json
{
  "error": "HALT: Only one timestamp present (2024-10-15T14:30:00Z). Grid construction requires at least 2 points.",
  "action": "Re-export from BMS with longer time range"
}
```


***

## 2. Edge Case: All Records Marked EXCLUDED (Entire Dataset in Maintenance Window)

**Scenario**: User approves an exclusion window that spans the entire dataset (e.g., chiller offline for entire export period).

**Detection**:

```python
if exclusion_windows and \
   (exclusion_windows[0].start_ts <= df['timestamp'].min()) and \
   (exclusion_windows[0].end_ts >= df['timestamp'].max()):
    warning = "Entire dataset is inside exclusion window"
```

**Action**:

- Build grid (grid points will all be `EXCLUDED`).
- Grid coverage = 0% VALID.
- Penalty = **HALT** (no data to analyze).
- Log: `"Stage 3 HALT: Entire dataset excluded. No valid data for analysis."`
- User must re-export during operational period.

**Example Output**:

```json
{
  "warning": "Entire dataset (2025-08-26 to 2025-09-06) marked as excluded",
  "coverage_pct": 0.0,
  "action": "Re-export data during operational period, not maintenance window"
}
```


***

## 3. Edge Case: Grid Too Coarse (Information Loss)

**Scenario**: `T_NOMINAL_SECONDS` set to 3600 (1 hour) on 15‑minute COV data. Multiple raw points map to same grid timestamp.

**Detection**:

```python
raw_points_per_grid = []
for each grid interval:
    count = number of raw timestamps in 

**Action**:
- **Do not HALT**; continue with coarse grid.
- Compute **information loss metric**:
```

info_loss_pct = (1 - grid_points / total_raw_points) * 100

```
- If `info_loss_pct > 30%`: log strong warning.
- Suggest to user: `"Consider finer grid (e.g., 15 min) to preserve information."`
- Penalty: −0.03 for significant information loss.

**Example Output**:
```

{
"grid_coarseness": "COARSE",
"t_nominal_seconds": 3600,
"raw_points_per_grid_max": 24,
"info_loss_pct": 75.0,
"warning": "Grid is very coarse; 75% of raw data points collapsed. Consider 900 s grid.",
"penalty": -0.03,
"action": "User may re-run with finer T_NOMINAL"
}

```

---

## 4. Edge Case: Grid Too Fine (Mostly Missing)

**Scenario**: `T_NOMINAL_SECONDS` set to 60 (1 min) on 15‑minute COV data. Grid has many more points than raw data.

**Detection**:
```

coverage_pct = VALID_count / total_grid_points
if coverage_pct < 0.50:
warning = "Very fine grid; most points are MISSING"

```

**Action**:
- **Do not HALT** (still possible to analyze).
- Coverage penalty will be high (e.g., −0.10).
- Suggest coarser grid: `"Consider 900 s grid to improve coverage."`
- Log in metrics: `fine_grid_suggested = true`.

**Example Output**:
```

{
"grid_fine_ness": "FINE",
"t_nominal_seconds": 60,
"coverage_pct": 25.0,
"warning": "Very fine grid; only 25% coverage. Consider 900 s grid.",
"penalty": -0.10,
"action": "User may re-run with coarser T_NOMINAL"
}

```

---

## 5. Edge Case: All Streams Missing at Same Grid Point (Universal Gap)

**Scenario**: At grid timestamp `g_k`, **all mandatory streams** are `MISSING` (no raw point within tolerance).

**Detection**:
```

if all(align_quality_s[k] == 'MISSING' for s in mandatory_streams):
universal_gap = True

```

**Action**:
- Set `gap_type = 'COV_CONSTANT'` (if Stage 2 near that time had COV_CONSTANT).
- Set `confidence = 0.00`.
- This is **expected** in COV logging; it's how sparse data shows up.
- Do not treat as error; it's the intended behavior.
- Count in metrics: `universal_gap_count`.

**Example Output**:
```

{
"universal_gap_count": 177,
"universal_gap_pct": 0.5,
"interpretation": "Sparse COV logging; setpoint held constant",
"action": "No HALT; proceed to Stage 4"
}

```

---

## 6. Edge Case: Clock Skew Between Streams (Detected in Stage 3)

**Scenario**: CHWST timestamps are 30 seconds ahead of CHWRT timestamps (BMS clock drift).

**Detection**:
```


# After alignment, compute cross-stream offset

offsets = []
for i in range(len(grid)):
for s1, s2 in itertools.combinations(mandatory_streams, 2):
if align_quality[s1][i] != 'MISSING' and align_quality[s2][i] != 'MISSING':
dt = abs(aligned_timestamps[s1][i] - aligned_timestamps[s2][i])
offsets.append(dt.total_seconds())

mean_offset = mean(offsets)
std_offset = std(offsets)

if mean_offset > 120:  \# >2 minutes average offset
warning = "Clock skew detected between streams"

```

**Action**:
- Log large offset warning but **do not HALT**.
- Stage 3 alignment tolerates up to ±30 min; clock skew of seconds is fine.
- Note in metrics: `clock_skew_detected = true`, `mean_offset_s = 30`.
- No penalty (tolerated by design).
- Suggest user: "Consider NTP sync on BMS controllers."

**Example Output**:
```

{
"clock_skew_detected": true,
"mean_offset_s": 30.0,
"std_offset_s": 5.2,
"affected_streams": ["CHWRT"],
"warning": "Clock skew detected but within tolerance (±1800 s). No penalty.",
"action": "Tolerated; suggest NTP sync for future exports"
}

```

---

## 7. Edge Case: Duplicate Grid Timestamps (Clock Skew or Bug)

**Scenario**: Grid construction produces duplicate timestamps (e.g., due to floating point rounding or leap seconds).

**Detection**:
```

if len(grid) != len(set(grid)):
duplicate_count = len(grid) - len(set(grid))
error = f"Duplicate grid timestamps detected: {duplicate_count}"
halt = True

```

**Action**:
- **HALT immediately**.
- This indicates a bug in grid generator or corrupted timestamps.
- Inspect `grid` generation logic (floating point precision, timezone conversions).
- Fix and re-run.

**Example Output**:
```

{
"error": "HALT: Duplicate grid timestamps detected (3 duplicates)",
"action": "Check grid generation logic for floating point or timezone issues"
}

```

---

## 8. Edge Case: Jitter > 5% (Inconsistent Intervals)

**Scenario**: Grid intervals not perfectly uniform (e.g., 900, 900, 901, 899, 900 seconds). Could be due to floating point or BMS timestamp issues.

**Detection**:
```

intervals = [grid[i+1] - grid[i] for i in range(len(grid)-1)]
interval_std = std(intervals)
interval_cv = interval_std / mean(intervals) * 100

if interval_cv > 5.0:
warning = "Jitter exceeds 5% tolerance"
penalty = -0.02

```

**Action**:
- Log warning.
- Penalty modest (−0.02).
- Investigate cause: BMS clock drift, floating point rounding, DST transitions.
- If `interval_cv > 20%`, consider data quality too low; log strong warning or HALT.

**Example Output**:
```

{
"jitter": {
"interval_cv_pct": 6.8,
"interval_std_s": 61.2,
"interval_mean_s": 900.0
},
"warning": "Jitter exceeds 5% (6.8%) due to BMS clock drift",
"penalty": -0.02,
"action": "Tolerated; suggest BMS clock sync"
}

```

---

## 9. Edge Case: Tolerance Too Large (All Data Within Tolerance)

**Scenario**: `SYNC_TOLERANCE_SECONDS = 3600` (1 hour) on 15‑min nominal data. All raw points map to grid (no `MISSING`).

**Detection**:
```

if missing_pct < 5.0 and SYNC_TOLERANCE_SECONDS > 2 * T_NOMINAL_SECONDS:
warning = "Tolerance is very large; may mask truly missing data"

```

**Action**:
- Continue (no HALT).
- Log warning: `"Consider reducing SYNC_TOLERANCE_SECONDS to better reflect actual sync capability."`
- Penalty: 0.00 (but user may want to tighten tolerance for stricter validation).

**Example Output**:
```

{
"tolerance_s": 3600,
"t_nominal_s": 900,
"missing_pct": 1.2,
"warning": "Tolerance too large (4× T_nominal); consider 1800 s",
"penalty": 0.0,
"action": "No penalty; user may tighten tolerance"
}

```

---

## 10. Edge Case: Tolerance Too Small (Most Points Excluded)

**Scenario**: `SYNC_TOLERANCE_SECONDS = 300` (5 min) on 15‑min nominal data with COV gaps. Many valid raw points are >5 min away from grid.

**Detection**:
```

if missing_pct > 50 and SYNC_TOLERANCE_SECONDS < T_NOMINAL_SECONDS:
warning = "Tolerance too small; many valid points excluded"

```

**Action**:
- Coverage penalty will be large (−0.10).
- Log strong warning: `"Increase SYNC_TOLERANCE_SECONDS to capture more valid points."`
- Do not HALT; user can adjust and re-run.

**Example Output**:
```

{
"tolerance_s": 300,
"t_nominal_s": 900,
"missing_pct": 68.0,
"warning": "Tolerance too small; 68% of points excluded. Increase to 1800 s.",
"penalty": -0.10,
"action": "User should increase tolerance and re-run"
}

```

---

## 11. Edge Case: Very Large Datasets (Performance)

**Scenario**: 1 year of 1‑minute data → 525,600 grid points. Alignment algorithm O(N+M) could be slow if implemented naively.

**Detection**:
```

if len(grid) > 100_000:
info = "Large dataset; consider performance optimization"

```

**Action**:
- Use **two‑pointer scan** (already O(N+M) in spec).
- Ensure no nested loops over grid & raw data.
- Pre‑allocate arrays (avoid list appends).
- Optionally use NumPy vectorized operations for speed.

**Performance target**:
- 1 million grid points + 1 million raw points → <5 seconds on modern CPU.

**Example Output** (performance metric):
```

{
"performance": {
"grid_points": 525600,
"raw_records_total": 1576800,  \# 3 streams × 525k
"alignment_time_ms": 3200,
"status": "OK"
}
}

```

---

## 12. Edge Case: Flow/Power Missing Entirely (Post‑Stage 2)

**Scenario**: Stage 2 already flagged Flow/Power as `NOT_PROVIDED`. In Stage 3, these streams don't exist for alignment.

**Detection**:
```

if stream not in df.columns:
metrics['per_stream_alignment'][stream] = {
"status": "NOT_PROVIDED",
"aligned_exact_count": 0,
"aligned_close_count": 0,
"aligned_interp_count": 0,
"missing_count": len(grid),
"missing_pct": 100.0
}

```

**Action**:
- Do not attempt alignment.
- Row‑level `gap_type` still determined by mandatory streams (CHWST/CHWRT/CDWRT).
- Stage 4 will see `power_kw` column missing and mark COP as unavailable.

**Example Output**:
```

{
"per_stream_alignment": {
"CHWST": { "status": "OK", "exact_pct": 93.8, ... },
"CHWRT": { "status": "OK", "exact_pct": 93.9, ... },
"CDWRT": { "status": "OK", "exact_pct": 93.7, ... },
"Power": {
"status": "NOT_PROVIDED",
"missing_pct": 100.0,
"impact": "COP calculation unavailable in Stage 4"
}
}
}

```

---

## 13. Edge Case: Interpolation Threshold Ambiguity

**Scenario**: Raw point is exactly at `ALIGN_INTERP_THRESHOLD` (e.g., 1800 s). Should it be `INTERP` or `MISSING`?

**Rule** (be consistent):
```

if align_distance_s <= ALIGN_INTERP_THRESHOLD:
align_quality = 'INTERP'
else:
align_quality = 'MISSING'

```

**Action**:
- Use `<=` (inclusive) for INTERP.
- Document choice in code comments.
- Include in unit tests.

---

## 14. Edge Case: Grid Point Exactly at Raw Timestamp

**Scenario**: Grid point `g_k` is exactly equal to a raw timestamp `t_r`.

**Detection**:
```

if abs((t_r - g_k).total_seconds()) < 1e-6:  \# floating point epsilon
align_distance_s = 0.0
align_quality = 'EXACT'

```

**Action**:
- Treat as `EXACT` (distance zero).
- No special handling needed; algorithm already picks nearest.
- Confidence = 0.95.

---

## 15. Quick Diagnostic: Did Stage 3 Run Correctly?

**Checklist**:

```

□ Grid points are uniformly spaced (interval CV < 0.1%)
□ No duplicate grid timestamps
□ Coverage % is reasonable (e.g., 80–100%)
□ Per‑stream alignment metrics sum to grid size (exact + close + interp + missing = grid_points)
□ Row-level gap_type distribution matches Stage 2 gap semantics (COV_CONSTANT count ≈ Stage 2 count)
□ Stage3 confidence = stage2_confidence + penalty (e.g., 0.93 + (−0.05) = 0.88)
□ No HALT unless coverage catastrophically low (<30%) or jitter extreme (>20%)
□ Performance acceptable (alignment time < 5 s per million points)

```

---

**Status**: Edge cases & troubleshooting for Stage 3.  
**Use**: Reference during implementation and debugging.  
**Generated**: 2025-12-08```


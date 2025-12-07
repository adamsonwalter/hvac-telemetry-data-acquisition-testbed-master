<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# HTDAM v2.0 Stage 3: Timestamp Synchronization

## Comprehensive Implementation Artefacts (Including JSON Specs)

Stage 3 turns irregular, gap-classified streams from Stage 2 into a **single synchronized time grid** (e.g. 15‑minute) with a **row‑level `gap_type` and `confidence`** that all downstream logic (Stage 4, MoAE, other apps) can rely on.

Below are the full artefacts your programmer needs:

- Stage 3 Implementation Guide (algorithms, constants, output formats).
- Metrics / JSON specifications.
- Edge cases \& troubleshooting guide.
- Implementation checklist.

Everything is written so it slots cleanly into your existing **`htdam_constants`**, **domain layer**, and **`useOrchestration`**.

***

## 1. Stage 3 Overview

**Stage name**: Timestamp Synchronization
**Order in HTDAM v2.0**: Stage 3 (after Gap Detection, before Signal Preservation)
**Goals**:

- Create a **master time grid** (usually 15‑minute) spanning the analysis period.
- **Align each stream** (CHWST, CHWRT, CDWRT, Flow, Power, etc.) to this grid using deterministic nearest‑neighbor logic.
- Compute **alignment quality flags** (`EXACT`, `CLOSE`, `INTERP`, `MISSING`) per stream \& timestamp.
- Produce **row‑level `gap_type` and `confidence`** that combine alignment quality + Stage 2 gap semantics.
- Validate **timebase quality**: jitter, coverage, duplicates.

**Inputs** (from Stage 2):

- Enriched dataframe with at least:
    - `timestamp` (datetime, UTC).
    - Canonical fields: `chwst`, `chwrt`, `cdwrt`, `flow_m3s`, `power_kw` (where present).
    - Stage 2 gap metadata: per‑stream:
        - `gap_before_duration_s`
        - `gap_before_class` (`NORMAL`, `MINOR_GAP`, `MAJOR_GAP`)
        - `gap_before_semantic` (`COV_CONSTANT`, `COV_MINOR`, `SENSOR_ANOMALY`, `UNKNOWN`)
        - `exclusion_window_id` (if inside an approved exclusion window)
- Stage 2 metrics object (for reference).

**Outputs**:

- Synchronized dataframe on a **single master grid**, with:
    - One row per grid timestamp.
    - One column per aligned stream (canonical units).
    - Row‑level `gap_type` and `confidence`.
    - Per‑stream `align_quality` and `align_distance_s`.
- Stage 3 metrics JSON (see Section 5).

***

## 2. Master Grid Construction

### 2.1 Parameters \& Constants

Add (or confirm) in `htdam_constants`:

```python
# Stage 3 Synchronization

T_NOMINAL_SECONDS = 900          # 15-minute grid, must match Stage 2
SYNC_TOLERANCE_SECONDS = 1800    # ±30 minutes max allowed distance

ALIGN_EXACT_THRESHOLD = 60       # <60 s → EXACT
ALIGN_CLOSE_THRESHOLD = 300      # 60–300 s → CLOSE
ALIGN_INTERP_THRESHOLD = 1800    # 300–1800 s → INTERP (beyond this → MISSING)
```


### 2.2 Time Span

From Stage 2 dataframe:

```python
t_start_raw = df['timestamp'].min()
t_end_raw   = df['timestamp'].max()
```

Optionally trim to exclude beginning/ending tails (e.g. first/last day with very sparse data), or keep full span.

### 2.3 Grid Definition

Define master grid $G = [g_0, g_1, ..., g_{M-1}]$:

```python
def ceil_to_grid(ts, step_s):
    # Convert to epoch seconds, ceil, then back to datetime
    # (exact implementation language-dependent)
    ...

g0 = ceil_to_grid(t_start_raw, T_NOMINAL_SECONDS)

grid = []
t = g0
while t <= t_end_raw:
    grid.append(t)
    t = t + T_NOMINAL_SECONDS  # add 900 s
```

Output:

- `grid`: list of uniformly spaced timestamps.
- `M = len(grid)`.

***

## 3. Per-Stream Nearest-Neighbor Alignment

### 3.1 Inputs Per Stream

For each stream `s` (e.g. `CHWST`):

- `timestamps_raw_s`: strictly increasing list of datetimes (from Stage 2).
- `values_raw_s`: aligned values (canonical units).
- Optional: we can also have a per‑record Stage 2 `gap_before_*` for context, but Stage 3 works primarily with timestamps \& values.


### 3.2 Alignment Algorithm (O(M + N))

Pseudocode:

```python
def align_stream_to_grid(timestamps_raw, values_raw, grid, tolerance_s):
    """
    Returns:
      values_grid: list[float or NaN]
      align_quality: list[str] in {EXACT, CLOSE, INTERP, MISSING}
      align_distance_s: list[float or None]
    """
    N = len(timestamps_raw)
    M = len(grid)
    
    values_grid = [float('nan')] * M
    align_quality = ['MISSING'] * M
    align_distance_s = [None] * M
    
    j = 0  # pointer into timestamps_raw
    
    for k in range(M):
        g = grid[k]
        
        # advance j until timestamps_raw[j] >= g
        while j < N and timestamps_raw[j] < g:
            j += 1
        
        candidates = []
        # left neighbor: j-1
        if j - 1 >= 0:
            candidates.append(j - 1)
        # right neighbor: j
        if j < N:
            candidates.append(j)
        
        if not candidates:
            continue  # remains MISSING
        
        # choose nearest
        best_idx = None
        best_dt = None
        
        for idx in candidates:
            dt = abs((timestamps_raw[idx] - g).total_seconds())
            if best_dt is None or dt < best_dt:
                best_dt = dt
                best_idx = idx
        
        if best_dt is None or best_dt > tolerance_s:
            # too far: treat as missing
            continue
        
        v = values_raw[best_idx]
        values_grid[k] = v
        align_distance_s[k] = best_dt
        
        # quality classification
        if best_dt < ALIGN_EXACT_THRESHOLD:
            align_quality[k] = 'EXACT'
        elif best_dt < ALIGN_CLOSE_THRESHOLD:
            align_quality[k] = 'CLOSE'
        elif best_dt <= ALIGN_INTERP_THRESHOLD:
            align_quality[k] = 'INTERP'
        else:
            # beyond interpolation threshold but ≤ tolerance_s (should not happen if thresholds consistent)
            align_quality[k] = 'MISSING'
    
    return values_grid, align_quality, align_distance_s
```

Run this for each stream:

- `aligned_chwst, q_chwst, dt_chwst = align_stream_to_grid(...)`
- `aligned_chwrt, ...`
- `aligned_cdwrt, ...`
- `aligned_flow, ...` (if available)
- `aligned_power, ...` (if available)

***

## 4. Row-Level `gap_type` and `confidence`

Now that each stream is aligned to the grid, Stage 3 must:

1. Combine **alignment quality** across streams.
2. Incorporate Stage 2 gap semantics (COV vs anomaly) and exclusion windows.
3. Produce a **single `gap_type` and `confidence` per row**.

### 4.1 Inputs Per Grid Row k

At grid time `g_k`:

- For each mandatory stream `s` in `{CHWST, CHWRT, CDWRT}`:
    - `align_quality_s[k]` ∈ `{EXACT, CLOSE, INTERP, MISSING}`.
    - `aligned_value_s[k]` (or NaN).
- Optional streams (Flow, Power) similar, but treated differently in confidence.
- `exclusion_window_id[k]`:
    - Derived by checking whether `g_k` is within any approved exclusion window from Stage 2.


### 4.2 Per-Stream Alignment Confidence

Define per‑stream alignment confidence:

```python
def alignment_conf_for_quality(q: str) -> float:
    if q == 'EXACT':
        return 0.95
    elif q == 'CLOSE':
        return 0.90
    elif q == 'INTERP':
        return 0.85
    elif q == 'MISSING':
        return 0.00
    else:
        return 0.00
```


### 4.3 Row-Level Logic

Pseudocode:

```python
def derive_row_gap_type_and_conf(
    k,
    grid_time,
    align_quality_by_stream,   # dict[stream_id -> str]
    exclusion_window_id,       # None or string
    stage2_gap_semantics_opt   # optional: semantics around this time
):
    mandatory_streams = ['CHWST', 'CHWRT', 'CDWRT']
    
    # 1. Exclusion window has highest precedence
    if exclusion_window_id is not None:
        return 'EXCLUDED', 0.00
    
    # 2. Check mandatory streams coverage
    quals = [align_quality_by_stream[s] for s in mandatory_streams]
    
    # If any mandatory stream is MISSING
    if any(q == 'MISSING' for q in quals):
        # Look up Stage 2 semantics near this time if available
        semantic = lookup_stage2_semantic(grid_time, stage2_gap_semantics_opt)
        
        if semantic == 'COV_CONSTANT':
            return 'COV_CONSTANT', 0.00
        elif semantic == 'COV_MINOR':
            return 'COV_MINOR', 0.00
        elif semantic == 'SENSOR_ANOMALY':
            return 'SENSOR_ANOMALY', 0.00
        else:
            return 'GAP', 0.00  # generic gap
    
    # 3. All mandatory streams have some value; classify VALID row
    confs = [alignment_conf_for_quality(q) for q in quals]
    row_conf = min(confs)
    
    # If any INTERP present
    if any(q == 'INTERP' for q in quals):
        gap_type = 'VALID'  # still valid but note lower confidence
    else:
        gap_type = 'VALID'
    
    return gap_type, row_conf
```

**Notes**:

- `lookup_stage2_semantic(grid_time, ...)` can:
    - Use nearest or overlapping Stage 2 gap window around `grid_time`.
    - If no semantic known, return `None`.
- Flow and Power alignment qualities should **not block** a row from being `VALID` (for temperature-level analysis), but may be used later for COP‑specific confidence.


### 4.4 Integration with Exclusion Windows

For each approved exclusion window from Stage 2:

```python
for each grid_time g_k:
    if any(window.start_ts <= g_k <= window.end_ts for window in approved_windows):
        gap_type[k] = 'EXCLUDED'
        confidence[k] = 0.00
        exclusion_window_id[k] = window.window_id
        # Optionally null all values for that row
```


***

## 5. Stage 3 Output Format

### 5.1 DataFrame Columns

**Input**: Stage 2 dataframe with original timestamps \& semantics.

**Output**: New dataframe `df_sync` with one row per grid timestamp:

Required columns:

- `timestamp` (grid timeline).
- `chwst`, `chwrt`, `cdwrt` (aligned temperatures, canonical units).
- `flow_m3s` (aligned, if present).
- `power_kw` (aligned, if present).

Per‑stream alignment metadata:

- `chwst_align_quality` (`EXACT`, `CLOSE`, `INTERP`, `MISSING`).
- `chwst_align_distance_s` (float seconds or null).
- Same for `chwrt`, `cdwrt`, `flow`, `power`.

Row-level fields:

- `gap_type`:
    - `VALID`, `COV_CONSTANT`, `COV_MINOR`, `SENSOR_ANOMALY`, `GAP`, `EXCLUDED`.
- `confidence` (0.0–0.95).
- `exclusion_window_id` (string or null).

Optional derived fields (used in Stage 4 but may be computed here):

- `delta_t_c` = `chwrt - chwst`.
- `lift_c` = `cdwrt - chwst`.

Example row:

```text
timestamp:            2024-10-15T15:00:00Z
chwst:                17.56
chwrt:                17.39
cdwrt:                22.11
flow_m3s:             0.001234
power_kw:             45.2

chwst_align_quality:  EXACT
chwst_align_distance_s: 12
chwrt_align_quality:  EXACT
chwrt_align_distance_s: 8
cdwrt_align_quality:  CLOSE
cdwrt_align_distance_s: 120

gap_type:             VALID
confidence:           0.90
exclusion_window_id:  null
```


### 5.2 Metrics JSON (Stage 3)

Example JSON structure:

```json
{
  "stage": "SYNC",
  "timestamp_start": "2024-09-18T03:30:00Z",
  "timestamp_end": "2025-09-19T03:15:00Z",
  "grid": {
    "t_nominal_seconds": 900,
    "grid_points": 35136,
    "coverage_seconds": 31622400
  },
  "per_stream_alignment": {
    "CHWST": {
      "total_raw_records": 35574,
      "aligned_exact_count": 32959,
      "aligned_close_count": 70,
      "aligned_interp_count": 178,
      "missing_count": 1929,
      "exact_pct": 93.8,
      "close_pct": 0.2,
      "interp_pct": 0.5,
      "missing_pct": 5.5,
      "mean_align_distance_s": 22.0,
      "max_align_distance_s": 835.0
    },
    "CHWRT": { /* similar */ },
    "CDWRT": { /* similar */ },
    "Flow": { /* if present */ },
    "Power": { /* if present */ }
  },
  "row_classification": {
    "VALID_count": 32959,
    "VALID_pct": 93.8,
    "COV_CONSTANT_count": 155,
    "COV_MINOR_count": 62,
    "SENSOR_ANOMALY_count": 19,
    "EXCLUDED_count": 1760,
    "GAP_count": 181,
    "confidence_mean": 0.88,
    "confidence_median": 0.90
  },
  "jitter": {
    "interval_mean_s": 900.0,
    "interval_std_s": 0.0,
    "interval_cv_pct": 0.0
  },
  "penalty": -0.05,
  "stage3_confidence": 0.88,
  "warnings": [
    "Flow stream missing for 10% of grid points; COP confidence reduced in Stage 4"
  ],
  "errors": [],
  "halt": false
}
```


***

## 6. Scoring \& Penalties (Stage 3)

Stage 3 primarily evaluates **alignment quality \& coverage**.

### 6.1 Coverage-Based Penalty

Define:

- `coverage_pct` = `VALID_count / total_grid_points`.

Penalty suggestion:

```python
if coverage_pct >= 0.95:
    penalty = 0.0
elif coverage_pct >= 0.90:
    penalty = -0.02
elif coverage_pct >= 0.80:
    penalty = -0.05
else:
    penalty = -0.10  # or even HALT if too low for analysis
```

In your BarTech example:

- `coverage_pct ≈ 93.8%` → penalty ≈ `-0.05`.


### 6.2 Consistency-Based Penalty

- If `interval_std_s > T_NOMINAL_SECONDS * 0.05` (jitter >5%), apply additional penalty (e.g. −0.02).
- If any duplicate grid timestamps exist → HALT and log error.


### 6.3 Stage 3 Confidence

Assume from Stage 2:

```python
stage2_confidence = 0.93
stage3_penalty = -0.05
stage3_confidence = stage2_confidence + stage3_penalty  # 0.88
```

Store `stage3_confidence` and pass into Stage 4.

***

## 7. Edge Cases \& Troubleshooting (Stage 3)

### 7.1 Grid Too Coarse or Too Fine

- **Too coarse** (e.g. 60‑min grid):
    - Many raw points mapped to same grid timestamp; information lost.
    - Consider smaller `T_NOMINAL_SECONDS`.
- **Too fine** (e.g. 1‑min grid on 15‑min data):
    - Most grid points `MISSING`, coverage very low.
    - Coverage penalty will push confidence down; warn user and suggest coarser grid.


### 7.2 Streams with Very Sparse Data

- If `missing_pct` for a stream > 50%:
    - Mark stream as `PARTIAL` in metrics.
    - Use it cautiously in Stage 4 (lower weight in COP confidence).
    - Do **not** HALT Stage 3, but log strong warning.


### 7.3 No Valid Match Within Tolerance

- When all nearest‑neighbor distances exceed `SYNC_TOLERANCE_SECONDS`, treat grid point as `MISSING` for that stream.
- Combined row classification may become `GAP` / `COV_*` / `EXCLUDED` depending on Stage 2 semantics.


### 7.4 Conflicting Semantics vs Alignment

- If Stage 2 says COV_CONSTANT but Stage 3 finds aligned values that differ > tolerance:
    - Prefer Stage 2 semantic for `gap_type`.
    - But log a warning: `"Stage2 semantic COV_CONSTANT inconsistent with Stage3 value difference"`.


### 7.5 Power or Flow Missing Entirely

- If stream absent:
    - Do not attempt alignment.
    - Set metrics entry for that stream: `"status": "NOT_PROVIDED"`.
    - Row‑level `gap_type` determines **temperature validity** only; Stage 4 will mark COP as unavailable.

***

## 8. Implementation Checklist (Stage 3)

Your programmer should be able to tick all of these:

- [ ] Read Stage 3 spec (this document) end‑to‑end.
- [ ] Define/confirm constants in `htdam_constants`:
    - `T_NOMINAL_SECONDS`
    - `SYNC_TOLERANCE_SECONDS`
    - `ALIGN_EXACT_THRESHOLD`, `ALIGN_CLOSE_THRESHOLD`, `ALIGN_INTERP_THRESHOLD`
- [ ] Implement master grid generator (`ceil_to_grid` + loop).
- [ ] Implement `align_stream_to_grid(...)` nearest‑neighbor algorithm.
- [ ] For each stream, compute:
    - `values_grid`
    - `align_quality`
    - `align_distance_s`
- [ ] Implement row‑level logic `derive_row_gap_type_and_conf(...)`.
- [ ] Integrate exclusion window IDs from Stage 2 (approved windows).
- [ ] Build `df_sync` with:
    - Required columns (`timestamp`, aligned values, per‑stream align metadata).
    - Row‑level `gap_type`, `confidence`, `exclusion_window_id`.
- [ ] Compute Stage 3 metrics JSON exactly as specified.
- [ ] Implement coverage \& jitter penalties; compute `stage3_confidence`.
- [ ] Test on BarTech data:
    - ~35,136 grid points.
    - `coverage_pct ≈ 93.8%`.
    - `VALID_count ≈ 32,959`.
    - `stage3_confidence ≈ 0.88`.
- [ ] No HALT unless coverage is catastrophically low or timebase inconsistent.

***

## 9. Example `Stage3Result` Type (for your domain layer)

TypeScript-like interface:

```ts
interface Stage3Metrics {
  stage: 'SYNC';
  timestamp_start: string;
  timestamp_end: string;
  grid: {
    t_nominal_seconds: number;
    grid_points: number;
    coverage_seconds: number;
  };
  per_stream_alignment: {
    [streamId: string]: {
      total_raw_records: number;
      aligned_exact_count: number;
      aligned_close_count: number;
      aligned_interp_count: number;
      missing_count: number;
      exact_pct: number;
      close_pct: number;
      interp_pct: number;
      missing_pct: number;
      mean_align_distance_s: number;
      max_align_distance_s: number;
      status?: 'OK' | 'PARTIAL' | 'NOT_PROVIDED';
    };
  };
  row_classification: {
    VALID_count: number;
    VALID_pct: number;
    COV_CONSTANT_count: number;
    COV_MINOR_count: number;
    SENSOR_ANOMALY_count: number;
    EXCLUDED_count: number;
    GAP_count: number;
    confidence_mean: number;
    confidence_median: number;
  };
  jitter: {
    interval_mean_s: number;
    interval_std_s: number;
    interval_cv_pct: number;
  };
  penalty: number;
  stage3_confidence: number;
  warnings: string[];
  errors: string[];
  halt: boolean;
}

interface Stage3Result {
  data: DataFrameLike;      // df_sync
  metrics: Stage3Metrics;
  scoreDelta: number;       // same as 'penalty'
  messages: string[];       // human-friendly log messages
}
```


***

## 10. How This Connects to Stages 4 \& 5

- Stage 4 will:
    - Use `df_sync` rows with `gap_type == 'VALID'` to compute ΔT, load, COP.
    - Use `confidence` as a weighting / filter for training models or evaluating COP.
- Stage 5 will:
    - Decide which export options are recommended based on `stage3_confidence` and coverage.

Stage 3 is the **last structural stage**: after this, all signals live on a clean timebase and can safely be used in any downstream analysis, including MoAE.

***

If you want, next step can be a **Stage 3 Edge Cases document** in the same style as Stage 2 (expanded with real examples), or a minimal implementation sketch in your preferred language (Python/TypeScript) wiring Stage 3 into `useOrchestration`.


# Stage 2: Gap Detection & Classification

**HTDAM Pipeline Stage 2 - Gap Analysis**  
Version: 1.0  
Status: Implemented  
Date: 2024-12-08

## Overview

Stage 2 performs gap detection and classification on unsynchronized HVAC telemetry signals. It identifies and characterizes time gaps between measurements, distinguishes benign COV (Change-of-Value) logging behavior from sensor anomalies, validates thermodynamic relationships at gap boundaries, and proposes exclusion windows for multi-stream data corruption.

**Why Before Synchronization?**: Gap detection MUST run before synchronization to preserve COV logging semantics. Synchronization creates artificial interpolated values that would obscure the true gap structure. See `htdam/stage-2-gap-detection/HTDAM_Reorder_Gap-First.md` for detailed rationale (+30% confidence improvement).

## Algorithm Overview

### Core Principle

BMS systems use Change-of-Value (COV) logging: sensors log only when values change beyond a threshold (typically 0.5%). Regular time intervals with constant values are **expected behavior**, not gaps. Stage 2 distinguishes:

- **Benign**: COV_CONSTANT (setpoint held) or COV_MINOR (slow drift)
- **Suspicious**: SENSOR_ANOMALY (large jump), physics violations, or multi-stream data corruption

### Gap Classification Thresholds

Based on nominal interval `T_NOMINAL_SECONDS = 900` (15 minutes):

| Class | Threshold | Example | Interpretation |
|-------|-----------|---------|----------------|
| **NORMAL** | ≤ 1.5× (22.5 min) | 900s | Expected COV logging |
| **MINOR_GAP** | 1.5×–4.0× (22.5–60 min) | 1800s | Extended COV hold or slow drift |
| **MAJOR_GAP** | > 4.0× (> 60 min) | 7200s | Data corruption, sensor failure, or maintenance |

### Gap Semantics

For MINOR_GAP and MAJOR_GAP classifications, we analyze value change across the gap:

| Semantic | Value Change | Penalty | Interpretation |
|----------|--------------|---------|----------------|
| **COV_CONSTANT** | < 0.5% | 0.0 | Setpoint held (benign) |
| **COV_MINOR** | 0.5%–5.0% | -0.02 | Slow drift (benign) |
| **SENSOR_ANOMALY** | > 5.0% absolute | -0.05 | Large jump (suspicious) |
| **N/A** | NORMAL class | 0.0 | Not a gap |

### Physics Validation

At each gap boundary, validate thermodynamic relationships:

**CHW Delta-T Checks:**
- CHWST < CHWRT (supply must be cooler than return)
- 2°F ≤ Delta-T ≤ 25°F (typical chiller operation)

**Condenser Relationships:**
- CHWRT < CDWRT (evaporator must be cooler than condenser)

Physics violations result in `SENSOR_ANOMALY` classification and `-0.05` penalty.

### Exclusion Window Detection

When ≥2 signals have overlapping MAJOR_GAPs ≥8 hours, propose an **exclusion window**:

```
Criteria:
- Minimum overlap streams: 2
- Minimum duration: 8 hours
- Gap class: MAJOR_GAP only
```

**Human Approval Required**: When exclusion windows are detected, pipeline pauses and requires human review before proceeding to Stage 3 (synchronization).

## Domain Functions

All domain functions are **pure** (zero side effects, no logging, no I/O).

### 1. `computeInterSampleIntervals(timestamps, values)`

Compute time intervals between consecutive measurements.

**Signature:**
```python
def compute_inter_sample_intervals(
    timestamps: pd.Series,
    values: pd.Series
) -> Tuple[pd.Series, pd.Series]:
```

**Inputs:**
- `timestamps`: Series of Unix timestamps (seconds) or datetime objects
- `values`: Series of signal values (same length as timestamps)

**Outputs:**
- `intervals`: Series of interval durations in seconds (length N-1)
- `sorted_values`: Series of values sorted by timestamp (length N)

**Algorithm:**
1. Sort data by timestamp
2. Compute time deltas: `delta_t[i] = t[i+1] - t[i]`
3. Return intervals and sorted values

**Example:**
```python
timestamps = pd.Series([1000, 1015, 1090])
values = pd.Series([6.8, 6.8, 7.0])
intervals, sorted_vals = compute_inter_sample_intervals(timestamps, values)
# intervals: [15, 75] seconds
```

### 2. `classifyGap(interval_seconds, t_nominal)`

Classify time interval as NORMAL, MINOR_GAP, or MAJOR_GAP.

**Signature:**
```python
def classify_gap(
    interval_seconds: float,
    t_nominal: float = T_NOMINAL_SECONDS
) -> str:
```

**Inputs:**
- `interval_seconds`: Time interval in seconds
- `t_nominal`: Nominal interval (default: 900s)

**Output:**
- Gap class: `"NORMAL"` | `"MINOR_GAP"` | `"MAJOR_GAP"`

**Algorithm:**
1. Compute thresholds: `normal_max = 1.5 × t_nominal`, `minor_max = 4.0 × t_nominal`
2. Compare interval to thresholds
3. Return classification

**Example:**
```python
classify_gap(900)   # "NORMAL"
classify_gap(1800)  # "MINOR_GAP"
classify_gap(7200)  # "MAJOR_GAP"
```

### 3. `detectGapSemantic(value_before, value_after, gap_class)`

Determine gap semantic based on value change.

**Signature:**
```python
def detect_gap_semantic(
    value_before: float,
    value_after: float,
    gap_class: str
) -> str:
```

**Inputs:**
- `value_before`: Signal value immediately before gap
- `value_after`: Signal value immediately after gap
- `gap_class`: Gap classification from `classify_gap()`

**Output:**
- Gap semantic: `"COV_CONSTANT"` | `"COV_MINOR"` | `"SENSOR_ANOMALY"` | `"N/A"`

**Algorithm:**
1. If `gap_class == "NORMAL"`, return `"N/A"`
2. Compute absolute and relative value change
3. If absolute change > 5.0°C → `"SENSOR_ANOMALY"`
4. If relative change < 0.5% → `"COV_CONSTANT"`
5. Otherwise → `"COV_MINOR"`

**Example:**
```python
detect_gap_semantic(17.56, 17.61, "MAJOR_GAP")  # "COV_CONSTANT" (0.28% change)
detect_gap_semantic(12.3, 7.8, "MAJOR_GAP")     # "SENSOR_ANOMALY" (4.5°C jump)
detect_gap_semantic(6.8, 6.8, "NORMAL")         # "N/A"
```

### 4. `validatePhysicsAtGap(temps_before, temps_after)`

Validate thermodynamic relationships at gap boundaries.

**Signature:**
```python
def validate_physics_at_gap(
    temps_before: Dict[str, float],
    temps_after: Dict[str, float]
) -> Dict:
```

**Inputs:**
- `temps_before`: `{"CHWST": float, "CHWRT": float, "CDWRT": float}` before gap
- `temps_after`: Same structure after gap

**Output:**
```python
{
    "physics_valid": bool,
    "violations": List[str]  # Empty if valid
}
```

**Checks:**
1. CHWST < CHWRT (supply cooler than return)
2. 2°F ≤ (CHWRT - CHWST) ≤ 25°F (Delta-T sanity)
3. CHWRT < CDWRT (evaporator cooler than condenser)

**Example:**
```python
temps_before = {"CHWST": 44.0, "CHWRT": 54.0, "CDWRT": 85.0}
temps_after = {"CHWST": 43.5, "CHWRT": 53.5, "CDWRT": 84.0}
result = validate_physics_at_gap(temps_before, temps_after)
# result: {"physics_valid": True, "violations": []}
```

### 5. `computeGapPenalties(gap_semantics)`

Compute total confidence penalty from gap semantics.

**Signature:**
```python
def compute_gap_penalties(gap_semantics: List[str]) -> float:
```

**Input:**
- `gap_semantics`: List of semantic labels

**Output:**
- Total penalty (sum of individual penalties)

**Penalty Values:**
- `COV_CONSTANT`: 0.0
- `COV_MINOR`: -0.02
- `SENSOR_ANOMALY`: -0.05
- `EXCLUDED`: -0.03
- `UNKNOWN`: -0.01

**Example:**
```python
compute_gap_penalties(["COV_CONSTANT", "COV_MINOR", "SENSOR_ANOMALY"])
# Result: -0.07 (0.0 + -0.02 + -0.05)
```

### 6. `detectExclusionWindowCandidates(per_signal_gaps, timestamps)`

Detect exclusion window candidates from cross-signal gap overlap.

**Signature:**
```python
def detect_exclusion_window_candidates(
    per_signal_gaps: Dict[str, List[Dict]],
    timestamps: Dict[str, pd.Series]
) -> List[Dict]:
```

**Inputs:**
- `per_signal_gaps`: Dict mapping signal_id to list of gap dicts with `gap_class`, `gap_start_idx`, `gap_end_idx`, `duration_hours`
- `timestamps`: Dict mapping signal_id to timestamp Series

**Output:**
- List of exclusion window dicts:
```python
{
    "window_id": "EXW_001",
    "start_ts": Unix timestamp,
    "end_ts": Unix timestamp,
    "duration_hours": float,
    "affected_streams": List[str],
    "affected_streams_count": int
}
```

**Algorithm:**
1. Filter to MAJOR_GAPs ≥8 hours
2. Find temporal overlaps across ≥2 streams
3. Compute union intervals
4. Generate window_id (EXW_XXX)

### 7. `buildStage2AnnotatedDataFrame(df, intervals, gap_classes, ...)`

Add gap metadata columns to signal DataFrame.

**Signature:**
```python
def build_stage2_annotated_dataframe(
    df: pd.DataFrame,
    intervals: pd.Series,
    gap_classes: List[str],
    gap_semantics: List[str],
    gap_confidences: List[float],
    value_changes_pct: List[float],
    exclusion_windows: List[Dict],
    timestamp_col: str = "timestamp"
) -> pd.DataFrame:
```

**Adds 6 Columns:**
1. `gap_before_duration_s`: Interval to previous record (seconds)
2. `gap_before_class`: NORMAL | MINOR_GAP | MAJOR_GAP
3. `gap_before_semantic`: COV_CONSTANT | COV_MINOR | SENSOR_ANOMALY | N/A
4. `gap_before_confidence`: Confidence penalty for this gap
5. `value_changed_relative_pct`: Relative change from previous value (%)
6. `exclusion_window_id`: EXW_XXX if in exclusion window, else None

**Example Output:**
```
timestamp            value  gap_before_duration_s  gap_before_class  gap_before_semantic  ...
2024-01-01 00:00:00  70.0   NaN                    None              None                 ...
2024-01-01 00:15:00  70.0   900.0                  NORMAL            N/A                  ...
2024-01-01 02:00:00  71.5   6300.0                 MAJOR_GAP         COV_MINOR            ...
```

### 8. `buildStage2Metrics(per_signal_summaries, exclusion_windows, ...)`

Build Stage 2 metrics JSON.

**Signature:**
```python
def build_stage2_metrics(
    per_signal_summaries: Dict[str, Dict],
    exclusion_windows: List[Dict],
    stage1_confidence: float,
    aggregate_penalty: float,
    warnings: List[str],
    errors: List[str]
) -> Dict:
```

**Output Structure:**
```json
{
    "stage": "GAPS",
    "per_stream_summary": {
        "CHWST": {
            "total_records": 35574,
            "total_intervals": 35573,
            "interval_stats": {
                "normal_count": 33850,
                "normal_pct": 95.2,
                "minor_gap_count": 1565,
                "minor_gap_pct": 4.4,
                "major_gap_count": 158,
                "major_gap_pct": 0.4
            },
            "gap_semantics": {
                "COV_CONSTANT": 155,
                "COV_MINOR": 62,
                "SENSOR_ANOMALY": 6
            },
            "stream_penalty": -0.07,
            "stream_confidence": 0.93
        },
        "CHWRT": { ... }
    },
    "exclusion_windows": [ ... ],
    "aggregate_penalty": -0.09,
    "stage2_confidence": 0.91,
    "warnings": [ ... ],
    "errors": [ ... ],
    "halt": false,
    "human_approval_required": true
}
```

## Hook: `useStage2GapDetector()`

Orchestration hook that calls all domain functions per signal with logging and error handling.

**Signature:**
```python
def use_stage2_gap_detector(
    signals: Dict[str, pd.DataFrame],
    t_nominal: float = T_NOMINAL_SECONDS,
    timestamp_col: str = "timestamp",
    value_col: str = "value"
) -> Tuple[Dict[str, pd.DataFrame], Dict]:
```

**Inputs:**
- `signals`: Dict mapping signal_id to DataFrame (from Stage 1)
- `t_nominal`: Nominal interval in seconds
- `timestamp_col`: Name of timestamp column
- `value_col`: Name of value column

**Outputs:**
- `annotated_signals`: Dict mapping signal_id to gap-annotated DataFrame
- `metrics`: Stage 2 metrics JSON dict

**Workflow per Signal:**
1. Call `compute_inter_sample_intervals()` → intervals, sorted_values
2. For each interval, call `classify_gap()` → gap_classes
3. For each gap, call `detect_gap_semantic()` → gap_semantics
4. Validate physics at major gaps → physics_violations
5. Call `compute_gap_penalties()` → stream_penalty
6. Call `build_stage2_annotated_dataframe()` → annotated_df

**Cross-Signal Processing:**
7. Call `detect_exclusion_window_candidates()` → exclusion_windows
8. Compute aggregate_penalty (sum across streams)
9. Call `build_stage2_metrics()` → metrics

**Error Handling:**
- Invalid temperature values → Warning, mark as SENSOR_ANOMALY
- Empty DataFrames → Skip signal, add warning
- Physics violations → Add to violations list, apply penalty

**Logging:**
- INFO: Gap detection progress per signal
- WARNING: Physics violations, sensor anomalies
- CRITICAL: Exclusion windows detected (requires human approval)

## CLI Integration

### Command

```bash
python -m src.orchestration.HtdamCLI run_stage2 \
    --stage1-dir output/bartech_phase1/stage1 \
    --output-dir output/bartech_phase1/stage2
```

### Workflow

1. **Load Stage 1 Signals**: Read `stage1_chwst.csv`, `stage1_chwrt.csv`, etc.
2. **Run Gap Detection**: Call `use_stage2_gap_detector()`
3. **Save Outputs**:
   - Gap-annotated CSVs: `stage2_chwst_gaps.csv`, etc.
   - Metrics JSON: `stage2_report.json`
4. **Human Approval Check**: If `human_approval_required == True`, pause and log:
   ```
   ⚠️  PIPELINE PAUSED: Stage 2 detected 2 exclusion windows requiring human review.
   Review stage2_report.json and approve/reject exclusion windows before proceeding to Stage 3.
   ```

### Output Files

**Gap-Annotated CSVs** (`stage2_<param>_gaps.csv`):
```csv
timestamp,value,gap_before_duration_s,gap_before_class,gap_before_semantic,gap_before_confidence,value_changed_relative_pct,exclusion_window_id
2024-01-01 00:00:00,70.0,,,,,
2024-01-01 00:15:00,70.0,900.0,NORMAL,N/A,0.0,0.0,
2024-01-01 02:00:00,71.5,6300.0,MAJOR_GAP,COV_MINOR,-0.02,2.14,
2024-01-02 10:00:00,72.0,115200.0,MAJOR_GAP,SENSOR_ANOMALY,-0.05,0.69,EXW_001
```

**Metrics JSON** (`stage2_report.json`):
See `buildStage2Metrics()` output structure above.

## Interpreting Gap Semantics

### COV_CONSTANT (Penalty: 0.0)

**Interpretation**: Setpoint held constant during gap (expected COV behavior).

**Action**: No confidence reduction. Data is reliable.

**Example**: Chiller CHWST holds at 44.0°F for 3 hours during light-load period.

### COV_MINOR (Penalty: -0.02)

**Interpretation**: Slow drift triggered COV logging (expected behavior, slight concern).

**Action**: Small confidence reduction (2%). Data likely reliable.

**Example**: CDWRT drifts from 82°F to 84°F over 2 hours as ambient temp rises.

### SENSOR_ANOMALY (Penalty: -0.05)

**Interpretation**: Large value jump (>5°C) or physics violation. Possible sensor failure, calibration error, or data corruption.

**Action**: Moderate confidence reduction (5%). Investigate further.

**Example**: CHWRT jumps from 12°C to 18°C across 90-minute gap (impossible without load change).

### N/A (NORMAL intervals)

**Interpretation**: Not a gap (interval ≤22.5 min for 15-min logging).

**Action**: No analysis performed. Full confidence.

## Human Approval Workflow

When `human_approval_required == True`:

### Review Stage 2 Report

Check `stage2_report.json` → `exclusion_windows`:

```json
{
    "exclusion_windows": [
        {
            "window_id": "EXW_001",
            "start_ts": 1704067200,
            "end_ts": 1704096000,
            "duration_hours": 8.0,
            "affected_streams": ["CHWST", "CHWRT", "CDWRT"],
            "affected_streams_count": 3
        }
    ]
}
```

### Decision Options

1. **Approve Exclusion**: Remove window from analysis (Stage 3 will skip these timestamps)
2. **Reject Exclusion**: Keep data (may reduce overall confidence)
3. **Manual Investigation**: Review raw BMS logs, maintenance records, or contact facility

### Update Configuration

If approving exclusion windows, update `htdam_config.json`:

```json
{
    "exclusion_windows": [
        {
            "window_id": "EXW_001",
            "approved": true,
            "reason": "Confirmed chiller maintenance shutdown",
            "approved_by": "walter@example.com",
            "approved_at": "2024-12-08T10:30:00Z"
        }
    ]
}
```

### Resume Pipeline

```bash
python -m src.orchestration.HtdamCLI run --resume-from=stage3
```

## Constants Reference

From `src/domain/htdam/constants.py`:

```python
# Nominal interval (15 minutes)
T_NOMINAL_SECONDS = 900

# Gap classification thresholds
NORMAL_MAX_FACTOR = 1.5      # ≤22.5 min
MINOR_GAP_UPPER_FACTOR = 4.0  # ≤60 min
MAJOR_GAP_LOWER_FACTOR = 4.0  # >60 min

# Gap semantic thresholds
COV_TOLERANCE_RELATIVE_PCT = 0.5  # 0.5%
SENSOR_ANOMALY_JUMP_THRESHOLD = 5.0  # 5°C absolute

# Exclusion window criteria
EXCLUSION_MIN_OVERLAP_STREAMS = 2  # ≥2 signals
EXCLUSION_MIN_DURATION_HOURS = 8   # ≥8 hours

# Confidence penalties
GAP_PENALTIES = {
    "COV_CONSTANT": 0.0,
    "COV_MINOR": -0.02,
    "SENSOR_ANOMALY": -0.05,
    "EXCLUDED": -0.03,
    "UNKNOWN": -0.01,
}
```

## Performance Metrics

**Typical Processing Time** (35,574 records × 5 signals):
- Gap detection: ~0.8 seconds
- Physics validation: ~0.3 seconds
- Exclusion window detection: ~0.1 seconds
- **Total**: ~1.2 seconds

**Memory Usage**: ~15MB per signal (35K records)

## Error Handling

### Warnings (Non-fatal)

- Physics violations at gap boundaries
- Sensor anomalies (large jumps)
- Missing temperature values (use interpolation flag)

### Errors (Fatal)

- Empty input DataFrames (all signals)
- Invalid timestamp formats
- Missing required columns (timestamp, value)

## Next Stage

**Stage 3: Synchronization** (Currently labeled Stage 1.5)

After gap detection and optional exclusion window approval, proceed to Stage 3 to:
1. Interpolate signals to common timeline
2. Apply exclusion windows (if approved)
3. Prepare synchronized 5-signal matrix for Stage 4 COP calculation

**Critical**: Stage 3 MUST run after Stage 2 to preserve gap semantics.

## References

- `htdam/stage-2-gap-detection/HTDAM_Stage2_Impl_Guide.md` - Implementation specification
- `htdam/stage-2-gap-detection/HTDAM_Reorder_Gap-First.md` - Rationale for gap-first architecture
- `src/domain/htdam/constants.py` - Stage 2 constants and thresholds
- `src/hooks/useStage2GapDetector.py` - Orchestration hook implementation

## Version History

- **v1.0** (2024-12-08): Initial implementation with 8 domain functions, 1 hook, CLI integration

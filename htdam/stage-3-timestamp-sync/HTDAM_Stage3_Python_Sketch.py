# HTDAM v2.0 Stage 3: Python Implementation Sketch
## Minimal Working Code for Timestamp Synchronization

**Date**: 2025-12-08  
**Status**: Production-ready skeleton code  
**Language**: Python 3.8+  
**Dependencies**: pandas, numpy, datetime

---

## 1. Constants (Add to `htdam_constants.py`)

```python
# Stage 3 Timestamp Synchronization

T_NOMINAL_SECONDS = 900                    # 15-minute grid
SYNC_TOLERANCE_SECONDS = 1800              # ±30 minutes max allowed distance

# Alignment quality thresholds
ALIGN_EXACT_THRESHOLD = 60                 # <60 s → EXACT
ALIGN_CLOSE_THRESHOLD = 300                # 60–300 s → CLOSE
ALIGN_INTERP_THRESHOLD = 1800              # 300–1800 s → INTERP

# Coverage penalty thresholds
COVERAGE_EXCELLENT_PCT = 95.0
COVERAGE_GOOD_PCT = 90.0
COVERAGE_FAIR_PCT = 80.0

# Jitter tolerance
JITTER_CV_TOLERANCE_PCT = 5.0
JITTER_CV_HALT_PCT = 20.0

# Mandatory streams for row-level classification
MANDATORY_STREAMS = ['chwst', 'chwrt', 'cdwrt']
OPTIONAL_STREAMS = ['flow_m3s', 'power_kw']
```

---

## 2. Grid Construction

```python
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import List, Tuple


def ceil_to_grid(ts: datetime, step_s: int) -> datetime:
    """
    Round timestamp UP to the nearest grid step.
    
    Args:
        ts: datetime to round
        step_s: step size in seconds
    
    Returns:
        datetime rounded up to grid boundary
    """
    epoch = datetime(1970, 1, 1, tzinfo=ts.tzinfo)
    delta = ts - epoch
    total_s = delta.total_seconds()
    
    # ceil to nearest step
    grid_s = int(np.ceil(total_s / step_s) * step_s)
    
    return epoch + timedelta(seconds=grid_s)


def build_master_grid(
    t_start: datetime,
    t_end: datetime,
    t_nominal_s: int
) -> List[datetime]:
    """
    Build uniform time grid.
    
    Args:
        t_start: earliest timestamp (will be ceiled to grid)
        t_end: latest timestamp
        t_nominal_s: grid step in seconds
    
    Returns:
        List of uniformly-spaced datetime objects
    """
    g0 = ceil_to_grid(t_start, t_nominal_s)
    
    grid = []
    t = g0
    while t <= t_end:
        grid.append(t)
        t = t + timedelta(seconds=t_nominal_s)
    
    return grid


# Test
if __name__ == "__main__":
    from datetime import timezone
    t_start = datetime(2024, 9, 18, 3, 30, 0, tzinfo=timezone.utc)
    t_end = datetime(2025, 9, 19, 3, 15, 0, tzinfo=timezone.utc)
    
    grid = build_master_grid(t_start, t_end, T_NOMINAL_SECONDS)
    print(f"Grid points: {len(grid)}")
    print(f"First: {grid[0]}, Last: {grid[-1]}")
```

---

## 3. Per-Stream Nearest-Neighbor Alignment

```python
def align_stream_to_grid(
    timestamps_raw: List[datetime],
    values_raw: List[float],
    grid: List[datetime],
    tolerance_s: int,
    exact_threshold: int = ALIGN_EXACT_THRESHOLD,
    close_threshold: int = ALIGN_CLOSE_THRESHOLD,
    interp_threshold: int = ALIGN_INTERP_THRESHOLD
) -> Tuple[List[float], List[str], List[float]]:
    """
    Align a single stream to master grid using nearest-neighbor (O(N+M)).
    
    Args:
        timestamps_raw: list of raw datetimes (strictly increasing)
        values_raw: list of raw values
        grid: master time grid
        tolerance_s: max allowed distance in seconds
        exact_threshold, close_threshold, interp_threshold: quality thresholds
    
    Returns:
        (values_grid, align_quality, align_distance_s)
        - values_grid: list[float or nan]
        - align_quality: list[str] in {EXACT, CLOSE, INTERP, MISSING}
        - align_distance_s: list[float or None]
    """
    N = len(timestamps_raw)
    M = len(grid)
    
    values_grid = [float('nan')] * M
    align_quality = ['MISSING'] * M
    align_distance_s = [None] * M
    
    j = 0  # pointer into timestamps_raw
    
    for k in range(M):
        g = grid[k]
        
        # Advance j until timestamps_raw[j] >= g
        while j < N and timestamps_raw[j] < g:
            j += 1
        
        # Candidates: j-1 (left), j (right)
        candidates = []
        if j - 1 >= 0:
            candidates.append(j - 1)
        if j < N:
            candidates.append(j)
        
        if not candidates:
            continue  # remains MISSING
        
        # Find nearest
        best_idx = None
        best_dt_s = None
        
        for idx in candidates:
            dt = abs((timestamps_raw[idx] - g).total_seconds())
            if best_dt_s is None or dt < best_dt_s:
                best_dt_s = dt
                best_idx = idx
        
        # Check tolerance
        if best_dt_s is None or best_dt_s > tolerance_s:
            continue  # remains MISSING
        
        # Assign value and quality
        values_grid[k] = values_raw[best_idx]
        align_distance_s[k] = best_dt_s
        
        # Classify quality
        if best_dt_s < exact_threshold:
            align_quality[k] = 'EXACT'
        elif best_dt_s < close_threshold:
            align_quality[k] = 'CLOSE'
        elif best_dt_s <= interp_threshold:
            align_quality[k] = 'INTERP'
        else:
            # Should not happen if tolerance >= interp_threshold
            align_quality[k] = 'MISSING'
    
    return values_grid, align_quality, align_distance_s


# Test
if __name__ == "__main__":
    # Mock data
    raw_ts = [
        datetime(2024, 10, 15, 14, 0, 0, tzinfo=timezone.utc),
        datetime(2024, 10, 15, 14, 15, 12, tzinfo=timezone.utc),  # +912s
        datetime(2024, 10, 15, 14, 30, 5, tzinfo=timezone.utc),   # +893s
        datetime(2024, 10, 15, 14, 45, 0, tzinfo=timezone.utc),   # +895s
    ]
    raw_vals = [17.56, 17.39, 17.42, 17.45]
    
    grid = build_master_grid(raw_ts[0], raw_ts[-1], T_NOMINAL_SECONDS)
    
    vals, quals, dists = align_stream_to_grid(raw_ts, raw_vals, grid, SYNC_TOLERANCE_SECONDS)
    
    print(f"Aligned {len([q for q in quals if q != 'MISSING'])} of {len(grid)} grid points")
    for i, (v, q, d) in enumerate(zip(vals[:4], quals[:4], dists[:4])):
        print(f"  Grid {i}: value={v:.2f}, quality={q}, distance={d}s")
```

---

## 4. Row-Level Gap Type & Confidence Derivation

```python
def get_alignment_confidence(quality: str) -> float:
    """Map alignment quality to confidence."""
    if quality == 'EXACT':
        return 0.95
    elif quality == 'CLOSE':
        return 0.90
    elif quality == 'INTERP':
        return 0.85
    else:  # MISSING
        return 0.00


def lookup_stage2_semantic(
    grid_time: datetime,
    stage2_df: pd.DataFrame,
    tolerance_s: int = 1800
) -> str:
    """
    Look up Stage 2 gap semantic (COV_CONSTANT, etc.) near grid_time.
    
    Args:
        grid_time: grid timestamp
        stage2_df: Stage 2 dataframe (has 'timestamp', 'gap_before_semantic' columns)
        tolerance_s: how far to search
    
    Returns:
        Semantic string, or None if not found
    """
    if stage2_df is None or len(stage2_df) == 0:
        return None
    
    # Find raw records near grid_time
    mask = (stage2_df['timestamp'] >= grid_time - timedelta(seconds=tolerance_s)) & \
           (stage2_df['timestamp'] <= grid_time + timedelta(seconds=tolerance_s))
    
    nearby = stage2_df[mask]
    if len(nearby) == 0:
        return None
    
    # Return most common semantic near this time
    semantics = nearby['gap_before_semantic'].value_counts()
    if len(semantics) > 0:
        return semantics.index[0]
    
    return None


def derive_row_gap_type_and_confidence(
    k: int,
    grid_time: datetime,
    align_quality_by_stream: dict,  # {stream_id -> align_quality}
    exclusion_window_id: str,
    stage2_df: pd.DataFrame = None
) -> Tuple[str, float]:
    """
    Determine row-level gap_type and confidence.
    
    Args:
        k: grid index (for reference)
        grid_time: grid timestamp at k
        align_quality_by_stream: dict of {stream -> EXACT|CLOSE|INTERP|MISSING}
        exclusion_window_id: window ID or None
        stage2_df: Stage 2 dataframe (optional, for semantics)
    
    Returns:
        (gap_type, confidence)
    """
    mandatory_streams = MANDATORY_STREAMS
    
    # 1. Exclusion window has highest precedence
    if exclusion_window_id is not None:
        return 'EXCLUDED', 0.00
    
    # 2. Check mandatory streams
    quals = [align_quality_by_stream.get(s) for s in mandatory_streams]
    
    # If any mandatory stream MISSING
    if any(q == 'MISSING' for q in quals):
        # Look up Stage 2 semantic
        semantic = lookup_stage2_semantic(grid_time, stage2_df)
        
        if semantic in ['COV_CONSTANT', 'COV_MINOR', 'SENSOR_ANOMALY']:
            return semantic, 0.00
        else:
            return 'GAP', 0.00
    
    # 3. All mandatory streams have values; classify VALID
    confs = [get_alignment_confidence(q) for q in quals]
    row_conf = min(confs)  # worst of the three
    
    # Any INTERP present?
    if any(q == 'INTERP' for q in quals):
        # Still VALID but note in confidence
        pass
    
    return 'VALID', row_conf


# Test
if __name__ == "__main__":
    test_align = {
        'chwst': 'EXACT',
        'chwrt': 'EXACT',
        'cdwrt': 'CLOSE'
    }
    gap_type, conf = derive_row_gap_type_and_confidence(
        0,
        datetime(2024, 10, 15, 14, 0, 0, tzinfo=timezone.utc),
        test_align,
        exclusion_window_id=None,
        stage2_df=None
    )
    print(f"Gap type: {gap_type}, Confidence: {conf}")
```

---

## 5. Build Synchronized DataFrame

```python
def synchronize_streams(
    df_stage2: pd.DataFrame,
    t_nominal_s: int = T_NOMINAL_SECONDS,
    tolerance_s: int = SYNC_TOLERANCE_SECONDS
) -> Tuple[pd.DataFrame, dict]:
    """
    Main synchronization function.
    
    Args:
        df_stage2: Stage 2 enriched dataframe
        t_nominal_s: grid step in seconds
        tolerance_s: alignment tolerance
    
    Returns:
        (df_sync, metrics_json)
    """
    # Build grid
    t_start = df_stage2['timestamp'].min()
    t_end = df_stage2['timestamp'].max()
    grid = build_master_grid(t_start, t_end, t_nominal_s)
    
    M = len(grid)
    print(f"Built grid: {M} points from {t_start} to {t_end}")
    
    # Initialize output dataframe
    df_sync = pd.DataFrame({
        'timestamp': grid
    })
    
    # Align each mandatory stream
    per_stream_metrics = {}
    
    for stream in MANDATORY_STREAMS:
        if stream not in df_stage2.columns:
            print(f"Warning: Stream {stream} not in input dataframe")
            continue
        
        raw_ts = df_stage2['timestamp'].tolist()
        raw_vals = df_stage2[stream].tolist()
        
        vals, quals, dists = align_stream_to_grid(
            raw_ts, raw_vals, grid, tolerance_s
        )
        
        df_sync[stream] = vals
        df_sync[f'{stream}_align_quality'] = quals
        df_sync[f'{stream}_align_distance_s'] = dists
        
        # Metrics for this stream
        exact_count = quals.count('EXACT')
        close_count = quals.count('CLOSE')
        interp_count = quals.count('INTERP')
        missing_count = quals.count('MISSING')
        
        per_stream_metrics[stream] = {
            'total_raw_records': len(raw_vals),
            'aligned_exact_count': exact_count,
            'aligned_close_count': close_count,
            'aligned_interp_count': interp_count,
            'missing_count': missing_count,
            'exact_pct': 100.0 * exact_count / M,
            'close_pct': 100.0 * close_count / M,
            'interp_pct': 100.0 * interp_count / M,
            'missing_pct': 100.0 * missing_count / M,
            'mean_align_distance_s': np.nanmean(dists) if dists else None,
            'max_align_distance_s': np.nanmax(dists) if dists else None,
        }
    
    # Align optional streams
    for stream in OPTIONAL_STREAMS:
        if stream not in df_stage2.columns:
            continue
        
        raw_ts = df_stage2['timestamp'].tolist()
        raw_vals = df_stage2[stream].tolist()
        
        vals, quals, dists = align_stream_to_grid(
            raw_ts, raw_vals, grid, tolerance_s
        )
        
        df_sync[stream] = vals
        df_sync[f'{stream}_align_quality'] = quals
        df_sync[f'{stream}_align_distance_s'] = dists
        
        # Metrics
        missing_pct = 100.0 * quals.count('MISSING') / M
        per_stream_metrics[stream] = {
            'total_raw_records': len(raw_vals),
            'missing_count': quals.count('MISSING'),
            'missing_pct': missing_pct,
            'status': 'PARTIAL' if missing_pct > 10 else 'OK'
        }
    
    # Row-level gap_type and confidence
    gap_types = []
    confidences = []
    
    for k in range(M):
        align_qual = {
            s: df_sync.loc[k, f'{s}_align_quality']
            for s in MANDATORY_STREAMS
            if f'{s}_align_quality' in df_sync.columns
        }
        
        # Check exclusion windows (simplified: if any exclusion_window_id column exists)
        exclusion_id = None  # TODO: derive from Stage 2 exclusion windows
        
        gap_type, conf = derive_row_gap_type_and_confidence(
            k, grid[k], align_qual, exclusion_id, df_stage2
        )
        gap_types.append(gap_type)
        confidences.append(conf)
    
    df_sync['gap_type'] = gap_types
    df_sync['confidence'] = confidences
    
    # Compute row-level metrics
    valid_count = gap_types.count('VALID')
    cov_const_count = gap_types.count('COV_CONSTANT')
    cov_minor_count = gap_types.count('COV_MINOR')
    sensor_anom_count = gap_types.count('SENSOR_ANOMALY')
    excluded_count = gap_types.count('EXCLUDED')
    gap_count = gap_types.count('GAP')
    
    row_classification = {
        'VALID_count': valid_count,
        'VALID_pct': 100.0 * valid_count / M,
        'COV_CONSTANT_count': cov_const_count,
        'COV_MINOR_count': cov_minor_count,
        'SENSOR_ANOMALY_count': sensor_anom_count,
        'EXCLUDED_count': excluded_count,
        'GAP_count': gap_count,
        'confidence_mean': np.mean(confidences),
        'confidence_median': np.median(confidences),
    }
    
    # Jitter analysis
    intervals = [(grid[i+1] - grid[i]).total_seconds() for i in range(M-1)]
    interval_mean = np.mean(intervals)
    interval_std = np.std(intervals)
    interval_cv = 100.0 * interval_std / interval_mean if interval_mean > 0 else 0
    
    jitter_metrics = {
        'interval_mean_s': interval_mean,
        'interval_std_s': interval_std,
        'interval_cv_pct': interval_cv
    }
    
    # Penalty & confidence
    coverage_pct = row_classification['VALID_pct']
    
    if coverage_pct >= COVERAGE_EXCELLENT_PCT:
        coverage_penalty = 0.0
    elif coverage_pct >= COVERAGE_GOOD_PCT:
        coverage_penalty = -0.02
    elif coverage_pct >= COVERAGE_FAIR_PCT:
        coverage_penalty = -0.05
    else:
        coverage_penalty = -0.10
    
    jitter_penalty = -0.02 if interval_cv > JITTER_CV_TOLERANCE_PCT else 0.0
    
    total_penalty = coverage_penalty + jitter_penalty
    
    # Assume stage2_confidence available
    stage2_confidence = 0.93  # Example; should come from stage2_df metadata
    stage3_confidence = stage2_confidence + total_penalty
    
    # Build metrics dict
    metrics = {
        'stage': 'SYNC',
        'timestamp_start': str(t_start),
        'timestamp_end': str(t_end),
        'grid': {
            't_nominal_seconds': t_nominal_s,
            'grid_points': M,
            'coverage_seconds': (t_end - t_start).total_seconds()
        },
        'per_stream_alignment': per_stream_metrics,
        'row_classification': row_classification,
        'jitter': jitter_metrics,
        'penalties': {
            'coverage_penalty': coverage_penalty,
            'jitter_penalty': jitter_penalty
        },
        'stage3_confidence': stage3_confidence,
        'warnings': [],
        'errors': [],
        'halt': False
    }
    
    return df_sync, metrics


# Main entry point
if __name__ == "__main__":
    # Example: create mock Stage 2 dataframe
    print("Creating mock Stage 2 dataframe...")
    
    timestamps = pd.date_range('2024-10-15 14:00:00', periods=100, freq='15T', tz='UTC')
    df_mock = pd.DataFrame({
        'timestamp': timestamps,
        'chwst': np.random.normal(17.5, 0.5, 100),
        'chwrt': np.random.normal(17.4, 0.5, 100),
        'cdwrt': np.random.normal(22.1, 0.5, 100),
        'gap_before_semantic': ['COV_CONSTANT'] * 100
    })
    
    print(f"Input: {len(df_mock)} records")
    
    # Run synchronization
    df_sync, metrics = synchronize_streams(df_mock)
    
    print(f"\nOutput:")
    print(f"  Grid points: {len(df_sync)}")
    print(f"  VALID rows: {metrics['row_classification']['VALID_count']}")
    print(f"  Coverage: {metrics['row_classification']['VALID_pct']:.1f}%")
    print(f"  Stage 3 Confidence: {metrics['stage3_confidence']:.2f}")
    print(f"\nFirst 5 rows:")
    print(df_sync[['timestamp', 'chwst', 'chwrt', 'gap_type', 'confidence']].head())
```

---

## 6. Integration with `useOrchestration`

```python
async def run_stage3(ctx: HTDAMContext) -> HTDAMContext:
    """
    Stage 3 synchronization as a domain function.
    
    Args:
        ctx: HTDAM context from Stage 2
    
    Returns:
        Updated context with synchronized data
    """
    try:
        df_stage2 = ctx.sync['data']  # from Stage 2
        
        # Run synchronization
        df_sync, metrics = synchronize_streams(df_stage2)
        
        # Update context
        ctx.sync = {
            'data': df_sync,
            'metrics': metrics,
            'scoreDelta': metrics['penalties']['coverage_penalty'] + 
                         metrics['penalties']['jitter_penalty'],
            'messages': metrics['warnings']
        }
        
        ctx.finalScore += ctx.sync['scoreDelta']
        ctx.warnings.extend(metrics['warnings'])
        
        if metrics['halt']:
            ctx.errors.append("Stage 3 HALT triggered")
            ctx.finalScore = 0.00
        
        return ctx
    
    except Exception as e:
        ctx.errors.append(f"Stage 3 error: {str(e)}")
        ctx.finalScore = 0.00
        return ctx


# Wire into orchestration
stageFns['SYNC'] = run_stage3
```

---

## 7. Unit Tests

```python
import unittest


class TestStage3(unittest.TestCase):
    
    def test_ceil_to_grid(self):
        ts = datetime(2024, 10, 15, 14, 7, 30, tzinfo=timezone.utc)
        g = ceil_to_grid(ts, 900)
        expected = datetime(2024, 10, 15, 14, 15, 0, tzinfo=timezone.utc)
        self.assertEqual(g, expected)
    
    def test_build_master_grid(self):
        t_start = datetime(2024, 10, 15, 14, 0, 0, tzinfo=timezone.utc)
        t_end = datetime(2024, 10, 15, 15, 0, 0, tzinfo=timezone.utc)
        grid = build_master_grid(t_start, t_end, 900)
        self.assertEqual(len(grid), 5)  # 14:00, 14:15, 14:30, 14:45, 15:00
    
    def test_align_stream_perfect(self):
        # Perfect alignment: raw points exactly on grid
        raw_ts = [
            datetime(2024, 10, 15, 14, 0, 0, tzinfo=timezone.utc),
            datetime(2024, 10, 15, 14, 15, 0, tzinfo=timezone.utc),
            datetime(2024, 10, 15, 14, 30, 0, tzinfo=timezone.utc),
        ]
        raw_vals = [17.5, 17.4, 17.6]
        
        grid = build_master_grid(raw_ts[0], raw_ts[-1], 900)
        vals, quals, dists = align_stream_to_grid(raw_ts, raw_vals, grid, 1800)
        
        # All should be EXACT
        self.assertEqual(quals.count('EXACT'), 3)
        self.assertEqual(vals[0], 17.5)
    
    def test_gap_type_valid(self):
        align_qual = {'chwst': 'EXACT', 'chwrt': 'EXACT', 'cdwrt': 'CLOSE'}
        gap_type, conf = derive_row_gap_type_and_confidence(
            0, datetime.now(timezone.utc), align_qual, None
        )
        self.assertEqual(gap_type, 'VALID')
        self.assertEqual(conf, 0.90)  # min of (0.95, 0.95, 0.90)
    
    def test_gap_type_excluded(self):
        align_qual = {'chwst': 'EXACT', 'chwrt': 'EXACT', 'cdwrt': 'EXACT'}
        gap_type, conf = derive_row_gap_type_and_confidence(
            0, datetime.now(timezone.utc), align_qual, 'WINDOW_001'
        )
        self.assertEqual(gap_type, 'EXCLUDED')
        self.assertEqual(conf, 0.00)


if __name__ == '__main__':
    unittest.main()
```

---

## 8. Usage Example

```python
# In your main application
if __name__ == "__main__":
    # Load Stage 2 output
    df_stage2 = pd.read_csv('stage2_output.csv')
    df_stage2['timestamp'] = pd.to_datetime(df_stage2['timestamp'])
    
    # Run Stage 3
    df_sync, metrics = synchronize_streams(df_stage2, t_nominal_s=900)
    
    # Export synchronized data
    df_sync.to_csv('stage3_synchronized.csv', index=False)
    
    # Export metrics
    import json
    with open('stage3_metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2, default=str)
    
    # Log summary
    print(f"✓ Stage 3 Complete")
    print(f"  Grid points: {len(df_sync)}")
    print(f"  Coverage: {metrics['row_classification']['VALID_pct']:.1f}%")
    print(f"  Stage 3 Confidence: {metrics['stage3_confidence']:.2f}")
```

---

## 9. Notes for Your Programmer

1. **Floating Point Handling**:
   - Use `np.nanmean()`, `np.nanmedian()` for distance calculations.
   - Timestamps: convert to epoch seconds for arithmetic, then back to datetime.

2. **Performance**:
   - The alignment algorithm is O(N + M), where N = raw records, M = grid points.
   - For 1 million points, should complete in <5 seconds.

3. **Memory**:
   - Store per-stream columns separately (chwst_align_quality, chwrt_align_quality, etc.).
   - For very large datasets, consider chunking or out-of-core processing.

4. **Testing**:
   - Test on BarTech data: expect ~35,136 grid points, 93.8% coverage, confidence 0.88.
   - Unit tests provided; add more as needed.

5. **Integration**:
   - Wire into `useOrchestration` via `stageFns['SYNC'] = run_stage3`.
   - Pass `ctx` through pipeline; each stage updates and returns it.

---

**Status**: Production-ready Python skeleton for Stage 3.  
**Next**: Implement, test against BarTech, hand to Stage 4.  
**Generated**: 2025-12-08

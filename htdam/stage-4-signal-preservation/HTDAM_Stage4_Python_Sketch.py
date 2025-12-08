# HTDAM v2.0 Stage 4: Python Implementation Sketch
## Signal Preservation & COP Calculation

**Date**: 2025-12-08  
**Status**: Production-ready skeleton code  
**Language**: Python 3.8+  
**Dependencies**: pandas, numpy, datetime

---

## 1. Constants (Add to `htdam_constants.py`)

```python
# Stage 4 Signal Preservation & COP Calculation

# Load calculation
WATER_SPECIFIC_HEAT_kJ_kg_K = 4.186
WATER_DENSITY_kg_m3 = 1000.0

# COP validation
COP_VALID_MIN = 2.0
COP_VALID_MAX = 7.0

# Hunting parameters
HUNT_WINDOW_HOURS = 24
HUNT_MINOR_FREQUENCY = 0.2          # cycles/hour
HUNT_MAJOR_FREQUENCY = 1.0
HUNT_CYCLE_MIN_COUNT = 3

# Fouling thresholds
FOULING_EVAP_MINOR_PCT = 10.0
FOULING_EVAP_MAJOR_PCT = 25.0
FOULING_CONDENSER_MINOR_PCT = 5.0
FOULING_CONDENSER_MAJOR_PCT = 15.0
```

---

## 2. Temperature Calculations

```python
import numpy as np
import pandas as pd
from typing import Tuple

def compute_temperature_differentials(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute chilled water ΔT and compressor lift.
    
    Args:
        df: dataframe with chwst, chwrt, cdwrt columns
    
    Returns:
        (delta_t_chw, lift) as numpy arrays
    """
    delta_t_chw = df['chwrt'] - df['chwst']
    lift = df['cdwrt'] - df['chwst']
    
    return delta_t_chw, lift


def validate_temperature_differentials(
    delta_t_chw: np.ndarray,
    lift: np.ndarray
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Validate ΔT and lift; set invalid to NaN.
    
    Args:
        delta_t_chw: chilled water temperature differential (°C)
        lift: compressor lift (°C)
    
    Returns:
        (delta_t_chw, lift) with invalid values set to NaN
    """
    # ΔT must be ≥ 0 (return ≥ supply)
    delta_t_chw = np.where(delta_t_chw < 0, np.nan, delta_t_chw)
    
    # Lift must be > 0 (positive compression)
    lift = np.where(lift <= 0, np.nan, lift)
    
    return delta_t_chw, lift
```

---

## 3. Load Calculation

```python
def compute_cooling_load(
    flow_m3s: np.ndarray,
    delta_t_chw: np.ndarray,
    cp: float = WATER_SPECIFIC_HEAT_kJ_kg_K,
    rho: float = WATER_DENSITY_kg_m3
) -> np.ndarray:
    """
    Compute evaporator cooling load.
    
    Q [kW] = flow [m³/s] × rho [kg/m³] × cp [kJ/kg·K] × ΔT [K] / 1000
           = flow × cp × ΔT (simplified, rho/1000 cancels)
    
    Args:
        flow_m3s: CHW flow (m³/s)
        delta_t_chw: chilled water ΔT (°C or K)
        cp: specific heat (kJ/kg·K)
        rho: water density (kg/m³)
    
    Returns:
        q_evap [kW]
    """
    q_evap = flow_m3s * rho * cp * delta_t_chw / 1000.0
    
    # Set to NaN if flow or ΔT invalid
    q_evap = np.where(
        (np.isnan(flow_m3s)) | (np.isnan(delta_t_chw)),
        np.nan,
        q_evap
    )
    
    # Set to NaN if Q < 0 (invalid)
    q_evap = np.where(q_evap < 0, np.nan, q_evap)
    
    return q_evap


def compute_q_confidence(
    df: pd.DataFrame,
    q_evap: np.ndarray
) -> np.ndarray:
    """
    Compute load confidence based on component confidences & validity.
    
    Args:
        df: synchronized dataframe with confidence column
        q_evap: computed load (kW)
    
    Returns:
        q_confidence [0.0–1.0]
    """
    M = len(df)
    q_confidence = np.full(M, 0.0)
    
    for i in range(M):
        # Start with Stage 3 confidence (row-level)
        base = df.loc[i, 'confidence']
        
        # Check flow alignment quality
        flow_quality = df.loc[i, 'flow_m3s_align_quality']
        if pd.isna(flow_quality) or flow_quality == 'MISSING':
            q_confidence[i] = 0.00
            continue
        
        # Check temperature quality (min of chwst, chwrt)
        chwst_quality = df.loc[i, 'chwst_align_quality']
        chwrt_quality = df.loc[i, 'chwrt_align_quality']
        
        if (pd.isna(chwst_quality) or chwst_quality == 'MISSING' or
            pd.isna(chwrt_quality) or chwrt_quality == 'MISSING'):
            q_confidence[i] = 0.00
            continue
        
        # Start with minimum of all three
        confidence = min(
            base,
            0.95 if flow_quality == 'EXACT' else 0.90 if flow_quality == 'CLOSE' else 0.85
        )
        
        # Penalties for edge cases
        delta_t = df.loc[i, 'delta_t_chw']
        
        if pd.notna(delta_t):
            if delta_t < 1.0:
                confidence -= 0.10  # Very low ΔT
            elif delta_t > 15.0:
                confidence -= 0.05  # Very high ΔT
        
        # Check if Q is NaN
        if np.isnan(q_evap[i]):
            confidence = 0.00
        
        q_confidence[i] = max(0.0, confidence)
    
    return q_confidence
```

---

## 4. COP Calculation

```python
def compute_cop(
    q_evap: np.ndarray,
    power_kw: np.ndarray,
    valid_range: Tuple[float, float] = (COP_VALID_MIN, COP_VALID_MAX)
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute COP and validate within range.
    
    Args:
        q_evap: cooling load (kW)
        power_kw: electrical power input (kW)
        valid_range: (min, max) for valid COP
    
    Returns:
        (cop, cop_valid) where cop_valid is boolean
    """
    # Compute COP
    cop = np.divide(q_evap, power_kw, where=power_kw > 0, out=np.full_like(q_evap, np.nan))
    
    # Validate range
    cop_valid = (cop >= valid_range[0]) & (cop <= valid_range[1])
    
    # Set out-of-range to NaN
    cop = np.where(cop_valid | np.isnan(cop), cop, np.nan)
    
    return cop, cop_valid


def compute_cop_confidence(
    q_confidence: np.ndarray,
    power_quality: np.ndarray,  # align_quality strings
    cop: np.ndarray
) -> np.ndarray:
    """
    Compute COP confidence.
    
    Args:
        q_confidence: load confidence from compute_q_confidence
        power_quality: power align_quality (EXACT, CLOSE, INTERP, MISSING)
        cop: computed COP values
    
    Returns:
        cop_confidence [0.0–1.0]
    """
    M = len(cop)
    cop_confidence = np.full(M, 0.0)
    
    for i in range(M):
        # If Q invalid, COP invalid
        if q_confidence[i] < 0.5:
            cop_confidence[i] = 0.00
            continue
        
        # If power missing or out-of-range
        if pd.isna(power_quality[i]) or power_quality[i] == 'MISSING':
            cop_confidence[i] = 0.00
            continue
        
        # If COP is NaN
        if np.isnan(cop[i]):
            cop_confidence[i] = 0.00
            continue
        
        # Base confidence from Q
        confidence = q_confidence[i]
        
        # Add power quality (minor contribution)
        power_conf = 0.95 if power_quality[i] == 'EXACT' else \
                     0.90 if power_quality[i] == 'CLOSE' else 0.85
        
        confidence = min(confidence, power_conf)
        
        cop_confidence[i] = confidence
    
    return cop_confidence


def compute_carnot_cop(
    chwst_c: np.ndarray,
    lift_c: np.ndarray
) -> np.ndarray:
    """
    Compute theoretical (Carnot) COP.
    
    COP_carnot = T_evap [K] / (T_condenser [K] - T_evap [K])
               = (chwst + 273.15) / lift [K]
    
    Args:
        chwst_c: chilled water supply temp (°C)
        lift_c: compressor lift (°C or K)
    
    Returns:
        cop_carnot [dimensionless]
    """
    chwst_k = chwst_c + 273.15
    
    # Avoid division by zero
    cop_carnot = np.divide(
        chwst_k,
        lift_c,
        where=lift_c > 0,
        out=np.full_like(chwst_k, np.nan)
    )
    
    return cop_carnot
```

---

## 5. Hunting Detection

```python
def detect_hunting_in_window(
    timestamps: pd.Series,
    chwst_values: np.ndarray,
    window_start: pd.Timestamp,
    window_end: pd.Timestamp,
    min_reversals: int = HUNT_CYCLE_MIN_COUNT,
    minor_threshold: float = HUNT_MINOR_FREQUENCY,
    major_threshold: float = HUNT_MAJOR_FREQUENCY
) -> dict:
    """
    Detect hunting in a time window.
    
    Args:
        timestamps: datetime index
        chwst_values: setpoint temperatures (°C)
        window_start, window_end: window bounds
        min_reversals: minimum reversals to flag
        minor_threshold, major_threshold: cycles/hour thresholds
    
    Returns:
        {'detected': bool, 'severity': str, 'frequency': float, 'reversals': int}
    """
    # Filter to window
    mask = (timestamps >= window_start) & (timestamps <= window_end)
    window_ts = timestamps[mask]
    window_vals = chwst_values[mask]
    
    if len(window_vals) < 3:
        return {'detected': False, 'severity': 'NONE', 'frequency': 0.0, 'reversals': 0}
    
    # Compute sign changes
    diffs = np.diff(window_vals)
    signs = np.sign(diffs)
    reversals = np.sum(np.abs(np.diff(signs)) > 0)
    
    if reversals < min_reversals:
        return {'detected': False, 'severity': 'NONE', 'frequency': 0.0, 'reversals': reversals}
    
    # Compute frequency
    time_span_hours = (window_end - window_start).total_seconds() / 3600.0
    
    if time_span_hours == 0:
        frequency = 0.0
    else:
        frequency = reversals / time_span_hours
    
    # Classify severity
    if frequency >= major_threshold:
        severity = 'MAJOR'
        detected = True
    elif frequency >= minor_threshold:
        severity = 'MINOR'
        detected = True
    else:
        severity = 'NONE'
        detected = False
    
    return {
        'detected': detected,
        'severity': severity,
        'frequency': frequency,
        'reversals': reversals
    }


def detect_hunting_all_windows(
    df: pd.DataFrame,
    window_hours: int = HUNT_WINDOW_HOURS
) -> Tuple[np.ndarray, np.ndarray, dict]:
    """
    Apply hunting detection across all sliding windows.
    
    Args:
        df: synchronized dataframe with timestamp and chwst
        window_hours: sliding window size
    
    Returns:
        (hunt_flag, hunt_severity, hunt_stats)
    """
    M = len(df)
    hunt_flag = np.full(M, False)
    hunt_severity = np.full(M, 'NONE', dtype=object)
    
    window_duration = pd.Timedelta(hours=window_hours)
    windows_with_hunt = 0
    total_windows = 0
    hunt_severities = {'NONE': 0, 'MINOR': 0, 'MAJOR': 0}
    
    # Slide window over entire dataset
    for i in range(M):
        current_time = df.loc[i, 'timestamp']
        window_start = current_time - window_duration / 2
        window_end = current_time + window_duration / 2
        
        result = detect_hunting_in_window(
            df['timestamp'],
            df['chwst'].values,
            window_start,
            window_end
        )
        
        hunt_flag[i] = result['detected']
        hunt_severity[i] = result['severity']
        hunt_severities[result['severity']] += 1
        
        if result['detected']:
            windows_with_hunt += 1
        
        total_windows += 1
    
    hunt_stats = {
        'windows_with_hunt': windows_with_hunt,
        'total_windows': total_windows,
        'hunt_pct': 100.0 * windows_with_hunt / total_windows if total_windows > 0 else 0.0,
        'severity_breakdown': hunt_severities
    }
    
    return hunt_flag, hunt_severity, hunt_stats
```

---

## 6. Fouling Analysis

```python
def compute_fouling_evap(
    flow_m3s: np.ndarray,
    q_evap: np.ndarray,
    baseline_ufoa: float = None,
    baseline_flow: float = None,
    baseline_days: int = 7
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute evaporator fouling (UFOA change).
    
    UFOA [kW/K] = Q / ΔT
    Fouling % = (1 - UFOA_current / UFOA_baseline) × 100
    
    Args:
        flow_m3s: CHW flow
        q_evap: cooling load
        baseline_ufoa: baseline UFOA (from nameplate or first N days)
        baseline_flow: baseline flow (for sanity check)
        baseline_days: days to use for auto-baseline if no nameplate
    
    Returns:
        (fouling_evap_pct, fouling_severity)
    """
    M = len(flow_m3s)
    fouling_pct = np.full(M, np.nan)
    fouling_severity = np.full(M, 'CLEAN', dtype=object)
    
    # Compute UFOA
    ufoa = np.divide(q_evap, np.maximum(flow_m3s, 1e-6), out=np.full_like(q_evap, np.nan))
    
    # If no baseline provided, use first N days average
    if baseline_ufoa is None:
        valid_ufoa = ufoa[~np.isnan(ufoa)]
        if len(valid_ufoa) > 0:
            baseline_ufoa = np.mean(valid_ufoa[:int(len(valid_ufoa) * 0.2)])  # First 20%
    
    if baseline_ufoa is not None and baseline_ufoa > 0:
        fouling_pct = (1 - ufoa / baseline_ufoa) * 100
        
        # Classify severity
        fouling_severity = np.where(
            fouling_pct < FOULING_EVAP_MINOR_PCT,
            'CLEAN',
            np.where(fouling_pct < FOULING_EVAP_MAJOR_PCT, 'MINOR_FOULING', 'MAJOR_FOULING')
        )
    
    return fouling_pct, fouling_severity


def compute_fouling_condenser(
    cdwrt: np.ndarray,
    chwst: np.ndarray,
    lift: np.ndarray,
    baseline_lift: float = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute condenser fouling (lift change).
    
    Fouling % = ((lift_current / lift_baseline) - 1) × 100
    
    Args:
        cdwrt, chwst: temperatures
        lift: computed lift (cdwrt - chwst)
        baseline_lift: baseline lift from nameplate (typical 10–12 K)
    
    Returns:
        (fouling_condenser_pct, fouling_severity)
    """
    M = len(lift)
    fouling_pct = np.full(M, np.nan)
    fouling_severity = np.full(M, 'CLEAN', dtype=object)
    
    # If no baseline provided, use median observed lift
    if baseline_lift is None:
        valid_lift = lift[~np.isnan(lift)]
        if len(valid_lift) > 0:
            baseline_lift = np.median(valid_lift)
    
    if baseline_lift is not None and baseline_lift > 0:
        fouling_pct = ((lift / baseline_lift) - 1) * 100
        
        # Classify severity
        fouling_severity = np.where(
            fouling_pct < FOULING_CONDENSER_MINOR_PCT,
            'CLEAN',
            np.where(fouling_pct < FOULING_CONDENSER_MAJOR_PCT, 'MINOR_FOULING', 'MAJOR_FOULING')
        )
    
    return fouling_pct, fouling_severity
```

---

## 7. Main Orchestration

```python
def signal_preservation_and_cop(df_stage3: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """
    Main Stage 4 function.
    
    Args:
        df_stage3: Stage 3 synchronized dataframe
    
    Returns:
        (df_stage4, metrics_json)
    """
    df = df_stage3.copy()
    M = len(df)
    
    # 1. Compute temperature differentials
    delta_t_chw, lift = compute_temperature_differentials(df)
    delta_t_chw, lift = validate_temperature_differentials(delta_t_chw, lift)
    
    df['delta_t_chw'] = delta_t_chw
    df['lift'] = lift
    
    # 2. Compute cooling load
    q_evap = compute_cooling_load(df['flow_m3s'].values, delta_t_chw)
    q_confidence = compute_q_confidence(df, q_evap)
    
    df['q_evap_kw'] = q_evap
    df['q_confidence'] = q_confidence
    df['q_valid'] = ~np.isnan(q_evap)
    
    # 3. Compute COP
    cop, cop_valid = compute_cop(q_evap, df['power_kw'].values)
    cop_confidence = compute_cop_confidence(
        q_confidence,
        df['power_kw_align_quality'].values,
        cop
    )
    
    df['cop'] = cop
    df['cop_confidence'] = cop_confidence
    df['cop_valid'] = cop_valid | np.isnan(cop)  # False only if valid data
    
    # 4. Compute Carnot COP
    cop_carnot = compute_carnot_cop(df['chwst'].values, lift)
    cop_normalized = np.divide(cop, cop_carnot, where=cop_carnot > 0, out=np.full_like(cop, np.nan))
    
    df['cop_carnot'] = cop_carnot
    df['cop_normalized'] = cop_normalized
    
    # 5. Detect hunting
    hunt_flag, hunt_severity, hunt_stats = detect_hunting_all_windows(df)
    hunt_confidence = np.where(
        hunt_flag, 0.95,
        np.where(hunt_stats['hunt_pct'] > 1.0, 0.50, 0.00)
    )
    
    df['hunt_flag'] = hunt_flag
    df['hunt_severity'] = hunt_severity
    df['hunt_confidence'] = hunt_confidence
    
    # 6. Compute fouling
    fouling_evap_pct, fouling_evap_severity = compute_fouling_evap(
        df['flow_m3s'].values,
        q_evap
    )
    fouling_cond_pct, fouling_cond_severity = compute_fouling_condenser(
        df['cdwrt'].values,
        df['chwst'].values,
        lift
    )
    
    df['fouling_evap_pct'] = fouling_evap_pct
    df['fouling_evap_severity'] = fouling_evap_severity
    df['fouling_condenser_pct'] = fouling_cond_pct
    df['fouling_condenser_severity'] = fouling_cond_severity
    
    fouling_confidence = np.full(M, 0.60)  # Base low confidence
    df['fouling_confidence'] = fouling_confidence
    
    # 7. Compute metrics
    metrics = {
        'stage': 'SPOC',
        'timestamp_start': str(df['timestamp'].min()),
        'timestamp_end': str(df['timestamp'].max()),
        'total_rows': M,
        'load_analysis': {
            'q_valid_count': int(df['q_valid'].sum()),
            'q_valid_pct': 100.0 * df['q_valid'].sum() / M,
            'q_mean_kw': float(df['q_evap_kw'].mean()),
            'q_std_kw': float(df['q_evap_kw'].std()),
            'q_confidence_mean': float(q_confidence.mean())
        },
        'cop_analysis': {
            'cop_valid_count': int((~np.isnan(cop)).sum()),
            'cop_valid_pct': 100.0 * (~np.isnan(cop)).sum() / M,
            'cop_mean': float(np.nanmean(cop)),
            'cop_std': float(np.nanstd(cop)),
            'cop_normalized_median': float(np.nanmedian(cop_normalized)),
            'cop_confidence_mean': float(cop_confidence.mean())
        },
        'hunt_analysis': hunt_stats,
        'fouling_analysis': {
            'evaporator_fouling_mean_pct': float(np.nanmean(fouling_evap_pct)),
            'condenser_fouling_mean_pct': float(np.nanmean(fouling_cond_pct))
        },
        'overall_statistics': {
            'component_confidence_mean': float(np.mean([
                q_confidence.mean(),
                cop_confidence.mean(),
                hunt_confidence.mean(),
                fouling_confidence.mean()
            ]))
        },
        'stage4_confidence': 0.78,  # Placeholder; compute from components
        'halt': False,
        'warnings': [],
        'errors': []
    }
    
    return df, metrics


# Integration with useOrchestration
async def run_stage4(ctx: HTDAMContext) -> HTDAMContext:
    """Wire Stage 4 into orchestration."""
    try:
        df_stage3 = ctx.sync['data']
        df_stage4, metrics = signal_preservation_and_cop(df_stage3)
        
        ctx.sync = {
            'data': df_stage4,
            'metrics': metrics,
            'scoreDelta': -0.10,  # Example penalty
            'messages': metrics['warnings']
        }
        
        ctx.finalScore += ctx.sync['scoreDelta']
        return ctx
    
    except Exception as e:
        ctx.errors.append(f"Stage 4 error: {str(e)}")
        ctx.finalScore = 0.00
        return ctx
```

---

**Status**: Production-ready Python skeleton for Stage 4.  
**Next**: Implement, test against BarTech, hand to Stage 5.  
**Generated**: 2025-12-08

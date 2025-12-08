"""
Pure function: Detect operational state (ACTIVE/STANDBY/OFF) for Stage 1.

ZERO side effects. No logging, no I/O.
"""
from typing import Dict
import pandas as pd

from src.domain.htdam.constants import (
    DELTA_T_ACTIVE_MIN_C,
    COL_CHWST,
    COL_CHWRT,
    COL_FLOW,
    COL_POWER,
)


def detect_operational_state(
    df_converted: pd.DataFrame,
    signal_mappings: Dict[str, str],
    delta_t_threshold_c: float = DELTA_T_ACTIVE_MIN_C,
) -> pd.Series:
    """
    Classify each row as 'ACTIVE', 'STANDBY', or 'OFF' using conservative rules:
    - Compute Delta-T = CHWRT - CHWST (°C)
    - ACTIVE if Delta-T ≥ delta_t_threshold_c
    - OFF if (FLOW and POWER present) and both ≈ 0
    - Otherwise STANDBY

    Args:
        df_converted: DataFrame after unit conversion (canonical cols: chwst, chwrt, flow_m3s, power_kw)
        signal_mappings: BMD mappings (not used directly, kept for interface consistency)
        delta_t_threshold_c: Threshold for ACTIVE classification

    Returns:
        pd.Series of category strings: 'ACTIVE' | 'STANDBY' | 'OFF'
    """
    chwst = df_converted.get(COL_CHWST)
    chwrt = df_converted.get(COL_CHWRT)

    # If temps missing, default to STANDBY
    if chwst is None or chwrt is None:
        return pd.Series(['STANDBY'] * len(df_converted), index=df_converted.index)

    delta_t = chwrt - chwst

    # ACTIVE if Delta-T >= threshold (ignoring NaN)
    active_mask = (delta_t >= float(delta_t_threshold_c))
    
    # OFF detection (both flow and power near-zero, if available)
    flow = df_converted.get(COL_FLOW)
    power = df_converted.get(COL_POWER)
    
    off_mask = pd.Series([False] * len(df_converted), index=df_converted.index)
    if flow is not None and power is not None:
        # Both must be near-zero for OFF
        off_mask = (flow.fillna(0.0) <= 1e-6) & (power.fillna(0.0) <= 1e-3)
    
    # Default to STANDBY, then override with OFF and ACTIVE
    state = pd.Series('STANDBY', index=df_converted.index)
    state[off_mask] = 'OFF'
    state[active_mask] = 'ACTIVE'  # ACTIVE takes precedence over OFF

    return state
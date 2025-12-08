"""
Pure function: Filter DataFrame rows by operational state.

ZERO side effects. No logging, no I/O.
"""
from typing import Iterable
import pandas as pd


def filter_to_states(
    df: pd.DataFrame,
    operational_state: pd.Series,
    allowed_states: Iterable[str] = ('ACTIVE',),
) -> pd.DataFrame:
    """
    Return only rows whose operational_state is in allowed_states.

    Args:
        df: Input DataFrame
        operational_state: Series indexed like df with state strings
        allowed_states: States to include (default: ACTIVE)

    Returns:
        Filtered DataFrame (view copy)
    """
    allowed = set(allowed_states)
    mask = operational_state.astype(str).isin(allowed)
    return df.loc[mask].copy()
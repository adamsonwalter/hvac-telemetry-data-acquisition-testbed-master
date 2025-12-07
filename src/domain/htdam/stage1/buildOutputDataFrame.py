"""
HTDAM Stage 1: Output DataFrame Builder

Pure function for building enhanced DataFrame with dual columns.
ZERO side effects - no logging, no file I/O, no global state.

Output strategy:
- Preserve original columns (never delete/replace)
- Add converted columns with standard names
- Add metadata columns for each signal
- Add overall Stage 1 columns
"""

from typing import Dict
import pandas as pd

from ..constants import (
    SUFFIX_ORIG,
    SUFFIX_ORIG_UNIT,
    SUFFIX_UNIT_CONFIDENCE,
    SUFFIX_PHYSICS_VIOLATIONS_COUNT,
    SUFFIX_PHYSICS_VIOLATIONS_PCT,
    COL_CHWST,
    COL_CHWRT,
    COL_CDWRT,
    COL_FLOW,
    COL_POWER,
    COL_STAGE1_CONFIDENCE,
    COL_STAGE1_PHYSICS_VALID,
    COL_STAGE1_PENALTY,
)


def build_stage1_output_dataframe(
    df_input: pd.DataFrame,
    signal_mappings: Dict[str, str],
    conversions: Dict,
    validations: Dict,
    confidences: Dict,
) -> pd.DataFrame:
    """
    Pure function: Build Stage 1 output DataFrame with dual columns.
    
    Strategy:
    1. Start with copy of input DataFrame (preserve original data)
    2. Add converted columns (chwst, chwrt, cdwrt, flow_m3s, power_kw)
    3. Add metadata columns for each signal:
       - <signal>_orig: Original column name reference
       - <signal>_orig_unit: Original unit
       - <signal>_unit_confidence: Unit confidence score
       - <signal>_physics_violations_count: Number of violations
       - <signal>_physics_violations_pct: Percentage of violations
    4. Add overall Stage 1 columns:
       - stage1_overall_confidence: Min of all channel confidences
       - stage1_physics_valid: Boolean (no HALT conditions)
       - stage1_penalty: Penalty to apply to COP
    
    Args:
        df_input: Input DataFrame with raw signals
        signal_mappings: Dict mapping BMD channels to column names
        conversions: Output from convert_all_units()
        validations: Output from validate_all_physics()
        confidences: Output from compute_all_confidences()
    
    Returns:
        Enhanced DataFrame with all original + new columns
        
    Example:
        >>> df_input = pd.DataFrame({
        ...     "Chiller_1_CHWST": [6, 8, 10],
        ...     "Chiller_1_CHWRT": [12, 14, 16],
        ...     "Chiller_1_CDWRT": [20, 22, 24],
        ...     "Water_Flow": [0.05, 0.08, 0.10],
        ...     "Chiller_Power": [100, 150, 200]
        ... })
        >>> # ... after detection, conversion, validation ...
        >>> df_output = build_stage1_output_dataframe(df_input, mappings, conversions, validations, confidences)
        >>> df_output.columns.tolist()
        ['Chiller_1_CHWST', 'Chiller_1_CHWRT', ..., 'chwst', 'chwrt', ..., 'stage1_overall_confidence', ...]
    """
    # Start with copy of input
    df_output = df_input.copy()
    
    # Add converted columns and metadata
    channel_mapping = {
        "CHWST": COL_CHWST,
        "CHWRT": COL_CHWRT,
        "CDWRT": COL_CDWRT,
        "FLOW": COL_FLOW,
        "POWER": COL_POWER,
    }
    
    for bmd_channel, new_col_name in channel_mapping.items():
        orig_col = signal_mappings.get(bmd_channel)
        
        if orig_col and new_col_name in df_output.columns:
            # Add metadata columns
            base_name = new_col_name.replace("_m3s", "").replace("_kw", "")
            
            # Original column reference
            df_output[f"{base_name}{SUFFIX_ORIG}"] = orig_col
            
            # Original unit
            if bmd_channel in conversions:
                orig_unit = conversions[bmd_channel].get("from_unit", "unknown")
            else:
                orig_unit = "unknown"
            df_output[f"{base_name}{SUFFIX_ORIG_UNIT}"] = orig_unit
            
            # Unit confidence
            if bmd_channel in confidences.get("channel_confidences", {}):
                unit_conf = confidences["channel_confidences"][bmd_channel]
            else:
                unit_conf = 0.0
            df_output[f"{base_name}{SUFFIX_UNIT_CONFIDENCE}"] = unit_conf
            
            # Physics violations count
            violations_count = 0
            violations_pct = 0.0
            
            # Check temperature range violations
            temp_ranges = validations.get("temperature_ranges", {})
            if bmd_channel in temp_ranges:
                violations_count = temp_ranges[bmd_channel].get("violations_count", 0)
                violations_pct = temp_ranges[bmd_channel].get("violations_pct", 0.0)
            
            # Check non-negative violations
            non_neg = validations.get("non_negative", {})
            if bmd_channel in non_neg:
                violations_count = non_neg[bmd_channel].get("negative_count", 0)
                violations_pct = non_neg[bmd_channel].get("negative_pct", 0.0)
            
            df_output[f"{base_name}{SUFFIX_PHYSICS_VIOLATIONS_COUNT}"] = violations_count
            df_output[f"{base_name}{SUFFIX_PHYSICS_VIOLATIONS_PCT}"] = violations_pct
    
    # Add overall Stage 1 columns
    stage1_conf = confidences.get("stage1_confidence", 0.0)
    stage1_penalty = confidences.get("stage1_penalty", -0.05)
    halt_required = validations.get("halt_required", False)
    
    df_output[COL_STAGE1_CONFIDENCE] = stage1_conf
    df_output[COL_STAGE1_PENALTY] = stage1_penalty
    df_output[COL_STAGE1_PHYSICS_VALID] = not halt_required
    
    return df_output

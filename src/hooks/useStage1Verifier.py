"""
HTDAM Stage 1: Orchestration Hook

Hook for orchestrating Stage 1 unit verification and physics validation.
ALL side effects here - logging, progress tracking, error handling.

Calls pure functions from domain layer for business logic.
"""

import logging
from typing import Dict, Optional, Tuple
import pandas as pd

# Import pure functions from domain layer
from src.domain.htdam.stage1.detectUnits import detect_all_units
from src.domain.htdam.stage1.convertUnits import convert_all_units
from src.domain.htdam.stage1.validatePhysics import validate_all_physics
from src.domain.htdam.stage1.computeConfidence import compute_all_confidences
from src.domain.htdam.stage1.buildOutputDataFrame import build_stage1_output_dataframe
from src.domain.htdam.stage1.buildMetrics import build_stage1_metrics
from src.domain.htdam.constants import COL_CHWST, COL_CHWRT

# Set up logger (side effect)
logger = logging.getLogger(__name__)


class Stage1HaltException(Exception):
    """Exception raised when Stage 1 HALT conditions are met."""
    pass


def use_stage1_verifier(
    df: pd.DataFrame,
    signal_mappings: Dict[str, str],
    metadata: Optional[Dict] = None,
    halt_on_violation: bool = True,
) -> Tuple[pd.DataFrame, Dict]:
    """
    Hook: Orchestrate Stage 1 unit verification and physics validation.
    
    This hook contains ALL side effects:
    - Logging
    - Progress tracking
    - Error handling
    - Exception raising (for HALT conditions)
    
    Business logic is delegated to pure functions in domain layer.
    
    Args:
        df: DataFrame with raw BMD signals
        signal_mappings: Dict mapping BMD channels to column names
            e.g., {"CHWST": "Chiller_1_CHWST", "CHWRT": "Chiller_1_CHWRT", ...}
        metadata: Optional dict with per-signal metadata
            e.g., {"Chiller_1_CHWST": {"unit": "°C"}}
        halt_on_violation: If True, raise exception on HALT conditions
    
    Returns:
        (df_enriched, metrics_dict)
        
    Raises:
        Stage1HaltException: If halt_on_violation=True and HALT conditions detected
        
    Example:
        >>> df = pd.DataFrame({
        ...     "CHWST": [6, 8, 10],
        ...     "CHWRT": [12, 14, 16],
        ...     "CDWRT": [20, 22, 24],
        ...     "Flow": [0.05, 0.08, 0.10],
        ...     "Power": [100, 150, 200]
        ... })
        >>> mappings = {
        ...     "CHWST": "CHWST",
        ...     "CHWRT": "CHWRT",
        ...     "CDWRT": "CDWRT",
        ...     "FLOW": "Flow",
        ...     "POWER": "Power"
        ... }
        >>> df_out, metrics = use_stage1_verifier(df, mappings)
        >>> metrics["stage1_confidence"]
        0.7  # Example (depends on data quality)
    """
    logger.info("=" * 80)
    logger.info("HTDAM Stage 1: Unit Verification & Physics Baseline")
    logger.info("=" * 80)
    logger.info(f"Input DataFrame: {len(df)} records, {len(df.columns)} columns")
    logger.info(f"BMD channels to process: {list(signal_mappings.keys())}")
    
    # Step 1: Detect units
    logger.info("\n" + "-" * 80)
    logger.info("Step 1: Unit Detection")
    logger.info("-" * 80)
    
    try:
        detected_units = detect_all_units(df, signal_mappings, metadata)
        
        for channel, (unit, confidence) in detected_units.items():
            if unit:
                logger.info(f"  {channel}: {unit} (confidence: {confidence:.2f})")
            else:
                logger.warning(f"  {channel}: UNKNOWN unit (confidence: {confidence:.2f})")
    
    except Exception as e:
        logger.error(f"Unit detection failed: {e}")
        raise
    
    # Step 2: Convert units
    logger.info("\n" + "-" * 80)
    logger.info("Step 2: Unit Conversion")
    logger.info("-" * 80)
    
    try:
        df_converted, conversions = convert_all_units(df, signal_mappings, detected_units)
        
        for channel, conv in conversions.items():
            if conv.get("status") == "success":
                logger.info(
                    f"  {channel}: {conv['from_unit']} → {conv['to_unit']} "
                    f"(factor: {conv.get('conversion_factor', 'N/A')})"
                )
            elif conv.get("status") == "no_conversion_needed":
                logger.info(f"  {channel}: {conv['from_unit']} (no conversion needed)")
            else:
                logger.error(f"  {channel}: FAILED - {conv.get('error', 'Unknown error')}")
    
    except Exception as e:
        logger.error(f"Unit conversion failed: {e}")
        raise
    
    # Step 3: Validate physics
    logger.info("\n" + "-" * 80)
    logger.info("Step 3: Physics Validation")
    logger.info("-" * 80)
    
    try:
        validations = validate_all_physics(df_converted, signal_mappings)
        
        # Log temperature range violations
        logger.info("  Temperature Ranges:")
        for signal, result in validations.get("temperature_ranges", {}).items():
            if result["violations_count"] == 0:
                logger.info(
                    f"    {signal}: ✓ All samples within valid range "
                    f"({result['valid_min']}-{result['valid_max']}°C)"
                )
            else:
                logger.warning(
                    f"    {signal}: ⚠ {result['violations_count']} violations "
                    f"({result['violations_pct']:.2f}%) outside valid range "
                    f"({result['valid_min']}-{result['valid_max']}°C)"
                )
        
        # Log temperature relationships
        logger.info("  Temperature Relationships:")
        temp_rel = validations.get("temperature_relationships", {})
        if temp_rel:
            if temp_rel["chwrt_lt_chwst_count"] == 0:
                logger.info("    CHWRT ≥ CHWST: ✓ All samples valid")
            else:
                logger.warning(
                    f"    CHWRT < CHWST: ⚠ {temp_rel['chwrt_lt_chwst_count']} violations "
                    f"({temp_rel['chwrt_lt_chwst_pct']:.2f}%)"
                )
            
            if temp_rel["cdwrt_lte_chwst_count"] == 0:
                logger.info("    CDWRT > CHWST: ✓ All samples valid")
            else:
                logger.warning(
                    f"    CDWRT ≤ CHWST: ⚠ {temp_rel['cdwrt_lte_chwst_count']} violations "
                    f"({temp_rel['cdwrt_lte_chwst_pct']:.2f}%)"
                )
        
        # Log non-negative
        logger.info("  Non-negative Constraints:")
        for signal, result in validations.get("non_negative", {}).items():
            if result["negative_count"] == 0:
                logger.info(f"    {signal}: ✓ All samples ≥ 0")
            else:
                logger.warning(
                    f"    {signal}: ⚠ {result['negative_count']} negative values "
                    f"({result['negative_pct']:.2f}%)"
                )
    
    except Exception as e:
        logger.error(f"Physics validation failed: {e}")
        raise
    
    # Step 4: Compute confidence scores
    logger.info("\n" + "-" * 80)
    logger.info("Step 4: Confidence Scoring")
    logger.info("-" * 80)
    
    try:
        confidences = compute_all_confidences(conversions, validations)
        
        logger.info("  Channel Confidences:")
        for channel, conf in confidences["channel_confidences"].items():
            logger.info(f"    {channel}: {conf:.4f}")
        
        logger.info(f"\n  Overall Stage 1 Confidence: {confidences['stage1_confidence']:.4f}")
        logger.info(f"  Stage 1 Penalty: {confidences['stage1_penalty']:.4f}")
    
    except Exception as e:
        logger.error(f"Confidence scoring failed: {e}")
        raise
    
    # Step 5: Check HALT conditions
    logger.info("\n" + "-" * 80)
    logger.info("Step 5: HALT Condition Check")
    logger.info("-" * 80)
    
    if validations.get("halt_required", False):
        halt_reasons = validations.get("halt_reasons", [])
        logger.error("❌ HALT CONDITIONS DETECTED:")
        for reason in halt_reasons:
            logger.error(f"  - {reason}")

        # Attempt salvage if CHWRT<CHWST violations are high (likely standby reversal)
        temp_rel = validations.get("temperature_relationships", {})
        try_salvage = False
        if temp_rel:
            chwrt_lt_pct = float(temp_rel.get("chwrt_lt_chwst_pct", 0.0))
            try_salvage = chwrt_lt_pct >= 50.0  # strong indicator of swapped signals in standby

        if try_salvage:
            logger.info("\nAttempting salvage via state-based filtering (ACTIVE-only)...")
            # Lazy import to keep domain layer independent
            from src.domain.htdam.stage1.detectOperationalState import detect_operational_state
            from src.domain.htdam.stage1.filterByState import filter_to_states

            # 1) Detect operational state on converted data
            op_state = detect_operational_state(df_converted, signal_mappings)

            # 2) Filter to ACTIVE state only
            df_active = filter_to_states(df_converted, op_state, allowed_states=("ACTIVE",))
            
            # Calculate ratio based on valid temperature samples (not total merged rows with NaN)
            valid_temp_mask = df_converted[COL_CHWST].notna() & df_converted[COL_CHWRT].notna()
            n_valid_temps = valid_temp_mask.sum()
            active_ratio = len(df_active) / max(1, n_valid_temps)
            
            logger.info(f"  ACTIVE rows: {len(df_active)} / {n_valid_temps} valid temp samples ({active_ratio*100:.1f}%)")
            logger.info(f"  (Total merged rows: {len(df_converted)}, includes NaN from outer merge)")

            if len(df_active) >= 100 and active_ratio >= 0.10:  # Require >=10% ACTIVE for salvage
                # 3) Re-run physics validation on ACTIVE-only
                validations_active = validate_all_physics(df_active, signal_mappings)
                if not validations_active.get("halt_required", False):
                    logger.info("  ✓ Salvage succeeded: ACTIVE-only data passes physics validation")
                    # Recompute confidences using ACTIVE validations
                    confidences_active = compute_all_confidences(conversions, validations_active)
                    # Build output from ACTIVE-only
                    df_output = build_stage1_output_dataframe(
                        df_active,
                        signal_mappings,
                        conversions,
                        validations_active,
                        confidences_active,
                    )
                    metrics = build_stage1_metrics(df_output, conversions, validations_active, confidences_active)
                    metrics.setdefault('warnings', []).append('Filtered to ACTIVE state due to suspected standby reversal')
                    metrics['salvage'] = True

                    logger.info("\n" + "=" * 80)
                    logger.info("Stage 1 Complete (Salvaged: ACTIVE-only)")
                    logger.info("=" * 80)
                    return df_output, metrics
                else:
                    logger.warning("  Salvage failed: ACTIVE-only still violates physics")
            else:
                logger.warning("  Salvage skipped: insufficient ACTIVE samples or too small ratio")

        if halt_on_violation:
            error_msg = "Stage 1 HALT: " + "; ".join(halt_reasons)
            logger.error(f"\nRaising exception: {error_msg}")
            raise Stage1HaltException(error_msg)
        else:
            logger.warning("HALT conditions detected but halt_on_violation=False, continuing...")
    else:
        logger.info("✓ No HALT conditions detected")
    
    # Step 6: Build output DataFrame
    logger.info("\n" + "-" * 80)
    logger.info("Step 6: Building Output DataFrame")
    logger.info("-" * 80)
    
    try:
        df_output = build_stage1_output_dataframe(
            df_converted,
            signal_mappings,
            conversions,
            validations,
            confidences,
        )
        
        logger.info(f"  Output DataFrame: {len(df_output)} records, {len(df_output.columns)} columns")
        logger.info(f"  Added columns: {len(df_output.columns) - len(df.columns)}")
    
    except Exception as e:
        logger.error(f"Output DataFrame building failed: {e}")
        raise
    
    # Step 7: Build metrics
    logger.info("\n" + "-" * 80)
    logger.info("Step 7: Building Metrics")
    logger.info("-" * 80)
    
    try:
        metrics = build_stage1_metrics(df_output, conversions, validations, confidences)
        
        logger.info(f"  Total records: {metrics['total_records']}")
        logger.info(f"  Warnings: {len(metrics['warnings'])}")
        logger.info(f"  Errors: {len(metrics['errors'])}")
        logger.info(f"  HALT: {metrics['halt']}")
        logger.info(f"  Final Score: {metrics['final_score']:.4f}")
    
    except Exception as e:
        logger.error(f"Metrics building failed: {e}")
        raise
    
    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("Stage 1 Complete")
    logger.info("=" * 80)
    logger.info(f"✓ Unit detection: {len(detected_units)} channels")
    logger.info(f"✓ Unit conversion: {len([c for c in conversions.values() if c.get('status') in ['success', 'no_conversion_needed']])} channels")
    logger.info(f"✓ Physics validation: {len(validations.get('temperature_ranges', {}))} temp ranges, {len(validations.get('non_negative', {}))} non-negative")
    logger.info(f"✓ Confidence scoring: Overall {confidences['stage1_confidence']:.4f}")
    logger.info(f"✓ Output: {len(df_output.columns)} columns total")
    
    if metrics['warnings']:
        logger.warning(f"\n⚠ {len(metrics['warnings'])} warnings - review metrics for details")
    
    if metrics['errors']:
        logger.error(f"\n❌ {len(metrics['errors'])} errors - review metrics for details")
    
    logger.info("=" * 80)
    
    return df_output, metrics

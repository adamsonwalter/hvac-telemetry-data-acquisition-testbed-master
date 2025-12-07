"""
HTDAM Stage 1: Confidence Scoring

Pure functions for computing confidence scores and penalties.
ZERO side effects - no logging, no file I/O, no global state.

Confidence components:
1. Unit confidence: Based on detection quality and conversions
2. Physics confidence: Based on validation violations
3. Overall Stage 1 confidence: Min of all channel confidences
4. Stage 1 penalty: Applied to final COP score based on confidence
"""

from typing import Dict, Tuple
import pandas as pd

from ..constants import (
    PENALTY_MISSING_UNIT,
    PENALTY_AMBIGUOUS_UNIT,
    PENALTY_MANUAL_UNIT,
    PENALTY_OUT_OF_RANGE,
    PENALTY_PHYSICS_VIOLATION,
    PENALTY_STAGE1_HIGH_CONFIDENCE,
    PENALTY_STAGE1_MEDIUM_CONFIDENCE,
    PENALTY_STAGE1_LOW_CONFIDENCE,
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
)


def compute_unit_confidence(
    detected_unit: str,
    detection_confidence: float,
    conversion_applied: bool,
    metadata_provided: bool = False,
) -> float:
    """
    Pure function: Compute confidence score for unit detection/conversion.
    
    Formula: confidence = 1.0 × (1 - penalty_sum)
    
    Penalties:
    - Missing unit (had to infer): -0.30
    - Ambiguous detection (confidence < 0.8): -0.20
    - Manual unit specified: -0.10
    
    Args:
        detected_unit: Unit that was detected (or None)
        detection_confidence: Confidence from detection heuristic (0-1)
        conversion_applied: Whether conversion was needed
        metadata_provided: Whether unit came from metadata (not inferred)
    
    Returns:
        Unit confidence score (0.0-1.0)
        
    Examples:
        >>> # Perfect detection from metadata
        >>> compute_unit_confidence("C", 0.95, False, metadata_provided=True)
        1.0
        
        >>> # Inferred with ambiguous confidence
        >>> compute_unit_confidence("C", 0.70, True, metadata_provided=False)
        0.5  # -0.30 (missing) + -0.20 (ambiguous) = -0.50
    """
    confidence = 1.0
    
    # Missing unit (had to infer from data)
    if detected_unit is None:
        confidence += PENALTY_MISSING_UNIT
    elif not metadata_provided:
        confidence += PENALTY_MISSING_UNIT
    
    # Ambiguous detection (low confidence)
    if detection_confidence < CONFIDENCE_MEDIUM:
        confidence += PENALTY_AMBIGUOUS_UNIT
    
    # Manual override (if metadata was manually added, not from BMS)
    # Note: This would be set by caller if known
    # For now, we don't apply this penalty automatically
    
    return max(0.0, confidence)


def compute_physics_confidence(
    violations_pct: float,
    violation_type: str = "range",
) -> float:
    """
    Pure function: Compute confidence penalty from physics violations.
    
    Formula: confidence = 1.0 - (violations_pct / 100 × 0.10)
    
    Args:
        violations_pct: Percentage of samples violating physics (0-100)
        violation_type: Type of violation ("range", "relationship", "negative")
    
    Returns:
        Physics confidence score (0.0-1.0)
        
    Examples:
        >>> # No violations
        >>> compute_physics_confidence(0.0)
        1.0
        
        >>> # 0.5% violations (under HALT threshold)
        >>> compute_physics_confidence(0.5)
        0.95  # 1.0 - (0.5 / 100 × 0.10) = 0.995 ≈ 0.95
        
        >>> # 5% violations (would HALT, but for calculation)
        >>> compute_physics_confidence(5.0)
        0.5  # 1.0 - (5.0 / 100 × 0.10) = 0.5
    """
    penalty = violations_pct / 100.0 * PENALTY_PHYSICS_VIOLATION
    confidence = max(0.0, 1.0 - penalty)
    return confidence


def compute_channel_confidence(
    unit_confidence: float,
    physics_confidence: float,
) -> float:
    """
    Pure function: Compute overall confidence for a single channel.
    
    Formula: min(unit_confidence, physics_confidence)
    
    Args:
        unit_confidence: Confidence from unit detection/conversion
        physics_confidence: Confidence from physics validation
    
    Returns:
        Channel confidence score (0.0-1.0)
        
    Examples:
        >>> # Both perfect
        >>> compute_channel_confidence(1.0, 1.0)
        1.0
        
        >>> # Limited by unit confidence
        >>> compute_channel_confidence(0.80, 1.0)
        0.8
        
        >>> # Limited by physics confidence
        >>> compute_channel_confidence(1.0, 0.90)
        0.9
    """
    return min(unit_confidence, physics_confidence)


def compute_stage1_confidence(
    channel_confidences: Dict[str, float],
) -> float:
    """
    Pure function: Compute overall Stage 1 confidence.
    
    Formula: min(chwst_conf, chwrt_conf, cdwrt_conf, flow_conf, power_conf)
    
    Rationale: All 5 BMD channels are required, so confidence is limited by
    the weakest link.
    
    Args:
        channel_confidences: Dict mapping channel to confidence
            e.g., {"CHWST": 0.95, "CHWRT": 0.90, "CDWRT": 0.95, "FLOW": 1.0, "POWER": 0.85}
    
    Returns:
        Stage 1 overall confidence (0.0-1.0)
        
    Examples:
        >>> # All channels perfect
        >>> confidences = {
        ...     "CHWST": 1.0, "CHWRT": 1.0, "CDWRT": 1.0,
        ...     "FLOW": 1.0, "POWER": 1.0
        ... }
        >>> compute_stage1_confidence(confidences)
        1.0
        
        >>> # Limited by lowest channel
        >>> confidences = {
        ...     "CHWST": 0.95, "CHWRT": 0.90, "CDWRT": 0.95,
        ...     "FLOW": 1.0, "POWER": 0.80
        ... }
        >>> compute_stage1_confidence(confidences)
        0.8
    """
    if not channel_confidences:
        return 0.0
    
    return min(channel_confidences.values())


def compute_stage1_penalty(
    stage1_confidence: float,
) -> float:
    """
    Pure function: Compute penalty to apply to final COP score.
    
    Penalty thresholds:
    - ≥0.95: No penalty (-0.00)
    - 0.80-0.95: Small penalty (-0.02)
    - <0.80: Medium penalty (-0.05)
    
    Args:
        stage1_confidence: Overall Stage 1 confidence (0.0-1.0)
    
    Returns:
        Penalty value (negative float)
        
    Examples:
        >>> # High confidence, no penalty
        >>> compute_stage1_penalty(0.95)
        -0.0
        
        >>> # Medium confidence, small penalty
        >>> compute_stage1_penalty(0.85)
        -0.02
        
        >>> # Low confidence, medium penalty
        >>> compute_stage1_penalty(0.75)
        -0.05
    """
    if stage1_confidence >= CONFIDENCE_HIGH:
        return PENALTY_STAGE1_HIGH_CONFIDENCE  # -0.00
    elif stage1_confidence >= CONFIDENCE_MEDIUM:
        return PENALTY_STAGE1_MEDIUM_CONFIDENCE  # -0.02
    else:
        return PENALTY_STAGE1_LOW_CONFIDENCE  # -0.05


def compute_all_confidences(
    conversions: Dict,
    validations: Dict,
) -> Dict:
    """
    Pure function: Compute all confidence scores for Stage 1.
    
    Args:
        conversions: Output from convert_all_units()
        validations: Output from validate_all_physics()
    
    Returns:
        Dict with all confidence scores:
        {
            "channel_confidences": {
                "CHWST": float,
                "CHWRT": float,
                "CDWRT": float,
                "FLOW": float,
                "POWER": float,
            },
            "stage1_confidence": float,
            "stage1_penalty": float,
        }
        
    Example:
        >>> conversions = {
        ...     "CHWST": {"detection_confidence": 0.95, "conversion_applied": False},
        ...     "CHWRT": {"detection_confidence": 0.95, "conversion_applied": False},
        ...     "CDWRT": {"detection_confidence": 0.95, "conversion_applied": False},
        ...     "FLOW": {"detection_confidence": 0.80, "conversion_applied": True},
        ...     "POWER": {"detection_confidence": 0.80, "conversion_applied": True},
        ... }
        >>> validations = {
        ...     "temperature_ranges": {
        ...         "CHWST": {"violations_pct": 0.0},
        ...         "CHWRT": {"violations_pct": 0.0},
        ...         "CDWRT": {"violations_pct": 0.0}
        ...     },
        ...     "non_negative": {
        ...         "FLOW": {"negative_pct": 0.0},
        ...         "POWER": {"negative_pct": 0.0}
        ...     }
        ... }
        >>> result = compute_all_confidences(conversions, validations)
        >>> result["stage1_confidence"]
        0.7  # Limited by FLOW/POWER (0.80 detection - 0.30 penalty = 0.50)
    """
    channel_confidences = {}
    
    # Compute confidence for each BMD channel
    bmd_channels = ["CHWST", "CHWRT", "CDWRT", "FLOW", "POWER"]
    
    for channel in bmd_channels:
        # Get unit confidence
        if channel in conversions:
            conv = conversions[channel]
            detected_unit = conv.get("from_unit")
            detection_conf = conv.get("detection_confidence", 0.0)
            conversion_applied = conv.get("conversion_applied", False)
            
            # Check if unit came from metadata (high confidence) or inferred
            metadata_provided = detection_conf >= CONFIDENCE_HIGH
            
            unit_conf = compute_unit_confidence(
                detected_unit,
                detection_conf,
                conversion_applied,
                metadata_provided,
            )
        else:
            unit_conf = 0.0  # Missing channel
        
        # Get physics confidence
        physics_conf = 1.0  # Default: no violations
        
        # Check temperature range violations
        temp_ranges = validations.get("temperature_ranges", {})
        if channel in temp_ranges:
            violations_pct = temp_ranges[channel].get("violations_pct", 0.0)
            physics_conf = min(physics_conf, compute_physics_confidence(violations_pct))
        
        # Check non-negative violations
        non_neg = validations.get("non_negative", {})
        if channel in non_neg:
            violations_pct = non_neg[channel].get("negative_pct", 0.0)
            physics_conf = min(physics_conf, compute_physics_confidence(violations_pct))
        
        # Compute channel confidence
        channel_confidences[channel] = compute_channel_confidence(unit_conf, physics_conf)
    
    # Compute overall Stage 1 confidence
    stage1_conf = compute_stage1_confidence(channel_confidences)
    
    # Compute Stage 1 penalty
    stage1_penalty = compute_stage1_penalty(stage1_conf)
    
    return {
        "channel_confidences": channel_confidences,
        "stage1_confidence": stage1_conf,
        "stage1_penalty": stage1_penalty,
    }

"""
HTDAM Stage 1: Metrics Builder

Pure function for building JSON-serializable metrics dict.
ZERO side effects - no logging, no file I/O, no global state.

Metrics structure:
- Stage identifier
- Record counts
- Unit conversion summary
- Physics validation summary
- Confidence scores
- Penalty
- Warnings and errors
- HALT flag
"""

from typing import Dict, List
import pandas as pd


def build_stage1_metrics(
    df: pd.DataFrame,
    conversions: Dict,
    validations: Dict,
    confidences: Dict,
) -> Dict:
    """
    Pure function: Build Stage 1 metrics dictionary.
    
    Args:
        df: Output DataFrame (for record count)
        conversions: Output from convert_all_units()
        validations: Output from validate_all_physics()
        confidences: Output from compute_all_confidences()
    
    Returns:
        JSON-serializable dict with all Stage 1 metrics
        
    Example output:
        {
            "stage": "UNITS",
            "total_records": 1000,
            "unit_conversions": {
                "CHWST": {"from_unit": "C", "to_unit": "C", "conversion_applied": false},
                "CHWRT": {"from_unit": "C", "to_unit": "C", "conversion_applied": false},
                "CDWRT": {"from_unit": "C", "to_unit": "C", "conversion_applied": false},
                "FLOW": {"from_unit": "m3/s", "to_unit": "m3/s", "conversion_applied": false},
                "POWER": {"from_unit": "kW", "to_unit": "kW", "conversion_applied": false}
            },
            "physics_violations": {
                "temperature_ranges": {
                    "CHWST": {"violations_count": 0, "violations_pct": 0.0},
                    "CHWRT": {"violations_count": 0, "violations_pct": 0.0},
                    "CDWRT": {"violations_count": 0, "violations_pct": 0.0}
                },
                "temperature_relationships": {
                    "chwrt_lt_chwst_count": 0,
                    "chwrt_lt_chwst_pct": 0.0,
                    "cdwrt_lte_chwst_count": 0,
                    "cdwrt_lte_chwst_pct": 0.0
                },
                "non_negative": {
                    "FLOW": {"negative_count": 0, "negative_pct": 0.0},
                    "POWER": {"negative_count": 0, "negative_pct": 0.0}
                }
            },
            "confidence_scores": {
                "CHWST": 1.0,
                "CHWRT": 1.0,
                "CDWRT": 1.0,
                "FLOW": 1.0,
                "POWER": 1.0,
                "overall": 1.0
            },
            "penalty": -0.0,
            "final_score": 1.0,
            "warnings": [],
            "errors": [],
            "halt": false
        }
    """
    metrics = {
        "stage": "UNITS",
        "total_records": len(df),
        "unit_conversions": {},
        "physics_violations": {},
        "confidence_scores": {},
        "penalty": 0.0,
        "final_score": 0.0,
        "warnings": [],
        "errors": [],
        "halt": False,
    }
    
    # Unit conversions summary
    for channel, conv in conversions.items():
        if conv.get("status") == "success" or conv.get("status") == "no_conversion_needed":
            metrics["unit_conversions"][channel] = {
                "from_unit": conv.get("from_unit", "unknown"),
                "to_unit": conv.get("to_unit", "unknown"),
                "conversion_applied": conv.get("conversion_applied", False),
                "detection_confidence": conv.get("detection_confidence", 0.0),
            }
        else:
            # Conversion failed
            metrics["unit_conversions"][channel] = {
                "status": conv.get("status", "error"),
                "error": conv.get("error", "Unknown error"),
            }
            metrics["errors"].append(
                f"{channel}: {conv.get('error', 'Unit conversion failed')}"
            )
    
    # Physics violations summary
    metrics["physics_violations"] = {
        "temperature_ranges": {},
        "temperature_relationships": {},
        "non_negative": {},
    }
    
    # Temperature ranges
    for signal, result in validations.get("temperature_ranges", {}).items():
        metrics["physics_violations"]["temperature_ranges"][signal] = {
            "violations_count": result.get("violations_count", 0),
            "violations_pct": result.get("violations_pct", 0.0),
            "valid_min": result.get("valid_min", 0.0),
            "valid_max": result.get("valid_max", 0.0),
            "actual_min": result.get("actual_min", 0.0),
            "actual_max": result.get("actual_max", 0.0),
        }
        
        # Add warning if violations present
        if result.get("violations_pct", 0.0) > 0.0:
            metrics["warnings"].append(
                f"{signal}: {result['violations_pct']:.2f}% of samples outside valid range "
                f"({result['valid_min']}-{result['valid_max']}°C)"
            )
    
    # Temperature relationships
    temp_rel = validations.get("temperature_relationships", {})
    if temp_rel:
        metrics["physics_violations"]["temperature_relationships"] = {
            "chwrt_lt_chwst_count": temp_rel.get("chwrt_lt_chwst_count", 0),
            "chwrt_lt_chwst_pct": temp_rel.get("chwrt_lt_chwst_pct", 0.0),
            "cdwrt_lte_chwst_count": temp_rel.get("cdwrt_lte_chwst_count", 0),
            "cdwrt_lte_chwst_pct": temp_rel.get("cdwrt_lte_chwst_pct", 0.0),
        }
        
        # Add warnings
        if temp_rel.get("chwrt_lt_chwst_pct", 0.0) > 0.0:
            metrics["warnings"].append(
                f"CHWRT < CHWST in {temp_rel['chwrt_lt_chwst_pct']:.2f}% of samples "
                f"(violates physics: return temp must be ≥ supply temp)"
            )
        if temp_rel.get("cdwrt_lte_chwst_pct", 0.0) > 0.0:
            metrics["warnings"].append(
                f"CDWRT ≤ CHWST in {temp_rel['cdwrt_lte_chwst_pct']:.2f}% of samples "
                f"(violates physics: condenser return must be > chilled water supply)"
            )
    
    # Non-negative
    for signal, result in validations.get("non_negative", {}).items():
        metrics["physics_violations"]["non_negative"][signal] = {
            "negative_count": result.get("negative_count", 0),
            "negative_pct": result.get("negative_pct", 0.0),
            "actual_min": result.get("actual_min", 0.0),
        }
        
        # Add warning if negative values present
        if result.get("negative_count", 0) > 0:
            metrics["warnings"].append(
                f"{signal}: {result['negative_count']} negative values "
                f"({result['negative_pct']:.2f}% of samples)"
            )
    
    # Confidence scores
    channel_confidences = confidences.get("channel_confidences", {})
    for channel, conf in channel_confidences.items():
        metrics["confidence_scores"][channel] = round(conf, 4)
    
    metrics["confidence_scores"]["overall"] = round(
        confidences.get("stage1_confidence", 0.0), 4
    )
    
    # Penalty and final score
    metrics["penalty"] = round(confidences.get("stage1_penalty", -0.05), 4)
    metrics["final_score"] = round(
        confidences.get("stage1_confidence", 0.0) + metrics["penalty"], 4
    )
    
    # HALT flag and reasons
    metrics["halt"] = validations.get("halt_required", False)
    if metrics["halt"]:
        halt_reasons = validations.get("halt_reasons", [])
        for reason in halt_reasons:
            metrics["errors"].append(f"HALT: {reason}")
    
    return metrics

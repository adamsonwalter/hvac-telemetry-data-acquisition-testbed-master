#!/usr/bin/env python3
"""
Hook: Orchestrate signal unit validation.

This module contains ALL side effects:
- Logging
- Error handling
- Progress reporting

Pure functions are called from domain layer.
"""

import logging
import pandas as pd
from typing import Dict, List, Optional

# Import pure functions
from ..domain.validator.detectLoadVsKw import detect_load_vs_kw
from ..domain.validator.detectModeChanges import detect_mode_changes
from ..domain.validator.detectKwhConfusion import detect_kwh_confusion
from ..domain.validator.validateLoadPowerCorr import validate_load_power_correlation
from ..domain.validator.formatValidationReport import format_validation_report

logger = logging.getLogger(__name__)


def use_signal_validator(
    signal_series: pd.Series,
    signal_name: str,
    equipment_type: str,
    nameplate_kw: Optional[float] = None,
    power_series: Optional[pd.Series] = None
) -> Dict:
    """
    Hook: Orchestrate comprehensive signal validation.
    
    ORCHESTRATION HOOK - CONTAINS SIDE EFFECTS
    - Logging: progress and results
    - Error handling: validates inputs
    - Calls multiple pure validation functions
    
    Args:
        signal_series: Raw signal data
        signal_name: Name for logging
        equipment_type: 'chiller', 'pump', 'fan', 'tower', etc.
        nameplate_kw: Equipment nameplate capacity (optional)
        power_series: Corresponding power signal (optional)
    
    Returns:
        Validation result dictionary with:
        - signal_name, equipment_type
        - likely_unit, confidence
        - issues, recommendations
        - use_for_cop, use_for_energy
    
    Examples:
        >>> import pandas as pd
        >>> signal = pd.Series([0, 50, 100])
        >>> result = use_signal_validator(signal, 'Pump_Speed', 'pump')
        >>> result['likely_unit']
        'LOAD_PERCENT'
    """
    # Side effect: Log start
    logger.info(f"Validating signal: {signal_name} ({equipment_type})")
    
    result = {
        "signal_name": signal_name,
        "equipment_type": equipment_type,
        "likely_unit": "UNKNOWN",
        "confidence": "low",
        "issues": [],
        "recommendations": [],
        "use_for_cop": False,
        "use_for_energy": False,
    }
    
    # Clean data
    s = signal_series.dropna()
    if len(s) == 0:
        logger.warning(f"{signal_name}: No valid data points")
        result["issues"].append("No valid data points")
        return result
    
    logger.info(f"Processing {len(s)} valid data points")
    
    # Call pure function: Load vs kW detection
    logger.info(f"Running Load vs kW detection...")
    load_vs_kw = detect_load_vs_kw(s, nameplate_kw, equipment_type)
    result.update(load_vs_kw)
    logger.info(f"✓ Detected unit: {result['likely_unit']} (confidence: {result['confidence']})")
    
    # Call pure function: Mode changes
    logger.info(f"Checking for mode changes...")
    mode_changes = detect_mode_changes(s, signal_name)
    if mode_changes["has_mode_changes"]:
        logger.warning(f"⚠️  Mode changes detected in {signal_name}")
        result["issues"].append(mode_changes["description"])
        result["recommendations"].extend(mode_changes["recommendations"])
    else:
        logger.info(f"✓ No mode changes detected")
    
    # Call pure function: kWh confusion
    if power_series is not None:
        logger.info(f"Checking for kW/kWh confusion...")
        kwh_confusion = detect_kwh_confusion(s, power_series, signal_name)
        if kwh_confusion["is_confused"]:
            logger.error(f"🚨 kW/kWh confusion detected in {signal_name}")
            result["issues"].append(kwh_confusion["description"])
            result["recommendations"].extend(kwh_confusion["recommendations"])
        else:
            logger.info(f"✓ No kW/kWh confusion detected")
    
    # Call pure function: Correlation validation
    if power_series is not None and result["likely_unit"] in ["LOAD_PERCENT", "LOAD_FRACTION"]:
        logger.info(f"Validating load-power correlation...")
        correlation_check = validate_load_power_correlation(s, power_series, nameplate_kw)
        result["correlation_analysis"] = correlation_check
        
        if correlation_check["status"] == "FAIL":
            logger.error(f"🚨 Correlation check failed for {signal_name}")
            result["issues"].append(correlation_check["reason"])
        elif correlation_check["status"] == "PASS":
            logger.info(f"✓ Correlation check passed: {correlation_check.get('note', '')}")
        elif correlation_check["status"] == "WARNING":
            logger.warning(f"⚠️  Correlation warning: {correlation_check.get('note', '')}")
    
    # Final recommendations
    result["use_for_cop"] = (
        result["likely_unit"] in ["LOAD_PERCENT", "LOAD_FRACTION"] 
        and result["confidence"] in ["high", "medium"]
        and len(result["issues"]) == 0
    )
    result["use_for_energy"] = (
        result["likely_unit"] == "REAL_KW"
        and result["confidence"] in ["high", "medium"]
    )
    
    # Side effect: Log final result
    logger.info(f"Validation complete for {signal_name}:")
    logger.info(f"  use_for_cop={result['use_for_cop']}")
    logger.info(f"  use_for_energy={result['use_for_energy']}")
    
    if result["issues"]:
        logger.warning(f"  {len(result['issues'])} issues found")
    
    return result


def validate_multiple_signals(signals: List[Dict]) -> str:
    """
    Hook: Validate multiple signals and generate report.
    
    ORCHESTRATION HOOK - CONTAINS SIDE EFFECTS
    - Logging: batch progress
    - Calls validation hook for each signal
    - Calls pure report formatter
    
    Args:
        signals: List of signal configuration dicts, each with:
            - signal_series, signal_name, equipment_type
            - nameplate_kw (optional), power_series (optional)
    
    Returns:
        Formatted validation report string
    
    Examples:
        >>> signals = [{'signal_series': pd.Series([0,50,100]),
        ...             'signal_name': 'Pump_1',
        ...             'equipment_type': 'pump'}]
        >>> report = validate_multiple_signals(signals)
    """
    logger.info("=" * 80)
    logger.info(f"Starting batch validation: {len(signals)} signals")
    logger.info("=" * 80)
    
    results = []
    for i, signal_config in enumerate(signals, 1):
        logger.info(f"Processing signal {i}/{len(signals)}")
        result = use_signal_validator(**signal_config)
        results.append(result)
    
    # Call pure function: Format report
    logger.info("Generating validation report...")
    report = format_validation_report(results)
    
    logger.info("=" * 80)
    logger.info(f"Batch validation complete: {len(results)} signals processed")
    logger.info("=" * 80)
    
    return report

#!/usr/bin/env python3
"""
Pure function: Format validation report.

This module contains ZERO side effects:
- NO logging
- NO file I/O
- NO global state
- Pure string formatting only
"""

from typing import List, Dict


def format_validation_report(results: List[Dict]) -> str:
    """
    Generate human-readable validation report from results.
    
    PURE FUNCTION - NO SIDE EFFECTS
    - Deterministic: same input → same output
    - No logging or file I/O
    - Just string formatting
    
    Args:
        results: List of validation result dictionaries
    
    Returns:
        Formatted report string
    
    Examples:
        >>> results = [{
        ...     'signal_name': 'Test_Signal',
        ...     'equipment_type': 'chiller',
        ...     'likely_unit': 'LOAD_PERCENT',
        ...     'confidence': 'high',
        ...     'issues': [],
        ...     'recommendations': []
        ... }]
        >>> report = format_validation_report(results)
        >>> 'SIGNAL UNIT VALIDATION REPORT' in report
        True
    """
    report = []
    report.append("=" * 80)
    report.append("SIGNAL UNIT VALIDATION REPORT")
    report.append("=" * 80)
    report.append("")
    
    # Group by status
    critical = [r for r in results if "🚨" in str(r.get("issues", []))]
    warnings = [r for r in results if "⚠️" in str(r.get("issues", []))]
    passed = [r for r in results if not r.get("issues")]
    
    if critical:
        report.append("🚨 CRITICAL ISSUES (Block Analytics):")
        report.append("-" * 80)
        for r in critical:
            report.append(f"  {r['signal_name']} ({r['equipment_type']})")
            report.append(f"    Detected Unit: {r['likely_unit']} (Confidence: {r['confidence']})")
            for issue in r["issues"]:
                report.append(f"    {issue}")
            for rec in r.get("recommendations", []):
                report.append(f"    {rec}")
            report.append("")
    
    if warnings:
        report.append("⚠️  WARNINGS (Review Before Use):")
        report.append("-" * 80)
        for r in warnings:
            report.append(f"  {r['signal_name']} ({r['equipment_type']})")
            report.append(f"    Detected Unit: {r['likely_unit']} (Confidence: {r['confidence']})")
            for issue in r["issues"]:
                report.append(f"    {issue}")
            report.append("")
    
    if passed:
        report.append("✅ VALIDATED SIGNALS:")
        report.append("-" * 80)
        for r in passed:
            report.append(f"  {r['signal_name']}: {r['likely_unit']} (Confidence: {r['confidence']})")
    
    report.append("")
    report.append("=" * 80)
    report.append(f"Summary: {len(passed)} passed, {len(warnings)} warnings, {len(critical)} critical")
    report.append("=" * 80)
    
    return "\n".join(report)

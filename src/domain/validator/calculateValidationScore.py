#!/usr/bin/env python3
"""
Pure function: Calculate validation score and provide recommendations.

This module contains ZERO side effects:
- NO logging
- NO file I/O
- NO global state
- Pure scoring logic only

Provides actionable guidance to users about signal quality and next steps.
"""

from typing import Dict, List, Tuple
from enum import Enum


class ValidationScore(Enum):
    """Validation score levels."""
    EXCELLENT = "EXCELLENT"      # 90-100 points
    GOOD = "GOOD"               # 75-89 points
    ACCEPTABLE = "ACCEPTABLE"   # 60-74 points
    POOR = "POOR"               # 40-59 points
    TERMINAL = "TERMINAL"       # 0-39 points


def calculate_validation_score(metadata: Dict) -> Tuple[int, ValidationScore, List[str], List[str]]:
    """
    Calculate validation score (0-100) for a decoded BMS signal.
    
    PURE FUNCTION - NO SIDE EFFECTS
    - Deterministic: same metadata → same score
    - No logging or file I/O
    - Pure scoring logic
    
    Scoring Rubric:
    - Detection type: 0-40 points (based on confidence)
    - Data completeness: 0-20 points
    - Range sanity: 0-20 points
    - Statistical quality: 0-20 points
    
    Args:
        metadata: Decoded signal metadata from normalize_percent_signal()
            Required keys:
            - detected_type: str
            - confidence: str ('high', 'medium', 'low', 'very_low')
            - original_count: int
            - original_min: float
            - original_max: float
            - original_mean: float
            - p995: float
            - p005: float
    
    Returns:
        Tuple of:
        - score: int (0-100)
        - level: ValidationScore enum
        - issues: List[str] (problems found)
        - recommendations: List[str] (actionable next steps)
    
    Examples:
        >>> metadata = {
        ...     'detected_type': 'percentage_0_100',
        ...     'confidence': 'high',
        ...     'original_count': 1000,
        ...     'original_min': 0.0,
        ...     'original_max': 95.0,
        ...     'original_mean': 45.0,
        ...     'p995': 94.0,
        ...     'p005': 0.5
        ... }
        >>> score, level, issues, recs = calculate_validation_score(metadata)
        >>> score >= 90
        True
        >>> level == ValidationScore.EXCELLENT
        True
    """
    score = 0
    issues = []
    recommendations = []
    
    # Category 1: Detection Confidence (0-40 points)
    confidence = metadata.get('confidence', 'unknown').lower()
    detected_type = metadata.get('detected_type', 'unknown')
    
    if confidence == 'high':
        score += 40
    elif confidence == 'medium':
        score += 30
        issues.append("Medium confidence detection - may need verification")
        recommendations.append("✓ Verify with BMS documentation or nameplate")
    elif confidence == 'low':
        score += 15
        issues.append("⚠️  Low confidence detection")
        recommendations.append("⚠️  REQUIRED: Verify encoding with BMS vendor documentation")
        recommendations.append("⚠️  Cross-check with equipment nameplate or trending graphs")
    else:  # very_low or unknown
        score += 5
        issues.append("🚨 Very low confidence - uncertain detection")
        recommendations.append("🚨 CRITICAL: Manual verification required before using data")
        recommendations.append("🚨 Check BMS point configuration and raw data samples")
    
    # Bonus for well-known encodings
    high_quality_types = ['percentage_0_100', 'fraction_0_1', 'counts_10000_0.01pct', 
                          'counts_1000_0.1pct', 'counts_100000_siemens']
    if detected_type in high_quality_types:
        # Already captured in confidence score
        pass
    elif detected_type in ['analog_unscaled', 'raw_counts_large']:
        issues.append("Dynamic scaling used (percentile-based)")
        recommendations.append("✓ Validate normalized output against expected range")
    elif detected_type == 'percentile_range_normalized':
        issues.append("Fallback normalization applied")
        recommendations.append("⚠️  Signal has unusual characteristics - verify data quality")
    elif detected_type == 'fallback_divide_100':
        issues.append("🚨 Desperate fallback normalization")
        recommendations.append("🚨 Signal pattern unrecognized - likely incorrect encoding")
    
    # Category 2: Data Completeness (0-20 points)
    original_count = metadata.get('original_count', 0)
    
    if original_count >= 1000:
        score += 20
    elif original_count >= 500:
        score += 18
        issues.append("Moderate sample size")
        recommendations.append("✓ Consider collecting more data for robust statistics")
    elif original_count >= 100:
        score += 15
        issues.append("⚠️  Small sample size")
        recommendations.append("⚠️  Collect at least 500 samples for reliable analysis")
    elif original_count >= 50:
        score += 10
        issues.append("⚠️  Very small sample size")
        recommendations.append("🚨 INSUFFICIENT DATA: Collect at least 500-1000 samples")
    elif original_count > 0:
        score += 5
        issues.append("🚨 Critically low sample size")
        recommendations.append("🚨 TERMINAL: Cannot validate with <50 samples - collect more data")
    else:
        score += 0
        issues.append("🚨 No valid data points")
        recommendations.append("🚨 TERMINAL: No data available - check BMS connectivity")
    
    # Category 3: Range Sanity (0-20 points)
    original_min = metadata.get('original_min')
    original_max = metadata.get('original_max')
    original_mean = metadata.get('original_mean')
    
    if original_min is not None and original_max is not None:
        range_span = original_max - original_min
        
        if range_span > 0:
            score += 15  # Has variation
            
            # Check for stuck/flat signals
            if range_span < 1.0 and detected_type not in ['fraction_0_1']:
                issues.append("⚠️  Very low variation detected")
                recommendations.append("⚠️  Signal may be stuck or equipment not operating")
                recommendations.append("⚠️  Verify equipment is running and sensor is connected")
            else:
                score += 5  # Good variation
            
            # Check for unrealistic averages (equipment rarely at max)
            if original_mean is not None and range_span > 0:
                avg_position = (original_mean - original_min) / range_span
                if avg_position > 0.85:
                    issues.append("Unusually high average load")
                    recommendations.append("✓ Verify equipment typically operates at high loads")
        else:
            score += 5
            issues.append("🚨 No variation in signal (flat/stuck)")
            recommendations.append("🚨 CRITICAL: Signal appears stuck - check sensor connection")
            recommendations.append("🚨 Verify equipment is operational and trending is active")
    else:
        issues.append("🚨 Missing range statistics")
        recommendations.append("🚨 TERMINAL: Cannot validate without min/max values")
    
    # Category 4: Statistical Quality (0-20 points)
    p995 = metadata.get('p995')
    p005 = metadata.get('p005')
    
    if p995 is not None and p005 is not None:
        # Check for reasonable percentile spread
        percentile_range = p995 - p005
        
        if original_max is not None and original_min is not None:
            full_range = original_max - original_min
            
            if full_range > 0:
                coverage = percentile_range / full_range
                
                if coverage >= 0.80:
                    score += 20  # Good data coverage
                elif coverage >= 0.60:
                    score += 15
                    issues.append("Moderate data spread")
                    recommendations.append("✓ Signal shows reasonable variation")
                elif coverage >= 0.30:
                    score += 10
                    issues.append("⚠️  Limited data spread")
                    recommendations.append("⚠️  Equipment may not be exercising full range")
                    recommendations.append("⚠️  Consider collecting data during peak operations")
                else:
                    score += 5
                    issues.append("⚠️  Very limited data spread")
                    recommendations.append("🚨 Signal confined to narrow range - verify equipment operation")
            else:
                score += 5
                issues.append("🚨 Zero range span")
        else:
            score += 10  # Partial credit
    else:
        issues.append("🚨 Missing percentile statistics")
        recommendations.append("🚨 TERMINAL: Cannot assess data quality without percentiles")
    
    # Determine validation level
    if score >= 90:
        level = ValidationScore.EXCELLENT
        if not recommendations:
            recommendations.append("✅ Signal ready for production analytics")
            recommendations.append("✅ No action required - proceed with confidence")
    elif score >= 75:
        level = ValidationScore.GOOD
        if not recommendations:
            recommendations.append("✅ Signal suitable for analytics with minor reservations")
            recommendations.append("✓ Review issues and apply recommended verifications")
    elif score >= 60:
        level = ValidationScore.ACCEPTABLE
        recommendations.append("⚠️  Signal usable but requires verification")
        recommendations.append("⚠️  Address issues before production use")
    elif score >= 40:
        level = ValidationScore.POOR
        recommendations.append("🚨 Signal quality insufficient for production")
        recommendations.append("🚨 Address all critical issues before proceeding")
    else:
        level = ValidationScore.TERMINAL
        recommendations.append("🚨 TERMINAL: Signal cannot be used in current state")
        recommendations.append("🚨 REQUIRED: Fix fundamental issues before retry")
        recommendations.append("🚨 Contact BMS administrator or equipment vendor")
    
    return score, level, issues, recommendations


def format_score_report(
    signal_name: str,
    score: int,
    level: ValidationScore,
    issues: List[str],
    recommendations: List[str],
    metadata: Dict
) -> str:
    """
    Format validation score report for user display.
    
    PURE FUNCTION - NO SIDE EFFECTS
    - Just string formatting
    - No logging or I/O
    
    Args:
        signal_name: Name of the signal
        score: Validation score (0-100)
        level: ValidationScore enum
        issues: List of issues found
        recommendations: List of recommendations
        metadata: Original metadata for context
    
    Returns:
        Formatted report string
    
    Examples:
        >>> report = format_score_report("Test_Signal", 95, ValidationScore.EXCELLENT, [], ["Ready"], {})
        >>> "EXCELLENT" in report
        True
    """
    lines = []
    lines.append("=" * 80)
    lines.append("VALIDATION SCORE REPORT")
    lines.append("=" * 80)
    lines.append("")
    
    lines.append(f"Signal: {signal_name}")
    lines.append(f"Detected Type: {metadata.get('detected_type', 'unknown')}")
    lines.append(f"Confidence: {metadata.get('confidence', 'unknown')}")
    lines.append("")
    
    # Score visualization
    lines.append(f"Overall Score: {score}/100")
    
    # Progress bar
    bar_length = 50
    filled = int(bar_length * score / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    lines.append(f"[{bar}] {score}%")
    lines.append("")
    
    # Level with emoji
    level_display = {
        ValidationScore.EXCELLENT: "✅ EXCELLENT - Production Ready",
        ValidationScore.GOOD: "✅ GOOD - Minor Issues",
        ValidationScore.ACCEPTABLE: "⚠️  ACCEPTABLE - Verify Before Use",
        ValidationScore.POOR: "🚨 POOR - Major Issues",
        ValidationScore.TERMINAL: "🚨 TERMINAL - Cannot Use"
    }
    lines.append(f"Validation Level: {level_display.get(level, level.value)}")
    lines.append("")
    
    # Score breakdown
    lines.append("Score Breakdown:")
    lines.append("  • Detection Confidence: 0-40 points")
    lines.append("  • Data Completeness:    0-20 points")
    lines.append("  • Range Sanity:         0-20 points")
    lines.append("  • Statistical Quality:  0-20 points")
    lines.append("")
    
    # Issues
    if issues:
        lines.append(f"Issues Found ({len(issues)}):")
        for issue in issues:
            lines.append(f"  {issue}")
        lines.append("")
    else:
        lines.append("Issues Found: None ✅")
        lines.append("")
    
    # Recommendations
    lines.append(f"Recommendations ({len(recommendations)}):")
    for rec in recommendations:
        lines.append(f"  {rec}")
    lines.append("")
    
    # Context
    lines.append("Signal Statistics:")
    lines.append(f"  Samples: {metadata.get('original_count', 0)}")
    lines.append(f"  Range: [{metadata.get('original_min', 0):.2f}, {metadata.get('original_max', 0):.2f}]")
    lines.append(f"  Mean: {metadata.get('original_mean', 0):.2f}")
    lines.append(f"  P99.5: {metadata.get('p995', 0):.2f}")
    lines.append("")
    
    lines.append("=" * 80)
    
    return "\n".join(lines)

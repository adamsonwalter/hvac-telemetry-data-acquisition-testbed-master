"""
Stage 3 Domain Function: Compute Coverage Penalty

Pure function - NO side effects, NO logging, NO I/O.
Maps coverage percentage to confidence penalty.

Reference: htdam/stage-3-timestamp-sync/HTDAM v2.0 Stage 3_ Timestamp Synchronization.md
"""

from src.domain.htdam.constants import (
    COVERAGE_EXCELLENT_PCT,
    COVERAGE_GOOD_PCT,
    COVERAGE_FAIR_PCT,
)


def compute_coverage_penalty(coverage_pct: float) -> float:
    """
    Compute confidence penalty based on coverage percentage.
    
    Coverage is defined as the percentage of grid points classified as VALID
    (i.e., all mandatory streams present with acceptable alignment quality).
    
    Args:
        coverage_pct: Percentage of VALID grid points (0.0-100.0)
        
    Returns:
        Penalty value (0.0 to -0.10)
        
    Penalty Tiers:
        - ≥95% (EXCELLENT): No penalty (0.0)
        - ≥90% (GOOD): Small penalty (-0.02)
        - ≥80% (FAIR): Moderate penalty (-0.05)
        - <80% (POOR): Large penalty (-0.10)
        
    Rationale:
        - Excellent coverage (≥95%): Data quality is very high, minimal gaps
        - Good coverage (≥90%): Acceptable for most analysis, slight reduction
        - Fair coverage (≥80%): Usable but degraded quality, noticeable penalty
        - Poor coverage (<80%): Significant data quality issues, consider HALT
        
    Note:
        If coverage is extremely low (<50%), the orchestration hook should
        consider HALT to prevent unreliable analysis.
        
    Example:
        >>> compute_coverage_penalty(96.5)
        0.0  # Excellent coverage
        
        >>> compute_coverage_penalty(93.8)
        0.0  # Still excellent (BarTech example)
        
        >>> compute_coverage_penalty(92.0)
        -0.02  # Good coverage
        
        >>> compute_coverage_penalty(85.0)
        -0.05  # Fair coverage
        
        >>> compute_coverage_penalty(75.0)
        -0.1  # Poor coverage
    """
    if coverage_pct >= COVERAGE_EXCELLENT_PCT:
        return 0.0
    elif coverage_pct >= COVERAGE_GOOD_PCT:
        return -0.02
    elif coverage_pct >= COVERAGE_FAIR_PCT:
        return -0.05
    else:
        # Poor coverage (<80%)
        return -0.10

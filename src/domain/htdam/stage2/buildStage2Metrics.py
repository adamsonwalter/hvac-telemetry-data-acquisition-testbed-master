"""
Stage 2 Domain Function: Build Stage 2 Metrics

Pure function - NO side effects, NO logging, NO I/O.
Constructs metrics JSON dictionary for Stage 2 gap detection output.

Reference: htdam/stage-2-gap-detection/HTAM Stage 2/HTDAM_Stage2_Impl_Guide.md
"""

from typing import Dict, List
from collections import Counter


def build_stage2_metrics(
    per_signal_summaries: Dict[str, Dict],
    exclusion_windows: List[Dict],
    stage1_confidence: float,
    aggregate_penalty: float,
    warnings: List[str],
    errors: List[str]
) -> Dict:
    """
    Build Stage 2 metrics JSON dictionary.
    
    Output structure matches Stage 2 schema:
    - stage: "GAPS"
    - per_stream_summary: Dict[stream_id, gap stats + semantics]
    - exclusion_windows: List of proposed windows
    - aggregate_penalty: Total confidence penalty
    - stage2_confidence: stage1_confidence + penalty
    - warnings: List of warning messages
    - errors: List of error messages
    - halt: bool (always False for Stage 2)
    - human_approval_required: bool (True if exclusion windows detected)
    
    Args:
        per_signal_summaries: Dict mapping signal_id to summary dict with:
            - total_records: int
            - total_intervals: int
            - interval_stats: Dict with normal/minor/major counts and percentages
            - gap_semantics: Counter of semantic types
            - stream_penalty: float
            - stream_confidence: float
        exclusion_windows: List of exclusion window dicts
        stage1_confidence: Confidence from Stage 1 (typically 1.00)
        aggregate_penalty: Total penalty from all streams
        warnings: List of warning messages
        errors: List of error messages
        
    Returns:
        Metrics dictionary conforming to Stage 2 schema
        
    Algorithm:
        1. Assemble per_stream_summary from inputs
        2. Add exclusion_windows list
        3. Compute stage2_confidence = stage1 + penalty
        4. Set human_approval_required flag
        5. Return complete metrics dict
        
    Example:
        >>> summaries = {
        ...     "CHWST": {
        ...         "total_records": 35574,
        ...         "total_intervals": 35573,
        ...         "interval_stats": {"normal_count": 33850, "normal_pct": 95.2, ...},
        ...         "gap_semantics": Counter({"COV_CONSTANT": 155, "COV_MINOR": 62}),
        ...         "stream_penalty": -0.07,
        ...         "stream_confidence": 0.93
        ...     }
        ... }
        >>> exclusions = [{"window_id": "EXW_001", "start_ts": 1000, "end_ts": 5000, ...}]
        >>> metrics = build_stage2_metrics(summaries, exclusions, 1.00, -0.07, [], [])
        >>> metrics["stage2_confidence"]
        0.93
        >>> metrics["human_approval_required"]
        True
    """
    # Convert gap_semantics Counters to dicts
    per_stream_summary_formatted = {}
    for signal_id, summary in per_signal_summaries.items():
        formatted_summary = summary.copy()
        
        # Convert Counter to dict if needed
        if "gap_semantics" in formatted_summary:
            gap_sem = formatted_summary["gap_semantics"]
            if isinstance(gap_sem, Counter):
                formatted_summary["gap_semantics"] = dict(gap_sem)
        
        per_stream_summary_formatted[signal_id] = formatted_summary
    
    # Compute Stage 2 confidence
    stage2_confidence = stage1_confidence + aggregate_penalty
    
    # Determine if human approval required
    human_approval_required = len(exclusion_windows) > 0
    
    # Build metrics dictionary
    metrics = {
        "stage": "GAPS",
        "per_stream_summary": per_stream_summary_formatted,
        "exclusion_windows": exclusion_windows,
        "aggregate_penalty": aggregate_penalty,
        "stage2_confidence": stage2_confidence,
        "warnings": warnings,
        "errors": errors,
        "halt": False,  # Stage 2 never halts
        "human_approval_required": human_approval_required,
    }
    
    return metrics

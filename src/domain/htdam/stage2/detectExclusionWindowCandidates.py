"""
Stage 2 Domain Function: Detect Exclusion Window Candidates

Pure function - NO side effects, NO logging, NO I/O.
Identifies time periods when multiple signals have overlapping MAJOR_GAPs,
indicating system offline/maintenance periods.

Reference: htdam/stage-2-gap-detection/HTAM Stage 2/HTDAM_Stage2_Impl_Guide.md
"""

from typing import Dict, List
from src.domain.htdam.constants import (
    EXCLUSION_MIN_OVERLAP_STREAMS,
    EXCLUSION_MIN_DURATION_HOURS,
    GAP_CLASS_MAJOR,
)


def detect_exclusion_window_candidates(
    per_signal_gaps: Dict[str, List[Dict]]
) -> List[Dict]:
    """
    Detect exclusion window candidates from overlapping MAJOR_GAPs.
    
    An exclusion window is proposed when:
    - >= 2 mandatory streams have overlapping MAJOR_GAPs
    - Overlap duration >= 8 hours
    
    Args:
        per_signal_gaps: Dict mapping signal_id to list of gap dicts
                        Each gap dict must have:
                        - gap_class: str ("MAJOR_GAP", etc.)
                        - start_ts: float (Unix epoch seconds)
                        - end_ts: float (Unix epoch seconds)
                        - duration_seconds: float
                        
    Returns:
        List of exclusion window candidate dicts:
        - window_id: str (e.g., "EXW_001")
        - start_ts: float (Unix epoch seconds)
        - end_ts: float (Unix epoch seconds)
        - duration_hours: float
        - affecting_streams: List[str] (signal IDs involved)
        - status: str ("PENDING_APPROVAL")
        
    Algorithm:
        1. Extract all MAJOR_GAPs from all signals
        2. Find pairwise overlaps between MAJOR_GAPs from different signals
        3. Filter overlaps by duration (>= 8 hours)
        4. Merge overlapping windows that share streams
        5. Return list of unique exclusion window candidates
        
    Example:
        >>> gaps = {
        ...     "CHWST": [
        ...         {"gap_class": "MAJOR_GAP", "start_ts": 1000, "end_ts": 5000, "duration_seconds": 4000}
        ...     ],
        ...     "CHWRT": [
        ...         {"gap_class": "MAJOR_GAP", "start_ts": 1200, "end_ts": 4800, "duration_seconds": 3600}
        ...     ]
        ... }
        >>> detect_exclusion_window_candidates(gaps)
        [{
            "window_id": "EXW_001",
            "start_ts": 1200,
            "end_ts": 4800,
            "duration_hours": 1.0,
            "affecting_streams": ["CHWST", "CHWRT"],
            "status": "PENDING_APPROVAL"
        }]
    """
    # Extract MAJOR_GAPs from all signals
    major_gaps_by_signal = {}
    for signal_id, gaps in per_signal_gaps.items():
        major_gaps = [g for g in gaps if g.get("gap_class") == GAP_CLASS_MAJOR]
        if major_gaps:
            major_gaps_by_signal[signal_id] = major_gaps
    
    # No MAJOR_GAPs found - no exclusion windows
    if len(major_gaps_by_signal) < EXCLUSION_MIN_OVERLAP_STREAMS:
        return []
    
    # Find overlapping MAJOR_GAPs between pairs of signals
    candidates = []
    signal_ids = list(major_gaps_by_signal.keys())
    
    for i in range(len(signal_ids)):
        for j in range(i + 1, len(signal_ids)):
            signal_a = signal_ids[i]
            signal_b = signal_ids[j]
            
            gaps_a = major_gaps_by_signal[signal_a]
            gaps_b = major_gaps_by_signal[signal_b]
            
            # Check all pairs of gaps for overlap
            for gap_a in gaps_a:
                for gap_b in gaps_b:
                    # Compute overlap
                    overlap_start = max(gap_a["start_ts"], gap_b["start_ts"])
                    overlap_end = min(gap_a["end_ts"], gap_b["end_ts"])
                    
                    if overlap_end > overlap_start:
                        overlap_duration_hours = (overlap_end - overlap_start) / 3600.0
                        
                        # Check if overlap meets minimum duration
                        if overlap_duration_hours >= EXCLUSION_MIN_DURATION_HOURS:
                            candidates.append({
                                "start_ts": overlap_start,
                                "end_ts": overlap_end,
                                "duration_hours": overlap_duration_hours,
                                "affecting_streams": sorted([signal_a, signal_b]),
                            })
    
    # Merge overlapping/adjacent candidates
    if not candidates:
        return []
    
    # Sort by start time
    candidates.sort(key=lambda x: x["start_ts"])
    
    # Merge overlapping windows
    merged = []
    current = candidates[0].copy()
    
    for next_window in candidates[1:]:
        # Check if windows overlap or are adjacent
        if next_window["start_ts"] <= current["end_ts"]:
            # Merge: extend end time and combine stream lists
            current["end_ts"] = max(current["end_ts"], next_window["end_ts"])
            current["duration_hours"] = (current["end_ts"] - current["start_ts"]) / 3600.0
            
            # Merge affecting_streams (unique)
            combined_streams = set(current["affecting_streams"]) | set(next_window["affecting_streams"])
            current["affecting_streams"] = sorted(combined_streams)
        else:
            # No overlap - save current and start new
            merged.append(current)
            current = next_window.copy()
    
    # Add final window
    merged.append(current)
    
    # Assign window IDs and status
    for idx, window in enumerate(merged, start=1):
        window["window_id"] = f"EXW_{idx:03d}"
        window["status"] = "PENDING_APPROVAL"
    
    return merged

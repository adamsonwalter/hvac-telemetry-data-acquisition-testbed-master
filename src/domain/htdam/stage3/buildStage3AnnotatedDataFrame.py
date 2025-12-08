"""
Stage 3 Domain Function: Build Stage 3 Annotated DataFrame

Pure function - NO side effects, NO logging, NO I/O.
Constructs synchronized DataFrame with alignment metadata and row classifications.

Reference: htdam/stage-3-timestamp-sync/HTDAM v2.0 Stage 3_ Timestamp Synchronization.md
"""

from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
from src.domain.htdam.constants import (
    COL_GRID_TIMESTAMP,
    COL_SUFFIX_ALIGN_QUALITY,
    COL_SUFFIX_ALIGN_DISTANCE,
    COL_ROW_GAP_TYPE,
    COL_ROW_CONFIDENCE,
    COL_ROW_EXCLUSION_WINDOW_ID,
)


def build_stage3_annotated_dataframe(
    grid: List[datetime],
    aligned_streams: Dict[str, Dict],
    row_gap_types: List[str],
    row_confidences: List[float],
    row_exclusion_window_ids: List[Optional[str]]
) -> pd.DataFrame:
    """
    Build synchronized DataFrame with alignment metadata and row classifications.
    
    This function assembles all Stage 3 outputs into a single DataFrame ready
    for Stage 4 COP calculation.
    
    Args:
        grid: Master grid timestamps (length M)
        aligned_streams: Dict mapping stream_id to alignment results:
            {
                'stream_id': {
                    'values': List[float] (length M, NaN if missing),
                    'qualities': List[str] (EXACT/CLOSE/INTERP/MISSING),
                    'distances': List[float|None] (seconds from grid)
                }
            }
            Example keys: 'CHWST', 'CHWRT', 'CDWRT', 'FLOW', 'POWER'
        row_gap_types: List of gap types per grid row (length M)
        row_confidences: List of confidences per grid row (length M)
        row_exclusion_window_ids: List of exclusion window IDs (length M, None if not excluded)
        
    Returns:
        DataFrame with columns:
        - timestamp: Grid timestamp
        - <stream_id>: Aligned value (e.g., 'chwst', 'chwrt', etc.)
        - <stream_id>_align_quality: Quality tier (e.g., 'chwst_align_quality')
        - <stream_id>_align_distance_s: Distance in seconds (e.g., 'chwst_align_distance_s')
        - gap_type: Row-level gap type
        - confidence: Row-level confidence
        - exclusion_window_id: Exclusion window ID or None
        
    Output Structure:
        One row per grid timestamp, all streams synchronized to common timeline.
        
    Example:
        >>> from datetime import datetime
        >>> grid = [datetime(2024, 10, 15, 14, 45, 0)]
        >>> aligned_streams = {
        ...     'CHWST': {
        ...         'values': [17.56],
        ...         'qualities': ['EXACT'],
        ...         'distances': [12.0]
        ...     },
        ...     'CHWRT': {
        ...         'values': [17.39],
        ...         'qualities': ['EXACT'],
        ...         'distances': [8.0]
        ...     }
        ... }
        >>> row_gap_types = ['VALID']
        >>> row_confidences = [0.95]
        >>> row_exclusion_ids = [None]
        >>> df = build_stage3_annotated_dataframe(
        ...     grid, aligned_streams, row_gap_types, row_confidences, row_exclusion_ids
        ... )
        >>> df.columns.tolist()
        ['timestamp', 'chwst', 'chwst_align_quality', 'chwst_align_distance_s',
         'chwrt', 'chwrt_align_quality', 'chwrt_align_distance_s',
         'gap_type', 'confidence', 'exclusion_window_id']
    """
    M = len(grid)
    
    # Validate input lengths
    if len(row_gap_types) != M:
        raise ValueError(
            f"row_gap_types length ({len(row_gap_types)}) must match grid length ({M})"
        )
    if len(row_confidences) != M:
        raise ValueError(
            f"row_confidences length ({len(row_confidences)}) must match grid length ({M})"
        )
    if len(row_exclusion_window_ids) != M:
        raise ValueError(
            f"row_exclusion_window_ids length ({len(row_exclusion_window_ids)}) must match grid length ({M})"
        )
    
    # Initialize DataFrame with grid timestamps
    data = {COL_GRID_TIMESTAMP: grid}
    
    # Add aligned stream data
    # Process streams in canonical order for consistent column ordering
    canonical_order = ['CHWST', 'CHWRT', 'CDWRT', 'FLOW', 'POWER']
    
    for stream_id in canonical_order:
        if stream_id not in aligned_streams:
            continue
        
        stream_data = aligned_streams[stream_id]
        
        # Validate stream data length
        if len(stream_data['values']) != M:
            raise ValueError(
                f"Stream {stream_id} values length ({len(stream_data['values'])}) must match grid length ({M})"
            )
        
        # Add value column (lowercase stream ID for canonical unit)
        col_value = stream_id.lower()
        data[col_value] = stream_data['values']
        
        # Add alignment quality column
        col_quality = stream_id.lower() + COL_SUFFIX_ALIGN_QUALITY
        data[col_quality] = stream_data['qualities']
        
        # Add alignment distance column
        col_distance = stream_id.lower() + COL_SUFFIX_ALIGN_DISTANCE
        data[col_distance] = stream_data['distances']
    
    # Add row-level columns
    data[COL_ROW_GAP_TYPE] = row_gap_types
    data[COL_ROW_CONFIDENCE] = row_confidences
    data[COL_ROW_EXCLUSION_WINDOW_ID] = row_exclusion_window_ids
    
    # Construct DataFrame
    df = pd.DataFrame(data)
    
    return df

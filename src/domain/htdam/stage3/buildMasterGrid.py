"""
Stage 3 Domain Function: Build Master Grid

Pure function - NO side effects, NO logging, NO I/O.
Generates a uniform time grid with specified step interval.

Reference: htdam/stage-3-timestamp-sync/HTDAM v2.0 Stage 3_ Timestamp Synchronization.md
"""

from datetime import datetime, timedelta
from typing import List
from src.domain.htdam.stage3.ceilToGrid import ceil_to_grid


def build_master_grid(
    t_start: datetime,
    t_end: datetime,
    step_seconds: int
) -> List[datetime]:
    """
    Generate uniform time grid from start to end with specified step.
    
    This function creates the master timeline for Stage 3 synchronization.
    All raw data points from Stage 2 will be aligned to this grid using
    nearest-neighbor logic.
    
    Args:
        t_start: Start of time range (will be ceiled to grid boundary)
        t_end: End of time range (inclusive if aligned, exclusive otherwise)
        step_seconds: Grid step size in seconds (typically 900 for 15-minute intervals)
        
    Returns:
        List of datetime objects at uniform intervals
        
    Algorithm:
        1. Round t_start UP to first grid boundary using ceil_to_grid()
        2. Generate timestamps by incrementing step_seconds
        3. Stop when next timestamp would exceed t_end
        
    Example:
        >>> from datetime import datetime
        >>> t_start = datetime(2024, 10, 15, 14, 37, 0)
        >>> t_end = datetime(2024, 10, 15, 16, 0, 0)
        >>> grid = build_master_grid(t_start, t_end, 900)
        >>> len(grid)
        6  # 14:45, 15:00, 15:15, 15:30, 15:45, 16:00
        >>> grid[0]
        datetime(2024, 10, 15, 14, 45, 0)
        >>> grid[-1]
        datetime(2024, 10, 15, 16, 0, 0)
        
    Performance:
        For 1 year at 15-minute intervals: ~35,136 grid points
        Generation time: <10ms
    """
    # Validate inputs
    if t_end <= t_start:
        raise ValueError(
            f"t_end ({t_end}) must be after t_start ({t_start})"
        )
    
    if step_seconds <= 0:
        raise ValueError(
            f"step_seconds must be positive, got {step_seconds}"
        )
    
    # Round start time up to first grid boundary
    grid_start = ceil_to_grid(t_start, step_seconds)
    
    # Generate grid points
    grid = []
    current = grid_start
    
    while current <= t_end:
        grid.append(current)
        current = current + timedelta(seconds=step_seconds)
    
    return grid

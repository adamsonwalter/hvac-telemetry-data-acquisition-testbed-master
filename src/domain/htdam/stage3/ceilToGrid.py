"""
Stage 3 Domain Function: Ceil to Grid

Pure function - NO side effects, NO logging, NO I/O.
Rounds timestamp UP to the next grid boundary.

Reference: htdam/stage-3-timestamp-sync/HTDAM v2.0 Stage 3_ Timestamp Synchronization.md
"""

from datetime import datetime, timedelta
import math


def ceil_to_grid(timestamp: datetime, step_seconds: int) -> datetime:
    """
    Round timestamp UP to the next grid boundary.
    
    This function ensures all grid timestamps are perfectly aligned to the
    specified step interval. For example, with a 900-second (15-minute) step:
    - 14:37:23 → 14:45:00
    - 14:45:00 → 14:45:00 (already aligned)
    - 14:00:01 → 14:15:00
    
    Args:
        timestamp: Input datetime to round
        step_seconds: Grid step size in seconds (typically 900 for 15-minute intervals)
        
    Returns:
        Datetime rounded UP to next grid boundary
        
    Algorithm:
        1. Convert timestamp to Unix epoch seconds
        2. Compute ceiling: ceil(epoch / step) * step
        3. Convert back to datetime
        
    Example:
        >>> from datetime import datetime
        >>> t = datetime(2024, 10, 15, 14, 37, 23)
        >>> ceil_to_grid(t, 900)
        datetime(2024, 10, 15, 14, 45, 0)
        
        >>> t = datetime(2024, 10, 15, 14, 45, 0)
        >>> ceil_to_grid(t, 900)  # Already aligned
        datetime(2024, 10, 15, 14, 45, 0)
    """
    # Convert to Unix epoch seconds
    epoch = timestamp.timestamp()
    
    # Compute ceiling to next grid boundary
    # math.ceil ensures we always round UP (never down)
    grid_epoch = math.ceil(epoch / step_seconds) * step_seconds
    
    # Convert back to datetime
    return datetime.fromtimestamp(grid_epoch, tz=timestamp.tzinfo)

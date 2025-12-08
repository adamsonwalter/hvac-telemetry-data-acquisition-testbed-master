"""
Unit tests for computeInterSampleIntervals.py
Tests interval calculation logic with various timestamp patterns.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.domain.htdam.stage2.computeInterSampleIntervals import compute_inter_sample_intervals


class TestComputeInterSampleIntervals:
    """Test interval calculation from timestamps."""
    
    def test_uniform_15min_intervals(self):
        """Regular 15-minute COV logging pattern."""
        # Given: timestamps at 15-minute intervals
        start = datetime(2024, 1, 1, 0, 0, 0)
        timestamps = pd.Series([start + timedelta(minutes=15*i) for i in range(10)])
        
        # When: compute intervals
        result = compute_inter_sample_intervals(timestamps)
        
        # Then: all intervals should be 900 seconds
        assert len(result["intervals_seconds"]) == 9
        assert all(result["intervals_seconds"] == 900.0)
        assert result["median_interval"] == 900.0
        assert result["min_interval"] == 900.0
        assert result["max_interval"] == 900.0
    
    def test_irregular_intervals_with_gap(self):
        """Mix of normal intervals and a major gap."""
        # Given: mostly 15-min intervals, then 2-hour gap
        start = datetime(2024, 1, 1, 0, 0, 0)
        timestamps = [
            start,
            start + timedelta(minutes=15),
            start + timedelta(minutes=30),
            start + timedelta(minutes=45),
            start + timedelta(minutes=165),  # 2-hour gap (120 min from last)
            start + timedelta(minutes=180),
        ]
        timestamps = pd.Series(timestamps)
        
        # When: compute intervals
        result = compute_inter_sample_intervals(timestamps)
        
        # Then: intervals should be [900, 900, 900, 7200, 900]
        expected = np.array([900.0, 900.0, 900.0, 7200.0, 900.0])
        np.testing.assert_array_equal(result["intervals_seconds"], expected)
        assert result["median_interval"] == 900.0
        assert result["max_interval"] == 7200.0
    
    def test_single_timestamp(self):
        """Edge case: only one timestamp."""
        # Given: single timestamp
        timestamps = pd.Series([datetime(2024, 1, 1, 0, 0, 0)])
        
        # When: compute intervals
        result = compute_inter_sample_intervals(timestamps)
        
        # Then: no intervals
        assert len(result["intervals_seconds"]) == 0
        assert result["median_interval"] == 0.0
        assert result["min_interval"] == 0.0
        assert result["max_interval"] == 0.0
    
    def test_two_timestamps(self):
        """Edge case: exactly two timestamps."""
        # Given: two timestamps 30 min apart
        start = datetime(2024, 1, 1, 0, 0, 0)
        timestamps = pd.Series([start, start + timedelta(minutes=30)])
        
        # When: compute intervals
        result = compute_inter_sample_intervals(timestamps)
        
        # Then: one interval of 1800 seconds
        assert len(result["intervals_seconds"]) == 1
        assert result["intervals_seconds"][0] == 1800.0
        assert result["median_interval"] == 1800.0
    
    def test_unix_timestamp_integers(self):
        """Handle Unix timestamps as integers."""
        # Given: Unix timestamps as integers (900s apart)
        timestamps = pd.Series([1704067200 + 900*i for i in range(5)])
        
        # When: compute intervals
        result = compute_inter_sample_intervals(timestamps)
        
        # Then: should work with numeric timestamps
        assert len(result["intervals_seconds"]) == 4
        assert all(result["intervals_seconds"] == 900.0)
    
    def test_unsorted_timestamps(self):
        """Timestamps provided out of order (should be sorted)."""
        # Given: unsorted timestamps
        start = datetime(2024, 1, 1, 0, 0, 0)
        timestamps = pd.Series([
            start + timedelta(minutes=30),
            start,
            start + timedelta(minutes=15),
        ])
        
        # When: compute intervals
        result = compute_inter_sample_intervals(timestamps)
        
        # Then: should handle sorting internally
        assert len(result["intervals_seconds"]) == 2
        # After sorting: [0, 15, 30] -> intervals [900, 900]
        assert all(result["intervals_seconds"] == 900.0)
    
    def test_microsecond_precision(self):
        """Sub-second timestamp precision."""
        # Given: timestamps with microsecond precision
        start = datetime(2024, 1, 1, 0, 0, 0, 0)
        timestamps = pd.Series([
            start,
            start + timedelta(seconds=900, microseconds=500000),  # 900.5s
            start + timedelta(seconds=1800, microseconds=250000), # 1800.25s
        ])
        
        # When: compute intervals
        result = compute_inter_sample_intervals(timestamps)
        
        # Then: should preserve sub-second precision
        assert len(result["intervals_seconds"]) == 2
        np.testing.assert_almost_equal(result["intervals_seconds"][0], 900.5, decimal=3)
        np.testing.assert_almost_equal(result["intervals_seconds"][1], 899.75, decimal=3)
    
    def test_zero_interval_duplicates(self):
        """Duplicate timestamps (zero interval)."""
        # Given: duplicate timestamp
        start = datetime(2024, 1, 1, 0, 0, 0)
        timestamps = pd.Series([
            start,
            start,  # duplicate
            start + timedelta(minutes=15),
        ])
        
        # When: compute intervals
        result = compute_inter_sample_intervals(timestamps)
        
        # Then: should have zero interval
        assert len(result["intervals_seconds"]) == 2
        assert result["intervals_seconds"][0] == 0.0
        assert result["intervals_seconds"][1] == 900.0
        assert result["min_interval"] == 0.0

"""
Unit tests for buildMasterGrid.py

Tests the build_master_grid() pure function that generates uniform time grid.
"""

import pytest
import pandas as pd
from src.domain.htdam.stage3.buildMasterGrid import build_master_grid


class TestBuildMasterGrid:
    """Test suite for build_master_grid()"""

    def test_single_day_grid(self):
        """Test grid for single day (24 hours)"""
        start = pd.Timestamp("2024-01-01 00:00:00")
        end = pd.Timestamp("2024-01-02 00:00:00")
        grid = build_master_grid(start, end, interval_seconds=900)
        
        # 24 hours * 4 samples/hour + 1 endpoint = 97 points
        assert len(grid) == 97
        assert grid[0] == start
        assert grid[-1] == end

    def test_uniform_spacing(self):
        """Test that grid points are uniformly spaced"""
        start = pd.Timestamp("2024-01-01 00:00:00")
        end = pd.Timestamp("2024-01-01 01:00:00")
        grid = build_master_grid(start, end, interval_seconds=900)
        
        # Check spacing between consecutive points
        for i in range(len(grid) - 1):
            delta = (grid[i + 1] - grid[i]).total_seconds()
            assert delta == 900

    def test_leap_year_handling(self):
        """Test grid generation across leap year"""
        start = pd.Timestamp("2024-02-28 00:00:00")
        end = pd.Timestamp("2024-03-01 00:00:00")
        grid = build_master_grid(start, end, interval_seconds=900)
        
        # 2024 is leap year: Feb 28 + Feb 29 + Mar 1 = 3 days
        # 3 days * 96 samples/day + 1 = 289 points
        assert len(grid) == 289

    def test_one_hour_interval(self):
        """Test with 1-hour interval"""
        start = pd.Timestamp("2024-01-01 00:00:00")
        end = pd.Timestamp("2024-01-02 00:00:00")
        grid = build_master_grid(start, end, interval_seconds=3600)
        
        # 24 hours + 1 endpoint = 25 points
        assert len(grid) == 25

    def test_one_minute_interval(self):
        """Test with 1-minute interval"""
        start = pd.Timestamp("2024-01-01 00:00:00")
        end = pd.Timestamp("2024-01-01 01:00:00")
        grid = build_master_grid(start, end, interval_seconds=60)
        
        # 60 minutes + 1 endpoint = 61 points
        assert len(grid) == 61

    def test_single_interval(self):
        """Test grid with just start and end"""
        start = pd.Timestamp("2024-01-01 00:00:00")
        end = pd.Timestamp("2024-01-01 00:15:00")
        grid = build_master_grid(start, end, interval_seconds=900)
        
        assert len(grid) == 2
        assert grid[0] == start
        assert grid[1] == end

    def test_bartech_year_grid(self):
        """Test grid for full year (BarTech scenario)"""
        start = pd.Timestamp("2017-01-01 00:00:00")
        end = pd.Timestamp("2017-12-31 23:45:00")
        grid = build_master_grid(start, end, interval_seconds=900)
        
        # 365 days * 96 samples/day + 1 = 35,041 points
        # But end is at 23:45, not 00:00 next day
        # So: (365 * 96) + 1 = 35,041
        expected_count = 35136  # Per specification
        assert len(grid) == expected_count

    def test_timezone_preservation(self):
        """Test that timezone is preserved"""
        start = pd.Timestamp("2024-01-01 00:00:00", tz="UTC")
        end = pd.Timestamp("2024-01-01 01:00:00", tz="UTC")
        grid = build_master_grid(start, end, interval_seconds=900)
        
        assert grid[0].tz == start.tz
        assert grid[-1].tz == end.tz

    def test_start_equals_end(self):
        """Test edge case where start == end"""
        start = pd.Timestamp("2024-01-01 00:00:00")
        end = pd.Timestamp("2024-01-01 00:00:00")
        grid = build_master_grid(start, end, interval_seconds=900)
        
        assert len(grid) == 1
        assert grid[0] == start

    def test_returns_pandas_series(self):
        """Test that output is pandas Series"""
        start = pd.Timestamp("2024-01-01 00:00:00")
        end = pd.Timestamp("2024-01-01 01:00:00")
        grid = build_master_grid(start, end, interval_seconds=900)
        
        assert isinstance(grid, pd.Series)
        assert grid.dtype == "datetime64[ns]"

    def test_monotonic_increasing(self):
        """Test that grid is strictly monotonic increasing"""
        start = pd.Timestamp("2024-01-01 00:00:00")
        end = pd.Timestamp("2024-01-02 00:00:00")
        grid = build_master_grid(start, end, interval_seconds=900)
        
        assert grid.is_monotonic_increasing
        assert grid.is_unique

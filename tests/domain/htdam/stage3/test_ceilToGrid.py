"""
Unit tests for ceilToGrid.py

Tests the ceil_to_grid() pure function that rounds timestamps UP to grid boundary.
"""

import pytest
import pandas as pd
from datetime import datetime
from src.domain.htdam.stage3.ceilToGrid import ceil_to_grid


class TestCeilToGrid:
    """Test suite for ceil_to_grid()"""

    def test_already_on_grid(self):
        """Test timestamp already on 15-min grid"""
        ts = pd.Timestamp("2024-01-01 00:00:00")
        result = ceil_to_grid(ts, interval_seconds=900)
        assert result == ts

    def test_rounds_up_to_next_grid_point(self):
        """Test timestamp rounds UP to next 15-min boundary"""
        ts = pd.Timestamp("2024-01-01 00:01:00")  # 1 minute past midnight
        result = ceil_to_grid(ts, interval_seconds=900)
        expected = pd.Timestamp("2024-01-01 00:15:00")
        assert result == expected

    def test_rounds_up_within_same_hour(self):
        """Test rounding within same hour"""
        ts = pd.Timestamp("2024-01-01 00:14:59")  # 1 second before 15-min mark
        result = ceil_to_grid(ts, interval_seconds=900)
        expected = pd.Timestamp("2024-01-01 00:15:00")
        assert result == expected

    def test_rounds_up_across_hour_boundary(self):
        """Test rounding across hour boundary"""
        ts = pd.Timestamp("2024-01-01 00:59:00")
        result = ceil_to_grid(ts, interval_seconds=900)
        expected = pd.Timestamp("2024-01-01 01:00:00")
        assert result == expected

    def test_rounds_up_across_day_boundary(self):
        """Test rounding across day boundary"""
        ts = pd.Timestamp("2024-01-01 23:59:00")
        result = ceil_to_grid(ts, interval_seconds=900)
        expected = pd.Timestamp("2024-01-02 00:00:00")
        assert result == expected

    def test_custom_interval_60_seconds(self):
        """Test with 1-minute interval"""
        ts = pd.Timestamp("2024-01-01 00:00:30")  # 30 seconds
        result = ceil_to_grid(ts, interval_seconds=60)
        expected = pd.Timestamp("2024-01-01 00:01:00")
        assert result == expected

    def test_custom_interval_3600_seconds(self):
        """Test with 1-hour interval"""
        ts = pd.Timestamp("2024-01-01 00:30:00")  # 30 minutes
        result = ceil_to_grid(ts, interval_seconds=3600)
        expected = pd.Timestamp("2024-01-01 01:00:00")
        assert result == expected

    def test_epoch_time(self):
        """Test with Unix epoch"""
        ts = pd.Timestamp("1970-01-01 00:00:00")
        result = ceil_to_grid(ts, interval_seconds=900)
        assert result == ts

    def test_microseconds_round_up(self):
        """Test that microseconds are handled correctly"""
        ts = pd.Timestamp("2024-01-01 00:00:00.000001")  # 1 microsecond
        result = ceil_to_grid(ts, interval_seconds=900)
        expected = pd.Timestamp("2024-01-01 00:15:00")
        assert result == expected

    def test_type_preservation(self):
        """Test that output is pandas Timestamp"""
        ts = pd.Timestamp("2024-01-01 00:01:00")
        result = ceil_to_grid(ts, interval_seconds=900)
        assert isinstance(result, pd.Timestamp)

    def test_timezone_aware_input(self):
        """Test with timezone-aware timestamp"""
        ts = pd.Timestamp("2024-01-01 00:01:00", tz="UTC")
        result = ceil_to_grid(ts, interval_seconds=900)
        expected = pd.Timestamp("2024-01-01 00:15:00", tz="UTC")
        assert result == expected
        assert result.tz == ts.tz

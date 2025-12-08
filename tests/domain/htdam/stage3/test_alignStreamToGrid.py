"""
Unit tests for alignStreamToGrid.py

Tests the align_stream_to_grid() CORE algorithm (O(N+M) two-pointer scan).
"""

import pytest
import pandas as pd
import numpy as np
from src.domain.htdam.stage3.alignStreamToGrid import align_stream_to_grid


class TestAlignStreamToGrid:
    """Test suite for align_stream_to_grid()"""

    def test_perfect_alignment(self):
        """Test stream perfectly aligned with grid"""
        grid = pd.Series([
            pd.Timestamp("2024-01-01 00:00:00"),
            pd.Timestamp("2024-01-01 00:15:00"),
            pd.Timestamp("2024-01-01 00:30:00"),
        ])
        stream_ts = pd.Series([
            pd.Timestamp("2024-01-01 00:00:00"),
            pd.Timestamp("2024-01-01 00:15:00"),
            pd.Timestamp("2024-01-01 00:30:00"),
        ])
        stream_val = pd.Series([10.0, 20.0, 30.0])
        
        result = align_stream_to_grid(grid, stream_ts, stream_val, tolerance_seconds=1800)
        
        assert len(result) == 3
        assert result["values"].tolist() == [10.0, 20.0, 30.0]
        assert result["quality"].tolist() == ["EXACT", "EXACT", "EXACT"]
        assert result["jitter"].tolist() == [0, 0, 0]

    def test_close_alignment(self):
        """Test CLOSE quality (60-300 seconds jitter)"""
        grid = pd.Series([
            pd.Timestamp("2024-01-01 00:00:00"),
            pd.Timestamp("2024-01-01 00:15:00"),
        ])
        stream_ts = pd.Series([
            pd.Timestamp("2024-01-01 00:01:00"),  # 60s jitter
            pd.Timestamp("2024-01-01 00:19:00"),  # 240s jitter
        ])
        stream_val = pd.Series([10.0, 20.0])
        
        result = align_stream_to_grid(grid, stream_ts, stream_val, tolerance_seconds=1800)
        
        assert result["values"].tolist() == [10.0, 20.0]
        assert result["quality"].tolist() == ["CLOSE", "CLOSE"]
        assert result["jitter"].tolist() == [60, 240]

    def test_interp_quality(self):
        """Test INTERP quality (300-1800 seconds jitter)"""
        grid = pd.Series([
            pd.Timestamp("2024-01-01 00:00:00"),
        ])
        stream_ts = pd.Series([
            pd.Timestamp("2024-01-01 00:10:00"),  # 600s jitter
        ])
        stream_val = pd.Series([10.0])
        
        result = align_stream_to_grid(grid, stream_ts, stream_val, tolerance_seconds=1800)
        
        assert result["values"].iloc[0] == 10.0
        assert result["quality"].iloc[0] == "INTERP"
        assert result["jitter"].iloc[0] == 600

    def test_missing_outside_tolerance(self):
        """Test MISSING when no sample within tolerance"""
        grid = pd.Series([
            pd.Timestamp("2024-01-01 00:00:00"),
        ])
        stream_ts = pd.Series([
            pd.Timestamp("2024-01-01 01:00:00"),  # 3600s away (> 1800s tolerance)
        ])
        stream_val = pd.Series([10.0])
        
        result = align_stream_to_grid(grid, stream_ts, stream_val, tolerance_seconds=1800)
        
        assert pd.isna(result["values"].iloc[0])
        assert result["quality"].iloc[0] == "MISSING"
        assert pd.isna(result["jitter"].iloc[0])

    def test_sparse_stream(self):
        """Test sparse stream with gaps"""
        grid = pd.Series([
            pd.Timestamp("2024-01-01 00:00:00"),
            pd.Timestamp("2024-01-01 00:15:00"),
            pd.Timestamp("2024-01-01 00:30:00"),
            pd.Timestamp("2024-01-01 00:45:00"),
        ])
        stream_ts = pd.Series([
            pd.Timestamp("2024-01-01 00:00:00"),
            pd.Timestamp("2024-01-01 00:45:00"),  # Missing 00:15, 00:30
        ])
        stream_val = pd.Series([10.0, 40.0])
        
        result = align_stream_to_grid(grid, stream_ts, stream_val, tolerance_seconds=1800)
        
        assert result["values"].iloc[0] == 10.0
        assert pd.isna(result["values"].iloc[1])
        assert pd.isna(result["values"].iloc[2])
        assert result["values"].iloc[3] == 40.0
        
        assert result["quality"].tolist() == ["EXACT", "MISSING", "MISSING", "EXACT"]

    def test_dense_stream_multiple_candidates(self):
        """Test dense stream where multiple samples compete for same grid point"""
        grid = pd.Series([
            pd.Timestamp("2024-01-01 00:00:00"),
        ])
        stream_ts = pd.Series([
            pd.Timestamp("2023-12-31 23:59:00"),  # 60s before
            pd.Timestamp("2024-01-01 00:01:00"),  # 60s after
        ])
        stream_val = pd.Series([10.0, 20.0])
        
        result = align_stream_to_grid(grid, stream_ts, stream_val, tolerance_seconds=1800)
        
        # Should pick nearest (both 60s away, picks first)
        assert result["values"].iloc[0] == 10.0
        assert result["quality"].iloc[0] == "CLOSE"

    def test_empty_stream(self):
        """Test empty stream"""
        grid = pd.Series([
            pd.Timestamp("2024-01-01 00:00:00"),
            pd.Timestamp("2024-01-01 00:15:00"),
        ])
        stream_ts = pd.Series([], dtype="datetime64[ns]")
        stream_val = pd.Series([], dtype=float)
        
        result = align_stream_to_grid(grid, stream_ts, stream_val, tolerance_seconds=1800)
        
        assert len(result) == 2
        assert pd.isna(result["values"]).all()
        assert (result["quality"] == "MISSING").all()

    def test_single_grid_point(self):
        """Test with single grid point"""
        grid = pd.Series([pd.Timestamp("2024-01-01 00:00:00")])
        stream_ts = pd.Series([pd.Timestamp("2024-01-01 00:00:30")])
        stream_val = pd.Series([42.0])
        
        result = align_stream_to_grid(grid, stream_ts, stream_val, tolerance_seconds=1800)
        
        assert len(result) == 1
        assert result["values"].iloc[0] == 42.0
        assert result["quality"].iloc[0] == "EXACT"

    def test_returns_dataframe_with_correct_columns(self):
        """Test output schema"""
        grid = pd.Series([pd.Timestamp("2024-01-01 00:00:00")])
        stream_ts = pd.Series([pd.Timestamp("2024-01-01 00:00:00")])
        stream_val = pd.Series([10.0])
        
        result = align_stream_to_grid(grid, stream_ts, stream_val, tolerance_seconds=1800)
        
        assert isinstance(result, pd.DataFrame)
        assert "values" in result.columns
        assert "quality" in result.columns
        assert "jitter" in result.columns
        assert len(result.columns) == 3

    def test_exact_quality_threshold(self):
        """Test EXACT boundary (<60s)"""
        grid = pd.Series([pd.Timestamp("2024-01-01 00:00:00")])
        stream_ts = pd.Series([pd.Timestamp("2024-01-01 00:00:59")])  # 59s
        stream_val = pd.Series([10.0])
        
        result = align_stream_to_grid(grid, stream_ts, stream_val, tolerance_seconds=1800)
        
        assert result["quality"].iloc[0] == "EXACT"
        assert result["jitter"].iloc[0] == 59

    def test_close_quality_lower_boundary(self):
        """Test CLOSE lower boundary (60s)"""
        grid = pd.Series([pd.Timestamp("2024-01-01 00:00:00")])
        stream_ts = pd.Series([pd.Timestamp("2024-01-01 00:01:00")])  # 60s exactly
        stream_val = pd.Series([10.0])
        
        result = align_stream_to_grid(grid, stream_ts, stream_val, tolerance_seconds=1800)
        
        assert result["quality"].iloc[0] == "CLOSE"
        assert result["jitter"].iloc[0] == 60

    def test_interp_quality_lower_boundary(self):
        """Test INTERP lower boundary (300s)"""
        grid = pd.Series([pd.Timestamp("2024-01-01 00:00:00")])
        stream_ts = pd.Series([pd.Timestamp("2024-01-01 00:05:00")])  # 300s exactly
        stream_val = pd.Series([10.0])
        
        result = align_stream_to_grid(grid, stream_ts, stream_val, tolerance_seconds=1800)
        
        assert result["quality"].iloc[0] == "INTERP"
        assert result["jitter"].iloc[0] == 300

    def test_tolerance_boundary(self):
        """Test exactly at tolerance boundary"""
        grid = pd.Series([pd.Timestamp("2024-01-01 00:00:00")])
        stream_ts = pd.Series([pd.Timestamp("2024-01-01 00:30:00")])  # 1800s exactly
        stream_val = pd.Series([10.0])
        
        result = align_stream_to_grid(grid, stream_ts, stream_val, tolerance_seconds=1800)
        
        # At boundary should be INTERP (≤ tolerance)
        assert result["quality"].iloc[0] == "INTERP"
        assert result["jitter"].iloc[0] == 1800

    def test_negative_jitter_handled(self):
        """Test that timestamps before grid point work correctly"""
        grid = pd.Series([pd.Timestamp("2024-01-01 00:15:00")])
        stream_ts = pd.Series([pd.Timestamp("2024-01-01 00:14:00")])  # 60s before
        stream_val = pd.Series([10.0])
        
        result = align_stream_to_grid(grid, stream_ts, stream_val, tolerance_seconds=1800)
        
        assert result["values"].iloc[0] == 10.0
        assert result["jitter"].iloc[0] == 60  # Absolute value

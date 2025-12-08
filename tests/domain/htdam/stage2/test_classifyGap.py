"""
Unit tests for classifyGap.py
Tests gap classification logic based on interval duration.
"""

import pytest
from src.domain.htdam.stage2.classifyGap import classify_gap


class TestClassifyGap:
    """Test gap classification into NORMAL/MINOR_GAP/MAJOR_GAP."""
    
    def test_normal_interval_exact_nominal(self):
        """Interval exactly at nominal (15 min)."""
        # Given: 900 seconds (15 min)
        result = classify_gap(interval_seconds=900.0, t_nominal_seconds=900.0)
        
        # Then: NORMAL
        assert result["gap_class"] == "NORMAL"
        assert result["interval_seconds"] == 900.0
        assert result["t_nominal_seconds"] == 900.0
    
    def test_normal_interval_within_tolerance(self):
        """Interval slightly above nominal but within NORMAL range."""
        # Given: 22 minutes (1320s) - should be <= 22.5 min (1350s)
        result = classify_gap(interval_seconds=1320.0, t_nominal_seconds=900.0)
        
        # Then: NORMAL (1.5x factor allows up to 1350s)
        assert result["gap_class"] == "NORMAL"
    
    def test_normal_interval_at_boundary(self):
        """Interval at exact NORMAL/MINOR_GAP boundary."""
        # Given: exactly 22.5 minutes (1350s)
        result = classify_gap(interval_seconds=1350.0, t_nominal_seconds=900.0)
        
        # Then: NORMAL (boundary is inclusive)
        assert result["gap_class"] == "NORMAL"
    
    def test_minor_gap_just_above_normal(self):
        """Interval just above NORMAL threshold."""
        # Given: 23 minutes (1380s) - exceeds 1.5x
        result = classify_gap(interval_seconds=1380.0, t_nominal_seconds=900.0)
        
        # Then: MINOR_GAP
        assert result["gap_class"] == "MINOR_GAP"
    
    def test_minor_gap_midrange(self):
        """Interval in middle of MINOR_GAP range."""
        # Given: 45 minutes (2700s) - between 1.5x and 4x
        result = classify_gap(interval_seconds=2700.0, t_nominal_seconds=900.0)
        
        # Then: MINOR_GAP
        assert result["gap_class"] == "MINOR_GAP"
    
    def test_minor_gap_at_boundary(self):
        """Interval at exact MINOR_GAP/MAJOR_GAP boundary."""
        # Given: exactly 60 minutes (3600s = 4x nominal)
        result = classify_gap(interval_seconds=3600.0, t_nominal_seconds=900.0)
        
        # Then: MINOR_GAP (boundary is inclusive)
        assert result["gap_class"] == "MINOR_GAP"
    
    def test_major_gap_just_above_minor(self):
        """Interval just above MINOR_GAP threshold."""
        # Given: 61 minutes (3660s) - exceeds 4x
        result = classify_gap(interval_seconds=3660.0, t_nominal_seconds=900.0)
        
        # Then: MAJOR_GAP
        assert result["gap_class"] == "MAJOR_GAP"
    
    def test_major_gap_large_value(self):
        """Very large interval (multi-hour gap)."""
        # Given: 8 hours (28800s)
        result = classify_gap(interval_seconds=28800.0, t_nominal_seconds=900.0)
        
        # Then: MAJOR_GAP
        assert result["gap_class"] == "MAJOR_GAP"
    
    def test_zero_interval(self):
        """Zero interval (duplicate timestamp)."""
        # Given: 0 seconds
        result = classify_gap(interval_seconds=0.0, t_nominal_seconds=900.0)
        
        # Then: NORMAL (no gap)
        assert result["gap_class"] == "NORMAL"
    
    def test_sub_nominal_interval(self):
        """Interval shorter than nominal (high-frequency logging)."""
        # Given: 5 minutes (300s) - less than 15 min nominal
        result = classify_gap(interval_seconds=300.0, t_nominal_seconds=900.0)
        
        # Then: NORMAL
        assert result["gap_class"] == "NORMAL"
    
    def test_custom_nominal_value(self):
        """Non-default nominal interval (e.g., 5 min)."""
        # Given: 20 minutes (1200s) with 5-min nominal (300s)
        # 1200 / 300 = 4x -> boundary of MINOR_GAP
        result = classify_gap(interval_seconds=1200.0, t_nominal_seconds=300.0)
        
        # Then: MINOR_GAP
        assert result["gap_class"] == "MINOR_GAP"
    
    def test_custom_nominal_major_gap(self):
        """Major gap with custom nominal."""
        # Given: 30 minutes (1800s) with 5-min nominal (300s)
        # 1800 / 300 = 6x -> exceeds 4x threshold
        result = classify_gap(interval_seconds=1800.0, t_nominal_seconds=300.0)
        
        # Then: MAJOR_GAP
        assert result["gap_class"] == "MAJOR_GAP"
    
    def test_fractional_seconds(self):
        """Fractional second intervals."""
        # Given: 1350.5 seconds (just over NORMAL boundary)
        result = classify_gap(interval_seconds=1350.5, t_nominal_seconds=900.0)
        
        # Then: MINOR_GAP
        assert result["gap_class"] == "MINOR_GAP"
    
    def test_metadata_completeness(self):
        """Verify all expected metadata fields are present."""
        # Given: any interval
        result = classify_gap(interval_seconds=2000.0, t_nominal_seconds=900.0)
        
        # Then: should have all fields
        assert "gap_class" in result
        assert "interval_seconds" in result
        assert "t_nominal_seconds" in result
        assert "factor" in result
        assert result["factor"] == pytest.approx(2000.0 / 900.0, rel=1e-6)

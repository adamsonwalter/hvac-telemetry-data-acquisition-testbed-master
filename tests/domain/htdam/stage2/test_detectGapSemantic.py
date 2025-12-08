"""
Unit tests for detectGapSemantic.py
Tests gap semantic classification (COV_CONSTANT, COV_MINOR, SENSOR_ANOMALY).
"""

import pytest
import numpy as np
from src.domain.htdam.stage2.detectGapSemantic import detect_gap_semantic


class TestDetectGapSemantic:
    """Test semantic classification of gaps based on value changes."""
    
    def test_cov_constant_no_change(self):
        """Value unchanged across gap (true COV behavior)."""
        # Given: identical values
        result = detect_gap_semantic(
            value_before=72.5,
            value_after=72.5,
            gap_class="MINOR_GAP"
        )
        
        # Then: COV_CONSTANT
        assert result["gap_semantic"] == "COV_CONSTANT"
        assert result["value_changed_relative_pct"] == 0.0
        assert result["confidence_penalty"] == 0.0
    
    def test_cov_constant_tiny_change_within_tolerance(self):
        """Value changed by tiny amount (within 0.5% tolerance)."""
        # Given: 0.3% change (within tolerance)
        result = detect_gap_semantic(
            value_before=100.0,
            value_after=100.3,  # 0.3% change
            gap_class="MINOR_GAP"
        )
        
        # Then: COV_CONSTANT (within tolerance)
        assert result["gap_semantic"] == "COV_CONSTANT"
        assert result["confidence_penalty"] == 0.0
    
    def test_cov_constant_at_tolerance_boundary(self):
        """Value changed by exactly 0.5% (boundary case)."""
        # Given: exactly 0.5% change
        result = detect_gap_semantic(
            value_before=100.0,
            value_after=100.5,
            gap_class="MINOR_GAP"
        )
        
        # Then: COV_CONSTANT (boundary is inclusive)
        assert result["gap_semantic"] == "COV_CONSTANT"
    
    def test_cov_minor_small_change(self):
        """Value changed by small amount (0.5% < change < 5%)."""
        # Given: 2% change
        result = detect_gap_semantic(
            value_before=50.0,
            value_after=51.0,  # 2% change
            gap_class="MINOR_GAP"
        )
        
        # Then: COV_MINOR
        assert result["gap_semantic"] == "COV_MINOR"
        assert result["confidence_penalty"] == -0.02
        assert result["value_changed_relative_pct"] == pytest.approx(2.0, rel=0.01)
    
    def test_cov_minor_at_anomaly_boundary(self):
        """Value changed by exactly 5% (boundary case)."""
        # Given: exactly 5% change
        result = detect_gap_semantic(
            value_before=100.0,
            value_after=105.0,
            gap_class="MINOR_GAP"
        )
        
        # Then: COV_MINOR (boundary is inclusive)
        assert result["gap_semantic"] == "COV_MINOR"
        assert result["confidence_penalty"] == -0.02
    
    def test_sensor_anomaly_large_jump(self):
        """Value changed by large amount (>5%)."""
        # Given: 15% change
        result = detect_gap_semantic(
            value_before=80.0,
            value_after=92.0,  # 15% change
            gap_class="MAJOR_GAP"
        )
        
        # Then: SENSOR_ANOMALY
        assert result["gap_semantic"] == "SENSOR_ANOMALY"
        assert result["confidence_penalty"] == -0.05
        assert result["value_changed_relative_pct"] == pytest.approx(15.0, rel=0.01)
    
    def test_sensor_anomaly_massive_jump(self):
        """Very large value change (>>5%)."""
        # Given: 50% change
        result = detect_gap_semantic(
            value_before=60.0,
            value_after=90.0,  # 50% change
            gap_class="MAJOR_GAP"
        )
        
        # Then: SENSOR_ANOMALY with large penalty
        assert result["gap_semantic"] == "SENSOR_ANOMALY"
        assert result["confidence_penalty"] == -0.05
    
    def test_negative_value_change(self):
        """Value decreased across gap."""
        # Given: 3% decrease
        result = detect_gap_semantic(
            value_before=100.0,
            value_after=97.0,  # -3% change
            gap_class="MINOR_GAP"
        )
        
        # Then: COV_MINOR (absolute change matters)
        assert result["gap_semantic"] == "COV_MINOR"
        assert result["value_changed_relative_pct"] == pytest.approx(-3.0, rel=0.01)
    
    def test_normal_interval_no_gap_classification(self):
        """Normal interval (no gap) - semantic should be N/A."""
        # Given: NORMAL gap class
        result = detect_gap_semantic(
            value_before=70.0,
            value_after=75.0,
            gap_class="NORMAL"
        )
        
        # Then: N/A (no gap analysis for normal intervals)
        assert result["gap_semantic"] == "N/A"
        assert result["confidence_penalty"] == 0.0
    
    def test_zero_denominator_zero_before_value(self):
        """Edge case: value_before is zero."""
        # Given: zero before value, non-zero after
        result = detect_gap_semantic(
            value_before=0.0,
            value_after=5.0,
            gap_class="MINOR_GAP"
        )
        
        # Then: should handle gracefully (infinite % change)
        assert result["gap_semantic"] == "SENSOR_ANOMALY"
        assert result["confidence_penalty"] == -0.05
    
    def test_both_values_zero(self):
        """Edge case: both values are zero."""
        # Given: both zero
        result = detect_gap_semantic(
            value_before=0.0,
            value_after=0.0,
            gap_class="MINOR_GAP"
        )
        
        # Then: should be COV_CONSTANT (no change)
        assert result["gap_semantic"] == "COV_CONSTANT"
        assert result["value_changed_relative_pct"] == 0.0
    
    def test_negative_values(self):
        """Handle negative sensor values (e.g., errors)."""
        # Given: negative values
        result = detect_gap_semantic(
            value_before=-10.0,
            value_after=-8.0,
            gap_class="MINOR_GAP"
        )
        
        # Then: should calculate relative change correctly
        # (-8 - (-10)) / |-10| = 2 / 10 = 20%
        assert result["gap_semantic"] == "SENSOR_ANOMALY"
    
    def test_nan_value_handling(self):
        """Handle NaN values in input."""
        # Given: NaN value
        result = detect_gap_semantic(
            value_before=50.0,
            value_after=np.nan,
            gap_class="MINOR_GAP"
        )
        
        # Then: should flag as anomaly
        assert result["gap_semantic"] == "SENSOR_ANOMALY"
    
    def test_metadata_completeness(self):
        """Verify all expected metadata fields."""
        # Given: any valid input
        result = detect_gap_semantic(
            value_before=100.0,
            value_after=102.0,
            gap_class="MINOR_GAP"
        )
        
        # Then: should have all fields
        assert "gap_semantic" in result
        assert "value_changed_relative_pct" in result
        assert "confidence_penalty" in result
        assert "value_before" in result
        assert "value_after" in result

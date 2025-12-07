"""
Tests for HTDAM Stage 1: Confidence Scoring

Pure function tests - NO MOCKS NEEDED.
All functions are deterministic with no side effects.
"""

import pytest
import pandas as pd

from src.domain.htdam.stage1.computeConfidence import (
    compute_unit_confidence,
    compute_physics_confidence,
    compute_channel_confidence,
    compute_stage1_confidence,
    compute_stage1_penalty,
    compute_all_confidences,
)


class TestComputeUnitConfidence:
    """Test unit confidence calculation."""
    
    def test_perfect_unit_confidence(self):
        """Should return 1.0 for perfect unit detection."""
        confidence = compute_unit_confidence(
            detected_unit="C",
            detection_confidence=0.95,
            conversion_applied=False,
            metadata_provided=True
        )
        assert confidence == 1.0
    
    def test_missing_unit_penalty(self):
        """Should apply -0.30 penalty for missing unit."""
        confidence = compute_unit_confidence(
            detected_unit="C",
            detection_confidence=0.80,
            conversion_applied=False,
            metadata_provided=False  # Had to infer
        )
        # 1.0 - 0.30 (missing) = 0.70
        assert confidence == 0.70
    
    def test_ambiguous_unit_penalty(self):
        """Should apply -0.20 penalty for ambiguous detection."""
        confidence = compute_unit_confidence(
            detected_unit="C",
            detection_confidence=0.70,  # < 0.80 = ambiguous
            conversion_applied=False,
            metadata_provided=True
        )
        # 1.0 - 0.20 (ambiguous) = 0.80
        assert confidence == 0.80
    
    def test_combined_penalties(self):
        """Should apply multiple penalties."""
        confidence = compute_unit_confidence(
            detected_unit="C",
            detection_confidence=0.70,  # < 0.80 = ambiguous
            conversion_applied=False,
            metadata_provided=False  # Had to infer
        )
        # 1.0 - 0.30 (missing) - 0.20 (ambiguous) = 0.50
        assert confidence == pytest.approx(0.50, abs=1e-9)
    
    def test_none_unit(self):
        """Should handle None unit gracefully."""
        confidence = compute_unit_confidence(
            detected_unit=None,
            detection_confidence=0.0,
            conversion_applied=False,
            metadata_provided=False
        )
        # 1.0 - 0.30 (missing) - 0.20 (ambiguous, conf=0.0 < 0.80) = 0.50
        assert confidence == pytest.approx(0.50, abs=1e-9)


class TestComputePhysicsConfidence:
    """Test physics confidence calculation."""
    
    def test_no_violations(self):
        """Should return 1.0 for no violations."""
        confidence = compute_physics_confidence(violations_pct=0.0)
        assert confidence == 1.0
    
    def test_half_percent_violations(self):
        """Should apply correct penalty for 0.5% violations."""
        confidence = compute_physics_confidence(violations_pct=0.5)
        # 1.0 - (0.5 / 100 × 0.10) = 1.0 - 0.0005 = 0.9995
        assert confidence == pytest.approx(0.9995, rel=0.001)
    
    def test_one_percent_violations(self):
        """Should apply correct penalty for 1% violations."""
        confidence = compute_physics_confidence(violations_pct=1.0)
        # 1.0 - (1.0 / 100 × 0.10) = 1.0 - 0.001 = 0.999
        assert confidence == pytest.approx(0.999, rel=0.001)
    
    def test_five_percent_violations(self):
        """Should apply correct penalty for 5% violations."""
        confidence = compute_physics_confidence(violations_pct=5.0)
        # 1.0 - (5.0 / 100 × 0.10) = 1.0 - 0.005 = 0.995
        assert confidence == pytest.approx(0.995, rel=0.001)


class TestComputeChannelConfidence:
    """Test channel confidence calculation."""
    
    def test_perfect_channel(self):
        """Should return 1.0 when both unit and physics are perfect."""
        confidence = compute_channel_confidence(
            unit_confidence=1.0,
            physics_confidence=1.0
        )
        assert confidence == 1.0
    
    def test_limited_by_unit_confidence(self):
        """Should be limited by unit confidence."""
        confidence = compute_channel_confidence(
            unit_confidence=0.80,
            physics_confidence=1.0
        )
        assert confidence == 0.80
    
    def test_limited_by_physics_confidence(self):
        """Should be limited by physics confidence."""
        confidence = compute_channel_confidence(
            unit_confidence=1.0,
            physics_confidence=0.90
        )
        assert confidence == 0.90
    
    def test_limited_by_lowest(self):
        """Should use minimum of both."""
        confidence = compute_channel_confidence(
            unit_confidence=0.75,
            physics_confidence=0.85
        )
        assert confidence == 0.75


class TestComputeStage1Confidence:
    """Test overall Stage 1 confidence calculation."""
    
    def test_all_channels_perfect(self):
        """Should return 1.0 when all channels are perfect."""
        confidences = {
            "CHWST": 1.0,
            "CHWRT": 1.0,
            "CDWRT": 1.0,
            "FLOW": 1.0,
            "POWER": 1.0
        }
        stage1_conf = compute_stage1_confidence(confidences)
        assert stage1_conf == 1.0
    
    def test_limited_by_weakest_channel(self):
        """Should be limited by weakest channel."""
        confidences = {
            "CHWST": 0.95,
            "CHWRT": 0.90,
            "CDWRT": 0.95,
            "FLOW": 1.0,
            "POWER": 0.80  # Weakest
        }
        stage1_conf = compute_stage1_confidence(confidences)
        assert stage1_conf == 0.80
    
    def test_empty_dict(self):
        """Should return 0.0 for empty dict."""
        stage1_conf = compute_stage1_confidence({})
        assert stage1_conf == 0.0


class TestComputeStage1Penalty:
    """Test Stage 1 penalty calculation."""
    
    def test_high_confidence_no_penalty(self):
        """Should apply no penalty for ≥0.95 confidence."""
        penalty = compute_stage1_penalty(0.95)
        assert penalty == -0.0
        
        penalty = compute_stage1_penalty(1.0)
        assert penalty == -0.0
    
    def test_medium_confidence_small_penalty(self):
        """Should apply -0.02 penalty for 0.80-0.95 confidence."""
        penalty = compute_stage1_penalty(0.85)
        assert penalty == -0.02
        
        penalty = compute_stage1_penalty(0.94)
        assert penalty == -0.02
    
    def test_low_confidence_medium_penalty(self):
        """Should apply -0.05 penalty for <0.80 confidence."""
        penalty = compute_stage1_penalty(0.75)
        assert penalty == -0.05
        
        penalty = compute_stage1_penalty(0.50)
        assert penalty == -0.05
        
        penalty = compute_stage1_penalty(0.0)
        assert penalty == -0.05


class TestComputeAllConfidences:
    """Test comprehensive confidence calculation."""
    
    def test_all_perfect(self):
        """Should compute perfect confidence for clean data."""
        conversions = {
            "CHWST": {
                "from_unit": "C",
                "detection_confidence": 0.95,
                "conversion_applied": False
            },
            "CHWRT": {
                "from_unit": "C",
                "detection_confidence": 0.95,
                "conversion_applied": False
            },
            "CDWRT": {
                "from_unit": "C",
                "detection_confidence": 0.95,
                "conversion_applied": False
            },
            "FLOW": {
                "from_unit": "m3/s",
                "detection_confidence": 0.95,
                "conversion_applied": False
            },
            "POWER": {
                "from_unit": "kW",
                "detection_confidence": 0.95,
                "conversion_applied": False
            }
        }
        
        validations = {
            "temperature_ranges": {
                "CHWST": {"violations_pct": 0.0},
                "CHWRT": {"violations_pct": 0.0},
                "CDWRT": {"violations_pct": 0.0}
            },
            "non_negative": {
                "FLOW": {"negative_pct": 0.0},
                "POWER": {"negative_pct": 0.0}
            }
        }
        
        result = compute_all_confidences(conversions, validations)
        
        assert result["stage1_confidence"] == 1.0
        assert result["stage1_penalty"] == -0.0
        assert all(conf == 1.0 for conf in result["channel_confidences"].values())
    
    def test_limited_by_weakest_channel(self):
        """Should be limited by weakest channel."""
        conversions = {
            "CHWST": {
                "from_unit": "C",
                "detection_confidence": 0.95,
                "conversion_applied": False
            },
            "CHWRT": {
                "from_unit": "C",
                "detection_confidence": 0.95,
                "conversion_applied": False
            },
            "CDWRT": {
                "from_unit": "C",
                "detection_confidence": 0.95,
                "conversion_applied": False
            },
            "FLOW": {
                "from_unit": "m3/s",
                "detection_confidence": 0.95,
                "conversion_applied": False
            },
            "POWER": {
                "from_unit": "kW",
                "detection_confidence": 0.70,  # Low confidence
                "conversion_applied": True
            }
        }
        
        validations = {
            "temperature_ranges": {
                "CHWST": {"violations_pct": 0.0},
                "CHWRT": {"violations_pct": 0.0},
                "CDWRT": {"violations_pct": 0.0}
            },
            "non_negative": {
                "FLOW": {"negative_pct": 0.0},
                "POWER": {"negative_pct": 0.0}
            }
        }
        
        result = compute_all_confidences(conversions, validations)
        
        # POWER should be weakest due to low detection confidence + inference
        # 1.0 - 0.30 (inferred) - 0.20 (ambiguous) = 0.50
        assert result["channel_confidences"]["POWER"] == pytest.approx(0.50, abs=1e-9)
        assert result["stage1_confidence"] == pytest.approx(0.50, abs=1e-9)  # Limited by POWER
        assert result["stage1_penalty"] == -0.05  # < 0.80
    
    def test_missing_channel(self):
        """Should handle missing channel gracefully."""
        conversions = {
            "CHWST": {
                "from_unit": "C",
                "detection_confidence": 0.95,
                "conversion_applied": False
            }
            # Missing other channels
        }
        
        validations = {
            "temperature_ranges": {},
            "non_negative": {}
        }
        
        result = compute_all_confidences(conversions, validations)
        
        # Missing channels should have 0.0 confidence
        assert result["channel_confidences"]["CHWRT"] == 0.0
        assert result["channel_confidences"]["CDWRT"] == 0.0
        assert result["channel_confidences"]["FLOW"] == 0.0
        assert result["channel_confidences"]["POWER"] == 0.0
        
        # Overall should be 0.0 (limited by missing channels)
        assert result["stage1_confidence"] == 0.0
        assert result["stage1_penalty"] == -0.05


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Unit tests for Stage 3 helper functions:
- getAlignmentConfidence.py
- computeCoveragePenalty.py
- deriveRowGapTypeAndConfidence.py
"""

import pytest
import pandas as pd
from src.domain.htdam.stage3.getAlignmentConfidence import get_alignment_confidence
from src.domain.htdam.stage3.computeCoveragePenalty import compute_coverage_penalty
from src.domain.htdam.stage3.deriveRowGapTypeAndConfidence import derive_row_gap_type_and_confidence


class TestGetAlignmentConfidence:
    """Test suite for get_alignment_confidence()"""

    def test_exact_alignment(self):
        """Test EXACT quality tier"""
        conf = get_alignment_confidence("EXACT")
        assert conf == 1.00

    def test_close_alignment(self):
        """Test CLOSE quality tier"""
        conf = get_alignment_confidence("CLOSE")
        assert conf == 0.95

    def test_interp_alignment(self):
        """Test INTERP quality tier"""
        conf = get_alignment_confidence("INTERP")
        assert conf == 0.80

    def test_missing_alignment(self):
        """Test MISSING quality tier"""
        conf = get_alignment_confidence("MISSING")
        assert conf == 0.00

    def test_unknown_quality_defaults_to_zero(self):
        """Test unknown quality defaults to 0"""
        conf = get_alignment_confidence("UNKNOWN")
        assert conf == 0.00

    def test_case_sensitivity(self):
        """Test that quality labels are case-sensitive"""
        conf = get_alignment_confidence("exact")  # lowercase
        assert conf == 0.00  # Should not match

    def test_whitespace_handling(self):
        """Test that whitespace matters"""
        conf = get_alignment_confidence(" EXACT ")
        assert conf == 0.00  # Should not match


class TestComputeCoveragePenalty:
    """Test suite for compute_coverage_penalty()"""

    def test_excellent_coverage_no_penalty(self):
        """Test excellent coverage (≥95%) has no penalty"""
        penalty = compute_coverage_penalty(valid_pct=98.0)
        assert penalty == 0.00

    def test_excellent_boundary(self):
        """Test exactly at 95% boundary"""
        penalty = compute_coverage_penalty(valid_pct=95.0)
        assert penalty == 0.00

    def test_good_coverage_small_penalty(self):
        """Test good coverage (90-95%) has -0.02 penalty"""
        penalty = compute_coverage_penalty(valid_pct=92.5)
        assert penalty == -0.02

    def test_good_boundary_lower(self):
        """Test exactly at 90% boundary"""
        penalty = compute_coverage_penalty(valid_pct=90.0)
        assert penalty == -0.02

    def test_fair_coverage_moderate_penalty(self):
        """Test fair coverage (80-90%) has -0.05 penalty"""
        penalty = compute_coverage_penalty(valid_pct=85.0)
        assert penalty == -0.05

    def test_fair_boundary_lower(self):
        """Test exactly at 80% boundary"""
        penalty = compute_coverage_penalty(valid_pct=80.0)
        assert penalty == -0.05

    def test_poor_coverage_large_penalty(self):
        """Test poor coverage (<80%) has -0.10 penalty"""
        penalty = compute_coverage_penalty(valid_pct=75.0)
        assert penalty == -0.10

    def test_very_poor_coverage(self):
        """Test very poor coverage"""
        penalty = compute_coverage_penalty(valid_pct=50.0)
        assert penalty == -0.10

    def test_zero_coverage(self):
        """Test 0% coverage"""
        penalty = compute_coverage_penalty(valid_pct=0.0)
        assert penalty == -0.10

    def test_100_percent_coverage(self):
        """Test perfect 100% coverage"""
        penalty = compute_coverage_penalty(valid_pct=100.0)
        assert penalty == 0.00

    def test_bartech_scenario(self):
        """Test BarTech expected coverage (~93.8%)"""
        penalty = compute_coverage_penalty(valid_pct=93.8)
        assert penalty == -0.02  # Good tier


class TestDeriveRowGapTypeAndConfidence:
    """Test suite for derive_row_gap_type_and_confidence()"""

    def test_excluded_row(self):
        """Test row in exclusion window"""
        result = derive_row_gap_type_and_confidence(
            is_excluded=True,
            chwst_quality="MISSING",
            chwrt_quality="MISSING",
            cdwrt_quality="MISSING",
            flow_quality="MISSING",
            power_quality="MISSING",
            chwst_stage2_gap="MAJOR_GAP",
            chwrt_stage2_gap="MAJOR_GAP",
            cdwrt_stage2_gap="MAJOR_GAP",
            flow_stage2_gap="MAJOR_GAP",
            power_stage2_gap="MAJOR_GAP"
        )
        
        assert result["gap_type"] == "EXCLUDED"
        assert result["row_confidence"] == 0.0

    def test_valid_row_all_mandatory_exact(self):
        """Test VALID row with all mandatory streams EXACT"""
        result = derive_row_gap_type_and_confidence(
            is_excluded=False,
            chwst_quality="EXACT",
            chwrt_quality="EXACT",
            cdwrt_quality="EXACT",
            flow_quality="EXACT",
            power_quality="EXACT",
            chwst_stage2_gap="VALID",
            chwrt_stage2_gap="VALID",
            cdwrt_stage2_gap="VALID",
            flow_stage2_gap="VALID",
            power_stage2_gap="VALID"
        )
        
        assert result["gap_type"] == "VALID"
        assert result["row_confidence"] == 1.0  # All EXACT

    def test_valid_row_mixed_quality(self):
        """Test VALID row with mixed quality tiers"""
        result = derive_row_gap_type_and_confidence(
            is_excluded=False,
            chwst_quality="EXACT",
            chwrt_quality="CLOSE",
            cdwrt_quality="INTERP",
            flow_quality="EXACT",
            power_quality="CLOSE",
            chwst_stage2_gap="VALID",
            chwrt_stage2_gap="VALID",
            cdwrt_stage2_gap="VALID",
            flow_stage2_gap="VALID",
            power_stage2_gap="VALID"
        )
        
        assert result["gap_type"] == "VALID"
        # Average: (1.0 + 0.95 + 0.80 + 1.0 + 0.95) / 5 = 0.94
        assert abs(result["row_confidence"] - 0.94) < 0.01

    def test_missing_mandatory_stream_is_major_gap(self):
        """Test row with missing mandatory stream is MAJOR_GAP"""
        result = derive_row_gap_type_and_confidence(
            is_excluded=False,
            chwst_quality="EXACT",
            chwrt_quality="MISSING",  # Mandatory missing
            cdwrt_quality="EXACT",
            flow_quality="EXACT",
            power_quality="EXACT",
            chwst_stage2_gap="VALID",
            chwrt_stage2_gap="MAJOR_GAP",
            cdwrt_stage2_gap="VALID",
            flow_stage2_gap="VALID",
            power_stage2_gap="VALID"
        )
        
        assert result["gap_type"] == "MAJOR_GAP"
        assert result["row_confidence"] == 0.0

    def test_stage2_major_gap_propagates(self):
        """Test Stage 2 MAJOR_GAP in mandatory stream propagates"""
        result = derive_row_gap_type_and_confidence(
            is_excluded=False,
            chwst_quality="EXACT",
            chwrt_quality="EXACT",
            cdwrt_quality="EXACT",
            flow_quality="EXACT",
            power_quality="EXACT",
            chwst_stage2_gap="MAJOR_GAP",  # Stage 2 says MAJOR_GAP
            chwrt_stage2_gap="VALID",
            cdwrt_stage2_gap="VALID",
            flow_stage2_gap="VALID",
            power_stage2_gap="VALID"
        )
        
        assert result["gap_type"] == "MAJOR_GAP"
        assert result["row_confidence"] == 0.0

    def test_optional_streams_dont_block_valid(self):
        """Test missing optional streams don't prevent VALID"""
        result = derive_row_gap_type_and_confidence(
            is_excluded=False,
            chwst_quality="EXACT",
            chwrt_quality="EXACT",
            cdwrt_quality="EXACT",
            flow_quality="MISSING",  # Optional missing
            power_quality="MISSING",  # Optional missing
            chwst_stage2_gap="VALID",
            chwrt_stage2_gap="VALID",
            cdwrt_stage2_gap="VALID",
            flow_stage2_gap="MAJOR_GAP",
            power_stage2_gap="MAJOR_GAP"
        )
        
        assert result["gap_type"] == "VALID"
        # Only mandatory streams count: (1.0 + 1.0 + 1.0) / 3 = 1.0
        assert result["row_confidence"] == 1.0

    def test_returns_dict_with_correct_keys(self):
        """Test output schema"""
        result = derive_row_gap_type_and_confidence(
            is_excluded=False,
            chwst_quality="EXACT",
            chwrt_quality="EXACT",
            cdwrt_quality="EXACT",
            flow_quality="EXACT",
            power_quality="EXACT",
            chwst_stage2_gap="VALID",
            chwrt_stage2_gap="VALID",
            cdwrt_stage2_gap="VALID",
            flow_stage2_gap="VALID",
            power_stage2_gap="VALID"
        )
        
        assert isinstance(result, dict)
        assert "gap_type" in result
        assert "row_confidence" in result
        assert len(result) == 2

    def test_exclusion_overrides_everything(self):
        """Test exclusion checked FIRST (overrides all other logic)"""
        result = derive_row_gap_type_and_confidence(
            is_excluded=True,  # EXCLUDED
            chwst_quality="EXACT",  # But everything looks good
            chwrt_quality="EXACT",
            cdwrt_quality="EXACT",
            flow_quality="EXACT",
            power_quality="EXACT",
            chwst_stage2_gap="VALID",
            chwrt_stage2_gap="VALID",
            cdwrt_stage2_gap="VALID",
            flow_stage2_gap="VALID",
            power_stage2_gap="VALID"
        )
        
        # Exclusion takes priority
        assert result["gap_type"] == "EXCLUDED"
        assert result["row_confidence"] == 0.0

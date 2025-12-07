"""
Tests for HTDAM Stage 1: Physics Validation

Pure function tests - NO MOCKS NEEDED.
All functions are deterministic with no side effects.
"""

import pytest
import pandas as pd
import numpy as np

from src.domain.htdam.stage1.validatePhysics import (
    validate_temperature_range,
    validate_temperature_relationships,
    validate_non_negative,
    validate_all_physics,
    compute_physics_confidence,
)


class TestValidateTemperatureRange:
    """Test temperature range validation."""
    
    def test_chwst_all_valid(self):
        """Should pass when all CHWST values are valid."""
        temps = pd.Series([6, 8, 10, 12, 14])
        result = validate_temperature_range(temps, "CHWST", 3.0, 20.0)
        
        assert result["violations_count"] == 0
        assert result["violations_pct"] == 0.0
        assert len(result["outside_range_indices"]) == 0
    
    def test_chwst_with_violations(self):
        """Should detect CHWST violations."""
        temps = pd.Series([2, 8, 10, 12, 25])  # 2°C too low, 25°C too high
        result = validate_temperature_range(temps, "CHWST", 3.0, 20.0)
        
        assert result["violations_count"] == 2
        assert result["violations_pct"] == 40.0  # 2/5 = 40%
        assert len(result["outside_range_indices"]) == 2
    
    def test_chwrt_all_valid(self):
        """Should pass when all CHWRT values are valid."""
        temps = pd.Series([12, 14, 16, 18, 20])
        result = validate_temperature_range(temps, "CHWRT", 5.0, 30.0)
        
        assert result["violations_count"] == 0
        assert result["violations_pct"] == 0.0
    
    def test_cdwrt_all_valid(self):
        """Should pass when all CDWRT values are valid."""
        temps = pd.Series([20, 22, 24, 26, 28])
        result = validate_temperature_range(temps, "CDWRT", 15.0, 45.0)
        
        assert result["violations_count"] == 0
        assert result["violations_pct"] == 0.0
    
    def test_actual_min_max_reported(self):
        """Should report actual min/max values."""
        temps = pd.Series([6, 8, 10, 12, 14])
        result = validate_temperature_range(temps, "CHWST", 3.0, 20.0)
        
        assert result["actual_min"] == 6.0
        assert result["actual_max"] == 14.0


class TestValidateTemperatureRelationships:
    """Test temperature relationship validation."""
    
    def test_all_relationships_valid(self):
        """Should pass when all relationships are valid."""
        chwst = pd.Series([6, 8, 10])
        chwrt = pd.Series([12, 14, 16])
        cdwrt = pd.Series([20, 22, 24])
        
        result = validate_temperature_relationships(chwst, chwrt, cdwrt)
        
        assert result["chwrt_lt_chwst_count"] == 0
        assert result["chwrt_lt_chwst_pct"] == 0.0
        assert result["cdwrt_lte_chwst_count"] == 0
        assert result["cdwrt_lte_chwst_pct"] == 0.0
    
    def test_chwrt_lt_chwst_violation(self):
        """Should detect when CHWRT < CHWST."""
        chwst = pd.Series([10, 10, 10])
        chwrt = pd.Series([8, 10, 12])  # First value violates
        cdwrt = pd.Series([20, 20, 20])
        
        result = validate_temperature_relationships(chwst, chwrt, cdwrt)
        
        assert result["chwrt_lt_chwst_count"] == 1
        assert result["chwrt_lt_chwst_pct"] == pytest.approx(33.33, rel=0.1)
    
    def test_cdwrt_lte_chwst_violation(self):
        """Should detect when CDWRT ≤ CHWST."""
        chwst = pd.Series([10, 10, 10])
        chwrt = pd.Series([12, 12, 12])
        cdwrt = pd.Series([8, 10, 20])  # First two violate
        
        result = validate_temperature_relationships(chwst, chwrt, cdwrt)
        
        assert result["cdwrt_lte_chwst_count"] == 2
        assert result["cdwrt_lte_chwst_pct"] == pytest.approx(66.67, rel=0.1)
    
    def test_multiple_violations(self):
        """Should detect multiple relationship violations."""
        chwst = pd.Series([10, 10, 10, 10])
        chwrt = pd.Series([8, 12, 8, 12])  # 2 violations
        cdwrt = pd.Series([8, 20, 8, 20])  # 2 violations
        
        result = validate_temperature_relationships(chwst, chwrt, cdwrt)
        
        assert result["chwrt_lt_chwst_count"] == 2
        assert result["cdwrt_lte_chwst_count"] == 2


class TestValidateNonNegative:
    """Test non-negative validation."""
    
    def test_flow_all_positive(self):
        """Should pass when all flow values are positive."""
        flow = pd.Series([0.05, 0.08, 0.10, 0.12, 0.15])
        result = validate_non_negative(flow, "FLOW")
        
        assert result["negative_count"] == 0
        assert result["negative_pct"] == 0.0
        assert len(result["negative_indices"]) == 0
    
    def test_flow_with_zero(self):
        """Should allow zero flow (chiller off)."""
        flow = pd.Series([0.0, 0.05, 0.10])
        result = validate_non_negative(flow, "FLOW")
        
        assert result["negative_count"] == 0
        assert result["negative_pct"] == 0.0
    
    def test_flow_with_negative(self):
        """Should detect negative flow values."""
        flow = pd.Series([0.05, -0.02, 0.10, -0.01, 0.15])
        result = validate_non_negative(flow, "FLOW")
        
        assert result["negative_count"] == 2
        assert result["negative_pct"] == 40.0
        assert len(result["negative_indices"]) == 2
    
    def test_power_all_positive(self):
        """Should pass when all power values are positive."""
        power = pd.Series([100, 150, 200, 250, 300])
        result = validate_non_negative(power, "POWER")
        
        assert result["negative_count"] == 0
        assert result["negative_pct"] == 0.0
    
    def test_power_with_negative(self):
        """Should detect negative power values."""
        power = pd.Series([100, -50, 200])
        result = validate_non_negative(power, "POWER")
        
        assert result["negative_count"] == 1
        assert result["negative_pct"] == pytest.approx(33.33, rel=0.1)


class TestValidateAllPhysics:
    """Test comprehensive physics validation."""
    
    def test_all_physics_valid(self):
        """Should pass when all physics constraints are met."""
        df = pd.DataFrame({
            "chwst": [6, 8, 10],
            "chwrt": [12, 14, 16],
            "cdwrt": [20, 22, 24],
            "flow_m3s": [0.05, 0.08, 0.10],
            "power_kw": [100, 150, 200]
        })
        
        result = validate_all_physics(df, {})
        
        assert result["halt_required"] is False
        assert len(result["halt_reasons"]) == 0
        
        # Check all range validations passed
        assert result["temperature_ranges"]["CHWST"]["violations_count"] == 0
        assert result["temperature_ranges"]["CHWRT"]["violations_count"] == 0
        assert result["temperature_ranges"]["CDWRT"]["violations_count"] == 0
        
        # Check relationships passed
        assert result["temperature_relationships"]["chwrt_lt_chwst_count"] == 0
        assert result["temperature_relationships"]["cdwrt_lte_chwst_count"] == 0
        
        # Check non-negative passed
        assert result["non_negative"]["FLOW"]["negative_count"] == 0
        assert result["non_negative"]["POWER"]["negative_count"] == 0
    
    def test_halt_on_negative_flow(self):
        """Should HALT when flow is negative."""
        df = pd.DataFrame({
            "chwst": [6, 8, 10],
            "chwrt": [12, 14, 16],
            "cdwrt": [20, 22, 24],
            "flow_m3s": [0.05, -0.02, 0.10],  # Negative flow
            "power_kw": [100, 150, 200]
        })
        
        result = validate_all_physics(df, {})
        
        assert result["halt_required"] is True
        assert any("FLOW" in reason for reason in result["halt_reasons"])
    
    def test_halt_on_negative_power(self):
        """Should HALT when power is negative."""
        df = pd.DataFrame({
            "chwst": [6, 8, 10],
            "chwrt": [12, 14, 16],
            "cdwrt": [20, 22, 24],
            "flow_m3s": [0.05, 0.08, 0.10],
            "power_kw": [100, -50, 200]  # Negative power
        })
        
        result = validate_all_physics(df, {})
        
        assert result["halt_required"] is True
        assert any("POWER" in reason for reason in result["halt_reasons"])
    
    def test_halt_on_chwrt_lt_chwst(self):
        """Should HALT when CHWRT < CHWST in >1% of samples."""
        # Create 100 samples with 2 violations (2%)
        chwst = pd.Series([10] * 100)
        chwrt = pd.Series([12] * 98 + [8, 8])  # 2 violations
        cdwrt = pd.Series([20] * 100)
        
        df = pd.DataFrame({
            "chwst": chwst,
            "chwrt": chwrt,
            "cdwrt": cdwrt,
            "flow_m3s": [0.05] * 100,
            "power_kw": [100] * 100
        })
        
        result = validate_all_physics(df, {})
        
        assert result["halt_required"] is True
        assert any("CHWRT < CHWST" in reason for reason in result["halt_reasons"])
    
    def test_no_halt_on_minor_violations(self):
        """Should NOT HALT when violations are <1%."""
        # Create 1000 samples with 5 violations (0.5%)
        chwst = pd.Series([10] * 1000)
        chwrt = pd.Series([12] * 995 + [8] * 5)  # 0.5% violations
        cdwrt = pd.Series([20] * 1000)
        
        df = pd.DataFrame({
            "chwst": chwst,
            "chwrt": chwrt,
            "cdwrt": cdwrt,
            "flow_m3s": [0.05] * 1000,
            "power_kw": [100] * 1000
        })
        
        result = validate_all_physics(df, {})
        
        # Should have violations but NOT halt
        assert result["temperature_relationships"]["chwrt_lt_chwst_count"] == 5
        assert result["halt_required"] is False


class TestComputePhysicsConfidence:
    """Test physics confidence calculation."""
    
    def test_perfect_physics_confidence(self):
        """Should return 1.0 for perfect physics."""
        validations = {
            "temperature_ranges": {
                "CHWST": {"violations_pct": 0.0},
                "CHWRT": {"violations_pct": 0.0},
                "CDWRT": {"violations_pct": 0.0}
            },
            "temperature_relationships": {
                "chwrt_lt_chwst_pct": 0.0,
                "cdwrt_lte_chwst_pct": 0.0
            },
            "non_negative": {
                "FLOW": {"negative_pct": 0.0},
                "POWER": {"negative_pct": 0.0}
            },
            "halt_required": False,
            "halt_reasons": []
        }
        
        confidence, halt, reasons = compute_physics_confidence(validations)
        
        assert confidence == 1.0
        assert halt is False
        assert len(reasons) == 0
    
    def test_minor_violations_reduce_confidence(self):
        """Should reduce confidence for minor violations."""
        validations = {
            "temperature_ranges": {
                "CHWST": {"violations_pct": 0.5}  # 0.5% violations
            },
            "temperature_relationships": {},
            "non_negative": {},
            "halt_required": False,
            "halt_reasons": []
        }
        
        confidence, halt, reasons = compute_physics_confidence(validations)
        
        # 0.5% violations × 0.10 penalty = 0.005 penalty
        # 1.0 - 0.005 = 0.995
        assert confidence == pytest.approx(0.995, rel=0.01)
        assert halt is False
    
    def test_halt_returns_zero_confidence(self):
        """Should return 0.0 confidence when HALT required."""
        validations = {
            "temperature_ranges": {},
            "temperature_relationships": {},
            "non_negative": {},
            "halt_required": True,
            "halt_reasons": ["Test HALT reason"]
        }
        
        confidence, halt, reasons = compute_physics_confidence(validations)
        
        assert confidence == 0.0
        assert halt is True
        assert len(reasons) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

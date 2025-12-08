"""
Unit tests for validatePhysicsAtGap.py
Tests physics validation at gap boundaries (Delta-T checks, condenser relationships).
"""

import pytest
import numpy as np
from src.domain.htdam.stage2.validatePhysicsAtGap import validate_physics_at_gap


class TestValidatePhysicsAtGap:
    """Test thermodynamic validation at gap boundaries."""
    
    def test_valid_physics_normal_operation(self):
        """All physics checks pass (typical chiller operation)."""
        # Given: valid temps (CHWST < CHWRT < CDWRT)
        temps_before = {
            "CHWST": 44.0,  # 6.7°C
            "CHWRT": 54.0,  # 12.2°C
            "CDWRT": 85.0,  # 29.4°C
        }
        temps_after = {
            "CHWST": 43.5,
            "CHWRT": 53.5,
            "CDWRT": 84.0,
        }
        
        # When: validate physics
        result = validate_physics_at_gap(temps_before, temps_after)
        
        # Then: all checks pass
        assert result["physics_valid"] is True
        assert len(result["violations"]) == 0
    
    def test_invalid_chwst_greater_than_chwrt(self):
        """Supply temp exceeds return temp (impossible)."""
        # Given: CHWST > CHWRT
        temps_before = {
            "CHWST": 55.0,
            "CHWRT": 54.0,  # Less than supply!
            "CDWRT": 85.0,
        }
        temps_after = {
            "CHWST": 44.0,
            "CHWRT": 54.0,
            "CDWRT": 85.0,
        }
        
        # When: validate physics
        result = validate_physics_at_gap(temps_before, temps_after)
        
        # Then: violation detected
        assert result["physics_valid"] is False
        assert any("CHWST > CHWRT" in v for v in result["violations"])
    
    def test_invalid_chwrt_greater_than_cdwrt(self):
        """CHW return exceeds condenser return (cooling impossible)."""
        # Given: CHWRT > CDWRT
        temps_before = {
            "CHWST": 44.0,
            "CHWRT": 90.0,  # Hotter than condenser!
            "CDWRT": 85.0,
        }
        temps_after = {
            "CHWST": 44.0,
            "CHWRT": 54.0,
            "CDWRT": 85.0,
        }
        
        # When: validate physics
        result = validate_physics_at_gap(temps_before, temps_after)
        
        # Then: violation detected
        assert result["physics_valid"] is False
        assert any("CHWRT > CDWRT" in v for v in result["violations"])
    
    def test_delta_t_too_small(self):
        """CHW Delta-T too small (<2°F)."""
        # Given: tiny Delta-T
        temps_before = {
            "CHWST": 44.0,
            "CHWRT": 45.0,  # Only 1°F difference
            "CDWRT": 85.0,
        }
        temps_after = {
            "CHWST": 44.0,
            "CHWRT": 54.0,
            "CDWRT": 85.0,
        }
        
        # When: validate physics
        result = validate_physics_at_gap(temps_before, temps_after)
        
        # Then: violation detected
        assert result["physics_valid"] is False
        assert any("Delta-T too small" in v for v in result["violations"])
    
    def test_delta_t_too_large(self):
        """CHW Delta-T too large (>25°F)."""
        # Given: excessive Delta-T
        temps_before = {
            "CHWST": 40.0,
            "CHWRT": 70.0,  # 30°F difference (unlikely)
            "CDWRT": 85.0,
        }
        temps_after = {
            "CHWST": 44.0,
            "CHWRT": 54.0,
            "CDWRT": 85.0,
        }
        
        # When: validate physics
        result = validate_physics_at_gap(temps_before, temps_after)
        
        # Then: violation detected
        assert result["physics_valid"] is False
        assert any("Delta-T too large" in v for v in result["violations"])
    
    def test_multiple_violations(self):
        """Multiple physics violations at once."""
        # Given: multiple problems
        temps_before = {
            "CHWST": 55.0,  # Greater than CHWRT
            "CHWRT": 54.0,
            "CDWRT": 50.0,  # Less than CHWRT
        }
        temps_after = {
            "CHWST": 44.0,
            "CHWRT": 54.0,
            "CDWRT": 85.0,
        }
        
        # When: validate physics
        result = validate_physics_at_gap(temps_before, temps_after)
        
        # Then: multiple violations
        assert result["physics_valid"] is False
        assert len(result["violations"]) >= 2
    
    def test_missing_temperature_fields(self):
        """Handle missing/incomplete temp data."""
        # Given: missing CDWRT
        temps_before = {
            "CHWST": 44.0,
            "CHWRT": 54.0,
            # CDWRT missing
        }
        temps_after = {
            "CHWST": 44.0,
            "CHWRT": 54.0,
            "CDWRT": 85.0,
        }
        
        # When: validate physics
        result = validate_physics_at_gap(temps_before, temps_after)
        
        # Then: should handle gracefully (skip checks or flag as invalid)
        assert "violations" in result
    
    def test_nan_temperature_values(self):
        """Handle NaN temperature values."""
        # Given: NaN in temps
        temps_before = {
            "CHWST": 44.0,
            "CHWRT": np.nan,
            "CDWRT": 85.0,
        }
        temps_after = {
            "CHWST": 44.0,
            "CHWRT": 54.0,
            "CDWRT": 85.0,
        }
        
        # When: validate physics
        result = validate_physics_at_gap(temps_before, temps_after)
        
        # Then: should flag as invalid
        assert result["physics_valid"] is False
    
    def test_boundary_case_delta_t_exactly_2f(self):
        """Delta-T exactly at minimum threshold (2°F)."""
        # Given: exactly 2°F Delta-T
        temps_before = {
            "CHWST": 44.0,
            "CHWRT": 46.0,  # Exactly 2°F
            "CDWRT": 85.0,
        }
        temps_after = {
            "CHWST": 44.0,
            "CHWRT": 54.0,
            "CDWRT": 85.0,
        }
        
        # When: validate physics
        result = validate_physics_at_gap(temps_before, temps_after)
        
        # Then: should pass (boundary inclusive)
        assert result["physics_valid"] is True
    
    def test_boundary_case_delta_t_exactly_25f(self):
        """Delta-T exactly at maximum threshold (25°F)."""
        # Given: exactly 25°F Delta-T
        temps_before = {
            "CHWST": 40.0,
            "CHWRT": 65.0,  # Exactly 25°F
            "CDWRT": 85.0,
        }
        temps_after = {
            "CHWST": 44.0,
            "CHWRT": 54.0,
            "CDWRT": 85.0,
        }
        
        # When: validate physics
        result = validate_physics_at_gap(temps_before, temps_after)
        
        # Then: should pass (boundary inclusive)
        assert result["physics_valid"] is True
    
    def test_violation_after_gap_not_before(self):
        """Physics valid before gap, invalid after."""
        # Given: valid before, invalid after
        temps_before = {
            "CHWST": 44.0,
            "CHWRT": 54.0,
            "CDWRT": 85.0,
        }
        temps_after = {
            "CHWST": 55.0,  # Greater than return
            "CHWRT": 54.0,
            "CDWRT": 85.0,
        }
        
        # When: validate physics
        result = validate_physics_at_gap(temps_before, temps_after)
        
        # Then: violation detected (after gap)
        assert result["physics_valid"] is False
        assert any("after" in v.lower() for v in result["violations"])
    
    def test_metadata_completeness(self):
        """Verify all expected metadata fields."""
        # Given: any input
        temps_before = {"CHWST": 44.0, "CHWRT": 54.0, "CDWRT": 85.0}
        temps_after = {"CHWST": 44.0, "CHWRT": 54.0, "CDWRT": 85.0}
        
        # When: validate physics
        result = validate_physics_at_gap(temps_before, temps_after)
        
        # Then: should have all fields
        assert "physics_valid" in result
        assert "violations" in result
        assert isinstance(result["violations"], list)

"""
Tests for HTDAM Stage 1: Unit Detection

Pure function tests - NO MOCKS NEEDED.
All functions are deterministic with no side effects.
"""

import pytest
import pandas as pd
import numpy as np

from src.domain.htdam.stage1.detectUnits import (
    _parse_unit_from_metadata,
    detect_temperature_unit,
    detect_flow_unit,
    detect_power_unit,
    detect_all_units,
)


class TestParseUnitFromMetadata:
    """Test metadata parsing for unit strings."""
    
    def test_temperature_from_signal_name_degc(self):
        """Should detect °C from signal name."""
        result = _parse_unit_from_metadata("CHWST_degC")
        assert result == "C"
    
    def test_temperature_from_signal_name_degf(self):
        """Should detect °F from signal name."""
        result = _parse_unit_from_metadata("CHWST_degF")
        assert result == "F"
    
    def test_temperature_from_signal_name_symbol(self):
        """Should detect °C from symbol in name."""
        result = _parse_unit_from_metadata("Temperature_°C")
        assert result == "C"
    
    def test_flow_from_signal_name_gpm(self):
        """Should detect GPM from signal name."""
        result = _parse_unit_from_metadata("Flow_GPM")
        assert result == "GPM"
    
    def test_flow_from_signal_name_lps(self):
        """Should detect L/s from signal name."""
        result = _parse_unit_from_metadata("Flow_LPS")
        assert result == "L/s"
    
    def test_power_from_signal_name_kw(self):
        """Should detect kW from signal name."""
        result = _parse_unit_from_metadata("Power_kW")
        assert result == "kW"
    
    def test_unit_from_metadata_dict(self):
        """Should extract unit from metadata dict."""
        result = _parse_unit_from_metadata("Signal", metadata={"unit": "°C"})
        assert result == "C"
    
    def test_no_unit_found(self):
        """Should return None if no unit found."""
        result = _parse_unit_from_metadata("Unknown_Signal")
        assert result is None


class TestDetectTemperatureUnit:
    """Test temperature unit detection from data."""
    
    def test_celsius_typical_chwst(self):
        """Should detect Celsius for typical CHWST range."""
        temps = pd.Series([6, 8, 10, 12, 14])
        unit, confidence = detect_temperature_unit(temps, "CHWST")
        assert unit == "C"
        assert confidence >= 0.8
    
    def test_celsius_typical_chwrt(self):
        """Should detect Celsius for typical CHWRT range."""
        temps = pd.Series([12, 14, 16, 18, 20])
        unit, confidence = detect_temperature_unit(temps, "CHWRT")
        assert unit == "C"
        assert confidence >= 0.8
    
    def test_celsius_typical_cdwrt(self):
        """Should detect Celsius for typical CDWRT range."""
        temps = pd.Series([20, 22, 24, 26, 28])
        unit, confidence = detect_temperature_unit(temps, "CDWRT")
        assert unit == "C"
        assert confidence >= 0.8
    
    def test_fahrenheit_typical_chwst(self):
        """Should detect Fahrenheit for typical CHWST range."""
        temps = pd.Series([43, 46, 50, 54, 57])  # ~6-14°C in Fahrenheit
        unit, confidence = detect_temperature_unit(temps, "CHWST")
        assert unit == "F"
        assert confidence >= 0.8
    
    def test_fahrenheit_typical_cdwrt(self):
        """Should detect Fahrenheit for typical CDWRT range."""
        temps = pd.Series([68, 72, 75, 79, 82])  # ~20-28°C in Fahrenheit
        unit, confidence = detect_temperature_unit(temps, "CDWRT")
        assert unit == "F"
        assert confidence >= 0.8
    
    def test_kelvin_typical_range(self):
        """Should detect Kelvin for typical range."""
        temps = pd.Series([279, 281, 283, 285, 287])  # ~6-14°C in Kelvin
        unit, confidence = detect_temperature_unit(temps, "CHWST")
        assert unit == "K"
        assert confidence >= 0.8
    
    def test_metadata_override(self):
        """Should use metadata unit with high confidence."""
        temps = pd.Series([6, 8, 10, 12, 14])
        unit, confidence = detect_temperature_unit(
            temps, "CHWST_degC", metadata={"unit": "C"}
        )
        assert unit == "C"
        assert confidence == 0.95  # High confidence from metadata
    
    def test_signal_name_override(self):
        """Should detect unit from signal name with high confidence."""
        temps = pd.Series([6, 8, 10, 12, 14])
        unit, confidence = detect_temperature_unit(temps, "CHWST_degF")
        assert unit == "F"
        assert confidence == 0.95
    
    def test_unknown_range(self):
        """Should return None for out-of-range temps."""
        temps = pd.Series([100, 120, 140, 160, 180])  # Way too high
        unit, confidence = detect_temperature_unit(temps, "CHWST")
        assert unit is None
        assert confidence == 0.0
    
    def test_robust_to_outliers(self):
        """Should handle outliers using 99.5th percentile."""
        temps = pd.Series([6, 8, 10, 12, 14, 999])  # One outlier
        unit, confidence = detect_temperature_unit(temps, "CHWST")
        assert unit == "C"  # Should still detect Celsius
        assert confidence >= 0.8


class TestDetectFlowUnit:
    """Test flow unit detection from data."""
    
    def test_m3s_typical_range(self):
        """Should detect m³/s for typical range."""
        flow = pd.Series([0.05, 0.08, 0.10, 0.12, 0.15])
        unit, confidence = detect_flow_unit(flow, "CHWF")
        assert unit == "m3/s"
        assert confidence >= 0.8
    
    def test_ls_typical_range(self):
        """Should detect L/s for typical range."""
        flow = pd.Series([50, 80, 100, 120, 150])  # 0.05-0.15 m³/s in L/s
        unit, confidence = detect_flow_unit(flow, "Flow")
        assert unit == "L/s"
        assert confidence >= 0.8
    
    def test_gpm_typical_range(self):
        """Should detect GPM for typical range."""
        flow = pd.Series([800, 1200, 1600, 1900, 2400])  # ~0.05-0.15 m³/s in GPM
        unit, confidence = detect_flow_unit(flow, "Flow")
        assert unit == "GPM"
        assert confidence >= 0.6  # Lower confidence for wide range
    
    def test_m3h_typical_range(self):
        """Should detect m³/h for typical range."""
        flow = pd.Series([180, 288, 360, 432, 540])  # 0.05-0.15 m³/s in m³/h
        unit, confidence = detect_flow_unit(flow, "Flow")
        assert unit == "m3/h"
        assert confidence >= 0.8
    
    def test_metadata_override(self):
        """Should use metadata unit with high confidence."""
        flow = pd.Series([50, 80, 100])
        unit, confidence = detect_flow_unit(
            flow, "Flow_LPS", metadata={"unit": "L/s"}
        )
        assert unit == "L/s"
        assert confidence == 0.95
    
    def test_signal_name_gpm(self):
        """Should detect GPM from signal name."""
        flow = pd.Series([800, 1200, 1600])
        unit, confidence = detect_flow_unit(flow, "Water_Flow_GPM")
        assert unit == "GPM"
        assert confidence == 0.95
    
    def test_unknown_range(self):
        """Should return None for out-of-range flow."""
        flow = pd.Series([50000, 60000, 70000])  # Way too high
        unit, confidence = detect_flow_unit(flow, "Flow")
        assert unit is None
        assert confidence == 0.0
    
    def test_zero_flow(self):
        """Should handle zero flow values."""
        flow = pd.Series([0.0, 0.05, 0.10, 0.15])
        unit, confidence = detect_flow_unit(flow, "Flow")
        assert unit == "m3/s"
        assert confidence >= 0.8


class TestDetectPowerUnit:
    """Test power unit detection from data."""
    
    def test_kw_typical_range(self):
        """Should detect kW for typical chiller range."""
        power = pd.Series([50, 100, 200, 300, 400])
        unit, confidence = detect_power_unit(power, "Power")
        assert unit == "kW"
        assert confidence >= 0.8
    
    def test_watts_large_values(self):
        """Should detect W for large numeric values."""
        power = pd.Series([50000, 100000, 200000, 300000])
        unit, confidence = detect_power_unit(power, "Power")
        assert unit == "W"
        assert confidence >= 0.8
    
    def test_mw_small_values(self):
        """Should detect MW for small values."""
        power = pd.Series([0.05, 0.10, 0.20, 0.30])
        unit, confidence = detect_power_unit(power, "Power")
        assert unit == "MW"
        assert confidence >= 0.6  # Lower confidence (could be kW)
    
    def test_metadata_override(self):
        """Should use metadata unit with high confidence."""
        power = pd.Series([50, 100, 200])
        unit, confidence = detect_power_unit(
            power, "Chiller_Power", metadata={"unit": "kW"}
        )
        assert unit == "kW"
        assert confidence == 0.95
    
    def test_signal_name_kw(self):
        """Should detect kW from signal name."""
        power = pd.Series([50, 100, 200])
        unit, confidence = detect_power_unit(power, "Power_kW")
        assert unit == "kW"
        assert confidence == 0.95
    
    def test_signal_name_w(self):
        """Should detect W from signal name."""
        power = pd.Series([50000, 100000, 200000])
        unit, confidence = detect_power_unit(power, "Power_W")
        assert unit == "W"
        assert confidence == 0.95
    
    def test_zero_power(self):
        """Should handle zero power (chiller off)."""
        power = pd.Series([0, 50, 100, 200, 300])
        unit, confidence = detect_power_unit(power, "Power")
        assert unit == "kW"
        assert confidence >= 0.8
    
    def test_unknown_range(self):
        """Should return None for ambiguous range."""
        power = pd.Series([5, 8, 10])  # Too small for kW, could be anything
        unit, confidence = detect_power_unit(power, "Power")
        # Could detect as MW or unknown
        assert unit in ["MW", None]


class TestDetectAllUnits:
    """Test batch unit detection for all BMD signals."""
    
    def test_all_units_celsius_m3s_kw(self):
        """Should detect all units correctly for typical °C/m³/s/kW data."""
        df = pd.DataFrame({
            "CHWST": [6, 8, 10, 12, 14],
            "CHWRT": [12, 14, 16, 18, 20],
            "CDWRT": [20, 22, 24, 26, 28],
            "Flow": [0.05, 0.08, 0.10, 0.12, 0.15],
            "Power": [100, 150, 200, 250, 300]
        })
        
        mappings = {
            "CHWST": "CHWST",
            "CHWRT": "CHWRT",
            "CDWRT": "CDWRT",
            "FLOW": "Flow",
            "POWER": "Power"
        }
        
        results = detect_all_units(df, mappings)
        
        assert results["CHWST"][0] == "C"
        assert results["CHWRT"][0] == "C"
        assert results["CDWRT"][0] == "C"
        assert results["FLOW"][0] == "m3/s"
        assert results["POWER"][0] == "kW"
        
        # All should have reasonable confidence
        assert all(conf >= 0.8 for _, conf in results.values())
    
    def test_all_units_fahrenheit_gpm_w(self):
        """Should detect Fahrenheit, GPM, Watts."""
        df = pd.DataFrame({
            "Chiller_1_CHWST": [43, 46, 50, 54, 57],
            "Chiller_1_CHWRT": [54, 57, 61, 64, 68],
            "Chiller_1_CDWRT": [68, 72, 75, 79, 82],
            "Water_Flow": [800, 1200, 1600, 1900, 2400],
            "Chiller_Power": [100000, 150000, 200000, 250000, 300000]
        })
        
        mappings = {
            "CHWST": "Chiller_1_CHWST",
            "CHWRT": "Chiller_1_CHWRT",
            "CDWRT": "Chiller_1_CDWRT",
            "FLOW": "Water_Flow",
            "POWER": "Chiller_Power"
        }
        
        results = detect_all_units(df, mappings)
        
        assert results["CHWST"][0] == "F"
        assert results["CHWRT"][0] == "F"
        assert results["CDWRT"][0] == "F"
        assert results["FLOW"][0] == "GPM"
        assert results["POWER"][0] == "W"
    
    def test_missing_column(self):
        """Should handle missing columns gracefully."""
        df = pd.DataFrame({
            "CHWST": [6, 8, 10],
            "CHWRT": [12, 14, 16]
        })
        
        mappings = {
            "CHWST": "CHWST",
            "CHWRT": "CHWRT",
            "CDWRT": "Missing_Column",  # Doesn't exist
            "FLOW": "Also_Missing",
            "POWER": "Not_Here"
        }
        
        results = detect_all_units(df, mappings)
        
        assert results["CHWST"][0] == "C"
        assert results["CHWRT"][0] == "C"
        assert results["CDWRT"][0] is None
        assert results["FLOW"][0] is None
        assert results["POWER"][0] is None
        
        # Missing columns should have zero confidence
        assert results["CDWRT"][1] == 0.0
        assert results["FLOW"][1] == 0.0
        assert results["POWER"][1] == 0.0
    
    def test_with_metadata(self):
        """Should use metadata when provided."""
        df = pd.DataFrame({
            "Temp1": [6, 8, 10],
            "Temp2": [12, 14, 16],
            "Temp3": [20, 22, 24],
            "FlowRate": [50, 80, 100],
            "PowerDemand": [100, 150, 200]
        })
        
        mappings = {
            "CHWST": "Temp1",
            "CHWRT": "Temp2",
            "CDWRT": "Temp3",
            "FLOW": "FlowRate",
            "POWER": "PowerDemand"
        }
        
        metadata = {
            "Temp1": {"unit": "°C"},
            "Temp2": {"unit": "°C"},
            "Temp3": {"unit": "°C"},
            "FlowRate": {"unit": "L/s"},
            "PowerDemand": {"unit": "kW"}
        }
        
        results = detect_all_units(df, mappings, metadata)
        
        # All should use metadata with high confidence
        assert all(conf == 0.95 for _, conf in results.values())
        assert results["FLOW"][0] == "L/s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

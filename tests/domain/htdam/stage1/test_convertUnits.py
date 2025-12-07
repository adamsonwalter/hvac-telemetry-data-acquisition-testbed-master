"""
Tests for HTDAM Stage 1: Unit Conversion

Pure function tests - NO MOCKS NEEDED.
All functions are deterministic with no side effects.
"""

import pytest
import pandas as pd
import numpy as np

from src.domain.htdam.stage1.convertUnits import (
    convert_temperature,
    convert_flow,
    convert_power,
    convert_all_units,
)


class TestConvertTemperature:
    """Test temperature unit conversions."""
    
    def test_fahrenheit_to_celsius(self):
        """Should convert °F to °C correctly."""
        temps_f = pd.Series([32, 68, 212])
        converted, meta = convert_temperature(temps_f, "F", "C")
        
        expected = [0.0, 20.0, 100.0]
        assert list(converted.round(1)) == expected
        assert meta["conversion_applied"] is True
        assert meta["conversion_factor"] == "F_to_C"
    
    def test_kelvin_to_celsius(self):
        """Should convert K to °C correctly."""
        temps_k = pd.Series([273.15, 293.15, 373.15])
        converted, meta = convert_temperature(temps_k, "K", "C")
        
        expected = [0.0, 20.0, 100.0]
        assert list(converted.round(1)) == expected
        assert meta["conversion_applied"] is True
        assert meta["conversion_factor"] == "K_to_C"
    
    def test_celsius_to_celsius_passthrough(self):
        """Should pass through °C to °C without conversion."""
        temps_c = pd.Series([6, 8, 10, 12, 14])
        converted, meta = convert_temperature(temps_c, "C", "C")
        
        assert list(converted) == [6, 8, 10, 12, 14]
        assert meta["conversion_applied"] is False
    
    def test_fahrenheit_chwst_realistic(self):
        """Should convert realistic CHWST values."""
        temps_f = pd.Series([43, 46, 50, 54, 57])
        converted, meta = convert_temperature(temps_f, "F", "C")
        
        # 43°F ≈ 6.1°C, 57°F ≈ 13.9°C
        assert 6.0 <= converted.min() <= 6.5
        assert 13.5 <= converted.max() <= 14.5
    
    def test_kelvin_chwst_realistic(self):
        """Should convert realistic CHWST Kelvin values."""
        temps_k = pd.Series([279.15, 281.15, 283.15, 285.15, 287.15])
        converted, meta = convert_temperature(temps_k, "K", "C")
        
        # 279.15K = 6°C, 287.15K = 14°C
        assert list(converted) == [6, 8, 10, 12, 14]


class TestConvertFlow:
    """Test flow unit conversions."""
    
    def test_liters_per_second_to_m3s(self):
        """Should convert L/s to m³/s correctly."""
        flow_ls = pd.Series([50, 80, 100, 120, 150])
        converted, meta = convert_flow(flow_ls, "L/s", "m3/s")
        
        expected = [0.05, 0.08, 0.10, 0.12, 0.15]
        assert list(converted) == expected
        assert meta["conversion_applied"] is True
        assert meta["conversion_factor"] == 0.001
    
    def test_gpm_to_m3s(self):
        """Should convert GPM to m³/s correctly."""
        flow_gpm = pd.Series([793, 1268, 1585, 1902, 2378])
        converted, meta = convert_flow(flow_gpm, "GPM", "m3/s")
        
        # GPM × 0.0000630902 = m³/s
        # 793 GPM ≈ 0.05 m³/s
        assert 0.049 <= converted.iloc[0] <= 0.051
        assert 0.149 <= converted.iloc[4] <= 0.151
        assert meta["conversion_applied"] is True
    
    def test_m3h_to_m3s(self):
        """Should convert m³/h to m³/s correctly."""
        flow_m3h = pd.Series([180, 288, 360, 432, 540])
        converted, meta = convert_flow(flow_m3h, "m3/h", "m3/s")
        
        expected = [0.05, 0.08, 0.10, 0.12, 0.15]
        assert list(converted) == expected
        assert meta["conversion_applied"] is True
    
    def test_m3s_to_m3s_passthrough(self):
        """Should pass through m³/s without conversion."""
        flow_m3s = pd.Series([0.05, 0.08, 0.10, 0.12, 0.15])
        converted, meta = convert_flow(flow_m3s, "m3/s", "m3/s")
        
        assert list(converted) == [0.05, 0.08, 0.10, 0.12, 0.15]
        assert meta["conversion_applied"] is False
    
    def test_zero_flow(self):
        """Should handle zero flow (chiller off)."""
        flow_ls = pd.Series([0, 50, 100])
        converted, meta = convert_flow(flow_ls, "L/s", "m3/s")
        
        assert converted.iloc[0] == 0.0
        assert converted.iloc[1] == 0.05
        assert converted.iloc[2] == 0.10


class TestConvertPower:
    """Test power unit conversions."""
    
    def test_watts_to_kw(self):
        """Should convert W to kW correctly."""
        power_w = pd.Series([50000, 100000, 200000, 300000, 400000])
        converted, meta = convert_power(power_w, "W", "kW")
        
        expected = [50, 100, 200, 300, 400]
        assert list(converted) == expected
        assert meta["conversion_applied"] is True
        assert meta["conversion_factor"] == 0.001
    
    def test_megawatts_to_kw(self):
        """Should convert MW to kW correctly."""
        power_mw = pd.Series([0.05, 0.10, 0.20, 0.30, 0.40])
        converted, meta = convert_power(power_mw, "MW", "kW")
        
        expected = [50, 100, 200, 300, 400]
        assert list(converted) == expected
        assert meta["conversion_applied"] is True
        assert meta["conversion_factor"] == 1000.0
    
    def test_kw_to_kw_passthrough(self):
        """Should pass through kW without conversion."""
        power_kw = pd.Series([50, 100, 200, 300, 400])
        converted, meta = convert_power(power_kw, "kW", "kW")
        
        assert list(converted) == [50, 100, 200, 300, 400]
        assert meta["conversion_applied"] is False
    
    def test_zero_power(self):
        """Should handle zero power (chiller off)."""
        power_w = pd.Series([0, 50000, 100000])
        converted, meta = convert_power(power_w, "W", "kW")
        
        assert converted.iloc[0] == 0.0
        assert converted.iloc[1] == 50.0
        assert converted.iloc[2] == 100.0


class TestConvertAllUnits:
    """Test batch unit conversion for all BMD signals."""
    
    def test_all_units_no_conversion_needed(self):
        """Should handle data already in SI units."""
        df = pd.DataFrame({
            "CHWST": [6, 8, 10],
            "CHWRT": [12, 14, 16],
            "CDWRT": [20, 22, 24],
            "Flow": [0.05, 0.08, 0.10],
            "Power": [100, 150, 200]
        })
        
        mappings = {
            "CHWST": "CHWST",
            "CHWRT": "CHWRT",
            "CDWRT": "CDWRT",
            "FLOW": "Flow",
            "POWER": "Power"
        }
        
        detected_units = {
            "CHWST": ("C", 0.80),
            "CHWRT": ("C", 0.80),
            "CDWRT": ("C", 0.80),
            "FLOW": ("m3/s", 0.80),
            "POWER": ("kW", 0.80)
        }
        
        df_converted, conversions = convert_all_units(df, mappings, detected_units)
        
        # Should have new columns
        assert "chwst" in df_converted.columns
        assert "chwrt" in df_converted.columns
        assert "cdwrt" in df_converted.columns
        assert "flow_m3s" in df_converted.columns
        assert "power_kw" in df_converted.columns
        
        # Values should be unchanged
        assert list(df_converted["chwst"]) == [6, 8, 10]
        assert list(df_converted["chwrt"]) == [12, 14, 16]
        
        # All conversions should be "no_conversion_needed"
        for channel in ["CHWST", "CHWRT", "CDWRT", "FLOW", "POWER"]:
            assert conversions[channel]["status"] == "no_conversion_needed"
            assert conversions[channel]["conversion_applied"] is False
    
    def test_all_units_fahrenheit_gpm_watts(self):
        """Should convert °F, GPM, W to SI units."""
        df = pd.DataFrame({
            "Temp1": [43, 46, 50],
            "Temp2": [54, 57, 61],
            "Temp3": [68, 72, 75],
            "FlowRate": [793, 1268, 1585],
            "PowerDemand": [50000, 100000, 200000]
        })
        
        mappings = {
            "CHWST": "Temp1",
            "CHWRT": "Temp2",
            "CDWRT": "Temp3",
            "FLOW": "FlowRate",
            "POWER": "PowerDemand"
        }
        
        detected_units = {
            "CHWST": ("F", 0.80),
            "CHWRT": ("F", 0.80),
            "CDWRT": ("F", 0.80),
            "FLOW": ("GPM", 0.80),
            "POWER": ("W", 0.80)
        }
        
        df_converted, conversions = convert_all_units(df, mappings, detected_units)
        
        # Should have converted columns
        assert "chwst" in df_converted.columns
        assert "flow_m3s" in df_converted.columns
        assert "power_kw" in df_converted.columns
        
        # Temperature should be converted to °C
        assert 6.0 <= df_converted["chwst"].iloc[0] <= 6.5  # 43°F ≈ 6.1°C
        
        # Flow should be converted to m³/s
        assert 0.049 <= df_converted["flow_m3s"].iloc[0] <= 0.051  # 793 GPM ≈ 0.05 m³/s
        
        # Power should be converted to kW
        assert df_converted["power_kw"].iloc[0] == 50.0  # 50,000 W = 50 kW
        
        # All conversions should be "success"
        for channel in ["CHWST", "CHWRT", "CDWRT", "FLOW", "POWER"]:
            assert conversions[channel]["status"] == "success"
            assert conversions[channel]["conversion_applied"] is True
    
    def test_missing_column(self):
        """Should handle missing columns gracefully."""
        df = pd.DataFrame({
            "CHWST": [6, 8, 10],
            "CHWRT": [12, 14, 16]
        })
        
        mappings = {
            "CHWST": "CHWST",
            "CHWRT": "CHWRT",
            "CDWRT": "Missing",
            "FLOW": "Also_Missing",
            "POWER": "Not_Here"
        }
        
        detected_units = {
            "CHWST": ("C", 0.80),
            "CHWRT": ("C", 0.80),
            "CDWRT": (None, 0.0),
            "FLOW": (None, 0.0),
            "POWER": (None, 0.0)
        }
        
        df_converted, conversions = convert_all_units(df, mappings, detected_units)
        
        # Should handle CHWST and CHWRT
        assert conversions["CHWST"]["status"] == "no_conversion_needed"
        assert conversions["CHWRT"]["status"] == "no_conversion_needed"
        
        # Should report missing columns
        assert conversions["CDWRT"]["status"] == "missing"
        assert conversions["FLOW"]["status"] == "missing"
        assert conversions["POWER"]["status"] == "missing"
    
    def test_preserves_original_columns(self):
        """Should preserve all original columns."""
        df = pd.DataFrame({
            "Original_CHWST": [6, 8, 10],
            "Other_Column": ["a", "b", "c"]
        })
        
        mappings = {
            "CHWST": "Original_CHWST"
        }
        
        detected_units = {
            "CHWST": ("C", 0.80)
        }
        
        df_converted, conversions = convert_all_units(df, mappings, detected_units)
        
        # Original columns should still exist
        assert "Original_CHWST" in df_converted.columns
        assert "Other_Column" in df_converted.columns
        
        # New column should be added
        assert "chwst" in df_converted.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

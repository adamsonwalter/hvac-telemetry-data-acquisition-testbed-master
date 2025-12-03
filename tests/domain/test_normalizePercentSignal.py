#!/usr/bin/env python3
"""
Unit tests for normalize_percent_signal pure function.

These tests require NO MOCKS because the function is pure:
- No logging
- No file I/O
- No global state
- Just math and logic
"""

import pytest
import pandas as pd
import numpy as np

# Import pure function
from src.domain.decoder.normalizePercentSignal import normalize_percent_signal


class TestNormalizePercentSignal:
    """Test suite for normalize_percent_signal pure function."""
    
    def test_fraction_0_1_detection(self):
        """Test Rule 1: 0-1 fraction detection."""
        # Given: signal already in 0-1 range
        signal = pd.Series([0.0, 0.5, 1.0, 0.3, 0.8])
        
        # When: normalize
        normalized, metadata = normalize_percent_signal(signal, "test_fraction")
        
        # Then: detected correctly, no transformation
        assert metadata["detected_type"] == "fraction_0_1"
        assert metadata["confidence"] == "high"
        assert metadata["scaling_factor"] == 1.0
        assert normalized.max() == 1.0
        assert normalized.min() == 0.0
    
    def test_percentage_0_100_detection(self):
        """Test Rule 2: 0-100% detection."""
        # Given: signal in 0-100 range
        signal = pd.Series([0, 25, 50, 75, 100])
        
        # When: normalize
        normalized, metadata = normalize_percent_signal(signal, "test_percentage")
        
        # Then: detected and scaled to 0-1
        assert metadata["detected_type"] == "percentage_0_100"
        assert metadata["confidence"] == "high"
        assert metadata["scaling_factor"] == 100.0
        assert normalized.max() == 1.0
        assert normalized.min() == 0.0
        assert np.isclose(normalized.iloc[2], 0.5)  # 50% → 0.5
    
    def test_counts_10000_detection(self):
        """Test Rule 3: 0-10000 counts detection."""
        # Given: signal in 0-10000 range (0.01% resolution)
        signal = pd.Series([0, 2500, 5000, 7500, 10000])
        
        # When: normalize
        normalized, metadata = normalize_percent_signal(signal, "test_10k_counts")
        
        # Then: detected and scaled to 0-1
        assert metadata["detected_type"] == "counts_10000_0.01pct"
        assert metadata["confidence"] == "high"
        assert metadata["scaling_factor"] == 10000.0
        assert np.isclose(normalized.max(), 1.0)
        assert np.isclose(normalized.iloc[2], 0.5)  # 5000 → 0.5
    
    def test_counts_1000_detection(self):
        """Test Rule 4: 0-1000 counts detection."""
        # Given: signal in 0-1000 range (0.1% resolution)
        signal = pd.Series([0, 250, 500, 750, 1000])
        
        # When: normalize
        normalized, metadata = normalize_percent_signal(signal, "test_1k_counts")
        
        # Then: detected and scaled to 0-1
        assert metadata["detected_type"] == "counts_1000_0.1pct"
        assert metadata["confidence"] == "high"
        assert metadata["scaling_factor"] == 1000.0
        assert np.isclose(normalized.max(), 1.0)
        assert np.isclose(normalized.iloc[2], 0.5)  # 500 → 0.5
    
    def test_siemens_100000_detection(self):
        """Test Rule 5: 0-100000 Siemens detection."""
        # Given: signal in 0-100000 range (Siemens encoding)
        signal = pd.Series([0, 25000, 50000, 75000, 100000])
        
        # When: normalize
        normalized, metadata = normalize_percent_signal(signal, "test_siemens")
        
        # Then: detected and scaled to 0-1
        assert metadata["detected_type"] == "counts_100000_siemens"
        assert metadata["confidence"] == "high"
        assert metadata["scaling_factor"] == 100000.0
        assert np.isclose(normalized.max(), 1.0)
        assert np.isclose(normalized.iloc[2], 0.5)  # 50000 → 0.5
    
    def test_large_raw_counts_detection(self):
        """Test Rule 6: Large raw counts (e.g., pump VSD 0-50000)."""
        # Given: signal with large raw counts
        signal = pd.Series([0, 12500, 25000, 37500, 50000])
        
        # When: normalize
        normalized, metadata = normalize_percent_signal(signal, "test_large_counts")
        
        # Then: detected and scaled by p995
        assert metadata["detected_type"] == "raw_counts_large"
        assert metadata["confidence"] == "medium"  # Lower confidence for dynamic scaling
        assert normalized.max() <= 1.2  # Allow slight overshoot
        assert np.isclose(normalized.iloc[2], 0.5, atol=0.05)  # ~0.5 for midpoint
    
    def test_analog_unscaled_detection(self):
        """Test Rule 7: Unscaled analog (e.g., 0-4095, 0-27648)."""
        # Given: signal with analog counts
        signal = pd.Series([0, 1024, 2048, 3072, 4095])
        
        # When: normalize
        normalized, metadata = normalize_percent_signal(signal, "test_analog")
        
        # Then: detected and scaled by p995
        assert metadata["detected_type"] == "analog_unscaled"
        assert metadata["confidence"] == "medium"
        assert normalized.max() <= 1.2
    
    def test_empty_series(self):
        """Test handling of empty series."""
        # Given: empty series
        signal = pd.Series([], dtype=float)
        
        # When: normalize
        normalized, metadata = normalize_percent_signal(signal, "test_empty")
        
        # Then: gracefully handled
        assert metadata["detected_type"] == "no_data"
        assert len(normalized) == 0
    
    def test_series_with_nan(self):
        """Test handling of NaN values."""
        # Given: series with NaN
        signal = pd.Series([0, np.nan, 50, np.nan, 100])
        
        # When: normalize
        normalized, metadata = normalize_percent_signal(signal, "test_nan")
        
        # Then: NaN excluded from detection, preserved in output
        assert metadata["detected_type"] == "percentage_0_100"
        assert len(normalized) == 5  # Same length as input
        assert normalized.notna().sum() == 3  # 3 valid values
    
    def test_percentile_range_normalized(self):
        """Test Rule 8: Percentile range normalization (fallback)."""
        # Given: signal with unusual range (non-zero minimum)
        signal = pd.Series([500, 600, 700, 800, 900])
        
        # When: normalize
        normalized, metadata = normalize_percent_signal(signal, "test_percentile")
        
        # Then: uses percentile range
        assert metadata["detected_type"] == "percentile_range_normalized"
        assert metadata["confidence"] == "low"
        assert normalized.min() >= 0.0
        assert normalized.max() <= 1.2
    
    def test_metadata_completeness(self):
        """Test that metadata contains all required fields."""
        # Given: any valid signal
        signal = pd.Series([0, 50, 100])
        
        # When: normalize
        normalized, metadata = normalize_percent_signal(signal, "test_metadata")
        
        # Then: metadata has all fields
        required_fields = [
            "signal_name", "original_min", "original_max", "original_mean",
            "original_count", "detected_type", "scaling_factor", "confidence",
            "p995", "p005"
        ]
        for field in required_fields:
            assert field in metadata, f"Missing metadata field: {field}"
    
    def test_output_index_preservation(self):
        """Test that output series preserves original index."""
        # Given: series with custom index
        signal = pd.Series([0, 50, 100], index=[10, 20, 30])
        
        # When: normalize
        normalized, metadata = normalize_percent_signal(signal, "test_index")
        
        # Then: index preserved
        assert normalized.index.tolist() == [10, 20, 30]
    
    def test_deterministic_behavior(self):
        """Test that function is deterministic (pure)."""
        # Given: same input signal
        signal = pd.Series([0, 50, 100])
        
        # When: normalize twice
        result1, meta1 = normalize_percent_signal(signal, "test_deterministic")
        result2, meta2 = normalize_percent_signal(signal, "test_deterministic")
        
        # Then: identical results
        pd.testing.assert_series_equal(result1, result2)
        assert meta1 == meta2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Unit tests for Stage 1.5: buildSynchronizedDataFrame

Tests cover:
- Basic synchronization
- Missing signals
- Different value column names
- Empty timestamps
- Coverage metrics
- Quality validation
"""

import pytest
import pandas as pd
import numpy as np

from src.domain.htdam.stage15.buildSynchronizedDataFrame import (
    build_synchronized_dataframe,
    compute_coverage_per_signal,
    validate_synchronization_quality,
)


class TestBuildSynchronizedDataFrame:
    """Test suite for build_synchronized_dataframe() pure function."""
    
    def test_basic_synchronization(self):
        """Test basic synchronization with matching timestamps."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 200, 300], "value": [10.0, 11.0, 12.0]}),
            "CHWRT": pd.DataFrame({"timestamp": [100, 200, 300], "value": [15.0, 16.0, 17.0]}),
        }
        common_ts = pd.Series([100, 200, 300])
        
        df_sync = build_synchronized_dataframe(signal_dfs, common_ts)
        
        assert df_sync.shape == (3, 3)  # 3 rows, 3 cols (timestamp + 2 signals)
        assert list(df_sync.columns) == ["timestamp", "CHWST", "CHWRT"]
        assert list(df_sync["timestamp"]) == [100, 200, 300]
        assert list(df_sync["CHWST"]) == [10.0, 11.0, 12.0]
        assert list(df_sync["CHWRT"]) == [15.0, 16.0, 17.0]
    
    def test_partial_timestamp_overlap(self):
        """Test synchronization when signals have extra timestamps."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 200, 300, 400], "value": [10, 11, 12, 13]}),
            "CHWRT": pd.DataFrame({"timestamp": [100, 150, 200, 300], "value": [15, 16, 17, 18]}),
        }
        common_ts = pd.Series([100, 200, 300])  # Only these are common
        
        df_sync = build_synchronized_dataframe(signal_dfs, common_ts)
        
        assert df_sync.shape == (3, 3)
        assert list(df_sync["timestamp"]) == [100, 200, 300]
        assert list(df_sync["CHWST"]) == [10, 11, 12]
        assert list(df_sync["CHWRT"]) == [15, 17, 18]  # Skips 150 timestamp
    
    def test_empty_common_timestamps(self):
        """Test with no common timestamps (edge case)."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 200], "value": [10, 11]}),
            "CHWRT": pd.DataFrame({"timestamp": [300, 400], "value": [15, 16]}),
        }
        common_ts = pd.Series([])  # No overlap
        
        df_sync = build_synchronized_dataframe(signal_dfs, common_ts)
        
        assert df_sync.shape == (0, 3)  # Empty DataFrame
        assert list(df_sync.columns) == ["timestamp", "CHWST", "CHWRT"]
    
    def test_single_common_timestamp(self):
        """Test with only one common timestamp."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 200, 300], "value": [10, 11, 12]}),
            "CHWRT": pd.DataFrame({"timestamp": [100, 400, 500], "value": [15, 16, 17]}),
        }
        common_ts = pd.Series([100])
        
        df_sync = build_synchronized_dataframe(signal_dfs, common_ts)
        
        assert df_sync.shape == (1, 3)
        assert df_sync.iloc[0]["timestamp"] == 100
        assert df_sync.iloc[0]["CHWST"] == 10
        assert df_sync.iloc[0]["CHWRT"] == 15
    
    def test_alternative_value_column_names(self):
        """Test when value column is named after signal (not 'value')."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 200], "chwst": [10, 11]}),  # lowercase signal name
            "CHWRT": pd.DataFrame({"timestamp": [100, 200], "chwrt": [15, 16]}),
        }
        common_ts = pd.Series([100, 200])
        
        df_sync = build_synchronized_dataframe(signal_dfs, common_ts)
        
        assert df_sync.shape == (2, 3)
        assert list(df_sync["CHWST"]) == [10, 11]
        assert list(df_sync["CHWRT"]) == [15, 16]
    
    def test_mixed_value_column_names(self):
        """Test when signals use different value column conventions."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 200], "value": [10, 11]}),
            "CHWRT": pd.DataFrame({"timestamp": [100, 200], "chwrt": [15, 16]}),
            "POWER": pd.DataFrame({"timestamp": [100, 200], "reading": [50, 60]}),  # 3rd column
        }
        common_ts = pd.Series([100, 200])
        
        df_sync = build_synchronized_dataframe(signal_dfs, common_ts)
        
        assert df_sync.shape == (2, 4)
        assert list(df_sync["CHWST"]) == [10, 11]
        assert list(df_sync["CHWRT"]) == [15, 16]
        assert list(df_sync["POWER"]) == [50, 60]
    
    def test_missing_timestamp_column_raises_error(self):
        """Test that missing timestamp column raises ValueError."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"time": [100, 200], "value": [10, 11]}),  # Wrong col name
        }
        common_ts = pd.Series([100, 200])
        
        with pytest.raises(ValueError, match="Signal 'CHWST' missing timestamp column"):
            build_synchronized_dataframe(signal_dfs, common_ts)
    
    def test_missing_value_column_raises_error(self):
        """Test that ambiguous value column raises ValueError."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 200]}),  # No value column
        }
        common_ts = pd.Series([100, 200])
        
        with pytest.raises(ValueError, match="has no recognizable value column"):
            build_synchronized_dataframe(signal_dfs, common_ts)
    
    def test_sorted_by_timestamp(self):
        """Test that output is sorted by timestamp."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [300, 100, 200], "value": [12, 10, 11]}),
            "CHWRT": pd.DataFrame({"timestamp": [100, 300, 200], "value": [15, 17, 16]}),
        }
        common_ts = pd.Series([100, 200, 300])
        
        df_sync = build_synchronized_dataframe(signal_dfs, common_ts)
        
        assert list(df_sync["timestamp"]) == [100, 200, 300]  # Sorted
        assert list(df_sync["CHWST"]) == [10, 11, 12]
        assert list(df_sync["CHWRT"]) == [15, 16, 17]
    
    def test_no_nan_in_synchronized_output(self):
        """Test that synchronized output has no NaN for matched timestamps."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 200, 300, 400], "value": [10, 11, 12, 13]}),
            "CHWRT": pd.DataFrame({"timestamp": [100, 200, 300, 500], "value": [15, 16, 17, 18]}),
        }
        common_ts = pd.Series([100, 200, 300])
        
        df_sync = build_synchronized_dataframe(signal_dfs, common_ts)
        
        assert df_sync.isnull().sum().sum() == 0  # No NaN values
    
    def test_large_dataset_performance(self):
        """Test performance with large dataset (10K rows)."""
        import time
        
        timestamps = list(range(10000))
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": timestamps, "value": [float(i) for i in timestamps]}),
            "CHWRT": pd.DataFrame({"timestamp": timestamps, "value": [float(i+10) for i in timestamps]}),
            "POWER": pd.DataFrame({"timestamp": timestamps, "value": [float(i*2) for i in timestamps]}),
        }
        common_ts = pd.Series(timestamps)
        
        start = time.time()
        df_sync = build_synchronized_dataframe(signal_dfs, common_ts)
        elapsed = time.time() - start
        
        assert df_sync.shape == (10000, 4)
        assert elapsed < 0.5  # Should complete in under 0.5 seconds


class TestComputeCoveragePerSignal:
    """Test suite for compute_coverage_per_signal() pure function."""
    
    def test_perfect_coverage(self):
        """Test 100% coverage when no NaN values."""
        df_sync = pd.DataFrame({
            "timestamp": [100, 200, 300],
            "CHWST": [10.0, 11.0, 12.0],
            "CHWRT": [15.0, 16.0, 17.0],
        })
        
        coverage = compute_coverage_per_signal(df_sync)
        
        assert coverage["CHWST"]["coverage_pct"] == 100.0
        assert coverage["CHWRT"]["coverage_pct"] == 100.0
        assert coverage["CHWST"]["non_null_rows"] == 3
        assert coverage["CHWRT"]["non_null_rows"] == 3
    
    def test_partial_coverage_with_nan(self):
        """Test coverage calculation with NaN values."""
        df_sync = pd.DataFrame({
            "timestamp": [100, 200, 300, 400],
            "CHWST": [10.0, np.nan, 12.0, 13.0],  # 3/4 = 75%
            "CHWRT": [15.0, 16.0, np.nan, np.nan],  # 2/4 = 50%
        })
        
        coverage = compute_coverage_per_signal(df_sync)
        
        assert coverage["CHWST"]["coverage_pct"] == 75.0
        assert coverage["CHWST"]["null_rows"] == 1
        assert coverage["CHWRT"]["coverage_pct"] == 50.0
        assert coverage["CHWRT"]["null_rows"] == 2
    
    def test_zero_coverage(self):
        """Test coverage when signal is all NaN."""
        df_sync = pd.DataFrame({
            "timestamp": [100, 200, 300],
            "CHWST": [np.nan, np.nan, np.nan],
        })
        
        coverage = compute_coverage_per_signal(df_sync)
        
        assert coverage["CHWST"]["coverage_pct"] == 0.0
        assert coverage["CHWST"]["non_null_rows"] == 0
        assert coverage["CHWST"]["null_rows"] == 3
    
    def test_empty_dataframe(self):
        """Test coverage on empty DataFrame."""
        df_sync = pd.DataFrame({"timestamp": [], "CHWST": [], "CHWRT": []})
        
        coverage = compute_coverage_per_signal(df_sync)
        
        assert coverage["CHWST"]["coverage_pct"] == 0.0
        assert coverage["CHWRT"]["coverage_pct"] == 0.0


class TestValidateSynchronizationQuality:
    """Test suite for validate_synchronization_quality() pure function."""
    
    def test_valid_quality(self):
        """Test validation passes with good quality data."""
        df_sync = pd.DataFrame({
            "timestamp": list(range(200)),
            "CHWST": [10.0] * 200,  # 100% coverage
            "CHWRT": [15.0] * 200,  # 100% coverage
        })
        
        validation = validate_synchronization_quality(
            df_sync,
            min_rows=100,
            min_coverage_pct=80.0
        )
        
        assert validation["valid"] is True
        assert validation["n_rows"] == 200
        assert len(validation["violations"]) == 0
    
    def test_insufficient_rows_violation(self):
        """Test validation fails with too few rows."""
        df_sync = pd.DataFrame({
            "timestamp": list(range(50)),  # Only 50 rows
            "CHWST": [10.0] * 50,
        })
        
        validation = validate_synchronization_quality(
            df_sync,
            min_rows=100,
            min_coverage_pct=80.0
        )
        
        assert validation["valid"] is False
        assert len(validation["violations"]) == 1
        assert "Insufficient synchronized rows" in validation["violations"][0]
    
    def test_low_coverage_violation(self):
        """Test validation fails with low signal coverage."""
        df_sync = pd.DataFrame({
            "timestamp": list(range(200)),
            "CHWST": [10.0] * 140 + [np.nan] * 60,  # 70% coverage
        })
        
        validation = validate_synchronization_quality(
            df_sync,
            min_rows=100,
            min_coverage_pct=80.0
        )
        
        assert validation["valid"] is False
        assert len(validation["violations"]) == 1
        assert "coverage" in validation["violations"][0]
        assert "70" in validation["violations"][0]
    
    def test_warnings_for_borderline_quality(self):
        """Test warnings are generated for borderline quality."""
        df_sync = pd.DataFrame({
            "timestamp": list(range(150)),  # 150 rows (warning: should be >200)
            "CHWST": [10.0] * 145 + [np.nan] * 5,  # 96.7% coverage (warning: <95%)
        })
        
        validation = validate_synchronization_quality(
            df_sync,
            min_rows=100,
            min_coverage_pct=80.0
        )
        
        assert validation["valid"] is True  # Passes thresholds
        assert len(validation["warnings"]) >= 1  # But has warnings
    
    def test_multiple_violations(self):
        """Test multiple violations are reported."""
        df_sync = pd.DataFrame({
            "timestamp": list(range(50)),  # Too few rows
            "CHWST": [10.0] * 30 + [np.nan] * 20,  # 60% coverage (too low)
        })
        
        validation = validate_synchronization_quality(
            df_sync,
            min_rows=100,
            min_coverage_pct=80.0
        )
        
        assert validation["valid"] is False
        assert len(validation["violations"]) == 2  # Row count + coverage
    
    def test_custom_thresholds(self):
        """Test validation with custom thresholds."""
        df_sync = pd.DataFrame({
            "timestamp": list(range(250)),
            "CHWST": [10.0] * 200 + [np.nan] * 50,  # 80% coverage
        })
        
        # Strict thresholds
        validation_strict = validate_synchronization_quality(
            df_sync,
            min_rows=300,
            min_coverage_pct=85.0
        )
        assert validation_strict["valid"] is False
        
        # Lenient thresholds
        validation_lenient = validate_synchronization_quality(
            df_sync,
            min_rows=200,
            min_coverage_pct=75.0
        )
        assert validation_lenient["valid"] is True


# Future feature: interpolation and nearest-neighbor methods
@pytest.mark.skip(reason="Interpolation/nearest methods not yet implemented")
class TestAlternativeSyncMethods:
    """Test suite for future synchronization methods."""
    
    def test_nearest_timestamp_matching(self):
        """Test nearest-neighbor timestamp matching."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100.0, 200.0, 300.0], "value": [10, 11, 12]}),
            "CHWRT": pd.DataFrame({"timestamp": [100.5, 200.5, 300.5], "value": [15, 16, 17]}),
        }
        common_ts = pd.Series([100.0, 200.0, 300.0])
        
        df_sync = build_synchronized_dataframe(
            signal_dfs,
            common_ts,
            method="nearest",
            tolerance=1.0  # Within 1 second
        )
        
        assert df_sync.shape == (3, 3)
        # CHWRT values should be mapped to nearest timestamps
    
    def test_linear_interpolation(self):
        """Test linear interpolation for missing timestamps."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 200, 300], "value": [10, 11, 12]}),
            "CHWRT": pd.DataFrame({"timestamp": [100, 300], "value": [15, 17]}),  # Missing 200
        }
        common_ts = pd.Series([100, 200, 300])
        
        df_sync = build_synchronized_dataframe(
            signal_dfs,
            common_ts,
            method="interpolate"
        )
        
        # CHWRT at 200 should be interpolated: (15 + 17) / 2 = 16
        assert df_sync.loc[df_sync["timestamp"] == 200, "CHWRT"].values[0] == 16.0

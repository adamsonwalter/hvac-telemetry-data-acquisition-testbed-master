"""
Unit tests for Stage 1.5: detectCommonTimestamps

Tests cover:
- Exact timestamp matches
- No overlapping timestamps
- Partial overlap
- Empty signals
- Single row
- NaN timestamps
- Duplicate timestamps
- Tolerance matching (future)
"""

import pytest
import pandas as pd
import numpy as np

from src.domain.htdam.stage15.detectCommonTimestamps import (
    detect_common_timestamps,
    compute_synchronization_metrics,
)


class TestDetectCommonTimestamps:
    """Test suite for detect_common_timestamps() pure function."""
    
    def test_exact_match_full_overlap(self):
        """Test when all signals have identical timestamps."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 200, 300]}),
            "CHWRT": pd.DataFrame({"timestamp": [100, 200, 300]}),
            "POWER": pd.DataFrame({"timestamp": [100, 200, 300]}),
        }
        
        common = detect_common_timestamps(signal_dfs, required_signals=["CHWST", "CHWRT"])
        
        assert len(common) == 3
        assert list(common) == [100, 200, 300]
    
    def test_exact_match_partial_overlap(self):
        """Test when signals have partial timestamp overlap."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 200, 300, 400]}),
            "CHWRT": pd.DataFrame({"timestamp": [100, 200, 500]}),
            "POWER": pd.DataFrame({"timestamp": [50, 100, 150, 200, 250]}),
        }
        
        common = detect_common_timestamps(signal_dfs, required_signals=["CHWST", "CHWRT"])
        
        assert len(common) == 2
        assert list(common) == [100, 200]
    
    def test_no_overlap(self):
        """Test when signals have no common timestamps."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 200, 300]}),
            "CHWRT": pd.DataFrame({"timestamp": [400, 500, 600]}),
        }
        
        common = detect_common_timestamps(signal_dfs, required_signals=["CHWST", "CHWRT"])
        
        assert len(common) == 0
    
    def test_single_timestamp_match(self):
        """Test when only one timestamp matches."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 200, 300]}),
            "CHWRT": pd.DataFrame({"timestamp": [50, 100, 150]}),
        }
        
        common = detect_common_timestamps(signal_dfs, required_signals=["CHWST", "CHWRT"])
        
        assert len(common) == 1
        assert list(common) == [100]
    
    def test_empty_signal(self):
        """Test when one signal has no timestamps."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 200, 300]}),
            "CHWRT": pd.DataFrame({"timestamp": []}),
        }
        
        common = detect_common_timestamps(signal_dfs, required_signals=["CHWST", "CHWRT"])
        
        assert len(common) == 0
    
    def test_all_empty_signals(self):
        """Test when all signals are empty."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": []}),
            "CHWRT": pd.DataFrame({"timestamp": []}),
        }
        
        common = detect_common_timestamps(signal_dfs, required_signals=["CHWST", "CHWRT"])
        
        assert len(common) == 0
    
    def test_nan_timestamps_ignored(self):
        """Test that NaN timestamps are properly filtered out."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, np.nan, 200, 300]}),
            "CHWRT": pd.DataFrame({"timestamp": [100, 200, np.nan, 300]}),
        }
        
        common = detect_common_timestamps(signal_dfs, required_signals=["CHWST", "CHWRT"])
        
        assert len(common) == 3
        assert list(common) == [100, 200, 300]
    
    def test_duplicate_timestamps_deduplicated(self):
        """Test that duplicate timestamps are deduplicated."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 100, 200, 200, 300]}),
            "CHWRT": pd.DataFrame({"timestamp": [100, 200, 200, 300, 300]}),
        }
        
        common = detect_common_timestamps(signal_dfs, required_signals=["CHWST", "CHWRT"])
        
        assert len(common) == 3
        assert list(common) == [100, 200, 300]
    
    def test_only_required_signals_checked(self):
        """Test that only required signals are checked for intersection."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 200, 300]}),
            "CHWRT": pd.DataFrame({"timestamp": [100, 200, 300]}),
            "POWER": pd.DataFrame({"timestamp": [999]}),  # No overlap
        }
        
        # Only require CHWST and CHWRT (POWER ignored)
        common = detect_common_timestamps(signal_dfs, required_signals=["CHWST", "CHWRT"])
        
        assert len(common) == 3
        assert list(common) == [100, 200, 300]
    
    def test_missing_required_signal_raises_error(self):
        """Test that missing required signal raises ValueError."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 200, 300]}),
        }
        
        with pytest.raises(ValueError, match="Required signal 'CHWRT' not found"):
            detect_common_timestamps(signal_dfs, required_signals=["CHWST", "CHWRT"])
    
    def test_missing_timestamp_column_raises_error(self):
        """Test that missing timestamp column raises ValueError."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"time": [100, 200, 300]}),  # Wrong column name
            "CHWRT": pd.DataFrame({"timestamp": [100, 200, 300]}),
        }
        
        with pytest.raises(ValueError, match="Signal 'CHWST' missing timestamp column"):
            detect_common_timestamps(signal_dfs, required_signals=["CHWST", "CHWRT"])
    
    def test_empty_required_signals_raises_error(self):
        """Test that empty required_signals list raises ValueError."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 200, 300]}),
        }
        
        with pytest.raises(ValueError, match="required_signals must contain at least one"):
            detect_common_timestamps(signal_dfs, required_signals=[])
    
    def test_sorted_output(self):
        """Test that output timestamps are sorted."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [300, 100, 200]}),  # Unsorted
            "CHWRT": pd.DataFrame({"timestamp": [200, 300, 100]}),  # Unsorted
        }
        
        common = detect_common_timestamps(signal_dfs, required_signals=["CHWST", "CHWRT"])
        
        assert len(common) == 3
        assert list(common) == [100, 200, 300]  # Should be sorted
    
    def test_large_dataset_performance(self):
        """Test performance with large datasets (10K timestamps)."""
        import time
        
        ts1 = list(range(0, 20000, 2))  # Even numbers: 0, 2, 4, ..., 19998
        ts2 = list(range(1000, 15000, 2))  # Even numbers: 1000, 1002, ..., 14998
        
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": ts1}),
            "CHWRT": pd.DataFrame({"timestamp": ts2}),
        }
        
        start = time.time()
        common = detect_common_timestamps(signal_dfs, required_signals=["CHWST", "CHWRT"])
        elapsed = time.time() - start
        
        # Should find 1000-14998 evens: (14998-1000)/2 + 1 = 7000
        assert len(common) == 7000
        assert elapsed < 1.0  # Should complete in under 1 second


class TestComputeSynchronizationMetrics:
    """Test suite for compute_synchronization_metrics() pure function."""
    
    def test_perfect_sync_quality(self):
        """Test metrics when all timestamps match (100% coverage)."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 200, 300]}),
            "CHWRT": pd.DataFrame({"timestamp": [100, 200, 300]}),
        }
        common_timestamps = pd.Series([100, 200, 300])
        
        metrics = compute_synchronization_metrics(signal_dfs, common_timestamps)
        
        assert metrics["n_common_timestamps"] == 3
        assert metrics["per_signal_coverage"]["CHWST"] == 100.0
        assert metrics["per_signal_coverage"]["CHWRT"] == 100.0
        assert metrics["overall_data_retention"] == 100.0
        assert metrics["sync_quality"] == "excellent"
    
    def test_partial_sync_quality(self):
        """Test metrics with partial timestamp overlap."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 200, 300, 400]}),  # 4 samples
            "CHWRT": pd.DataFrame({"timestamp": [100, 200, 500]}),  # 3 samples
        }
        common_timestamps = pd.Series([100, 200])  # 2 common
        
        metrics = compute_synchronization_metrics(signal_dfs, common_timestamps)
        
        assert metrics["n_common_timestamps"] == 2
        assert metrics["per_signal_coverage"]["CHWST"] == 50.0  # 2/4
        assert metrics["per_signal_coverage"]["CHWRT"] == pytest.approx(66.67, rel=0.1)  # 2/3
        # Overall: (2 common × 2 signals) / (4 + 3 total) = 4/7 ≈ 57.14%
        assert metrics["overall_data_retention"] == pytest.approx(57.14, rel=0.1)
        assert metrics["sync_quality"] == "fair"
    
    def test_no_common_timestamps(self):
        """Test metrics when no timestamps match."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 200, 300]}),
            "CHWRT": pd.DataFrame({"timestamp": [400, 500, 600]}),
        }
        common_timestamps = pd.Series([])
        
        metrics = compute_synchronization_metrics(signal_dfs, common_timestamps)
        
        assert metrics["n_common_timestamps"] == 0
        assert metrics["per_signal_coverage"]["CHWST"] == 0.0
        assert metrics["per_signal_coverage"]["CHWRT"] == 0.0
        assert metrics["overall_data_retention"] == 0.0
        assert metrics["sync_quality"] == "poor"
    
    def test_empty_signal_coverage(self):
        """Test coverage calculation with empty signal."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, 200, 300]}),
            "CHWRT": pd.DataFrame({"timestamp": []}),
        }
        common_timestamps = pd.Series([])
        
        metrics = compute_synchronization_metrics(signal_dfs, common_timestamps)
        
        assert metrics["per_signal_coverage"]["CHWST"] == 0.0
        assert metrics["per_signal_coverage"]["CHWRT"] == 0.0
    
    def test_sync_quality_thresholds(self):
        """Test sync quality rating thresholds."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": list(range(100))}),
            "CHWRT": pd.DataFrame({"timestamp": list(range(100))}),
        }
        
        # Excellent: >=80%
        common = pd.Series(list(range(80)))
        metrics = compute_synchronization_metrics(signal_dfs, common)
        assert metrics["sync_quality"] == "excellent"
        
        # Good: >=60%
        common = pd.Series(list(range(60)))
        metrics = compute_synchronization_metrics(signal_dfs, common)
        assert metrics["sync_quality"] == "good"
        
        # Fair: >=40%
        common = pd.Series(list(range(40)))
        metrics = compute_synchronization_metrics(signal_dfs, common)
        assert metrics["sync_quality"] == "fair"
        
        # Poor: <40%
        common = pd.Series(list(range(30)))
        metrics = compute_synchronization_metrics(signal_dfs, common)
        assert metrics["sync_quality"] == "poor"
    
    def test_nan_timestamps_not_counted(self):
        """Test that NaN timestamps don't affect coverage calculation."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100, np.nan, 200, 300]}),  # 3 valid
            "CHWRT": pd.DataFrame({"timestamp": [100, 200, 300, np.nan]}),  # 3 valid
        }
        common_timestamps = pd.Series([100, 200, 300])
        
        metrics = compute_synchronization_metrics(signal_dfs, common_timestamps)
        
        # Both signals have 3 valid timestamps, all 3 are common
        assert metrics["per_signal_coverage"]["CHWST"] == 100.0
        assert metrics["per_signal_coverage"]["CHWRT"] == 100.0


# Edge case tests for tolerance matching (future feature)
@pytest.mark.skip(reason="Tolerance matching not yet implemented")
class TestToleranceMatching:
    """Test suite for tolerance-based timestamp matching (future)."""
    
    def test_tolerance_within_seconds(self):
        """Test matching timestamps within tolerance."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100.0, 200.5, 300.0]}),
            "CHWRT": pd.DataFrame({"timestamp": [100.1, 200.4, 300.2]}),
        }
        
        common = detect_common_timestamps(
            signal_dfs,
            required_signals=["CHWST", "CHWRT"],
            tolerance_seconds=0.3
        )
        
        assert len(common) == 3  # All should match within 0.3s
    
    def test_tolerance_outside_range(self):
        """Test timestamps outside tolerance don't match."""
        signal_dfs = {
            "CHWST": pd.DataFrame({"timestamp": [100.0, 200.0]}),
            "CHWRT": pd.DataFrame({"timestamp": [100.6, 200.6]}),
        }
        
        common = detect_common_timestamps(
            signal_dfs,
            required_signals=["CHWST", "CHWRT"],
            tolerance_seconds=0.5
        )
        
        assert len(common) == 0  # 0.6s > 0.5s tolerance

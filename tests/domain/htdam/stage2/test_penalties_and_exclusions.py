"""
Unit tests for computeGapPenalties and detectExclusionWindowCandidates.
Tests penalty calculation and exclusion window detection logic.
"""

import pytest
from datetime import datetime, timedelta
from src.domain.htdam.stage2.computeGapPenalties import compute_gap_penalties
from src.domain.htdam.stage2.detectExclusionWindowCandidates import detect_exclusion_window_candidates


class TestComputeGapPenalties:
    """Test penalty calculation from gap semantics."""
    
    def test_no_gaps_zero_penalty(self):
        """No gaps detected - zero penalty."""
        # Given: no gap entries
        gap_semantics = []
        
        # When: compute penalties
        result = compute_gap_penalties(gap_semantics)
        
        # Then: zero penalty
        assert result["total_penalty"] == 0.0
        assert result["gap_count"] == 0
    
    def test_all_cov_constant_zero_penalty(self):
        """All COV_CONSTANT gaps - zero penalty."""
        # Given: only constant gaps
        gap_semantics = [
            {"gap_semantic": "COV_CONSTANT"},
            {"gap_semantic": "COV_CONSTANT"},
            {"gap_semantic": "COV_CONSTANT"},
        ]
        
        # When: compute penalties
        result = compute_gap_penalties(gap_semantics)
        
        # Then: zero penalty
        assert result["total_penalty"] == 0.0
        assert result["gap_count"] == 3
    
    def test_single_cov_minor_penalty(self):
        """One COV_MINOR gap - -0.02 penalty."""
        # Given: one minor gap
        gap_semantics = [{"gap_semantic": "COV_MINOR"}]
        
        # When: compute penalties
        result = compute_gap_penalties(gap_semantics)
        
        # Then: -0.02 penalty
        assert result["total_penalty"] == -0.02
        assert result["gap_count"] == 1
    
    def test_single_sensor_anomaly_penalty(self):
        """One SENSOR_ANOMALY - -0.05 penalty."""
        # Given: one anomaly
        gap_semantics = [{"gap_semantic": "SENSOR_ANOMALY"}]
        
        # When: compute penalties
        result = compute_gap_penalties(gap_semantics)
        
        # Then: -0.05 penalty
        assert result["total_penalty"] == -0.05
    
    def test_mixed_gap_types_cumulative(self):
        """Mixed gap types - penalties accumulate."""
        # Given: mix of gap types
        gap_semantics = [
            {"gap_semantic": "COV_CONSTANT"},    # 0.0
            {"gap_semantic": "COV_MINOR"},       # -0.02
            {"gap_semantic": "COV_CONSTANT"},    # 0.0
            {"gap_semantic": "SENSOR_ANOMALY"},  # -0.05
            {"gap_semantic": "COV_MINOR"},       # -0.02
        ]
        
        # When: compute penalties
        result = compute_gap_penalties(gap_semantics)
        
        # Then: sum of penalties
        assert result["total_penalty"] == pytest.approx(-0.09, abs=1e-6)
        assert result["gap_count"] == 5
    
    def test_normal_intervals_ignored(self):
        """N/A semantics (normal intervals) ignored."""
        # Given: mix with N/A entries
        gap_semantics = [
            {"gap_semantic": "N/A"},
            {"gap_semantic": "COV_MINOR"},
            {"gap_semantic": "N/A"},
        ]
        
        # When: compute penalties
        result = compute_gap_penalties(gap_semantics)
        
        # Then: only actual gaps counted
        assert result["total_penalty"] == -0.02
        assert result["gap_count"] == 3


class TestDetectExclusionWindowCandidates:
    """Test exclusion window detection across signals."""
    
    def test_no_gaps_no_exclusions(self):
        """No gaps in any signal - no exclusions."""
        # Given: no gaps
        per_signal_gaps = {
            "CHWST": [],
            "CHWRT": [],
            "CDWRT": [],
            "FLOW": [],
            "POWER": [],
        }
        
        # When: detect exclusions
        result = detect_exclusion_window_candidates(per_signal_gaps)
        
        # Then: no exclusions
        assert len(result["exclusion_windows"]) == 0
    
    def test_single_major_gap_no_exclusion(self):
        """Major gap in only one signal - no exclusion (need ≥2 streams)."""
        # Given: major gap in CHWST only
        start = datetime(2024, 1, 1, 0, 0, 0)
        per_signal_gaps = {
            "CHWST": [
                {
                    "gap_class": "MAJOR_GAP",
                    "gap_start": start,
                    "gap_end": start + timedelta(hours=10),
                    "duration_hours": 10.0,
                }
            ],
            "CHWRT": [],
            "CDWRT": [],
            "FLOW": [],
            "POWER": [],
        }
        
        # When: detect exclusions
        result = detect_exclusion_window_candidates(per_signal_gaps)
        
        # Then: no exclusion (only 1 stream)
        assert len(result["exclusion_windows"]) == 0
    
    def test_two_overlapping_major_gaps_creates_exclusion(self):
        """Two overlapping MAJOR_GAPs ≥8 hours - creates exclusion."""
        # Given: overlapping 10-hour gaps in 2 signals
        start = datetime(2024, 1, 1, 0, 0, 0)
        per_signal_gaps = {
            "CHWST": [
                {
                    "gap_class": "MAJOR_GAP",
                    "gap_start": start,
                    "gap_end": start + timedelta(hours=10),
                    "duration_hours": 10.0,
                }
            ],
            "CHWRT": [
                {
                    "gap_class": "MAJOR_GAP",
                    "gap_start": start + timedelta(hours=1),
                    "gap_end": start + timedelta(hours=11),
                    "duration_hours": 10.0,
                }
            ],
            "CDWRT": [],
            "FLOW": [],
            "POWER": [],
        }
        
        # When: detect exclusions
        result = detect_exclusion_window_candidates(per_signal_gaps)
        
        # Then: one exclusion window
        assert len(result["exclusion_windows"]) == 1
        assert result["exclusion_windows"][0]["affected_streams_count"] == 2
    
    def test_non_overlapping_major_gaps_no_exclusion(self):
        """Major gaps in 2 signals but no overlap - no exclusion."""
        # Given: non-overlapping gaps
        start = datetime(2024, 1, 1, 0, 0, 0)
        per_signal_gaps = {
            "CHWST": [
                {
                    "gap_class": "MAJOR_GAP",
                    "gap_start": start,
                    "gap_end": start + timedelta(hours=10),
                    "duration_hours": 10.0,
                }
            ],
            "CHWRT": [
                {
                    "gap_class": "MAJOR_GAP",
                    "gap_start": start + timedelta(hours=12),  # No overlap
                    "gap_end": start + timedelta(hours=22),
                    "duration_hours": 10.0,
                }
            ],
            "CDWRT": [],
            "FLOW": [],
            "POWER": [],
        }
        
        # When: detect exclusions
        result = detect_exclusion_window_candidates(per_signal_gaps)
        
        # Then: no exclusion (no overlap)
        assert len(result["exclusion_windows"]) == 0
    
    def test_major_gap_too_short_no_exclusion(self):
        """Overlapping gaps but <8 hours - no exclusion."""
        # Given: overlapping 5-hour gaps
        start = datetime(2024, 1, 1, 0, 0, 0)
        per_signal_gaps = {
            "CHWST": [
                {
                    "gap_class": "MAJOR_GAP",
                    "gap_start": start,
                    "gap_end": start + timedelta(hours=5),
                    "duration_hours": 5.0,
                }
            ],
            "CHWRT": [
                {
                    "gap_class": "MAJOR_GAP",
                    "gap_start": start,
                    "gap_end": start + timedelta(hours=5),
                    "duration_hours": 5.0,
                }
            ],
            "CDWRT": [],
            "FLOW": [],
            "POWER": [],
        }
        
        # When: detect exclusions
        result = detect_exclusion_window_candidates(per_signal_gaps)
        
        # Then: no exclusion (too short)
        assert len(result["exclusion_windows"]) == 0
    
    def test_three_overlapping_major_gaps(self):
        """Three signals with overlapping MAJOR_GAPs."""
        # Given: 3 overlapping gaps
        start = datetime(2024, 1, 1, 0, 0, 0)
        per_signal_gaps = {
            "CHWST": [
                {
                    "gap_class": "MAJOR_GAP",
                    "gap_start": start,
                    "gap_end": start + timedelta(hours=12),
                    "duration_hours": 12.0,
                }
            ],
            "CHWRT": [
                {
                    "gap_class": "MAJOR_GAP",
                    "gap_start": start + timedelta(hours=2),
                    "gap_end": start + timedelta(hours=14),
                    "duration_hours": 12.0,
                }
            ],
            "CDWRT": [
                {
                    "gap_class": "MAJOR_GAP",
                    "gap_start": start + timedelta(hours=1),
                    "gap_end": start + timedelta(hours=13),
                    "duration_hours": 12.0,
                }
            ],
            "FLOW": [],
            "POWER": [],
        }
        
        # When: detect exclusions
        result = detect_exclusion_window_candidates(per_signal_gaps)
        
        # Then: one exclusion with 3 streams
        assert len(result["exclusion_windows"]) == 1
        assert result["exclusion_windows"][0]["affected_streams_count"] == 3
    
    def test_minor_gaps_ignored(self):
        """MINOR_GAPs do not trigger exclusions."""
        # Given: overlapping minor gaps
        start = datetime(2024, 1, 1, 0, 0, 0)
        per_signal_gaps = {
            "CHWST": [
                {
                    "gap_class": "MINOR_GAP",
                    "gap_start": start,
                    "gap_end": start + timedelta(hours=10),
                    "duration_hours": 10.0,
                }
            ],
            "CHWRT": [
                {
                    "gap_class": "MINOR_GAP",
                    "gap_start": start,
                    "gap_end": start + timedelta(hours=10),
                    "duration_hours": 10.0,
                }
            ],
            "CDWRT": [],
            "FLOW": [],
            "POWER": [],
        }
        
        # When: detect exclusions
        result = detect_exclusion_window_candidates(per_signal_gaps)
        
        # Then: no exclusion (only MAJOR_GAPs count)
        assert len(result["exclusion_windows"]) == 0

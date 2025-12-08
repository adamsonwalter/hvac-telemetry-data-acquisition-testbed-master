"""
Unit tests for buildStage2AnnotatedDataFrame and buildStage2Metrics.
Tests DataFrame annotation and metrics JSON generation.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.domain.htdam.stage2.buildStage2AnnotatedDataFrame import build_stage2_annotated_dataframe
from src.domain.htdam.stage2.buildStage2Metrics import build_stage2_metrics


class TestBuildStage2AnnotatedDataFrame:
    """Test gap-annotated DataFrame construction."""
    
    def test_basic_annotation_structure(self):
        """Verify all expected columns are added."""
        # Given: simple signal DataFrame
        timestamps = pd.date_range(start='2024-01-01', periods=5, freq='15min')
        df = pd.DataFrame({
            'timestamp': timestamps,
            'value': [70.0, 70.5, 71.0, 70.0, 70.5],
        })
        
        # Gap analysis results
        gap_results = [
            {
                "gap_before_duration_s": 900.0,
                "gap_before_class": "NORMAL",
                "gap_before_semantic": "N/A",
                "gap_before_confidence": 0.0,
                "value_changed_relative_pct": 0.0,
                "exclusion_window_id": None,
            }
            for _ in range(len(df))
        ]
        
        # When: build annotated DataFrame
        result = build_stage2_annotated_dataframe(df, gap_results)
        
        # Then: should have all 6 new columns
        expected_cols = [
            'gap_before_duration_s',
            'gap_before_class',
            'gap_before_semantic',
            'gap_before_confidence',
            'value_changed_relative_pct',
            'exclusion_window_id'
        ]
        for col in expected_cols:
            assert col in result.columns
    
    def test_preserves_original_columns(self):
        """Original DataFrame columns preserved."""
        # Given: DataFrame with existing columns
        df = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=3, freq='15min'),
            'value': [70.0, 71.0, 72.0],
            'original_column': ['a', 'b', 'c'],
        })
        
        gap_results = [
            {"gap_before_duration_s": 900.0, "gap_before_class": "NORMAL", 
             "gap_before_semantic": "N/A", "gap_before_confidence": 0.0, 
             "value_changed_relative_pct": 0.0, "exclusion_window_id": None}
            for _ in range(len(df))
        ]
        
        # When: build annotated DataFrame
        result = build_stage2_annotated_dataframe(df, gap_results)
        
        # Then: original columns preserved
        assert 'timestamp' in result.columns
        assert 'value' in result.columns
        assert 'original_column' in result.columns
        pd.testing.assert_series_equal(result['original_column'], df['original_column'])
    
    def test_gap_metadata_correctly_aligned(self):
        """Gap metadata aligns with DataFrame rows."""
        # Given: 3-row DataFrame
        df = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=3, freq='15min'),
            'value': [70.0, 71.0, 72.0],
        })
        
        gap_results = [
            {"gap_before_duration_s": 0.0, "gap_before_class": "NORMAL", 
             "gap_before_semantic": "N/A", "gap_before_confidence": 0.0, 
             "value_changed_relative_pct": 0.0, "exclusion_window_id": None},
            {"gap_before_duration_s": 900.0, "gap_before_class": "NORMAL", 
             "gap_before_semantic": "COV_CONSTANT", "gap_before_confidence": 0.0, 
             "value_changed_relative_pct": 1.4, "exclusion_window_id": None},
            {"gap_before_duration_s": 7200.0, "gap_before_class": "MAJOR_GAP", 
             "gap_before_semantic": "SENSOR_ANOMALY", "gap_before_confidence": -0.05, 
             "value_changed_relative_pct": 5.3, "exclusion_window_id": "EX001"},
        ]
        
        # When: build annotated DataFrame
        result = build_stage2_annotated_dataframe(df, gap_results)
        
        # Then: metadata correctly aligned
        assert result.iloc[0]['gap_before_duration_s'] == 0.0
        assert result.iloc[1]['gap_before_duration_s'] == 900.0
        assert result.iloc[2]['gap_before_duration_s'] == 7200.0
        assert result.iloc[2]['gap_before_semantic'] == "SENSOR_ANOMALY"
        assert result.iloc[2]['exclusion_window_id'] == "EX001"
    
    def test_empty_dataframe(self):
        """Handle empty DataFrame."""
        # Given: empty DataFrame
        df = pd.DataFrame(columns=['timestamp', 'value'])
        gap_results = []
        
        # When: build annotated DataFrame
        result = build_stage2_annotated_dataframe(df, gap_results)
        
        # Then: should have columns but no rows
        assert len(result) == 0
        assert 'gap_before_duration_s' in result.columns


class TestBuildStage2Metrics:
    """Test Stage 2 metrics JSON generation."""
    
    def test_basic_metrics_structure(self):
        """Verify all required fields in metrics JSON."""
        # Given: minimal per-signal summaries
        per_stream_summary = {
            "CHWST": {
                "total_gaps": 2,
                "major_gaps": 1,
                "minor_gaps": 1,
                "cov_constant_count": 1,
                "sensor_anomaly_count": 0,
                "penalty": -0.02,
            }
        }
        
        exclusion_windows = []
        aggregate_penalty = -0.02
        warnings = []
        
        # When: build metrics
        result = build_stage2_metrics(
            per_stream_summary,
            exclusion_windows,
            aggregate_penalty,
            warnings
        )
        
        # Then: should have all required fields
        assert "per_stream_summary" in result
        assert "exclusion_windows" in result
        assert "aggregate_penalty" in result
        assert "stage2_confidence" in result
        assert "warnings" in result
        assert "human_approval_required" in result
    
    def test_confidence_calculation(self):
        """Stage 2 confidence = 1.0 + aggregate_penalty."""
        # Given: aggregate penalty of -0.07
        result = build_stage2_metrics(
            per_stream_summary={},
            exclusion_windows=[],
            aggregate_penalty=-0.07,
            warnings=[]
        )
        
        # Then: confidence = 1.0 - 0.07 = 0.93
        assert result["stage2_confidence"] == pytest.approx(0.93, abs=1e-6)
    
    def test_human_approval_required_with_exclusions(self):
        """Human approval required when exclusion windows exist."""
        # Given: exclusion windows present
        exclusion_windows = [
            {
                "window_id": "EX001",
                "start": "2024-01-01T00:00:00",
                "end": "2024-01-01T10:00:00",
                "affected_streams_count": 2,
            }
        ]
        
        # When: build metrics
        result = build_stage2_metrics(
            per_stream_summary={},
            exclusion_windows=exclusion_windows,
            aggregate_penalty=0.0,
            warnings=[]
        )
        
        # Then: human approval required
        assert result["human_approval_required"] is True
    
    def test_human_approval_not_required_without_exclusions(self):
        """No human approval needed when no exclusion windows."""
        # Given: no exclusion windows
        result = build_stage2_metrics(
            per_stream_summary={},
            exclusion_windows=[],
            aggregate_penalty=0.0,
            warnings=[]
        )
        
        # Then: human approval not required
        assert result["human_approval_required"] is False
    
    def test_per_stream_summary_preserved(self):
        """Per-stream summary data correctly preserved."""
        # Given: detailed per-stream data
        per_stream_summary = {
            "CHWST": {
                "total_gaps": 5,
                "major_gaps": 2,
                "minor_gaps": 3,
                "cov_constant_count": 3,
                "cov_minor_count": 1,
                "sensor_anomaly_count": 1,
                "penalty": -0.07,
            },
            "CHWRT": {
                "total_gaps": 3,
                "major_gaps": 1,
                "minor_gaps": 2,
                "cov_constant_count": 2,
                "cov_minor_count": 1,
                "sensor_anomaly_count": 0,
                "penalty": -0.02,
            }
        }
        
        # When: build metrics
        result = build_stage2_metrics(
            per_stream_summary=per_stream_summary,
            exclusion_windows=[],
            aggregate_penalty=-0.09,
            warnings=[]
        )
        
        # Then: summary preserved
        assert result["per_stream_summary"]["CHWST"]["total_gaps"] == 5
        assert result["per_stream_summary"]["CHWRT"]["penalty"] == -0.02
    
    def test_warnings_preserved(self):
        """Warnings list correctly preserved."""
        # Given: warnings list
        warnings = [
            "CDWRT has 3 SENSOR_ANOMALY gaps",
            "FLOW has 15-hour exclusion window"
        ]
        
        # When: build metrics
        result = build_stage2_metrics(
            per_stream_summary={},
            exclusion_windows=[],
            aggregate_penalty=0.0,
            warnings=warnings
        )
        
        # Then: warnings preserved
        assert len(result["warnings"]) == 2
        assert result["warnings"][0] == "CDWRT has 3 SENSOR_ANOMALY gaps"
    
    def test_zero_penalty_full_confidence(self):
        """Zero penalty results in 1.0 confidence."""
        # Given: no gaps, zero penalty
        result = build_stage2_metrics(
            per_stream_summary={},
            exclusion_windows=[],
            aggregate_penalty=0.0,
            warnings=[]
        )
        
        # Then: full confidence
        assert result["stage2_confidence"] == 1.0
    
    def test_large_penalty_low_confidence(self):
        """Large penalty results in low confidence."""
        # Given: large aggregate penalty
        result = build_stage2_metrics(
            per_stream_summary={},
            exclusion_windows=[],
            aggregate_penalty=-0.25,  # 25% confidence reduction
            warnings=[]
        )
        
        # Then: low confidence
        assert result["stage2_confidence"] == pytest.approx(0.75, abs=1e-6)

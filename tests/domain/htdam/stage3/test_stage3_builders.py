"""
Unit tests for Stage 3 output builder functions:
- buildStage3AnnotatedDataFrame.py
- buildStage3Metrics.py
"""

import pytest
import pandas as pd
import numpy as np
from src.domain.htdam.stage3.buildStage3AnnotatedDataFrame import build_stage3_annotated_dataframe
from src.domain.htdam.stage3.buildStage3Metrics import build_stage3_metrics


class TestBuildStage3AnnotatedDataFrame:
    """Test suite for build_stage3_annotated_dataframe()"""

    def test_minimal_synchronized_dataframe(self):
        """Test building minimal synchronized DataFrame"""
        grid = pd.Series([
            pd.Timestamp("2024-01-01 00:00:00"),
            pd.Timestamp("2024-01-01 00:15:00"),
        ])
        
        aligned_streams = {
            "CHWST": pd.DataFrame({
                "values": [10.0, 11.0],
                "quality": ["EXACT", "EXACT"],
                "jitter": [0, 0]
            }),
            "CHWRT": pd.DataFrame({
                "values": [20.0, 21.0],
                "quality": ["EXACT", "EXACT"],
                "jitter": [0, 0]
            }),
            "CDWRT": pd.DataFrame({
                "values": [30.0, 31.0],
                "quality": ["EXACT", "EXACT"],
                "jitter": [0, 0]
            }),
            "FLOW": pd.DataFrame({
                "values": [100.0, 110.0],
                "quality": ["EXACT", "EXACT"],
                "jitter": [0, 0]
            }),
            "POWER": pd.DataFrame({
                "values": [500.0, 510.0],
                "quality": ["EXACT", "EXACT"],
                "jitter": [0, 0]
            }),
        }
        
        exclusion_windows = []
        stage2_gaps = {
            "CHWST": pd.Series(["VALID", "VALID"]),
            "CHWRT": pd.Series(["VALID", "VALID"]),
            "CDWRT": pd.Series(["VALID", "VALID"]),
            "FLOW": pd.Series(["VALID", "VALID"]),
            "POWER": pd.Series(["VALID", "VALID"]),
        }
        
        result = build_stage3_annotated_dataframe(
            grid, aligned_streams, exclusion_windows, stage2_gaps
        )
        
        # Check basic structure
        assert len(result) == 2
        assert "grid_time" in result.columns
        assert "gap_type" in result.columns
        assert "row_confidence" in result.columns
        
        # Check values
        assert result["CHWST"].tolist() == [10.0, 11.0]
        assert result["CHWRT"].tolist() == [20.0, 21.0]
        assert result["gap_type"].tolist() == ["VALID", "VALID"]

    def test_excluded_row_handling(self):
        """Test row marked as EXCLUDED"""
        grid = pd.Series([
            pd.Timestamp("2024-01-01 00:00:00"),
            pd.Timestamp("2024-01-01 00:15:00"),
        ])
        
        aligned_streams = {
            "CHWST": pd.DataFrame({
                "values": [10.0, np.nan],
                "quality": ["EXACT", "MISSING"],
                "jitter": [0, np.nan]
            }),
            "CHWRT": pd.DataFrame({
                "values": [20.0, np.nan],
                "quality": ["EXACT", "MISSING"],
                "jitter": [0, np.nan]
            }),
            "CDWRT": pd.DataFrame({
                "values": [30.0, np.nan],
                "quality": ["EXACT", "MISSING"],
                "jitter": [0, np.nan]
            }),
            "FLOW": pd.DataFrame({
                "values": [100.0, np.nan],
                "quality": ["EXACT", "MISSING"],
                "jitter": [0, np.nan]
            }),
            "POWER": pd.DataFrame({
                "values": [500.0, np.nan],
                "quality": ["EXACT", "MISSING"],
                "jitter": [0, np.nan]
            }),
        }
        
        # Exclusion window covers second row
        exclusion_windows = [(
            pd.Timestamp("2024-01-01 00:15:00"),
            pd.Timestamp("2024-01-01 00:30:00")
        )]
        
        stage2_gaps = {
            "CHWST": pd.Series(["VALID", "MAJOR_GAP"]),
            "CHWRT": pd.Series(["VALID", "MAJOR_GAP"]),
            "CDWRT": pd.Series(["VALID", "MAJOR_GAP"]),
            "FLOW": pd.Series(["VALID", "MAJOR_GAP"]),
            "POWER": pd.Series(["VALID", "MAJOR_GAP"]),
        }
        
        result = build_stage3_annotated_dataframe(
            grid, aligned_streams, exclusion_windows, stage2_gaps
        )
        
        assert result["gap_type"].iloc[0] == "VALID"
        assert result["gap_type"].iloc[1] == "EXCLUDED"
        assert result["row_confidence"].iloc[1] == 0.0

    def test_missing_mandatory_stream_creates_major_gap(self):
        """Test MISSING mandatory stream results in MAJOR_GAP"""
        grid = pd.Series([pd.Timestamp("2024-01-01 00:00:00")])
        
        aligned_streams = {
            "CHWST": pd.DataFrame({
                "values": [10.0],
                "quality": ["EXACT"],
                "jitter": [0]
            }),
            "CHWRT": pd.DataFrame({
                "values": [np.nan],  # Missing mandatory
                "quality": ["MISSING"],
                "jitter": [np.nan]
            }),
            "CDWRT": pd.DataFrame({
                "values": [30.0],
                "quality": ["EXACT"],
                "jitter": [0]
            }),
            "FLOW": pd.DataFrame({
                "values": [100.0],
                "quality": ["EXACT"],
                "jitter": [0]
            }),
            "POWER": pd.DataFrame({
                "values": [500.0],
                "quality": ["EXACT"],
                "jitter": [0]
            }),
        }
        
        exclusion_windows = []
        stage2_gaps = {
            "CHWST": pd.Series(["VALID"]),
            "CHWRT": pd.Series(["MAJOR_GAP"]),
            "CDWRT": pd.Series(["VALID"]),
            "FLOW": pd.Series(["VALID"]),
            "POWER": pd.Series(["VALID"]),
        }
        
        result = build_stage3_annotated_dataframe(
            grid, aligned_streams, exclusion_windows, stage2_gaps
        )
        
        assert result["gap_type"].iloc[0] == "MAJOR_GAP"
        assert result["row_confidence"].iloc[0] == 0.0

    def test_column_ordering(self):
        """Test that columns are in expected order"""
        grid = pd.Series([pd.Timestamp("2024-01-01 00:00:00")])
        
        aligned_streams = {
            "CHWST": pd.DataFrame({"values": [10.0], "quality": ["EXACT"], "jitter": [0]}),
            "CHWRT": pd.DataFrame({"values": [20.0], "quality": ["EXACT"], "jitter": [0]}),
            "CDWRT": pd.DataFrame({"values": [30.0], "quality": ["EXACT"], "jitter": [0]}),
            "FLOW": pd.DataFrame({"values": [100.0], "quality": ["EXACT"], "jitter": [0]}),
            "POWER": pd.DataFrame({"values": [500.0], "quality": ["EXACT"], "jitter": [0]}),
        }
        
        exclusion_windows = []
        stage2_gaps = {k: pd.Series(["VALID"]) for k in aligned_streams.keys()}
        
        result = build_stage3_annotated_dataframe(
            grid, aligned_streams, exclusion_windows, stage2_gaps
        )
        
        # Check column order: grid_time, values, quality, jitter, gap_type, row_confidence
        cols = result.columns.tolist()
        assert cols[0] == "grid_time"
        assert "gap_type" in cols
        assert "row_confidence" in cols


class TestBuildStage3Metrics:
    """Test suite for build_stage3_metrics()"""

    def test_perfect_metrics(self):
        """Test metrics for perfect synchronization"""
        df = pd.DataFrame({
            "gap_type": ["VALID"] * 100,
            "row_confidence": [1.0] * 100,
            "CHWST_quality": ["EXACT"] * 100,
            "CHWRT_quality": ["EXACT"] * 100,
            "CDWRT_quality": ["EXACT"] * 100,
            "FLOW_quality": ["EXACT"] * 100,
            "POWER_quality": ["EXACT"] * 100,
            "CHWST_jitter": [0] * 100,
            "CHWRT_jitter": [0] * 100,
            "CDWRT_jitter": [0] * 100,
            "FLOW_jitter": [0] * 100,
            "POWER_jitter": [0] * 100,
        })
        
        stage2_confidence = 0.95
        
        metrics = build_stage3_metrics(df, stage2_confidence)
        
        assert metrics["total_rows"] == 100
        assert metrics["VALID_count"] == 100
        assert metrics["MAJOR_GAP_count"] == 0
        assert metrics["EXCLUDED_count"] == 0
        assert metrics["valid_pct"] == 100.0
        assert metrics["coverage_tier"] == "EXCELLENT"
        assert metrics["coverage_penalty"] == 0.0
        assert metrics["stage3_confidence"] == 0.95  # No penalty

    def test_with_exclusions_and_gaps(self):
        """Test metrics with mixed gap types"""
        df = pd.DataFrame({
            "gap_type": ["VALID"] * 80 + ["MAJOR_GAP"] * 10 + ["EXCLUDED"] * 10,
            "row_confidence": [1.0] * 80 + [0.0] * 20,
            "CHWST_quality": ["EXACT"] * 100,
            "CHWRT_quality": ["EXACT"] * 100,
            "CDWRT_quality": ["EXACT"] * 100,
            "FLOW_quality": ["EXACT"] * 100,
            "POWER_quality": ["EXACT"] * 100,
            "CHWST_jitter": [0] * 100,
            "CHWRT_jitter": [0] * 100,
            "CDWRT_jitter": [0] * 100,
            "FLOW_jitter": [0] * 100,
            "POWER_jitter": [0] * 100,
        })
        
        stage2_confidence = 0.90
        
        metrics = build_stage3_metrics(df, stage2_confidence)
        
        assert metrics["total_rows"] == 100
        assert metrics["VALID_count"] == 80
        assert metrics["MAJOR_GAP_count"] == 10
        assert metrics["EXCLUDED_count"] == 10
        assert metrics["valid_pct"] == 80.0
        assert metrics["coverage_tier"] == "FAIR"  # 80-90%
        assert metrics["coverage_penalty"] == -0.05

    def test_jitter_statistics(self):
        """Test jitter statistics calculation"""
        df = pd.DataFrame({
            "gap_type": ["VALID"] * 5,
            "row_confidence": [1.0] * 5,
            "CHWST_quality": ["EXACT"] * 5,
            "CHWRT_quality": ["CLOSE"] * 5,
            "CDWRT_quality": ["INTERP"] * 5,
            "FLOW_quality": ["EXACT"] * 5,
            "POWER_quality": ["EXACT"] * 5,
            "CHWST_jitter": [0, 10, 20, 30, 40],
            "CHWRT_jitter": [60, 60, 60, 60, 60],
            "CDWRT_jitter": [300, 400, 500, 600, 700],
            "FLOW_jitter": [0] * 5,
            "POWER_jitter": [0] * 5,
        })
        
        stage2_confidence = 1.0
        
        metrics = build_stage3_metrics(df, stage2_confidence)
        
        # Check jitter stats exist
        assert "jitter_stats" in metrics
        assert "CHWST_mean_jitter" in metrics["jitter_stats"]
        assert "CHWRT_mean_jitter" in metrics["jitter_stats"]
        assert metrics["jitter_stats"]["CHWST_mean_jitter"] == 20.0  # (0+10+20+30+40)/5
        assert metrics["jitter_stats"]["CHWRT_mean_jitter"] == 60.0

    def test_bartech_scenario_metrics(self):
        """Test expected metrics for BarTech scenario"""
        # Simulate ~93.8% coverage
        valid_count = 33000
        major_gap_count = 2136
        total_rows = 35136
        
        df = pd.DataFrame({
            "gap_type": ["VALID"] * valid_count + ["MAJOR_GAP"] * major_gap_count,
            "row_confidence": [0.95] * valid_count + [0.0] * major_gap_count,
            "CHWST_quality": ["EXACT"] * total_rows,
            "CHWRT_quality": ["CLOSE"] * total_rows,
            "CDWRT_quality": ["EXACT"] * total_rows,
            "FLOW_quality": ["EXACT"] * total_rows,
            "POWER_quality": ["EXACT"] * total_rows,
            "CHWST_jitter": [0] * total_rows,
            "CHWRT_jitter": [30] * total_rows,
            "CDWRT_jitter": [0] * total_rows,
            "FLOW_jitter": [0] * total_rows,
            "POWER_jitter": [0] * total_rows,
        })
        
        stage2_confidence = 0.93
        
        metrics = build_stage3_metrics(df, stage2_confidence)
        
        assert metrics["total_rows"] == 35136
        assert metrics["VALID_count"] == 33000
        expected_pct = (33000 / 35136) * 100  # ~93.9%
        assert abs(metrics["valid_pct"] - expected_pct) < 0.1
        assert metrics["coverage_tier"] == "GOOD"  # 90-95%
        assert metrics["coverage_penalty"] == -0.02
        # stage3_confidence = 0.93 - 0.02 = 0.91
        assert abs(metrics["stage3_confidence"] - 0.91) < 0.01

    def test_returns_dict_with_required_keys(self):
        """Test output schema has all required keys"""
        df = pd.DataFrame({
            "gap_type": ["VALID"],
            "row_confidence": [1.0],
            "CHWST_quality": ["EXACT"],
            "CHWRT_quality": ["EXACT"],
            "CDWRT_quality": ["EXACT"],
            "FLOW_quality": ["EXACT"],
            "POWER_quality": ["EXACT"],
            "CHWST_jitter": [0],
            "CHWRT_jitter": [0],
            "CDWRT_jitter": [0],
            "FLOW_jitter": [0],
            "POWER_jitter": [0],
        })
        
        metrics = build_stage3_metrics(df, 1.0)
        
        required_keys = [
            "total_rows", "VALID_count", "MAJOR_GAP_count", "EXCLUDED_count",
            "valid_pct", "coverage_tier", "coverage_penalty",
            "stage2_confidence", "stage3_confidence", "jitter_stats"
        ]
        
        for key in required_keys:
            assert key in metrics

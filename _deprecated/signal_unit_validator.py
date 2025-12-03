#!/usr/bin/env python3
"""
Signal Unit Validator - Detects Unit Confusion in HVAC Telemetry

Solves 3 critical problems:
1. "Load %" vs Real Power (kW) confusion
2. Load > 100% as mode change vs fault
3. kW vs kWh (instantaneous vs cumulative) confusion
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple
from scipy.stats import pearsonr
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SignalUnitValidator:
    """Validates and detects unit confusion in HVAC signals."""
    
    def __init__(self):
        self.validation_results = []
    
    def validate_load_signal(
        self,
        signal_series: pd.Series,
        signal_name: str,
        equipment_type: str,
        nameplate_kw: float = None,
        power_series: pd.Series = None
    ) -> Dict:
        """
        Comprehensive validation for load/power signals.
        
        Detects:
        - Load % mislabeled as kW or vice versa
        - Mode changes (% → RT → capacity index)
        - kW vs kWh confusion
        
        Args:
            signal_series: Raw signal data
            signal_name: Name for logging
            equipment_type: 'chiller', 'pump', 'fan', etc.
            nameplate_kw: Equipment nameplate capacity
            power_series: Corresponding power signal (if available)
        
        Returns:
            Validation result dictionary
        """
        result = {
            "signal_name": signal_name,
            "equipment_type": equipment_type,
            "likely_unit": "UNKNOWN",
            "confidence": "low",
            "issues": [],
            "recommendations": [],
            "use_for_cop": False,
            "use_for_energy": False,
        }
        
        s = signal_series.dropna()
        if len(s) == 0:
            result["issues"].append("No valid data points")
            return result
        
        # Problem #1: Is this Load % or Real kW?
        load_vs_kw = self._detect_load_vs_kw(s, nameplate_kw, equipment_type)
        result.update(load_vs_kw)
        
        # Problem #2: Mode changes (% → RT, capacity index, etc.)
        mode_changes = self._detect_mode_changes(s, signal_name)
        if mode_changes["has_mode_changes"]:
            result["issues"].append(mode_changes["description"])
            result["recommendations"].extend(mode_changes["recommendations"])
        
        # Problem #3: kW vs kWh confusion
        if power_series is not None:
            kwh_confusion = self._detect_kwh_confusion(s, power_series, signal_name)
            if kwh_confusion["is_confused"]:
                result["issues"].append(kwh_confusion["description"])
                result["recommendations"].extend(kwh_confusion["recommendations"])
        
        # Cross-validation with power signal
        if power_series is not None and result["likely_unit"] in ["LOAD_PERCENT", "LOAD_FRACTION"]:
            correlation_check = self._validate_load_power_correlation(
                s, power_series, nameplate_kw
            )
            result["correlation_analysis"] = correlation_check
            if correlation_check["status"] == "FAIL":
                result["issues"].append(correlation_check["reason"])
        
        # Final recommendations
        result["use_for_cop"] = (
            result["likely_unit"] in ["LOAD_PERCENT", "LOAD_FRACTION"] 
            and result["confidence"] in ["high", "medium"]
            and len(result["issues"]) == 0
        )
        
        result["use_for_energy"] = (
            result["likely_unit"] == "REAL_KW"
            and result["confidence"] in ["high", "medium"]
        )
        
        return result
    
    def _detect_load_vs_kw(
        self, 
        series: pd.Series, 
        nameplate_kw: float, 
        equipment_type: str
    ) -> Dict:
        """
        Problem #1: Detect if signal is Load % or Real kW.
        
        Key insight: Load % should not correlate with nameplate,
        but real kW will be bounded by nameplate.
        """
        mn, mx, mean = series.min(), series.max(), series.mean()
        p995 = np.percentile(series, 99.5)
        
        result = {
            "likely_unit": "UNKNOWN",
            "confidence": "low",
            "issues": [],
            "recommendations": []
        }
        
        # Check 1: Value range alignment with nameplate
        if nameplate_kw:
            # If max is close to nameplate → likely real kW
            if 0.6 * nameplate_kw < mx < 1.4 * nameplate_kw:
                result["likely_unit"] = "REAL_KW"
                result["confidence"] = "high"
                result["recommendations"].append(
                    f"✅ Detected as REAL kW: Max ({mx:.0f}) aligns with nameplate ({nameplate_kw:.0f} kW)"
                )
                result["recommendations"].append(
                    "🚫 DO NOT NORMALIZE - Use raw values for power calculations"
                )
                return result
            
            # If max is 0-1 or 0-100 → likely Load %
            if mx <= 1.05:
                result["likely_unit"] = "LOAD_FRACTION"
                result["confidence"] = "high"
            elif mx <= 110:
                result["likely_unit"] = "LOAD_PERCENT"
                result["confidence"] = "high"
        
        # Check 2: Unrealistic average for load signal
        if mean / (mx + 0.001) > 0.7:  # Mean > 70% of max
            result["issues"].append(
                f"⚠️  SUSPICIOUS: Average ({mean:.1f}) is {mean/(mx+0.001)*100:.0f}% of max"
            )
            result["issues"].append(
                "   Equipment rarely operates >70% average load"
            )
            result["recommendations"].append(
                "   → Verify if this is actually kW, not Load %"
            )
            result["confidence"] = "low"
        
        # Check 3: kW range check for specific equipment
        kw_ranges = {
            "chiller": (50, 5000),    # Chillers typically 50-5000 kW
            "pump": (5, 500),         # Pumps typically 5-500 kW
            "fan": (5, 200),          # Fans typically 5-200 kW
            "tower": (10, 300),       # Cooling tower fans 10-300 kW
        }
        
        if equipment_type in kw_ranges:
            kw_min, kw_max = kw_ranges[equipment_type]
            if kw_min < mx < kw_max:
                if not nameplate_kw:  # No nameplate to contradict
                    result["likely_unit"] = "POSSIBLE_REAL_KW"
                    result["confidence"] = "medium"
                    result["recommendations"].append(
                        f"⚠️  Max ({mx:.0f}) falls in typical {equipment_type} kW range ({kw_min}-{kw_max})"
                    )
                    result["recommendations"].append(
                        "   → Verify with BMS documentation or nameplate"
                    )
        
        return result
    
    def _detect_mode_changes(self, series: pd.Series, signal_name: str) -> Dict:
        """
        Problem #2: Detect if Load > 100% indicates mode change.
        
        Some chillers switch from % → RT (tons) → capacity index beyond 100%.
        """
        mx = series.max()
        p99 = np.percentile(series, 99)
        
        # Count samples > 100 (assuming some normalization happened)
        if mx > 100:
            over_100_count = (series > 100).sum()
            over_100_pct = over_100_count / len(series) * 100
            
            if over_100_pct > 1:  # More than 1% of samples
                return {
                    "has_mode_changes": True,
                    "description": f"🚨 MODE CHANGE DETECTED: {over_100_pct:.1f}% of samples > 100",
                    "recommendations": [
                        "   → Signal likely switches units beyond 100%",
                        "   → Common: % → Refrigerant Tons (RT) → Capacity Index",
                        "   → Split analysis: [0-100] vs [>100] separately",
                        "   → Contact vendor for unit documentation"
                    ]
                }
        
        # Detect sudden step changes (possible mode shifts)
        diffs = series.diff().abs()
        large_steps = (diffs > 50).sum()  # Steps > 50 units
        
        if large_steps > len(series) * 0.005:  # >0.5% of samples
            return {
                "has_mode_changes": True,
                "description": f"⚠️  {large_steps} large step changes detected (>50 unit jumps)",
                "recommendations": [
                    "   → Possible unit changes mid-stream",
                    "   → Review time-series plot for discontinuities",
                    "   → Verify BMS configuration changes"
                ]
            }
        
        return {"has_mode_changes": False}
    
    def _detect_kwh_confusion(
        self,
        signal_series: pd.Series,
        power_series: pd.Series,
        signal_name: str
    ) -> Dict:
        """
        Problem #3: Detect kW vs kWh confusion.
        
        Key insight:
        - kWh (cumulative) should be monotonic increasing
        - kW (instantaneous) should vary up/down
        """
        s = signal_series.dropna()
        
        # Check 1: Monotonicity (cumulative signals always increase)
        diffs = s.diff().dropna()
        negative_diffs = (diffs < -0.01).sum()  # Allow tiny floating point errors
        negative_pct = negative_diffs / len(diffs) * 100
        
        if negative_pct < 1:  # <1% negative diffs → likely cumulative
            # But is it labeled as kW?
            if "kw" in signal_name.lower() and "kwh" not in signal_name.lower():
                return {
                    "is_confused": True,
                    "description": "🚨 kW/kWh CONFUSION: Signal is monotonic (cumulative) but labeled as kW",
                    "recommendations": [
                        "   → This is kWh (cumulative), NOT kW (instantaneous)",
                        "   → DO NOT integrate - differentiate instead",
                        "   → kW = diff(kWh) / diff(time_hours)",
                        "   → Fix BMS point label"
                    ]
                }
        
        # Check 2: Variance (instantaneous signals vary more)
        cv = s.std() / (s.mean() + 0.001)  # Coefficient of variation
        
        if cv < 0.05:  # Very low variation
            if s.mean() > 0 and s.max() / s.mean() < 1.2:
                return {
                    "is_confused": True,
                    "description": "⚠️  Signal shows very low variation - possible cumulative counter",
                    "recommendations": [
                        "   → CV < 0.05 suggests cumulative kWh, not instantaneous kW",
                        "   → Verify with time-series plot",
                        "   → Check if values always increase"
                    ]
                }
        
        # Check 3: Cross-check with another power signal
        if power_series is not None:
            # If this signal is cumulative, its diff should correlate with power_series
            s_diff = s.diff()
            corr, _ = pearsonr(s_diff.dropna(), power_series.loc[s_diff.dropna().index])
            
            if corr > 0.7:
                return {
                    "is_confused": True,
                    "description": f"✅ Signal is cumulative kWh (diff correlates {corr:.2f} with kW)",
                    "recommendations": [
                        "   → Differentiate to get instantaneous kW",
                        "   → kW = diff(kWh) / diff(time_hours)"
                    ]
                }
        
        return {"is_confused": False}
    
    def _validate_load_power_correlation(
        self,
        load_series: pd.Series,
        power_series: pd.Series,
        nameplate_kw: float
    ) -> Dict:
        """
        Validate that Load % and Power kW have expected relationship.
        
        Expected: Power ≈ Nameplate_kW × Load × Efficiency_Factor
        For chillers: Relationship should be ~cubic (affinity laws)
        """
        # Align series
        common_idx = load_series.index.intersection(power_series.index)
        load = load_series.loc[common_idx]
        power = power_series.loc[common_idx]
        
        if len(load) < 10:
            return {"status": "SKIP", "reason": "Insufficient overlapping data"}
        
        # Normalize load to 0-1 if needed
        if load.max() > 10:
            load = load / load.max()
        elif load.max() > 1.5:
            load = load / 100
        
        # Filter to operating periods (load > 5%)
        operating = (load > 0.05) & (power > 0)
        load_op = load[operating]
        power_op = power[operating]
        
        if len(load_op) < 10:
            return {"status": "SKIP", "reason": "Insufficient operating data"}
        
        # Check 1: Linear correlation
        corr_linear, _ = pearsonr(load_op, power_op)
        
        if corr_linear < 0.5:
            return {
                "status": "FAIL",
                "reason": f"Load-Power correlation {corr_linear:.2f} < 0.5",
                "recommendation": "🚨 Load % and Power kW do not correlate - verify units"
            }
        
        # Check 2: Cubic relationship (for chillers/pumps - affinity laws)
        load_cubed = load_op ** 3
        corr_cubic, _ = pearsonr(load_cubed, power_op)
        
        if corr_cubic > corr_linear + 0.1:
            return {
                "status": "PASS",
                "confidence": "HIGH",
                "correlation_linear": corr_linear,
                "correlation_cubic": corr_cubic,
                "note": f"✅ Cubic relationship confirmed (r³={corr_cubic:.3f} > r={corr_linear:.3f})",
                "recommendation": "Load % and Power kW relationship is physically plausible"
            }
        
        # Check 3: Power ratio plausibility
        if nameplate_kw:
            power_ratio = power_op.max() / nameplate_kw
            if power_ratio < 0.3 or power_ratio > 1.5:
                return {
                    "status": "WARNING",
                    "correlation_linear": corr_linear,
                    "note": f"⚠️  Power/Nameplate ratio {power_ratio:.2f} is unusual",
                    "recommendation": "Verify nameplate capacity or check if power signal is correct"
                }
        
        return {
            "status": "PASS",
            "confidence": "MEDIUM",
            "correlation_linear": corr_linear,
            "note": f"✅ Linear correlation {corr_linear:.2f} acceptable"
        }
    
    def generate_validation_report(self, results: list) -> str:
        """Generate human-readable validation report."""
        report = []
        report.append("=" * 80)
        report.append("SIGNAL UNIT VALIDATION REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Group by status
        critical = [r for r in results if "🚨" in str(r.get("issues", []))]
        warnings = [r for r in results if "⚠️" in str(r.get("issues", []))]
        passed = [r for r in results if not r.get("issues")]
        
        if critical:
            report.append("🚨 CRITICAL ISSUES (Block Analytics):")
            report.append("-" * 80)
            for r in critical:
                report.append(f"  {r['signal_name']} ({r['equipment_type']})")
                report.append(f"    Detected Unit: {r['likely_unit']} (Confidence: {r['confidence']})")
                for issue in r["issues"]:
                    report.append(f"    {issue}")
                for rec in r["recommendations"]:
                    report.append(f"    {rec}")
                report.append("")
        
        if warnings:
            report.append("⚠️  WARNINGS (Review Before Use):")
            report.append("-" * 80)
            for r in warnings:
                report.append(f"  {r['signal_name']} ({r['equipment_type']})")
                report.append(f"    Detected Unit: {r['likely_unit']} (Confidence: {r['confidence']})")
                for issue in r["issues"]:
                    report.append(f"    {issue}")
                report.append("")
        
        if passed:
            report.append("✅ VALIDATED SIGNALS:")
            report.append("-" * 80)
            for r in passed:
                report.append(f"  {r['signal_name']}: {r['likely_unit']} (Confidence: {r['confidence']})")
        
        report.append("")
        report.append("=" * 80)
        report.append(f"Summary: {len(passed)} passed, {len(warnings)} warnings, {len(critical)} critical")
        report.append("=" * 80)
        
        return "\n".join(report)


if __name__ == "__main__":
    # Example usage
    validator = SignalUnitValidator()
    
    # Test case 1: Load % mislabeled as kW
    chiller_signal = pd.Series(np.random.uniform(200, 1200, 1000))  # Looks like kW
    result1 = validator.validate_load_signal(
        chiller_signal,
        "Chiller_1_Load",
        "chiller",
        nameplate_kw=1200
    )
    
    print(validator.generate_validation_report([result1]))

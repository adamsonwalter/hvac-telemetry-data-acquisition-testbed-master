#!/usr/bin/env python3
"""
Comprehensive test suite for universal BMS percent decoder.
Tests all HVAC equipment types and encoding variations.
"""

import pandas as pd
from pathlib import Path
from universal_bms_percent_decoder import decode_telemetry_file, generate_detection_report
import sys

# Expected detections for each equipment type
EXPECTED_DETECTIONS = {
    # PUMPS
    "Test_Pump_VSD_50000.csv": {"type": "raw_counts_large", "confidence": "medium"},
    "Test_Pump_VSD_65535.csv": {"type": "raw_counts_large", "confidence": "medium"},
    "Test_Pump_VSD_Percent.csv": {"type": "percentage_0_100", "confidence": "high"},
    
    # COOLING TOWERS
    "Test_CoolingTower_Fan_10000.csv": {"type": "counts_10000_0.01pct", "confidence": "high"},
    "Test_CoolingTower_Fan_32767.csv": {"type": "raw_counts_large", "confidence": "medium"},
    
    # VALVES
    "Test_CHW_Valve_1000.csv": {"type": "counts_1000_0.1pct", "confidence": "high"},
    "Test_HW_Valve_Percent.csv": {"type": "percentage_0_100", "confidence": "high"},
    "Test_CHW_Valve_Fraction.csv": {"type": "fraction_0_1", "confidence": "high"},
    
    # DAMPERS
    "Test_OA_Damper_4095.csv": {"type": "analog_unscaled", "confidence": "medium"},
    "Test_OA_Damper_1000.csv": {"type": "counts_1000_0.1pct", "confidence": "high"},
    "Test_VAV_Damper_2764.csv": {"type": "analog_unscaled", "confidence": "medium"},
    
    # FANS
    "Test_AHU_SupplyFan_Percent.csv": {"type": "percentage_0_100", "confidence": "high"},
    "Test_AHU_SupplyFan_10000.csv": {"type": "counts_10000_0.01pct", "confidence": "high"},
    "Test_ExhaustFan_27648.csv": {"type": "analog_unscaled", "confidence": "medium"},
    
    # CHILLERS
    "Test_Chiller_Load_Fraction.csv": {"type": "fraction_0_1", "confidence": "high"},
    "Test_Chiller_Load_Percent.csv": {"type": "percentage_0_100", "confidence": "high"},
    "Test_Chiller_Load_10000.csv": {"type": "counts_10000_0.01pct", "confidence": "high"},
    
    # BOILERS
    "Test_Boiler_FiringRate_Percent.csv": {"type": "percentage_0_100", "confidence": "high"},
    "Test_Boiler_FiringRate_1000.csv": {"type": "counts_1000_0.1pct", "confidence": "high"},
    
    # SIEMENS
    "Test_Siemens_Pump_100000.csv": {"type": "counts_100000_siemens", "confidence": "high"},
    "Test_Siemens_Valve_100000.csv": {"type": "counts_100000_siemens", "confidence": "high"},
}


def validate_normalized_range(df: pd.DataFrame, tolerance: float = 0.05) -> tuple:
    """Validate that normalized values are in expected 0-1.2 range."""
    norm_min = df["normalized"].min()
    norm_max = df["normalized"].max()
    
    if norm_min < -tolerance:
        return False, f"Min too low: {norm_min:.4f}"
    
    if norm_max > 1.25:
        return False, f"Max too high: {norm_max:.4f}"
    
    return True, "OK"


def run_comprehensive_tests():
    """Run comprehensive tests on all HVAC equipment types."""
    print("=" * 80)
    print("UNIVERSAL BMS PERCENT DECODER - COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    print()
    
    base_path = Path(__file__).parent
    passed = 0
    failed = 0
    warnings = 0
    
    # Group files by equipment type
    equipment_types = {
        "PUMPS": [f for f in EXPECTED_DETECTIONS.keys() if "Pump" in f],
        "COOLING TOWERS": [f for f in EXPECTED_DETECTIONS.keys() if "CoolingTower" in f],
        "VALVES": [f for f in EXPECTED_DETECTIONS.keys() if "Valve" in f],
        "DAMPERS": [f for f in EXPECTED_DETECTIONS.keys() if "Damper" in f],
        "FANS": [f for f in EXPECTED_DETECTIONS.keys() if "Fan" in f and "CoolingTower" not in f],
        "CHILLERS": [f for f in EXPECTED_DETECTIONS.keys() if "Chiller" in f],
        "BOILERS": [f for f in EXPECTED_DETECTIONS.keys() if "Boiler" in f],
        "SIEMENS SYSTEMS": [f for f in EXPECTED_DETECTIONS.keys() if "Siemens" in f],
    }
    
    for equipment_type, files in equipment_types.items():
        print(f"\n{'='*80}")
        print(f"TESTING: {equipment_type}")
        print(f"{'='*80}")
        
        for filename in files:
            filepath = base_path / filename
            
            if not filepath.exists():
                print(f"  ❌ SKIP: {filename} (file not found)")
                failed += 1
                continue
            
            expected = EXPECTED_DETECTIONS[filename]
            
            try:
                # Decode file
                df = decode_telemetry_file(str(filepath))
                
                # Get detected type
                detected_type = df["meta_detected_type"].iloc[0]
                detected_confidence = df["meta_confidence"].iloc[0]
                
                # Validate detection
                type_match = detected_type == expected["type"]
                confidence_match = detected_confidence == expected["confidence"]
                range_valid, range_msg = validate_normalized_range(df)
                
                # Determine pass/fail/warning
                if type_match and range_valid:
                    if confidence_match:
                        print(f"  ✅ PASS: {filename}")
                        passed += 1
                    else:
                        print(f"  ⚠️  WARN: {filename} (confidence mismatch)")
                        print(f"       Expected: {expected['confidence']}, Got: {detected_confidence}")
                        warnings += 1
                        passed += 1  # Still counts as pass
                    
                    # Show brief stats
                    norm_stats = df["normalized"].describe()
                    print(f"       Type: {detected_type}")
                    print(f"       Range: {norm_stats['min']:.4f} to {norm_stats['max']:.4f}")
                    
                else:
                    print(f"  ❌ FAIL: {filename}")
                    if not type_match:
                        print(f"       Expected type: {expected['type']}")
                        print(f"       Got type: {detected_type}")
                    if not range_valid:
                        print(f"       Range issue: {range_msg}")
                    failed += 1
                    
            except Exception as e:
                print(f"  ❌ ERROR: {filename}")
                print(f"       {e}")
                failed += 1
    
    # Summary
    total = passed + failed
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests:    {total}")
    print(f"✅ Passed:      {passed}")
    print(f"⚠️  Warnings:    {warnings}")
    print(f"❌ Failed:      {failed}")
    print(f"Success Rate:   {(passed/total*100):.1f}%")
    print("=" * 80)
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Universal decoder working perfectly.")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed - review errors above")
        return False


def test_specific_file(filepath: str):
    """Test a specific file and show detailed report."""
    print(f"\nTesting: {filepath}")
    print("=" * 80)
    
    df = decode_telemetry_file(filepath)
    print(generate_detection_report(df))
    
    # Show sample values
    print("\nSample Values (first 10 rows):")
    print(df[["timestamp", "raw_value", "normalized"]].head(10).to_string(index=False))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test specific file
        test_specific_file(sys.argv[1])
    else:
        # Run full test suite
        success = run_comprehensive_tests()
        sys.exit(0 if success else 1)

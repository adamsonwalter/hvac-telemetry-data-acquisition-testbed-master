#!/usr/bin/env python3
"""
Automated test suite for universal chiller load decoder.
Validates detection accuracy across all signal types.
"""

import pandas as pd
from pathlib import Path
from universal_chiller_load_decoder import decode_telemetry_file, generate_detection_report

# Expected detection types for each test file
EXPECTED_DETECTIONS = {
    "Test_Carrier_Chiller_A_Load.csv": {
        "type": "fraction_0_1",
        "confidence": "high",
        "nameplate_kw": None
    },
    "Test_Standard_Chiller_B_Load.csv": {
        "type": "percentage_0_100",
        "confidence": "high",
        "nameplate_kw": None
    },
    "Test_Trend_Chiller_C_Load.csv": {
        "type": "raw_counts_percentile",  # Falls through to percentile
        "confidence": "medium",
        "nameplate_kw": None
    },
    "Test_Schneider_Chiller_D_Load.csv": {
        "type": "counts_1000_0.1pct",
        "confidence": "high",
        "nameplate_kw": None
    },
    "Test_RealKW_Chiller_E_Load.csv": {
        "type": "real_kw",
        "confidence": "medium",
        "nameplate_kw": 1200
    },
    "Test_Amps_Chiller_F_Load.csv": {
        "type": "current_amps",
        "confidence": "medium",
        "nameplate_kw": 1200
    },
    "Test_ADC16bit_Chiller_G_Load.csv": {
        "type": "raw_counts_percentile",
        "confidence": "medium",
        "nameplate_kw": None
    },
    "Test_ADC15bit_Chiller_H_Load.csv": {
        "type": "raw_counts_percentile",
        "confidence": "medium",
        "nameplate_kw": None
    },
    "Test_Counts50k_Chiller_I_Load.csv": {
        "type": "raw_counts_percentile",
        "confidence": "medium",
        "nameplate_kw": None
    },
    "Test_Weird_Chiller_J_Load.csv": {
        "type": "raw_counts_percentile",
        "confidence": "medium",
        "nameplate_kw": None
    },
    "BarTech_160_Ann_St_Level_22_MSSB_Chiller_2_Load.csv": {
        "type": "percentage_0_100",
        "confidence": "high",
        "nameplate_kw": None
    }
}


def validate_plr_range(df: pd.DataFrame) -> bool:
    """Validate that PLR values are reasonable (0-1.2 range)."""
    plr_min = df["plr"].min()
    plr_max = df["plr"].max()
    
    if plr_min < -0.01:
        print(f"    ❌ PLR min too low: {plr_min:.4f}")
        return False
    
    if plr_max > 1.25:
        print(f"    ❌ PLR max too high: {plr_max:.4f}")
        return False
    
    return True


def run_tests():
    """Run all decoder tests."""
    print("=" * 80)
    print("UNIVERSAL CHILLER LOAD DECODER - TEST SUITE")
    print("=" * 80)
    print()
    
    base_path = Path(__file__).parent
    passed = 0
    failed = 0
    
    for filename, expected in EXPECTED_DETECTIONS.items():
        filepath = base_path / filename
        
        if not filepath.exists():
            print(f"❌ SKIP: {filename} (file not found)")
            failed += 1
            continue
        
        print(f"Testing: {filename}")
        
        try:
            # Decode file
            df = decode_telemetry_file(
                str(filepath),
                nameplate_kw=expected["nameplate_kw"]
            )
            
            # Get detected type
            detected_type = df["meta_detected_type"].iloc[0]
            detected_confidence = df["meta_confidence"].iloc[0]
            
            # Validate detection
            type_match = detected_type == expected["type"]
            confidence_match = detected_confidence == expected["confidence"]
            plr_valid = validate_plr_range(df)
            
            if type_match and plr_valid:
                print(f"  ✅ PASS: Detected {detected_type} ({detected_confidence} confidence)")
                passed += 1
            else:
                print(f"  ❌ FAIL:")
                if not type_match:
                    print(f"    Expected: {expected['type']}, Got: {detected_type}")
                if not confidence_match:
                    print(f"    Confidence: Expected {expected['confidence']}, Got: {detected_confidence}")
                if not plr_valid:
                    print(f"    PLR range validation failed")
                failed += 1
            
            # Show PLR stats
            plr_stats = df["plr"].describe()
            print(f"    PLR range: {plr_stats['min']:.4f} to {plr_stats['max']:.4f}")
            print()
            
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            failed += 1
            print()
    
    # Summary
    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed} tests")
    
    if failed == 0:
        print("✅ All tests passed!")
    else:
        print(f"❌ {failed} test(s) failed")
    
    print("=" * 80)
    
    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)

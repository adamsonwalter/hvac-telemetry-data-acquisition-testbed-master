#!/usr/bin/env python3
"""
Generate synthetic test files for ALL HVAC equipment percentage signals.
Covers pumps, fans, valves, dampers, chillers, towers, etc.
"""

import numpy as np
import pandas as pd
from pathlib import Path

BASE_TIMESTAMP = 1754609985


def generate_realistic_percent_pattern(n_points: int, seed: int = 42) -> np.ndarray:
    """Generate realistic 0-1 percentage pattern for HVAC equipment."""
    np.random.seed(seed)
    
    percent = []
    i = 0
    
    while i < n_points:
        mode = np.random.choice(['off', 'low', 'medium', 'high', 'modulating'], 
                                p=[0.25, 0.15, 0.25, 0.15, 0.20])
        
        if mode == 'off':
            duration = np.random.randint(30, 150)
            percent.extend([0.0] * duration)
            i += duration
            
        elif mode == 'low':
            duration = np.random.randint(20, 60)
            base = np.random.uniform(0.15, 0.35)
            variation = np.random.normal(0, 0.03, duration)
            values = np.clip(base + variation, 0.1, 0.4)
            percent.extend(values)
            i += duration
            
        elif mode == 'medium':
            duration = np.random.randint(30, 80)
            base = np.random.uniform(0.45, 0.65)
            variation = np.random.normal(0, 0.04, duration)
            values = np.clip(base + variation, 0.4, 0.7)
            percent.extend(values)
            i += duration
            
        elif mode == 'high':
            duration = np.random.randint(15, 50)
            base = np.random.uniform(0.75, 0.95)
            variation = np.random.normal(0, 0.02, duration)
            values = np.clip(base + variation, 0.7, 1.0)
            percent.extend(values)
            i += duration
            
        elif mode == 'modulating':
            duration = np.random.randint(40, 100)
            # Create smooth modulation
            t = np.linspace(0, 4*np.pi, duration)
            wave = 0.5 + 0.3 * np.sin(t) + 0.1 * np.random.randn(duration)
            values = np.clip(wave, 0.2, 0.9)
            percent.extend(values)
            i += duration
    
    return np.array(percent[:n_points])


def generate_timestamps(n_points: int) -> np.ndarray:
    """Generate timestamps."""
    timestamps = [BASE_TIMESTAMP]
    for i in range(1, n_points):
        jump = 60 + np.random.randint(-5, 10)
        timestamps.append(timestamps[-1] + jump)
    return np.array(timestamps)


def create_hvac_test_file(filename: str, signal_type: str, equipment_type: str, n_points: int = 500):
    """Create test CSV for specific HVAC equipment and signal encoding."""
    
    # Generate base 0-1 pattern
    fraction = generate_realistic_percent_pattern(n_points, seed=hash(filename) % 1000)
    timestamps = generate_timestamps(n_points)
    
    # Apply encoding based on signal type
    encodings = {
        "fraction_0_1": lambda x: x,
        "percentage_0_100": lambda x: x * 100,
        "counts_10000": lambda x: x * 10000,
        "counts_1000": lambda x: x * 1000,
        "counts_100000": lambda x: x * 100000,
        "raw_50000": lambda x: x * 50000,
        "raw_65535": lambda x: x * 65535,
        "raw_32767": lambda x: x * 32767,
        "analog_4095": lambda x: x * 4095,  # 12-bit ADC
        "analog_2764": lambda x: x * 2764,  # Weird custom
        "analog_27648": lambda x: x * 27648,  # Some Honeywell
    }
    
    if signal_type not in encodings:
        raise ValueError(f"Unknown signal type: {signal_type}")
    
    values = encodings[signal_type](fraction)
    
    # Round to integers for count-based signals
    if signal_type not in ["fraction_0_1", "percentage_0_100"]:
        values = np.round(values).astype(int)
    
    df = pd.DataFrame({
        "save_time": timestamps,
        "value": values
    })
    
    output_path = Path(__file__).parent / filename
    df.to_csv(output_path, index=False)
    
    print(f"Generated: {filename}")
    print(f"  Equipment: {equipment_type}")
    print(f"  Encoding:  {signal_type}")
    print(f"  Range:     {values.min():.2f} to {values.max():.2f}")
    print()


if __name__ == "__main__":
    print("=" * 80)
    print("GENERATING HVAC EQUIPMENT TEST FILES")
    print("=" * 80)
    print()
    
    # PUMPS (VSD Demand/Speed) - Most common problem signal
    print("--- PUMP VSD SIGNALS ---")
    create_hvac_test_file(
        "Test_Pump_VSD_50000.csv",
        "raw_50000",
        "Chilled Water Pump VSD"
    )
    create_hvac_test_file(
        "Test_Pump_VSD_65535.csv",
        "raw_65535",
        "Condenser Water Pump VSD"
    )
    create_hvac_test_file(
        "Test_Pump_VSD_Percent.csv",
        "percentage_0_100",
        "Heating Water Pump VSD"
    )
    
    # COOLING TOWER FANS
    print("--- COOLING TOWER FAN SIGNALS ---")
    create_hvac_test_file(
        "Test_CoolingTower_Fan_10000.csv",
        "counts_10000",
        "Cooling Tower Fan VSD"
    )
    create_hvac_test_file(
        "Test_CoolingTower_Fan_32767.csv",
        "raw_32767",
        "Cooling Tower Fan VSD"
    )
    
    # VALVES (CHW, HW, etc.)
    print("--- VALVE POSITION SIGNALS ---")
    create_hvac_test_file(
        "Test_CHW_Valve_1000.csv",
        "counts_1000",
        "AHU Chilled Water Valve"
    )
    create_hvac_test_file(
        "Test_HW_Valve_Percent.csv",
        "percentage_0_100",
        "AHU Heating Water Valve"
    )
    create_hvac_test_file(
        "Test_CHW_Valve_Fraction.csv",
        "fraction_0_1",
        "FCU Chilled Water Valve"
    )
    
    # DAMPERS (OA, Return, Exhaust)
    print("--- DAMPER POSITION SIGNALS ---")
    create_hvac_test_file(
        "Test_OA_Damper_4095.csv",
        "analog_4095",
        "AHU Outdoor Air Damper"
    )
    create_hvac_test_file(
        "Test_OA_Damper_1000.csv",
        "counts_1000",
        "AHU Outdoor Air Damper"
    )
    create_hvac_test_file(
        "Test_VAV_Damper_2764.csv",
        "analog_2764",
        "VAV Box Damper"
    )
    
    # AHU/FCU FANS
    print("--- FAN SPEED SIGNALS ---")
    create_hvac_test_file(
        "Test_AHU_SupplyFan_Percent.csv",
        "percentage_0_100",
        "AHU Supply Fan VSD"
    )
    create_hvac_test_file(
        "Test_AHU_SupplyFan_10000.csv",
        "counts_10000",
        "AHU Supply Fan VSD"
    )
    create_hvac_test_file(
        "Test_ExhaustFan_27648.csv",
        "analog_27648",
        "Exhaust Fan VSD"
    )
    
    # CHILLERS (Load signals)
    print("--- CHILLER LOAD SIGNALS ---")
    create_hvac_test_file(
        "Test_Chiller_Load_Fraction.csv",
        "fraction_0_1",
        "Chiller Load (Carrier)"
    )
    create_hvac_test_file(
        "Test_Chiller_Load_Percent.csv",
        "percentage_0_100",
        "Chiller Load (Generic)"
    )
    create_hvac_test_file(
        "Test_Chiller_Load_10000.csv",
        "counts_10000",
        "Chiller Load (Trend)"
    )
    
    # BOILERS (Firing Rate)
    print("--- BOILER FIRING RATE SIGNALS ---")
    create_hvac_test_file(
        "Test_Boiler_FiringRate_Percent.csv",
        "percentage_0_100",
        "Boiler Firing Rate"
    )
    create_hvac_test_file(
        "Test_Boiler_FiringRate_1000.csv",
        "counts_1000",
        "Boiler Firing Rate"
    )
    
    # SIEMENS SPECIFIC (100000 counts)
    print("--- SIEMENS SPECIFIC SIGNALS ---")
    create_hvac_test_file(
        "Test_Siemens_Pump_100000.csv",
        "counts_100000",
        "Pump VSD (Siemens)"
    )
    create_hvac_test_file(
        "Test_Siemens_Valve_100000.csv",
        "counts_100000",
        "Valve Position (Siemens)"
    )
    
    print("=" * 80)
    print(f"Generated 25 test files covering all HVAC equipment types!")
    print("\nTo test decoder on all files:")
    print("  python3 test_universal_bms_decoder.py")

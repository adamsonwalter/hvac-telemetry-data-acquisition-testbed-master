#!/usr/bin/env python3
"""
Generate synthetic test files for all chiller load signal variations.
Uses the same timestamp pattern as the reference file.
"""

import numpy as np
import pandas as pd
from pathlib import Path

# Reference timestamp from the original file
BASE_TIMESTAMP = 1754609985  # First timestamp from BarTech file


def generate_realistic_load_pattern(n_points: int, seed: int = 42) -> np.ndarray:
    """
    Generate realistic chiller load pattern:
    - Long periods of 0 (chiller off)
    - Startup ramps
    - Variable load operation
    - Occasional peaks
    """
    np.random.seed(seed)
    
    load_plr = []
    i = 0
    
    while i < n_points:
        # Decide operational mode
        mode = np.random.choice(['off', 'startup', 'steady', 'peak'], p=[0.3, 0.1, 0.5, 0.1])
        
        if mode == 'off':
            # Chiller off
            duration = np.random.randint(50, 200)
            load_plr.extend([0.0] * duration)
            i += duration
            
        elif mode == 'startup':
            # Startup ramp
            duration = np.random.randint(10, 30)
            ramp = np.linspace(0.1, 0.3, duration)
            load_plr.extend(ramp)
            i += duration
            
        elif mode == 'steady':
            # Steady operation with variation
            duration = np.random.randint(30, 100)
            base_load = np.random.uniform(0.2, 0.5)
            variation = np.random.normal(0, 0.05, duration)
            steady = np.clip(base_load + variation, 0.1, 0.7)
            load_plr.extend(steady)
            i += duration
            
        elif mode == 'peak':
            # Peak load
            duration = np.random.randint(15, 40)
            base_load = np.random.uniform(0.5, 0.65)
            variation = np.random.normal(0, 0.03, duration)
            peak = np.clip(base_load + variation, 0.4, 0.7)
            load_plr.extend(peak)
            i += duration
    
    return np.array(load_plr[:n_points])


def generate_timestamps(n_points: int, interval_seconds: int = 60) -> np.ndarray:
    """Generate timestamps with variable intervals like real BMS data."""
    timestamps = [BASE_TIMESTAMP]
    
    for i in range(1, n_points):
        # Variable interval with occasional jumps (like real data)
        if np.random.random() < 0.05:
            # Occasional long gap
            jump = np.random.randint(3600, 7200)
        else:
            # Normal interval with slight variation
            jump = interval_seconds + np.random.randint(-5, 10)
        
        timestamps.append(timestamps[-1] + jump)
    
    return np.array(timestamps)


def create_test_file(
    filename: str,
    signal_type: str,
    n_points: int = 500,
    scaling_params: dict = None
):
    """
    Create a test CSV file for a specific signal type.
    
    Args:
        filename: Output filename
        signal_type: Type of signal (determines scaling)
        n_points: Number of data points
        scaling_params: Additional parameters for specific signal types
    """
    # Generate base load pattern (0-1 PLR)
    plr = generate_realistic_load_pattern(n_points)
    
    # Generate timestamps
    timestamps = generate_timestamps(n_points)
    
    # Apply scaling based on signal type
    if signal_type == "fraction_0_1":
        # 0-1 fraction (Carrier, York, Trane)
        values = plr
        
    elif signal_type == "percentage_0_100":
        # 0-100 percentage
        values = plr * 100
        
    elif signal_type == "counts_10000":
        # 0-10,000 counts (0.01% resolution) - Trend, Siemens, JCI
        values = plr * 10000
        
    elif signal_type == "counts_1000":
        # 0-1000 counts (0.1% resolution) - Older Schneider
        values = plr * 1000
        
    elif signal_type == "real_kw":
        # Real kW signal (requires nameplate)
        nameplate_kw = scaling_params.get("nameplate_kw", 1200)
        values = plr * nameplate_kw
        
    elif signal_type == "current_amps":
        # Current in Amps (requires nameplate for estimation)
        nameplate_kw = scaling_params.get("nameplate_kw", 1200)
        fla = nameplate_kw * 1.2  # Approx FLA
        values = plr * fla
        
    elif signal_type == "raw_adc_16bit":
        # Raw 16-bit ADC counts (0-65535)
        values = plr * 65535
        
    elif signal_type == "raw_adc_15bit":
        # Raw 15-bit ADC counts (0-32767)
        values = plr * 32767
        
    elif signal_type == "raw_counts_50000":
        # Arbitrary large counts
        values = plr * 50000
        
    elif signal_type == "weird_3276":
        # Bizarre custom scaling (0-3276.7)
        values = plr * 3276.7
        
    else:
        raise ValueError(f"Unknown signal type: {signal_type}")
    
    # Round to integers for count-based signals
    if signal_type in ["counts_10000", "counts_1000", "raw_adc_16bit", 
                       "raw_adc_15bit", "raw_counts_50000", "real_kw", "current_amps"]:
        values = np.round(values).astype(int)
    
    # Create DataFrame
    df = pd.DataFrame({
        "save_time": timestamps,
        "value": values
    })
    
    # Save to CSV
    output_path = Path(__file__).parent / filename
    df.to_csv(output_path, index=False)
    print(f"Generated: {output_path}")
    print(f"  - Signal type: {signal_type}")
    print(f"  - Points: {n_points}")
    print(f"  - Value range: {values.min():.2f} to {values.max():.2f}")
    print()


if __name__ == "__main__":
    print("Generating test files for all chiller load signal variations...")
    print("=" * 80)
    print()
    
    # Test case 1: 0-1 fraction (Carrier, York, Trane i-Vu)
    create_test_file(
        "Test_Carrier_Chiller_A_Load.csv",
        "fraction_0_1",
        n_points=500
    )
    
    # Test case 2: 0-100 percentage (most common)
    create_test_file(
        "Test_Standard_Chiller_B_Load.csv",
        "percentage_0_100",
        n_points=500
    )
    
    # Test case 3: 0-10,000 counts (Trend, Siemens, JCI)
    create_test_file(
        "Test_Trend_Chiller_C_Load.csv",
        "counts_10000",
        n_points=500
    )
    
    # Test case 4: 0-1000 counts (Older Schneider)
    create_test_file(
        "Test_Schneider_Chiller_D_Load.csv",
        "counts_1000",
        n_points=500
    )
    
    # Test case 5: Real kW signal
    create_test_file(
        "Test_RealKW_Chiller_E_Load.csv",
        "real_kw",
        n_points=500,
        scaling_params={"nameplate_kw": 1200}
    )
    
    # Test case 6: Current (Amps) signal
    create_test_file(
        "Test_Amps_Chiller_F_Load.csv",
        "current_amps",
        n_points=500,
        scaling_params={"nameplate_kw": 1200}
    )
    
    # Test case 7: Raw 16-bit ADC counts (0-65535)
    create_test_file(
        "Test_ADC16bit_Chiller_G_Load.csv",
        "raw_adc_16bit",
        n_points=500
    )
    
    # Test case 8: Raw 15-bit ADC counts (0-32767)
    create_test_file(
        "Test_ADC15bit_Chiller_H_Load.csv",
        "raw_adc_15bit",
        n_points=500
    )
    
    # Test case 9: Arbitrary large counts (0-50000)
    create_test_file(
        "Test_Counts50k_Chiller_I_Load.csv",
        "raw_counts_50000",
        n_points=500
    )
    
    # Test case 10: Bizarre custom scaling (edge case)
    create_test_file(
        "Test_Weird_Chiller_J_Load.csv",
        "weird_3276",
        n_points=500
    )
    
    print("=" * 80)
    print("All test files generated successfully!")
    print("\nTo test the decoder on all files, run:")
    print("  python universal_chiller_load_decoder.py <test_file.csv> [nameplate_kw]")

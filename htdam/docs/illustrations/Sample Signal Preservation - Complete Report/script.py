
import pandas as pd
import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

print("=" * 90)
print("REQUIREMENT 4: SIGNAL PRESERVATION - Hunting Detection & Transient Analysis")
print("=" * 90)

# Use the synchronized data from previous step
# Create it fresh for this analysis
chwst_df = pd.read_csv('BarTech_160_Ann_St_Level_22_MSSB_Chiller_2_CHWST_Leaving_Chilled_Water_Temperature_Sensor.csv')
chwrt_df = pd.read_csv('BarTech_160_Ann_St_Level_22_MSSB_Chiller_2_CHWRT_Entering_Chilled_Water_Temperature_Sensor.csv')
cdwrt_df = pd.read_csv('BarTech_160_Ann_St_Level_22_MSSB_Chiller_2_CDWRT_Entering_Condenser_Water_Temperature_Sensor.csv')

# Convert timestamps
chwst_df['timestamp'] = pd.to_datetime(chwst_df['save_time'], unit='s')
chwrt_df['timestamp'] = pd.to_datetime(chwrt_df['save_time'], unit='s')
cdwrt_df['timestamp'] = pd.to_datetime(cdwrt_df['save_time'], unit='s')

# Create indexed dataframes
chwst = chwst_df[['timestamp', 'value']].set_index('timestamp').sort_index()
chwrt = chwrt_df[['timestamp', 'value']].set_index('timestamp').sort_index()
cdwrt = cdwrt_df[['timestamp', 'value']].set_index('timestamp').sort_index()

# Remove exclusion window
exclusion_start = pd.Timestamp('2025-08-26 04:26:00')
exclusion_end = pd.Timestamp('2025-09-06 21:00:00')

chwst_filtered = chwst[(chwst.index < exclusion_start) | (chwst.index > exclusion_end)]
chwrt_filtered = chwrt[(chwrt.index < exclusion_start) | (chwrt.index > exclusion_end)]
cdwrt_filtered = cdwrt[(cdwrt.index < exclusion_start) | (cdwrt.index > exclusion_end)]

print("\n" + "─" * 90)
print("STEP 1: SPECTRAL ANALYSIS - FFT FOR HUNTING DETECTION")
print("─" * 90)

def detect_hunting_signal(df, stream_name, nominal_interval_sec=900):
    """
    Detect control hunting (guide vane oscillation) via FFT.
    Hunting periods: typically 100-600 seconds (1.6-10 minutes)
    Hunting frequency: 0.0017 Hz to 0.01 Hz
    """
    
    # Drop NaN values for FFT
    values = df['value'].dropna().values
    
    if len(values) < 100:
        print(f"{stream_name}: Insufficient data for FFT")
        return None
    
    # Detrend to remove warming/cooling trends
    values_detrended = signal.detrend(values, type='linear')
    
    # Compute FFT
    fft_result = np.fft.fft(values_detrended)
    
    # Frequency bins (1/Ts where Ts = interval in samples)
    freqs = np.fft.fftfreq(len(values), d=nominal_interval_sec)
    power = np.abs(fft_result) ** 2
    
    # Focus on positive frequencies only
    positive_freqs = freqs[:len(freqs)//2]
    positive_power = power[:len(power)//2]
    
    # Hunting frequency range: 0.001 Hz (1000 sec period) to 0.01 Hz (100 sec period)
    hunting_range = (positive_freqs >= 0.001) & (positive_freqs <= 0.015)
    
    if np.any(hunting_range):
        hunting_freqs = positive_freqs[hunting_range]
        hunting_power = positive_power[hunting_range]
        
        # Find dominant frequency in hunting range
        max_idx = np.argmax(hunting_power)
        dominant_freq = hunting_freqs[max_idx]
        dominant_power = hunting_power[max_idx]
        
        # Calculate power ratio (relative to max overall power)
        max_overall_power = np.max(positive_power)
        power_ratio = dominant_power / max_overall_power
        
        # Period corresponding to frequency
        if dominant_freq > 0:
            period_sec = 1 / dominant_freq
        else:
            period_sec = np.inf
        
        print(f"\n{stream_name}:")
        print(f"  Dominant hunting frequency: {dominant_freq:.4f} Hz")
        print(f"  Corresponding period: {period_sec:.1f} seconds ({period_sec/60:.1f} minutes)")
        print(f"  Power in hunting band: {power_ratio*100:.1f}% of total")
        
        # Detect if hunting is present
        if power_ratio > 0.05:  # >5% of power in hunting band
            hunting_detected = True
            hunting_severity = "HIGH" if power_ratio > 0.20 else "MODERATE" if power_ratio > 0.10 else "LOW"
        else:
            hunting_detected = False
            hunting_severity = "NONE"
        
        print(f"  Hunting Status: {hunting_severity} ({'DETECTED' if hunting_detected else 'NOT DETECTED'})")
        
        return {
            'stream': stream_name,
            'dominant_freq': dominant_freq,
            'period_sec': period_sec,
            'power_ratio': power_ratio,
            'detected': hunting_detected,
            'severity': hunting_severity,
            'confidence': 0.80 if power_ratio > 0.05 else 0.30
        }
    else:
        print(f"\n{stream_name}: No signals in hunting frequency range")
        return None

hunting_chwst = detect_hunting_signal(chwst_filtered, "CHWST")
hunting_chwrt = detect_hunting_signal(chwrt_filtered, "CHWRT")
hunting_cdwrt = detect_hunting_signal(cdwrt_filtered, "CDWRT")

print("\n" + "─" * 90)
print("STEP 2: TRANSIENT ANALYSIS - Startup Ramps & Load Changes")
print("─" * 90)

def analyze_transients(df, stream_name, window_size=96):
    """
    Detect rapid temperature changes (transients).
    Startup ramps, load steps, valve operations visible here.
    """
    
    values = df['value'].dropna().values
    
    # Calculate first differences (rates of change)
    diffs = np.diff(values)
    
    # Identify transients (>0.1°C per 15-min interval)
    transient_threshold = 0.1  # °C per interval
    transient_mask = np.abs(diffs) > transient_threshold
    
    n_transients = np.sum(transient_mask)
    transient_rate = n_transients / len(diffs) * 100
    
    # Largest transients
    largest_transients = np.argsort(np.abs(diffs))[-5:]
    
    print(f"\n{stream_name}:")
    print(f"  Transient Events (>0.1°C/interval): {n_transients} ({transient_rate:.2f}%)")
    print(f"  Largest rate changes (°C per 15-min):")
    for i, idx in enumerate(largest_transients[::-1]):
        print(f"    {i+1}. {diffs[idx]:+.3f}°C at record {idx}")
    
    # Startup ramp detection (sustained cooling from ~20°C to 6-8°C)
    max_cool_rate = np.min(diffs)  # Most negative = fastest cooling
    min_heat_rate = np.max(diffs)  # Most positive = fastest heating
    
    print(f"  Coolest ramp rate: {max_cool_rate:.3f}°C per 15-min")
    print(f"  Hottest ramp rate: {min_heat_rate:.3f}°C per 15-min")
    
    # Stability metric: standard deviation of diffs (low = stable, high = changing)
    stability_std = np.std(diffs)
    print(f"  Stability (std of rates): {stability_std:.4f}°C per 15-min")
    
    if stability_std < 0.05:
        stability = "EXCELLENT (steady operation)"
    elif stability_std < 0.10:
        stability = "GOOD"
    elif stability_std < 0.20:
        stability = "MODERATE (some control activity)"
    else:
        stability = "LOW (frequent adjustments)"
    
    print(f"  Operating Mode: {stability}")
    
    return {
        'stream': stream_name,
        'n_transients': n_transients,
        'transient_rate': transient_rate,
        'max_cool_rate': max_cool_rate,
        'max_heat_rate': min_heat_rate,
        'stability_std': stability_std,
        'stability_class': stability
    }

transient_chwst = analyze_transients(chwst_filtered, "CHWST")
transient_chwrt = analyze_transients(chwrt_filtered, "CHWRT")
transient_cdwrt = analyze_transients(cdwrt_filtered, "CDWRT")

print("\n" + "─" * 90)
print("STEP 3: DIURNAL PATTERN ANALYSIS")
print("─" * 90)

def extract_diurnal_pattern(df, stream_name):
    """
    Extract average daily pattern (heating/cooling cycles).
    Shows peak load times and setpoint variations.
    """
    
    df_copy = df.copy()
    df_copy['hour'] = df_copy.index.hour
    df_copy['month'] = df_copy.index.month
    
    # Hourly averages
    hourly = df_copy.groupby('hour')['value'].agg(['mean', 'std', 'min', 'max'])
    
    # Monthly variation (seasonal)
    monthly = df_copy.groupby('month')['value'].agg(['mean', 'std'])
    
    print(f"\n{stream_name}:")
    print(f"  Hourly Statistics (24-hour cycle):")
    print(f"    Peak (warmest hour): {hourly['mean'].max():.2f}°C (hour {hourly['mean'].idxmax()})")
    print(f"    Trough (coldest hour): {hourly['mean'].min():.2f}°C (hour {hourly['mean'].idxmin()})")
    print(f"    Daily range: {hourly['mean'].max() - hourly['mean'].min():.2f}°C")
    
    print(f"\n  Seasonal Statistics (monthly averages):")
    print(f"    Warmest month: {monthly['mean'].max():.2f}°C (month {monthly['mean'].idxmax()})")
    print(f"    Coldest month: {monthly['mean'].min():.2f}°C (month {monthly['mean'].idxmin()})")
    print(f"    Seasonal range: {monthly['mean'].max() - monthly['mean'].min():.2f}°C")
    
    # Identify control patterns
    if hourly['mean'].max() - hourly['mean'].min() < 1.0:
        pattern = "TIGHT CONTROL (±0.5°C setpoint hold)"
    elif hourly['mean'].max() - hourly['mean'].min() < 3.0:
        pattern = "MODERATE CONTROL (±1.5°C variation)"
    else:
        pattern = "LOOSE CONTROL or MULTI-SETPOINT OPERATION"
    
    print(f"  Control Pattern: {pattern}")
    
    return {
        'stream': stream_name,
        'peak_hour': hourly['mean'].idxmax(),
        'trough_hour': hourly['mean'].idxmin(),
        'daily_range': hourly['mean'].max() - hourly['mean'].min(),
        'seasonal_range': monthly['mean'].max() - monthly['mean'].min(),
        'control_pattern': pattern
    }

diurnal_chwst = extract_diurnal_pattern(chwst_filtered, "CHWST")
diurnal_chwrt = extract_diurnal_pattern(chwrt_filtered, "CHWRT")
diurnal_cdwrt = extract_diurnal_pattern(cdwrt_filtered, "CDWRT")

print("\n" + "=" * 90)
print("REQUIREMENT 4 FINDINGS SUMMARY")
print("=" * 90)

summary_data = {
    'Stream': ['CHWST', 'CHWRT', 'CDWRT'],
    'Hunting Detected': [
        hunting_chwst['detected'] if hunting_chwst else False,
        hunting_chwrt['detected'] if hunting_chwrt else False,
        hunting_cdwrt['detected'] if hunting_cdwrt else False
    ],
    'Transient Rate (%)': [
        transient_chwst['transient_rate'],
        transient_chwrt['transient_rate'],
        transient_cdwrt['transient_rate']
    ],
    'Daily Range (°C)': [
        diurnal_chwst['daily_range'],
        diurnal_chwrt['daily_range'],
        diurnal_cdwrt['daily_range']
    ],
    'Control Quality': [
        diurnal_chwst['control_pattern'],
        diurnal_chwrt['control_pattern'],
        diurnal_cdwrt['control_pattern']
    ]
}

summary_df = pd.DataFrame(summary_data)
print("\n" + summary_df.to_string(index=False))

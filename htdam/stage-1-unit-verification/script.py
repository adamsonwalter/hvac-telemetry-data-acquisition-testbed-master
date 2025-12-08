
import pandas as pd
import numpy as np
from scipy import stats
from scipy.optimize import minimize_scalar
from sklearn.mixture import GaussianMixture

# Load temperature data
chwst = pd.read_csv("BarTech_160_Ann_St_Level_22_MSSB_Chiller_2_CHWST_Leaving_Chilled_Water_Temperature_Sensor.csv")
chwrt = pd.read_csv("BarTech_160_Ann_St_Level_22_MSSB_Chiller_2_CHWRT_Entering_Chilled_Water_Temperature_Sensor.csv")

chwst['timestamp'] = pd.to_datetime(chwst['save_time'], unit='s')
chwrt['timestamp'] = pd.to_datetime(chwrt['save_time'], unit='s')
chwst.rename(columns={'value': 'CHWST'}, inplace=True)
chwrt.rename(columns={'value': 'CHWRT'}, inplace=True)

merged = pd.merge(chwst[['timestamp', 'CHWST']], chwrt[['timestamp', 'CHWRT']], on='timestamp', how='outer')
merged = merged.sort_values('timestamp').reset_index(drop=True)
paired = merged.dropna().copy()

print("=== METHODS TO DEFINE LOAD THRESHOLDS PER EQUIPMENT TYPE ===\n")
print(f"Dataset: {len(paired)} samples\n")

# Calculate Delta-T which serves as a proxy for load when actual load unavailable
paired['Delta_T'] = paired['CHWRT'] - paired['CHWST']
paired['abs_Delta_T'] = abs(paired['Delta_T'])
paired['physics_valid'] = paired['Delta_T'] >= 0

print("METHOD 1: DATA-DRIVEN THRESHOLD USING PHYSICS VIOLATION RATE")
print("=" * 70)
print("\nPrinciple: Find threshold where physics violations drop dramatically\n")

# Create bins of Delta_T and calculate violation rates
# Since we don't have actual load, we'll use abs_Delta_T as proxy
bins = np.percentile(paired['abs_Delta_T'], np.linspace(0, 100, 21))
paired['delta_bin'] = pd.cut(paired['abs_Delta_T'], bins=bins, include_lowest=True)

violation_by_bin = paired.groupby('delta_bin', observed=True).agg({
    'physics_valid': ['mean', 'count'],
    'abs_Delta_T': 'mean'
})
violation_by_bin.columns = ['validity_rate', 'sample_count', 'avg_delta_t']
violation_by_bin['violation_rate'] = 1 - violation_by_bin['validity_rate']
violation_by_bin = violation_by_bin[violation_by_bin['sample_count'] > 10]  # Sufficient samples

print("Violation Rate by Delta-T Level:")
print(violation_by_bin[['avg_delta_t', 'violation_rate', 'sample_count']].round(3))

# Find the "knee" in the curve - where violation rate drops sharply
violation_by_bin['violation_rate_smooth'] = violation_by_bin['violation_rate'].rolling(3, center=True).mean()

# Calculate rate of change
violation_by_bin['rate_change'] = violation_by_bin['violation_rate_smooth'].diff()

# Find maximum negative rate of change (steepest drop)
if len(violation_by_bin) > 3:
    knee_idx = violation_by_bin['rate_change'].idxmin()
    knee_threshold = violation_by_bin.loc[knee_idx, 'avg_delta_t']
    print(f"\n✓ KNEE POINT DETECTED: Delta_T ≈ {knee_threshold:.2f}°C")
    print(f"  This represents the transition from standby to active operation")
    print(f"  Violation rate at this point: {violation_by_bin.loc[knee_idx, 'violation_rate']*100:.1f}%")

print("\n\nMETHOD 2: BIMODAL DISTRIBUTION ANALYSIS")
print("=" * 70)
print("\nPrinciple: Find the valley between two operational modes\n")

# Fit Gaussian Mixture Model to identify modes
valid_deltas = paired[paired['abs_Delta_T'] > 0]['abs_Delta_T'].values.reshape(-1, 1)

# Try 2-component mixture
gmm = GaussianMixture(n_components=2, random_state=42)
gmm.fit(valid_deltas)

means = gmm.means_.flatten()
stds = np.sqrt(gmm.covariances_.flatten())
weights = gmm.weights_

print(f"Detected Modes:")
print(f"  Mode 1 (Low): mean={means[0]:.2f}°C, std={stds[0]:.2f}°C, weight={weights[0]:.1%}")
print(f"  Mode 2 (High): mean={means[1]:.2f}°C, std={stds[1]:.2f}°C, weight={weights[1]:.1%}")

# Threshold at intersection of two gaussians or at valley
# Valley is approximately at the point where the two distributions have equal probability
def mixture_pdf(x):
    """Negative mixture PDF for minimization"""
    pdf = 0
    for i in range(2):
        pdf += weights[i] * stats.norm.pdf(x, means[i], stds[i])
    return -pdf

# Find minimum between the two means
lower_bound = min(means)
upper_bound = max(means)
result = minimize_scalar(mixture_pdf, bounds=(lower_bound, upper_bound), method='bounded')
valley_threshold = result.x

print(f"\n✓ VALLEY THRESHOLD: {valley_threshold:.2f}°C")
print(f"  This is the natural boundary between operational modes")

# Alternative: Use mean of the two modes
midpoint_threshold = np.mean(means)
print(f"\n✓ MIDPOINT THRESHOLD: {midpoint_threshold:.2f}°C")
print(f"  Conservative choice between modes")

print("\n\nMETHOD 3: INFORMATION CONTENT OPTIMIZATION")
print("=" * 70)
print("\nPrinciple: Maximize separation of valid vs invalid data\n")

# For each potential threshold, calculate quality metrics
thresholds_test = np.percentile(paired['abs_Delta_T'], np.linspace(5, 95, 19))

results = []
for thresh in thresholds_test:
    below = paired[paired['abs_Delta_T'] <= thresh]
    above = paired[paired['abs_Delta_T'] > thresh]
    
    if len(below) > 10 and len(above) > 10:
        # Calculate separation metrics
        violation_below = (below['Delta_T'] < 0).mean()
        violation_above = (above['Delta_T'] < 0).mean()
        violation_diff = violation_below - violation_above
        
        # Calculate information gain (difference in standard deviation)
        std_below = below['Delta_T'].std()
        std_above = above['Delta_T'].std()
        std_ratio = std_above / std_below if std_below > 0 else 0
        
        # Calculate sample balance (avoid extreme splits)
        split_ratio = min(len(below), len(above)) / max(len(below), len(above))
        
        # Combined score: maximize violation separation and std ratio, prefer balanced splits
        score = violation_diff * std_ratio * (0.5 + 0.5 * split_ratio)
        
        results.append({
            'threshold': thresh,
            'violation_diff': violation_diff,
            'std_ratio': std_ratio,
            'split_ratio': split_ratio,
            'score': score,
            'pct_below': len(below) / len(paired) * 100
        })

results_df = pd.DataFrame(results)
best_idx = results_df['score'].idxmax()
optimal_threshold = results_df.loc[best_idx, 'threshold']

print(f"Tested {len(results_df)} thresholds from {thresholds_test.min():.2f} to {thresholds_test.max():.2f}°C")
print(f"\nTop 5 candidates:")
print(results_df.nlargest(5, 'score')[['threshold', 'violation_diff', 'std_ratio', 'pct_below', 'score']].round(3))

print(f"\n✓ OPTIMAL THRESHOLD: {optimal_threshold:.2f}°C")
print(f"  Maximizes separation between valid and invalid operational states")
print(f"  Violation difference: {results_df.loc[best_idx, 'violation_diff']:.1%}")
print(f"  STD ratio (active/standby): {results_df.loc[best_idx, 'std_ratio']:.2f}x")
print(f"  Split: {results_df.loc[best_idx, 'pct_below']:.1f}% below / {100-results_df.loc[best_idx, 'pct_below']:.1f}% above")

print("\n\nMETHOD 4: MANUFACTURER SPECIFICATIONS + SAFETY MARGIN")
print("=" * 70)
print("\nPrinciple: Use equipment turndown limits with operational safety margin\n")

manufacturer_specs = {
    'Chiller': {
        'typical_turndown': 0.10,  # 10% minimum
        'high_efficiency_turndown': 0.05,  # VFD chillers can go lower
        'safety_margin': 1.5,  # 50% above minimum for stable operation
        'typical_min_kw_ton': 0.5,  # kW/ton at minimum load
    },
    'Boiler': {
        'typical_turndown': 0.20,  # 20% minimum (worse than chillers)
        'high_efficiency_turndown': 0.15,  # Modulating burners
        'safety_margin': 1.3,
        'typical_min_efficiency': 0.65,  # Efficiency at minimum fire
    },
    'AHU_Fan': {
        'typical_turndown': 0.30,  # 30% minimum speed
        'vfd_turndown': 0.20,  # VFD allows lower
        'safety_margin': 1.2,
        'min_static_pressure': 0.2,  # inches w.c.
    },
    'Cooling_Tower': {
        'typical_turndown': 0.25,  # Fan speed
        'vfd_turndown': 0.15,
        'safety_margin': 1.3,
        'min_approach': 2.0,  # °F approach at low load
    }
}

print("Equipment Type        | Min Load | w/ Safety | Rationale")
print("-" * 70)
for equip, specs in manufacturer_specs.items():
    min_load = specs['typical_turndown'] * 100
    safe_threshold = specs['typical_turndown'] * specs['safety_margin'] * 100
    
    rationale = ""
    if equip == 'Chiller':
        rationale = "Below turndown: compressor cycling, oil return issues"
    elif equip == 'Boiler':
        rationale = "Below turndown: flame instability, condensation risk"
    elif equip == 'AHU_Fan':
        rationale = "Below turndown: stall region, control instability"
    elif equip == 'Cooling_Tower':
        rationale = "Below turndown: fan cycling, poor plume control"
    
    print(f"{equip:<20} | {min_load:>6.0f}%  | {safe_threshold:>7.1f}% | {rationale}")

print("\n✓ RECOMMENDED: Use safety_margin × manufacturer_minimum")
print("  Ensures equipment operates in stable, controllable region")
print("  For chillers: 10% × 1.5 = 15% threshold")
print("  For boilers: 20% × 1.3 = 26% threshold")

print("\n\nMETHOD 5: EMPIRICAL CALIBRATION FROM TIME-SERIES PATTERNS")
print("=" * 70)
print("\nPrinciple: Use temporal clustering to identify natural operational modes\n")

# Calculate rolling statistics to identify stable periods
window = 20
paired['rolling_mean_dt'] = paired['abs_Delta_T'].rolling(window, center=True).mean()
paired['rolling_std_dt'] = paired['abs_Delta_T'].rolling(window, center=True).std()

# Identify stable low-load periods (candidates for threshold)
stable_low = paired[
    (paired['rolling_std_dt'] < 0.3) &  # Stable
    (paired['rolling_mean_dt'] < 1.0)    # Low
]

stable_high = paired[
    (paired['rolling_std_dt'] > 0.5) &  # Variable
    (paired['rolling_mean_dt'] > 1.0)   # High
]

if len(stable_low) > 0 and len(stable_high) > 0:
    print(f"Stable Low Load Region: {len(stable_low)} samples")
    print(f"  Mean Delta_T: {stable_low['abs_Delta_T'].mean():.2f}°C")
    print(f"  95th percentile: {stable_low['abs_Delta_T'].quantile(0.95):.2f}°C")
    
    print(f"\nStable High Load Region: {len(stable_high)} samples")
    print(f"  Mean Delta_T: {stable_high['abs_Delta_T'].mean():.2f}°C")
    print(f"  5th percentile: {stable_high['abs_Delta_T'].quantile(0.05):.2f}°C")
    
    # Threshold as 95th percentile of low + 5% buffer
    empirical_threshold = stable_low['abs_Delta_T'].quantile(0.95) * 1.05
    
    print(f"\n✓ EMPIRICAL THRESHOLD: {empirical_threshold:.2f}°C")
    print(f"  Based on observed operational patterns")
    print(f"  Separates stable-low from variable-high regions")

print("\n\nMETHOD 6: CROSS-VALIDATION WITH AUXILIARY SIGNALS")
print("=" * 70)
print("\nPrinciple: When multiple signals available, find consensus threshold\n")

print("If load, flow, and power data available:")
print("  1. Calculate individual thresholds for each signal")
print("  2. Normalize to common scale (% of max or design)")
print("  3. Find threshold where MAJORITY of signals indicate 'active'")
print("  4. Use as cross-validated threshold")
print("\nExample consensus logic:")
print("  Active = (Load > threshold_L) + (Flow > threshold_F) + (Power > threshold_P) >= 2")
print("  This requires 2 of 3 signals to agree")
print("\nBenefits:")
print("  • Robust to single signal failure")
print("  • Handles sensor-specific issues")
print("  • Self-correcting if one signal has mapping error")

print("\n\nMETHOD 7: ADAPTIVE THRESHOLD USING QUANTILE REGRESSION")
print("=" * 70)
print("\nPrinciple: Threshold may vary by time, season, or building load\n")

# Group by hour to see if threshold should be time-dependent
paired['hour'] = paired['timestamp'].dt.hour
hourly_stats = paired.groupby('hour').agg({
    'abs_Delta_T': ['mean', 'std', 'median'],
    'physics_valid': 'mean'
})
hourly_stats.columns = ['mean_dt', 'std_dt', 'median_dt', 'validity_rate']

print("Hourly Statistics (sample):")
print(hourly_stats.head(10).round(3))

# Check if there's significant hourly variation
hourly_variation = hourly_stats['mean_dt'].std() / hourly_stats['mean_dt'].mean()
print(f"\nHourly variation coefficient: {hourly_variation:.2%}")

if hourly_variation > 0.3:
    print("  HIGH variation → Consider time-dependent thresholds")
    print("  Example: threshold_peak_hours = 1.5 × threshold_off_hours")
else:
    print("  LOW variation → Single global threshold sufficient")

print("\n\nMETHOD 8: BUSINESS RULE APPROACH")
print("=" * 70)
print("\nPrinciple: Define threshold based on operational/analytical objectives\n")

objectives = {
    'Maximize_Data_Quality': {
        'priority': 'Exclude all questionable data',
        'threshold_strategy': 'Conservative (high threshold)',
        'example': 'Use 25th percentile of active data',
        'tradeoff': 'Lose sample count but ensure validity'
    },
    'Maximize_Sample_Size': {
        'priority': 'Include maximum usable data',
        'threshold_strategy': 'Aggressive (low threshold)',
        'example': 'Use 95th percentile of standby data',
        'tradeoff': 'More samples but lower average quality'
    },
    'Balance_Quality_Quantity': {
        'priority': 'Optimize for statistical power',
        'threshold_strategy': 'Balanced (median approach)',
        'example': 'Use valley between modes',
        'tradeoff': 'Reasonable quality with adequate N'
    },
    'Match_Physics': {
        'priority': 'Align with thermodynamic reality',
        'threshold_strategy': 'Physics-based cutoff',
        'example': 'Minimum Delta_T for heat transfer: ~0.5°C',
        'tradeoff': 'Theoretically sound but may include noise'
    }
}

print("Objective              | Strategy        | Example                     | Tradeoff")
print("-" * 95)
for obj, details in objectives.items():
    print(f"{obj:<21} | {details['threshold_strategy']:<15} | {details['example']:<27} | {details['tradeoff']}")

print("\n✓ RECOMMENDATION: Define threshold based on analysis objective")
print("  Different use cases justify different thresholds")
print("  Document reasoning in metadata")

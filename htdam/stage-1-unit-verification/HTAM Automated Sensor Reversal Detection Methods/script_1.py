
# METHOD 6: State-Dependent Reversal Detection (the key insight from earlier)
print("\nMETHOD 6: STATE-DEPENDENT REVERSAL DETECTION")
print("=" * 60)
print("\nPrinciple: Some reversals are conditional on operational state\n")

# Create a synthetic operational state indicator based on absolute temps and variability
# High temps + high variability = likely active operation
paired['temp_level'] = (paired['CHWST'] + paired['CHWRT']) / 2
paired['temp_variability'] = abs(paired['CHWST'] - paired['CHWRT'])

# Use rolling statistics to identify operational periods
window = 20
paired['rolling_std_st'] = paired['CHWST'].rolling(window).std()
paired['rolling_std_rt'] = paired['CHWRT'].rolling(window).std()
paired['rolling_mean_dt'] = paired['Delta_T_as_labeled'].rolling(window).mean()

# Define operational states based on temperature characteristics
# State A: High variability, likely active cooling
# State B: Low variability, likely standby/transition

variability_threshold = paired['temp_variability'].quantile(0.7)
paired['inferred_state'] = 'Standby'
paired.loc[paired['temp_variability'] > variability_threshold, 'inferred_state'] = 'Active'

# Alternative: Use absolute temp levels (warmer = more likely correct operation)
temp_high_threshold = paired['temp_level'].quantile(0.6)
temp_low_threshold = paired['temp_level'].quantile(0.4)

paired['temp_state'] = 'Medium'
paired.loc[paired['temp_level'] > temp_high_threshold, 'temp_state'] = 'Warm'
paired.loc[paired['temp_level'] < temp_low_threshold, 'temp_state'] = 'Cool'

# Analyze violation rates by inferred state
print("Violation rates by inferred operational state:")
print("\nBy Temperature Variability State:")
state_analysis = paired.groupby('inferred_state').agg({
    'Delta_T_as_labeled': lambda x: (x < 0).sum(),
    'timestamp': 'count'
})
state_analysis.columns = ['Violations', 'Total']
state_analysis['Violation_Rate_%'] = (state_analysis['Violations'] / state_analysis['Total'] * 100).round(1)
print(state_analysis)

print("\nBy Temperature Level State:")
temp_state_analysis = paired.groupby('temp_state').agg({
    'Delta_T_as_labeled': lambda x: (x < 0).sum(),
    'timestamp': 'count',
    'temp_level': 'mean'
})
temp_state_analysis.columns = ['Violations', 'Total', 'Avg_Temp']
temp_state_analysis['Violation_Rate_%'] = (temp_state_analysis['Violations'] / temp_state_analysis['Total'] * 100).round(1)
print(temp_state_analysis)

# Test for state-dependency
violation_variance = state_analysis['Violation_Rate_%'].std()
print(f"\nVariance in violation rates across states: {violation_variance:.1f}%")
print(f"Interpretation:")
if violation_variance > 20:
    print(f"  HIGH variance ({violation_variance:.1f}%) → STRONG state-dependency detected")
    print(f"  Recommendation: Apply conditional swap logic based on operational state")
elif violation_variance > 10:
    print(f"  MODERATE variance ({violation_variance:.1f}%) → Possible state-dependency")
    print(f"  Recommendation: Investigate operational modes further")
else:
    print(f"  LOW variance ({violation_variance:.1f}%) → Consistent behavior across states")
    print(f"  Recommendation: Simple global swap or sensor malfunction")

# METHOD 7: Bi-modal Distribution Detection
print("\n\nMETHOD 7: BI-MODAL DISTRIBUTION DETECTION")
print("=" * 60)
print("\nPrinciple: State-dependent swaps create bi-modal Delta-T distributions\n")

# Analyze Delta-T histogram
dt_hist, dt_bins = np.histogram(paired['Delta_T_as_labeled'], bins=50)
dt_bin_centers = (dt_bins[:-1] + dt_bins[1:]) / 2

# Find peaks (local maxima)
from scipy.signal import find_peaks
peaks, properties = find_peaks(dt_hist, height=100, distance=5)

print(f"Number of significant peaks detected: {len(peaks)}")
if len(peaks) > 0:
    print(f"Peak locations (Delta-T values):")
    for i, peak_idx in enumerate(peaks):
        print(f"  Peak {i+1}: {dt_bin_centers[peak_idx]:.2f}°C (count: {dt_hist[peak_idx]})")

if len(peaks) >= 2:
    print(f"\n✓ BI-MODAL distribution detected")
    print(f"  This strongly suggests STATE-DEPENDENT reversal pattern")
    print(f"  One mode likely represents correct mapping, other represents swapped")
    
    # Identify the modes
    peak_locs = dt_bin_centers[peaks]
    negative_peaks = [p for p in peak_locs if p < 0]
    positive_peaks = [p for p in peak_locs if p > 0]
    
    if len(negative_peaks) > 0 and len(positive_peaks) > 0:
        print(f"\n  Negative mode (swapped): ~{negative_peaks[0]:.2f}°C")
        print(f"  Positive mode (correct): ~{positive_peaks[0]:.2f}°C")
else:
    print(f"\n✗ UNI-MODAL distribution")
    print(f"  Suggests consistent behavior (either always correct or always swapped)")

# Calculate bimodality coefficient
from scipy.stats import kurtosis
n = len(paired)
skewness = stats.skew(paired['Delta_T_as_labeled'])
kurt = kurtosis(paired['Delta_T_as_labeled'])
bimodality_coeff = (skewness**2 + 1) / (kurt + 3 * ((n-1)**2 / ((n-2)*(n-3))))

print(f"\nBimodality coefficient: {bimodality_coeff:.3f}")
print(f"  > 0.555: Suggests bimodal distribution")
print(f"  < 0.555: Suggests unimodal distribution")

if bimodality_coeff > 0.555:
    print(f"  Result: BIMODAL → State-dependent reversal likely")
else:
    print(f"  Result: UNIMODAL → Simple reversal or no reversal")

# METHOD 8: Temporal Pattern Analysis
print("\n\nMETHOD 8: TEMPORAL TRANSITION PATTERN ANALYSIS")
print("=" * 60)
print("\nPrinciple: Abrupt sign changes in Delta-T indicate state transitions\n")

# Detect transitions between positive and negative Delta-T
paired['dt_sign'] = np.sign(paired['Delta_T_as_labeled'])
paired['sign_change'] = (paired['dt_sign'] != paired['dt_sign'].shift(1)).astype(int)

total_transitions = paired['sign_change'].sum()
avg_samples_between_transitions = len(paired) / (total_transitions + 1)

print(f"Total sign transitions: {total_transitions}")
print(f"Average samples between transitions: {avg_samples_between_transitions:.1f}")
print(f"Transition frequency: {total_transitions / len(paired) * 100:.2f}% of samples")

if total_transitions > 100:
    print(f"\n✓ HIGH transition frequency → State-dependent reversal confirmed")
    print(f"  The system alternates between correct and swapped mappings")
elif total_transitions > 10:
    print(f"\n⚠ MODERATE transition frequency → Possible operational mode changes")
else:
    print(f"\n✗ LOW transition frequency → Likely consistent behavior")

# Analyze transition timing
paired['hour'] = paired['timestamp'].dt.hour
transition_samples = paired[paired['sign_change'] == 1]
if len(transition_samples) > 0:
    print(f"\nTransition timing analysis:")
    print(f"  Most common hours for transitions:")
    hourly_transitions = transition_samples['hour'].value_counts().head(5)
    print(hourly_transitions)

print("\n" + "=" * 60)
print("FINAL RECOMMENDATION MATRIX")
print("=" * 60)

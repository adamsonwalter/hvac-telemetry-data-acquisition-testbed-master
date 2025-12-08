
import pandas as pd
import numpy as np
from scipy import stats

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

print("=== AUTOMATED SENSOR REVERSAL DETECTION METHODS ===\n")
print(f"Dataset: {len(paired)} paired samples\n")

# METHOD 1: Statistical Distribution Analysis
print("METHOD 1: STATISTICAL DISTRIBUTION COMPARISON")
print("=" * 60)
print("\nPrinciple: Supply temp should have LOWER mean and HIGHER variance")
print("(Supply is actively controlled, return floats with building load)\n")

chwst_stats = {
    'mean': paired['CHWST'].mean(),
    'std': paired['CHWST'].std(),
    'min': paired['CHWST'].min(),
    'max': paired['CHWST'].max(),
    'range': paired['CHWST'].max() - paired['CHWST'].min()
}

chwrt_stats = {
    'mean': paired['CHWRT'].mean(),
    'std': paired['CHWRT'].std(),
    'min': paired['CHWRT'].min(),
    'max': paired['CHWRT'].max(),
    'range': paired['CHWRT'].max() - paired['CHWRT'].min()
}

print(f"CHWST (labeled 'Supply'): mean={chwst_stats['mean']:.2f}°C, std={chwst_stats['std']:.2f}°C, range={chwst_stats['range']:.2f}°C")
print(f"CHWRT (labeled 'Return'): mean={chwrt_stats['mean']:.2f}°C, std={chwrt_stats['std']:.2f}°C, range={chwrt_stats['range']:.2f}°C")

# Test 1A: Mean comparison
mean_test = "PASS" if chwst_stats['mean'] < chwrt_stats['mean'] else "FAIL"
print(f"\nTest 1A - Mean Relationship: {mean_test}")
print(f"  Expected: CHWST < CHWRT")
print(f"  Actual: {chwst_stats['mean']:.2f} vs {chwrt_stats['mean']:.2f}")
print(f"  Difference: {chwrt_stats['mean'] - chwst_stats['mean']:.2f}°C")

# Test 1B: Variance comparison (supply often has higher variance due to control action)
variance_ratio = chwst_stats['std'] / chwrt_stats['std']
print(f"\nTest 1B - Variance Ratio (CHWST/CHWRT): {variance_ratio:.2f}")
print(f"  Typical: 1.0-1.5 (supply may vary more with control)")
print(f"  Observed: {variance_ratio:.2f}")

# METHOD 2: Physical Constraint Violation Rate
print("\n\nMETHOD 2: PHYSICAL CONSTRAINT VIOLATION ANALYSIS")
print("=" * 60)
print("\nPrinciple: CHWRT must be ≥ CHWST (thermodynamic law)\n")

paired['Delta_T_as_labeled'] = paired['CHWRT'] - paired['CHWST']
paired['Delta_T_if_swapped'] = paired['CHWST'] - paired['CHWRT']

violations_as_labeled = (paired['Delta_T_as_labeled'] < 0).sum()
violations_if_swapped = (paired['Delta_T_if_swapped'] < 0).sum()

violation_rate_labeled = violations_as_labeled / len(paired) * 100
violation_rate_swapped = violations_if_swapped / len(paired) * 100

print(f"Violation Rate (as labeled):  {violation_rate_labeled:.1f}% ({violations_as_labeled} of {len(paired)})")
print(f"Violation Rate (if swapped):  {violation_rate_swapped:.1f}% ({violations_if_swapped} of {len(paired)})")

swap_recommendation = ""
if violation_rate_labeled > 20 and violation_rate_swapped < violation_rate_labeled * 0.3:
    swap_recommendation = "STRONG RECOMMENDATION: Swap labels"
elif violation_rate_labeled > 10 and violation_rate_swapped < 5:
    swap_recommendation = "MODERATE RECOMMENDATION: Investigate potential swap"
elif violation_rate_labeled < 5:
    swap_recommendation = "LABELS APPEAR CORRECT"
else:
    swap_recommendation = "INCONCLUSIVE: May have sensor issues beyond simple swap"

print(f"\nDECISION: {swap_recommendation}")

# METHOD 3: Delta-T Distribution Analysis
print("\n\nMETHOD 3: DELTA-T DISTRIBUTION SHAPE")
print("=" * 60)
print("\nPrinciple: Delta-T should be predominantly positive with right skew\n")

dt_mean_labeled = paired['Delta_T_as_labeled'].mean()
dt_median_labeled = paired['Delta_T_as_labeled'].median()
dt_skew_labeled = stats.skew(paired['Delta_T_as_labeled'])

dt_mean_swapped = paired['Delta_T_if_swapped'].mean()
dt_median_swapped = paired['Delta_T_if_swapped'].median()
dt_skew_swapped = stats.skew(paired['Delta_T_if_swapped'])

print(f"As Labeled:  mean={dt_mean_labeled:.3f}°C, median={dt_median_labeled:.3f}°C, skew={dt_skew_labeled:.3f}")
print(f"If Swapped:  mean={dt_mean_swapped:.3f}°C, median={dt_median_swapped:.3f}°C, skew={dt_skew_swapped:.3f}")

print(f"\nExpected characteristics for CORRECT labeling:")
print(f"  - Mean > 0.5°C (typical chiller Delta-T is 2-6°C)")
print(f"  - Median > 0")
print(f"  - Positive skew (occasional high Delta-T during low flow)")

score_labeled = 0
score_swapped = 0

if dt_mean_labeled > 0.5:
    score_labeled += 2
if dt_mean_swapped > 0.5:
    score_swapped += 2
    
if dt_median_labeled > 0:
    score_labeled += 1
if dt_median_swapped > 0:
    score_swapped += 1
    
if dt_skew_labeled > 0:
    score_labeled += 1
if dt_skew_swapped > 0:
    score_swapped += 1

print(f"\nDistribution Quality Score:")
print(f"  As Labeled: {score_labeled}/4")
print(f"  If Swapped: {score_swapped}/4")

# METHOD 4: Time-Lagged Cross-Correlation
print("\n\nMETHOD 4: TIME-LAGGED CROSS-CORRELATION")
print("=" * 60)
print("\nPrinciple: Return temp should LAG supply temp (thermal transport delay)\n")

# Calculate cross-correlation at different lags
max_lag = 10  # samples
correlations = []

for lag in range(-max_lag, max_lag + 1):
    if lag < 0:
        corr = paired['CHWST'].iloc[:lag].corr(paired['CHWRT'].iloc[-lag:])
    elif lag > 0:
        corr = paired['CHWST'].iloc[lag:].corr(paired['CHWRT'].iloc[:-lag])
    else:
        corr = paired['CHWST'].corr(paired['CHWRT'])
    correlations.append({'lag': lag, 'correlation': corr})

corr_df = pd.DataFrame(correlations)
max_corr_lag = corr_df.loc[corr_df['correlation'].idxmax(), 'lag']
max_corr_value = corr_df['correlation'].max()

print(f"Maximum correlation at lag: {max_corr_lag} samples")
print(f"Correlation value: {max_corr_value:.3f}")
print(f"\nInterpretation:")
if max_corr_lag > 0:
    print(f"  Return lags supply by {max_corr_lag} samples ✓ Expected")
elif max_corr_lag < 0:
    print(f"  Supply lags return by {abs(max_corr_lag)} samples ✗ Suggests swap or sensor issue")
else:
    print(f"  No lag detected - may indicate slow sampling or long averaging")

print(f"\nTop 5 correlations:")
print(corr_df.nlargest(5, 'correlation')[['lag', 'correlation']])

# METHOD 5: Percentile Analysis
print("\n\nMETHOD 5: PERCENTILE RELATIONSHIP ANALYSIS")
print("=" * 60)
print("\nPrinciple: Return should exceed supply across most percentiles\n")

percentiles = [10, 25, 50, 75, 90, 95, 99]
print(f"{'Percentile':<12} {'CHWST':<10} {'CHWRT':<10} {'CHWRT>CHWST':<12}")
print("-" * 44)

correct_count = 0
for p in percentiles:
    chwst_p = np.percentile(paired['CHWST'], p)
    chwrt_p = np.percentile(paired['CHWRT'], p)
    is_correct = "✓" if chwrt_p > chwst_p else "✗"
    if chwrt_p > chwst_p:
        correct_count += 1
    print(f"{p}th{'':<9} {chwst_p:<10.2f} {chwrt_p:<10.2f} {is_correct}")

percentile_score = correct_count / len(percentiles) * 100
print(f"\nPercentile Test Score: {percentile_score:.0f}% correct")
print(f"Expected: >80% for correct labeling")

test_result = "PASS" if percentile_score > 80 else "FAIL"
print(f"Result: {test_result}")

print("\n" + "=" * 60)
print("SUMMARY OF DETECTION METHODS")
print("=" * 60)

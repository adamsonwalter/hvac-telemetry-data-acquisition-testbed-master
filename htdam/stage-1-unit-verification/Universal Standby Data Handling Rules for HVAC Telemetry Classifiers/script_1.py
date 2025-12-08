
# Load the previously saved combined dataset
import pandas as pd
import numpy as np

combined = pd.read_csv('chiller2_combined_analysis.csv')
combined['timestamp'] = pd.to_datetime(combined['timestamp'])

print("=== DEVELOPING UNIVERSAL HVAC TELEMETRY VALIDATION RULES ===\n")

print("Dataset loaded: {} records\n".format(len(combined)))

print("1. PHYSICAL CONSTRAINT VIOLATIONS AS DIAGNOSTIC SIGNALS:\n")

print("For Chiller Systems:")
print("  Core Physical Law: CHWRT must be ≥ CHWST (return warmer than supply)")
print("  Violation indicates: Signal swap, sensor failure, or invalid data state\n")

print("Key Insight from Chiller 2 Analysis:")
print("  - Violation rate correlates with operational state (not random)")
print("  - Suggests: BMS state-dependent mapping error, not sensor malfunction")
print("  - Pattern: 73.3% violations at Load≤10% vs 1.2% at Load>10%")
print("  - Implication: Different data validity rules for different operational states\n")

print("2. GENERALIZED DATA QUALITY INDICATORS:\n")

# Calculate metrics for quality assessment
combined['has_valid_physics'] = combined['Delta_T'] >= 0
combined['has_operational_data'] = combined['load'] > 10

# Cross-tabulation of validity
validity_matrix = pd.crosstab(
    combined['has_operational_data'], 
    combined['has_valid_physics'],
    margins=True,
    normalize='index'
)
validity_matrix.index = ['Standby (Load≤10%)', 'Active (Load>10%)', 'All']
validity_matrix.columns = ['Physics Violated', 'Physics Valid', 'Total']

print("Data Validity by Operational State:")
print(validity_matrix.round(3))

print("\n3. OPERATIONAL STATE DETECTION METHODS:\n")

# Examine multiple indicators of operational state
print("Multiple concurrent indicators suggest 'real' vs 'placeholder' data:")
print("\nActive Operation Indicators:")
print(f"  Load > 10%: {(combined['load'] > 10).sum()} samples ({(combined['load'] > 10).mean()*100:.1f}%)")
print(f"  Flow > 10 L/s: {(combined['flow'] > 10).sum()} samples ({(combined['flow'] > 10).mean()*100:.1f}%)")  
print(f"  |Delta_T| > 0.5°C: {(abs(combined['Delta_T']) > 0.5).sum()} samples ({(abs(combined['Delta_T']) > 0.5).mean()*100:.1f}%)")
print(f"  Delta_T >= 0: {(combined['Delta_T'] >= 0).sum()} samples ({(combined['Delta_T'] >= 0).mean()*100:.1f}%)")

print("\nStandby/Invalid Indicators:")
print(f"  Load ≤ 10%: {(combined['load'] <= 10).sum()} samples ({(combined['load'] <= 10).mean()*100:.1f}%)")
print(f"  Flow ≤ 10 L/s: {(combined['flow'] <= 10).sum()} samples ({(combined['flow'] <= 10).mean()*100:.1f}%)")
print(f"  |Delta_T| < 0.5°C: {(abs(combined['Delta_T']) < 0.5).sum()} samples ({(abs(combined['Delta_T']) < 0.5).mean()*100:.1f}%)")
print(f"  Delta_T < 0: {(combined['Delta_T'] < 0).sum()} samples ({(combined['Delta_T'] < 0).mean()*100:.1f}%)")

print("\n4. MULTI-DIMENSIONAL VALIDITY SCORE:\n")

# Create composite validity score
combined['validity_score'] = 0

# Increment for each validity indicator
combined.loc[combined['load'] > 10, 'validity_score'] += 2  # Strong indicator
combined.loc[combined['flow'] > 5, 'validity_score'] += 2   # Strong indicator
combined.loc[combined['Delta_T'] >= 0, 'validity_score'] += 3  # Critical constraint
combined.loc[abs(combined['Delta_T']) > 0.5, 'validity_score'] += 1  # Meaningful load
combined.loc[combined['status'] == 1, 'validity_score'] += 1  # Enabled state

print("Validity Score Distribution:")
print(combined['validity_score'].value_counts().sort_index())

print("\nValidity Score vs Physical Correctness:")
score_analysis = combined.groupby('validity_score').agg({
    'has_valid_physics': ['sum', 'count', 'mean'],
    'load': 'mean',
    'flow': 'mean',
    'Delta_T': 'mean'
}).round(3)
score_analysis.columns = ['_'.join(col).strip() for col in score_analysis.columns.values]
print(score_analysis)

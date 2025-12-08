
# Analyze the broader pattern to develop universal rules
import pandas as pd
import numpy as np

print("=== DEVELOPING UNIVERSAL HVAC TELEMETRY VALIDATION RULES ===\n")

# Examine the physical constraints and patterns
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
active_data = combined[combined['load'] > 10]
print(f"  Load > threshold: {(combined['load'] > 10).sum()} samples")
print(f"  Flow > threshold: {(combined['flow'] > 10).sum()} samples")  
print(f"  |Delta_T| > 0.5°C: {(abs(combined['Delta_T']) > 0.5).sum()} samples")
print(f"  Temp range > 3°C: {((combined['CHWST'].rolling(10).max() - combined['CHWST'].rolling(10).min()) > 3).sum()} samples")

print("\nStandby/Invalid Indicators:")
standby_data = combined[combined['load'] <= 10]
print(f"  Load ≤ threshold: {(combined['load'] <= 10).sum()} samples")
print(f"  Flow ≤ threshold: {(combined['flow'] <= 10).sum()} samples")
print(f"  |Delta_T| ≤ 0.5°C: {(abs(combined['Delta_T']) <= 0.5).sum()} samples")
print(f"  Temp stability: {((combined['CHWST'].rolling(10).std()) < 0.1).sum()} samples")

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
print(score_analysis)

print("\n5. RECOMMENDED UNIVERSAL CLASSIFICATION FRAMEWORK:\n")

# Define classification tiers
def classify_data_quality(row):
    """Universal HVAC telemetry quality classifier"""
    score = 0
    reasons = []
    
    # Tier 1: Physical constraints (CRITICAL)
    if pd.notna(row['Delta_T']):
        if row['Delta_T'] < 0:
            reasons.append("Physics_Violation")
        else:
            score += 3
            
    # Tier 2: Operational state (HIGH)
    if pd.notna(row['load']) and row['load'] > 10:
        score += 2
        reasons.append("Active_Load")
    elif pd.notna(row['load']) and row['load'] <= 10:
        reasons.append("Standby_Mode")
        
    if pd.notna(row['flow']) and row['flow'] > 5:
        score += 2
        reasons.append("Active_Flow")
        
    # Tier 3: Signal quality (MEDIUM)
    if pd.notna(row['Delta_T']) and abs(row['Delta_T']) > 0.5:
        score += 1
        reasons.append("Meaningful_DeltaT")
        
    # Classification
    if score >= 6:
        return 'VALID_HIGH', score, reasons
    elif score >= 4:
        return 'VALID_MEDIUM', score, reasons
    elif score >= 2:
        return 'QUESTIONABLE', score, reasons
    else:
        return 'INVALID', score, reasons

combined[['quality_class', 'quality_score', 'quality_reasons']] = combined.apply(
    classify_data_quality, axis=1, result_type='expand'
)

print("Data Quality Classification Results:")
print(combined['quality_class'].value_counts())

print("\nQuality Class vs Physics Validity:")
quality_physics = pd.crosstab(
    combined['quality_class'],
    combined['has_valid_physics'],
    normalize='index'
)
quality_physics.columns = ['Physics_Violated_%', 'Physics_Valid_%']
print(quality_physics.round(3))

# Save the framework
framework_summary = combined.groupby('quality_class').agg({
    'has_valid_physics': 'mean',
    'load': ['mean', 'std'],
    'flow': ['mean', 'std'],
    'Delta_T': ['mean', 'std', 'count']
}).round(3)

framework_summary.to_csv('hvac_quality_framework.csv')
print("\n✓ Saved quality framework to hvac_quality_framework.csv")

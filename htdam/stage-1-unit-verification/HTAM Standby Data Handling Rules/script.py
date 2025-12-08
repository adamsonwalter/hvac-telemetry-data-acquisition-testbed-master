
import pandas as pd
import numpy as np

# Reload the temperature data to analyze standby patterns
chwst = pd.read_csv("BarTech_160_Ann_St_Level_22_MSSB_Chiller_2_CHWST_Leaving_Chilled_Water_Temperature_Sensor.csv")
chwrt = pd.read_csv("BarTech_160_Ann_St_Level_22_MSSB_Chiller_2_CHWRT_Entering_Chilled_Water_Temperature_Sensor.csv")

chwst['timestamp'] = pd.to_datetime(chwst['save_time'], unit='s')
chwrt['timestamp'] = pd.to_datetime(chwrt['save_time'], unit='s')
chwst.rename(columns={'value': 'CHWST'}, inplace=True)
chwrt.rename(columns={'value': 'CHWRT'}, inplace=True)

merged = pd.merge(chwst[['timestamp', 'CHWST']], chwrt[['timestamp', 'CHWRT']], on='timestamp', how='outer')
merged = merged.sort_values('timestamp').reset_index(drop=True)
paired = merged.dropna().copy()

print("=== STANDBY DATA HANDLING RULES FOR TELEMETRY CLASSIFIERS ===\n")
print(f"Dataset: {len(paired)} samples over {(paired['timestamp'].max() - paired['timestamp'].min()).days} days\n")

# ANALYSIS 1: Characterize standby data patterns
print("PART 1: IDENTIFYING STANDBY DATA CHARACTERISTICS")
print("=" * 70)

paired['Delta_T'] = paired['CHWRT'] - paired['CHWST']
paired['abs_Delta_T'] = abs(paired['Delta_T'])

# Use multiple indicators to identify standby periods
paired['is_low_delta'] = paired['abs_Delta_T'] < 0.5  # Minimal thermal transfer
paired['temp_avg'] = (paired['CHWST'] + paired['CHWRT']) / 2

# Rolling statistics to detect stable periods (characteristic of standby)
window = 10
paired['rolling_std_combined'] = ((paired['CHWST'].rolling(window).std() + 
                                   paired['CHWRT'].rolling(window).std()) / 2)
paired['is_stable'] = paired['rolling_std_combined'] < 0.2  # Very stable temps

# Detect invalid physics
paired['physics_violated'] = paired['Delta_T'] < 0

# Classify data quality
def classify_standby_state(row):
    """Multi-factor standby detection"""
    if pd.isna(row['rolling_std_combined']):
        return 'Unknown'
    
    # Strong indicators of standby
    if row['is_low_delta'] and row['is_stable'] and row['physics_violated']:
        return 'Standby_Invalid'
    elif row['is_low_delta'] and row['is_stable']:
        return 'Standby_Stable'
    elif row['physics_violated'] and row['is_low_delta']:
        return 'Standby_Questionable'
    elif not row['physics_violated'] and row['abs_Delta_T'] > 1.0:
        return 'Active_Valid'
    elif not row['physics_violated'] and row['abs_Delta_T'] > 0.5:
        return 'Active_LowLoad'
    else:
        return 'Transitional'

paired['state_classification'] = paired.apply(classify_standby_state, axis=1)

print("\nData Classification Distribution:")
classification_summary = paired['state_classification'].value_counts()
print(classification_summary)
print(f"\nPercentages:")
print((classification_summary / len(paired) * 100).round(1))

# ANALYSIS 2: Information content of standby data
print("\n\nPART 2: INFORMATION CONTENT ANALYSIS")
print("=" * 70)

standby_data = paired[paired['state_classification'].str.contains('Standby', na=False)]
active_data = paired[paired['state_classification'].str.contains('Active', na=False)]

print("\nStandby Data Characteristics:")
print(f"  Sample count: {len(standby_data)} ({len(standby_data)/len(paired)*100:.1f}%)")
print(f"  Physics violations: {(standby_data['physics_violated']).sum()} ({(standby_data['physics_violated']).mean()*100:.1f}%)")
print(f"  Avg Delta_T: {standby_data['Delta_T'].mean():.3f}°C (std: {standby_data['Delta_T'].std():.3f}°C)")
print(f"  Temperature range: {standby_data['temp_avg'].min():.1f} - {standby_data['temp_avg'].max():.1f}°C")
print(f"  Avg stability (rolling std): {standby_data['rolling_std_combined'].mean():.3f}°C")

print("\nActive Data Characteristics:")
print(f"  Sample count: {len(active_data)} ({len(active_data)/len(paired)*100:.1f}%)")
print(f"  Physics violations: {(active_data['physics_violated']).sum()} ({(active_data['physics_violated']).mean()*100:.1f}%)")
print(f"  Avg Delta_T: {active_data['Delta_T'].mean():.3f}°C (std: {active_data['Delta_T'].std():.3f}°C)")
print(f"  Temperature range: {active_data['temp_avg'].min():.1f} - {active_data['temp_avg'].max():.1f}°C")
print(f"  Avg stability (rolling std): {active_data['rolling_std_combined'].mean():.3f}°C")

print("\n\nKEY INSIGHT: Information Content Comparison")
print(f"  Active data Delta_T range: {active_data['Delta_T'].max() - active_data['Delta_T'].min():.2f}°C")
print(f"  Standby data Delta_T range: {standby_data['Delta_T'].max() - standby_data['Delta_T'].min():.2f}°C")
print(f"  Signal-to-noise ratio (Active/Standby std): {active_data['Delta_T'].std() / standby_data['Delta_T'].std():.2f}x")

# ANALYSIS 3: Use cases and handling strategies
print("\n\nPART 3: USE CASE DEPENDENT HANDLING STRATEGIES")
print("=" * 70)

use_cases = {
    'Use Case': [
        'Energy Efficiency Analysis',
        'Chiller Performance Calibration',
        'Demand Response Baseline',
        'Predictive Maintenance',
        'Fault Detection Training',
        'Equipment Scheduling',
        'Sensor Drift Detection',
        'Building Load Profiling',
        'Control Algorithm Training',
        'Carbon/Cost Attribution'
    ],
    'Include_Standby': [
        'NO',
        'NO',
        'CONDITIONAL',
        'YES',
        'YES',
        'YES',
        'YES',
        'CONDITIONAL',
        'NO',
        'NO'
    ],
    'Rationale': [
        'Standby has no cooling load; distorts efficiency metrics',
        'Invalid physics makes thermal models unreliable',
        'Include for baseline consumption; exclude for cooling baseline',
        'Standby-to-active transitions contain diagnostic info',
        'Failures often occur during state transitions',
        'Operating hours include standby; need full timeline',
        'Drift detection requires all data to identify bias patterns',
        'Peak demand occurs during active; standby inflates sample count',
        'Training data must represent real control scenarios',
        'Zero load periods have minimal energy cost'
    ]
}

use_case_df = pd.DataFrame(use_cases)
print("\n" + use_case_df.to_string(index=False))

# ANALYSIS 4: Quality scoring framework
print("\n\nPART 4: DATA QUALITY SCORING FRAMEWORK")
print("=" * 70)

def compute_quality_score(row, use_case_type='efficiency_analysis'):
    """
    Compute data quality score based on use case
    Returns: score (0-100), factors dict
    """
    score = 100
    factors = {}
    
    # Universal deductions
    if row['physics_violated']:
        score -= 50
        factors['physics_violation'] = -50
    
    if row['is_low_delta']:
        if use_case_type in ['efficiency_analysis', 'calibration', 'control_training']:
            score -= 30
            factors['low_information_content'] = -30
        else:
            score -= 10
            factors['low_signal'] = -10
    
    if row['is_stable']:
        if use_case_type in ['efficiency_analysis', 'calibration']:
            score -= 20
            factors['no_dynamic_behavior'] = -20
        elif use_case_type == 'drift_detection':
            score += 10  # Stability is good for drift detection
            factors['stable_baseline'] = +10
    
    # Positive factors
    if row['abs_Delta_T'] > 1.0 and not row['physics_violated']:
        score += 20
        factors['meaningful_load'] = +20
    
    if row['rolling_std_combined'] > 0.3:
        if use_case_type in ['efficiency_analysis', 'predictive_maintenance']:
            score += 10
            factors['dynamic_operation'] = +10
    
    return max(0, min(100, score)), factors

# Apply quality scoring for efficiency analysis use case
paired['quality_score_efficiency'] = paired.apply(
    lambda x: compute_quality_score(x, 'efficiency_analysis')[0], axis=1
)

paired['quality_score_maintenance'] = paired.apply(
    lambda x: compute_quality_score(x, 'predictive_maintenance')[0], axis=1
)

paired['quality_score_drift'] = paired.apply(
    lambda x: compute_quality_score(x, 'drift_detection')[0], axis=1
)

print("\nQuality Score Distributions by Use Case:")
print("\nFor EFFICIENCY ANALYSIS:")
print(paired['quality_score_efficiency'].describe())
print(f"  Samples with score ≥70 (usable): {(paired['quality_score_efficiency'] >= 70).sum()} ({(paired['quality_score_efficiency'] >= 70).mean()*100:.1f}%)")
print(f"  Samples with score <30 (discard): {(paired['quality_score_efficiency'] < 30).sum()} ({(paired['quality_score_efficiency'] < 30).mean()*100:.1f}%)")

print("\nFor PREDICTIVE MAINTENANCE:")
print(paired['quality_score_maintenance'].describe())
print(f"  Samples with score ≥70 (usable): {(paired['quality_score_maintenance'] >= 70).sum()} ({(paired['quality_score_maintenance'] >= 70).mean()*100:.1f}%)")

print("\nFor DRIFT DETECTION:")
print(paired['quality_score_drift'].describe())
print(f"  Samples with score ≥70 (usable): {(paired['quality_score_drift'] >= 70).sum()} ({(paired['quality_score_drift'] >= 70).mean()*100:.1f}%)")

print("\n\nQuality Score vs State Classification:")
quality_by_state = paired.groupby('state_classification').agg({
    'quality_score_efficiency': 'mean',
    'quality_score_maintenance': 'mean',
    'quality_score_drift': 'mean'
}).round(1)
quality_by_state.columns = ['Efficiency', 'Maintenance', 'Drift_Detection']
print(quality_by_state)

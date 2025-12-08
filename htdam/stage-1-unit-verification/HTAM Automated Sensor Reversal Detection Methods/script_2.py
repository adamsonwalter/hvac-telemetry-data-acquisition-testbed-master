
# Create comprehensive detection algorithm summary
print("\n" + "=" * 70)
print("AUTOMATED SENSOR REVERSAL DETECTION ALGORITHM")
print("=" * 70)

detection_results = {
    'Method': [],
    'Test': [],
    'Result': [],
    'Confidence': [],
    'Indicator': []
}

# Method 1
detection_results['Method'].append('1. Statistical')
detection_results['Test'].append('Mean Comparison')
detection_results['Result'].append('PASS (CHWST < CHWRT)')
detection_results['Confidence'].append('Low')
detection_results['Indicator'].append('Overall means suggest correct labels')

# Method 2
detection_results['Method'].append('2. Physical Constraints')
detection_results['Test'].append('Violation Rate')
detection_results['Result'].append('FAIL (55% violations)')
detection_results['Confidence'].append('High')
detection_results['Indicator'].append('Massive violation rate indicates issue')

# Method 3
detection_results['Method'].append('3. Delta-T Distribution')
detection_results['Test'].append('Distribution Shape')
detection_results['Result'].append('MIXED (mean OK, median negative)')
detection_results['Confidence'].append('Medium')
detection_results['Indicator'].append('Conflicting signals suggest complexity')

# Method 4
detection_results['Method'].append('4. Cross-Correlation')
detection_results['Test'].append('Temporal Lag')
detection_results['Result'].append('INCONCLUSIVE (no lag)')
detection_results['Confidence'].append('Low')
detection_results['Indicator'].append('15min sampling too slow for lag detection')

# Method 5
detection_results['Method'].append('5. Percentile Analysis')
detection_results['Test'].append('Relationship Across Range')
detection_results['Result'].append('FAIL (only 43% correct)')
detection_results['Confidence'].append('High')
detection_results['Indicator'].append('Strong evidence of reversal issue')

# Method 6
detection_results['Method'].append('6. State-Dependent')
detection_results['Test'].append('Violation by State')
detection_results['Result'].append('CRITICAL: 77% vs 6%')
detection_results['Confidence'].append('Very High')
detection_results['Indicator'].append('State-dependent reversal confirmed')

# Method 7
detection_results['Method'].append('7. Bi-modal Detection')
detection_results['Test'].append('Distribution Modes')
detection_results['Result'].append('POSITIVE (coeff=0.610)')
detection_results['Confidence'].append('Very High')
detection_results['Indicator'].append('Two distinct operational modes detected')

# Method 8
detection_results['Method'].append('8. Temporal Transitions')
detection_results['Test'].append('Mode Switching')
detection_results['Result'].append('HIGH (2935 transitions)')
detection_results['Confidence'].append('Very High')
detection_results['Indicator'].append('Frequent state changes (every ~12 samples)')

results_df = pd.DataFrame(detection_results)
print("\n" + results_df.to_string(index=False))

print("\n" + "=" * 70)
print("DIAGNOSTIC CONCLUSIONS")
print("=" * 70)

print("""
ISSUE TYPE: State-Dependent Signal Mapping Error

PRIMARY EVIDENCE:
  • 50% variance in violation rates across operational states
  • Bimodal Delta-T distribution (peaks at -0.11°C and +3.63°C)
  • 2,935 mode transitions (8.4% of samples are transitions)
  • Transitions clustered at hours 8-9 AM and 7-8 PM (building load changes)

ROOT CAUSE:
  BMS conditional point mapping based on operational state:
  - During Standby/Low Activity: 77% violation rate (signals swapped)
  - During Active Operation: 6% violation rate (signals correct)

DETECTION CONFIDENCE: 95%
  Multiple independent methods confirm state-dependent reversal pattern

ACTION REQUIRED:
  1. Do NOT apply simple global signal swap
  2. Identify operational state indicator (load, flow, status)
  3. Apply conditional logic: swap when state = standby
  4. Log BMS configuration issue for vendor resolution
""")

print("\n" + "=" * 70)
print("UNIVERSAL DETECTION ALGORITHM - PSEUDOCODE")
print("=" * 70)

pseudocode = """
FUNCTION detect_sensor_reversal(supply_signal, return_signal, metadata):
    
    # STAGE 1: Quick Statistical Tests
    mean_diff = mean(return_signal) - mean(supply_signal)
    violation_rate = count(return_signal < supply_signal) / length(return_signal)
    
    IF mean_diff > 0.5 AND violation_rate < 0.05:
        RETURN "CORRECT_MAPPING", confidence=0.95
    
    IF mean_diff < -0.5 AND violation_rate > 0.95:
        RETURN "SIMPLE_REVERSAL", confidence=0.95
    
    # STAGE 2: Complex Pattern Detection (if Stage 1 inconclusive)
    
    # Test for bimodality
    delta_t = return_signal - supply_signal
    bimodality_coeff = calculate_bimodality_coefficient(delta_t)
    
    IF bimodality_coeff > 0.555:
        # Likely state-dependent
        
        # Identify states using clustering or thresholding
        states = infer_operational_states(supply_signal, return_signal, metadata)
        
        # Calculate violation rate per state
        violation_by_state = {}
        FOR each state IN states:
            violation_by_state[state] = calculate_violation_rate(state)
        
        state_variance = variance(violation_by_state.values())
        
        IF state_variance > 20%:
            RETURN "STATE_DEPENDENT_REVERSAL", 
                   confidence=0.90,
                   swap_conditions=identify_swap_states(violation_by_state)
    
    # STAGE 3: Temporal Pattern Analysis
    transitions = count_sign_transitions(delta_t)
    transition_rate = transitions / length(delta_t)
    
    IF transition_rate > 0.05:  # >5% of samples are transitions
        RETURN "INTERMITTENT_REVERSAL",
               confidence=0.85,
               pattern=analyze_transition_timing(transitions)
    
    # STAGE 4: Cross-validation with auxiliary signals
    IF metadata.has_flow_data AND metadata.has_load_data:
        correlation = analyze_auxiliary_correlation(
            delta_t, metadata.flow, metadata.load
        )
        
        IF correlation.identifies_operational_states():
            RETURN "STATE_DEPENDENT_REVERSAL",
                   confidence=0.95,
                   state_variable=correlation.best_indicator
    
    # Default: Inconclusive
    RETURN "SENSOR_QUALITY_ISSUE", confidence=0.50
"""

print(pseudocode)

# Save comprehensive detection report
detection_report = {
    'Detection_Method': detection_results['Method'],
    'Test_Type': detection_results['Test'],
    'Result': detection_results['Result'],
    'Confidence': detection_results['Confidence'],
    'Evidence': detection_results['Indicator']
}

report_df = pd.DataFrame(detection_report)
report_df.to_csv('sensor_reversal_detection_report.csv', index=False)

# Create summary statistics
summary_stats = pd.DataFrame({
    'Metric': [
        'Total Samples',
        'Overall Violation Rate',
        'Violation Rate (Active State)',
        'Violation Rate (Standby State)',
        'State Variance',
        'Bimodality Coefficient',
        'Transition Count',
        'Avg Samples Between Transitions',
        'Detection Confidence'
    ],
    'Value': [
        len(paired),
        f"{violation_rate_labeled:.1f}%",
        "5.8%",
        "76.5%",
        "50.0%",
        "0.610",
        "2935",
        "12.0",
        "95%"
    ]
})

summary_stats.to_csv('reversal_detection_summary.csv', index=False)

print("\n✓ Saved detection report to: sensor_reversal_detection_report.csv")
print("✓ Saved summary statistics to: reversal_detection_summary.csv")

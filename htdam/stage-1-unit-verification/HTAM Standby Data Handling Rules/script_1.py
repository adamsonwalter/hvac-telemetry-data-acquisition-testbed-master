
# Create comprehensive rule framework document
print("\n" + "=" * 70)
print("UNIVERSAL STANDBY DATA HANDLING RULES")
print("=" * 70)

rules_framework = """

RULE 1: MANDATORY STANDBY CLASSIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ALL telemetry classifiers MUST categorize data into operational states:
  • Active_Valid: Equipment operating with valid physics (26.7%)
  • Active_LowLoad: Equipment operating at minimal capacity (7.7%)
  • Standby_Stable: Equipment idle, sensors showing stable values (6.4%)
  • Standby_Questionable: Equipment idle, sensors showing questionable values (28.2%)
  • Standby_Invalid: Equipment idle with physics violations (17.8%)
  • Transitional: Mode changes, startup/shutdown (13.1%)

Detection Criteria (Multi-Factor):
  ✓ |Delta_T| < 0.5°C        → Low thermal activity indicator
  ✓ Rolling_Std < 0.2°C      → Stability indicator (10-sample window)
  ✓ Delta_T < 0              → Physics violation flag
  ✓ Load ≤ 10%               → Equipment state (when available)
  ✓ Flow < design_minimum    → Flow state (when available)


RULE 2: USE-CASE DEPENDENT FILTERING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Thermal/Energy Analysis → EXCLUDE ALL STANDBY DATA
  • Efficiency calculations
  • COP/EER modeling
  • Chiller performance curves
  • Thermal load analysis
  • Control algorithm training
  
  Rationale: Standby has 7.86x LOWER signal-to-noise ratio
             Invalid physics makes thermal models unreliable
             Zero-load periods distort efficiency metrics

Predictive Maintenance → INCLUDE STANDBY DATA (with labels)
  • Failure prediction models
  • State transition analysis
  • Anomaly detection systems
  
  Rationale: Failures often occur during state transitions
             Abnormal standby behavior is diagnostic
             Need full operational timeline

Sensor Health Monitoring → INCLUDE STANDBY DATA
  • Drift detection
  • Calibration validation
  • Signal quality assessment
  
  Rationale: Consistent standby patterns establish sensor baseline
             Drift manifests across all operational states
             87.7% violation rate in standby reveals mapping errors

Operational Analytics → CONDITIONAL INCLUSION
  • Equipment scheduling: Include (need runtime vs idle time)
  • Demand response: Include for power baseline, exclude for cooling baseline
  • Load profiling: Exclude (standby inflates sample count, distorts peaks)


RULE 3: QUALITY SCORE METADATA TAGGING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Every sample MUST include use-case-specific quality scores (0-100):

Quality_Efficiency = 100
  - 50 if physics_violated
  - 30 if |Delta_T| < 0.5°C
  - 20 if rolling_std < 0.2°C
  + 20 if |Delta_T| > 1.0°C AND physics_valid

Quality_Maintenance = 100
  - 50 if physics_violated
  - 10 if |Delta_T| < 0.5°C
  + 10 if rolling_std > 0.3°C (dynamic behavior)

Quality_Drift = 100
  - 50 if physics_violated
  + 10 if rolling_std < 0.2°C (stable baseline desirable)

Thresholds:
  • Score ≥ 70: High quality, use directly
  • Score 40-69: Medium quality, use with caution or weighting
  • Score < 40: Low quality, exclude or use only for metadata


RULE 4: INFORMATION CONTENT ASSESSMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Quantitative metrics to assess standby data value:

Signal-to-Noise Ratio:
  SNR = std(Delta_T_active) / std(Delta_T_standby)
  
  This dataset: 1.401°C / 0.178°C = 7.86x
  
  Interpretation:
    SNR > 5.0   → Active data highly informative; standby adds noise
    SNR 2.0-5.0 → Moderate difference; weight appropriately
    SNR < 2.0   → Standby may contain useful information

Dynamic Range Ratio:
  DRR = range(Delta_T_active) / range(Delta_T_standby)
  
  This dataset: 9.22°C / 1.00°C = 9.22x
  
  Interpretation:
    DRR > 5.0   → Standby data lacks discriminative power
    DRR < 2.0   → Standby captures meaningful variation

Physics Violation Differential:
  PVD = violation_rate_standby - violation_rate_active
  
  This dataset: 87.7% - 0.0% = 87.7%
  
  Interpretation:
    PVD > 50%   → State-dependent data quality issue (CRITICAL)
    PVD 10-50%  → Sensor degradation during idle
    PVD < 10%   → Consistent sensor behavior


RULE 5: TEMPORAL CONTEXT PRESERVATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

When filtering standby data, PRESERVE temporal metadata:

Required Retention:
  • Timestamp of all filtered samples
  • State classification labels
  • Transition event markers
  • Duration of standby periods
  • Reason for exclusion

Enable downstream analysis:
  • Equipment runtime calculations
  • Duty cycle analysis
  • State transition frequency
  • Operational schedule validation

DO NOT:
  • Simply delete standby records without logging
  • Merge timestamps (creates false continuity)
  • Lose sample count information (affects statistical power)


RULE 6: TRANSITIONAL DATA HANDLING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Transitional samples (13.1% of data) require special treatment:

Characteristics:
  • Neither clearly active nor clearly standby
  • Often occur at mode boundaries
  • May show sensor lag effects
  • Can reveal control system behavior

Handling Strategy:
  1. Flag as "transitional" (do not classify as active or standby)
  2. Exclude from steady-state analysis
  3. INCLUDE for:
     - Control response analysis
     - System dynamics modeling
     - Fault detection at startup/shutdown
  4. Buffer transitions: exclude ±5 samples around state changes


RULE 7: MULTI-EQUIPMENT CONSISTENCY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

In multi-chiller/multi-equipment systems:

Cross-Equipment Validation:
  • If Chiller 1 shows active, Chiller 2 standby should be valid
  • System-level load should sum to individual equipment loads
  • Lead equipment should show higher active percentage than lag

Standby Definition Consistency:
  • Apply same criteria across all equipment of same type
  • Document equipment-specific thresholds (if different)
  • Justify differences (e.g., different capacity, vintage, control)

Lead/Lag State Tracking:
  • Tag which equipment is lead vs lag at each timestamp
  • Standby data quality differs by role:
    * Lead standby: Unusual, may indicate system issue
    * Lag standby: Normal, expected during low load


RULE 8: DOCUMENTATION AND PROVENANCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Every filtered dataset MUST include metadata file:

Required Documentation:
  • Total samples (original count)
  • Active samples (count and %)
  • Standby samples excluded (count and %)
  • Transitional samples (count and %)
  • Unknown/unclassified (count and %)
  • Classification criteria used
  • Quality score thresholds applied
  • Use case specified
  • Filter decision rationale

Enable Reproducibility:
  • Exact filtering logic (with code/pseudocode)
  • Library versions (if using algorithms)
  • Manual overrides documented
  • Date of processing
  • Analyst/system identifier

"""

print(rules_framework)

# Create a decision tree structure
print("\n" + "=" * 70)
print("DECISION TREE: SHOULD I INCLUDE STANDBY DATA?")
print("=" * 70)

decision_tree = """

START → What is your analysis objective?
  │
  ├─→ Thermal/Energy Analysis (efficiency, COP, calibration)
  │   │
  │   └─→ EXCLUDE standby data
  │       Rationale: Physics violations + low signal-to-noise
  │       Quality Score Threshold: ≥70 (only 38.1% of samples pass)
  │
  ├─→ Predictive Maintenance / Fault Detection
  │   │
  │   ├─→ Does your model need state transitions?
  │   │   ├─→ YES → INCLUDE standby WITH labels
  │   │   │         Mark: state='standby', quality_score (medium)
  │   │   │
  │   │   └─→ NO  → EXCLUDE standby, keep only active
  │   │             Focus on operational degradation patterns
  │   │
  │   └─→ Are you detecting sensor failures?
  │       └─→ YES → INCLUDE standby (critical for this case!)
  │                 87.7% violation rate reveals sensor mapping error
  │
  ├─→ Sensor Health / Drift Detection
  │   │
  │   └─→ INCLUDE ALL standby data
  │       Rationale: Need baseline across all states
  │       Drift manifests universally, not just during active operation
  │
  ├─→ Control Algorithm Training
  │   │
  │   ├─→ Are you training for setpoint tracking?
  │   │   └─→ YES → EXCLUDE standby
  │   │             Control doesn't operate during standby
  │   │
  │   ├─→ Are you training for mode switching?
  │   │   └─→ YES → INCLUDE standby + transitional data
  │   │             Mode logic requires full state space
  │   │
  │   └─→ Are you training for optimal scheduling?
  │       └─→ YES → INCLUDE standby as "off" state
  │                 Scheduler needs to know idle state exists
  │
  ├─→ Operational Analytics
  │   │
  │   ├─→ Equipment Runtime / Duty Cycle
  │   │   └─→ INCLUDE standby (labeled as idle time)
  │   │
  │   ├─→ Peak Load / Demand Analysis
  │   │   └─→ EXCLUDE standby (distorts peak identification)
  │   │
  │   └─→ Energy Cost Attribution
  │       └─→ CONDITIONAL:
  │           - Include standby for parasitic/auxiliary load
  │           - Exclude standby for cooling energy calculation
  │
  └─→ Baseline / Benchmarking
      │
      ├─→ Comparing to design specifications?
      │   └─→ EXCLUDE standby (design specs are for rated operation)
      │
      ├─→ Comparing to peer equipment?
      │   └─→ NORMALIZE by active hours, exclude standby
      │         Or: report metrics separately for active vs standby
      │
      └─→ Regulatory compliance reporting?
          └─→ CHECK STANDARD:
              - ASHRAE 90.1: Exclude standby from efficiency calcs
              - ISO 50001: Include for total energy accounting
              - LEED: Depends on credit (document your choice)

"""

print(decision_tree)

# Save comprehensive framework
framework_doc = pd.DataFrame({
    'Rule_Number': [1, 2, 3, 4, 5, 6, 7, 8],
    'Rule_Name': [
        'Mandatory Classification',
        'Use-Case Filtering',
        'Quality Score Tagging',
        'Information Content Assessment',
        'Temporal Context Preservation',
        'Transitional Data Handling',
        'Multi-Equipment Consistency',
        'Documentation & Provenance'
    ],
    'Compliance': [
        'REQUIRED',
        'REQUIRED',
        'REQUIRED',
        'RECOMMENDED',
        'REQUIRED',
        'RECOMMENDED',
        'CONDITIONAL',
        'REQUIRED'
    ],
    'Impact_If_Violated': [
        'Undetected data quality issues',
        'Invalid analysis results',
        'Inability to filter appropriately',
        'Suboptimal data utilization',
        'Loss of operational context',
        'Startup/shutdown artifacts in analysis',
        'Cross-equipment analysis failures',
        'Non-reproducible results'
    ]
})

framework_doc.to_csv('standby_data_handling_rules.csv', index=False)
print("\n✓ Saved framework to: standby_data_handling_rules.csv")

# Create example implementation
print("\n" + "=" * 70)
print("EXAMPLE: PYTHON IMPLEMENTATION PATTERN")
print("=" * 70)

example_code = """
class StandbyClassifier:
    '''Universal HVAC telemetry standby detection and quality scoring'''
    
    def __init__(self, equipment_type='chiller', use_case='efficiency_analysis'):
        self.equipment_type = equipment_type
        self.use_case = use_case
        self.thresholds = self._get_thresholds()
    
    def _get_thresholds(self):
        '''Equipment-specific thresholds'''
        thresholds = {
            'chiller': {
                'delta_t_min': 0.5,  # °C
                'stability_max': 0.2,  # rolling std °C
                'load_min': 10,  # %
                'flow_min_pct': 10  # % of design
            },
            'boiler': {
                'delta_t_min': 1.0,
                'stability_max': 0.3,
                'load_min': 15,
                'flow_min_pct': 15
            }
        }
        return thresholds.get(self.equipment_type, thresholds['chiller'])
    
    def classify_operational_state(self, df):
        '''Multi-factor state classification'''
        
        # Calculate indicators
        df['abs_delta_t'] = abs(df['delta_t'])
        df['is_low_delta'] = df['abs_delta_t'] < self.thresholds['delta_t_min']
        df['rolling_std'] = df['supply_temp'].rolling(10).std()
        df['is_stable'] = df['rolling_std'] < self.thresholds['stability_max']
        df['physics_violated'] = df['delta_t'] < 0
        
        # Classification logic
        conditions = [
            (df['is_low_delta'] & df['is_stable'] & df['physics_violated']),
            (df['is_low_delta'] & df['is_stable'] & ~df['physics_violated']),
            (df['is_low_delta'] & df['physics_violated']),
            (~df['physics_violated'] & (df['abs_delta_t'] > 1.0)),
            (~df['physics_violated'] & (df['abs_delta_t'] > 0.5)),
        ]
        
        labels = [
            'Standby_Invalid',
            'Standby_Stable',
            'Standby_Questionable',
            'Active_Valid',
            'Active_LowLoad'
        ]
        
        df['state'] = np.select(conditions, labels, default='Transitional')
        return df
    
    def compute_quality_scores(self, df):
        '''Use-case specific quality scoring'''
        
        scores = pd.DataFrame(index=df.index)
        
        # Base score
        scores['efficiency'] = 100
        scores['maintenance'] = 100
        scores['drift'] = 100
        
        # Deductions
        scores.loc[df['physics_violated'], 'efficiency'] -= 50
        scores.loc[df['physics_violated'], 'maintenance'] -= 50
        scores.loc[df['physics_violated'], 'drift'] -= 50
        
        scores.loc[df['is_low_delta'], 'efficiency'] -= 30
        scores.loc[df['is_low_delta'], 'maintenance'] -= 10
        
        scores.loc[df['is_stable'], 'efficiency'] -= 20
        scores.loc[df['is_stable'], 'drift'] += 10
        
        # Bonuses
        good_signal = (~df['physics_violated']) & (df['abs_delta_t'] > 1.0)
        scores.loc[good_signal, 'efficiency'] += 20
        scores.loc[good_signal, 'maintenance'] += 20
        
        # Clip to valid range
        return scores.clip(0, 100)
    
    def filter_for_use_case(self, df):
        '''Apply use-case appropriate filtering'''
        
        filters = {
            'efficiency_analysis': df['quality_score_efficiency'] >= 70,
            'calibration': df['state'].str.contains('Active'),
            'predictive_maintenance': df['quality_score_maintenance'] >= 40,
            'drift_detection': True,  # Keep all
            'control_training': df['state'].str.contains('Active'),
            'scheduling': True,  # Keep all with labels
        }
        
        mask = filters.get(self.use_case, True)
        
        # Log filtering stats
        self._log_filter_stats(df, mask)
        
        return df[mask].copy()
    
    def _log_filter_stats(self, df, mask):
        '''Document filtering decisions'''
        stats = {
            'total_samples': len(df),
            'kept_samples': mask.sum() if isinstance(mask, pd.Series) else len(df),
            'excluded_samples': len(df) - (mask.sum() if isinstance(mask, pd.Series) else 0),
            'state_distribution': df['state'].value_counts().to_dict(),
            'use_case': self.use_case,
            'timestamp': pd.Timestamp.now()
        }
        # Save to metadata file
        with open(f'filter_log_{self.use_case}.json', 'w') as f:
            json.dump(stats, f, indent=2, default=str)

# Usage example:
classifier = StandbyClassifier(use_case='efficiency_analysis')
df = classifier.classify_operational_state(df)
df[['quality_score_efficiency', 'quality_score_maintenance', 'quality_score_drift']] = \\
    classifier.compute_quality_scores(df)
df_filtered = classifier.filter_for_use_case(df)
"""

print(example_code)
print("\n✓ Complete framework with implementation example generated")

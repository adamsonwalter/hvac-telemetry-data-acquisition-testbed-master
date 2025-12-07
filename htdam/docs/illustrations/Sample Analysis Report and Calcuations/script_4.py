
print("\n--- STEP 2: Classify Gap Types ---\n")

def classify_gaps_v2(df, gaps_series, stream_name):
    """Classify the reason for each gap on raw data (before sync)."""
    
    classifications = []
    
    for idx in gaps_series.index:
        # Find position in dataframe
        pos = list(df.index).index(idx)
        
        if pos > 0 and pos < len(df) - 1:
            value_before = df.iloc[pos - 1, 0]  # Get temperature value
            value_after = df.iloc[pos + 1, 0]
            gap_duration = gaps_series[idx]
            
            # Classify based on value change during gap
            value_change = abs(value_after - value_before)
            
            if value_change < 0.1:
                gap_type = "COV_CONSTANT"  # Value barely changed during gap
                confidence = 0.90
                reason = "Change-of-Value: setpoint held constant"
            elif value_change < 0.5:
                gap_type = "COV_MINOR"  # Small gradual change
                confidence = 0.75
                reason = "Small transient through gap"
            elif gap_duration > 3600:  # > 1 hour
                gap_type = "SYSTEM_OFFLINE"  # Long gap = likely system off
                confidence = 0.85
                reason = "System maintenance/shutdown window"
            else:
                gap_type = "SENSOR_ANOMALY"
                confidence = 0.60
                reason = "Unexpected sensor behavior"
            
            classifications.append({
                'gap_time': idx,
                'duration_hr': gap_duration / 3600,
                'value_before': value_before,
                'value_after': value_after,
                'value_change': value_change,
                'type': gap_type,
                'confidence': confidence,
                'reason': reason
            })
    
    if len(classifications) > 0:
        gap_table = pd.DataFrame(classifications)
        
        print(f"{stream_name}:")
        print(f"  Total gaps: {len(gap_table)}\n")
        
        for gap_type in gap_table['type'].unique():
            subset = gap_table[gap_table['type'] == gap_type]
            count = len(subset)
            avg_dur = subset['duration_hr'].mean()
            print(f"  {gap_type}: {count} gaps, avg {avg_dur:.1f} hours")
        
        print(f"\n  ⚠ Critical gaps (should be EXCLUDED from analysis):")
        critical = gap_table[gap_table['type'] == 'SYSTEM_OFFLINE']
        for _, row in critical.iterrows():
            print(f"    {row['gap_time'].strftime('%Y-%m-%d %H:%M')}: {row['duration_hr']:.1f} hours (conf {row['confidence']:.0%})")
        
        print(f"\n  ✓ Recoverable gaps (COV-like): Can be forward-filled with metadata")
        recoverable = gap_table[gap_table['type'].isin(['COV_CONSTANT', 'COV_MINOR'])]
        for _, row in recoverable.iterrows():
            print(f"    {row['gap_time'].strftime('%Y-%m-%d %H:%M')}: {row['duration_hr']:.2f} hours, ΔT={row['value_change']:.3f}°C")
        
        return gap_table
    else:
        print(f"{stream_name}: No gaps to classify ✓")
        return pd.DataFrame()

gaps_chwst_class = classify_gaps_v2(chwst, gaps_chwst, "CHWST")
print()
gaps_chwrt_class = classify_gaps_v2(chwrt, gaps_chwrt, "CHWRT")
print()
gaps_cdwrt_class = classify_gaps_v2(cdwrt, gaps_cdwrt, "CDWRT")

print("\n" + "=" * 80)
print("--- STEP 3: GAP RESOLUTION STRATEGY ---\n")

print("For each gap type:")
print("""
  • COV_CONSTANT (value unchanged):
    └─ Forward-fill the missing period with last known value
    └─ Mark as "COV: setpoint held" (HIGH confidence for statistics)
    └─ Confidence penalty: 0.0 (intentional sparsity, not missing data)

  • COV_MINOR (value changed <0.5°C during gap):
    └─ Linear interpolation between before/after values
    └─ Mark as "COV: interpolated transient"
    └─ Confidence penalty: -0.10 (minor uncertainty)

  • SYSTEM_OFFLINE (>1 hour gap, usually multi-hour):
    └─ DO NOT FILL - mark as exclusion window
    └─ Exclude from all statistical analysis
    └─ Confidence penalty: -0.30 (unreliable period)
    └─ Audit note: "Chiller offline 2025-08-26 04:27 to 2025-08-28 21:07"
""")

print("\nGap Resolution Summary:")
print("─" * 80)

total_records_pre = len(chwst) + len(chwrt) + len(cdwrt)
print(f"\nBefore gap resolution: {total_records_pre} total records across 3 streams")

# Count by type
all_gaps = pd.concat([
    gaps_chwst_class.assign(stream='CHWST'),
    gaps_chwrt_class.assign(stream='CHWRT'),
    gaps_cdwrt_class.assign(stream='CDWRT')
], ignore_index=True)

if len(all_gaps) > 0:
    for gap_type in all_gaps['type'].unique():
        subset = all_gaps[all_gaps['type'] == gap_type]
        count = len(subset)
        total_time = subset['duration_hr'].sum()
        print(f"  {gap_type}: {count} gaps totaling {total_time:.0f} hours")

print(f"\nExclusion Windows (SYSTEM_OFFLINE):")
if len(all_gaps) > 0:
    offline = all_gaps[all_gaps['type'] == 'SYSTEM_OFFLINE']
    if len(offline) > 0:
        for _, row in offline.sort_values('gap_time').iterrows():
            gap_end = row['gap_time'] + pd.Timedelta(hours=row['duration_hr'])
            print(f"  • {row['stream']}: {row['gap_time'].strftime('%Y-%m-%d %H:%M')} to {gap_end.strftime('%Y-%m-%d %H:%M')} ({row['duration_hr']:.1f}h)")
    else:
        print("  (None detected)")

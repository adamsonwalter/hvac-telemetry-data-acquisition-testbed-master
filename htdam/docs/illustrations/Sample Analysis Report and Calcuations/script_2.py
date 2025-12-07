
print("\n" + "=" * 80)
print("REQUIREMENT 3: GAP DETECTION & RESOLUTION (BEFORE SYNC)")
print("=" * 80)

# Set index to timestamps
chwst = chwst_df.set_index('timestamp').sort_index()
chwrt = chwrt_df.set_index('timestamp').sort_index()
cdwrt = cdwrt_df.set_index('timestamp').sort_index()

print("\n--- STEP 1: Detect Gaps via Time Interval Analysis ---\n")

def analyze_gaps(df, stream_name):
    """Detect gaps in a stream."""
    time_diffs = df.index.to_series().diff().dt.total_seconds()
    
    # Nominal interval detection
    median_interval = time_diffs.median()
    nominal_interval = round(median_interval / 10) * 10  # Round to nearest 10 sec
    
    # Find gaps (intervals > 2x nominal)
    gap_threshold = nominal_interval * 2.0
    gaps = time_diffs[time_diffs > gap_threshold]
    
    print(f"{stream_name}:")
    print(f"  Total records: {len(df)}")
    print(f"  Time range: {df.index[0]} to {df.index[-1]}")
    print(f"  Nominal interval: {nominal_interval:.0f} sec ({nominal_interval/60:.1f} min)")
    print(f"  Jitter std dev: {time_diffs.std():.2f} sec")
    print(f"  Gaps detected (>2× nominal): {len(gaps)}")
    
    if len(gaps) > 0:
        print(f"    Largest gap: {gaps.max():.0f} sec ({gaps.max()/3600:.2f} hours)")
        print(f"    Smallest gap: {gaps.min():.0f} sec ({gaps.min()/60:.1f} min)")
        print(f"    Total time lost to gaps: {gaps.sum()/3600:.1f} hours")
    else:
        print(f"    No gaps detected ✓")
    
    print(f"  Jitter coefficient of variation: {time_diffs.std() / nominal_interval:.3f} ({time_diffs.std() / nominal_interval * 100:.1f}%)")
    
    return gaps, nominal_interval, time_diffs

gaps_chwst, nominal_chwst, diffs_chwst = analyze_gaps(chwst, "CHWST")
print()
gaps_chwrt, nominal_chwrt, diffs_chwrt = analyze_gaps(chwrt, "CHWRT")
print()
gaps_cdwrt, nominal_cdwrt, diffs_cdwrt = analyze_gaps(cdwrt, "CDWRT")

print("\n--- STEP 2: Classify Gap Types (COV vs Sensor Fault vs System Offline) ---\n")

def classify_gaps(df, gaps_series, stream_name):
    """Classify the reason for each gap."""
    
    classifications = []
    
    for idx in gaps_series.index:
        # Get value before and after gap
        pos = df.index.get_loc(idx)
        if pos > 0 and pos < len(df) - 1:
            value_before = df.iloc[pos - 1, 0]
            value_after = df.iloc[pos + 1, 0]
            gap_duration = gaps_series[idx]
            
            # Classify
            value_change = abs(value_after - value_before)
            
            if value_change < 0.05:
                gap_type = "COV_UNCHANGED"  # Change of Value: but value didn't change
                confidence = 0.95
            elif value_change < 0.5:
                gap_type = "MINOR_TRANSIENT"
                confidence = 0.70
            elif gap_duration > 3600:  # > 1 hour
                gap_type = "SYSTEM_OFFLINE"
                confidence = 0.80
            else:
                gap_type = "SENSOR_TRANSIENT"
                confidence = 0.60
            
            classifications.append({
                'timestamp': idx,
                'gap_duration_sec': gap_duration,
                'value_before': value_before,
                'value_after': value_after,
                'value_change': value_change,
                'type': gap_type,
                'confidence': confidence
            })
    
    if len(classifications) > 0:
        gap_df = pd.DataFrame(classifications)
        
        print(f"{stream_name}:")
        print(f"  Total gaps: {len(gap_df)}")
        
        for gap_type in gap_df['type'].unique():
            count = len(gap_df[gap_df['type'] == gap_type])
            avg_duration = gap_df[gap_df['type'] == gap_type]['gap_duration_sec'].mean()
            print(f"    {gap_type}: {count} gaps, avg duration {avg_duration/60:.1f} min")
        
        # Show largest gaps
        print(f"  Largest 3 gaps:")
        for _, row in gap_df.nlargest(3, 'gap_duration_sec').iterrows():
            print(f"    {row['timestamp']}: {row['gap_duration_sec']/3600:.2f} hr ({row['type']}, conf {row['confidence']:.0%})")
    else:
        print(f"{stream_name}: No gaps to classify ✓")
    
    print()
    return classifications

chwst_gaps = classify_gaps(chwst, gaps_chwst, "CHWST")
chwrt_gaps = classify_gaps(chwrt, gaps_chwrt, "CHWRT")
cdwrt_gaps = classify_gaps(cdwrt, gaps_cdwrt, "CDWRT")

print("--- STEP 3: COV Detection via Value Stability ---\n")

def detect_cov_regions(df, stream_name, nominal_interval):
    """Detect regions where value is constant (COV protocol)."""
    
    # Find consecutive records with same (or very similar) values
    value_diffs = df.diff().abs()
    stable_threshold = 0.02  # ±0.02°C = stable
    
    stable_mask = value_diffs.iloc[:, 0] < stable_threshold
    stable_runs = stable_mask.astype(int).diff().ne(0).cumsum()
    
    cov_regions = []
    for region_id in stable_runs.unique():
        region_mask = stable_runs == region_id
        region_df = df[region_mask]
        
        if len(region_df) > 100:  # At least 100 stable records = 20+ min at typical frequency
            start_time = region_df.index[0]
            end_time = region_df.index[-1]
            duration = (end_time - start_time).total_seconds() / 60
            value = region_df.iloc[0, 0]
            
            cov_regions.append({
                'start': start_time,
                'end': end_time,
                'duration_min': duration,
                'value': value,
                'records': len(region_df)
            })
    
    # Sort by duration, descending
    cov_regions = sorted(cov_regions, key=lambda x: x['duration_min'], reverse=True)
    
    print(f"{stream_name}:")
    print(f"  COV regions detected (stable ±0.02°C for >100 records): {len(cov_regions)}")
    
    if len(cov_regions) > 0:
        total_cov_minutes = sum(r['duration_min'] for r in cov_regions)
        total_minutes = (df.index[-1] - df.index[0]).total_seconds() / 60
        cov_percentage = total_cov_minutes / total_minutes * 100
        
        print(f"  Total time in COV regions: {total_cov_minutes/60:.0f} hours ({cov_percentage:.1f}% of dataset)")
        print(f"  Top 5 longest COV regions:")
        for i, region in enumerate(cov_regions[:5]):
            print(f"    {i+1}. {region['start'].strftime('%Y-%m-%d %H:%M')} to {region['end'].strftime('%Y-%m-%d %H:%M')}")
            print(f"       Duration: {region['duration_min']:.0f} min, Value: {region['value']:.2f}°C, {region['records']} records")
    
    print()
    return cov_regions

chwst_cov = detect_cov_regions(chwst, "CHWST", nominal_chwst)
chwrt_cov = detect_cov_regions(chwrt, "CHWRT", nominal_chwrt)
cdwrt_cov = detect_cov_regions(cdwrt, "CDWRT", nominal_cdwrt)


print("\n" + "─" * 90)
print("STEP 1b: SKEW ESTIMATION (CORRECTED - Analyzing Interval Drift Only)")
print("─" * 90)

def analyze_interval_stability(df, stream_name):
    """
    Analyze whether intervals are drifting or stable.
    This avoids confusing COV-sparse logging with clock drift.
    """
    
    timestamps = df.index
    
    # Calculate inter-sample intervals
    intervals = np.array([(timestamps[i+1] - timestamps[i]).total_seconds() 
                         for i in range(len(timestamps)-1)])
    
    # Statistics on intervals themselves
    interval_mean = np.mean(intervals)
    interval_std = np.std(intervals)
    interval_min = np.min(intervals)
    interval_max = np.max(intervals)
    interval_median = np.median(intervals)
    
    # Check if intervals are drifting over time
    # Split into two halves and compare
    mid = len(intervals) // 2
    first_half_mean = np.mean(intervals[:mid])
    second_half_mean = np.mean(intervals[mid:])
    drift_rate = (second_half_mean - first_half_mean) / (len(intervals) * np.median(intervals))
    
    print(f"\n{stream_name}:")
    print(f"  Interval Statistics:")
    print(f"    Mean: {interval_mean:.1f} sec")
    print(f"    Median: {interval_median:.1f} sec")
    print(f"    Std Dev: {interval_std:.1f} sec")
    print(f"    Min: {interval_min:.1f} sec ({interval_min/60:.2f} min)")
    print(f"    Max: {interval_max:.1f} sec ({interval_max/60:.2f} min)")
    
    print(f"\n  Drift Analysis:")
    print(f"    First half avg interval: {first_half_mean:.1f} sec")
    print(f"    Second half avg interval: {second_half_mean:.1f} sec")
    print(f"    Drift rate: {drift_rate*100:+.2f}% (negligible if <1%)")
    
    # Interpretation
    if abs(drift_rate) < 0.01 and interval_std < interval_mean * 0.1:
        clock_quality = "EXCELLENT (stable, regular BMS)"
    elif interval_std < interval_mean * 0.5:
        clock_quality = "GOOD (mostly stable)"
    elif interval_std < interval_mean * 1.0:
        clock_quality = "FAIR (irregular, COV protocol likely)"
    else:
        clock_quality = "EVENT-TRIGGERED (COV logging confirmed)"
    
    print(f"  Clock Quality: {clock_quality}")
    
    return {
        'stream': stream_name,
        'interval_mean': interval_mean,
        'interval_std': interval_std,
        'interval_cv': interval_std / interval_mean,
        'drift_rate': drift_rate,
        'clock_quality': clock_quality
    }

# Use filtered data (after exclusion)
interval_chwst = analyze_interval_stability(chwst_filtered, "CHWST (after exclusion)")
interval_chwrt = analyze_interval_stability(chwrt_filtered, "CHWRT (after exclusion)")
interval_cdwrt = analyze_interval_stability(cdwrt_filtered, "CDWRT (after exclusion)")

print("\n" + "─" * 90)
print("STEP 3: MASTER TIMELINE CREATION")
print("─" * 90)

# Create master timeline covering all data
min_time = min(chwst_filtered.index[0], chwrt_filtered.index[0], cdwrt_filtered.index[0])
max_time = max(chwst_filtered.index[-1], chwrt_filtered.index[-1], cdwrt_filtered.index[-1])

print(f"\nMaster Timeline Definition:")
print(f"  Start: {min_time}")
print(f"  End: {max_time}")
print(f"  Span: {(max_time - min_time).days} days")

# Create ideal 15-min grid
master_timeline = pd.date_range(start=min_time, end=max_time, freq='15min')

print(f"  Frequency: 15 minutes (900 seconds)")
print(f"  Expected records: {len(master_timeline):,}")

print("\n" + "─" * 90)
print("STEP 4: STREAM ALIGNMENT WITH NEAREST-NEIGHBOR MATCHING")
print("─" * 90)

def align_stream_event_based(df, master_timeline, stream_name, tolerance_minutes=30):
    """
    Align sparse event-triggered data to regular grid using nearest-neighbor.
    This is appropriate for COV-based logging.
    """
    
    tolerance = pd.Timedelta(minutes=tolerance_minutes)
    aligned_values = []
    alignment_quality = []
    
    for master_ts in master_timeline:
        # Find nearest timestamp in df
        distances = np.abs((df.index - master_ts).total_seconds())
        nearest_idx = np.argmin(distances)
        nearest_distance = distances[nearest_idx]
        
        if nearest_distance <= tolerance.total_seconds():
            # Within tolerance: use nearest
            value = df.iloc[nearest_idx, 0]
            aligned_values.append(value)
            
            if nearest_distance < 60:  # < 1 minute
                quality = 'exact'
            elif nearest_distance < 300:  # < 5 minutes
                quality = 'close'
            else:  # < 30 minutes
                quality = 'interpolated'
            alignment_quality.append(quality)
        else:
            # Outside tolerance: NaN
            aligned_values.append(np.nan)
            alignment_quality.append('missing')
    
    aligned_df = pd.DataFrame(
        {stream_name: aligned_values},
        index=master_timeline
    )
    
    # Statistics
    n_exact = sum(1 for q in alignment_quality if q == 'exact')
    n_close = sum(1 for q in alignment_quality if q == 'close')
    n_interp = sum(1 for q in alignment_quality if q == 'interpolated')
    n_missing = sum(1 for q in alignment_quality if q == 'missing')
    
    print(f"\n{stream_name} Alignment:")
    print(f"  Exact (<1 min): {n_exact:,} ({n_exact/len(aligned_df)*100:.1f}%)")
    print(f"  Close (1-5 min): {n_close:,} ({n_close/len(aligned_df)*100:.1f}%)")
    print(f"  Interpolated (5-30 min): {n_interp:,} ({n_interp/len(aligned_df)*100:.1f}%)")
    print(f"  Missing (>30 min): {n_missing:,} ({n_missing/len(aligned_df)*100:.1f}%)")
    print(f"  Total coverage: {(1 - n_missing/len(aligned_df))*100:.1f}%")
    
    return aligned_df, {
        'exact': n_exact,
        'close': n_close,
        'interpolated': n_interp,
        'missing': n_missing,
        'coverage_pct': (1 - n_missing/len(aligned_df))*100
    }

chwst_aligned, chwst_quality = align_stream_event_based(chwst_filtered, master_timeline, 'CHWST')
chwrt_aligned, chwrt_quality = align_stream_event_based(chwrt_filtered, master_timeline, 'CHWRT')
cdwrt_aligned, cdwrt_quality = align_stream_event_based(cdwrt_filtered, master_timeline, 'CDWRT')

print("\n" + "─" * 90)
print("STEP 5: JITTER CHARACTERIZATION (POST-SYNC)")
print("─" * 90)

print(f"\nAfter alignment to master 15-min timeline:\n")

# Calculate new interval statistics
synced_intervals_chwst = np.array([(chwst_aligned.index[i+1] - chwst_aligned.index[i]).total_seconds() 
                                   for i in range(len(chwst_aligned)-1)])
synced_intervals_chwrt = np.array([(chwrt_aligned.index[i+1] - chwrt_aligned.index[i]).total_seconds() 
                                   for i in range(len(chwrt_aligned)-1)])
synced_intervals_cdwrt = np.array([(cdwrt_aligned.index[i+1] - cdwrt_aligned.index[i]).total_seconds() 
                                   for i in range(len(cdwrt_aligned)-1)])

print(f"CHWST (Post-Sync):")
print(f"  Interval CV: {np.std(synced_intervals_chwst) / np.mean(synced_intervals_chwst) * 100:.2f}%")
print(f"  All intervals: {np.unique(synced_intervals_chwst)} seconds")

print(f"\nCHWRT (Post-Sync):")
print(f"  Interval CV: {np.std(synced_intervals_chwrt) / np.mean(synced_intervals_chwrt) * 100:.2f}%")
print(f"  All intervals: {np.unique(synced_intervals_chwrt)} seconds")

print(f"\nCDWRT (Post-Sync):")
print(f"  Interval CV: {np.std(synced_intervals_cdwrt) / np.mean(synced_intervals_cdwrt) * 100:.2f}%")
print(f"  All intervals: {np.unique(synced_intervals_cdwrt)} seconds")

print(f"\n✓ All streams aligned to 15-min master timeline")
print(f"✓ Jitter characterized and documented")

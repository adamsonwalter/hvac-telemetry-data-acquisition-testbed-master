
# Re-examine the raw data
print("Raw column check:")
print(chwst_df[['save_time', 'value']].head(20))
print("\nValue statistics:")
print(f"Min value: {chwst_df['value'].min()}")
print(f"Max value: {chwst_df['value'].max()}")
print(f"Mean value: {chwst_df['value'].mean()}")

# The 'value' column is actually the temperature
# Let's recalculate
chwst = chwst_df[['timestamp', 'value']].set_index('timestamp').sort_index()
chwrt = chwrt_df[['timestamp', 'value']].set_index('timestamp').sort_index()
cdwrt = cdwrt_df[['timestamp', 'value']].set_index('timestamp').sort_index()

print("\n" + "=" * 80)
print("REQUIREMENT 3: GAP DETECTION & RESOLUTION (CORRECTED)")
print("=" * 80)

def analyze_gaps_corrected(df, stream_name):
    """Detect gaps in a stream."""
    time_diffs = df.index.to_series().diff().dt.total_seconds()
    
    # Nominal interval detection
    median_interval = time_diffs.median()
    nominal_interval = round(median_interval / 10) * 10
    
    # Find gaps (intervals > 2x nominal)
    gap_threshold = nominal_interval * 2.0
    gaps = time_diffs[time_diffs > gap_threshold]
    
    print(f"\n{stream_name} ({len(df)} records):")
    print(f"  Time span: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')} ({(df.index[-1] - df.index[0]).days} days)")
    print(f"  Nominal interval: {nominal_interval:.0f} sec ({nominal_interval/60:.1f} min)")
    print(f"  Interval jitter: mean={time_diffs.mean():.0f} sec, std={time_diffs.std():.0f} sec")
    print(f"  Jitter CV: {time_diffs.std() / nominal_interval * 100:.1f}%")
    print(f"  Gaps (>2× nominal): {len(gaps)} total gaps")
    
    if len(gaps) > 0:
        print(f"    Largest: {gaps.max()/3600:.1f} hours")
        print(f"    Total gap time: {gaps.sum()/3600:.0f} hours")
        gap_pct = gaps.sum() / ((df.index[-1] - df.index[0]).total_seconds()) * 100
        print(f"    % of dataset: {gap_pct:.1f}%")
    else:
        print(f"    No long gaps detected ✓")
    
    # Value statistics
    print(f"  Value range: {df['value'].min():.2f}–{df['value'].max():.2f}°C")
    print(f"  Mean: {df['value'].mean():.2f}°C, Std: {df['value'].std():.2f}°C")
    
    return gaps, nominal_interval, time_diffs

print("\n--- STEP 1: Gap Detection (Time Intervals) ---")
gaps_chwst, nom_chwst, diffs_chwst = analyze_gaps_corrected(chwst, "CHWST")
gaps_chwrt, nom_chwrt, diffs_chwrt = analyze_gaps_corrected(chwrt, "CHWRT")
gaps_cdwrt, nom_cdwrt, diffs_cdwrt = analyze_gaps_corrected(cdwrt, "CDWRT")

# HTDAM v2.0 Stage 5: Transformation & Export
## Complete Implementation Specification

**Date**: 2025-12-08  
**Status**: Complete specification for Stage 5 (FINAL STAGE)  
**Audience**: Programmer, technical reviewer, project owner

---

## 1. Stage 5 Overview

**Stage name**: Transformation & Export  
**Order in HTDAM v2.0**: Stage 5 (final stage, after Signal Preservation & COP)  
**Goals**:

- Compute **final pipeline confidence score** (aggregate of all 4 stages).
- Apply **final transformations** (derive optional fields, format corrections).
- Select **export format** (CSV, Parquet, JSON, database insert).
- Generate **use-case recommendations** (energy savings %, fouling severity, hunt status).
- Produce **executive summary** (key metrics, findings, next steps).
- Validate **data quality** one final time before delivery.

**Physics Foundation**:
- No new physics calculations in Stage 5.
- All measurements verified in Stages 1–4.
- Stage 5 focuses on **presentation, integration, and business value**.

**Inputs** (from Stage 4):

- Extended dataframe with all derived columns (35+ columns, 35,136 rows).
- Stage 4 metrics JSON (load, COP, hunt, fouling statistics).
- Stage 3 metrics JSON (synchronization quality).
- Stage 2 metrics JSON (gap semantics, exclusion windows).
- Stage 1 metrics JSON (unit conversions, physics violations).

**Outputs**:

- Final dataframe (export-ready, all columns, no NaN except valid nulls).
- Executive summary (1–2 page markdown with key findings).
- Use-case recommendations (energy savings opportunity, maintenance actions).
- Export files (CSV, Parquet, or database insert scripts).
- Final pipeline metrics JSON (confidence score, completeness, quality).

---

## 2. Final Confidence Calculation

### 2.1 Component Confidence Scores (From Prior Stages)

Each stage produced a confidence score:

```
Stage 1 Confidence (unit_confidence):
  - Base: 1.00 × (1 − sum_of_penalties)
  - Penalties: missing units, ambiguous units, physics violations
  - Expected: 1.00 (perfect on BarTech)

Stage 2 Confidence (gap_confidence):
  - Base: 0.93 on BarTech
  - Penalties: COV_MINOR (−0.02), SENSOR_ANOMALY (−0.05)
  - Exclusion windows: (−0.20 per overlapping major window)
  - Expected: 0.93 (±0.02)

Stage 3 Confidence (sync_confidence):
  - Base: 0.88 on BarTech
  - Penalties: jitter, coverage gaps, interpolation
  - Expected: 0.88 (±0.02)

Stage 4 Confidence (component_confidence):
  - Load confidence: 0.85
  - COP confidence: 0.78
  - Hunt confidence: 0.70
  - Fouling confidence: 0.55
  - Mean: 0.72
  - With power/fouling penalties: 0.78
  - Expected: 0.78 (±0.05)
```

### 2.2 Final Pipeline Confidence

```
final_pipeline_confidence = weighted_average(
    stage1_confidence × 0.10,    # Unit verification (foundation)
    stage2_confidence × 0.15,    # Gap detection (data quality)
    stage3_confidence × 0.25,    # Synchronization (critical for downstream)
    stage4_confidence × 0.50     # COP & analysis (primary deliverable)
)
```

**Expected (BarTech)**:
```
final = (1.00 × 0.10) + (0.93 × 0.15) + (0.88 × 0.25) + (0.78 × 0.50)
      = 0.10 + 0.1395 + 0.22 + 0.39
      = 0.8495
      ≈ 0.85 (±0.03)
```

### 2.3 Quality Tiers

Based on final confidence:

```
final_confidence >= 0.90:  TIER_A   "Production-ready, high confidence"
final_confidence >= 0.80:  TIER_B   "Suitable for analysis, monitor edge cases"
final_confidence >= 0.70:  TIER_C   "Use with caution, verify key metrics"
final_confidence >= 0.60:  TIER_D   "Limited use, significant gaps present"
final_confidence < 0.60:   TIER_F   "Do not use without expert review"
```

**BarTech Expected**: TIER_B (0.85)

---

## 3. Final Transformations

### 3.1 Optional Derived Columns

Add these if computation is fast and meaningful:

```
# Energy & Efficiency
baseline_cop_nameplate = 4.5        (if provided by user)
cop_vs_baseline_pct = ((cop / baseline_cop_nameplate) - 1) × 100
energy_savings_potential_kwh = sum(q_evap where cop < baseline_cop) × 0.25h
                              (over entire period)

# Maintenance Triggers
needs_cleaning = fouling_severity == "MAJOR_FOULING"
needs_investigation = hunt_flag == True AND hunt_severity == "MAJOR"

# Data Quality Flags
data_row_quality = (q_confidence + cop_confidence + fouling_confidence) / 3
is_high_quality_row = data_row_quality >= 0.80
is_usable_row = data_row_quality >= 0.60

# Time-based Features (if useful)
hour_of_day = timestamp.hour
day_of_week = timestamp.dayofweek
season = "WINTER" if month in [6,7,8] else "SUMMER" if month in [12,1,2] else "SHOULDER"
```

### 3.2 Data Cleanup (Final Pass)

Before export:

```python
# Step 1: Standardize column names (snake_case)
df.columns = df.columns.str.lower().str.replace(' ', '_')

# Step 2: Ensure datetime precision (ISO 8601)
df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%SZ')

# Step 3: Round numeric columns to reasonable precision
df[float_cols] = df[float_cols].round(4)

# Step 4: Fill valid nulls with explicit markers (optional)
# For columns where NULL is meaningful:
#   - power_kw: NaN = "power_not_measured"
#   - cop: NaN = "cop_not_computable"
# Keep as NaN for downstream tools (Pandas, Power BI, etc. handle this)

# Step 5: Verify no critical columns are entirely NaN
for col in ['timestamp', 'chwst', 'chwrt', 'cdwrt', 'flow_m3s']:
    if df[col].isna().all():
        raise ValueError(f"Critical column {col} is entirely NaN")

# Step 6: Sort by timestamp (ensure temporal order)
df = df.sort_values('timestamp')
```

---

## 4. Export Format Selection

Your programmer should support **at least one** of these:

### 4.1 CSV (Human-Readable, Universal)

**Pros**:
- Opens in Excel, Python, R, SQL.
- Human-readable columns.
- Version control friendly (text).
- Small file size.

**Cons**:
- Precision loss (floating-point rounding).
- No schema validation.
- Large rows (35+ columns).

**When to use**: Default for 80% of users.

**Output format**:
```
timestamp,chwst,chwrt,cdwrt,flow_m3s,power_kw,...,final_confidence,quality_tier
2024-09-18T03:30:00Z,7.5,12.1,21.0,0.125,50.2,...,0.85,TIER_B
2024-09-18T03:45:00Z,7.6,12.0,20.9,0.126,51.1,...,0.84,TIER_B
```

**File size** (BarTech): ~8 MB

---

### 4.2 Parquet (Compressed, Typed)

**Pros**:
- Column compression (3–5× smaller than CSV).
- Preserves data types (no rounding).
- Fast read performance.
- Schema included.
- Spark/Dask compatible.

**Cons**:
- Requires Parquet library (Python, R, etc.).
- Not human-readable in text editor.
- Overkill for small datasets.

**When to use**: Data engineering pipelines, large datasets, repeated access.

**Output format**:
```
parquet_file = df.to_parquet('bartech_stage5_output.parquet', compression='snappy')
```

**File size** (BarTech): ~2 MB

---

### 4.3 JSON (Structured, Flexible)

**Pros**:
- Flexible nested structure.
- API-friendly.
- Includes metadata (schema, units).

**Cons**:
- Very large file size (35k rows × 35 columns).
- Slower to parse.
- Not ideal for data analysis.

**When to use**: API endpoints, nested reporting, metadata emphasis.

**Output format**:
```json
{
  "stage": "EXPORT",
  "metadata": {
    "units": {
      "timestamp": "ISO 8601",
      "chwst": "°C",
      "chwrt": "°C",
      "power_kw": "kW",
      "cop": "dimensionless"
    },
    "final_confidence": 0.85,
    "quality_tier": "TIER_B"
  },
  "data": [
    {
      "timestamp": "2024-09-18T03:30:00Z",
      "chwst": 7.5,
      "chwrt": 12.1,
      ...
    },
    ...
  ]
}
```

**File size** (BarTech): ~25 MB

---

### 4.4 Database (SQL Insert)

**Pros**:
- Real-time queryable.
- Scalable to petabyte scale.
- Supports transactions.
- Access control.

**Cons**:
- Requires database setup.
- Schema definition needed.
- Slower single-row inserts.

**When to use**: Operational dashboards, continuous monitoring.

**Output format**:
```sql
INSERT INTO hvac_analytics.chiller_data (timestamp, chwst, chwrt, ..., final_confidence)
VALUES
  ('2024-09-18T03:30:00Z', 7.5, 12.1, ..., 0.85),
  ('2024-09-18T03:45:00Z', 7.6, 12.0, ..., 0.84),
  ...
;
```

**Implementation**:
```python
# Using SQLAlchemy
from sqlalchemy import create_engine

engine = create_engine('postgresql://user:password@localhost/hvac_db')
df.to_sql('chiller_data', engine, if_exists='append', index=False)
```

---

## 5. Use-Case Recommendations

Based on Stage 4 outputs, generate recommendations for 3 common use cases:

### 5.1 Energy Savings Opportunity

**Metric**: COP vs. nameplate baseline.

```
if baseline_cop_provided:
    cop_loss_pct = ((1 - cop_mean / baseline_cop) × 100)
    
    if cop_loss_pct > 10:
        recommendation = "SIGNIFICANT OPPORTUNITY"
        actions = [
            "Investigate condenser fouling (check lift elevation)",
            "Verify evaporator ΔT (target 4–6 °C)",
            "Review setpoint strategy for hunting"
        ]
    elif cop_loss_pct > 5:
        recommendation = "MINOR OPPORTUNITY"
        actions = [
            "Monitor fouling trends over next 30 days",
            "Verify measurement accuracy"
        ]
    else:
        recommendation = "OPERATING AS EXPECTED"
        actions = [
            "Continue normal monitoring"
        ]
```

**Expected (BarTech)**: COP 4.5 vs baseline 4.0 = −12.5% (better performance; nameplate was conservative).

---

### 5.2 Fouling Diagnosis

**Metric**: Evaporator & condenser fouling percentages.

```
evap_fouling_mean = fouling_analysis.evaporator_fouling_mean_pct
cond_fouling_mean = fouling_analysis.condenser_fouling_mean_pct

if evap_fouling_mean > 20:
    recommendation = "EVAPORATOR CLEANING RECOMMENDED"
    urgency = "HIGH"
    estimated_savings_pct = evap_fouling_mean × 0.8  # 80% of fouling gain recoverable
else:
    recommendation = "EVAPORATOR CLEAN"
    urgency = "LOW"

if cond_fouling_mean > 15:
    recommendation = "CONDENSER CLEANING RECOMMENDED"
    urgency = "HIGH"
    estimated_savings_pct = cond_fouling_mean × 0.6  # 60% of fouling gain recoverable
else:
    recommendation = "CONDENSER ACCEPTABLE"
    urgency = "LOW"
```

**Expected (BarTech)**: Evap 8.2%, Cond 12.5% → both ACCEPTABLE, no cleaning needed.

---

### 5.3 Control Stability (Hunting)

**Metric**: Hunt frequency and severity.

```
hunt_pct = hunt_analysis.hunt_pct

if hunt_pct > 10:
    recommendation = "CONTROL INSTABILITY DETECTED"
    actions = [
        "Review setpoint deadband (increase to 1–2 °C)",
        "Check sensor noise (filter if needed)",
        "Verify PID tuning"
    ]
elif hunt_pct > 5:
    recommendation = "MINOR CYCLING OBSERVED"
    actions = [
        "Monitor frequency trend",
        "Consider minor tuning adjustment"
    ]
else:
    recommendation = "CONTROL STABLE"
    actions = [
        "No action required"
    ]
```

**Expected (BarTech)**: Hunt 4.9% → CONTROL STABLE.

---

## 6. Executive Summary Output

Generate a 1–2 page markdown report:

```markdown
# HTDAM v2.0 Analysis Report
## BarTech Chiller | 2024-09-18 to 2025-09-19

### Overview
- **Observation Period**: 366 days
- **Data Points**: 35,136 grid timestamps (15-min intervals)
- **Coverage**: 93.8% valid, 6.2% excluded/gaps
- **Final Confidence**: 0.85 (TIER_B: Suitable for analysis)

### Key Findings

#### Energy Performance
- **Mean COP**: 4.5 (vs baseline 4.0, **−12.5% loss**)
- **COP Range**: 2.1–6.8
- **Normalized COP**: 0.40 (40% of Carnot theoretical max)
- **Assessment**: Operating as designed; no energy recovery opportunity.

#### Equipment Health
- **Evaporator Fouling**: 8.2% (CLEAN, no action needed)
- **Condenser Fouling**: 12.5% (ACCEPTABLE, monitor)
- **Assessment**: Equipment in good condition.

#### Control Stability
- **Hunting Detected**: 4.9% of observation window
- **Severity**: 348 NONE, 15 MINOR, 3 MAJOR
- **Assessment**: Control stable; no tuning needed.

### Data Quality
- **Stage 1 (Units)**: Confidence 1.00 ✓
- **Stage 2 (Gaps)**: Confidence 0.93 ✓
- **Stage 3 (Sync)**: Confidence 0.88 ✓
- **Stage 4 (COP/Fouling)**: Confidence 0.78 ✓
- **Stage 5 (Final)**: Confidence 0.85 ✓

### Recommendations

1. **Continue Normal Operation**: All metrics within acceptable ranges.
2. **Monitor Condenser**: Fouling at 12.5%; schedule cleaning if >15% next review.
3. **Annual Review**: Re-assess COP trend over next 12 months for degradation.

### Appendix
- Detailed metrics: [Export file]
- Raw data: [CSV/Parquet file]
- Metadata: [Schema and units]
```

---

## 7. Output Format: Stage 5

### 7.1 Final Dataframe

**Columns** (all from Stages 1–4 + Stage 5 derived):

```
timestamp                          # ISO 8601
chwst, chwrt, cdwrt                # Original measurements (°C)
flow_m3s, power_kw                 # Original measurements (m³/s, kW)
chwst_align_quality, ...           # Alignment quality (EXACT/CLOSE/INTERP/MISSING)
gap_type                           # Row classification (VALID/COV/ANOMALY/EXCLUDED/GAP)
confidence                         # Row-level confidence (Stage 3)

# Stage 4 Derived
delta_t_chw, lift                  # Temperature differentials (°C)
q_evap_kw, cop                     # Load & efficiency (kW, dimensionless)
cop_carnot, cop_normalized         # Theoretical COP
q_confidence, cop_confidence       # Component confidences
hunt_flag, hunt_severity           # Hunting detection
fouling_evap_pct, fouling_condenser_pct  # Fouling percentage
fouling_evap_severity, fouling_condenser_severity  # Fouling classification

# Stage 5 Derived (Optional)
cop_vs_baseline_pct                # COP loss/gain vs nameplate (%)
energy_savings_potential_kwh       # Cumulative savings if COP improved to baseline (kWh)
needs_cleaning                     # Boolean: major fouling detected
needs_investigation                # Boolean: major hunting detected
data_row_quality                   # Average of 3 component confidences
is_high_quality_row                # Boolean: quality >= 0.80
is_usable_row                      # Boolean: quality >= 0.60

# Stage 5 Meta
final_confidence                   # Final pipeline confidence (0.0–1.0)
quality_tier                       # TIER_A/B/C/D/F
data_source                        # "BarTech" (for tracking)
```

**Size**: 35,136 rows × 40 columns

---

### 7.2 Metrics JSON (Stage 5)

```json
{
  "stage": "EXPORT",
  "timestamp_start": "2024-09-18T03:30:00Z",
  "timestamp_end": "2025-09-19T03:15:00Z",
  "observation_days": 366,
  "total_rows": 35136,
  
  "data_coverage": {
    "valid_rows_pct": 93.8,
    "excluded_rows_pct": 5.0,
    "gap_rows_pct": 1.2
  },
  
  "final_confidence_breakdown": {
    "stage1_confidence": 1.00,
    "stage2_confidence": 0.93,
    "stage3_confidence": 0.88,
    "stage4_confidence": 0.78,
    "final_pipeline_confidence": 0.85,
    "weight_s1": 0.10,
    "weight_s2": 0.15,
    "weight_s3": 0.25,
    "weight_s4": 0.50
  },
  
  "quality_tier": "TIER_B",
  "quality_interpretation": "Suitable for analysis, monitor edge cases",
  
  "energy_performance": {
    "cop_mean": 4.5,
    "cop_baseline": 4.0,
    "cop_vs_baseline_pct": -12.5,
    "interpretation": "Better than expected; nameplate was conservative"
  },
  
  "fouling_summary": {
    "evaporator_fouling_pct": 8.2,
    "evaporator_severity": "CLEAN",
    "condenser_fouling_pct": 12.5,
    "condenser_severity": "ACCEPTABLE"
  },
  
  "hunting_summary": {
    "hunt_pct": 4.9,
    "hunt_severity_breakdown": {
      "NONE": 348,
      "MINOR": 15,
      "MAJOR": 3
    },
    "control_stability": "STABLE"
  },
  
  "recommendations": [
    "Continue normal operation",
    "Monitor condenser fouling; schedule cleaning if >15%",
    "Annual COP review for degradation trend"
  ],
  
  "export_filename": "bartech_htdam_v2.0_stage5_2024-2025.csv",
  "export_format": "CSV",
  "export_size_mb": 8.5,
  
  "errors": [],
  "warnings": [
    "Fouling confidence inherently lower (0.55); limited observability"
  ],
  "halt": false
}
```

---

## 8. Implementation Checklist (Stage 5)

Your programmer should be able to tick all of these:

- [ ] Read Stage 5 spec end-to-end.
- [ ] Import Stage 4 output (dataframe + all metrics JSON from Stages 1–4).
- [ ] Implement `calculate_final_confidence()` (weighted average, Stage 1–4).
- [ ] Assign `quality_tier` based on confidence.
- [ ] (Optional) Compute derived columns (COP vs baseline, energy savings, etc.).
- [ ] (Optional) Add maintenance trigger flags (needs_cleaning, needs_investigation).
- [ ] Implement data cleanup (standardize names, ensure datetime precision, verify no critical nulls).
- [ ] Implement `select_export_format()` (CSV default, Parquet optional).
- [ ] Generate use-case recommendations (energy savings, fouling, hunting).
- [ ] Generate executive summary markdown (1–2 page report).
- [ ] Build Stage 5 metrics JSON exactly as specified.
- [ ] Export dataframe (CSV or Parquet).
- [ ] Export executive summary (markdown).
- [ ] Export metrics JSON.
- [ ] Verify export files contain all expected columns.
- [ ] Spot-check BarTech data (metrics match expected values).
- [ ] Final validation (no data loss, no corruption, timestamps correct).

---

## 9. Expected BarTech Outputs (Stage 5)

**Input**: Stage 4 output (35,136 rows, 35+ columns, confidence = 0.78).

**Output Files**:

```
bartech_htdam_v2.0_stage5_2024-2025.csv         (8.5 MB)
├─ Rows: 35,136
├─ Columns: 40
└─ Includes all derived + final_confidence + quality_tier

bartech_htdam_v2.0_stage5_summary.md            (15 KB)
├─ Title: HTDAM v2.0 Analysis Report
├─ Key findings: COP 4.5, fouling 8.2%/12.5%, hunting 4.9%
├─ Recommendations: Continue normal operation, monitor condenser
└─ Quality: TIER_B (0.85 confidence)

bartech_htdam_v2.0_stage5_metrics.json          (50 KB)
├─ Final confidence: 0.85
├─ Quality tier: TIER_B
├─ All 4-stage metrics rolled up
└─ Recommendations array
```

---

## 10. FAQ (Stage 5)

### Q1: Why is final confidence lower than Stage 4?

**A**: It shouldn't be much lower. Final confidence (0.85) is weighted average of 4 stages; Stage 4 (0.78) is just one component. The final score reflects the whole pipeline quality.

### Q2: What should we do with TIER_C data?

**A**: Use with caution. Verify key metrics manually. Consider deeper investigation into specific timestamp ranges.

### Q3: Can we export to multiple formats?

**A**: Yes! Export to CSV (universal) + Parquet (analysis) is ideal. JSON if API is needed.

### Q4: How do we integrate with existing dashboards?

**A**: Use CSV export for most BI tools (Power BI, Tableau). Use Parquet for Python/Spark pipelines. Use JSON for REST APIs.

### Q5: What if baseline COP is not provided?

**A**: Skip COP vs baseline comparison. Assess COP in absolute terms (4.5 is good; 3.0 is concerning; 6.0 is excellent).

---

## 11. Constants Summary (Copy-Paste Ready)

Add to `htdam_constants.py`:

```python
# Stage 5: Transformation & Export

# Final Confidence Weights
CONFIDENCE_WEIGHT_STAGE1 = 0.10    # Unit verification (foundation)
CONFIDENCE_WEIGHT_STAGE2 = 0.15    # Gap detection (data quality)
CONFIDENCE_WEIGHT_STAGE3 = 0.25    # Synchronization (temporal alignment)
CONFIDENCE_WEIGHT_STAGE4 = 0.50    # COP & analysis (primary deliverable)

# Quality Tiers
QUALITY_TIER_THRESHOLDS = {
    'TIER_A': 0.90,     # >= 0.90: Production-ready
    'TIER_B': 0.80,     # >= 0.80: Suitable for analysis
    'TIER_C': 0.70,     # >= 0.70: Use with caution
    'TIER_D': 0.60,     # >= 0.60: Limited use
    'TIER_F': 0.00,     # <  0.60: Do not use
}

# Export Formats
EXPORT_FORMATS = ['CSV', 'PARQUET', 'JSON', 'SQL']
DEFAULT_EXPORT_FORMAT = 'CSV'

# Energy Savings Parameters
BASELINE_COP_TYPICAL = 4.5          # Nameplate (if not provided)
FOULING_RECOVERY_RATE_EVAP = 0.80  # 80% of fouling loss recoverable
FOULING_RECOVERY_RATE_COND = 0.60  # 60% of fouling loss recoverable

# Maintenance Thresholds
FOULING_MAJOR_THRESHOLD_EVAP = 25.0    # % above baseline
FOULING_MAJOR_THRESHOLD_COND = 15.0
HUNT_MAJOR_THRESHOLD_PCT = 10.0        # % of windows with hunting

# High Quality Row Thresholds
HIGH_QUALITY_ROW_THRESHOLD = 0.80
USABLE_ROW_THRESHOLD = 0.60
```

---

## 12. Integration with Stage 4

**Input Interface**:

```python
async def run_stage5(ctx: HTDAMContext) -> HTDAMContext:
    """
    Final stage: Transformation & Export.
    
    Args:
        ctx.sync['data']: Stage 4 dataframe (35,136 rows, 35+ columns)
        ctx.sync['metrics']: Stage 4 metrics JSON
        ctx.metrics_stage1, ctx.metrics_stage2, ctx.metrics_stage3: Prior stage metrics
    
    Returns:
        ctx with export files and final summary
    """
    try:
        df_stage4 = ctx.sync['data']
        metrics_stage4 = ctx.sync['metrics']
        
        # Calculate final confidence
        final_confidence = weighted_average_confidence(
            ctx.metrics_stage1['stage1_confidence'],
            ctx.metrics_stage2['stage2_confidence'],
            ctx.metrics_stage3['stage3_confidence'],
            metrics_stage4['stage4_confidence']
        )
        
        # Assign quality tier
        quality_tier = assign_quality_tier(final_confidence)
        
        # Add Stage 5 columns
        df_stage5 = add_stage5_columns(df_stage4, quality_tier)
        
        # Generate recommendations
        recommendations = generate_use_case_recommendations(metrics_stage4)
        
        # Export
        export_csv(df_stage5, 'bartech_stage5_export.csv')
        export_summary(recommendations, final_confidence, 'bartech_stage5_summary.md')
        
        # Metrics
        metrics_stage5 = {
            'stage': 'EXPORT',
            'final_confidence': final_confidence,
            'quality_tier': quality_tier,
            'recommendations': recommendations,
            'halt': False
        }
        
        ctx.sync = {
            'data': df_stage5,
            'metrics': metrics_stage5,
            'export_files': [
                'bartech_stage5_export.csv',
                'bartech_stage5_summary.md'
            ],
            'finalScore': final_confidence
        }
        
        return ctx
    
    except Exception as e:
        ctx.errors.append(f"Stage 5 error: {str(e)}")
        ctx.finalScore = 0.00
        return ctx
```

---

**Status**: Complete for Stage 5 (FINAL STAGE).  
**Next**: None; Stage 5 is the end of HTDAM v2.0 pipeline.  
**Generated**: 2025-12-08

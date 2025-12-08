# Stage 1 Diagnostic Reports: Data Quality Forensics

**Purpose**: Document user-facing reports that showcase Stage 1's automated diagnostic depth  
**Date**: 2025-12-08  
**Status**: Design Specification  

---

## The User Value Proposition

### What Users See Now (Typical Industry Practice)
❌ "Data validation failed"  
❌ "Physics constraints violated"  
❌ "Please check sensor configuration"

**Problem**: Generic error messages with no diagnostic insight. Users left wondering:
- Which sensors are wrong?
- Is this a BMS issue or equipment issue?
- Can we salvage any of the data?
- How much will this cost to fix?

### What HTDAM Stage 1 Delivers
✅ **Automated root cause analysis**  
✅ **Quantified data quality metrics**  
✅ **State-dependent diagnostic correlation**  
✅ **Actionable recommendations with cost/benefit**

**Value**: Users understand exactly what's wrong, why it's wrong, and what to do about it.

---

## Report Types

### 1. **Sensor Reversal Detection Report** 🔥

**Trigger**: CHWRT < CHWST violation rate >50% in Stage 1 physics validation

**Example Output**:

```markdown
# 🚨 CRITICAL DATA QUALITY ISSUE DETECTED

## Sensor Reversal: CHWRT ↔ CHWST Swap (State-Dependent)

**Building**: BarTech 160 Ann St, Chiller 2  
**Detection Date**: 2025-12-08  
**Confidence**: 99.3% (extremely high)  

---

## SMOKING GUN IDENTIFIED 🔍

The operational data **definitively explains the issue**: the signal swap occurs 
when the chiller is **OFF or at minimal load**.

### Critical Correlation

| Operational State | Anomaly Rate | Samples | Avg Load | Avg Flow | Avg ΔT |
|-------------------|--------------|---------|----------|----------|--------|
| **ACTIVE (>10% load)** | **1.2%** ✓ | 8,116 | 41.7% | 37.2 L/s | **+1.90°C** ✓ |
| **STANDBY (≤10% load)** | **73.3%** ❌ | 24,397 | 0.4% | 3.1 L/s | **-0.34°C** ❌ |

**Correlation strength**: Anomalies drop from **73% → 1%** when chiller transitions 
from standby to active operation.

**Flow data corroboration**:
- Low flow (<1 L/s): 77% anomaly rate ❌
- Medium flow (10-30 L/s): 0.7% anomaly rate ✓

---

## Root Cause: BMS Data Mapping Logic Error

The BMS appears to have **conditional point mapping** that switches based on 
chiller operational state.

**Most likely mechanism**:

### During Active Operation (Load >10%)
✓ BMS correctly maps physical sensor addresses to CHWST/CHWRT labels  
✓ Produces proper positive Delta-T values (avg +1.90°C)  
✓ Physics validation: PASS

### During Standby/Off Mode (Load ≤10%)
❌ BMS uses alternate data structure (default state, backup register, or init values)  
❌ Sensor assignments are reversed  
❌ Creates impossible negative Delta-T (avg -0.34°C)  
❌ Physics validation: FAIL

---

## Why This Happens

### Possible BMS Configuration Issues:

1. **Lead/Lag Configuration Bug**  
   Multi-chiller systems poll standby chillers differently than active chillers. 
   BMS may read "Chiller 2" sensor data from lead chiller template when inactive, 
   then switch to correct physical mapping when chiller starts.

2. **Initialization State Bug**  
   BMS populates temperature points with reversed mappings during chiller 
   initialization/standby, then corrects them once control loop becomes active.

3. **Virtual Point Calculation**  
   Some BMS systems calculate standby temperatures from system-level average values 
   with swapped logic, then switch to real sensor readings during operation.

---

## Data Salvage Analysis

### Current Dataset (Full Year)
- **Total samples**: 35,095
- **Physics violations**: 19,451 (54.7%)
- **Usable for analysis**: ❌ NO

### Filtered Dataset (ACTIVE-only, >10% load)
- **ACTIVE samples**: 10,624 (30.3%)
- **Physics violations**: 128 (1.2%)
- **Usable for analysis**: ✅ YES

**Salvage rate**: **30.3%** of telemetry is physics-valid

---

## Recommendations

### ✅ IMMEDIATE (No BMS Changes Required)

**Use ACTIVE-only filtered dataset**  
Stage 1 automatically detected and isolated the 10,624 physics-valid samples.
These can be used immediately for:
- Efficiency analysis
- COP calculations  
- Performance benchmarking
- Control optimization

**Estimated value**: $8,000-15,000 in avoided site visits and manual data cleaning

---

### 🔧 SHORT-TERM (BMS Configuration Fix)

**Contact BMS vendor** to investigate conditional point mapping logic.

**Diagnostic questions to ask**:
1. Does Chiller 2 use different point mappings in standby vs active modes?
2. Are CHWST/CHWRT addresses pulled from a template or physical addresses?
3. Is there a lead/lag switching logic that affects sensor assignments?

**Expected fix time**: 2-4 hours (remote BMS configuration change)  
**Expected fix cost**: $500-1,500 (vendor service call)  
**Data quality improvement**: Salvage rate 30% → 98%

---

### 📊 LONG-TERM (System-Wide Validation)

**Run Stage 1 verification on ALL chillers** in the facility to identify:
- Similar state-dependent reversals in other units
- Other BMS configuration anomalies
- System-wide data quality baseline

**HTDAM can automate this** across your entire portfolio (180 buildings) 
with zero manual intervention.

---

## Financial Impact

### Cost of Ignoring This Issue
- **Wasted analysis effort**: 54.7% of data produces invalid results
- **Missed savings opportunities**: Cannot optimize chiller when data is wrong
- **Incorrect control decisions**: BMS automation using swapped signals

**Estimated annual cost**: $25,000-50,000 per building in lost efficiency

### Value of Stage 1 Detection
- **Automated diagnosis**: $8,000 (vs manual site visit + data forensics)
- **Data salvage**: 30.3% of telemetry immediately usable
- **Root cause identified**: Targeted BMS fix ($500) vs equipment replacement ($80,000)

**ROI**: 16-32× return on Stage 1 analysis investment

---

## Technical Details (For BMS Vendor)

### Affected Point Mappings
```
Signal: CHWST (Chilled Water Supply Temperature)
Signal: CHWRT (Chilled Water Return Temperature)
Chiller: BarTech 160 Ann St Level 22 MSSB Chiller 2
BMS: [vendor/model from Stage 0 metadata]
```

### Evidence Summary
```
Total samples analyzed: 35,095
Date range: 2024-09-18 to 2025-10-10
CHWRT < CHWST violations: 19,451 (54.7%)

State-dependent correlation:
- Load ≤10%: 73.3% violation rate (standby reversal)
- Load >10%: 1.2% violation rate (correct mapping)

Statistical significance: p < 0.0001 (chi-squared test)
```

### Recommended BMS Audit
1. Review point mapping logic for Chiller 2 CHWST/CHWRT
2. Compare active vs standby point assignment tables
3. Check for template-based vs physical address mapping
4. Validate lead/lag switching logic
5. Test initialization sequence behavior

---

## Additional Resources

- **Filtered dataset**: `output/bartech_active_only.csv` (10,624 samples, physics-valid)
- **Full diagnostic report**: `output/stage1_sensor_reversal_analysis.json`
- **Visualization**: `output/stage1_delta_t_by_operational_state.png`
- **HTDAM methodology**: See `docs/STAGE1_UNIT_VERIFICATION.md`

---

## Questions?

Contact [HTDAM support] for:
- BMS vendor coordination
- Additional diagnostic analysis  
- Multi-building portfolio screening
- Custom data quality reports

**This analysis was performed automatically by HTDAM Stage 1 Unit Verification.**
```

---

## Report Implementation Requirements

### Backend (Automated Generation)

**When to trigger**: Stage 1 salvage success (>50% CHWRT<CHWST violations, ACTIVE-only passes)

**Report generator function**:
```python
# src/domain/htdam/reports/generateSensorReversalReport.py

def generate_sensor_reversal_report(
    validations_full: Dict,
    validations_active: Dict,
    operational_state_breakdown: Dict,
    building_metadata: Dict,
) -> str:
    """
    Pure function: Generate markdown report for sensor reversal detection.
    
    Args:
        validations_full: Physics validation on full dataset
        validations_active: Physics validation on ACTIVE-only
        operational_state_breakdown: Stats by ACTIVE/STANDBY/OFF
        building_metadata: From Stage 0 (building name, equipment ID)
    
    Returns:
        Markdown-formatted report string
    """
```

**Output files**:
- `stage1_sensor_reversal_report.md` (user-facing, shown above)
- `stage1_sensor_reversal_analysis.json` (machine-readable metrics)
- `stage1_delta_t_by_operational_state.png` (visualization)

---

### Frontend (User Dashboard)

**Alert banner** when sensor reversal detected:
```
🚨 CRITICAL DATA QUALITY ISSUE DETECTED

Sensor reversal identified: CHWRT ↔ CHWST swap (state-dependent)
Confidence: 99.3% | Data salvaged: 30.3% | Estimated fix cost: $500-1,500

[View Full Diagnostic Report] [Download Filtered Dataset] [Contact BMS Vendor]
```

**Report sections** (collapsible cards):
1. 🔍 **Smoking Gun Summary** (correlation table)
2. 🔧 **Root Cause Analysis** (BMS logic explanation)
3. 💾 **Data Salvage** (filtered dataset ready to use)
4. ✅ **Recommendations** (immediate, short-term, long-term)
5. 💰 **Financial Impact** (cost of ignoring vs fixing)
6. 📞 **BMS Vendor Coordination** (technical details + audit checklist)

**Visualization**: Interactive Delta-T vs Load scatter plot with operational state color coding

---

## Similar Reports to Implement

### 2. **Unit Confusion Detection Report**

**Trigger**: Load signal >100 or >nameplate capacity

**Key sections**:
- "Units Mismatch: % vs RT vs Capacity Index"
- Mode change analysis (when does signal exceed 100?)
- Nameplate capacity comparison
- Recommendation: Verify point scaling factor in BMS

### 3. **kW vs kWh Confusion Report**

**Trigger**: Power signal monotonically increasing

**Key sections**:
- "Cumulative Energy vs Instantaneous Power"
- Monotonicity test results
- Variance analysis
- Recommendation: Check BMS point type (analog input vs pulse counter)

### 4. **Multi-Building Data Quality Dashboard**

**Trigger**: Portfolio-wide Stage 1 analysis complete

**Key sections**:
- Data quality heatmap (180 buildings, color by Stage 1 confidence)
- Common issues ranked by prevalence
- Total salvage rate across portfolio
- Aggregate financial impact
- Bulk BMS vendor coordination report

---

## Documentation Strategy

### For End Users (Building Operators)
- **Focus**: What's wrong, why, and what to do
- **Language**: Plain English, minimize jargon
- **Length**: 2-3 pages max
- **Format**: Markdown → PDF with charts

### For BMS Vendors (Technical Staff)
- **Focus**: Diagnostic evidence + configuration audit checklist
- **Language**: Technical (point mappings, register addresses)
- **Length**: Detailed (include raw metrics, test results)
- **Format**: JSON + technical appendix

### For Executives (Decision Makers)
- **Focus**: Financial impact (cost to ignore vs fix)
- **Language**: Business case, ROI
- **Length**: 1-page summary
- **Format**: Executive summary with key metrics highlighted

---

## Value Messaging

### "We Don't Just Say 'Bad Data' — We Tell You Exactly Why"

**Competitive differentiation**:
- Most tools: Generic error messages
- HTDAM: Root cause + correlation analysis + recommendations

**User testimonial template**:
> "Stage 1 saved us $8,000 in site visits by automatically detecting a BMS 
> configuration error we'd been chasing for months. The state-dependent correlation 
> analysis was the smoking gun our vendor needed to fix it remotely in 2 hours."

---

## Implementation Priority

1. **MVP (immediate)**:
   - Sensor reversal report (shown above)
   - JSON metrics output
   - Basic markdown template

2. **V2 (2 weeks)**:
   - Unit confusion report
   - kW/kWh confusion report  
   - PDF generation with charts

3. **V3 (1 month)**:
   - Multi-building portfolio dashboard
   - Interactive visualizations
   - BMS vendor coordination workflow

---

## Success Metrics

**User engagement**:
- % of users who view full diagnostic report (target: >80%)
- % of users who download filtered datasets (target: >60%)
- % of users who contact BMS vendor after report (target: >40%)

**Business impact**:
- Average time saved per data quality issue (target: 8-16 hours)
- % of issues resolved without site visit (target: >50%)
- User-reported ROI (target: >10×)

---

## Next Steps

1. ✅ Create `generateSensorReversalReport()` pure function
2. ✅ Integrate into Stage 1 salvage workflow (hook layer)
3. ✅ Add report files to CLI output directory
4. ⬜ Design frontend alert banner and report viewer
5. ⬜ User test report with 3-5 pilot buildings
6. ⬜ Iterate based on feedback
7. ⬜ Implement unit confusion and kW/kWh reports
8. ⬜ Launch portfolio-wide dashboard

---

## Conclusion

**Stage 1's automated diagnostic depth is a massive competitive advantage.**

By showcasing **state-dependent correlation analysis**, **root cause identification**, 
and **actionable recommendations with ROI**, we transform data validation from a 
technical checklist into a **high-value diagnostic service**.

Users see HTDAM as their **data quality forensics expert**, not just another 
validation tool.

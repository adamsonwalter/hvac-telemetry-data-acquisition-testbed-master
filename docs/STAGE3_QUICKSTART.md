# Stage 3 Quick Reference

**Fast reference for Stage 3 Timestamp Synchronization**

## One-Line Summary
Synchronizes 5 HVAC streams to uniform 15-min grid using O(N+M) nearest-neighbor alignment.

## Quick Usage

### CLI (Recommended)
```bash
python3 -m src.orchestration.HtdamCLI \
    --input data.csv \
    --chiller-id ChillerA \
    --output-dir ./output/
```

### Python API
```python
from src.hooks.useStage3Synchronizer import use_stage3_synchronizer

df, metrics, halt = use_stage3_synchronizer(
    gap_annotated_signals=stage2_signals,
    exclusion_windows=windows,
    stage2_confidence=0.93
)
```

## Key Outputs

### 1. Synchronized CSV
**File**: `stage3_synchronized.csv`
- **Rows**: ~35,136 (1 year @ 15-min intervals)
- **Columns**: 25 (grid_time + 5 streams × 3 attributes + gap_type + row_confidence)

### 2. Metrics JSON
**File**: `stage3_metrics.json`
```json
{
  "stage3_confidence": 0.88,
  "valid_pct": 93.8,
  "coverage_tier": "GOOD",
  "VALID_count": 32959,
  "MAJOR_GAP_count": 2177
}
```

## Quality Tiers

| Coverage | Tier | Penalty | Confidence Impact |
|----------|------|---------|-------------------|
| ≥95% | EXCELLENT | 0.0 | None |
| ≥90% | GOOD | -0.02 | Small reduction |
| ≥80% | FAIR | -0.05 | Moderate reduction |
| <80% | POOR | -0.10 | Large reduction |

## Alignment Quality

| Label | Distance | Confidence | Meaning |
|-------|----------|------------|---------|
| EXACT | <60s | 1.00 | Precise alignment |
| CLOSE | 60-300s | 0.95 | Acceptable drift |
| INTERP | 300-1800s | 0.80 | Significant drift |
| MISSING | >1800s | 0.00 | No data in tolerance |

## Common Issues

### Low Confidence (<0.80)
**Check**: 
- `valid_pct` in metrics
- `gap_type` distribution in CSV

**Fix**:
- Review Stage 2 gap detection
- Check for missing streams
- Consider exclusion windows

### HALT: Coverage < 50%
**Cause**: More than half grid points are MAJOR_GAP

**Fix**:
1. Verify all 5 streams loaded (Stage 1)
2. Review Stage 2 COV detection
3. Check for large data gaps in raw files

### High Jitter
**Symptom**: Mean jitter > 60s in metrics

**Impact**: Many CLOSE/INTERP quality alignments

**Action**: 
- Review BMS logging consistency
- Check for systematic time drift
- Acceptable if coverage still ≥90%

## HALT Conditions

Stage 3 stops processing if:
1. **Coverage < 50%**: Too much missing data
2. **Entire dataset excluded**: All rows in exclusion windows

HALT prevents unreliable COP calculations in Stage 4.

## Performance Expectations

| Metric | BarTech Data | Typical Range |
|--------|--------------|---------------|
| Processing Time | 1-2s | 0.5-5s |
| Grid Points | 35,136 | 10k-100k |
| Coverage | 93.8% | 85-98% |
| Stage 3 Confidence | 0.88 | 0.75-0.95 |
| Mean Jitter | 12-18s | 5-60s |

## Architecture Quick View

```
Input (Stage 2)           Stage 3                    Output
─────────────────────────────────────────────────────────────
Gap-annotated signals  →  Build master grid      →  Synchronized
(5 × ~35k points)         (35k uniform points)      DataFrame
                                                     (35k × 25 cols)
                       →  Align streams          →  
                          (nearest-neighbor)        Metrics JSON
                          O(N+M) algorithm          (coverage, jitter)
                       
                       →  Classify rows          →
                          (VALID/GAP/EXCLUDED)      row_confidence
                                                    per grid point
```

## Decision Tree: Row Classification

```
1. In exclusion window?
   YES → EXCLUDED (conf=0.0)
   NO  ↓

2. All mandatory streams present?
   (CHWST, CHWRT, CDWRT)
   NO  → MAJOR_GAP (conf=0.0)
   YES ↓

3. Any Stage 2 MAJOR_GAP?
   YES → MAJOR_GAP (conf=0.0)
   NO  ↓

4. VALID (conf = avg quality)
```

## Key Constants

```python
SYNC_TOLERANCE_SECONDS = 1800  # ±30 min
MANDATORY_STREAMS = ['CHWST', 'CHWRT', 'CDWRT']
OPTIONAL_STREAMS = ['FLOW', 'POWER']
T_NOMINAL_SECONDS = 900  # 15-min grid
```

## Next Steps

1. **Validation**: Check stage3_confidence ≥ 0.70
2. **Review**: Inspect gap_type distribution
3. **Proceed**: If no HALT, continue to Stage 4 Signal Preservation

## Full Documentation

See [STAGE3_SYNCHRONIZATION.md](./STAGE3_SYNCHRONIZATION.md) for:
- Complete algorithm details
- Edge case handling (15 scenarios)
- Troubleshooting guide
- Performance benchmarks
- Integration examples

## Files to Inspect

```bash
# Check synchronization quality
head -20 output/stage3_synchronized.csv

# Check metrics
cat output/stage3_metrics.json | jq .

# Count gap types
cut -d, -f17 output/stage3_synchronized.csv | sort | uniq -c
#   32959 VALID
#    2177 MAJOR_GAP
```

## When to HALT Manually

Even if Stage 3 doesn't HALT, consider stopping if:
- Stage 3 confidence < 0.70 (marginal quality)
- VALID coverage < 80% (too many gaps)
- Mean jitter > 120s (BMS logging unstable)
- All optional streams missing (Stage 4 requires FLOW/POWER for COP)

---

**Status**: Production-Ready ✅  
**Version**: HTDAM v2.0  
**Last Updated**: 2024-12-08

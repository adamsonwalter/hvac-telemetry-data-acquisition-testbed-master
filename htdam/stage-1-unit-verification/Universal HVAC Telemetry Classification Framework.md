A **conditional validation heuristic** for certain BMS implementation. Here's how to integrate it into your Stage 1 data validation framework:

## Universal HVAC Telemetry Classification Framework

### Tier 1: Physical Constraint Validation (Equipment-Agnostic)

**Chiller/Cooling Systems**

- CHWRT ≥ CHWST (return must be warmer than supply)
- 0°C < CHWST < 25°C (typical operating range)
- 0°C < Delta_T < 15°C (thermodynamically feasible)
- Flow > 0 when Load > 0 (no cooling without flow)

**Heating Systems**

- HWST ≥ HWRT (supply must be warmer than return)
- 20°C < HWST < 120°C (typical range)

**Air Handling Units**

- Supply Air Temp within physical bounds given mixed air conditions
- Static pressure > 0 when fan enabled
- Outdoor Air % between 0-100%

This tier establishes **hard physics violations** that indicate data quality issues regardless of operational state.[^1][^2]

### Tier 2: Operational State Classification (Context-Aware)

Define equipment operational modes using **multiple concurrent indicators** rather than single thresholds:

**Active Operation State** (data likely valid):

- Load > threshold (equipment-specific: 10% for chillers, 20% for boilers)
- Flow > minimum (e.g., >10% design flow)
- |Delta_T| > minimum meaningful (e.g., >0.5°C)
- Status = enabled/running
- Power draw > standby level

**Standby/Transition State** (data potentially invalid):

- Load ≤ threshold but equipment enabled
- Flow present but minimal
- Temperature signals show lag or instability
- Recent mode changes (<5 minutes)

**Off State** (data may be placeholder):

- Load = 0
- Flow ≈ 0 or constant minimum
- Status = disabled
- Temperatures may be ambient or last-known values

The Chiller 2 case demonstrates that **standby state data can have systematic mapping errors** specific to that BMS configuration .

### Tier 3: Signal Quality Metrics (Statistical)

**Temporal Consistency**

- Rate of change within physical limits (e.g., temp change <5°C/min)
- No excessive oscillation (standard deviation over rolling window)
- Timestamp monotonicity and interval regularity

**Cross-Signal Coherence**

- Load correlates with flow (Pearson r > 0.7 expected)
- Delta_T correlates inversely with flow (higher flow = lower Delta_T)
- Power correlates with load for electrically-driven equipment

**Sensor Health Indicators**

- Not stuck (variance > threshold over window)
- Not drifting (bias relative to peer sensors)
- Not showing digital quantization artifacts (too many repeated values)

These metrics detect sensor failures, communication issues, or data historian problems that affect validity across all operational states.[^2]

### Implementation Architecture

**Stage 1A: Physics-Based Filtering**

```
FOR each equipment type:
  - Apply hard physical constraints
  - Flag violations as INVALID_PHYSICS
  - Confidence: HIGH (these are definitive)
```

**Stage 1B: Operational Context Classification**

```
FOR each sample:
  - Compute operational_state_score (0-10 scale)
  - Weight by multiple indicators:
    * Load > threshold: +3 points
    * Flow > threshold: +3 points  
    * |Delta_T| meaningful: +2 points
    * Status enabled: +1 point
    * Recent stability: +1 point
  
  - Classify as:
    * VALID_HIGH (score ≥ 7): Use for calibration, analysis
    * VALID_MEDIUM (score 4-6): Use with caution
    * QUESTIONABLE (score 2-3): Exclude from training data
    * INVALID (score 0-1): Discard or flag for investigation
```

**Stage 1C: Pattern Recognition for BMS-Specific Issues**

```
FOR each equipment_id over time_window:
  - Detect correlation between operational_state and physics_violations
  - IF violation_rate[standby] >> violation_rate[active]:
    * Flag as "STATE_DEPENDENT_MAPPING_ERROR"
    * Apply conditional filtering rules
    * Log for BMS configuration review
  - ELSE IF violations random:
    * Flag as "SENSOR_MALFUNCTION" 
    * Exclude all data from this sensor
```


### Ontology Integration

Structure your validation metadata using **Brick Schema** or similar ontology:

```turtle
:Chiller_2_CHWST a brick:Leaving_Chilled_Water_Temperature_Sensor ;
    brick:hasQualityFlag [
        a :DataQualityMetric ;
        :validityScore 8.2 ;
        :physicsViolationRate 0.012 ;
        :operationalStateDependency true ;
        :recommendedFilter "exclude_when_load_below_10pct"
    ] .
```

This enables **LLM-extractable knowledge** by encoding validation rules as structured semantic relationships rather than procedural code.[^3]

### Non-Universal Aspects

**Equipment-Specific Thresholds**

- Chiller load minimum: 10% (from this analysis)
- Boiler load minimum: 15-20% (typically higher turndown limits)
- VFD minimum speed: 20-30% (manufacturer-dependent)

**BMS Vendor Behaviors**

- Johnson Controls: known for different point mapping in lead/lag configurations
- Siemens: may use virtual points during commissioning mode
- Tridium Niagara: proxy points can show stale data when equipment offline

**Facility-Specific Calibration**

- Delta_T expectations vary by design (2-6°C typical, but site-specific)
- Flow ranges depend on pipe sizing and pump curves
- "Normal" operating hours inform temporal validity windows

The key insight: **Make the validation framework adaptive and self-documenting**. Your system should **learn** that Chiller 2 has state-dependent mapping issues rather than applying a universal "exclude Load≤10%" rule to all chillers globally. This enables the LLM to generate equipment-specific validation reports that explain *why* certain data was excluded, not just that it was filtered.[^4][^5][^2]
<span style="display:none">[^10][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://www.gxpcellators.com/building-monitoring-systems-benefits-regulatory-requirements-and-validation-strategies/

[^2]: https://www.csemag.com/ways-to-leverage-and-enhance-building-control-system-data/

[^3]: https://patents.google.com/patent/US20140032555A1/en

[^4]: https://www.racefor2030.com.au/content/uploads/0350-AI-buildings-report-v2.pdf

[^5]: https://pmc.ncbi.nlm.nih.gov/articles/PMC9568938/

[^6]: https://fivevalidation.com/hvac-validation/

[^7]: https://www.linkedin.com/pulse/building-management-systems-bms-validation-overview-graham-okeeffe

[^8]: https://www.sciencedirect.com/science/article/abs/pii/S0378778825003238

[^9]: https://nexla.com/data-fabric-architecture/data-automation/

[^10]: https://docs.johnsoncontrols.com/bas/r/Johnson-Controls/en-US/Johnson-Controls-Central-Plant-Optimization-10-Application-Note/Setup-and-commissioning/Configuring-the-Chiller-Selector/Operational-data-for-simulation-and-commissioning-Chiller


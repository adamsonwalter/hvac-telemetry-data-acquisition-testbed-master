# Telemetry Filename Auto-Parsing Specification v1.1

## 1. Overview
This specification defines the logic for automatically classifying HVAC telemetry files based on their filenames. The system identifies the **Feed Type** (e.g., Chilled Water Supply Temperature, Power, Flow) by matching filenames against a prioritized set of Regular Expressions (Regex).

**Purpose:** Enable automated data ingestion from diverse BMS (Building Management System) exports without manual classification.

**Scope:** Chiller plant telemetry covering 5 critical data feeds required for thermodynamic analysis.

---

## 2. Required Feed Types

| Feed Type | Code | Physical Meaning | Typical Units | Criticality |
|-----------|------|------------------|---------------|-------------|
| **Chilled Water Supply Temp** | `CHWST` | Water leaving evaporator (to building) | °C / °F | CRITICAL |
| **Chilled Water Return Temp** | `CHWRT` | Water entering evaporator (from building) | °C / °F | CRITICAL |
| **Condenser Water Return Temp** | `CDWRT` | Water entering condenser (from cooling tower) | °C / °F | CRITICAL |
| **Power** | `POWER` | Total electrical power consumption | kW | CRITICAL |
| **Flow** | `FLOW` | Chilled water volumetric flow rate | L/s, GPM | CRITICAL |

---

## 3. Parsing Algorithm

### 3.1. Normalization
Before pattern matching:
1. **Convert to Uppercase:** `Chiller_1_Power.csv` → `CHILLER_1_POWER.CSV`
2. **Strip File Extension:** `.csv`, `.xlsx`, `.txt` are ignored
3. **Delimiter Agnostic:** Underscores `_`, hyphens `-`, spaces, and dots `.` are treated equivalently

### 3.2. Priority-Based Matching
Patterns are evaluated **sequentially** in the order listed below. The **first match wins**.

> **Critical Design Decision:** CDWRT is checked first because `COND` or `CDW` are highly specific, whereas generic terms like `SUPPLY` or `RETURN` could appear in non-chiller contexts.

---

## 4. Pattern Definitions

### 4.1. Priority 1: Condenser Water Return Temperature (CDWRT)
**Physical Context:** Temperature of water returning from the cooling tower to the condenser.

**Regex Pattern:**
```regex
/COND|CDW/
```

**Rationale:** Condenser-related terms are highly specific and unlikely to appear in chilled water or power feeds.

**Example Matches:**
- ✅ `Chiller_1_Condenser_Water_Return_Temp.csv`
- ✅ `CDW_RT_Sensor.csv`
- ✅ `Cooling_Tower_Condenser_Inlet.csv`

**Example Non-Matches:**
- ❌ `CHW_Supply_Temp.csv` (No condenser reference)
- ❌ `Power_Consumption.csv` (No condenser reference)

---

### 4.2. Priority 2: Chilled Water Supply Temperature (CHWST)
**Physical Context:** Temperature of water leaving the chiller (to the building's cooling coils).

**Regex Pattern:**
```regex
/CHW.*SUPPLY|CHWST|CHW.*ST|SUPPLY.*TEMP|LEAVING.*TEMP|CHW.*LEAV/
```

**Rationale:** Captures industry-standard acronyms (CHWST, LWT) and common BMS naming conventions.

**Example Matches:**
- ✅ `CHW_Supply_Temp.csv`
- ✅ `CHWST_Sensor_1.csv`
- ✅ `Chiller_Leaving_Water_Temp.csv`
- ✅ `CHW_ST_Building_A.csv`
- ✅ `Supply_Temp_Chilled_Water.csv`

**Example Non-Matches:**
- ❌ `CHW_Return_Temp.csv` (Contains `RETURN`, not `SUPPLY`)
- ❌ `Condenser_Supply.csv` (Matched by CDWRT first)

**Ambiguity Handling:**
- If filename contains both `SUPPLY` and `RETURN`, the first occurrence determines classification.
- Example: `CHW_Supply_and_Return.csv` → Matches CHWST (Supply appears first in pattern).

---

### 4.3. Priority 3: Chilled Water Return Temperature (CHWRT)
**Physical Context:** Temperature of water entering the chiller (from the building's cooling coils).

**Regex Pattern:**
```regex
/CHW.*RETURN|CHWRT|CHW.*RT|RETURN.*TEMP|ENTERING.*TEMP|CHW.*ENT/
```

**Rationale:** Mirrors CHWST logic but for return/entering side.

**Example Matches:**
- ✅ `CHW_Return_Temp.csv`
- ✅ `CHWRT_Sensor.csv`
- ✅ `Chiller_Entering_Water_Temp.csv`
- ✅ `CHW_RT_Floor_12.csv`
- ✅ `Return_Temp_Chilled_Water.csv`

**Example Non-Matches:**
- ❌ `CHW_Supply_Temp.csv` (Matched by CHWST)
- ❌ `Condenser_Return.csv` (Matched by CDWRT first)

---

### 4.4. Priority 4: Power
**Physical Context:** Total electrical power consumption of the chiller.

**Regex Pattern:**
```regex
/POWER|KW|KILOWATT|WATT|ENERGY|ELEC|DEMAND|LOAD/
```

**Rationale:** Broad pattern to capture various BMS naming conventions for electrical consumption.

**Example Matches:**
- ✅ `Chiller_Power_Consumption.csv`
- ✅ `Total_kW.csv`
- ✅ `Electrical_Demand.csv`
- ✅ `Energy_Meter_Chiller_1.csv`
- ✅ `Active_Power_kW.csv`

**Example Non-Matches:**
- ❌ `CHW_Flow_Rate.csv` (No power-related terms)
- ❌ `Cooling_Load_Tons.csv` (Thermal load, not electrical power)

**Known Ambiguity:**
- `LOAD` can refer to electrical load (power) OR thermal load (cooling capacity).
- **Current Behavior:** `LOAD` is classified as **Power**.
- **Recommendation:** If thermal load is needed, use explicit terms like `COOLING_LOAD` or `TONS` and add a separate pattern.

---

### 4.5. Priority 5: Flow
**Physical Context:** Volumetric flow rate of chilled water through the evaporator.

**Regex Pattern:**
```regex
/FLOW|GPM|LPS|L\/S|LITRE|GALLON|RATE/
```

**Rationale:** Captures both generic `FLOW` and unit-specific terms (GPM, LPS).

**Example Matches:**
- ✅ `CHW_Flow_Rate.csv`
- ✅ `Flow_Sensor_GPM.csv`
- ✅ `Chiller_LPS.csv`
- ✅ `Water_Flow_L_per_S.csv`

**Example Non-Matches:**
- ❌ `CHW_Supply_Temp.csv` (No flow-related terms)
- ❌ `Power_Demand.csv` (No flow-related terms)

**Known Ambiguity:**
- `RATE` is generic and could refer to flow rate, heat rate, etc.
- **Current Behavior:** `RATE` alone triggers Flow classification.
- **Recommendation:** Combine with context keywords (e.g., `FLOW_RATE`, `WATER_RATE`).

---

## 5. Edge Cases & Handling

### 5.1. Ambiguous Filenames
**Scenario:** Filename contains keywords from multiple categories.

**Example:** `Chiller_Power_Supply_Temp.csv`
- Contains `POWER` (Priority 4) and `SUPPLY` (Priority 2)
- **Result:** Classified as **CHWST** (Priority 2 is checked before Priority 4)

**Mitigation:** Users should use more specific naming conventions or manually override classification.

---

### 5.2. Unknown/Unclassified Files
**Scenario:** Filename doesn't match any pattern.

**Example:** `Chiller_Status.csv`, `Alarm_Log.csv`
- **Result:** Returns `null` (Unknown)
- **User Action Required:** Manual classification via UI dropdown

---

### 5.3. Multiple Chillers
**Scenario:** Filenames include unit identifiers (e.g., `Chiller_1`, `CH-02`).

**Example:** `Chiller_1_CHW_Supply_Temp.csv`
- **Result:** Correctly classified as **CHWST**
- **Note:** Unit identifiers are ignored by the regex (treated as wildcards)

---

### 5.4. Non-English Naming
**Current Limitation:** Patterns are English-only.

**Example:** `Temperatura_Suministro_Agua.csv` (Spanish for "Supply Water Temperature")
- **Result:** Returns `null` (Unknown)
- **Future Enhancement:** Add multi-language pattern sets

---

## 6. Common BMS Naming Conventions

### 6.1. Honeywell
- `CHWST`: `CHW_Supply_Temp`, `CHWST_Sensor`
- `CHWRT`: `CHW_Return_Temp`, `CHWRT_Sensor`
- `CDWRT`: `CDW_Return_Temp`, `Condenser_Inlet`
- `Power`: `Chiller_kW`, `Power_Consumption`
- `Flow`: `CHW_Flow_GPM`, `Flow_Sensor`

### 6.2. Johnson Controls (Metasys)
- `CHWST`: `Leaving_Chilled_Water_Temp`, `LWT`
- `CHWRT`: `Entering_Chilled_Water_Temp`, `EWT`
- `CDWRT`: `Condenser_Water_Return`, `CWT_Return`
- `Power`: `Electrical_Demand_kW`, `Active_Power`
- `Flow`: `CHW_Flow_Rate`, `GPM_Sensor`

### 6.3. Siemens (Desigo)
- `CHWST`: `CHW_ST`, `Supply_Temp`
- `CHWRT`: `CHW_RT`, `Return_Temp`
- `CDWRT`: `CDW_RT`, `Condenser_Temp`
- `Power`: `Power_kW`, `Energy_Meter`
- `Flow`: `Flow_LPS`, `Water_Flow`

### 6.4. Trane (Tracer)
- `CHWST`: `CHWST`, `Leaving_Water_Temp`
- `CHWRT`: `CHWRT`, `Entering_Water_Temp`
- `CDWRT`: `Condenser_Entering_Temp`, `CWT`
- `Power`: `Chiller_Power`, `kW_Input`
- `Flow`: `Evap_Flow`, `CHW_Flow`

---

## 7. Critical Data Quality Traps

### 7.1. "Unix Zero" Timestamps (NOT Real Unix Time)

**Trap for Young Players**: BMS exports often contain timestamp columns labeled with misleading names like "unix_time", "timestamp", or numeric values that look like Unix timestamps but ARE NOT.

#### What It Actually Is

**NOT** a true Unix timestamp (seconds since 1970-01-01 00:00:00 UTC).

**IS** a serial index: Ticks since some local zero point:
- Start of export window
- BMS controller epoch (e.g., controller boot time)
- Internal reference time specific to that building/system

#### Real-World Example

```csv
save_time,value
0,45.2
300,45.8
600,46.1
900,46.5
```

This looks like Unix time, but:
- `0` → NOT January 1, 1970
- `0` → Start of THIS export or THIS controller's reference
- `Δt = 300` → 5-minute sampling interval

#### How to Handle It

1. **Treat as ordered time index**:
   - First column is sample order, not absolute time
   - Preserve ordering
   
2. **Calculate sample interval**:
   ```python
   delta_t = df['save_time'].diff().median()
   # If delta_t ≈ 300 → 5-minute data
   # If delta_t ≈ 900 → 15-minute data
   ```

3. **Anchor to real time** (if needed):
   - Check for companion files with real timestamps
   - Look for BMS export metadata (export date/time)
   - Check filename for date information
   - Use building operational context ("this is Monday morning data")

4. **Reconstruct absolute timestamps**:
   ```python
   # Option A: From export metadata
   export_start = pd.Timestamp('2025-11-27 00:00:00')
   df['real_time'] = export_start + pd.to_timedelta(df['save_time'], unit='s')
   
   # Option B: From first sample anchor
   anchor_time = pd.Timestamp('2025-11-27 08:00:00')  # Known start
   df['real_time'] = anchor_time + pd.to_timedelta(
       df['save_time'] - df['save_time'].iloc[0], 
       unit='s'
   )
   ```

#### Consequences of Getting This Wrong

❌ **If interpreted as true Unix time**:
- Wildly wrong absolute times (decades in the past/future)
- Wrong daily cycles (peak demand at 3am instead of 3pm)
- Wrong energy integrals (multiply by seconds → huge errors)
- Broken time-of-day analysis
- Failed correlations with weather/occupancy

✅ **Correct approach**:
- Use for ordering and interval calculation
- Don't use for absolute time without anchoring
- Document the zero point in metadata

#### Detection Heuristics

```python
def is_unix_zero_timestamp(series: pd.Series) -> bool:
    """
    Detect if timestamp column is 'unix zero' (local reference).
    
    Indicators:
    - Starts at or near 0
    - Regular intervals (300, 900, 1800 common)
    - Much smaller than current Unix time (~1.7 billion)
    """
    min_val = series.min()
    max_val = series.max()
    span = max_val - min_val
    
    # True Unix time for recent data should be > 1.6 billion
    if max_val < 1_000_000_000:
        return True  # Definitely not real Unix time
    
    # Starts near zero?
    if min_val < 1_000_000:
        return True
    
    # Span is small (< 1 year in seconds)?
    if span < 31_536_000:
        # Could be legitimate short export
        # Check if intervals are regular
        intervals = series.diff().dropna()
        if intervals.std() < 10:  # Very regular
            return True  # Likely serial index
    
    return False  # Probably real Unix time
```

#### Vendor-Specific Patterns

**BarTech**: 
- Column: `save_time`
- Pattern: Starts at 0 or small value
- Interval: Typically 300s (5 min) or 900s (15 min)
- **NOT real Unix time**

**Trend BMS**:
- May use "seconds since controller start"
- Resets on controller reboot
- Requires anchor from export metadata

**Siemens Desigo**:
- Sometimes uses "relative time" for efficiency
- Export header may contain real start time

**Honeywell**:
- Usually provides real timestamps
- But watch for "log index" columns

#### Validation Checklist

- [ ] Check if timestamp values are reasonable for current date
- [ ] Verify first value (if near 0 → likely not real Unix time)
- [ ] Calculate interval statistics (should be consistent)
- [ ] Look for metadata/headers with real export time
- [ ] Test: Convert to datetime and verify year is reasonable

#### References

This trap was discovered in real production data where:
- Site: BarTech export
- Column: `save_time`
- Quote: *"it's not the normal timeframe… it's a unique serial… it took me a while to figure that out…"*

---

## 8. Implementation Reference

### 7.1. TypeScript/JavaScript
```typescript
type FeedType = 'CHWST' | 'CHWRT' | 'CDWRT' | 'POWER' | 'FLOW';

const detectFeedType = (filename: string): FeedType | null => {
    const name = filename.toUpperCase();

    // Priority 1: Condenser Water Return Temperature
    if (name.match(/COND|CDW/)) return 'CDWRT';

    // Priority 2: Chilled Water Supply Temperature
    if (name.match(/CHW.*SUPPLY|CHWST|CHW.*ST|SUPPLY.*TEMP|LEAVING.*TEMP|CHW.*LEAV/)) return 'CHWST';

    // Priority 3: Chilled Water Return Temperature
    if (name.match(/CHW.*RETURN|CHWRT|CHW.*RT|RETURN.*TEMP|ENTERING.*TEMP|CHW.*ENT/)) return 'CHWRT';

    // Priority 4: Power
    if (name.match(/POWER|KW|KILOWATT|WATT|ENERGY|ELEC|DEMAND|LOAD/)) return 'POWER';

    // Priority 5: Flow
    if (name.match(/FLOW|GPM|LPS|L\/S|LITRE|GALLON|RATE/)) return 'FLOW';

    return null; // Unknown
};
```

### 7.2. Python
```python
import re
from typing import Optional

def detect_feed_type(filename: str) -> Optional[str]:
    name = filename.upper()
    
    # Priority 1: CDWRT
    if re.search(r'COND|CDW', name):
        return 'CDWRT'
    
    # Priority 2: CHWST
    if re.search(r'CHW.*SUPPLY|CHWST|CHW.*ST|SUPPLY.*TEMP|LEAVING.*TEMP|CHW.*LEAV', name):
        return 'CHWST'
    
    # Priority 3: CHWRT
    if re.search(r'CHW.*RETURN|CHWRT|CHW.*RT|RETURN.*TEMP|ENTERING.*TEMP|CHW.*ENT', name):
        return 'CHWRT'
    
    # Priority 4: Power
    if re.search(r'POWER|KW|KILOWATT|WATT|ENERGY|ELEC|DEMAND|LOAD', name):
        return 'POWER'
    
    # Priority 5: Flow
    if re.search(r'FLOW|GPM|LPS|L/S|LITRE|GALLON|RATE', name):
        return 'FLOW'
    
    return None  # Unknown
```

---

## 9. Validation & Testing

### 9.1. Test Cases
```typescript
// Should match CDWRT
assert(detectFeedType('Condenser_Water_Return.csv') === 'CDWRT');
assert(detectFeedType('CDW_RT.csv') === 'CDWRT');

// Should match CHWST
assert(detectFeedType('CHW_Supply_Temp.csv') === 'CHWST');
assert(detectFeedType('Leaving_Water_Temp.csv') === 'CHWST');

// Should match CHWRT
assert(detectFeedType('CHW_Return_Temp.csv') === 'CHWRT');
assert(detectFeedType('Entering_Water_Temp.csv') === 'CHWRT');

// Should match POWER
assert(detectFeedType('Chiller_Power_kW.csv') === 'POWER');
assert(detectFeedType('Electrical_Demand.csv') === 'POWER');

// Should match FLOW
assert(detectFeedType('CHW_Flow_GPM.csv') === 'FLOW');
assert(detectFeedType('Water_Flow_Rate.csv') === 'FLOW');

// Should return null
assert(detectFeedType('Chiller_Status.csv') === null);
assert(detectFeedType('Alarm_Log.csv') === null);
```

### 9.2. Validation Rules
After classification, validate the data:
1. **Temperature Feeds (CHWST, CHWRT, CDWRT):**
   - Range: -10°C to 50°C (14°F to 122°F)
   - Reject if >90% of values are outside this range
2. **Power Feed:**
   - Range: 0 kW to 10,000 kW (typical chiller range)
   - Reject if negative values or >95% zeros
3. **Flow Feed:**
   - Range: 0 to 1,000 L/s (0 to 15,850 GPM)
   - Reject if negative values or >95% zeros

---

## 10. Future Enhancements

### 10.1. Confidence Scoring
Instead of binary match/no-match, assign confidence scores:
- **High Confidence (90-100%):** Exact acronym match (e.g., `CHWST`)
- **Medium Confidence (60-89%):** Partial match (e.g., `CHW_Supply`)
- **Low Confidence (30-59%):** Generic match (e.g., `Supply_Temp`)

### 10.2. Multi-Language Support
Add pattern sets for:
- Spanish: `SUMINISTRO` (Supply), `RETORNO` (Return)
- French: `ALIMENTATION` (Supply), `RETOUR` (Return)
- German: `VORLAUF` (Supply), `RÜCKLAUF` (Return)

### 10.3. Machine Learning Classifier
Train a model on labeled BMS exports to handle:
- Non-standard naming conventions
- Typos and abbreviations
- Context-dependent classification

---

## 11. Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.2 | 2025-12-07 | Added Section 7: Critical Data Quality Traps - "Unix Zero" timestamps detection and handling |
| 1.1 | 2025-11-27 | Added examples, edge cases, BMS conventions, validation rules, Python implementation |
| 1.0 | 2025-11-27 | Initial specification |

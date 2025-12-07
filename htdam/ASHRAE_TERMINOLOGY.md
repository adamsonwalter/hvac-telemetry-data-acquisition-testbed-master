# ASHRAE Standard Terminology Mapping
## Flexible Pattern Matching for HVAC Sensor Names

**Purpose**: Normalize vendor-specific column names to ASHRAE standard terminology for consistent HTDAM processing.

**Reference**: ASHRAE Standard 30-2019 (Method of Testing Liquid Chillers), ASHRAE 90.1-2019 (Energy Standard)

---

## Core Bare Minimum Data (BMD) Parameters

### Temperature Sensors

| ASHRAE Standard | Alternative Names | Pattern Matching |
|-----------------|-------------------|------------------|
| **CHWST** | CHW Supply Temp, Chilled Water Supply Temperature, CHW Supply, CHWST, Leaving Chilled Water Temp, LWT | `(?i)(chw|chilled.*water).*(supply|leaving|st)` |
| **CHWRT** | CHW Return Temp, Chilled Water Return Temperature, CHW Return, CHWRT, Entering Chilled Water Temp, EWT | `(?i)(chw|chilled.*water).*(return|entering|rt)` |
| **CDWST** | CDW Supply Temp, Condenser Water Supply Temperature, CW Supply, CWST, Entering Condenser Water Temp | `(?i)(cdw|cw|cond.*water).*(supply|entering|st)` |
| **CDWRT** | CDW Return Temp, Condenser Water Return Temperature, CW Return, CWRT, Leaving Condenser Water Temp | `(?i)(cdw|cw|cond.*water).*(return|leaving|rt)` |

### Flow Sensors

| ASHRAE Standard | Alternative Names | Pattern Matching |
|-----------------|-------------------|------------------|
| **CHWF** | CHW Flow, Chilled Water Flow Rate, Flow Rate, GPM, L/s, m³/h, Evaporator Flow | `(?i)(chw|chilled.*water|evap).*(flow|gpm|l/s)` |
| **CDWF** | CDW Flow, Condenser Water Flow Rate, CW Flow, Condenser Flow | `(?i)(cdw|cw|cond.*water).*(flow|gpm|l/s)` |

### Power Sensors

| ASHRAE Standard | Alternative Names | Pattern Matching |
|-----------------|-------------------|------------------|
| **POWER** | Demand Kilowatts, Power, kW, Electrical Power, Total Power, Chiller Power, Input Power | `(?i)(power|kilowatt|kw|demand.*kw)` |

---

## Extended HVAC Parameters (Stage 4+)

### Control Signals

| ASHRAE Standard | Alternative Names | Pattern Matching |
|-----------------|-------------------|------------------|
| **GUIDE_VANE** | Guide Vane Position, Actual Guide Vane Position, Vane Position, IGV Position, Inlet Guide Vane | `(?i)(guide.*vane|igv|vane.*pos)` |
| **VFD_SPEED** | VFD Speed, Variable Speed, Compressor Speed, Motor Speed | `(?i)(vfd|variable.*speed|motor.*speed)` |
| **VALVE_POS** | Valve Position, Control Valve, Modulating Valve | `(?i)valve.*(pos|position)` |

### Compressor Parameters

| ASHRAE Standard | Alternative Names | Pattern Matching |
|-----------------|-------------------|------------------|
| **COMP_DISCHARGE_TEMP** | Comp Discharge Temp, Compressor Discharge Temperature, Discharge Temp | `(?i)comp.*(discharge|disch).*(temp|t)` |
| **COMP_MOTOR_TEMP** | Comp Motor Winding Temp, Motor Winding Temperature, Motor Temp | `(?i)(comp.*motor|motor.*wind).*(temp|t)` |
| **COMP_CURRENT** | Actual Line Current, Compressor Current, Motor Current, Avg Line Current | `(?i)(comp|motor|line).*(current|amp)` |

### Refrigerant Parameters

| ASHRAE Standard | Alternative Names | Pattern Matching |
|-----------------|-------------------|------------------|
| **EVAP_REFRIG_PRESS** | Evap Refrigerant Press, Evaporator Pressure, Suction Pressure | `(?i)evap.*(refrig|refrigerant).*(press|psi)` |
| **EVAP_REFRIG_TEMP** | Evap Refrigerant Temp, Evaporator Temperature, Suction Temp | `(?i)evap.*(refrig|refrigerant).*(temp|t)` |
| **COND_REFRIG_PRESS** | Cond Refrigerant Press, Condenser Pressure, Discharge Pressure | `(?i)cond.*(refrig|refrigerant).*(press|psi)` |
| **COND_REFRIG_TEMP** | Cond Refrigerant Temp, Condenser Temperature, Discharge Temp | `(?i)cond.*(refrig|refrigerant).*(temp|t)` |

### Performance Metrics

| ASHRAE Standard | Alternative Names | Pattern Matching |
|-----------------|-------------------|------------------|
| **EVAP_APPROACH** | Evap Approach, Evaporator Approach Temperature | `(?i)evap.*(approach)` |
| **COND_APPROACH** | Cond Approach, Condenser Approach Temperature | `(?i)cond.*(approach)` |
| **SETPOINT** | Setpoint, CHW Setpoint, LCW Setpoint, Target Temperature | `(?i)(setpoint|target|set.*point)` |

---

## Unit Normalization

### Temperature Units

| Detected Unit | Conversion to °C | Detection Pattern |
|---------------|------------------|-------------------|
| **°F** | `(T - 32) × 5/9` | Value range 32-212 (water range), or explicit "F", "°F" in column name |
| **K** | `T - 273.15` | Value range 273-373 (water range), or explicit "K", "Kelvin" in column name |
| **°C** | Pass-through | Value range 0-100 (water range), or explicit "C", "°C" in column name |

### Flow Units

| Detected Unit | Conversion to m³/s | Detection Pattern |
|---------------|-------------------|-------------------|
| **L/s** | `÷ 1000` | Column name contains "L/s", "LPS", or range 10-500 (typical chiller) |
| **GPM** | `× 0.00006309` | Column name contains "GPM", "gpm", or range 50-2000 (US typical) |
| **m³/h** | `÷ 3600` | Column name contains "m³/h", "m3/h", or range 500-10000 |
| **m³/s** | Pass-through | Column name contains "m³/s", "m3/s", or range <1 |

### Power Units

| Detected Unit | Conversion to kW | Detection Pattern |
|---------------|-------------------|-------------------|
| **W** | `÷ 1000` | Column name contains " W" (with space), or range >10000 |
| **kW** | Pass-through | Column name contains "kW", "kilowatt", or range 50-5000 (typical) |
| **MW** | `× 1000` | Column name contains "MW", "megawatt", or range <10 |

---

## Header Detection Algorithm

### Strategy: Investigate First 3 Rows

```python
def detect_header_row(df_no_header: pd.DataFrame) -> int:
    """
    Detect which of first 3 rows is the actual header.
    
    Header row characteristics:
    1. Has multiple non-null values (≥50% columns filled)
    2. Contains sensor-like names (keywords: temp, flow, power, vane, pressure)
    3. NOT all dates/timestamps (that would be data row)
    4. NOT all numeric (that would be data row)
    5. NOT units-only row (e.g., "°C", "L/s", "kW")
    
    Returns:
        header_row_index: 0, 1, or 2
    """
    pass
```

**Example from Monash Dataset**:
```
Row 0: "Chiller 1", NaN, NaN, ...           → Title row (sparse)
Row 1: "Location:", "Monash University...", → Metadata row (prose)
Row 2: "Date", "Actual Line Current", ...   → HEADER ROW ✓ (sensor names)
Row 3: 2025-09-03 23:00:00, 0, 0, ...       → Data row (mixed types)
```

**Decision**: Row 2 is header (keyword match + density + type variety).

---

## Pattern Matching Implementation

### Fuzzy Matching Strategy

**Priority Order**:
1. **Exact Match** (case-insensitive): "CHWST" → CHWST ✓
2. **Regex Pattern Match**: "CHW Supply Temp" → CHWST ✓
3. **Fuzzy String Match** (Levenshtein distance): "CHWS" → CHWST (distance=1) ✓
4. **Keyword Intersection**: "Chilled Water Temperature Supply" → CHWST (keywords: chilled, water, supply, temp)

**Confidence Scoring**:
- Exact match: confidence = 1.0
- Regex match: confidence = 0.95
- Fuzzy match (distance ≤ 2): confidence = 0.85
- Keyword match (≥3 keywords): confidence = 0.75
- Ambiguous: confidence < 0.7 → flag for manual review

### Example Mappings

**Real-world column names** → **ASHRAE standard**:

| Original | ASHRAE | Confidence | Method |
|----------|--------|-----------|--------|
| CHWST | CHWST | 1.00 | Exact |
| CHW Supply Temp | CHWST | 0.95 | Regex |
| Chilled Water Supply Temperature | CHWST | 0.95 | Regex |
| Leaving Chilled Water Temp | CHWST | 0.90 | Regex + keyword |
| LWT | CHWST | 0.75 | Keyword (leaving water temp) |
| Demand Kilowatts | POWER | 0.95 | Regex |
| Guide Vane Position | GUIDE_VANE | 0.95 | Regex |

---

## Timestamp Column Detection

### Patterns to Match

| Pattern Type | Examples | Regex |
|-------------|----------|-------|
| **Explicit** | "Date", "Time", "Timestamp", "DateTime" | `(?i)(date|time|timestamp|datetime)` |
| **Compound** | "Date Time", "Date/Time", "Date_Time" | `(?i)date.*(time|stamp)` |
| **Abbreviated** | "DT", "TS" | `^(DT|TS)$` |
| **Positional** | First column (if no name match) | column_index == 0 AND dtype datetime-like |

### Validation

After detection, validate:
1. Parse as datetime (pandas `pd.to_datetime`)
2. Check monotonicity: `series.is_monotonic_increasing` (≥95% increasing)
3. Check reasonable range: 2020-2030 for current datasets
4. Check density: not all null, ≥80% valid timestamps

---

## Usage in HTDAM Stage 1

### Workflow

```python
# 1. Load XLSX with flexible header detection
df_raw, metadata = parse_hvac_xlsx("chiller_1_2025.xlsx", sheet_name="2025")

# 2. Normalize column names to ASHRAE
normalized_columns = {
    "CHW Supply Temp": "CHWST",
    "Demand Kilowatts": "POWER",
    ...
}
df_normalized = df_raw.rename(columns=normalized_columns)

# 3. Verify required BMD parameters
bmd_required = ["CHWST", "CHWRT", "CDWRT", "CHWF", "POWER"]
bmd_present = [col for col in bmd_required if col in df_normalized.columns]
bmd_missing = [col for col in bmd_required if col not in df_normalized.columns]

# 4. Stage 1 unit verification
for col in bmd_present:
    if col in ["CHWST", "CHWRT", "CDWRT"]:
        result = verify_temperature_unit(df_normalized[col], col)
    elif col == "CHWF":
        result = verify_flow_unit(df_normalized[col])
    elif col == "POWER":
        result = verify_power_unit(df_normalized[col])
```

---

## Ambiguity Handling

### Common Ambiguous Cases

**Case 1: "Supply Temp" without context**
- Could be: CHWST, CDWST, or heating supply
- **Resolution**: Check other columns for context
  - If "Return Temp" nearby → likely CHW or CDW pair
  - If "Flow" column present → likely CHW (primary circuit)
  - If "Condenser" keyword elsewhere → likely CDWST
- **Action**: Flag for manual review if confidence < 0.7

**Case 2: "Flow" without circuit specification**
- Could be: CHWF or CDWF
- **Resolution**: 
  - Check value range (CHW typically lower flow than CDW)
  - Check if other CHW params present (CHWST/CHWRT) → likely CHWF
  - Default to CHWF (primary circuit assumption)

**Case 3: Multiple temperature columns with similar names**
- Example: "Temp 1", "Temp 2", "Temp 3", "Temp 4"
- **Resolution**: Cannot auto-resolve
- **Action**: Flag entire dataset for manual column mapping

---

## Validation Rules

### Post-Normalization Checks

**Temperature Consistency**:
- If CHWST and CHWRT both present → CHWRT > CHWST for ≥95% of time
- If CDWRT present → CDWRT > CHWST for ≥95% (positive lift)

**Range Plausibility**:
- CHWST: 3-20°C (typical chiller range)
- CHWRT: 5-25°C
- CDWRT: 15-35°C (ambient dependent)
- CHWF: >0, typically 10-500 L/s for commercial chillers
- POWER: >0, typically 50-5000 kW for commercial chillers

**Cross-Parameter Logic**:
- If POWER and CHWF both present → can compute COP (good)
- If POWER missing but CHWF present → cannot compute COP (flag)
- If both missing → degraded dataset, temperature analysis only

---

## Future Extensions

### Stage 4+ Parameters (Not BMD, but useful)

Additional sensors to normalize:
- Ambient temperature (for approach calculations)
- Humidity sensors
- Pump speeds (CHWP, CDWP)
- Tower fan speeds
- Pressure sensors (differential pressure)
- Fouling indicators

### Multi-Language Support

Add terminology mappings for:
- Chinese BMS systems (华氏度 → °F, etc.)
- German systems (Vorlauftemperatur → supply temp)
- French systems (température de départ → supply temp)

---

## Reference Implementation

**Pure Function**: `normalizeColumnNames.py`

```python
def normalize_column_names(
    columns: List[str],
    mapping_table: Dict[str, List[str]]
) -> Tuple[Dict[str, str], Dict]:
    """
    Pure function: Map raw column names to ASHRAE standard.
    
    Args:
        columns: List of raw column names from XLSX/CSV
        mapping_table: ASHRAE terminology lookup table
    
    Returns:
        Tuple of:
        - column_mapping: Dict[original_name, ashrae_name]
        - metadata: Dict with confidence scores and ambiguities
    """
    pass
```

---

## Summary

**ASHRAE Normalization** ensures:
1. ✅ Consistent terminology across all vendors/systems
2. ✅ Flexible pattern matching (handles variations gracefully)
3. ✅ Confidence scoring (flags ambiguous mappings)
4. ✅ Validation logic (cross-checks plausibility)
5. ✅ BMD completeness checking (reports missing critical parameters)

**Result**: HTDAM Stage 1 can ingest XLSX files with ANY column naming convention and produce standardized BMD datasets.

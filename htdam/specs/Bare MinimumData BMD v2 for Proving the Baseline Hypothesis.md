### Minimum Bare Data for Proving the Baseline Hypothesis

**Baseline Hypothesis**
“In the future it is not possible to save at least 7% in the chiller system using standard efficiency improvements due to the system’s current mechanical and thermal limitations.”

***

## 1. Core Required Measurements (5 parameters)

These are the **irreducible** measurements required by physics, thermodynamics, and ASHRAE methods to rigorously test the baseline hypothesis.


| Parameter | Symbol | Unit | Why It’s Critical | ASHRAE Reference |
| :-- | :-- | :-- | :-- | :-- |
| CHW Supply Temp | CHWST | °C | Required for chilled-water temperature difference $\Delta T$ | ASHRAE 30-2019 §9.1.2 |
| CHW Return Temp | CHWRT | °C | Required for $\Delta T$ calculation | ASHRAE 30-2019 §9.1.2 |
| CHW Flow Rate | $\dot{V}_{\text{chw}}$ | L/s or GPM | **MANDATORY** for cooling capacity calculation | ASHRAE 30-2019 §9.1.6 |
| Electrical Power | $W_{\text{input}}$ | kW | **MANDATORY** for COP and kW/ton calculation | ASHRAE 30-2019 §9.1.3 |
| Condenser Return Temp | CDWRT | °C | Required to infer lift and evaluate part-load performance | ASHRAE 90.1-2019 §6.4.1.2.1 |

From these 5, you also derive:

- **LOAD** (cooling capacity) $\dot{Q}$
- **COP** (coefficient of performance)

So in practice the “bare minimum dataset” is:

- Measured: CHWST, CHWRT, CHW Flow, Power, CDWRT
- Derived: $\Delta T$, LOAD, COP

***

## 2. Physics Verification

### Cooling Capacity Calculation (Mandatory)

Cooling capacity is given by:

$$
\dot{Q} = \dot{m} \, c_p \, \Delta T
$$

Where:

- $\dot{Q}$ = cooling capacity (kW)
- $\dot{m}$ = mass flow rate (kg/s) = $\dot{V} \times \rho$
- $\dot{V}$ = CHW flow rate (m³/s)
- $\rho$ = water density (≈ 1,000 kg/m³ for HVAC ranges)
- $c_p$ = specific heat of water (≈ 4.186 kJ/kg·K)
- $\Delta T = \text{CHWRT} - \text{CHWST}$

Without **FLOW**, $\dot{Q}$ is unknown and cannot be computed from temperatures alone.

### COP Calculation (Mandatory for hypothesis testing)

Coefficient of performance:

$$
\text{COP} = \frac{\dot{Q}}{W_{\text{input}}}
$$

Where:

- $\dot{Q}$ = cooling capacity from above
- $W_{\text{input}}$ = electrical input power (kW)

To test “≥ 7% improvement”, you must be able to:

- Compute present COP at given operating points
- Compare against baseline/design COP or a calibrated reference
- Quantify improvement in COP after standard measures (setpoint reset, staging, tower optimization, etc.)

If **COP cannot be calculated**, the baseline hypothesis cannot be **proven or rejected** in a physically rigorous way; only qualitative guesses are possible.

***

## 3. Thermodynamic Verification (Part-Load Behaviour)

Part-load efficiency is central to the baseline hypothesis. At low loading, chillers suffer strong COP penalties; whether this is an **efficiency opportunity** or a **hard mechanical limit** depends on:

- **Flow rate**: confirms actual tonnage being delivered
- **Power**: confirms actual electrical effort for that tonnage
- **CHWST/CHWRT**: confirms that the heat balance makes sense (no major sensor faults)
- **CDWRT**: provides a proxy for condenser temperature and lift

From these, you can distinguish scenarios such as:

- **Efficiency opportunity**
    - Low building load
    - Chiller operating far down its part-load curve
    - Normal temperatures and reasonable lift
    - ⇒ Standard measures (staging, setpoint reset, tower optimization) can plausibly deliver ≥ 7%
- **Mechanical/thermal limitation**
    - Abnormal lift or temperatures for the load
    - Indications of fouling or degraded heat transfer
    - Performance close to what physics and manufacturer curves predict even after optimization
    - ⇒ Standard efficiency tweaks alone may not reach 7%; mechanical work required

Concrete example in principle (not tied to any particular dataset):
At **very low effective loading** (e.g. guide vane or VFD speed in the bottom part-load region), actual part-load COP can **only** be verified if:

- Flow rate is known (tonnage)
- Power is measured (kW)
- Temperatures are measured (CHWST/CHWRT, CDWRT) to verify thermal performance

Without flow, two fundamentally different explanations are indistinguishable:

- Low load with inefficient control (efficiency opportunity)
- Flow restriction or other mechanical problem (hard limitation)

***

## 4. ASHRAE Method Requirements (Field Performance)

**ASHRAE Standard 30-2019 – Method of Testing Liquid Chillers**

- §9.1.2: *“Net refrigerating capacity shall be identified (kW [tonR]).”*
- §9.1.3: *“Total input power to chiller shall be identified (kW).”*
- §9.1.6: *“Chilled-liquid flow rate (L/s or m³/h [gpm]) at entering heat exchanger conditions.”*
- §9.1.7: *“Temperature and pressure measurements shall be made at points that reflect gross refrigerating capacity.”*

**ASHRAE 90.1-2019 – Energy Standard**

- Uses these quantities (capacity, power, temperatures) for **performance verification** and **efficiency compliance**.

These standards effectively codify that **flow, temperatures, and power** are the non‑negotiable backbone of any rigorous COP and savings assessment.

***

## 5. Minimum Bare Data (Summary, Updated)

Your original intuition stands, with a small clarification that **LOAD** is derived:

- ✅ **CHWST** – Required for $\Delta T$
- ✅ **CHWRT** – Required for $\Delta T$
- ✅ **CHW FLOW** – **MANDATORY** for capacity $\dot{Q}$
- ✅ **POWER** – **MANDATORY** for COP $= \dot{Q} / W_{\text{input}}$
- ✅ **CDWRT** – Required for lift/part-load performance evaluation
- ✅ **LOAD** – Calculated from the above

$$
\dot{Q} = \dot{m} \, c_p \, (\text{CHWRT} - \text{CHWST})
$$

With these 5 measured quantities (plus derived LOAD), you can, **from first principles**:

- Calculate actual cooling capacity (kW or tons)
- Calculate actual operating COP
- Compare COP against design/nameplate or a calibrated baseline
- Assess how COP changes with load and lift (part-load efficiency)
- Identify whether observed performance is **consistent** with mechanical/thermal limitations or indicates **optimizable** inefficiencies

Flow is the critical pivot:

- **With FLOW**: Capacity and COP are calculable → the baseline hypothesis can be evaluated physically.
- **Without FLOW**: You have incomplete energy balance → the hypothesis cannot be *rigorously* proven or rejected; you are limited to indicative, not definitive, conclusions.

***

## 6. If Two Extra Points Are Available (Non-core but High-Value)

Without changing the core “bare minimum” above, if the BMS also provides, at essentially **zero extra effort**:

- **CDWST** – Condenser water supply temperature
- **Guide Vane Position (or VFD speed)** – Chiller loading/control signal

then you gain:

- Clear tower/heat-rejection diagnostics (from CDWST vs. ambient and CDWRT)
- Direct visibility into part-load control behaviour and hunting (from guide vane / speed)

These **do not change** the core definition of minimum bare data, but they allow:

- Much sharper separation between **mechanical limits** and **control/operational issues**
- More compelling, specific narratives for prospects (“here is exactly where your losses are coming from”)

while still relying on data that is usually as easy to obtain as the core set.


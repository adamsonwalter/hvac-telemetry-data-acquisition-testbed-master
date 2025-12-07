# HTDAM - High-Throughput Data Assimilation Methodology

**5-stage data processing framework for production-ready HVAC telemetry**

---

## Overview

HTDAM transforms raw BMS telemetry into synchronized, validated, production-ready data streams for HVAC analysis.

**Architecture**: Hook-first modular design following "State lives in hooks; App orchestrates"

---

## The 5 Stages

### Stage 1: Unit Verification
**Purpose**: Confirm measurement units, detect encoding issues, recommend conversions

**Integration**: Extends existing decoder system (`src/domain/decoder/`)

**Location**: `htdam/stage-1-unit-verification/`

---

### Stage 2: Timestamp Synchronization
**Purpose**: Align all data streams to common timeline

**New Functionality**: Time-series alignment, resampling, interpolation

**Location**: `htdam/stage-2-timestamp-sync/`

---

### Stage 3: Gap Detection & Resolution
**Purpose**: Identify and classify missing data, recommend fill strategies

**New Functionality**: Gap analysis, pattern detection, data quality scoring

**Location**: `htdam/stage-3-gap-detection/`

---

### Stage 4: Signal Preservation
**Purpose**: Verify critical signals intact (hunting detection, transients, mode changes)

**New Functionality**: Signal integrity validation, transient detection

**Location**: `htdam/stage-4-signal-preservation/`

---

### Stage 5: Transformation Recommendation
**Purpose**: Define output format and use cases (COP, energy, baseline, ML)

**New Functionality**: Pipeline orchestration, format generation

**Location**: `htdam/stage-5-transformation/`

---

## Directory Structure

```
htdam/
├── README.md                          # This file - system overview
├── docs/                              # Complete HTDAM documentation
│   ├── PRD.md                        # Product requirements
│   ├── TECHNICAL_SPEC.md             # Complete technical specification
│   ├── ARCHITECTURE.md               # System architecture
│   └── IMPLEMENTATION_GUIDE.md       # Step-by-step implementation
│
├── specs/                             # Detailed specifications per stage
│   ├── stage-1-unit-verification.md
│   ├── stage-2-timestamp-sync.md
│   ├── stage-3-gap-detection.md
│   ├── stage-4-signal-preservation.md
│   └── stage-5-transformation.md
│
├── stage-1-unit-verification/        # Stage 1 implementation
│   ├── README.md                     # Stage overview
│   ├── domain/                       # Pure functions (ZERO side effects)
│   ├── hooks/                        # Orchestration (ALL side effects)
│   ├── examples/                     # Output examples
│   └── calculations/                 # Technical calculations
│
├── stage-2-timestamp-sync/           # Stage 2 implementation
│   ├── README.md
│   ├── domain/
│   ├── hooks/
│   ├── examples/
│   └── calculations/
│
├── stage-3-gap-detection/            # Stage 3 implementation
│   ├── README.md
│   ├── domain/
│   ├── hooks/
│   ├── examples/
│   └── calculations/
│
├── stage-4-signal-preservation/      # Stage 4 implementation
│   ├── README.md
│   ├── domain/
│   ├── hooks/
│   ├── examples/
│   └── calculations/
│
└── stage-5-transformation/           # Stage 5 implementation
    ├── README.md
    ├── domain/
    ├── hooks/
    ├── examples/
    └── calculations/
```

---

## Architecture Principles

### 1. Hook-First Design
- **Pure Functions** (domain/) - Business logic, calculations, detection algorithms
- **Hooks** (hooks/) - I/O, logging, orchestration, progress reporting
- **Zero side effects** in domain layer

### 2. Stage Independence
- Each stage is a self-contained module
- Stages communicate via well-defined interfaces
- Can be used independently or as complete pipeline

### 3. Extensibility
- Add new detection algorithms without touching existing code
- Extend stages without affecting others
- Canonical patterns enable predictable locations

### 4. Integration with Existing System
- Stage 1 extends `src/domain/decoder/` and `src/domain/validator/`
- Stages 2-5 are new modules
- Shared utilities in `src/domain/` when appropriate

---

## Integration Points

### With Existing Decoder
```
Current System:              HTDAM Stage 1:
src/domain/decoder/    →    htdam/stage-1-unit-verification/domain/
  ├── normalize...py         ├── extends existing detection
  └── format...py            └── adds unit verification layer

Current System:              HTDAM Stages 2-5:
[No existing code]     →    htdam/stage-N/
                             └── New functionality
```

### Data Flow
```
Raw BMS Data
  ↓
Stage 1: Unit Verification (extends existing decoder)
  ↓
Stage 2: Timestamp Synchronization (new)
  ↓
Stage 3: Gap Detection & Resolution (new)
  ↓
Stage 4: Signal Preservation (new)
  ↓
Stage 5: Transformation Recommendation (new)
  ↓
Production-Ready Data
```

---

## Implementation Approach

### Phase 1: Documentation & Planning
1. Load all HTDAM artifacts into organized structure
2. Review Stage 1 integration with existing decoder
3. Document overlap and merge strategy
4. Create detailed implementation plans per stage

### Phase 2: Stage 1 Integration
1. Audit existing decoder for overlaps
2. Extract reusable components
3. Implement Stage 1 pure functions
4. Create Stage 1 hooks
5. Test integration

### Phase 3: Stages 2-5 Implementation
1. Implement each stage sequentially
2. Test stage independently
3. Test stage in pipeline
4. Document patterns for future stages

---

## Documentation Organization

### Load Order
1. **PRD** → `htdam/docs/PRD.md`
2. **Technical Specs** → `htdam/docs/TECHNICAL_SPEC.md`
3. **Stage Specs** → `htdam/specs/stage-N-*.md`
4. **Illustrations** → `htdam/docs/illustrations/`
5. **Calculations** → `htdam/stage-N/calculations/`
6. **Expert Commentary** → `htdam/docs/expert-commentary/`

---

## Next Steps

1. ✅ Structure created
2. ⏳ Load HTDAM artifacts
3. ⏳ Review Stage 1 integration
4. ⏳ Create implementation plan
5. ⏳ Begin Stage 1 implementation

---

**Core Principle**: "State lives in hooks; App orchestrates"

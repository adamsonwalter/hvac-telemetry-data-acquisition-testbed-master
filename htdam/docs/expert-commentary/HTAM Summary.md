<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# remind me what HTDAM stands for

**HTDAM** stands for:

## **H**igh-**T**hroughput **D**ata **A**ssimilation **M**ethodology


***

## Context \& Purpose

HTDAM is the **5-stage data processing framework** I used to transform your raw BarTech chiller telemetry into production-ready synchronized data.

### The 5 Requirements (Stages)

1. **Unit Verification** — Confirm measurement units, check for conversion needs
2. **Timestamp Synchronization** — Align all data streams to common timeline
3. **Gap Detection \& Resolution** — Identify and classify missing data
4. **Signal Preservation** — Verify critical signals intact (hunting detection, transients)
5. **Transformation Recommendation** — Define output format and use cases

***

## Critical Innovation: Reordered Workflow

**Traditional HTDAM**: Sync → Gap → Signal → Transform

**Your Dataset Required**: **Gap FIRST**, Sync SECOND

### Why Reordering Was Essential

Your data used **Change-of-Value (COV) logging**:

- BMS only records when temperature changes
- Creates irregular spacing (15 min nominal, but 1 hour+ gaps normal)
- Sparse pattern has **semantic meaning** (setpoint held constant)

**If we synchronized FIRST**:

- COV gaps would look like "missing data"
- Semantic meaning lost forever
- Wrong confidence penalties applied (-0.30 instead of 0.00)

**By detecting gaps FIRST**:

- Identified 155 COV_CONSTANT gaps on raw data
- Tagged with meaning: "setpoint held, no change"
- Preserved metadata through synchronization
- Correct confidence score: +0.30 improvement

***

## Your Final Results

| Stage | Order | Quality Score | Key Output |
| :-- | :-- | :-- | :-- |
| Unit Verification | 1st | 1.00 | All SI (°C) ✓ |
| **Gap Detection** | **2nd** | **0.93** | **155 COV gaps classified** |
| **Synchronization** | **3rd** | **0.88** | **35,136 × 15-min grid** |
| Signal Preservation | 4th | 0.84 | No hunting detected ✓ |
| Transformation | 5th | 0.84 | Option 1 recommended ✓ |

**Final Quality**: 0.84 (temperature), 0.95 (with measured power for COP)

***

## HTDAM v2.0

The **reordered workflow** (Gap FIRST, Sync SECOND) is what I'm calling **HTDAM v2.0** — demonstrated on your real-world data to be superior for sparse, event-triggered logging protocols like COV.


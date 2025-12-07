This is the algorithm HTDAM v2.0 uses to align irregular HVAC telemetry to a regular grid (e.g., 15‑minute). It is designed for sparse / COV logging and must preserve gap semantics.

### 1.1 Inputs

Per **stream** (e.g., CHWST, CHWRT, CDWRT, Flow, Power):

- `timestamps_raw`: strictly increasing list of datetimes $[t_0, t_1, …, t_{N-1}]$.
- `values_raw`: numeric list $[v_0, v_1, …, v_{N-1}]$.
- `gap_class_raw` (optional): per‑interval or per‑point gap classification (NORMAL, COV_CONSTANT, COV_MINOR, SENSOR_ANOMALY, EXCLUDED) from Stage 2.

Global:

- `T_grid`: grid step in seconds (default 900 s for 15‑minute).
- `t_start`, `t_end`: global start/end for analysis (from min/max timestamps after exclusions).
- `tolerance`: maximum allowed distance between grid timestamp and raw point (default 30 min = 1800 s).


### 1.2 Master grid construction

Compute the master time grid:

- $G = [g_0, g_1, …, g_{M-1}]$ where:
    - $g_0 = \text{ceilToGrid}(t_{\text{start}}, T_{\text{grid}})$.
    - $g_{k+1} = g_k + T_{\text{grid}}$.
    - Continue until $g_{M-1} \leq t_{\text{end}}$.

`ceilToGrid` means “round up to the next multiple of T_grid”.

### 1.3 Per‑stream nearest‑neighbor alignment

For each stream, produce:

- `values_grid`: length M, numeric or NaN.
- `align_quality`: length M, categorical:
    - `EXACT`, `CLOSE`, `INTERP`, `MISSING`.
- Optionally: `align_distance`: absolute time difference in seconds.

Efficient algorithm (O(M + N)):

- Maintain an index `j` into `timestamps_raw`.
- For each grid time `g_k`:
    - Advance `j` until `timestamps_raw[j] >= g_k` or end.
    - Candidate neighbors:
        - `left = j - 1` (if ≥ 0).
        - `right = j` (if < N).
    - Compute distances:
        - `d_left = |timestamps_raw[left] - g_k|` (if left valid).
        - `d_right = |timestamps_raw[right] - g_k|` (if right valid).
    - Choose nearest:
        - If both valid, pick smaller distance; break ties by picking `right` or `left` consistently.
        - Let `d = min(d_left, d_right)` and `idx = argmin`.

Assignment rules:

- If `d <= tolerance`:
    - `values_grid[k] = values_raw[idx]`.
    - `align_distance[k] = d`.
    - `align_quality[k] =`:
        - `EXACT` if `d < 60 s`.
        - `CLOSE` if `60 s ≤ d < 300 s`.
        - `INTERP` if `300 s ≤ d ≤ tolerance`.
- Else:
    - `values_grid[k] = NaN`.
    - `align_quality[k] = MISSING`.
    - `align_distance[k] = null`.

This uses 1‑nearest‑neighbor in time with a hard tolerance.

### 1.4 Unified row‑level gap_type and confidence

Once all streams are aligned to the same grid:

For each grid index `k`:

- Inputs:
    - `align_quality_stream_s[k]` for each stream s.
    - `per‑stream gap_class_raw` near that time (optional).
    - Whether `g_k` lies in an exclusion window.

Compute:

- `gap_type[k]` (scalar for the row).
- `confidence[k]` in $[0, 1]$.

Algorithm:

1. If `g_k` lies within a known exclusion window:
    - `gap_type[k] = EXCLUDED`.
    - `confidence[k] = 0.00`.
    - All values may be empty/NaN.
2. Else:
    - For each mandatory stream s, inspect `align_quality_s[k]`:
        - If all mandatory streams have `EXACT` or `CLOSE`:
            - `gap_type[k] = VALID`.
            - Per‑stream confidence:
                - EXACT → 0.95.
                - CLOSE → 0.90.
            - `confidence[k] = min(conf_s[k] over all mandatory streams)`.
        - Else if any mandatory stream has `MISSING` (and not EXCLUDED):
            - If raw gap_class_raw around `g_k` was `COV_CONSTANT`:
                - `gap_type[k] = COV_CONSTANT`.
                - `confidence[k] = 0.00`.
            - Else if `COV_MINOR`:
                - `gap_type[k] = COV_MINOR`.
                - `confidence[k] = 0.00`.
            - Else:
                - `gap_type[k] = SENSOR_ANOMALY` or generic `GAP`.
                - `confidence[k] = 0.00`.
        - Else (e.g., some streams INTERP, none MISSING):
            - `gap_type[k] = VALID`.
            - Set per‑stream confidence:
                - INTERP → 0.85.
            - `confidence[k] = min(conf_s[k])`.

This yields a single `gap_type` and `confidence` per row, preserving semantics from Stage 2.

### 1.5 Output data structure

The synchronized dataset is:

- A table of length M with columns:
    - `timestamp = g_k`.
    - `chwst_temp_c`, `chwrt_temp_c`, `cdwrt_temp_c`, `flow`, `power` (aligned values).
    - Derived: `delta_t`, `load_kW`, `cop`, `lift` (from Stage 4).
    - `gap_type`, `confidence`.

The algorithm is deterministic, O(M + N per stream), and works for any telemetered variable with monotone timestamps.

***

2. `useOrchestration` implementation sketch
------------------------------------------

Below is a **TypeScript/React‑style sketch** of `useOrchestration` that wires the five HTDAM stages together. It is illustrative; you can adapt it to your runtime (Node, server, worker, etc.).

### 2.1 Types (domain‑oriented, not framework‑specific)

```ts
// Core stage IDs
type HTDAMStageId = 'INGEST' | 'UNITS' | 'GAPS' | 'SYNC' | 'SIGNAL' | 'TRANSFORM';

// Generic result from a stage
interface StageResult<Data = any, Metrics = any> {
  data: Data;
  metrics: Metrics;
  scoreDelta: number;      // negative penalty or positive adjustment
  messages: string[];      // warnings / info
}

// HTDAM context flowing through stages
interface HTDAMContext {
  rawInput: any;           // original telemetry
  normalized?: any;
  units?: StageResult;
  gaps?: StageResult;
  sync?: StageResult;
  signal?: StageResult;
  transform?: StageResult;
  finalScore: number;      // cumulative [0,1]
  errors: string[];
  warnings: string[];
}

// Domain functions (you implement these with the algorithms above)
type StageFn = (ctx: HTDAMContext) => Promise<HTDAMContext>;
```

Typical stage function signatures:

```ts
async function runUnitVerification(ctx: HTDAMContext): Promise<HTDAMContext> { /* ... */ }
async function runGapDetection(ctx: HTDAMContext): Promise<HTDAMContext> { /* ... */ }
async function runSynchronization(ctx: HTDAMContext): Promise<HTDAMContext> { /* ... */ }
async function runSignalPreservation(ctx: HTDAMContext): Promise<HTDAMContext> { /* ... */ }
async function runTransformation(ctx: HTDAMContext): Promise<HTDAMContext> { /* ... */ }
```

Each one:

- Reads from `ctx`.
- Writes its own `ctx.[stage] = { data, metrics, scoreDelta, messages }`.
- Updates `ctx.finalScore += scoreDelta`.
- Pushes any warnings into `ctx.warnings`.


### 2.2 `useOrchestration` hook

```ts
import { useState, useCallback } from 'react';

interface OrchestrationConfig {
  stages: HTDAMStageId[];        // default: ['INGEST','UNITS','GAPS','SYNC','SIGNAL','TRANSFORM']
  stageFns: Record<HTDAMStageId, StageFn>;
}

type OrchestrationStatus = 'idle' | 'running' | 'paused' | 'error' | 'complete';

interface OrchestrationState {
  status: OrchestrationStatus;
  currentStage?: HTDAMStageId;
  completedStages: HTDAMStageId[];
  ctx: HTDAMContext;
  error?: string;
  logs: string[];
}

// Hook API
export function useOrchestration(config: OrchestrationConfig) {
  const [state, setState] = useState<OrchestrationState>({
    status: 'idle',
    currentStage: undefined,
    completedStages: [],
    ctx: { rawInput: null, finalScore: 1.0, errors: [], warnings: [] },
    logs: [],
  });

  const log = useCallback((msg: string) => {
    setState(prev => ({ ...prev, logs: [...prev.logs, msg] }));
  }, []);

  const run = useCallback(async (rawInput: any) => {
    let ctx: HTDAMContext = {
      rawInput,
      finalScore: 1.0,
      errors: [],
      warnings: [],
    };

    setState(prev => ({ ...prev, status: 'running', currentStage: config.stages[^0], ctx }));

    try {
      for (const stageId of config.stages) {
        setState(prev => ({ ...prev, status: 'running', currentStage: stageId }));
        log(`Starting stage ${stageId}`);

        const stageFn = config.stageFns[stageId];
        ctx = await stageFn(ctx);

        setState(prev => ({
          ...prev,
          ctx,
          completedStages: [...prev.completedStages, stageId],
        }));

        // Early abort if severe error recorded by stage
        if (ctx.errors.length > 0) {
          throw new Error(`Stage ${stageId} reported error(s): ${ctx.errors.join('; ')}`);
        }
      }

      setState(prev => ({ ...prev, status: 'complete', currentStage: undefined, ctx }));
      log(`HTDAM completed with finalScore=${ctx.finalScore.toFixed(2)}`);
    } catch (err: any) {
      const msg = err?.message || 'Unknown error';
      setState(prev => ({ ...prev, status: 'error', error: msg, ctx }));
      log(`HTDAM error: ${msg}`);
    }
  }, [config, log]);

  const retry = useCallback(() => {
    // Simply reset to idle; caller can call run() again with same or new input
    setState(prev => ({
      ...prev,
      status: 'idle',
      currentStage: undefined,
      completedStages: [],
      error: undefined,
      logs: [...prev.logs, 'Retry requested'],
    }));
  }, []);

  const gotoStage = useCallback((stageId: HTDAMStageId) => {
    // Optional: support re-running from a specific stage
    setState(prev => ({
      ...prev,
      status: 'running',
      currentStage: stageId,
      completedStages: prev.completedStages.filter(s => s < stageId),
      logs: [...prev.logs, `gotoStage(${stageId}) requested`],
    }));
    // Implementation detail: you can adjust `run` to accept a startStage
  }, []);

  return { state, run, retry, gotoStage };
}
```


### 2.3 Wiring HTDAM stages into `useOrchestration`

In your app’s domain layer:

```ts
const stageFns: Record<HTDAMStageId, StageFn> = {
  INGEST: async (ctx) => {
    // parse rawInput, normalize streams
    const normalized = await ingestAndNormalize(ctx.rawInput);
    return {
      ...ctx,
      normalized,
      // No score change here, or small penalty if many rows dropped
    };
  },

  UNITS: async (ctx) => {
    const { verifiedStreams, metrics, penalty, messages } = verifyUnitsAndPhysics(ctx.normalized);
    return {
      ...ctx,
      units: { data: verifiedStreams, metrics, scoreDelta: penalty, messages },
      finalScore: ctx.finalScore + penalty,
      warnings: [...ctx.warnings, ...messages],
    };
  },

  GAPS: async (ctx) => {
    const { streamsWithGaps, metrics, penalty, messages } =
      detectAndClassifyGaps(ctx.units?.data ?? ctx.normalized);
    return {
      ...ctx,
      gaps: { data: streamsWithGaps, metrics, scoreDelta: penalty, messages },
      finalScore: ctx.finalScore + penalty,
      warnings: [...ctx.warnings, ...messages],
    };
  },

  SYNC: async (ctx) => {
    const { syncedStreams, metrics, penalty, messages } =
      synchronizeTimestamps(ctx.gaps?.data ?? ctx.units?.data);
    return {
      ...ctx,
      sync: { data: syncedStreams, metrics, scoreDelta: penalty, messages },
      finalScore: ctx.finalScore + penalty,
      warnings: [...ctx.warnings, ...messages],
    };
  },

  SIGNAL: async (ctx) => {
    const { signalMetrics, penalty, messages } =
      preserveAndAssessSignals(ctx.sync?.data);
    return {
      ...ctx,
      signal: { data: ctx.sync?.data, metrics: signalMetrics, scoreDelta: penalty, messages },
      finalScore: ctx.finalScore + penalty,
      warnings: [...ctx.warnings, ...messages],
    };
  },

  TRANSFORM: async (ctx) => {
    const { exportSpecs, penalty, messages } =
      recommendTransformations(ctx.sync?.data, ctx.signal?.metrics);
    return {
      ...ctx,
      transform: { data: exportSpecs, metrics: exportSpecs.metrics, scoreDelta: penalty, messages },
      finalScore: ctx.finalScore + penalty,
      warnings: [...ctx.warnings, ...messages],
    };
  },
};
```

Usage in a component (or service):

```ts
const { state, run, retry } = useOrchestration({
  stages: ['INGEST','UNITS','GAPS','SYNC','SIGNAL','TRANSFORM'],
  stageFns,
});

// Example: start HTDAM when user uploads files
async function onUpload(files: File[]) {
  const rawInput = await readFilesAsDomainInput(files);
  run(rawInput);
}
```


### 2.4 Self‑verification hooks inside orchestration

You can embed **meta‑checks** in `useOrchestration` or in stage functions:

- After Stage UNITS:
    - Verify all 5 bare minimum channels exist and are in canonical units:
        - If any missing, append error to `ctx.errors` and stop pipeline.[^1]
- After Stage SYNC:
    - Check that grid has expected length and interval.
    - If interval not uniform or duplicates found, push error.
- After Stage SIGNAL:
    - If flow or power missing for > X% of time, downgrade `finalScore` or mark COP as unavailable.[^1]

These checks ensure HTDAM only outputs **baseline‑hypothesis‑ready** data when physics requirements are truly met.

***

This gives you:

1. A **precise alignment algorithm** you can implement in any language.
2. A **concrete orchestration hook sketch** showing how to wire HTDAM stages into a composable pipeline (`useOrchestration`), while keeping domain logic fully reusable and independent of UI or platform.
<span style="display:none">[^10][^11][^2][^3][^4][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: Minimum-Bare-Data-for-Proving-the-Baseline-Hypothe.md

[^2]: https://en.wikipedia.org/wiki/K-nearest_neighbors_algorithm

[^3]: https://scikit-learn.org/stable/modules/neighbors.html

[^4]: https://arxiv.org/pdf/2103.14200.pdf

[^5]: https://www.cs.sfu.ca/~jpei/publications/early prediction IJCAI09.pdf

[^6]: https://www.sciencedirect.com/science/article/pii/S0031320318301286

[^7]: https://dzone.com/articles/custom-react-hooks-simplify-complex-scenarios

[^8]: https://blog.smartbuildingsacademy.com/how-to-rope-in-your-chiller-performance

[^9]: https://www.angularminds.com/blog/advanced-react-hooks-patterns-and-best-practices

[^10]: https://airah.org.au/Common/Uploaded files/Archive/Conferences/2017/BS/TechnicalPapers/ABSC2017_TP_Stewart.pdf

[^11]: https://codewithseb.com/blog/advanced-react-hooks-best-practices-in-react-with-nextjs-and-remix


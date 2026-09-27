## 2. Current implementation evidence

As of 2026-09-27, the implementation repository has been bootstrapped and verified through Gate G1.

Verified evidence includes:

- canonical six-file specification set;
- Python package using the `src/` layout;
- clean virtual-environment installation through `pyproject.toml`;
- executable pytest test suite;
- project-owned domain enums and dataclass contracts;
- configuration loading with defaults/profile/explicit override precedence;
- semantic configuration validation;
- deterministic resolved-configuration serialization and SHA-256 identity;
- project-owned Core protocols;
- run metadata identity generation;
- machine-readable run logging;
- deterministic `ReplayFrameSource` with source-derived timestamps;
- `OpenCVCameraSource` with monotonic runtime timestamps;
- successful physical webcam smoke test;
- explicit BGR frame acquisition semantics;
- MediaPipe Hand Landmarker adapter isolated behind the project-owned `LandmarkProvider` contract;
- explicit BGR → RGB conversion at the MediaPipe provider boundary;
- successful real MediaPipe model loading and inference smoke test;
- project-domain `LandmarkObservation` output without MediaPipe objects leaking downstream;
- explicit unavailable measurement quality when no documented per-observation quality value exists;
- no use of handedness classification score as tracking confidence;
- safe `NO_HAND` behavior without fake zero landmarks;
- `MeasurementValidator` for project-domain observation validation;
- Raw/F0 landmark path with no temporal smoothing;
- pre-G2 `TrackingFrame` representation with unavailable ROI/illumination diagnostics represented by `None`, not fabricated measurements;
- `ReplayRuntime` connecting replay acquisition, provider, validation, Raw filtering, `TrackingFrame`, and `RunLogger`;
- machine-readable Raw frame and landmark logs;
- replay integration tests covering deterministic frame identity, timestamps, Raw output, no-hand behavior, logging, and resource release;
- successful end-to-end replay → MediaPipe → Raw → logger smoke test;
- automated G1 test suite executed successfully.

No ROI/CLAHE, canonical fixed 1-Euro, adaptive 1-Euro, gesture engine, renderer, or final experiment result is claimed complete by this status.

## 3. Current stage

### Specification status

```text
CANONICAL SPECIFICATION: FROZEN FOR IMPLEMENTATION
```

The six canonical specification files remain the normative project source of truth.

### Implementation status

```text
G0 — BOOTSTRAP AND CONTRACTS: COMPLETE
G1 — RAW BASELINE + REPLAY: COMPLETE
G2 — DIP PREPROCESSING: NOT STARTED
```

G0–G1 completion establishes the engineering baseline:

```text
deterministic frame acquisition
→ provider isolation
→ explicit color conversion
→ project-domain landmark observations
→ safe Raw/F0 path
→ TrackingFrame
→ structured machine-readable logs
```

This does not imply that DIP preprocessing, temporal filtering, gesture behavior, rendered interaction, or final experimental claims have been validated.

## 4. Current task

**Task G2 — Implement DIP preprocessing.**

Required implementation direction:

```text
full-frame BGR input
    ↓
ROI state and geometry
    ↓
illumination analysis on ROI
    ↓
temporally stabilized illumination decision
    ↓
adaptive CLAHE or bypass
    ↓
processed ROI composited into unchanged full-size BGR frame
    ↓
existing MediaPipe provider boundary
```

Primary G2 objectives:

1. implement the ROI state machine:
   - `SEARCHING`;
   - `TRACKING`;
   - `COASTING`;
2. provide safe full-frame fallback when ROI is unavailable or invalid;
3. preserve unchanged full-frame dimensions and detector geometry;
4. compute documented HSV V-channel illumination descriptors;
5. implement illumination decision stabilization/hysteresis;
6. implement configurable CLAHE/bypass behavior;
7. modify only the selected ROI while preserving the rest of the frame;
8. populate real `TrackingFrame.roi` and `TrackingFrame.illumination` diagnostics;
9. add unit tests for ROI geometry/state transitions, illumination descriptors, color semantics, frame shape, and adaptive preprocessing decisions;
10. preserve deterministic replay compatibility for future P0/P1 comparisons.

G2 MUST NOT:

- perform variable-size ROI-only MediaPipe inference in the course baseline;
- change normalized detector geometry between preprocessing conditions;
- introduce temporal landmark filtering;
- implement gesture or renderer behavior;
- claim tracking improvement solely from increased image contrast.

### G1 completion evidence

G1 was completed with the following verified implementation path:

```text
OpenCVCameraSource / ReplayFrameSource
    ↓
FramePacket
    ↓
MediaPipe Hand Landmarker adapter
    ↓
explicit BGR → RGB conversion
    ↓
LandmarkObservation
    ↓
MeasurementValidator
    ↓
RawLandmarkFilter
    ↓
Raw TrackingFrame
    ↓
FileRunLogger
```

Verified Gate G1 acceptance evidence:

- physical camera smoke path works on available hardware;
- replay frame IDs and source-derived timestamps are deterministic;
- MediaPipe model loads and executes through the project adapter;
- blank/no-hand input produces explicit `NO_HAND`;
- missing hand data does not create fake landmarks;
- measurement quality remains explicitly unavailable when no valid source exists;
- Raw/F0 landmarks pass through without temporal smoothing;
- Raw logs are machine-readable;
- replay integration produces consistent frame and landmark records;
- runtime shutdown releases replay/camera/provider/logger resources;
- full automated test suite passes.

No performance, tracking-accuracy, FPS, latency, jitter-reduction, or robustness result is inferred from these engineering verification tests.

### G1 contract correction — LandmarkProvider input

Change:

`LandmarkProvider.process` accepts `FramePacket` instead of separate image/timestamp arguments.

Reason:

The previous signature could not preserve required `frame_id` identity and conflicted with the rule that the MediaPipe adapter owns explicit BGR → RGB conversion.

Canonical file/section changed:

`02_ARCHITECTURE_AND_CONTRACTS.md`, Public interfaces.

Code/modules affected:

`core/interfaces.py`, tracking-provider adapter, runtime integration.

Algorithmic impact:

None.

Experimental impact:

None.

Compatibility impact:

Public interface corrected before final provider experiments existed.

Tests added/updated:

Provider tests verify frame identity, timestamps, and explicit BGR → RGB conversion.

Existing results invalidated:

No — no final provider experiment results existed before the correction.

### G1 contract correction — pre-G2 TrackingFrame diagnostics

Change:

`TrackingFrame.roi` and `TrackingFrame.illumination` may be `None` when the corresponding stages have not been executed.

Reason:

G1 requires a Raw `TrackingFrame`, while ROI and illumination processing are introduced only in G2. Fabricating zero-valued measurements would violate project evidence semantics.

Canonical file/section changed:

`02_ARCHITECTURE_AND_CONTRACTS.md`, TrackingFrame contract.

Code/modules affected:

`core/contracts.py`, `RunLogger`, replay runtime integration.

Algorithmic impact:

None.

Experimental impact:

Pre-G2 development logs explicitly distinguish unavailable diagnostics from measured diagnostics.

Compatibility impact:

G2+ runs are required to populate ROI and illumination whenever the preprocessing stages are executed.

Tests added/updated:

Core contract, logger, and replay-integration tests verify explicit unavailable pre-G2 diagnostics.

Existing results invalidated:

No — no final G2+ experiment results existed before the correction.

### G2 algorithm decision — illumination state stabilization

Change:

Defined the baseline illumination-state decision using EMA-smoothed
`mean_v` and `robust_range_v`, with separate enter/exit hysteresis
thresholds.

Reason:

The canonical specification required `NORMAL`, `LOW_LIGHT`,
`LOW_CONTRAST`, and `DIFFICULT` states and required temporal stability,
but did not previously define the exact mapping from descriptors to
states.

Canonical file/section changed:

`03_ALGORITHM_AND_EXPERIMENTS.md`, Illumination assessment.

Code/modules affected:

`configuration`, `preprocessing/illumination_decision.py`, future
adaptive preprocessing/runtime integration.

Algorithmic impact:

Defines the course-baseline illumination classification and
stabilization behavior.

Experimental impact:

Future P0/P1 preprocessing runs must preserve the resolved threshold and
EMA configuration used for each run.

Compatibility impact:

No completed final illumination experiments existed before this rule was
defined.

Tests added/updated:

Configuration threshold-ordering tests and illumination
EMA/hysteresis/state-transition tests.

Existing results invalidated:

No — no final G2 illumination results exist yet.

### G2 semantic clarification — enhancement_active

Change:

`IlluminationMetrics.enhancement_active` is defined as whether CLAHE was
actually applied after preprocessing policy resolution.

Reason:

Illumination state and preprocessing policy are distinct. A difficult
illumination state may still be intentionally bypassed in P0/bypass
conditions.

Canonical file/section changed:

`03_ALGORITHM_AND_EXPERIMENTS.md`, Adaptive CLAHE.

Code/modules affected:

`preprocessing/illumination_decision.py`,
`preprocessing/adaptive_preprocessor.py`,
future runtime/logging integration.

Algorithmic impact:

Clarifies adaptive/always/bypass policy behavior.

Experimental impact:

P0/P1 logs can distinguish measured illumination state from actual
enhancement application.

Existing results invalidated:

No — no final G2 preprocessing experiment results exist yet.

## 5. Immediate next tasks

Proceed in this order unless a documented blocker requires rearrangement:

1. **G2 DIP preprocessing** — ROI state machine, illumination descriptors/hysteresis, adaptive CLAHE/bypass, unchanged full-frame provider geometry.
2. **G3 Canonical fixed 1-Euro** — derivative low-pass `d_cutoff`, fixed parameters, diagnostics, reset behavior, and synthetic tests.
3. **G4 Bounded adaptive 1-Euro** — velocity-dependent adaptation, optional valid quality branch, cutoff bounds, and safe loss/reacquisition handling.
4. **G5 Gesture + 3D Extension** — normalized pinch/hysteresis, bounded rotation/scale mapping, renderer-independent `InteractionState`, and minimal rendered STEM scene.
5. **G6 Minimal experiment tooling** — replay profiles, paired comparisons, run/trial manifests, required descriptive metrics, and reproducibility capture.
6. **G7 Final evaluation** — collect final trials, regenerate plots/tables from recorded artifacts, write evidence-bounded results, and package the final demo/report.

Do not prioritize renderer polish ahead of G2–G4 correctness.
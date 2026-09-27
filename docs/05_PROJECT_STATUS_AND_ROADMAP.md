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
G2 — DIP PREPROCESSING: COMPLETE
G3 — CANONICAL FIXED 1-EURO: COMPLETE
G4 — BOUNDED ADAPTIVE 1-EURO: NOT STARTED
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

**Task G4 — Implement the bounded adaptive 1-Euro filter.**

G3 canonical fixed 1-Euro is technically complete.

G3 completion evidence includes:

- canonical 1-Euro reference/provenance verification;
- reusable low-pass primitive and alpha validation;
- canonical scalar 1-Euro implementation with derivative low-pass `d_cutoff`;
- regression against the published OneEuroFilter ground-truth fixture;
- project-specific independent per-landmark x/y vectorization;
- shared x/y cutoff within each landmark and independent state across landmarks;
- model-relative z pass-through in the fixed baseline;
- timestamp-derived `dt`;
- safe short-loss state retention without fake measurements;
- long-loss and timestamp-discontinuity reset behavior;
- deterministic reinitialization after reset;
- public `ONE_EURO_FIXED` `LandmarkFilter` implementation;
- deterministic frame-level diagnostic summary semantics;
- fixed-filter configuration validation;
- ReplayRuntime and FileRunLogger integration through the existing public contracts;
- deterministic synthetic tests covering constant, step, ramp, sine,
  noise, known noisy trajectory, and nonuniform valid `dt`;
- full automated project suite passing with 225 tests.

Key G3 implementation/evidence commits:

```text
fab66d0 docs: verify canonical one euro reference
0294fdb feat: add canonical low pass primitives
7381fb0 feat: add canonical scalar one euro filter
49f3c82 docs: clarify landmark one euro vectorization
db0df50 feat: add fixed one euro landmark vector core
7e60e03 feat: add fixed one euro temporal state handling
01e1b37 docs: define one euro diagnostic summary semantics
ce37135 feat: expose fixed one euro landmark filter
20ec3d3 feat: define fixed one euro configuration
596367e test: integrate fixed one euro replay logging
f56192c test: add one euro reference regression
c96f834 test: add one euro synthetic acceptance suite
```
G3 completion establishes the canonical F1 baseline. It does not imply
that the adaptive F2 method, gesture behavior, rendered interaction, or
final experiment outcomes have been validated.
The next implementation stage is G4. G4 reuses the already frozen
timestamp/loss/reset safety semantics rather than redefining them.

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

### G3 algorithm clarification — landmark vectorization scope

Change:

Defined the fixed 1-Euro landmark vectorization as one independent x/y
2D filter vector per landmark. Each landmark derives one shared x/y
speed and cutoff from its own filtered x/y derivatives. Model-relative
z is passed through unchanged in the course baseline.

Reason:

The previous specification required a "shared speed" and "shared
cutoff" for landmark vectors but did not state whether sharing applied
within one landmark or across all 21 landmarks. Those interpretations
produce materially different filtering behavior.

Canonical file/section changed:

`03_ALGORITHM_AND_EXPERIMENTS.md`, Section 7.2 Project vectorization.

Code/modules affected:

Future fixed landmark 1-Euro core, temporal-filter wrapper, diagnostics,
synthetic tests, and adaptive filter extension.

Algorithmic impact:

Clarifies the project-specific vectorization layered on top of the
canonical scalar 1-Euro algorithm. The canonical scalar equations are
unchanged.

Experimental impact:

F1/F2 landmark filtering will use independent per-landmark x/y motion
rather than a concatenated all-landmark speed vector.

Compatibility impact:

No completed F1/F2 experiment results exist yet.

Tests added/updated:

Upcoming G3.4 tests will verify shared x/y cutoff within one landmark,
independence between landmarks, z pass-through, and preservation of
landmark identity/coordinate space.

Existing results invalidated:

No — no final fixed/adaptive temporal-filter experiment results exist.

### G3 contract clarification — frame-level filter diagnostics

Change:

Defined the scalar public `FilterDiagnostics` fields for per-landmark
vector filtering. Frame-level `speed` is the maximum per-landmark x/y
speed; `final_cutoff_hz` and `signal_alpha` come from the same landmark.
Ties use the lowest landmark index. Initialization and no-measurement
semantics were also defined.

Reason:

The public contract contains one scalar diagnostic set while the frozen
G3 landmark vectorization maintains independent speed/cutoff state for
each landmark. Leaving the mapping unspecified would make logs
ambiguous.

Canonical file/section changed:

`02_ARCHITECTURE_AND_CONTRACTS.md`, `FilterDiagnostics`;
`03_ALGORITHM_AND_EXPERIMENTS.md`, fixed-filter diagnostics and common
loss/reset semantics.

Code/modules affected:

Fixed/adaptive LandmarkFilter wrappers, ReplayRuntime integration,
RunLogger serialization tests, later analysis diagnostics.

Algorithmic impact:

None on landmark filtering equations. The aggregation is diagnostic
only and MUST NOT feed back into filtering.

Experimental impact:

F1/F2 frame diagnostics become deterministic and comparable. Primary
jitter/responsiveness metrics remain trajectory-based.

Compatibility impact:

No completed fixed/adaptive final experiment logs exist. Existing Raw
logs are unaffected.

Tests added/updated:

Upcoming G3.6 tests will verify max-speed representative selection,
deterministic tie handling, initialization/no-measurement diagnostics,
reset reporting, and runtime serialization.

Existing results invalidated:

No — no final F1/F2 experimental results exist.

### G4 contract clarification — bounded adaptive beta mapping

Change:

Defined the exact project-specific F2 velocity-to-beta mapping, clarified
per-landmark adaptive vectorization, primary quality-disabled behavior,
final-cutoff safety, and adaptive public diagnostic aggregation.

Reason:

The canonical specification already defined adaptive parameters and
final cutoff bounds but did not state the exact beta(v) equation.
Implementation would otherwise have to choose algorithm behavior
silently.

Canonical file/section changed:

`03_ALGORITHM_AND_EXPERIMENTS.md`, adaptive F2 algorithm;
`02_ARCHITECTURE_AND_CONTRACTS.md`, adaptive FilterDiagnostics semantics.

Code/modules affected:

Upcoming adaptive landmark core, adaptive public LandmarkFilter,
configuration validation, replay/logging tests.

Algorithmic impact:

F2 beta is explicitly nondecreasing with speed and bounded by configured
beta limits. Optional velocity limiting applies to beta adaptation.
Final cutoff remains independently bounded.

Experimental impact:

Defines the F2 method that will later be compared with F0 and F1.
Primary F2 does not use measurement-quality adaptation unless a valid
documented source exists.

Compatibility impact:

No adaptive implementation or final F2 result exists yet.

Tests added/updated:

Upcoming G4 tests will cover beta bounds/monotonicity, velocity spikes,
final cutoff bounds, unavailable quality, invalid dt, reset, and
reacquisition.

Existing results invalidated:

No — no F2 implementation/final experimental results exist.

### G4 contract correction — temporal filter event propagation

Change:

Added explicit filter-event propagation through `FilterDiagnostics.events`
to `TrackingFrame.events` and `RunLogger.log_event`. Frozen the existing
temporal event names for F1/F2.

Reason:

The temporal filter cores already detect timestamp/loss/reset events, and
the run artifact contract already includes `TrackingFrame.events` and
`events.csv`, but the public `LandmarkFilter` return contract had no path
for carrying those events to the runtime. ReplayRuntime therefore could
not preserve them without duplicating temporal state logic.

Canonical file/section changed:

`02_ARCHITECTURE_AND_CONTRACTS.md`, FilterDiagnostics / TrackingFrame /
LandmarkFilter logging semantics;

`03_ALGORITHM_AND_EXPERIMENTS.md`, tracking-loss/discontinuity event
semantics.

Code/modules affected:

Core FilterDiagnostics contract;
Raw/fixed/adaptive LandmarkFilter implementations;
ReplayRuntime;
run logging integration and tests.

Algorithmic impact:

None. Existing timestamp, loss, reset, and reacquisition decisions are
unchanged.

Experimental impact:

Future F1/F2 run artifacts preserve temporal reset/discontinuity events
needed for auditability and exclusion/debugging.

Compatibility impact:

In-memory `FilterDiagnostics` gains an events field. Existing CSV column
schemas are unchanged; the already-defined events artifact will begin
receiving the events that were previously dropped.

The existing FileRunLogger already serializes TrackingFrame.events.
The contract therefore assigns serialization responsibility to RunLogger
rather than requiring ReplayRuntime to issue a second duplicate
log_event call.

Tests added/updated:

Core contract tests;
Raw/F1/F2 public-filter tests;
ReplayRuntime event propagation tests;
events.csv logging tests.

Existing results invalidated:

No — no final F1/F2 experimental result set exists. Earlier development
runs may lack these event records and must not be treated as final
event-complete runs.

## 5. Immediate next tasks

Proceed in this order unless a documented blocker requires rearrangement:

1. **G4 Bounded adaptive 1-Euro** — velocity-dependent adaptation,
   optional valid quality branch, cutoff bounds, and reuse of the frozen
   loss/reset/reacquisition semantics.
2. **G5 Gesture + 3D Extension** — normalized pinch/hysteresis, bounded
   rotation/scale mapping, renderer-independent `InteractionState`, and
   minimal rendered STEM scene.
3. **G6 Minimal experiment tooling** — replay profiles, paired comparisons,
   run/trial manifests, required descriptive metrics, and reproducibility capture.
4. **G7 Final evaluation** — collect final trials, regenerate plots/tables
   from recorded artifacts, write evidence-bounded results, and package the
   final demo/report.

Do not prioritize renderer polish ahead of G4 correctness.
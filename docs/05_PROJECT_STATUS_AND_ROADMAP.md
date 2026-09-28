## 2. Current implementation evidence

As of 2026-09-28, the implementation repository has been verified
through Gate G6.

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
- deterministic normalized pinch ratio and pinch hysteresis;
- bounded/deadzoned renderer-independent rotation and scale commands;
- explicit neutral initialization, loss/reset, and reacquisition behavior;
- `GestureEngine` consuming filtered project-domain landmarks and producing `InteractionState`;
- ReplayRuntime interaction integration and interaction-state logging;
- renderer-independent `Stem3DSceneState` with bounded accumulated scale;
- optional Pygame/PyOpenGL 3D Extension with lazy graphics imports;
- Extension boundary tests confirming renderer/application modules do not import Core algorithm internals;
- synchronous `RealtimeRuntime` exposing the latest public `InteractionState`;
- visible synthetic OpenGL renderer smoke test;
- live webcam → preprocessing → MediaPipe → filter → gesture → `InteractionState` → 3D Extension integration;
- physical no-hand / hand-enter / hand-leave / hand-reacquire smoke test completed successfully;
- clean camera/provider/logger/renderer shutdown verified in the live demo;
- final G5 automated project suite passing with 378 tests.
- frozen G6 primary experiment protocol before final data collection;
- explicit F0/F1/F2 and P0/P1 experiment profiles;
- deterministic single-replay experiment entry point;
- manifest-driven paired batch execution preserving one replay source across compared conditions;
- immutable batch index preserving exact trial/profile/run/source identity;
- analysis loader consuming logger-produced metadata, resolved config, frames, landmarks, and events without manual raw-log editing;
- primary A1 radial RMS jitter metric on filtered landmark 8 in FRAME_NORMALIZED coordinates;
- primary A2 trajectory-deviation RMSE relative to F0 using common usable frame IDs;
- primary Experiment B valid hand-observation rate using VALID and REACQUIRED statuses;
- paired timestamp/frame alignment checks for comparative metrics;
- automatic CSV/table and Matplotlib plot regeneration from indexed run artifacts;
- generated-analysis provenance preserving batch identity, run IDs, analysis window, planned comparisons, exclusion rules, run code revision, config hash, model/source identity, and analysis code revision;
- SHA-256 capture for available local model and replay-source files;
- explicit unavailable checksum semantics when a referenced file is not available;
- no inferential statistics or optional performance benchmark added to the minimum course gate;
- final G6 targeted acceptance suite passing with 47 tests;
- final automated project regression suite passing with 425 tests.

G0–G6 are technically complete. Final controlled data collection,
final evaluation, report conclusions, and final research outcomes are
not claimed complete by this status.

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
G4 — BOUNDED ADAPTIVE 1-EURO: COMPLETE
G5 — GESTURE + 3D EXTENSION: COMPLETE
G6 — EXPERIMENT READINESS: COMPLETE
G7 — FINAL EVALUATION / PACKAGE: NOT STARTED
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

G0–G6 completion establishes the implemented Core, interaction-demo,
and reproducible experiment-tooling pipeline. It does not imply that the
project hypotheses are supported, that one method outperforms another,
or that final experimental claims have been validated. Those claims
remain dependent on the controlled final experiments in G7.

## 4. Current task

**Task G7 — Run the final controlled evaluation and package the submission.**

G6 experiment readiness is technically complete.

G6 completion evidence includes:

- primary A1/A2/B metrics frozen before final data collection;
- baseline-isolated F0/F1/F2 and P0/P1 profiles;
- deterministic single-replay execution;
- manifest-driven paired replay batches;
- immutable batch indexes preserving exact run identities;
- analysis loading directly from machine-readable run artifacts;
- common-frame paired metric alignment;
- radial RMS jitter implementation for A1;
- F0-relative trajectory-deviation RMSE for A2;
- valid hand-observation rate for Experiment B;
- automatic metrics CSV and plot regeneration;
- model and replay-source SHA-256 capture when files are available;
- resolved configuration, code revision, schema, dependency, system,
  model/source, and run identity preserved through run metadata;
- predefined exclusion rules preserved through batch and generated-analysis provenance;
- analysis provenance linking generated outputs back to exact run IDs,
  configs, source/model hashes, and analysis revision;
- no optional inferential statistics required or introduced;
- G6 targeted acceptance: 47 passed;
- final G6 full regression: 425 passed.

Key G6 implementation/evidence commits:

```text
f2b9cca docs: freeze g6 primary experiment metrics
cb2e285 feat: define g6 experiment profiles
2b9af8f feat: add deterministic experiment replay runner
53ad036 feat: add paired experiment batch runner
f67c7cb feat: add run artifact analysis loader
6e16d2b feat: add primary experiment metrics
bede648 feat: persist experiment batch index
edbd1a4 feat: regenerate experiment tables and plots
6f119e9 feat: capture experiment file checksums
78725b9 feat: preserve analysis provenance and exclusions
```

G6 completion establishes experiment readiness only. No final A1, A2,
or Experiment B outcome has yet been collected, and no superiority,
jitter-reduction, robustness, accuracy, FPS, latency, or statistical
claim is made from the G6 tooling tests.

G5 gesture mapping and the minimal 3D STEM Extension are technically complete.

G5 completion evidence includes:

- palm-width-normalized pinch ratio with strict hysteresis;
- bounded/deadzoned rotation and scale mapping;
- deterministic neutral initialization, loss/reset, and reacquisition;
- public renderer-independent `InteractionState`;
- `GestureEngine` using filtered project-domain landmarks only;
- ReplayRuntime interaction generation and logging;
- renderer-independent 3D scene-state accumulation;
- optional Pygame/PyOpenGL renderer;
- Extension/Core dependency-boundary tests;
- synchronous RealtimeRuntime with latest `InteractionState`;
- synthetic visible 3D renderer smoke;
- physical webcam → MediaPipe → Core → InteractionState → 3D smoke;
- verified no-hand, enter, leave, and reacquisition behavior;
- clean shutdown of runtime and renderer resources;
- final automated G5 regression suite: 378 passed.

Key G5 implementation/evidence commits:

```text
8435352 docs: freeze deterministic gesture semantics
0b978ba feat: add gesture configuration
f464c04 feat: add gesture math
ba7a2cd feat: add deterministic gesture engine
b5e2c1d feat: integrate gesture interaction into replay
55cc986 feat: add stem3d scene state
319c043 feat: add optional stem3d renderer
495587e feat: add visible stem3d smoke demo
7d88e9c feat: add realtime interaction runtime
eaa1c18 feat: add live touchless stem3d demo
```

Physical G5 smoke evidence:

```text
live run 1: 386 processed frames, clean shutdown
live run 2: 1141 processed frames, clean shutdown
manual acceptance: no-hand / enter / leave / reacquire / shutdown PASS
```

G5 completion demonstrates practical rendered interaction and safe runtime
behavior. It does not claim experimental superiority, accuracy, FPS,
latency, or final RQ3 research outcome.

G4 bounded adaptive 1-Euro is technically complete.

G4 completion evidence includes:

- frozen project-specific bounded adaptive 1-Euro semantics;
- speed derived from filtered per-landmark x/y derivatives;
- bounded velocity-dependent beta;
- optional quality-dependent minimum-cutoff primitive with no invented
  measurement quality;
- primary F2 baseline using `f_base` when quality adaptation is disabled
  or unavailable;
- independent final-cutoff bounds;
- project-specific independent per-landmark x/y adaptive state;
- model-relative z pass-through;
- shared F1/F2 timestamp, short-loss, long-loss, discontinuity, reset,
  and reacquisition semantics;
- public `ONE_EURO_ADAPTIVE` `LandmarkFilter`;
- deterministic frame-level adaptive diagnostics;
- validated adaptive configuration and engineering defaults;
- explicit filter-originated temporal events propagated through
  `FilterDiagnostics` and `TrackingFrame`;
- temporal reset/discontinuity events serialized to `events.csv`;
- ReplayRuntime integration for Raw/F0, Fixed/F1, and Adaptive/F2;
- acceptance coverage for beta bounds, cutoff bounds, monotonic beta,
  unavailable quality fallback, valid-quality minimum-cutoff
  monotonicity, extreme finite speed, invalid dt, long-gap reset,
  missing measurements, and reacquisition;
- full automated project suite passing with 290 tests.

Key G4 implementation/evidence commits:

```text
8884df1 docs: define bounded adaptive one euro semantics
877d17f feat: add bounded adaptive filter policy
958e3e4 feat: add adaptive one euro landmark core
e7be912 feat: share temporal semantics across one euro filters
2145739 feat: expose adaptive one euro filter configuration
5730abb docs: define temporal filter event propagation
3bbe8bf feat: expose temporal filter events
35aa24a docs: clarify tracking frame event serialization
2ddfd34 test: integrate adaptive filter replay logging
15a5a4f test: complete adaptive filter gate acceptance
```
G4 completion establishes the project F2 temporal baseline. It does not
claim that F2 outperforms F0/F1; that conclusion remains dependent on
future recorded experiments.
G5 followed G4 and preserves the Core/Extension boundary: gesture
processing consumes filtered project-domain landmarks, and the 3D
Extension consumes InteractionState rather than reaching into filter,
tracking, or preprocessing internals.


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

### G5 algorithm/interface decision — deterministic gesture mapping

Change:

Defined the course-baseline gesture mapping and GestureEngine contract:
configured landmark roles, palm-width-normalized pinch, pinch
hysteresis, bounded/deadzoned pointer rotation, pinch-ratio scale delta,
and explicit neutral loss/reset/reacquisition behavior.

Reason:

The previous G5 specification required normalized pinch, hysteresis,
rotation/scale deadzones and clamps, but did not define the exact
landmark roles, scale mapping, public InteractionState field semantics,
or initialization/reacquisition state transitions. Implementing those
details without a specification decision would make gesture behavior
ambiguous.

Canonical file/section changed:

`02_ARCHITECTURE_AND_CONTRACTS.md`, InteractionState and public
interfaces;

`03_ALGORITHM_AND_EXPERIMENTS.md`, Gesture mapping.

Code/modules affected:

future `interaction` / gesture modules, configuration validation,
ReplayRuntime/RealtimeRuntime gesture integration, interaction logging,
and 3D STEM Extension.

Algorithmic impact:

Defines the project-specific G5 gesture algorithm. It does not alter Raw,
fixed 1-Euro, adaptive 1-Euro, ROI, illumination, or landmark-provider
behavior.

Experimental impact:

RQ1/RQ2 preprocessing and temporal-filter baselines are unchanged.
Future RQ3 demo behavior must use this gesture mapping and preserve its
resolved configuration.

Compatibility impact:

No implemented G5 gesture engine or final RQ3 interaction result existed
before this decision.

Tests added/updated:

G5 tests cover normalized pinch, denominator protection, hysteresis,
rotation deadzone/gain/clamp, scale deadzone/gain/clamp, loss reset,
first-frame neutrality, temporal-filter-reset neutrality, reacquisition
neutrality, scene-state accumulation and bounds, Extension/Core dependency
boundaries, ReplayRuntime/RealtimeRuntime interaction integration, and
clean renderer/runtime behavior.

Existing results invalidated:

No — no final G5 interaction experiments/results exist.

### G6 experiment-design decision — primary metrics and baseline isolation

Change:

Frozen the minimum course primary metrics and comparison isolation rules:

- A1 F0/F1/F2 primary metric: radial RMS jitter of filtered landmark 8;
- A2 F0/F1/F2 primary metric: 2D trajectory-deviation RMSE relative to
  F0 on the identical dynamic replay;
- Experiment B P0/P1 primary metric: valid hand-observation rate;
- A1/A2 hold preprocessing constant at P1;
- Experiment B holds temporal filtering constant at F0 / Raw;
- paired conditions use the same source, timestamps, predefined analysis
  window, and common usable frame IDs where applicable.

Reason:

The canonical experiment specification required choosing one primary
metric before final comparison but intentionally did not preselect the
metric. G6 tooling requires those choices to be frozen before final data
collection so analysis code cannot select favorable metrics after viewing
results.

Canonical file/section changed:

`03_ALGORITHM_AND_EXPERIMENTS.md`, Experiments A1, A2, and B.

Code/modules affected:

Future G6 experiment manifests, analysis loaders, metric functions,
batch runner, result tables, and plot regeneration.

Algorithmic impact:

None. F0, F1, F2, P0, and P1 processing algorithms are unchanged.

Experimental impact:

Defines the primary descriptive outcomes that will support RQ1/RQ2 and
prevents preprocessing and temporal-filter conditions from being changed
simultaneously in their primary comparisons.

Compatibility impact:

No final experiment result set exists. Development runs produced before
this decision may be used for tooling/debugging but MUST NOT be mixed into
final tables unless they satisfy the frozen protocol.

Tests added/updated:

Upcoming G6 tests will cover metric calculations, paired frame alignment,
manifest validation, deterministic condition expansion, and analysis of
generated run artifacts without manual CSV editing.

Existing results invalidated:

No — no final A1/A2/B result set has been collected.

## 5. Immediate next tasks

Proceed in this order unless a documented blocker requires rearrangement:

1. **G7 Final controlled evaluation** — define the actual final A1, A2,
   and Experiment B manifests, including recorded source identities,
   actual trial counts, predefined analysis windows/warmup, and exclusion
   rules before inspecting final outcomes.

2. **Run final paired replay experiments** — execute F0/F1/F2 for the
   static and dynamic RQ2 sources and P0/P1 for the required illumination
   conditions using the frozen G6 tooling.

3. **Regenerate final evidence** — produce the required trajectories,
   primary metric tables/plots, illumination comparison outputs, and
   DIP-focused before/after visual evidence directly from recorded artifacts.

4. **Submission demo application/presentation shell** — after the final
   experiment evidence is secured, add only the presentation-oriented UI
   needed for the final demo: camera preview, tracking/ROI/illumination/filter
   status, pinch/interaction state, 3D view, start/stop/reset controls, and
   run/log identity. Do not alter Core algorithms or experiment semantics.

5. **Final report/package** — write evidence-bounded Results, Discussion,
   limitations/threats to validity, and Conclusions for RQ1–RQ3; package
   reproducibility instructions, model acquisition/checksum information,
   selected result assets, and the final demo.

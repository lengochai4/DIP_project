## 2. Current implementation evidence

As of 2026-09-29, the implementation repository has been verified
through Gate G7 and the G7 release is tagged.

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
- frozen G7 final A1/A2/Experiment B trial plans and recorded sources;
- regenerated, provenance-linked G7 metrics, plots, and selected evidence
  under `submission/evidence/`;
- final report and submission instructions included in the tagged tree;
- recorded G7 full regression of 433 passing tests, as stated in
  `submission/README.md`;
- physical final-demo smoke and a separate run recording the exact live
  execution revision, both with clean shutdown;
- annotated `g7-final` tag resolving to release commit
  `f454c6b8325c85199c0122c0e822fe8e76c1526c`.

G0–G7 are complete as the canonical-v1.2 research and submission
baseline. G7 does not establish universal method superiority: A2's
primary metric is unavailable in all three final trials, and the
adaptive P1 path did not activate CLAHE in the analyzed B trials. Final
claims remain limited to the recorded evidence in `FINAL_REPORT.md`.

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
G7 — FINAL EVALUATION / PACKAGE: COMPLETE (FROZEN AT `g7-final`)
G8 — POST-G7 UI / STEM EXTENSION PRODUCTIZATION: PLANNED
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

G0–G7 completion establishes the implemented Core, interaction demo,
reproducible experiment tooling, and the final evidence-bounded report.
It does not imply that the project hypotheses are universally supported
or that one method outperforms another. The unavailable A2 result and
inactive adaptive-CLAHE path remain explicit limitations.

G8 is a separate post-G7 presentation/Extension direction. It does not
change the scope or interpretation of the frozen G7 experiment release.

## 4. Current task

**Task G8-U7 — Harden presentation loading, error, empty, disabled, and cleanup states — COMPLETE.**

The G7 controlled evaluation and submission package are complete and
frozen at `g7-final`. The active G8 direction is a separately scoped
post-G7 application/Extension continuation. U1 through U7 are implemented.
U6 presents selected frozen G7 artifacts without modifying evidence or
research conclusions. U7 adds explicit lifecycle feedback, failure
handling, disabled controls, keyboard fallback, and cleanup hardening. The
next roadmap unit is U8. Preserve the existing G7/Core boundary while
continuing that presentation work.

G8 is not a new research experiment and does not claim commercial
readiness. Any change to Core semantics, public contracts, experiment
metrics, or G7 evidence requires the canonical governance and change
review process.

### G8-U6 Evidence Mode completion — 2026-09-30

Evidence Mode displays selected immutable G7 plots and recorded trial values
across six navigable pages. It preserves the A2 unavailable status and reason,
the CLAHE non-activation limitation, A1 trial availability and five-frame
caution, the practical false-positive limitation, and separate release/demo
provenance. Missing images and malformed optional metadata produce explicit
unavailable states.

Focused Extension tests passed (40), the full project suite passed (478),
`compileall extensions/stem3d` succeeded, and six synthetic dashboard pages
rendered for presentation inspection. No physical webcam smoke was run for
U6. The frozen G7 evidence files and `g7-final` tag remain unchanged.

### G8-U7 Commercial UX Hardening completion — 2026-09-30

The dashboard and application controller now expose explicit startup,
component-failure, tracking, and shutdown states. Camera, hand model/provider,
renderer, and dashboard failures remain distinct from ordinary no-hand or
tracking-loss states. Invalid interaction clears stale landmarks, pointer,
panel hover/press, and interaction values; touchless controls are visibly
disabled until interaction is available. Keyboard guidance and contextual
molecule shortcuts match the current DEMO/ANALYSIS/EVIDENCE and three-scene
surface. Evidence asset errors remain separate from frozen experiment-level
unavailability.

Partial renderer/dashboard initialization is cleaned up, shutdown is
idempotent, and cleanup failures are not reported as a clean stop. Focused
Extension tests passed (93), the full project suite passed (499),
`compileall extensions/stem3d` succeeded, and `git diff --check` was clean.
Five synthetic startup, camera/model/renderer failure, and clean-shutdown
screens rendered at the supported minimum dashboard size. No physical
webcam/hand smoke was run for U7.

Core algorithms, research contracts, G7 results/evidence, and the `g7-final`
tag are unchanged. The next roadmap unit is U8 — Automated Validation.

### G6 experiment-readiness completion record (historical)

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

At the end of G6, tooling completion alone did not establish final
experiment outcomes or method superiority. G7 outcomes and their
limitations are recorded in the evidence snapshot below and in
`FINAL_REPORT.md`; no FPS, latency, accuracy, or inferential-statistics
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

No — no final G2+ experiment results existed at the time of this
correction.

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

No — no final G2 illumination results existed when this rule was
recorded.

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

No — no final G2 preprocessing experiment results existed when this
rule was recorded.

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

Fixed landmark 1-Euro core, temporal-filter wrapper, diagnostics,
synthetic tests, and adaptive-filter extension.

Algorithmic impact:

Clarifies the project-specific vectorization layered on top of the
canonical scalar 1-Euro algorithm. The canonical scalar equations are
unchanged.

Experimental impact:

F1/F2 landmark filtering uses independent per-landmark x/y motion
rather than a concatenated all-landmark speed vector.

Compatibility impact:

At the time of this clarification, no completed F1/F2 experiment results
existed.

Tests added/updated:

G3.4 tests cover shared x/y cutoff within one landmark, independence
between landmarks, z pass-through, and preservation of landmark
identity/coordinate space.

Existing results invalidated:

No — no final fixed/adaptive temporal-filter experiment results existed
at the time of this clarification.

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

No completed fixed/adaptive final experiment logs existed at the time of
this clarification. Existing Raw logs were unaffected.

Tests added/updated:

G3.6 tests cover max-speed representative selection, deterministic tie
handling, initialization/no-measurement diagnostics, reset reporting,
and runtime serialization.

Existing results invalidated:

No — no final F1/F2 experimental results existed at the time of this
clarification.

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

Adaptive landmark core, adaptive public LandmarkFilter, configuration
validation, and replay/logging tests.

Algorithmic impact:

F2 beta is explicitly nondecreasing with speed and bounded by configured
beta limits. Optional velocity limiting applies to beta adaptation.
Final cutoff remains independently bounded.

Experimental impact:

Defines the F2 method used in the final G7 comparison with F0 and F1.
Primary F2 does not use measurement-quality adaptation unless a valid
documented source exists.

Compatibility impact:

No adaptive implementation or final F2 result existed when this decision
was recorded.

Tests added/updated:

G4 tests cover beta bounds/monotonicity, velocity spikes, final cutoff
bounds, unavailable quality, invalid dt, reset, and reacquisition.

Existing results invalidated:

No — no F2 implementation or final experimental results existed when
this decision was recorded.

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

F1/F2 run artifacts preserve temporal reset/discontinuity events needed
for auditability and exclusion/debugging.

Compatibility impact:

In-memory `FilterDiagnostics` gains an events field. Existing CSV column
schemas are unchanged; the events artifact now receives the events that
were previously dropped.

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

No — no final F1/F2 experimental result set existed when this change
was made. Earlier development runs may lack these event records and must
not be treated as final event-complete runs.

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

No final experiment result set existed when this decision was recorded.
Development runs produced before this decision may be used for
tooling/debugging but MUST NOT be mixed into final tables unless they
satisfy the frozen protocol.

Tests added/updated:

G6 tests cover metric calculations, paired frame alignment, manifest
validation, deterministic condition expansion, and analysis of generated
run artifacts without manual CSV editing.

Existing results invalidated:

No — at the time this pre-G7 design decision was recorded, no final
A1/A2/B result set had been collected.

### G7 experiment-protocol clarification — unavailable paired metric

Change:

Defined explicit handling for A1/A2 trials whose predefined paired
analysis window contains zero common usable F0/F1/F2 landmark frames.

Such a trial remains in the final experiment record, but its paired
primary metric is marked unavailable with reason
`no_common_usable_frames`. Analysis continues for other trials.

Reason:

The first final A1 batch exposed a previously unspecified edge case:
one retained final trial contained no usable landmark observations in
the predefined analysis window for any F0/F1/F2 condition. The frozen
exclusion policy correctly prevents removing that trial for poor
tracking/NO_HAND behavior, while the radial RMS metric cannot be
numerically calculated without usable landmark samples.

Canonical file/section changed:

`03_ALGORITHM_AND_EXPERIMENTS.md`, paired A1/A2 metric availability.

Code/modules affected:

`analysis/regenerate.py`, analysis tests, and possibly metric-result
serialization helpers. Core algorithms, acquisition, tracking provider,
preprocessing, filtering, and recorded sources are unchanged.

Algorithmic impact:

None.

Experimental impact:

The planned and recorded trial remains part of the experiment. The
primary paired metric is calculated only for trials having a non-empty
common usable landmark-frame set. Generated outputs must explicitly
retain unavailable trials and report the evaluable-trial count.

Compatibility impact:

The existing G7 A1 batch and all nine recorded final sources remain
valid. No A1 primary metric output had been successfully generated
before this clarification. No source is replaced and no analysis window
is changed.

Tests added/updated:

Analysis regeneration tests cover empty common paired sets producing an
explicit unavailable metric record rather than aborting the entire batch,
while ordinary evaluable trials remain unchanged.

Existing results invalidated:

No. A1 regeneration previously failed before producing final metric
outputs. The raw run artifacts and frozen source recordings remain
valid.


### G7 presentation-interface addition — read-only realtime callback

Change:

Added an optional `RealtimeRuntime` presentation callback that receives
one presentation-safe camera-frame copy, the public `TrackingFrame`, and
the current `InteractionState | None` once per processed realtime frame.

Reason:

The final presentation shell requires camera preview plus
tracking/ROI/illumination/filter/interaction status. `RealtimeRuntime`
previously exposed only the latest `InteractionState`, while the required
tracking diagnostics existed only inside the runtime/logger path.
Presentation code must not reach into mutable Core internals.

Canonical file/section changed:

`02_ARCHITECTURE_AND_CONTRACTS.md`, RealtimeRuntime presentation seam.

Code/modules affected:

`src/dip_touchless/runtime/realtime.py`;
`tests/runtime/test_realtime_runtime.py`;
future submission/demo presentation code.

Algorithmic impact:

None. ROI selection, illumination decisions, CLAHE behavior, landmark
provider behavior, temporal filtering, gesture mapping, logging, and the
3D scene-state algorithm are unchanged.

Experimental impact:

None. ReplayRuntime and all frozen G7 A1/A2/B experiment semantics and
recorded result artifacts are unchanged. The callback is realtime-only
presentation plumbing.

Compatibility impact:

Additive optional constructor argument only. Existing RealtimeRuntime
callers remain valid. The existing `interaction_consumer` remains the
InteractionState-only boundary used by the 3D Extension.

Tests added/updated:

RealtimeRuntime test coverage verifies one callback per processed frame,
matching frame identity/status/interaction state, and a non-shared camera
image copy that presentation code can mutate without modifying the source
frame buffer.

Existing results invalidated:

No — the change does not alter ReplayRuntime, experiment configuration,
analysis code, or any algorithm used to generate the retained final
results.

### G7 final evaluation evidence snapshot — A1/A2/B

Status:

Final paired replay collection and primary analysis have been executed for
A1, A2, B-normal, and B-lowlight using the frozen G7 sources, predefined
2.0--10.0 s analysis window, frozen manifests, and exclusion policy.

No source recording, analysis window, primary metric, or comparison condition
was replaced after inspecting outcomes.

Analysis regeneration revision:

`abdc32b2417fde28cbb9df4b96f1ce5e20e0be4f`

#### A1 — static temporal stability

Batch:

`G7-A1-STATIC-20260928T144254479591Z`

Primary metric:

`radial_rms_jitter`

Recorded trials:

3

Evaluable trials:

2

Observed results:

- `trial-001`, common usable frames = 5:
  - F0 = `0.006607584161915466`
  - F1 = `0.001628449479902759`
  - F2 = `0.001629070583985972`
- `trial-002`:
  - paired primary metric unavailable;
  - reason = `no_common_usable_frames`;
  - the trial remains in the final experiment record.
- `trial-003`, common usable frames = 128:
  - F0 = `0.030597141717346094`
  - F1 = `0.026704461422596908`
  - F2 = `0.026753300347156422`

Evidence-bounded interpretation:

- F1 and F2 both have lower radial RMS jitter than F0 in the two evaluable
  trials.
- F1 and F2 are very close to each other in both evaluable trials.
- `trial-001` contains only five common usable frames, so its numeric value
  is weak descriptive evidence.
- The three-trial source-group size is small; no population-level or
  inferential superiority claim is supported.

#### A2 — dynamic responsiveness characterization

Batch:

`G7-A2-DYNAMIC-20260928T151157912799Z`

Primary metric:

`trajectory_deviation_rmse`

Recorded trials:

3

Evaluable trials:

0

All three trials retain explicit unavailable primary-metric records with:

`no_common_usable_frames`

Diagnostic result:

- `trial-001`: all 360 replay frames were `NO_HAND`;
- `trial-002`: all 360 replay frames were `NO_HAND`;
- `trial-003`: one `VALID` raw-landmark frame occurred at frame 33, outside
  the predefined 2.0--10.0 s primary analysis window; the analysis window
  contained no usable landmark frame;
- within each trial, the raw usable-frame sets were identical across
  F0/F1/F2, so the unavailable result is not evidence of a filter-specific
  alignment difference.

Evidence-bounded interpretation:

The final A2 source set does not provide an evaluable quantitative
trajectory-deviation result. Therefore the final RQ2 evidence can describe
the observed A1 static-jitter behavior, but the predefined primary
responsiveness characterization is unavailable and must remain an explicit
limitation.

No A2 source is replaced and the analysis window is not changed after seeing
this outcome.

#### Experiment B — illumination robustness

Primary metric:

`valid_hand_observation_rate`

Temporal filtering was held at F0 / Raw.

##### B-normal

Batch:

`G7-B-NORMAL-20260928T151702564004Z`

Recorded/evaluable trials:

3 / 3

Each condition used 241 analyzed frames per trial.

Observed P0 / P1 rates:

- `trial-001`: `0.02074688796680498 / 0.02074688796680498`
- `trial-002`: `0.0 / 0.0`
- `trial-003`: `0.5311203319502075 / 0.5311203319502075`

P0 and P1 therefore produced the same primary outcome in each tested
normal-light trial.

##### B-lowlight

Batch:

`G7-B-LOWLIGHT-20260928T152103579608Z`

Recorded/evaluable trials:

3 / 3

Each condition used 241 analyzed frames per trial.

Observed P0 / P1 rates:

- `trial-001`: `0.0 / 0.0`
- `trial-002`: `0.0 / 0.0`
- `trial-003`: `0.0 / 0.0`

The retained source sidecars label these three recordings
`low-light-room`. Auto-exposure and auto-white-balance state were recorded
as `unknown`, so no claim is made about whether camera auto controls
compensated for the physical lighting change.

Illumination-activation audit:

- B-normal P1: stabilized state was `NORMAL` and
  `enhancement_active=False` for all 723 analyzed frames;
- B-lowlight P1: stabilized state was also `NORMAL` and
  `enhancement_active=False` for all 723 analyzed frames.

Therefore the final P0/P1 equality must not be described as evidence that
CLAHE itself is ineffective. Under the tested sources and resolved
configuration, the adaptive activation policy did not request/apply CLAHE,
so P1 resolved to the unenhanced path throughout the analyzed frames.

Evidence-bounded RQ1 interpretation:

Under the tested final conditions, adaptive preprocessing did not increase
valid hand-observation rate relative to bypass. The challenging-light source
group also exposes an activation-policy limitation: despite being acquired
and documented as `low-light-room`, the runtime illumination classifier
remained `NORMAL`, so the final experiment does not provide a direct
CLAHE-active-versus-bypass tracking comparison.

This limitation must remain explicit in the Results and Discussion and must
not be converted into a general claim about CLAHE effectiveness.

#### Current RQ evidence boundary

RQ1:

The primary P0/P1 metric is available for all normal and low-light trials.
No improvement was observed, but the low-light P1 path never activated
CLAHE, limiting the conclusion to the tested adaptive policy and source
conditions.

RQ2:

Static-jitter evidence is available for two of three A1 trials. The primary
A2 responsiveness metric is unavailable for all three final dynamic trials
because the predefined analysis windows contain no common usable landmarks.

RQ3:

The existing G5 physical interaction smoke test demonstrates practical
interaction behavior but is not treated as an RQ1/RQ2 quantitative result.
The final demo runs, execution identity, observed interaction, and known
false-positive limitation are recorded below and in `FINAL_REPORT.md`.

### G7 final demo physical smoke — 2026-09-29

Final presentation-shell smoke run:

```text
run_id: g7-demo-20260929-190838
processed_frames: 4947
shutdown: clean
Observed behavior:
- final camera/status presentation and 3D interaction ran successfully;
- the frozen gesture mapping remained unchanged: index-fingertip motion
  controls rotation and thumb-index pinch controls scale;
- the application remained operational through the live run and closed
  cleanly;
- an occasional false-positive hand-like detection was observed around
  the user's face/background, producing a small unintended cube rotation.
Interpretation:
The false-positive behavior is retained as a practical tracking limitation
of the final live demo. It is not hidden by post-hoc tracking-threshold or
algorithm changes. It does not alter the frozen A1/A2/B replay results or
their interpretation.
### G7 post-commit final demo identity verification — 2026-09-29

A second final-demo run was executed after committing the completed
presentation shell so that runtime metadata identifies the exact immutable
code revision used for submission.

```text
run_id: g7-demo-20260929-192030
processed_frames: 1188
shutdown: clean
code_revision: 6a87dc50f9d3920ed9fd39a2669e266be00f9735
spec_version: canonical-v1.2
config_hash: ecfaeb11725d9a289b8b6e71a7650a9be5b90fbfb65e5775fe14e13ff5b83a08
model_filename: hand_landmarker.task
model_sha256: fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1

The recorded code_revision exactly matched repository HEAD for this
run. This run is therefore the primary reproducibility identity for the
final submitted live demo.
The earlier g7-demo-20260929-190838 run remains the physical behavior
smoke in which rotation, pinch/scale, reset, reacquisition, presentation
status, and clean shutdown were exercised. Its observed occasional
face/background false-positive remains a documented practical limitation.
No Core algorithm, experiment source, analysis window, or retained G7
experiment result was changed between the final evidence collection and
this demo-identity verification.

### G7 release closure and G8 transition — 2026-09-29

G7 is complete and frozen at annotated tag `g7-final`, which resolves to
release commit `f454c6b8325c85199c0122c0e822fe8e76c1526c`. The tag tree
contains `FINAL_REPORT.md`, `submission/README.md`, and the selected
generated assets under `submission/evidence/`. The primary live-demo
execution revision `6a87dc50f9d3920ed9fd39a2669e266be00f9735` is recorded
separately in the report and is not the release commit.

The last recorded G7 full regression is 433 passing tests, as reported by
`submission/README.md`. This is a historical project result; no test suite
was run as part of this documentation update.

G7 evidence remains bounded: two of three A1 trials have evaluable paired
metrics; A2 has no evaluable trial; P0 and P1 have equal valid-observation
rates in the retained B trials, while adaptive P1 never activated CLAHE in
the analyzed windows. The live demo ran successfully, with an occasional
face/background false-positive recorded as a limitation. Exact values and
provenance remain in the report and evidence artifacts.

The current branch `feat/final-ui-extension` starts from the frozen G7
release. G8 is promoted as a separate post-G7 UI/Extension roadmap. It is
not a seventh canonical research specification and does not change the
canonical-v1.2 algorithms, G7 measurements, or report conclusions.

Canonical file/section changed:

`05_PROJECT_STATUS_AND_ROADMAP.md`, current stage/task and immediate
roadmap; supplemental direction in `06_G8_UI_EXTENSION_PRODUCTIZATION.md`.

Algorithmic and experimental impact:

None. G7 provenance and all final experiment artifacts remain frozen.

## 5. Immediate next tasks

G7 is closed. U1–U7 are implemented on `feat/final-ui-extension`. U2
provides DEMO/ANALYSIS modes, live ROI and pointer overlays, distinct
raw/filtered landmarks, DIP diagnostics, and run identity from recorded
metadata. U3 defines the `STEMScene` contract and local `SceneRegistry`,
routes scenes through an Extension-owned lifecycle, and leaves Core
unchanged. U4 registers Coordinate Geometry, Molecular Geometry (H2O and
CH4), and Orbital System through the same scene contract. U4-focused tests
pass (56), the full automated suite passes (462), and Extension compile
validation succeeds. An OpenGL renderer smoke opened a visible window,
rendered all three scenes, exercised rotation/scale/reset, switched the
molecule preset, advanced the orbital scene, repeated scene switches, and
closed cleanly using synthetic public `InteractionState` values. It did
not use a webcam or physical hand input. Continue with the post-G7 roadmap in
`docs/06_G8_UI_EXTENSION_PRODUCTIZATION.md`, in this order:

1. **U1 — Application foundation — COMPLETE:** add an application controller,
   immutable presentation state, centralized design tokens, responsive
   layout calculations, and a dashboard shell. Keep the existing live
   demo working while extracting responsibilities incrementally.
2. **U2 — DIP visibility — COMPLETE:** present camera, ROI, landmarks, pointer,
   tracking, illumination, CLAHE, filter, and runtime identity using the
   public read-only realtime presentation seam.
3. **U3 — Scene architecture — COMPLETE:** define the Extension-owned `STEMScene`
   lifecycle and local registry, then migrate the existing coordinate
   cube without changing `InteractionState` semantics.
4. **U4 — STEM scenes — COMPLETE:** provide coordinate geometry, H2O/CH4
   molecular geometry, and a deterministic educational orbital system.
5. **U5 — Spatial Control Panel — COMPLETE:** add screen-space touchless navigation
   using normalized `pointer_xy`, valid pinch rising edges, and explicit
   UI/scene focus routing. Keep all click and focus behavior in the
   Extension.
6. **U6 — Evidence mode — COMPLETE:** display selected frozen G7 assets and retain
   unavailable findings and known limitations without editing or
   regenerating the source evidence.
7. **U7 — Commercial UX hardening — COMPLETE:** make startup and component
   failures explicit; clear stale tracking/interaction presentation;
   disable unusable touchless controls; preserve keyboard fallback; and
   make partial initialization and shutdown cleanup safe.
8. **U8 — Automated validation — NEXT:** run targeted Extension tests and
   full `pytest` regression for the post-G7 UI/Extension surface.
9. **U9/U10 — Physical validation and release:** exercise the complete
   application with the webcam, document screenshots/demo instructions,
   record limitations, and create a new post-G7 release identity without
   moving `g7-final`.

G8 is a product-direction phase, not a new scientific evaluation. Do not
add cloud, account, telemetry-backend, or unrelated platform features.

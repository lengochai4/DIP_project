# 04 — Implementation and Testing Guide

**Specification set:** Canonical v1.2  
**Status:** Normative for implementation workflow, testing, quality gates, and human/AI coding behavior

## 1. Purpose

This file tells a human developer or AI coding agent **how to implement and verify** the architecture defined by files `01`–`03` without silently changing it.

It does not redefine algorithm equations or public contract semantics.

## 2. Required reading order before nontrivial changes

Before changing architecture, algorithms, public interfaces, experiment behavior, or research-critical tests:

1. read `00_GOVERNANCE.md`;
2. read `01_MASTER_SPEC.md`;
3. read relevant sections of `02_ARCHITECTURE_AND_CONTRACTS.md`;
4. read relevant sections of `03_ALGORITHM_AND_EXPERIMENTS.md`;
5. inspect existing implementation, configuration, and tests;
6. check current stage/task in `05_PROJECT_STATUS_AND_ROADMAP.md`.

Do not assume existing code is compliant until inspected.

## 3. Recommended repository structure

The implementation SHOULD keep a `src/` package layout and a thin 3D extension outside the DIP Core:

```text
DIP-Touchless-STEM/
├── README.md
├── pyproject.toml
├── config/
│   ├── default.yaml
│   └── experiments/
├── models/
│   └── README.md
├── docs/
│   ├── 00_GOVERNANCE.md
│   ├── 01_MASTER_SPEC.md
│   ├── 02_ARCHITECTURE_AND_CONTRACTS.md
│   ├── 03_ALGORITHM_AND_EXPERIMENTS.md
│   ├── 04_IMPLEMENTATION_TESTING_GUIDE.md
│   └── 05_PROJECT_STATUS_AND_ROADMAP.md
├── src/dip_touchless/
│   ├── domain/
│   ├── capture/
│   ├── preprocessing/
│   ├── tracking/
│   ├── filtering/
│   ├── interaction/
│   ├── coordinates/
│   ├── telemetry/
│   ├── runtime/
│   ├── config.py
│   └── pipeline.py
├── extensions/stem3d/
├── experiments/
├── analysis/
├── tests/
│   ├── unit/
│   ├── synthetic/
│   ├── integration/
│   └── fixtures/
├── runs/       # generated/ignored by default
└── results/    # generated/selected outputs
```

Exact filenames may change while preserving module responsibilities and dependency direction.

## 4. Dependency policy

Expected baseline dependencies:

- Python;
- NumPy;
- OpenCV;
- MediaPipe;
- YAML parser such as PyYAML;
- pytest;
- Matplotlib;
- SciPy only if optional inferential/statistical analysis requires it;
- Pygame and PyOpenGL for the 3D extension.

Do not add large ML frameworks merely for helper utilities.

`pyproject.toml` SHOULD be the canonical package/build/tool metadata source. A `requirements.txt` MAY be generated for coursework convenience but SHOULD NOT become an independently maintained conflicting dependency source.

Model files MUST have documented origin/version/name and a checksum for final experiments when practical. Replacing a model can invalidate results.

## 5. Minimum implementation entry points

The repository SHOULD expose commands or equivalent scripts for:

```text
realtime demo
single replay run
experiment batch/profile run
analysis/regeneration of plots and tables
test suite
```

Exact CLI library and command names are implementation details.

## 6. Implementation stages and quality gates

Development progresses through gates. Do not skip a gate by adding later UI features first.

### Stage/Gate G0 — Bootstrap and contracts

Implement:

- package/project skeleton;
- configuration loader + validator + resolved-config snapshot/hash;
- domain enums/dataclasses/protocols from `02`;
- test runner;
- logging skeleton.

Gate passes when contracts instantiate/serialize correctly, config validation works, and the test runner runs in a clean environment.

### Stage/Gate G1 — Raw baseline + replay

Implement:

```text
camera/replay
→ explicit color conversion
→ MediaPipe adapter
→ LandmarkObservation
→ raw TrackingFrame
→ RunLogger
```

Gate passes when:

- camera smoke path works where hardware is available;
- replay path is deterministic;
- no-hand behavior is safe;
- raw logs are machine-readable;
- clean shutdown releases resources.

### Stage/Gate G2 — DIP preprocessing

Implement:

- ROI state machine;
- illumination metrics;
- decision stabilization/hysteresis;
- adaptive CLAHE/bypass;
- same-size full-frame compositing.

Gate passes only after ROI/color/shape/illumination tests pass and diagnostics appear in run data.

### Stage/Gate G3 — Canonical fixed 1-Euro

Implement:

- low-pass primitive;
- derivative low-pass with `d_cutoff`;
- fixed `f_min` and fixed `beta` path;
- filter diagnostics;
- reset initialization.

Gate passes only after canonical acceptance tests and synthetic-signal tests pass.

### Stage/Gate G4 — Proposed bounded adaptive 1-Euro

Implement:

- speed from filtered derivative;
- velocity-dependent bounded beta;
- optional quality mapping only when a valid source exists;
- bounded final cutoff;
- loss/reset/reacquisition semantics.

Gate passes only after numerical bounds, missing-quality, spike, invalid-dt, and reacquisition tests pass.

### Stage/Gate G5 — Gesture + 3D Extension

Implement:

- normalized pinch ratio;
- pinch hysteresis;
- bounded/deadzoned rotation and scale deltas;
- neutral reacquisition behavior;
- simple rendered STEM object interaction.

Gate passes when Extension uses `InteractionState` only and does not import/modify Core algorithm internals.

### Stage/Gate G6 — Experiment readiness

Implement/finalize:

- experiment profiles/manifests;
- replay batch runner;
- analysis loaders and required descriptive metrics;
- optional statistical helpers only if inferential analysis is deliberately adopted;
- plot/table regeneration;
- run metadata/reproducibility capture;
- documented exclusion rules.

Gate passes when all required compared configurations run on the same replay input, the required primary metrics can be regenerated without manual editing of raw logs, and no optional performance/statistical work is required for the gate.

### Stage/Gate G7 — Final evaluation/package

Run final experiments and produce final report assets. G7 passes only when the final Definition of Done in `05_PROJECT_STATUS_AND_ROADMAP.md` is satisfied.

## 7. Testing layers

### 7.1 Unit tests — required

No physical camera required.

Cover at least:

- ROI clamp/bounds/state transitions;
- illumination descriptors and hysteresis;
- CLAHE bypass/shape/dtype/color contract;
- timestamp/dt validation;
- low-pass alpha calculation;
- canonical fixed 1-Euro behavior;
- adaptive cutoff/beta bounds;
- unavailable measurement-quality behavior;
- loss/reset/reacquisition;
- normalized pinch and hysteresis;
- coordinate/render picking math if implemented;
- configuration validation;
- run-logging serialization essentials.

### 7.2 Synthetic signal tests — required

Filter fixtures SHOULD include:

```text
constant
step
ramp
sine
noise
known trajectory + noise
nonuniform valid dt
invalid dt
large timestamp gap
velocity spike
missing measurements
```

Tests enforce invariants and deterministic behavior; they MUST NOT hard-code the desired research conclusion.

### 7.3 Replay integration tests — required

Run a short fixture sequence through the real Core without requiring the renderer.

Verify:

- deterministic frame order;
- Raw/Fixed/Adaptive modes all execute;
- frame/color/coordinate semantics remain valid;
- expected run artifacts are produced;
- tracking loss does not inject zeros;
- reacquisition produces neutral first-frame interaction deltas;
- repeated replay with same source/config is behaviorally reproducible within deterministic components.

### 7.4 Runtime smoke tests — required before final demo

Where hardware is available:

- camera opens or fails explicitly;
- no-hand state does not crash;
- hand enter/leave/reacquire is safe;
- renderer consumes public state only;
- shutdown releases camera/renderer resources.

Physical-camera smoke tests SHOULD NOT be required for normal CI.

## 8. Canonical 1-Euro acceptance tests

Tests MUST demonstrate that:

- derivative low-pass filtering with `d_cutoff` exists;
- fixed mode keeps configured `f_min` and `beta` constant;
- derivative/signal alpha remain in `(0,1]` for valid parameters;
- finite valid input produces finite output;
- invalid/non-positive dt is not processed as an ordinary update;
- reset/first-sample initialization is deterministic.

Any implementation failing the derivative-low-pass requirement MUST NOT be labeled `ONE_EURO_FIXED` in this project.

## 9. Adaptive-filter acceptance tests

Tests MUST verify:

- beta remains in configured bounds;
- final cutoff remains in configured bounds;
- increasing speed under the defined mapping does not accidentally decrease beta;
- unavailable quality uses base minimum cutoff rather than invented quality;
- when quality adaptation is enabled, lower valid quality does not increase the quality-derived minimum cutoff;
- extreme but finite speed is handled according to configured safety limits;
- long gaps/reset conditions clear state as specified;
- first reacquired frame does not emit a motion impulse.

## 10. ROI/preprocessing acceptance tests

Tests MUST verify:

- ROI never indexes outside the frame;
- invalid bbox falls back safely;
- SEARCHING/TRACKING/COASTING transitions obey config;
- enhanced output preserves full-frame shape and declared BGR semantics;
- bypass does not silently change geometry/color meaning;
- BGR↔HSV and BGR→RGB boundaries are explicit and tested.

## 11. Gesture acceptance tests

Tests MUST verify:

- hand-scale denominator cannot collapse to zero silently;
- `pinch_on < pinch_off` validation;
- hysteresis prevents switching chatter inside the threshold band;
- loss invalidates/releases pinch safely;
- first reacquired frame produces neutral rotation/scale deltas;
- deadzones, gains, and clamps are respected.

## 12. Logging/reproducibility acceptance tests

Tests MUST verify:

- run directory creation;
- metadata and resolved config are written;
- config hash/schema version are present;
- frame IDs are consistent across artifacts;
- unavailable quality is serialized explicitly as unavailable;
- logs remain parseable after graceful shutdown;
- analysis can consume a short generated run without hand-editing CSV.

## 13. AI/human coding rules

Every contributor MUST follow these rules:

1. preserve course scope and Core/Extension separation;
2. preserve Raw and canonical Fixed baselines;
3. never fabricate benchmark values, test results, or experiment outcomes;
4. never claim a test passed unless it was actually executed and observed;
5. never silently change equations, parameter meaning, public semantics, coordinate spaces, or experiment protocol;
6. keep tunable research parameters in configuration;
7. never convert missing tracking into zero landmarks;
8. never invent measurement quality/confidence;
9. obey the `MeasurementQuality` source/semantics defined in `02`;
10. never call a derivative-less variant canonical 1-Euro;
11. make the smallest coherent change that satisfies the task;
12. do not refactor unrelated modules during a narrow fix unless required for correctness;
13. update tests with research-critical behavior changes;
14. identify experiment/result invalidation when behavior changes;
15. do not add technologies or product features excluded by the Master Spec without an explicit scope change.

## 14. Standard task workflow for AI or human contributors

For every nontrivial task:

### Step 1 — Inspect

Read relevant specs, implementation files, tests, and config. Confirm current repository behavior rather than assuming it.

### Step 2 — Define the task contract

Identify internally:

```text
requested behavior
input/output contracts
files/modules expected to change
invariants that must remain unchanged
required tests
possible experiment/data invalidation
```

### Step 3 — Implement the smallest coherent change

Reuse existing public contracts. Avoid unrelated cleanup.

### Step 4 — Add/update tests

Prefer tests before or together with research-critical math/state changes.

### Step 5 — Run targeted tests

Record actual command/result.

### Step 6 — Run regression tests

If a shared/public component changed, run the relevant broader suite.

### Step 7 — Report the change

Every meaningful handoff/PR should state:

```text
What changed
Why
Files/modules changed
Algorithm/interface impact
Experiment/data compatibility impact
Tests actually run + actual result
Known limitations/TODOs
```

## 15. Stop conditions

A developer/AI MUST stop implementation of the ambiguous portion and surface the issue when:

- two canonical files conflict materially;
- required provider semantics cannot be verified;
- a requested change would violate a frozen scope/algorithm contract;
- existing data would be invalidated and the task assumes it remains comparable;
- a required model/file/config is missing and guessing would change behavior;
- test failure indicates the requested modification breaks a research-critical invariant.

This does not require stopping unrelated safe work.

## 16. Debugging order

For unstable tracking/interaction, inspect in this order:

1. source frame validity;
2. timestamps and `dt`;
3. color-space conversion;
4. ROI geometry/state;
5. illumination descriptors/preprocessing output;
6. raw landmark observation/status;
7. measurement-quality source, if enabled;
8. canonical fixed filter;
9. adaptive filter diagnostics;
10. gesture state;
11. renderer/application mapping.

Do not tune the adaptive filter first when the failure originates in acquisition, ROI, or tracking.

## 17. Team change/review discipline

A research-critical change is review-ready only when:

- code is scoped to the task;
- affected tests are present and pass;
- public contract/algorithm changes are reflected in the canonical owner file;
- configuration changes are validated;
- experiment invalidation is stated;
- no generated/fabricated benchmark is committed as evidence;
- no secret/personal data is committed.

Stable final experiment runs SHOULD reference an immutable commit/tag/code revision.

## 18. CI recommendation

Normal CI SHOULD run without a physical webcam:

```text
format/lint
unit tests
synthetic filter tests
short replay integration test
configuration validation
analysis smoke test on fixture data
```

Coverage percentage is secondary to correctness of mathematical behavior, state transitions, boundaries, and research-critical contracts.

# 05 — Project Status and Roadmap

**Specification set:** Canonical v1.2  
**Status snapshot:** 2026-09-27  
**Status owner:** Project lead / current implementing team

## 1. Status rule

This file is the single source of truth for:

- current project stage;
- current task;
- next tasks;
- roadmap priorities;
- known blockers/risks;
- final Definition of Done.

Update this file when the actual implementation state changes. Do not infer completion from the existence of specifications alone.

## 2. Current implementation evidence

As of 2026-09-27, the implementation repository has been bootstrapped and verified through Gate G0.

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
- run logging skeleton producing machine-readable run artifacts;
- automated G0 tests executed successfully.

No G1 camera, replay, MediaPipe landmark-provider, preprocessing, temporal-filter, gesture, renderer, or final experiment result is claimed complete by this status.

## 3. Current stage

### Specification status

```text
CANONICAL SPECIFICATION: FROZEN FOR IMPLEMENTATION
```

The six canonical specification files remain the normative project source of truth.

### Implementation status

```text
G0 — BOOTSTRAP AND CONTRACTS: COMPLETE
G1 — RAW BASELINE + REPLAY: NOT STARTED
```

G0 completion means the project foundation is established and verified. It does not imply that tracking, preprocessing, filtering, interaction, or experimental claims have been validated.

## 4. Current task

**Task G1 — Implement Raw + Replay baseline.**

Required implementation direction:

```text
FrameSource
    ↓
OpenCVCameraSource / ReplayFrameSource
    ↓
explicit BGR → RGB provider boundary
    ↓
MediaPipe Hand Landmarker adapter
    ↓
MeasurementValidator
    ↓
LandmarkObservation
    ↓
RAW temporal path
    ↓
TrackingFrame
    ↓
RunLogger
```

Primary G1 objectives:

1. add required runtime dependencies deliberately;
2. implement `OpenCVCameraSource`;
3. implement deterministic `ReplayFrameSource`;
4. verify explicit frame/timestamp/color semantics;
5. implement the MediaPipe provider adapter without leaking provider objects downstream;
6. represent unavailable measurement quality explicitly;
7. implement a safe raw/no-filter baseline;
8. serialize Raw `TrackingFrame` data through the existing logger;
9. add unit and replay integration tests;
10. run camera smoke testing only where hardware is available.

No ROI/CLAHE or 1-Euro behavior belongs in G1.

## 5. Immediate next tasks

After G1 passes:

1. **G2 DIP preprocessing** — ROI state machine, illumination descriptors/hysteresis, adaptive CLAHE, unchanged full-frame provider geometry.
2. **G3 Canonical fixed 1-Euro** — derivative low-pass `d_cutoff`, fixed parameters, diagnostics and synthetic tests.
3. **G4 Bounded adaptive 1-Euro** — velocity adaptation, optional valid quality branch, cutoff bounds and safe reset/reacquisition.
4. **G5 Gesture + 3D Extension** — normalized pinch/hysteresis, bounded interaction mapping and minimal rendered STEM scene.
5. **G6 Minimal experiment tooling** — deterministic comparisons, required descriptive metrics and reproducibility.
6. **G7 Final evaluation** — final trials, evidence-bounded results/report and demo packaging.

## 6. Course-final roadmap

### Phase M0.1 — Engineering baseline

Target: G0–G1.

Outcome:

```text
deterministic data path
provider isolation
raw baseline
replay path
structured logs
```

### Phase M0.2 — DIP method

Target: G2.

Outcome:

```text
ROI management
illumination analysis
adaptive CLAHE
DIP diagnostics
```

### Phase M0.3 — Temporal method

Target: G3–G4.

Outcome:

```text
canonical fixed baseline
proposed adaptive filter
safe loss/reacquisition
synthetic/replay verification
```

### Phase M0.4 — Interaction demonstration

Target: G5.

Outcome:

```text
renderer-independent interaction state
stable pinch/rotation/scale behavior
minimal 3D STEM demo
```

### Phase M0.5 — Evaluation and submission

Target: G6–G7.

Outcome:

```text
paired experiments
minimal descriptive quantitative evaluation
reproducible result assets
final report + demo
```

## 7. Known blockers and risks

### R1 — Measurement-quality availability

**Risk:** the selected MediaPipe API/model may not expose a suitable per-observation tracking-quality value.

**Required response:** do not invent one. Run the primary adaptive filter with quality adaptation disabled; treat any later quality source as a separately defined branch.

**Severity:** medium for optional branch, low for core project because RQ2 remains answerable with velocity adaptation.

### R2 — Legacy “1-Euro” implementation may be simplified

**Risk:** existing code may omit derivative low-pass `d_cutoff` while being named fixed 1-Euro.

**Required response:** audit against Section 7 of `03`; replace/rename before final comparisons. Old incompatible benchmark results cannot be treated as canonical-baseline results.

**Severity:** high for RQ2 validity.

### R3 — ROI cropping may alter provider geometry

**Risk:** legacy code may infer directly on variable-size ROI crops, changing normalized coordinate/apparent-scale semantics between conditions.

**Required response:** baseline must preserve full-frame geometry as specified. ROI-only inference belongs to future optimization unless fully remapped/evaluated.

**Severity:** high for fair preprocessing experiments.

### R4 — Non-deterministic live comparison

**Risk:** comparing methods from separate live-camera performances confounds algorithm condition with different hand motion/camera frames.

**Required response:** record once and compare through ReplayRuntime wherever pairing is possible.

**Severity:** high for experimental credibility.

### R5 — Pseudoreplication

**Risk:** if inferential statistics are later used, treating thousands of adjacent frames as independent samples can produce misleading results.

**Required response:** for optional inferential analysis, use trial/run/session-level metrics by default.

**Severity:** high only when inferential claims are made; otherwise this does not create a mandatory course task.

### R6 — Camera auto exposure/white balance

**Risk:** automatic camera controls alter illumination conditions during Experiment B.

**Required response:** lock controls when reliably supported, otherwise let them settle and document the limitation.

**Severity:** medium.

### R7 — Scope expansion through demo features

**Risk:** 3D UI polish, picking, extra models, or product features consume time before the DIP experiments are valid.

**Required response:** protect G0–G4 and Experiment A/B/C/D work first. Optional picking can be dropped without harming core RQs.

**Severity:** high for schedule.

### R8 — Model/dependency drift

**Risk:** changing MediaPipe/model/dependency versions changes outputs while old results are reused.

**Required response:** record versions/checksums and rerun/version-separate affected final results.

**Severity:** medium-high.

### R9 — No verified implementation status

**Risk:** planning assumes modules/tests exist because they were described in specs.

**Required response:** current task begins with repository inspection and evidence-based gate status.

**Severity:** immediate.

## 8. Definition of Done — final-term project

This section is the **only canonical final Definition of Done**.

The course project is complete only when every mandatory item below is satisfied or explicitly marked not applicable by an approved spec change.

### 8.1 Governance and scope

- six canonical docs are current and consistent;
- final implementation stays within the Master Spec scope;
- no silent architecture/equation/interface/experiment changes remain undocumented;
- no final claim relies on fabricated or target numbers.

### 8.2 Core architecture

- Core does not depend on 3D scene/application classes;
- MediaPipe/provider objects do not leak downstream of the provider adapter;
- RealtimeRuntime and ReplayRuntime both use the specified Core contracts;
- explicit color, coordinate, and timestamp semantics are respected;
- invalid/missing data is explicit rather than represented by fake zeros.

### 8.3 DIP preprocessing

- ROI SEARCHING/TRACKING/COASTING behavior works and is tested;
- invalid ROI safely falls back;
- HSV illumination descriptors are implemented/logged;
- illumination switching is temporally stabilized/hysteretic;
- CLAHE/bypass is configurable;
- baseline preprocessing preserves full-frame detector geometry;
- P0/P1 preprocessing modes are reproducible.

### 8.4 Tracking and temporal filtering

- raw F0 path works;
- canonical fixed F1 includes derivative low-pass `d_cutoff` and passes acceptance tests;
- proposed bounded adaptive F2 passes numerical/bound tests;
- measurement-quality handling conforms to the single contract in `02_ARCHITECTURE_AND_CONTRACTS.md`;
- tracking loss does not inject zeros;
- long gaps/loss reset state correctly;
- first reacquired frame is interaction-neutral.

### 8.5 Gesture and extension

- pinch uses documented hand-scale normalization;
- pinch hysteresis works;
- rotation/scale deltas are bounded/deadzoned as configured;
- 3D extension consumes `InteractionState` rather than Core internals;
- at least one rendered STEM object can be manipulated in the demo;
- optional picking is not required if omitted deliberately.

### 8.6 Testing

- required unit tests pass;
- canonical/adaptive synthetic filter tests pass;
- replay integration test passes;
- configuration validation tests pass;
- logging/analysis smoke tests pass;
- runtime camera/demo smoke test passes on the presentation machine or an explicitly documented compatible machine;
- no one claims unexecuted tests passed.

### 8.7 Experiments

- F0/F1/F2 comparison is collected using documented paired inputs where appropriate;
- P0/P1 illumination comparison is collected;
- one predefined primary static-jitter metric is reported;
- one predefined primary responsiveness metric is reported;
- one predefined primary illumination/tracking-stability outcome is reported for P0/P1;
- actual trial/run count and exclusion rules are documented;
- final run metadata/config/model/code/schema identities are preserved;
- no required FPS, latency, accuracy, jitter-reduction percentage, or other numerical success threshold exists;
- detailed software-performance benchmarking is optional;
- full ablation is optional;
- inferential statistics, p-values, confidence intervals, and effect sizes are optional and are included only if actually performed with an appropriate design.

### 8.8 Results and report

- required plots/tables can be regenerated from saved run artifacts;
- DIP-focused before/after image evidence is included without overstating tracking benefit;
- Results contain measured values only;
- Discussion covers trade-offs, failure cases, limitations, and threats to validity;
- Conclusion answers RQ1–RQ3 only to the degree supported by evidence;
- the report does not claim metric real-world 3D hand tracking;
- the report distinguishes canonical methods, project adaptations, and measured outcomes.

### 8.9 Reproducibility and delivery

- a clean setup procedure exists;
- model acquisition/checksum information exists;
- resolved configs for final runs exist;
- code revision for final runs is immutable/identifiable;
- run artifacts are machine-readable;
- analysis regeneration procedure works;
- default privacy behavior does not store/upload raw video without explicit configuration;
- final demo and report assets are packaged for submission.

## 9. Post-course roadmap — extension seams only

These phases are FUTURE and are not part of M0 Definition of Done.

### M1 — Engineering hardening

Potential work:

- packaged installer/launcher;
- camera/device compatibility matrix;
- settings migration;
- calibration profiles;
- crash recovery and structured diagnostic bundle;
- profiling-driven performance optimization;
- async/latest-frame runtime kept separate from deterministic replay semantics.

### M2 — User MVP

Potential work:

- real lesson/content architecture above `InteractionState`;
- onboarding/UI/UX;
- accessibility and user preference calibration;
- broader user/device testing.

### M3 — Product validation

Potential work:

- broader lighting/background/user conditions;
- long-session reliability;
- privacy/security/legal review;
- consent/retention/deletion behavior if recording/user data is stored;
- licensing review for code, model, assets, and content.

### M4 — Distribution/scale

Potential work:

- update/rollback strategy;
- signed releases;
- support process;
- deployment/operations appropriate to the chosen product model.

None of M1–M4 should be implemented during the course solely to make the architecture “look commercial.” Build only thin seams now.

## 10. Status-update template

When project status changes, update Sections 3–7 using evidence:

```text
Date:
Current gate/stage:
Evidence completed:
Current task:
Next tasks:
Blockers:
Risks changed:
Experiments/results invalidated by recent changes:
```

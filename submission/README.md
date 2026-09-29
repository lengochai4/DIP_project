# DIP Touchless STEM — Final Submission

## 1. Project overview

**DIP Touchless STEM** is a Digital Image Processing final-term project and research-ready prototype for real-time touchless interaction with rendered 3D STEM content using a single RGB webcam.

The project investigates a lightweight processing pipeline for webcam-based hand interaction under practical limitations such as:

- illumination variation;
- landmark jitter;
- temporary tracking loss;
- the smoothing-versus-responsiveness trade-off.

The primary academic contribution is the **Digital Image Processing and temporal signal-processing pipeline and its controlled evaluation**.

The rendered 3D application is a demonstration and validation layer. It is not presented as the primary research contribution.

### Processing pipeline

```text
RGB Webcam / Recorded Replay
        ↓
Frame + Timing Contract
        ↓
ROI Management
        ↓
Illumination Analysis
        ↓
Adaptive ROI Preprocessing
        ↓
MediaPipe Hand Landmark Provider
        ↓
Measurement Validation
        ↓
Raw / Fixed / Adaptive Temporal Filtering
        ↓
Gesture + Coordinate Mapping
        ↓
InteractionState
        ↓
Rendered 3D STEM Extension
```

The canonical specification set is version:

```text
canonical-v1.2
```

---

## 2. Research questions

### RQ1 — Illumination preprocessing

Under the tested lighting conditions, does ROI-based adaptive illumination preprocessing improve hand-landmark detection/tracking robustness or stability compared with unprocessed input?

### RQ2 — Temporal filtering

Does the proposed bounded adaptive 1-Euro strategy reduce measured temporal jitter while preserving responsiveness compared with raw landmarks and a canonical fixed 1-Euro baseline?

### RQ3 — Practical interaction

Can the resulting processed signal support real-time touchless manipulation of rendered 3D STEM objects using a single RGB camera under the tested conditions?

---

## 3. Main implemented components

The final project includes:

- RGB webcam acquisition;
- deterministic recorded replay;
- explicit frame and timestamp handling;
- ROI state management;
- HSV illumination analysis;
- adaptive CLAHE/bypass preprocessing;
- MediaPipe Hand Landmarker integration through a project-owned adapter;
- explicit measurement validity;
- Raw landmark baseline;
- canonical fixed 1-Euro baseline;
- bounded adaptive 1-Euro filter;
- tracking-loss and reacquisition handling;
- normalized pinch gesture detection with hysteresis;
- bounded rotation and scale interaction;
- renderer-independent `InteractionState`;
- Pygame/PyOpenGL 3D STEM demonstration;
- structured run logging;
- resolved-configuration hashing;
- deterministic experiment batch execution;
- automatic descriptive metric/plot regeneration;
- selected reproducible G7 evidence package.

The project does **not** claim metric 3D hand reconstruction, physical camera depth, multi-camera tracking, multi-user tracking, cloud inference, or a full commercial VR/AR system.

---

## 4. Requirements

The project requires:

```text
Python >= 3.11
```

The verified development environment used Python 3.11.

The package metadata is defined in:

```text
pyproject.toml
```

---

## 5. Environment setup

From the repository root:

```powershell
python -m venv .venv
```

Activate the environment on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Upgrade `pip`:

```powershell
python -m pip install --upgrade pip
```

Install the project and development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Verify the environment:

```powershell
python --version
pytest --version
```

Run the automated test suite:

```powershell
pytest
```

The last recorded full G7 regression before final packaging completed with:

```text
433 passed
```

---

## 6. MediaPipe model asset

The runtime uses the external model:

```text
models/hand_landmarker.task
```

The model binary is not represented by a tracked model file in the verified Git file list, so it must be present locally before running the webcam or replay pipelines.

The exact model used by the final demo has SHA-256:

```text
fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1
```

Verify the local model before reproducing the final runtime:

```powershell
Get-FileHash models/hand_landmarker.task -Algorithm SHA256
```

Expected hash:

```text
FBC2A30080C3C557093B5DDFC334698132EB341044CCEE322CCF8BCF3607CDE1
```

Replacing the model may change provider behavior and therefore may invalidate direct reproducibility of the recorded results.

---

## 7. Run the final interactive demo

From the repository root with the virtual environment active:

```powershell
python -m extensions.stem3d.live_demo
```

### Interaction

```text
Index fingertip movement
    → rotate the 3D object

Thumb-index pinch + pinch-distance variation
    → scale the object
```

### Presentation controls

```text
S      start
R      reset
Q      stop
ESC    stop
```

The final presentation shell also displays camera and runtime status information while preserving the Core processing path.

### Important CLI note

The current modules:

```text
extensions.stem3d.live_demo
extensions.stem3d.demo
```

do not implement a conventional `--help` exit path.

Invoking them with `--help` currently starts the application instead of only displaying help text.

Use the commands above directly rather than relying on `--help`.

---

## 8. Deterministic replay

A single replay condition can be executed with:

```powershell
python -m experiments.run_replay `
    --profile f0 `
    --source <recorded-source.avi> `
    --experiment-id <experiment-id> `
    --trial-id <trial-id>
```

Available profiles are:

```text
f0
f1
f2
p0
p1
```

An explicit model may also be supplied:

```powershell
python -m experiments.run_replay `
    --profile f0 `
    --source <recorded-source.avi> `
    --experiment-id <experiment-id> `
    --trial-id <trial-id> `
    --model models/hand_landmarker.task
```

The replay runtime preserves deterministic source ordering and allows compared methods to operate on the same recorded input.

---

## 9. Run paired experiment batches

The frozen final experiment manifests are:

```text
experiments/final/g7_a1_static.yaml
experiments/final/g7_a2_dynamic.yaml
experiments/final/g7_b_normal.yaml
experiments/final/g7_b_lowlight.yaml
```

Example:

```powershell
python -m experiments.run_batch `
    --manifest experiments/final/g7_a1_static.yaml
```

Other final batches use the corresponding manifest path.

The manifests preserve:

- compared profiles;
- recorded source identity;
- predefined analysis window;
- primary metric;
- planned comparisons;
- exclusion policy.

---

## 10. Regenerate descriptive analysis

Analysis is regenerated from immutable run artifacts through:

```powershell
python -m analysis.regenerate `
    --batch-index <path-to-batch-index>
```

Optional arguments include:

```text
--runs-root
--output-root
```

The exact batch-index path depends on the run output location and is therefore intentionally not hard-coded here.

The analysis pipeline consumes recorded run metadata, frame logs, landmark logs and experiment provenance rather than manually edited result values.

---

## 11. Record a deterministic replay source

The source recorder can be invoked with:

```powershell
python -m experiments.record_source `
    --output <output-video.avi> `
    --duration-s 12 `
    --settle-s 3 `
    --lighting-label <label> `
    --auto-exposure unknown `
    --auto-white-balance unknown
```

The final G7 acquisition plan used nominal camera settings of:

```text
camera index: 0
requested width: 640
requested height: 480
requested FPS: 30
recording duration: 12 s
settle time: 3 s
```

Camera automatic-control state is recorded as `unknown` when it was not independently verified.

---

# 12. Final controlled evaluation

The G7 controlled evaluation used three experiment groups.

## A1 — Static temporal stability

Compared:

```text
F0 — Raw
F1 — canonical fixed 1-Euro
F2 — bounded adaptive 1-Euro
```

Preprocessing was held constant at P1.

Primary metric:

```text
radial RMS jitter
```

Measured on:

```text
landmark index: 8
stage: filtered
coordinate space: FRAME_NORMALIZED
analysis window: 2.0–10.0 s
```

### Final A1 results

Recorded trials:

```text
3
```

Evaluable trials:

```text
2
```

| Trial | Common usable frames | F0 | F1 | F2 |
|---|---:|---:|---:|---:|
| trial-001 | 5 | 0.0066075842 | 0.0016284495 | 0.0016290706 |
| trial-002 | 0 | unavailable | unavailable | unavailable |
| trial-003 | 128 | 0.0305971417 | 0.0267044614 | 0.0267533003 |

`trial-002` is retained in the experiment record with:

```text
no_common_usable_frames
```

In the two evaluable trials, both F1 and F2 produced lower radial RMS jitter than F0.

However:

- only two trials produced an evaluable metric;
- `trial-001` contains only five common usable frames;
- F1 and F2 are extremely close to one another;
- the sample size is too limited for a population-level or inferential superiority claim.

---

## A2 — Dynamic responsiveness

Primary metric:

```text
trajectory_deviation_rmse
```

F0 was the reference trajectory.

Recorded trials:

```text
3
```

Evaluable trials:

```text
0
```

All three final trials produced:

```text
no_common_usable_frames
```

Observed diagnostic behavior:

```text
trial-001: all 360 replay frames NO_HAND
trial-002: all 360 replay frames NO_HAND
trial-003: one VALID raw frame occurred outside the predefined analysis window
```

Therefore the predefined quantitative responsiveness metric is unavailable for the final A2 source set.

The experiment was not replaced and its analysis window was not changed after observing the result.

Consequently, the final project does **not** claim that the adaptive filter has demonstrated a complete jitter-versus-responsiveness advantage over the baselines.

---

## Experiment B — Illumination robustness

Compared:

```text
P0 — preprocessing bypass + Raw temporal path
P1 — adaptive ROI preprocessing + Raw temporal path
```

Primary metric:

```text
valid_hand_observation_rate
```

Each condition used 241 analyzed frames per trial.

### B-normal

| Trial | P0 | P1 |
|---|---:|---:|
| trial-001 | 0.0207468880 | 0.0207468880 |
| trial-002 | 0.0000000000 | 0.0000000000 |
| trial-003 | 0.5311203320 | 0.5311203320 |

P0 and P1 produced the same primary outcome in every tested normal-light trial.

### B-lowlight

| Trial | P0 | P1 |
|---|---:|---:|
| trial-001 | 0.0 | 0.0 |
| trial-002 | 0.0 | 0.0 |
| trial-003 | 0.0 | 0.0 |

The challenging-light recordings were labeled:

```text
low-light-room
```

However, an important limitation was observed.

For every analyzed P1 frame in both normal and low-light groups:

```text
illumination state = NORMAL
enhancement_active = False
```

Therefore the adaptive policy did not activate CLAHE during these analyzed frames.

The P0/P1 equality must **not** be interpreted as evidence that CLAHE itself is ineffective.

The final experiment only establishes that, under these recorded sources and resolved configuration, the adaptive activation policy did not improve the measured valid-hand-observation rate and did not activate its CLAHE branch.

---

# 13. Research-question evidence boundary

## RQ1

The primary P0/P1 valid-hand-observation metric was available for all final Experiment B trials.

No improvement was observed under the tested final conditions.

However, CLAHE was not activated by the adaptive P1 policy during the analyzed frames, so the result cannot be generalized into a direct CLAHE-versus-bypass effectiveness conclusion.

## RQ2

Static A1 evidence exists for two of three final trials and shows lower measured radial RMS jitter for F1/F2 than F0 in those two trials.

The required A2 responsiveness metric is unavailable for all three final dynamic trials.

Therefore the final evidence is insufficient to claim that the proposed F2 filter has demonstrated the complete intended jitter-versus-responsiveness advantage.

## RQ3

Physical realtime demonstrations showed that the implemented signal pipeline can drive practical touchless 3D object rotation and scale interaction using a single RGB webcam.

This is practical demo evidence only.

It is not treated as evidence that F2, P1, or any other algorithmic condition is universally superior.

---

# 14. Selected submission evidence

The curated final evidence is stored under:

```text
submission/evidence/
```

## A1 static stability

```text
submission/evidence/a1_static/metrics.csv
submission/evidence/a1_static/provenance.json
submission/evidence/a1_static/static_jitter.png
submission/evidence/a1_static/trajectories.csv
submission/evidence/a1_static/trajectory_xy.png
```

## A2 dynamic responsiveness

```text
submission/evidence/a2_dynamic/metrics.csv
submission/evidence/a2_dynamic/provenance.json
submission/evidence/a2_dynamic/responsiveness_unavailable.png
```

## Experiment B — normal illumination

```text
submission/evidence/b_normal/metrics.csv
submission/evidence/b_normal/provenance.json
submission/evidence/b_normal/valid_hand_rate.png
```

## Experiment B — low light

```text
submission/evidence/b_lowlight/metrics.csv
submission/evidence/b_lowlight/provenance.json
submission/evidence/b_lowlight/valid_hand_rate.png
```

## DIP-focused visual evidence

```text
submission/evidence/dip_visual/dip_clahe_frame161.json
submission/evidence/dip_visual/dip_clahe_frame161.png
```

Additional explanation of the selected evidence is available in:

```text
submission/evidence/README.md
```

---

# 15. Final demo reproducibility identity

The primary post-commit final-demo verification run is:

```text
run_id:
g7-demo-20260929-192030

processed_frames:
1188

shutdown:
clean

executed code_revision:
6a87dc50f9d3920ed9fd39a2669e266be00f9735

spec_version:
canonical-v1.2

config_hash:
ecfaeb11725d9a289b8b6e71a7650a9be5b90fbfb65e5775fe14e13ff5b83a08

model_filename:
hand_landmarker.task

model_sha256:
fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1
```

At the time this run was executed:

```text
runtime code_revision == Git HEAD
```

The exact executed revision is therefore:

```text
6a87dc50f9d3920ed9fd39a2669e266be00f9735
```

A later documentation-only commit recorded this provenance:

```text
7d62e934fed05470a1e738ea958ce0578fab8723
docs: record final demo identity
```

These two revisions have different roles:

```text
6a87dc5...
    exact code executed by the primary final live demo

7d62e93...
    later documentation commit recording that demo identity
```

They are not expected to remain equal after documentation/package commits are added.

---

# 16. Physical behavior smoke evidence

An earlier live presentation run was retained as the main physical-behavior smoke:

```text
run_id:
g7-demo-20260929-190838

processed_frames:
4947

shutdown:
clean
```

During this run the following behaviors were exercised:

- rotation;
- pinch/scale interaction;
- reset;
- hand loss and reacquisition;
- presentation status display;
- clean shutdown.

An occasional hand-like false-positive was observed around the face/background, causing a small unintended cube rotation.

This behavior is retained as a documented practical limitation rather than hidden through post-hoc threshold or algorithm changes.

---

# 17. Known limitations

The final evaluation has several important limitations.

1. Final source groups contain only three recordings each.

2. A1 produced only two evaluable paired trials.

3. One A1 trial contained only five common usable frames.

4. All three A2 trials lacked usable common landmarks in the predefined analysis window, preventing calculation of the required responsiveness metric.

5. All low-light B trials had zero valid-hand-observation rate.

6. The adaptive illumination classifier remained `NORMAL` in the analyzed B recordings, so P1 never activated CLAHE.

7. Camera auto-exposure and auto-white-balance states were not independently verified for the retained lighting sources and remain recorded as `unknown`.

8. Occasional false-positive hand-like detections were observed during the physical realtime demo.

9. The project uses a single RGB camera and does not measure metric physical hand depth.

10. Final results are descriptive. No inferential statistical claim is made.

---

# 18. Reproducibility and evidence policy

Quantitative claims in this submission are intended to remain traceable through:

```text
claim
→ metric
→ analysis output
→ run/trial identity
→ resolved configuration
→ code/model/schema revision
→ recorded source
```

Raw final experiment sources and run artifacts are not altered to improve the reported outcome.

Unavailable metrics remain explicitly unavailable instead of being converted to zero or replaced with favorable trials.

The final demo is treated as evidence that the application executed under the observed physical conditions. It is not treated as proof of algorithmic superiority.

---

# 19. Canonical project documentation

The normative specification set is:

```text
docs/00_GOVERNANCE.md
docs/01_MASTER_SPEC.md
docs/02_ARCHITECTURE_AND_CONTRACTS.md
docs/03_ALGORITHM_AND_EXPERIMENTS.md
docs/04_IMPLEMENTATION_TESTING_GUIDE.md
docs/05_PROJECT_STATUS_AND_ROADMAP.md
```

The frozen final controlled-evaluation plan is:

```text
experiments/final/G7_FINAL_TRIAL_PLAN.md
```

These files define the scope, algorithms, contracts, experimental protocol, evidence policy and final project status.

---

# 20. Summary

The project delivers a complete, modular Digital Image Processing prototype combining:

```text
adaptive ROI image preprocessing
+
explicit landmark validation
+
canonical and adaptive temporal filtering
+
safe gesture mapping
+
reproducible recorded evaluation
+
realtime 3D STEM interaction
```

The strongest final evidence is the implemented and reproducible processing architecture, controlled experiment pipeline, recorded A1 static-jitter observations, explicit negative/unavailable experimental outcomes, and functioning realtime touchless interaction demo.

The submission deliberately limits its conclusions to the evidence actually recorded.

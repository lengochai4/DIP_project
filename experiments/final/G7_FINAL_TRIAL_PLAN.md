# G7 Final Controlled Evaluation Plan

Status: frozen before final data collection.

## 1. Scope

This plan defines the final required course experiments only:

- A1 — static temporal stability;
- A2 — dynamic responsiveness characterization;
- B — illumination robustness.

No inferential statistics are planned for the course baseline.

## 2. Common acquisition configuration

Final replay sources use the existing project camera defaults:

- camera index: 0;
- requested width: 640;
- requested height: 480;
- requested FPS: 30;
- backend: default;
- recorded format: MJPG AVI;
- recorded color space: raw BGR uint8;
- preprocessing during recording: none.

Each recording command uses:

- acquisition settle time: 3.0 s before recording begins;
- recorded duration: 12.0 s;
- expected encoded frame count: 360 frames at 30 FPS.

The source recorder sidecar JSON records the actual observed camera properties,
source SHA-256, lighting label, auto-exposure status, auto-white-balance
status, software revision, and recording metadata.

If auto-exposure or auto-white-balance state is not independently verified,
the value remains `unknown`; it must not be guessed.

## 3. Replay analysis window

Each final replay experiment uses:

- warmup metadata: 2.0 s;
- analysis start: 2.0 s;
- analysis end: 10.0 s.

The same predefined window is used for all compared profiles within one trial.

The first and last two seconds of the recorded source are not part of the
primary analysis window. This rule is fixed before final outcomes are viewed.

## 4. Source groups

### A1 / B-normal source group — `static_normal`

Three source recordings:

- trial-001;
- trial-002;
- trial-003.

Procedure:

- normal room illumination;
- hand fully visible;
- index fingertip approximately stationary;
- wrist/forearm supported when practical;
- maintain approximately constant camera distance and orientation;
- avoid deliberate movement during the recording.

The same three source files are reused for:

- A1 F0/F1/F2 static stability;
- Experiment B normal-light P0/P1 comparison.

## 5. A2 source group — `dynamic_normal`

Three source recordings:

- trial-001;
- trial-002;
- trial-003.

Procedure:

- normal room illumination;
- hand fully visible;
- move the index fingertip continuously and smoothly in an approximately
  horizontal left-right trajectory between two fixed visual reference points;
- maintain approximately constant camera distance and hand orientation;
- continue the repeated motion throughout the recording.

The motion is not treated as physical ground truth. The A2 primary metric
only measures trajectory deviation of F1/F2 relative to F0 on the identical
replay source.

## 6. Experiment B challenging-light source group — `static_lowlight`

Three source recordings:

- trial-001;
- trial-002;
- trial-003.

Procedure:

- use the same approximate camera position, hand distance, background, and
  static-hand procedure as `static_normal`;
- reduce ambient/front illumination sufficiently to create a clearly more
  challenging low-light condition;
- do not deliberately alter the hand pose to help or hurt either method;
- allow the camera to settle for the predefined 3.0 s before recording.

The source sidecar must label the condition `low-light-room`.

## 7. Required conditions and primary metrics

### A1

Profiles:

- F0 — Raw landmarks with P1 preprocessing;
- F1 — canonical fixed 1-Euro with P1 preprocessing;
- F2 — bounded adaptive 1-Euro with P1 preprocessing.

Primary metric:

`radial_rms_jitter`

Landmark:

index 8, filtered stage, FRAME_NORMALIZED coordinates.

Planned comparisons:

- F0 vs F1;
- F0 vs F2.

### A2

Profiles:

- F0;
- F1;
- F2.

Primary metric:

`trajectory_deviation_rmse`

F0 is the reference trajectory.

Planned comparisons:

- F0 vs F1;
- F0 vs F2.

The result must not be described as physical tracking accuracy or
sensor-to-photon latency.

### Experiment B

Profiles:

- P0 — preprocessing bypass + Raw temporal path;
- P1 — adaptive ROI CLAHE preprocessing + Raw temporal path.

Primary metric:

`valid_hand_observation_rate`

Normal and low-light source groups are evaluated separately using the same
P0/P1 comparison.

## 8. Exclusion policy

Exclusions are defined before final results are inspected.

A complete trial may be excluded only for one of these reasons:

- recorded source file is corrupted or unreadable;
- replay timestamps are invalid/non-monotonic such that the predefined
  experiment cannot be executed correctly;
- paired profiles fail the required frame/timestamp pairing invariant because
  of a source/runtime failure;
- complete camera/source acquisition failure makes the intended trial
  unavailable.

The following are not valid exclusion reasons:

- poor tracking;
- NO_HAND frames;
- high jitter;
- unfavorable P0/P1, F0/F1/F2 result;
- noisy segment that makes one method look worse;
- post-hoc selection of a more favorable analysis interval.

Tracking failures and NO_HAND frames in Experiment B remain part of the
primary valid-observation-rate outcome.

### Undefined paired primary metric

A recorded trial is retained even when the predefined A1/A2 analysis
window contains no common usable F0/F1/F2 landmark frames.

In that case:

- the trial is not excluded;
- the paired primary metric is reported as unavailable;
- the reason is recorded as `no_common_usable_frames`;
- the evaluable-trial count is reported separately from the recorded
  trial count;
- no replacement recording is substituted for the original final trial
  solely because of tracking failure.

## 9. Final trial count

Planned unique recorded sources:

- `static_normal`: 3;
- `dynamic_normal`: 3;
- `static_lowlight`: 3.

Total unique recorded source videos: 9.

Because the final evaluation uses only three replay sequences per source
group, the final report must describe the sample size as limited and avoid
unsupported population-level claims.

## 10. Final evidence discipline

All final claims must trace through:

claim
→ primary metric
→ regenerated analysis output
→ run/trial IDs
→ resolved configuration
→ code/model/schema revision
→ recorded source identity and SHA-256.

No final superiority, robustness, accuracy, jitter-reduction, latency, or
performance claim is made until the final paired runs and analysis outputs
have actually been generated.

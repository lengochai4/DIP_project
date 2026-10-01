# Full-hand geometry, classification and temporal stabilization

This is an additive v1.1 Extension module. It is not imported by the v1.0
default v1.0 application composition, does not implement the Core GestureEngine protocol,
and emits no InteractionState or application commands.

## A2 to A3 data flow

```text
TrackingFrame.filtered_landmarks + matching FrameGeometry
    -> extract_hand_geometry
    -> HandGeometry
    -> classify_pose(hand, explicit PoseThresholds)
    -> PoseObservation
```

FingerState is EXTENDED / FLEXED / INTERMEDIATE / UNKNOWN. HandPose is
OPEN / POINT / PINCH / FIST / UNKNOWN. All contracts and nested collections
are immutable. PoseObservation retains frame identity, per-finger states,
geometry reasons, predicate results and classification reasons. No confidence
is synthesized and no handedness metadata is needed.

## Caller-supplied thresholds

FingerThresholds, ThumbThresholds and PoseThresholds have no implicit tuning
defaults. A caller must supply finite, ordered values explicitly. Angles are
radians; straightness is dimensionless; distances are divided by A2 palm width.
Test values are synthetic fixture parameters, not calibrated settings or research
results. Any future runtime profile must record its thresholds separately from
the frozen G7 configuration. This module adds no profile loader or sensitivity
setting.

## Single-frame rules

- For the four non-thumb fingers, EXTENDED requires both interior joint angles
  at or above the configured minimum and straightness at or above its minimum.
  FLEXED requires at least one interior angle at or below the flexion maximum
  and straightness at or below its maximum. Both boundaries are inclusive.
- Opposed angle/straightness evidence (extended angles with flexed straightness,
  or a flexed angle with extended straightness) is UNKNOWN. Other unresolved
  chain geometry is INTERMEDIATE.
- Thumb uses its own chain thresholds. EXTENDED also requires sufficient
  separation from both index/pinky MCPs and an axis-to-distal-palm angle within
  its configured maximum. FLEXED also requires the tip to be near at least one
  of those MCPs. A straight but opposed thumb is INTERMEDIATE, not automatically
  a curled thumb. Missing thumb features are UNKNOWN.
- OPEN requires five EXTENDED states. POINT requires index EXTENDED and
  middle/ring/pinky FLEXED; the thumb may be any known state. FIST requires five
  FLEXED states. Intermediate states never satisfy extended/flexed predicates.
- PinchGeometry exposes independent `distance < enter` and `distance > exit`
  predicates. Equalities and the interval between thresholds are an unresolved
  boundary band. No active latch, previous-pose input, dwell or timestamp history
  exists in A3.
- On valid, complete geometry with known finger states, pinch enter takes
  precedence over other pose matches, including POINT/FIST. Invalid geometry or
  UNKNOWN finger evidence prevents a PINCH result too. The pinch boundary band
  is UNKNOWN rather than an implicit continuation of an earlier pose. Otherwise
  exactly one non-pinch predicate must match; no match/conflict is UNKNOWN.

All predicates use A2 aspect-corrected, anatomical palm-relative x/y geometry.
There are no global tip.y rules or z/depth calculations. The predicates are
invariant under translation, uniform scale, in-plane rotation and reflection
where the underlying geometry is valid. Projection, occlusion and out-of-plane
poses remain unvalidated; synthetic fixtures are not physical robustness evidence.

## Compatibility/change record

- Change: add pure finger-state estimation and single-frame pose classification.
- Reason: approved v1.1 A3, building on A2 without changing v1.0 behavior.
- Canonical sections changed: none; new contracts are Extension-only.
- Modules: pose_contracts.py, finger_states.py, pose_classifier.py, exports.
- Algorithmic impact: isolated geometric predicates, no Core processing impact.
- Experimental impact: none; no evidence, experiments or research logs changed.
- Compatibility impact: existing A2 API and legacy application path unchanged.
- Tests: synthetic landmark poses, transforms, thumb cases, boundary/conflict
  cases, invalid geometry, statelessness and immutable diagnostics.
- Existing results invalidated: no; the module is not wired into any runtime.

## A4 temporal tracker

```text
PoseObservation + explicit TrackingStatus + filter_reset flag
    -> TemporalPoseTracker.update
    -> immutable StablePoseState
```

The caller supplies TemporalPoseConfig: ordinary enter/exit dwell, PINCH
enter/exit dwell, rearm dwell and reset gap, all in seconds. There are no
production defaults. Dwell is measured from the first continuous candidate
timestamp, not frame count or wall-clock time. Confirmation occurs at `>= dwell`;
a timestamp gap resets only at `> reset_gap_s`. Switching away from a stable
pose requires the maximum of the old pose's exit dwell and new pose's enter
dwell, measured concurrently. A new candidate restarts that reference. A return
to the old stable pose cancels the pending switch. Every replacement-candidate
frame is action-blocked until confirmed.

Initialization, run change, non-finite/non-increasing timestamps, non-increasing
frame identity, excessive gaps, filter reset, reacquisition and explicit reset
produce an immediate neutral state. Unusable tracking/geometry also releases
immediately, cancels pending dwell and disarms. Repeated continuous loss frames
do not repeat reset events. Invalid samples never contribute to dwell.

The initialization/reacquisition/reset frame itself cannot rearm. Subsequent
continuous known non-PINCH poses with `pinch.exit=True` must satisfy rearm dwell.
The frame completing rearm is still neutral; pose entry dwell starts on the next
frame. A hand that reappears pinched cannot reactivate until released evidence
rearms it. UNKNOWN cancels rearm and pending transitions and safely releases
the stable pose, regardless of configured exit dwell.

The sole UNKNOWN exception is A3's exact PINCH_BOUNDARY_BAND observation with
usable geometry and known finger states. If PINCH is already stable/armed, it
retains its latch across that band, cancelling any pending exit transition.
**action_allowed remains false on every UNKNOWN band frame.** A later definite
PINCH-enter sample may resume permission; definite released candidates must
satisfy PINCH exit dwell before changing stable pose. A band cannot finish a
pending PINCH entry or create a latch. Other UNKNOWN reasons never retain PINCH.

Consumers must not infer action permission from stable_pose/pinch_latched.
Only action_allowed describes current-frame eligibility; it is not a rotation,
scale, click or other command. No runtime/InteractionState/UI integration exists.

Diagnostics expose raw candidate, pending pose, candidate/rearm reference times,
stable pose, armed flag, latch, per-update reasons and original A3 source reasons.
transition_id increments on stable pose changes, including safe release;
reset_id increments on reset events. Both remain monotonic for the lifetime of
one tracker, even across explicit reset and run changes. There are no fabricated
measurements or tracking confidence values. Explicit reset returns a neutral
snapshot immediately and makes the next sample initialization-neutral.

A4 compatibility/change record: additive timestamp-driven state machine in
temporal.py/temporal_contracts.py; canonical contracts and Core behavior unchanged;
synthetic dwell/glitch/boundary/loss/reset/replay tests added; no experimental
impact or invalidated G7 results. Physical validation and timing calibration have
not been performed for A4.

## A5 OBSERVE_FULL_HAND composition

Run the opt-in application (existing Python 3.11 environment, model and demo3d
dependencies documented in the submission guide):

```powershell
python -m extensions.stem3d.full_hand_app --mode OBSERVE_FULL_HAND
```

The default development profile is `config/extensions/full_hand_observe.yaml`;
override with `--profile <path>`. It contains explicit uncalibrated A3/A4 starting
values from synthetic fixtures. It changes no legacy gains, pinch thresholds or
G7 configuration. `--mode LEGACY` delegates to the unchanged default composition;
`python -m extensions.stem3d.live_demo` also remains legacy.

```text
camera source -> GeometryCaptureSource (actual image.shape, SAME FramePacket)
    -> unchanged Core provider/validator/filter
    -> unchanged legacy GestureEngine -> SAME InteractionState
    -> controller/router/scene (one delivery)
    -> readonly presentation callback
        -> A2 geometry -> A3 classification -> A4 temporal tracker
        -> FullHandSnapshot -> separate diagnostic sink
        -> existing legacy presentation callback
```

The observer never calls the gesture engine, interaction consumer, router or
scene. No full-hand command adapter is present. Observation runs after Core
logging and command delivery, outside Core stage-timing measurements. It may add
unmeasured frame-loop overhead; deterministic parity applies to the same input
samples, not an assertion that separately captured physical runs are identical.

Source/presentation/tracking/interaction identity and actual dimensions must
align. An observer alignment/analysis failure resets only the observer and emits
an unavailable diagnostic; legacy delivery continues. Source open/close clears
cached geometry/snapshots and resets the tracker, including restart. Core loss,
reacquisition and filter-reset metadata feed A4 explicitly. Duplicate diagnostic
delivery of the same identity is idempotent. Sinks receive immutable diagnostics,
never the source image or mutable processing components. Sink errors are reported
and do not replace legacy output.

`FullHandObserver.latest_snapshot` and its optional snapshot sink make current
pose/finger/temporal diagnostics available to future presentation adapters;
current UI fields/layout are unchanged. Console prints state changes. Separate
files under `runs/full-hand-observe/<legacy-run-id>/` are:

- `manifest.json`: sidecar schema, legacy run metadata/revision/model/config
  provenance, resolved observer profile and profile SHA-256.
- `snapshots.jsonl`: one snapshot per processed frame, full geometry validity and
  reasons, finger predicates, pose predicates, temporal/reset/transition identity.

No images/video are written by this sidecar. These are local development
observation artifacts, never frozen G7 evidence or replacements for Core logs.
The journal closes even after cancellation, provider/runtime errors or controller
shutdown. No files are opened until the application is actually started.

P1 is ready to execute, but has NOT RUN: use one hand at a time, show OPEN,
POINT, PINCH and FIST, pause between poses, try comfortable in-plane rotations
and both left/right hands separately, then withdraw/reacquire. Record visible
candidate/stable states, ambiguity, false classifications and tracking drops
honestly against run/profile identity. UNKNOWN/uncalibrated thresholds remain
expected limitations; do not tune legacy sensitivity to make observation pass.

A5 change record: add observation/profile/journal modules and a separate entry
point; add optional Extension-only factory/source/presentation hooks to the live
composition with identical defaults. Canonical/Core contracts, research logger
schema, scenes/router and legacy commands are unchanged. Tests compare every
InteractionState field and Core log object on deterministic inputs, single scene
delivery and router click, alignment, reset/loss/restart and failure cleanup.
Existing G7 results are not invalidated. No G9 source is restored or copied.

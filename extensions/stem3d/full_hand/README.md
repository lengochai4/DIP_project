# Full-hand geometry, classification and temporal stabilization

This is an additive v1.1 Extension module. It is not imported by the v1.0
application composition, does not implement the Core GestureEngine protocol,
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

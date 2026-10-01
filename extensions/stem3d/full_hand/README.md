# Full-hand geometry and single-frame classification

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

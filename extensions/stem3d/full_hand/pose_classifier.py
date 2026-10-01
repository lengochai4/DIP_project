"""Pure single-frame pose classification over A2 geometry, not a gesture engine."""

import math

from .contracts import Finger, HandGeometry
from .finger_states import estimate_finger_state
from .pose_contracts import (
    ClassificationReason as Reason, FingerObservation, FingerState, HandPose,
    PinchGeometry, PoseObservation, PoseThresholds, PredicateDiagnostic as Predicate,
)


def evaluate_pinch_geometry(distance: float | None, thresholds: PoseThresholds) -> PinchGeometry:
    """d < enter, d > exit; both equalities belong to the unresolved band.

    No previous active state is accepted or stored. A later temporal layer may
    use these predicates, but A3 never latches PINCH in the band.
    """
    if distance is None or not math.isfinite(distance) or distance < 0:
        return PinchGeometry(None, None, None, None, (
            Predicate("pinch_enter", None), Predicate("pinch_exit", None),
            Predicate("pinch_boundary_band", None),
        ))
    enter = distance < thresholds.pinch_enter_distance_palm
    exit_ = distance > thresholds.pinch_exit_distance_palm
    band = not enter and not exit_
    return PinchGeometry(distance, enter, exit_, band, (
        Predicate("pinch_enter", enter, distance, thresholds.pinch_enter_distance_palm, "<"),
        Predicate("pinch_exit", exit_, distance, thresholds.pinch_exit_distance_palm, ">"),
        Predicate("pinch_boundary_band", band),
    ))


def classify_pose(hand: HandGeometry, thresholds: PoseThresholds) -> PoseObservation:
    """OPEN: all extended; POINT: index extended, other three non-thumb flexed.

    POINT allows any known thumb state. FIST requires all five flexed. PINCH
    enter takes precedence over POINT/FIST. Invalid/conflicting features and
    the pinch boundary band are UNKNOWN. Intermediate states are not errors,
    but never substitute for required extended/flexed predicates.
    """
    supplied = {f.finger: f for f in hand.fingers}
    complete = len(hand.fingers) == 5 and set(supplied) == set(Finger)
    fingers = tuple(
        estimate_finger_state(supplied[f], thresholds.fingers, thresholds.thumb)
        if f in supplied else FingerObservation(f, FingerState.UNKNOWN, (),
                                                (Reason.MISSING_FEATURES,))
        for f in Finger
    )
    usable = hand.valid and hand.palm is not None and complete
    pinch = evaluate_pinch_geometry(hand.thumb_index_distance_palm if usable else None,
                                   thresholds)
    known = all(f.state is not FingerState.UNKNOWN for f in fingers)
    states = {f.finger: f.state for f in fingers}
    open_ = all(s is FingerState.EXTENDED for s in states.values()) if usable and known else None
    point = (states[Finger.INDEX] is FingerState.EXTENDED and
             all(states[f] is FingerState.FLEXED for f in (Finger.MIDDLE, Finger.RING, Finger.PINKY))) if usable and known else None
    fist = all(s is FingerState.FLEXED for s in states.values()) if usable and known else None
    predicates = (
        Predicate("geometry_usable", usable), Predicate("finger_states_known", known),
        *pinch.predicates, Predicate("pose_open", open_),
        Predicate("pose_point", point), Predicate("pose_fist", fist),
    )
    pose, reasons = HandPose.UNKNOWN, ()
    if not usable:
        reasons = (Reason.INVALID_GEOMETRY,)
    elif not known:
        reasons = (Reason.FINGER_UNKNOWN,)
    elif pinch.enter is None:
        reasons = (Reason.MISSING_FEATURES if hand.thumb_index_distance_palm is None
                   else Reason.INVALID_FEATURE_RANGE,)
    elif pinch.enter:
        pose = HandPose.PINCH
    elif pinch.boundary_band:
        reasons = (Reason.PINCH_BOUNDARY_BAND,)
    else:
        matches = tuple(p for p, matched in (
            (HandPose.OPEN, open_), (HandPose.POINT, point), (HandPose.FIST, fist),
        ) if matched)
        if len(matches) == 1:
            pose = matches[0]
        else:
            reasons = (Reason.CONFLICTING_POSES if matches else Reason.NO_POSE_MATCH,)
    return PoseObservation(hand.frame_geometry, pose, fingers, pinch, predicates,
                           reasons, hand.reasons)

"""Deterministic geometric finger states; no global tip.y or temporal state."""

import math

from .contracts import Finger, FingerGeometry
from .pose_contracts import (
    ClassificationReason as Reason, FingerObservation, FingerState,
    FingerThresholds, PredicateDiagnostic as Predicate, ThumbThresholds,
)


def _unknown(finger: FingerGeometry, reason: Reason) -> FingerObservation:
    return FingerObservation(finger.finger, FingerState.UNKNOWN, (),
                             (reason,), finger.reasons)


def estimate_finger_state(
    finger: FingerGeometry, thresholds: FingerThresholds,
    thumb_thresholds: ThumbThresholds,
) -> FingerObservation:
    """Both joints plus chain straightness; thumb also uses palm geometry.

    Extended comparisons are inclusive >=; flexed comparisons inclusive <=.
    Crossed angle/straightness evidence is UNKNOWN, not an arbitrary winner.
    Unresolved but non-conflicting geometry is INTERMEDIATE.
    """
    if not finger.valid:
        return _unknown(finger, Reason.INVALID_GEOMETRY)
    if finger.joint_angles_rad is None or finger.straightness is None:
        return _unknown(finger, Reason.MISSING_FEATURES)
    if (any(not 0 <= a <= math.pi for a in finger.joint_angles_rad)
            or not 0 <= finger.straightness <= 1 + 64 * math.ulp(1.0)):
        return _unknown(finger, Reason.INVALID_FEATURE_RANGE)
    t = thumb_thresholds.chain if finger.finger is Finger.THUMB else thresholds
    angle = min(finger.joint_angles_rad)
    straightness = finger.straightness
    predicates = (
        Predicate("chain_extended_angles", angle >= t.extended_min_angle_rad,
                  angle, t.extended_min_angle_rad, ">="),
        Predicate("chain_flexed_angle", angle <= t.flexed_max_angle_rad,
                  angle, t.flexed_max_angle_rad, "<="),
        Predicate("chain_extended_straightness", straightness >= t.extended_min_straightness,
                  straightness, t.extended_min_straightness, ">="),
        Predicate("chain_flexed_straightness", straightness <= t.flexed_max_straightness,
                  straightness, t.flexed_max_straightness, "<="),
    )
    ae, af, se, sf = (p.passed for p in predicates)
    if (ae and sf) or (af and se):
        return FingerObservation(finger.finger, FingerState.UNKNOWN, predicates,
                                 (Reason.CONFLICTING_FEATURES,))
    extended, flexed = ae and se, af and sf
    reason = Reason.BETWEEN_THRESHOLDS
    if finger.finger is Finger.THUMB:
        thumb = finger.thumb
        if thumb is None:
            return _unknown(finger, Reason.MISSING_FEATURES)
        if (not 0 <= thumb.axis_to_palm_rad <= math.pi
                or min(thumb.tip_to_index_mcp_palm, thumb.tip_to_pinky_mcp_palm) < 0):
            return _unknown(finger, Reason.INVALID_FEATURE_RANGE)
        distance = min(thumb.tip_to_index_mcp_palm, thumb.tip_to_pinky_mcp_palm)
        thumb_predicates = (
            Predicate("thumb_spread", distance >= thumb_thresholds.spread_min_distance_palm,
                      distance, thumb_thresholds.spread_min_distance_palm, ">="),
            Predicate("thumb_opposed", distance <= thumb_thresholds.opposition_max_distance_palm,
                      distance, thumb_thresholds.opposition_max_distance_palm, "<="),
            Predicate("thumb_extended_axis", thumb.axis_to_palm_rad <= thumb_thresholds.extended_max_axis_to_palm_rad,
                      thumb.axis_to_palm_rad, thumb_thresholds.extended_max_axis_to_palm_rad, "<="),
        )
        predicates += thumb_predicates
        extended = extended and thumb_predicates[0].passed and thumb_predicates[2].passed
        flexed = flexed and thumb_predicates[1].passed
        reason = Reason.THUMB_POSTURE_UNRESOLVED
    state = (FingerState.EXTENDED if extended else
             FingerState.FLEXED if flexed else FingerState.INTERMEDIATE)
    return FingerObservation(finger.finger, state, predicates,
                             (reason,) if state is FingerState.INTERMEDIATE else ())

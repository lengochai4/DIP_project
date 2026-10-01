"""Synthetic A3 cases, not physical validation or calibrated thresholds."""

from dataclasses import FrozenInstanceError, replace
import math

import pytest

from dip_touchless.core import (
    CoordinateSpace, FilterDiagnostics, FilterMode, Landmark,
    MeasurementQuality, StageTimings, TrackingFrame, TrackingStatus,
)
from extensions.stem3d.full_hand import (
    ClassificationReason as Reason, Finger, FingerState, FingerThresholds,
    FrameGeometry, GeometryReason, HandPose, PoseThresholds, ThumbThresholds,
    classify_pose, estimate_finger_state, evaluate_pinch_geometry,
    extract_hand_geometry,
)


def _thresholds():
    # Fixture parameters only. No production defaults or claim of optimality.
    chain = FingerThresholds(2.6, 1.5, .9, .65)
    return PoseThresholds(chain, ThumbThresholds(chain, .5, .65, 2.0), .2, .35)


def _hand(pose="OPEN", *, angle=0., mirror=False, width=1600, height=900):
    points = [
        (.50, .80),
        (.40, .68), (.32, .61), (.25, .53), (.20, .48),
        (.40, .55), (.40, .42), (.40, .31), (.40, .20),
        (.50, .50), (.50, .35), (.50, .23), (.50, .11),
        (.60, .54), (.61, .40), (.62, .29), (.63, .19),
        (.68, .61), (.71, .50), (.73, .41), (.75, .33),
    ]
    fold = {"POINT": (9, 13, 17), "FIST": (5, 9, 13, 17),
            "UNKNOWN": (13, 17)}.get(pose, ())
    for i in fold:
        x, y = points[i]
        points[i + 1:i + 4] = [(x, y - .10), (x + .08, y - .08),
                              (x + .015, y + .025)]
    if pose == "FIST":
        points[2:5] = [(.50, .56), (.56, .68), (.55, .64)]
    if pose == "PINCH":
        points[4] = points[8]
    if pose == "DEGENERATE":
        points[7] = points[6]
    geometry = FrameGeometry("synthetic-a3", 3, .1, width, height)
    landmarks = []
    for i, (x, y) in enumerate(points):
        x, y = x - .5, y - .5
        if mirror:
            x = -x
        px = x * math.cos(angle) - y * math.sin(angle)
        py = x * math.sin(angle) + y * math.cos(angle)
        landmarks.append(Landmark(i, .5 + px / (width / height), .5 + py,
                                  -.01 * i, CoordinateSpace.FRAME_NORMALIZED))
    frame = TrackingFrame(
        geometry.run_id, geometry.frame_id, geometry.timestamp_s,
        TrackingStatus.VALID, (), tuple(landmarks),
        MeasurementQuality.unavailable(), None, None,
        FilterDiagnostics(FilterMode.RAW, None, None, None, None, None,
                          None, None, False), StageTimings(0., 0., 0., 0., 0.), (),
    )
    return extract_hand_geometry(frame, geometry)


@pytest.mark.parametrize("pose", ["OPEN", "POINT", "PINCH", "FIST", "UNKNOWN"])
@pytest.mark.parametrize("angle", [0., .6, math.pi / 2, math.pi, -1.2])
@pytest.mark.parametrize("mirror", [False, True])
def test_end_to_end_landmark_pose_fixtures(pose, angle, mirror):
    hand = _hand(pose, angle=angle, mirror=mirror)
    assert hand.valid
    observation = classify_pose(hand, _thresholds())
    assert observation.pose is HandPose[pose]
    assert observation.frame_geometry == hand.frame_geometry
    assert tuple(f.finger for f in observation.fingers) == tuple(Finger)
    if pose == "UNKNOWN":
        assert observation.reasons == (Reason.NO_POSE_MATCH,)
    else:
        assert observation.reasons == ()


@pytest.mark.parametrize("dimensions", [(900, 900), (1920, 1080), (900, 1600)])
@pytest.mark.parametrize("pose", ["OPEN", "POINT", "PINCH", "FIST"])
def test_classification_preserves_aspect_corrected_a2_geometry(dimensions, pose):
    assert classify_pose(_hand(pose, width=dimensions[0], height=dimensions[1]),
                         _thresholds()).pose is HandPose[pose]


def test_finger_and_thumb_diagnostics_explain_open_fixture():
    observation = classify_pose(_hand(), _thresholds())
    assert all(f.state is FingerState.EXTENDED for f in observation.fingers)
    thumb = observation.fingers[0]
    assert {p.name for p in thumb.predicates} >= {
        "thumb_spread", "thumb_opposed", "thumb_extended_axis"}
    for finger in observation.fingers[1:]:
        assert len(finger.predicates) == 4
    for predicate in thumb.predicates:
        assert predicate.value is not None
        assert predicate.threshold is not None
        assert predicate.comparison is not None


def _estimate(finger, thresholds=None):
    t = thresholds or _thresholds()
    return estimate_finger_state(finger, t.fingers, t.thumb)


@pytest.mark.parametrize("angles,straightness,state", [
    ((2.6, 2.6), .9, FingerState.EXTENDED),
    ((1.5, 2.), .65, FingerState.FLEXED),
    ((2.59, 2.59), .89, FingerState.INTERMEDIATE),
    ((1.51, 2.), .66, FingerState.INTERMEDIATE),
    ((2.7, 2.7), .60, FingerState.UNKNOWN),
    ((1.4, 2.), .95, FingerState.UNKNOWN),
])
def test_finger_threshold_equalities_gaps_and_conflicts(angles, straightness, state):
    finger = replace(_hand().fingers[1], joint_angles_rad=angles,
                     straightness=straightness)
    result = _estimate(finger)
    assert result.state is state
    if state is FingerState.UNKNOWN:
        assert result.reasons == (Reason.CONFLICTING_FEATURES,)
    elif state is FingerState.INTERMEDIATE:
        assert result.reasons == (Reason.BETWEEN_THRESHOLDS,)


@pytest.mark.parametrize("distance,axis,state", [
    (.65, 2., FingerState.EXTENDED),
    (.649, 2., FingerState.INTERMEDIATE),
    (.65, 2.001, FingerState.INTERMEDIATE),
    (.5, 1., FingerState.INTERMEDIATE),
])
def test_extended_thumb_requires_spread_and_palm_axis(distance, axis, state):
    finger = _hand().fingers[0]
    thumb = replace(finger.thumb, tip_to_index_mcp_palm=distance,
                    tip_to_pinky_mcp_palm=2., axis_to_palm_rad=axis)
    finger = replace(finger, thumb=thumb)
    assert _estimate(finger).state is state


@pytest.mark.parametrize("distance,state", [(.5, FingerState.FLEXED),
                                          (.501, FingerState.INTERMEDIATE)])
def test_flexed_thumb_requires_opposition(distance, state):
    finger = _hand("FIST").fingers[0]
    finger = replace(finger, thumb=replace(finger.thumb,
                     tip_to_index_mcp_palm=distance, tip_to_pinky_mcp_palm=2.))
    assert _estimate(finger).state is state


@pytest.mark.parametrize("change,reason", [
    (dict(thumb=None), Reason.MISSING_FEATURES),
    (dict(joint_angles_rad=None), Reason.MISSING_FEATURES),
    (dict(straightness=None), Reason.MISSING_FEATURES),
    (dict(joint_angles_rad=(-.1, 2.)), Reason.INVALID_FEATURE_RANGE),
    (dict(straightness=1.1), Reason.INVALID_FEATURE_RANGE),
])
def test_missing_or_invalid_finger_features_are_unknown(change, reason):
    result = _estimate(replace(_hand().fingers[0], **change))
    assert result.state is FingerState.UNKNOWN and result.reasons == (reason,)


@pytest.mark.parametrize("distance,enter,exit_,band", [
    (.199, True, False, False), (.2, False, False, True),
    (.27, False, False, True), (.35, False, False, True),
    (.351, False, True, False),
])
def test_pinch_strict_enter_exit_and_equality_band(distance, enter, exit_, band):
    pinch = evaluate_pinch_geometry(distance, _thresholds())
    assert (pinch.enter, pinch.exit, pinch.boundary_band) == (enter, exit_, band)
    result = classify_pose(replace(_hand(), thumb_index_distance_palm=distance), _thresholds())
    assert result.pose is (HandPose.PINCH if enter else HandPose.UNKNOWN if band else HandPose.OPEN)
    if band:
        assert result.reasons == (Reason.PINCH_BOUNDARY_BAND,)


@pytest.mark.parametrize("distance", [None, -1., math.inf, math.nan])
def test_unavailable_pinch_geometry_never_fakes_distance(distance):
    result = evaluate_pinch_geometry(distance, _thresholds())
    assert result.distance_palm is None
    assert result.enter is None and result.exit is None and result.boundary_band is None
    assert all(p.passed is None for p in result.predicates)


@pytest.mark.parametrize("distance,reason", [(None, Reason.MISSING_FEATURES),
                                           (-.1, Reason.INVALID_FEATURE_RANGE)])
def test_missing_or_negative_pinch_feature_has_explicit_reason(distance, reason):
    result = classify_pose(replace(_hand(), thumb_index_distance_palm=distance),
                           _thresholds())
    assert result.pose is HandPose.UNKNOWN and result.reasons == (reason,)


def test_pinch_band_does_not_latch_after_enter():
    thresholds = _thresholds()
    hand = _hand("POINT")
    assert classify_pose(replace(hand, thumb_index_distance_palm=.1), thresholds).pose is HandPose.PINCH
    band = replace(hand, thumb_index_distance_palm=.3)
    assert classify_pose(band, thresholds).pose is HandPose.UNKNOWN
    classify_pose(_hand("OPEN"), thresholds)
    assert classify_pose(band, thresholds).pose is HandPose.UNKNOWN


@pytest.mark.parametrize("thumb_change", [dict(axis_to_palm_rad=-.1),
    dict(tip_to_index_mcp_palm=-.1), dict(axis_to_palm_rad=4.)])
def test_invalid_thumb_geometry_ranges_are_unknown(thumb_change):
    finger = _hand().fingers[0]
    result = _estimate(replace(finger, thumb=replace(finger.thumb, **thumb_change)))
    assert result.state is FingerState.UNKNOWN
    assert result.reasons == (Reason.INVALID_FEATURE_RANGE,)


def test_thumb_chain_thresholds_are_independent_of_other_fingers():
    thresholds = _thresholds()
    thumb_chain = replace(thresholds.thumb.chain, extended_min_angle_rad=3.1)
    thresholds = replace(thresholds, thumb=replace(thresholds.thumb, chain=thumb_chain))
    result = classify_pose(_hand(), thresholds)
    assert result.fingers[0].state is FingerState.INTERMEDIATE
    assert all(f.state is FingerState.EXTENDED for f in result.fingers[1:])
    assert result.pose is HandPose.UNKNOWN


@pytest.mark.parametrize("pose,predicate", [("POINT", "pose_point"), ("FIST", "pose_fist")])
def test_pinch_precedes_overlapping_point_and_fist_predicates(pose, predicate):
    # Isolated feature fixture to exercise overlap resolution, not a camera run.
    hand = replace(_hand(pose), thumb_index_distance_palm=.1)
    result = classify_pose(hand, _thresholds())
    assert result.pose is HandPose.PINCH
    assert next(p.passed for p in result.predicates if p.name == predicate)


def test_point_allows_intermediate_thumb_but_fist_does_not():
    for pose in ("POINT", "FIST"):
        hand = _hand(pose)
        finger = replace(hand.fingers[0], joint_angles_rad=(2., 2.), straightness=.8)
        hand = replace(hand, fingers=(finger, *hand.fingers[1:]))
        result = classify_pose(hand, _thresholds())
        assert result.fingers[0].state is FingerState.INTERMEDIATE
        assert result.pose is (HandPose.POINT if pose == "POINT" else HandPose.UNKNOWN)


def test_conflicting_finger_geometry_blocks_even_pinch():
    hand = _hand("PINCH")
    finger = replace(hand.fingers[1], joint_angles_rad=(1., 1.), straightness=.95)
    result = classify_pose(replace(hand, fingers=(hand.fingers[0], finger, *hand.fingers[2:])),
                           _thresholds())
    assert result.pinch.enter
    assert result.pose is HandPose.UNKNOWN and result.reasons == (Reason.FINGER_UNKNOWN,)
    assert result.fingers[1].reasons == (Reason.CONFLICTING_FEATURES,)


def test_degenerate_geometry_propagates_reasons_and_unknown():
    hand = _hand("DEGENERATE")
    result = classify_pose(hand, _thresholds())
    assert result.pose is HandPose.UNKNOWN
    assert result.geometry_reasons == (GeometryReason.DEGENERATE_FINGER,)
    assert result.fingers[1].state is FingerState.UNKNOWN
    assert result.fingers[1].geometry_reasons == hand.fingers[1].reasons
    assert result.pinch.distance_palm is None


@pytest.mark.parametrize("change", ["empty", "duplicate", "no_palm"])
def test_incomplete_or_duplicate_geometry_cannot_classify(change):
    hand = _hand()
    if change == "empty":
        hand = replace(hand, fingers=())
    elif change == "duplicate":
        hand = replace(hand, fingers=(hand.fingers[0], *hand.fingers[:-1]))
    else:
        hand = replace(hand, palm=None)
    result = classify_pose(hand, _thresholds())
    assert result.pose is HandPose.UNKNOWN
    assert result.reasons == (Reason.INVALID_GEOMETRY,)
    assert result.pinch.enter is None


def test_classification_is_stateless_and_immutable():
    hand, thresholds = _hand(), _thresholds()
    before = repr(hand), repr(thresholds)
    expected = classify_pose(hand, thresholds)
    for pose in ("PINCH", "FIST", "DEGENERATE", "UNKNOWN", "POINT"):
        classify_pose(_hand(pose), thresholds)
    assert classify_pose(hand, thresholds) == expected
    assert (repr(hand), repr(thresholds)) == before
    for obj, field, value in [(expected, "pose", HandPose.UNKNOWN),
                              (expected.fingers[0], "state", FingerState.UNKNOWN),
                              (expected.predicates[0], "passed", False),
                              (expected.pinch, "enter", True),
                              (thresholds, "pinch_enter_distance_palm", .1)]:
        with pytest.raises(FrozenInstanceError):
            setattr(obj, field, value)
    with pytest.raises(TypeError):
        replace(expected, fingers=list(expected.fingers))


@pytest.mark.parametrize("change", [dict(extended_min_angle_rad=math.inf),
    dict(extended_min_angle_rad=1.), dict(flexed_max_angle_rad=-1.),
    dict(extended_min_straightness=.5), dict(flexed_max_straightness=-.1),
    dict(extended_min_angle_rad=4.), dict(extended_min_straightness=1.1)])
def test_invalid_finger_thresholds_rejected(change):
    with pytest.raises(ValueError):
        replace(_thresholds().fingers, **change)


@pytest.mark.parametrize("change", [dict(opposition_max_distance_palm=.65),
    dict(spread_min_distance_palm=.4), dict(extended_max_axis_to_palm_rad=4.),
    dict(opposition_max_distance_palm=-.1)])
def test_invalid_thumb_thresholds_rejected(change):
    with pytest.raises(ValueError):
        replace(_thresholds().thumb, **change)


@pytest.mark.parametrize("change", [dict(pinch_enter_distance_palm=.35),
    dict(pinch_exit_distance_palm=.1), dict(pinch_enter_distance_palm=-.1),
    dict(pinch_exit_distance_palm=math.nan)])
def test_invalid_pinch_thresholds_rejected(change):
    with pytest.raises(ValueError):
        replace(_thresholds(), **change)

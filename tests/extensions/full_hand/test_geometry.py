"""Deterministic synthetic geometry only; no webcam/pose-validation claims."""

from dataclasses import FrozenInstanceError, replace
import math

import pytest

from dip_touchless.core import (
    CoordinateSpace, FilterDiagnostics, FilterMode, Landmark,
    MeasurementQuality, StageTimings, TrackingFrame, TrackingStatus,
)
from extensions.stem3d.full_hand import (
    Finger, FrameGeometry, GeometryReason, extract_hand_geometry,
)


# Isotropic image-height coordinates, wrist followed by five anatomical chains.
_POINTS = (
    (.50, .80),
    (.40, .68), (.32, .61), (.25, .53), (.20, .48),
    (.40, .55), (.40, .42), (.40, .31), (.40, .20),
    (.50, .50), (.50, .35), (.50, .23), (.50, .11),
    (.60, .54), (.61, .40), (.62, .29), (.63, .19),
    (.68, .61), (.71, .50), (.73, .41), (.75, .33),
)


def _fixture(width=1600, height=900, transform=lambda x, y: (x, y)):
    geometry = FrameGeometry("synthetic-a2", 7, .25, width, height)
    landmarks = []
    for i, (x, y) in enumerate(_POINTS):
        x, y = transform(x, y)
        landmarks.append(Landmark(
            i, .5 + (x - .5) / (width / height), y, -.01 * i,
            CoordinateSpace.FRAME_NORMALIZED,
        ))
    frame = TrackingFrame(
        geometry.run_id, geometry.frame_id, geometry.timestamp_s,
        TrackingStatus.VALID, (), tuple(landmarks),
        MeasurementQuality.unavailable(), None, None,
        FilterDiagnostics(FilterMode.RAW, None, None, None, None, None,
                          None, None, False),
        StageTimings(0., 0., 0., 0., 0.), (),
    )
    return frame, geometry


def _assert_same_shape(a, b):
    assert a.valid and b.valid
    assert a.thumb_index_distance_palm == pytest.approx(b.thumb_index_distance_palm)
    for first, second in zip(a.fingers, b.fingers):
        assert first.finger == second.finger
        assert first.landmark_indices == second.landmark_indices
        assert first.joint_angles_rad == pytest.approx(second.joint_angles_rad)
        assert first.segment_lengths_palm == pytest.approx(second.segment_lengths_palm)
        assert first.straightness == pytest.approx(second.straightness)
        assert first.tip_to_wrist_palm == pytest.approx(second.tip_to_wrist_palm)
        assert first.tip_in_palm == pytest.approx(second.tip_in_palm)
        if first.thumb:
            assert first.thumb.axis_to_palm_rad == pytest.approx(second.thumb.axis_to_palm_rad)
            assert first.thumb.tip_to_index_mcp_palm == pytest.approx(second.thumb.tip_to_index_mcp_palm)
            assert first.thumb.tip_to_pinky_mcp_palm == pytest.approx(second.thumb.tip_to_pinky_mcp_palm)


def test_valid_hand_has_five_anatomical_chains_and_known_geometry():
    frame, geometry = _fixture()
    hand = extract_hand_geometry(frame, geometry)
    assert hand.valid and hand.reasons == ()
    assert tuple(f.finger for f in hand.fingers) == tuple(Finger)
    assert hand.palm.width_image_height == pytest.approx(math.hypot(.28, .06))
    index = hand.fingers[1]
    assert index.joint_angles_rad == pytest.approx((math.pi, math.pi))
    assert index.straightness == pytest.approx(1.)
    assert index.segment_lengths_palm == pytest.approx(
        tuple(n / math.hypot(.28, .06) for n in (.13, .11, .11)))
    assert hand.thumb_index_distance_palm == pytest.approx(
        math.hypot(.20, .28) / math.hypot(.28, .06))
    assert hand.fingers[0].thumb is not None
    assert all(f.thumb is None for f in hand.fingers[1:])


@pytest.mark.parametrize("dimensions", [(900, 900), (1920, 1080), (640, 480), (900, 1600)])
def test_aspect_ratio_corrects_the_same_isotropic_hand(dimensions):
    baseline = extract_hand_geometry(*_fixture())
    other = extract_hand_geometry(*_fixture(*dimensions))
    _assert_same_shape(baseline, other)
    assert baseline.palm.width_image_height == pytest.approx(other.palm.width_image_height)


@pytest.mark.parametrize("angle", [0., .7, math.pi / 2, math.pi, -1.2])
@pytest.mark.parametrize("scale", [.25, 1., 1.8])
def test_translation_scale_rotation_invariants(angle, scale):
    def transform(x, y):
        x, y = x - .5, y - .5
        return (.57 + scale * (x * math.cos(angle) - y * math.sin(angle)),
                .44 + scale * (x * math.sin(angle) + y * math.cos(angle)))
    a = extract_hand_geometry(*_fixture())
    b = extract_hand_geometry(*_fixture(transform=transform))
    _assert_same_shape(a, b)
    assert b.palm.width_image_height == pytest.approx(a.palm.width_image_height * scale)


@pytest.mark.parametrize("transform", [lambda x, y: (1 - x, y), lambda x, y: (x, 1 - y)])
def test_mirrored_hand_uses_anatomical_axes_without_handedness(transform):
    _assert_same_shape(extract_hand_geometry(*_fixture()),
                       extract_hand_geometry(*_fixture(transform=transform)))


def test_aspect_correction_is_not_independent_normalized_xy_distance():
    frame, geometry = _fixture()
    a, b = frame.filtered_landmarks[5], frame.filtered_landmarks[17]
    uncorrected = math.hypot(a.x - b.x, a.y - b.y)
    assert extract_hand_geometry(frame, geometry).palm.width_image_height != pytest.approx(uncorrected)


@pytest.mark.parametrize("status", [TrackingStatus.NO_HAND, TrackingStatus.TEMPORARY_LOSS, TrackingStatus.INVALID])
def test_unusable_tracking_never_reuses_present_landmarks(status):
    frame, geometry = _fixture()
    result = extract_hand_geometry(replace(frame, status=status), geometry)
    assert result.reasons == (GeometryReason.TRACKING_UNUSABLE,)
    assert not result.valid and result.palm is None and result.fingers == ()


def test_reacquired_geometry_does_not_claim_interaction_validity():
    frame, geometry = _fixture()
    assert extract_hand_geometry(replace(frame, status=TrackingStatus.REACQUIRED), geometry).valid


@pytest.mark.parametrize("change", [dict(run_id="other"), dict(frame_id=8), dict(timestamp_s=.26)])
def test_geometry_identity_must_match_frame(change):
    frame, geometry = _fixture()
    assert extract_hand_geometry(frame, replace(geometry, **change)).reasons == (GeometryReason.IDENTITY_MISMATCH,)


@pytest.mark.parametrize("change", [dict(run_id=""), dict(frame_id=-1), dict(timestamp_s=math.nan)])
def test_invalid_tracking_identity_is_explicit(change):
    frame, geometry = _fixture()
    assert extract_hand_geometry(replace(frame, **change), geometry).reasons == (GeometryReason.INVALID_FRAME_IDENTITY,)


@pytest.mark.parametrize("change", [dict(width=0), dict(height=-1), dict(width=1.5), dict(height=True), dict(timestamp_s=math.inf), dict(run_id=""), dict(frame_id=True)])
def test_invalid_frame_geometry_rejected_at_construction(change):
    _, geometry = _fixture()
    with pytest.raises(ValueError):
        replace(geometry, **change)


@pytest.mark.parametrize("count", [0, 20, 22])
def test_missing_or_extra_landmarks(count):
    frame, geometry = _fixture()
    landmarks = frame.filtered_landmarks[:count]
    if count == 22:
        landmarks += (landmarks[0],)
    result = extract_hand_geometry(replace(frame, filtered_landmarks=landmarks), geometry)
    assert result.reasons == (GeometryReason.LANDMARK_COUNT,)
    assert result.thumb_index_distance_palm is None


@pytest.mark.parametrize("index", [0, 21, 1.5, True])
def test_duplicate_out_of_range_or_invalid_indices(index):
    frame, geometry = _fixture()
    landmarks = list(frame.filtered_landmarks)
    landmarks[1] = replace(landmarks[1], index=index)
    result = extract_hand_geometry(replace(frame, filtered_landmarks=tuple(landmarks)), geometry)
    assert result.reasons == (GeometryReason.LANDMARK_INDICES,)


def test_unordered_indices_are_deterministic():
    frame, geometry = _fixture()
    assert extract_hand_geometry(frame, geometry) == extract_hand_geometry(
        replace(frame, filtered_landmarks=tuple(reversed(frame.filtered_landmarks))), geometry)


@pytest.mark.parametrize("space", [CoordinateSpace.FRAME_PIXEL, CoordinateSpace.MODEL_RELATIVE_Z, "FRAME_NORMALIZED"])
def test_invalid_coordinate_space(space):
    frame, geometry = _fixture()
    landmarks = list(frame.filtered_landmarks)
    landmarks[4] = replace(landmarks[4], coordinate_space=space)
    result = extract_hand_geometry(replace(frame, filtered_landmarks=tuple(landmarks)), geometry)
    assert result.reasons == (GeometryReason.COORDINATE_SPACE,)


@pytest.mark.parametrize("component", ["x", "y", "z"])
@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_nonfinite_defensive_boundary(component, value):
    frame, geometry = _fixture()
    # Public Landmark constructor normally rejects these. Corrupt a NEW fixture
    # object to exercise defensive extraction of malformed external input.
    bad = replace(frame.filtered_landmarks[4])
    object.__setattr__(bad, component, value)
    landmarks = (*frame.filtered_landmarks[:4], bad, *frame.filtered_landmarks[5:])
    result = extract_hand_geometry(replace(frame, filtered_landmarks=landmarks), geometry)
    assert result.reasons == (GeometryReason.NON_FINITE_COORDINATE,)


def test_finite_out_of_frame_coordinates_are_not_clamped():
    frame, geometry = _fixture(transform=lambda x, y: (x + 3, y - 2))
    result = extract_hand_geometry(frame, geometry)
    _assert_same_shape(extract_hand_geometry(*_fixture()), result)
    assert result.palm.anchor_xy[0] > 1 and result.palm.anchor_xy[1] < 0


@pytest.mark.parametrize("kind", ["collapsed", "zero_width", "collinear"])
def test_degenerate_palm_has_no_fabricated_geometry(kind):
    frame, geometry = _fixture()
    points = list(frame.filtered_landmarks)
    if kind == "collapsed":
        points = [replace(p, x=.5, y=.5) for p in points]
    elif kind == "zero_width":
        points[17] = replace(points[17], x=points[5].x, y=points[5].y)
    else:
        for i in (0, 5, 9, 13, 17):
            points[i] = replace(points[i], y=.5)
    result = extract_hand_geometry(replace(frame, filtered_landmarks=tuple(points)), geometry)
    assert result.reasons == (GeometryReason.DEGENERATE_PALM,)
    assert result.palm is None and result.fingers == ()


@pytest.mark.parametrize("finger,base,next_index", [(0, 1, 2), (1, 5, 6), (4, 17, 18)])
def test_degenerate_finger_retains_only_other_usable_geometry(finger, base, next_index):
    frame, geometry = _fixture()
    points = list(frame.filtered_landmarks)
    points[next_index] = replace(points[next_index], x=points[base].x, y=points[base].y)
    result = extract_hand_geometry(replace(frame, filtered_landmarks=tuple(points)), geometry)
    assert not result.valid and result.palm is not None
    assert result.reasons == (GeometryReason.DEGENERATE_FINGER,)
    assert not result.fingers[finger].valid
    assert result.fingers[finger].joint_angles_rad is None
    assert all(f.valid for i, f in enumerate(result.fingers) if i != finger)


def test_thumb_opposition_distances_change_without_classifying_pose():
    frame, geometry = _fixture()
    before = extract_hand_geometry(frame, geometry)
    points = list(frame.filtered_landmarks)
    points[4] = replace(points[4], x=points[8].x, y=points[8].y)
    after = extract_hand_geometry(replace(frame, filtered_landmarks=tuple(points)), geometry)
    assert after.valid and after.thumb_index_distance_palm == 0
    assert after.fingers[0].thumb != before.fingers[0].thumb
    assert after.fingers[1:] == before.fingers[1:]


def test_bent_finger_has_smaller_angles_and_straightness():
    frame, geometry = _fixture()
    points = list(frame.filtered_landmarks)
    points[7] = replace(points[7], x=points[6].x + .04, y=.46)
    points[8] = replace(points[8], x=points[6].x + .01, y=.54)
    hand = extract_hand_geometry(replace(frame, filtered_landmarks=tuple(points)), geometry)
    assert hand.valid
    assert all(a < math.pi for a in hand.fingers[1].joint_angles_rad)
    assert hand.fingers[1].straightness < 1


def test_only_filtered_xy_influences_geometry():
    frame, geometry = _fixture()
    before = extract_hand_geometry(frame, geometry)
    changed = replace(frame, raw_landmarks=tuple(reversed(frame.filtered_landmarks)),
                      filtered_landmarks=tuple(replace(p, z=1e100) for p in frame.filtered_landmarks))
    assert extract_hand_geometry(changed, geometry) == before


def test_extreme_finite_input_has_explicit_numerical_failure():
    frame, geometry = _fixture()
    points = tuple(replace(p, x=1e308 if p.index % 2 else -1e308)
                   for p in frame.filtered_landmarks)
    assert extract_hand_geometry(replace(frame, filtered_landmarks=points), geometry).reasons == (GeometryReason.NUMERICAL_FAILURE,)


def test_inputs_and_nested_outputs_are_immutable_and_repeatable():
    frame, geometry = _fixture()
    before = repr(frame), repr(geometry)
    hand = extract_hand_geometry(frame, geometry)
    assert extract_hand_geometry(frame, geometry) == hand
    assert (repr(frame), repr(geometry)) == before
    for obj, field, value in [(geometry, "width", 5), (hand, "valid", False),
                              (hand.palm, "anchor_xy", (0., 0.)),
                              (hand.fingers[0], "valid", False),
                              (hand.fingers[0].thumb, "axis_to_palm_rad", 0.)]:
        with pytest.raises(FrozenInstanceError):
            setattr(obj, field, value)
    with pytest.raises(TypeError):
        hand.fingers[0].joint_angles_rad[0] = 0.


@pytest.mark.parametrize("target,field", [
    ("hand", "fingers"), ("hand", "reasons"), ("palm", "anchor_xy"),
    ("palm", "lateral_axis"), ("finger", "landmark_indices"),
    ("finger", "joint_angles_rad"), ("finger", "segment_lengths_palm"),
    ("finger", "tip_in_palm"), ("finger", "reasons"),
])
def test_contracts_reject_mutable_collections(target, field):
    hand = extract_hand_geometry(*_fixture())
    obj = {"hand": hand, "palm": hand.palm, "finger": hand.fingers[0]}[target]
    with pytest.raises(ValueError):
        replace(obj, **{field: list(getattr(obj, field))})


def test_loss_with_empty_landmarks_has_no_zero_geometry():
    frame, geometry = _fixture()
    hand = extract_hand_geometry(replace(frame, status=TrackingStatus.NO_HAND,
                                        filtered_landmarks=()), geometry)
    assert not hand.valid and hand.palm is None and hand.fingers == ()
    assert hand.thumb_index_distance_palm is None


def test_small_hand_is_not_rejected_by_an_absolute_size_threshold():
    _assert_same_shape(extract_hand_geometry(*_fixture()),
                       extract_hand_geometry(*_fixture(
                           transform=lambda x, y: (.5 + 1e-7 * (x - .5),
                                                   .5 + 1e-7 * (y - .5)))))


def test_filter_reset_metadata_does_not_create_geometry_state():
    frame, geometry = _fixture()
    assert extract_hand_geometry(frame, geometry) == extract_hand_geometry(
        replace(frame, filter_diagnostics=replace(frame.filter_diagnostics,
                                                  reset_occurred=True)), geometry)

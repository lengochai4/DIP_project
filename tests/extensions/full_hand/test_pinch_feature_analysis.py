"""Recorded geometry regression, not a physical accuracy benchmark."""

from collections import Counter
from dataclasses import FrozenInstanceError, replace
import json
import math
from pathlib import Path

import pytest

from dip_touchless.core import CoordinateSpace, Landmark, TrackingStatus
from extensions.stem3d.full_hand import FrameGeometry, HandPose, TemporalPoseTracker, classify_pose, extract_hand_geometry
from extensions.stem3d.full_hand.observe import load_observe_profile
from extensions.stem3d.full_hand.pinch_feature_analysis import extract_pinch_features
from test_geometry import _fixture


FIXTURE = json.loads((Path(__file__).parent / "fixtures/pinch_feature_recordings.json").read_text())
SAMPLES = FIXTURE["samples"]


def _recorded(sample):
    frame, _ = _fixture()
    geometry = FrameGeometry(sample["run_id"], sample["frame_id"], sample["timestamp_s"],
                             sample["width"], sample["height"])
    landmarks = tuple(Landmark(p["index"], p["x"], p["y"], p["z"],
                              CoordinateSpace.FRAME_NORMALIZED) for p in sample["landmarks"])
    return replace(frame, run_id=geometry.run_id, frame_id=geometry.frame_id,
                   timestamp_s=geometry.timestamp_s, filtered_landmarks=landmarks), geometry


def _values(observation):
    return {f.name: f.value for f in observation.features}


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda s: f'{s["run_id"]}-{s["frame_id"]}')
def test_recorded_geometry_reproduces_source_and_is_read_only(sample):
    frame, geometry = _recorded(sample)
    before = frame.filtered_landmarks
    result = extract_pinch_features(frame, geometry)
    assert result.geometry_valid and not result.geometry_reasons
    assert result.frame_geometry == geometry
    values = _values(result)
    assert values["distance_palm"] == pytest.approx(sample["expected_distance"], abs=1e-12)
    assert math.hypot(values["gap_lateral_palm"], values["gap_distal_palm"]) == pytest.approx(values["distance_palm"])
    assert all(f.reason is None and math.isfinite(f.value) for f in result.features)
    assert frame.filtered_landmarks is before
    assert result == extract_pinch_features(frame, geometry)
    with pytest.raises(FrozenInstanceError):
        result.features[0].value = 0.


def test_fixture_provenance_and_contaminated_marker_exclusion():
    assert len(SAMPLES) == 73
    assert Counter(s["label"] for s in SAMPLES) == {
        "PINCH_TOUCH": 41, "PINCH_NEAR_NO_TOUCH": 8,
        "PINCH_MEDIUM_SEPARATION": 6, "PINCH_RELEASE": 18}
    assert Counter(s["label_basis"] for s in SAMPLES) == {
        "synchronized_image_and_operator_confirmation": 42,
        "supplemental_operator_label": 4, "operator_interval_no_image": 27}
    assert len({(s["run_id"], s["frame_id"]) for s in SAMPLES}) == 73
    assert not any(s["run_id"].endswith("095623") and s["marker_id"] == 1 for s in SAMPLES)
    assert all(len(s["source_sha256"]) == 64 and len(s["landmarks"]) == 21 for s in SAMPLES)
    assert len(FIXTURE["runs"]) == 6


def test_scalar_baseline_misses_contacts_and_rejected_candidate_accepts_clean_negatives():
    baseline = load_observe_profile(Path("config/extensions/full_hand_observe.yaml"))
    candidate = load_observe_profile(Path("config/extensions/full_hand_pinch_candidate.yaml"))
    for label, baseline_count, candidate_count in [
        ("PINCH_TOUCH", 0, 14), ("PINCH_NEAR_NO_TOUCH", 0, 4),
        ("PINCH_MEDIUM_SEPARATION", 0, 0), ("PINCH_RELEASE", 0, 0),
    ]:
        observations = [extract_hand_geometry(*_recorded(s)) for s in SAMPLES
                        if s["label"] == label and s["label_basis"] == "synchronized_image_and_operator_confirmation"]
        assert sum(classify_pose(h, baseline.pose).pose is HandPose.PINCH for h in observations) == baseline_count
        assert sum(classify_pose(h, candidate.pose).pose is HandPose.PINCH for h in observations) == candidate_count


def test_promising_index_bend_separator_is_not_supported_across_p1d_contacts():
    # .85 is a rejected offline hypothesis, never a configuration or predicate.
    features = [(s, _values(extract_pinch_features(*_recorded(s)))) for s in SAMPLES]
    contact = [v for s, v in features if s["label"] == "PINCH_TOUCH" and s["label_basis"] == "synchronized_image_and_operator_confirmation"]
    near = [v for s, v in features if s["run_id"].endswith("100358") and s["label"] == "PINCH_NEAR_NO_TOUCH"]
    assert max(v["index_straightness"] for v in contact) < .85
    assert min(v["index_straightness"] for v in near) > .85
    historical = [v for s, v in features if s["label_basis"] == "operator_interval_no_image" and v["distance_palm"] < .33]
    assert max(v["index_straightness"] for v in historical) > min(v["index_straightness"] for v in near)
    # Neither distal direction nor opposition has a disjoint positive/negative range.
    for feature in ("distal_segment_cosine", "thumb_axis_to_palm_rad", "thumb_to_index_mcp_palm",
                    "index_toward_thumb_cosine", "gap_distal_palm"):
        assert max(v[feature] for v in contact) >= min(v[feature] for v in near)
        assert max(v[feature] for v in near) >= min(v[feature] for v in contact)


@pytest.mark.parametrize("transform", ["mirror", "rotate", "translate", "scale", "z_only"])
def test_recorded_features_invariant_to_xy_similarities_and_ignore_z(transform):
    frame, geometry = _recorded(SAMPLES[0])
    aspect = geometry.width / geometry.height
    def change(p):
        x, y, z = p.x * aspect, p.y, p.z
        if transform == "mirror": x = -x
        elif transform == "rotate": x, y = x*math.cos(.7)-y*math.sin(.7), x*math.sin(.7)+y*math.cos(.7)
        elif transform == "translate": x, y = x + .3, y - .2
        elif transform == "scale": x, y = x * 1.7, y * 1.7
        elif transform == "z_only": z = 1000. + p.index
        return replace(p, x=x/aspect, y=y, z=z)
    before = _values(extract_pinch_features(frame, geometry))
    after = _values(extract_pinch_features(replace(frame, filtered_landmarks=tuple(map(change, frame.filtered_landmarks))), geometry))
    width = before.pop("palm_width_image_height")
    assert after.pop("palm_width_image_height") == pytest.approx(width * (1.7 if transform == "scale" else 1.))
    assert before == pytest.approx(after)


@pytest.mark.parametrize("case", ["loss", "missing", "duplicate", "nonfinite", "degenerate", "identity"])
def test_invalid_inputs_expose_reasons_without_plausible_features(case):
    frame, geometry = _fixture()
    landmarks = list(frame.filtered_landmarks)
    if case == "loss": frame = replace(frame, status=TrackingStatus.NO_HAND)
    elif case == "missing": landmarks.pop()
    elif case == "duplicate": landmarks[-1] = landmarks[0]
    elif case == "nonfinite":
        landmarks[4] = replace(landmarks[4])
        object.__setattr__(landmarks[4], "x", float("nan"))  # Defensive foreign input.
    elif case == "degenerate": landmarks[4] = replace(landmarks[3], index=4)
    elif case == "identity": geometry = replace(geometry, frame_id=geometry.frame_id+1)
    frame = replace(frame, filtered_landmarks=tuple(landmarks))
    result = extract_pinch_features(frame, geometry)
    assert not result.geometry_valid and result.geometry_reasons and not result.features


def test_coincident_tips_have_explicitly_unavailable_gap_direction():
    frame, geometry = _fixture()
    landmarks = list(frame.filtered_landmarks)
    landmarks[8] = replace(landmarks[4], index=8)
    result = extract_pinch_features(replace(frame, filtered_landmarks=tuple(landmarks)), geometry)
    assert result.geometry_valid
    assert _values(result)["distance_palm"] == 0.
    unavailable = [f for f in result.features if f.value is None]
    assert {f.name for f in unavailable} == {"thumb_toward_index_cosine", "index_toward_thumb_cosine"}
    assert all(f.reason == "DIRECTION_UNAVAILABLE" for f in unavailable)


@pytest.mark.parametrize("width,height", [(1600, 900), (1920, 1080), (480, 640)])
def test_actual_frame_aspect_is_used_for_segment_directions(width, height):
    frame, geometry = _recorded(SAMPLES[0])
    other_geometry = replace(geometry, width=width, height=height)
    factor = (geometry.width / geometry.height) / (width / height)
    other = replace(frame, filtered_landmarks=tuple(replace(p, x=p.x*factor) for p in frame.filtered_landmarks))
    assert _values(extract_pinch_features(frame, geometry)) == pytest.approx(_values(extract_pinch_features(other, other_geometry)))


@pytest.mark.parametrize("profile_name", ["full_hand_observe.yaml", "full_hand_pinch_candidate.yaml"])
def test_offline_analysis_preserves_pose_and_temporal_replay_exactly(profile_name):
    profile = load_observe_profile(Path("config/extensions") / profile_name)
    before_tracker = TemporalPoseTracker(profile.temporal)
    after_tracker = TemporalPoseTracker(profile.temporal)
    for sample in sorted(SAMPLES, key=lambda s: (s["run_id"], s["timestamp_s"])):
        frame, geometry = _recorded(sample)
        pose = classify_pose(extract_hand_geometry(frame, geometry), profile.pose)
        expected = before_tracker.update(pose, tracking_status=frame.status)
        extract_pinch_features(frame, geometry)
        after_pose = classify_pose(extract_hand_geometry(frame, geometry), profile.pose)
        assert after_pose == pose
        assert after_tracker.update(after_pose, tracking_status=frame.status) == expected

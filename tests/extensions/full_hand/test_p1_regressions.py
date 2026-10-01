"""Recorded P1 excerpts; transformed variants are regression inputs, not evidence."""

import json
import math
from dataclasses import replace
from pathlib import Path

import pytest

from dip_touchless.core import (
    CoordinateSpace, FilterDiagnostics, FilterMode, Landmark, MeasurementQuality,
    StageTimings, TrackingFrame, TrackingStatus,
)
from extensions.stem3d.full_hand import (
    ClassificationReason, Finger, FingerObservation, FingerState, FrameGeometry,
    HandPose, PoseObservation, TemporalPoseTracker, classify_pose,
    evaluate_pinch_geometry, extract_hand_geometry,
)
from extensions.stem3d.full_hand.observe import load_observe_profile


DATA = json.loads((Path(__file__).parent / "fixtures/p1_regressions.json").read_text())
PROFILE = load_observe_profile(Path("config/extensions/full_hand_observe.yaml"))


def _geometry(sample, angle=0., mirror=False):
    g = FrameGeometry(sample["run_id"], sample["frame_id"], sample["timestamp_s"],
                      sample["width"], sample["height"])
    aspect = g.width / g.height
    landmarks = []
    for i, x, y, z in sample["landmarks"]:
        x, y = (x - .5) * aspect, y - .5
        if mirror:
            x = -x
        rx = x * math.cos(angle) - y * math.sin(angle)
        ry = x * math.sin(angle) + y * math.cos(angle)
        landmarks.append(Landmark(i, .5 + rx / aspect, .5 + ry, z,
                                  CoordinateSpace.FRAME_NORMALIZED))
    frame = TrackingFrame(g.run_id, g.frame_id, g.timestamp_s, TrackingStatus.VALID,
        (), tuple(landmarks), MeasurementQuality.unavailable(), None, None,
        FilterDiagnostics(FilterMode.RAW, None, None, None, None, None, None, None, False),
        StageTimings(0., 0., 0., 0., 0.), ())
    return extract_hand_geometry(frame, g)


@pytest.mark.parametrize("frame", [337, 1355])
@pytest.mark.parametrize("angle", [0., .6, math.pi / 2, math.pi])
@pytest.mark.parametrize("mirror", [False, True])
def test_p1_opposed_thumb_with_four_curled_fingers_is_fist(frame, angle, mirror):
    sample = next(s for s in DATA["geometry_samples"]
                  if s["run_id"].endswith("222450") and s["frame_id"] == frame)
    assert sample["recorded_pose"] == "UNKNOWN" and sample["recorded_thumb"] == "INTERMEDIATE"
    result = classify_pose(_geometry(sample, angle, mirror), PROFILE.pose)
    assert result.fingers[0].state is FingerState.INTERMEDIATE
    assert all(f.state is FingerState.FLEXED for f in result.fingers[1:])
    assert result.pinch.exit and result.pose is HandPose.FIST
    assert next(p.passed for p in result.predicates if p.name == "fist_thumb_compatible")


@pytest.mark.parametrize("sample", DATA["geometry_samples"])
def test_p1_pinch_precedence_and_other_recorded_poses_preserved(sample):
    result = classify_pose(_geometry(sample), PROFILE.pose)
    if sample["run_id"].endswith("222450") and sample["frame_id"] in (337, 1355):
        assert result.pose is HandPose.FIST
    else:
        assert result.pose.value == sample["recorded_pose"]


def test_p1_four_curled_fingers_without_thumb_opposition_stay_unknown():
    sample = next(s for s in DATA["geometry_samples"] if s["frame_id"] == 80)
    hand = _geometry(sample)
    result = classify_pose(replace(hand, thumb_index_distance_palm=.4), PROFILE.pose)
    assert result.fingers[0].state is FingerState.INTERMEDIATE
    assert result.pose is HandPose.UNKNOWN
    assert not next(p.passed for p in result.predicates if p.name == "fist_thumb_compatible")


def test_p1_earned_rearm_survives_pure_band_without_unknown_action():
    tracker = TemporalPoseTracker(PROFILE.temporal)
    for sample in DATA["temporal_samples"]:
        g = FrameGeometry(sample["run_id"], sample["frame_id"], sample["timestamp_s"], 640, 480)
        obs = PoseObservation(g, HandPose(sample["pose"]),
            tuple(FingerObservation(f, FingerState(s), (), ())
                  for f, s in zip(Finger, sample["states"])),
            evaluate_pinch_geometry(sample["distance"], PROFILE.pose), (),
            tuple(ClassificationReason(r) for r in sample["reasons"]), ())
        state = tracker.update(obs, tracking_status=TrackingStatus(sample["tracking_status"]))
    assert sample["frame_id"] == 81 and not sample["recorded_armed"]
    assert state.armed and state.pending_pose is None
    assert state.candidate_pose is HandPose.UNKNOWN and not state.action_allowed

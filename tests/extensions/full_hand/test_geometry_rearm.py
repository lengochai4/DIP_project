"""A5.2 clutch evidence is independent of semantic pose permission."""

from dataclasses import replace
import json
from pathlib import Path

import pytest

from dip_touchless.core import TrackingStatus
from extensions.stem3d.full_hand import (
    ClassificationReason as C, Finger, FingerObservation, FingerState, FrameGeometry,
    GeometryReason, HandPose as P, PoseObservation, TemporalPoseTracker,
    TemporalReason as R, evaluate_pinch_geometry,
)
from extensions.stem3d.full_hand.observe import load_observe_profile


PROFILE = load_observe_profile(Path("config/extensions/full_hand_observe.yaml"))
DATA = json.loads((Path(__file__).parent / "fixtures/p1_rearm_sequences.json").read_text())


def observation(t, distance, pose=P.UNKNOWN):
    return PoseObservation(FrameGeometry("geometry-rearm", int(t * 1000), t, 640, 480),
        pose, tuple(FingerObservation(f, FingerState.INTERMEDIATE, (), ()) for f in Finger),
        evaluate_pinch_geometry(distance, PROFILE.pose), (),
        (C.PINCH_BOUNDARY_BAND,) if .2 <= distance <= .35 else
        (C.NO_POSE_MATCH,) if pose is P.UNKNOWN else (), ())


def update(tracker, t, distance, pose=P.UNKNOWN, **kwargs):
    return tracker.update(observation(t, distance, pose),
                          tracking_status=kwargs.pop("tracking_status", TrackingStatus.VALID),
                          **kwargs)


def armed():
    tracker = TemporalPoseTracker(PROFILE.temporal)
    for t in (0., .125, .25):
        state = update(tracker, t, .5)
    assert state.armed and state.stable_pose is P.UNKNOWN and not state.action_allowed
    return tracker


@pytest.mark.parametrize("run", DATA["runs"], ids=lambda r:r["run_id"])
def test_recorded_p1_and_p1b_release_geometry_rearms_then_enters_pinch(run):
    tracker = TemporalPoseTracker(PROFILE.temporal)
    states = []
    for s in run["samples"]:
        obs = PoseObservation(FrameGeometry(**s["frame_geometry"]), P(s["pose"]),
            tuple(FingerObservation(f, FingerState(state), (), (),
                                    tuple(GeometryReason(r) for r in reasons))
                  for f, state, reasons in zip(Finger, s["states"], s["finger_geometry_reasons"])),
            evaluate_pinch_geometry(s["distance"], PROFILE.pose), (),
            tuple(C(r) for r in s["reasons"]), tuple(GeometryReason(r) for r in s["geometry_reasons"]))
        states.append(tracker.update(obs, tracking_status=TrackingStatus(s["tracking_status"]),
                                     filter_reset=s["filter_reset"]))
    assert any(R.REARMED in s.reasons for s in states)
    if run["run_id"].endswith("225528"):
        assert any(R.REARMED in s.reasons and s.candidate_pose is P.UNKNOWN for s in states)
    assert states[-1].stable_pose is P.PINCH and states[-1].action_allowed
    assert not run["samples"][-1]["recorded_armed"]
    assert all(not s.action_allowed for s in states if s.candidate_pose is P.UNKNOWN)


@pytest.mark.parametrize("offset,expected", [(.124, False), (.125, True), (.126, True)])
def test_unknown_release_dwell_uses_configured_seconds(offset, expected):
    tracker = TemporalPoseTracker(PROFILE.temporal)
    update(tracker, 0., .5)
    first = update(tracker, .125, .5)
    assert first.rearm_since_s == .125
    state = update(tracker, .125 + offset, .5)
    assert state.armed is expected and not state.action_allowed
    assert state.stable_pose is P.UNKNOWN


@pytest.mark.parametrize("distance", [.2, .3, .35, .1])
def test_band_and_enter_interrupt_release_without_rearming(distance):
    tracker = TemporalPoseTracker(PROFILE.temporal)
    update(tracker, 0., .5)
    update(tracker, .125, .5)
    state = update(tracker, .25, distance)
    assert not state.armed and state.rearm_since_s is None and not state.action_allowed
    assert R.REARM_PENDING in state.reasons
    first = update(tracker, .375, .5)
    assert not first.armed and first.rearm_since_s == .375
    assert update(tracker, .5, .5).armed


def test_armed_unknown_and_band_never_act_and_reentry_requires_fresh_dwell():
    tracker = armed()
    assert update(tracker, .375, .1, P.PINCH).pending_pose is P.PINCH
    assert update(tracker, .625, .1, P.PINCH).pinch_latched
    released = update(tracker, .75, .5)
    assert R.SAFE_RELEASE in released.reasons and released.armed
    assert not released.pinch_latched and not released.action_allowed
    band = update(tracker, .875, .3)
    assert band.armed and not band.action_allowed
    start = update(tracker, 1., .1, P.PINCH)
    assert start.candidate_since_s == 1. and not start.action_allowed
    assert not update(tracker, 1.125, .1, P.PINCH).action_allowed
    assert update(tracker, 1.25, .1, P.PINCH).action_allowed


def test_semantic_finger_unknown_is_not_missing_pinch_geometry():
    tracker = TemporalPoseTracker(PROFILE.temporal)
    for t in (0., .125, .25):
        obs = observation(t, .5)
        finger = replace(obs.fingers[0], state=FingerState.UNKNOWN,
                         reasons=(C.CONFLICTING_FEATURES,))
        state = tracker.update(replace(obs, fingers=(finger, *obs.fingers[1:]),
            reasons=(C.FINGER_UNKNOWN,)), tracking_status=TrackingStatus.VALID)
        assert not state.action_allowed
    assert state.armed


@pytest.mark.parametrize("status", [TrackingStatus.NO_HAND, TrackingStatus.INVALID,
                                   TrackingStatus.REACQUIRED])
def test_loss_and_reacquisition_override_geometry_release(status):
    tracker = armed()
    lost = update(tracker, .375, .5, tracking_status=status)
    assert not lost.armed and not lost.action_allowed
    returned = update(tracker, .5, .5)
    if status is not TrackingStatus.REACQUIRED:
        assert R.REACQUISITION in returned.reasons and not returned.armed
    assert not update(tracker, .625, .1, P.PINCH).armed


@pytest.mark.parametrize("fault", ["run", "timestamp", "gap", "filter", "explicit", "geometry"])
def test_reset_or_invalid_geometry_discards_earned_release(fault):
    tracker = armed()
    obs = observation(.375, .5)
    kwargs = {}
    if fault == "run":
        obs = replace(obs, frame_geometry=replace(obs.frame_geometry, run_id="new"))
    elif fault == "timestamp":
        obs = replace(obs, frame_geometry=replace(obs.frame_geometry, timestamp_s=.25))
    elif fault == "gap":
        obs = replace(obs, frame_geometry=replace(obs.frame_geometry, timestamp_s=3.))
    elif fault == "filter":
        kwargs["filter_reset"] = True
    elif fault == "explicit":
        tracker.reset()
    else:
        obs = replace(obs, geometry_reasons=(GeometryReason.DEGENERATE_PALM,))
    state = tracker.update(obs, tracking_status=TrackingStatus.VALID, **kwargs)
    assert state.reset_occurred and not state.armed and not state.action_allowed

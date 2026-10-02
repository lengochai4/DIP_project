"""Experimental profile opt-in, exact boundaries, safety and legacy parity."""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from dip_touchless.core import TrackingStatus
from extensions.stem3d.full_hand import (
    ClassificationReason, HandPose, TemporalPoseTracker, classify_pose, evaluate_pinch_geometry,
)
from extensions.stem3d.full_hand.observe import load_observe_profile
from extensions.stem3d.full_hand.pinch_diagnostic import MarkerEdges, poll_markers
from test_observe import _execute, _run
from test_pose_classification import _hand

BASELINE = Path("config/extensions/full_hand_observe.yaml")
CANDIDATE = Path("config/extensions/full_hand_pinch_candidate.yaml")


def test_candidate_differs_only_in_enter_and_baseline_hash_is_frozen():
    baseline = load_observe_profile(BASELINE)
    candidate = load_observe_profile(CANDIDATE)
    assert candidate == replace(baseline, pose=replace(baseline.pose, pinch_enter_distance_palm=.33))
    assert baseline.pose.pinch_enter_distance_palm == .20
    assert baseline.pose.pinch_exit_distance_palm == candidate.pose.pinch_exit_distance_palm == .35
    canonical = json.dumps(asdict(baseline), sort_keys=True, allow_nan=False)
    assert hashlib.sha256(canonical.encode()).hexdigest() == "a8bc8f01468c590a093af1f295e1c8f4a50ebd1a2c0c9d00c3b6c790558d89ba"


def test_cli_default_baseline_and_explicit_candidate(monkeypatch):
    from extensions.stem3d import full_hand_app
    loaded = []
    def load(path):
        loaded.append(path.resolve())
        return load_observe_profile(path)
    monkeypatch.setattr(full_hand_app, "load_observe_profile", load)
    monkeypatch.setattr(full_hand_app.live_demo, "main", lambda **kwargs: None)
    full_hand_app.main([])
    full_hand_app.main(["--mode", "OBSERVE_FULL_HAND", "--profile", str(CANDIDATE)])
    assert loaded == [BASELINE.resolve(), CANDIDATE.resolve()]


def test_candidate_rejected_in_legacy_mode():
    from extensions.stem3d.full_hand_app import main
    with pytest.raises(SystemExit) as exc:
        main(["--mode", "LEGACY", "--profile", str(CANDIDATE)])
    assert exc.value.code == 2


@pytest.mark.parametrize("d,zone", [(.20, "ENTER"), (.27074, "ENTER"), (.31250, "ENTER"),
    (.329999, "ENTER"), (.33, "BAND"), (.330001, "BAND"), (.349999, "BAND"),
    (.35, "BAND"), (.350001, "RELEASE")])
def test_candidate_strict_boundaries(d, zone):
    profile = load_observe_profile(CANDIDATE)
    pinch = evaluate_pinch_geometry(d, profile.pose)
    assert (pinch.enter, pinch.boundary_band, pinch.exit) == (zone == "ENTER", zone == "BAND", zone == "RELEASE")
    observation = classify_pose(replace(_hand(), thumb_index_distance_palm=d), profile.pose)
    assert observation.pose is (HandPose.PINCH if zone == "ENTER" else HandPose.UNKNOWN if zone == "BAND" else HandPose.OPEN)


@pytest.mark.parametrize("d", [.27074, .30, .31250])
def test_baseline_retains_unknown_band_on_p1e_contact_distances(d):
    baseline = load_observe_profile(BASELINE)
    assert classify_pose(replace(_hand(), thumb_index_distance_palm=d), baseline.pose).pose is HandPose.UNKNOWN


@pytest.mark.parametrize("path", [BASELINE, CANDIDATE])
def test_geometry_rearm_unknown_safety_band_and_loss_are_unchanged(path):
    profile = load_observe_profile(path)
    tracker = TemporalPoseTracker(profile.temporal)
    def update(t, d, *, unknown=False, status=TrackingStatus.VALID):
        hand = _hand()
        hand = replace(hand, frame_geometry=replace(hand.frame_geometry, frame_id=int(t*1000), timestamp_s=t), thumb_index_distance_palm=d)
        observation = classify_pose(hand, profile.pose)
        if unknown:
            observation = replace(observation, pose=HandPose.UNKNOWN, reasons=(ClassificationReason.NO_POSE_MATCH,))
        return tracker.update(observation, tracking_status=status)
    for t in (0., .125, .25): state = update(t, .5, unknown=True)
    assert state.armed and not state.action_allowed
    d = profile.pose.pinch_enter_distance_palm - .01
    assert not update(.375, d).action_allowed
    stable = update(.625, d)
    assert stable.stable_pose is HandPose.PINCH and stable.action_allowed
    band = update(.75, (profile.pose.pinch_enter_distance_palm + .35) / 2)
    assert band.armed and band.pinch_latched and not band.action_allowed
    lost = update(.875, d, status=TrackingStatus.NO_HAND)
    assert not lost.armed and not lost.action_allowed and not lost.pinch_latched
    assert not update(1., d, status=TrackingStatus.REACQUIRED).armed
    assert not update(1.125, .5, unknown=True).armed
    # Return to entering geometry cancels strict release dwell.
    assert not update(1.1875, d).armed
    assert not update(1.25, .35).armed  # Exit equality is not release evidence.
    assert not update(1.375, .5, unknown=True).armed
    rearmed = update(1.5, .5, unknown=True)
    assert rearmed.armed and not rearmed.action_allowed
    assert not update(1.625, d).action_allowed
    reentry = update(1.875, d)
    assert reentry.action_allowed and reentry.stable_pose is HandPose.PINCH


def test_candidate_legacy_interaction_is_identical_field_for_field():
    legacy, baseline, candidate = _run(False), _run(True), _run(True)
    candidate.observer.profile = load_observe_profile(CANDIDATE)
    candidate.observer.tracker = TemporalPoseTracker(candidate.observer.profile.temporal)
    assert _execute(legacy) == _execute(baseline) == _execute(candidate) == 16
    assert [asdict(s) for s in legacy.received] == [asdict(s) for s in baseline.received] == [asdict(s) for s in candidate.received]
    assert legacy.logger.tracking == candidate.logger.tracking


def test_calibration_keys_are_explicit_and_conflicts_do_not_choose_a_label(monkeypatch):
    fake = SimpleNamespace(K_t=0, K_u=1, K_n=2, K_v=3, K_b=4,
                           key=SimpleNamespace(get_pressed=lambda: [False, False, False, True, False], get_focused=lambda: True))
    monkeypatch.setitem(sys.modules, "pygame", fake)
    assert poll_markers() == (set(), True)
    assert poll_markers(calibration=True) == ({"PINCH_NEAR_NO_TOUCH"}, True)
    edges = MarkerEdges()
    assert edges.update({"PINCH_NEAR_NO_TOUCH"}) == ("PINCH_NEAR_NO_TOUCH",)
    edges.update(set())
    assert edges.update({"PINCH_TOUCH", "PINCH_MEDIUM_SEPARATION"}) == ("CONFLICTING_MARKERS",)


def test_calibration_markers_require_diagnostic_flag():
    from extensions.stem3d.full_hand_app import main
    with pytest.raises(SystemExit) as exc:
        main(["--pinch-calibration-markers"])
    assert exc.value.code == 2


def test_four_class_visual_labels_and_manifest_are_observation_only(tmp_path):
    from extensions.stem3d.full_hand.pinch_diagnostic import PinchDiagnosticJournal
    observed = _run(True)
    _execute(observed)
    events = iter([{"PINCH_NEAR_NO_TOUCH"}, set(), {"PINCH_MEDIUM_SEPARATION"}])
    journal = PinchDiagnosticJournal(tmp_path, load_observe_profile(CANDIDATE),
        lambda: (next(events), True), visual_capture=True, calibration_labels=True)
    try:
        for i in range(3):
            journal.consume(observed.logger.tracking[i], observed.snapshots[i], observed.source.packets[i])
    finally:
        journal.close()
    manifest = json.loads((tmp_path / "pinch_diagnostic_manifest.json").read_text())
    assert manifest["enter"] == .33 and manifest["exit"] == .35
    assert manifest["extra_keys"] == {"V": "PINCH_NEAR_NO_TOUCH", "B": "PINCH_MEDIUM_SEPARATION"}
    assert journal.visual.max_samples == 40
    images = [json.loads(p.read_text()) for p in (tmp_path / "pinch_visual").glob("*.json")]
    assert {s["physical_marker"]["event"] for s in images} == {"PINCH_NEAR_NO_TOUCH", "PINCH_MEDIUM_SEPARATION"}
    assert all(s["sample_kind"] == "MARKER" for s in images)

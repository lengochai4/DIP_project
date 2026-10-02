"""Explicit reference lifecycle, projected compatibility and fail-safe replay."""

from dataclasses import replace, FrozenInstanceError
from pathlib import Path

import pytest

from dip_touchless.core import TrackingStatus
from extensions.stem3d.full_hand import extract_hand_geometry
from extensions.stem3d.full_hand.intent_pinch_contracts import ReferenceStatus, RelativeClosureThresholds
from extensions.stem3d.full_hand.intent_session import (
    IntentObservationSession, IntentObserveProfile, load_intent_profile, palm_signature,
)
from extensions.stem3d.full_hand.intent_temporal import IntentPinchState as S
from test_geometry import _fixture
from test_relative_intent_pinch import _scope, _policy
from test_intent_temporal import _config


def _session():
    profile = IntentObserveProfile(_policy(), RelativeClosureThresholds(.5, .25), _config(), .5, .2, 3.)
    return IntentObservationSession(profile, _scope())


def _tick(session, t, c=0., *, events=(), status=TrackingStatus.VALID,
          reset=False, run="synthetic-a2", transform=lambda x, y: (x, y)):
    frame, fg = _fixture(transform=transform)
    fg = replace(fg, run_id=run, frame_id=int(t*1000), timestamp_s=t)
    frame = replace(frame, run_id=run, frame_id=fg.frame_id, timestamp_s=t, status=status,
                    filter_diagnostics=replace(frame.filter_diagnostics, reset_occurred=reset))
    hand = extract_hand_geometry(frame, fg)
    if hand.valid:
        hand = replace(hand, thumb_index_distance_palm=1. - c)
    return session.consume(frame, hand, events=events)


def _calibrated(session):
    assert _tick(session, 0., events=("CALIBRATE_RELEASE",)).calibration_status == "CAPTURING_RELEASE"
    _tick(session, .25)
    result = _tick(session, .5)
    assert result.reference.valid and result.temporal.state is S.UNKNOWN
    assert result.observation is None and result.calibration_status == "READY"
    return result.reference


def _active(session):
    ref = _calibrated(session)
    _tick(session, .625)
    _tick(session, .75)
    assert _tick(session, 1.).temporal.armed
    _tick(session, 1.125, .75)
    result = _tick(session, 1.375, .75)
    assert result.temporal.active_evidence
    return ref


def test_no_startup_reference_guessing_despite_static_open_or_closed_hand():
    session = _session()
    for i in range(20):
        result = _tick(session, i * .125, .75 if i % 2 else 0.)
        assert result.calibration_status == "NEEDS_CALIBRATION" and result.reference is None
        assert result.temporal.state is S.UNKNOWN and not result.temporal.active_evidence


def test_confirmed_capture_frozen_reference_and_repeated_cycles():
    session = _session()
    ref = _active(session)
    for t, c in ((1.5, .375), (1.625, 0.), (1.75, 0.), (1.875, 0.), (2., .75), (2.25, .75)):
        result = _tick(session, t, c)
        assert result.reference is ref
    assert result.temporal.active_evidence and result.temporal.cycle_id == 2


def test_noisy_capture_rejects_without_silently_retrying():
    session = _session()
    _tick(session, 0., events=("CALIBRATE_RELEASE",))
    _tick(session, .25, -.3)
    result = _tick(session, .5)
    assert result.calibration_status == "NEEDS_CALIBRATION" and result.reference is None
    assert "NOISY_WINDOW" in result.enrollment_reasons
    assert _tick(session, .75).reference is None


@pytest.mark.parametrize("status", [TrackingStatus.TEMPORARY_LOSS, TrackingStatus.REACQUIRED,
                                   TrackingStatus.NO_HAND, TrackingStatus.INVALID])
def test_capture_interruption_requires_explicit_retry(status):
    session = _session()
    _tick(session, 0., events=("CALIBRATE_RELEASE",))
    result = _tick(session, .25, status=status)
    assert result.enrollment_reasons == ("ENROLLMENT_INTERRUPTED",)
    assert not result.temporal.active_evidence
    assert _tick(session, .5).reference is None


def test_loss_closed_reacquisition_and_band_never_revalidate_or_resume():
    session = _session()
    ref = _active(session)
    lost = _tick(session, 1.5, status=TrackingStatus.TEMPORARY_LOSS)
    assert lost.reference.status is ReferenceStatus.UNVERIFIED
    for t, c, status in ((1.625, .75, TrackingStatus.REACQUIRED),
                         (1.75, .75, TrackingStatus.VALID), (1.875, .375, TrackingStatus.VALID)):
        result = _tick(session, t, c, status=status)
        assert result.calibration_status == "REVALIDATING_RELEASE" and not result.temporal.armed
        assert not result.temporal.active_evidence
    _tick(session, 2.)
    _tick(session, 2.125, .375)  # Interrupts proof-only release interval.
    _tick(session, 2.25)
    assert _tick(session, 2.375).reference.status is ReferenceStatus.UNVERIFIED
    ready_ref = _tick(session, 2.5)
    assert ready_ref.reference.valid and ready_ref.revalidation_id == 1
    assert ready_ref.reference.distance_palm == ref.distance_palm
    assert ready_ref.reference.reference_id == ref.reference_id
    assert not ready_ref.temporal.active_evidence
    _tick(session, 2.625)
    assert _tick(session, 2.875).temporal.armed
    _tick(session, 3., .75)
    assert _tick(session, 3.25, .75).temporal.active_evidence


@pytest.mark.parametrize("kind", ["reset", "filter_reset", "gap", "run", "duplicate"])
def test_hard_reset_invalidates_reference_and_never_implicitly_reenrolls(kind):
    session = _session()
    _active(session)
    kwargs = {"reset": dict(events=("RESET_REFERENCE",)), "filter_reset": dict(reset=True),
              "gap": {}, "run": dict(run="new-run"), "duplicate": {}}[kind]
    t = 3. if kind == "gap" else 1.375 if kind == "duplicate" else 1.5
    result = _tick(session, t, .75, **kwargs)
    assert not result.temporal.active_evidence and result.reference.status is ReferenceStatus.INVALIDATED
    assert result.calibration_status == "NEEDS_CALIBRATION"


def test_refresh_mid_hold_neutralizes_old_episode_and_creates_new_version():
    session = _session()
    old = _active(session)
    first = _tick(session, 1.5, events=("CALIBRATE_RELEASE",))
    assert first.reference is None and not first.temporal.active_evidence
    _tick(session, 1.75)
    new = _tick(session, 2.)
    assert new.reference.version == 2 and new.reference.reference_id != old.reference_id
    assert new.reference.valid and not new.temporal.active_evidence


@pytest.mark.parametrize("transform", [lambda x, y: (x+.2, y-.1), lambda x, y: (1.-x, y),
    lambda x, y: (.5+1.8*(x-.5), .5+1.8*(y-.5)), lambda x, y: (y, 1.-x)])
def test_guard_accepts_comparable_translation_scale_rotation_and_mirror(transform):
    session = _session()
    _calibrated(session)
    result = _tick(session, .625, transform=transform)
    assert result.observation.valid and result.palm_shape_delta == pytest.approx(0., abs=1e-14)


def test_guard_rejects_projected_palm_shape_change():
    session = _session()
    _calibrated(session)
    # x-only deformation changes palm ratios; not interpreted as metric depth.
    result = _tick(session, .625, transform=lambda x, y: (.5+.1*(x-.5), y))
    assert result.reference.status is ReferenceStatus.INVALIDATED
    assert result.observation.relative_closure is None and not result.temporal.active_evidence


def test_actual_source_dimensions_change_invalidates_reference():
    session = _session()
    _calibrated(session)
    frame, fg = _fixture(900, 900)
    fg = replace(fg, frame_id=625, timestamp_s=.625)
    frame = replace(frame, frame_id=625, timestamp_s=.625)
    result = session.consume(frame, extract_hand_geometry(frame, fg))
    assert result.reference.status is ReferenceStatus.INVALIDATED
    assert result.observation.relative_closure is None


def test_missing_geometry_and_identity_mismatch_clear_old_feedback():
    session = _session()
    _active(session)
    frame, fg = _fixture()
    assert session.consume(frame, None) is None
    assert session.reference.status is ReferenceStatus.UNVERIFIED
    with pytest.raises(ValueError, match="identity mismatch"):
        session.consume(frame, replace(extract_hand_geometry(frame, fg), frame_geometry=replace(fg, frame_id=99)))


def test_profile_selection_hash_and_snapshot_immutability():
    path = Path("config/extensions/intent_pinch_observe.yaml")
    profile = load_intent_profile(path)
    assert profile.sha256 == load_intent_profile(path).sha256
    assert profile.closure.enter == .60 and profile.closure.exit == .25
    snapshot = _tick(_session(), 0.)
    with pytest.raises(FrozenInstanceError):
        snapshot.calibration_status = "READY"


def test_session_replay_deterministic_and_public_input_immutable():
    sequence = [(0., 0., ("CALIBRATE_RELEASE",)), (.25, 0., ()), (.5, 0., ()),
                (.625, 0., ()), (.75, 0., ()), (1., 0., ()), (1.125, .75, ()), (1.375, .75, ())]
    def replay():
        session = _session()
        return tuple(_tick(session, t, c, events=events) for t, c, events in sequence)
    assert replay() == replay()
    session = _session()
    frame, fg = _fixture()
    hand = extract_hand_geometry(frame, fg)
    before = repr((frame, hand))
    session.consume(frame, hand, events=("CALIBRATE_RELEASE",))
    assert repr((frame, hand)) == before

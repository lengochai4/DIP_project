"""Synthetic intended-close sequences, not physical acceptance results."""

from dataclasses import FrozenInstanceError, replace

import pytest

from extensions.stem3d.full_hand.intent_temporal import (
    IntentTemporalConfig, IntentPinchState as S, IntentTransitionReason as R,
    TemporalIntentPinchTracker,
)
from test_relative_intent_pinch import _build, _window, _hand, _evaluate


def _config():
    return IntentTemporalConfig(.25, .125, .25, 1., 2., .125, 2.)


def _ob(t, c=0., *, ref=None):
    return _evaluate(_hand(1. - c, int(t * 1000), t), ref or _build(_window((1.,) * 3)).reference)


def _ready(tracker):
    assert not tracker.update(_ob(1.)).armed
    assert not tracker.update(_ob(1.125)).armed
    result = tracker.update(_ob(1.375))
    assert result.state is S.RELEASED and result.armed and not result.active_evidence
    return result


def _active(tracker):
    _ready(tracker)
    assert tracker.update(_ob(1.5, .75)).state is S.CLOSING
    result = tracker.update(_ob(1.75, .75))
    assert result.state is S.PINCH_ACTIVE and result.active_evidence
    return result


def test_repeated_lifecycle_entry_hold_release_rearm_reentry():
    tracker = TemporalIntentPinchTracker(_config())
    first = _active(tracker)
    hold = tracker.update(_ob(1.875, .375))
    assert hold.state is S.HOLD and hold.active_evidence and hold.cycle_id == first.cycle_id == 1
    released = tracker.update(_ob(2.))
    assert released.state is S.RELEASE and not released.active_evidence and not released.armed
    assert R.SAFE_RELEASE in released.reasons
    confirmed = tracker.update(_ob(2.125))
    assert confirmed.release_confirmed and not confirmed.armed
    ready = tracker.update(_ob(2.25))
    assert ready.state is S.RELEASED and ready.armed and not ready.active_evidence
    tracker.update(_ob(2.375, .75))
    second = tracker.update(_ob(2.625, .75))
    assert second.state is S.PINCH_ACTIVE and second.cycle_id == 2
    assert second.transition_id > first.transition_id


def test_startup_closed_never_enters_without_confirmed_rearm():
    tracker = TemporalIntentPinchTracker(_config())
    for t in (1., 1.25, 1.5, 1.75, 2.):
        result = tracker.update(_ob(t, .75))
        assert result.state is S.UNKNOWN and result.waiting_for_release and not result.active_evidence


def test_enter_dwell_boundary_and_short_glitch():
    tracker = TemporalIntentPinchTracker(_config())
    _ready(tracker)
    tracker.update(_ob(1.5, .75))
    before = tracker.update(_ob(1.749, .75))
    assert not before.active_evidence
    band = tracker.update(_ob(1.75, .375))
    assert R.ENTRY_CANCELLED in band.reasons and band.enter_since_s is None
    tracker.update(_ob(1.875, .75))
    assert tracker.update(_ob(2.125, .75)).active_evidence


@pytest.mark.parametrize("closure", [.25, .375, .5, .75])
def test_band_or_return_to_closed_cancels_release_dwell_without_restoring_hold(closure):
    tracker = TemporalIntentPinchTracker(_config())
    _active(tracker)
    tracker.update(_ob(2.))
    interrupted = tracker.update(_ob(2.125, closure))
    assert interrupted.state is S.RELEASE and interrupted.waiting_for_release
    assert interrupted.release_since_s is None and not interrupted.active_evidence
    tracker.update(_ob(2.25))
    assert not tracker.update(_ob(2.375)).armed
    assert tracker.update(_ob(2.5)).state is S.RELEASED


def test_unknown_immediately_revokes_and_requires_new_release():
    tracker = TemporalIntentPinchTracker(_config())
    _active(tracker)
    missing = _evaluate(_hand(.25, 1875, 1.875), None)
    result = tracker.update(missing)
    assert not result.active_evidence and result.state is S.UNKNOWN
    for t in (2., 2.125, 2.25):
        result = tracker.update(_ob(t, .75))
        assert not result.active_evidence and not result.armed
    tracker.update(_ob(2.375))
    assert tracker.update(_ob(2.625)).armed


@pytest.mark.parametrize("kind", ["duplicate", "out_of_order", "gap", "run", "reference"])
def test_discontinuities_cancel_action_and_do_not_resume_on_closed_hand(kind):
    tracker = TemporalIntentPinchTracker(_config())
    _active(tracker)
    observation = _ob(1.875, .75)
    if kind == "duplicate": observation = _ob(1.75, .75)
    elif kind == "out_of_order": observation = _ob(1.5, .75)
    elif kind == "gap": observation = _ob(3., .75)
    elif kind == "run": observation = replace(observation, frame_geometry=replace(observation.frame_geometry, run_id="new"))
    elif kind == "reference": observation = replace(observation, reference=replace(observation.reference, reference_id="new"))
    result = tracker.update(observation)
    assert result.state is S.UNKNOWN and not result.active_evidence and not result.armed
    assert result.reset_id >= 2


def test_duplicate_never_advances_entry_or_generates_second_identity():
    tracker = TemporalIntentPinchTracker(_config())
    active = _active(tracker)
    repeated = tracker.update(_ob(1.75, .75))
    assert R.TIMESTAMP_DISCONTINUITY in repeated.reasons
    assert repeated.cycle_id == active.cycle_id and not repeated.active_evidence
    assert not tracker.update(_ob(1.875, .75)).active_evidence


def test_candidate_expiry_requires_release_before_next_entry():
    tracker = TemporalIntentPinchTracker(_config())
    _ready(tracker)
    tracker.update(_ob(1.5, .375))
    for t in (1.75, 2., 2.25, 2.5, 2.75, 3., 3.25, 3.5):
        assert not tracker.update(_ob(t, .375)).active_evidence
    expired = tracker.update(_ob(3.625, .375))
    assert expired.state is S.UNKNOWN and R.CANDIDATE_EXPIRED in expired.reasons
    assert not tracker.update(_ob(3.75, .75)).active_evidence


def test_noise_and_minimum_progress_require_fresh_excursion():
    tracker = TemporalIntentPinchTracker(replace(_config(), min_relative_progress=.9))
    _ready(tracker)
    assert tracker.update(_ob(1.5, .75)).state is S.RELEASED
    assert not tracker.update(_ob(1.75, .75)).active_evidence


def test_reopening_abandons_candidate_and_refreshes_motion_anchor_only():
    tracker = TemporalIntentPinchTracker(_config())
    _ready(tracker)
    tracker.update(_ob(1.5, .75))
    result = tracker.update(_ob(1.625, -.25))
    assert result.state is S.RELEASED and result.release_anchor_closure == -.25
    assert result.closing_since_s is None and result.enter_since_s is None
    assert not result.active_evidence and R.REOPENED in result.reasons


@pytest.mark.parametrize("release,rearm", [(0., .25), (.25, 0.), (.5, .25), (.25, .5)])
def test_release_and_rearm_share_interval_instead_of_double_wait(release, rearm):
    tracker = TemporalIntentPinchTracker(replace(_config(), release_dwell_s=release, rearm_dwell_s=rearm))
    tracker.update(_ob(1.))
    tracker.update(_ob(1.125))
    result = tracker.update(_ob(1.125 + max(release, rearm)))
    assert result.armed and not result.active_evidence


def test_reset_and_replay_are_deterministic_and_immutable():
    observations = tuple(_ob(t, c) for t, c in (
        (1., 0.), (1.125, 0.), (1.375, 0.), (1.5, .75), (1.75, .75), (2., 0.), (2.25, 0.)))
    before = repr(observations)
    def replay():
        tracker = TemporalIntentPinchTracker(_config())
        snapshots = tuple(tracker.update(o) for o in observations)
        reset = tracker.reset()
        assert reset.state is S.UNKNOWN and reset.reset_id > snapshots[-1].reset_id
        assert not tracker.update(_ob(3., .75)).active_evidence
        return snapshots, reset
    assert replay() == replay() and repr(observations) == before
    with pytest.raises(FrozenInstanceError):
        replay()[0][-1].armed = True


@pytest.mark.parametrize("change", [dict(enter_dwell_s=-1.), dict(reset_gap_s=0.),
    dict(max_closing_age_s=.25), dict(min_relative_progress=0.),
    dict(progress_noise_multiplier=.5), dict(rearm_dwell_s=float("nan"))])
def test_temporal_policy_rejects_invalid_parameters(change):
    with pytest.raises(ValueError):
        replace(_config(), **change)

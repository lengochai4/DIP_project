"""Synthetic timestamp sequences only; no runtime or physical validation."""

from dataclasses import FrozenInstanceError, replace
import math

import pytest

from dip_touchless.core import TrackingStatus
from extensions.stem3d.full_hand import (
    ClassificationReason, Finger, FingerObservation, FingerState, FrameGeometry,
    GeometryReason, HandPose, PinchGeometry, PoseObservation,
    TemporalPoseConfig, TemporalPoseTracker, TemporalReason as R,
)


def _config(**changes):
    # Binary-exact synthetic timings; no production defaults.
    return replace(TemporalPoseConfig(.125, .25, .25, .375, .125, 2.), **changes)


def _obs(pose, timestamp, *, band=False, invalid=False, run="r", frame_id=None):
    geometry = FrameGeometry(run, int(timestamp * 1000) if frame_id is None else frame_id,
                             timestamp, 1600, 900)
    states = {
        HandPose.OPEN: (FingerState.EXTENDED,) * 5,
        HandPose.POINT: (FingerState.EXTENDED, FingerState.EXTENDED,
                        FingerState.FLEXED, FingerState.FLEXED, FingerState.FLEXED),
        HandPose.FIST: (FingerState.FLEXED,) * 5,
    }.get(pose, (FingerState.INTERMEDIATE,) * 5)
    fingers = tuple(FingerObservation(f, s, (), ()) for f, s in zip(Finger, states))
    enter = pose is HandPose.PINCH
    pinch = PinchGeometry(.1 if enter else .3 if band else .5,
                          enter, not enter and not band, band, ())
    reasons = ((ClassificationReason.PINCH_BOUNDARY_BAND,) if band else
               (ClassificationReason.NO_POSE_MATCH,) if pose is HandPose.UNKNOWN else ())
    if invalid:
        reasons = (ClassificationReason.INVALID_GEOMETRY,)
    return PoseObservation(geometry, pose, fingers, pinch, (), reasons,
                           (GeometryReason.DEGENERATE_PALM,) if invalid else ())


def _update(tracker, pose, t, **kwargs):
    return tracker.update(_obs(pose, t, **kwargs), tracking_status=TrackingStatus.VALID)


def _ready(config=None):
    tracker = TemporalPoseTracker(config or _config())
    for t in (0., .125, .25, .375, .5, .625):
        state = _update(tracker, HandPose.OPEN, t)
    assert state.armed and state.stable_pose is HandPose.OPEN and state.action_allowed
    return tracker


def _pinched():
    tracker = _ready()
    _update(tracker, HandPose.PINCH, .75)
    state = _update(tracker, HandPose.PINCH, 1.)
    assert state.stable_pose is HandPose.PINCH and state.action_allowed
    return tracker


def test_initialization_rearm_and_first_pose_dwell_are_distinct_neutral_gates():
    tracker = TemporalPoseTracker(_config())
    initial = _update(tracker, HandPose.OPEN, 0.)
    assert initial.reset_occurred and initial.reasons == (R.INITIALIZATION,)
    assert not initial.armed and initial.stable_pose is HandPose.UNKNOWN
    pending = _update(tracker, HandPose.OPEN, .125)
    assert pending.rearm_since_s == .125 and not pending.action_allowed
    armed = _update(tracker, HandPose.OPEN, .25)
    assert armed.armed and not armed.action_allowed and R.REARMED in armed.reasons
    first = _update(tracker, HandPose.OPEN, .375)
    assert first.pending_pose is HandPose.OPEN and first.candidate_since_s == .375
    assert first.stable_pose is HandPose.UNKNOWN and not first.action_allowed
    stable = _update(tracker, HandPose.OPEN, .5)
    assert stable.stable_pose is HandPose.OPEN and stable.action_allowed
    assert stable.transition_id == 1 and stable.reset_id == 1


@pytest.mark.parametrize("offset,confirmed", [(.249, False), (.25, True), (.251, True)])
def test_regular_transition_requires_both_enter_and_exit_dwell(offset, confirmed):
    tracker = _ready()
    first = _update(tracker, HandPose.POINT, .75)
    assert first.stable_pose is HandPose.OPEN and not first.action_allowed
    result = _update(tracker, HandPose.POINT, .75 + offset)
    assert (result.stable_pose is HandPose.POINT) is confirmed
    assert result.action_allowed is confirmed


def test_zero_dwell_still_keeps_initialization_and_rearm_frames_neutral():
    tracker = TemporalPoseTracker(_config(enter_dwell_s=0., exit_dwell_s=0.,
        pinch_enter_dwell_s=0., pinch_exit_dwell_s=0., rearm_dwell_s=0.))
    assert not _update(tracker, HandPose.OPEN, 0.).action_allowed
    armed = _update(tracker, HandPose.OPEN, .125)
    assert armed.armed and not armed.action_allowed
    assert _update(tracker, HandPose.POINT, .25).action_allowed


def test_short_candidate_glitch_cancels_without_changing_stable_identity():
    tracker = _ready()
    before = _update(tracker, HandPose.OPEN, .75)
    glitch = _update(tracker, HandPose.FIST, .875)
    assert glitch.pending_pose is HandPose.FIST and not glitch.action_allowed
    recovered = _update(tracker, HandPose.OPEN, 1.)
    assert recovered.action_allowed and recovered.stable_pose is HandPose.OPEN
    assert recovered.transition_id == before.transition_id
    assert recovered.pending_pose is None and R.CANDIDATE_CANCELLED in recovered.reasons


def test_different_candidates_restart_the_dwell_reference():
    tracker = _ready()
    _update(tracker, HandPose.POINT, .75)
    switched = _update(tracker, HandPose.FIST, .875)
    assert switched.candidate_since_s == .875
    assert R.CANDIDATE_CANCELLED in switched.reasons
    assert not _update(tracker, HandPose.FIST, 1.).action_allowed
    assert _update(tracker, HandPose.FIST, 1.125).stable_pose is HandPose.FIST


def test_irregular_sampling_uses_seconds_not_frame_counts():
    tracker = _ready()
    for t in (.75, .751, .76, .80, .99):
        assert not _update(tracker, HandPose.PINCH, t).action_allowed
    assert _update(tracker, HandPose.PINCH, 1.).action_allowed


def test_pinch_enter_dwell_is_independently_configurable():
    tracker = _ready(_config(pinch_enter_dwell_s=.5))
    _update(tracker, HandPose.PINCH, .75)
    assert not _update(tracker, HandPose.PINCH, 1.).action_allowed
    assert _update(tracker, HandPose.PINCH, 1.25).pinch_latched


def test_pinch_band_holds_latch_but_never_allows_actions():
    tracker = _pinched()
    band = _update(tracker, HandPose.UNKNOWN, 1.125, band=True)
    assert band.stable_pose is HandPose.PINCH and band.pinch_latched
    assert band.candidate_pose is HandPose.UNKNOWN and not band.action_allowed
    assert band.reasons == (R.PINCH_BAND_HOLD,)
    assert band.transition_id == 2
    continued = _update(tracker, HandPose.PINCH, 1.25)
    assert continued.action_allowed and continued.transition_id == band.transition_id


@pytest.mark.parametrize("offset,confirmed", [(.374, False), (.375, True), (.376, True)])
def test_pinch_exit_dwell_delays_stable_transition_but_suspends_actions(offset, confirmed):
    tracker = _pinched()
    first = _update(tracker, HandPose.POINT, 1.125)
    assert first.pinch_latched and not first.action_allowed
    result = _update(tracker, HandPose.POINT, 1.125 + offset)
    assert (result.stable_pose is HandPose.POINT) is confirmed
    assert result.action_allowed is confirmed


def test_pinch_exit_glitch_and_band_cancel_exit_dwell():
    tracker = _pinched()
    _update(tracker, HandPose.POINT, 1.125)
    band = _update(tracker, HandPose.UNKNOWN, 1.25, band=True)
    assert band.pinch_latched and not band.action_allowed
    assert band.pending_pose is None and R.CANDIDATE_CANCELLED in band.reasons
    restarted = _update(tracker, HandPose.POINT, 1.375)
    assert restarted.candidate_since_s == 1.375
    assert not _update(tracker, HandPose.POINT, 1.5).action_allowed


def test_band_never_finishes_an_unconfirmed_pinch_entry():
    tracker = _ready()
    _update(tracker, HandPose.PINCH, .75)
    band = _update(tracker, HandPose.UNKNOWN, 1., band=True)
    assert not band.pinch_latched and band.armed
    assert not band.action_allowed and band.pending_pose is None
    restarted = _update(tracker, HandPose.PINCH, 1.125)
    assert restarted.candidate_since_s == 1.125 and not restarted.action_allowed
    assert _update(tracker, HandPose.PINCH, 1.375).pinch_latched
    assert band.stable_pose is HandPose.OPEN


@pytest.mark.parametrize("start", [HandPose.OPEN, HandPose.PINCH])
def test_semantic_unknown_releases_action_memory_without_disarming_geometry(start):
    tracker = _pinched() if start is HandPose.PINCH else _ready()
    unknown = _update(tracker, HandPose.UNKNOWN, 1.125)
    assert unknown.stable_pose is HandPose.UNKNOWN and unknown.armed
    assert not unknown.action_allowed and not unknown.pinch_latched
    assert R.UNKNOWN_INPUT in unknown.reasons and R.SAFE_RELEASE in unknown.reasons
    held = _update(tracker, HandPose.PINCH, 1.25)
    assert held.armed and not held.action_allowed and held.candidate_since_s == 1.25


def test_unknown_cancels_pending_and_dwell_cannot_bridge_the_gap():
    tracker = _ready()
    _update(tracker, HandPose.POINT, .75)
    unknown = _update(tracker, HandPose.UNKNOWN, .875)
    assert unknown.pending_pose is None and unknown.candidate_since_s is None
    first = _update(tracker, HandPose.POINT, 1.)
    assert first.armed and first.candidate_since_s == 1. and not first.action_allowed
    confirmed = _update(tracker, HandPose.POINT, 1.125)
    assert confirmed.action_allowed and confirmed.stable_pose is HandPose.POINT


@pytest.mark.parametrize("status", [TrackingStatus.NO_HAND, TrackingStatus.TEMPORARY_LOSS, TrackingStatus.INVALID])
def test_loss_immediately_cancels_and_repeated_loss_does_not_spam_resets(status):
    tracker = _pinched()
    lost = tracker.update(_obs(HandPose.PINCH, 1.125), tracking_status=status)
    assert lost.reset_occurred and R.TRACKING_LOSS in lost.reasons
    assert R.SAFE_RELEASE in lost.reasons and not lost.pinch_latched
    repeated = tracker.update(_obs(HandPose.PINCH, 1.25), tracking_status=status)
    assert not repeated.reset_occurred
    assert repeated.reset_id == lost.reset_id and repeated.transition_id == lost.transition_id
    assert not _update(tracker, HandPose.PINCH, 1.375).armed


def test_reacquisition_is_neutral_even_when_pose_is_open():
    tracker = _pinched()
    result = tracker.update(_obs(HandPose.OPEN, 1.125), tracking_status=TrackingStatus.REACQUIRED)
    assert R.REACQUISITION in result.reasons and result.reset_occurred
    assert result.stable_pose is HandPose.UNKNOWN and not result.armed
    assert result.rearm_since_s is None
    assert not _update(tracker, HandPose.OPEN, 1.25).armed
    assert _update(tracker, HandPose.OPEN, 1.375).armed


def test_valid_return_after_loss_is_also_reacquisition_neutral():
    tracker = _pinched()
    tracker.update(_obs(HandPose.PINCH, 1.125), tracking_status=TrackingStatus.NO_HAND)
    returned = _update(tracker, HandPose.OPEN, 1.25)
    assert returned.reset_occurred and R.REACQUISITION in returned.reasons
    assert not returned.armed and returned.rearm_since_s is None
    assert not _update(tracker, HandPose.OPEN, 1.375).armed
    assert _update(tracker, HandPose.OPEN, 1.5).armed


def test_rearm_requires_continuous_valid_released_evidence():
    tracker = TemporalPoseTracker(_config())
    _update(tracker, HandPose.OPEN, 0.)
    _update(tracker, HandPose.OPEN, .125)
    pinch = _update(tracker, HandPose.PINCH, .25)
    assert pinch.rearm_since_s is None and not pinch.armed
    _update(tracker, HandPose.OPEN, .375)
    assert _update(tracker, HandPose.OPEN, .5).armed


@pytest.mark.parametrize("timestamp", [.625, .5])
def test_duplicate_and_out_of_order_timestamps_reset_safely(timestamp):
    tracker = _ready()
    result = tracker.update(_obs(HandPose.OPEN, timestamp, frame_id=1000),
                            tracking_status=TrackingStatus.VALID)
    assert result.reset_occurred and R.TIMESTAMP_DISCONTINUITY in result.reasons
    assert not result.armed and result.stable_pose is HandPose.UNKNOWN


@pytest.mark.parametrize("timestamp", [math.nan, math.inf, -math.inf])
def test_nonfinite_timestamp_is_explicit_unavailable_and_neutral(timestamp):
    tracker = _ready()
    observation = _obs(HandPose.OPEN, .75)
    geometry = replace(observation.frame_geometry)
    # FrameGeometry normally rejects this. Defensive corrupted fixture only.
    object.__setattr__(geometry, "timestamp_s", timestamp)
    result = tracker.update(replace(observation, frame_geometry=geometry),
                            tracking_status=TrackingStatus.VALID)
    assert R.TIMESTAMP_DISCONTINUITY in result.reasons
    assert result.timestamp_s is None and not result.action_allowed


def test_frame_identity_discontinuity_also_resets():
    tracker = _ready()
    result = tracker.update(_obs(HandPose.OPEN, .75, frame_id=1),
                            tracking_status=TrackingStatus.VALID)
    assert R.FRAME_DISCONTINUITY in result.reasons
    assert result.reset_occurred and not result.action_allowed


@pytest.mark.parametrize("gap,resets", [(2., False), (2.001, True)])
def test_timestamp_gap_is_strictly_greater_than_configured_limit(gap, resets):
    tracker = _ready()
    result = _update(tracker, HandPose.OPEN, .625 + gap)
    assert result.reset_occurred is resets
    assert (R.TIMESTAMP_GAP in result.reasons) is resets
    assert result.action_allowed is not resets


def test_run_change_cannot_carry_dwell_or_stable_pose():
    tracker = _pinched()
    result = _update(tracker, HandPose.PINCH, 0., run="next")
    assert result.reset_occurred and R.RUN_CHANGE in result.reasons
    assert result.stable_pose is HandPose.UNKNOWN and not result.pinch_latched
    assert result.pending_pose is None and result.transition_id == 3


def test_filter_reset_is_neutral_and_resets_pending_reference():
    tracker = _ready()
    _update(tracker, HandPose.PINCH, .75)
    result = tracker.update(_obs(HandPose.PINCH, 1.), tracking_status=TrackingStatus.VALID,
                            filter_reset=True)
    assert result.reset_occurred and R.FILTER_RESET in result.reasons
    assert result.pending_pose is None and not result.armed


def test_explicit_reset_returns_immediate_release_and_preserves_counters():
    tracker = _pinched()
    reset = tracker.reset()
    assert reset.stable_pose is HandPose.UNKNOWN and not reset.action_allowed
    assert R.EXPLICIT_RESET in reset.reasons and R.SAFE_RELEASE in reset.reasons
    assert reset.transition_id == 3 and reset.reset_id == 2
    next_ = _update(tracker, HandPose.PINCH, 0.)
    assert next_.transition_id == 3 and next_.reset_id == 3
    assert next_.reset_occurred and not next_.armed


def test_invalid_geometry_overrides_pinch_latch():
    tracker = _pinched()
    result = _update(tracker, HandPose.UNKNOWN, 1.125, invalid=True)
    assert R.INVALID_OBSERVATION in result.reasons
    assert not result.pinch_latched and not result.action_allowed


def test_conflicting_pinch_flags_cannot_retain_a_latch():
    tracker = _pinched()
    observation = _obs(HandPose.UNKNOWN, 1.125, band=True)
    observation = replace(observation, pinch=replace(observation.pinch, enter=True))
    result = tracker.update(observation, tracking_status=TrackingStatus.VALID)
    assert R.INVALID_OBSERVATION in result.reasons and not result.pinch_latched


def test_generic_unknown_with_band_flags_is_not_the_a3_band_exception():
    tracker = _pinched()
    observation = replace(_obs(HandPose.UNKNOWN, 1.125, band=True),
                           reasons=(ClassificationReason.FINGER_UNKNOWN,))
    result = tracker.update(observation, tracking_status=TrackingStatus.VALID)
    assert R.UNKNOWN_INPUT in result.reasons and not result.pinch_latched


def test_replay_and_input_immutability():
    source = [(_obs(HandPose.OPEN, t), TrackingStatus.VALID) for t in (0., .125, .25, .375, .5)]
    source += [(_obs(HandPose.PINCH, .75), TrackingStatus.VALID),
               (_obs(HandPose.PINCH, 1.), TrackingStatus.VALID),
               (_obs(HandPose.UNKNOWN, 1.125, band=True), TrackingStatus.VALID),
               (_obs(HandPose.POINT, 1.25), TrackingStatus.VALID),
               (_obs(HandPose.PINCH, 1.375), TrackingStatus.NO_HAND)]
    before = repr(source)
    def replay():
        tracker = TemporalPoseTracker(_config())
        return tuple(tracker.update(o, tracking_status=s) for o, s in source)
    first = replay()
    assert replay() == first and repr(source) == before
    with pytest.raises(FrozenInstanceError):
        first[-1].action_allowed = True
    assert [s.transition_id for s in first] == sorted(s.transition_id for s in first)


@pytest.mark.parametrize("field", ["enter_dwell_s", "exit_dwell_s", "pinch_enter_dwell_s",
                                   "pinch_exit_dwell_s", "rearm_dwell_s", "reset_gap_s"])
@pytest.mark.parametrize("value", [-1., math.nan, math.inf, True])
def test_invalid_timing_configuration_rejected(field, value):
    with pytest.raises(ValueError):
        _config(**{field: value})


def test_zero_reset_gap_rejected():
    with pytest.raises(ValueError):
        _config(reset_gap_s=0.)


def test_untyped_tracking_metadata_fails_safe():
    tracker = _pinched()
    state = tracker.update(_obs(HandPose.PINCH, 1.125), tracking_status="VALID")
    assert R.TRACKING_LOSS in state.reasons and not state.action_allowed


def test_snapshot_contract_cannot_enable_actions_on_unknown_band():
    tracker = _pinched()
    state = _update(tracker, HandPose.UNKNOWN, 1.125, band=True)
    with pytest.raises(ValueError):
        replace(state, action_allowed=True)
    with pytest.raises(TypeError):
        replace(state, reasons=list(state.reasons))


def test_unknown_with_definite_release_geometry_can_complete_rearm_dwell():
    tracker = TemporalPoseTracker(_config())
    _update(tracker, HandPose.OPEN, 0.)
    _update(tracker, HandPose.OPEN, .125)
    released = _update(tracker, HandPose.UNKNOWN, .25)
    assert released.armed and not released.action_allowed
    assert R.REARMED in released.reasons
    state = _update(tracker, HandPose.OPEN, .375)
    assert state.armed and state.candidate_since_s == .375 and not state.action_allowed


@pytest.mark.parametrize("distance", [.2, .3, .35])
def test_band_does_not_rearm_or_bridge_release_dwell_even_at_equalities(distance):
    tracker = TemporalPoseTracker(_config())
    _update(tracker, HandPose.PINCH, 0.)
    _update(tracker, HandPose.OPEN, .125)
    for t in (.25, .5, .75):
        obs = _obs(HandPose.UNKNOWN, t, band=True)
        obs = replace(obs, pinch=replace(obs.pinch, distance_palm=distance))
        state = tracker.update(obs, tracking_status=TrackingStatus.VALID)
        assert not state.armed and not state.action_allowed
        assert state.rearm_since_s is None and R.PINCH_BAND_WAIT in state.reasons
    assert not _update(tracker, HandPose.PINCH, .875).armed
    first = _update(tracker, HandPose.OPEN, 1.)
    assert first.rearm_since_s == 1. and not first.armed
    assert _update(tracker, HandPose.OPEN, 1.125).armed


def test_return_to_pinch_cancels_release_dwell_without_band_counting_as_release():
    tracker = _pinched()
    _update(tracker, HandPose.OPEN, 1.125)
    returned = _update(tracker, HandPose.PINCH, 1.25)
    assert returned.pending_pose is None and returned.pinch_latched
    assert R.CANDIDATE_CANCELLED in returned.reasons
    band = _update(tracker, HandPose.UNKNOWN, 1.375, band=True)
    assert not band.action_allowed
    first = _update(tracker, HandPose.OPEN, 1.5)
    assert first.candidate_since_s == 1.5 and not first.action_allowed
    assert not _update(tracker, HandPose.OPEN, 1.75).action_allowed
    assert _update(tracker, HandPose.OPEN, 1.875).stable_pose is HandPose.OPEN


@pytest.mark.parametrize("status", [TrackingStatus.NO_HAND, TrackingStatus.INVALID,
                                   TrackingStatus.REACQUIRED])
def test_loss_or_reacquisition_overrides_earned_band_arm(status):
    tracker = _ready()
    assert _update(tracker, HandPose.UNKNOWN, .75, band=True).armed
    state = tracker.update(_obs(HandPose.UNKNOWN, .875, band=True), tracking_status=status)
    assert not state.armed and state.stable_pose is HandPose.UNKNOWN
    returned = _update(tracker, HandPose.UNKNOWN, 1., band=True)
    assert not returned.armed and not returned.action_allowed
    assert not _update(tracker, HandPose.PINCH, 1.125).armed


def test_a2_a3_a4_sequence_preserves_real_classifier_band_semantics():
    from dip_touchless.core import (
        CoordinateSpace, FilterDiagnostics, FilterMode, Landmark,
        MeasurementQuality, StageTimings, TrackingFrame,
    )
    from extensions.stem3d.full_hand import (
        FingerThresholds, PoseThresholds, ThumbThresholds,
        classify_pose, extract_hand_geometry,
    )
    points = (
        (.50, .80), (.40, .68), (.32, .61), (.25, .53), (.20, .48),
        (.40, .55), (.40, .42), (.40, .31), (.40, .20),
        (.50, .50), (.50, .35), (.50, .23), (.50, .11),
        (.60, .54), (.61, .40), (.62, .29), (.63, .19),
        (.68, .61), (.71, .50), (.73, .41), (.75, .33),
    )
    chain = FingerThresholds(2.6, 1.5, .9, .65)
    thresholds = PoseThresholds(chain, ThumbThresholds(chain, .5, .65, 2.), .2, .35)
    def observation(t, distance=None):
        geometry = FrameGeometry("a2-a3-a4", int(t * 1000), t, 1600, 900)
        current = list(points)
        if distance is not None:
            width = math.hypot(.28, .06)
            current[4] = (current[8][0] - distance * width, current[8][1])
        landmarks = tuple(Landmark(i, .5 + (x - .5) / (1600 / 900), y,
                                    -.01 * i, CoordinateSpace.FRAME_NORMALIZED)
                          for i, (x, y) in enumerate(current))
        frame = TrackingFrame(
            geometry.run_id, geometry.frame_id, t, TrackingStatus.VALID, (), landmarks,
            MeasurementQuality.unavailable(), None, None,
            FilterDiagnostics(FilterMode.RAW, None, None, None, None, None,
                              None, None, False), StageTimings(0., 0., 0., 0., 0.), (),
        )
        return classify_pose(extract_hand_geometry(frame, geometry), thresholds)
    tracker = TemporalPoseTracker(_config())
    for t in (0., .125, .25, .375, .5, .625):
        state = tracker.update(observation(t), tracking_status=TrackingStatus.VALID)
    assert state.stable_pose is HandPose.OPEN
    for t in (.75, 1.):
        state = tracker.update(observation(t, .1), tracking_status=TrackingStatus.VALID)
    assert state.pinch_latched and state.action_allowed
    band = observation(1.125, .3)
    assert band.pose is HandPose.UNKNOWN
    assert band.reasons == (ClassificationReason.PINCH_BOUNDARY_BAND,)
    state = tracker.update(band, tracking_status=TrackingStatus.VALID)
    assert state.pinch_latched and not state.action_allowed

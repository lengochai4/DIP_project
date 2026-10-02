"""Synthetic A5.6 foundation; fixture parameters are NOT physical calibration."""

from dataclasses import FrozenInstanceError, replace
import math

import pytest

from dip_touchless.core import TrackingStatus
from extensions.stem3d.full_hand import GeometryReason, extract_hand_geometry
from extensions.stem3d.full_hand.intent_pinch_contracts import (
    ConfirmedReleaseWindow, IntentPinchReason as Reason, IntentPredicateDiagnostic,
    ProjectionCompatibility as Compatibility, ReferenceEvent, ReferenceScope,
    ReferenceStatus, ReleaseReferencePolicy, ReleaseSample,
    RelativeClosureThresholds, RelativeClosureZone as Zone,
)
from extensions.stem3d.full_hand.pinch_reference import build_release_reference, invalidate_reference
from extensions.stem3d.full_hand.relative_closure import evaluate_relative_closure
from test_geometry import _fixture


def _scope():
    return ReferenceScope("synthetic-session", "synthetic-a2", "synthetic-camera",
                          "synthetic-provider", "fixture-only", "frame-xy", "epoch-0")


def _policy():
    # Explicit mathematical test policy, not a profile for physical use.
    return ReleaseReferencePolicy(3, .5, .3, .02, .05, 1.1, 2.)


def _hand(distance=1., frame_id=10, timestamp_s=1., **fixture):
    frame, geometry = _fixture(**fixture)
    geometry = replace(geometry, frame_id=frame_id, timestamp_s=timestamp_s)
    frame = replace(frame, frame_id=frame_id, timestamp_s=timestamp_s)
    hand = extract_hand_geometry(frame, geometry)
    # Scalar injection isolates exact arithmetic boundaries. Similarity tests
    # below use real 21-landmark extraction without injection.
    return replace(hand, thumb_index_distance_palm=distance)


def _window(distances=(1., 1.01, .99)):
    samples = tuple(ReleaseSample(_hand(d, i, i * .25), TrackingStatus.VALID, False)
                    for i, d in enumerate(distances))
    return ConfirmedReleaseWindow(_scope(), samples, True, "operator-window-1", Compatibility.CONFIRMED)


def _build(window=None, policy=None):
    return build_release_reference(window or _window(), policy or _policy(),
                                   reference_id="synthetic-ref", version=1)


def _evaluate(hand, reference, **changes):
    args = dict(scope=_scope(), tracking_status=TrackingStatus.VALID,
                filter_reset_occurred=False, projection_compatibility=Compatibility.CONFIRMED)
    args.update(changes)
    return evaluate_relative_closure(hand, reference, RelativeClosureThresholds(.5, .25), **args)


def test_confirmed_reference_records_median_noise_and_provenance():
    window, policy = _window(), _policy()
    result = _build(window, policy)
    assert result.valid and not result.reasons and not result.geometry_reasons
    ref = result.reference
    assert ref.valid and ref.scope == window.scope and ref.distance_palm == 1.
    assert ref.mad_distance_palm == pytest.approx(.01)
    assert ref.max_deviation_distance_palm == pytest.approx(.01)
    assert ref.noise_allowance_relative == pytest.approx(.02)
    assert ref.source_frames == tuple(s.geometry.frame_geometry for s in window.samples)
    assert ref.policy is policy and ref.confirmation_id == window.confirmation_id
    assert all(p.passed for p in result.predicates)


def test_even_window_median_is_robust_and_overflow_safe():
    assert _build(_window((1., 1.02, .98, 1.01))).reference.distance_palm == pytest.approx(1.005)
    result = _build(_window((1e308,) * 4))
    assert result.valid and result.reference.distance_palm == 1e308


def test_first_hand_or_large_separation_is_not_release_confirmation():
    result = _build(replace(_window((10.,) * 3), comfortable_apart_confirmed=False))
    assert not result.valid and result.reference is None
    assert Reason.RELEASE_NOT_CONFIRMED in result.reasons


@pytest.mark.parametrize("count", [0, 1, 2])
def test_insufficient_window_does_not_guess_a_reference(count):
    result = _build(_window((1.,) * count))
    assert result.reference is None and Reason.INSUFFICIENT_SAMPLES in result.reasons


def test_short_release_window_is_rejected():
    window = _window()
    samples = tuple(replace(s, geometry=replace(s.geometry, frame_geometry=replace(
        s.geometry.frame_geometry, timestamp_s=i * .1))) for i, s in enumerate(window.samples))
    assert Reason.INSUFFICIENT_DURATION in _build(replace(window, samples=samples)).reasons


def test_extreme_timestamp_span_is_explicit_numerical_failure():
    window = _window()
    samples = tuple(replace(s, geometry=replace(s.geometry, frame_geometry=replace(
        s.geometry.frame_geometry, timestamp_s=t)))
        for s, t in zip(window.samples, (-1e308, 0., 1e308)))
    result = _build(replace(window, samples=samples))
    assert result.reference is None and Reason.NUMERICAL_FAILURE in result.reasons


def test_builder_does_not_mutate_or_trim_rejected_window():
    window, policy = _window((1., 1., 1.2)), _policy()
    before = repr((window, policy))
    first, second = _build(window, policy), _build(window, policy)
    assert not first.valid and first == second
    assert repr((window, policy)) == before


@pytest.mark.parametrize("kind", ["duplicate_frame", "reverse_frame", "duplicate_time", "reverse_time", "gap"])
def test_discontinuous_window_is_not_trimmed_or_reordered(kind):
    window = _window()
    sample = window.samples[1]
    changes = {
        "duplicate_frame": dict(frame_id=0), "reverse_frame": dict(frame_id=3),
        "duplicate_time": dict(timestamp_s=0.), "reverse_time": dict(timestamp_s=-.1),
        "gap": dict(timestamp_s=2.),
    }[kind]
    sample = replace(sample, geometry=replace(sample.geometry,
                       frame_geometry=replace(sample.geometry.frame_geometry, **changes)))
    result = _build(replace(window, samples=(window.samples[0], sample, window.samples[2])))
    assert not result.valid and Reason.DISCONTINUOUS_WINDOW in result.reasons


@pytest.mark.parametrize("distances", [(1., .8, 1.2), (1., 1., 1.2)])
def test_noisy_window_including_single_outlier_is_rejected(distances):
    assert Reason.NOISY_WINDOW in _build(_window(distances)).reasons


def test_enrollment_bounds_are_inclusive():
    policy = replace(_policy(), max_relative_mad=.125, max_relative_deviation=.125)
    result = _build(_window((.875, 1., 1.125)), policy)
    assert result.valid and result.reference.noise_allowance_relative == .25


def test_noise_cannot_consume_reference_span():
    policy = replace(_policy(), max_relative_mad=1., max_relative_deviation=1., noise_multiplier=4.)
    assert Reason.NOISE_EXCEEDS_REFERENCE in _build(_window((.75, 1., 1.25)), policy).reasons


@pytest.mark.parametrize("distance", [0., -1.])
def test_degenerate_release_distance_is_not_repaired(distance):
    assert Reason.DEGENERATE_DISTANCE in _build(_window((distance,) * 3)).reasons


def test_unstable_palm_denominator_rejects_enrollment():
    window = _window()
    sample = window.samples[1]
    palm = replace(sample.geometry.palm, width_image_height=sample.geometry.palm.width_image_height * 1.2)
    changed = replace(sample, geometry=replace(sample.geometry, palm=palm))
    assert Reason.PALM_WIDTH_UNSTABLE in _build(replace(window, samples=(
        window.samples[0], changed, window.samples[2]))).reasons


@pytest.mark.parametrize("status", [TrackingStatus.REACQUIRED, TrackingStatus.NO_HAND,
                                    TrackingStatus.TEMPORARY_LOSS, TrackingStatus.INVALID])
def test_enrollment_requires_ordinary_valid_samples(status):
    window = _window()
    result = _build(replace(window, samples=(
        replace(window.samples[0], tracking_status=status), *window.samples[1:])))
    assert not result.valid
    assert (Reason.REACQUISITION if status is TrackingStatus.REACQUIRED else Reason.TRACKING_UNUSABLE) in result.reasons


def test_filter_reset_inside_window_rejects_enrollment():
    window = _window()
    assert Reason.FILTER_RESET in _build(replace(window, samples=(
        replace(window.samples[0], filter_reset_occurred=True), *window.samples[1:]))).reasons


@pytest.mark.parametrize("compatibility", [Compatibility.UNCONFIRMED, Compatibility.INCOMPATIBLE])
def test_projection_comparison_must_be_explicitly_confirmed(compatibility):
    assert not _build(replace(_window(), projection_compatibility=compatibility)).valid
    observation = _evaluate(_hand(), _build().reference, projection_compatibility=compatibility)
    assert observation.zone is Zone.UNKNOWN and not observation.reference.valid


def test_geometry_failure_rejects_entire_window_with_a2_reasons():
    window = _window()
    geometry = replace(window.samples[0].geometry, valid=False, reasons=(GeometryReason.DEGENERATE_FINGER,))
    result = _build(replace(window, samples=(replace(window.samples[0], geometry=geometry), *window.samples[1:])))
    assert Reason.INVALID_GEOMETRY in result.reasons
    assert result.geometry_reasons == (GeometryReason.DEGENERATE_FINGER,)


def test_wrong_run_inside_window_is_rejected():
    window = _window()
    sample = window.samples[0]
    changed = replace(sample, geometry=replace(sample.geometry,
        frame_geometry=replace(sample.geometry.frame_geometry, run_id="different-run")))
    assert Reason.SCOPE_MISMATCH in _build(replace(window, samples=(changed, *window.samples[1:]))).reasons


@pytest.mark.parametrize("distance,closure,zone", [
    (1.25, -.25, Zone.RELEASED), (1., 0., Zone.RELEASED),
    (.875, .125, Zone.RELEASED), (.75, .25, Zone.BAND),
    (.625, .375, Zone.BAND), (.5, .5, Zone.BAND), (.25, .75, Zone.ENTRY), (0., 1., Zone.ENTRY),
])
def test_relative_formula_and_strict_boundaries(distance, closure, zone):
    ref = _build(_window((1.,) * 3)).reference
    result = _evaluate(_hand(distance), ref)
    assert result.valid and result.zone is zone and result.relative_closure == closure
    assert result.released is (closure < .25)
    assert result.band is (.25 <= closure <= .5)
    assert result.closing is (closure > 0.) and result.entry is (closure > .5)
    assert result.reference is ref
    assert result.tip_distance_image_height == pytest.approx(distance * result.palm_width_image_height)


@pytest.mark.parametrize("boundary", [.25, .5])
def test_threshold_floating_point_neighbors(boundary):
    ref = _build(_window((1.,) * 3)).reference
    for d in (math.nextafter(1 - boundary, 0.), 1 - boundary, math.nextafter(1 - boundary, math.inf)):
        result = _evaluate(_hand(d), ref)
        c = (1. - d) / 1.
        assert result.released == (c < .25)
        assert result.band == (.25 <= c <= .5)
        assert result.entry == (c > .5)


def test_closing_is_noise_separated_extent_not_temporal_state():
    ref = _build(_window((.875, 1., 1.125)), replace(
        _policy(), max_relative_mad=.125, max_relative_deviation=.125)).reference
    assert ref.noise_allowance_relative == .25
    at_noise = _evaluate(_hand(.75), ref)
    assert at_noise.band and not at_noise.closing and not at_noise.entry
    assert _evaluate(_hand(.625), ref).closing
    # Geometry ENTRY zone can fail the independent noise predicate.
    very_noisy = replace(ref, noise_allowance_relative=.75)
    extent = _evaluate(_hand(.375), very_noisy)
    assert extent.zone is Zone.ENTRY and not extent.entry


def test_missing_reference_is_unknown_without_commands():
    result = _evaluate(_hand(.1), None)
    assert Reason.NO_REFERENCE in result.reasons and result.zone is Zone.UNKNOWN
    assert result.relative_closure is None
    assert all(getattr(result, name) is None for name in ("released", "closing", "band", "entry"))
    assert all(p.passed is None for p in result.predicates if p.name in ("released", "closing", "band", "entry"))


@pytest.mark.parametrize("event", list(ReferenceEvent))
def test_every_lifecycle_event_neutralizes_without_rearming(event):
    ref = _build().reference
    invalidated = invalidate_reference(ref, event)
    assert ref.valid and not invalidated.valid and invalidated.distance_palm == ref.distance_palm
    assert invalidated.source_frames is ref.source_frames and invalidated.invalidation_events == (event,)
    assert invalidate_reference(invalidated, event) == invalidated
    observation = _evaluate(_hand(.1), ref, event=event)
    assert observation.zone is Zone.UNKNOWN and observation.entry is None and not observation.reference.valid
    later = _evaluate(_hand(1., 11, 1.25), observation.reference)
    assert later.zone is Zone.UNKNOWN and later.released is None


def test_loss_reacquisition_retains_unverified_metadata_reset_never_downgrades():
    ref = _build().reference
    loss = _evaluate(_hand(.1), ref, tracking_status=TrackingStatus.TEMPORARY_LOSS)
    assert loss.reference.status is ReferenceStatus.UNVERIFIED
    reacquired = _evaluate(_hand(.1, 11, 1.25), loss.reference, tracking_status=TrackingStatus.REACQUIRED)
    assert reacquired.zone is Zone.UNKNOWN and not reacquired.reference.valid
    reset = invalidate_reference(reacquired.reference, ReferenceEvent.EXPLICIT_RESET)
    assert invalidate_reference(reset, ReferenceEvent.TRACKING_LOSS).status is ReferenceStatus.INVALIDATED
    assert invalidate_reference(None, ReferenceEvent.EXPLICIT_RESET) is None


@pytest.mark.parametrize("field", ["session_id", "run_id", "camera_id", "provider_id", "profile_id",
                                 "coordinate_domain_id", "reset_id"])
def test_scope_changes_invalidate_reference(field):
    result = _evaluate(_hand(), _build().reference, scope=replace(_scope(), **{field: "changed"}))
    assert Reason.SCOPE_MISMATCH in result.reasons and not result.reference.valid


@pytest.mark.parametrize("change", [dict(frame_id=2), dict(timestamp_s=.5)])
def test_pre_enrollment_or_duplicate_identity_is_neutral(change):
    hand = _hand()
    hand = replace(hand, frame_geometry=replace(hand.frame_geometry, **change))
    result = _evaluate(hand, _build().reference)
    assert Reason.PRE_ENROLLMENT_FRAME in result.reasons
    assert result.reference.invalidation_events == (ReferenceEvent.TIMESTAMP_DISCONTINUITY,)


def test_invalid_geometry_with_retained_palm_cannot_produce_evidence():
    hand = replace(_hand(.1), valid=False, reasons=(GeometryReason.DEGENERATE_FINGER,))
    result = _evaluate(hand, _build().reference)
    assert result.geometry_reasons == hand.reasons and result.entry is None
    assert result.relative_closure is None and not result.reference.valid


def test_real_tracking_loss_keeps_missing_values_missing():
    frame, geometry = _fixture()
    hand = extract_hand_geometry(replace(frame, status=TrackingStatus.NO_HAND, filtered_landmarks=()), geometry)
    result = _evaluate(hand, _build().reference, tracking_status=TrackingStatus.NO_HAND)
    assert not result.valid and result.distance_palm is None and result.palm_width_image_height is None
    assert result.tip_distance_image_height is None and result.entry is None


@pytest.mark.parametrize("angle", [0., .7, -1.2, math.pi / 2])
@pytest.mark.parametrize("scale", [.4, 1., 2.])
@pytest.mark.parametrize("mirror", [False, True])
def test_actual_a2_similarity_does_not_imply_closure(angle, scale, mirror):
    def transform(x, y):
        x, y = x - .5, y - .5
        if mirror:
            x = -x
        return (.6 + scale * (x * math.cos(angle) - y * math.sin(angle)),
                .4 + scale * (x * math.sin(angle) + y * math.cos(angle)))
    samples = []
    for i in range(3):
        frame, fg = _fixture()
        fg = replace(fg, frame_id=i, timestamp_s=i * .25)
        frame = replace(frame, frame_id=i, timestamp_s=i * .25)
        samples.append(ReleaseSample(extract_hand_geometry(frame, fg), TrackingStatus.VALID, False))
    ref = _build(replace(_window(), samples=tuple(samples))).reference
    frame, fg = _fixture(transform=transform)
    fg = replace(fg, frame_id=10, timestamp_s=1.)
    current = extract_hand_geometry(replace(frame, frame_id=10, timestamp_s=1.), fg)
    result = _evaluate(current, ref)
    assert result.valid and result.released and not result.entry
    assert result.relative_closure == pytest.approx(0., abs=1e-14)
    assert result.distance_palm == pytest.approx(ref.distance_palm)
    assert result.palm_width_image_height == pytest.approx(ref.palm_width_median * scale)


@pytest.mark.parametrize("dimensions", [(900, 900), (1920, 1080), (900, 1600)])
def test_aspect_corrected_same_shape_keeps_relative_metric(dimensions):
    frame, fg = _fixture()
    ref_distance = extract_hand_geometry(frame, fg).thumb_index_distance_palm
    ref = _build(_window((ref_distance,) * 3)).reference
    frame, fg = _fixture(*dimensions)
    fg = replace(fg, frame_id=10, timestamp_s=1.)
    hand = extract_hand_geometry(replace(frame, frame_id=10, timestamp_s=1.), fg)
    result = _evaluate(hand, ref)
    assert result.valid and result.relative_closure == pytest.approx(0., abs=1e-14)
    assert result.frame_geometry.width == dimensions[0]


def test_reference_does_not_drift_through_release_close_hold_and_wider_open():
    ref = _build().reference
    before = repr(ref)
    for i, d in enumerate((1., .8, .5, .2, .2, .75, 1.2, 1.)):
        result = _evaluate(_hand(d, 10 + i, 1. + i * .1), ref)
        assert result.reference is ref and repr(ref) == before
    assert _build().reference == ref


def test_nested_inputs_and_outputs_are_immutable_and_repeatable():
    window, policy = _window(), _policy()
    ref = _build(window, policy).reference
    hand = _hand(.2)
    before = repr((window, policy, ref, hand))
    results = tuple(_evaluate(hand, ref) for _ in range(20))
    assert all(r == results[0] for r in results) and repr((window, policy, ref, hand)) == before
    for obj, field, value in (
        (ref, "distance_palm", .01), (ref.scope, "run_id", "new"),
        (window, "comfortable_apart_confirmed", False), (policy, "min_samples", 0),
        (results[0], "entry", True), (results[0].predicates[0], "passed", True),
    ):
        with pytest.raises(FrozenInstanceError):
            setattr(obj, field, value)
    with pytest.raises(TypeError):
        ref.source_frames[0] = hand.frame_geometry


@pytest.mark.parametrize("enter,exit", [(0., 0.), (.5, .5), (.25, .5), (1., .25),
                                      (.5, 0.), (math.nan, .25), (.5, math.inf), (True, .25)])
def test_thresholds_require_explicit_finite_relative_bounds(enter, exit):
    with pytest.raises(ValueError):
        RelativeClosureThresholds(enter, exit)


def test_no_defaults_or_mutable_contract_collections():
    with pytest.raises(TypeError):
        RelativeClosureThresholds()
    with pytest.raises(TypeError):
        ReleaseReferencePolicy()
    with pytest.raises(TypeError):
        replace(_window(), samples=list(_window().samples))
    with pytest.raises(TypeError):
        replace(_build().reference, source_frames=list(_build().reference.source_frames))
    with pytest.raises(TypeError):
        IntentPredicateDiagnostic("closing", 1, "bad bool")


@pytest.mark.parametrize("change", [dict(min_samples=1), dict(min_samples=True),
    dict(min_duration_s=0.), dict(max_sample_gap_s=-1.), dict(max_relative_mad=-.1),
    dict(max_relative_mad=.1), dict(max_palm_width_ratio=.5), dict(noise_multiplier=.5),
    dict(noise_multiplier=math.inf)])
def test_invalid_reference_policy_rejected(change):
    with pytest.raises(ValueError):
        replace(_policy(), **change)


def test_explicit_new_enrollment_after_reset_uses_new_identity():
    ref = _build().reference
    reset = invalidate_reference(ref, ReferenceEvent.EXPLICIT_RESET)
    result = build_release_reference(_window((1.5,) * 3), _policy(), reference_id="new-ref", version=2)
    assert result.valid and reset.status is ReferenceStatus.INVALIDATED
    assert result.reference.version == 2 and result.reference.distance_palm == 1.5
    assert reset.distance_palm == 1. and not reset.valid


@pytest.mark.parametrize("kind", ["nonfinite", "negative", "missing_palm", "overflow"])
def test_invalid_and_extreme_geometry_never_authorizes_evidence(kind):
    hand, ref = _hand(.1), _build().reference
    if kind == "nonfinite":
        object.__setattr__(hand, "thumb_index_distance_palm", math.nan)
    elif kind == "negative":
        hand = replace(hand, thumb_index_distance_palm=-1.)
    elif kind == "missing_palm":
        hand = replace(hand, palm=None)
    else:
        hand = replace(hand, thumb_index_distance_palm=1e308,
                       palm=replace(hand.palm, width_image_height=1e308))
    result = _evaluate(hand, ref)
    assert result.zone is Zone.UNKNOWN and result.relative_closure is None and result.entry is None
    assert not result.reference.valid


def test_relative_closure_overflow_is_reported_without_clamping():
    ref = _build(_window((1e-300,) * 3)).reference
    result = _evaluate(_hand(1e100), ref)
    assert Reason.NUMERICAL_FAILURE in result.reasons
    assert result.relative_closure is None and result.zone is Zone.UNKNOWN
    assert not result.reference.valid


def test_filter_reset_flag_neutralizes_an_otherwise_valid_frame():
    result = _evaluate(_hand(.1), _build().reference, filter_reset_occurred=True)
    assert Reason.FILTER_RESET in result.reasons and result.entry is None
    assert result.reference.status is ReferenceStatus.INVALIDATED


@pytest.mark.parametrize("have_reference", [False, True])
def test_legacy_interaction_field_parity_during_pure_foundation_evaluation(have_reference):
    from dataclasses import asdict
    from dip_touchless.configuration import resolve_config
    from extensions.stem3d.live_demo import _build_gesture_engine, DEFAULT_CONFIG

    cfg = resolve_config(DEFAULT_CONFIG).to_dict()
    baseline = _build_gesture_engine(cfg["gesture"])
    compared = _build_gesture_engine(cfg["gesture"])
    ref = _build().reference if have_reference else None
    # No runtime hook: call pure math between updates of two independent engines.
    for i in range(16):
        frame, fg = _fixture(transform=lambda x, y: (x + i * .01, y))
        fg = replace(fg, frame_id=10 + i, timestamp_s=1. + i * .125)
        status = TrackingStatus.TEMPORARY_LOSS if i == 10 else TrackingStatus.REACQUIRED if i == 11 else TrackingStatus.VALID
        landmarks = frame.filtered_landmarks
        if i in (4, 5, 6, 11):
            landmarks = tuple(replace(p, x=landmarks[8].x, y=landmarks[8].y)
                              if p.index == 4 else p for p in landmarks)
        frame = replace(frame, frame_id=fg.frame_id, timestamp_s=fg.timestamp_s,
                        status=status, filtered_landmarks=landmarks if i != 10 else ())
        before = repr(frame)
        expected = baseline.update(frame)
        geometry = extract_hand_geometry(frame, fg)
        observation = _evaluate(geometry, ref, tracking_status=status)
        ref = observation.reference
        assert repr(frame) == before
        assert asdict(compared.update(frame)) == asdict(expected)

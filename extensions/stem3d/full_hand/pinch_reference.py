"""Pure confirmed-window enrollment and explicit immutable invalidation.

No automatic enrollment, update/adaptation, persistence, or revalidation. Loss
can retain UNVERIFIED metadata; only a newly confirmed window builds an active
reference in this foundation. Callers must thread invalidated results forward.
"""

from dataclasses import replace
import math

from dip_touchless.core import TrackingStatus

from .intent_pinch_contracts import (
    ConfirmedReleaseWindow, IntentPinchReason as Reason, IntentPredicateDiagnostic,
    ProjectionCompatibility, ReferenceBuildResult, ReferenceEvent,
    ReferenceStatus, ReleaseReference, ReleaseReferencePolicy,
)


def _positive_median(values):
    """Avoid (a+b)/2 overflow for finite nonnegative observations."""
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    lo, hi = ordered[middle - 1:middle + 1]
    return lo + (hi - lo) / 2


def invalidate_reference(
    reference: ReleaseReference | None, event: ReferenceEvent,
) -> ReleaseReference | None:
    """Return a neutral copy, preserving frozen numbers/provenance, never rearm."""
    if not isinstance(event, ReferenceEvent):
        raise TypeError("invalidation needs an explicit ReferenceEvent")
    if reference is None:
        return None
    if not isinstance(reference, ReleaseReference):
        raise TypeError("reference must be ReleaseReference or None")
    status = ReferenceStatus.UNVERIFIED if event in (
        ReferenceEvent.TRACKING_LOSS, ReferenceEvent.REACQUISITION,
        ReferenceEvent.INVALID_GEOMETRY,
    ) else ReferenceStatus.INVALIDATED
    if reference.status is ReferenceStatus.INVALIDATED:
        status = ReferenceStatus.INVALIDATED
    events = tuple(dict.fromkeys((*reference.invalidation_events, event)))
    return replace(reference, status=status, invalidation_events=events)


def build_release_reference(
    window: ConfirmedReleaseWindow, policy: ReleaseReferencePolicy,
    *, reference_id: str, version: int,
) -> ReferenceBuildResult:
    """Median of ALL confirmed samples; reject bad samples, do not trim/guess.

    MAD = median(abs(distance - median)); maximum deviation additionally catches
    isolated outliers. Relative noise = multiplier * max_deviation / median.
    All acceptance parameters are explicit; no physical values chosen here.
    """
    if not isinstance(window, ConfirmedReleaseWindow) or not isinstance(policy, ReleaseReferencePolicy):
        raise TypeError("builder requires immutable confirmed window and policy")
    if not isinstance(reference_id, str) or not reference_id.strip():
        raise ValueError("reference_id must be nonempty")
    if type(version) is not int or version < 1:
        raise ValueError("version must be a positive integer")
    reasons, diagnostics = [], []

    def check(name, passed, reason, value=None, threshold=None):
        diagnostics.append(IntentPredicateDiagnostic(name, passed, reason.value, value, threshold))
        if not passed:
            reasons.append(reason)

    check("comfortable_apart_confirmed", window.comfortable_apart_confirmed,
          Reason.RELEASE_NOT_CONFIRMED)
    check("projection_comparable", window.projection_compatibility is ProjectionCompatibility.CONFIRMED,
          Reason.COMPARISON_INCOMPATIBLE if window.projection_compatibility is ProjectionCompatibility.INCOMPATIBLE
          else Reason.COMPARISON_UNCONFIRMED)
    check("sample_count", len(window.samples) >= policy.min_samples,
          Reason.INSUFFICIENT_SAMPLES, len(window.samples), policy.min_samples)
    geometry_reasons = tuple(dict.fromkeys(
        r for s in window.samples for r in s.geometry.reasons))
    for sample in window.samples:
        hand = sample.geometry
        check("geometry_valid", hand.valid and hand.palm is not None
              and hand.thumb_index_distance_palm is not None, Reason.INVALID_GEOMETRY)
        check("tracking_valid", sample.tracking_status is TrackingStatus.VALID,
              Reason.REACQUISITION if sample.tracking_status is TrackingStatus.REACQUIRED
              else Reason.TRACKING_UNUSABLE)
        check("filter_continuous", not sample.filter_reset_occurred, Reason.FILTER_RESET)
        check("run_scope", hand.frame_geometry.run_id == window.scope.run_id, Reason.SCOPE_MISMATCH)
    frames = tuple(s.geometry.frame_geometry for s in window.samples)
    if frames:
        duration = frames[-1].timestamp_s - frames[0].timestamp_s
        check("window_duration", math.isfinite(duration) and duration >= policy.min_duration_s,
              Reason.INSUFFICIENT_DURATION if math.isfinite(duration) else Reason.NUMERICAL_FAILURE,
              duration if math.isfinite(duration) else None, policy.min_duration_s)
        check("ordered_contiguous_window", all(
            a.frame_id < b.frame_id and 0 < b.timestamp_s - a.timestamp_s <= policy.max_sample_gap_s
            for a, b in zip(frames, frames[1:])), Reason.DISCONTINUOUS_WINDOW)
    if reasons:
        return ReferenceBuildResult(None, tuple(dict.fromkeys(reasons)), geometry_reasons, tuple(diagnostics))
    distances = tuple(s.geometry.thumb_index_distance_palm for s in window.samples)
    widths = tuple(s.geometry.palm.width_image_height for s in window.samples)
    check("positive_release_distance", all(math.isfinite(d) and d > 0 for d in distances),
          Reason.DEGENERATE_DISTANCE)
    check("positive_palm_width", all(math.isfinite(p) and p > 0 for p in widths),
          Reason.INVALID_GEOMETRY)
    if reasons:
        return ReferenceBuildResult(None, tuple(dict.fromkeys(reasons)), geometry_reasons, tuple(diagnostics))
    r = _positive_median(distances)
    deviations = tuple(abs(d - r) for d in distances)
    mad, maximum = _positive_median(deviations), max(deviations)
    relative_mad, relative_max = mad / r, maximum / r
    noise = relative_max * policy.noise_multiplier
    width_ratio = max(widths) / min(widths)
    check("relative_mad", relative_mad <= policy.max_relative_mad,
          Reason.NOISY_WINDOW, relative_mad if math.isfinite(relative_mad) else None,
          policy.max_relative_mad)
    check("relative_max_deviation", relative_max <= policy.max_relative_deviation,
          Reason.NOISY_WINDOW, relative_max if math.isfinite(relative_max) else None,
          policy.max_relative_deviation)
    check("palm_width_ratio", width_ratio <= policy.max_palm_width_ratio,
          Reason.PALM_WIDTH_UNSTABLE, width_ratio if math.isfinite(width_ratio) else None,
          policy.max_palm_width_ratio)
    check("span_above_noise", math.isfinite(noise) and noise < 1,
          Reason.NOISE_EXCEEDS_REFERENCE, noise if math.isfinite(noise) else None, 1.)
    if reasons:
        return ReferenceBuildResult(None, tuple(dict.fromkeys(reasons)), geometry_reasons, tuple(diagnostics))
    reference = ReleaseReference(
        reference_id, version, window.scope, window.confirmation_id, frames,
        r, mad, maximum, noise, _positive_median(widths), min(widths), max(widths), policy,
    )
    return ReferenceBuildResult(reference, (), (), tuple(diagnostics))

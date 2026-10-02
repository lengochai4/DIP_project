"""Explicit session enrollment, projection guard and observation-only lifecycle."""

from dataclasses import asdict, dataclass, replace
import hashlib
import json
import math
from pathlib import Path
from statistics import median

import yaml

from dip_touchless.core import TrackingStatus
from .contracts import FrameGeometry
from .intent_pinch_contracts import (
    ConfirmedReleaseWindow, ProjectionCompatibility as Compatibility,
    ReferenceEvent, ReferenceScope, ReferenceStatus, ReleaseReferencePolicy,
    ReleaseSample, RelativeClosureThresholds, ReleaseReference, RelativeClosureObservation,
)
from .intent_temporal import IntentTemporalConfig, IntentPinchSnapshot, TemporalIntentPinchTracker
from .pinch_reference import build_release_reference, invalidate_reference
from .relative_closure import evaluate_relative_closure


@dataclass(frozen=True, slots=True)
class IntentObserveProfile:
    reference: ReleaseReferencePolicy
    closure: RelativeClosureThresholds
    temporal: IntentTemporalConfig
    capture_duration_s: float
    max_palm_shape_delta: float
    max_palm_scale_ratio: float

    def __post_init__(self):
        for obj, kind in ((self.reference, ReleaseReferencePolicy),
                          (self.closure, RelativeClosureThresholds), (self.temporal, IntentTemporalConfig)):
            if not isinstance(obj, kind):
                raise TypeError("intent profile requires immutable configuration")
        values = (self.capture_duration_s, self.max_palm_shape_delta, self.max_palm_scale_ratio)
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
            raise ValueError("capture/projection policies must be finite")
        if self.capture_duration_s < self.reference.min_duration_s:
            raise ValueError("capture must cover the required release duration")
        if self.max_palm_shape_delta <= 0 or self.max_palm_scale_ratio < 1:
            raise ValueError("projection bounds must be positive, scale ratio >= 1")
        if self.closure.exit < self.temporal.min_relative_progress:
            raise ValueError("progress must not exceed release boundary")

    @property
    def sha256(self):
        canonical = json.dumps(asdict(self), sort_keys=True, allow_nan=False)
        return hashlib.sha256(canonical.encode()).hexdigest()


def load_intent_profile(path: Path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {
        "reference", "closure", "temporal", "capture_duration_s",
        "max_palm_shape_delta", "max_palm_scale_ratio",
    }:
        raise ValueError("intent observation profile has missing/unknown keys")
    return IntentObserveProfile(
        ReleaseReferencePolicy(**data["reference"]), RelativeClosureThresholds(**data["closure"]),
        IntentTemporalConfig(**data["temporal"]), data["capture_duration_s"],
        data["max_palm_shape_delta"], data["max_palm_scale_ratio"],
    )


def palm_signature(frame, hand):
    """10 projected palm distance ratios; no handedness/confidence/depth.

    This detects a changed projected domain, not identity or 3D orientation.
    Uniform scale/translation/in-plane rotation/reflection preserve these ratios.
    """
    if hand is None or not hand.valid or hand.palm is None:
        return None
    points = {p.index: p for p in frame.filtered_landmarks}
    indices = (0, 5, 9, 13, 17)
    if any(i not in points for i in indices):
        return None
    aspect = hand.frame_geometry.width / hand.frame_geometry.height
    width = hand.palm.width_image_height
    values = tuple(math.hypot((points[a].x - points[b].x) * aspect,
                              points[a].y - points[b].y) / width
                   for j, a in enumerate(indices) for b in indices[j + 1:])
    return values if all(math.isfinite(v) for v in values) else None


@dataclass(frozen=True, slots=True)
class IntentSessionSnapshot:
    frame_geometry: FrameGeometry
    calibration_status: str
    message: str
    calibration_version: int
    revalidation_id: int
    palm_shape_delta: float | None
    palm_scale_ratio: float | None
    enrollment_reasons: tuple[str, ...]
    reference: ReleaseReference | None
    observation: RelativeClosureObservation | None
    temporal: IntentPinchSnapshot

    def __post_init__(self):
        if not isinstance(self.frame_geometry, FrameGeometry) or not isinstance(self.temporal, IntentPinchSnapshot):
            raise TypeError("session snapshot requires immutable frame and temporal contracts")
        if self.reference is not None and not isinstance(self.reference, ReleaseReference):
            raise TypeError("session reference must be immutable or unavailable")
        if self.observation is not None and not isinstance(self.observation, RelativeClosureObservation):
            raise TypeError("session observation must be immutable or unavailable")
        if type(self.enrollment_reasons) is not tuple or not all(isinstance(r, str) for r in self.enrollment_reasons):
            raise TypeError("enrollment reasons must be immutable strings")


class IntentObservationSession:
    """Lifecycle owns references; tracker owns dwell. Neither owns commands."""

    def __init__(self, profile: IntentObserveProfile, scope: ReferenceScope):
        self.profile, self.scope = profile, scope
        self.tracker = TemporalIntentPinchTracker(profile.temporal)
        self.reference = None
        self._samples = None
        self._signatures = []
        self._shape = None
        self._last_frame = None
        self._revalidate_since = None
        self._version = self._revalidation_id = self._epoch = 0
        self._status = "NEEDS_CALIBRATION"
        self._message = "K: hold thumb and index comfortably apart to calibrate"
        self._enrollment_reasons = ()

    def reset(self, event=ReferenceEvent.EXPLICIT_RESET):
        self.reference = invalidate_reference(self.reference, event)
        self._epoch += 1
        self.scope = replace(self.scope, reset_id=f"intent-epoch-{self._epoch}")
        self._samples = None
        self._signatures = []
        self._revalidate_since = None
        self.tracker.reset()
        self._status = "NEEDS_CALIBRATION"
        self._message = "Reference cleared. K: recalibrate with fingers apart"

    def begin_calibration(self):
        # The operator confirms a comfortable-apart window, not a detected OPEN.
        self.reset()
        self.reference = None
        self._shape = None
        self._samples = []
        self._version += 1
        self._enrollment_reasons = ()
        self._status = "CAPTURING_RELEASE"
        self._message = "Keep thumb and index comfortably apart; hold steady"

    def _comparison(self, hand, signature):
        if self.reference is None or self._shape is None or signature is None:
            return Compatibility.UNCONFIRMED, None, None
        delta = max(abs(a - b) for a, b in zip(signature, self._shape))
        width = hand.palm.width_image_height
        enrolled = self.reference.palm_width_median
        ratio = max(width / enrolled, enrolled / width)
        valid = delta <= self.profile.max_palm_shape_delta and ratio <= self.profile.max_palm_scale_ratio
        return Compatibility.CONFIRMED if valid else Compatibility.INCOMPATIBLE, delta, ratio

    def consume(self, frame, hand, *, events=()):
        if hand is None:
            self.reset(ReferenceEvent.INVALID_GEOMETRY)
            return None  # Caller must expose missing geometry, never keep old active feedback.
        fg = hand.frame_geometry
        identity = (frame.run_id, frame.frame_id, frame.timestamp_s)
        if identity != (fg.run_id, fg.frame_id, fg.timestamp_s):
            self.reset(ReferenceEvent.DOMAIN_CHANGE)
            raise ValueError("intent frame/geometry identity mismatch")
        event = None
        old = self._last_frame
        if frame.run_id != self.scope.run_id:
            self.reset(ReferenceEvent.RUN_CHANGE)
            self.scope = replace(self.scope, run_id=frame.run_id, session_id=frame.run_id)
            event = ReferenceEvent.RUN_CHANGE
        elif old is not None and (fg.frame_id <= old.frame_id or fg.timestamp_s <= old.timestamp_s):
            self.reset(ReferenceEvent.TIMESTAMP_DISCONTINUITY)
            event = ReferenceEvent.TIMESTAMP_DISCONTINUITY
        elif old is not None and fg.timestamp_s - old.timestamp_s > self.profile.temporal.reset_gap_s:
            self.reset(ReferenceEvent.LONG_GAP)
            event = ReferenceEvent.LONG_GAP
        elif old is not None and (fg.width, fg.height) != (old.width, old.height):
            self.reset(ReferenceEvent.DOMAIN_CHANGE)
            event = ReferenceEvent.DOMAIN_CHANGE
        elif frame.filter_diagnostics.reset_occurred:
            self.reset(ReferenceEvent.FILTER_RESET)
            event = ReferenceEvent.FILTER_RESET
        if event is not ReferenceEvent.TIMESTAMP_DISCONTINUITY:
            self._last_frame = fg
        if "RESET_REFERENCE" in events:
            self.reset()
            event = ReferenceEvent.EXPLICIT_RESET
        elif "CALIBRATE_RELEASE" in events:
            self.begin_calibration()
        signature = palm_signature(frame, hand)
        ordinary = frame.status is TrackingStatus.VALID and hand.valid and event is None
        if self._samples is not None:
            if not ordinary or signature is None:
                self._samples = None
                self._status = "NEEDS_CALIBRATION"
                self._enrollment_reasons = ("ENROLLMENT_INTERRUPTED",)
                self._message = "Calibration interrupted by tracking/reset. K: retry"
            else:
                self._samples.append(ReleaseSample(hand, frame.status, False))
                self._signatures.append(signature)
                elapsed = fg.timestamp_s - self._samples[0].geometry.frame_geometry.timestamp_s
                if elapsed >= self.profile.capture_duration_s:
                    window = ConfirmedReleaseWindow(self.scope, tuple(self._samples), True,
                        f"keyboard-release-{self._version}", Compatibility.CONFIRMED)
                    result = build_release_reference(window, self.profile.reference,
                        reference_id=f"{self.scope.session_id}:release:{self._version}", version=self._version)
                    shape = tuple(median(v[i] for v in self._signatures) for i in range(10))
                    stable_shape = all(max(abs(a - b) for a, b in zip(s, shape)) <= self.profile.max_palm_shape_delta
                                       for s in self._signatures)
                    self._enrollment_reasons = tuple(r.value for r in result.reasons)
                    if not stable_shape:
                        self._enrollment_reasons += ("PALM_PROJECTION_UNSTABLE",)
                    if result.valid and stable_shape:
                        self.reference, self._shape = result.reference, shape
                        self._status = "READY"
                        self._message = "Calibrated. Stay released until armed, then close intentionally"
                        self.tracker.reset()
                    else:
                        self._status = "NEEDS_CALIBRATION"
                        self._message = "Release window unstable. K: retry comfortably apart"
                    self._samples = None
        compatibility, delta, ratio = self._comparison(hand, signature)
        if self.reference is not None and self.reference.status is ReferenceStatus.UNVERIFIED:
            # Retained reference is proof-only: enter/hold outputs never leave this block.
            proof_reference = replace(self.reference, status=ReferenceStatus.ACTIVE, invalidation_events=())
            proof = evaluate_relative_closure(hand, proof_reference, self.profile.closure,
                scope=self.scope, tracking_status=frame.status,
                filter_reset_occurred=frame.filter_diagnostics.reset_occurred,
                projection_compatibility=compatibility, event=event)
            if ordinary and proof.valid and proof.released:
                if self._revalidate_since is None:
                    self._revalidate_since = fg.timestamp_s
                duration = fg.timestamp_s - self._revalidate_since
                if duration >= max(self.profile.temporal.release_dwell_s, self.profile.temporal.rearm_dwell_s):
                    self.reference = proof_reference
                    self._revalidation_id += 1
                    self._revalidate_since = None
                    self.tracker.reset()
            else:
                self._revalidate_since = None
        just_enrolled = self.reference is not None and self.reference.valid and fg == self.reference.source_frames[-1]
        if just_enrolled:
            # Enrollment endpoint is neutral; do not evaluate it as continuation.
            temporal = self.tracker.reset()
            return IntentSessionSnapshot(fg, self._status, self._message, self._version,
                self._revalidation_id, delta, ratio, self._enrollment_reasons,
                self.reference, None, temporal)
        observation = evaluate_relative_closure(hand, self.reference, self.profile.closure,
            scope=self.scope, tracking_status=frame.status,
            filter_reset_occurred=frame.filter_diagnostics.reset_occurred,
            projection_compatibility=compatibility, event=event)
        self.reference = observation.reference
        temporal = self.tracker.update(observation)
        if self._samples is None:
            if self.reference is None or self.reference.status is ReferenceStatus.INVALIDATED:
                if self._status == "READY":
                    self._message = "Reference unavailable/incompatible. K: recalibrate apart"
                self._status = "NEEDS_CALIBRATION"
            elif self.reference.status is ReferenceStatus.UNVERIFIED:
                self._status = "REVALIDATING_RELEASE"
                self._message = "Tracking returned: separate thumb/index steadily to rearm"
            elif observation.valid:
                self._status = "READY"
                self._message = "Observation only / legacy controls active"
        return IntentSessionSnapshot(fg, self._status, self._message, self._version,
            self._revalidation_id, delta, ratio, self._enrollment_reasons,
            self.reference, observation, temporal)

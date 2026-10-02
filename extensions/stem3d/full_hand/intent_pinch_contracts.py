"""A5.6 immutable, observation-only contracts. No temporal state or commands.

All policy values are supplied by callers. There is no physical default profile.
Compatibility/confirmation are explicit caller attestations, not confidence or
an inference of contact, identity, depth, or mental intent.
"""

from dataclasses import dataclass
from enum import Enum
import math

from dip_touchless.core import TrackingStatus

from .contracts import FrameGeometry, GeometryReason, HandGeometry


def _finite(*values):
    if not all(type(v) in (int, float) and math.isfinite(v) for v in values):
        raise ValueError("values must be finite numbers")


def _text(*values):
    if not all(isinstance(v, str) and v.strip() for v in values):
        raise ValueError("identities must be nonempty strings")


def _tuple(value, kind):
    if type(value) is not tuple or not all(isinstance(v, kind) for v in value):
        raise TypeError("collections must be typed immutable tuples")


class ProjectionCompatibility(str, Enum):
    CONFIRMED = "CONFIRMED"
    UNCONFIRMED = "UNCONFIRMED"
    INCOMPATIBLE = "INCOMPATIBLE"


class ReferenceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    UNVERIFIED = "UNVERIFIED"
    INVALIDATED = "INVALIDATED"


class ReferenceEvent(str, Enum):
    INVALID_GEOMETRY = "INVALID_GEOMETRY"
    TRACKING_LOSS = "TRACKING_LOSS"
    REACQUISITION = "REACQUISITION"
    EXPLICIT_RESET = "EXPLICIT_RESET"
    FILTER_RESET = "FILTER_RESET"
    TIMESTAMP_DISCONTINUITY = "TIMESTAMP_DISCONTINUITY"
    LONG_GAP = "LONG_GAP"
    RUN_CHANGE = "RUN_CHANGE"
    SESSION_CHANGE = "SESSION_CHANGE"
    DOMAIN_CHANGE = "DOMAIN_CHANGE"


class IntentPinchReason(str, Enum):
    RELEASE_NOT_CONFIRMED = "RELEASE_NOT_CONFIRMED"
    INSUFFICIENT_SAMPLES = "INSUFFICIENT_SAMPLES"
    INSUFFICIENT_DURATION = "INSUFFICIENT_DURATION"
    DISCONTINUOUS_WINDOW = "DISCONTINUOUS_WINDOW"
    INVALID_GEOMETRY = "INVALID_GEOMETRY"
    TRACKING_UNUSABLE = "TRACKING_UNUSABLE"
    REACQUISITION = "REACQUISITION"
    FILTER_RESET = "FILTER_RESET"
    SCOPE_MISMATCH = "SCOPE_MISMATCH"
    COMPARISON_UNCONFIRMED = "COMPARISON_UNCONFIRMED"
    COMPARISON_INCOMPATIBLE = "COMPARISON_INCOMPATIBLE"
    DEGENERATE_DISTANCE = "DEGENERATE_DISTANCE"
    NOISY_WINDOW = "NOISY_WINDOW"
    PALM_WIDTH_UNSTABLE = "PALM_WIDTH_UNSTABLE"
    NOISE_EXCEEDS_REFERENCE = "NOISE_EXCEEDS_REFERENCE"
    NO_REFERENCE = "NO_REFERENCE"
    REFERENCE_INACTIVE = "REFERENCE_INACTIVE"
    PRE_ENROLLMENT_FRAME = "PRE_ENROLLMENT_FRAME"
    NUMERICAL_FAILURE = "NUMERICAL_FAILURE"


class RelativeClosureZone(str, Enum):
    RELEASED = "RELEASED"
    BAND = "BAND"
    ENTRY = "ENTRY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ReferenceScope:
    session_id: str
    run_id: str
    camera_id: str
    provider_id: str
    profile_id: str
    coordinate_domain_id: str
    reset_id: str

    def __post_init__(self):
        _text(self.session_id, self.run_id, self.camera_id, self.provider_id,
              self.profile_id, self.coordinate_domain_id, self.reset_id)


@dataclass(frozen=True, slots=True)
class ReleaseSample:
    geometry: HandGeometry
    tracking_status: TrackingStatus
    filter_reset_occurred: bool

    def __post_init__(self):
        if not isinstance(self.geometry, HandGeometry):
            raise TypeError("sample requires immutable A2 HandGeometry")
        if not isinstance(self.tracking_status, TrackingStatus):
            raise TypeError("tracking status must be explicit")
        if type(self.filter_reset_occurred) is not bool:
            raise TypeError("filter reset must be explicit bool")


@dataclass(frozen=True, slots=True)
class ConfirmedReleaseWindow:
    scope: ReferenceScope
    samples: tuple[ReleaseSample, ...]
    comfortable_apart_confirmed: bool
    confirmation_id: str
    projection_compatibility: ProjectionCompatibility

    def __post_init__(self):
        if not isinstance(self.scope, ReferenceScope):
            raise TypeError("window requires ReferenceScope")
        _tuple(self.samples, ReleaseSample)
        if type(self.comfortable_apart_confirmed) is not bool:
            raise TypeError("confirmation must be explicit bool")
        _text(self.confirmation_id)
        if not isinstance(self.projection_compatibility, ProjectionCompatibility):
            raise TypeError("projection compatibility must be explicit")


@dataclass(frozen=True, slots=True)
class ReleaseReferencePolicy:
    min_samples: int
    min_duration_s: float
    max_sample_gap_s: float
    max_relative_mad: float
    max_relative_deviation: float
    max_palm_width_ratio: float
    noise_multiplier: float

    def __post_init__(self):
        if type(self.min_samples) is not int or self.min_samples < 2:
            raise ValueError("release enrollment needs at least two samples")
        _finite(self.min_duration_s, self.max_sample_gap_s, self.max_relative_mad,
                self.max_relative_deviation, self.max_palm_width_ratio,
                self.noise_multiplier)
        if self.min_duration_s <= 0 or self.max_sample_gap_s <= 0:
            raise ValueError("duration and gap must be positive")
        if not 0 <= self.max_relative_mad <= self.max_relative_deviation:
            raise ValueError("require 0 <= MAD bound <= deviation bound")
        if self.max_palm_width_ratio < 1 or self.noise_multiplier < 1:
            raise ValueError("palm ratio and noise multiplier must be >= 1")


@dataclass(frozen=True, slots=True)
class RelativeClosureThresholds:
    enter: float
    exit: float

    def __post_init__(self):
        _finite(self.enter, self.exit)
        if not 0 < self.exit < self.enter < 1:
            raise ValueError("require 0 < relative exit < relative enter < 1")


@dataclass(frozen=True, slots=True)
class IntentPredicateDiagnostic:
    name: str
    passed: bool | None
    reason: str
    value: float | None = None
    threshold: float | None = None

    def __post_init__(self):
        _text(self.name, self.reason)
        if self.passed is not None and type(self.passed) is not bool:
            raise TypeError("predicate must be bool or explicitly unavailable")
        for value in (self.value, self.threshold):
            if value is not None:
                _finite(value)


@dataclass(frozen=True, slots=True)
class ReleaseReference:
    reference_id: str
    version: int
    scope: ReferenceScope
    confirmation_id: str
    source_frames: tuple[FrameGeometry, ...]
    distance_palm: float
    mad_distance_palm: float
    max_deviation_distance_palm: float
    noise_allowance_relative: float
    palm_width_median: float
    palm_width_min: float
    palm_width_max: float
    policy: ReleaseReferencePolicy
    status: ReferenceStatus = ReferenceStatus.ACTIVE
    invalidation_events: tuple[ReferenceEvent, ...] = ()
    # Structural version/method: no alternative endpoint formula in A5.6.
    schema_version: str = "intent-pinch-reference-v1"
    acquisition_method: str = "CONFIRMED_COMFORTABLE_APART"

    def __post_init__(self):
        _text(self.reference_id, self.confirmation_id)
        if type(self.version) is not int or self.version < 1:
            raise ValueError("reference version must be a positive integer")
        if not isinstance(self.scope, ReferenceScope) or not isinstance(self.policy, ReleaseReferencePolicy):
            raise TypeError("reference requires immutable scope and policy")
        _tuple(self.source_frames, FrameGeometry)
        _tuple(self.invalidation_events, ReferenceEvent)
        if len(self.source_frames) < self.policy.min_samples:
            raise ValueError("reference must retain its source window")
        if any(f.run_id != self.scope.run_id for f in self.source_frames):
            raise ValueError("reference frame/run scope mismatch")
        if not isinstance(self.status, ReferenceStatus):
            raise TypeError("reference status must be an enum")
        if (self.status is ReferenceStatus.ACTIVE) != (not self.invalidation_events):
            raise ValueError("inactive reference requires invalidation reasons")
        _finite(self.distance_palm, self.mad_distance_palm,
                self.max_deviation_distance_palm, self.noise_allowance_relative,
                self.palm_width_median, self.palm_width_min, self.palm_width_max)
        if self.distance_palm <= 0 or not 0 <= self.noise_allowance_relative < 1:
            raise ValueError("reference must have a usable positive noise-separated span")
        if not 0 <= self.mad_distance_palm <= self.max_deviation_distance_palm:
            raise ValueError("invalid measured dispersion")
        if not 0 < self.palm_width_min <= self.palm_width_median <= self.palm_width_max:
            raise ValueError("invalid palm denominator summary")
        if (self.schema_version != "intent-pinch-reference-v1"
                or self.acquisition_method != "CONFIRMED_COMFORTABLE_APART"):
            raise ValueError("unsupported reference schema or acquisition method")

    @property
    def valid(self) -> bool:
        return self.status is ReferenceStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class ReferenceBuildResult:
    reference: ReleaseReference | None
    reasons: tuple[IntentPinchReason, ...]
    geometry_reasons: tuple[GeometryReason, ...]
    predicates: tuple[IntentPredicateDiagnostic, ...]

    def __post_init__(self):
        _tuple(self.reasons, IntentPinchReason)
        _tuple(self.geometry_reasons, GeometryReason)
        _tuple(self.predicates, IntentPredicateDiagnostic)
        if self.reference is not None and not isinstance(self.reference, ReleaseReference):
            raise TypeError("reference must be immutable or None")
        if (self.reference is not None) != (not self.reasons):
            raise ValueError("successful build has a reference and no failure reasons")

    @property
    def valid(self) -> bool:
        return self.reference is not None and self.reference.valid


@dataclass(frozen=True, slots=True)
class RelativeClosureObservation:
    frame_geometry: FrameGeometry
    # Thread this immutable result forward; an inactive reference is metadata only.
    reference: ReleaseReference | None
    geometry_valid: bool
    reference_valid: bool
    reasons: tuple[IntentPinchReason, ...]
    geometry_reasons: tuple[GeometryReason, ...]
    zone: RelativeClosureZone
    distance_palm: float | None
    tip_distance_image_height: float | None
    palm_width_image_height: float | None
    relative_closure: float | None
    released: bool | None
    closing: bool | None
    band: bool | None
    entry: bool | None
    predicates: tuple[IntentPredicateDiagnostic, ...]

    def __post_init__(self):
        if not isinstance(self.frame_geometry, FrameGeometry):
            raise TypeError("observation requires actual frame identity/geometry")
        if self.reference is not None and not isinstance(self.reference, ReleaseReference):
            raise TypeError("reference must be immutable or None")
        if not isinstance(self.zone, RelativeClosureZone):
            raise TypeError("zone must be an enum")
        for value in (self.geometry_valid, self.reference_valid):
            if type(value) is not bool:
                raise TypeError("validity must be bool")
        for value in (self.released, self.closing, self.band, self.entry):
            if value is not None and type(value) is not bool:
                raise TypeError("evidence must be bool or unavailable")
        for value in (self.distance_palm, self.tip_distance_image_height,
                      self.palm_width_image_height, self.relative_closure):
            if value is not None:
                _finite(value)
        _tuple(self.reasons, IntentPinchReason)
        _tuple(self.geometry_reasons, GeometryReason)
        _tuple(self.predicates, IntentPredicateDiagnostic)
        if self.zone is RelativeClosureZone.UNKNOWN:
            if not self.reasons or any(v is not None for v in (
                    self.relative_closure, self.released, self.closing, self.band, self.entry)):
                raise ValueError("UNKNOWN must have reasons and no usable closure evidence")
        elif self.reasons or not (self.geometry_valid and self.reference_valid):
            raise ValueError("usable closure requires valid geometry and reference")

    @property
    def valid(self) -> bool:
        return self.zone is not RelativeClosureZone.UNKNOWN

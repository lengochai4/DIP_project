"""Immutable single-frame classification contracts, separate from Core/G7."""

from dataclasses import dataclass
from enum import Enum
import math

from .contracts import Finger, FrameGeometry, GeometryReason


class FingerState(str, Enum):
    EXTENDED = "EXTENDED"
    FLEXED = "FLEXED"
    INTERMEDIATE = "INTERMEDIATE"
    UNKNOWN = "UNKNOWN"


class HandPose(str, Enum):
    OPEN = "OPEN"
    POINT = "POINT"
    PINCH = "PINCH"
    FIST = "FIST"
    UNKNOWN = "UNKNOWN"


class ClassificationReason(str, Enum):
    INVALID_GEOMETRY = "INVALID_GEOMETRY"
    MISSING_FEATURES = "MISSING_FEATURES"
    INVALID_FEATURE_RANGE = "INVALID_FEATURE_RANGE"
    CONFLICTING_FEATURES = "CONFLICTING_FEATURES"
    BETWEEN_THRESHOLDS = "BETWEEN_THRESHOLDS"
    THUMB_POSTURE_UNRESOLVED = "THUMB_POSTURE_UNRESOLVED"
    FINGER_UNKNOWN = "FINGER_UNKNOWN"
    PINCH_BOUNDARY_BAND = "PINCH_BOUNDARY_BAND"
    NO_POSE_MATCH = "NO_POSE_MATCH"
    CONFLICTING_POSES = "CONFLICTING_POSES"


def _finite(*values) -> None:
    if not all(type(v) in (int, float) and math.isfinite(v) for v in values):
        raise ValueError("thresholds/diagnostics must be finite numbers")


def _collection(value, kind) -> None:
    if type(value) is not tuple or not all(isinstance(v, kind) for v in value):
        raise TypeError("diagnostic collections must be typed immutable tuples")


@dataclass(frozen=True, slots=True)
class FingerThresholds:
    """Caller-supplied thresholds; angles in radians, straightness in [0, 1]."""

    extended_min_angle_rad: float
    flexed_max_angle_rad: float
    extended_min_straightness: float
    flexed_max_straightness: float

    def __post_init__(self) -> None:
        _finite(self.extended_min_angle_rad, self.flexed_max_angle_rad,
                self.extended_min_straightness, self.flexed_max_straightness)
        if not 0 <= self.flexed_max_angle_rad < self.extended_min_angle_rad <= math.pi:
            raise ValueError("require 0 <= flexed angle < extended angle <= pi")
        if not 0 <= self.flexed_max_straightness < self.extended_min_straightness <= 1:
            raise ValueError("require 0 <= flexed straightness < extended straightness <= 1")


@dataclass(frozen=True, slots=True)
class ThumbThresholds:
    chain: FingerThresholds
    opposition_max_distance_palm: float
    spread_min_distance_palm: float
    extended_max_axis_to_palm_rad: float

    def __post_init__(self) -> None:
        if not isinstance(self.chain, FingerThresholds):
            raise TypeError("thumb chain requires FingerThresholds")
        _finite(self.opposition_max_distance_palm, self.spread_min_distance_palm,
                self.extended_max_axis_to_palm_rad)
        if not 0 <= self.opposition_max_distance_palm < self.spread_min_distance_palm:
            raise ValueError("require 0 <= opposition distance < spread distance")
        if not 0 <= self.extended_max_axis_to_palm_rad <= math.pi:
            raise ValueError("thumb axis threshold must be in [0, pi]")


@dataclass(frozen=True, slots=True)
class PoseThresholds:
    fingers: FingerThresholds
    thumb: ThumbThresholds
    pinch_enter_distance_palm: float
    pinch_exit_distance_palm: float

    def __post_init__(self) -> None:
        if not isinstance(self.fingers, FingerThresholds) or not isinstance(self.thumb, ThumbThresholds):
            raise TypeError("pose thresholds require immutable finger/thumb thresholds")
        _finite(self.pinch_enter_distance_palm, self.pinch_exit_distance_palm)
        if not 0 <= self.pinch_enter_distance_palm < self.pinch_exit_distance_palm:
            raise ValueError("require 0 <= pinch enter < pinch exit")


@dataclass(frozen=True, slots=True)
class PredicateDiagnostic:
    name: str
    passed: bool | None
    # None means not evaluated/unavailable, never a fabricated measurement.
    value: float | None = None
    threshold: float | None = None
    comparison: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("predicate name must be a nonempty string")
        if self.passed is not None and type(self.passed) is not bool:
            raise TypeError("passed must be bool or None")
        for v in (self.value, self.threshold):
            if v is not None:
                _finite(v)
        if self.comparison is not None and not isinstance(self.comparison, str):
            raise TypeError("comparison must be str or None")


@dataclass(frozen=True, slots=True)
class FingerObservation:
    finger: Finger
    state: FingerState
    predicates: tuple[PredicateDiagnostic, ...]
    reasons: tuple[ClassificationReason, ...]
    geometry_reasons: tuple[GeometryReason, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.finger, Finger) or not isinstance(self.state, FingerState):
            raise TypeError("finger/state must be enums")
        _collection(self.predicates, PredicateDiagnostic)
        _collection(self.reasons, ClassificationReason)
        _collection(self.geometry_reasons, GeometryReason)


@dataclass(frozen=True, slots=True)
class PinchGeometry:
    """Independent strict enter/exit predicates, NOT a hysteretic active state."""

    distance_palm: float | None
    enter: bool | None
    exit: bool | None
    boundary_band: bool | None
    predicates: tuple[PredicateDiagnostic, ...]

    def __post_init__(self) -> None:
        if self.distance_palm is not None:
            _finite(self.distance_palm)
        for v in (self.enter, self.exit, self.boundary_band):
            if v is not None and type(v) is not bool:
                raise TypeError("pinch predicates must be bool or None")
        _collection(self.predicates, PredicateDiagnostic)


@dataclass(frozen=True, slots=True)
class PoseObservation:
    frame_geometry: FrameGeometry
    pose: HandPose
    fingers: tuple[FingerObservation, ...]
    pinch: PinchGeometry
    predicates: tuple[PredicateDiagnostic, ...]
    reasons: tuple[ClassificationReason, ...]
    geometry_reasons: tuple[GeometryReason, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.frame_geometry, FrameGeometry) or not isinstance(self.pose, HandPose):
            raise TypeError("pose requires FrameGeometry and HandPose")
        if not isinstance(self.pinch, PinchGeometry):
            raise TypeError("pinch must be immutable PinchGeometry")
        _collection(self.fingers, FingerObservation)
        _collection(self.predicates, PredicateDiagnostic)
        _collection(self.reasons, ClassificationReason)
        _collection(self.geometry_reasons, GeometryReason)

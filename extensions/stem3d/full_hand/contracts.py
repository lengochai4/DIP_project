"""Immutable Extension-only geometry contracts; no pose or command semantics.

All points/vectors are 2D tuples. Distances ending in ``_palm`` are divided
by palm width, angles are unsigned radians, and no field represents depth,
tracking confidence, finger state, or a classified hand pose.
"""

from dataclasses import dataclass
from enum import Enum
import math


def _tuple(value, length, element_type=None) -> None:
    if type(value) is not tuple or (length is not None and len(value) != length):
        raise ValueError("geometry collections must be tuples of the declared size")
    if element_type is not None:
        if not all(isinstance(v, element_type) for v in value):
            raise TypeError("unexpected geometry collection element type")
    else:
        _finite(*value)


def _finite(*values) -> None:
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
        raise ValueError("geometry values must be finite numbers")


def _validity(valid, reasons) -> None:
    _tuple(reasons, None, GeometryReason)
    if type(valid) is not bool or valid != (not reasons):
        raise ValueError("valid geometry has no reasons; invalid geometry has reasons")


class Finger(str, Enum):
    THUMB = "THUMB"
    INDEX = "INDEX"
    MIDDLE = "MIDDLE"
    RING = "RING"
    PINKY = "PINKY"


class GeometryReason(str, Enum):
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    INVALID_FRAME_IDENTITY = "INVALID_FRAME_IDENTITY"
    TRACKING_UNUSABLE = "TRACKING_UNUSABLE"
    LANDMARK_COUNT = "LANDMARK_COUNT"
    LANDMARK_INDICES = "LANDMARK_INDICES"
    COORDINATE_SPACE = "COORDINATE_SPACE"
    NON_FINITE_COORDINATE = "NON_FINITE_COORDINATE"
    DEGENERATE_PALM = "DEGENERATE_PALM"
    DEGENERATE_FINGER = "DEGENERATE_FINGER"
    NUMERICAL_FAILURE = "NUMERICAL_FAILURE"


@dataclass(frozen=True, slots=True)
class FrameGeometry:
    """Actual full-frame dimensions, never ROI or requested camera dimensions.

    Supplied explicitly by the caller; A2 does not hook into acquisition.
    Identity must match the TrackingFrame exactly, including its timestamp.
    """

    run_id: str
    frame_id: int
    timestamp_s: float
    width: int
    height: int

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, str) or not self.run_id:
            raise ValueError("run_id must be a non-empty string")
        if type(self.frame_id) is not int or self.frame_id < 0:
            raise ValueError("frame_id must be a non-negative integer")
        if not math.isfinite(self.timestamp_s):
            raise ValueError("timestamp_s must be finite")
        if any(type(v) is not int or v <= 0 for v in (self.width, self.height)):
            raise ValueError("actual frame dimensions must be positive integers")


@dataclass(frozen=True, slots=True)
class PalmGeometry:
    # Mean of wrist and MCP landmarks 5, 9, 13, 17; full-frame normalized.
    anchor_xy: tuple[float, float]
    # Width 5--17 in image-height units: x * width/height, y unchanged.
    width_image_height: float
    # Anatomical transverse axis (pinky -> index), orthogonal distal axis.
    lateral_axis: tuple[float, float]
    distal_axis: tuple[float, float]

    def __post_init__(self) -> None:
        for point in (self.anchor_xy, self.lateral_axis, self.distal_axis):
            _tuple(point, 2)
        _finite(self.width_image_height)
        if self.width_image_height <= 0:
            raise ValueError("palm width must be positive")


@dataclass(frozen=True, slots=True)
class ThumbGeometry:
    """CMC/MCP/IP/tip chain plus opposition geometry (not an opposition state)."""

    axis_to_palm_rad: float
    tip_to_index_mcp_palm: float
    tip_to_pinky_mcp_palm: float

    def __post_init__(self) -> None:
        _finite(self.axis_to_palm_rad, self.tip_to_index_mcp_palm,
                self.tip_to_pinky_mcp_palm)


@dataclass(frozen=True, slots=True)
class FingerGeometry:
    finger: Finger
    landmark_indices: tuple[int, int, int, int]
    valid: bool
    reasons: tuple[GeometryReason, ...]
    # Interior joint angles at chain elements 1 and 2: straight == pi.
    joint_angles_rad: tuple[float, float] | None
    segment_lengths_palm: tuple[float, float, float] | None
    # Distance base--tip / total chain length; geometry, not finger state.
    straightness: float | None
    tip_to_wrist_palm: float | None
    # Tip relative to palm anchor, projected onto anatomical palm axes.
    tip_in_palm: tuple[float, float] | None
    thumb: ThumbGeometry | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.finger, Finger):
            raise TypeError("finger must be a Finger")
        _tuple(self.landmark_indices, 4, int)
        _validity(self.valid, self.reasons)
        for value, size in ((self.joint_angles_rad, 2),
                            (self.segment_lengths_palm, 3), (self.tip_in_palm, 2)):
            if value is not None:
                _tuple(value, size)
        for value in (self.straightness, self.tip_to_wrist_palm):
            if value is not None:
                _finite(value)
        if self.thumb is not None and not isinstance(self.thumb, ThumbGeometry):
            raise TypeError("thumb must be immutable ThumbGeometry or None")


@dataclass(frozen=True, slots=True)
class HandGeometry:
    frame_geometry: FrameGeometry
    valid: bool
    reasons: tuple[GeometryReason, ...]
    palm: PalmGeometry | None
    # THUMB, INDEX, MIDDLE, RING, PINKY order; empty for unusable input/palm.
    fingers: tuple[FingerGeometry, ...]
    thumb_index_distance_palm: float | None

    def __post_init__(self) -> None:
        if not isinstance(self.frame_geometry, FrameGeometry):
            raise TypeError("frame_geometry must be FrameGeometry")
        if self.palm is not None and not isinstance(self.palm, PalmGeometry):
            raise TypeError("palm must be immutable PalmGeometry or None")
        _validity(self.valid, self.reasons)
        _tuple(self.fingers, None, FingerGeometry)
        if self.thumb_index_distance_palm is not None:
            _finite(self.thumb_index_distance_palm)

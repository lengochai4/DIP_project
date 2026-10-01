"""Pure single-frame extraction from 21 filtered FRAME_NORMALIZED landmarks.

No raw-landmark fallback, smoothing, pose thresholds, runtime hooks or commands.
Uses only aspect-corrected x/y. z is checked for finite contract input but never
used as geometry: Core filters pass model-relative z through unchanged.
Finite coordinates outside [0, 1] remain legitimate out-of-frame observations.
"""

import math
import sys

from dip_touchless.core import CoordinateSpace, Landmark, TrackingFrame, TrackingStatus

from .contracts import (
    Finger, FingerGeometry, FrameGeometry, GeometryReason, HandGeometry,
    PalmGeometry, ThumbGeometry,
)

# Structural MediaPipe/project landmark topology, not configurable thresholds.
_CHAINS = (
    (Finger.THUMB, (1, 2, 3, 4)),
    (Finger.INDEX, (5, 6, 7, 8)),
    (Finger.MIDDLE, (9, 10, 11, 12)),
    (Finger.RING, (13, 14, 15, 16)),
    (Finger.PINKY, (17, 18, 19, 20)),
)
_MCP = (5, 9, 13, 17)
# Floating-point degeneracy tolerance, relative to palm width. Not a pose,
# sensitivity, calibration or physical edge-on threshold.
_ROUND_OFF = 64 * sys.float_info.epsilon
_Point = tuple[float, float]


def _sub(a: _Point, b: _Point) -> _Point:
    return (a[0] - b[0], a[1] - b[1])


def _dot(a: _Point, b: _Point) -> float:
    return a[0] * b[0] + a[1] * b[1]


def _length(a: _Point) -> float:
    return math.hypot(*a)


def _angle(a: _Point, b: _Point) -> float:
    # atan2 avoids acos rounding and is unsigned under reflection.
    return math.atan2(abs(a[0] * b[1] - a[1] * b[0]), _dot(a, b))


def _invalid(geometry: FrameGeometry, reason: GeometryReason) -> HandGeometry:
    return HandGeometry(geometry, False, (reason,), None, (), None)


def extract_hand_geometry(
    frame: TrackingFrame, geometry: FrameGeometry,
) -> HandGeometry:
    """Return immutable geometry or explicit unavailability, without mutation.

    VALID/REACQUIRED both provide geometry; this function decides no interaction
    validity. Unordered indices are accepted and reordered locally. Finger
    degeneracy retains the usable palm/other fingers but makes hand.valid false.
    """
    if (not isinstance(frame.run_id, str) or not frame.run_id
            or type(frame.frame_id) is not int or frame.frame_id < 0
            or not math.isfinite(frame.timestamp_s)):
        return _invalid(geometry, GeometryReason.INVALID_FRAME_IDENTITY)
    if (frame.run_id, frame.frame_id, frame.timestamp_s) != (
        geometry.run_id, geometry.frame_id, geometry.timestamp_s,
    ):
        return _invalid(geometry, GeometryReason.IDENTITY_MISMATCH)
    if frame.status not in (TrackingStatus.VALID, TrackingStatus.REACQUIRED):
        return _invalid(geometry, GeometryReason.TRACKING_UNUSABLE)
    landmarks = frame.filtered_landmarks
    if len(landmarks) != 21:
        return _invalid(geometry, GeometryReason.LANDMARK_COUNT)
    indices = tuple(p.index for p in landmarks)
    if (any(type(i) is not int for i in indices)
            or set(indices) != set(range(21))):
        return _invalid(geometry, GeometryReason.LANDMARK_INDICES)
    if any(p.coordinate_space is not CoordinateSpace.FRAME_NORMALIZED
           for p in landmarks):
        return _invalid(geometry, GeometryReason.COORDINATE_SPACE)
    if any(not all(math.isfinite(v) for v in (p.x, p.y, p.z))
           for p in landmarks):
        return _invalid(geometry, GeometryReason.NON_FINITE_COORDINATE)
    try:
        return _extract(geometry, landmarks)
    except (OverflowError, ZeroDivisionError):
        return _invalid(geometry, GeometryReason.NUMERICAL_FAILURE)


def _extract(geometry: FrameGeometry, landmarks: tuple[Landmark, ...]) -> HandGeometry:
    ordered = sorted(landmarks, key=lambda p: p.index)
    aspect = geometry.width / geometry.height
    points = tuple((p.x * aspect, p.y) for p in ordered)
    if not all(math.isfinite(v) for p in points for v in p):
        return _invalid(geometry, GeometryReason.NUMERICAL_FAILURE)
    # Subtract wrist first, so local calculations do not depend on translation.
    local = tuple(_sub(p, points[0]) for p in points)
    lateral = _sub(local[5], local[17])
    width = _length(lateral)
    if not math.isfinite(width):
        return _invalid(geometry, GeometryReason.NUMERICAL_FAILURE)
    if width == 0:
        return _invalid(geometry, GeometryReason.DEGENERATE_PALM)
    local = tuple((p[0] / width, p[1] / width) for p in local)
    if not all(math.isfinite(v) for p in local for v in p):
        return _invalid(geometry, GeometryReason.NUMERICAL_FAILURE)
    lateral = (lateral[0] / width, lateral[1] / width)
    distal = (-lateral[1], lateral[0])
    mcp_center = tuple(math.fsum(local[i][d] / 4 for i in _MCP)
                       for d in (0, 1))
    distal_projection = _dot(mcp_center, distal)
    if not math.isfinite(distal_projection):
        return _invalid(geometry, GeometryReason.NUMERICAL_FAILURE)
    if abs(distal_projection) <= _ROUND_OFF:
        return _invalid(geometry, GeometryReason.DEGENERATE_PALM)
    if distal_projection < 0:
        distal = (-distal[0], -distal[1])
    anchor_local = tuple(math.fsum(local[i][d] / 5 for i in (0, *_MCP))
                         for d in (0, 1))
    anchor_xy = tuple(math.fsum(getattr(ordered[i], name) / 5
                               for i in (0, *_MCP)) for name in ("x", "y"))
    palm = PalmGeometry(anchor_xy, width, lateral, distal)
    fingers = tuple(_finger(f, chain, local, anchor_local, lateral, distal)
                    for f, chain in _CHAINS)
    reasons = tuple(dict.fromkeys(r for f in fingers for r in f.reasons))
    pinch = _length(_sub(local[4], local[8]))
    if not math.isfinite(pinch):
        return _invalid(geometry, GeometryReason.NUMERICAL_FAILURE)
    return HandGeometry(geometry, not reasons, reasons, palm, fingers, pinch)


def _finger(
    finger: Finger, chain: tuple[int, int, int, int], points: tuple[_Point, ...],
    anchor: _Point, lateral: _Point, distal: _Point,
) -> FingerGeometry:
    p = tuple(points[i] for i in chain)
    segments = tuple(_sub(p[i + 1], p[i]) for i in range(3))
    lengths = tuple(_length(s) for s in segments)
    if not all(math.isfinite(v) for v in lengths):
        reason = GeometryReason.NUMERICAL_FAILURE
    elif min(lengths) <= _ROUND_OFF:
        reason = GeometryReason.DEGENERATE_FINGER
    else:
        reason = None
    if reason is not None:
        return FingerGeometry(finger, chain, False, (reason,),
                              None, None, None, None, None)
    # Unit segments avoid overflow in angle cross/dot products.
    unit = tuple((s[0] / n, s[1] / n) for s, n in zip(segments, lengths))
    angles = tuple(_angle((-unit[i][0], -unit[i][1]), unit[i + 1])
                   for i in range(2))
    tip_vector = _sub(p[3], anchor)
    tip_in_palm = (_dot(tip_vector, lateral), _dot(tip_vector, distal))
    axis = _sub(p[3], p[0])
    axis_length = _length(axis)
    thumb = None
    if finger is Finger.THUMB:
        if axis_length <= _ROUND_OFF:
            return FingerGeometry(finger, chain, False,
                                  (GeometryReason.DEGENERATE_FINGER,),
                                  None, None, None, None, None)
        thumb = ThumbGeometry(
            _angle((axis[0] / axis_length, axis[1] / axis_length), distal),
            _length(_sub(p[3], points[5])),
            _length(_sub(p[3], points[17])),
        )
    straightness = axis_length / math.fsum(lengths)
    wrist_distance = _length(p[3])
    values = (*angles, *tip_in_palm, straightness, wrist_distance)
    if thumb is not None:
        values += (thumb.axis_to_palm_rad, thumb.tip_to_index_mcp_palm,
                   thumb.tip_to_pinky_mcp_palm)
    if not all(math.isfinite(v) for v in values):
        return FingerGeometry(finger, chain, False,
                              (GeometryReason.NUMERICAL_FAILURE,),
                              None, None, None, None, None)
    return FingerGeometry(finger, chain, True, (), angles, lengths,
                          straightness, wrist_distance, tip_in_palm, thumb)

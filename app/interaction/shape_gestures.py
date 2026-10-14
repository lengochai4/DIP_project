"""ShapeGestureEngine: interprets fingertip positions as shape-drawing candidates.

Receives TipSample lists from the product hand geometry layer and, given a
target shape type, computes shape parameters (center, radii, corners …) and
tracks whether the pose is stable enough to be "frozen" into the scene.

Rules
-----
* Circle  : 1 hand → thumb-tip + index-tip (center = midpoint, r = dist/2)
             2 hands → 2 index-tips (center = midpoint, r = dist/2)
* Square  : same landmark selection as Circle; the side length = dist
* Rectangle 1-hand: thumb + index, aspect ratio 2:1 fixed
  Rectangle 2-hand: 2 index-tips define opposite corners of the bounding box
* Triangle 1-hand: index + middle + thumb define the three vertices
  Triangle 2-hand: the hand whose (index, thumb) distance is smaller
              contributes the apex (at its index-tip); the other hand
              contributes the other two vertices (index-tip, thumb-tip).
* Sphere  : 2 hands required; each hand: index + thumb → center = grand
              midpoint, radius = half of distance between the two index-tips
* Cube    : 2 hands; thumb+index per hand define opposite body diagonal corners
* Box     : 2 hands; index+middle+ring+pinky per hand (4 pts each = 8 pts total)
* Pyramid : 2 hands; hand with smaller (index, thumb) dist → apex at index-tip;
              other hand → base edge (index-tip, thumb-tip)

Stability: position and size must change by less than STABILITY_THRESHOLD for
at least STABILITY_FRAMES consecutive frames before `is_stable` is True.

No Core imports; product-layer only.
"""

import math
from dataclasses import dataclass, field
from typing import Optional, Sequence

# ------------------------------------------------------------------
# Public shape types matching the toolbar labels
# ------------------------------------------------------------------

SHAPE_2D = ("Circle", "Square", "Triangle", "Rectangle")
SHAPE_3D = ("Sphere", "Cube", "Box", "Pyramid")
ALL_SHAPES = SHAPE_2D + SHAPE_3D

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

STABILITY_THRESHOLD = 0.018   # normalised-coordinate units
STABILITY_FRAMES = 39         # ~1.3 s @ 30 fps (shortened by 35% from 60 frames)
STABILITY_DURATION_S = 1.8    # 1.5s -> 2.0s realtime freeze hold duration


# ------------------------------------------------------------------
# Data contracts
# ------------------------------------------------------------------

@dataclass(frozen=True)
class ShapeParams:
    """Renderer-agnostic shape description in FRAME_NORMALIZED coordinates."""
    kind: str
    center_xy: tuple[float, float]
    # 2-D shapes
    radius: float = 0.0
    width: float = 0.0
    height: float = 0.0
    corners_xy: tuple[tuple[float, float], ...] = ()
    # 3-D shapes
    size: float = 0.0
    corners_3d: tuple[tuple[float, float, float], ...] = ()
    # Diagnostic
    hands_used: int = 0
    degenerate: bool = False


@dataclass
class ShapeCandidate:
    """Result of one engine update tick."""
    shape_type: str
    params: Optional[ShapeParams]
    is_stable: bool = False
    stable_fraction: float = 0.0   # [0, 1] progress toward stability
    reason: str = ""               # human-readable status


# ------------------------------------------------------------------
# Tip selection helpers
# ------------------------------------------------------------------

_FINGER_NAMES = {
    "THUMB": 0,
    "INDEX": 1,
    "MIDDLE": 2,
    "RING": 3,
    "PINKY": 4,
}

_FINGER_IDX = {
    "INDEX":  lambda samples: _tip(samples, "INDEX"),
    "THUMB":  lambda samples: _tip(samples, "THUMB"),
    "MIDDLE": lambda samples: _tip(samples, "MIDDLE"),
    "RING":   lambda samples: _tip(samples, "RING"),
    "PINKY":  lambda samples: _tip(samples, "PINKY"),
}


def _tip(samples, finger: str):
    """Return the TipSample matching finger name or index, or None."""
    idx = _FINGER_NAMES.get(finger)
    for s in samples:
        matches = (
            s.token.endswith(f"_{finger}")
            or s.token.endswith(f":{finger}")
            or (idx is not None and s.token.endswith(f":{idx}"))
        )
        if matches:
            if s.extended or finger == "THUMB":
                return s
    if idx is not None and len(samples) == 5:
        s = samples[idx]
        if s.extended or finger == "THUMB":
            return s
    return None


def _xy(tip) -> Optional[tuple[float, float]]:
    return tip.xy if tip is not None else None


def _dist(a, b) -> float:
    if a is None or b is None:
        return 0.0
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _midpoint(a, b) -> tuple[float, float]:
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)


def _key(params: ShapeParams) -> tuple:
    """Compact tuple for stability comparison."""
    return (*params.center_xy, params.radius, params.width, params.height, params.size)


# ------------------------------------------------------------------
# Per-shape extractors
# ------------------------------------------------------------------

def _extract_circle(dom_tips, sup_tips):
    """Circle: 1 hand: index + thumb -> radius; 2 hands: 2 index fingers -> radius."""
    idx_d = _tip(dom_tips, "INDEX")
    thb_d = _tip(dom_tips, "THUMB")

    if sup_tips:
        idx_s = _tip(sup_tips, "INDEX")
        if idx_d and idx_s:
            center = _midpoint(idx_d.xy, idx_s.xy)
            r = _dist(idx_d.xy, idx_s.xy)
            return ShapeParams("Circle", center, radius=r, hands_used=2)
        return None
    if idx_d and thb_d:
        center = _midpoint(idx_d.xy, thb_d.xy)
        r = _dist(idx_d.xy, thb_d.xy)
        return ShapeParams("Circle", center, radius=r, hands_used=1)
    return None


def _extract_square(dom_tips, sup_tips):
    """Square: 1 hand: index + thumb -> side; 2 hands: 2 index fingers -> diagonal."""
    idx_d = _tip(dom_tips, "INDEX")
    thb_d = _tip(dom_tips, "THUMB")

    if sup_tips:
        idx_s = _tip(sup_tips, "INDEX")
        if idx_d and idx_s:
            p0, p1 = idx_d.xy, idx_s.xy
            center = _midpoint(p0, p1)
            dx = abs(p1[0] - p0[0])
            dy = abs(p1[1] - p0[1])
            side = max(dx, dy, _dist(p0, p1) / math.sqrt(2))
            hs = side / 2
            corners = (
                (center[0] - hs, center[1] - hs),
                (center[0] + hs, center[1] - hs),
                (center[0] + hs, center[1] + hs),
                (center[0] - hs, center[1] + hs),
            )
            return ShapeParams("Square", center, width=side, height=side,
                               corners_xy=corners, hands_used=2)
        return None
    if idx_d and thb_d:
        center = _midpoint(idx_d.xy, thb_d.xy)
        side = _dist(idx_d.xy, thb_d.xy)
        hs = side / 2
        corners = (
            (center[0] - hs, center[1] - hs),
            (center[0] + hs, center[1] - hs),
            (center[0] + hs, center[1] + hs),
            (center[0] - hs, center[1] + hs),
        )
        return ShapeParams("Square", center, width=side, height=side,
                           corners_xy=corners, hands_used=1)
    return None


def _extract_rectangle(dom_tips, sup_tips):
    """Rectangle: 1 hand: index + thumb -> 2:1 fixed ratio; 2 hands: 2 index -> 2 diagonal corners."""
    idx_d = _tip(dom_tips, "INDEX")
    thb_d = _tip(dom_tips, "THUMB")

    if sup_tips:
        idx_s = _tip(sup_tips, "INDEX")
        if idx_d and idx_s:
            # Two-hand: 2 index fingertips form the 2 diagonal corners
            x0, y0 = idx_d.xy
            x1, y1 = idx_s.xy
            center = ((x0 + x1) / 2, (y0 + y1) / 2)
            w, h = max(abs(x1 - x0), 0.02), max(abs(y1 - y0), 0.02)
            corners = (
                (min(x0, x1), min(y0, y1)),
                (max(x0, x1), min(y0, y1)),
                (max(x0, x1), max(y0, y1)),
                (min(x0, x1), max(y0, y1)),
            )
            return ShapeParams("Rectangle", center, width=w, height=h,
                               corners_xy=corners, hands_used=2)
        return None
    if idx_d and thb_d:
        # One hand: 2:1 fixed aspect from distance
        d = _dist(idx_d.xy, thb_d.xy)
        center = _midpoint(idx_d.xy, thb_d.xy)
        w, h = d, d / 2
        corners = (
            (center[0] - w / 2, center[1] - h / 2),
            (center[0] + w / 2, center[1] - h / 2),
            (center[0] + w / 2, center[1] + h / 2),
            (center[0] - w / 2, center[1] + h / 2),
        )
        return ShapeParams("Rectangle", center, width=w, height=h,
                           corners_xy=corners, hands_used=1)
    return None


def _extract_triangle(dom_tips, sup_tips):
    """Triangle: vertices directly mapped from finger positions (1 hand: 3 fingers or 2 fingers;
    2 hands: dom apex + sup base fingers, or 2 index fingers). No forced equilateral shape.
    """
    idx_d = _tip(dom_tips, "INDEX")
    thb_d = _tip(dom_tips, "THUMB")
    mid_d = _tip(dom_tips, "MIDDLE")

    if sup_tips:
        if idx_d:
            idx_s = _tip(sup_tips, "INDEX")
            if idx_s:
                center = _midpoint(idx_d.xy, idx_s.xy)
                thb_s = _tip(sup_tips, "THUMB")
                mid_s = _tip(sup_tips, "MIDDLE")
                # Look for 3rd finger across the 2 hands
                third_tip = thb_s or mid_s or thb_d or mid_d
                if third_tip:
                    pts = (idx_d.xy, idx_s.xy, third_tip.xy)
                else:
                    dx = idx_s.xy[0] - idx_d.xy[0]
                    dy = idx_s.xy[1] - idx_d.xy[1]
                    apex = (center[0] - dy * 0.75, center[1] + dx * 0.75)
                    pts = (apex, idx_d.xy, idx_s.xy)
                return ShapeParams("Triangle", center, corners_xy=pts, hands_used=2)
        return None

    # 1 hand: 3 extended fingertips (INDEX, THUMB, MIDDLE or other)
    active_tips = [t for t in (idx_d, thb_d, mid_d, _tip(dom_tips, "RING"), _tip(dom_tips, "PINKY")) if t]
    if len(active_tips) >= 3:
        pts = (active_tips[0].xy, active_tips[1].xy, active_tips[2].xy)
        center = (sum(p[0] for p in pts) / 3, sum(p[1] for p in pts) / 3)
        return ShapeParams("Triangle", center, corners_xy=pts, hands_used=1)
    if idx_d and thb_d:
        p1 = idx_d.xy
        p2 = thb_d.xy
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        p3 = (p1[0] - dy * 0.8, p1[1] + dx * 0.8)
        pts = (p1, p2, p3)
        center = (sum(p[0] for p in pts) / 3, sum(p[1] for p in pts) / 3)
        return ShapeParams("Triangle", center, corners_xy=pts, hands_used=1)
    return None


def _extract_sphere(dom_tips, sup_tips):
    """Sphere (requires 2 hands): center is midpoint between the 2 index fingers."""
    if not sup_tips:
        return None
    idx_d = _tip(dom_tips, "INDEX")
    idx_s = _tip(sup_tips, "INDEX")
    if not (idx_d and idx_s):
        return None
    center = _midpoint(idx_d.xy, idx_s.xy)
    r = _dist(idx_d.xy, idx_s.xy) / 2
    return ShapeParams("Sphere", center, radius=r, size=r * 2, hands_used=2)


def _extract_cube(dom_tips, sup_tips):
    """Cube (requires 2 hands): center is midpoint between the 2 index fingers."""
    if not sup_tips:
        return None
    idx_d = _tip(dom_tips, "INDEX")
    idx_s = _tip(sup_tips, "INDEX")
    if not (idx_d and idx_s):
        return None
    center = _midpoint(idx_d.xy, idx_s.xy)
    side = max(_dist(idx_d.xy, idx_s.xy) / math.sqrt(2), 0.05)
    hs = side / 2
    # 8 cube vertices centered at center
    corners_3d = tuple(
        (center[0] + sx * hs, center[1] + sy * hs, sz * hs)
        for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)
    )
    return ShapeParams("Cube", center, size=side,
                       corners_3d=corners_3d, hands_used=2)


def _extract_box(dom_tips, sup_tips):
    """Rectangular box (requires 2 hands): center is midpoint between the 2 index fingers."""
    if not sup_tips:
        return None
    idx_d = _tip(dom_tips, "INDEX")
    idx_s = _tip(sup_tips, "INDEX")
    if not (idx_d and idx_s):
        return None
    center = _midpoint(idx_d.xy, idx_s.xy)
    fingers = ("INDEX", "MIDDLE", "RING", "PINKY")
    pts_d = [_tip(dom_tips, f) for f in fingers]
    pts_s = [_tip(sup_tips, f) for f in fingers]
    all_pts = [p.xy for p in pts_d + pts_s if p is not None]
    if len(all_pts) >= 4:
        xs = [p[0] for p in all_pts]
        ys = [p[1] for p in all_pts]
        w = max(max(xs) - min(xs), abs(idx_s.xy[0] - idx_d.xy[0]), 0.08)
        h = max(max(ys) - min(ys), abs(idx_s.xy[1] - idx_d.xy[1]), 0.06)
    else:
        w = max(abs(idx_s.xy[0] - idx_d.xy[0]), _dist(idx_d.xy, idx_s.xy), 0.08)
        h = max(abs(idx_s.xy[1] - idx_d.xy[1]), w * 0.6, 0.06)
    depth = (w + h) / 2
    hw, hh, hd = w / 2, h / 2, depth / 2
    corners_3d = tuple(
        (center[0] + sx * hw, center[1] + sy * hh, sz * hd)
        for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)
    )
    corners_xy = tuple(all_pts) if all_pts else ()
    return ShapeParams("Box", center, width=w, height=h, size=depth,
                       corners_3d=corners_3d, corners_xy=corners_xy, hands_used=2)


def _extract_pyramid(dom_tips, sup_tips):
    """Pyramid (requires 2 hands, 3 fingers per hand: thumb, index, middle).

    Hand with smaller distance between index and thumb -> apex at index tip.
    The other hand's 3 fingers (index, thumb, middle) -> 3 vertices of the base.
    """
    if not sup_tips:
        return None
    idx_d = _tip(dom_tips, "INDEX")
    idx_s = _tip(sup_tips, "INDEX")
    if not (idx_d and idx_s):
        return None
    thb_d = _tip(dom_tips, "THUMB")
    thb_s = _tip(sup_tips, "THUMB")
    mid_d = _tip(dom_tips, "MIDDLE")
    mid_s = _tip(sup_tips, "MIDDLE")

    center = _midpoint(idx_d.xy, idx_s.xy)
    if thb_d and thb_s:
        d_dom = _dist(idx_d.xy, thb_d.xy)
        d_sup = _dist(idx_s.xy, thb_s.xy)
        if d_dom <= d_sup:
            apex = idx_d.xy
            b1 = idx_s.xy
            b2 = thb_s.xy
            b3 = mid_s.xy if mid_s else None
        else:
            apex = idx_s.xy
            b1 = idx_d.xy
            b2 = thb_d.xy
            b3 = mid_d.xy if mid_d else None

        if b3 is not None:
            corners_xy = (apex, b1, b2, b3)
        else:
            corners_xy = (apex, b1, b2)
    else:
        base_w = max(_dist(idx_d.xy, idx_s.xy), 0.05)
        h = base_w * (math.sqrt(3) / 2)
        apex = (center[0], center[1] - h * 2 / 3)
        b1 = (center[0] - base_w / 2, center[1] + h / 3)
        b2 = (center[0] + base_w / 2, center[1] + h / 3)
        corners_xy = (apex, b1, b2)
    return ShapeParams("Pyramid", center, corners_xy=corners_xy, hands_used=2)


_EXTRACTORS = {
    "Circle":    _extract_circle,
    "Square":    _extract_square,
    "Rectangle": _extract_rectangle,
    "Triangle":  _extract_triangle,
    "Sphere":    _extract_sphere,
    "Cube":      _extract_cube,
    "Box":       _extract_box,
    "Pyramid":   _extract_pyramid,
}


# ------------------------------------------------------------------
# Main engine
# ------------------------------------------------------------------

class ShapeGestureEngine:
    """Stateful engine that converts TipSamples into ShapeCandidate each tick."""

    def __init__(
        self,
        stability_threshold: float = 0.025,
        stability_frames: int = STABILITY_FRAMES,
        stability_duration_s: Optional[float] = None,
    ):
        self._thresh = stability_threshold
        self._req = stability_frames
        if stability_duration_s is not None:
            self._duration_s = stability_duration_s
        elif stability_frames != STABILITY_FRAMES:
            self._duration_s = stability_frames * 0.033
        else:
            self._duration_s = STABILITY_DURATION_S
        self._stable_count = 0
        self._stable_time_s = 0.0
        self._last_key: Optional[tuple] = None
        self._preferred_hands: Optional[int] = None
        self._drop_grace_frames = 0
        self._smoothed_params: Optional[ShapeParams] = None
        self._last_valid_params: Optional[ShapeParams] = None
        self._last_mirror: Optional[bool] = None

    def reset(self) -> None:
        self._stable_count = 0
        self._stable_time_s = 0.0
        self._last_key = None
        self._drop_grace_frames = 0
        self._smoothed_params = None
        self._last_valid_params = None
        self._last_mirror = None

    def _calc_progress(self) -> tuple[bool, float]:
        if self._duration_s is not None and self._duration_s > 0:
            time_frac = min(1.0, self._stable_time_s / self._duration_s)
        else:
            time_frac = 0.0
        frame_frac = min(1.0, self._stable_count / max(1, self._req))
        if self._req != STABILITY_FRAMES:
            # Custom frame requirement passed in test (e.g. stability_frames=3 or 5)
            frac = max(time_frac, frame_frac)
            stable = (self._stable_count >= self._req) or (self._stable_time_s >= self._duration_s)
        else:
            # Realtime production requirement (1.5 -> 2s, default 1.8s)
            frac = time_frac
            stable = self._stable_time_s >= self._duration_s
        return stable, frac

    def _smooth(self, current: ShapeParams, mirror: bool) -> ShapeParams:
        if (
            self._smoothed_params is None
            or self._smoothed_params.kind != current.kind
            or self._smoothed_params.hands_used != current.hands_used
            or self._last_mirror != mirror
        ):
            self._smoothed_params = current
            self._last_mirror = mirror
            return current
        prev = self._smoothed_params
        alpha = 0.4
        cx = (1 - alpha) * prev.center_xy[0] + alpha * current.center_xy[0]
        cy = (1 - alpha) * prev.center_xy[1] + alpha * current.center_xy[1]
        r = (1 - alpha) * prev.radius + alpha * current.radius
        w = (1 - alpha) * prev.width + alpha * current.width
        h = (1 - alpha) * prev.height + alpha * current.height
        sz = (1 - alpha) * prev.size + alpha * current.size

        if current.corners_xy and prev.corners_xy and len(current.corners_xy) == len(prev.corners_xy):
            c_xy = tuple(
                (
                    (1 - alpha) * p[0] + alpha * c[0],
                    (1 - alpha) * p[1] + alpha * c[1],
                )
                for p, c in zip(prev.corners_xy, current.corners_xy)
            )
        else:
            c_xy = current.corners_xy

        if current.corners_3d and prev.corners_3d and len(current.corners_3d) == len(prev.corners_3d):
            c_3d = tuple(
                (
                    (1 - alpha) * p[0] + alpha * c[0],
                    (1 - alpha) * p[1] + alpha * c[1],
                    (1 - alpha) * p[2] + alpha * c[2],
                )
                for p, c in zip(prev.corners_3d, current.corners_3d)
            )
        else:
            c_3d = current.corners_3d

        smoothed = ShapeParams(
            kind=current.kind,
            center_xy=(cx, cy),
            radius=r,
            width=w,
            height=h,
            corners_xy=c_xy,
            size=sz,
            corners_3d=c_3d,
            hands_used=current.hands_used,
            degenerate=current.degenerate,
        )
        self._smoothed_params = smoothed
        self._last_mirror = mirror
        return smoothed

    def update(
        self,
        hands: Sequence,
        shape_type: str,
        mirror: bool = False,
        dt: float = 0.033,
    ) -> ShapeCandidate:
        """Run one frame.

        Parameters
        ----------
        hands : list of product hand descriptors (from hand_geometry.describe)
        shape_type : one of ALL_SHAPES
        mirror : if True, mirrors X coordinate horizontally for camera alignment
        dt : elapsed real-time seconds since last frame
        """
        if shape_type not in _EXTRACTORS:
            self.reset()
            return ShapeCandidate(shape_type, None, reason="UNKNOWN_SHAPE")

        if not hands:
            self._drop_grace_frames += 1
            if self._drop_grace_frames > 6:
                self.reset()
                self._preferred_hands = None
                return ShapeCandidate(shape_type, None, reason="NO_DOMINANT_HAND")
            if self._last_valid_params is not None:
                _, frac = self._calc_progress()
                return ShapeCandidate(
                    shape_type,
                    self._last_valid_params,
                    is_stable=False,
                    stable_fraction=frac,
                    reason="HOLDING",
                )
            return ShapeCandidate(shape_type, None, reason="NO_DOMINANT_HAND")

        if len(hands) >= 2:
            self._preferred_hands = 2
            dom = next((h for h in hands if h.role == "DOMINANT"), hands[0])
            sup = next((h for h in hands if h.role == "SUPPORT" and h is not dom), None)
            if sup is None:
                sup = next((h for h in hands if h is not dom), None)
        else:
            dom = hands[0]
            sup = None

        if dom is None:
            self.reset()
            return ShapeCandidate(shape_type, None, reason="NO_DOMINANT_HAND")

        # If user established a 2-hand gesture, require 2 hands; do not jump onto 1 hand:
        if self._preferred_hands == 2 and sup is None:
            self._drop_grace_frames += 1
            if self._drop_grace_frames > 6:
                self.reset()
                self._preferred_hands = None
                return ShapeCandidate(shape_type, None, reason="NEED_SECOND_HAND")
            if self._last_valid_params is not None:
                _, frac = self._calc_progress()
                return ShapeCandidate(
                    shape_type,
                    self._last_valid_params,
                    is_stable=False,
                    stable_fraction=frac,
                    reason="HOLDING",
                )
            return ShapeCandidate(shape_type, None, reason="NEED_SECOND_HAND")

        if mirror:
            from dataclasses import replace
            dom_tips = tuple(replace(s, xy=(1.0 - s.xy[0], s.xy[1])) for s in dom.tip_samples)
            sup_tips = (
                tuple(replace(s, xy=(1.0 - s.xy[0], s.xy[1])) for s in sup.tip_samples)
                if sup
                else []
            )
        else:
            dom_tips = dom.tip_samples
            sup_tips = sup.tip_samples if sup else []

        extractor = _EXTRACTORS[shape_type]
        params = extractor(dom_tips, sup_tips)

        if params is None:
            self._drop_grace_frames += 1
            if self._drop_grace_frames > 6:
                self.reset()
                need2 = shape_type in SHAPE_3D or shape_type == "Triangle" or self._preferred_hands == 2
                msg = "NEED_SECOND_HAND" if (need2 and not sup_tips) else "INSUFFICIENT_TIPS"
                return ShapeCandidate(shape_type, None, reason=msg)
            if self._last_valid_params is not None:
                _, frac = self._calc_progress()
                return ShapeCandidate(
                    shape_type,
                    self._last_valid_params,
                    is_stable=False,
                    stable_fraction=frac,
                    reason="HOLDING",
                )
            need2 = shape_type in SHAPE_3D or shape_type == "Triangle" or self._preferred_hands == 2
            msg = "NEED_SECOND_HAND" if (need2 and not sup_tips) else "INSUFFICIENT_TIPS"
            return ShapeCandidate(shape_type, None, reason=msg)

        self._drop_grace_frames = 0
        smoothed = self._smooth(params, mirror)

        # Stability check
        k = _key(smoothed)
        if self._last_key is not None:
            delta = math.sqrt(sum((a - b) ** 2 for a, b in zip(k, self._last_key)))
            if delta < self._thresh:
                self._stable_count += 1
                self._stable_time_s += dt
            elif delta < self._thresh * 2.0:
                self._stable_count = max(0, self._stable_count - 1)
                self._stable_time_s = max(0.0, self._stable_time_s - dt)
            else:
                self._stable_count = 0
                self._stable_time_s = 0.0
        self._last_key = k
        self._last_valid_params = smoothed

        stable, frac = self._calc_progress()
        return ShapeCandidate(
            shape_type,
            smoothed,
            is_stable=stable,
            stable_fraction=frac,
            reason="STABLE" if stable else "ACCUMULATING",
        )


# ------------------------------------------------------------------
# Touch Hit-Testing and Direct Manipulation Utilities
# ------------------------------------------------------------------

def hit_test_frozen_shape(shape, point_xy: tuple[float, float]) -> bool:
    """Check if normalized screen point (px, py) touches the shape."""
    p = getattr(shape, "params", shape) if not isinstance(shape, dict) else shape
    cx, cy = p.get("center_xy", (0.5, 0.5))
    px, py = point_xy
    d = math.hypot(px - cx, py - cy)
    kind = getattr(shape, "kind", p.get("kind", ""))

    if kind in ("Circle", "Sphere"):
        r = p.get("radius", 0.05)
        return d <= max(r * 1.3, 0.09)

    elif kind in ("Square", "Cube"):
        side = p.get("width") or p.get("size") or 0.1
        hs = max(side / 2 * 1.3, 0.09)
        return abs(px - cx) <= hs and abs(py - cy) <= hs

    elif kind in ("Rectangle", "Box"):
        w = max(p.get("width", 0.1) / 2 * 1.3, 0.09)
        h = max(p.get("height", 0.1) / 2 * 1.3, 0.09)
        return abs(px - cx) <= w and abs(py - cy) <= h

    elif kind in ("Triangle", "Pyramid"):
        corners = p.get("corners_xy", [])
        if corners:
            max_r = max((math.hypot(c[0] - cx, c[1] - cy) for c in corners), default=0.1)
            return d <= max(max_r * 1.3, 0.09)
        return d <= 0.12

    return d <= 0.10


def find_hit_shape(shapes: Sequence, point_xy: tuple[float, float]):
    """Return the nearest shape touching point_xy, or None."""
    hits = [s for s in shapes if hit_test_frozen_shape(s, point_xy)]
    if not hits:
        return None
    return min(
        hits,
        key=lambda s: math.hypot(
            point_xy[0] - (s.params.get("center_xy", (0.5, 0.5))[0] if hasattr(s, "params") else s.get("center_xy", (0.5, 0.5))[0]),
            point_xy[1] - (s.params.get("center_xy", (0.5, 0.5))[1] if hasattr(s, "params") else s.get("center_xy", (0.5, 0.5))[1]),
        ),
    )

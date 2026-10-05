"""Pure gesture-mapping mathematics."""

from __future__ import annotations

import math


Point2D = tuple[float, float]


def distance_xy(
    a: Point2D,
    b: Point2D,
) -> float:
    """Return finite Euclidean distance in x/y."""

    _require_finite_point(
        a,
        name="a",
    )
    _require_finite_point(
        b,
        name="b",
    )

    return math.hypot(
        b[0] - a[0],
        b[1] - a[1],
    )


def normalized_pinch_ratio(
    *,
    thumb_xy: Point2D,
    index_xy: Point2D,
    scale_a_xy: Point2D,
    scale_b_xy: Point2D,
    epsilon: float,
) -> float:
    """Return thumb-index distance normalized by hand scale."""

    _require_positive_finite(
        epsilon,
        name="epsilon",
    )

    pinch_distance = distance_xy(
        thumb_xy,
        index_xy,
    )

    hand_scale = distance_xy(
        scale_a_xy,
        scale_b_xy,
    )

    denominator = max(
        hand_scale,
        epsilon,
    )

    ratio = (
        pinch_distance
        / denominator
    )

    if (
        not math.isfinite(ratio)
        or ratio < 0.0
    ):
        raise RuntimeError(
            "normalized pinch ratio became invalid"
        )

    return ratio


def apply_deadzone(
    value: float,
    *,
    deadzone: float,
) -> float:
    """Apply the continuous deadzone D(a, z)."""

    _require_finite(
        value,
        name="value",
    )

    _require_nonnegative_finite(
        deadzone,
        name="deadzone",
    )

    magnitude = abs(value)

    if magnitude <= deadzone:
        return 0.0

    return math.copysign(
        magnitude - deadzone,
        value,
    )


def bounded_rotation_delta(
    *,
    delta_x: float,
    delta_y: float,
    deadzone: float,
    gain: float,
    max_delta_rad: float,
) -> tuple[float, float]:
    """Map pointer displacement to bounded yaw/pitch deltas."""

    _require_finite(
        delta_x,
        name="delta_x",
    )

    _require_finite(
        delta_y,
        name="delta_y",
    )

    _require_nonnegative_finite(
        deadzone,
        name="deadzone",
    )

    _require_nonnegative_finite(
        gain,
        name="gain",
    )

    _require_positive_finite(
        max_delta_rad,
        name="max_delta_rad",
    )

    yaw = gain * apply_deadzone(
        delta_x,
        deadzone=deadzone,
    )

    pitch = -gain * apply_deadzone(
        delta_y,
        deadzone=deadzone,
    )

    return (
        _clip_symmetric(
            yaw,
            max_abs=max_delta_rad,
        ),
        _clip_symmetric(
            pitch,
            max_abs=max_delta_rad,
        ),
    )


def bounded_scale_delta(
    *,
    current_ratio: float,
    previous_ratio: float,
    deadzone: float,
    gain: float,
    max_delta: float,
) -> float:
    """Map normalized pinch-ratio change to bounded scale delta."""

    _require_nonnegative_finite(
        current_ratio,
        name="current_ratio",
    )

    _require_nonnegative_finite(
        previous_ratio,
        name="previous_ratio",
    )

    _require_nonnegative_finite(
        deadzone,
        name="deadzone",
    )

    _require_nonnegative_finite(
        gain,
        name="gain",
    )

    _require_positive_finite(
        max_delta,
        name="max_delta",
    )

    ratio_delta = (
        current_ratio
        - previous_ratio
    )

    mapped = gain * apply_deadzone(
        ratio_delta,
        deadzone=deadzone,
    )

    return _clip_symmetric(
        mapped,
        max_abs=max_delta,
    )


def _clip_symmetric(
    value: float,
    *,
    max_abs: float,
) -> float:
    return max(
        -max_abs,
        min(
            value,
            max_abs,
        ),
    )


def _require_finite_point(
    point: Point2D,
    *,
    name: str,
) -> None:
    if (
        len(point) != 2
        or not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            for value in point
        )
    ):
        raise ValueError(
            f"{name} must contain two finite numeric values"
        )


def _require_finite(
    value: float,
    *,
    name: str,
) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError(
            f"{name} must be finite"
        )


def _require_nonnegative_finite(
    value: float,
    *,
    name: str,
) -> None:
    _require_finite(
        value,
        name=name,
    )

    if value < 0.0:
        raise ValueError(
            f"{name} must be non-negative"
        )


def _require_positive_finite(
    value: float,
    *,
    name: str,
) -> None:
    _require_finite(
        value,
        name=name,
    )

    if value <= 0.0:
        raise ValueError(
            f"{name} must be positive"
        )
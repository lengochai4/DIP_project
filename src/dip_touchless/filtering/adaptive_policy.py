"""Pure policy functions for the bounded adaptive 1-Euro F2 path."""

from __future__ import annotations

import math

from dip_touchless.core import MeasurementQuality


def _finite_number(
    value: float,
    *,
    name: str,
) -> float:
    if isinstance(value, bool):
        raise ValueError(
            f"{name} must be a finite number"
        )

    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{name} must be a finite number"
        ) from exc

    if not math.isfinite(numeric):
        raise ValueError(
            f"{name} must be finite"
        )

    return numeric


def adaptive_beta(
    *,
    speed: float,
    beta_min: float,
    beta_base: float,
    beta_max: float,
    velocity_gain: float,
    velocity_max: float | None,
) -> float:
    """Map filtered derivative speed to bounded adaptive beta."""

    speed = _finite_number(
        speed,
        name="speed",
    )
    beta_min = _finite_number(
        beta_min,
        name="beta_min",
    )
    beta_base = _finite_number(
        beta_base,
        name="beta_base",
    )
    beta_max = _finite_number(
        beta_max,
        name="beta_max",
    )
    velocity_gain = _finite_number(
        velocity_gain,
        name="velocity_gain",
    )

    if speed < 0.0:
        raise ValueError(
            "speed must be non-negative"
        )

    if beta_min < 0.0:
        raise ValueError(
            "beta_min must be non-negative"
        )

    if not (
        beta_min
        <= beta_base
        <= beta_max
    ):
        raise ValueError(
            "beta bounds must satisfy "
            "beta_min <= beta_base <= beta_max"
        )

    if velocity_gain < 0.0:
        raise ValueError(
            "velocity_gain must be non-negative"
        )

    if velocity_max is None:
        beta_speed = speed
    else:
        velocity_max = _finite_number(
            velocity_max,
            name="velocity_max",
        )

        if velocity_max <= 0.0:
            raise ValueError(
                "velocity_max must be positive "
                "when enabled"
            )

        beta_speed = min(
            speed,
            velocity_max,
        )

    if velocity_gain == 0.0:
        return beta_base

    # Avoid overflow for extreme but finite speed.
    headroom = beta_max - beta_base

    if headroom <= 0.0:
        return beta_max

    saturation_speed = (
        headroom / velocity_gain
    )

    if beta_speed >= saturation_speed:
        return beta_max

    candidate = (
        beta_base
        + velocity_gain * beta_speed
    )

    return min(
        max(candidate, beta_min),
        beta_max,
    )


def effective_min_cutoff_hz(
    *,
    base_cutoff_hz: float,
    quality_adaptation_enabled: bool,
    quality: MeasurementQuality,
    quality_low_cutoff_hz: float | None,
    quality_high_cutoff_hz: float | None,
) -> float:
    """Return the effective adaptive minimum cutoff.

    Unavailable/invalid quality falls back to the configured base cutoff.
    No synthetic quality value is created.
    """

    base_cutoff_hz = _finite_number(
        base_cutoff_hz,
        name="base_cutoff_hz",
    )

    if base_cutoff_hz <= 0.0:
        raise ValueError(
            "base_cutoff_hz must be positive"
        )

    if not quality_adaptation_enabled:
        return base_cutoff_hz

    if (
        quality_low_cutoff_hz is None
        or quality_high_cutoff_hz is None
    ):
        raise ValueError(
            "quality cutoff bounds are required "
            "when quality adaptation is enabled"
        )

    low = _finite_number(
        quality_low_cutoff_hz,
        name="quality_low_cutoff_hz",
    )
    high = _finite_number(
        quality_high_cutoff_hz,
        name="quality_high_cutoff_hz",
    )

    if low <= 0.0:
        raise ValueError(
            "quality_low_cutoff_hz "
            "must be positive"
        )

    if high < low:
        raise ValueError(
            "quality cutoff bounds must satisfy "
            "low <= high"
        )

    if (
        not quality.valid
        or quality.value is None
    ):
        return base_cutoff_hz

    quality_value = _finite_number(
        quality.value,
        name="quality.value",
    )

    if not 0.0 <= quality_value <= 1.0:
        raise ValueError(
            "quality.value must be in [0, 1]"
        )

    return (
        low
        + quality_value
        * (high - low)
    )


def bounded_final_cutoff_hz(
    *,
    min_cutoff_hz: float,
    beta: float,
    speed: float,
    final_cutoff_min_hz: float,
    final_cutoff_max_hz: float,
) -> float:
    """Calculate and clip the final adaptive signal cutoff."""

    min_cutoff_hz = _finite_number(
        min_cutoff_hz,
        name="min_cutoff_hz",
    )
    beta = _finite_number(
        beta,
        name="beta",
    )
    speed = _finite_number(
        speed,
        name="speed",
    )
    lower = _finite_number(
        final_cutoff_min_hz,
        name="final_cutoff_min_hz",
    )
    upper = _finite_number(
        final_cutoff_max_hz,
        name="final_cutoff_max_hz",
    )

    if min_cutoff_hz <= 0.0:
        raise ValueError(
            "min_cutoff_hz must be positive"
        )

    if beta < 0.0:
        raise ValueError(
            "beta must be non-negative"
        )

    if speed < 0.0:
        raise ValueError(
            "speed must be non-negative"
        )

    if not (
        0.0 < lower < upper
    ):
        raise ValueError(
            "final cutoff bounds must satisfy "
            "0 < min < max"
        )

    # Candidate already above the upper bound.
    if min_cutoff_hz >= upper:
        return upper

    if beta == 0.0:
        return min(
            max(min_cutoff_hz, lower),
            upper,
        )

    # Avoid overflow from beta * speed.
    headroom = (
        upper - min_cutoff_hz
    )

    if speed >= headroom / beta:
        return upper

    candidate = (
        min_cutoff_hz
        + beta * speed
    )

    return min(
        max(candidate, lower),
        upper,
    )
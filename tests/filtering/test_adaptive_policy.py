import math

import pytest

from dip_touchless.core import (
    MeasurementQuality,
)
from dip_touchless.filtering.adaptive_policy import (
    adaptive_beta,
    bounded_final_cutoff_hz,
    effective_min_cutoff_hz,
)


def _beta(
    speed: float,
    *,
    velocity_max: float | None = 10.0,
) -> float:
    return adaptive_beta(
        speed=speed,
        beta_min=0.1,
        beta_base=0.2,
        beta_max=1.0,
        velocity_gain=0.1,
        velocity_max=velocity_max,
    )


def test_zero_speed_returns_beta_base() -> None:
    assert _beta(0.0) == pytest.approx(
        0.2
    )


def test_beta_is_nondecreasing_with_speed() -> None:
    speeds = [
        0.0,
        0.5,
        1.0,
        2.0,
        5.0,
        10.0,
        100.0,
    ]

    values = [
        _beta(speed)
        for speed in speeds
    ]

    assert all(
        later >= earlier
        for earlier, later in zip(
            values,
            values[1:],
        )
    )


def test_beta_never_exceeds_configured_bounds() -> None:
    for speed in [
        0.0,
        1.0,
        10.0,
        1e100,
        1e308,
    ]:
        value = _beta(speed)

        assert 0.1 <= value <= 1.0


def test_velocity_max_limits_beta_adaptation_input() -> None:
    limited = _beta(
        100.0,
        velocity_max=2.0,
    )

    at_limit = _beta(
        2.0,
        velocity_max=2.0,
    )

    assert limited == pytest.approx(
        at_limit
    )


def test_velocity_limit_can_be_disabled() -> None:
    value = _beta(
        3.0,
        velocity_max=None,
    )

    assert value == pytest.approx(
        0.5
    )


def test_extreme_finite_speed_saturates_beta_safely() -> None:
    value = adaptive_beta(
        speed=1e308,
        beta_min=0.0,
        beta_base=0.1,
        beta_max=0.8,
        velocity_gain=1e308,
        velocity_max=None,
    )

    assert value == pytest.approx(
        0.8
    )

    assert math.isfinite(value)


@pytest.mark.parametrize(
    "speed",
    [
        -1.0,
        float("nan"),
        float("inf"),
    ],
)
def test_invalid_speed_is_rejected(
    speed: float,
) -> None:
    with pytest.raises(ValueError):
        _beta(speed)


def test_unavailable_quality_uses_base_cutoff() -> None:
    result = effective_min_cutoff_hz(
        base_cutoff_hz=1.5,
        quality_adaptation_enabled=True,
        quality=MeasurementQuality.unavailable(),
        quality_low_cutoff_hz=0.5,
        quality_high_cutoff_hz=2.0,
    )

    assert result == pytest.approx(
        1.5
    )


def test_disabled_quality_adaptation_uses_base_cutoff() -> None:
    result = effective_min_cutoff_hz(
        base_cutoff_hz=1.5,
        quality_adaptation_enabled=False,
        quality=MeasurementQuality.unavailable(),
        quality_low_cutoff_hz=None,
        quality_high_cutoff_hz=None,
    )

    assert result == pytest.approx(
        1.5
    )


def test_final_cutoff_uses_candidate_inside_bounds() -> None:
    result = bounded_final_cutoff_hz(
        min_cutoff_hz=1.0,
        beta=0.5,
        speed=2.0,
        final_cutoff_min_hz=0.5,
        final_cutoff_max_hz=10.0,
    )

    assert result == pytest.approx(
        2.0
    )


def test_final_cutoff_clips_to_lower_bound() -> None:
    result = bounded_final_cutoff_hz(
        min_cutoff_hz=0.5,
        beta=0.0,
        speed=0.0,
        final_cutoff_min_hz=1.0,
        final_cutoff_max_hz=10.0,
    )

    assert result == pytest.approx(
        1.0
    )


def test_final_cutoff_clips_to_upper_bound() -> None:
    result = bounded_final_cutoff_hz(
        min_cutoff_hz=1.0,
        beta=1.0,
        speed=100.0,
        final_cutoff_min_hz=0.5,
        final_cutoff_max_hz=8.0,
    )

    assert result == pytest.approx(
        8.0
    )


def test_extreme_finite_speed_has_finite_bounded_cutoff() -> None:
    result = bounded_final_cutoff_hz(
        min_cutoff_hz=1.0,
        beta=1e308,
        speed=1e308,
        final_cutoff_min_hz=0.5,
        final_cutoff_max_hz=12.0,
    )

    assert result == pytest.approx(
        12.0
    )

    assert math.isfinite(result)
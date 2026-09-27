import math

import pytest

from dip_touchless.core import (
    CoordinateSpace,
    Landmark,
)
from dip_touchless.filtering import (
    AdaptiveOneEuroLandmarkCore,
    adaptive_beta,
    bounded_final_cutoff_hz,
    low_pass_alpha,
)


def _landmark(
    index: int,
    x: float,
    y: float,
    z: float = -0.1,
) -> Landmark:
    return Landmark(
        index=index,
        x=x,
        y=y,
        z=z,
        coordinate_space=(
            CoordinateSpace.FRAME_NORMALIZED
        ),
    )


def _core(
    *,
    velocity_max: float | None = 10.0,
    final_cutoff_max_hz: float = 20.0,
) -> AdaptiveOneEuroLandmarkCore:
    return AdaptiveOneEuroLandmarkCore(
        base_cutoff_hz=1.0,
        beta_min=0.1,
        beta_base=0.2,
        beta_max=1.0,
        velocity_gain=0.5,
        velocity_max=velocity_max,
        final_cutoff_min_hz=0.5,
        final_cutoff_max_hz=(
            final_cutoff_max_hz
        ),
        derivative_cutoff_hz=1.0,
    )


def test_initialization_preserves_values_and_base_policy() -> None:
    core = _core()

    source = (
        _landmark(
            0,
            0.2,
            0.3,
            -0.11,
        ),
        _landmark(
            1,
            0.6,
            0.7,
            -0.22,
        ),
    )

    result = core.update(
        source,
        dt_s=None,
    )

    assert result.landmarks == source

    assert all(
        item.initialization_occurred
        for item in result.diagnostics
    )

    assert all(
        item.speed == pytest.approx(0.0)
        for item in result.diagnostics
    )

    assert all(
        item.beta == pytest.approx(0.2)
        for item in result.diagnostics
    )

    assert all(
        item.min_cutoff_hz
        == pytest.approx(1.0)
        for item in result.diagnostics
    )

    assert all(
        item.cutoff_hz
        == pytest.approx(1.0)
        for item in result.diagnostics
    )


def test_one_landmark_uses_adaptive_shared_xy_cutoff() -> None:
    core = _core()

    core.update(
        (
            _landmark(
                0,
                0.0,
                0.0,
            ),
        ),
        dt_s=None,
    )

    result = core.update(
        (
            _landmark(
                0,
                0.2,
                0.1,
            ),
        ),
        dt_s=0.1,
    )

    diag = result.diagnostics[0]

    derivative_alpha = low_pass_alpha(
        dt_s=0.1,
        cutoff_hz=1.0,
    )

    expected_dx = (
        derivative_alpha * 2.0
    )

    expected_dy = (
        derivative_alpha * 1.0
    )

    expected_speed = math.hypot(
        expected_dx,
        expected_dy,
    )

    expected_beta = adaptive_beta(
        speed=expected_speed,
        beta_min=0.1,
        beta_base=0.2,
        beta_max=1.0,
        velocity_gain=0.5,
        velocity_max=10.0,
    )

    expected_cutoff = (
        bounded_final_cutoff_hz(
            min_cutoff_hz=1.0,
            beta=expected_beta,
            speed=expected_speed,
            final_cutoff_min_hz=0.5,
            final_cutoff_max_hz=20.0,
        )
    )

    expected_signal_alpha = (
        low_pass_alpha(
            dt_s=0.1,
            cutoff_hz=expected_cutoff,
        )
    )

    assert diag.filtered_dx == pytest.approx(
        expected_dx
    )

    assert diag.filtered_dy == pytest.approx(
        expected_dy
    )

    assert diag.speed == pytest.approx(
        expected_speed
    )

    assert diag.beta == pytest.approx(
        expected_beta
    )

    assert diag.cutoff_hz == pytest.approx(
        expected_cutoff
    )

    assert diag.signal_alpha == pytest.approx(
        expected_signal_alpha
    )

    landmark = result.landmarks[0]

    assert landmark.x == pytest.approx(
        expected_signal_alpha * 0.2
    )

    assert landmark.y == pytest.approx(
        expected_signal_alpha * 0.1
    )


def test_landmarks_have_independent_adaptive_policy() -> None:
    core = _core()

    core.update(
        (
            _landmark(
                0,
                0.0,
                0.0,
            ),
            _landmark(
                1,
                0.5,
                0.5,
            ),
        ),
        dt_s=None,
    )

    result = core.update(
        (
            _landmark(
                0,
                0.3,
                0.0,
            ),
            _landmark(
                1,
                0.5,
                0.5,
            ),
        ),
        dt_s=0.1,
    )

    moving = result.diagnostics[0]
    stationary = result.diagnostics[1]

    assert moving.speed > 0.0
    assert moving.beta >= stationary.beta

    assert stationary.speed == pytest.approx(
        0.0
    )

    assert stationary.beta == pytest.approx(
        0.2
    )

    assert stationary.cutoff_hz == pytest.approx(
        1.0
    )


def test_velocity_max_limits_beta_but_not_real_speed() -> None:
    core = _core(
        velocity_max=0.1,
    )

    core.update(
        (
            _landmark(
                0,
                0.0,
                0.0,
            ),
        ),
        dt_s=None,
    )

    result = core.update(
        (
            _landmark(
                0,
                0.8,
                0.0,
            ),
        ),
        dt_s=0.1,
    )

    diag = result.diagnostics[0]

    assert diag.speed > 0.1

    expected_beta = adaptive_beta(
        speed=diag.speed,
        beta_min=0.1,
        beta_base=0.2,
        beta_max=1.0,
        velocity_gain=0.5,
        velocity_max=0.1,
    )

    assert diag.beta == pytest.approx(
        expected_beta
    )

    expected_cutoff = bounded_final_cutoff_hz(
        min_cutoff_hz=1.0,
        beta=expected_beta,
        speed=diag.speed,
        final_cutoff_min_hz=0.5,
        final_cutoff_max_hz=20.0,
    )

    assert diag.cutoff_hz == pytest.approx(
        expected_cutoff
    )


def test_extreme_motion_respects_final_cutoff_bound() -> None:
    core = _core(
        velocity_max=1.0,
        final_cutoff_max_hz=3.0,
    )

    core.update(
        (
            _landmark(
                0,
                0.0,
                0.0,
            ),
        ),
        dt_s=None,
    )

    result = core.update(
        (
            _landmark(
                0,
                1e100,
                0.0,
            ),
        ),
        dt_s=0.1,
    )

    diag = result.diagnostics[0]

    assert math.isfinite(
        diag.speed
    )

    assert diag.cutoff_hz == pytest.approx(
        3.0
    )


def test_effective_min_cutoff_can_be_supplied_per_frame() -> None:
    core = _core()

    result = core.update(
        (
            _landmark(
                0,
                0.2,
                0.3,
            ),
        ),
        dt_s=None,
        min_cutoff_hz=2.0,
    )

    diag = result.diagnostics[0]

    assert diag.min_cutoff_hz == pytest.approx(
        2.0
    )

    assert diag.cutoff_hz == pytest.approx(
        2.0
    )


def test_z_is_passed_through_without_filtering() -> None:
    core = _core()

    core.update(
        (
            _landmark(
                0,
                0.2,
                0.3,
                -0.1,
            ),
        ),
        dt_s=None,
    )

    result = core.update(
        (
            _landmark(
                0,
                0.4,
                0.5,
                -0.9,
            ),
        ),
        dt_s=0.1,
    )

    assert result.landmarks[0].z == pytest.approx(
        -0.9
    )


def test_derivative_uses_previous_filtered_xy() -> None:
    core = _core()

    core.update(
        (
            _landmark(
                0,
                0.0,
                0.0,
            ),
        ),
        dt_s=None,
    )

    second = core.update(
        (
            _landmark(
                0,
                1.0,
                0.0,
            ),
        ),
        dt_s=0.1,
    )

    third = core.update(
        (
            _landmark(
                0,
                1.0,
                0.0,
            ),
        ),
        dt_s=0.1,
    )

    previous_filtered_x = (
        second.landmarks[0].x
    )

    expected_raw_dx = (
        1.0 - previous_filtered_x
    ) / 0.1

    assert expected_raw_dx > 0.0

    derivative_alpha = low_pass_alpha(
        dt_s=0.1,
        cutoff_hz=1.0,
    )

    previous_filtered_dx = (
        second.diagnostics[0].filtered_dx
    )

    expected_filtered_dx = (
        derivative_alpha * expected_raw_dx
        + (1.0 - derivative_alpha)
        * previous_filtered_dx
    )

    assert (
        third.diagnostics[0].filtered_dx
        == pytest.approx(
            expected_filtered_dx
        )
    )


def test_reset_clears_all_landmark_state() -> None:
    core = _core()

    core.update(
        (
            _landmark(
                0,
                0.2,
                0.3,
            ),
        ),
        dt_s=None,
    )

    core.update(
        (
            _landmark(
                0,
                0.5,
                0.6,
            ),
        ),
        dt_s=0.1,
    )

    core.reset()

    assert core.initialized is False

    restarted = (
        _landmark(
            0,
            0.9,
            0.8,
        ),
    )

    result = core.update(
        restarted,
        dt_s=None,
    )

    assert result.landmarks == restarted

    assert (
        result.diagnostics[
            0
        ].initialization_occurred
        is True
    )


def test_index_order_change_is_rejected() -> None:
    core = _core()

    core.update(
        (
            _landmark(
                0,
                0.1,
                0.1,
            ),
            _landmark(
                1,
                0.2,
                0.2,
            ),
        ),
        dt_s=None,
    )

    with pytest.raises(ValueError):
        core.update(
            (
                _landmark(
                    1,
                    0.2,
                    0.2,
                ),
                _landmark(
                    0,
                    0.1,
                    0.1,
                ),
            ),
            dt_s=0.1,
        )


@pytest.mark.parametrize(
    "dt_s",
    [
        0.0,
        -0.1,
        math.inf,
        -math.inf,
        math.nan,
    ],
)
def test_invalid_dt_is_rejected(
    dt_s: float,
) -> None:
    core = _core()

    core.update(
        (
            _landmark(
                0,
                0.1,
                0.1,
            ),
        ),
        dt_s=None,
    )

    with pytest.raises(ValueError):
        core.update(
            (
                _landmark(
                    0,
                    0.2,
                    0.2,
                ),
            ),
            dt_s=dt_s,
        )
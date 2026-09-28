import math

import pytest

from dip_touchless.interaction import (
    apply_deadzone,
    bounded_rotation_delta,
    bounded_scale_delta,
    distance_xy,
    normalized_pinch_ratio,
)


def test_distance_xy() -> None:
    assert distance_xy(
        (0.0, 0.0),
        (3.0, 4.0),
    ) == pytest.approx(5.0)


def test_normalized_pinch_ratio() -> None:
    result = normalized_pinch_ratio(
        thumb_xy=(0.0, 0.0),
        index_xy=(0.3, 0.0),
        scale_a_xy=(0.0, 0.0),
        scale_b_xy=(1.0, 0.0),
        epsilon=1e-6,
    )

    assert result == pytest.approx(
        0.3
    )


def test_zero_hand_scale_uses_epsilon() -> None:
    result = normalized_pinch_ratio(
        thumb_xy=(0.0, 0.0),
        index_xy=(0.2, 0.0),
        scale_a_xy=(0.5, 0.5),
        scale_b_xy=(0.5, 0.5),
        epsilon=0.1,
    )

    assert math.isfinite(result)

    assert result == pytest.approx(
        2.0
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.005, 0.0),
        (-0.005, 0.0),
        (0.02, 0.015),
        (-0.02, -0.015),
    ],
)
def test_continuous_deadzone(
    value: float,
    expected: float,
) -> None:
    result = apply_deadzone(
        value,
        deadzone=0.005,
    )

    assert result == pytest.approx(
        expected
    )


def test_rotation_mapping_applies_gain_and_y_sign() -> None:
    yaw, pitch = bounded_rotation_delta(
        delta_x=0.03,
        delta_y=0.02,
        deadzone=0.01,
        gain=2.0,
        max_delta_rad=1.0,
    )

    assert yaw == pytest.approx(
        0.04
    )

    assert pitch == pytest.approx(
        -0.02
    )


def test_rotation_mapping_clamps_both_axes() -> None:
    yaw, pitch = bounded_rotation_delta(
        delta_x=1.0,
        delta_y=-1.0,
        deadzone=0.0,
        gain=10.0,
        max_delta_rad=0.1,
    )

    assert yaw == pytest.approx(
        0.1
    )

    assert pitch == pytest.approx(
        0.1
    )


def test_scale_delta_positive_means_enlarge() -> None:
    result = bounded_scale_delta(
        current_ratio=0.50,
        previous_ratio=0.40,
        deadzone=0.01,
        gain=2.0,
        max_delta=1.0,
    )

    assert result == pytest.approx(
        0.18
    )


def test_scale_delta_negative_means_shrink() -> None:
    result = bounded_scale_delta(
        current_ratio=0.30,
        previous_ratio=0.40,
        deadzone=0.01,
        gain=2.0,
        max_delta=1.0,
    )

    assert result == pytest.approx(
        -0.18
    )


def test_scale_delta_inside_deadzone_is_zero() -> None:
    result = bounded_scale_delta(
        current_ratio=0.405,
        previous_ratio=0.40,
        deadzone=0.01,
        gain=2.0,
        max_delta=1.0,
    )

    assert result == pytest.approx(
        0.0
    )


def test_scale_delta_is_clamped() -> None:
    result = bounded_scale_delta(
        current_ratio=2.0,
        previous_ratio=0.0,
        deadzone=0.0,
        gain=10.0,
        max_delta=0.1,
    )

    assert result == pytest.approx(
        0.1
    )


@pytest.mark.parametrize(
    "epsilon",
    [
        0.0,
        -1.0,
        math.inf,
        math.nan,
    ],
)
def test_invalid_epsilon_is_rejected(
    epsilon: float,
) -> None:
    with pytest.raises(ValueError):
        normalized_pinch_ratio(
            thumb_xy=(0.0, 0.0),
            index_xy=(0.1, 0.0),
            scale_a_xy=(0.0, 0.0),
            scale_b_xy=(1.0, 0.0),
            epsilon=epsilon,
        )


@pytest.mark.parametrize(
    "bad_value",
    [
        math.nan,
        math.inf,
        -math.inf,
    ],
)
def test_nonfinite_point_is_rejected(
    bad_value: float,
) -> None:
    with pytest.raises(ValueError):
        distance_xy(
            (bad_value, 0.0),
            (0.0, 0.0),
        )
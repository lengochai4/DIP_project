import math

import pytest

from dip_touchless.filtering import (
    ScalarLowPassFilter,
    low_pass_alpha,
)


def test_alpha_matches_known_value() -> None:
    alpha = low_pass_alpha(
        dt_s=1.0 / 60.0,
        cutoff_hz=1.0,
    )

    assert alpha == pytest.approx(
        0.0947930501,
        rel=1e-9,
    )


def test_alpha_increases_with_cutoff() -> None:
    slow = low_pass_alpha(
        dt_s=1.0 / 60.0,
        cutoff_hz=1.0,
    )

    fast = low_pass_alpha(
        dt_s=1.0 / 60.0,
        cutoff_hz=10.0,
    )

    assert 0.0 < slow < fast <= 1.0


def test_alpha_increases_with_dt() -> None:
    short_dt = low_pass_alpha(
        dt_s=1.0 / 120.0,
        cutoff_hz=1.0,
    )

    long_dt = low_pass_alpha(
        dt_s=1.0 / 30.0,
        cutoff_hz=1.0,
    )

    assert (
        0.0
        < short_dt
        < long_dt
        <= 1.0
    )


@pytest.mark.parametrize(
    "dt_s",
    [
        0.0,
        -0.01,
        math.inf,
        -math.inf,
        math.nan,
    ],
)
def test_invalid_dt_is_rejected(
    dt_s: float,
) -> None:
    with pytest.raises(ValueError):
        low_pass_alpha(
            dt_s=dt_s,
            cutoff_hz=1.0,
        )


@pytest.mark.parametrize(
    "cutoff_hz",
    [
        0.0,
        -1.0,
        math.inf,
        -math.inf,
        math.nan,
    ],
)
def test_invalid_cutoff_is_rejected(
    cutoff_hz: float,
) -> None:
    with pytest.raises(ValueError):
        low_pass_alpha(
            dt_s=1.0 / 60.0,
            cutoff_hz=cutoff_hz,
        )


def test_first_sample_initializes_directly() -> None:
    low_pass = ScalarLowPassFilter()

    result = low_pass.filter(
        10.0,
        alpha=0.1,
    )

    assert result == pytest.approx(10.0)
    assert low_pass.initialized is True

    assert (
        low_pass.last_filtered_value
        == pytest.approx(10.0)
    )


def test_subsequent_sample_uses_previous_filtered_output() -> None:
    low_pass = ScalarLowPassFilter()

    low_pass.filter(
        10.0,
        alpha=0.25,
    )

    result = low_pass.filter(
        14.0,
        alpha=0.25,
    )

    # 0.25 * 14 + 0.75 * 10 = 11
    assert result == pytest.approx(
        11.0
    )

    assert (
        low_pass.last_filtered_value
        == pytest.approx(11.0)
    )


def test_filter_uses_recursive_filtered_state() -> None:
    low_pass = ScalarLowPassFilter()

    low_pass.filter(
        0.0,
        alpha=0.5,
    )

    first = low_pass.filter(
        10.0,
        alpha=0.5,
    )

    second = low_pass.filter(
        10.0,
        alpha=0.5,
    )

    assert first == pytest.approx(
        5.0
    )

    assert second == pytest.approx(
        7.5
    )


def test_reset_clears_state() -> None:
    low_pass = ScalarLowPassFilter()

    low_pass.filter(
        10.0,
        alpha=0.2,
    )

    low_pass.reset()

    assert low_pass.initialized is False
    assert low_pass.last_filtered_value is None

    result = low_pass.filter(
        20.0,
        alpha=0.2,
    )

    assert result == pytest.approx(
        20.0
    )


@pytest.mark.parametrize(
    "value",
    [
        math.inf,
        -math.inf,
        math.nan,
    ],
)
def test_nonfinite_measurement_is_rejected(
    value: float,
) -> None:
    low_pass = ScalarLowPassFilter()

    with pytest.raises(ValueError):
        low_pass.filter(
            value,
            alpha=0.5,
        )


@pytest.mark.parametrize(
    "alpha",
    [
        0.0,
        -0.1,
        1.1,
        math.inf,
        math.nan,
    ],
)
def test_invalid_alpha_is_rejected(
    alpha: float,
) -> None:
    low_pass = ScalarLowPassFilter()

    with pytest.raises(ValueError):
        low_pass.filter(
            10.0,
            alpha=alpha,
        )
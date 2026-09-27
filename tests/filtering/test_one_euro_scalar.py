import math

import pytest

from dip_touchless.filtering import (
    ScalarOneEuroFilter,
    low_pass_alpha,
)


def _filter(
    *,
    min_cutoff_hz: float = 1.0,
    beta: float = 0.1,
    derivative_cutoff_hz: float = 1.0,
) -> ScalarOneEuroFilter:
    return ScalarOneEuroFilter(
        min_cutoff_hz=min_cutoff_hz,
        beta=beta,
        derivative_cutoff_hz=derivative_cutoff_hz,
    )


def test_first_sample_initializes_with_zero_derivative() -> None:
    one_euro = _filter()

    result = one_euro.update(
        12.5,
        dt_s=None,
    )

    assert result.filtered_value == pytest.approx(
        12.5
    )

    assert result.raw_derivative == pytest.approx(
        0.0
    )

    assert (
        result.filtered_derivative
        == pytest.approx(0.0)
    )

    assert result.cutoff_hz == pytest.approx(
        1.0
    )

    assert result.signal_alpha is None
    assert result.derivative_alpha is None
    assert result.initialization_occurred is True

    assert one_euro.initialized is True


def test_ordinary_update_matches_canonical_equations() -> None:
    one_euro = _filter(
        min_cutoff_hz=1.0,
        beta=0.1,
        derivative_cutoff_hz=1.0,
    )

    one_euro.update(
        0.0,
        dt_s=None,
    )

    result = one_euro.update(
        10.0,
        dt_s=0.1,
    )

    expected_derivative_alpha = low_pass_alpha(
        dt_s=0.1,
        cutoff_hz=1.0,
    )

    expected_raw_derivative = 100.0

    expected_filtered_derivative = (
        expected_derivative_alpha
        * expected_raw_derivative
    )

    expected_cutoff = (
        1.0
        + 0.1
        * abs(expected_filtered_derivative)
    )

    expected_signal_alpha = low_pass_alpha(
        dt_s=0.1,
        cutoff_hz=expected_cutoff,
    )

    expected_output = (
        expected_signal_alpha
        * 10.0
    )

    assert result.raw_derivative == pytest.approx(
        expected_raw_derivative
    )

    assert (
        result.derivative_alpha
        == pytest.approx(
            expected_derivative_alpha
        )
    )

    assert (
        result.filtered_derivative
        == pytest.approx(
            expected_filtered_derivative
        )
    )

    assert result.cutoff_hz == pytest.approx(
        expected_cutoff
    )

    assert result.signal_alpha == pytest.approx(
        expected_signal_alpha
    )

    assert result.filtered_value == pytest.approx(
        expected_output
    )


def test_derivative_uses_previous_filtered_not_previous_raw() -> None:
    one_euro = _filter(
        min_cutoff_hz=1.0,
        beta=0.1,
        derivative_cutoff_hz=1.0,
    )

    one_euro.update(
        0.0,
        dt_s=None,
    )

    second = one_euro.update(
        10.0,
        dt_s=0.1,
    )

    third = one_euro.update(
        10.0,
        dt_s=0.1,
    )

    expected_raw_derivative = (
        10.0
        - second.filtered_value
    ) / 0.1

    assert third.raw_derivative == pytest.approx(
        expected_raw_derivative
    )

    # If previous raw input were incorrectly used here,
    # the derivative would be zero because both raw samples are 10.
    assert third.raw_derivative > 0.0


def test_known_three_sample_sequence() -> None:
    one_euro = _filter(
        min_cutoff_hz=1.0,
        beta=0.1,
        derivative_cutoff_hz=1.0,
    )

    first = one_euro.update(
        0.0,
        dt_s=None,
    )

    second = one_euro.update(
        10.0,
        dt_s=0.1,
    )

    third = one_euro.update(
        10.0,
        dt_s=0.1,
    )

    assert first.filtered_value == pytest.approx(
        0.0
    )

    assert second.filtered_value == pytest.approx(
        7.532575181149229
    )

    assert third.raw_derivative == pytest.approx(
        24.674248188507704
    )

    assert third.filtered_derivative == pytest.approx(
        33.21846485038015
    )

    assert third.cutoff_hz == pytest.approx(
        4.321846485038016
    )

    assert third.filtered_value == pytest.approx(
        9.335909750997667
    )


def test_beta_zero_keeps_signal_cutoff_fixed() -> None:
    one_euro = _filter(
        min_cutoff_hz=2.0,
        beta=0.0,
        derivative_cutoff_hz=1.0,
    )

    one_euro.update(
        0.0,
        dt_s=None,
    )

    result = one_euro.update(
        100.0,
        dt_s=0.05,
    )

    assert result.cutoff_hz == pytest.approx(
        2.0
    )


def test_nonzero_speed_increases_cutoff_when_beta_positive() -> None:
    one_euro = _filter(
        min_cutoff_hz=1.0,
        beta=0.5,
        derivative_cutoff_hz=1.0,
    )

    one_euro.update(
        0.0,
        dt_s=None,
    )

    result = one_euro.update(
        10.0,
        dt_s=0.1,
    )

    assert result.filtered_derivative > 0.0
    assert result.cutoff_hz > 1.0


def test_reset_returns_filter_to_initialization_state() -> None:
    one_euro = _filter()

    one_euro.update(
        0.0,
        dt_s=None,
    )

    one_euro.update(
        10.0,
        dt_s=0.1,
    )

    one_euro.reset()

    assert one_euro.initialized is False
    assert one_euro.last_filtered_value is None

    result = one_euro.update(
        50.0,
        dt_s=None,
    )

    assert result.filtered_value == pytest.approx(
        50.0
    )

    assert result.raw_derivative == pytest.approx(
        0.0
    )

    assert result.initialization_occurred is True


def test_first_sample_requires_no_dt() -> None:
    one_euro = _filter()

    with pytest.raises(ValueError):
        one_euro.update(
            1.0,
            dt_s=0.1,
        )


def test_initialized_filter_requires_dt() -> None:
    one_euro = _filter()

    one_euro.update(
        1.0,
        dt_s=None,
    )

    with pytest.raises(ValueError):
        one_euro.update(
            2.0,
            dt_s=None,
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
def test_invalid_ordinary_dt_is_rejected(
    dt_s: float,
) -> None:
    one_euro = _filter()

    one_euro.update(
        1.0,
        dt_s=None,
    )

    with pytest.raises(ValueError):
        one_euro.update(
            2.0,
            dt_s=dt_s,
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
    one_euro = _filter()

    with pytest.raises(ValueError):
        one_euro.update(
            value,
            dt_s=None,
        )


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("min_cutoff_hz", 0.0),
        ("min_cutoff_hz", -1.0),
        ("min_cutoff_hz", math.inf),
        ("derivative_cutoff_hz", 0.0),
        ("derivative_cutoff_hz", -1.0),
        ("derivative_cutoff_hz", math.nan),
        ("beta", -0.1),
        ("beta", math.inf),
    ],
)
def test_invalid_parameters_are_rejected(
    name: str,
    value: float,
) -> None:
    kwargs = {
        "min_cutoff_hz": 1.0,
        "beta": 0.1,
        "derivative_cutoff_hz": 1.0,
    }

    kwargs[name] = value

    with pytest.raises(ValueError):
        ScalarOneEuroFilter(
            **kwargs,
        )
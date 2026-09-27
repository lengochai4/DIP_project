"""Deterministic synthetic acceptance tests for fixed 1-Euro filtering."""

from __future__ import annotations

import math
import statistics

import pytest
from itertools import pairwise

from dip_touchless.filtering import ScalarOneEuroFilter


def _run_filter(
    values: list[float],
    *,
    dt_s: float = 1.0 / 60.0,
    min_cutoff_hz: float = 1.0,
    beta: float = 0.1,
    derivative_cutoff_hz: float = 1.0,
) -> list[float]:
    assert values

    one_euro = ScalarOneEuroFilter(
        min_cutoff_hz=min_cutoff_hz,
        beta=beta,
        derivative_cutoff_hz=derivative_cutoff_hz,
    )

    outputs = [
        one_euro.update(
            values[0],
            dt_s=None,
        ).filtered_value
    ]

    for value in values[1:]:
        result = one_euro.update(
            value,
            dt_s=dt_s,
        )

        outputs.append(
            result.filtered_value
        )

    return outputs


def _rmse(
    actual: list[float],
    expected: list[float],
) -> float:
    assert len(actual) == len(expected)
    assert actual

    return math.sqrt(
        sum(
            (a - e) ** 2
            for a, e in zip(
                actual,
                expected,
                strict=True,
            )
        )
        / len(actual)
    )


def test_constant_signal_is_preserved() -> None:
    values = [0.25] * 180

    outputs = _run_filter(values)

    assert outputs == pytest.approx(
        values
    )


def test_step_response_is_bounded_and_converges() -> None:
    values = (
        [0.0] * 30
        + [1.0] * 120
    )

    outputs = _run_filter(
        values,
        beta=0.2,
    )

    step_response = outputs[30:]

    assert 0.0 < step_response[0] < 1.0

    assert all(
        0.0 <= value <= 1.0
        for value in step_response
    )

    assert all(
        later >= earlier
        for earlier, later in pairwise(
            step_response
        )
    )

    assert step_response[-1] == pytest.approx(
        1.0,
        abs=1e-5,
    )


def test_increasing_ramp_has_no_overshoot() -> None:
    values = [
        index / 119.0
        for index in range(120)
    ]

    outputs = _run_filter(
        values,
        beta=0.2,
    )

    assert all(
        later >= earlier
        for earlier, later in pairwise(
            outputs
        )
    )

    assert all(
        filtered <= raw + 1e-12
        for filtered, raw in zip(
            outputs,
            values,
            strict=True,
        )
    )

    assert outputs[-1] > 0.9
    assert outputs[-1] < 1.0


def test_sine_signal_remains_finite_and_bounded() -> None:
    sample_rate_hz = 60.0
    frequency_hz = 0.5

    values = [
        math.sin(
            2.0
            * math.pi
            * frequency_hz
            * index
            / sample_rate_hz
        )
        for index in range(600)
    ]

    outputs = _run_filter(
        values,
        dt_s=1.0 / sample_rate_hz,
        min_cutoff_hz=1.0,
        beta=0.1,
    )

    assert all(
        math.isfinite(value)
        for value in outputs
    )

    assert all(
        -1.0 <= value <= 1.0
        for value in outputs
    )

    # The signal must remain responsive rather than collapsing
    # to a constant under a periodic input.
    assert max(outputs) > 0.5
    assert min(outputs) < -0.5


def test_deterministic_high_frequency_noise_is_reduced() -> None:
    raw = [
        0.5
        + (
            0.05
            if index % 2 == 0
            else -0.05
        )
        for index in range(600)
    ]

    filtered = _run_filter(
        raw,
        min_cutoff_hz=1.0,
        beta=0.0,
    )

    # Ignore deterministic startup transient.
    warmup = 120

    raw_tail = raw[warmup:]
    filtered_tail = filtered[warmup:]

    assert statistics.pstdev(
        filtered_tail
    ) < statistics.pstdev(
        raw_tail
    )


def test_known_noisy_trajectory_can_reduce_rmse() -> None:
    sample_rate_hz = 60.0
    frequency_hz = 0.5

    clean = [
        math.sin(
            2.0
            * math.pi
            * frequency_hz
            * index
            / sample_rate_hz
        )
        for index in range(600)
    ]

    noisy = [
        value
        + (
            0.08
            if index % 2 == 0
            else -0.08
        )
        for index, value in enumerate(
            clean
        )
    ]

    filtered = _run_filter(
        noisy,
        dt_s=1.0 / sample_rate_hz,
        min_cutoff_hz=8.0,
        beta=0.1,
        derivative_cutoff_hz=1.0,
    )

    warmup = 120

    clean_tail = clean[warmup:]
    noisy_tail = noisy[warmup:]
    filtered_tail = filtered[warmup:]

    raw_rmse = _rmse(
        noisy_tail,
        clean_tail,
    )

    filtered_rmse = _rmse(
        filtered_tail,
        clean_tail,
    )

    assert filtered_rmse < raw_rmse


def test_nonuniform_valid_dt_is_supported() -> None:
    values = [
        0.0,
        0.2,
        0.4,
        0.6,
        0.8,
        1.0,
    ]

    dt_values = [
        0.010,
        0.025,
        0.015,
        0.040,
        0.020,
    ]

    one_euro = ScalarOneEuroFilter(
        min_cutoff_hz=1.0,
        beta=0.1,
        derivative_cutoff_hz=1.0,
    )

    first = one_euro.update(
        values[0],
        dt_s=None,
    )

    assert first.filtered_value == pytest.approx(
        0.0
    )

    outputs = [
        first.filtered_value
    ]

    for value, dt_s in zip(
        values[1:],
        dt_values,
        strict=True,
    ):
        result = one_euro.update(
            value,
            dt_s=dt_s,
        )

        assert math.isfinite(
            result.filtered_value
        )

        assert result.signal_alpha is not None
        assert (
            0.0
            < result.signal_alpha
            <= 1.0
        )

        assert (
            result.derivative_alpha
            is not None
        )

        assert (
            0.0
            < result.derivative_alpha
            <= 1.0
        )

        outputs.append(
            result.filtered_value
        )

    assert all(
        later >= earlier
        for earlier, later in pairwise(
            outputs
        )
    )


def test_larger_dt_changes_filter_response() -> None:
    short_dt_filter = ScalarOneEuroFilter(
        min_cutoff_hz=1.0,
        beta=0.0,
        derivative_cutoff_hz=1.0,
    )

    long_dt_filter = ScalarOneEuroFilter(
        min_cutoff_hz=1.0,
        beta=0.0,
        derivative_cutoff_hz=1.0,
    )

    short_dt_filter.update(
        0.0,
        dt_s=None,
    )

    long_dt_filter.update(
        0.0,
        dt_s=None,
    )

    short = short_dt_filter.update(
        1.0,
        dt_s=0.01,
    )

    long = long_dt_filter.update(
        1.0,
        dt_s=0.10,
    )

    assert short.signal_alpha is not None
    assert long.signal_alpha is not None

    assert (
        long.signal_alpha
        > short.signal_alpha
    )

    assert (
        long.filtered_value
        > short.filtered_value
    )
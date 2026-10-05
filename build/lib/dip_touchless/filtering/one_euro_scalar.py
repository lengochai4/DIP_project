"""Canonical scalar 1-Euro filter."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .low_pass import (
    ScalarLowPassFilter,
    low_pass_alpha,
)


@dataclass(frozen=True)
class ScalarOneEuroResult:
    """Diagnostics for one scalar 1-Euro update."""

    filtered_value: float
    raw_derivative: float
    filtered_derivative: float
    cutoff_hz: float
    signal_alpha: float | None
    derivative_alpha: float | None
    initialization_occurred: bool


class ScalarOneEuroFilter:
    """Canonical derivative-filtered scalar 1-Euro filter.

    Fixed parameters:
    - min_cutoff_hz
    - beta
    - derivative_cutoff_hz

    The signal cutoff itself remains speed-dependent.
    """

    def __init__(
        self,
        *,
        min_cutoff_hz: float,
        beta: float,
        derivative_cutoff_hz: float,
    ) -> None:
        self._require_positive_finite(
            min_cutoff_hz,
            name="min_cutoff_hz",
        )

        self._require_nonnegative_finite(
            beta,
            name="beta",
        )

        self._require_positive_finite(
            derivative_cutoff_hz,
            name="derivative_cutoff_hz",
        )

        self._min_cutoff_hz = float(
            min_cutoff_hz
        )

        self._beta = float(beta)

        self._derivative_cutoff_hz = float(
            derivative_cutoff_hz
        )

        self._signal_filter = ScalarLowPassFilter()
        self._derivative_filter = ScalarLowPassFilter()

    @property
    def initialized(self) -> bool:
        return self._signal_filter.initialized

    @property
    def last_filtered_value(
        self,
    ) -> float | None:
        return self._signal_filter.last_filtered_value

    def reset(self) -> None:
        """Clear signal and derivative filter state."""

        self._signal_filter.reset()
        self._derivative_filter.reset()

    def update(
        self,
        value: float,
        *,
        dt_s: float | None,
    ) -> ScalarOneEuroResult:
        """Filter one scalar measurement.

        The first accepted sample after construction/reset uses dt_s=None,
        initializes the signal directly from the measurement, and uses
        derivative zero.

        Ordinary updates require a finite positive dt_s.
        """

        if not math.isfinite(value):
            raise ValueError(
                "value must be finite"
            )

        if not self.initialized:
            if dt_s is not None:
                raise ValueError(
                    "dt_s must be None for initialization"
                )

            return self._initialize(
                float(value)
            )

        if dt_s is None:
            raise ValueError(
                "dt_s is required after initialization"
            )

        if (
            not math.isfinite(dt_s)
            or dt_s <= 0.0
        ):
            raise ValueError(
                "dt_s must be finite and positive"
            )

        previous_filtered = (
            self._signal_filter.last_filtered_value
        )

        assert previous_filtered is not None

        raw_derivative = (
            value - previous_filtered
        ) / dt_s

        if not math.isfinite(raw_derivative):
            raise RuntimeError(
                "raw derivative became non-finite"
            )

        derivative_alpha = low_pass_alpha(
            dt_s=dt_s,
            cutoff_hz=self._derivative_cutoff_hz,
        )

        filtered_derivative = (
            self._derivative_filter.filter(
                raw_derivative,
                alpha=derivative_alpha,
            )
        )

        cutoff_hz = (
            self._min_cutoff_hz
            + self._beta
            * abs(filtered_derivative)
        )

        if (
            not math.isfinite(cutoff_hz)
            or cutoff_hz <= 0.0
        ):
            raise RuntimeError(
                "signal cutoff became invalid"
            )

        signal_alpha = low_pass_alpha(
            dt_s=dt_s,
            cutoff_hz=cutoff_hz,
        )

        filtered_value = (
            self._signal_filter.filter(
                value,
                alpha=signal_alpha,
            )
        )

        return ScalarOneEuroResult(
            filtered_value=filtered_value,
            raw_derivative=raw_derivative,
            filtered_derivative=filtered_derivative,
            cutoff_hz=cutoff_hz,
            signal_alpha=signal_alpha,
            derivative_alpha=derivative_alpha,
            initialization_occurred=False,
        )

    def _initialize(
        self,
        value: float,
    ) -> ScalarOneEuroResult:
        # ScalarLowPassFilter initializes directly from its first sample.
        # alpha=1 is supplied only because the primitive validates alpha;
        # no ordinary low-pass update occurs on initialization.
        filtered_derivative = (
            self._derivative_filter.filter(
                0.0,
                alpha=1.0,
            )
        )

        filtered_value = (
            self._signal_filter.filter(
                value,
                alpha=1.0,
            )
        )

        return ScalarOneEuroResult(
            filtered_value=filtered_value,
            raw_derivative=0.0,
            filtered_derivative=filtered_derivative,
            cutoff_hz=self._min_cutoff_hz,
            signal_alpha=None,
            derivative_alpha=None,
            initialization_occurred=True,
        )

    @staticmethod
    def _require_positive_finite(
        value: float,
        *,
        name: str,
    ) -> None:
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value <= 0.0
        ):
            raise ValueError(
                f"{name} must be finite and positive"
            )

    @staticmethod
    def _require_nonnegative_finite(
        value: float,
        *,
        name: str,
    ) -> None:
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value < 0.0
        ):
            raise ValueError(
                f"{name} must be finite and non-negative"
            )
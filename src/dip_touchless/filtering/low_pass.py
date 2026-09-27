"""Scalar low-pass primitives used by temporal filters."""

from __future__ import annotations

import math


def low_pass_alpha(
    *,
    dt_s: float,
    cutoff_hz: float,
) -> float:
    """Return the canonical first-order low-pass coefficient.

    alpha = 1 / (1 + tau / dt)
    tau = 1 / (2 * pi * cutoff)
    """

    if (
        not math.isfinite(dt_s)
        or dt_s <= 0.0
    ):
        raise ValueError(
            "dt_s must be finite and positive"
        )

    if (
        not math.isfinite(cutoff_hz)
        or cutoff_hz <= 0.0
    ):
        raise ValueError(
            "cutoff_hz must be finite and positive"
        )

    tau_s = (
        1.0
        / (
            2.0
            * math.pi
            * cutoff_hz
        )
    )

    alpha = (
        1.0
        / (
            1.0
            + tau_s / dt_s
        )
    )

    if (
        not math.isfinite(alpha)
        or not 0.0 < alpha <= 1.0
    ):
        raise RuntimeError(
            "computed low-pass alpha is invalid"
        )

    return alpha


class ScalarLowPassFilter:
    """Stateful scalar first-order low-pass filter.

    The first accepted sample initializes the filter directly from the
    measurement. Subsequent samples apply the supplied alpha.
    """

    def __init__(self) -> None:
        self.reset()

    @property
    def initialized(self) -> bool:
        return self._filtered_value is not None

    @property
    def last_filtered_value(
        self,
    ) -> float | None:
        return self._filtered_value

    def reset(self) -> None:
        """Clear filter state."""

        self._filtered_value: float | None = None

    def filter(
        self,
        value: float,
        *,
        alpha: float,
    ) -> float:
        """Filter one finite scalar measurement."""

        if not math.isfinite(value):
            raise ValueError(
                "value must be finite"
            )

        if (
            not math.isfinite(alpha)
            or not 0.0 < alpha <= 1.0
        ):
            raise ValueError(
                "alpha must be finite and in (0, 1]"
            )

        if self._filtered_value is None:
            self._filtered_value = float(
                value
            )

            return self._filtered_value

        filtered = (
            alpha * value
            + (1.0 - alpha)
            * self._filtered_value
        )

        if not math.isfinite(filtered):
            raise RuntimeError(
                "low-pass output became non-finite"
            )

        self._filtered_value = filtered

        return filtered
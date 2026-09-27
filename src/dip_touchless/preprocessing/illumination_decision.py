"""Stateful illumination decision using EMA and hysteresis."""

from __future__ import annotations

from dip_touchless.core import (
    IlluminationMetrics,
    IlluminationState,
)

from .illumination import IlluminationDescriptors


class IlluminationDecisionStabilizer:
    """Convert raw illumination descriptors into a stabilized state."""

    def __init__(
        self,
        *,
        ema_alpha: float,
        low_light_enter_v: float,
        low_light_exit_v: float,
        low_contrast_enter_range_v: float,
        low_contrast_exit_range_v: float,
    ) -> None:
        if not 0.0 < ema_alpha <= 1.0:
            raise ValueError(
                "ema_alpha must be in (0, 1]"
            )

        if not (
            0.0
            <= low_light_enter_v
            < low_light_exit_v
            <= 255.0
        ):
            raise ValueError(
                "low-light thresholds must satisfy "
                "0 <= enter < exit <= 255"
            )

        if not (
            0.0
            <= low_contrast_enter_range_v
            < low_contrast_exit_range_v
            <= 255.0
        ):
            raise ValueError(
                "low-contrast thresholds must satisfy "
                "0 <= enter < exit <= 255"
            )

        self._ema_alpha = float(
            ema_alpha
        )

        self._low_light_enter_v = float(
            low_light_enter_v
        )
        self._low_light_exit_v = float(
            low_light_exit_v
        )

        self._low_contrast_enter_range_v = float(
            low_contrast_enter_range_v
        )
        self._low_contrast_exit_range_v = float(
            low_contrast_exit_range_v
        )

        self.reset()

    @property
    def ema_mean_v(self) -> float | None:
        return self._ema_mean_v

    @property
    def ema_robust_range_v(
        self,
    ) -> float | None:
        return self._ema_robust_range_v

    def reset(self) -> None:
        """Clear EMA and hysteresis state."""

        self._ema_mean_v: float | None = None
        self._ema_robust_range_v: float | None = None

        self._low_light_active = False
        self._low_contrast_active = False

    def update(
        self,
        descriptors: IlluminationDescriptors,
    ) -> IlluminationMetrics:
        """Update stabilized illumination state."""

        self._ema_mean_v = self._ema(
            previous=self._ema_mean_v,
            current=descriptors.mean_v,
        )

        self._ema_robust_range_v = self._ema(
            previous=self._ema_robust_range_v,
            current=descriptors.robust_range_v,
        )

        self._update_low_light()
        self._update_low_contrast()

        state = self._state()

        return IlluminationMetrics(
            mean_v=descriptors.mean_v,
            std_v=descriptors.std_v,
            p10_v=descriptors.p10_v,
            p90_v=descriptors.p90_v,
            robust_range_v=descriptors.robust_range_v,
            state=state,
            enhancement_active=(
                state is not IlluminationState.NORMAL
            ),
        )

    def _ema(
        self,
        *,
        previous: float | None,
        current: float,
    ) -> float:
        if previous is None:
            return float(current)

        return (
            self._ema_alpha * current
            + (1.0 - self._ema_alpha) * previous
        )

    def _update_low_light(self) -> None:
        assert self._ema_mean_v is not None

        if self._low_light_active:
            if (
                self._ema_mean_v
                >= self._low_light_exit_v
            ):
                self._low_light_active = False
        elif (
            self._ema_mean_v
            < self._low_light_enter_v
        ):
            self._low_light_active = True

    def _update_low_contrast(self) -> None:
        assert (
            self._ema_robust_range_v
            is not None
        )

        if self._low_contrast_active:
            if (
                self._ema_robust_range_v
                >= self._low_contrast_exit_range_v
            ):
                self._low_contrast_active = False
        elif (
            self._ema_robust_range_v
            < self._low_contrast_enter_range_v
        ):
            self._low_contrast_active = True

    def _state(
        self,
    ) -> IlluminationState:
        if (
            self._low_light_active
            and self._low_contrast_active
        ):
            return IlluminationState.DIFFICULT

        if self._low_light_active:
            return IlluminationState.LOW_LIGHT

        if self._low_contrast_active:
            return IlluminationState.LOW_CONTRAST

        return IlluminationState.NORMAL
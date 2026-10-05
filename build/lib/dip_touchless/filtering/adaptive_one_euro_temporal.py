"""Shared temporal semantics for bounded adaptive F2 filtering."""

from __future__ import annotations

from dataclasses import dataclass

from dip_touchless.core import (
    Landmark,
    LandmarkObservation,
)

from .adaptive_one_euro_landmarks import (
    AdaptiveLandmarkDiagnostics,
    AdaptiveLandmarkResult,
    AdaptiveOneEuroLandmarkCore,
)
from .temporal_controller import (
    OneEuroTemporalController,
)


@dataclass(frozen=True)
class AdaptiveOneEuroTemporalResult:
    landmarks: tuple[Landmark, ...]

    landmark_diagnostics: tuple[
        AdaptiveLandmarkDiagnostics,
        ...,
    ]

    dt_s: float | None
    measurement_accepted: bool
    initialization_occurred: bool
    reset_occurred: bool
    event: str | None


class _AdaptiveMeasurementCore:
    """Primary F2 measurement core.

    Quality adaptation remains disabled here, therefore the
    adaptive landmark core uses its configured base cutoff.
    """

    def __init__(
        self,
        *,
        base_cutoff_hz: float,
        beta_min: float,
        beta_base: float,
        beta_max: float,
        velocity_gain: float,
        velocity_max: float | None,
        final_cutoff_min_hz: float,
        final_cutoff_max_hz: float,
        derivative_cutoff_hz: float,
    ) -> None:
        self._core = AdaptiveOneEuroLandmarkCore(
            base_cutoff_hz=base_cutoff_hz,
            beta_min=beta_min,
            beta_base=beta_base,
            beta_max=beta_max,
            velocity_gain=velocity_gain,
            velocity_max=velocity_max,
            final_cutoff_min_hz=(
                final_cutoff_min_hz
            ),
            final_cutoff_max_hz=(
                final_cutoff_max_hz
            ),
            derivative_cutoff_hz=(
                derivative_cutoff_hz
            ),
        )

    @property
    def initialized(self) -> bool:
        return self._core.initialized

    def reset(self) -> None:
        self._core.reset()

    def update(
        self,
        observation: LandmarkObservation,
        *,
        dt_s: float | None,
    ) -> AdaptiveLandmarkResult:
        return self._core.update(
            observation.landmarks,
            dt_s=dt_s,
        )


class AdaptiveOneEuroTemporalCore:
    """Bounded adaptive F2 using shared F1/F2 temporal semantics."""

    def __init__(
        self,
        *,
        base_cutoff_hz: float,
        beta_min: float,
        beta_base: float,
        beta_max: float,
        velocity_gain: float,
        velocity_max: float | None,
        final_cutoff_min_hz: float,
        final_cutoff_max_hz: float,
        derivative_cutoff_hz: float,
        reset_gap_s: float,
    ) -> None:
        self._controller = (
            OneEuroTemporalController[
                AdaptiveLandmarkDiagnostics
            ](
                measurement_core=(
                    _AdaptiveMeasurementCore(
                        base_cutoff_hz=(
                            base_cutoff_hz
                        ),
                        beta_min=beta_min,
                        beta_base=beta_base,
                        beta_max=beta_max,
                        velocity_gain=(
                            velocity_gain
                        ),
                        velocity_max=(
                            velocity_max
                        ),
                        final_cutoff_min_hz=(
                            final_cutoff_min_hz
                        ),
                        final_cutoff_max_hz=(
                            final_cutoff_max_hz
                        ),
                        derivative_cutoff_hz=(
                            derivative_cutoff_hz
                        ),
                    )
                ),
                reset_gap_s=reset_gap_s,
            )
        )

    @property
    def initialized(self) -> bool:
        return self._controller.initialized

    @property
    def last_accepted_timestamp_s(
        self,
    ) -> float | None:
        return (
            self._controller
            .last_accepted_timestamp_s
        )

    def reset(self) -> None:
        self._controller.reset()

    def update(
        self,
        observation: LandmarkObservation,
    ) -> AdaptiveOneEuroTemporalResult:
        result = self._controller.update(
            observation
        )

        return AdaptiveOneEuroTemporalResult(
            landmarks=result.landmarks,
            landmark_diagnostics=(
                result.landmark_diagnostics
            ),
            dt_s=result.dt_s,
            measurement_accepted=(
                result.measurement_accepted
            ),
            initialization_occurred=(
                result.initialization_occurred
            ),
            reset_occurred=(
                result.reset_occurred
            ),
            event=result.event,
        )
"""Tracking/timestamp semantics for fixed 1-Euro landmark filtering."""

from __future__ import annotations

from dataclasses import dataclass

from dip_touchless.core import (
    Landmark,
    LandmarkObservation,
)

from .one_euro_landmarks import (
    FixedOneEuroLandmarkCore,
    LandmarkOneEuroDiagnostics,
    LandmarkOneEuroResult,
)
from .temporal_controller import (
    OneEuroTemporalController,
)


@dataclass(frozen=True)
class FixedOneEuroTemporalResult:
    landmarks: tuple[Landmark, ...]

    landmark_diagnostics: tuple[
        LandmarkOneEuroDiagnostics,
        ...,
    ]

    dt_s: float | None
    measurement_accepted: bool
    initialization_occurred: bool
    reset_occurred: bool
    event: str | None


class _FixedMeasurementCore:
    def __init__(
        self,
        *,
        min_cutoff_hz: float,
        beta: float,
        derivative_cutoff_hz: float,
    ) -> None:
        self._core = FixedOneEuroLandmarkCore(
            min_cutoff_hz=min_cutoff_hz,
            beta=beta,
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
    ) -> LandmarkOneEuroResult:
        return self._core.update(
            observation.landmarks,
            dt_s=dt_s,
        )


class FixedOneEuroTemporalCore:
    """Fixed F1 using shared temporal semantics."""

    def __init__(
        self,
        *,
        min_cutoff_hz: float,
        beta: float,
        derivative_cutoff_hz: float,
        reset_gap_s: float,
    ) -> None:
        self._controller = (
            OneEuroTemporalController[
                LandmarkOneEuroDiagnostics
            ](
                measurement_core=(
                    _FixedMeasurementCore(
                        min_cutoff_hz=(
                            min_cutoff_hz
                        ),
                        beta=beta,
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
    ) -> FixedOneEuroTemporalResult:
        result = self._controller.update(
            observation
        )

        return FixedOneEuroTemporalResult(
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
"""Public fixed 1-Euro LandmarkFilter implementation."""

from __future__ import annotations

from dip_touchless.core import (
    FilterDiagnostics,
    FilterMode,
    Landmark,
    LandmarkObservation,
)

from .one_euro_landmarks import (
    LandmarkOneEuroDiagnostics,
)
from .one_euro_temporal import (
    FixedOneEuroTemporalCore,
    FixedOneEuroTemporalResult,
)


class FixedOneEuroLandmarkFilter:
    """Canonical fixed 1-Euro landmark filter.

    Public LandmarkFilter wrapper around the project temporal/vector
    implementation.

    Filtering:
    - independent x/y vector state per landmark;
    - shared x/y cutoff within each landmark;
    - model-relative z pass-through;
    - timestamp/loss/reset handling in the temporal core.

    Public diagnostics use the frozen frame-level summary semantics.
    """

    def __init__(
        self,
        *,
        min_cutoff_hz: float,
        beta: float,
        derivative_cutoff_hz: float,
        reset_gap_s: float,
    ) -> None:
        self._min_cutoff_hz = float(
            min_cutoff_hz
        )
        self._beta = float(beta)

        self._core = FixedOneEuroTemporalCore(
            min_cutoff_hz=min_cutoff_hz,
            beta=beta,
            derivative_cutoff_hz=(
                derivative_cutoff_hz
            ),
            reset_gap_s=reset_gap_s,
        )

    def reset(self) -> None:
        """Reset all fixed-filter temporal state."""

        self._core.reset()

    def update(
        self,
        observation: LandmarkObservation,
    ) -> tuple[
        tuple[Landmark, ...],
        FilterDiagnostics,
    ]:
        """Filter one validated landmark observation."""

        result = self._core.update(
            observation
        )

        diagnostics = (
            self._to_public_diagnostics(
                result
            )
        )

        return (
            result.landmarks,
            diagnostics,
        )

    def _to_public_diagnostics(
        self,
        result: FixedOneEuroTemporalResult,
    ) -> FilterDiagnostics:
        if not result.measurement_accepted:
            return FilterDiagnostics(
                mode=(
                    FilterMode.ONE_EURO_FIXED
                ),
                dt_s=None,
                speed=None,
                beta=self._beta,
                min_cutoff_hz=(
                    self._min_cutoff_hz
                ),
                final_cutoff_hz=None,
                signal_alpha=None,
                derivative_alpha=None,
                reset_occurred=(
                    result.reset_occurred
                ),
                events=(
                    ()
                    if result.event is None
                    else (result.event,)
                ),
            )

        representative = (
            self._select_representative(
                result.landmark_diagnostics
            )
        )

        return FilterDiagnostics(
            mode=FilterMode.ONE_EURO_FIXED,
            dt_s=result.dt_s,
            speed=representative.speed,
            beta=self._beta,
            min_cutoff_hz=(
                self._min_cutoff_hz
            ),
            final_cutoff_hz=(
                representative.cutoff_hz
            ),
            signal_alpha=(
                representative.signal_alpha
            ),
            derivative_alpha=(
                representative.derivative_alpha
            ),
            reset_occurred=(
                result.reset_occurred
            ),
            events=(
                ()
                if result.event is None
                else (result.event,)
            ),
        )

    @staticmethod
    def _select_representative(
        diagnostics: tuple[
            LandmarkOneEuroDiagnostics,
            ...
        ],
    ) -> LandmarkOneEuroDiagnostics:
        if not diagnostics:
            raise RuntimeError(
                "accepted measurement has no "
                "landmark diagnostics"
            )

        # Maximum speed wins.
        #
        # For an exact tie, lower landmark index wins:
        #   max((speed, -index))
        return max(
            diagnostics,
            key=lambda item: (
                item.speed,
                -item.landmark_index,
            ),
        )
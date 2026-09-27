"""Public bounded adaptive 1-Euro LandmarkFilter implementation."""

from __future__ import annotations

from dip_touchless.core import (
    FilterDiagnostics,
    FilterMode,
    Landmark,
    LandmarkObservation,
)

from .adaptive_one_euro_landmarks import (
    AdaptiveLandmarkDiagnostics,
)
from .adaptive_one_euro_temporal import (
    AdaptiveOneEuroTemporalCore,
    AdaptiveOneEuroTemporalResult,
)


class AdaptiveOneEuroLandmarkFilter:
    """Project-specific bounded adaptive 1-Euro landmark filter.

    Primary F2 path:
    - independent x/y state per landmark;
    - speed from filtered x/y derivative;
    - bounded velocity-dependent beta;
    - bounded final signal cutoff;
    - model-relative z pass-through;
    - shared F1/F2 timestamp/loss/reset semantics;
    - quality adaptation disabled unless separately specified.
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
        reset_gap_s: float,
    ) -> None:
        self._base_cutoff_hz = float(
            base_cutoff_hz
        )

        self._beta_base = float(
            beta_base
        )

        self._core = AdaptiveOneEuroTemporalCore(
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
            reset_gap_s=reset_gap_s,
        )

    def reset(self) -> None:
        """Reset all adaptive-filter temporal state."""

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

        return (
            result.landmarks,
            self._to_public_diagnostics(
                result
            ),
        )

    def _to_public_diagnostics(
        self,
        result: AdaptiveOneEuroTemporalResult,
    ) -> FilterDiagnostics:
        if not result.measurement_accepted:
            return FilterDiagnostics(
                mode=(
                    FilterMode.ONE_EURO_ADAPTIVE
                ),
                dt_s=None,
                speed=None,
                beta=None,
                min_cutoff_hz=(
                    self._base_cutoff_hz
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
            mode=(
                FilterMode.ONE_EURO_ADAPTIVE
            ),
            dt_s=result.dt_s,
            speed=representative.speed,
            beta=representative.beta,
            min_cutoff_hz=(
                representative.min_cutoff_hz
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
            AdaptiveLandmarkDiagnostics,
            ...,
        ],
    ) -> AdaptiveLandmarkDiagnostics:
        if not diagnostics:
            raise RuntimeError(
                "accepted measurement has no "
                "landmark diagnostics"
            )

        return max(
            diagnostics,
            key=lambda item: (
                item.speed,
                -item.landmark_index,
            ),
        )
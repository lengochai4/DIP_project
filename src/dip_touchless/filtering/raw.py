"""Raw landmark baseline with no temporal smoothing."""

from __future__ import annotations

from dip_touchless.core import (
    FilterDiagnostics,
    FilterMode,
    Landmark,
    LandmarkObservation,
    TrackingStatus,
)


class RawLandmarkFilter:
    """F0 baseline: return valid landmarks unchanged."""

    def update(
        self,
        observation: LandmarkObservation,
    ) -> tuple[
        tuple[Landmark, ...],
        FilterDiagnostics,
    ]:
        usable = observation.status in {
            TrackingStatus.VALID,
            TrackingStatus.REACQUIRED,
        }

        landmarks = (
            observation.landmarks
            if usable
            else ()
        )

        diagnostics = FilterDiagnostics(
            mode=FilterMode.RAW,
            dt_s=None,
            speed=None,
            beta=None,
            min_cutoff_hz=None,
            final_cutoff_hz=None,
            signal_alpha=None,
            derivative_alpha=None,
            reset_occurred=False,
        )

        return landmarks, diagnostics

    def reset(self) -> None:
        """RAW mode has no temporal state."""
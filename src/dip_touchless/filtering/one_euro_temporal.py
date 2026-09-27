"""Tracking/timestamp semantics for fixed 1-Euro landmark filtering."""

from __future__ import annotations

from dataclasses import dataclass
import math

from dip_touchless.core import (
    Landmark,
    LandmarkObservation,
    TrackingStatus,
)

from .one_euro_landmarks import (
    FixedOneEuroLandmarkCore,
    LandmarkOneEuroDiagnostics,
)


@dataclass(frozen=True)
class FixedOneEuroTemporalResult:
    """Internal result before public FilterDiagnostics mapping."""

    landmarks: tuple[Landmark, ...]
    landmark_diagnostics: tuple[
        LandmarkOneEuroDiagnostics,
        ...
    ]

    dt_s: float | None
    measurement_accepted: bool
    initialization_occurred: bool
    reset_occurred: bool
    event: str | None


class FixedOneEuroTemporalCore:
    """Apply tracking-loss and timestamp semantics around landmark F1."""

    _USABLE_STATUSES = {
        TrackingStatus.VALID,
        TrackingStatus.REACQUIRED,
    }

    def __init__(
        self,
        *,
        min_cutoff_hz: float,
        beta: float,
        derivative_cutoff_hz: float,
        reset_gap_s: float,
    ) -> None:
        if (
            not math.isfinite(reset_gap_s)
            or reset_gap_s <= 0.0
        ):
            raise ValueError(
                "reset_gap_s must be finite and positive"
            )

        self._reset_gap_s = float(reset_gap_s)

        self._landmark_core = (
            FixedOneEuroLandmarkCore(
                min_cutoff_hz=min_cutoff_hz,
                beta=beta,
                derivative_cutoff_hz=(
                    derivative_cutoff_hz
                ),
            )
        )

        self._last_accepted_timestamp_s: (
            float | None
        ) = None

        self._last_seen_timestamp_s: (
            float | None
        ) = None

    @property
    def initialized(self) -> bool:
        return self._landmark_core.initialized

    @property
    def last_accepted_timestamp_s(
        self,
    ) -> float | None:
        return self._last_accepted_timestamp_s

    def reset(self) -> None:
        """Clear filter state and timestamp history."""

        self._landmark_core.reset()
        self._last_accepted_timestamp_s = None
        self._last_seen_timestamp_s = None

    def update(
        self,
        observation: LandmarkObservation,
    ) -> FixedOneEuroTemporalResult:
        """Consume one validated landmark observation."""

        timestamp_s = observation.timestamp_s

        if not math.isfinite(timestamp_s):
            raise ValueError(
                "observation timestamp must be finite"
            )

        timestamp_discontinuity = (
            self._last_seen_timestamp_s
            is not None
            and timestamp_s
            <= self._last_seen_timestamp_s
        )

        self._last_seen_timestamp_s = (
            timestamp_s
        )

        usable = (
            observation.status
            in self._USABLE_STATUSES
        )

        if timestamp_discontinuity:
            had_state = self.initialized

            self._landmark_core.reset()
            self._last_accepted_timestamp_s = None

            if usable:
                return self._initialize_measurement(
                    observation,
                    reset_occurred=had_state,
                    event=(
                        "timestamp_discontinuity"
                    ),
                )

            return self._empty_result(
                reset_occurred=had_state,
                event="timestamp_discontinuity",
            )

        if not usable:
            return self._handle_missing_measurement(
                timestamp_s
            )

        if (
            not self.initialized
            or self._last_accepted_timestamp_s
            is None
        ):
            return self._initialize_measurement(
                observation,
                reset_occurred=False,
                event=None,
            )

        dt_s = (
            timestamp_s
            - self._last_accepted_timestamp_s
        )

        # Defensive fallback. Overall timestamp monotonicity above should
        # normally catch this before reaching here.
        if (
            not math.isfinite(dt_s)
            or dt_s <= 0.0
        ):
            self._landmark_core.reset()
            self._last_accepted_timestamp_s = None

            return self._initialize_measurement(
                observation,
                reset_occurred=True,
                event="timestamp_discontinuity",
            )

        if dt_s > self._reset_gap_s:
            self._landmark_core.reset()
            self._last_accepted_timestamp_s = None

            return self._initialize_measurement(
                observation,
                reset_occurred=True,
                event="reset_gap_exceeded",
            )

        result = self._landmark_core.update(
            observation.landmarks,
            dt_s=dt_s,
        )

        self._last_accepted_timestamp_s = (
            timestamp_s
        )

        return FixedOneEuroTemporalResult(
            landmarks=result.landmarks,
            landmark_diagnostics=(
                result.diagnostics
            ),
            dt_s=dt_s,
            measurement_accepted=True,
            initialization_occurred=False,
            reset_occurred=False,
            event=None,
        )

    def _handle_missing_measurement(
        self,
        timestamp_s: float,
    ) -> FixedOneEuroTemporalResult:
        """Retain short-gap state; reset after a long loss."""

        if (
            not self.initialized
            or self._last_accepted_timestamp_s
            is None
        ):
            return self._empty_result(
                reset_occurred=False,
                event=None,
            )

        elapsed_s = (
            timestamp_s
            - self._last_accepted_timestamp_s
        )

        if elapsed_s > self._reset_gap_s:
            self._landmark_core.reset()
            self._last_accepted_timestamp_s = None

            return self._empty_result(
                reset_occurred=True,
                event="loss_gap_exceeded",
            )

        return self._empty_result(
            reset_occurred=False,
            event=None,
        )

    def _initialize_measurement(
        self,
        observation: LandmarkObservation,
        *,
        reset_occurred: bool,
        event: str | None,
    ) -> FixedOneEuroTemporalResult:
        result = self._landmark_core.update(
            observation.landmarks,
            dt_s=None,
        )

        self._last_accepted_timestamp_s = (
            observation.timestamp_s
        )

        return FixedOneEuroTemporalResult(
            landmarks=result.landmarks,
            landmark_diagnostics=(
                result.diagnostics
            ),
            dt_s=None,
            measurement_accepted=True,
            initialization_occurred=True,
            reset_occurred=reset_occurred,
            event=event,
        )

    @staticmethod
    def _empty_result(
        *,
        reset_occurred: bool,
        event: str | None,
    ) -> FixedOneEuroTemporalResult:
        return FixedOneEuroTemporalResult(
            landmarks=(),
            landmark_diagnostics=(),
            dt_s=None,
            measurement_accepted=False,
            initialization_occurred=False,
            reset_occurred=reset_occurred,
            event=event,
        )
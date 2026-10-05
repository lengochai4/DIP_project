"""Project-specific landmark vectorization of adaptive 1-Euro filtering."""

from __future__ import annotations

from dataclasses import dataclass
import math

from dip_touchless.core import (
    CoordinateSpace,
    Landmark,
)

from .adaptive_policy import (
    adaptive_beta,
    bounded_final_cutoff_hz,
)
from .low_pass import (
    ScalarLowPassFilter,
    low_pass_alpha,
)


@dataclass(frozen=True)
class AdaptiveLandmarkDiagnostics:
    """Internal diagnostics for one adaptive landmark x/y vector."""

    landmark_index: int

    filtered_dx: float
    filtered_dy: float

    speed: float
    beta: float

    min_cutoff_hz: float
    cutoff_hz: float

    signal_alpha: float | None
    derivative_alpha: float | None

    initialization_occurred: bool


@dataclass(frozen=True)
class AdaptiveLandmarkResult:
    """Filtered landmarks plus per-landmark adaptive diagnostics."""

    landmarks: tuple[Landmark, ...]

    diagnostics: tuple[
        AdaptiveLandmarkDiagnostics,
        ...,
    ]


class _AdaptiveLandmarkXYState:
    """Internal temporal state for one landmark."""

    def __init__(self) -> None:
        self.signal_x = ScalarLowPassFilter()
        self.signal_y = ScalarLowPassFilter()

        self.derivative_x = ScalarLowPassFilter()
        self.derivative_y = ScalarLowPassFilter()

    def reset(self) -> None:
        self.signal_x.reset()
        self.signal_y.reset()

        self.derivative_x.reset()
        self.derivative_y.reset()


class AdaptiveOneEuroLandmarkCore:
    """Bounded adaptive 1-Euro x/y filtering per landmark.

    Each landmark owns independent temporal state.

    Per landmark:
        filtered derivative x/y
            -> 2D speed
            -> bounded adaptive beta
            -> bounded signal cutoff
            -> shared signal alpha
            -> filtered x/y

    Model-relative z is passed through unchanged.
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
        self._require_positive_finite(
            base_cutoff_hz,
            name="base_cutoff_hz",
        )

        self._require_positive_finite(
            derivative_cutoff_hz,
            name="derivative_cutoff_hz",
        )

        # Reuse the frozen policy validation rather than
        # silently duplicating parameter semantics here.
        adaptive_beta(
            speed=0.0,
            beta_min=beta_min,
            beta_base=beta_base,
            beta_max=beta_max,
            velocity_gain=velocity_gain,
            velocity_max=velocity_max,
        )

        bounded_final_cutoff_hz(
            min_cutoff_hz=base_cutoff_hz,
            beta=beta_base,
            speed=0.0,
            final_cutoff_min_hz=(
                final_cutoff_min_hz
            ),
            final_cutoff_max_hz=(
                final_cutoff_max_hz
            ),
        )

        self._base_cutoff_hz = float(
            base_cutoff_hz
        )

        self._beta_min = float(beta_min)
        self._beta_base = float(beta_base)
        self._beta_max = float(beta_max)

        self._velocity_gain = float(
            velocity_gain
        )

        self._velocity_max = (
            None
            if velocity_max is None
            else float(velocity_max)
        )

        self._final_cutoff_min_hz = float(
            final_cutoff_min_hz
        )

        self._final_cutoff_max_hz = float(
            final_cutoff_max_hz
        )

        self._derivative_cutoff_hz = float(
            derivative_cutoff_hz
        )

        self._states: dict[
            int,
            _AdaptiveLandmarkXYState,
        ] = {}

        self._expected_indices: tuple[
            int,
            ...,
        ] | None = None

    @property
    def initialized(self) -> bool:
        return self._expected_indices is not None

    def reset(self) -> None:
        """Clear all landmark temporal state."""

        self._states.clear()
        self._expected_indices = None

    def update(
        self,
        landmarks: tuple[Landmark, ...],
        *,
        dt_s: float | None,
        min_cutoff_hz: float | None = None,
    ) -> AdaptiveLandmarkResult:
        """Filter one complete landmark measurement.

        min_cutoff_hz is the effective frame minimum cutoff.

        When omitted, the primary F2 quality-disabled path uses
        the configured base cutoff.
        """

        self._validate_landmarks(
            landmarks
        )

        effective_min_cutoff_hz = (
            self._base_cutoff_hz
            if min_cutoff_hz is None
            else float(min_cutoff_hz)
        )

        self._require_positive_finite(
            effective_min_cutoff_hz,
            name="min_cutoff_hz",
        )

        indices = tuple(
            landmark.index
            for landmark in landmarks
        )

        if not self.initialized:
            if dt_s is not None:
                raise ValueError(
                    "dt_s must be None for initialization"
                )

            self._expected_indices = indices

            return self._initialize(
                landmarks,
                min_cutoff_hz=(
                    effective_min_cutoff_hz
                ),
            )

        if indices != self._expected_indices:
            raise ValueError(
                "landmark indices/order changed after initialization"
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

        derivative_alpha = low_pass_alpha(
            dt_s=dt_s,
            cutoff_hz=self._derivative_cutoff_hz,
        )

        filtered_landmarks: list[
            Landmark
        ] = []

        diagnostics: list[
            AdaptiveLandmarkDiagnostics
        ] = []

        for landmark in landmarks:
            state = self._states[
                landmark.index
            ]

            previous_x = (
                state.signal_x.last_filtered_value
            )

            previous_y = (
                state.signal_y.last_filtered_value
            )

            assert previous_x is not None
            assert previous_y is not None

            raw_dx = (
                landmark.x - previous_x
            ) / dt_s

            raw_dy = (
                landmark.y - previous_y
            ) / dt_s

            filtered_dx = (
                state.derivative_x.filter(
                    raw_dx,
                    alpha=derivative_alpha,
                )
            )

            filtered_dy = (
                state.derivative_y.filter(
                    raw_dy,
                    alpha=derivative_alpha,
                )
            )

            speed = math.hypot(
                filtered_dx,
                filtered_dy,
            )

            if not math.isfinite(speed):
                raise RuntimeError(
                    "landmark speed became invalid"
                )

            beta = adaptive_beta(
                speed=speed,
                beta_min=self._beta_min,
                beta_base=self._beta_base,
                beta_max=self._beta_max,
                velocity_gain=(
                    self._velocity_gain
                ),
                velocity_max=(
                    self._velocity_max
                ),
            )

            cutoff_hz = bounded_final_cutoff_hz(
                min_cutoff_hz=(
                    effective_min_cutoff_hz
                ),
                beta=beta,
                speed=speed,
                final_cutoff_min_hz=(
                    self._final_cutoff_min_hz
                ),
                final_cutoff_max_hz=(
                    self._final_cutoff_max_hz
                ),
            )

            signal_alpha = low_pass_alpha(
                dt_s=dt_s,
                cutoff_hz=cutoff_hz,
            )

            filtered_x = (
                state.signal_x.filter(
                    landmark.x,
                    alpha=signal_alpha,
                )
            )

            filtered_y = (
                state.signal_y.filter(
                    landmark.y,
                    alpha=signal_alpha,
                )
            )

            filtered_landmarks.append(
                Landmark(
                    index=landmark.index,
                    x=filtered_x,
                    y=filtered_y,
                    z=landmark.z,
                    coordinate_space=(
                        landmark.coordinate_space
                    ),
                )
            )

            diagnostics.append(
                AdaptiveLandmarkDiagnostics(
                    landmark_index=(
                        landmark.index
                    ),
                    filtered_dx=filtered_dx,
                    filtered_dy=filtered_dy,
                    speed=speed,
                    beta=beta,
                    min_cutoff_hz=(
                        effective_min_cutoff_hz
                    ),
                    cutoff_hz=cutoff_hz,
                    signal_alpha=signal_alpha,
                    derivative_alpha=(
                        derivative_alpha
                    ),
                    initialization_occurred=False,
                )
            )

        return AdaptiveLandmarkResult(
            landmarks=tuple(
                filtered_landmarks
            ),
            diagnostics=tuple(
                diagnostics
            ),
        )

    def _initialize(
        self,
        landmarks: tuple[Landmark, ...],
        *,
        min_cutoff_hz: float,
    ) -> AdaptiveLandmarkResult:
        filtered_landmarks: list[
            Landmark
        ] = []

        diagnostics: list[
            AdaptiveLandmarkDiagnostics
        ] = []

        beta = adaptive_beta(
            speed=0.0,
            beta_min=self._beta_min,
            beta_base=self._beta_base,
            beta_max=self._beta_max,
            velocity_gain=self._velocity_gain,
            velocity_max=self._velocity_max,
        )

        cutoff_hz = bounded_final_cutoff_hz(
            min_cutoff_hz=min_cutoff_hz,
            beta=beta,
            speed=0.0,
            final_cutoff_min_hz=(
                self._final_cutoff_min_hz
            ),
            final_cutoff_max_hz=(
                self._final_cutoff_max_hz
            ),
        )

        for landmark in landmarks:
            state = _AdaptiveLandmarkXYState()

            state.derivative_x.filter(
                0.0,
                alpha=1.0,
            )

            state.derivative_y.filter(
                0.0,
                alpha=1.0,
            )

            filtered_x = state.signal_x.filter(
                landmark.x,
                alpha=1.0,
            )

            filtered_y = state.signal_y.filter(
                landmark.y,
                alpha=1.0,
            )

            self._states[
                landmark.index
            ] = state

            filtered_landmarks.append(
                Landmark(
                    index=landmark.index,
                    x=filtered_x,
                    y=filtered_y,
                    z=landmark.z,
                    coordinate_space=(
                        landmark.coordinate_space
                    ),
                )
            )

            diagnostics.append(
                AdaptiveLandmarkDiagnostics(
                    landmark_index=(
                        landmark.index
                    ),
                    filtered_dx=0.0,
                    filtered_dy=0.0,
                    speed=0.0,
                    beta=beta,
                    min_cutoff_hz=(
                        min_cutoff_hz
                    ),
                    cutoff_hz=cutoff_hz,
                    signal_alpha=None,
                    derivative_alpha=None,
                    initialization_occurred=True,
                )
            )

        return AdaptiveLandmarkResult(
            landmarks=tuple(
                filtered_landmarks
            ),
            diagnostics=tuple(
                diagnostics
            ),
        )

    @staticmethod
    def _validate_landmarks(
        landmarks: tuple[Landmark, ...],
    ) -> None:
        if not landmarks:
            raise ValueError(
                "landmarks must not be empty"
            )

        indices = [
            landmark.index
            for landmark in landmarks
        ]

        if len(indices) != len(set(indices)):
            raise ValueError(
                "landmark indices must be unique"
            )

        for landmark in landmarks:
            if (
                landmark.coordinate_space
                is not CoordinateSpace.FRAME_NORMALIZED
            ):
                raise ValueError(
                    "adaptive landmark filtering requires "
                    "FRAME_NORMALIZED x/y"
                )

            if not all(
                math.isfinite(value)
                for value in (
                    landmark.x,
                    landmark.y,
                    landmark.z,
                )
            ):
                raise ValueError(
                    "landmark coordinates must be finite"
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
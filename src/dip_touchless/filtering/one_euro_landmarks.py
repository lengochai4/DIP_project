"""Project-specific landmark vectorization of fixed 1-Euro filtering."""

from __future__ import annotations

from dataclasses import dataclass
import math

from dip_touchless.core import (
    CoordinateSpace,
    Landmark,
)

from .low_pass import (
    ScalarLowPassFilter,
    low_pass_alpha,
)


@dataclass(frozen=True)
class LandmarkOneEuroDiagnostics:
    """Internal diagnostics for one landmark x/y vector."""

    landmark_index: int
    filtered_dx: float
    filtered_dy: float
    speed: float
    cutoff_hz: float
    signal_alpha: float | None
    derivative_alpha: float | None
    initialization_occurred: bool


@dataclass(frozen=True)
class LandmarkOneEuroResult:
    """Filtered landmarks plus per-landmark diagnostics."""

    landmarks: tuple[Landmark, ...]
    diagnostics: tuple[
        LandmarkOneEuroDiagnostics,
        ...
    ]


class _LandmarkXYState:
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


class FixedOneEuroLandmarkCore:
    """Fixed 1-Euro x/y vector filtering per landmark.

    Each landmark owns independent temporal state.

    For one landmark:
        filtered derivative x/y
            -> 2D speed
            -> shared cutoff
            -> shared signal alpha
            -> filtered x/y

    Model-relative z is passed through unchanged.
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

        self._states: dict[
            int,
            _LandmarkXYState,
        ] = {}

        self._expected_indices: tuple[
            int,
            ...
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
    ) -> LandmarkOneEuroResult:
        """Filter one complete landmark measurement."""

        self._validate_landmarks(
            landmarks
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
                landmarks
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
            LandmarkOneEuroDiagnostics
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

            cutoff_hz = (
                self._min_cutoff_hz
                + self._beta * speed
            )

            if (
                not math.isfinite(cutoff_hz)
                or cutoff_hz <= 0.0
            ):
                raise RuntimeError(
                    "landmark signal cutoff became invalid"
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
                LandmarkOneEuroDiagnostics(
                    landmark_index=(
                        landmark.index
                    ),
                    filtered_dx=filtered_dx,
                    filtered_dy=filtered_dy,
                    speed=speed,
                    cutoff_hz=cutoff_hz,
                    signal_alpha=signal_alpha,
                    derivative_alpha=(
                        derivative_alpha
                    ),
                    initialization_occurred=False,
                )
            )

        return LandmarkOneEuroResult(
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
    ) -> LandmarkOneEuroResult:
        filtered_landmarks: list[
            Landmark
        ] = []

        diagnostics: list[
            LandmarkOneEuroDiagnostics
        ] = []

        for landmark in landmarks:
            state = _LandmarkXYState()

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
                LandmarkOneEuroDiagnostics(
                    landmark_index=(
                        landmark.index
                    ),
                    filtered_dx=0.0,
                    filtered_dy=0.0,
                    speed=0.0,
                    cutoff_hz=(
                        self._min_cutoff_hz
                    ),
                    signal_alpha=None,
                    derivative_alpha=None,
                    initialization_occurred=True,
                )
            )

        return LandmarkOneEuroResult(
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
                    "fixed landmark filtering requires "
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
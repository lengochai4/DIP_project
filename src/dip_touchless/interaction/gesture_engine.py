"""Stateful renderer-independent gesture engine."""

from __future__ import annotations

import math

from dip_touchless.core import (
    CoordinateSpace,
    InteractionState,
    TrackingFrame,
    TrackingStatus,
)

from .gesture_math import (
    bounded_rotation_delta,
    bounded_scale_delta,
    normalized_pinch_ratio,
)


Point2D = tuple[float, float]


class DeterministicGestureEngine:
    """Course-baseline deterministic gesture state machine."""

    _USABLE_STATUSES = {
        TrackingStatus.VALID,
        TrackingStatus.REACQUIRED,
    }

    def __init__(
        self,
        *,
        pointer_landmark_index: int,
        pinch_thumb_landmark_index: int,
        pinch_index_landmark_index: int,
        hand_scale_landmark_a: int,
        hand_scale_landmark_b: int,
        hand_scale_epsilon: float,
        pinch_on: float,
        pinch_off: float,
        rotation_deadzone: float,
        rotation_gain: float,
        rotation_max_delta_rad: float,
        scale_deadzone: float,
        scale_gain: float,
        scale_max_delta: float,
    ) -> None:
        self._require_index(
            pointer_landmark_index,
            name="pointer_landmark_index",
        )
        self._require_index(
            pinch_thumb_landmark_index,
            name="pinch_thumb_landmark_index",
        )
        self._require_index(
            pinch_index_landmark_index,
            name="pinch_index_landmark_index",
        )
        self._require_index(
            hand_scale_landmark_a,
            name="hand_scale_landmark_a",
        )
        self._require_index(
            hand_scale_landmark_b,
            name="hand_scale_landmark_b",
        )

        if (
            pinch_thumb_landmark_index
            == pinch_index_landmark_index
        ):
            raise ValueError(
                "pinch landmarks must be distinct"
            )

        if (
            hand_scale_landmark_a
            == hand_scale_landmark_b
        ):
            raise ValueError(
                "hand-scale landmarks must be distinct"
            )

        self._require_positive_finite(
            hand_scale_epsilon,
            name="hand_scale_epsilon",
        )

        self._require_nonnegative_finite(
            pinch_on,
            name="pinch_on",
        )
        self._require_nonnegative_finite(
            pinch_off,
            name="pinch_off",
        )

        if not pinch_on < pinch_off:
            raise ValueError(
                "pinch_on must be less than pinch_off"
            )

        self._require_nonnegative_finite(
            rotation_deadzone,
            name="rotation_deadzone",
        )
        self._require_nonnegative_finite(
            rotation_gain,
            name="rotation_gain",
        )
        self._require_positive_finite(
            rotation_max_delta_rad,
            name="rotation_max_delta_rad",
        )

        self._require_nonnegative_finite(
            scale_deadzone,
            name="scale_deadzone",
        )
        self._require_nonnegative_finite(
            scale_gain,
            name="scale_gain",
        )
        self._require_positive_finite(
            scale_max_delta,
            name="scale_max_delta",
        )

        self._pointer_landmark_index = (
            pointer_landmark_index
        )
        self._pinch_thumb_landmark_index = (
            pinch_thumb_landmark_index
        )
        self._pinch_index_landmark_index = (
            pinch_index_landmark_index
        )
        self._hand_scale_landmark_a = (
            hand_scale_landmark_a
        )
        self._hand_scale_landmark_b = (
            hand_scale_landmark_b
        )

        self._hand_scale_epsilon = float(
            hand_scale_epsilon
        )

        self._pinch_on = float(pinch_on)
        self._pinch_off = float(pinch_off)

        self._rotation_deadzone = float(
            rotation_deadzone
        )
        self._rotation_gain = float(
            rotation_gain
        )
        self._rotation_max_delta_rad = float(
            rotation_max_delta_rad
        )

        self._scale_deadzone = float(
            scale_deadzone
        )
        self._scale_gain = float(
            scale_gain
        )
        self._scale_max_delta = float(
            scale_max_delta
        )

        self._required_indices = frozenset(
            {
                self._pointer_landmark_index,
                self._pinch_thumb_landmark_index,
                self._pinch_index_landmark_index,
                self._hand_scale_landmark_a,
                self._hand_scale_landmark_b,
            }
        )

        self.reset()

    def reset(self) -> None:
        """Clear pointer, pinch, and scale temporal state."""

        self._initialized = False

        self._previous_pointer: (
            Point2D | None
        ) = None

        self._previous_pinch_ratio: (
            float | None
        ) = None

        self._pinch_active = False

    def update(
        self,
        frame: TrackingFrame,
    ) -> InteractionState:
        """Map one TrackingFrame into InteractionState."""

        if frame.status not in self._USABLE_STATUSES:
            return self._invalidate(
                frame
            )

        points = self._required_points(
            frame
        )

        if points is None:
            return self._invalidate(
                frame
            )

        pointer = points[
            self._pointer_landmark_index
        ]

        pinch_ratio = normalized_pinch_ratio(
            thumb_xy=points[
                self._pinch_thumb_landmark_index
            ],
            index_xy=points[
                self._pinch_index_landmark_index
            ],
            scale_a_xy=points[
                self._hand_scale_landmark_a
            ],
            scale_b_xy=points[
                self._hand_scale_landmark_b
            ],
            epsilon=self._hand_scale_epsilon,
        )

        initialization = (
            not self._initialized
            or frame.status
            is TrackingStatus.REACQUIRED
            or frame.filter_diagnostics.reset_occurred
        )

        if initialization:
            return self._initialize(
                frame,
                pointer=pointer,
                pinch_ratio=pinch_ratio,
            )

        if (
            self._previous_pointer is None
            or self._previous_pinch_ratio is None
        ):
            raise RuntimeError(
                "initialized gesture engine "
                "is missing previous state"
            )

        delta_x = (
            pointer[0]
            - self._previous_pointer[0]
        )
        delta_y = (
            pointer[1]
            - self._previous_pointer[1]
        )

        rotation_delta = (
            bounded_rotation_delta(
                delta_x=delta_x,
                delta_y=delta_y,
                deadzone=self._rotation_deadzone,
                gain=self._rotation_gain,
                max_delta_rad=(
                    self._rotation_max_delta_rad
                ),
            )
        )

        previous_pinch_active = (
            self._pinch_active
        )

        pinch_active = self._next_pinch_state(
            pinch_ratio
        )

        scale_delta = 0.0

        if (
            previous_pinch_active
            and pinch_active
        ):
            scale_delta = bounded_scale_delta(
                current_ratio=pinch_ratio,
                previous_ratio=(
                    self._previous_pinch_ratio
                ),
                deadzone=self._scale_deadzone,
                gain=self._scale_gain,
                max_delta=self._scale_max_delta,
            )

        self._previous_pointer = pointer
        self._previous_pinch_ratio = (
            pinch_ratio
        )
        self._pinch_active = pinch_active

        return InteractionState(
            run_id=frame.run_id,
            frame_id=frame.frame_id,
            timestamp_s=frame.timestamp_s,
            interaction_valid=True,
            pointer_xy=pointer,
            pinch_ratio=pinch_ratio,
            pinch_active=pinch_active,
            rotation_delta=rotation_delta,
            scale_delta=scale_delta,
        )

    def _initialize(
        self,
        frame: TrackingFrame,
        *,
        pointer: Point2D,
        pinch_ratio: float,
    ) -> InteractionState:
        self._initialized = True

        self._previous_pointer = pointer
        self._previous_pinch_ratio = (
            pinch_ratio
        )

        self._pinch_active = False

        return InteractionState(
            run_id=frame.run_id,
            frame_id=frame.frame_id,
            timestamp_s=frame.timestamp_s,
            interaction_valid=False,
            pointer_xy=pointer,
            pinch_ratio=pinch_ratio,
            pinch_active=False,
            rotation_delta=(0.0, 0.0),
            scale_delta=0.0,
        )

    def _invalidate(
        self,
        frame: TrackingFrame,
    ) -> InteractionState:
        self.reset()

        return InteractionState(
            run_id=frame.run_id,
            frame_id=frame.frame_id,
            timestamp_s=frame.timestamp_s,
            interaction_valid=False,
            pointer_xy=None,
            pinch_ratio=None,
            pinch_active=False,
            rotation_delta=(0.0, 0.0),
            scale_delta=0.0,
        )

    def _next_pinch_state(
        self,
        pinch_ratio: float,
    ) -> bool:
        if self._pinch_active:
            if pinch_ratio > self._pinch_off:
                return False

            return True

        if pinch_ratio < self._pinch_on:
            return True

        return False

    def _required_points(
        self,
        frame: TrackingFrame,
    ) -> dict[int, Point2D] | None:
        points: dict[
            int,
            Point2D,
        ] = {}

        for landmark in frame.filtered_landmarks:
            if (
                landmark.index
                not in self._required_indices
            ):
                continue

            if landmark.index in points:
                return None

            if (
                landmark.coordinate_space
                is not
                CoordinateSpace.FRAME_NORMALIZED
            ):
                return None

            if (
                not math.isfinite(landmark.x)
                or not math.isfinite(landmark.y)
            ):
                return None

            points[landmark.index] = (
                float(landmark.x),
                float(landmark.y),
            )

        if (
            set(points)
            != self._required_indices
        ):
            return None

        return points

    @staticmethod
    def _require_index(
        value: int,
        *,
        name: str,
    ) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise ValueError(
                f"{name} must be a "
                "non-negative integer"
            )

    @staticmethod
    def _require_nonnegative_finite(
        value: float,
        *,
        name: str,
    ) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                (int, float),
            )
            or not math.isfinite(value)
            or value < 0.0
        ):
            raise ValueError(
                f"{name} must be finite "
                "and non-negative"
            )

    @classmethod
    def _require_positive_finite(
        cls,
        value: float,
        *,
        name: str,
    ) -> None:
        cls._require_nonnegative_finite(
            value,
            name=name,
        )

        if value <= 0.0:
            raise ValueError(
                f"{name} must be positive"
            )
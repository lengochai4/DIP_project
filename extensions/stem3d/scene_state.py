"""Renderer-independent state for the minimal STEM 3D extension."""

from __future__ import annotations

from dataclasses import dataclass
import math

from dip_touchless.core import InteractionState


@dataclass(frozen=True)
class SceneTransform:
    """Accumulated transform consumed by a renderer."""

    yaw_rad: float
    pitch_rad: float
    scale: float


class Stem3DSceneState:
    """Accumulate InteractionState commands into scene transform."""

    def __init__(
        self,
        *,
        initial_scale: float,
        min_scale: float,
        max_scale: float,
    ) -> None:
        self._require_positive_finite(
            initial_scale,
            name="initial_scale",
        )
        self._require_positive_finite(
            min_scale,
            name="min_scale",
        )
        self._require_positive_finite(
            max_scale,
            name="max_scale",
        )

        if not (
            min_scale
            <= initial_scale
            <= max_scale
        ):
            raise ValueError(
                "scale bounds must satisfy "
                "min_scale <= initial_scale <= max_scale"
            )

        self._initial_scale = float(
            initial_scale
        )
        self._min_scale = float(
            min_scale
        )
        self._max_scale = float(
            max_scale
        )

        self.reset()

    @property
    def transform(self) -> SceneTransform:
        return self._transform

    def reset(self) -> None:
        """Restore the renderer transform to its initial state."""

        self._transform = SceneTransform(
            yaw_rad=0.0,
            pitch_rad=0.0,
            scale=self._initial_scale,
        )

    def consume(
        self,
        state: InteractionState,
    ) -> SceneTransform:
        """Consume one public Core InteractionState."""

        if not state.interaction_valid:
            return self._transform

        yaw_delta, pitch_delta = (
            state.rotation_delta
        )

        self._require_finite(
            yaw_delta,
            name="yaw_delta",
        )
        self._require_finite(
            pitch_delta,
            name="pitch_delta",
        )
        self._require_finite(
            state.scale_delta,
            name="scale_delta",
        )

        next_scale = (
            self._transform.scale
            + state.scale_delta
        )

        next_scale = max(
            self._min_scale,
            min(
                next_scale,
                self._max_scale,
            ),
        )

        self._transform = SceneTransform(
            yaw_rad=(
                self._transform.yaw_rad
                + yaw_delta
            ),
            pitch_rad=(
                self._transform.pitch_rad
                + pitch_delta
            ),
            scale=next_scale,
        )

        return self._transform

    @staticmethod
    def _require_finite(
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
        ):
            raise ValueError(
                f"{name} must be finite"
            )

    @classmethod
    def _require_positive_finite(
        cls,
        value: float,
        *,
        name: str,
    ) -> None:
        cls._require_finite(
            value,
            name=name,
        )

        if value <= 0.0:
            raise ValueError(
                f"{name} must be positive"
            )
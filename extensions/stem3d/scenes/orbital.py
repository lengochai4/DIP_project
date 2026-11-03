"""Deterministic, simplified orbital-system visualization."""

from __future__ import annotations

import math

from dip_touchless.core import InteractionState

from ..scene_state import Stem3DSceneState
from .base import SceneViewport
from .metadata import SceneMetadata
from .visuals import SceneFrame, SceneLine, SceneSphere


_TAU = math.tau
_ANGULAR_SPEED_RAD_S = 0.36
_ORBITAL_PERIOD_S = _TAU / _ANGULAR_SPEED_RAD_S
_ORBIT_RADIUS_X = 1.65
_ORBIT_RADIUS_Z = 1.18
_PATH_COLOR = (0.28, 0.40, 0.53)


class OrbitalSystemScene:
    """Show a central star and one body on a slow educational orbit."""

    metadata = SceneMetadata(
        scene_id="orbital-system",
        title="Orbital System",
        category="Physics / Astronomy",
        description=(
            "A central body and a smaller orbiting body on a visible "
            "elliptical path, shown as a simplified educational model."
        ),
        educational_topic=(
            "Orbital paths, relative motion, and three-dimensional orientation."
        ),
        interaction_hint=(
            "The orbit advances slowly with elapsed runtime time; move the "
            "index fingertip to rotate the view and pinch to scale."
        ),
    )

    def __init__(self, scene_state: Stem3DSceneState) -> None:
        self._scene_state = scene_state
        self._active = False
        self._phase_rad = 0.0

    @property
    def id(self) -> str:
        return self.metadata.scene_id

    @property
    def title(self) -> str:
        return self.metadata.title

    @property
    def category(self) -> str:
        return self.metadata.category

    @property
    def active(self) -> bool:
        return self._active

    @property
    def phase_rad(self) -> float:
        return self._phase_rad

    @property
    def transform(self):
        return self._scene_state.transform

    @property
    def orbiting_position(self) -> tuple[float, float, float]:
        return (
            _ORBIT_RADIUS_X * math.cos(self._phase_rad),
            0.0,
            _ORBIT_RADIUS_Z * math.sin(self._phase_rad),
        )

    @property
    def frame(self) -> SceneFrame:
        position = self.orbiting_position
        path_points = tuple(
            (
                _ORBIT_RADIUS_X * math.cos(_TAU * index / 96),
                0.0,
                _ORBIT_RADIUS_Z * math.sin(_TAU * index / 96),
            )
            for index in range(96)
        )
        path_lines = tuple(
            SceneLine(
                start=path_points[index],
                end=path_points[(index + 1) % len(path_points)],
                color=_PATH_COLOR,
                width=1.5,
            )
            for index in range(len(path_points))
        )
        return SceneFrame(
            scene_id=self.id,
            title=self.title,
            subtitle="Simplified elliptical orbit - educational visualization",
            transform=self._scene_state.transform,
            lines=path_lines,
            spheres=(
                SceneSphere(
                    center=(0.0, 0.0, 0.0),
                    radius=0.43,
                    color=(1.0, 0.68, 0.24),
                ),
                SceneSphere(
                    center=position,
                    radius=0.19,
                    color=(0.34, 0.70, 0.91),
                ),
            ),
        )

    def activate(self) -> None:
        self._active = True

    def deactivate(self) -> None:
        self._active = False

    def reset(self) -> None:
        self._scene_state.reset()
        self._phase_rad = 0.0

    def update(self, dt_s: float) -> None:
        self._require_active()
        if (
            isinstance(dt_s, bool)
            or not isinstance(dt_s, (int, float))
            or not math.isfinite(dt_s)
            or dt_s < 0.0
        ):
            raise ValueError("orbital dt_s must be finite and non-negative")

        # Reduce first so even very large finite elapsed intervals stay safe.
        elapsed_within_period = float(dt_s) % _ORBITAL_PERIOD_S
        self._phase_rad = (
            self._phase_rad
            + elapsed_within_period * _ANGULAR_SPEED_RAD_S
        ) % _TAU

    def apply_interaction(self, state: InteractionState) -> None:
        self._require_active()
        self._scene_state.consume(state)

    def render(self, viewport: SceneViewport) -> None:
        self._require_active()
        viewport.render(self.frame)

    def _require_active(self) -> None:
        if not self._active:
            raise RuntimeError(f"STEM scene {self.id!r} is not active")

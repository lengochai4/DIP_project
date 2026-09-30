"""Coordinate-cube scene adapter around the existing bounded scene state."""

from __future__ import annotations

from typing import Any

from dip_touchless.core import InteractionState

from ..scene_state import SceneTransform, Stem3DSceneState


class CoordinateCubeScene:
    """Apply public interaction commands to the existing coordinate cube."""

    id = "coordinate-cube"
    title = "Coordinate Cube"
    category = "coordinate-geometry"

    def __init__(self, scene_state: Stem3DSceneState) -> None:
        self._scene_state = scene_state
        self._active = False

    @property
    def active(self) -> bool:
        return self._active

    @property
    def transform(self) -> SceneTransform:
        return self._scene_state.transform

    def activate(self) -> None:
        self._active = True

    def deactivate(self) -> None:
        self._active = False

    def reset(self) -> None:
        self._scene_state.reset()

    def update(self, dt_s: float) -> None:
        del dt_s

    def apply_interaction(
        self,
        state: InteractionState,
    ) -> None:
        self._require_active()
        self._scene_state.consume(state)

    def render(self, viewport: Any) -> None:
        self._require_active()
        viewport.render(self._scene_state.transform)

    def _require_active(self) -> None:
        if not self._active:
            raise RuntimeError(
                f"STEM scene {self.id!r} is not active"
            )

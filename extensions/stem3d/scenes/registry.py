"""Small local registry with explicit scene lifecycle transitions."""

from __future__ import annotations

from collections.abc import Iterable

from .base import STEMScene


class SceneRegistry:
    """Own scene lookup and activation without a remote plugin system."""

    def __init__(
        self,
        scenes: Iterable[STEMScene],
        *,
        initial_scene_id: str,
    ) -> None:
        if (
            not isinstance(initial_scene_id, str)
            or not initial_scene_id.strip()
        ):
            raise ValueError(
                "initial STEM scene id must be a non-empty string"
            )
        self._scenes: dict[str, STEMScene] = {}
        self._initial_scene_id = initial_scene_id
        self._active_scene_id: str | None = None

        for scene in scenes:
            self.register(scene)

        if not self._scenes:
            raise ValueError("scene registry must contain at least one scene")
        if initial_scene_id not in self._scenes:
            raise KeyError(
                f"initial STEM scene is not registered: {initial_scene_id}"
            )

    @property
    def scenes(self) -> tuple[STEMScene, ...]:
        return tuple(self._scenes.values())

    @property
    def initial_scene_id(self) -> str:
        return self._initial_scene_id

    @property
    def active_scene_id(self) -> str | None:
        return self._active_scene_id

    @property
    def active_scene(self) -> STEMScene | None:
        if self._active_scene_id is None:
            return None
        return self._scenes[self._active_scene_id]

    def register(self, scene: STEMScene) -> None:
        scene_id = getattr(scene, "id", None)
        if not isinstance(scene_id, str) or not scene_id.strip():
            raise ValueError("STEM scene id must be a non-empty string")
        if scene_id in self._scenes:
            raise ValueError(f"duplicate STEM scene id: {scene_id}")

        for field in ("title", "category"):
            value = getattr(scene, field, None)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"STEM scene {scene_id!r} requires a non-empty {field}"
                )
        for method in (
            "activate",
            "deactivate",
            "reset",
            "update",
            "apply_interaction",
            "render",
        ):
            if not callable(getattr(scene, method, None)):
                raise ValueError(
                    f"STEM scene {scene_id!r} is missing {method}()"
                )

        self._scenes[scene_id] = scene

    def get(self, scene_id: str) -> STEMScene:
        try:
            return self._scenes[scene_id]
        except KeyError as exc:
            raise KeyError(f"unknown STEM scene id: {scene_id}") from exc

    def activate_initial(self) -> STEMScene:
        return self.activate(self._initial_scene_id)

    def activate(self, scene_id: str) -> STEMScene:
        scene = self.get(scene_id)
        if self._active_scene_id == scene_id:
            return scene

        previous = self.active_scene
        if previous is not None:
            self._active_scene_id = None
            previous.deactivate()

        scene.activate()
        self._active_scene_id = scene_id
        return scene

    def deactivate(self) -> None:
        scene = self.active_scene
        self._active_scene_id = None
        if scene is not None:
            scene.deactivate()

    def reset_active(self) -> None:
        scene = self.active_scene
        if scene is None:
            raise RuntimeError("no STEM scene is active")
        scene.reset()

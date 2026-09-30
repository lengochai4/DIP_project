"""Thin application boundary for the STEM 3D extension."""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Protocol

from dip_touchless.core import (
    InteractionState,
)

from .scenes import (
    STEMScene,
    SceneRegistry,
    SceneFrame,
)


class StemRenderer(Protocol):
    def open(self) -> None: ...

    def render(
        self,
        frame: SceneFrame,
    ) -> None: ...

    def close_requested(
        self,
    ) -> bool: ...

    def close(self) -> None: ...


class RendererFailure(RuntimeError):
    """Presentation-layer error raised when the STEM viewport fails."""

    component = "renderer"


class Stem3DExtension:
    """Route public interaction commands through the active STEM scene."""

    def __init__(
        self,
        *,
        scene_registry: SceneRegistry,
        renderer: StemRenderer,
    ) -> None:
        self._scene_registry = scene_registry
        self._renderer = renderer
        self._renderer_open = False
        self._previous_timestamp_s: float | None = None

    @property
    def active_scene(self) -> STEMScene | None:
        return self._scene_registry.active_scene

    @property
    def active_scene_id(self) -> str | None:
        return self._scene_registry.active_scene_id

    def set_keyboard_action(
        self,
        action: Callable[[str], None],
    ) -> None:
        """Route renderer-window character keys through the app controls."""

        set_key_consumer = getattr(
            self._renderer,
            "set_key_consumer",
            None,
        )
        if callable(set_key_consumer):
            set_key_consumer(action)

    def open(self) -> None:
        if self._renderer_open:
            return

        try:
            self._renderer.open()
        except Exception as exc:
            try:
                self._renderer.close()
            except Exception as cleanup_error:
                exc.add_note(
                    f"renderer cleanup also failed: {cleanup_error}"
                )
            raise RendererFailure(
                f"3D renderer initialization failed: {exc}"
            ) from exc
        self._renderer_open = True
        try:
            scene = self._scene_registry.activate_initial()
            self._render_scene(scene)
        except Exception:
            try:
                self._scene_registry.deactivate()
            finally:
                try:
                    self._renderer.close()
                finally:
                    self._renderer_open = False
            raise

    def consume(
        self,
        state: InteractionState,
    ) -> None:
        scene = self._require_active_scene()
        timestamp_s = state.timestamp_s
        if (
            isinstance(timestamp_s, bool)
            or not isinstance(timestamp_s, (int, float))
            or not math.isfinite(timestamp_s)
        ):
            raise ValueError("InteractionState timestamp must be finite")

        dt_s = 0.0
        if self._previous_timestamp_s is not None:
            dt_s = timestamp_s - self._previous_timestamp_s
            if dt_s < 0.0:
                raise ValueError(
                    "InteractionState timestamps must be non-decreasing"
                )

        scene.apply_interaction(state)
        scene.update(dt_s)
        self._previous_timestamp_s = float(timestamp_s)
        self._render_scene(scene)

    def activate_scene(self, scene_id: str) -> STEMScene:
        """Activate a registered scene and display its initial state."""

        if not self._renderer_open:
            raise RuntimeError("STEM extension is not open")
        scene = self._scene_registry.activate(scene_id)
        self._previous_timestamp_s = None
        self._render_scene(scene)
        return scene

    def refresh_active_scene(self) -> STEMScene:
        """Render the current scene after a presentation-only option change."""

        if not self._renderer_open:
            raise RuntimeError("STEM extension is not open")
        scene = self._require_active_scene()
        self._render_scene(scene)
        return scene

    def reset(self) -> None:
        """Reset the active scene and refresh the renderer if open."""

        self._scene_registry.reset_active()
        self._previous_timestamp_s = None
        if self._renderer_open:
            scene = self._require_active_scene()
            self._render_scene(scene)

    def close_requested(
        self,
    ) -> bool:
        return (
            self._renderer
            .close_requested()
        )

    def close(self) -> None:
        try:
            self._scene_registry.deactivate()
        finally:
            try:
                if self._renderer_open:
                    try:
                        self._renderer.close()
                    except Exception as exc:
                        raise RendererFailure(
                            f"3D renderer shutdown failed: {exc}"
                        ) from exc
            finally:
                self._renderer_open = False
                self._previous_timestamp_s = None

    def _require_active_scene(self) -> STEMScene:
        if not self._renderer_open:
            raise RuntimeError("STEM extension is not open")
        scene = self._scene_registry.active_scene
        if scene is None:
            raise RuntimeError("no STEM scene is active")
        return scene

    def _render_scene(self, scene: STEMScene) -> None:
        try:
            scene.render(self._renderer)
        except RendererFailure:
            raise
        except Exception as exc:
            raise RendererFailure(
                f"3D renderer failed while drawing {scene.title}: {exc}"
            ) from exc

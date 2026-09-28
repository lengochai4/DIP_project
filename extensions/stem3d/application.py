"""Thin application boundary for the STEM 3D extension."""

from __future__ import annotations

from typing import Protocol

from dip_touchless.core import (
    InteractionState,
)

from .scene_state import (
    SceneTransform,
    Stem3DSceneState,
)


class StemRenderer(Protocol):
    def open(self) -> None: ...

    def render(
        self,
        transform: SceneTransform,
    ) -> None: ...

    def close_requested(
        self,
    ) -> bool: ...

    def close(self) -> None: ...


class Stem3DExtension:
    """Consume InteractionState and drive a renderer."""

    def __init__(
        self,
        *,
        scene_state: Stem3DSceneState,
        renderer: StemRenderer,
    ) -> None:
        self._scene_state = (
            scene_state
        )
        self._renderer = renderer

    @property
    def transform(
        self,
    ) -> SceneTransform:
        return (
            self._scene_state.transform
        )

    def open(self) -> None:
        self._renderer.open()

    def consume(
        self,
        state: InteractionState,
    ) -> SceneTransform:
        transform = (
            self._scene_state.consume(
                state
            )
        )

        self._renderer.render(
            transform
        )

        return transform

    def close_requested(
        self,
    ) -> bool:
        return (
            self._renderer
            .close_requested()
        )

    def close(self) -> None:
        self._renderer.close()
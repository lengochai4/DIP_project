"""Structural contract for renderer-independent STEM scenes."""

from __future__ import annotations

from typing import Protocol

from dip_touchless.core import InteractionState

from .metadata import SceneMetadata
from .visuals import SceneFrame


class SceneViewport(Protocol):
    """Renderer seam that accepts immutable scene geometry."""

    def render(self, frame: SceneFrame) -> None: ...


class STEMScene(Protocol):
    """One Extension-owned educational scene."""

    metadata: SceneMetadata

    @property
    def id(self) -> str: ...

    @property
    def title(self) -> str: ...

    @property
    def category(self) -> str: ...

    def activate(self) -> None: ...

    def deactivate(self) -> None: ...

    def reset(self) -> None: ...

    def update(self, dt_s: float) -> None: ...

    def apply_interaction(
        self,
        state: InteractionState,
    ) -> None: ...

    def render(self, viewport: SceneViewport) -> None: ...

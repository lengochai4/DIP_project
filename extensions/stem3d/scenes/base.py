"""Structural contract for renderer-independent STEM scenes."""

from __future__ import annotations

from typing import Any, Protocol

from dip_touchless.core import InteractionState


class STEMScene(Protocol):
    """One Extension-owned educational scene."""

    id: str
    title: str
    category: str

    def activate(self) -> None: ...

    def deactivate(self) -> None: ...

    def reset(self) -> None: ...

    def update(self, dt_s: float) -> None: ...

    def apply_interaction(
        self,
        state: InteractionState,
    ) -> None: ...

    def render(self, viewport: Any) -> None: ...

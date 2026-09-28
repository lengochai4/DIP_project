"""Project-owned public interfaces.

External providers and application extensions should interact with the
DIP Core through these protocols rather than provider-specific classes.
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from .contracts import (
    FilterDiagnostics,
    FramePacket,
    InteractionState,
    Landmark,
    LandmarkObservation,
    TrackingFrame,
)


class FrameSource(Protocol):
    def open(self) -> None:
        """Open the underlying frame source."""
        ...

    def read(self) -> FramePacket | None:
        """Return the next frame, or None for normal replay EOF."""
        ...

    def close(self) -> None:
        """Release the frame source."""
        ...


class LandmarkProvider(Protocol):
    def process(
        self,
        frame: FramePacket,
    ) -> LandmarkObservation:
        """Convert one project-owned frame into a landmark observation."""
        ...


class LandmarkFilter(Protocol):
    def update(
        self,
        observation: LandmarkObservation,
    ) -> tuple[tuple[Landmark, ...], FilterDiagnostics]:
        """Filter a project-owned landmark observation."""
        ...

    def reset(self) -> None:
        """Clear temporal state."""
        ...


class GestureEngine(Protocol):
    def update(
        self,
        frame: TrackingFrame,
    ) -> InteractionState:
        """Map one tracking frame into renderer-independent interaction state."""
        ...

    def reset(self) -> None:
        """Clear all gesture temporal state."""
        ...


class RunLogger(Protocol):
    def start_run(
        self,
        metadata: Mapping[str, Any],
        resolved_config: Mapping[str, Any],
    ) -> None:
        """Create run artifacts and freeze run identity."""
        ...

    def log_tracking_frame(
        self,
        frame: TrackingFrame,
    ) -> None:
        """Record one tracking frame."""
        ...

    def log_interaction_state(
        self,
        state: InteractionState,
    ) -> None:
        """Record the interaction result associated with a frame."""
        ...

    def log_event(
        self,
        event: Mapping[str, Any],
    ) -> None:
        """Record an explicit diagnostic/event."""
        ...

    def close(self) -> None:
        """Flush and close run artifacts."""
        ...
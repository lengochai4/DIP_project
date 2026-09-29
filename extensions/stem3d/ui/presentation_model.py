"""Immutable presentation values adapted from public runtime contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from dip_touchless.core import (
    ColorSpace,
    FramePacket,
    InteractionState as CoreInteractionState,
    TrackingFrame,
)


class ApplicationPhase(str, Enum):
    READY = "READY"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class ApplicationState:
    run_id: str
    phase: ApplicationPhase
    active_scene: str = "Coordinate Cube"
    camera_available: bool | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class RoiPresentation:
    state: str
    bounds_xywh: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class IlluminationPresentation:
    state: str
    enhancement_active: bool
    mean_v: float
    robust_range_v: float


@dataclass(frozen=True, slots=True)
class FilterPresentation:
    mode: str
    dt_s: float | None
    speed: float | None
    beta: float | None
    cutoff_hz: float | None
    compute_total_ms: float


@dataclass(frozen=True, slots=True)
class InteractionPresentation:
    available: bool
    valid: bool
    pointer_xy: tuple[float, float] | None
    pinch_active: bool | None
    pinch_ratio: float | None
    rotation_delta: tuple[float, float] | None
    scale_delta: float | None


@dataclass(frozen=True, slots=True)
class PresentationState:
    run_id: str
    frame_id: int
    timestamp_s: float
    tracking_status: str
    roi: RoiPresentation | None
    illumination: IlluminationPresentation | None
    filter: FilterPresentation
    interaction: InteractionPresentation


def build_presentation_state(
    packet: FramePacket,
    tracking_frame: TrackingFrame,
    interaction_state: CoreInteractionState | None,
) -> PresentationState:
    """Map one public realtime callback into display-safe immutable values."""

    if (
        packet.run_id != tracking_frame.run_id
        or packet.frame_id != tracking_frame.frame_id
        or packet.timestamp_s != tracking_frame.timestamp_s
    ):
        raise ValueError(
            "presentation frame and TrackingFrame identities must match"
        )

    if packet.color_space is not ColorSpace.BGR:
        raise ValueError(
            "dashboard presentation requires a BGR frame"
        )

    if interaction_state is not None and (
        interaction_state.run_id != packet.run_id
        or interaction_state.frame_id != packet.frame_id
        or interaction_state.timestamp_s != packet.timestamp_s
    ):
        raise ValueError(
            "presentation InteractionState identity must match the frame"
        )

    roi = tracking_frame.roi
    roi_presentation = (
        None
        if roi is None
        else RoiPresentation(
            state=roi.state.value,
            bounds_xywh=(
                roi.x,
                roi.y,
                roi.width,
                roi.height,
            ),
        )
    )

    illumination = tracking_frame.illumination
    illumination_presentation = (
        None
        if illumination is None
        else IlluminationPresentation(
            state=illumination.state.value,
            enhancement_active=(
                illumination.enhancement_active
            ),
            mean_v=illumination.mean_v,
            robust_range_v=illumination.robust_range_v,
        )
    )

    diagnostics = tracking_frame.filter_diagnostics
    filter_presentation = FilterPresentation(
        mode=diagnostics.mode.value,
        dt_s=diagnostics.dt_s,
        speed=diagnostics.speed,
        beta=diagnostics.beta,
        cutoff_hz=diagnostics.final_cutoff_hz,
        compute_total_ms=(
            tracking_frame.timings.compute_total_ms
        ),
    )

    interaction_presentation = (
        InteractionPresentation(
            available=False,
            valid=False,
            pointer_xy=None,
            pinch_active=None,
            pinch_ratio=None,
            rotation_delta=None,
            scale_delta=None,
        )
        if interaction_state is None
        else InteractionPresentation(
            available=True,
            valid=interaction_state.interaction_valid,
            pointer_xy=interaction_state.pointer_xy,
            pinch_active=interaction_state.pinch_active,
            pinch_ratio=interaction_state.pinch_ratio,
            rotation_delta=interaction_state.rotation_delta,
            scale_delta=interaction_state.scale_delta,
        )
    )

    return PresentationState(
        run_id=packet.run_id,
        frame_id=packet.frame_id,
        timestamp_s=packet.timestamp_s,
        tracking_status=tracking_frame.status.value,
        roi=roi_presentation,
        illumination=illumination_presentation,
        filter=filter_presentation,
        interaction=interaction_presentation,
    )

"""Immutable presentation values adapted from public runtime contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
import math
from typing import Any

from dip_touchless.core import (
    ColorSpace,
    FramePacket,
    InteractionState as CoreInteractionState,
    Landmark,
    TrackingFrame,
)


class ApplicationPhase(str, Enum):
    READY = "READY"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


class DashboardMode(str, Enum):
    DEMO = "DEMO"
    ANALYSIS = "ANALYSIS"
    EVIDENCE = "EVIDENCE"


@dataclass(frozen=True, slots=True)
class RuntimeIdentityPresentation:
    spec_version: str | None
    code_revision: str | None
    log_schema_version: str | None
    config_sha256: str | None
    python_version: str | None
    dependency_versions: tuple[tuple[str, str | None], ...]
    provider_name: str | None
    model_filename: str | None
    model_sha256: str | None
    camera_backend: str | None
    camera_requested: str | None


@dataclass(frozen=True, slots=True)
class ApplicationState:
    run_id: str
    phase: ApplicationPhase
    active_scene: str = "Coordinate Geometry"
    camera_available: bool | None = None
    error_message: str | None = None
    runtime_identity: RuntimeIdentityPresentation | None = None


@dataclass(frozen=True, slots=True)
class LandmarkPresentation:
    index: int
    x: float
    y: float
    coordinate_space: str


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
    raw_landmarks: tuple[LandmarkPresentation, ...]
    filtered_landmarks: tuple[LandmarkPresentation, ...]
    roi: RoiPresentation | None
    illumination: IlluminationPresentation | None
    filter: FilterPresentation
    interaction: InteractionPresentation


def build_runtime_identity(
    metadata: Mapping[str, Any],
) -> RuntimeIdentityPresentation:
    """Copy recorded runtime identity fields into immutable UI values."""

    provider = metadata.get("provider")
    if not isinstance(provider, Mapping):
        provider = {}
    camera = metadata.get("camera")
    if not isinstance(camera, Mapping):
        camera = {}
    requested = camera.get("requested")
    if not isinstance(requested, Mapping):
        requested = {}
    versions = metadata.get("dependency_versions")
    if not isinstance(versions, Mapping):
        versions = {}

    width = _optional_text(requested.get("width"))
    height = _optional_text(requested.get("height"))
    fps = _optional_text(requested.get("fps"))
    camera_parts = []
    if width is not None or height is not None:
        camera_parts.append(
            f"{width or 'n/a'}x{height or 'n/a'}"
        )
    if fps is not None:
        camera_parts.append(f"{fps} fps")
    camera_requested = (
        "requested " + " @ ".join(camera_parts)
        if camera_parts
        else None
    )

    dependency_names = (
        "PyYAML",
        "numpy",
        "opencv-contrib-python",
        "mediapipe",
        "matplotlib",
    )

    return RuntimeIdentityPresentation(
        spec_version=_optional_text(
            metadata.get("spec_version")
        ),
        code_revision=_optional_text(
            metadata.get("code_revision")
        ),
        log_schema_version=_optional_text(
            metadata.get("log_schema_version")
        ),
        config_sha256=_optional_text(
            metadata.get("config_hash")
        ),
        python_version=_optional_text(
            metadata.get("python_version")
        ),
        dependency_versions=tuple(
            (
                name,
                _optional_text(versions.get(name)),
            )
            for name in dependency_names
        ),
        provider_name=_optional_text(
            provider.get("name")
        ),
        model_filename=_optional_text(
            provider.get("model_filename")
        ),
        model_sha256=_optional_text(
            provider.get("model_checksum")
        ),
        camera_backend=_optional_text(
            camera.get("backend")
        ),
        camera_requested=camera_requested,
    )


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

    def landmark_values(
        landmarks: tuple[Landmark, ...],
    ) -> tuple[LandmarkPresentation, ...]:
        return tuple(
            LandmarkPresentation(
                index=landmark.index,
                x=landmark.x,
                y=landmark.y,
                coordinate_space=(
                    landmark.coordinate_space.value
                ),
            )
            for landmark in landmarks
        )

    return PresentationState(
        run_id=packet.run_id,
        frame_id=packet.frame_id,
        timestamp_s=packet.timestamp_s,
        tracking_status=tracking_frame.status.value,
        raw_landmarks=landmark_values(
            tracking_frame.raw_landmarks
        ),
        filtered_landmarks=landmark_values(
            tracking_frame.filtered_landmarks
        ),
        roi=roi_presentation,
        illumination=illumination_presentation,
        filter=filter_presentation,
        interaction=interaction_presentation,
    )


def _optional_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value if value else None
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
    ):
        return None
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return f"{value:g}"
    return str(value)

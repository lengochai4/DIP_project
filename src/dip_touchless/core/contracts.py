"""Project-owned public data contracts.

External provider objects must be converted into these contracts before
entering downstream Core modules.
"""

from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass

from .enums import (
    ColorSpace,
    CoordinateSpace,
    FilterMode,
    IlluminationState,
    QualitySource,
    ROIState,
    TrackingStatus,
)


@dataclass(frozen=True)
class FramePacket:
    run_id: str
    frame_id: int
    timestamp_s: float
    image: np.ndarray
    color_space: ColorSpace
    source_name: str

    def __post_init__(self) -> None:
        if self.frame_id < 0:
            raise ValueError("frame_id must be non-negative")
        if not math.isfinite(self.timestamp_s):
            raise ValueError("timestamp_s must be finite")
        if not self.run_id:
            raise ValueError("run_id must not be empty")
        if not self.source_name:
            raise ValueError("source_name must not be empty")
        if not isinstance(self.image, np.ndarray):
            raise TypeError("image must be a numpy.ndarray")
        if self.image.size == 0:
            raise ValueError("image must not be empty")
        if not isinstance(self.color_space, ColorSpace):
            raise TypeError("color_space must be a ColorSpace")


@dataclass(frozen=True)
class ROI:
    x: int
    y: int
    width: int
    height: int
    state: ROIState

    def __post_init__(self) -> None:
        if self.x < 0 or self.y < 0:
            raise ValueError("ROI x and y must be non-negative")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("ROI width and height must be positive")


@dataclass(frozen=True)
class IlluminationMetrics:
    mean_v: float
    std_v: float
    p10_v: float
    p90_v: float
    robust_range_v: float
    state: IlluminationState
    enhancement_active: bool


@dataclass(frozen=True)
class Landmark:
    index: int
    x: float
    y: float
    z: float
    coordinate_space: CoordinateSpace

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("landmark index must be non-negative")

        if not all(math.isfinite(value) for value in (self.x, self.y, self.z)):
            raise ValueError("landmark coordinates must be finite")


@dataclass(frozen=True)
class MeasurementQuality:
    value: float | None
    source: QualitySource
    valid: bool
    semantic_name: str | None

    def __post_init__(self) -> None:
        if self.valid:
            if self.value is None:
                raise ValueError("valid quality requires a value")
            if not math.isfinite(self.value):
                raise ValueError("quality value must be finite")
            if not 0.0 <= self.value <= 1.0:
                raise ValueError("quality value must be in [0, 1]")
            if self.source is QualitySource.NONE:
                raise ValueError("valid quality requires a real quality source")
            if not self.semantic_name:
                raise ValueError(
                    "valid quality requires semantic_name describing the quantity"
                )

    @classmethod
    def unavailable(cls) -> MeasurementQuality:
        return cls(
            value=None,
            source=QualitySource.NONE,
            valid=False,
            semantic_name=None,
        )


@dataclass(frozen=True)
class LandmarkObservation:
    frame_id: int
    timestamp_s: float
    status: TrackingStatus
    landmarks: tuple[Landmark, ...]
    handedness_label: str | None
    handedness_score: float | None
    quality: MeasurementQuality
    hand_bbox: ROI | None
    provider_name: str


@dataclass(frozen=True)
class FilterDiagnostics:
    mode: FilterMode
    dt_s: float | None
    speed: float | None
    beta: float | None
    min_cutoff_hz: float | None
    final_cutoff_hz: float | None
    signal_alpha: float | None
    derivative_alpha: float | None
    reset_occurred: bool


@dataclass(frozen=True)
class StageTimings:
    preprocess_ms: float
    tracking_ms: float
    filtering_ms: float
    gesture_ms: float
    compute_total_ms: float


@dataclass(frozen=True)
class TrackingFrame:
    run_id: str
    frame_id: int
    timestamp_s: float
    status: TrackingStatus
    raw_landmarks: tuple[Landmark, ...]
    filtered_landmarks: tuple[Landmark, ...]
    quality: MeasurementQuality
    roi: ROI | None
    illumination: IlluminationMetrics | None
    filter_diagnostics: FilterDiagnostics
    timings: StageTimings
    events: tuple[str, ...]


@dataclass(frozen=True)
class InteractionState:
    run_id: str
    frame_id: int
    timestamp_s: float
    interaction_valid: bool
    pointer_xy: tuple[float, float] | None
    pinch_ratio: float | None
    pinch_active: bool
    rotation_delta: tuple[float, float]
    scale_delta: float
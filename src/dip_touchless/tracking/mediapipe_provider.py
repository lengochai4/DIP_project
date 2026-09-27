"""MediaPipe Hand Landmarker adapter."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp
import numpy as np

from dip_touchless.core import (
    ColorSpace,
    CoordinateSpace,
    FramePacket,
    Landmark,
    LandmarkObservation,
    MeasurementQuality,
    TrackingStatus,
)


PROVIDER_NAME = "mediapipe_hand_landmarker"


class MediaPipeHandLandmarkerProvider:
    """Adapt MediaPipe Hand Landmarker output to project contracts."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        *,
        num_hands: int = 1,
        min_hand_detection_confidence: float = 0.5,
        min_hand_presence_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        landmarker: Any | None = None,
    ) -> None:
        if num_hands != 1:
            raise ValueError(
                "current baseline supports exactly one hand"
            )

        for name, value in (
            (
                "min_hand_detection_confidence",
                min_hand_detection_confidence,
            ),
            (
                "min_hand_presence_confidence",
                min_hand_presence_confidence,
            ),
            (
                "min_tracking_confidence",
                min_tracking_confidence,
            ),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be in [0, 1]"
                )

        if landmarker is not None:
            self._landmarker = landmarker
        else:
            if model_path is None:
                raise ValueError(
                    "model_path is required when no "
                    "landmarker is injected"
                )

            path = Path(model_path)

            if not path.is_file():
                raise FileNotFoundError(
                    f"MediaPipe model not found: {path}"
                )

            base_options = mp.tasks.BaseOptions(
                model_asset_path=str(path)
            )

            options = (
                mp.tasks.vision.HandLandmarkerOptions(
                    base_options=base_options,
                    running_mode=(
                        mp.tasks.vision.RunningMode.VIDEO
                    ),
                    num_hands=num_hands,
                    min_hand_detection_confidence=(
                        min_hand_detection_confidence
                    ),
                    min_hand_presence_confidence=(
                        min_hand_presence_confidence
                    ),
                    min_tracking_confidence=(
                        min_tracking_confidence
                    ),
                )
            )

            self._landmarker = (
                mp.tasks.vision.HandLandmarker
                .create_from_options(options)
            )

        self._last_timestamp_ms: int | None = None
        self._closed = False

    def process(
        self,
        frame: FramePacket,
    ) -> LandmarkObservation:
        if self._closed:
            raise RuntimeError(
                "MediaPipe provider is already closed"
            )

        self._validate_frame(frame)

        timestamp_ms = self._timestamp_ms(
            frame.timestamp_s
        )

        rgb = cv2.cvtColor(
            frame.image,
            cv2.COLOR_BGR2RGB,
        )

        rgb = np.ascontiguousarray(rgb)

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb,
        )

        result = self._landmarker.detect_for_video(
            mp_image,
            timestamp_ms,
        )

        self._last_timestamp_ms = timestamp_ms

        if not result.hand_landmarks:
            return LandmarkObservation(
                frame_id=frame.frame_id,
                timestamp_s=frame.timestamp_s,
                status=TrackingStatus.NO_HAND,
                landmarks=(),
                handedness_label=None,
                handedness_score=None,
                quality=MeasurementQuality.unavailable(),
                hand_bbox=None,
                provider_name=PROVIDER_NAME,
            )

        provider_landmarks = result.hand_landmarks[0]

        if len(provider_landmarks) != 21:
            return LandmarkObservation(
                frame_id=frame.frame_id,
                timestamp_s=frame.timestamp_s,
                status=TrackingStatus.INVALID,
                landmarks=(),
                handedness_label=None,
                handedness_score=None,
                quality=MeasurementQuality.unavailable(),
                hand_bbox=None,
                provider_name=PROVIDER_NAME,
            )

        landmarks: list[Landmark] = []

        for index, provider_landmark in enumerate(
            provider_landmarks
        ):
            values = (
                provider_landmark.x,
                provider_landmark.y,
                provider_landmark.z,
            )

            if any(
                value is None
                or not math.isfinite(float(value))
                for value in values
            ):
                return LandmarkObservation(
                    frame_id=frame.frame_id,
                    timestamp_s=frame.timestamp_s,
                    status=TrackingStatus.INVALID,
                    landmarks=(),
                    handedness_label=None,
                    handedness_score=None,
                    quality=MeasurementQuality.unavailable(),
                    hand_bbox=None,
                    provider_name=PROVIDER_NAME,
                )

            landmarks.append(
                Landmark(
                    index=index,
                    x=float(provider_landmark.x),
                    y=float(provider_landmark.y),
                    z=float(provider_landmark.z),
                    coordinate_space=(
                        CoordinateSpace.FRAME_NORMALIZED
                    ),
                )
            )

        handedness_label: str | None = None
        handedness_score: float | None = None

        if (
            result.handedness
            and result.handedness[0]
        ):
            category = result.handedness[0][0]

            handedness_label = (
                category.category_name
                or category.display_name
            )

            if category.score is not None:
                handedness_score = float(
                    category.score
                )

        return LandmarkObservation(
            frame_id=frame.frame_id,
            timestamp_s=frame.timestamp_s,
            status=TrackingStatus.VALID,
            landmarks=tuple(landmarks),
            handedness_label=handedness_label,
            handedness_score=handedness_score,
            quality=MeasurementQuality.unavailable(),
            hand_bbox=None,
            provider_name=PROVIDER_NAME,
        )

    def _validate_frame(
        self,
        frame: FramePacket,
    ) -> None:
        if frame.color_space is not ColorSpace.BGR:
            raise ValueError(
                "MediaPipe adapter requires BGR FramePacket input"
            )

        image = frame.image

        if (
            image.dtype != np.uint8
            or image.ndim != 3
            or image.shape[2] != 3
        ):
            raise ValueError(
                "MediaPipe adapter requires HxWx3 uint8 BGR input"
            )

    def _timestamp_ms(
        self,
        timestamp_s: float,
    ) -> int:
        if timestamp_s < 0:
            raise ValueError(
                "MediaPipe timestamp must be non-negative"
            )

        timestamp_ms = int(
            round(timestamp_s * 1000.0)
        )

        if (
            self._last_timestamp_ms is not None
            and timestamp_ms
            <= self._last_timestamp_ms
        ):
            raise ValueError(
                "MediaPipe VIDEO timestamp must increase "
                "after millisecond conversion"
            )

        return timestamp_ms

    def close(self) -> None:
        if self._closed:
            return

        self._landmarker.close()
        self._closed = True
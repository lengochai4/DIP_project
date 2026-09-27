"""Adaptive HSV V-channel CLAHE preprocessing."""

from __future__ import annotations

from dataclasses import dataclass, replace

import cv2
import numpy as np

from dip_touchless.core import (
    ColorSpace,
    FramePacket,
    IlluminationMetrics,
    IlluminationState,
    ROI,
)


@dataclass(frozen=True)
class ROIPreprocessResult:
    """Result of preprocessing one BGR ROI."""

    image_bgr: np.ndarray
    illumination: IlluminationMetrics


@dataclass(frozen=True)
class FramePreprocessResult:
    """Result of preprocessing and compositing one full frame."""

    frame: FramePacket
    illumination: IlluminationMetrics


class AdaptivePreprocessor:
    """Apply bypass or HSV V-channel CLAHE to one BGR ROI."""

    VALID_POLICIES = {
        "adaptive",
        "always",
        "bypass",
    }

    def __init__(
        self,
        *,
        policy: str,
        clip_limit: float,
        tile_grid_size: tuple[int, int],
    ) -> None:
        if policy not in self.VALID_POLICIES:
            raise ValueError(
                "policy must be 'adaptive', 'always', or 'bypass'"
            )

        if clip_limit <= 0:
            raise ValueError(
                "clip_limit must be positive"
            )

        if (
            len(tile_grid_size) != 2
            or any(
                not isinstance(value, int)
                or isinstance(value, bool)
                or value <= 0
                for value in tile_grid_size
            )
        ):
            raise ValueError(
                "tile_grid_size must contain two positive integers"
            )

        self._policy = policy
        self._clip_limit = float(
            clip_limit
        )
        self._tile_grid_size = (
            int(tile_grid_size[0]),
            int(tile_grid_size[1]),
        )

        self._clahe = cv2.createCLAHE(
            clipLimit=self._clip_limit,
            tileGridSize=self._tile_grid_size,
        )

    def process_frame(
        self,
        frame: FramePacket,
        roi: ROI,
        illumination: IlluminationMetrics,
    ) -> FramePreprocessResult:
        """Preprocess selected ROI and composite it into a full-size frame."""

        if frame.color_space is not ColorSpace.BGR:
            raise ValueError(
                "adaptive preprocessing requires BGR FramePacket input"
            )

        frame_height, frame_width = frame.image.shape[:2]

        self._validate_frame_roi(
            roi,
            frame_width=frame_width,
            frame_height=frame_height,
        )

        roi_bgr = frame.image[
            roi.y : roi.y + roi.height,
            roi.x : roi.x + roi.width,
        ]

        roi_result = self.process_roi(
            roi_bgr,
            illumination,
        )

        output_image = frame.image.copy()

        output_image[
            roi.y : roi.y + roi.height,
            roi.x : roi.x + roi.width,
        ] = roi_result.image_bgr

        output_frame = replace(
            frame,
            image=output_image,
        )

        return FramePreprocessResult(
            frame=output_frame,
            illumination=roi_result.illumination,
        )
    
    def process_roi(
        self,
        roi_bgr: np.ndarray,
        illumination: IlluminationMetrics,
    ) -> ROIPreprocessResult:
        """Apply configured preprocessing to one BGR uint8 ROI."""

        self._validate_roi_image(
            roi_bgr
        )

        apply_enhancement = (
            self._should_apply(
                illumination.state
            )
        )

        if not apply_enhancement:
            return ROIPreprocessResult(
                image_bgr=roi_bgr.copy(),
                illumination=replace(
                    illumination,
                    enhancement_active=False,
                ),
            )

        hsv = cv2.cvtColor(
            roi_bgr,
            cv2.COLOR_BGR2HSV,
        )

        enhanced_v = self._clahe.apply(
            hsv[:, :, 2]
        )

        enhanced_hsv = hsv.copy()
        enhanced_hsv[:, :, 2] = enhanced_v

        enhanced_bgr = cv2.cvtColor(
            enhanced_hsv,
            cv2.COLOR_HSV2BGR,
        )

        return ROIPreprocessResult(
            image_bgr=enhanced_bgr,
            illumination=replace(
                illumination,
                enhancement_active=True,
            ),
        )

    def _should_apply(
        self,
        state: IlluminationState,
    ) -> bool:
        if self._policy == "bypass":
            return False

        if self._policy == "always":
            return True

        return (
            state is not IlluminationState.NORMAL
        )

    @staticmethod
    def _validate_frame_roi(
        roi: ROI,
        *,
        frame_width: int,
        frame_height: int,
    ) -> None:
        if roi.x < 0 or roi.y < 0:
            raise ValueError(
                "ROI origin must be inside the frame"
            )

        if roi.width <= 0 or roi.height <= 0:
            raise ValueError(
                "ROI dimensions must be positive"
            )

        if (
            roi.x + roi.width > frame_width
            or roi.y + roi.height > frame_height
        ):
            raise ValueError(
                "ROI must be contained within frame bounds"
            )
    
    @staticmethod
    def _validate_roi_image(
        roi_bgr: np.ndarray,
    ) -> None:
        if not isinstance(
            roi_bgr,
            np.ndarray,
        ):
            raise TypeError(
                "ROI image must be a numpy.ndarray"
            )

        if roi_bgr.dtype != np.uint8:
            raise ValueError(
                "ROI image must have dtype uint8"
            )

        if (
            roi_bgr.ndim != 3
            or roi_bgr.shape[2] != 3
        ):
            raise ValueError(
                "ROI image must be HxWx3 BGR"
            )

        if roi_bgr.size == 0:
            raise ValueError(
                "ROI image must not be empty"
            )
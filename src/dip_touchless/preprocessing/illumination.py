"""HSV V-channel illumination descriptor extraction."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from dip_touchless.core import (
    ColorSpace,
    FramePacket,
    ROI,
)


@dataclass(frozen=True)
class IlluminationDescriptors:
    """Raw illumination descriptors measured from the HSV V channel."""

    mean_v: float
    std_v: float
    p10_v: float
    p90_v: float
    robust_range_v: float


class IlluminationAnalyzer:
    """Measure illumination descriptors from a selected BGR ROI."""

    def measure(
        self,
        frame: FramePacket,
        roi: ROI,
    ) -> IlluminationDescriptors:
        """Measure HSV V-channel statistics for one full-frame ROI."""

        self._validate_frame(frame)
        self._validate_roi(
            roi,
            frame_width=frame.image.shape[1],
            frame_height=frame.image.shape[0],
        )

        roi_bgr = frame.image[
            roi.y : roi.y + roi.height,
            roi.x : roi.x + roi.width,
        ]

        if roi_bgr.size == 0:
            raise ValueError(
                "ROI produced an empty image region"
            )

        roi_hsv = cv2.cvtColor(
            roi_bgr,
            cv2.COLOR_BGR2HSV,
        )

        value_channel = roi_hsv[:, :, 2].astype(
            np.float64,
            copy=False,
        )

        mean_v = float(
            np.mean(value_channel)
        )

        std_v = float(
            np.std(
                value_channel,
                ddof=0,
            )
        )

        p10_v = float(
            np.percentile(
                value_channel,
                10,
                method="linear",
            )
        )

        p90_v = float(
            np.percentile(
                value_channel,
                90,
                method="linear",
            )
        )

        robust_range_v = (
            p90_v - p10_v
        )

        return IlluminationDescriptors(
            mean_v=mean_v,
            std_v=std_v,
            p10_v=p10_v,
            p90_v=p90_v,
            robust_range_v=robust_range_v,
        )

    @staticmethod
    def _validate_frame(
        frame: FramePacket,
    ) -> None:
        if frame.color_space is not ColorSpace.BGR:
            raise ValueError(
                "illumination analysis requires BGR input"
            )

        image = frame.image

        if image.dtype != np.uint8:
            raise ValueError(
                "illumination analysis requires uint8 input"
            )

        if (
            image.ndim != 3
            or image.shape[2] != 3
        ):
            raise ValueError(
                "illumination analysis requires HxWx3 BGR input"
            )

    @staticmethod
    def _validate_roi(
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
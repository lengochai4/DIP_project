"""ROI state and geometry management."""

from __future__ import annotations

import math

from dip_touchless.core import ROI, ROIState


class ROIManager:
    """Manage SEARCHING/TRACKING/COASTING ROI geometry.

    The manager does not inspect or modify image pixels and does not call
    the landmark provider.

    A supplied hand_bbox represents the most recent usable hand geometry.
    A missing bbox represents temporary tracking loss.
    """

    def __init__(
        self,
        *,
        padding_ratio: float,
        coast_expand_ratio: float,
        coast_frames: int,
        min_width: int,
        min_height: int,
    ) -> None:
        if padding_ratio < 0:
            raise ValueError(
                "padding_ratio must be non-negative"
            )

        if coast_expand_ratio < 0:
            raise ValueError(
                "coast_expand_ratio must be non-negative"
            )

        if (
            not isinstance(coast_frames, int)
            or isinstance(coast_frames, bool)
            or coast_frames < 0
        ):
            raise ValueError(
                "coast_frames must be a non-negative integer"
            )

        if (
            not isinstance(min_width, int)
            or isinstance(min_width, bool)
            or min_width <= 0
        ):
            raise ValueError(
                "min_width must be a positive integer"
            )

        if (
            not isinstance(min_height, int)
            or isinstance(min_height, bool)
            or min_height <= 0
        ):
            raise ValueError(
                "min_height must be a positive integer"
            )

        self._padding_ratio = float(
            padding_ratio
        )
        self._coast_expand_ratio = float(
            coast_expand_ratio
        )
        self._coast_frames = coast_frames
        self._min_width = min_width
        self._min_height = min_height

        self._state = ROIState.SEARCHING
        self._last_tracking_roi: ROI | None = None
        self._coast_count = 0

    @property
    def state(self) -> ROIState:
        return self._state

    @property
    def coast_count(self) -> int:
        return self._coast_count

    def reset(self) -> None:
        """Reset ROI tracking state."""
        self._state = ROIState.SEARCHING
        self._last_tracking_roi = None
        self._coast_count = 0

    def update(
        self,
        *,
        frame_width: int,
        frame_height: int,
        hand_bbox: ROI | None,
    ) -> ROI:
        """Produce the ROI to use from the latest known hand geometry."""

        self._validate_frame_dimensions(
            frame_width,
            frame_height,
        )

        full_frame = ROI(
            x=0,
            y=0,
            width=frame_width,
            height=frame_height,
            state=ROIState.SEARCHING,
        )

        if hand_bbox is not None:
            clipped_bbox = self._clip_bbox(
                hand_bbox,
                frame_width=frame_width,
                frame_height=frame_height,
            )

            if clipped_bbox is None:
                self.reset()
                return full_frame

            tracking_roi = self._expand_and_fit(
                clipped_bbox,
                ratio=self._padding_ratio,
                frame_width=frame_width,
                frame_height=frame_height,
                state=ROIState.TRACKING,
            )

            self._state = ROIState.TRACKING
            self._last_tracking_roi = tracking_roi
            self._coast_count = 0

            return tracking_roi

        if (
            self._last_tracking_roi is not None
            and self._state
            in {
                ROIState.TRACKING,
                ROIState.COASTING,
            }
            and self._coast_count
            < self._coast_frames
        ):
            self._coast_count += 1

            coast_roi = self._expand_and_fit(
                self._last_tracking_roi,
                ratio=self._coast_expand_ratio,
                frame_width=frame_width,
                frame_height=frame_height,
                state=ROIState.COASTING,
            )

            self._state = ROIState.COASTING

            return coast_roi

        self.reset()

        return full_frame

    def _validate_frame_dimensions(
        self,
        frame_width: int,
        frame_height: int,
    ) -> None:
        if (
            not isinstance(frame_width, int)
            or isinstance(frame_width, bool)
            or frame_width <= 0
        ):
            raise ValueError(
                "frame_width must be a positive integer"
            )

        if (
            not isinstance(frame_height, int)
            or isinstance(frame_height, bool)
            or frame_height <= 0
        ):
            raise ValueError(
                "frame_height must be a positive integer"
            )

        if self._min_width > frame_width:
            raise ValueError(
                "min_width exceeds frame_width"
            )

        if self._min_height > frame_height:
            raise ValueError(
                "min_height exceeds frame_height"
            )

    @staticmethod
    def _clip_bbox(
        bbox: ROI,
        *,
        frame_width: int,
        frame_height: int,
    ) -> ROI | None:
        left = max(0, bbox.x)
        top = max(0, bbox.y)

        right = min(
            frame_width,
            bbox.x + bbox.width,
        )
        bottom = min(
            frame_height,
            bbox.y + bbox.height,
        )

        if right <= left or bottom <= top:
            return None

        return ROI(
            x=left,
            y=top,
            width=right - left,
            height=bottom - top,
            state=ROIState.TRACKING,
        )

    def _expand_and_fit(
        self,
        roi: ROI,
        *,
        ratio: float,
        frame_width: int,
        frame_height: int,
        state: ROIState,
    ) -> ROI:
        horizontal_padding = (
            roi.width * ratio
        )
        vertical_padding = (
            roi.height * ratio
        )

        left = (
            roi.x - horizontal_padding
        )
        top = (
            roi.y - vertical_padding
        )
        right = (
            roi.x
            + roi.width
            + horizontal_padding
        )
        bottom = (
            roi.y
            + roi.height
            + vertical_padding
        )

        natural_left = math.floor(left)
        natural_top = math.floor(top)
        natural_right = math.ceil(right)
        natural_bottom = math.ceil(bottom)

        natural_width = (
            natural_right - natural_left
        )
        natural_height = (
            natural_bottom - natural_top
        )

        target_width = min(
            frame_width,
            max(
                natural_width,
                self._min_width,
            ),
        )

        target_height = min(
            frame_height,
            max(
                natural_height,
                self._min_height,
            ),
        )

        center_x = (
            left + right
        ) / 2.0

        center_y = (
            top + bottom
        ) / 2.0

        target_x = math.floor(
            center_x
            - target_width / 2.0
        )

        target_y = math.floor(
            center_y
            - target_height / 2.0
        )

        target_x = min(
            max(0, target_x),
            frame_width - target_width,
        )

        target_y = min(
            max(0, target_y),
            frame_height - target_height,
        )

        return ROI(
            x=target_x,
            y=target_y,
            width=target_width,
            height=target_height,
            state=state,
        )
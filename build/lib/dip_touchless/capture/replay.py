"""Deterministic video replay frame source."""

from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

from dip_touchless.core import ColorSpace, FramePacket


class ReplayFrameSource:
    """Read a recorded video as deterministic BGR FramePacket objects.

    Replay timestamps are derived from source frame index and source FPS:

        timestamp_s = frame_id / source_fps

    This intentionally avoids wall-clock timing so repeated runs over the
    same source produce the same frame/timestamp sequence.
    """

    def __init__(
        self,
        source_path: str | Path,
        *,
        run_id: str,
    ) -> None:
        if not run_id:
            raise ValueError("run_id must not be empty")

        self._source_path = Path(source_path)
        self._run_id = run_id

        self._capture: cv2.VideoCapture | None = None
        self._source_fps: float | None = None
        self._frame_id = 0

    @property
    def source_path(self) -> Path:
        return self._source_path

    @property
    def source_fps(self) -> float | None:
        return self._source_fps

    def open(self) -> None:
        if self._capture is not None:
            raise RuntimeError(
                "replay source is already open"
            )

        if not self._source_path.is_file():
            raise FileNotFoundError(
                f"replay source not found: {self._source_path}"
            )

        capture = cv2.VideoCapture(
            str(self._source_path)
        )

        if not capture.isOpened():
            capture.release()

            raise RuntimeError(
                "failed to open replay source: "
                f"{self._source_path}"
            )

        source_fps = float(
            capture.get(cv2.CAP_PROP_FPS)
        )

        if (
            not math.isfinite(source_fps)
            or source_fps <= 0.0
        ):
            capture.release()

            raise RuntimeError(
                "replay source has invalid FPS: "
                f"{source_fps!r}"
            )

        self._capture = capture
        self._source_fps = source_fps
        self._frame_id = 0

    def read(self) -> FramePacket | None:
        if (
            self._capture is None
            or self._source_fps is None
        ):
            raise RuntimeError(
                "replay source is not open"
            )

        success, frame = self._capture.read()

        if not success:
            return None

        self._validate_decoded_frame(frame)

        frame_id = self._frame_id
        timestamp_s = frame_id / self._source_fps

        packet = FramePacket(
            run_id=self._run_id,
            frame_id=frame_id,
            timestamp_s=timestamp_s,
            image=frame,
            color_space=ColorSpace.BGR,
            source_name=f"replay:{self._source_path.name}",
        )

        self._frame_id += 1

        return packet

    @staticmethod
    def _validate_decoded_frame(
        frame: object,
    ) -> None:
        if not isinstance(frame, np.ndarray):
            raise RuntimeError(
                "decoded replay frame is not a numpy array"
            )

        if frame.size == 0:
            raise RuntimeError(
                "decoded replay frame is empty"
            )

        if frame.dtype != np.uint8:
            raise RuntimeError(
                "decoded replay frame must have dtype uint8"
            )

        if (
            frame.ndim != 3
            or frame.shape[2] != 3
        ):
            raise RuntimeError(
                "decoded replay frame must be HxWx3 BGR"
            )

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()

        self._capture = None
        self._source_fps = None
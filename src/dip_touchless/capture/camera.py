"""OpenCV live-camera frame source."""

from __future__ import annotations

import math
import time
from collections.abc import Callable

import cv2
import numpy as np

from dip_touchless.core import ColorSpace, FramePacket


_BACKENDS: dict[str, int | None] = {
    "default": None,
    "dshow": cv2.CAP_DSHOW,
    "msmf": cv2.CAP_MSMF,
    "v4l2": cv2.CAP_V4L2,
    "avfoundation": cv2.CAP_AVFOUNDATION,
}


class OpenCVCameraSource:
    """Live camera source producing unprocessed BGR FramePacket objects."""

    def __init__(
        self,
        *,
        run_id: str,
        camera_index: int = 0,
        width: int = 640,
        height: int = 480,
        requested_fps: float = 30.0,
        backend: str = "default",
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        if not run_id:
            raise ValueError("run_id must not be empty")

        if camera_index < 0:
            raise ValueError("camera_index must be non-negative")

        if width <= 0 or height <= 0:
            raise ValueError("camera dimensions must be positive")

        if requested_fps <= 0:
            raise ValueError("requested_fps must be positive")

        backend_key = backend.lower()

        if backend_key not in _BACKENDS:
            raise ValueError(
                f"unsupported camera backend: {backend}"
            )

        self._run_id = run_id
        self._camera_index = camera_index
        self._width = width
        self._height = height
        self._requested_fps = float(requested_fps)
        self._backend_name = backend_key
        self._clock = clock

        self._capture: cv2.VideoCapture | None = None
        self._start_time: float | None = None
        self._last_timestamp_s: float | None = None
        self._frame_id = 0

    @property
    def backend_name(self) -> str:
        return self._backend_name

    @property
    def observed_width(self) -> int | None:
        if self._capture is None:
            return None

        return int(
            self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        )

    @property
    def observed_height(self) -> int | None:
        if self._capture is None:
            return None

        return int(
            self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        )

    @property
    def observed_fps(self) -> float | None:
        if self._capture is None:
            return None

        value = float(
            self._capture.get(cv2.CAP_PROP_FPS)
        )

        if not math.isfinite(value) or value <= 0:
            return None

        return value

    def open(self) -> None:
        if self._capture is not None:
            raise RuntimeError(
                "camera source is already open"
            )

        backend = _BACKENDS[self._backend_name]

        if backend is None:
            capture = cv2.VideoCapture(
                self._camera_index
            )
        else:
            capture = cv2.VideoCapture(
                self._camera_index,
                backend,
            )

        if not capture.isOpened():
            capture.release()

            raise RuntimeError(
                f"failed to open camera index "
                f"{self._camera_index}"
            )

        capture.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            self._width,
        )
        capture.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            self._height,
        )
        capture.set(
            cv2.CAP_PROP_FPS,
            self._requested_fps,
        )

        start_time = self._clock()

        if not math.isfinite(start_time):
            capture.release()
            raise RuntimeError(
                "camera clock returned a non-finite value"
            )

        self._capture = capture
        self._start_time = start_time
        self._last_timestamp_s = None
        self._frame_id = 0

    def read(self) -> FramePacket:
        if (
            self._capture is None
            or self._start_time is None
        ):
            raise RuntimeError(
                "camera source is not open"
            )

        success, frame = self._capture.read()

        if not success:
            raise RuntimeError(
                "failed to read frame from camera"
            )

        self._validate_frame(frame)

        now = self._clock()

        if not math.isfinite(now):
            raise RuntimeError(
                "camera clock returned a non-finite value"
            )

        timestamp_s = now - self._start_time

        if timestamp_s < 0:
            raise RuntimeError(
                "camera clock moved backwards"
            )

        if (
            self._last_timestamp_s is not None
            and timestamp_s <= self._last_timestamp_s
        ):
            raise RuntimeError(
                "camera timestamp is not increasing"
            )

        packet = FramePacket(
            run_id=self._run_id,
            frame_id=self._frame_id,
            timestamp_s=timestamp_s,
            image=frame,
            color_space=ColorSpace.BGR,
            source_name=f"camera:{self._camera_index}",
        )

        self._frame_id += 1
        self._last_timestamp_s = timestamp_s

        return packet

    @staticmethod
    def _validate_frame(
        frame: object,
    ) -> None:
        if not isinstance(frame, np.ndarray):
            raise RuntimeError(
                "camera frame is not a numpy array"
            )

        if frame.size == 0:
            raise RuntimeError(
                "camera frame is empty"
            )

        if frame.dtype != np.uint8:
            raise RuntimeError(
                "camera frame must have dtype uint8"
            )

        if frame.ndim != 3 or frame.shape[2] != 3:
            raise RuntimeError(
                "camera frame must be HxWx3 BGR"
            )

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()

        self._capture = None
        self._start_time = None
        self._last_timestamp_s = None
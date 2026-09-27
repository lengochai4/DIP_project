import cv2
import numpy as np
import pytest

from dip_touchless.capture import OpenCVCameraSource
from dip_touchless.core import ColorSpace


class FakeCameraCapture:
    def __init__(
        self,
        frames: list[np.ndarray],
    ) -> None:
        self.frames = frames
        self.index = 0
        self.released = False
        self.properties: dict[int, float] = {}

    def isOpened(self) -> bool:
        return True

    def set(
        self,
        property_id: int,
        value: float,
    ) -> bool:
        self.properties[property_id] = value
        return True

    def get(
        self,
        property_id: int,
    ) -> float:
        if property_id in self.properties:
            return self.properties[property_id]

        return 0.0

    def read(
        self,
    ) -> tuple[bool, np.ndarray | None]:
        if self.index >= len(self.frames):
            return False, None

        frame = self.frames[self.index]
        self.index += 1

        return True, frame

    def release(self) -> None:
        self.released = True


def test_camera_requires_open() -> None:
    source = OpenCVCameraSource(
        run_id="run-test"
    )

    with pytest.raises(RuntimeError):
        source.read()


def test_camera_produces_bgr_frames_with_monotonic_timestamps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frames = [
        np.zeros((2, 3, 3), dtype=np.uint8),
        np.ones((2, 3, 3), dtype=np.uint8),
    ]

    fake_capture = FakeCameraCapture(frames)

    monkeypatch.setattr(
        cv2,
        "VideoCapture",
        lambda *args: fake_capture,
    )

    times = iter([100.0, 100.1, 100.2])

    source = OpenCVCameraSource(
        run_id="run-test",
        clock=lambda: next(times),
    )

    source.open()

    first = source.read()
    second = source.read()

    source.close()

    assert first.frame_id == 0
    assert second.frame_id == 1

    assert first.timestamp_s == pytest.approx(0.1)
    assert second.timestamp_s == pytest.approx(0.2)

    assert first.color_space is ColorSpace.BGR
    assert second.color_space is ColorSpace.BGR


def test_camera_requests_configured_properties(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_capture = FakeCameraCapture([])

    monkeypatch.setattr(
        cv2,
        "VideoCapture",
        lambda *args: fake_capture,
    )

    source = OpenCVCameraSource(
        run_id="run-test",
        width=1280,
        height=720,
        requested_fps=60.0,
        clock=lambda: 1.0,
    )

    source.open()

    assert (
        fake_capture.properties[
            cv2.CAP_PROP_FRAME_WIDTH
        ]
        == 1280
    )

    assert (
        fake_capture.properties[
            cv2.CAP_PROP_FRAME_HEIGHT
        ]
        == 720
    )

    assert (
        fake_capture.properties[
            cv2.CAP_PROP_FPS
        ]
        == 60.0
    )

    source.close()


def test_camera_does_not_modify_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = np.arange(
        18,
        dtype=np.uint8,
    ).reshape(2, 3, 3)

    expected = frame.copy()

    fake_capture = FakeCameraCapture([frame])

    monkeypatch.setattr(
        cv2,
        "VideoCapture",
        lambda *args: fake_capture,
    )

    times = iter([10.0, 10.1])

    source = OpenCVCameraSource(
        run_id="run-test",
        clock=lambda: next(times),
    )

    source.open()
    packet = source.read()
    source.close()

    np.testing.assert_array_equal(
        packet.image,
        expected,
    )


def test_camera_read_failure_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_capture = FakeCameraCapture([])

    monkeypatch.setattr(
        cv2,
        "VideoCapture",
        lambda *args: fake_capture,
    )

    source = OpenCVCameraSource(
        run_id="run-test",
        clock=lambda: 1.0,
    )

    source.open()

    with pytest.raises(RuntimeError):
        source.read()

    source.close()


def test_camera_close_releases_capture(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_capture = FakeCameraCapture([])

    monkeypatch.setattr(
        cv2,
        "VideoCapture",
        lambda *args: fake_capture,
    )

    source = OpenCVCameraSource(
        run_id="run-test",
        clock=lambda: 1.0,
    )

    source.open()
    source.close()

    assert fake_capture.released is True
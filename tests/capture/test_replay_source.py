from pathlib import Path

import cv2
import numpy as np
import pytest

from dip_touchless.capture import ReplayFrameSource
from dip_touchless.core import ColorSpace


class FakeVideoCapture:
    def __init__(
        self,
        frames: list[np.ndarray],
        *,
        fps: float,
    ) -> None:
        self.frames = frames
        self.fps = fps
        self.index = 0
        self.released = False

    def isOpened(self) -> bool:
        return True

    def get(self, property_id: int) -> float:
        if property_id == cv2.CAP_PROP_FPS:
            return self.fps

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


def _video_path(
    tmp_path: Path,
) -> Path:
    path = tmp_path / "fixture.mp4"
    path.touch()

    return path


def test_replay_requires_open(
    tmp_path: Path,
) -> None:
    source = ReplayFrameSource(
        _video_path(tmp_path),
        run_id="run-test",
    )

    with pytest.raises(RuntimeError):
        source.read()


def test_replay_produces_deterministic_frame_ids_and_timestamps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frames = [
        np.full(
            (2, 3, 3),
            fill_value=index,
            dtype=np.uint8,
        )
        for index in range(3)
    ]

    fake_capture = FakeVideoCapture(
        frames,
        fps=20.0,
    )

    monkeypatch.setattr(
        cv2,
        "VideoCapture",
        lambda _: fake_capture,
    )

    source = ReplayFrameSource(
        _video_path(tmp_path),
        run_id="run-test",
    )

    source.open()

    packets = [
        source.read(),
        source.read(),
        source.read(),
    ]

    assert [
        packet.frame_id
        for packet in packets
        if packet is not None
    ] == [0, 1, 2]

    assert [
        packet.timestamp_s
        for packet in packets
        if packet is not None
    ] == pytest.approx(
        [0.0, 0.05, 0.10]
    )

    assert all(
        packet is not None
        and packet.color_space is ColorSpace.BGR
        for packet in packets
    )

    source.close()


def test_replay_does_not_modify_decoded_frame(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = np.arange(
        18,
        dtype=np.uint8,
    ).reshape(2, 3, 3)

    expected = frame.copy()

    fake_capture = FakeVideoCapture(
        [frame],
        fps=30.0,
    )

    monkeypatch.setattr(
        cv2,
        "VideoCapture",
        lambda _: fake_capture,
    )

    source = ReplayFrameSource(
        _video_path(tmp_path),
        run_id="run-test",
    )

    source.open()
    packet = source.read()
    source.close()

    assert packet is not None

    np.testing.assert_array_equal(
        packet.image,
        expected,
    )


def test_replay_returns_none_at_eof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_capture = FakeVideoCapture(
        [],
        fps=30.0,
    )

    monkeypatch.setattr(
        cv2,
        "VideoCapture",
        lambda _: fake_capture,
    )

    source = ReplayFrameSource(
        _video_path(tmp_path),
        run_id="run-test",
    )

    source.open()

    assert source.read() is None

    source.close()


def test_replay_rejects_invalid_source_fps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_capture = FakeVideoCapture(
        [],
        fps=0.0,
    )

    monkeypatch.setattr(
        cv2,
        "VideoCapture",
        lambda _: fake_capture,
    )

    source = ReplayFrameSource(
        _video_path(tmp_path),
        run_id="run-test",
    )

    with pytest.raises(RuntimeError):
        source.open()

    assert fake_capture.released is True


def test_close_releases_capture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_capture = FakeVideoCapture(
        [],
        fps=30.0,
    )

    monkeypatch.setattr(
        cv2,
        "VideoCapture",
        lambda _: fake_capture,
    )

    source = ReplayFrameSource(
        _video_path(tmp_path),
        run_id="run-test",
    )

    source.open()
    source.close()

    assert fake_capture.released is True
    assert source.source_fps is None
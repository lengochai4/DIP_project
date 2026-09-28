import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from dip_touchless.core import ColorSpace, FramePacket
from experiments.record_source import record_frame_source


class FakeSource:
    def __init__(self, packets) -> None:
        self._packets = iter(packets)
        self.opened = False
        self.closed = False
        self.backend_name = "fake"
        self.observed_width = 2
        self.observed_height = 2
        self.observed_fps = 10.0

    def open(self) -> None:
        self.opened = True

    def read(self) -> FramePacket:
        return next(self._packets)

    def close(self) -> None:
        self.closed = True


class FakeWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.released = False
        self.path.write_bytes(b"")

    def write(self, frame: np.ndarray) -> None:
        with self.path.open("ab") as file:
            file.write(frame.tobytes())

    def release(self) -> None:
        self.released = True


class FailingWriter(FakeWriter):
    def write(self, frame: np.ndarray) -> None:
        raise RuntimeError("writer failed")


def _packet(
    frame_id: int,
    timestamp_s: float,
    *,
    color_space: ColorSpace = ColorSpace.BGR,
) -> FramePacket:
    return FramePacket(
        run_id="source-test",
        frame_id=frame_id,
        timestamp_s=timestamp_s,
        image=np.full(
            (2, 2, 3),
            frame_id,
            dtype=np.uint8,
        ),
        color_space=color_space,
        source_name="camera:0",
    )


def test_record_source_writes_fixed_frames_and_metadata(
    tmp_path: Path,
) -> None:
    source = FakeSource(
        [
            _packet(0, 0.0),
            _packet(1, 0.1),
            _packet(2, 0.2),
            _packet(3, 0.3),
            _packet(4, 0.4),
        ]
    )
    writers = []

    def writer_factory(path, fps, size):
        assert fps == 10.0
        assert size == (2, 2)
        writer = FakeWriter(path)
        writers.append(writer)
        return writer

    output = tmp_path / "trial-001.avi"
    result = record_frame_source(
        source=source,
        output_path=output,
        frame_count=3,
        encoded_fps=10.0,
        settle_s=0.1,
        requested_camera={
            "index": 0,
            "width": 2,
            "height": 2,
            "fps": 10.0,
            "backend": "fake",
        },
        lighting_label="normal",
        auto_exposure_status="enabled",
        auto_white_balance_status="enabled",
        notes="fixture",
        writer_factory=writer_factory,
        code_revision="test-revision",
    )

    assert source.opened is True
    assert source.closed is True
    assert writers[0].released is True
    assert result.frame_count == 3
    assert result.video_path == output
    assert output.read_bytes() == (
        bytes([1] * 12)
        + bytes([2] * 12)
        + bytes([3] * 12)
    )

    payload = json.loads(
        result.metadata_path.read_text(
            encoding="utf-8"
        )
    )

    assert payload["video"]["frame_count"] == 3
    assert payload["video"]["encoded_fps"] == 10.0
    assert payload["video"]["encoded_width"] == 2
    assert payload["video"]["encoded_height"] == 2
    assert payload["acquisition"][
        "first_recorded_timestamp_s"
    ] == pytest.approx(0.1)
    assert payload["acquisition"][
        "last_recorded_timestamp_s"
    ] == pytest.approx(0.3)
    assert payload["lighting"]["label"] == "normal"
    assert payload["lighting"]["auto_exposure"] == "enabled"
    assert payload["lighting"]["auto_white_balance"] == "enabled"
    assert payload["processing"]["preprocessing"] == "none"
    assert payload["software"]["code_revision"] == "test-revision"

    expected_hash = hashlib.sha256(
        output.read_bytes()
    ).hexdigest()
    assert payload["video"]["sha256"] == expected_hash
    assert result.sha256 == expected_hash


def test_record_source_rejects_non_bgr_input(
    tmp_path: Path,
) -> None:
    source = FakeSource(
        [_packet(0, 0.0, color_space=ColorSpace.RGB)]
    )
    output = tmp_path / "bad.avi"

    with pytest.raises(RuntimeError, match="BGR"):
        record_frame_source(
            source=source,
            output_path=output,
            frame_count=1,
            encoded_fps=10.0,
            settle_s=0.0,
            requested_camera={},
            lighting_label="test",
            auto_exposure_status="unknown",
            auto_white_balance_status="unknown",
        )

    assert source.closed is True
    assert not output.exists()


def test_record_source_releases_and_removes_partial_output_on_failure(
    tmp_path: Path,
) -> None:
    source = FakeSource([_packet(0, 0.0)])
    writers = []

    def writer_factory(path, fps, size):
        writer = FailingWriter(path)
        writers.append(writer)
        return writer

    output = tmp_path / "failed.avi"

    with pytest.raises(RuntimeError, match="writer failed"):
        record_frame_source(
            source=source,
            output_path=output,
            frame_count=1,
            encoded_fps=10.0,
            settle_s=0.0,
            requested_camera={},
            lighting_label="test",
            auto_exposure_status="unknown",
            auto_white_balance_status="unknown",
            writer_factory=writer_factory,
        )

    assert source.closed is True
    assert writers[0].released is True
    assert not output.exists()
    assert not output.with_suffix(".json").exists()


def test_record_source_refuses_overwrite(
    tmp_path: Path,
) -> None:
    output = tmp_path / "existing.avi"
    output.write_bytes(b"existing")
    source = FakeSource([_packet(0, 0.0)])

    with pytest.raises(FileExistsError):
        record_frame_source(
            source=source,
            output_path=output,
            frame_count=1,
            encoded_fps=10.0,
            settle_s=0.0,
            requested_camera={},
            lighting_label="test",
            auto_exposure_status="unknown",
            auto_white_balance_status="unknown",
        )

    assert source.opened is False

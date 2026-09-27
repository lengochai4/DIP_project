import csv
from pathlib import Path

import cv2
import numpy as np
import pytest

from dip_touchless.capture import ReplayFrameSource
from dip_touchless.configuration import resolve_config
from dip_touchless.core import (
    CoordinateSpace,
    Landmark,
    LandmarkObservation,
    MeasurementQuality,
    TrackingStatus,
)
from dip_touchless.filtering import RawLandmarkFilter
from dip_touchless.runtime import ReplayRuntime
from dip_touchless.telemetry import (
    FileRunLogger,
    build_run_metadata,
)
from dip_touchless.tracking import MeasurementValidator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = (
    PROJECT_ROOT / "config" / "default.yaml"
)


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

    def get(
        self,
        property_id: int,
    ) -> float:
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


class FakeProvider:
    def __init__(self) -> None:
        self.closed = False

    def process(
        self,
        frame,
    ) -> LandmarkObservation:
        if frame.frame_id == 0:
            landmarks = tuple(
                Landmark(
                    index=index,
                    x=0.1 + index * 0.001,
                    y=0.2,
                    z=-0.01,
                    coordinate_space=(
                        CoordinateSpace.FRAME_NORMALIZED
                    ),
                )
                for index in range(21)
            )

            return LandmarkObservation(
                frame_id=frame.frame_id,
                timestamp_s=frame.timestamp_s,
                status=TrackingStatus.VALID,
                landmarks=landmarks,
                handedness_label="Right",
                handedness_score=0.9,
                quality=(
                    MeasurementQuality.unavailable()
                ),
                hand_bbox=None,
                provider_name="fake-provider",
            )

        return LandmarkObservation(
            frame_id=frame.frame_id,
            timestamp_s=frame.timestamp_s,
            status=TrackingStatus.NO_HAND,
            landmarks=(),
            handedness_label=None,
            handedness_score=None,
            quality=MeasurementQuality.unavailable(),
            hand_bbox=None,
            provider_name="fake-provider",
        )

    def close(self) -> None:
        self.closed = True


def test_replay_runtime_writes_raw_machine_readable_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frames = [
        np.zeros(
            (2, 3, 3),
            dtype=np.uint8,
        ),
        np.ones(
            (2, 3, 3),
            dtype=np.uint8,
        ),
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

    video_path = tmp_path / "fixture.mp4"
    video_path.touch()

    run_id = "integration-run"

    source = ReplayFrameSource(
        video_path,
        run_id=run_id,
    )

    provider = FakeProvider()

    resolved = resolve_config(
        DEFAULT_CONFIG,
        overrides={
            "runtime": {
                "mode": "replay",
                "replay_source": str(
                    video_path
                ),
            },
            "filter": {
                "mode": "RAW",
            },
        },
    )

    metadata = build_run_metadata(
        resolved,
        run_id=run_id,
        code_revision="test-revision",
    )

    logger = FileRunLogger(
        tmp_path / "runs"
    )

    runtime = ReplayRuntime(
        source=source,
        provider=provider,
        validator=MeasurementValidator(),
        landmark_filter=RawLandmarkFilter(),
        logger=logger,
    )

    processed = runtime.run(
        metadata=metadata,
        resolved_config=resolved.to_dict(),
    )

    assert processed == 2

    run_dir = (
        tmp_path
        / "runs"
        / run_id
    )

    with (
        run_dir / "frames.csv"
    ).open(
        newline="",
        encoding="utf-8",
    ) as file:
        frame_rows = list(
            csv.DictReader(file)
        )

    assert len(frame_rows) == 2

    assert [
        row["frame_id"]
        for row in frame_rows
    ] == ["0", "1"]

    assert [
        row["tracking_status"]
        for row in frame_rows
    ] == ["VALID", "NO_HAND"]

    assert all(
        row["filter_mode"] == "RAW"
        for row in frame_rows
    )

    assert all(
        row["roi_state"] == ""
        for row in frame_rows
    )

    assert all(
        row["illumination_state"] == ""
        for row in frame_rows
    )

    with (
        run_dir / "landmarks.csv"
    ).open(
        newline="",
        encoding="utf-8",
    ) as file:
        landmark_rows = list(
            csv.DictReader(file)
        )

    # Frame 0 has 21 raw + 21 Raw-filter output landmarks.
    # Frame 1 is NO_HAND and contributes none.
    assert len(landmark_rows) == 42

    assert {
        row["stage"]
        for row in landmark_rows
    } == {
        "raw",
        "filtered",
    }

    assert fake_capture.released is True
    assert provider.closed is True
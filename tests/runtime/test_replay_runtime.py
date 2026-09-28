import csv
import json
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
    ROI,
    ROIState,
)
from dip_touchless.preprocessing import (
    AdaptivePreprocessor,
    IlluminationAnalyzer,
    IlluminationDecisionStabilizer,
    ROIManager,
)
from dip_touchless.filtering import (
    AdaptiveOneEuroLandmarkFilter,
    FixedOneEuroLandmarkFilter,
    RawLandmarkFilter,
)
from dip_touchless.runtime import ReplayRuntime
from dip_touchless.telemetry import (
    FileRunLogger,
    build_run_metadata,
)
from dip_touchless.tracking import MeasurementValidator
from dip_touchless.interaction import (
    DeterministicGestureEngine,
)


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
                hand_bbox=ROI(
                    x=8,
                    y=8,
                    width=8,
                    height=8,
                    state=ROIState.TRACKING,
                ),
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


class MovingFakeProvider:
    def __init__(self) -> None:
        self.closed = False

    def process(
        self,
        frame,
    ) -> LandmarkObservation:
        movement = (
            0.0
            if frame.frame_id == 0
            else 0.30
        )

        landmarks = tuple(
            Landmark(
                index=index,
                x=(
                    0.10
                    + index * 0.001
                    + movement
                ),
                y=0.20,
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
            quality=MeasurementQuality.unavailable(),
            hand_bbox=ROI(
                x=8,
                y=8,
                width=8,
                height=8,
                state=ROIState.TRACKING,
            ),
            provider_name="moving-fake-provider",
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


def test_replay_runtime_logs_fixed_one_euro_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frames = [
        np.zeros(
            (16, 16, 3),
            dtype=np.uint8,
        ),
        np.ones(
            (16, 16, 3),
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

    video_path = (
        tmp_path / "fixed-one-euro-fixture.mp4"
    )
    video_path.touch()

    run_id = "fixed-one-euro-integration-run"

    source = ReplayFrameSource(
        video_path,
        run_id=run_id,
    )

    provider = MovingFakeProvider()

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
                "mode": "ONE_EURO_FIXED",
                "min_cutoff_hz": 1.0,
                "beta": 0.5,
                "derivative_cutoff_hz": 1.0,
                "reset_gap_s": 0.5,
            },
        },
    )

    filter_config = (
        resolved.data["filter"]
    )

    landmark_filter = (
        FixedOneEuroLandmarkFilter(
            min_cutoff_hz=(
                filter_config[
                    "min_cutoff_hz"
                ]
            ),
            beta=filter_config["beta"],
            derivative_cutoff_hz=(
                filter_config[
                    "derivative_cutoff_hz"
                ]
            ),
            reset_gap_s=(
                filter_config[
                    "reset_gap_s"
                ]
            ),
        )
    )

    metadata = build_run_metadata(
        resolved,
        run_id=run_id,
        code_revision="test-revision",
    )

    runtime = ReplayRuntime(
        source=source,
        provider=provider,
        validator=MeasurementValidator(),
        landmark_filter=landmark_filter,
        logger=FileRunLogger(
            tmp_path / "runs"
        ),
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

    first = frame_rows[0]
    second = frame_rows[1]

    assert first["filter_mode"] == (
        "ONE_EURO_FIXED"
    )

    assert first["dt_s"] == ""

    assert float(
        first["speed"]
    ) == pytest.approx(0.0)

    assert float(
        first["beta"]
    ) == pytest.approx(0.5)

    assert float(
        first["min_cutoff_hz"]
    ) == pytest.approx(1.0)

    assert float(
        first["final_cutoff_hz"]
    ) == pytest.approx(1.0)

    assert first["signal_alpha"] == ""
    assert first["derivative_alpha"] == ""

    assert first["reset_occurred"] == (
        "False"
    )

    assert second["filter_mode"] == (
        "ONE_EURO_FIXED"
    )

    # Replay source at 20 FPS gives dt = 0.05 s.
    assert float(
        second["dt_s"]
    ) == pytest.approx(0.05)

    assert float(
        second["speed"]
    ) > 0.0

    assert float(
        second["beta"]
    ) == pytest.approx(0.5)

    assert float(
        second["min_cutoff_hz"]
    ) == pytest.approx(1.0)

    assert float(
        second["final_cutoff_hz"]
    ) > 1.0

    assert (
        0.0
        < float(
            second["signal_alpha"]
        )
        <= 1.0
    )

    assert (
        0.0
        < float(
            second["derivative_alpha"]
        )
        <= 1.0
    )

    assert second["reset_occurred"] == (
        "False"
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

    # Two valid frames:
    # 21 raw + 21 filtered per frame.
    assert len(landmark_rows) == 84

    second_raw = next(
        row
        for row in landmark_rows
        if (
            row["frame_id"] == "1"
            and row["stage"] == "raw"
            and row["landmark_index"] == "0"
        )
    )

    second_filtered = next(
        row
        for row in landmark_rows
        if (
            row["frame_id"] == "1"
            and row["stage"] == "filtered"
            and row["landmark_index"] == "0"
        )
    )

    raw_x = float(
        second_raw["x"]
    )

    filtered_x = float(
        second_filtered["x"]
    )

    # Frame 0 x was 0.10 and frame 1 raw x is 0.40.
    # Fixed 1-Euro must smooth the ordinary update.
    assert raw_x == pytest.approx(
        0.40
    )

    assert 0.10 < filtered_x < raw_x

    # z is intentionally pass-through in F1.
    assert float(
        second_filtered["z"]
    ) == pytest.approx(
        float(second_raw["z"])
    )

    assert fake_capture.released is True
    assert provider.closed is True


def test_replay_runtime_logs_g2_preprocessing_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frames = [
        np.zeros(
            (32, 32, 3),
            dtype=np.uint8,
        )
        for _ in range(3)
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

    video_path = tmp_path / "g2-fixture.mp4"
    video_path.touch()

    run_id = "g2-integration-run"

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
            "clahe": {
                "policy": "bypass",
            },
        },
    )

    metadata = build_run_metadata(
        resolved,
        run_id=run_id,
        code_revision="test-revision",
    )

    runtime = ReplayRuntime(
        source=source,
        provider=provider,
        validator=MeasurementValidator(),
        landmark_filter=RawLandmarkFilter(),
        logger=FileRunLogger(
            tmp_path / "runs"
        ),
        roi_manager=ROIManager(
            padding_ratio=0.20,
            coast_expand_ratio=0.15,
            coast_frames=2,
            min_width=1,
            min_height=1,
        ),
        illumination_analyzer=(
            IlluminationAnalyzer()
        ),
        illumination_decision=(
            IlluminationDecisionStabilizer(
                ema_alpha=1.0,
                low_light_enter_v=70.0,
                low_light_exit_v=85.0,
                low_contrast_enter_range_v=35.0,
                low_contrast_exit_range_v=45.0,
            )
        ),
        adaptive_preprocessor=(
            AdaptivePreprocessor(
                policy="bypass",
                clip_limit=2.0,
                tile_grid_size=(8, 8),
            )
        ),
    )

    processed = runtime.run(
        metadata=metadata,
        resolved_config=resolved.to_dict(),
    )

    assert processed == 3

    frames_path = (
        tmp_path
        / "runs"
        / run_id
        / "frames.csv"
    )

    with frames_path.open(
        newline="",
        encoding="utf-8",
    ) as file:
        rows = list(
            csv.DictReader(file)
        )

    assert len(rows) == 3

    assert [
        row["frame_id"]
        for row in rows
    ] == [
        "0",
        "1",
        "2",
    ]

    # Frame 0 has no previous geometry.
    # Frame 1 uses frame 0's detected bbox.
    # Frame 2 coasts after frame 1 reports NO_HAND.
    assert [
        row["roi_state"]
        for row in rows
    ] == [
        "SEARCHING",
        "TRACKING",
        "COASTING",
    ]

    # Black fixture:
    # mean V = 0 and robust range = 0.
    assert all(
        row["illumination_state"]
        == "DIFFICULT"
        for row in rows
    )

    assert all(
        float(row["mean_v"]) == pytest.approx(
            0.0
        )
        for row in rows
    )

    assert all(
        float(
            row["robust_range_v"]
        ) == pytest.approx(0.0)
        for row in rows
    )

    # Policy is bypass, therefore difficult illumination
    # does not imply that CLAHE was actually applied.
    assert all(
        row["enhancement_active"]
        == "False"
        for row in rows
    )

    assert all(
        row["filter_mode"] == "RAW"
        for row in rows
    )

    assert all(
        float(
            row["preprocess_ms"]
        ) >= 0.0
        for row in rows
    )

    assert fake_capture.released is True
    assert provider.closed is True


def test_replay_runtime_logs_adaptive_one_euro_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frames = [
        np.zeros(
            (16, 16, 3),
            dtype=np.uint8,
        ),
        np.ones(
            (16, 16, 3),
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

    video_path = (
        tmp_path
        / "adaptive-one-euro-fixture.mp4"
    )
    video_path.touch()

    run_id = (
        "adaptive-one-euro-integration-run"
    )

    source = ReplayFrameSource(
        video_path,
        run_id=run_id,
    )

    provider = MovingFakeProvider()

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
                "mode": (
                    "ONE_EURO_ADAPTIVE"
                ),
            },
        },
    )

    filter_config = resolved.data[
        "filter"
    ]

    adaptive = filter_config[
        "adaptive"
    ]

    landmark_filter = (
        AdaptiveOneEuroLandmarkFilter(
            base_cutoff_hz=(
                adaptive[
                    "base_cutoff_hz"
                ]
            ),
            beta_min=adaptive[
                "beta_min"
            ],
            beta_base=adaptive[
                "beta_base"
            ],
            beta_max=adaptive[
                "beta_max"
            ],
            velocity_gain=adaptive[
                "velocity_gain"
            ],
            velocity_max=adaptive[
                "velocity_max"
            ],
            final_cutoff_min_hz=(
                adaptive[
                    "final_cutoff_min_hz"
                ]
            ),
            final_cutoff_max_hz=(
                adaptive[
                    "final_cutoff_max_hz"
                ]
            ),
            derivative_cutoff_hz=(
                filter_config[
                    "derivative_cutoff_hz"
                ]
            ),
            reset_gap_s=(
                filter_config[
                    "reset_gap_s"
                ]
            ),
        )
    )

    metadata = build_run_metadata(
        resolved,
        run_id=run_id,
        code_revision="test-revision",
    )

    runtime = ReplayRuntime(
        source=source,
        provider=provider,
        validator=MeasurementValidator(),
        landmark_filter=landmark_filter,
        logger=FileRunLogger(
            tmp_path / "runs"
        ),
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
        rows = list(
            csv.DictReader(file)
        )

    assert len(rows) == 2

    first = rows[0]
    second = rows[1]

    assert first["filter_mode"] == (
        "ONE_EURO_ADAPTIVE"
    )

    assert first["dt_s"] == ""

    assert float(
        first["speed"]
    ) == pytest.approx(0.0)

    assert float(
        first["beta"]
    ) == pytest.approx(
        adaptive["beta_base"]
    )

    assert float(
        first["min_cutoff_hz"]
    ) == pytest.approx(
        adaptive["base_cutoff_hz"]
    )

    assert second["filter_mode"] == (
        "ONE_EURO_ADAPTIVE"
    )

    assert float(
        second["dt_s"]
    ) == pytest.approx(0.05)

    assert float(
        second["speed"]
    ) > 0.0

    beta = float(
        second["beta"]
    )

    assert (
        adaptive["beta_min"]
        <= beta
        <= adaptive["beta_max"]
    )

    cutoff = float(
        second["final_cutoff_hz"]
    )

    assert (
        adaptive[
            "final_cutoff_min_hz"
        ]
        <= cutoff
        <= adaptive[
            "final_cutoff_max_hz"
        ]
    )

    assert fake_capture.released is True
    assert provider.closed is True


def test_replay_runtime_logs_adaptive_filter_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frames = [
        np.zeros(
            (16, 16, 3),
            dtype=np.uint8,
        ),
        np.ones(
            (16, 16, 3),
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

    video_path = (
        tmp_path
        / "adaptive-event-fixture.mp4"
    )
    video_path.touch()

    run_id = (
        "adaptive-event-integration-run"
    )

    source = ReplayFrameSource(
        video_path,
        run_id=run_id,
    )

    provider = MovingFakeProvider()

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
                "mode": (
                    "ONE_EURO_ADAPTIVE"
                ),
                "reset_gap_s": 0.01,
            },
        },
    )

    filter_config = resolved.data[
        "filter"
    ]

    adaptive = filter_config[
        "adaptive"
    ]

    landmark_filter = (
        AdaptiveOneEuroLandmarkFilter(
            base_cutoff_hz=(
                adaptive[
                    "base_cutoff_hz"
                ]
            ),
            beta_min=adaptive[
                "beta_min"
            ],
            beta_base=adaptive[
                "beta_base"
            ],
            beta_max=adaptive[
                "beta_max"
            ],
            velocity_gain=adaptive[
                "velocity_gain"
            ],
            velocity_max=adaptive[
                "velocity_max"
            ],
            final_cutoff_min_hz=(
                adaptive[
                    "final_cutoff_min_hz"
                ]
            ),
            final_cutoff_max_hz=(
                adaptive[
                    "final_cutoff_max_hz"
                ]
            ),
            derivative_cutoff_hz=(
                filter_config[
                    "derivative_cutoff_hz"
                ]
            ),
            reset_gap_s=(
                filter_config[
                    "reset_gap_s"
                ]
            ),
        )
    )

    metadata = build_run_metadata(
        resolved,
        run_id=run_id,
        code_revision="test-revision",
    )

    runtime = ReplayRuntime(
        source=source,
        provider=provider,
        validator=MeasurementValidator(),
        landmark_filter=landmark_filter,
        logger=FileRunLogger(
            tmp_path / "runs"
        ),
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

    second = frame_rows[1]

    assert second["reset_occurred"] == (
        "True"
    )

    with (
        run_dir / "events.csv"
    ).open(
        newline="",
        encoding="utf-8",
    ) as file:
        event_rows = list(
            csv.DictReader(file)
        )

    assert len(event_rows) == 1

    event = event_rows[0]

    assert event["frame_id"] == "1"

    assert event["event_type"] == (
        "reset_gap_exceeded"
    )

    assert event["severity"] == "WARNING"

    details = json.loads(
        event["details_json"]
    )

    assert details["filter_mode"] == (
        "ONE_EURO_ADAPTIVE"
    )

    assert details["reset_occurred"] is True

    assert fake_capture.released is True
    assert provider.closed is True


def test_replay_runtime_logs_gesture_interaction_state(
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

    video_path = (
        tmp_path / "gesture-fixture.mp4"
    )
    video_path.touch()

    run_id = "gesture-integration-run"

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

    gesture_config = resolved.data[
        "gesture"
    ]

    gesture_engine = (
        DeterministicGestureEngine(
            pointer_landmark_index=(
                gesture_config[
                    "pointer_landmark_index"
                ]
            ),
            pinch_thumb_landmark_index=(
                gesture_config[
                    "pinch_thumb_landmark_index"
                ]
            ),
            pinch_index_landmark_index=(
                gesture_config[
                    "pinch_index_landmark_index"
                ]
            ),
            hand_scale_landmark_a=(
                gesture_config[
                    "hand_scale_landmark_a"
                ]
            ),
            hand_scale_landmark_b=(
                gesture_config[
                    "hand_scale_landmark_b"
                ]
            ),
            hand_scale_epsilon=(
                gesture_config[
                    "hand_scale_epsilon"
                ]
            ),
            pinch_on=(
                gesture_config["pinch_on"]
            ),
            pinch_off=(
                gesture_config["pinch_off"]
            ),
            rotation_deadzone=(
                gesture_config[
                    "rotation_deadzone"
                ]
            ),
            rotation_gain=(
                gesture_config[
                    "rotation_gain"
                ]
            ),
            rotation_max_delta_rad=(
                gesture_config[
                    "rotation_max_delta_rad"
                ]
            ),
            scale_deadzone=(
                gesture_config[
                    "scale_deadzone"
                ]
            ),
            scale_gain=(
                gesture_config[
                    "scale_gain"
                ]
            ),
            scale_max_delta=(
                gesture_config[
                    "scale_max_delta"
                ]
            ),
        )
    )

    metadata = build_run_metadata(
        resolved,
        run_id=run_id,
        code_revision="test-revision",
    )

    runtime = ReplayRuntime(
        source=ReplayFrameSource(
            video_path,
            run_id=run_id,
        ),
        provider=MovingFakeProvider(),
        validator=MeasurementValidator(),
        landmark_filter=RawLandmarkFilter(),
        logger=FileRunLogger(
            tmp_path / "runs"
        ),
        gesture_engine=gesture_engine,
    )

    processed = runtime.run(
        metadata=metadata,
        resolved_config=resolved.to_dict(),
    )

    assert processed == 2

    frames_path = (
        tmp_path
        / "runs"
        / run_id
        / "frames.csv"
    )

    with frames_path.open(
        newline="",
        encoding="utf-8",
    ) as file:
        rows = list(
            csv.DictReader(file)
        )

    assert len(rows) == 2

    first = rows[0]
    second = rows[1]

    assert first["interaction_valid"] == (
        "False"
    )

    assert float(
        first["pointer_x"]
    ) == pytest.approx(
        0.108
    )

    assert float(
        first["pointer_y"]
    ) == pytest.approx(
        0.20
    )

    assert float(
        first["rotation_dx"]
    ) == pytest.approx(
        0.0
    )

    assert float(
        first["rotation_dy"]
    ) == pytest.approx(
        0.0
    )

    assert float(
        first["scale_delta"]
    ) == pytest.approx(
        0.0
    )

    assert second["interaction_valid"] == (
        "True"
    )

    assert float(
        second["pointer_x"]
    ) == pytest.approx(
        0.408
    )

    assert float(
        second["rotation_dx"]
    ) == pytest.approx(
        0.10
    )

    assert float(
        second["rotation_dy"]
    ) == pytest.approx(
        0.0
    )

    assert second["gesture_ms"] != ""

    assert float(
        second["gesture_ms"]
    ) >= 0.0

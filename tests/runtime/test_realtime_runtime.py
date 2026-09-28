from pathlib import Path

import numpy as np

from dip_touchless.configuration import resolve_config
from dip_touchless.core import (
    ColorSpace,
    FramePacket,
    InteractionState,
    LandmarkObservation,
    MeasurementQuality,
    TrackingStatus,
)
from dip_touchless.filtering import RawLandmarkFilter
from dip_touchless.interaction import DeterministicGestureEngine
from dip_touchless.runtime import RealtimeRuntime
from dip_touchless.telemetry import (
    FileRunLogger,
    build_run_metadata,
)
from dip_touchless.tracking import MeasurementValidator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "default.yaml"


class FakeRealtimeSource:
    def __init__(self) -> None:
        self.index = 0
        self.opened = False
        self.closed = False

    def open(self) -> None:
        self.opened = True

    def read(self) -> FramePacket | None:
        if self.index >= 3:
            return None

        frame_id = self.index
        self.index += 1

        return FramePacket(
            run_id="realtime-test",
            frame_id=frame_id,
            timestamp_s=frame_id * 0.05,
            image=np.zeros(
                (8, 8, 3),
                dtype=np.uint8,
            ),
            color_space=ColorSpace.BGR,
            source_name="fake-camera",
        )

    def close(self) -> None:
        self.closed = True


class NoHandProvider:
    def __init__(self) -> None:
        self.closed = False

    def process(
        self,
        frame: FramePacket,
    ) -> LandmarkObservation:
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


def _gesture() -> DeterministicGestureEngine:
    return DeterministicGestureEngine(
        pointer_landmark_index=8,
        pinch_thumb_landmark_index=4,
        pinch_index_landmark_index=8,
        hand_scale_landmark_a=5,
        hand_scale_landmark_b=17,
        hand_scale_epsilon=1e-6,
        pinch_on=0.30,
        pinch_off=0.40,
        rotation_deadzone=0.005,
        rotation_gain=2.0,
        rotation_max_delta_rad=0.10,
        scale_deadzone=0.01,
        scale_gain=1.0,
        scale_max_delta=0.10,
    )


def test_realtime_runtime_exposes_safe_no_hand_state(
    tmp_path: Path,
) -> None:
    source = FakeRealtimeSource()
    provider = NoHandProvider()
    received: list[InteractionState] = []

    resolved = resolve_config(DEFAULT_CONFIG)
    metadata = build_run_metadata(
        resolved,
        run_id="realtime-test",
        code_revision="test-revision",
    )

    runtime = RealtimeRuntime(
        source=source,
        provider=provider,
        validator=MeasurementValidator(),
        landmark_filter=RawLandmarkFilter(),
        logger=FileRunLogger(tmp_path / "runs"),
        gesture_engine=_gesture(),
        interaction_consumer=received.append,
    )

    processed = runtime.run(
        metadata=metadata,
        resolved_config=resolved.to_dict(),
    )

    assert processed == 3
    assert len(received) == 3
    assert all(
        state.interaction_valid is False
        for state in received
    )
    assert all(
        state.pointer_xy is None
        for state in received
    )
    assert runtime.latest_interaction_state == received[-1]
    assert source.opened is True
    assert source.closed is True
    assert provider.closed is True

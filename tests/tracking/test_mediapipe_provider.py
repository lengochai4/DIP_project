from types import SimpleNamespace

import numpy as np
import pytest

from dip_touchless.core import (
    ColorSpace,
    FramePacket,
    QualitySource,
    TrackingStatus,
)
from dip_touchless.tracking import (
    MediaPipeHandLandmarkerProvider,
)


class FakeLandmarker:
    def __init__(self, result: object) -> None:
        self.result = result
        self.last_image = None
        self.last_timestamp_ms = None
        self.closed = False

    def detect_for_video(
        self,
        image: object,
        timestamp_ms: int,
    ) -> object:
        self.last_image = image
        self.last_timestamp_ms = timestamp_ms
        return self.result

    def close(self) -> None:
        self.closed = True


def _frame(
    *,
    frame_id: int = 4,
    timestamp_s: float = 1.25,
    color_space: ColorSpace = ColorSpace.BGR,
) -> FramePacket:
    image = np.array(
        [[[10, 20, 30]]],
        dtype=np.uint8,
    )

    return FramePacket(
        run_id="run-test",
        frame_id=frame_id,
        timestamp_s=timestamp_s,
        image=image,
        color_space=color_space,
        source_name="fixture",
    )


def _no_hand_result() -> object:
    return SimpleNamespace(
        hand_landmarks=[],
        handedness=[],
    )


def _valid_result() -> object:
    landmarks = [
        SimpleNamespace(
            x=0.1 + index * 0.001,
            y=0.2 + index * 0.001,
            z=-0.01 * index,
        )
        for index in range(21)
    ]

    category = SimpleNamespace(
        category_name="Right",
        display_name=None,
        score=0.92,
    )

    return SimpleNamespace(
        hand_landmarks=[landmarks],
        handedness=[[category]],
    )


def test_provider_preserves_frame_identity_and_timestamp() -> None:
    fake = FakeLandmarker(_no_hand_result())

    provider = MediaPipeHandLandmarkerProvider(
        landmarker=fake,
    )

    observation = provider.process(
        _frame(
            frame_id=7,
            timestamp_s=1.25,
        )
    )

    assert observation.frame_id == 7
    assert observation.timestamp_s == 1.25
    assert fake.last_timestamp_ms == 1250


def test_provider_converts_bgr_to_rgb() -> None:
    fake = FakeLandmarker(_no_hand_result())

    provider = MediaPipeHandLandmarkerProvider(
        landmarker=fake,
    )

    provider.process(_frame())

    rgb = fake.last_image.numpy_view()

    np.testing.assert_array_equal(
        rgb,
        np.array(
            [[[30, 20, 10]]],
            dtype=np.uint8,
        ),
    )


def test_no_hand_is_explicit_and_has_no_fake_landmarks() -> None:
    fake = FakeLandmarker(_no_hand_result())

    provider = MediaPipeHandLandmarkerProvider(
        landmarker=fake,
    )

    observation = provider.process(_frame())

    assert observation.status is TrackingStatus.NO_HAND
    assert observation.landmarks == ()

    assert observation.quality.valid is False
    assert observation.quality.value is None
    assert observation.quality.source is QualitySource.NONE


def test_valid_hand_maps_21_landmarks() -> None:
    fake = FakeLandmarker(_valid_result())

    provider = MediaPipeHandLandmarkerProvider(
        landmarker=fake,
    )

    observation = provider.process(_frame())

    assert observation.status is TrackingStatus.VALID
    assert len(observation.landmarks) == 21

    assert [
        landmark.index
        for landmark in observation.landmarks
    ] == list(range(21))

    assert observation.handedness_label == "Right"
    assert observation.handedness_score == pytest.approx(
        0.92
    )

    # Handedness classification score is not measurement quality.
    assert observation.quality.valid is False
    assert observation.quality.value is None


def test_provider_rejects_non_bgr_input() -> None:
    fake = FakeLandmarker(_no_hand_result())

    provider = MediaPipeHandLandmarkerProvider(
        landmarker=fake,
    )

    with pytest.raises(ValueError):
        provider.process(
            _frame(
                color_space=ColorSpace.RGB,
            )
        )


def test_provider_rejects_non_increasing_millisecond_timestamp() -> None:
    fake = FakeLandmarker(_no_hand_result())

    provider = MediaPipeHandLandmarkerProvider(
        landmarker=fake,
    )

    provider.process(
        _frame(
            frame_id=0,
            timestamp_s=1.0001,
        )
    )

    with pytest.raises(ValueError):
        provider.process(
            _frame(
                frame_id=1,
                timestamp_s=1.0004,
            )
        )


def test_close_releases_landmarker() -> None:
    fake = FakeLandmarker(_no_hand_result())

    provider = MediaPipeHandLandmarkerProvider(
        landmarker=fake,
    )

    provider.close()

    assert fake.closed is True
from dataclasses import replace

import pytest

from dip_touchless.core import (
    CoordinateSpace,
    Landmark,
    LandmarkObservation,
    MeasurementQuality,
    TrackingStatus,
)
from dip_touchless.tracking import MeasurementValidator


def _landmarks() -> tuple[Landmark, ...]:
    return tuple(
        Landmark(
            index=index,
            x=0.1,
            y=0.2,
            z=-0.01,
            coordinate_space=(
                CoordinateSpace.FRAME_NORMALIZED
            ),
        )
        for index in range(21)
    )


def _valid_observation() -> LandmarkObservation:
    return LandmarkObservation(
        frame_id=0,
        timestamp_s=1.0,
        status=TrackingStatus.VALID,
        landmarks=_landmarks(),
        handedness_label="Right",
        handedness_score=0.9,
        quality=MeasurementQuality.unavailable(),
        hand_bbox=None,
        provider_name="fixture",
    )


def test_valid_observation_is_accepted() -> None:
    validator = MeasurementValidator()

    observation = _valid_observation()

    assert validator.validate(observation) is observation


def test_no_hand_requires_empty_landmarks() -> None:
    validator = MeasurementValidator()

    observation = replace(
        _valid_observation(),
        status=TrackingStatus.NO_HAND,
    )

    with pytest.raises(ValueError):
        validator.validate(observation)


def test_valid_hand_requires_21_landmarks() -> None:
    validator = MeasurementValidator()

    observation = replace(
        _valid_observation(),
        landmarks=_landmarks()[:-1],
    )

    with pytest.raises(ValueError):
        validator.validate(observation)


def test_handedness_score_must_be_unit_interval() -> None:
    validator = MeasurementValidator()

    observation = replace(
        _valid_observation(),
        handedness_score=1.2,
    )

    with pytest.raises(ValueError):
        validator.validate(observation)
from dip_touchless.core import (
    CoordinateSpace,
    FilterMode,
    Landmark,
    LandmarkObservation,
    MeasurementQuality,
    TrackingStatus,
)
from dip_touchless.filtering import RawLandmarkFilter


def _landmarks() -> tuple[Landmark, ...]:
    return tuple(
        Landmark(
            index=index,
            x=0.1 + index * 0.01,
            y=0.2,
            z=-0.01,
            coordinate_space=(
                CoordinateSpace.FRAME_NORMALIZED
            ),
        )
        for index in range(21)
    )


def _observation(
    status: TrackingStatus,
) -> LandmarkObservation:
    return LandmarkObservation(
        frame_id=0,
        timestamp_s=1.0,
        status=status,
        landmarks=(
            _landmarks()
            if status in {
                TrackingStatus.VALID,
                TrackingStatus.REACQUIRED,
            }
            else ()
        ),
        handedness_label=None,
        handedness_score=None,
        quality=MeasurementQuality.unavailable(),
        hand_bbox=None,
        provider_name="fixture",
    )


def test_raw_filter_returns_landmarks_unchanged() -> None:
    raw_filter = RawLandmarkFilter()

    observation = _observation(
        TrackingStatus.VALID
    )

    landmarks, diagnostics = raw_filter.update(
        observation
    )

    assert landmarks == observation.landmarks
    assert diagnostics.mode is FilterMode.RAW


def test_raw_filter_does_not_inject_missing_landmarks() -> None:
    raw_filter = RawLandmarkFilter()

    observation = _observation(
        TrackingStatus.NO_HAND
    )

    landmarks, diagnostics = raw_filter.update(
        observation
    )

    assert landmarks == ()
    assert diagnostics.mode is FilterMode.RAW


def test_raw_filter_has_no_temporal_diagnostics() -> None:
    raw_filter = RawLandmarkFilter()

    _, diagnostics = raw_filter.update(
        _observation(TrackingStatus.VALID)
    )

    assert diagnostics.dt_s is None
    assert diagnostics.speed is None
    assert diagnostics.beta is None
    assert diagnostics.signal_alpha is None
    assert diagnostics.derivative_alpha is None
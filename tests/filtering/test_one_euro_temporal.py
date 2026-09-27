import math

import pytest

from dip_touchless.core import (
    CoordinateSpace,
    Landmark,
    LandmarkObservation,
    MeasurementQuality,
    QualitySource,
    TrackingStatus,
)
from dip_touchless.filtering import (
    FixedOneEuroTemporalCore,
)


def _landmarks(
    x: float,
    y: float,
) -> tuple[Landmark, ...]:
    return (
        Landmark(
            index=0,
            x=x,
            y=y,
            z=-0.1,
            coordinate_space=(
                CoordinateSpace.FRAME_NORMALIZED
            ),
        ),
    )


def _observation(
    *,
    timestamp_s: float,
    status: TrackingStatus,
    x: float = 0.0,
    y: float = 0.0,
) -> LandmarkObservation:
    usable = status in {
        TrackingStatus.VALID,
        TrackingStatus.REACQUIRED,
    }

    return LandmarkObservation(
        frame_id=0,
        timestamp_s=timestamp_s,
        status=status,
        landmarks=(
            _landmarks(x, y)
            if usable
            else ()
        ),
        handedness_label=None,
        handedness_score=None,
        quality=MeasurementQuality(
            value=None,
            source=QualitySource.NONE,
            valid=False,
            semantic_name=None,
        ),
        hand_bbox=None,
        provider_name="fixture",
    )


def _core(
    *,
    reset_gap_s: float = 0.5,
) -> FixedOneEuroTemporalCore:
    return FixedOneEuroTemporalCore(
        min_cutoff_hz=1.0,
        beta=0.5,
        derivative_cutoff_hz=1.0,
        reset_gap_s=reset_gap_s,
    )


def test_first_valid_measurement_initializes() -> None:
    core = _core()

    result = core.update(
        _observation(
            timestamp_s=1.0,
            status=TrackingStatus.VALID,
            x=0.2,
            y=0.3,
        )
    )

    assert result.measurement_accepted is True
    assert result.initialization_occurred is True
    assert result.reset_occurred is False
    assert result.dt_s is None

    assert result.landmarks[0].x == pytest.approx(
        0.2
    )

    assert result.landmarks[0].y == pytest.approx(
        0.3
    )


def test_valid_updates_use_timestamp_dt() -> None:
    core = _core()

    core.update(
        _observation(
            timestamp_s=1.0,
            status=TrackingStatus.VALID,
        )
    )

    result = core.update(
        _observation(
            timestamp_s=1.1,
            status=TrackingStatus.VALID,
            x=0.2,
            y=0.1,
        )
    )

    assert result.dt_s == pytest.approx(0.1)
    assert result.initialization_occurred is False
    assert result.reset_occurred is False


@pytest.mark.parametrize(
    "status",
    [
        TrackingStatus.NO_HAND,
        TrackingStatus.TEMPORARY_LOSS,
        TrackingStatus.INVALID,
    ],
)
def test_missing_measurement_does_not_update_with_fake_landmarks(
    status: TrackingStatus,
) -> None:
    core = _core()

    core.update(
        _observation(
            timestamp_s=1.0,
            status=TrackingStatus.VALID,
            x=0.2,
            y=0.3,
        )
    )

    result = core.update(
        _observation(
            timestamp_s=1.1,
            status=status,
        )
    )

    assert result.measurement_accepted is False
    assert result.landmarks == ()
    assert result.landmark_diagnostics == ()
    assert result.reset_occurred is False


def test_short_loss_retains_filter_state() -> None:
    core = _core(
        reset_gap_s=0.5
    )

    core.update(
        _observation(
            timestamp_s=1.0,
            status=TrackingStatus.VALID,
            x=0.0,
            y=0.0,
        )
    )

    core.update(
        _observation(
            timestamp_s=1.1,
            status=TrackingStatus.NO_HAND,
        )
    )

    result = core.update(
        _observation(
            timestamp_s=1.2,
            status=TrackingStatus.REACQUIRED,
            x=1.0,
            y=0.0,
        )
    )

    assert result.dt_s == pytest.approx(0.2)
    assert result.initialization_occurred is False
    assert result.reset_occurred is False

    # State was retained, so this is an ordinary filtered update,
    # not direct reinitialization to raw x=1.
    assert result.landmarks[0].x < 1.0


def test_long_loss_resets_before_reacquisition() -> None:
    core = _core(
        reset_gap_s=0.5
    )

    core.update(
        _observation(
            timestamp_s=1.0,
            status=TrackingStatus.VALID,
            x=0.0,
            y=0.0,
        )
    )

    loss = core.update(
        _observation(
            timestamp_s=1.6,
            status=TrackingStatus.NO_HAND,
        )
    )

    assert loss.reset_occurred is True
    assert loss.event == "loss_gap_exceeded"
    assert core.initialized is False

    reacquired = core.update(
        _observation(
            timestamp_s=1.7,
            status=TrackingStatus.REACQUIRED,
            x=0.8,
            y=0.4,
        )
    )

    assert (
        reacquired.initialization_occurred
        is True
    )

    assert reacquired.landmarks[0].x == pytest.approx(
        0.8
    )

    assert reacquired.landmarks[0].y == pytest.approx(
        0.4
    )


def test_direct_valid_gap_over_reset_threshold_reinitializes() -> None:
    core = _core(
        reset_gap_s=0.5
    )

    core.update(
        _observation(
            timestamp_s=1.0,
            status=TrackingStatus.VALID,
            x=0.0,
            y=0.0,
        )
    )

    result = core.update(
        _observation(
            timestamp_s=1.8,
            status=TrackingStatus.VALID,
            x=0.7,
            y=0.6,
        )
    )

    assert result.reset_occurred is True
    assert result.initialization_occurred is True
    assert result.event == "reset_gap_exceeded"

    assert result.landmarks[0].x == pytest.approx(
        0.7
    )


def test_non_increasing_timestamp_resets_and_reinitializes() -> None:
    core = _core()

    core.update(
        _observation(
            timestamp_s=2.0,
            status=TrackingStatus.VALID,
            x=0.0,
            y=0.0,
        )
    )

    result = core.update(
        _observation(
            timestamp_s=2.0,
            status=TrackingStatus.VALID,
            x=0.9,
            y=0.8,
        )
    )

    assert result.reset_occurred is True
    assert result.initialization_occurred is True
    assert result.event == "timestamp_discontinuity"

    assert result.landmarks[0].x == pytest.approx(
        0.9
    )


def test_reacquired_with_short_gap_is_continuous_update() -> None:
    core = _core()

    core.update(
        _observation(
            timestamp_s=1.0,
            status=TrackingStatus.VALID,
            x=0.0,
            y=0.0,
        )
    )

    result = core.update(
        _observation(
            timestamp_s=1.2,
            status=TrackingStatus.REACQUIRED,
            x=0.5,
            y=0.0,
        )
    )

    assert result.initialization_occurred is False
    assert result.reset_occurred is False
    assert result.dt_s == pytest.approx(0.2)


def test_manual_reset_clears_timestamp_and_filter_state() -> None:
    core = _core()

    core.update(
        _observation(
            timestamp_s=1.0,
            status=TrackingStatus.VALID,
        )
    )

    core.reset()

    assert core.initialized is False
    assert core.last_accepted_timestamp_s is None

    result = core.update(
        _observation(
            timestamp_s=10.0,
            status=TrackingStatus.VALID,
            x=0.4,
            y=0.5,
        )
    )

    assert result.initialization_occurred is True
    assert result.reset_occurred is False


def test_nonfinite_timestamp_is_rejected() -> None:
    core = _core()

    observation = _observation(
        timestamp_s=1.0,
        status=TrackingStatus.VALID,
    )

    bad = LandmarkObservation(
        frame_id=observation.frame_id,
        timestamp_s=math.nan,
        status=observation.status,
        landmarks=observation.landmarks,
        handedness_label=(
            observation.handedness_label
        ),
        handedness_score=(
            observation.handedness_score
        ),
        quality=observation.quality,
        hand_bbox=observation.hand_bbox,
        provider_name=observation.provider_name,
    )

    with pytest.raises(ValueError):
        core.update(bad)


@pytest.mark.parametrize(
    "reset_gap_s",
    [
        0.0,
        -0.1,
        math.inf,
        math.nan,
    ],
)
def test_invalid_reset_gap_is_rejected(
    reset_gap_s: float,
) -> None:
    with pytest.raises(ValueError):
        _core(
            reset_gap_s=reset_gap_s
        )
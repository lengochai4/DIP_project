import math

import pytest

from dip_touchless.core import (
    CoordinateSpace,
    Landmark,
    LandmarkObservation,
    MeasurementQuality,
    TrackingStatus,
)
from dip_touchless.filtering import (
    AdaptiveOneEuroTemporalCore,
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

    landmarks = (
        (
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
        if usable
        else ()
    )

    return LandmarkObservation(
        frame_id=0,
        timestamp_s=timestamp_s,
        status=status,
        landmarks=landmarks,
        handedness_label=None,
        handedness_score=None,
        quality=MeasurementQuality.unavailable(),
        hand_bbox=None,
        provider_name="fixture",
    )


def _core(
    *,
    reset_gap_s: float = 0.5,
) -> AdaptiveOneEuroTemporalCore:
    return AdaptiveOneEuroTemporalCore(
        base_cutoff_hz=1.0,
        beta_min=0.1,
        beta_base=0.2,
        beta_max=1.0,
        velocity_gain=0.5,
        velocity_max=10.0,
        final_cutoff_min_hz=0.5,
        final_cutoff_max_hz=20.0,
        derivative_cutoff_hz=1.0,
        reset_gap_s=reset_gap_s,
    )


def test_first_valid_measurement_initializes() -> None:
    result = _core().update(
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

    diag = result.landmark_diagnostics[0]

    assert diag.speed == pytest.approx(0.0)
    assert diag.beta == pytest.approx(0.2)


def test_valid_update_uses_timestamp_dt() -> None:
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
        )
    )

    assert result.dt_s == pytest.approx(0.1)
    assert result.initialization_occurred is False

    diag = result.landmark_diagnostics[0]

    assert 0.1 <= diag.beta <= 1.0
    assert 0.5 <= diag.cutoff_hz <= 20.0


def test_missing_measurement_does_not_inject_zeros() -> None:
    core = _core()

    core.update(
        _observation(
            timestamp_s=1.0,
            status=TrackingStatus.VALID,
            x=0.2,
        )
    )

    result = core.update(
        _observation(
            timestamp_s=1.1,
            status=TrackingStatus.NO_HAND,
        )
    )

    assert result.measurement_accepted is False
    assert result.landmarks == ()
    assert result.landmark_diagnostics == ()
    assert result.reset_occurred is False


def test_short_loss_retains_adaptive_filter_state() -> None:
    core = _core()

    core.update(
        _observation(
            timestamp_s=1.0,
            status=TrackingStatus.VALID,
            x=0.0,
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
        )
    )

    assert result.dt_s == pytest.approx(0.2)
    assert result.initialization_occurred is False
    assert result.reset_occurred is False

    assert result.landmarks[0].x < 1.0


def test_long_loss_resets_before_reacquisition() -> None:
    core = _core(
        reset_gap_s=0.5
    )

    core.update(
        _observation(
            timestamp_s=1.0,
            status=TrackingStatus.VALID,
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

    reacquired = core.update(
        _observation(
            timestamp_s=1.7,
            status=TrackingStatus.REACQUIRED,
            x=0.8,
            y=0.4,
        )
    )

    assert reacquired.initialization_occurred is True
    assert reacquired.landmarks[0].x == pytest.approx(
        0.8
    )


def test_direct_large_gap_reinitializes() -> None:
    core = _core()

    core.update(
        _observation(
            timestamp_s=1.0,
            status=TrackingStatus.VALID,
        )
    )

    result = core.update(
        _observation(
            timestamp_s=1.8,
            status=TrackingStatus.VALID,
            x=0.7,
        )
    )

    assert result.reset_occurred is True
    assert result.initialization_occurred is True
    assert result.event == "reset_gap_exceeded"

    assert result.landmarks[0].x == pytest.approx(
        0.7
    )


def test_non_increasing_timestamp_resets() -> None:
    core = _core()

    core.update(
        _observation(
            timestamp_s=2.0,
            status=TrackingStatus.VALID,
        )
    )

    result = core.update(
        _observation(
            timestamp_s=2.0,
            status=TrackingStatus.VALID,
            x=0.9,
        )
    )

    assert result.reset_occurred is True
    assert result.initialization_occurred is True
    assert result.event == (
        "timestamp_discontinuity"
    )


def test_manual_reset_clears_timestamp_and_state() -> None:
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


def test_nonfinite_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError):
        _core().update(
            _observation(
                timestamp_s=math.nan,
                status=TrackingStatus.VALID,
            )
        )
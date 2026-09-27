import pytest

from dip_touchless.core import (
    CoordinateSpace,
    FilterMode,
    Landmark,
    LandmarkObservation,
    MeasurementQuality,
    TrackingStatus,
)
from dip_touchless.filtering import (
    AdaptiveOneEuroLandmarkFilter,
)
from dip_touchless.filtering.adaptive_one_euro_landmarks import (
    AdaptiveLandmarkDiagnostics,
)


def _landmark(
    index: int,
    x: float,
    y: float,
    z: float = -0.1,
) -> Landmark:
    return Landmark(
        index=index,
        x=x,
        y=y,
        z=z,
        coordinate_space=(
            CoordinateSpace.FRAME_NORMALIZED
        ),
    )


def _observation(
    *,
    timestamp_s: float,
    status: TrackingStatus,
    landmarks: tuple[Landmark, ...] = (),
) -> LandmarkObservation:
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


def _filter() -> AdaptiveOneEuroLandmarkFilter:
    return AdaptiveOneEuroLandmarkFilter(
        base_cutoff_hz=1.0,
        beta_min=0.0,
        beta_base=0.1,
        beta_max=1.0,
        velocity_gain=0.5,
        velocity_max=10.0,
        final_cutoff_min_hz=0.5,
        final_cutoff_max_hz=20.0,
        derivative_cutoff_hz=1.0,
        reset_gap_s=0.5,
    )


def test_initialization_maps_adaptive_diagnostics() -> None:
    landmark_filter = _filter()

    filtered, diagnostics = (
        landmark_filter.update(
            _observation(
                timestamp_s=1.0,
                status=TrackingStatus.VALID,
                landmarks=(
                    _landmark(
                        0,
                        0.2,
                        0.3,
                    ),
                ),
            )
        )
    )

    assert len(filtered) == 1

    assert diagnostics.mode is (
        FilterMode.ONE_EURO_ADAPTIVE
    )

    assert diagnostics.dt_s is None
    assert diagnostics.speed == pytest.approx(
        0.0
    )

    assert diagnostics.beta == pytest.approx(
        0.1
    )

    assert (
        diagnostics.min_cutoff_hz
        == pytest.approx(1.0)
    )

    assert (
        diagnostics.final_cutoff_hz
        == pytest.approx(1.0)
    )

    assert diagnostics.signal_alpha is None
    assert diagnostics.derivative_alpha is None
    assert diagnostics.reset_occurred is False


def test_ordinary_update_uses_representative_adaptive_values() -> None:
    landmark_filter = _filter()

    landmark_filter.update(
        _observation(
            timestamp_s=1.0,
            status=TrackingStatus.VALID,
            landmarks=(
                _landmark(
                    0,
                    0.0,
                    0.0,
                ),
                _landmark(
                    1,
                    0.5,
                    0.5,
                ),
            ),
        )
    )

    _, diagnostics = landmark_filter.update(
        _observation(
            timestamp_s=1.1,
            status=TrackingStatus.VALID,
            landmarks=(
                _landmark(
                    0,
                    0.4,
                    0.0,
                ),
                _landmark(
                    1,
                    0.5,
                    0.5,
                ),
            ),
        )
    )

    assert diagnostics.dt_s == pytest.approx(
        0.1
    )

    assert diagnostics.speed is not None
    assert diagnostics.speed > 0.0

    assert diagnostics.beta is not None
    assert diagnostics.beta > 0.1
    assert diagnostics.beta <= 1.0

    assert (
        diagnostics.min_cutoff_hz
        == pytest.approx(1.0)
    )

    assert (
        diagnostics.final_cutoff_hz
        is not None
    )

    assert (
        0.5
        <= diagnostics.final_cutoff_hz
        <= 20.0
    )

    assert diagnostics.signal_alpha is not None
    assert (
        diagnostics.derivative_alpha
        is not None
    )


def test_no_measurement_has_no_effective_beta() -> None:
    landmark_filter = _filter()

    landmark_filter.update(
        _observation(
            timestamp_s=1.0,
            status=TrackingStatus.VALID,
            landmarks=(
                _landmark(
                    0,
                    0.2,
                    0.3,
                ),
            ),
        )
    )

    filtered, diagnostics = (
        landmark_filter.update(
            _observation(
                timestamp_s=1.1,
                status=TrackingStatus.NO_HAND,
            )
        )
    )

    assert filtered == ()

    assert diagnostics.mode is (
        FilterMode.ONE_EURO_ADAPTIVE
    )

    assert diagnostics.dt_s is None
    assert diagnostics.speed is None
    assert diagnostics.beta is None

    assert (
        diagnostics.min_cutoff_hz
        == pytest.approx(1.0)
    )

    assert diagnostics.final_cutoff_hz is None
    assert diagnostics.signal_alpha is None
    assert diagnostics.derivative_alpha is None
    assert diagnostics.reset_occurred is False


def test_long_loss_reports_reset() -> None:
    landmark_filter = _filter()

    landmark_filter.update(
        _observation(
            timestamp_s=1.0,
            status=TrackingStatus.VALID,
            landmarks=(
                _landmark(
                    0,
                    0.2,
                    0.3,
                ),
            ),
        )
    )

    _, diagnostics = landmark_filter.update(
        _observation(
            timestamp_s=1.6,
            status=TrackingStatus.NO_HAND,
        )
    )

    assert diagnostics.reset_occurred is True
    assert diagnostics.speed is None
    assert diagnostics.beta is None


def test_gap_reinitialization_uses_beta_base() -> None:
    landmark_filter = _filter()

    landmark_filter.update(
        _observation(
            timestamp_s=1.0,
            status=TrackingStatus.VALID,
            landmarks=(
                _landmark(
                    0,
                    0.0,
                    0.0,
                ),
            ),
        )
    )

    filtered, diagnostics = (
        landmark_filter.update(
            _observation(
                timestamp_s=2.0,
                status=TrackingStatus.VALID,
                landmarks=(
                    _landmark(
                        0,
                        0.8,
                        0.7,
                    ),
                ),
            )
        )
    )

    assert filtered[0].x == pytest.approx(
        0.8
    )

    assert diagnostics.reset_occurred is True
    assert diagnostics.dt_s is None

    assert diagnostics.speed == pytest.approx(
        0.0
    )

    assert diagnostics.beta == pytest.approx(
        0.1
    )

    assert (
        diagnostics.final_cutoff_hz
        == pytest.approx(1.0)
    )


def test_manual_reset_returns_to_initialization() -> None:
    landmark_filter = _filter()

    landmark_filter.update(
        _observation(
            timestamp_s=1.0,
            status=TrackingStatus.VALID,
            landmarks=(
                _landmark(
                    0,
                    0.0,
                    0.0,
                ),
            ),
        )
    )

    landmark_filter.reset()

    _, diagnostics = landmark_filter.update(
        _observation(
            timestamp_s=10.0,
            status=TrackingStatus.VALID,
            landmarks=(
                _landmark(
                    0,
                    0.9,
                    0.4,
                ),
            ),
        )
    )

    assert diagnostics.reset_occurred is False
    assert diagnostics.dt_s is None
    assert diagnostics.speed == pytest.approx(
        0.0
    )
    assert diagnostics.beta == pytest.approx(
        0.1
    )


def test_representative_tie_prefers_lower_index() -> None:
    low_index = AdaptiveLandmarkDiagnostics(
        landmark_index=2,
        filtered_dx=1.0,
        filtered_dy=0.0,
        speed=1.0,
        beta=0.4,
        min_cutoff_hz=1.0,
        cutoff_hz=1.4,
        signal_alpha=0.2,
        derivative_alpha=0.1,
        initialization_occurred=False,
    )

    high_index = AdaptiveLandmarkDiagnostics(
        landmark_index=9,
        filtered_dx=0.0,
        filtered_dy=1.0,
        speed=1.0,
        beta=0.8,
        min_cutoff_hz=1.0,
        cutoff_hz=1.8,
        signal_alpha=0.3,
        derivative_alpha=0.1,
        initialization_occurred=False,
    )

    representative = (
        AdaptiveOneEuroLandmarkFilter
        ._select_representative(
            (
                high_index,
                low_index,
            )
        )
    )

    assert representative.landmark_index == 2
    assert representative.beta == pytest.approx(
        0.4
    )
import math

import pytest
import numpy as np

from dip_touchless.core import (
    ColorSpace,
    CoordinateSpace,
    FramePacket,
    Landmark,
    MeasurementQuality,
    QualitySource,
    ROI,
    ROIState,
)


def test_measurement_quality_unavailable() -> None:
    quality = MeasurementQuality.unavailable()

    assert quality.valid is False
    assert quality.value is None
    assert quality.source is QualitySource.NONE
    assert quality.semantic_name is None


@pytest.mark.parametrize("value", [0.0, 0.5, 1.0])
def test_valid_measurement_quality_accepts_unit_interval(value: float) -> None:
    quality = MeasurementQuality(
        value=value,
        source=QualitySource.PROVIDER_DOCUMENTED,
        valid=True,
        semantic_name="provider_quality",
    )

    assert quality.value == value
    assert quality.valid is True


@pytest.mark.parametrize("value", [-0.01, 1.01, math.nan, math.inf])
def test_valid_measurement_quality_rejects_invalid_values(value: float) -> None:
    with pytest.raises(ValueError):
        MeasurementQuality(
            value=value,
            source=QualitySource.PROVIDER_DOCUMENTED,
            valid=True,
            semantic_name="provider_quality",
        )


def test_valid_measurement_quality_requires_real_source() -> None:
    with pytest.raises(ValueError):
        MeasurementQuality(
            value=0.8,
            source=QualitySource.NONE,
            valid=True,
            semantic_name="quality",
        )


def test_roi_requires_positive_dimensions() -> None:
    with pytest.raises(ValueError):
        ROI(
            x=0,
            y=0,
            width=0,
            height=100,
            state=ROIState.SEARCHING,
        )


def test_landmark_requires_finite_coordinates() -> None:
    with pytest.raises(ValueError):
        Landmark(
            index=8,
            x=math.nan,
            y=0.5,
            z=0.0,
            coordinate_space=CoordinateSpace.FRAME_NORMALIZED,
        )


def test_frame_packet_accepts_explicit_color_space() -> None:
    frame = FramePacket(
        run_id="run-test",
        frame_id=0,
        timestamp_s=1.0,
        image=np.zeros((2, 2, 3), dtype=np.uint8),
        color_space=ColorSpace.BGR,
        source_name="test-source",
    )

    assert frame.color_space is ColorSpace.BGR


def test_frame_packet_rejects_empty_image() -> None:
    with pytest.raises(ValueError):
        FramePacket(
            run_id="run-test",
            frame_id=0,
            timestamp_s=1.0,
            image=np.empty((0, 0, 3), dtype=np.uint8),
            color_space=ColorSpace.BGR,
            source_name="test-source",
        )
import numpy as np
import pytest

from dip_touchless.core import (
    ColorSpace,
    FramePacket,
    ROI,
    ROIState,
)
from dip_touchless.preprocessing import (
    IlluminationAnalyzer,
)


def _frame(
    image: np.ndarray,
    *,
    color_space: ColorSpace = ColorSpace.BGR,
) -> FramePacket:
    return FramePacket(
        run_id="run-test",
        frame_id=0,
        timestamp_s=0.0,
        image=image,
        color_space=color_space,
        source_name="fixture",
    )


def _roi(
    x: int,
    y: int,
    width: int,
    height: int,
) -> ROI:
    return ROI(
        x=x,
        y=y,
        width=width,
        height=height,
        state=ROIState.TRACKING,
    )


def test_constant_value_roi_has_expected_descriptors() -> None:
    image = np.full(
        (4, 5, 3),
        50,
        dtype=np.uint8,
    )

    analyzer = IlluminationAnalyzer()

    result = analyzer.measure(
        _frame(image),
        _roi(
            0,
            0,
            5,
            4,
        ),
    )

    assert result.mean_v == pytest.approx(50.0)
    assert result.std_v == pytest.approx(0.0)
    assert result.p10_v == pytest.approx(50.0)
    assert result.p90_v == pytest.approx(50.0)

    assert result.robust_range_v == pytest.approx(
        0.0
    )


def test_analyzer_uses_hsv_value_channel() -> None:
    image = np.array(
        [
            [
                [10, 20, 30],
                [100, 50, 20],
            ]
        ],
        dtype=np.uint8,
    )

    analyzer = IlluminationAnalyzer()

    result = analyzer.measure(
        _frame(image),
        _roi(
            0,
            0,
            2,
            1,
        ),
    )

    # HSV V is max(B, G, R):
    # [10, 20, 30] -> 30
    # [100, 50, 20] -> 100
    assert result.mean_v == pytest.approx(
        65.0
    )


def test_percentiles_and_robust_range_are_deterministic() -> None:
    values = np.array(
        [0, 10, 20, 30, 40],
        dtype=np.uint8,
    )

    image = np.stack(
        [values, values, values],
        axis=-1,
    ).reshape(
        1,
        5,
        3,
    )

    analyzer = IlluminationAnalyzer()

    result = analyzer.measure(
        _frame(image),
        _roi(
            0,
            0,
            5,
            1,
        ),
    )

    assert result.mean_v == pytest.approx(
        20.0
    )

    assert result.p10_v == pytest.approx(
        4.0
    )

    assert result.p90_v == pytest.approx(
        36.0
    )

    assert result.robust_range_v == pytest.approx(
        32.0
    )


def test_only_selected_roi_contributes_to_metrics() -> None:
    image = np.full(
        (4, 4, 3),
        200,
        dtype=np.uint8,
    )

    image[
        1:3,
        1:3,
    ] = 25

    analyzer = IlluminationAnalyzer()

    result = analyzer.measure(
        _frame(image),
        _roi(
            1,
            1,
            2,
            2,
        ),
    )

    assert result.mean_v == pytest.approx(
        25.0
    )

    assert result.std_v == pytest.approx(
        0.0
    )


def test_analyzer_does_not_modify_source_frame() -> None:
    image = np.arange(
        4 * 4 * 3,
        dtype=np.uint8,
    ).reshape(
        4,
        4,
        3,
    )

    original = image.copy()

    analyzer = IlluminationAnalyzer()

    analyzer.measure(
        _frame(image),
        _roi(
            1,
            1,
            2,
            2,
        ),
    )

    np.testing.assert_array_equal(
        image,
        original,
    )


def test_non_bgr_frame_is_rejected() -> None:
    image = np.zeros(
        (4, 4, 3),
        dtype=np.uint8,
    )

    analyzer = IlluminationAnalyzer()

    with pytest.raises(ValueError):
        analyzer.measure(
            _frame(
                image,
                color_space=ColorSpace.RGB,
            ),
            _roi(
                0,
                0,
                4,
                4,
            ),
        )


def test_out_of_bounds_roi_is_rejected() -> None:
    image = np.zeros(
        (4, 4, 3),
        dtype=np.uint8,
    )

    analyzer = IlluminationAnalyzer()

    with pytest.raises(ValueError):
        analyzer.measure(
            _frame(image),
            _roi(
                3,
                3,
                2,
                2,
            ),
        )
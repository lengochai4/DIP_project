import numpy as np
import pytest

from dip_touchless.core import (
    ColorSpace,
    FramePacket,
    IlluminationMetrics,
    IlluminationState,
    ROI,
    ROIState,
)
from dip_touchless.preprocessing import (
    AdaptivePreprocessor,
)


def _metrics(
    state: IlluminationState,
) -> IlluminationMetrics:
    return IlluminationMetrics(
        mean_v=80.0,
        std_v=20.0,
        p10_v=30.0,
        p90_v=90.0,
        robust_range_v=60.0,
        state=state,
        enhancement_active=(
            state is not IlluminationState.NORMAL
        ),
    )


def _processor(
    policy: str,
) -> AdaptivePreprocessor:
    return AdaptivePreprocessor(
        policy=policy,
        clip_limit=2.0,
        tile_grid_size=(8, 8),
    )


def _nonuniform_image() -> np.ndarray:
    values = np.tile(
        np.arange(
            32,
            dtype=np.uint8,
        ),
        (32, 1),
    )

    values = (
        values * 3
    ).astype(np.uint8)

    return np.stack(
        [values, values, values],
        axis=-1,
    )


def test_bypass_returns_semantically_unchanged_roi() -> None:
    image = _nonuniform_image()
    original = image.copy()

    result = _processor(
        "bypass"
    ).process_roi(
        image,
        _metrics(
            IlluminationState.DIFFICULT
        ),
    )

    np.testing.assert_array_equal(
        result.image_bgr,
        original,
    )

    assert (
        result.illumination.enhancement_active
        is False
    )

    np.testing.assert_array_equal(
        image,
        original,
    )


def test_adaptive_normal_state_bypasses_clahe() -> None:
    image = _nonuniform_image()

    result = _processor(
        "adaptive"
    ).process_roi(
        image,
        _metrics(
            IlluminationState.NORMAL
        ),
    )

    np.testing.assert_array_equal(
        result.image_bgr,
        image,
    )

    assert (
        result.illumination.enhancement_active
        is False
    )


def test_adaptive_difficult_state_applies_clahe() -> None:
    image = _nonuniform_image()

    result = _processor(
        "adaptive"
    ).process_roi(
        image,
        _metrics(
            IlluminationState.DIFFICULT
        ),
    )

    assert result.image_bgr.shape == image.shape
    assert result.image_bgr.dtype == np.uint8

    assert (
        result.illumination.enhancement_active
        is True
    )

    assert not np.array_equal(
        result.image_bgr,
        image,
    )


def test_always_policy_applies_even_in_normal_state() -> None:
    image = _nonuniform_image()

    result = _processor(
        "always"
    ).process_roi(
        image,
        _metrics(
            IlluminationState.NORMAL
        ),
    )

    assert (
        result.illumination.enhancement_active
        is True
    )

    assert not np.array_equal(
        result.image_bgr,
        image,
    )


@pytest.mark.parametrize(
    "state",
    [
        IlluminationState.LOW_LIGHT,
        IlluminationState.LOW_CONTRAST,
        IlluminationState.DIFFICULT,
    ],
)
def test_adaptive_policy_enhances_all_non_normal_states(
    state: IlluminationState,
) -> None:
    result = _processor(
        "adaptive"
    ).process_roi(
        _nonuniform_image(),
        _metrics(state),
    )

    assert (
        result.illumination.enhancement_active
        is True
    )


def test_preprocessing_preserves_shape_and_dtype() -> None:
    image = _nonuniform_image()

    result = _processor(
        "always"
    ).process_roi(
        image,
        _metrics(
            IlluminationState.LOW_CONTRAST
        ),
    )

    assert result.image_bgr.shape == image.shape
    assert result.image_bgr.dtype == image.dtype


def test_preprocessing_does_not_mutate_source_roi() -> None:
    image = _nonuniform_image()
    original = image.copy()

    _processor(
        "always"
    ).process_roi(
        image,
        _metrics(
            IlluminationState.DIFFICULT
        ),
    )

    np.testing.assert_array_equal(
        image,
        original,
    )


def test_invalid_policy_is_rejected() -> None:
    with pytest.raises(ValueError):
        _processor(
            "invalid"
        )


def test_non_uint8_roi_is_rejected() -> None:
    image = np.zeros(
        (8, 8, 3),
        dtype=np.float32,
    )

    with pytest.raises(ValueError):
        _processor(
            "always"
        ).process_roi(
            image,
            _metrics(
                IlluminationState.DIFFICULT
            ),
        )


def _frame(
    image: np.ndarray,
    *,
    color_space: ColorSpace = ColorSpace.BGR,
) -> FramePacket:
    return FramePacket(
        run_id="run-test",
        frame_id=7,
        timestamp_s=1.25,
        image=image,
        color_space=color_space,
        source_name="fixture",
    )


def _roi() -> ROI:
    return ROI(
        x=8,
        y=8,
        width=16,
        height=16,
        state=ROIState.TRACKING,
    )


def test_full_frame_preprocessing_preserves_frame_contract() -> None:
    image = _nonuniform_image()

    result = _processor(
        "always"
    ).process_frame(
        _frame(image),
        _roi(),
        _metrics(
            IlluminationState.LOW_CONTRAST
        ),
    )

    assert result.frame.image.shape == image.shape
    assert result.frame.image.dtype == np.uint8

    assert (
        result.frame.color_space
        is ColorSpace.BGR
    )

    assert result.frame.run_id == "run-test"
    assert result.frame.frame_id == 7
    assert result.frame.timestamp_s == pytest.approx(
        1.25
    )

    assert result.frame.source_name == "fixture"


def test_pixels_outside_roi_are_unchanged() -> None:
    image = _nonuniform_image()
    roi = _roi()

    result = _processor(
        "always"
    ).process_frame(
        _frame(image),
        roi,
        _metrics(
            IlluminationState.DIFFICULT
        ),
    )

    outside_mask = np.ones(
        image.shape[:2],
        dtype=bool,
    )

    outside_mask[
        roi.y : roi.y + roi.height,
        roi.x : roi.x + roi.width,
    ] = False

    np.testing.assert_array_equal(
        result.frame.image[outside_mask],
        image[outside_mask],
    )


def test_composited_roi_matches_roi_preprocessing_result() -> None:
    image = _nonuniform_image()
    roi = _roi()

    processor = _processor(
        "always"
    )

    expected = processor.process_roi(
        image[
            roi.y : roi.y + roi.height,
            roi.x : roi.x + roi.width,
        ],
        _metrics(
            IlluminationState.DIFFICULT
        ),
    )

    result = processor.process_frame(
        _frame(image),
        roi,
        _metrics(
            IlluminationState.DIFFICULT
        ),
    )

    actual_roi = result.frame.image[
        roi.y : roi.y + roi.height,
        roi.x : roi.x + roi.width,
    ]

    np.testing.assert_array_equal(
        actual_roi,
        expected.image_bgr,
    )


def test_full_frame_preprocessing_does_not_mutate_source() -> None:
    image = _nonuniform_image()
    original = image.copy()

    source = _frame(image)

    _processor(
        "always"
    ).process_frame(
        source,
        _roi(),
        _metrics(
            IlluminationState.DIFFICULT
        ),
    )

    np.testing.assert_array_equal(
        source.image,
        original,
    )


def test_full_frame_bypass_preserves_all_pixels() -> None:
    image = _nonuniform_image()

    result = _processor(
        "bypass"
    ).process_frame(
        _frame(image),
        _roi(),
        _metrics(
            IlluminationState.DIFFICULT
        ),
    )

    np.testing.assert_array_equal(
        result.frame.image,
        image,
    )

    assert (
        result.illumination.enhancement_active
        is False
    )


def test_searching_full_frame_roi_preserves_frame_geometry() -> None:
    image = _nonuniform_image()

    full_roi = ROI(
        x=0,
        y=0,
        width=image.shape[1],
        height=image.shape[0],
        state=ROIState.SEARCHING,
    )

    result = _processor(
        "always"
    ).process_frame(
        _frame(image),
        full_roi,
        _metrics(
            IlluminationState.LOW_LIGHT
        ),
    )

    assert result.frame.image.shape == image.shape
    assert result.frame.image.dtype == image.dtype
    assert result.frame.color_space is ColorSpace.BGR


def test_full_frame_preprocessing_rejects_out_of_bounds_roi() -> None:
    image = _nonuniform_image()

    invalid_roi = ROI(
        x=24,
        y=24,
        width=16,
        height=16,
        state=ROIState.TRACKING,
    )

    with pytest.raises(ValueError):
        _processor(
            "always"
        ).process_frame(
            _frame(image),
            invalid_roi,
            _metrics(
                IlluminationState.DIFFICULT
            ),
        )
import numpy as np
import pytest

from dip_touchless.core import (
    IlluminationMetrics,
    IlluminationState,
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
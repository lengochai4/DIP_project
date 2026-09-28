import math

import pytest

from dip_touchless.core import InteractionState
from extensions.stem3d import (
    Stem3DSceneState,
)


def _interaction(
    *,
    valid: bool = True,
    rotation: tuple[float, float] = (
        0.0,
        0.0,
    ),
    scale_delta: float = 0.0,
) -> InteractionState:
    return InteractionState(
        run_id="scene-test",
        frame_id=0,
        timestamp_s=0.0,
        interaction_valid=valid,
        pointer_xy=(0.5, 0.5),
        pinch_ratio=0.3,
        pinch_active=False,
        rotation_delta=rotation,
        scale_delta=scale_delta,
    )


def _scene() -> Stem3DSceneState:
    return Stem3DSceneState(
        initial_scale=1.0,
        min_scale=0.5,
        max_scale=2.0,
    )


def test_scene_starts_at_neutral_transform() -> None:
    scene = _scene()

    assert scene.transform.yaw_rad == 0.0
    assert scene.transform.pitch_rad == 0.0
    assert scene.transform.scale == 1.0


def test_valid_interaction_accumulates_rotation() -> None:
    scene = _scene()

    result = scene.consume(
        _interaction(
            rotation=(0.1, -0.2),
        )
    )

    assert result.yaw_rad == pytest.approx(
        0.1
    )
    assert result.pitch_rad == pytest.approx(
        -0.2
    )

    result = scene.consume(
        _interaction(
            rotation=(0.05, 0.10),
        )
    )

    assert result.yaw_rad == pytest.approx(
        0.15
    )
    assert result.pitch_rad == pytest.approx(
        -0.10
    )


def test_valid_interaction_accumulates_scale() -> None:
    scene = _scene()

    enlarged = scene.consume(
        _interaction(
            scale_delta=0.2,
        )
    )

    assert enlarged.scale == pytest.approx(
        1.2
    )

    shrunk = scene.consume(
        _interaction(
            scale_delta=-0.1,
        )
    )

    assert shrunk.scale == pytest.approx(
        1.1
    )


def test_invalid_interaction_is_scene_neutral() -> None:
    scene = _scene()

    before = scene.transform

    after = scene.consume(
        _interaction(
            valid=False,
            rotation=(1.0, 1.0),
            scale_delta=1.0,
        )
    )

    assert after == before


def test_scale_is_clamped_to_upper_bound() -> None:
    scene = _scene()

    result = scene.consume(
        _interaction(
            scale_delta=10.0,
        )
    )

    assert result.scale == pytest.approx(
        2.0
    )


def test_scale_is_clamped_to_lower_bound() -> None:
    scene = _scene()

    result = scene.consume(
        _interaction(
            scale_delta=-10.0,
        )
    )

    assert result.scale == pytest.approx(
        0.5
    )


def test_reset_restores_neutral_transform() -> None:
    scene = _scene()

    scene.consume(
        _interaction(
            rotation=(0.2, -0.1),
            scale_delta=0.4,
        )
    )

    scene.reset()

    assert scene.transform.yaw_rad == 0.0
    assert scene.transform.pitch_rad == 0.0
    assert scene.transform.scale == 1.0


@pytest.mark.parametrize(
    ("initial", "minimum", "maximum"),
    [
        (0.0, 0.5, 2.0),
        (1.0, 0.0, 2.0),
        (1.0, 0.5, 0.0),
        (0.4, 0.5, 2.0),
        (3.0, 0.5, 2.0),
        (math.nan, 0.5, 2.0),
    ],
)
def test_invalid_scene_scale_configuration_is_rejected(
    initial: float,
    minimum: float,
    maximum: float,
) -> None:
    with pytest.raises(ValueError):
        Stem3DSceneState(
            initial_scale=initial,
            min_scale=minimum,
            max_scale=maximum,
        )


def test_nonfinite_valid_interaction_is_rejected() -> None:
    scene = _scene()

    with pytest.raises(ValueError):
        scene.consume(
            _interaction(
                rotation=(math.inf, 0.0),
            )
        )
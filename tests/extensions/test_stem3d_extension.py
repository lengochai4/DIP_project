from pathlib import Path

import pytest

from dip_touchless.core import (
    InteractionState,
)
from extensions.stem3d import (
    OpenGLStemRenderer,
    SceneTransform,
    Stem3DExtension,
    Stem3DSceneState,
)


class FakeRenderer:
    def __init__(self) -> None:
        self.opened = False
        self.closed = False
        self.rendered: list[
            SceneTransform
        ] = []

    def open(self) -> None:
        self.opened = True

    def render(
        self,
        transform: SceneTransform,
    ) -> None:
        self.rendered.append(
            transform
        )

    def close_requested(
        self,
    ) -> bool:
        return False

    def close(self) -> None:
        self.closed = True


def _state(
    *,
    valid: bool = True,
    rotation: tuple[
        float,
        float,
    ] = (0.0, 0.0),
    scale_delta: float = 0.0,
) -> InteractionState:
    return InteractionState(
        run_id="extension-test",
        frame_id=0,
        timestamp_s=0.0,
        interaction_valid=valid,
        pointer_xy=(0.5, 0.5),
        pinch_ratio=0.3,
        pinch_active=False,
        rotation_delta=rotation,
        scale_delta=scale_delta,
    )


def test_extension_consumes_interaction_state() -> None:
    renderer = FakeRenderer()

    extension = Stem3DExtension(
        scene_state=Stem3DSceneState(
            initial_scale=1.0,
            min_scale=0.5,
            max_scale=2.0,
        ),
        renderer=renderer,
    )

    extension.open()

    result = extension.consume(
        _state(
            rotation=(0.1, -0.2),
            scale_delta=0.25,
        )
    )

    assert renderer.opened is True

    assert result.yaw_rad == pytest.approx(
        0.1
    )

    assert result.pitch_rad == pytest.approx(
        -0.2
    )

    assert result.scale == pytest.approx(
        1.25
    )

    assert renderer.rendered == [
        result
    ]

    extension.close()

    assert renderer.closed is True


def test_invalid_interaction_renders_unchanged_scene() -> None:
    renderer = FakeRenderer()

    extension = Stem3DExtension(
        scene_state=Stem3DSceneState(
            initial_scale=1.0,
            min_scale=0.5,
            max_scale=2.0,
        ),
        renderer=renderer,
    )

    result = extension.consume(
        _state(
            valid=False,
            rotation=(1.0, 1.0),
            scale_delta=1.0,
        )
    )

    assert result == SceneTransform(
        yaw_rad=0.0,
        pitch_rad=0.0,
        scale=1.0,
    )


@pytest.mark.parametrize(
    "forbidden_import",
    [
        "dip_touchless.filtering",
        "dip_touchless.tracking",
        "dip_touchless.preprocessing",
        "mediapipe",
    ],
)
def test_stem3d_extension_modules_do_not_import_algorithm_internals(
    forbidden_import: str,
) -> None:
    extension_root = (
        Path(__file__)
        .resolve()
        .parents[2]
        / "extensions"
        / "stem3d"
    )

    # live_demo is the composition root: it wires Core components into the
    # Extension. The boundary restriction applies to the Extension modules
    # that consume InteractionState, not to the composition root.
    extension_modules = (
        path.read_text(
            encoding="utf-8",
        )
        for path in extension_root.glob(
            "*.py"
        )
        if path.name != "live_demo.py"
    )
    source = "\n".join(extension_modules)

    assert (
        forbidden_import
        not in source
    )


@pytest.mark.parametrize(
    ("width", "height", "fps"),
    [
        (0, 720, 60),
        (1280, 0, 60),
        (1280, 720, 0),
        (-1, 720, 60),
    ],
)
def test_renderer_rejects_invalid_dimensions(
    width: int,
    height: int,
    fps: int,
) -> None:
    with pytest.raises(ValueError):
        OpenGLStemRenderer(
            width=width,
            height=height,
            target_fps=fps,
        )


def test_renderer_can_be_constructed_without_opening_context() -> None:
    renderer = OpenGLStemRenderer(
        width=1280,
        height=720,
        target_fps=60,
    )

    assert renderer.opened is False

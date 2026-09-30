import ast
from pathlib import Path

import pytest

from dip_touchless.core import (
    InteractionState,
)
from extensions.stem3d import (
    CoordinateCubeScene,
    OpenGLStemRenderer,
    SceneRegistry,
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
    scene = CoordinateCubeScene(
        Stem3DSceneState(
            initial_scale=1.0,
            min_scale=0.5,
            max_scale=2.0,
        )
    )
    registry = SceneRegistry(
        [scene],
        initial_scene_id=scene.id,
    )

    extension = Stem3DExtension(
        scene_registry=registry,
        renderer=renderer,
    )

    extension.open()

    extension.consume(
        _state(
            rotation=(0.1, -0.2),
            scale_delta=0.25,
        )
    )
    result = scene.transform

    assert renderer.opened is True
    assert scene.active is True
    assert extension.active_scene_id == scene.id

    assert result.yaw_rad == pytest.approx(
        0.1
    )

    assert result.pitch_rad == pytest.approx(
        -0.2
    )

    assert result.scale == pytest.approx(
        1.25
    )

    assert renderer.rendered[-1] == result

    extension.close()

    assert renderer.closed is True
    assert scene.active is False
    assert registry.active_scene is None


def test_invalid_interaction_renders_unchanged_scene() -> None:
    renderer = FakeRenderer()
    scene = CoordinateCubeScene(
        Stem3DSceneState(
            initial_scale=1.0,
            min_scale=0.5,
            max_scale=2.0,
        )
    )
    registry = SceneRegistry(
        [scene],
        initial_scene_id=scene.id,
    )

    extension = Stem3DExtension(
        scene_registry=registry,
        renderer=renderer,
    )
    extension.open()

    extension.consume(
        _state(
            valid=False,
            rotation=(1.0, 1.0),
            scale_delta=1.0,
        )
    )

    assert scene.transform == SceneTransform(
        yaw_rad=0.0,
        pitch_rad=0.0,
        scale=1.0,
    )
    assert renderer.rendered[-1] == scene.transform
    extension.close()


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
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for path in extension_root.rglob("*.py")
        if path.name != "live_demo.py"
    )
    imported_modules: set[str] = set()
    for module in extension_modules:
        for node in ast.walk(module):
            if isinstance(node, ast.Import):
                imported_modules.update(
                    alias.name for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom):
                imported_module = node.module or ""
                imported_modules.update(
                    f"{imported_module}.{alias.name}"
                    if imported_module
                    else alias.name
                    for alias in node.names
                )

    assert not any(
        module == forbidden_import
        or module.startswith(f"{forbidden_import}.")
        for module in imported_modules
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

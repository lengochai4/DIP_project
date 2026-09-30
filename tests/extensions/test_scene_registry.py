import pytest

from dip_touchless.core import InteractionState
from extensions.stem3d import (
    SceneRegistry,
    Stem3DExtension,
)


class RecordingScene:
    def __init__(self, scene_id: str) -> None:
        self.id = scene_id
        self.title = f"Scene {scene_id}"
        self.category = "test"
        self.calls: list[tuple[str, object | None]] = []

    def activate(self) -> None:
        self.calls.append(("activate", None))

    def deactivate(self) -> None:
        self.calls.append(("deactivate", None))

    def reset(self) -> None:
        self.calls.append(("reset", None))

    def update(self, dt_s: float) -> None:
        self.calls.append(("update", dt_s))

    def apply_interaction(self, state: InteractionState) -> None:
        self.calls.append(("interaction", state))

    def render(self, viewport: object) -> None:
        self.calls.append(("render", viewport))


class RecordingRenderer:
    def __init__(self) -> None:
        self.opened = False
        self.closed = False

    def open(self) -> None:
        self.opened = True

    def render(self, _transform: object) -> None:
        pass

    def close_requested(self) -> bool:
        return False

    def close(self) -> None:
        self.closed = True


class FailingRenderScene(RecordingScene):
    def render(self, viewport: object) -> None:
        super().render(viewport)
        raise RuntimeError("render failed")


def _interaction(timestamp_s: float) -> InteractionState:
    return InteractionState(
        run_id="registry-test",
        frame_id=0,
        timestamp_s=timestamp_s,
        interaction_valid=True,
        pointer_xy=(0.5, 0.5),
        pinch_ratio=0.3,
        pinch_active=False,
        rotation_delta=(0.0, 0.0),
        scale_delta=0.0,
    )


def test_registry_manages_initial_switch_reset_and_deactivation() -> None:
    first = RecordingScene("first")
    second = RecordingScene("second")
    registry = SceneRegistry(
        [first, second],
        initial_scene_id="first",
    )

    assert registry.active_scene is None
    assert registry.activate_initial() is first
    assert registry.active_scene_id == "first"
    assert first.calls == [("activate", None)]

    registry.activate("first")
    assert first.calls == [("activate", None)]

    assert registry.activate("second") is second
    assert first.calls[-1] == ("deactivate", None)
    assert second.calls == [("activate", None)]

    registry.reset_active()
    registry.deactivate()

    assert second.calls[-2:] == [
        ("reset", None),
        ("deactivate", None),
    ]
    assert registry.active_scene is None


def test_extension_routes_lifecycle_and_interaction_to_active_scene() -> None:
    first = RecordingScene("first")
    second = RecordingScene("second")
    registry = SceneRegistry(
        [first, second],
        initial_scene_id="first",
    )
    renderer = RecordingRenderer()
    extension = Stem3DExtension(
        scene_registry=registry,
        renderer=renderer,  # type: ignore[arg-type]
    )

    extension.open()
    extension.consume(_interaction(1.0))
    extension.consume(_interaction(1.05))
    extension.activate_scene("second")
    extension.consume(_interaction(3.0))
    extension.reset()
    extension.close()

    assert first.calls[0] == ("activate", None)
    assert first.calls[1] == ("render", renderer)
    assert first.calls[2] == ("interaction", _interaction(1.0))
    assert first.calls[3] == ("update", 0.0)
    assert first.calls[4] == ("render", renderer)
    assert first.calls[5] == ("interaction", _interaction(1.05))
    assert first.calls[6] == ("update", pytest.approx(0.05))
    assert first.calls[7] == ("render", renderer)
    assert first.calls[-1] == ("deactivate", None)

    assert second.calls == [
        ("activate", None),
        ("render", renderer),
        ("interaction", _interaction(3.0)),
        ("update", 0.0),
        ("render", renderer),
        ("reset", None),
        ("render", renderer),
        ("deactivate", None),
    ]
    assert renderer.closed is True


def test_registry_rejects_duplicate_and_unknown_scene_ids() -> None:
    first = RecordingScene("same")
    second = RecordingScene("same")

    with pytest.raises(ValueError, match="duplicate"):
        SceneRegistry(
            [first, second],
            initial_scene_id="same",
        )

    registry = SceneRegistry(
        [first],
        initial_scene_id="same",
    )
    with pytest.raises(KeyError, match="unknown STEM scene"):
        registry.activate("missing")


def test_registry_requires_a_registered_initial_scene() -> None:
    with pytest.raises(KeyError, match="initial STEM scene"):
        SceneRegistry(
            [RecordingScene("one")],
            initial_scene_id="missing",
        )


def test_registry_requires_at_least_one_scene() -> None:
    with pytest.raises(ValueError, match="at least one"):
        SceneRegistry([], initial_scene_id="missing")


def test_registry_rejects_scene_missing_lifecycle_methods() -> None:
    class IncompleteScene:
        id = "incomplete"
        title = "Incomplete"
        category = "test"

    with pytest.raises(ValueError, match=r"missing activate\(\)"):
        SceneRegistry(
            [IncompleteScene()],  # type: ignore[list-item]
            initial_scene_id="incomplete",
        )


def test_extension_closes_renderer_when_initial_scene_render_fails() -> None:
    scene = FailingRenderScene("failing")
    registry = SceneRegistry(
        [scene],
        initial_scene_id="failing",
    )
    renderer = RecordingRenderer()
    extension = Stem3DExtension(
        scene_registry=registry,
        renderer=renderer,  # type: ignore[arg-type]
    )

    with pytest.raises(RuntimeError, match="render failed"):
        extension.open()

    assert renderer.closed is True
    assert registry.active_scene is None
    assert scene.calls[-1] == ("deactivate", None)

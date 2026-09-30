import math

import pytest

from dip_touchless.core import InteractionState
from extensions.stem3d import (
    MOLECULE_PRESETS,
    MolecularGeometryScene,
    OrbitalSystemScene,
    SceneFrame,
    SceneMetadata,
    SceneRegistry,
    Stem3DApplicationController,
    Stem3DExtension,
    Stem3DSceneState,
    build_tier1_scene_registry,
)
from extensions.stem3d.ui import ApplicationPhase, LiveDashboard


def _scene_state() -> Stem3DSceneState:
    return Stem3DSceneState(
        initial_scale=1.0,
        min_scale=0.5,
        max_scale=2.0,
    )


def _interaction(
    timestamp_s: float,
    *,
    valid: bool = True,
    rotation: tuple[float, float] = (0.0, 0.0),
    scale_delta: float = 0.0,
) -> InteractionState:
    return InteractionState(
        run_id="u4-scene-test",
        frame_id=0,
        timestamp_s=timestamp_s,
        interaction_valid=valid,
        pointer_xy=(0.5, 0.5) if valid else None,
        pinch_ratio=0.3 if valid else None,
        pinch_active=False,
        rotation_delta=rotation,
        scale_delta=scale_delta,
    )


class _FrameRenderer:
    def __init__(self) -> None:
        self.opened = False
        self.closed = False
        self.frames: list[SceneFrame] = []

    def open(self) -> None:
        self.opened = True

    def render(self, frame: SceneFrame) -> None:
        self.frames.append(frame)

    def close_requested(self) -> bool:
        return False

    def close(self) -> None:
        self.closed = True


def test_tier1_scene_package_has_stable_order_and_complete_metadata() -> None:
    registry = build_tier1_scene_registry(
        initial_scale=1.0,
        min_scale=0.5,
        max_scale=2.0,
    )

    assert tuple(scene.id for scene in registry.scenes) == (
        "coordinate-geometry",
        "molecule",
        "orbital-system",
    )
    assert len({scene.id for scene in registry.scenes}) == 3
    assert registry.initial_scene_id == "coordinate-geometry"
    for scene in registry.scenes:
        metadata = scene.metadata
        assert isinstance(metadata, SceneMetadata)
        assert metadata.scene_id == scene.id
        assert metadata.title == scene.title
        assert metadata.category == scene.category
        assert metadata.description.strip()
        assert metadata.educational_topic.strip()
        assert metadata.interaction_hint.strip()


def test_coordinate_geometry_scene_renders_axes_grid_and_resets() -> None:
    registry = build_tier1_scene_registry(
        initial_scale=1.0,
        min_scale=0.5,
        max_scale=2.0,
    )
    scene = registry.get("coordinate-geometry")
    renderer = _FrameRenderer()
    extension = Stem3DExtension(
        scene_registry=registry,
        renderer=renderer,
    )
    extension.open()
    initial = renderer.frames[-1]

    extension.consume(
        _interaction(
            0.0,
            rotation=(0.2, -0.1),
            scale_delta=0.25,
        )
    )
    changed = renderer.frames[-1]
    assert changed.scene_id == "coordinate-geometry"
    assert changed.transform.yaw_rad == pytest.approx(0.2)
    assert changed.transform.pitch_rad == pytest.approx(-0.1)
    assert changed.transform.scale == pytest.approx(1.25)
    assert len(changed.lines) >= 30
    assert len(changed.spheres) >= 4
    assert any(line.color == (1.0, 0.32, 0.28) for line in changed.lines)
    assert any(line.color == (0.32, 0.88, 0.5) for line in changed.lines)
    assert any(line.color == (0.32, 0.58, 1.0) for line in changed.lines)
    assert any(sphere.center == (0.0, 0.0, 0.0) for sphere in changed.spheres)

    extension.reset()
    reset_frame = renderer.frames[-1]
    assert reset_frame.transform == initial.transform
    assert reset_frame.lines == initial.lines
    assert reset_frame.spheres == initial.spheres
    extension.close()


def _angle_degrees(
    vertex: tuple[float, float, float],
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> float:
    a = tuple(value - origin for value, origin in zip(first, vertex, strict=True))
    b = tuple(value - origin for value, origin in zip(second, vertex, strict=True))
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(value * value for value in a))
    norm_b = math.sqrt(sum(value * value for value in b))
    return math.degrees(math.acos(dot / (norm_a * norm_b)))


def test_molecule_presets_have_valid_deterministic_geometry() -> None:
    water = MOLECULE_PRESETS["H2O"]
    methane = MOLECULE_PRESETS["CH4"]

    assert water.name == "Water"
    assert water.formula == "H2O"
    assert len(water.atoms) == 3
    assert len(water.bonds) == 2
    assert _angle_degrees(
        water.atoms[0].position,
        water.atoms[1].position,
        water.atoms[2].position,
    ) == pytest.approx(104.5)

    assert methane.name == "Methane"
    assert methane.formula == "CH4"
    assert len(methane.atoms) == 5
    assert len(methane.bonds) == 4
    methane_angles = tuple(
        _angle_degrees(
            methane.atoms[0].position,
            methane.atoms[first].position,
            methane.atoms[second].position,
        )
        for first in range(1, 5)
        for second in range(first + 1, 5)
    )
    assert methane_angles == pytest.approx((109.47,) * 6, abs=0.01)

    for preset in (water, methane):
        assert all(atom.radius > 0.0 for atom in preset.atoms)
        assert all(
            all(math.isfinite(component) for component in atom.position)
            for atom in preset.atoms
        )
        assert all(
            0 <= bond.atom_a < len(preset.atoms)
            and 0 <= bond.atom_b < len(preset.atoms)
            for bond in preset.bonds
        )


def test_molecule_scene_switches_presets_interacts_and_resets() -> None:
    scene = MolecularGeometryScene(_scene_state())
    scene.activate()
    initial_frame = scene.frame
    assert initial_frame.title.endswith("Water (H2O)")
    assert len(initial_frame.spheres) == 3
    assert len(initial_frame.lines) == 2

    original_interaction = _interaction(
        0.0,
        rotation=(0.1, 0.2),
        scale_delta=0.2,
    )
    scene.apply_interaction(original_interaction)
    assert scene.transform.yaw_rad == pytest.approx(0.1)
    assert scene.transform.scale == pytest.approx(1.2)

    scene.select_preset("ch4")
    methane_frame = scene.frame
    assert methane_frame.title.endswith("Methane (CH4)")
    assert len(methane_frame.spheres) == 5
    assert len(methane_frame.lines) == 4
    assert len({sphere.color for sphere in methane_frame.spheres}) == 2

    scene.reset()
    assert scene.preset_key == "H2O"
    assert scene.frame == initial_frame
    scene.deactivate()


@pytest.mark.parametrize(
    "scene_id",
    ("coordinate-geometry", "molecule", "orbital-system"),
)
def test_each_scene_uses_interaction_state_and_ignores_invalid_input(
    scene_id: str,
) -> None:
    registry = build_tier1_scene_registry(
        initial_scale=1.0,
        min_scale=0.5,
        max_scale=2.0,
    )
    renderer = _FrameRenderer()
    extension = Stem3DExtension(
        scene_registry=registry,
        renderer=renderer,
    )
    extension.open()
    extension.activate_scene(scene_id)
    core_state = _interaction(
        0.0,
        rotation=(0.12, -0.08),
        scale_delta=0.15,
    )
    extension.consume(core_state)
    frame = renderer.frames[-1]
    assert frame.transform.yaw_rad == pytest.approx(0.12)
    assert frame.transform.pitch_rad == pytest.approx(-0.08)
    assert frame.transform.scale == pytest.approx(1.15)

    before = frame.transform
    extension.consume(
        _interaction(
            0.05,
            valid=False,
            rotation=(4.0, 4.0),
            scale_delta=1.0,
        )
    )
    assert renderer.frames[-1].transform == before
    assert core_state.rotation_delta == (0.12, -0.08)
    assert core_state.scale_delta == 0.15
    extension.close()


def test_orbital_motion_is_deterministic_bounded_and_resettable() -> None:
    first = OrbitalSystemScene(_scene_state())
    second = OrbitalSystemScene(_scene_state())
    assert first.phase_rad == second.phase_rad == 0.0
    assert first.orbiting_position == second.orbiting_position

    first.activate()
    second.activate()
    first.update(0.4)
    first.update(0.6)
    second.update(1.0)
    assert first.phase_rad == pytest.approx(0.36)
    assert first.phase_rad == pytest.approx(second.phase_rad)
    assert first.orbiting_position == pytest.approx(second.orbiting_position)
    assert len(first.frame.lines) == 96
    assert len(first.frame.spheres) == 2

    before_invalid = first.phase_rad
    for dt_s in (-1.0, math.nan, math.inf, True, "0.1"):
        with pytest.raises(ValueError, match="finite and non-negative"):
            first.update(dt_s)  # type: ignore[arg-type]
        assert first.phase_rad == before_invalid

    first.update(1e300)
    assert math.isfinite(first.phase_rad)
    first.reset()
    assert first.phase_rad == 0.0
    assert first.orbiting_position == (1.65, 0.0, 0.0)
    assert first.transform.yaw_rad == 0.0
    assert first.transform.pitch_rad == 0.0
    assert first.transform.scale == 1.0
    first.deactivate()
    second.deactivate()


def test_inactive_orbital_scene_does_not_advance_during_scene_switches() -> None:
    registry = build_tier1_scene_registry(
        initial_scale=1.0,
        min_scale=0.5,
        max_scale=2.0,
    )
    orbital = registry.get("orbital-system")
    renderer = _FrameRenderer()
    extension = Stem3DExtension(
        scene_registry=registry,
        renderer=renderer,
    )
    extension.open()
    extension.consume(_interaction(0.0))
    extension.activate_scene("orbital-system")
    extension.consume(_interaction(20.0))
    extension.consume(_interaction(21.0))
    phase_after_one_second = orbital.phase_rad
    assert phase_after_one_second == pytest.approx(0.36)

    extension.activate_scene("coordinate-geometry")
    extension.consume(_interaction(100.0))
    assert orbital.phase_rad == phase_after_one_second
    extension.activate_scene("orbital-system")
    extension.consume(_interaction(200.0))
    assert orbital.phase_rad == phase_after_one_second
    extension.close()


class _SelectionDashboard:
    def __init__(self) -> None:
        self.reset_action = None
        self.scene_select_action = None
        self.molecule_preset_action = None

    def set_reset_action(self, action) -> None:
        self.reset_action = action

    def set_scene_select_action(self, action) -> None:
        self.scene_select_action = action

    def set_molecule_preset_action(self, action) -> None:
        self.molecule_preset_action = action

    def wait_for_start(self, _state) -> bool:
        return True

    def stop_requested(self) -> bool:
        return False

    def consume(self, _image, _presentation, _application) -> None:
        pass

    def close(self) -> None:
        pass


def test_controller_keyboard_seams_switch_scenes_and_molecule_variant() -> None:
    registry = build_tier1_scene_registry(
        initial_scale=1.0,
        min_scale=0.5,
        max_scale=2.0,
    )
    renderer = _FrameRenderer()
    extension = Stem3DExtension(
        scene_registry=registry,
        renderer=renderer,
    )
    dashboard = _SelectionDashboard()
    controller = Stem3DApplicationController(
        run_id="u4-selection-test",
        extension=extension,
        dashboard=dashboard,  # type: ignore[arg-type]
    )

    assert controller.wait_for_start() is True
    controller.start()
    assert controller.state.active_scene == "Coordinate Geometry"

    dashboard.scene_select_action("molecule")
    assert extension.active_scene_id == "molecule"
    dashboard.molecule_preset_action("CH4")
    assert controller.state.active_scene.endswith("Methane (CH4)")
    assert renderer.frames[-1].title.endswith("Methane (CH4)")

    dashboard.scene_select_action("orbital-system")
    assert extension.active_scene_id == "orbital-system"
    assert controller.state.active_scene == "Orbital System"
    dashboard.reset_action()
    assert renderer.frames[-1].scene_id == "orbital-system"
    controller.close()
    assert controller.state.phase is ApplicationPhase.STOPPED
    assert renderer.closed is True


def test_dashboard_maps_u4_keyboard_selection_without_gui() -> None:
    selected_scenes: list[str] = []
    selected_presets: list[str] = []
    dashboard = LiveDashboard()
    dashboard.set_scene_select_action(selected_scenes.append)
    dashboard.set_molecule_preset_action(selected_presets.append)

    for key in (ord("1"), ord("2"), ord("3")):
        dashboard.handle_key(key)
    for key in (ord("h"), ord("C")):
        dashboard.handle_key(key)

    assert selected_scenes == [
        "coordinate-geometry",
        "molecule",
        "orbital-system",
    ]
    assert selected_presets == ["H2O", "CH4"]

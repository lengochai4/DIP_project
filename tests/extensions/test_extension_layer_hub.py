"""Unit tests for Extension Layer Hub and the 3 pillars."""

import pytest
import numpy as np
from app.extensions.hub.manager import ExtensionManager
from app.extensions.hub.base import ExtensionCategory

from app.extensions.interactive_3d.primitives import PrimitivesFactory
from app.extensions.interactive_3d.transforms import Quaternion, GestureTransformMapper
from app.extensions.interactive_3d.geometry_calc import RealtimeGeometryCalculator
from app.extensions.interactive_3d.surface_interaction import SurfaceInteractionManager
from app.extensions.interactive_3d.lab import InteractiveStemLab
from app.extensions.interactive_3d.module import InteractiveStemExtension

from app.extensions.presentation.slide_controller import SlideController
from app.extensions.presentation.whiteboard_ink import VirtualWhiteboardInk
from app.extensions.presentation.window_manager import WindowManagerExtension
from app.extensions.presentation.module import PresentationSupportExtension

from app.extensions.physics_2d.world import Physics2DWorld
from app.extensions.physics_2d.kinematic_hand import KinematicFingerInteraction
from app.extensions.physics_2d.vector_renderer import DynamicVectorRenderer
from app.extensions.physics_2d.experiments import PhysicsExperiments
from app.extensions.physics_2d.module import Physics2DSimulationExtension


def test_hub_manager_registration_and_lifecycle():
    manager = ExtensionManager()
    ext_3d = InteractiveStemExtension()
    ext_pres = PresentationSupportExtension()
    ext_phys = Physics2DSimulationExtension()

    manager.register(ext_3d)
    manager.register(ext_pres)
    manager.register(ext_phys)

    assert len(manager.list_modules()) == 3
    assert manager.get_module("interactive_3d_stem") is ext_3d
    assert manager.get_module("presentation_support") is ext_pres
    assert manager.get_module("physics_2d_simulation") is ext_phys

    # Enable / Disable
    assert manager.set_module_enabled("interactive_3d_stem", True)
    assert ext_3d.enabled is True
    assert ext_3d.status.active is True

    manager.set_module_enabled("interactive_3d_stem", False)
    assert ext_3d.enabled is False
    assert ext_3d.status.active is False

    manager.shutdown_all()


def test_interactive_3d_primitives():
    cube = PrimitivesFactory.create_cube(size=1.0)
    assert cube.name == "Cube"
    assert cube.vertices.shape == (8, 3)
    assert len(cube.faces) == 6

    sphere = PrimitivesFactory.create_sphere(radius=0.5, rings=6, sectors=8)
    assert sphere.name == "Sphere"
    assert len(sphere.faces) == 6 * 8

    cone = PrimitivesFactory.create_cone(radius=0.5, height=1.0, segments=12)
    assert cone.name == "Cone"
    assert len(cone.faces) == 13  # 12 sides + 1 base


def test_interactive_3d_transforms():
    mapper = GestureTransformMapper()
    # Rotation
    mapper.apply_rotation_delta(0.1, 0.0)
    assert mapper.orientation.w != 1.0 or mapper.orientation.y != 0.0

    # Translation
    mapper.apply_translation_delta(0.05, 0.05)
    assert mapper.translation[0] != 0.0

    # Zoom
    mapper.apply_pinch_zoom(0.1)
    assert mapper.scale > 1.0

    # Vertices transformation
    v = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    v_transformed = mapper.transform_vertices(v)
    assert v_transformed.shape == (2, 3)


def test_interactive_3d_geometry_calc():
    # Distance
    dist = RealtimeGeometryCalculator.distance_3d((0, 0, 0), (3, 4, 0))
    assert dist == pytest.approx(5.0)

    # Angle
    angle = RealtimeGeometryCalculator.angle_between_vectors((1, 0, 0), (0, 1, 0))
    assert angle == pytest.approx(90.0)

    # Area
    square = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
    area = RealtimeGeometryCalculator.polygon_area_2d(square)
    assert area == pytest.approx(4.0)


def test_interactive_3d_surface_interaction_and_lab():
    lab = InteractiveStemLab()
    assert lab.id == "interactive_stem"
    geom = lab.geometry()
    assert len(geom.faces) > 0
    assert len(geom.lines) > 0

    # Touch surface
    lab.set_touch_point((0.0, 0.0, 0.4))
    geom_touch = lab.geometry()
    assert geom_touch is not None

    # Change preset
    lab.set_preset("Sphere")
    assert lab.preset == "Sphere"


def test_presentation_slide_controller():
    ctrl = SlideController(cooldown_seconds=0.1)
    # Simulate swipe right (positive horizontal velocity)
    action1 = ctrl.process((0.2, 0.5), "POINT", 1.0)
    action2 = ctrl.process((0.8, 0.5), "POINT", 1.05)  # dx=0.6, dt=0.05 -> vel=12.0
    assert action2 == "NEXT_SLIDE"


def test_presentation_whiteboard_ink():
    ink = VirtualWhiteboardInk()
    # Pinch to draw
    drawing = ink.process((0.5, 0.5), is_pinching=True, screen_size=(1920, 1080))
    assert drawing is True
    assert len(ink.current_stroke) == 1

    # Release pinch
    drawing = ink.process((0.6, 0.6), is_pinching=False, screen_size=(1920, 1080))
    assert drawing is False
    assert len(ink.stroke_history) == 1


def test_presentation_window_manager():
    win_mgr = WindowManagerExtension(hold_duration=0.5)
    action1 = win_mgr.process("OPEN_PALM", 1.0)
    assert action1 is None
    action2 = win_mgr.process("OPEN_PALM", 1.6)
    assert action2 == "WINDOW_SWITCHED"


def test_physics_2d_simulation():
    world = Physics2DWorld(width=800, height=600, gravity=900.0)
    c = world.spawn_circle(400, 100, radius=20.0)
    b = world.spawn_box(400, 200, size=(30.0, 30.0))
    assert len(world.bodies) == 2

    # Step simulation
    world.step(1.0 / 60.0)
    world.step(1.0 / 60.0)
    assert c.position.y > 100.0  # Fell under gravity

    # Kinematic finger interaction
    finger = KinematicFingerInteraction(world.space, radius=25.0)
    finger.update_position((400, 250), dt=1.0 / 60.0)
    assert finger.body.position.x == 400

    # Vector renderer
    renderer = DynamicVectorRenderer()
    renderer.record_step(world.bodies)
    assert len(renderer.trajectories) == 2

    # Experiments
    PhysicsExperiments.setup_elastic_collision(world)
    assert len(world.bodies) == 2
    PhysicsExperiments.setup_pendulum(world)
    assert len(world.bodies) == 1

    # Hand gravity adjustment
    g = PhysicsExperiments.adjust_gravity_by_hand(world, 0.1)
    assert g <= 0.0

    finger.remove()
    world.clear_bodies()
    assert len(world.bodies) == 0

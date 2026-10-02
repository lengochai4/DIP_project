from dataclasses import replace
import math
import numpy as np
import pytest
from app.config import ProductConfig
from app.extensions.registry import ExtensionRegistry
from app.extensions.labs import SurfaceLab, VectorLab, OpticsLab
from app.interaction.contracts import GestureIntent as Intent, IntentType as Type, Phase


@pytest.mark.parametrize(
    "key",
    [
        "coordinate",
        "molecule",
        "orbital",
        "vector",
        "surface",
        "wave",
        "vector-field",
        "optics",
        "crystal",
    ],
)
def test_every_extension_runs_all_presets_both_modes_without_tracking(key):
    r = ExtensionRegistry(ProductConfig())
    lab = r.select(key)
    assert lab.active and lab.supports_hand_anchor
    for preset in lab.presets:
        lab.set_preset(preset)
        lab.update(0.1)
        geometry = lab.render()
        assert geometry.lines or geometry.balls
        assert all(
            math.isfinite(v)
            for line in geometry.lines
            for p in (line.a, line.b)
            for v in p
        )
        assert all(
            math.isfinite(v) for b in geometry.balls for v in (*b.center, b.radius)
        )
    lab.reset()
    assert lab.time == 0 and lab.scale == 1
    r.close()
    assert not lab.active


def test_point_never_transforms_and_cancel_ends_drag():
    lab = ExtensionRegistry(ProductConfig()).current
    original = lab.yaw, lab.pitch, lab.scale
    lab.on_intent(Intent(Type.POINT, world_or_scene_point=(0, 0, 0)))
    assert original == (lab.yaw, lab.pitch, lab.scale)
    lab.on_intent(Intent(Type.GRAB, Phase.BEGIN))
    lab.on_intent(Intent(Type.DRAG, delta_xy=(0.1, 0.2)))
    assert lab.yaw == pytest.approx(original[0] + 0.1)
    lab.on_intent(Intent(Type.CANCEL, Phase.CANCEL, validity=False))
    lab.on_intent(Intent(Type.DRAG, delta_xy=(0.8, 0.8)))
    assert lab.yaw == pytest.approx(original[0] + 0.1)


def test_construction_commit_idempotence_distance_angle_and_polygon():
    lab = ExtensionRegistry(ProductConfig()).select("coordinate")
    lab.set_tool("Angle")
    for cycle, point in enumerate(((1.0, 0, 0), (0.0, 0, 0), (0.0, 1, 0))):
        intent = Intent(
            Type.MEASURE_COMMIT, Phase.BEGIN, world_or_scene_point=point, cycle_id=cycle
        )
        lab.on_intent(intent)
        lab.on_intent(intent)
    assert len(lab.constructions) == 1 and "90.00" in " ".join(lab.measurements())
    lab.set_tool("Polygon")
    for cycle, point in enumerate(((0, 0, 0), (1, 0, 0), (1, 1, 0)), start=10):
        lab.on_intent(
            Intent(
                Type.TOOL_COMMIT,
                Phase.BEGIN,
                world_or_scene_point=point,
                cycle_id=cycle,
            )
        )
    lab.finish_polygon()
    assert lab.constructions[-1][0] == "Polygon"


@pytest.mark.parametrize("preset", SurfaceLab.presets)
def test_surface_analytic_gradient_matches_finite_difference(preset):
    lab = SurfaceLab(ProductConfig())
    lab.set_preset(preset)
    x, y, h = 0.7, -0.3, 1e-5
    gx = (lab.value(x + h, y) - lab.value(x - h, y)) / (2 * h)
    gy = (lab.value(x, y + h) - lab.value(x, y - h)) / (2 * h)
    assert lab.gradient(x, y) == pytest.approx((gx, gy), abs=1e-8)


def test_vector_math_and_snell_total_internal_reflection():
    lab = VectorLab(ProductConfig())
    u, v = lab.vectors()
    assert np.dot(np.cross(u, v), u) == pytest.approx(0.0, abs=1e-10)
    assert OpticsLab.refract(math.pi / 3, 1.5, 1.0) is None
    assert math.sin(OpticsLab.refract(0.4, 1.0, 1.5)) * 1.5 == pytest.approx(
        math.sin(0.4)
    )


def test_scale_is_relative_to_entry_and_bounded():
    lab = ExtensionRegistry(ProductConfig()).current
    lab.on_intent(Intent(Type.SCALE, Phase.BEGIN))
    lab.on_intent(Intent(Type.SCALE, scale_factor=2.0))
    lab.on_intent(Intent(Type.SCALE, scale_factor=2.0))
    assert lab.scale == 2.0
    lab.on_intent(Intent(Type.SCALE, scale_factor=1e9))
    assert lab.scale == lab.config.max_scale

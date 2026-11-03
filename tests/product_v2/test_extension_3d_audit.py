"""Closed geometry, semantic LIVE math and mode-switch orbit regressions."""

from collections import Counter
from itertools import product
import numpy as np
import pytest
from app.config import ProductConfig
from app.extensions.live_geometry import build_live_shape, render_live
from app.extensions.labs import VectorLab, MoleculeLab
from app.interaction.contracts import GestureIntent, IntentType
from app.rendering.transforms import rotation
from developer_tools.synthetic_hands import landmarks
from tests.product_v2.test_live_fingertips import live_window


def shape(points):
    return build_live_shape(
        points, tuple(f"v{i}" for i in range(len(points))), 1e-6, 1e-6
    )


def assert_closed_outward(s):
    counts = Counter(
        tuple(sorted(edge))
        for a, b, c in s.face_indices
        for edge in ((a, b), (b, c), (c, a))
    )
    assert set(counts.values()) == {2}
    p = np.asarray(s.points)
    for a, b, c in s.face_indices:
        n = np.cross(p[b] - p[a], p[c] - p[a])
        assert np.max((p - p[a]) @ n) < 1e-5


@pytest.mark.parametrize("scale", [0.1, 1, 100])
def test_cube_hull_has_closed_outward_faces_no_diagonal_edges_and_correct_volume(scale):
    points = np.asarray(list(product((-1, 1), repeat=3)), float)
    transformed = points @ rotation(0.4, 0.7).T * scale + (7, -3, 2)
    s = shape(transformed)
    assert s.solid and s.kind == "Polyhedron"
    assert len(s.face_indices) == 12 and len(s.edge_indices) == 12
    assert s.volume == pytest.approx(8 * scale**3)
    assert s.perimeter == pytest.approx(24 * scale)
    assert_closed_outward(s)


def test_tetrahedron_volume_and_all_interior_vertices_remain_observed():
    p = ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (0.1, 0.1, 0.1))
    s = shape(p)
    assert s.kind == "Tetrahedron" and s.volume == pytest.approx(1 / 6)
    assert len(s.points) == 5 and len(s.tokens) == 5
    assert len(render_live(s, 1e-6).balls) == 5
    assert all(4 not in face for face in s.face_indices)
    assert_closed_outward(s)


@pytest.mark.parametrize("seed", range(8))
def test_general_ten_point_hull_is_closed_and_supports_every_point(seed):
    s = shape(np.random.default_rng(seed).normal(size=(10, 3)))
    assert s.solid and len(s.points) == 10 and s.volume > 0
    assert_closed_outward(s)
    wire = render_live(s, 1e-6, fill=False)
    assert not wire.faces and len(wire.balls) == 10 and wire.lines


def test_nearly_coplanar_points_stay_surfaces_without_invented_thickness():
    s = shape(((0, 0, 0), (1, 0, 0), (1, 1, 0.001), (0, 1, 0)))
    assert not s.solid and s.volume is None
    assert s.edge_indices == () and s.face_indices == ()
    assert s.points[2][2] == 0.001


def live_intent(points, tokens):
    return GestureIntent(
        IntentType.TOOL_UPDATE,
        live_geometry=True,
        points=tuple(points),
        source_points=tuple((0.5, 0.5) for _ in points),
        source_depths=tuple(0.0 for _ in points),
        vertex_tokens=tuple(tokens),
    )


def test_live_vector_math_ignores_hidden_recorded_work_and_missing_pairs():
    lab = VectorLab(ProductConfig())
    lab.live_enabled = True
    lab.activate()
    lab.constructions = [("Vector", ((0, 0, 0), (99, 99, 99)))]
    assert lab.vectors() == (None, None)
    lab.on_intent(live_intent(((0, 0, 0), (1, 2, 3)), ("a", "b")))
    u, v = lab.vectors()
    assert u == pytest.approx((1, 2, 3)) and v is None
    assert "unavailable" in " ".join(lab.inspect())
    points = ((0, 0, 0), (1, 0, 0), (0, 0, 0), (0, 1, 0))
    lab.on_intent(live_intent(points, ("a", "b", "c", "d")))
    u, v = lab.vectors()
    assert np.cross(u, v) == pytest.approx((0, 0, 1))
    # A new boundary order does not change semantic vector pairs or the probe.
    order = (2, 0, 3, 1)
    lab.on_intent(
        live_intent(tuple(points[i] for i in order), tuple("abcd"[i] for i in order))
    )
    assert lab.preview == points[0]
    assert lab.vectors()[0] == pytest.approx(u)
    assert lab.vectors()[1] == pytest.approx(v)


def test_live_orbit_survives_recorded_construction_tool_switch(live_window):
    window, _ = live_window
    window.set_preference("geometry_mode", "RECORDED")
    window.choose_tool("Distance")
    window.set_preference("geometry_mode", "LIVE")
    before = window.registry.current.yaw
    window.manual("begin", (0.5, 0.5))
    window.manual("drag", (0.2, 0.1))
    window.manual("release", ())
    assert window.registry.current.yaw == pytest.approx(before + 0.2)
    assert not window._manual_active and not window.registry.current.dragging


def test_actual_fingertip_pipeline_can_form_closed_four_point_shape(live_window):
    window, feed = live_window
    hand = landmarks({1, 2, 3, 4}, tip_depths=(0, 0.05, -0.05, 0.05, -0.05))
    feed({"Right": hand})
    s = feed({"Right": hand})
    assert len(s.points) == 4 and s.solid and s.kind == "Tetrahedron"
    assert_closed_outward(s)
    projected = [window.viewport.projection().project(p)[:2] for p in s.points]
    expected = [
        np.array(window.viewport.fingertip_pointer(p))
        * (window.viewport.width(), window.viewport.height())
        for p in window.viewport.live_sources
    ]
    assert np.asarray(projected) == pytest.approx(np.asarray(expected))


def test_labels_follow_semantic_vertices_when_outline_order_changes():
    points = ((0, 0, 0), (1, 0, 0), (0, 1, 0))
    before = build_live_shape(points, ("a", "b", "c"), 1e-6, 1e-6)
    after = build_live_shape(tuple(reversed(points)), ("c", "b", "a"), 1e-6, 1e-6)
    labels = lambda s: {ball.label: ball.center for ball in render_live(s, 1e-6).balls}
    assert labels(before) == labels(after)


def test_inspector_prioritizes_lab_values_and_diagnostics_are_optional(live_window):
    window, feed = live_window
    window.select_lab("molecule")
    hands = {"Right": landmarks(set(range(5)))}
    feed(hands)
    feed(hands)
    text = window.inspector_text.toPlainText()
    assert (
        text.index("Bond") < text.index("Live fingertips")
        and "Live vertex XYZ" not in text
    )
    window.set_preference("diagnostics", True)
    feed(hands)
    feed(hands)
    text = window.inspector_text.toPlainText()
    assert text.index("Bond") < text.index("Live vertex XYZ")


@pytest.mark.parametrize("preset", ["CH4", "H2O", "CO2", "NH3"])
def test_molecular_dimensionality_is_honest_about_planar_presets(preset):
    lab = MoleculeLab(ProductConfig())
    lab.set_preset(preset)
    assert ("Planar" in lab.dimensionality) == (preset in {"H2O", "CO2"})


def test_nh3_illustration_matches_documented_reference_angle():
    lab = MoleculeLab(ProductConfig())
    lab.set_preset("NH3")
    atoms, _ = lab.atoms()
    vectors = [np.array(atom.center) - atoms[0].center for atom in atoms[1:]]
    angles = [
        np.degrees(
            np.arccos(
                np.dot(vectors[a], vectors[b])
                / (np.linalg.norm(vectors[a]) * np.linalg.norm(vectors[b]))
            )
        )
        for a, b in ((0, 1), (0, 2), (1, 2))
    ]
    assert angles == pytest.approx([106.7] * 3)
    assert not np.allclose([atom.center[1] for atom in atoms], 0)

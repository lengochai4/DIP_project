"""Full-hand live geometry: actual classifier -> exclusive intent -> GUI/render."""

from dataclasses import replace
from itertools import combinations
import numpy as np
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from app.config import ProductConfig, Settings
from app.interaction.hand_geometry import describe
from app.interaction.engine import IntentEngine
from app.interaction.contracts import IntentType, Owner
from app.extensions.live_geometry import build_live_shape, render_live
from app.rendering.transforms import Projection, rotation
from app.ui.shell import ProductWindow
from developer_tools.synthetic_hands import landmarks
from dip_touchless.core import (
    FramePacket,
    ColorSpace,
    TrackingFrame,
    TrackingStatus,
    MeasurementQuality,
    FilterDiagnostics,
    FilterMode,
    StageTimings,
)

C = ProductConfig()
TIPS = (4, 8, 12, 16, 20)


SUBSETS = [set(p) for n in range(1, 6) for p in combinations(range(5), n)]


@pytest.mark.parametrize("extended", SUBSETS)
@pytest.mark.parametrize("role", ["DOMINANT", "SUPPORT"])
def test_every_finger_subset_qualifies_geometry_in_either_role(extended, role):
    lm = landmarks(extended)
    h = describe(lm, 640, 480, C, track_id="hand", role=role)
    assert h.fingers == tuple(i in extended for i in range(5))
    assert len(h.tip_samples) == 5
    e = IntentEngine(C)
    e.update([h], ("run", 0, 1), settings=Settings(), fingertip_geometry=True)
    intent = e.update(
        [h], ("run", 1, 1.1), settings=Settings(), fingertip_geometry=True
    )
    assert intent.type is IntentType.TOOL_UPDATE and intent.owner is Owner.TOOL
    assert intent.live_geometry and len(intent.source_points) == len(extended)
    assert intent.source_points == tuple(
        (lm[TIPS[i]].x, lm[TIPS[i]].y) for i in sorted(extended)
    )
    assert intent.source_depths == tuple(
        s.relative_z for s in h.tip_samples if s.extended
    )
    assert all(p.reference is None for p in e.pinches.values())
    assert e.active is None


@pytest.fixture
def live_window(tmp_path, monkeypatch):
    import app.ui.shell as shell

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(shell, "ROOT", tmp_path)
    monkeypatch.setattr(
        QApplication, "applicationState", lambda: Qt.ApplicationState.ApplicationActive
    )
    window = ProductWindow(
        C, Settings(), software=True, preferences_path=tmp_path / "preferences.json"
    )
    app.applicationStateChanged.disconnect(window._application_state)
    window.show()
    window.navigate("Explore")
    window.select_lab("coordinate")
    app.processEvents()
    i = 0

    def feed(hands, *, valid=True, run="live", dt=0.1):
        nonlocal i
        feed.timestamp += dt
        packet = FramePacket(
            run,
            i,
            feed.timestamp,
            np.full((480, 640, 3), 25, np.uint8),
            ColorSpace.BGR,
            "synthetic",
        )
        frame = TrackingFrame(
            run,
            i,
            feed.timestamp,
            TrackingStatus.VALID,
            (),
            (),
            MeasurementQuality.unavailable(),
            None,
            None,
            FilterDiagnostics(
                FilterMode.RAW, None, None, None, None, None, None, None, False
            ),
            StageTimings(0, 0, 0, 0, 0),
            (),
        )
        window.consume(
            packet, frame, None, hands, valid, "TRACKING" if valid else "NO_HAND"
        )
        app.processEvents()
        i += 1
        return window.registry.current.live_shape

    feed.timestamp = 1.0
    yield window, feed
    window.close()
    app.processEvents()


@pytest.mark.parametrize("mode", ["WORLD", "HAND"])
def test_all_tips_realign_after_guidance_and_workspace_resize(live_window, mode):
    window, feed = live_window
    window.set_mode(mode)
    hands = {
        "Right": landmarks(set(range(5)), center=0.7),
        "Left": landmarks(set(range(5)), center=0.25),
    }
    transitions = (
        lambda: window.show_guide(False),
        lambda: window.set_expanded(True),
        lambda: window.show_guide(True),
        lambda: window.set_expanded(False),
    )
    for transition in transitions:
        transition()
        QApplication.instance().processEvents()
        feed(hands)
        shape = feed(hands)
        assert shape is not None and len(shape.points) == 10
        projected = np.array(
            [window.viewport.projection().project(p)[:2] for p in shape.points]
        )
        expected = np.array(
            [
                np.array(window.viewport.fingertip_pointer(p))
                * (window.viewport.width(), window.viewport.height())
                for p in window.viewport.live_sources
            ]
        )
        assert projected == pytest.approx(expected)
        assert not window.registry.current.constructions


@pytest.mark.parametrize("mode", ["WORLD", "HAND"])
@pytest.mark.parametrize("count", range(1, 11))
def test_one_to_ten_vertices_build_automatically_without_commits(
    live_window, mode, count
):
    window, feed = live_window
    window.set_mode(mode)
    hands = {"Right": landmarks(set(range(min(count, 5))), center=0.7, slope=0.1)}
    if count > 5:
        hands["Left"] = landmarks(set(range(count - 5)), center=0.25, slope=-0.1)
    feed(hands)
    shape = feed(hands)
    assert shape is not None and len(shape.points) == count
    planar_kind = {
        1: "Point",
        2: "Distance",
        3: "Triangle",
        4: "Quadrilateral",
    }.get(count, "Polygon")
    assert (
        shape.kind == ("Tetrahedron" if count == 4 else "Polyhedron")
        if shape.solid
        else shape.kind == planar_kind
    )
    assert (
        window.registry.current.points == []
        and window.registry.current.constructions == []
    )
    assert not window.tool_actions.isVisible() and not window.commit_button.isVisible()
    assert not window.tool_select.isVisible()
    assert len(window.viewport.live_sources) == count
    assert window.engine.active is None
    # Every semantic vertex projects back onto one of the actual displayed tips,
    # including relative depth relief and mirrored letterboxing.
    projected = np.array(
        [window.viewport.projection().project(p)[:2] for p in shape.points]
    )
    expected = [
        np.array(window.viewport.fingertip_pointer(p))
        * (window.viewport.width(), window.viewport.height())
        for p in window.viewport.live_sources
    ]
    for xy in expected:
        assert np.min(np.linalg.norm(projected - xy, axis=1)) < 1e-6
    assert (
        np.ptp((window.viewport.projection().matrix @ np.asarray(shape.points).T)[2])
        > 0
        if count > 1
        else True
    )
    previous = shape
    feed(hands)
    assert window.registry.current.live_shape.points == previous.points
    window.commit_point()
    assert window.registry.current.constructions == []


def test_pinky_motion_updates_its_vertex_and_folded_tip_is_removed(live_window):
    window, feed = live_window
    window.set_mode("HAND")
    original = landmarks(set(range(5)))
    feed({"Right": original})
    shape = feed({"Right": original})
    token = "vertex:Right:4"
    before = dict(zip(shape.tokens, shape.points))[token]
    moved = list(original)
    moved[20] = replace(moved[20], x=moved[20].x + 0.005)
    shape = feed({"Right": tuple(moved)})
    assert (
        len(shape.points) == 5
        and dict(zip(shape.tokens, shape.points))[token] != before
    )
    shape = feed({"Right": landmarks({0, 1, 2, 3})})
    assert len(shape.points) == 4 and token not in shape.tokens


def test_support_only_hand_needs_no_dominant_or_calibration(live_window):
    window, feed = live_window
    window.set_mode("HAND")
    hands = {"Left": landmarks({2, 3, 4})}
    feed(hands)
    assert len(feed(hands).points) == 3
    assert "No Add point/pinch" in window.interaction_hint.text()


@pytest.mark.parametrize(
    "loss", ["invalid", "no_hands", "folded", "gap", "run", "modal", "ui", "lab"]
)
def test_live_geometry_does_not_survive_loss_or_context_takeover(
    live_window, monkeypatch, loss
):
    window, feed = live_window
    window.set_mode("HAND")
    hands = {
        "Right": landmarks(set(range(5))),
        "Left": landmarks(set(range(5)), center=0.2),
    }
    feed(hands)
    assert len(feed(hands).points) == 10
    if loss == "invalid":
        feed(hands, valid=False)
    elif loss == "no_hands":
        feed({})
    elif loss == "folded":
        feed({key: landmarks(set()) for key in hands})
    elif loss == "gap":
        feed(hands, dt=1)
    elif loss == "run":
        feed(hands, run="different")
    elif loss == "modal":
        monkeypatch.setattr(QApplication, "activeModalWidget", lambda: object())
        feed(hands)
    elif loss == "ui":
        window.set_ui_control(True)
    else:
        window.select_lab("molecule")
    assert window.registry.current.live_shape is None
    assert window.viewport.live_sources == ()
    assert not window.export_button.isEnabled()


@pytest.mark.parametrize("depth", [-2, -0.2, 0, 0.5, 2])
def test_visual_depth_round_trip_remains_camera_aligned(depth):
    p = Projection(900, 600, (350, 320), 120, rotation(0.7, -0.4, 0.5), 8)
    xy = (0.3, 0.65)
    point = p.point_at_view_depth(xy, depth)
    assert point is not None
    assert p.project(point)[:2] == pytest.approx((xy[0] * p.width, xy[1] * p.height))
    assert (p.matrix @ point)[2] == pytest.approx(depth)


def test_auto_shapes_preserve_degeneracy_and_do_not_force_rectangles():
    square = ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0))
    tokens = tuple("abcd")
    assert build_live_shape(square, tokens, 1e-6, 1e-6).kind == "Rectangle"
    skew = (*square[:3], (0.2, 1, 0.3))
    assert build_live_shape(skew, tokens, 1e-6, 1e-6).kind == "Tetrahedron"
    line = build_live_shape(((0, 0, 0), (1, 0, 0), (2, 0, 0)), tuple("abc"), 1e-6, 1e-6)
    assert line.degenerate and not render_live(line, 1e-6).faces
    assert len(render_live(line, 1e-6).balls) == 3


def test_default_and_old_preferences_select_live_geometry(tmp_path):
    path = tmp_path / "old.json"
    path.write_text('{"engine": "PRODUCT", "dominant_hand": "Right"}')
    assert Settings().geometry_mode == Settings.load(path).geometry_mode == "LIVE"


def test_concave_outline_surface_does_not_cross_its_boundary():
    points = ((2, 0, 0), (0.5, 0.5, 0), (0, 2, 0), (-2, 0, 0), (0, -2, 0), (1, -1, 0))
    shape = build_live_shape(points, tuple("abcdef"), 1e-6, 1e-6)
    geometry = render_live(shape, 1e-6)
    p = np.asarray(points)
    polygon_area = (
        abs(np.sum(p[:, 0] * np.roll(p[:, 1], -1) - p[:, 1] * np.roll(p[:, 0], -1))) / 2
    )
    surface_area = sum(
        np.linalg.norm(np.cross(np.array(face.b) - face.a, np.array(face.c) - face.a))
        / 2
        for face in geometry.faces
    )
    assert surface_area == pytest.approx(polygon_area)
    assert len(geometry.balls) == 6  # Rendering centre is not an extra fingertip.


@pytest.mark.parametrize(
    "lab_id",
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
def test_all_labs_receive_all_ten_semantic_vertices(live_window, lab_id):
    window, feed = live_window
    window.select_lab(lab_id)
    window.set_mode("HAND")
    hands = {
        "Left": landmarks(set(range(5)), center=0.25, slope=0.1),
        "Right": landmarks(set(range(5)), center=0.75, slope=-0.1),
    }
    feed(hands)
    shape = feed(hands)
    assert shape is not None and len(shape.points) == 10
    geometry = window.registry.current.constructed()
    assert len(geometry.balls) == 10 and len(geometry.lines) >= 6
    assert bool(geometry.faces) == window.registry.current.live_surface_overlay
    assert "10 live vertices" in window.inspector_text.toPlainText()


@pytest.mark.parametrize("count", [1, 3, 10])
def test_export_freezes_live_scene_before_modal_cancels_it(
    live_window, tmp_path, monkeypatch, count
):
    from PySide6.QtWidgets import QFileDialog
    import csv
    import json

    window, feed = live_window
    hands = {"Right": landmarks(set(range(min(count, 5))), center=0.7)}
    if count > 5:
        hands["Left"] = landmarks(set(range(count - 5)), center=0.25)
    feed(hands)
    before = feed(hands)
    path = tmp_path / "live.csv"

    def dialog(*args):
        assert window.registry.current.live_shape is None
        return str(path), "CSV"

    monkeypatch.setattr(QFileDialog, "getSaveFileName", dialog)
    window.export_measurements()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1 and len(json.loads(rows[0]["points_scene_xyz"])) == count
    assert np.array(json.loads(rows[0]["points_scene_xyz"])) == pytest.approx(
        np.array(before.points)
    )
    assert "vertex:" not in path.read_text(encoding="utf-8-sig")
    if count == 1:
        assert rows[0]["distance_scene_units"] == rows[0]["vector_scene_xyz"] == ""


def test_out_of_image_active_tip_cancels_whole_geometry_instead_of_partial_shape():
    h = describe(landmarks(set(range(5))), 640, 480, C)
    samples = list(h.tip_samples)
    samples[4] = replace(samples[4], xy=(1.2, 0.5))
    h = replace(h, tip_samples=tuple(samples))
    e = IntentEngine(C)
    e.update([h], ("run", 0, 1), settings=Settings(), fingertip_geometry=True)
    intent = e.update(
        [h], ("run", 1, 1.1), settings=Settings(), fingertip_geometry=True
    )
    assert (
        intent.type is IntentType.CANCEL
        and not intent.points
        and not intent.source_points
    )


def test_geometry_mode_switch_cancels_before_recorded_controls_appear(live_window):
    window, feed = live_window
    hands = {"Right": landmarks(set(range(5)))}
    feed(hands)
    assert feed(hands) is not None
    window.set_preference("geometry_mode", "RECORDED")
    assert (
        window.registry.current.live_shape is None
        and not window.registry.current.live_enabled
    )
    assert window.viewport.live_sources == () and not window.tool_select.isHidden()
    window.set_preference("geometry_mode", "LIVE")
    assert window.registry.current.live_enabled and not window.tool_select.isVisible()
    feed(hands)
    assert feed(hands) is not None

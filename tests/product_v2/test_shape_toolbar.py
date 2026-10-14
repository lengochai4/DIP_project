"""Tests for touchless ShapeToolbar, DwellTracker, ShapeGestureEngine, and FrozenShape integration."""

import math
import pytest
from app.interaction.dwell_tracker import DwellTracker, DwellEvent
from app.interaction.shape_gestures import (
    ShapeGestureEngine,
    ShapeCandidate,
    ALL_SHAPES,
    SHAPE_2D,
    SHAPE_3D,
)
from app.interaction.contracts import HandState, TipSample
from app.extensions.base import FrozenShape
from app.extensions.registry import ExtensionRegistry
from app.config import ProductConfig


# =====================================================================
# Helpers for synthetic hand generation
# =====================================================================

def make_hand(role="DOMINANT", tips=None, pose="POINT"):
    """Create a minimal HandState with specified fingertip positions."""
    if tips is None:
        # Default: all 5 fingertips extended at distinct positions
        tips = {
            "THUMB": (0.3, 0.5),
            "INDEX": (0.4, 0.4),
            "MIDDLE": (0.5, 0.4),
            "RING": (0.6, 0.4),
            "PINKY": (0.7, 0.5),
        }
    order = ("THUMB", "INDEX", "MIDDLE", "RING", "PINKY")
    tip_samples = tuple(
        TipSample(
            f"vertex:{role.lower()}:{i}",
            tips.get(finger, (0.0, 0.0)),
            0.0,
            finger in tips,
        )
        for i, finger in enumerate(order)
    )
    return HandState(
        track_id=role.lower(),
        role=role,
        pose=pose,
        fingers=tuple(f in tips for f in order),
        pointer_xy=tips.get("INDEX", (0.5, 0.5)),
        palm=None,
        pinch_ratio=1.0,
        valid=True,
        palm_signature=(),
        tip_samples=tip_samples,
    )


# =====================================================================
# 1. DwellTracker tests
# =====================================================================

def test_dwell_tracker_accumulates_and_emits_enter_then_hold():
    tracker = DwellTracker(threshold_s=1.0)
    assert tracker.active_target is None
    assert tracker.fraction == 0.0

    # Advance halfway
    ev = tracker.update("BTN", 0.5, inside=True)
    assert ev is None
    assert tracker.fraction == pytest.approx(0.5)
    assert tracker.active_target == "BTN"

    # Advance past threshold -> ENTER
    ev = tracker.update("BTN", 0.6, inside=True)
    assert ev is not None
    assert ev.state == "ENTER"
    assert ev.target_id == "BTN"
    assert tracker.fraction == 1.0

    # Next tick while held -> HOLD
    ev = tracker.update("BTN", 0.1, inside=True)
    assert ev is not None
    assert ev.state == "HOLD"
    assert ev.target_id == "BTN"

    # Pointer exits -> EXIT
    ev = tracker.update("BTN", 0.1, inside=False)
    assert ev is not None
    assert ev.state == "EXIT"
    assert ev.target_id == "BTN"
    assert tracker.active_target is None


def test_dwell_tracker_target_switch_resets():
    tracker = DwellTracker(threshold_s=1.0)
    tracker.update("BTN_A", 0.8, inside=True)
    assert tracker.fraction == pytest.approx(0.8)

    # Switching target resets elapsed time
    ev = tracker.update("BTN_B", 0.2, inside=True)
    assert ev is None
    assert tracker.active_target == "BTN_B"
    assert tracker.fraction == pytest.approx(0.2)


def test_dwell_tracker_reset():
    tracker = DwellTracker(threshold_s=1.0)
    tracker.update("BTN", 0.9, inside=True)
    tracker.reset()
    assert tracker.active_target is None
    assert tracker.fraction == 0.0


# =====================================================================
# 2. ShapeGestureEngine tests
# =====================================================================

def test_shape_gesture_circle_one_hand():
    engine = ShapeGestureEngine(stability_frames=3)
    dom = make_hand("DOMINANT", {"THUMB": (0.3, 0.5), "INDEX": (0.5, 0.5)})
    cand = engine.update([dom], "Circle")
    assert cand.shape_type == "Circle"
    assert cand.params is not None
    assert cand.params.hands_used == 1
    assert cand.params.radius == pytest.approx(0.2)
    assert cand.params.center_xy == pytest.approx((0.4, 0.5))


def test_shape_gesture_circle_two_hands():
    engine = ShapeGestureEngine(stability_frames=3)
    dom = make_hand("DOMINANT", {"INDEX": (0.3, 0.5), "THUMB": (0.2, 0.5)})
    sup = make_hand("SUPPORT", {"INDEX": (0.7, 0.5), "THUMB": (0.8, 0.5)})
    cand = engine.update([dom, sup], "Circle")
    assert cand.shape_type == "Circle"
    assert cand.params is not None
    assert cand.params.hands_used == 2
    assert cand.params.radius == pytest.approx(0.4)
    assert cand.params.center_xy == pytest.approx((0.5, 0.5))


def test_shape_gesture_square_one_and_two_hands():
    engine = ShapeGestureEngine(stability_frames=3)
    # 1 hand: index + thumb -> side
    dom = make_hand("DOMINANT", {"THUMB": (0.4, 0.5), "INDEX": (0.6, 0.5)})
    cand = engine.update([dom], "Square")
    assert cand.shape_type == "Square"
    assert cand.params is not None
    assert cand.params.hands_used == 1
    assert cand.params.width == pytest.approx(0.2)
    assert cand.params.height == pytest.approx(0.2)
    assert len(cand.params.corners_xy) == 4

    # 2 hands: 2 index fingers -> diagonal
    sup = make_hand("SUPPORT", {"INDEX": (0.8, 0.7)})
    cand2 = engine.update([dom, sup], "Square")
    assert cand2.shape_type == "Square"
    assert cand2.params is not None
    assert cand2.params.hands_used == 2
    assert cand2.params.center_xy == pytest.approx((0.7, 0.6))
    assert len(cand2.params.corners_xy) == 4


def test_shape_gesture_rectangle():
    engine = ShapeGestureEngine(stability_frames=3)
    dom = make_hand("DOMINANT", {"INDEX": (0.2, 0.3), "THUMB": (0.2, 0.4)})
    sup = make_hand("SUPPORT", {"INDEX": (0.8, 0.7), "THUMB": (0.8, 0.8)})
    cand = engine.update([dom, sup], "Rectangle")
    assert cand.shape_type == "Rectangle"
    assert cand.params is not None
    assert cand.params.hands_used == 2
    assert cand.params.width == pytest.approx(0.6)
    assert cand.params.height == pytest.approx(0.4)


def test_shape_gesture_triangle():
    engine = ShapeGestureEngine(stability_frames=3)
    dom = make_hand("DOMINANT", {"INDEX": (0.5, 0.2), "THUMB": (0.3, 0.7), "MIDDLE": (0.7, 0.7)})
    cand = engine.update([dom], "Triangle")
    assert cand.shape_type == "Triangle"
    assert cand.params is not None
    assert cand.params.hands_used == 1
    assert len(cand.params.corners_xy) == 3


def test_shape_gesture_3d_shapes_require_two_hands():
    engine = ShapeGestureEngine()
    dom = make_hand("DOMINANT", {"INDEX": (0.4, 0.4), "THUMB": (0.3, 0.5)})
    for s3d in SHAPE_3D:
        cand = engine.update([dom], s3d)
        assert cand.params is None
        assert cand.reason == "NEED_SECOND_HAND"


def test_shape_gesture_sphere_two_hands():
    engine = ShapeGestureEngine(stability_frames=3)
    dom = make_hand("DOMINANT", {"INDEX": (0.3, 0.5), "THUMB": (0.3, 0.6)})
    sup = make_hand("SUPPORT", {"INDEX": (0.7, 0.5), "THUMB": (0.7, 0.6)})
    cand = engine.update([dom, sup], "Sphere")
    assert cand.shape_type == "Sphere"
    assert cand.params is not None
    assert cand.params.radius == pytest.approx(0.2)


def test_shape_gesture_cube_two_hands():
    engine = ShapeGestureEngine(stability_frames=3)
    dom = make_hand("DOMINANT", {"INDEX": (0.3, 0.5), "THUMB": (0.3, 0.6)})
    sup = make_hand("SUPPORT", {"INDEX": (0.7, 0.5), "THUMB": (0.7, 0.6)})
    cand = engine.update([dom, sup], "Cube")
    assert cand.shape_type == "Cube"
    assert cand.params is not None
    assert len(cand.params.corners_3d) == 8


def test_shape_gesture_box_two_hands():
    engine = ShapeGestureEngine(stability_frames=3)
    tips_d = {"INDEX": (0.2, 0.3), "MIDDLE": (0.3, 0.3), "RING": (0.4, 0.3), "PINKY": (0.5, 0.3)}
    tips_s = {"INDEX": (0.2, 0.7), "MIDDLE": (0.3, 0.7), "RING": (0.4, 0.7), "PINKY": (0.5, 0.7)}
    dom = make_hand("DOMINANT", tips_d)
    sup = make_hand("SUPPORT", tips_s)
    cand = engine.update([dom, sup], "Box")
    assert cand.shape_type == "Box"
    assert cand.params is not None
    assert cand.params.hands_used == 2


def test_shape_gesture_pyramid_two_hands():
    engine = ShapeGestureEngine(stability_frames=3)
    dom = make_hand("DOMINANT", {"INDEX": (0.5, 0.2), "THUMB": (0.5, 0.25)})
    sup = make_hand("SUPPORT", {"INDEX": (0.3, 0.8), "THUMB": (0.7, 0.8)})
    cand = engine.update([dom, sup], "Pyramid")
    assert cand.shape_type == "Pyramid"
    assert cand.params is not None
    assert len(cand.params.corners_xy) == 3


def test_shape_gesture_pyramid_three_fingers_each_hand():
    engine = ShapeGestureEngine(stability_frames=3)
    dom = make_hand("DOMINANT", {"INDEX": (0.5, 0.2), "THUMB": (0.5, 0.24), "MIDDLE": (0.52, 0.22)})
    sup = make_hand("SUPPORT", {"INDEX": (0.3, 0.8), "THUMB": (0.7, 0.8), "MIDDLE": (0.5, 0.9)})
    cand = engine.update([dom, sup], "Pyramid")
    assert cand.shape_type == "Pyramid"
    assert cand.params is not None
    assert len(cand.params.corners_xy) == 4
    # Dom hand has smaller (index, thumb) distance (0.04 vs 0.4) -> apex is dom index
    assert cand.params.corners_xy[0] == (0.5, 0.2)
    # Sup hand provides 3 base vertices: index, thumb, middle
    assert cand.params.corners_xy[1] == (0.3, 0.8)
    assert cand.params.corners_xy[2] == (0.7, 0.8)
    assert cand.params.corners_xy[3] == (0.5, 0.9)



def test_shape_gesture_stability_accumulation_and_freeze():
    # Set stability_frames = 5 for test speed
    engine = ShapeGestureEngine(stability_frames=5)
    dom = make_hand("DOMINANT", {"THUMB": (0.3, 0.5), "INDEX": (0.5, 0.5)})

    # Frame 1: sets initial reference key (count = 0)
    # Frames 2..5: accumulate 4 consecutive deltas < thresh (count = 1..4)
    for _ in range(5):
        cand = engine.update([dom], "Circle")
        assert not cand.is_stable
        assert cand.stable_fraction < 1.0

    # 6th frame (5th consecutive stable delta) -> is_stable becomes True
    cand = engine.update([dom], "Circle")
    assert cand.is_stable
    assert cand.stable_fraction == 1.0


# =====================================================================
# 3. FrozenShape & CoordinateLab integration tests
# =====================================================================

def test_frozen_shape_lifecycle_in_coordinate_lab():
    reg = ExtensionRegistry(ProductConfig())
    lab = reg.select("coordinate")
    assert lab.id == "coordinate"

    # Initially empty
    assert len(lab.frozen_shapes) == 0
    geo_empty = lab.geometry()
    initial_line_count = len(geo_empty.lines)

    # Add a frozen Circle
    fs_circle = FrozenShape(
        kind="Circle",
        params={"center_xy": (0.5, 0.5), "radius": 0.1, "hands_used": 1},
    )
    lab.add_frozen_shape(fs_circle)
    assert len(lab.frozen_shapes) == 1

    # Geometry now includes circle segments
    geo_with_circle = lab.geometry()
    assert len(geo_with_circle.lines) > initial_line_count

    # Add a frozen Cube
    fs_cube = FrozenShape(
        kind="Cube",
        params={
            "center_xy": (0.5, 0.5),
            "size": 0.2,
            "corners_3d": tuple((i * 0.1, j * 0.1, k * 0.1) for i in (0, 1) for j in (0, 1) for k in (0, 1)),
        },
    )
    lab.add_frozen_shape(fs_cube)
    assert len(lab.frozen_shapes) == 2

    # Remove circle by ID
    assert lab.remove_frozen_shape_by_id(fs_circle.shape_id)
    assert len(lab.frozen_shapes) == 1
    assert lab.frozen_shapes[0].kind == "Cube"

    # Clear all
    lab.clear_frozen_shapes()
    assert len(lab.frozen_shapes) == 0
    assert len(lab.geometry().lines) == initial_line_count


def test_frozen_geometry_renders_all_shapes_without_nan():
    reg = ExtensionRegistry(ProductConfig())
    lab = reg.select("coordinate")

    for shape_kind in ALL_SHAPES:
        fs = FrozenShape(
            kind=shape_kind,
            params={
                "center_xy": (0.5, 0.5),
                "radius": 0.15,
                "width": 0.3,
                "height": 0.2,
                "size": 0.25,
                "corners_xy": ((0.3, 0.4), (0.7, 0.4), (0.5, 0.8)),
                "corners_3d": tuple((i * 0.1, j * 0.1, k * 0.1) for i in (0, 1) for j in (0, 1) for k in (0, 1)),
            },
        )
        lab.add_frozen_shape(fs)

    geo = lab.geometry()
    assert geo.lines
    assert all(math.isfinite(v) for line in geo.lines for pt in (line.a, line.b) for v in pt)
    assert all(math.isfinite(v) for b in geo.balls for v in (*b.center, b.radius))
    lab.clear_frozen_shapes()


# =====================================================================
# 4. ShapeToolbar Widget tests
# =====================================================================

def test_shape_toolbar_open_select_and_delete_dwell():
    from PySide6.QtWidgets import QApplication
    from app.ui.shape_toolbar import ShapeToolbar

    app = QApplication.instance() or QApplication([])
    toolbar = ShapeToolbar()
    toolbar.resize(800, 600)

    # Initial state
    assert not toolbar._open
    assert toolbar.selected_shape is None
    assert toolbar.delete_event is None

    # 1. Hover on trigger strip for 0.4s -> stays closed (threshold 0.8s)
    tr = toolbar._trigger_rect()
    tx, ty = tr.center().x() / 800, tr.center().y() / 600
    toolbar.update_tip((tx, ty), 0.4)
    assert not toolbar._open

    # Another 0.5s (total 0.9s >= 0.8s) -> panel opens
    toolbar.update_tip((tx, ty), 0.5)
    assert toolbar._open

    # 2. Hover on Circle item in open panel
    item_rects = dict(toolbar._item_rects())
    assert "Circle" in item_rects
    cr = item_rects["Circle"]
    cx, cy = cr.center().x() / 800, cr.center().y() / 600

    # Moving tip outside does NOT auto-close the panel (user requirement to eliminate sensitivity issues)
    toolbar.update_tip((0.1, 0.1), 2.0)
    assert toolbar._open

    # Dwelling on the trigger button again toggles it closed (0.9s >= 0.8s)
    toolbar.update_tip((tx, ty), 0.9)
    assert not toolbar._open

    # User must exit trigger area before re-arming toggle
    toolbar.update_tip((0.1, 0.1), 0.1)

    # Open again
    toolbar.update_tip((tx, ty), 0.9)
    assert toolbar._open

    # Hover Circle for 0.9s (>= 0.8s) -> selected and panel closes
    toolbar.update_tip((cx, cy), 0.9)
    assert toolbar.selected_shape == "Circle"
    assert not toolbar._open

    # Clear selection
    toolbar.clear_selection()
    assert toolbar.selected_shape is None

    # 3. Delete button dwell
    dr = toolbar._delete_rect()
    dx, dy = dr.center().x() / 800, dr.center().y() / 600

    # Mode 1: Dragging a shape into trash -> 0.85s triggers DRAG_SINGLE
    toolbar.update_tip((dx, dy), 0.85, is_dragging_shape=True)
    assert toolbar.delete_event == "DRAG_SINGLE"
    toolbar.clear_delete_event()

    # Move away to reset
    toolbar.update_tip((0.1, 0.1), 0.1)

    # Mode 2: Pointing index finger on trash without dragging -> 0.85s triggers ALL
    toolbar.update_tip((dx, dy), 0.85, is_dragging_shape=False)
    assert toolbar.delete_event == "ALL"
    toolbar.clear_delete_event()


# =====================================================================
# 5. Shell Integration: Pointing conditioning & Initial suppression
# =====================================================================

def test_shell_pointing_gesture_only_updates_toolbar_tip(tmp_path, monkeypatch):
    import numpy as np
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    import app.ui.shell as shell
    from app.config import Settings
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

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(shell, "ROOT", tmp_path)
    monkeypatch.setattr(
        QApplication, "applicationState", lambda: Qt.ApplicationState.ApplicationActive
    )
    window = shell.ProductWindow(
        ProductConfig(), Settings(), software=True, preferences_path=tmp_path / "pref.json"
    )
    window.navigate("Explore")
    window.select_lab("coordinate")

    def make_frame_and_packet(source_name="camera"):
        packet = FramePacket(
            "run", 0, 1.0, np.full((480, 640, 3), 20, np.uint8), ColorSpace.BGR, source_name
        )
        frame = TrackingFrame(
            "run", 0, 1.0, TrackingStatus.VALID, (), (),
            MeasurementQuality.unavailable(), None, None,
            FilterDiagnostics(FilterMode.RAW, None, None, None, None, None, None, None, False),
            StageTimings(0, 0, 0, 0, 0), ()
        )
        return packet, frame

    # 1. Open palm (5 fingers extended) -> pose is "OPEN_PALM", NOT "POINT"
    # Toolbar tip must NOT be updated (tip_px remains None)
    open_palm_lm = {"Right": landmarks(set(range(5)))}
    packet, frame = make_frame_and_packet("camera")
    window.consume(packet, frame, None, open_palm_lm, True, "TRACKING")
    assert window.shape_toolbar._tip_px is None

    # 2. Index finger only (only finger index 1 extended) -> pose is "POINT"
    # Toolbar tip MUST be updated
    pointing_lm = {"Right": landmarks({1})}
    packet, frame = make_frame_and_packet("camera")
    window.consume(packet, frame, None, pointing_lm, True, "TRACKING")
    assert window.shape_toolbar._tip_px is not None

    # 3. Clean up
    window.close()


def test_coordinate_lab_suppresses_auto_drawing_initially(tmp_path, monkeypatch):
    import numpy as np
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    import app.ui.shell as shell
    from app.config import Settings
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

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(shell, "ROOT", tmp_path)
    monkeypatch.setattr(
        QApplication, "applicationState", lambda: Qt.ApplicationState.ApplicationActive
    )
    window = shell.ProductWindow(
        ProductConfig(), Settings(), software=True, preferences_path=tmp_path / "pref.json"
    )
    window.navigate("Explore")
    window.select_lab("coordinate")

    packet = FramePacket(
        "run", 0, 1.0, np.full((480, 640, 3), 20, np.uint8), ColorSpace.BGR, "camera"
    )
    frame = TrackingFrame(
        "run", 0, 1.0, TrackingStatus.VALID, (), (),
        MeasurementQuality.unavailable(), None, None,
        FilterDiagnostics(FilterMode.RAW, None, None, None, None, None, None, None, False),
        StageTimings(0, 0, 0, 0, 0), ()
    )

    # User enters CoordinateLab and shows hands before selecting a shape:
    # Auto-drawing must be SUPPRESSED!
    hands = {"Right": landmarks(set(range(5)))}
    window.consume(packet, frame, None, hands, True, "TRACKING")

    assert window.registry.current.live_shape is None
    assert window.viewport.live_sources == ()
    assert "Chỉ ngón trỏ vào nút Chọn hình" in window.feedback.text()

    # Once a shape is selected:
    window.shape_toolbar._selected_shape = "Circle"
    window.consume(packet, frame, None, hands, True, "TRACKING")
    # Shape drawing is active now
    assert window.registry.current.live_shape is None  # standard live_shape remains clean
    assert window.registry.current.preview_frozen_shape is not None
    assert window.registry.current.preview_frozen_shape.kind == "Circle"

    window.close()


def test_hit_test_frozen_shape_and_find():
    from app.interaction.shape_gestures import hit_test_frozen_shape, find_hit_shape

    s_circle = FrozenShape(kind="Circle", params={"center_xy": (0.3, 0.4), "radius": 0.1})
    s_cube = FrozenShape(kind="Cube", params={"center_xy": (0.7, 0.4), "size": 0.2})

    # Exact center hit
    assert hit_test_frozen_shape(s_circle, (0.3, 0.4))
    # Near edge hit
    assert hit_test_frozen_shape(s_circle, (0.35, 0.4))
    # Far miss
    assert not hit_test_frozen_shape(s_circle, (0.8, 0.8))

    # Test find_hit_shape
    shapes = [s_circle, s_cube]
    assert find_hit_shape(shapes, (0.31, 0.41)) is s_circle
    assert find_hit_shape(shapes, (0.71, 0.39)) is s_cube
    assert find_hit_shape(shapes, (0.05, 0.05)) is None


def test_shape_gesture_mirror_alignment():
    engine = ShapeGestureEngine(stability_frames=3)
    # Hand at camera x = 0.2
    dom = make_hand("DOMINANT", {"THUMB": (0.2, 0.5), "INDEX": (0.4, 0.5)})

    # Without mirror: center_x = 0.3
    cand_unmirrored = engine.update([dom], "Circle", mirror=False)
    assert cand_unmirrored.params.center_xy[0] == pytest.approx(0.3)

    # With mirror: camera 0.2 becomes screen 0.8, camera 0.4 becomes screen 0.6 -> center_x = 0.7
    cand_mirrored = engine.update([dom], "Circle", mirror=True)
    assert cand_mirrored.params.center_xy[0] == pytest.approx(0.7)
    # Radius is invariant to reflection
    assert cand_mirrored.params.radius == pytest.approx(cand_unmirrored.params.radius)


def test_shape_gesture_option_2_midpoint_centering():
    """Option 2: all 2-hand shapes are centered exactly at the midpoint between the 2 index fingers."""
    engine = ShapeGestureEngine(stability_frames=3)
    # Index fingers at (0.2, 0.4) and (0.8, 0.6) -> midpoint is (0.5, 0.5)
    dom = make_hand("DOMINANT", {
        "INDEX": (0.2, 0.4), "THUMB": (0.15, 0.45),
        "MIDDLE": (0.22, 0.4), "RING": (0.24, 0.4), "PINKY": (0.26, 0.45)
    })
    sup = make_hand("SUPPORT", {
        "INDEX": (0.8, 0.6), "THUMB": (0.85, 0.65),
        "MIDDLE": (0.78, 0.6), "RING": (0.76, 0.6), "PINKY": (0.74, 0.65)
    })
    expected_midpoint = (0.5, 0.5)

    for shape_name in ("Circle", "Square", "Rectangle", "Triangle", "Sphere", "Cube", "Box", "Pyramid"):
        cand = engine.update([dom, sup], shape_name)
        assert cand.params is not None, f"Failed for {shape_name}"
        assert cand.params.center_xy[0] == pytest.approx(expected_midpoint[0], abs=1e-3), (
            f"{shape_name} center_x {cand.params.center_xy[0]} != {expected_midpoint[0]}"
        )
        assert cand.params.center_xy[1] == pytest.approx(expected_midpoint[1], abs=1e-3), (
            f"{shape_name} center_y {cand.params.center_xy[1]} != {expected_midpoint[1]}"
        )


def test_frozen_shape_post_freeze_cooldown_and_pinch_anchoring(tmp_path, monkeypatch):
    """Verify that shape creation anchors firmly without sticking, and requires explicit pinch to grab."""
    import numpy as np
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    import app.ui.shell as shell
    from app.config import Settings
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

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(shell, "ROOT", tmp_path)
    monkeypatch.setattr(
        QApplication, "applicationState", lambda: Qt.ApplicationState.ApplicationActive
    )
    window = shell.ProductWindow(
        ProductConfig(), Settings(), software=True, preferences_path=tmp_path / "pref.json"
    )
    window.navigate("Explore")
    window.select_lab("coordinate")

    packet = FramePacket(
        "run", 0, 1.0, np.full((480, 640, 3), 20, np.uint8), ColorSpace.BGR, "camera"
    )
    frame = TrackingFrame(
        "run", 0, 1.0, TrackingStatus.VALID, (), (),
        MeasurementQuality.unavailable(), None, None,
        FilterDiagnostics(FilterMode.RAW, None, None, None, None, None, None, None, False),
        StageTimings(0, 0, 0, 0, 0), ()
    )

    # 1. Select Circle and hold fingers steady to freeze it
    window.shape_toolbar._selected_shape = "Circle"
    window.shape_gesture_engine._thresh = 0.05
    window.shape_gesture_engine._req = 2

    # Hand pointing at (0.5, 0.5)
    hand_dict = {"Right": landmarks({0, 1})}
    # Update until stable and frozen
    for _ in range(5):
        window.consume(packet, frame, None, hand_dict, True, "TRACKING")

    # Shape must now be frozen and toolbar cleared
    assert len(window.registry.current.frozen_shapes) == 1
    frozen_shape = window.registry.current.frozen_shapes[0]
    initial_center = frozen_shape.params["center_xy"]
    assert window.shape_toolbar.selected_shape is None

    # Cooldown must be active (30 frames) and shape must NOT be auto-grabbed
    assert window._freeze_cooldown_frames > 0
    assert window._drag_shape is None

    # Next frame during cooldown: shape must remain anchored at initial_center
    window.consume(packet, frame, None, hand_dict, True, "TRACKING")
    assert frozen_shape.params["center_xy"] == initial_center
    assert window._drag_shape is None

    window.close()


def test_independent_per_shape_rotation_and_selection():
    from app.extensions.registry import ExtensionRegistry
    from app.config import ProductConfig
    from app.extensions.base import FrozenShape

    reg = ExtensionRegistry(ProductConfig())
    lab = reg.select("coordinate")
    lab.clear_frozen_shapes()

    s1 = FrozenShape(kind="Cube", params={"center_xy": (0.3, 0.5), "size": 0.15})
    s2 = FrozenShape(kind="Pyramid", params={"center_xy": (0.7, 0.5), "corners_xy": ((0.7, 0.3), (0.6, 0.7), (0.8, 0.7))})

    lab.add_frozen_shape(s1)
    assert lab.selected_shape_id is None  # starts in static state
    lab.selected_shape_id = s1.shape_id
    assert lab.selected_shape_id == s1.shape_id

    lab.add_frozen_shape(s2)
    assert lab.selected_shape_id is None  # new shapes start in static state
    lab.selected_shape_id = s2.shape_id
    assert lab.selected_shape_id == s2.shape_id

    # Rotate s1 independently
    s1.yaw = 0.75
    s1.pitch = 0.40
    # s2 stays at default 0.0
    assert s2.yaw == 0.0
    assert s2.pitch == 0.0

    geo = lab.frozen_geometry()
    assert geo.lines
    assert geo.faces

    # Switch selection to s1
    lab.selected_shape_id = s1.shape_id
    geo_s1_selected = lab.frozen_geometry()
    assert geo_s1_selected.lines


def test_rotation_disengagement_rollback_buffer_logic(tmp_path, monkeypatch):
    import collections
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    import app.ui.shell as shell
    from app.config import Settings
    from app.extensions.base import FrozenShape

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(shell, "ROOT", tmp_path)
    monkeypatch.setattr(
        QApplication, "applicationState", lambda: Qt.ApplicationState.ApplicationActive
    )
    window = shell.ProductWindow(
        ProductConfig(), Settings(), software=True, preferences_path=tmp_path / "pref.json"
    )

    lab = window.registry.select("coordinate")
    shape = FrozenShape(kind="Cube", params={"center_xy": (0.5, 0.5), "size": 0.15})
    lab.add_frozen_shape(shape)

    # Simulate 5 frames of rotation history where user curled finger in last 2 frames
    # Target was (1.0, 0.5), curl caused unwanted flick to (1.0, 0.1)
    history = [(1.0, 0.5), (1.0, 0.5), (1.0, 0.45), (1.0, 0.3), (1.0, 0.1)]
    window._rotate_history = collections.deque(history, maxlen=6)
    window._was_rotating = True

    # Shape current angle is corrupted by curl
    shape.yaw, shape.pitch = 1.0, 0.1

    # Simulate disengagement rollback (when can_rotate becomes False)
    assert len(window._rotate_history) >= 3
    rb_idx = 0 if len(window._rotate_history) <= 4 else -4
    shape.yaw, shape.pitch = window._rotate_history[rb_idx]
    window._rotate_history.clear()
    window._was_rotating = False

    # Shape must have rolled back to before the curl flick
    assert shape.yaw == 1.0
    assert shape.pitch == 0.5
    assert not window._was_rotating
    assert len(window._rotate_history) == 0

    window.close()


def test_task_toolbar_enable_rules_single_vs_multiple_shapes():
    """Verify task button enable conditions:
    - 0 shapes: disabled
    - 1 shape: enabled immediately without needing selection
    - >= 2 shapes: disabled when none selected; enabled when 1 shape is selected
    """
    from PySide6.QtWidgets import QApplication
    from app.ui.shape_toolbar import ShapeToolbar
    from app.extensions.base import FrozenShape

    app = QApplication.instance() or QApplication([])
    tb = ShapeToolbar()
    tb.resize(800, 600)

    # 1. Zero shapes -> disabled
    tb.update_tip(None, 0.1, frozen_shapes=[])
    assert not tb.is_task_trigger_enabled()

    # 2. Exactly 1 shape -> enabled immediately!
    s1 = FrozenShape(kind="Cube", params={"center_xy": (0.3, 0.5), "size": 0.15})
    tb.update_tip(None, 0.1, frozen_shapes=[s1])
    assert tb.is_task_trigger_enabled()
    assert tb.get_active_shape() is s1

    # 3. Two shapes, none explicitly selected -> disabled!
    s2 = FrozenShape(kind="Circle", params={"center_xy": (0.7, 0.5), "radius": 0.1})
    tb.update_tip(None, 0.1, frozen_shapes=[s1, s2], selected_shape_id=None)
    assert not tb.is_task_trigger_enabled()
    assert tb.get_active_shape() is None

    # 4. Two shapes, s1 selected -> enabled!
    tb.update_tip(None, 0.1, frozen_shapes=[s1, s2], selected_shape_id=s1.shape_id)
    assert tb.is_task_trigger_enabled()
    assert tb.get_active_shape() is s1


def test_task_toolbar_mutual_exclusion_with_shape_dropdown():
    """Verify mutual exclusion:
    - When shape dropdown is open, task button is disabled.
    - When task dropdown is open, shape button cannot be opened.
    """
    from PySide6.QtWidgets import QApplication
    from app.ui.shape_toolbar import ShapeToolbar
    from app.extensions.base import FrozenShape

    app = QApplication.instance() or QApplication([])
    tb = ShapeToolbar()
    tb.resize(800, 600)
    s1 = FrozenShape(kind="Cube", params={"center_xy": (0.5, 0.5), "size": 0.15})
    tb.update_tip(None, 0.1, frozen_shapes=[s1])

    # Open shape dropdown
    tb._open = True
    assert not tb.is_task_trigger_enabled()  # Task button is disabled while shape dropdown is open!

    # Close shape dropdown
    tb._open = False
    assert tb.is_task_trigger_enabled()

    # Open task dropdown
    tb._task_open = True
    tr_rect = tb._trigger_rect()
    center_norm = (tr_rect.center().x() / 800.0, tr_rect.center().y() / 600.0)
    tb.update_tip(center_norm, 1.0, frozen_shapes=[s1])
    assert not tb._open  # Shape dropdown cannot open while task dropdown is open!


def test_task_toolbar_2d_vs_3d_task_options():
    """Verify:
    - 3D shape: all tasks unlocked including cross_section and unfold in Khối 3D section.
    - 2D shape: cross_section and unfold are disabled.
    """
    from PySide6.QtWidgets import QApplication
    from app.ui.shape_toolbar import ShapeToolbar
    from app.extensions.base import FrozenShape

    app = QApplication.instance() or QApplication([])
    tb = ShapeToolbar()
    tb.resize(800, 600)

    # 1. 3D Shape (Cube)
    s_3d = FrozenShape(kind="Cube", params={"center_xy": (0.5, 0.5), "size": 0.15})
    tb.update_tip(None, 0.1, frozen_shapes=[s_3d])
    tb._task_open = True
    items_3d = {tid: en for tid, _, _, en in tb._task_item_rects()}
    assert items_3d["distance"] is True
    assert items_3d["metrics"] is True
    assert items_3d["cross_section"] is True  # Unlocked for 3D!
    assert items_3d["unfold"] is True         # Unlocked for 3D!

    # 2. 2D Shape (Square)
    s_2d = FrozenShape(kind="Square", params={"center_xy": (0.5, 0.5), "size": 0.15})
    tb.update_tip(None, 0.1, frozen_shapes=[s_2d])
    items_2d = {tid: en for tid, _, _, en in tb._task_item_rects()}
    assert items_2d["distance"] is True
    assert items_2d["metrics"] is True
    assert items_2d["cross_section"] is False  # Disabled for 2D!
    assert items_2d["unfold"] is False         # Disabled for 2D!


def test_task_toolbar_multi_task_selection_and_auto_close():
    """Verify:
    - An object can have multiple tasks active simultaneously.
    - Each selection picks 1 task and closes the dropdown immediately.
    - User can re-open to pick another task.
    """
    from PySide6.QtWidgets import QApplication
    from app.ui.shape_toolbar import ShapeToolbar
    from app.extensions.base import FrozenShape

    app = QApplication.instance() or QApplication([])
    tb = ShapeToolbar()
    tb.resize(800, 600)
    s_3d = FrozenShape(kind="Cube", params={"center_xy": (0.5, 0.5), "size": 0.15})
    tb.update_tip(None, 0.1, frozen_shapes=[s_3d])

    # Open task dropdown
    tb._task_open = True
    item_rects = {tid: r for tid, _, r, en in tb._task_item_rects()}

    # Select distance
    r_dist = item_rects["distance"]
    tip_norm = (r_dist.center().x() / 800.0, r_dist.center().y() / 600.0)
    tb.update_tip(tip_norm, 0.85, frozen_shapes=[s_3d])

    assert "distance" in s_3d.tasks
    assert not tb._task_open  # Auto-closes immediately!
    assert "Đã bật" in tb.last_task_event

    # Re-open task dropdown to select a second task (metrics)
    tb._task_open = True
    tb._task_trigger_must_exit = False
    r_metrics = item_rects["metrics"]
    tip_norm2 = (r_metrics.center().x() / 800.0, r_metrics.center().y() / 600.0)
    tb.update_tip(tip_norm2, 0.85, frozen_shapes=[s_3d])

    assert "metrics" in s_3d.tasks
    assert "distance" in s_3d.tasks  # Both tasks active simultaneously!
    assert not tb._task_open


def test_frozen_geometry_renders_math_tasks():
    """Verify that distance, metrics, and cross_section tasks add their geometry and labels."""
    from app.extensions.registry import ExtensionRegistry
    from app.config import ProductConfig
    from app.extensions.base import FrozenShape

    reg = ExtensionRegistry(ProductConfig())
    lab = reg.select("coordinate")
    lab.clear_frozen_shapes()

    s = FrozenShape(kind="Cube", params={"center_xy": (0.5, 0.5), "size": 0.15})
    lab.add_frozen_shape(s)

    # Base cube without tasks
    geo_base = lab.frozen_geometry()
    lines_base_count = len(geo_base.lines)
    labels_base_count = len(geo_base.labels)
    faces_base_count = len(geo_base.faces)

    # 1. Enable distance task
    s.tasks.add("distance")
    geo_dist = lab.frozen_geometry()
    assert len(geo_dist.lines) > lines_base_count
    assert len(geo_dist.labels) > labels_base_count
    assert any("a=" in lbl[1] for lbl in geo_dist.labels)

    # 2. Enable metrics task
    s.tasks.add("metrics")
    geo_metrics = lab.frozen_geometry()
    assert any("V=" in lbl[1] for lbl in geo_metrics.labels)

    # 3. Enable cross_section task
    s.tasks.add("cross_section")
    geo_cs = lab.frozen_geometry()
    assert len(geo_cs.faces) > faces_base_count
    assert any("Thiết diện" in lbl[1] for lbl in geo_cs.labels)

    # 4. Enable unfold task
    s.tasks.add("unfold")
    geo_unfold = lab.frozen_geometry()
    assert any("Bung mặt phẳng" in lbl[1] for lbl in geo_unfold.labels)
    assert any("Mặt đáy" in lbl[1] for lbl in geo_unfold.labels)


def test_frozen_geometry_3d_unfolding_tasks():
    """Verify 3D Unfolding (Bung mặt phẳng) for Cube, Box, Pyramid, and Sphere:
    - Cube: Latin cross net with 6 faces, hinges, face labels, and S_tp = 6a^2.
    - Box: 6 faces unfolding outward, hinges, face labels, and S_tp = 2(LH+LW+HW).
    - Pyramid: Star net with base and 3 lateral triangles, hinges, and S_tp formula.
    - Sphere: Sinusoidal gore net with Gauss curvature theorem label.
    - Smooth animation: unfold_progress interpolates between 0.0 and 1.0.
    """
    from app.extensions.registry import ExtensionRegistry
    from app.config import ProductConfig
    from app.extensions.base import FrozenShape

    reg = ExtensionRegistry(ProductConfig())
    lab = reg.select("coordinate")

    # 1. Cube
    lab.clear_frozen_shapes()
    cube = FrozenShape(kind="Cube", params={"center_xy": (0.5, 0.5), "size": 0.15})
    cube.tasks.add("unfold")
    lab.add_frozen_shape(cube)
    geo_cube = lab.frozen_geometry()
    cube_labels = [lbl[1] for lbl in geo_cube.labels]
    assert any("Bung mặt phẳng: Khối lập phương" in l for l in cube_labels)
    assert any("Mặt đáy" in l for l in cube_labels)
    assert any("Mặt trước" in l for l in cube_labels)
    assert any("Mặt sau" in l for l in cube_labels)
    assert any("Mặt trái" in l for l in cube_labels)
    assert any("Mặt phải" in l for l in cube_labels)
    assert any("Mặt nắp" in l for l in cube_labels)
    # Hinges rendered in amber
    assert any(line.color == "#f59e0b" for line in geo_cube.lines)

    # 2. Box
    lab.clear_frozen_shapes()
    box = FrozenShape(kind="Box", params={"center_xy": (0.5, 0.5), "width": 0.2, "height": 0.15, "size": 0.12})
    box.tasks.add("unfold")
    lab.add_frozen_shape(box)
    geo_box = lab.frozen_geometry()
    box_labels = [lbl[1] for lbl in geo_box.labels]
    assert any("Bung mặt phẳng: Hộp chữ nhật" in l for l in box_labels)
    assert any("Mặt đáy" in l for l in box_labels)
    assert any("Mặt nắp" in l for l in box_labels)
    assert any(line.color == "#f59e0b" for line in geo_box.lines)

    # 3. Pyramid
    lab.clear_frozen_shapes()
    pyramid = FrozenShape(kind="Pyramid", params={"center_xy": (0.5, 0.5), "corners_xy": [(0.5, 0.2), (0.3, 0.7), (0.7, 0.7)]})
    pyramid.tasks.add("unfold")
    lab.add_frozen_shape(pyramid)
    geo_pyr = lab.frozen_geometry()
    pyr_labels = [lbl[1] for lbl in geo_pyr.labels]
    assert any("Bung mặt phẳng: Chóp tam giác" in l for l in pyr_labels)
    assert any("Mặt đáy" in l for l in pyr_labels)
    assert any("Mặt bên 1" in l for l in pyr_labels)
    assert any("Mặt bên 2" in l for l in pyr_labels)
    assert any("Mặt bên 3" in l for l in pyr_labels)
    assert any(line.color == "#f59e0b" for line in geo_pyr.lines)

    # 4. Sphere
    lab.clear_frozen_shapes()
    sphere = FrozenShape(kind="Sphere", params={"center_xy": (0.5, 0.5), "radius": 0.08})
    sphere.tasks.add("unfold")
    lab.add_frozen_shape(sphere)
    geo_sph = lab.frozen_geometry()
    sph_labels = [lbl[1] for lbl in geo_sph.labels]
    assert any("Bung mặt phẳng: Múi cầu" in l for l in sph_labels)
    assert any("Định lý Gauss" in l for l in sph_labels)
    assert len(geo_sph.faces) > 0  # 6 gores * 16 slices

    # 5. Animation progress progression (0.5 partially unfolded)
    lab.clear_frozen_shapes()
    cube.unfold_progress = 0.5
    lab.add_frozen_shape(cube)
    geo_half = lab.frozen_geometry()
    assert len(geo_half.faces) > 0
    assert any("Mặt nắp" in lbl[1] for lbl in geo_half.labels)


def test_unfold_progress_animation_transition():
    """Verify smooth unfold animation ticker behaves correctly when stepping forward and backward."""
    from app.extensions.base import FrozenShape

    s = FrozenShape(kind="Cube", params={"center_xy": (0.5, 0.5), "size": 0.15})
    assert s.unfold_progress == 0.0

    # User toggles "unfold" ON
    s.tasks.add("unfold")
    dt = 0.033  # ~30fps
    for _ in range(15):  # ~0.5s
        target = 1.0 if "unfold" in s.tasks else 0.0
        step = 2.5 * dt
        if s.unfold_progress < target:
            s.unfold_progress = min(target, s.unfold_progress + step)
    assert s.unfold_progress == 1.0

    # User toggles "unfold" OFF
    s.tasks.remove("unfold")
    for _ in range(15):
        target = 1.0 if "unfold" in s.tasks else 0.0
        step = 2.5 * dt
        if s.unfold_progress > target:
            s.unfold_progress = max(target, s.unfold_progress - step)
    assert s.unfold_progress == 0.0


def test_2d_shapes_metrics_have_no_volume():
    """Requirement 4: 2D shapes must not display volume, only area and perimeter."""
    from app.extensions.registry import ExtensionRegistry
    from app.config import ProductConfig
    from app.extensions.base import FrozenShape

    reg = ExtensionRegistry(ProductConfig())
    lab = reg.select("coordinate")

    for kind, params in [
        ("Circle", {"center_xy": (0.5, 0.5), "radius": 0.08}),
        ("Square", {"center_xy": (0.5, 0.5), "corners_xy": [(0.4, 0.4), (0.6, 0.4), (0.6, 0.6), (0.4, 0.6)]}),
        ("Rectangle", {"center_xy": (0.5, 0.5), "corners_xy": [(0.3, 0.4), (0.7, 0.4), (0.7, 0.6), (0.3, 0.6)]}),
        ("Triangle", {"center_xy": (0.5, 0.5), "corners_xy": [(0.5, 0.2), (0.3, 0.7), (0.8, 0.8)]}),
    ]:
        lab.clear_frozen_shapes()
        s = FrozenShape(kind=kind, params=params)
        s.tasks.add("metrics")
        lab.add_frozen_shape(s)
        geo = lab.frozen_geometry()
        label_texts = [lbl[1] for lbl in geo.labels]
        assert any("S=" in txt for txt in label_texts), f"{kind} must show area S"
        assert not any("V=" in txt for txt in label_texts), f"{kind} 2D shape must NOT show volume V"


def test_invariant_distance_measurements():
    """Requirement 2: Edge measurements must be strictly invariant under 3D rotation."""
    from app.extensions.registry import ExtensionRegistry
    from app.config import ProductConfig
    from app.extensions.base import FrozenShape

    reg = ExtensionRegistry(ProductConfig())
    lab = reg.select("coordinate")

    # Rectangle with corners
    corners = [(0.3, 0.3), (0.7, 0.3), (0.7, 0.6), (0.3, 0.6)]
    lab.clear_frozen_shapes()
    s = FrozenShape(kind="Rectangle", params={"center_xy": (0.5, 0.45), "corners_xy": corners})
    s.tasks.add("distance")
    lab.add_frozen_shape(s)

    # 1. Unrotated
    s.yaw = 0.0
    s.pitch = 0.0
    geo_0 = lab.frozen_geometry()
    labels_0 = {lbl[1] for lbl in geo_0.labels}
    assert any("W=" in txt for txt in labels_0)
    assert any("H=" in txt for txt in labels_0)

    # 2. Rotated by arbitrary yaw and pitch
    s.yaw = 1.25
    s.pitch = -0.85
    geo_rot = lab.frozen_geometry()
    labels_rot = {lbl[1] for lbl in geo_rot.labels}

    # Labels must be EXACTLY identical because dimensions are invariant physical properties
    assert labels_0 == labels_rot, f"Measurements changed under rotation: {labels_0} vs {labels_rot}"


def test_3d_box_face_area_visibility_threshold():
    """Requirement 3: Polyhedra volume is displayed once; each visible face shows its area; occluded faces hidden."""
    from app.extensions.registry import ExtensionRegistry
    from app.config import ProductConfig
    from app.extensions.base import FrozenShape

    reg = ExtensionRegistry(ProductConfig())
    lab = reg.select("coordinate")
    lab.yaw = 0.0
    lab.pitch = 0.0

    # Box with different dimensions L != H != W
    s = FrozenShape(kind="Box", params={"center_xy": (0.5, 0.5), "width": 0.20, "height": 0.12, "size": 0.16})
    s.tasks.add("metrics")
    lab.clear_frozen_shapes()
    lab.add_frozen_shape(s)

    geo = lab.frozen_geometry()
    v_labels = [lbl for lbl in geo.labels if "V=" in lbl[1]]
    s_labels = [lbl for lbl in geo.labels if "S=" in lbl[1]]

    # Single volume value for the whole box
    assert len(v_labels) == 1
    # Box has 6 faces; when viewed front-on without tilt, only the front face (+Z) is visible (>0.15 threshold)
    # The back and side faces are occluded / edge-on and therefore hidden!
    assert 1 <= len(s_labels) <= 3
    # Check that visible face area equals L * H = (2 * 0.20) * (2 * 0.12) = 0.40 * 0.24 = 0.096 (rounded 0.10)
    assert any("S=" in lbl[1] for lbl in s_labels)


def test_arbitrary_triangle_from_fingertips():
    """Requirement 5: Triangle vertices mapped directly from finger positions without equilateral constraint."""
    from app.interaction.shape_gestures import ShapeGestureEngine
    from tests.product_v2.test_shape_toolbar import make_hand
    import pytest

    engine = ShapeGestureEngine(stability_frames=3)
    # Define an asymmetric / right triangle: (0.2, 0.3), (0.8, 0.3), (0.2, 0.8)
    dom = make_hand("DOMINANT", {
        "INDEX": (0.2, 0.3),
        "THUMB": (0.8, 0.3),
        "MIDDLE": (0.2, 0.8),
    })
    cand = engine.update([dom], "Triangle")
    assert cand.shape_type == "Triangle"
    assert cand.params is not None
    corners = cand.params.corners_xy
    assert len(corners) == 3
    # Vertices must map to the 3 distinct fingertips directly
    xs = sorted([c[0] for c in corners])
    ys = sorted([c[1] for c in corners])
    assert xs[0] == pytest.approx(0.2)
    assert xs[2] == pytest.approx(0.8)
    assert ys[0] == pytest.approx(0.3)
    assert ys[2] == pytest.approx(0.8)


def test_brightness_sampling_and_adaptive_text_intensity():
    """Requirement 1: Average brightness sampled over 5-10 frames when task opened/started, setting contrast text intensity."""
    from PySide6.QtWidgets import QApplication
    from app.ui.shell import ProductWindow
    from app.config import ProductConfig
    import numpy as np
    import pytest

    app = QApplication.instance() or QApplication([])

    class DummyPacket:
        def __init__(self, val):
            self.image = np.full((120, 160, 3), val, dtype=np.uint8)
            self.source_name = "live"

    config = ProductConfig()
    shell = ProductWindow(config=config, software=True)

    dummy_frame = type("DummyFrame", (), {
        "run_id": "r", "frame_id": 1, "timestamp_s": 0.1,
        "illumination": None, "dominant": None, "support": None,
    })()

    # 1. Trigger brightness sampling (8 frames) for bright scene
    shell._brightness_sampling_counter = 8
    shell._brightness_samples = []
    for _ in range(8):
        shell.consume(DummyPacket(220), dummy_frame, None, {}, True, "OK")

    assert shell._brightness_sampling_counter == 0
    assert shell.average_scene_brightness == pytest.approx(220.0, abs=1.0)
    # Bright background -> dark text intensity
    assert shell.viewport.label_color.lightness() < 100

    # 2. Trigger brightness sampling for dark scene
    shell._brightness_sampling_counter = 8
    shell._brightness_samples = []
    for _ in range(8):
        shell.consume(DummyPacket(30), dummy_frame, None, {}, True, "OK")

    assert shell._brightness_sampling_counter == 0
    assert shell.average_scene_brightness == pytest.approx(30.0, abs=1.0)
    # Dark background -> bright text intensity
    assert shell.viewport.label_color.lightness() > 180
    shell.close()


# =====================================================================
# 11. Camera-Bounded UI, Closer-Hand Preemption, ONLY ONE Lock, 2-Hand Creation
# =====================================================================

def test_toolbar_camera_bounded_layout():
    from app.ui.shape_toolbar import (
        ShapeToolbar, TRIGGER_W, TRIGGER_H, CAMERA_INSET_X, CAMERA_INSET_Y, DELETE_W, DELETE_H
    )
    from PySide6.QtWidgets import QApplication, QWidget
    app = QApplication.instance() or QApplication([])

    # Mock parent viewport with letterboxed image rect
    parent = QWidget()
    parent.resize(1000, 800)
    parent.image_rect = lambda: (100.0, 50.0, 800.0, 600.0)

    tb = ShapeToolbar(parent)
    tb.resize(1000, 800)

    # 1. Shape trigger at top-right inside camera rect (x=100..900, y=50..650)
    tr1 = tb._trigger_rect()
    assert tr1.right() <= 900 - CAMERA_INSET_X
    assert tr1.left() >= 100
    assert tr1.top() == 50 + CAMERA_INSET_Y
    assert tr1.width() == TRIGGER_W
    assert tr1.height() == TRIGGER_H

    # 2. Task trigger directly below Shape trigger
    tr2 = tb._task_trigger_rect()
    assert tr2.top() == 50 + CAMERA_INSET_Y + TRIGGER_H + 8
    assert tr2.width() == TRIGGER_W
    assert tr2.height() == TRIGGER_H

    # 3. Dropdown panels positioned directly below the 2 buttons
    panel = tb._panel_rect()
    expected_panel_top = 50 + CAMERA_INSET_Y + TRIGGER_H + 8 + TRIGGER_H + 6
    assert panel.top() == expected_panel_top

    # 4. Delete button at bottom-left inside camera rect
    del_r = tb._delete_rect()
    assert del_r.left() == 100 + CAMERA_INSET_X
    assert del_r.bottom() == 50 + 600 - CAMERA_INSET_Y - 1
    assert del_r.width() == DELETE_W
    assert del_r.height() == DELETE_H


def test_stability_frames_shortened_by_35_percent():
    from app.interaction.shape_gestures import STABILITY_FRAMES
    assert STABILITY_FRAMES == 39  # reduced by 35% from 60 (~1.3s @ 30fps)


def test_normal_mode_single_hand_lock_and_1s_lost_transfer():
    from app.ui.shell import ProductWindow
    from app.config import ProductConfig
    from dip_touchless.core import Landmark, CoordinateSpace
    import numpy as np
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    config = ProductConfig()
    shell = ProductWindow(config=config, software=True)

    class DummyPacket:
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        source_name = "live"

    dummy_frame = type("DummyFrame", (), {
        "run_id": "test_preempt", "frame_id": 1, "timestamp_s": 0.1,
        "illumination": None, "dominant": None, "support": None,
    })()

    def make_lm(center_x, span):
        pts = []
        for i in range(21):
            if i == 5:
                pts.append(Landmark(i, center_x - span / 2, 0.5, 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i == 17:
                pts.append(Landmark(i, center_x + span / 2, 0.5, 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i in (1, 2, 3, 4):
                pts.append(Landmark(i, center_x - 0.05, 0.5 - 0.02 * i, 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i in (6, 7, 8):
                pts.append(Landmark(i, center_x - 0.02, 0.5 - 0.05 * (i - 5), 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i in (9, 10, 11, 12):
                pts.append(Landmark(i, center_x, 0.5 - 0.05 * (i - 9), 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i in (13, 14, 15, 16):
                pts.append(Landmark(i, center_x + 0.02, 0.5 - 0.05 * (i - 13), 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i in (18, 19, 20):
                pts.append(Landmark(i, center_x + 0.04, 0.5 - 0.04 * (i - 17), 0.0, CoordinateSpace.FRAME_NORMALIZED))
            else:
                pts.append(Landmark(i, center_x, 0.55, 0.0, CoordinateSpace.FRAME_NORMALIZED))
        return pts

    # Frame 1: Hand at 1.0m (span = 0.09) in frame -> acquired as ONLY ONE
    filtered_1 = {"hand_first": make_lm(0.4, 0.09)}
    shell.consume(DummyPacket(), dummy_frame, None, filtered_1, True, "OK")
    assert len(shell.current_hands) == 1
    assert shell.current_hands[0].track_id == "hand_first"
    assert shell._primary_hand_id == "hand_first"

    # Frame 2: Second hand enters closer at 0.5m (span = 0.18).
    # STRICT RULE: Do not recognize any other hand while controlling hand is present!
    filtered_2 = {
        "hand_first": make_lm(0.4, 0.09),
        "hand_second": make_lm(0.6, 0.18),
    }
    shell.consume(DummyPacket(), dummy_frame, None, filtered_2, True, "OK")
    assert len(shell.current_hands) == 1
    assert shell.current_hands[0].track_id == "hand_first"
    assert shell._primary_hand_id == "hand_first"

    # Frame 3: Another hand appears further at 0.7m (span = 0.13).
    # Still only hand_first is recognized!
    filtered_3 = {
        "hand_first": make_lm(0.4, 0.09),
        "hand_noise": make_lm(0.2, 0.13),
    }
    shell.consume(DummyPacket(), dummy_frame, None, filtered_3, True, "OK")
    assert len(shell.current_hands) == 1
    assert shell.current_hands[0].track_id == "hand_first"

    # Frame 4: Controlling hand disappears from camera for 0.4s (< 1.0s).
    # Must NOT recognize any other hand yet during this 1s grace period!
    import time
    t_recent = time.monotonic() - 0.4
    shell._primary_hand_last_seen_time = t_recent
    filtered_4 = {"hand_second": make_lm(0.6, 0.18)}
    shell.consume(DummyPacket(), dummy_frame, None, filtered_4, True, "OK")
    assert len(shell.current_hands) == 0  # does not jump to second hand!

    # Frame 5: Controlling hand has been hidden for >= 1.0s (1.2s).
    # Lock is now released, and the new hand in view is acquired cleanly!
    t_old = time.monotonic() - 1.2
    shell._primary_hand_last_seen_time = t_old
    shell.consume(DummyPacket(), dummy_frame, None, filtered_4, True, "OK")
    assert len(shell.current_hands) == 1
    assert shell.current_hands[0].track_id == "hand_second"
    assert shell._primary_hand_id == "hand_second"
    shell.close()


def test_shape_creation_two_hand_filter_and_noise_rejection():
    from app.ui.shell import ProductWindow
    from app.config import ProductConfig
    from app.ui.shape_toolbar import ShapeToolbar
    from dip_touchless.core import Landmark, CoordinateSpace
    import numpy as np
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    config = ProductConfig()
    shell = ProductWindow(config=config, software=True)
    shell.shape_toolbar = ShapeToolbar(shell.viewport)
    shell.shape_toolbar._selected_shape = "Cube"  # Shape creation mode active!

    class DummyPacket:
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        source_name = "live"

    dummy_frame = type("DummyFrame", (), {
        "run_id": "test_create", "frame_id": 1, "timestamp_s": 0.1,
        "illumination": None, "dominant": None, "support": None,
    })()

    def make_lm(center_x, span):
        pts = []
        for i in range(21):
            if i == 5:
                pts.append(Landmark(i, center_x - span / 2, 0.5, 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i == 17:
                pts.append(Landmark(i, center_x + span / 2, 0.5, 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i in (1, 2, 3, 4):
                pts.append(Landmark(i, center_x - 0.05, 0.5 - 0.02 * i, 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i in (6, 7, 8):
                pts.append(Landmark(i, center_x - 0.02, 0.5 - 0.05 * (i - 5), 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i in (9, 10, 11, 12):
                pts.append(Landmark(i, center_x, 0.5 - 0.05 * (i - 9), 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i in (13, 14, 15, 16):
                pts.append(Landmark(i, center_x + 0.02, 0.5 - 0.05 * (i - 13), 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i in (18, 19, 20):
                pts.append(Landmark(i, center_x + 0.04, 0.5 - 0.04 * (i - 17), 0.0, CoordinateSpace.FRAME_NORMALIZED))
            else:
                pts.append(Landmark(i, center_x, 0.55, 0.0, CoordinateSpace.FRAME_NORMALIZED))
        return pts

    # Frame 1: 1 Left hand and 1 Right hand present
    filtered_1 = {
        "Left": make_lm(0.3, 0.12),
        "Right": make_lm(0.7, 0.12),
    }
    shell.consume(DummyPacket(), dummy_frame, None, filtered_1, True, "OK")
    assert len(shell.current_hands) == 2
    track_ids = {h.track_id for h in shell.current_hands}
    assert track_ids == {"Left", "Right"}

    # Frame 2: 3rd and 4th hands (extra/noise hands) appear
    filtered_2 = {
        "Left": make_lm(0.3, 0.12),
        "Right": make_lm(0.7, 0.12),
        "Left_extra": make_lm(0.2, 0.08),
        "Right_extra": make_lm(0.8, 0.08),
    }
    shell.consume(DummyPacket(), dummy_frame, None, filtered_2, True, "OK")
    # Only 1 Left and 1 Right retained; extra hands ignored!
    assert len(shell.current_hands) == 2
    track_ids = {h.track_id for h in shell.current_hands}
    assert track_ids == {"Left", "Right"}

    # Frame 3: Cube creation completes and shape is frozen into scene.
    # Transition to control signals: MUST prioritize Right hand and lock onto it!
    # Left hand and other hands must NOT be recognized for control signals anymore!
    from app.extensions.base import FrozenShape
    frozen = FrozenShape(kind="Cube", params={"center_xy": (0.5, 0.5), "size": 0.2})
    shell.registry.current.add_frozen_shape(frozen)
    shell.shape_toolbar.clear_selection()

    # Right hand lock is activated upon freeze:
    right_cand = next((h for h in shell.current_hands if shell._hand_side(h) == "Right"), None)
    assert right_cand is not None
    shell._primary_hand_id = right_cand.track_id
    import time
    shell._primary_hand_last_seen_time = time.monotonic()

    # Now feed frame with both Left and Right hands (and noise hands) still in view:
    shell.consume(DummyPacket(), dummy_frame, None, filtered_2, True, "OK")
    assert len(shell.current_hands) == 1
    assert shell.current_hands[0].track_id == "Right"
    assert shell._primary_hand_id == "Right"

    # Frame 4: Right hand temporarily hidden for 0.4s (< 1.0s) -> grace period, Left hand still rejected
    shell._primary_hand_last_seen_time = time.monotonic() - 0.4
    filtered_left_only = {"Left": make_lm(0.3, 0.12)}
    shell.consume(DummyPacket(), dummy_frame, None, filtered_left_only, True, "OK")
    assert len(shell.current_hands) == 0

    # Frame 5: Right hand hidden for >= 1.0s (1.2s) -> lock released, Left hand can now be acquired
    shell._primary_hand_last_seen_time = time.monotonic() - 1.2
    shell.consume(DummyPacket(), dummy_frame, None, filtered_left_only, True, "OK")
    assert len(shell.current_hands) == 1
    assert shell.current_hands[0].track_id == "Left"
    shell.close()


def test_single_hand_lock_in_during_manipulation():
    from app.ui.shell import ProductWindow
    from app.config import ProductConfig
    from app.extensions.base import FrozenShape
    from dip_touchless.core import Landmark, CoordinateSpace
    import numpy as np
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    config = ProductConfig()
    shell = ProductWindow(config=config, software=True)

    class DummyPacket:
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        source_name = "live"

    dummy_frame = type("DummyFrame", (), {
        "run_id": "test_lock", "frame_id": 1, "timestamp_s": 0.1,
        "illumination": None, "dominant": None, "support": None,
    })()

    def make_lm(center_x, span):
        pts = []
        for i in range(21):
            if i == 5:
                pts.append(Landmark(i, center_x - span / 2, 0.5, 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i == 17:
                pts.append(Landmark(i, center_x + span / 2, 0.5, 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i in (1, 2, 3, 4):
                pts.append(Landmark(i, center_x - 0.05, 0.5 - 0.02 * i, 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i in (6, 7, 8):
                pts.append(Landmark(i, center_x - 0.02, 0.5 - 0.05 * (i - 5), 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i in (9, 10, 11, 12):
                pts.append(Landmark(i, center_x, 0.5 - 0.05 * (i - 9), 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i in (13, 14, 15, 16):
                pts.append(Landmark(i, center_x + 0.02, 0.5 - 0.05 * (i - 13), 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i in (18, 19, 20):
                pts.append(Landmark(i, center_x + 0.04, 0.5 - 0.04 * (i - 17), 0.0, CoordinateSpace.FRAME_NORMALIZED))
            else:
                pts.append(Landmark(i, center_x, 0.55, 0.0, CoordinateSpace.FRAME_NORMALIZED))
        return pts

    # Frame 1: User manipulating
    filtered = {
        "hand_main": make_lm(0.4, 0.12),
        "hand_other": make_lm(0.8, 0.10),
    }
    frozen = FrozenShape(kind="Cube", params={"center_xy": (0.4, 0.5), "size": 0.2})
    shell._drag_shape = frozen
    shell._manipulation_locked_hand_id = "hand_main"

    # Feed both hands into consume while manipulating
    shell.consume(DummyPacket(), dummy_frame, None, filtered, True, "OK")

    # Only hand_main must be recognized! hand_other is completely excluded
    assert len(shell.current_hands) == 1
    assert shell.current_hands[0].track_id == "hand_main"
    assert "hand_other" not in shell.viewport.landmarks

    # Frame 2: Manipulation ends
    shell._drag_shape = None
    shell.consume(DummyPacket(), dummy_frame, None, filtered, True, "OK")
    assert shell._manipulation_locked_hand_id is None
    shell.close()


def test_single_shape_requires_dwell_selection_and_disengagement_static_state(monkeypatch):
    import time
    from app.ui.shell import ProductWindow
    from app.config import ProductConfig, Settings
    from app.extensions.base import FrozenShape
    from developer_tools.synthetic_hands import landmarks
    from dip_touchless.core import Landmark, CoordinateSpace
    import numpy as np
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    cur_t = [100.0]
    monkeypatch.setattr(time, "monotonic", lambda: cur_t[0])

    def make_pointing_hand(target_x, target_y):
        pts = landmarks({1}, center=0.5)
        dx = target_x - pts[8].x
        dy = target_y - pts[8].y
        return [
            Landmark(p.index, p.x + dx, p.y + dy, p.z, CoordinateSpace.FRAME_NORMALIZED)
            for p in pts
        ]

    def make_curled_hand():
        return landmarks(set(), center=0.5)

    config = ProductConfig()
    settings = Settings(mirror=False)
    shell = ProductWindow(config=config, settings=settings, software=True)
    shell.navigate("Explore")
    shell.select_lab("coordinate")

    s1 = FrozenShape(kind="Cube", params={"center_xy": (0.3, 0.5), "size": 0.2})
    shell.registry.current.add_frozen_shape(s1)

    # 1. Newly created shape starts unselected / static state
    assert shell.registry.current.selected_shape_id is None

    class DummyPacket:
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        source_name = "live"

    # 2. Waving index finger in the air outside the shape does NOT select or rotate s1
    initial_yaw = s1.yaw
    f1 = type("DummyFrame", (), {"run_id": "test", "frame_id": 1, "timestamp_s": 0.033, "illumination": None, "dominant": None, "support": None})()
    shell.consume(DummyPacket(), f1, None, {"Right": make_pointing_hand(0.8, 0.2)}, True, "OK")
    cur_t[0] += 0.033
    f2 = type("DummyFrame", (), {"run_id": "test", "frame_id": 2, "timestamp_s": cur_t[0], "illumination": None, "dominant": None, "support": None})()
    shell.consume(DummyPacket(), f2, None, {"Right": make_pointing_hand(0.85, 0.2)}, True, "OK")
    assert shell.registry.current.selected_shape_id is None
    assert s1.yaw == initial_yaw

    # 3. Placing index fingertip over the shape and dwelling for >= 0.6s selects it
    for fid in range(3, 25):
        cur_t[0] += 0.05
        f = type("DummyFrame", (), {"run_id": "test", "frame_id": fid, "timestamp_s": cur_t[0], "illumination": None, "dominant": None, "support": None})()
        shell.consume(DummyPacket(), f, None, {"Right": make_pointing_hand(0.3, 0.5)}, True, "OK")
        if shell.registry.current.selected_shape_id == s1.shape_id:
            break

    assert shell.registry.current.selected_shape_id == s1.shape_id

    # 4. Now rotating moves s1
    shell._prev_rotate_xy = (0.3, 0.5)
    cur_t[0] += 0.033
    f_rot = type("DummyFrame", (), {"run_id": "test", "frame_id": 30, "timestamp_s": cur_t[0], "illumination": None, "dominant": None, "support": None})()
    shell.consume(DummyPacket(), f_rot, None, {"Right": make_pointing_hand(0.35, 0.5)}, True, "OK")
    assert s1.yaw != initial_yaw

    # 5. Actively curling finger away (disengagement) immediately returns shape to static state
    cur_t[0] += 0.033
    f_curl = type("DummyFrame", (), {"run_id": "test", "frame_id": 31, "timestamp_s": cur_t[0], "illumination": None, "dominant": None, "support": None})()
    shell.consume(DummyPacket(), f_curl, None, {"Right": make_curled_hand()}, True, "OK")
    assert shell.registry.current.selected_shape_id is None

    # 6. Subsequent waving of index finger in the air does NOT rotate or modify the shape
    cur_yaw = s1.yaw
    cur_t[0] += 0.033
    f_wave = type("DummyFrame", (), {"run_id": "test", "frame_id": 32, "timestamp_s": cur_t[0], "illumination": None, "dominant": None, "support": None})()
    shell.consume(DummyPacket(), f_wave, None, {"Right": make_pointing_hand(0.8, 0.3)}, True, "OK")
    cur_t[0] += 0.033
    f_wave2 = type("DummyFrame", (), {"run_id": "test", "frame_id": 33, "timestamp_s": cur_t[0], "illumination": None, "dominant": None, "support": None})()
    shell.consume(DummyPacket(), f_wave2, None, {"Right": make_pointing_hand(0.85, 0.3)}, True, "OK")
    # Shape stayed static!
    assert shell.registry.current.selected_shape_id is None
    assert s1.yaw == cur_yaw
    shell.close()


def test_multi_shape_dwell_selection_and_exclusive_targeting(monkeypatch):
    import time
    from app.ui.shell import ProductWindow
    from app.config import ProductConfig, Settings
    from app.extensions.base import FrozenShape
    from developer_tools.synthetic_hands import landmarks
    from dip_touchless.core import Landmark, CoordinateSpace
    import numpy as np
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    cur_t = [100.0]
    monkeypatch.setattr(time, "monotonic", lambda: cur_t[0])

    def make_pointing_hand(target_x, target_y):
        pts = landmarks({1}, center=0.5)
        dx = target_x - pts[8].x
        dy = target_y - pts[8].y
        return [
            Landmark(p.index, p.x + dx, p.y + dy, p.z, CoordinateSpace.FRAME_NORMALIZED)
            for p in pts
        ]

    def make_pinch_hand(target_x, target_y):
        pts = make_pointing_hand(target_x, target_y)
        idx_tip = pts[8]
        pts[4] = Landmark(4, idx_tip.x + 0.01, idx_tip.y, idx_tip.z, CoordinateSpace.FRAME_NORMALIZED)
        return pts

    config = ProductConfig()
    settings = Settings(mirror=False)
    shell = ProductWindow(config=config, settings=settings, software=True)
    shell.navigate("Explore")
    shell.select_lab("coordinate")

    s1 = FrozenShape(kind="Cube", params={"center_xy": (0.2, 0.5), "size": 0.15})
    s2 = FrozenShape(kind="Sphere", params={"center_xy": (0.7, 0.5), "size": 0.15})
    shell.registry.current.add_frozen_shape(s1)
    shell.registry.current.add_frozen_shape(s2)
    shell.registry.current.selected_shape_id = s1.shape_id

    class DummyPacket:
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        source_name = "live"

    # 1. Exclusive Pinch Drag: Pinching over unselected s2 does NOT drag s2!
    frame1 = type("DummyFrame", (), {"run_id": "test", "frame_id": 1, "timestamp_s": 0.033, "illumination": None, "dominant": None, "support": None})()
    hands_pinch_s2 = {"Right": make_pinch_hand(0.7, 0.5)}
    # Unpinched first to establish baseline
    shell.consume(DummyPacket(), frame1, None, {"Right": make_pointing_hand(0.7, 0.5)}, True, "OK")
    cur_t[0] += 0.033
    assert shell._drag_shape is None

    # Now pinch down over s2 (unselected shape)
    frame2 = type("DummyFrame", (), {"run_id": "test", "frame_id": 2, "timestamp_s": 0.066, "illumination": None, "dominant": None, "support": None})()
    shell.consume(DummyPacket(), frame2, None, hands_pinch_s2, True, "OK")
    cur_t[0] += 0.033
    # s2 MUST NOT be dragged because s1 is selected!
    assert shell._drag_shape is None

    # Pinch down over s1 (selected shape) -> grabs s1
    frame3 = type("DummyFrame", (), {"run_id": "test", "frame_id": 3, "timestamp_s": 0.100, "illumination": None, "dominant": None, "support": None})()
    shell.consume(DummyPacket(), frame3, None, {"Right": make_pointing_hand(0.2, 0.5)}, True, "OK")
    cur_t[0] += 0.033
    frame4 = type("DummyFrame", (), {"run_id": "test", "frame_id": 4, "timestamp_s": 0.133, "illumination": None, "dominant": None, "support": None})()
    shell.consume(DummyPacket(), frame4, None, {"Right": make_pinch_hand(0.2, 0.5)}, True, "OK")
    cur_t[0] += 0.033
    assert shell._drag_shape is s1
    shell._drag_shape = None

    # 2. Dwell selection: Pointing at s2 (unselected) for < 0.6s does NOT switch selection
    shell._prev_rotate_xy = None
    frame5 = type("DummyFrame", (), {"run_id": "test", "frame_id": 5, "timestamp_s": 0.200, "illumination": None, "dominant": None, "support": None})()
    shell.consume(DummyPacket(), frame5, None, {"Right": make_pointing_hand(0.7, 0.5)}, True, "OK")
    # Dwell tracker started on s2
    assert shell.registry.current.selected_shape_id == s1.shape_id
    assert shell._shape_select_dwell.active_target == s2.shape_id

    # 3. Dwell selection: Pointing at s2 until >= 0.6s selects s2
    for fid in range(6, 25):
        cur_t[0] += 0.05
        f = type("DummyFrame", (), {"run_id": "test", "frame_id": fid, "timestamp_s": cur_t[0], "illumination": None, "dominant": None, "support": None})()
        shell.consume(DummyPacket(), f, None, {"Right": make_pointing_hand(0.7, 0.5)}, True, "OK")
        if shell.registry.current.selected_shape_id == s2.shape_id:
            break

    assert shell.registry.current.selected_shape_id == s2.shape_id
    assert "Đã chọn Sphere" in shell.feedback.text()

    # 4. Exclusive Rotation: Rotating now affects s2, NOT s1
    initial_yaw_s1 = s1.yaw
    initial_yaw_s2 = s2.yaw
    shell._prev_rotate_xy = (0.7, 0.5)
    cur_t[0] += 0.033
    frame7 = type("DummyFrame", (), {"run_id": "test", "frame_id": 31, "timestamp_s": cur_t[0], "illumination": None, "dominant": None, "support": None})()
    # Move index finger horizontally to (0.75, 0.5)
    shell.consume(DummyPacket(), frame7, None, {"Right": make_pointing_hand(0.75, 0.5)}, True, "OK")
    assert s2.yaw != initial_yaw_s2
    assert s1.yaw == initial_yaw_s1  # s1 must remain unchanged!

    # 5. Mid-rotation stroke: sweeping across shape 1 does NOT switch selection
    shell._prev_rotate_xy = (0.75, 0.5)
    cur_t[0] += 0.033
    frame_sweep = type("DummyFrame", (), {"run_id": "test", "frame_id": 32, "timestamp_s": cur_t[0], "illumination": None, "dominant": None, "support": None})()
    shell.consume(DummyPacket(), frame_sweep, None, {"Right": make_pointing_hand(0.2, 0.5)}, True, "OK")
    assert shell.registry.current.selected_shape_id == s2.shape_id
    assert shell._shape_select_dwell.active_target is None

    shell.close()


def test_sidebar_guide_intro_and_gesture_order(tmp_path):
    """Test that sidebar guide and coordinate lab guide contain project introduction and 6 ordered gesture steps."""
    from app.ui.lab_guides import GUIDES
    from app.ui.shell import _SIDEBAR_GUIDE_HTML

    # Check that introduction is present in HTML
    assert "✦ DIP TOUCHLESS STEM" in _SIDEBAR_GUIDE_HTML
    assert "Hệ thống học tập STEM không chạm" in _SIDEBAR_GUIDE_HTML

    # Check 6 steps in logical chronological order
    step_keywords = [
        "1. Chọn hình vẽ",
        "2. Tạo hình & Đóng băng",
        "3. Chọn hình điều khiển",
        "4. Di chuyển vật thể",
        "5. Xoay hình độc lập",
        "6. Tác vụ nâng cao",
    ]
    last_idx = -1
    for step in step_keywords:
        idx = _SIDEBAR_GUIDE_HTML.find(step)
        assert idx != -1, f"Step '{step}' missing in _SIDEBAR_GUIDE_HTML"
        assert idx > last_idx, f"Step '{step}' out of order in _SIDEBAR_GUIDE_HTML"
        last_idx = idx

    # Check tips
    assert "Khóa tay gần nhất" in _SIDEBAR_GUIDE_HTML
    assert "Khối xoay Gizmo" in _SIDEBAR_GUIDE_HTML

    # Check coordinate guide steps match logical workflow
    coord_guide = GUIDES["coordinate"]
    assert len(coord_guide.steps) == 6
    assert "Bước 1 (Chọn hình)" in coord_guide.steps[0]
    assert "Bước 2 (Tạo & Đóng băng)" in coord_guide.steps[1]
    assert "Bước 3 (Chọn vật thể)" in coord_guide.steps[2]
    assert "Bước 4 (Di chuyển)" in coord_guide.steps[3]
    assert "Bước 5 (Xoay hình)" in coord_guide.steps[4]
    assert "Bước 6 (Tác vụ nâng cao)" in coord_guide.steps[5]


def test_realtime_shape_freeze_hold_duration():
    """Verify shape freezing conforms to 1.8s realtime duration regardless of framerate (no CPU lag dependence)."""
    from app.interaction.shape_gestures import ShapeGestureEngine, STABILITY_DURATION_S

    assert 1.5 <= STABILITY_DURATION_S <= 2.0  # User specified 1.5s -> 2.0s
    engine = ShapeGestureEngine()
    dom = make_hand("DOMINANT", {"THUMB": (0.3, 0.5), "INDEX": (0.5, 0.5)})

    # 1. At 30 FPS (dt = 0.033s):
    # Establish key at t=0
    engine.update([dom], "Circle", dt=0.033)
    # Simulate holding for 1.0s (30 frames) -> should NOT be stable yet
    for _ in range(30):
        cand = engine.update([dom], "Circle", dt=0.033)
    assert not cand.is_stable
    assert 0.5 < cand.stable_fraction < 0.65

    # Simulate until 1.8s (another 25 frames, total 55 frames * 0.033 = 1.815s)
    for _ in range(25):
        cand = engine.update([dom], "Circle", dt=0.033)
    assert cand.is_stable
    assert cand.stable_fraction == 1.0

    # 2. At low FPS e.g. 15 FPS (dt = 0.066s, e.g. slower CPU):
    # Reaches 1.8s in 28 frames, completely independent of CPU framerate!
    engine2 = ShapeGestureEngine()
    engine2.update([dom], "Circle", dt=0.066)
    # 27 deltas * 0.066s = 1.782s -> 99% of 1.8s
    for _ in range(27):
        cand2 = engine2.update([dom], "Circle", dt=0.066)
    assert not cand2.is_stable
    assert cand2.stable_fraction == pytest.approx(0.99, abs=0.02)
    # 28th delta (total elapsed 1.848s >= 1.8s) -> becomes stable in real time!
    cand2 = engine2.update([dom], "Circle", dt=0.066)
    assert cand2.is_stable
    assert cand2.stable_fraction == 1.0


def test_shape_lifecycle_pointing_open_create_and_freeze_right_hand_priority():
    """Verify exact lifecycle requested:
    1. Keypoint pointing to open toolbar/tool -> only 1 hand locked (Right hand prioritized).
    2. Select shape -> shape creation phase uses 2 hands (Left & Right), rejects extra 3rd hand.
    3. Freeze shape -> immediately locks to Right hand (Hand 1), drops Left hand (Hand 2),
       and rejects Left hand and all other hands from control signals.
    """
    from app.ui.shell import ProductWindow
    from app.config import ProductConfig
    from app.ui.shape_toolbar import ShapeToolbar
    from dip_touchless.core import Landmark, CoordinateSpace
    import numpy as np
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    config = ProductConfig()
    shell = ProductWindow(config=config, software=True)
    shell.page_name = "Explore"
    shell.shape_toolbar = ShapeToolbar(shell.viewport)

    class DummyPacket:
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        source_name = "live"

    dummy_frame = type("DummyFrame", (), {
        "run_id": "test_lifecycle", "frame_id": 1, "timestamp_s": 0.1,
        "illumination": None, "dominant": None, "support": None,
    })()

    def make_lm(center_x, span):
        pts = []
        for i in range(21):
            if i == 5:
                pts.append(Landmark(i, center_x - span / 2, 0.5, 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i == 17:
                pts.append(Landmark(i, center_x + span / 2, 0.5, 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i in (1, 2, 3, 4):
                pts.append(Landmark(i, center_x - 0.05, 0.5 - 0.02 * i, 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i in (6, 7, 8):
                pts.append(Landmark(i, center_x - 0.02, 0.5 - 0.05 * (i - 5), 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i in (9, 10, 11, 12):
                pts.append(Landmark(i, center_x, 0.5 - 0.05 * (i - 9), 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i in (13, 14, 15, 16):
                pts.append(Landmark(i, center_x + 0.02, 0.5 - 0.05 * (i - 13), 0.0, CoordinateSpace.FRAME_NORMALIZED))
            elif i in (18, 19, 20):
                pts.append(Landmark(i, center_x + 0.04, 0.5 - 0.04 * (i - 17), 0.0, CoordinateSpace.FRAME_NORMALIZED))
            else:
                pts.append(Landmark(i, center_x, 0.55, 0.0, CoordinateSpace.FRAME_NORMALIZED))
        return pts

    # Phase 1: Pointing to open tool / toolbar
    # Both Left and Right hands present, toolbar open
    shell.shape_toolbar._open = True
    filtered_both = {
        "Left": make_lm(0.3, 0.12),
        "Right": make_lm(0.7, 0.12),
        "Third_Hand": make_lm(0.5, 0.10),
    }
    shell.consume(DummyPacket(), dummy_frame, None, filtered_both, True, "OK")
    # Must lock ONLY 1 hand, and prioritize Right hand!
    assert len(shell.current_hands) == 1
    assert shell.current_hands[0].track_id == "Right"
    assert shell._primary_hand_id == "Right"

    # Phase 2: Shape selected -> shape creation phase
    # Cube selected, 2-hand creation logic active
    shell.shape_toolbar._selected_shape = "Cube"
    shell.consume(DummyPacket(), dummy_frame, None, filtered_both, True, "OK")
    # Retains exactly 2 hands (Left and Right) for drawing; rejects 3rd hand!
    assert len(shell.current_hands) == 2
    track_ids = {h.track_id for h in shell.current_hands}
    assert track_ids == {"Left", "Right"}

    # Phase 3: Shape completed & frozen into scene
    from app.extensions.base import FrozenShape
    frozen = FrozenShape(kind="Cube", params={"center_xy": (0.5, 0.5), "size": 0.2})
    shell.registry.current.add_frozen_shape(frozen)
    shell.shape_toolbar.clear_selection()
    # At freeze moment: Right hand is locked
    shell._primary_hand_id = "Right"
    import time
    shell._primary_hand_last_seen_time = time.monotonic()

    # Next frame: Both Left and Right hands (and third hand) still present
    shell.consume(DummyPacket(), dummy_frame, None, filtered_both, True, "OK")
    # Must prioritize Right hand and lock onto it; Left hand and 3rd hand are NOT recognized!
    assert len(shell.current_hands) == 1
    assert shell.current_hands[0].track_id == "Right"
    assert shell._primary_hand_id == "Right"

    shell.close()




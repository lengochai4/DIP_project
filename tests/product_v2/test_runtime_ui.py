"""Headless-compatible native GUI and real adapter seams with synthetic providers."""

from dataclasses import replace
from types import SimpleNamespace
import numpy as np
import pytest
from PySide6.QtWidgets import QApplication
from app.config import ProductConfig, Settings, ROOT
from app.ui.shell import ProductWindow, PAGES
from app.runtime.hand_runtime import ProductHandRuntime
from dip_touchless.configuration import resolve_config
from dip_touchless.core import FramePacket, ColorSpace


@pytest.fixture(scope="module")
def qt():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def window(qt, tmp_path):
    w = ProductWindow(
        ProductConfig(),
        Settings(geometry_mode="RECORDED"),
        software=True,
        preferences_path=tmp_path / "preferences.json",
    )
    w.show()
    qt.processEvents()
    yield w
    w.close()
    qt.processEvents()


def test_every_page_and_every_lab_renders_and_switches_neutralize(window, qt):
    for name in PAGES:
        window.navigate(name)
        qt.processEvents()
        assert (
            window.page_name == name
            and window.stack.currentWidget() is window.pages[name]
        )
        assert not window.grab().isNull()
    window.navigate("Explore")
    for key in window.registry.extensions:
        window.select_lab(key)
        for mode in ("WORLD", "HAND"):
            window.set_mode(mode)
            qt.processEvents()
            assert not window.viewport.grab().isNull()
            assert window.engine.active is None


def test_mouse_keyboard_construction_and_loss_do_not_leave_stuck_action(window):
    window.navigate("Explore")
    window.select_lab("coordinate")
    window.choose_tool("Distance")
    window.manual("point", (0.5, 0.5))
    window.commit_point()
    assert len(window.registry.current.points) == 1
    window.manual("point", (0.6, 0.5))
    window.commit_point()
    assert len(window.registry.current.constructions) == 1
    window.choose_tool("Inspect")
    initial = window.registry.current.yaw
    window.keyboard_motion(0.1, 0.2)
    assert window.registry.current.yaw == pytest.approx(initial + 0.1)
    assert not window.registry.current.dragging
    window.clear_tracking("lost")
    assert window.viewport.anchor is None and window.viewport.image is None


def test_preferences_error_safety_and_camera_restart_controls(window):
    window.set_preference("mirror", False)
    assert window.settings.mirror is False
    assert window.viewport.settings.mirror is False
    window.camera_error("model missing")
    assert window.engine.active is None
    window.camera_finished()
    assert window.start_button.isEnabled() and not window.stop_button.isEnabled()
    assert "unavailable" in window.tracking_label.text()
    assert window.diagnostics.toPlainText() == "model missing"


def test_tools_are_contextual_and_layout_changes_cancel_clutch(window, qt):
    window.navigate("Explore")
    qt.processEvents()
    assert not window.inspector_dock.isVisible()
    window.show_tools(True)
    assert window.inspector_dock.isVisible() and window.tool_actions.isHidden()
    window.choose_tool("Distance")
    assert not window.tool_actions.isHidden() and window.polygon_button.isHidden()
    assert not window.commit_button.isEnabled()
    window.manual("point", (0.5, 0.5))
    assert window.commit_button.isEnabled()
    window.choose_tool("Inspect")
    window.manual("begin", (0.5, 0.5))
    assert window.registry.current.dragging
    window.show_tools(False)
    assert not window.registry.current.dragging and not window._manual_active


def test_inspect_cannot_commit_measurements_and_completed_work_remains_undoable(window):
    window.navigate("Explore")
    window.manual("point", (0.5, 0.5))
    window.commit_point()
    assert window.registry.current.points == []
    window.choose_tool("Distance")
    for pointer in ((0.5, 0.5), (0.6, 0.5)):
        window.manual("point", pointer)
        window.commit_point()
    window.choose_tool("Inspect")
    assert len(window.registry.current.constructions) == 1
    assert not window.tool_actions.isHidden() and window.undo_button.isEnabled()
    assert window.commit_button.isHidden()
    window.undo()
    assert window.registry.current.constructions == []


def test_environment_guidance_uses_observed_state_and_crowding_priority(window):
    from dip_touchless.core import IlluminationState

    frame = SimpleNamespace(
        illumination=SimpleNamespace(state=IlluminationState.LOW_LIGHT)
    )
    window.navigate("Explore")
    window.manual("begin", (0.5, 0.5))
    assert window.registry.current.dragging
    window.update_environment(frame, "NO_HAND")
    assert not window.registry.current.dragging
    assert "Low light" in window.environment_notice.text()
    window.update_environment(frame, "TOO_MANY_HANDS")
    assert "two hands" in window.environment_notice.text()
    window.update_environment(SimpleNamespace(illumination=None), "TRACKING")
    assert window.environment_notice.isHidden()


def test_manual_and_gesture_commits_with_same_cycle_are_both_kept(window):
    from app.interaction.contracts import GestureIntent, IntentType, Phase, Owner

    window.navigate("Explore")
    window.select_lab("coordinate")
    window.choose_tool("Distance")
    window.manual("point", (0.5, 0.5))
    window.commit_point()  # Manual cycle 1.
    assert len(window.registry.current.points) == 1
    window.deliver(
        GestureIntent(
            IntentType.TOOL_COMMIT,
            Phase.BEGIN,
            world_or_scene_point=(1.0, 0.0, 0.0),
            cycle_id=1,
            tool_id="Distance",
            owner=Owner.TOOL,
        ),
        record=False,
    )
    assert len(window.registry.current.constructions) == 1


def test_native_number_editing_preserves_input_and_restores_shortcuts(window, qt):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QDoubleSpinBox

    window.navigate("Settings")
    editor = window.pages["Settings"].findChild(QDoubleSpinBox)
    editor.setFocus()
    editor.lineEdit().selectAll()
    qt.processEvents()
    assert all(not shortcut.isEnabled() for shortcut in window.shortcuts)
    QTest.keyClick(editor.lineEdit(), Qt.Key.Key_1)
    assert window.page_name == "Settings"
    assert "1" in editor.lineEdit().text()
    window.navigate("Explore")
    window.viewport.setFocus()
    qt.processEvents()
    assert all(shortcut.isEnabled() for shortcut in window.shortcuts)
    QTest.keyClick(window.viewport, Qt.Key.Key_7)
    assert window.page_name == "Help"


@pytest.fixture
def product_feed(window, monkeypatch, tmp_path):
    """Public packet -> GUI -> real intent engine -> active extension, without webcam."""
    from PySide6.QtCore import Qt
    from dip_touchless.core import (
        TrackingFrame,
        TrackingStatus,
        MeasurementQuality,
        FilterDiagnostics,
        FilterMode,
        StageTimings,
    )
    from app.interaction.contracts import HandState, AnchorPose
    import app.ui.shell as shell

    monkeypatch.setattr(shell, "ROOT", tmp_path)
    monkeypatch.setattr(
        QApplication, "applicationState", lambda: Qt.ApplicationState.ApplicationActive
    )
    # This harness drives focus explicitly; unrelated desktop activation events
    # must not interrupt synthetic frames between processEvents() calls.
    QApplication.instance().applicationStateChanged.disconnect(
        window._application_state
    )
    i = 0
    current = {}
    monkeypatch.setattr(
        shell, "describe", lambda label, *args, **kwargs: current[label]
    )

    def feed(
        ratio=1.0,
        pointer=(0.5, 0.5),
        *,
        dt=0.1,
        support_hand=None,
        valid=True,
        pose="POINT",
    ):
        nonlocal i
        current.clear()
        current["Right"] = HandState(
            "Right",
            "DOMINANT",
            pose,
            (False, True, False, False, False),
            pointer,
            AnchorPose((0.65, 0.55), 0.2, 0.0),
            ratio,
        )
        if support_hand is not None:
            current["Left"] = support_hand
        timestamp = feed.timestamp + dt
        feed.timestamp = timestamp
        packet = FramePacket(
            "synthetic-product",
            i,
            timestamp,
            np.zeros((24, 32, 3), np.uint8),
            ColorSpace.BGR,
            "synthetic",
        )
        frame = TrackingFrame(
            "synthetic-product",
            i,
            timestamp,
            TrackingStatus.VALID,
            (),
            (),
            MeasurementQuality.unavailable(),
            None,
            None,
            FilterDiagnostics(
                FilterMode.RAW, None, None, None, None, None, None, None, False
            ),
            StageTimings(0.0, 0.0, 0.0, 0.0, 0.0),
            (),
        )
        # Overlay draws real landmarks only; keep this seam's semantic fixture out of it.
        monkeypatch.setattr(window.analysis_camera, "set_packet", lambda *args: None)
        monkeypatch.setattr(window.calibration_camera, "set_packet", lambda *args: None)
        window.consume(
            packet, frame, None, {label: label for label in current}, valid, "VALID"
        )
        window.viewport.landmarks = {}
        i += 1

    feed.timestamp = 1.0
    return feed


def test_gui_modal_preempts_scene_and_requires_release_to_resume(
    window, qt, product_feed
):
    from PySide6.QtWidgets import QDialog

    window.navigate("Explore")
    product_feed()
    window.engine.pinches["DOMINANT"].reference = 1.0
    for _ in range(4):
        product_feed()
    product_feed(0.3)
    product_feed(0.3, dt=0.3)
    assert window.registry.current.dragging
    dialog = QDialog(window)
    dialog.setModal(True)
    dialog.show()
    qt.processEvents()
    product_feed(0.3, pointer=(0.7, 0.6))
    assert not window.registry.current.dragging
    assert window.engine.active is None and window.viewport.anchor is None
    assert "SYSTEM_MODAL" in window.feedback.text()
    dialog.close()
    qt.processEvents()
    for _ in range(4):
        product_feed(0.3)
    assert not window.registry.current.dragging
    for _ in range(4):
        product_feed()
    product_feed(0.3)
    product_feed(0.3, dt=0.3)
    assert window.registry.current.dragging


def test_mouse_drag_owns_scene_while_camera_frames_continue(window, product_feed):
    window.navigate("Explore")
    product_feed()
    window.manual("begin", (0.5, 0.5))
    assert window.registry.current.dragging and window._manual_active
    product_feed(0.3)
    assert (
        window.registry.current.dragging
    )  # Camera cancellation must not end mouse clutch.
    initial = window.registry.current.yaw
    window.manual("drag", (0.1, 0.0))
    assert window.registry.current.yaw == pytest.approx(initial + 0.1)
    window.manual("release", ())
    assert not window.registry.current.dragging and not window._manual_active
    product_feed(0.3)
    assert not window.registry.current.dragging


@pytest.mark.parametrize("interruption", ["gap", "invalid"])
def test_dwell_selection_requires_a_new_full_window_after_tracking_interruption(
    window, product_feed, monkeypatch, interruption
):
    activated = []
    monkeypatch.setattr(
        window, "ui_target", lambda pointer: ("target", lambda: activated.append(True))
    )
    window.set_preference("dwell_select", True)
    product_feed()
    product_feed()
    for _ in range(3):
        product_feed(dt=0.3)
    assert activated == []
    product_feed(
        dt=1.0 if interruption == "gap" else 0.1, valid=interruption != "invalid"
    )
    product_feed()
    assert activated == []
    for _ in range(5):
        product_feed(dt=0.3)
    assert activated == [True]


def test_modal_cancels_manual_clutch_even_without_camera_frames(window, qt):
    from PySide6.QtWidgets import QDialog

    window.navigate("Explore")
    window.manual("begin", (0.5, 0.5))
    assert window.registry.current.dragging
    dialog = QDialog(window)
    dialog.setModal(True)
    dialog.show()
    qt.processEvents()
    window.tick()
    assert not window.registry.current.dragging and not window._manual_active
    assert not window.shortcuts_allowed()
    dialog.close()
    qt.processEvents()
    window.tick()
    assert not window._modal_blocked


@pytest.mark.parametrize("mode", ["WORLD", "HAND"])
def test_gui_point_cursor_picking_and_dock_coordinates_agree(
    window, qt, product_feed, mode
):
    from PySide6.QtCore import QPoint
    from app.interaction.contracts import HandState, AnchorPose

    window.navigate("Explore")
    window.select_lab("molecule")
    window.set_mode(mode)
    qt.processEvents()
    support = HandState(
        "Left",
        "SUPPORT",
        "OPEN_PALM",
        (True,) * 5,
        (0.25, 0.5),
        AnchorPose((0.5, 0.5), 0.2, 0.0),
        1.0,
    )
    product_feed(support_hand=support)
    product_feed(support_hand=support)
    lab = window.registry.current
    atom = lab.render().balls[0].center
    projection = window.viewport.projection()
    x, y, _ = projection.project(atom)
    origin = window.viewport.mapTo(window, QPoint(0, 0))
    screen_pointer = (
        (origin.x() + x) / window.width(),
        (origin.y() + y) / window.height(),
    )
    local_pointer = (x / window.viewport.width(), y / window.viewport.height())
    assert window.viewport_pointer(screen_pointer) == pytest.approx(local_pointer)
    initial = lab.yaw, lab.pitch, lab.scale
    if mode == "HAND":
        rx, ry, rw, rh = window.viewport.image_rect()
        source_pointer = (1 - (x - rx) / rw, (y - ry) / rh)
    else:
        source_pointer = (1 - screen_pointer[0], screen_pointer[1])
    product_feed(pointer=source_pointer, support_hand=support)
    assert lab.hover == lab.pick(atom) and lab.hover is not None
    assert window.viewport.pointer == pytest.approx(local_pointer)
    assert (lab.yaw, lab.pitch, lab.scale) == initial
    # A native toolbar target and the rendered control cursor use the same screen mapping.
    stop = window.stop_button
    stop.setEnabled(True)
    center = stop.mapTo(window, stop.rect().center())
    pointer = (center.x() / window.width(), center.y() / window.height())
    assert window.ui_target(pointer)[0] is stop
    assert window.viewport.pick_point(window.viewport_pointer(pointer)) is None


def test_bimanual_measure_outside_scene_never_commits_partial_pair(
    window, product_feed
):
    from app.interaction.contracts import HandState, AnchorPose

    window.navigate("Explore")
    window.select_lab("coordinate")
    # Mirrored x=.02 lands outside the scene; dominant pointer remains in it.
    support = HandState(
        "Left",
        "SUPPORT",
        "POINT",
        (False, True, False, False, False),
        (0.98, 0.5),
        AnchorPose((0.25, 0.55), 0.2, 0),
        1.0,
    )
    product_feed(support_hand=support)
    for p in window.engine.pinches.values():
        p.reference = 1.0
    for _ in range(8):
        product_feed(support_hand=support)
    product_feed(0.3, support_hand=support)
    product_feed(0.3, dt=0.3, support_hand=support)
    assert window.registry.current.points == []
    assert window.registry.current.constructions == []


@pytest.mark.parametrize("mirror", [False, True])
@pytest.mark.parametrize("gain", [0.25, 3.0])
def test_hand_cursor_and_pick_follow_camera_tip_with_letterboxing(
    window, qt, product_feed, mirror, gain
):
    window.navigate("Explore")
    window.select_lab("coordinate")
    window.set_preference("mirror", mirror)
    window.set_preference("pointer_sensitivity", gain)
    window.set_mode("HAND")
    qt.processEvents()
    product_feed(pose="OPEN_PALM")
    pointer = (0.3, 0.25)
    product_feed(pointer=pointer)
    assert window.viewport.anchor is not None
    x, y, w, h = window.viewport.image_rect()
    expected = (
        (x + (1 - pointer[0] if mirror else pointer[0]) * w) / window.viewport.width(),
        (y + pointer[1] * h) / window.viewport.height(),
    )
    assert window.viewport.pointer == pytest.approx(expected)
    assert window.registry.current.preview == pytest.approx(
        window.viewport.pick_point(expected)
    )
    assert not window.touch_cursor.isVisible()
    # Tracking loss clears the live anchor, preview and cursor. A point cannot
    # silently reacquire an old palm; opening is required again.
    product_feed(valid=False)
    assert window.viewport.anchor is None and window.viewport.pointer is None
    product_feed(pointer=pointer)
    assert window.viewport.anchor is None and window.registry.current.preview is None


def test_hand_single_palm_can_point_and_commit_geometry_without_disappearing(
    window, product_feed
):
    window.navigate("Explore")
    window.select_lab("coordinate")
    window.choose_tool("Distance")
    window.set_mode("HAND")
    product_feed(pose="OPEN_PALM")
    window.engine.pinches["DOMINANT"].reference = 1.0
    for _ in range(5):
        product_feed(pointer=(0.4, 0.4))
    assert window.registry.current.preview is not None
    product_feed(0.3, pointer=(0.4, 0.4))
    product_feed(0.3, pointer=(0.4, 0.4), dt=0.3)
    assert len(window.registry.current.points) == 1
    assert window.viewport.anchor is not None
    for _ in range(5):
        product_feed(pointer=(0.6, 0.4))
    product_feed(0.3, pointer=(0.6, 0.4))
    product_feed(0.3, pointer=(0.6, 0.4), dt=0.3)
    assert len(window.registry.current.constructions) == 1
    assert window.registry.current.constructions[0][0] == "Distance"
    assert window.viewport.anchor is not None


def test_hand_both_pinches_scale_after_live_open_acquisition(window, product_feed):
    from app.interaction.contracts import HandState, AnchorPose

    window.navigate("Explore")
    window.set_mode("HAND")
    support = HandState(
        "Left",
        "SUPPORT",
        "OPEN_PALM",
        (True,) * 5,
        (0.2, 0.4),
        AnchorPose((0.25, 0.55), 0.2, 0),
        1.0,
    )
    product_feed(pose="OPEN_PALM", support_hand=support)
    support = replace(support, pose="POINT", fingers=(False, True, False, False, False))
    for pinch in window.engine.pinches.values():
        pinch.reference = 1.0
    for _ in range(5):
        product_feed(support_hand=support)
    closed = replace(support, pinch_ratio=0.3)
    product_feed(0.3, support_hand=closed)
    product_feed(0.3, support_hand=closed, dt=0.3)
    assert window.engine.active == "SCALE" and window.viewport.anchor is not None
    product_feed(
        0.3, support_hand=replace(closed, palm=AnchorPose((0.15, 0.55), 0.2, 0))
    )
    assert window.registry.current.scale == pytest.approx(1.25)
    assert window.viewport.anchor is not None


def test_hand_ui_control_is_explicit_exclusive_and_cancels_before_switch(
    window, qt, product_feed
):
    from PySide6.QtCore import QPoint

    window.navigate("Explore")
    window.select_lab("coordinate")
    window.set_mode("HAND")
    qt.processEvents()
    # This source coordinate would reach WORLD's window UI hit. HAND scene
    # instead places it inside the camera and must not activate the toolbar.
    center = window.tools_button.mapTo(window, window.tools_button.rect().center())
    source = (1 - center.x() / window.width(), center.y() / window.height())
    product_feed(pose="OPEN_PALM")
    product_feed(pointer=source)
    assert not window.tools_button.isChecked() and not window.touch_cursor.isVisible()
    assert window.viewport.pointer == pytest.approx(
        window.viewport.source_pointer(source)
    )
    window.set_ui_control(True)
    assert window.viewport.anchor is None and window.registry.current.preview is None
    product_feed(pointer=source)
    product_feed(pointer=source)
    assert window.engine.router.owner is None  # POINT has no clutch lease
    assert window.touch_cursor.isVisible() and window.viewport.pointer is None
    assert window.registry.current.preview is None
    window.set_ui_control(False)
    assert not window.touch_cursor.isVisible()
    assert window.viewport.anchor is None


def test_hand_locked_pair_survives_inspector_expansion_and_pinch_tip_motion(
    window, qt, product_feed
):
    from app.interaction.contracts import HandState, AnchorPose

    window.navigate("Explore")
    window.select_lab("coordinate")
    window.set_mode("HAND")
    support = HandState(
        "Left",
        "SUPPORT",
        "OPEN_PALM",
        (True,) * 5,
        (0.25, 0.4),
        AnchorPose((0.25, 0.55), 0.2, 0),
        1.0,
    )
    product_feed(pose="OPEN_PALM", support_hand=support)
    support = replace(support, pose="POINT", fingers=(False, True, False, False, False))
    for pinch in window.engine.pinches.values():
        pinch.reference = 1.0
    for _ in range(8):
        product_feed(pointer=(0.6, 0.4), support_hand=support)
        qt.processEvents()
    assert window.tools_button.isChecked() and window.viewport.anchor is not None, (
        window.engine.locked_pair,
        window.engine.pair_since,
        window.registry.current.tool,
        window.feedback.text(),
        window.latest_identity,
    )
    assert window.engine.locked_pair is not None
    expected = tuple(
        window.viewport.scene_point(window.viewport.source_pointer(p))
        for p in (support.pointer_xy, (0.6, 0.4))
    )
    product_feed(0.3, pointer=(0.65, 0.43), support_hand=support)
    product_feed(0.3, pointer=(0.65, 0.43), support_hand=support, dt=0.3)
    lab = window.registry.current
    assert len(lab.constructions) == 1
    assert np.asarray(lab.constructions[0][1]) == pytest.approx(np.asarray(expected))
    assert window.viewport.anchor is not None


def test_unknown_hand_pose_keeps_only_observed_presentation_and_blocks_commits(
    window, product_feed
):
    window.navigate("Explore")
    window.select_lab("coordinate")
    window.choose_tool("Distance")
    window.set_mode("HAND")
    product_feed(pose="OPEN_PALM")
    product_feed()
    assert window.registry.current.preview is not None
    product_feed(pose="UNKNOWN")
    assert window.viewport.anchor is not None
    assert window.registry.current.preview is None
    assert window.registry.current.points == []
    assert window.engine.active is None
    assert "Pose unclear" in window.interaction_hint.text()


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
def test_every_lab_accepts_fingertip_inspection_after_single_hand_acquisition(
    window, product_feed, lab_id
):
    window.navigate("Explore")
    window.select_lab(lab_id)
    window.set_mode("HAND")
    product_feed(pose="OPEN_PALM")
    product_feed(pointer=(0.45, 0.4))
    assert window.viewport.anchor is not None
    assert window.registry.current.preview is not None
    assert window.viewport.pointer == pytest.approx(
        window.viewport.source_pointer((0.45, 0.4))
    )


@pytest.mark.parametrize(
    "tool,count",
    [
        ("Distance", 2),
        ("Vector", 2),
        ("Angle", 3),
        ("Plane", 3),
        ("Triangle", 3),
        ("Rectangle", 4),
        ("Quadrilateral", 4),
        ("Polygon", 4),
    ],
)
def test_hand_geometry_tools_commit_camera_aligned_points(
    window, product_feed, tool, count
):
    window.navigate("Explore")
    window.select_lab("coordinate")
    window.choose_tool(tool)
    window.set_mode("HAND")
    product_feed(pose="OPEN_PALM")
    window.engine.pinches["DOMINANT"].reference = 1.0
    expected = ((-0.4, -0.4, 0), (0.4, -0.4, 0), (0.4, 0.4, 0), (-0.4, 0.4, 0))[:count]
    for point in expected:
        px, py, _ = window.viewport.projection().project(point)
        x, y, w, h = window.viewport.image_rect()
        source = (1 - (px - x) / w, (py - y) / h)
        for _ in range(5):
            product_feed(pointer=source)
        product_feed(0.3, pointer=source)
        product_feed(0.3, pointer=source, dt=0.3)
        assert window.viewport.anchor is not None
    lab = window.registry.current
    if tool == "Polygon":
        window.finish_polygon()
    assert not lab.construction_error
    assert len(lab.constructions) == 1 and lab.constructions[0][0] == tool
    assert np.asarray(lab.constructions[0][1]) == pytest.approx(np.asarray(expected))


def test_legacy_rearm_and_scale_preserve_original_additive_semantics(
    window, monkeypatch, tmp_path
):
    from PySide6.QtCore import Qt
    from dip_touchless.core import (
        TrackingFrame,
        TrackingStatus,
        MeasurementQuality,
        FilterDiagnostics,
        FilterMode,
        StageTimings,
        InteractionState,
    )
    import app.ui.shell as shell

    monkeypatch.setattr(shell, "ROOT", tmp_path)
    monkeypatch.setattr(
        QApplication, "applicationState", lambda: Qt.ApplicationState.ApplicationActive
    )
    window.navigate("Explore")
    window.set_preference("engine", "LEGACY")
    lab = window.registry.current
    initial = lab.scale

    def consume(i, active):
        timestamp = 1.0 + i * 0.1
        packet = FramePacket(
            "synthetic-legacy",
            i,
            timestamp,
            np.zeros((24, 32, 3), np.uint8),
            ColorSpace.BGR,
            "synthetic",
        )
        frame = TrackingFrame(
            "synthetic-legacy",
            i,
            timestamp,
            TrackingStatus.VALID,
            (),
            (),
            MeasurementQuality.unavailable(),
            None,
            None,
            FilterDiagnostics(
                FilterMode.RAW, None, None, None, None, None, None, None, False
            ),
            StageTimings(0.0, 0.0, 0.0, 0.0, 0.0),
            (),
        )
        legacy = InteractionState(
            "synthetic-legacy",
            i,
            timestamp,
            True,
            (0.5, 0.5),
            0.3,
            active,
            (0.0, 0.0),
            0.2,
        )
        window.consume(packet, frame, legacy, {}, False, "EXPLICIT_LEGACY")

    consume(0, True)
    assert lab.scale == initial
    consume(1, False)
    assert lab.scale == initial
    consume(2, True)
    assert lab.scale == pytest.approx(initial + 0.2)
    consume(3, True)
    assert lab.scale == pytest.approx(initial + 0.4)


class Provider:
    def __init__(self):
        self.closed = False
        self.calls = []
        self.hands = []

    def detect_for_video(self, image, timestamp):
        self.calls.append((image.numpy_view().copy(), timestamp))
        return SimpleNamespace(
            hand_landmarks=self.hands,
            handedness=[[SimpleNamespace(category_name="Right")] for _ in self.hands],
        )

    def close(self):
        self.closed = True


def test_product_adapter_bgr_mirror_timestamp_no_hand_and_cleanup():
    provider = Provider()
    cfg = resolve_config(ROOT / "config/default.yaml").to_dict()
    cfg["clahe"]["policy"] = "bypass"
    runtime = ProductHandRuntime("unused", cfg, ProductConfig(), landmarker=provider)
    image = np.zeros((24, 32, 3), np.uint8)
    image[:, 0] = (20, 40, 80)
    packet = FramePacket("synthetic", 0, 1.0, image, ColorSpace.BGR, "synthetic")
    assert runtime.process(packet)[0] == {}
    assert provider.calls[0][0][0, -1].tolist() == [80, 40, 20]
    assert np.array_equal(image[:, 0], np.tile([20, 40, 80], (24, 1)))
    assert runtime.process(packet)[2] == "VIDEO_TIMESTAMP_DISCONTINUITY"
    runtime.close()
    runtime.close()
    assert provider.closed
    with pytest.raises(RuntimeError):
        runtime.process(packet)


def test_product_adapter_two_hand_missing_role_and_invalid_geometry():
    provider = Provider()
    cfg = resolve_config(ROOT / "config/default.yaml").to_dict()
    runtime = ProductHandRuntime("unused", cfg, ProductConfig(), landmarker=provider)
    provider.hands = [
        [SimpleNamespace(x=0.5, y=0.5, z=float("nan")) for _ in range(21)]
    ]
    packet = FramePacket(
        "synthetic",
        0,
        1.0,
        np.zeros((24, 32, 3), np.uint8),
        ColorSpace.BGR,
        "synthetic",
    )
    assert runtime.process(packet) == ({}, False, "INVALID_PROVIDER_GEOMETRY")
    runtime.close()


def test_product_adapter_rejects_three_detected_hands_without_exposing_commands():
    provider = Provider()
    provider.hands = [
        [SimpleNamespace(x=0.2 + i * 0.2, y=0.5, z=0.0) for _ in range(21)]
        for i in range(3)
    ]
    runtime = ProductHandRuntime(
        "unused",
        resolve_config(ROOT / "config/default.yaml").to_dict(),
        ProductConfig(),
        landmarker=provider,
    )
    packet = FramePacket(
        "synthetic",
        0,
        1.0,
        np.zeros((24, 32, 3), np.uint8),
        ColorSpace.BGR,
        "synthetic",
    )
    try:
        assert runtime.process(packet) == ({}, False, "TOO_MANY_HANDS")
        assert runtime.filters == {}
    finally:
        runtime.close()


def test_scene_shortcuts_do_not_change_hidden_lab_or_intercept_list_navigation(
    window, qt
):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    lab = window.registry.current
    lab.yaw = 1.2
    for page in ("Home", "Analyze", "Evidence", "Calibrate", "Settings", "Help"):
        window.navigate(page)
        window.stack.setFocus()
        qt.processEvents()
        for key in (Qt.Key.Key_R, Qt.Key.Key_M, Qt.Key.Key_H, Qt.Key.Key_Space):
            QTest.keyClick(window.stack, key)
        assert lab.yaw == 1.2 and lab.tool == "Inspect" and not lab.paused
        assert window.viewport.mode == "WORLD"
    window.navigate("Explore")
    window.library.setFocus()
    qt.processEvents()
    before = window.library.currentRow()
    QTest.keyClick(window.library, Qt.Key.Key_Down)
    assert window.library.currentRow() == before + 1


def test_reset_view_keeps_measurements_parameters_and_animation_state(window):
    window.navigate("Explore")
    lab = window.registry.current
    lab.constructions = [("Distance", ((0, 0, 0), (1, 0, 0)))]
    lab.parameters["radius"] = 4
    lab.paused = True
    lab.yaw, lab.scale = 1.5, 3
    window.reset_view()
    assert lab.yaw == 0.35 and lab.scale == 1
    assert lab.constructions and lab.parameters["radius"] == 4 and lab.paused


def test_manual_hand_drag_preserves_observed_anchor_until_actual_loss(window):
    from app.interaction.contracts import AnchorPose

    window.navigate("Explore")
    window.set_mode("HAND")
    anchor = AnchorPose((0.5, 0.5), 0.2, 0)
    window.viewport.anchor = window.anchor.pose = anchor
    yaw = window.registry.current.yaw
    window.manual("begin", (0.5, 0.5))
    assert window.viewport.anchor is anchor
    window.manual("drag", (0.1, 0))
    assert window.registry.current.yaw == pytest.approx(yaw + 0.1)
    window.viewport.anchor = None
    window.manual("release", ())
    assert not window._manual_active and not window.registry.current.dragging


def test_actual_hand_anchor_loss_cancels_mouse_clutch(window, product_feed):
    from app.interaction.contracts import HandState, AnchorPose

    window.navigate("Explore")
    window.set_mode("HAND")
    support = HandState(
        "Left",
        "SUPPORT",
        "OPEN_PALM",
        (True,) * 5,
        (0.25, 0.5),
        AnchorPose((0.5, 0.5), 0.2, 0),
        1.0,
    )
    product_feed(support_hand=support)
    window.manual("begin", (0.5, 0.5))
    product_feed(valid=False)
    assert window.viewport.anchor is None
    assert not window._manual_active and not window.registry.current.dragging


@pytest.mark.parametrize("operation", ["keyboard_rotate", "keyboard_scale", "commit"])
def test_manual_hand_operations_keep_presentation_but_context_reset_still_clears_it(
    window, operation
):
    from app.interaction.contracts import AnchorPose

    window.navigate("Explore")
    window.set_mode("HAND")
    if operation == "commit":
        window.choose_tool("Distance")
        window.registry.current.preview = (1, 1, 0)
    anchor = AnchorPose((0.5, 0.5), 0.2, 0)
    window.viewport.anchor = window.anchor.pose = anchor
    if operation == "keyboard_rotate":
        window.keyboard_motion(0.1, 0)
    elif operation == "keyboard_scale":
        window.keyboard_scale(1.1)
    else:
        window.commit_point()
        assert len(window.registry.current.points) == 1
    assert window.viewport.anchor is anchor
    window.cancel(clear_reference=True, preserve_presentation=True)
    assert window.viewport.anchor is None and window.anchor.pose is None


def test_tracking_stop_clears_stale_ready_status_on_home_and_analyze(
    window, product_feed
):
    product_feed()
    assert window.last_tracking is not None
    window.clear_tracking("Camera stopped")
    assert window.last_tracking is None and window.latest_identity is None
    assert "Camera stopped" in window.home_status.text()
    assert "READY" not in window.home_status.text()
    assert window.diagnostics.toPlainText() == "Camera stopped"


def test_hand_without_anchor_blocks_mouse_keyboard_and_gesture_scene_work(
    window, product_feed
):
    window.navigate("Explore")
    window.set_mode("HAND")
    window.choose_tool("Distance")
    yaw = window.registry.current.yaw
    window.keyboard_motion(0.1, 0.1)
    window.keyboard_scale(2)
    assert window.registry.current.yaw == yaw and window.registry.current.scale == 1
    window.manual("begin", (0.5, 0.5))
    assert window.registry.current.points == [] and not window._manual_active
    assert window.viewport.pick_viewport((0.5, 0.5)) is None
    assert window.viewport.scene_point((0.5, 0.5)) is None
    product_feed()
    window.engine.pinches["DOMINANT"].reference = 1.0
    for _ in range(4):
        product_feed()
    product_feed(0.3)
    product_feed(0.3, dt=0.3)
    assert not window.registry.current.dragging and window.registry.current.points == []


def test_calibration_recapture_and_source_changes_clear_old_validation(
    window, product_feed
):
    window.navigate("Calibrate")
    product_feed()
    window.calibration_checks = {"cycle", "point", "open"}
    window._calibration_previous_active = True
    window.begin_calibration()
    assert not window.calibration_checks and not window._calibration_previous_active
    for _ in range(16):
        product_feed()
    assert window.engine.pinches["DOMINANT"].reference == pytest.approx(1)
    window.next_calibration()
    assert window.calibration_step == 2
    for _ in range(5):
        product_feed()
    product_feed(0.3)
    product_feed(0.3, dt=0.3)
    assert window._calibration_previous_active
    product_feed(valid=False)
    for _ in range(5):
        product_feed()
    assert "cycle" not in window.calibration_checks
    window.calibration_checks.add("cycle")
    window.set_preference("dominant_hand", "Left")
    assert window.calibration_step == 0 and not window.calibration_checks


def test_calibration_support_only_and_legacy_do_not_claim_readiness(
    window, product_feed
):
    from dataclasses import replace

    window.navigate("Calibrate")
    product_feed()
    window.current_hands = (replace(window.current_hands[0], role="SUPPORT"),)
    window.begin_calibration()
    assert window.calibration_step == 0
    assert "dominant hand" in window.feedback.text()
    window.set_preference("engine", "LEGACY")
    assert (
        not window.capture_button.isEnabled()
        and not window.calibration_next.isEnabled()
    )


@pytest.mark.parametrize("operation", ["open", "write", "close"])
def test_product_journal_failure_is_explicit_and_does_not_break_ui(
    window, product_feed, monkeypatch, operation
):
    from pathlib import Path

    window.navigate("Analyze")
    if operation == "open":
        monkeypatch.setattr(
            Path,
            "mkdir",
            lambda *args, **kwargs: (_ for _ in ()).throw(OSError("disk unavailable")),
        )
    else:

        class FailedLog:
            def write(self, text):
                if operation == "write":
                    raise OSError("disk full")

            def close(self):
                if operation == "close":
                    raise OSError("flush failed")

        window._journal = FailedLog()
    product_feed()
    if operation == "close":
        window.close_journal()
    assert window._journal_failed and window._journal is None
    assert "incomplete" in window._journal_error
    product_feed()
    assert "incomplete" in window.diagnostics.toPlainText()
    window.navigate("Explore")
    initial = window.registry.current.yaw
    window.keyboard_motion(0.1, 0)
    assert window.registry.current.yaw == pytest.approx(initial + 0.1)


def test_visual_and_developer_settings_change_visible_output_and_controls(
    window, product_feed
):
    window.navigate("Analyze")
    product_feed()
    assert (
        "PINCH" in window.feedback.text()
        and '"intent"' not in window.diagnostics.toPlainText()
    )
    window.set_preference("gesture_labels", False)
    window.set_preference("diagnostics", True)
    assert not window.preference_controls["gesture_labels"].isChecked()
    product_feed()
    assert (
        "PINCH" not in window.feedback.text()
        and '"intent"' in window.diagnostics.toPlainText()
    )


def test_measurement_export_uses_explicit_destination_without_camera_data(
    window, tmp_path, monkeypatch
):
    from PySide6.QtWidgets import QFileDialog

    window.registry.current.constructions = [("Distance", ((0, 0, 0), (3, 4, 0)))]
    path = tmp_path / "measurements.csv"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *args: (str(path), "CSV (*.csv)")
    )
    window.export_measurements()
    content = path.read_text(encoding="utf-8-sig")
    assert "distance_scene_units" in content and "5.0" in content
    assert "landmarks" not in content and "run_id" not in content


def test_native_button_space_activates_button_without_pausing_scene(window, qt):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    window.navigate("Explore")
    window.tools_button.setFocus()
    qt.processEvents()
    QTest.keyClick(window.tools_button, Qt.Key.Key_Space)
    assert window.tools_button.isChecked() and not window.registry.current.paused


def test_wave_parameters_allow_zero_phase_and_integer_sample_count(window):
    from PySide6.QtWidgets import QSpinBox, QDoubleSpinBox

    window.select_lab("wave")
    sample = window.parameter_panel.findChild(QSpinBox)
    assert sample.minimum() == 4 and sample.maximum() == 128
    phase = window.parameter_form.itemAt(
        2, window.parameter_form.ItemRole.FieldRole
    ).widget()
    assert isinstance(phase, QDoubleSpinBox) and phase.minimum() == 0
    phase.setValue(0)
    sample.setValue(64)
    assert window.registry.current.parameters["phase"] == 0
    assert window.registry.current.parameters["samples"] == 64


def test_scene_preset_and_parameter_controls_match_programmatic_state(window):
    window.select_lab("optics")
    assert window.library.currentRow() == tuple(window.registry.extensions).index(
        "optics"
    )
    window.choose_preset("Lens")
    assert window.preset_select.currentText() == "Lens"
    window.choose_tool("Distance")
    assert window.tool_select.currentText() == "Distance"
    window.set_parameter("focal", 2.5)
    assert window.parameter_controls["focal"].value() == 2.5


def test_optional_grid_snap_builds_a_true_rectangle_from_imprecise_free_points(window):
    window.navigate("Explore")
    window.select_lab("coordinate")
    window.choose_tool("Rectangle")
    window.set_preference("construction_snap", True)
    assert window.snap_control.isChecked()
    for point in ((0.26, 0.51, 0), (1.02, 0.49, 0), (1.03, 1.02, 0), (0.24, 0.99, 0)):
        x, y, _ = window.viewport.projection().project(point)
        window.manual(
            "point", (x / window.viewport.width(), y / window.viewport.height())
        )
        window.commit_point()
    lab = window.registry.current
    assert len(lab.constructions) == 1 and lab.is_rectangle(lab.constructions[0][1])


def test_snap_preserves_tilted_construction_plane_and_exact_atom_centres(window):
    from app.interaction.contracts import AnchorPose

    window.select_lab("coordinate")
    window.choose_tool("Distance")
    window.set_preference("construction_snap", True)
    window.viewport.reference_plane = AnchorPose(
        (0.5, 0.5), 0.2, 0, pitch_rad=0.4, yaw_rad=0.3
    )
    point = window.viewport.scene_point((0.65, 0.45))
    assert np.dot(point, window.viewport.plane_normal()) == pytest.approx(0, abs=1e-10)
    window.select_lab("molecule")
    window.choose_tool("Distance")
    atom = window.registry.current.atoms()[0][1]
    x, y, _ = window.viewport.projection().project(atom.center)
    assert (
        window.viewport.pick_viewport(
            (x / window.viewport.width(), y / window.viewport.height())
        )
        == atom.center
    )


def test_late_gpu_failure_switches_to_software_and_cancels_drag(qt, tmp_path):
    from app.rendering.viewport import SoftwareViewport

    window = ProductWindow(
        ProductConfig(), Settings(), preferences_path=tmp_path / "preferences.json"
    )
    window.show()
    window.navigate("Explore")
    qt.processEvents()
    try:
        window.manual("begin", (0.5, 0.5))
        window.viewport.gpu_error = "simulated context failure"
        window.tick()
        assert isinstance(window.viewport, SoftwareViewport)
        assert not window.registry.current.dragging and not window._manual_active
    finally:
        window.close()
        qt.processEvents()

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
        Settings(),
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
    i = 0
    current = {}
    monkeypatch.setattr(
        shell, "describe", lambda label, *args, **kwargs: current[label]
    )

    def feed(ratio=1.0, pointer=(0.5, 0.5), *, dt=0.1, support_hand=None):
        nonlocal i
        current.clear()
        current["Right"] = HandState(
            "Right",
            "DOMINANT",
            "POINT",
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
            packet, frame, None, {label: label for label in current}, True, "VALID"
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
    product_feed(
        pointer=(1 - screen_pointer[0], screen_pointer[1]), support_hand=support
    )
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

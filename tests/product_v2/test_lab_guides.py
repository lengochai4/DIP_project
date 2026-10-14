"""Native guide/layout transitions, persistence and input safety without a webcam."""

import json
import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from app.config import ProductConfig, Settings
from app.ui.shell import ProductWindow


@pytest.fixture
def window(tmp_path):
    qt = QApplication.instance() or QApplication([])
    w = ProductWindow(
        ProductConfig(),
        Settings(),
        software=True,
        preferences_path=tmp_path / "preferences.json",
    )
    w.show()
    w.navigate("Explore")
    qt.processEvents()
    yield w, qt
    w.close()
    qt.processEvents()


@pytest.mark.parametrize(
    "lab_id",
    (
        "coordinate",
        "molecule",
        "orbital",
        "vector",
        "surface",
        "wave",
        "vector-field",
        "optics",
        "crystal",
    ),
)
def test_context_guide_tracks_lab_preset_view_and_owner(window, lab_id):
    w, qt = window
    w.select_lab(lab_id)
    for preset in w.registry.current.presets:
        w.choose_preset(preset)
        assert w.guide_text.toPlainText().startswith(
            f"{w.registry.current.title} · {preset}"
        )
        assert "TƯƠNG TÁC HIỆN TẠI\nLIVE:" in w.guide_text.toPlainText()
    w.set_mode("HAND")
    assert "GÓC NHÌN\nHAND:" in w.guide_text.toPlainText()
    w.set_ui_control(True)
    assert "Control UI đang bật" in w.guide_text.toPlainText()
    w.set_preference("geometry_mode", "RECORDED")
    assert "TƯƠNG TÁC HIỆN TẠI\nRECORDED:" in w.guide_text.toPlainText()
    w.set_preference("engine", "LEGACY")
    assert "TƯƠNG TÁC HIỆN TẠI\nLEGACY / WORLD:" in w.guide_text.toPlainText()
    assert "GÓC NHÌN\nWORLD:" in w.guide_text.toPlainText()
    assert w.worker is None


def test_guide_visibility_is_persistent_and_exclusive_with_tools(window):
    w, qt = window
    assert w.guide_dock.isVisible() and w.guide_button.isChecked()
    w.guide_button.click()
    assert not w.guide_dock.isVisible()
    assert Settings.load(w.preferences_path).lab_guide is False
    w.show_tools(True)
    w.guide_button.click()
    assert w.guide_dock.isVisible() and not w.inspector_dock.isVisible()
    assert not w.tools_button.isChecked()
    assert Settings.load(w.preferences_path).lab_guide is True
    w.show_tools(True)
    assert not w.guide_dock.isVisible() and not w.guide_button.isChecked()
    assert w.inspector_dock.isVisible()
    w.navigate("Home")
    assert not w.guide_dock.isVisible() and not w.inspector_dock.isVisible()


@pytest.mark.parametrize("panel", ("guide", "tools", "none"))
def test_expansion_grows_viewport_and_restores_prior_layout_without_erasing_work(
    window, panel
):
    w, qt = window
    if panel == "tools":
        w.show_tools(True)
    elif panel == "none":
        w.show_guide(False)
    qt.processEvents()
    before = w.viewport.size()
    lab = w.registry.current
    work = [("Distance", ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)))]
    lab.constructions = work.copy()
    lab.yaw, lab.pitch, lab.scale = 0.7, 0.4, 1.2
    w.manual("begin", (0.5, 0.5))
    assert lab.dragging
    w.expand_button.click()
    qt.processEvents()
    assert w._expanded and w.expand_button.text() == "Thu gọn"
    assert w.navigation_dock.isHidden() and w.library.isHidden()
    assert w.guide_dock.isHidden() and w.inspector_dock.isHidden()
    assert w.viewport.width() > before.width()
    assert w.viewport.height() >= before.height()
    assert not lab.dragging and not w._manual_active
    assert lab.constructions == work
    assert (lab.yaw, lab.pitch, lab.scale) == (0.7, 0.4, 1.2)
    guide_preference = w.settings.lab_guide
    w.show_guide(True)  # Temporary help does not overwrite the layout preference.
    assert w.guide_dock.isVisible()
    assert w.settings.lab_guide == guide_preference
    w.escape_explore()
    qt.processEvents()
    assert not w._expanded and w.expand_button.text() == "Phóng to"
    assert w.navigation_dock.isVisible() and w.library.isVisible()
    assert w.guide_dock.isVisible() == (panel == "guide")
    assert w.inspector_dock.isVisible() == (panel == "tools")
    assert lab.constructions == work
    assert (lab.yaw, lab.pitch, lab.scale) == (0.7, 0.4, 1.2)


def test_guide_shortcuts_page_exit_and_native_editing(window):
    w, qt = window
    w.activateWindow()
    w.viewport.setFocus()
    qt.processEvents()
    QTest.keyClick(w.viewport, Qt.Key.Key_G)
    assert not w.guide_dock.isVisible()
    QTest.keyClick(
        w.viewport,
        Qt.Key.Key_F,
        Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier,
    )
    assert w._expanded
    QTest.keyClick(w.viewport, Qt.Key.Key_Escape)
    assert not w._expanded
    w.set_expanded(True)
    w.navigate("Settings")
    assert not w._expanded and w.navigation_dock.isVisible()
    editor = w.preference_controls["pointer_sensitivity"]
    editor.setFocus()
    qt.processEvents()
    assert all(not s.isEnabled() for s in w.shortcuts)
    w.navigate("Explore")
    assert not w.expand_button.isChecked()


def test_hidden_library_does_not_capture_window_pointer(window):
    w, qt = window
    w.set_expanded(True)
    qt.processEvents()
    # Move the hidden list over the visible viewport to exercise the stale-hit path.
    w.library.move(w.viewport.pos())
    point = w.library.viewport().mapTo(w, QPoint(30, 30))
    target, callback = w.ui_target((point.x() / w.width(), point.y() / w.height()))
    assert target is None and callback is None


def test_reading_guide_keeps_arrow_keys_for_native_scroll(window):
    w, qt = window
    w.guide_text.setFocus()
    qt.processEvents()
    shortcuts = {s.key().toString(): s for s in w.shortcuts}
    assert not shortcuts["Down"].isEnabled()
    assert not shortcuts["Space"].isEnabled()
    assert shortcuts["G"].isEnabled() and shortcuts["Ctrl+Shift+F"].isEnabled()
    before = (w.registry.current.yaw, w.registry.current.pitch)
    QTest.keyClick(w.guide_text, Qt.Key.Key_Down)
    assert (w.registry.current.yaw, w.registry.current.pitch) == before


@pytest.mark.parametrize(
    "preset, visible",
    (
        ("Reflection", set()),
        ("Mirror", set()),
        ("Refraction", {"index"}),
        ("Lens", {"focal"}),
    ),
)
def test_optics_only_displays_parameters_used_by_selected_preset(
    window, preset, visible
):
    w, qt = window
    w.select_lab("optics")
    w.show_tools(True)
    w.choose_preset(preset)
    assert {
        key for key, control in w.parameter_controls.items() if not control.isHidden()
    } == visible
    assert all(control.toolTip() for control in w.parameter_controls.values())


def test_old_preferences_default_to_guide_and_nonboolean_is_rejected(tmp_path):
    path = tmp_path / "old.json"
    path.write_text(json.dumps({"geometry_mode": "LIVE"}), encoding="utf-8")
    assert Settings.load(path).lab_guide is True
    with pytest.raises(ValueError, match="lab_guide must be boolean"):
        Settings(lab_guide=1)

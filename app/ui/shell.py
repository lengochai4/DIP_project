"""New native product shell: Explore, Analyze, Evidence, Calibrate, Settings, Help."""

from dataclasses import asdict, replace
import html
import json
import math
import time
import numpy as np
from PySide6.QtCore import Qt, QTimer, QPoint, Signal
from PySide6.QtGui import QKeySequence, QShortcut, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QListWidget,
    QDockWidget,
    QTextBrowser,
    QComboBox,
    QCheckBox,
    QDoubleSpinBox,
    QSpinBox,
    QFormLayout,
    QScrollArea,
    QGroupBox,
    QToolBar,
    QAbstractButton,
    QAbstractSpinBox,
    QLineEdit,
    QTextEdit,
    QFileDialog,
    QMessageBox,
)
from app.config import ROOT, Settings
from app.extensions.registry import ExtensionRegistry
from app.interaction.contracts import (
    GestureIntent as Intent,
    IntentType as Type,
    Phase,
    Owner,
)
from app.interaction.engine import IntentEngine
from app.interaction.hand_geometry import describe
from app.rendering.hand_anchor import HandAnchor
from app.rendering.viewport import Viewport, SoftwareViewport, bgr_image
from app.runtime.application_runtime import RuntimeWorker
from .camera import CameraWidget
from .theme import STYLE
from .lab_guides import PARAMETER_HINTS, guide_text

PAGES = ("Home", "Explore", "Analyze", "Evidence", "Calibrate", "Settings", "Help")


def heading(layout, title, subtitle=""):
    label = QLabel(title)
    label.setObjectName("Title")
    layout.addWidget(label)
    if subtitle:
        label = QLabel(subtitle)
        label.setObjectName("Subtitle")
        label.setWordWrap(True)
        layout.addWidget(label)


def button(layout, title, callback, *, checkable=False):
    control = QPushButton(title)
    control.setCheckable(checkable)
    control.clicked.connect(callback)
    layout.addWidget(control)
    return control


def page():
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(28, 24, 28, 24)
    layout.setSpacing(16)
    return widget, layout


class ProductWindow(QMainWindow):
    def __init__(self, config, settings=None, *, software=False, preferences_path=None):
        super().__init__()
        self.config = config
        self.preferences_path = (
            preferences_path or ROOT / "runs/product-v2/preferences.json"
        )
        self.settings = settings or Settings.load(self.preferences_path)
        self.registry = ExtensionRegistry(config)
        for lab in self.registry.extensions.values():
            lab.live_enabled = self.live_mode()
        self.engine = IntentEngine(config)
        self.anchor = HandAnchor(config)
        self.worker = None
        self._camera_failure = None
        self.page_name = "Home"
        self.epoch = 0
        self.last_frame_time = None
        self.latest_identity = None
        self.last_tracking = None
        self.current_hands = ()
        self.calibration_step = 0
        self.calibration_checks = set()
        self._calibration_previous_active = False
        self._journal = None
        self._journal_failed = False
        self._journal_error = None
        self._manual_cycle = 0
        self._manual_active = False
        self._modal_blocked = False
        self._legacy_rearm = True
        self._dwell_target = self._dwell_since = None
        self._ui_cycle = None
        self._ui_hover = None
        self._pose_checks_since = {}
        self._last_tick = time.monotonic()
        self._expanded = False
        self._expanded_panels = None
        self.setWindowTitle("DIP Touchless STEM · V2")
        self.resize(1440, 900)
        self.setMinimumSize(1040, 680)
        self.setStyleSheet(STYLE)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        toolbar = QToolBar("Session")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        brand = QLabel("DIP TOUCHLESS STEM")
        brand.setStyleSheet("font-size: 19px; font-weight: 600; padding: 6px;")
        toolbar.addWidget(brand)
        spacer = QWidget()
        spacer.setSizePolicy(
            spacer.sizePolicy().Policy.Expanding, spacer.sizePolicy().Policy.Preferred
        )
        toolbar.addWidget(spacer)
        self.tracking_label = QLabel("Camera stopped")
        toolbar.addWidget(self.tracking_label)
        self.start_button = QPushButton("Start camera")
        self.start_button.clicked.connect(self.start_camera)
        toolbar.addWidget(self.start_button)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_camera)
        self.stop_button.setEnabled(False)
        toolbar.addWidget(self.stop_button)
        self.navigation = QListWidget()
        self.navigation.addItems(PAGES)
        self.navigation.setMinimumWidth(145)
        self.navigation.setMaximumWidth(180)
        self.navigation_dock = QDockWidget("Navigation", self)
        self.navigation_dock.setFeatures(
            QDockWidget.DockWidgetFeature.NoDockWidgetFeatures
        )
        self.navigation_dock.setWidget(self.navigation)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.navigation_dock)
        self.navigation.currentRowChanged.connect(
            lambda index: (
                self.navigate(PAGES[index]) if 0 <= index < len(PAGES) else None
            )
        )
        self.pages = {}
        self._home()
        self._explore(software)
        self._analyze()
        self._evidence()
        self._calibration()
        self._settings()
        self._help()
        self._inspector()
        self._lab_guide()
        self.feedback = QLabel(
            "LIVE: extend any fingertips on one or two hands to create geometry automatically."
            if self.live_mode()
            else "POINT: inspect   ·   PINCH: manipulate   ·   OPEN PALM: present   ·   V-SIGN: measure"
        )
        self.statusBar().addWidget(self.feedback, 1)
        self._shortcuts()
        QApplication.instance().focusChanged.connect(self.refresh_shortcuts)
        self.navigation.setCurrentRow(0)
        self.touch_cursor = QLabel(self)
        self.touch_cursor.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.touch_cursor.setFixedSize(22, 22)
        self.touch_cursor.setStyleSheet(
            "background: transparent; border: 2px solid #efca82; border-radius: 11px;"
        )
        self.touch_cursor.hide()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)
        QApplication.instance().applicationStateChanged.connect(self._application_state)

    def _add(self, name, widget):
        self.pages[name] = widget
        self.stack.addWidget(widget)

    def _home(self):
        widget, layout = page()
        heading(
            layout,
            "See. Interact. Learn.",
            "Explore STEM ideas in a spatial workspace. Use your hands, or the familiar mouse and keyboard.",
        )
        row = QHBoxLayout()
        layout.addLayout(row)
        button(row, "Continue exploring", lambda: self.navigate("Explore"))
        button(row, "Calibrate hands", lambda: self.navigate("Calibrate"))
        self.home_status = QLabel(
            "Tracking: stopped   ·   Live geometry: no pinch calibration needed   ·   Mouse controls: available"
        )
        self.home_status.setWordWrap(True)
        layout.addWidget(self.home_status)
        group = QGroupBox("STEM labs")
        grid = QGridLayout(group)
        for i, lab in enumerate(self.registry.extensions.values()):
            card = QPushButton(lab.title + "\n" + lab.category)
            card.setMinimumHeight(88)
            card.clicked.connect(lambda checked=False, key=lab.id: self.open_lab(key))
            grid.addWidget(card, i // 3, i % 3)
        layout.addWidget(group)
        self.recent = QLabel("Recent session: none in this launch")
        layout.addWidget(self.recent)
        layout.addStretch()
        self._add("Home", widget)

    def _explore(self, software):
        widget, layout = page()
        layout.setContentsMargins(16, 16, 16, 16)
        row = QHBoxLayout()
        layout.addLayout(row)
        self.lab_title = QLabel(self.registry.current.title)
        self.lab_title.setObjectName("Title")
        self.lab_title.setWordWrap(True)
        row.addWidget(self.lab_title, 1)
        self.guide_button = button(row, "Hướng dẫn", self.show_guide, checkable=True)
        self.guide_button.setChecked(self.settings.lab_guide)
        self.guide_button.setToolTip("Ẩn/hiện cách dùng lab đang mở (G)")
        self.expand_button = button(row, "Phóng to", self.set_expanded, checkable=True)
        self.expand_button.setToolTip(
            "Mở rộng khung mô hình; thu các bảng phụ (Ctrl+Shift+F)"
        )
        row = QHBoxLayout()
        layout.addLayout(row)
        self.world_button = button(
            row, "WORLD", lambda: self.set_mode("WORLD"), checkable=True
        )
        self.hand_button = button(
            row, "HAND", lambda: self.set_mode("HAND"), checkable=True
        )
        self.world_button.setChecked(True)
        self.hand_button.setEnabled(self.settings.engine == "PRODUCT")
        self.ui_control_button = button(
            row, "Control UI", self.set_ui_control, checkable=True
        )
        self.ui_control_button.setToolTip(
            "HAND: switch between fingertip-aligned scene interaction and window UI control"
        )
        self.ui_control_button.setVisible(self.live_mode())
        self.tools_button = button(row, "Tools", self.show_tools, checkable=True)
        button(row, "Reset view", self.reset_view)
        self.environment_notice = QLabel()
        self.environment_notice.setWordWrap(True)
        self.environment_notice.setStyleSheet(
            "color: #efca82; padding: 8px; background: #243039;"
        )
        self.environment_notice.hide()
        layout.addWidget(self.environment_notice)
        self.interaction_hint = QLabel()
        self.interaction_hint.setWordWrap(True)
        self.interaction_hint.setVisible(self.live_mode())
        self.interaction_hint.setText(
            "Live geometry follows all extended fingertips on either hand. No Add point or pinch is needed."
        )
        layout.addWidget(self.interaction_hint)
        body = QHBoxLayout()
        layout.addLayout(body, 1)
        self.viewport_layout = body
        self.library = QListWidget()
        self.library.setFixedWidth(175)
        for lab in self.registry.extensions.values():
            self.library.addItem(lab.title.replace(" Lab", ""))
        self.library.setCurrentRow(1)
        self.library.currentRowChanged.connect(
            lambda i: (
                self.select_lab(tuple(self.registry.extensions)[i]) if i >= 0 else None
            )
        )
        body.addWidget(self.library)
        cls = SoftwareViewport if software else Viewport
        self.viewport = cls(self.registry, self.config, self.settings)
        self.viewport.manual.connect(self.manual)
        body.addWidget(self.viewport, 1)
        self._add("Explore", widget)

    def _analyze(self):
        widget, layout = page()
        heading(
            layout,
            "Analyze",
            "Live processing diagnostics. Frozen experiment findings have their own Evidence page.",
        )
        pipeline = QLabel(
            "Camera  →  ROI  →  Illumination  →  Preprocess  →  Provider  →  Filter  →  Hand geometry  →  Intent"
        )
        pipeline.setWordWrap(True)
        layout.addWidget(pipeline)
        row = QHBoxLayout()
        layout.addLayout(row, 1)
        self.analysis_camera = CameraWidget()
        self.analysis_camera.analyze = True
        row.addWidget(self.analysis_camera, 2)
        self.diagnostics = QTextBrowser()
        row.addWidget(self.diagnostics, 1)
        self.diagnostics.setPlainText(
            "Start camera to inspect the processing pipeline. Core raw: coral; Core filtered (F0): cyan; product F1: violet; ROI: amber."
        )
        self._add("Analyze", widget)

    def _evidence(self):
        from extensions.stem3d.evidence.presentation import load_evidence_catalog

        self.catalog = load_evidence_catalog()
        widget, layout = page()
        heading(
            layout, "Evidence", "Frozen G7 results · read-only · no experiment reruns"
        )
        self.evidence_select = QComboBox()
        self.evidence_select.addItems(
            (
                "G7 Overview",
                "A1 Static",
                "A2 Dynamic",
                "B Normal",
                "B Low-light",
                "RQ3",
                "Limitations",
                "Provenance",
            )
        )
        layout.addWidget(self.evidence_select)
        self.evidence_text = QTextBrowser()
        layout.addWidget(self.evidence_text, 1)
        self.evidence_image = QLabel()
        self.evidence_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.evidence_image, 2)
        self.evidence_select.currentIndexChanged.connect(self.refresh_evidence)
        self.refresh_evidence(0)
        self._add("Evidence", widget)

    def refresh_evidence(self, index):
        c = self.catalog.content
        fields = (
            (
                "overview_rq1_setup",
                "overview_rq1_result",
                "overview_rq1_limitation",
                "overview_a1_result",
                "overview_a2_status",
                "overview_a2_reason",
                "overview_rq3_claim_boundary",
            ),
            ("a1_result", "a1_caution"),
            ("a2_status", "a2_reason", "a2_summary", "a2_zero_boundary"),
            ("b_normal_result", "b_no_improvement", "b_clahe_limitation"),
            ("b_lowlight_result", "b_no_improvement", "b_clahe_limitation"),
            (
                "rq3_rotation",
                "rq3_scaling_and_states",
                "rq3_false_positive",
                "rq3_claim_boundary",
            ),
            (
                "overview_rq1_limitation",
                "a1_caution",
                "a2_reason",
                "b_clahe_limitation",
                "rq3_claim_boundary",
            ),
            (),
        )
        values = [getattr(c, k) for k in fields[index]]
        if index == 7:
            values = [
                f"Release: {self.catalog.release_tag}",
                f"Release commit: {self.catalog.release_commit}",
                f"Live demo run: {self.catalog.live_demo_run_id}",
                f"Live execution revision: {self.catalog.live_demo_revision}",
                "Execution revision and release commit are distinct. V2 does not replace or extend these research results.",
            ]
        self.evidence_text.setPlainText("\n\n".join(values))
        asset = {
            1: "a1_static_jitter",
            2: "a2_unavailable",
            3: "b_normal",
            4: "b_lowlight",
        }.get(index)
        image = self.catalog.load_image(asset) if asset else None
        self.evidence_image.clear()
        if image is not None:
            pix = QPixmap.fromImage(bgr_image(image))
            self.evidence_image.setPixmap(
                pix.scaled(
                    900,
                    370,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self.evidence_image.setText(
                "Asset unavailable"
                if asset
                else "Frozen provenance and limitations remain unchanged."
            )

    def _calibration(self):
        widget, layout = page()
        heading(
            layout,
            "Calibration center",
            "A comfortable release reference makes deliberate pinch observable. Calibrate each hand you plan to use.",
        )
        self.calibration_progress = QLabel()
        layout.addWidget(self.calibration_progress)
        self.calibration_camera = CameraWidget()
        layout.addWidget(self.calibration_camera, 1)
        self.calibration_message = QLabel()
        self.calibration_message.setWordWrap(True)
        layout.addWidget(self.calibration_message)
        row = QHBoxLayout()
        layout.addLayout(row)
        self.capture_button = button(
            row, "Capture comfortable release", self.begin_calibration
        )
        self.calibration_next = button(row, "Next", self.next_calibration)
        button(row, "Restart calibration", self.restart_calibration)
        button(row, "Cancel / Back", lambda: self.navigate("Home"))
        self.refresh_calibration()
        self._add("Calibrate", widget)

    def restart_calibration(self):
        self.cancel(clear_reference=True)
        self.calibration_step = 0
        self.calibration_checks.clear()
        self._pose_checks_since.clear()
        self.refresh_calibration()

    def begin_calibration(self):
        if self.settings.engine != "PRODUCT":
            self.feedback.setText("Select PRODUCT in Settings to calibrate hands.")
            return
        self.cancel(clear_reference=True)
        self.calibration_checks.clear()
        self._pose_checks_since.clear()
        self._calibration_previous_active = False
        roles = {h.role for h in self.current_hands}
        if "DOMINANT" not in roles:
            self.calibration_step = 0
            self.refresh_calibration()
            self.feedback.setText(
                "Position the chosen dominant hand first; change its side in Settings if needed."
            )
            return
        for role in roles:
            self.engine.pinches[role].calibrate()
        self.engine.last = self.latest_identity
        self.engine.context = self.interaction_context()
        self.engine.hand_ids = tuple(
            sorted((h.role, h.track_id) for h in self.current_hands)
        )
        self.calibration_step = 1
        self.refresh_calibration()

    def next_calibration(self):
        if not self.calibration_next.isEnabled():
            return
        self.cancel()
        self._calibration_previous_active = False
        self._pose_checks_since.clear()
        self.calibration_step = min(5, self.calibration_step + 1)
        self.refresh_calibration()

    def refresh_calibration(self):
        steps = (
            "Position hand",
            "Comfortable release",
            "Intentional pinch and release",
            "Point",
            "Open palm",
            "Validation",
        )
        self.calibration_progress.setText(
            "  →  ".join(
                ("● " if i == self.calibration_step else "") + s
                for i, s in enumerate(steps)
            )
        )
        descriptions = (
            "Position the chosen dominant hand fully inside the camera view.",
            "Hold thumb and index comfortably apart, then capture. Do not force skin contact.",
            "Close thumb and index deliberately, hold, then release until ready.",
            "Extend index only; hold briefly.",
            "Open all five fingers clearly; hold briefly.",
            "Session checks complete. This confirms observed calibration steps, not a measured physical usability acceptance rate.",
        )
        self.calibration_message.setText(descriptions[self.calibration_step])
        ready = (
            any(h.role == "DOMINANT" for h in self.current_hands),
            self.engine.pinches["DOMINANT"].reference is not None,
            "cycle" in self.calibration_checks,
            "point" in self.calibration_checks,
            "open" in self.calibration_checks,
            False,
        )[self.calibration_step]
        self.calibration_next.setEnabled(ready and self.settings.engine == "PRODUCT")
        self.capture_button.setEnabled(
            self.calibration_step in {0, 1} and self.settings.engine == "PRODUCT"
        )

    def _settings(self):
        self.preference_controls = {}
        widget, layout = page()
        heading(
            layout,
            "Settings",
            "Presentation preferences are separate from frozen research parameters.",
        )
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        panel = QWidget()
        form = QFormLayout(panel)
        scroll.setWidget(panel)
        layout.addWidget(scroll)
        for title, names in (
            (
                "Interaction",
                (
                    "dominant_hand",
                    "geometry_mode",
                    "engine",
                    "pointer_sensitivity",
                    "manipulation_sensitivity",
                    "construction_snap",
                ),
            ),
            (
                "Visual",
                ("skeleton", "gesture_labels", "grid", "object_labels", "lab_guide"),
            ),
            ("Camera", ("camera_index", "mirror")),
            (
                "Accessibility",
                (
                    "mouse_fallback",
                    "keyboard_shortcuts",
                    "dwell_select",
                    "reduced_motion",
                ),
            ),
            ("Developer", ("diagnostics",)),
        ):
            label = QLabel(title)
            label.setStyleSheet("font-size:18px;font-weight:600;padding-top:15px;")
            form.addRow(label)
            for name in names:
                value = getattr(self.settings, name)
                if type(value) is bool:
                    control = QCheckBox()
                    control.setChecked(value)
                    control.toggled.connect(
                        lambda v, key=name: self.set_preference(key, v)
                    )
                elif name in {"dominant_hand", "engine", "geometry_mode"}:
                    control = QComboBox()
                    control.addItems(
                        {
                            "dominant_hand": ("Left", "Right"),
                            "engine": ("PRODUCT", "LEGACY"),
                            "geometry_mode": ("LIVE", "RECORDED"),
                        }[name]
                    )
                    control.setCurrentText(value)
                    control.currentTextChanged.connect(
                        lambda v, key=name: self.set_preference(key, v)
                    )
                elif name == "camera_index":
                    control = QSpinBox()
                    control.setRange(0, 16)
                    control.setValue(value)
                    control.valueChanged.connect(
                        lambda v: self.set_preference("camera_index", v)
                    )
                else:
                    control = QDoubleSpinBox()
                    control.setRange(0.25, 3.0)
                    control.setSingleStep(0.25)
                    control.setValue(value)
                    control.valueChanged.connect(
                        lambda v, key=name: self.set_preference(key, v)
                    )
                form.addRow(
                    (
                        "Hướng dẫn theo lab"
                        if name == "lab_guide"
                        else name.replace("_", " ").capitalize()
                    ),
                    control,
                )
                self.preference_controls[name] = control
        button(layout, "Recalibrate", lambda: self.navigate("Calibrate"))
        self._add("Settings", widget)

    def set_preference(self, key, value):
        self.cancel(clear_reference=key in {"dominant_hand", "camera_index", "engine"})
        self.settings = replace(self.settings, **{key: value})
        control = self.preference_controls[key]
        control.blockSignals(True)
        if isinstance(control, QCheckBox):
            control.setChecked(value)
        elif isinstance(control, QComboBox):
            control.setCurrentText(value)
        else:
            control.setValue(value)
        control.blockSignals(False)
        if key == "construction_snap" and hasattr(self, "snap_control"):
            self.snap_control.blockSignals(True)
            self.snap_control.setChecked(value)
            self.snap_control.blockSignals(False)
        self.viewport.settings = self.settings
        if key == "lab_guide":
            self.reveal_guide(value)
        self.ui_control_button.setVisible(
            self.viewport.mode == "HAND" or self.live_mode()
        )
        self.interaction_hint.setVisible(
            self.viewport.mode == "HAND" or self.live_mode()
        )
        for lab in self.registry.extensions.values():
            lab.live_enabled = self.live_mode()
        self.refresh_inspector(rebuild=True)
        self.refresh_calibration()
        self.refresh_guide()
        self.refresh_shortcuts()
        self.hand_button.setEnabled(self.settings.engine == "PRODUCT")
        if self.settings.engine == "LEGACY" and self.viewport.mode == "HAND":
            self.set_mode("WORLD")
        self.analysis_camera.mirror = self.calibration_camera.mirror = (
            self.settings.mirror
        )
        try:
            self.settings.save(self.preferences_path)
        except OSError as exc:
            self.feedback.setText(f"Preferences could not be saved: {exc}")
        if (
            key in {"camera_index", "engine"}
            and self.worker is not None
            and self.worker.isRunning()
        ):
            self.stop_camera()
            self.feedback.setText("Camera/engine changed. Start camera to reconnect.")
        self.viewport.update()

    def _help(self):
        widget, layout = page()
        heading(
            layout,
            "Help",
            "Live fingertip geometry, with explicit menu control and recorded construction options.",
        )
        text = QTextBrowser()
        text.setPlainText(
            "LIVE GEOMETRY (default) — extend any fingers on one or two hands. Every extended tip becomes a live vertex: 1 point, 2 segment/vector, 3 triangle. Four or more noncoplanar vertices form a closed tetrahedron/polyhedron; nearly coplanar sets remain a polygon. Move, extend or fold fingers to update the shape directly. No Add point, pinch commit, saved shape or preliminary calibration is needed. All nine labs share this geometry layer. Coordinate/Vector show filled shapes; other labs use a wire outline so the model stays visible. Vertex labels stay stable while the same tips remain active. Detailed XYZ is available through Settings > diagnostics or CSV export.\n\n"
            "WORLD and HAND — vertices stay aligned with displayed fingertips. HAND also presents the lab on an observed palm, acquired with any extended fingertip. Loss, no extended tips or context changes remove the live shape.\n\n"
            "CONTROL UI — switch explicitly to exclusive menu navigation using POINT and calibrated PINCH. Turn it off to resume live geometry. Pinch calibration is needed for menu selection and recorded interaction, not live vertices.\n\n"
            "RECORDED (Settings > geometry_mode) — enables the earlier point-by-point tools and model manipulation described below. Those actions are separate from LIVE geometry.\n\n"
            "POINT — inspect and highlight. It never rotates the model.\n\nPINCH — after calibration and release/rearm, select or clutch. Hold and move to manipulate.\n\nOPEN PALM — present the active lab on your hand in HAND view. With two hands, the support palm provides the reference.\n\nV-SIGN — enter measure/create mode. POINT previews; PINCH commits. Both index fingers can preview a vector/distance; hold to lock, then pinch with the dominant hand to commit.\n\nTwo-hand scale — calibrate both hands, release/rearm, then pinch with both. Moving two open palms never scales.\n\nMouse — hover to inspect, drag to rotate, wheel to scale. In construction tools a click commits a point.\n\nKeyboard — 1–7 pages; H hand/world; M measure; Enter commit point; R reset; Esc cancel; arrows rotate; +/- scale; Space pause; F11 full screen.\n\nCamera/model errors — mouse and keyboard remain available. Check models/README.md and the selected camera source. Stop before reconnecting.\n\nLost/unknown tracking cancels immediately. Release before trying a new action. No metric camera depth or physical skin-contact detection is provided."
        )
        layout.addWidget(text, 1)
        text.append(
            "Explore: Hướng dẫn (G) shows or hides instructions for the selected lab and interaction mode. "
            "Phóng to (Ctrl+Shift+F) expands the model workspace; Thu gọn or Esc restores the previous panels. "
            "F11 toggles full screen independently. "
            "Tools: Reset view (R) restores orientation/zoom and keeps your measurements. "
            "Reset lab clears work after confirmation. Export measurements saves a CSV in scene units, without camera data. "
            "In RECORDED, optional Snap free points helps construct right angles on the current plane; exact atom-centre picks remain unchanged. "
            "Rectangle requires four right-angle corners in order; use Quadrilateral for arbitrary corners. "
            "Scene shortcuts apply in Explore; buttons and list navigation keep their native keys. "
            "RECORDED HAND: open palm once to anchor, then extend only the index finger to point; "
            "calibrated pinch commits. The same live palm stays anchored through these gestures. "
            "The cursor follows the camera tip. Control UI switches explicitly to window menus. "
            "Without an open-palm anchor, choose WORLD for manual controls."
        )
        self._add("Help", widget)

    def _lab_guide(self):
        self.guide_dock = QDockWidget("Cách dùng lab", self)
        self.guide_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.guide_dock.setMinimumWidth(260)
        self.guide_dock.setMaximumWidth(310)
        self.guide_text = QTextBrowser()
        self.guide_text.setAccessibleName("Hướng dẫn lab đang mở")
        self.guide_dock.setWidget(self.guide_text)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.guide_dock)
        self.refresh_guide()

    def refresh_guide(self):
        if hasattr(self, "guide_text"):
            self.guide_text.setPlainText(
                guide_text(
                    self.registry.current,
                    live=self.live_mode(),
                    engine=self.settings.engine,
                    mode=self.viewport.mode,
                    ui_control=self.ui_control_button.isChecked(),
                )
            )

    def reveal_guide(self, visible):
        self.guide_button.setChecked(visible)
        if visible:
            self.reveal_tools(False)
        self.guide_dock.setVisible(visible and self.page_name == "Explore")

    def show_guide(self, visible):
        if self._expanded:
            self.cancel(preserve_presentation=True)
            self.reveal_guide(visible)
            return
        self.set_preference("lab_guide", visible)

    def set_expanded(self, expanded):
        """Change layout only; cancel input whose coordinate frame just changed."""
        if expanded == self._expanded or self.page_name != "Explore":
            return
        self.cancel(preserve_presentation=True)
        self._expanded = expanded
        self.expand_button.setChecked(expanded)
        self.expand_button.setText("Thu gọn" if expanded else "Phóng to")
        self.expand_button.setToolTip(
            "Khôi phục bố cục trước khi phóng to (Esc / Ctrl+Shift+F)"
            if expanded
            else "Mở rộng khung mô hình; thu các bảng phụ (Ctrl+Shift+F)"
        )
        self.navigation_dock.setVisible(not expanded)
        self.library.setVisible(not expanded)
        if expanded:
            self._expanded_panels = (
                self.guide_button.isChecked(),
                self.tools_button.isChecked(),
            )
            self.reveal_guide(False)
            self.reveal_tools(False)
        else:
            guide, tools = self._expanded_panels
            self._expanded_panels = None
            self.reveal_tools(tools)
            self.reveal_guide(guide)
        self.viewport.setFocus()
        self.viewport.update()

    def escape_explore(self):
        if self._expanded:
            self.set_expanded(False)
        else:
            self.cancel_tool()

    def _inspector(self):
        self.inspector_dock = QDockWidget("Inspector", self)
        self.inspector_dock.setFeatures(
            QDockWidget.DockWidgetFeature.NoDockWidgetFeatures
        )
        self.inspector_dock.setMinimumWidth(255)
        self.inspector_dock.setMaximumWidth(330)
        panel = QWidget()
        layout = QVBoxLayout(panel)
        self.preset_select = QComboBox()
        layout.addWidget(self.preset_select)
        self.preset_select.currentTextChanged.connect(self.choose_preset)
        self.tool_select = QComboBox()
        self.tool_select.addItems(self.registry.current.tools)
        self.tool_select.currentTextChanged.connect(self.choose_tool)
        self.snap_control = QCheckBox(
            f"Snap free points: {self.config.construction_grid_step:g} scene units"
        )
        self.snap_control.setChecked(self.settings.construction_snap)
        self.snap_control.toggled.connect(
            lambda value: self.set_preference("construction_snap", value)
        )
        layout.addWidget(self.snap_control)
        layout.addWidget(self.tool_select)
        self.tool_actions = QWidget()
        actions_layout = QVBoxLayout(self.tool_actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tool_actions)
        row = QHBoxLayout()
        actions_layout.addLayout(row)
        self.commit_button = button(row, "Add point", self.commit_point)
        self.cancel_button = button(row, "Cancel", self.cancel_tool)
        row = QHBoxLayout()
        actions_layout.addLayout(row)
        self.polygon_button = button(row, "Finish polygon", self.finish_polygon)
        self.undo_button = button(row, "Undo", self.undo)
        self.parameter_panel = QWidget()
        self.parameter_form = QFormLayout(self.parameter_panel)
        layout.addWidget(self.parameter_panel)
        self.pause_button = button(layout, "Pause / Resume", self.toggle_pause)
        self.export_button = button(
            layout, "Export measurements…", self.export_measurements
        )
        button(layout, "Reset lab (clear work)…", self.confirm_reset_lab)
        self.inspector_text = QTextBrowser()
        layout.addWidget(self.inspector_text, 1)
        self.inspector_dock.setWidget(panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.inspector_dock)
        self.refresh_inspector(rebuild=True)

    def refresh_inspector(self, *, rebuild=False):
        lab = self.registry.current
        live = self.live_mode()
        self.tool_select.setVisible(not live)
        self.snap_control.setVisible(not live)
        self.tool_actions.setVisible(
            not live and (lab.tool != "Inspect" or bool(lab.constructions))
        )
        self.commit_button.setVisible(lab.tool != "Inspect")
        self.cancel_button.setVisible(lab.tool != "Inspect")
        self.commit_button.setEnabled(lab.preview is not None)
        self.polygon_button.setVisible(lab.tool == "Polygon")
        self.polygon_button.setEnabled(len(lab.points) >= 3)
        self.undo_button.setEnabled(bool(lab.points or lab.constructions))
        self.export_button.setEnabled(bool(lab.export_constructions()))
        values = lab.inspect()
        if live and self.settings.diagnostics:
            values += lab.vertex_details()
        self.inspector_text.setPlainText("\n\n".join(values))
        if rebuild:
            self.preset_select.blockSignals(True)
            self.preset_select.clear()
            self.preset_select.addItems(lab.presets)
            self.preset_select.setCurrentText(lab.preset)
            self.preset_select.blockSignals(False)
            self.tool_select.blockSignals(True)
            self.tool_select.clear()
            self.tool_select.addItems(lab.tools)
            self.tool_select.setCurrentText(lab.tool)
            self.tool_select.blockSignals(False)
            while self.parameter_form.rowCount():
                self.parameter_form.removeRow(0)
            self.parameter_controls = {}
            names = {
                "orbital": ("radius", "time_rate"),
                "wave": ("amplitude", "frequency", "phase", "samples"),
                "optics": ("index", "focal"),
            }.get(lab.id, ())
            for name in names:
                control = QSpinBox() if name == "samples" else QDoubleSpinBox()
                (
                    control.setRange(4, 128)
                    if name == "samples"
                    else (
                        control.setRange(0, 2 * math.pi)
                        if name == "phase"
                        else control.setRange(0.1, 6.0)
                    )
                )
                control.setValue(
                    lab.time_rate if name == "time_rate" else lab.parameters[name]
                )
                control.setSingleStep(1 if name == "samples" else 0.1)
                control.setToolTip(PARAMETER_HINTS[name])
                control.valueChanged.connect(
                    lambda v, key=name: self.set_parameter(key, v)
                )
                self.parameter_form.addRow(name.capitalize(), control)
                self.parameter_controls[name] = control
            self.pause_button.setVisible(lab.id in {"orbital", "wave"})
        if lab.id == "optics":
            for name in self.parameter_controls:
                self.parameter_form.setRowVisible(
                    self.parameter_controls[name],
                    (name == "index" and lab.preset == "Refraction")
                    or (name == "focal" and lab.preset == "Lens"),
                )

    def set_parameter(self, key, value):
        self.cancel()
        if key == "time_rate":
            self.registry.current.time_rate = value
        else:
            self.registry.current.parameters[key] = value
        control = self.parameter_controls.get(key)
        if control is not None:
            control.blockSignals(True)
            control.setValue(value)
            control.blockSignals(False)
        self.viewport.update()
        self.refresh_inspector()

    def choose_preset(self, text):
        if text:
            self.cancel()
            self.registry.current.set_preset(text)
            self.preset_select.blockSignals(True)
            self.preset_select.setCurrentText(text)
            self.preset_select.blockSignals(False)
            self.viewport.update()
            self.refresh_inspector()
            self.refresh_guide()

    def choose_tool(self, text):
        if self.live_mode():
            return
        if text:
            self.cancel()
            self.registry.current.set_tool(text)
            self.tool_select.blockSignals(True)
            self.tool_select.setCurrentText(text)
            self.tool_select.blockSignals(False)
            if text != "Inspect" and not self.tools_button.isChecked():
                self.show_tools(True)
            self.engine.measure = text != "Inspect"
            self.refresh_inspector()

    def cancel(self, *, clear_reference=False, preserve_presentation=False):
        if clear_reference:
            self.calibration_step = 0
            self.calibration_checks.clear()
            self._pose_checks_since.clear()
            self._calibration_previous_active = False
        self.epoch += 1
        self._manual_active = False
        self._legacy_rearm = True
        intent = self.engine.reset(clear_reference=clear_reference)
        self.registry.current.on_intent(intent)
        if clear_reference or not preserve_presentation:
            self.anchor.reset()
            self.viewport.anchor = None
            self.viewport.reference_plane = None
        self.viewport.pointer = None
        self.viewport.live_sources = ()
        self._dwell_target = self._dwell_since = None
        self._ui_cycle = None
        if hasattr(self, "touch_cursor"):
            self.touch_cursor.hide()
        if clear_reference and hasattr(self, "calibration_next"):
            self.refresh_calibration()
        if hasattr(self, "inspector_text"):
            self.refresh_inspector()
        return intent

    def cancel_tool(self):
        self.cancel()
        self.registry.current.set_tool("Inspect")
        self.registry.current.points.clear()
        self.refresh_inspector(rebuild=True)
        self.viewport.update()

    def navigate(self, name):
        if name not in self.pages:
            return
        if name != "Explore" and self._expanded:
            self.set_expanded(False)
        self.cancel()
        self.page_name = name
        self.stack.setCurrentWidget(self.pages[name])
        self.inspector_dock.setVisible(
            name == "Explore" and self.tools_button.isChecked()
        )
        self.guide_dock.setVisible(name == "Explore" and self.guide_button.isChecked())
        if name == "Explore":
            QTimer.singleShot(100, self.ensure_renderer)
        if self.navigation.currentRow() != PAGES.index(name):
            self.navigation.blockSignals(True)
            self.navigation.setCurrentRow(PAGES.index(name))
            self.navigation.blockSignals(False)
        self.refresh_shortcuts()

    def ensure_renderer(self):
        if (
            self.page_name != "Explore"
            or not isinstance(self.viewport, Viewport)
            or self.viewport.isValid()
            and not self.viewport.gpu_error
        ):
            return
        old = self.viewport
        self.cancel()
        old.close_renderer()
        fallback = SoftwareViewport(self.registry, self.config, self.settings)
        for name in (
            "mode",
            "image",
            "landmarks",
            "anchor",
            "reference_plane",
            "pointer",
        ):
            setattr(fallback, name, getattr(old, name))
        fallback.manual.connect(self.manual)
        self.viewport_layout.replaceWidget(old, fallback)
        self.viewport = fallback
        old.hide()
        old.deleteLater()
        fallback.show()
        self.feedback.setText(
            "OpenGL unavailable. Software renderer active; all labs remain available."
        )

    def select_lab(self, key):
        self.cancel()
        lab = self.registry.select(key)
        self.library.blockSignals(True)
        self.library.setCurrentRow(tuple(self.registry.extensions).index(key))
        self.library.blockSignals(False)
        self.lab_title.setText(lab.title)
        self.refresh_inspector(rebuild=True)
        self.refresh_guide()
        self.viewport.update()

    def show_tools(self, visible):
        self.cancel()
        self.reveal_tools(visible)

    def reveal_tools(self, visible):
        """Presentation-only inspector expansion after an already-routed tool intent."""
        self.tools_button.setChecked(visible)
        if visible and hasattr(self, "guide_dock"):
            self.guide_button.setChecked(False)
            self.guide_dock.hide()
        self.inspector_dock.setVisible(visible and self.page_name == "Explore")

    def open_lab(self, key):
        self.library.setCurrentRow(tuple(self.registry.extensions).index(key))
        self.navigate("Explore")

    def set_mode(self, mode):
        if mode == "HAND" and self.settings.engine == "LEGACY":
            self.feedback.setText(
                "Hand anchoring uses PRODUCT mode. Legacy remains available in WORLD view."
            )
            return
        self.cancel()
        self.viewport.mode = mode
        self.world_button.setChecked(mode == "WORLD")
        self.hand_button.setChecked(mode == "HAND")
        self.ui_control_button.setChecked(False)
        self.ui_control_button.setVisible(mode == "HAND" or self.live_mode())
        self.interaction_hint.setVisible(mode == "HAND" or self.live_mode())
        self.interaction_hint.setText(
            "Open palm once to anchor. Only index finger extended: point; calibrated thumb/index pinch: commit. "
            "Control UI: switch to menu navigation."
        )
        if self.live_mode():
            self.interaction_hint.setText(
                "Live geometry follows every extended fingertip on one or two hands; no point commit is needed."
            )
        self.refresh_guide()
        self.viewport.update()

    def set_ui_control(self, enabled):
        self.cancel()
        self.ui_control_button.setChecked(enabled)
        self.refresh_guide()
        self.viewport.update()

    def reset_lab(self):
        self.cancel()
        self.registry.current.reset()
        self.refresh_inspector(rebuild=True)
        self.refresh_guide()
        self.viewport.update()

    def reset_view(self):
        self.cancel()
        lab = self.registry.current
        lab.yaw, lab.pitch, lab.scale = 0.35, 0.35, 1.0
        self.viewport.update()

    def confirm_reset_lab(self):
        self.cancel()
        if (
            QMessageBox.question(
                self,
                "Reset lab",
                "Clear this lab's measurements and restore its parameters?",
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.reset_lab()

    def export_measurements(self):
        from app.extensions.measurement_export import export_csv, snapshot

        lab = snapshot(self.registry.current)
        if not lab.export_constructions():
            return
        self.cancel()
        path, _ = QFileDialog.getSaveFileName(
            self, "Export measurements", f"{lab.id}-measurements.csv", "CSV (*.csv)"
        )
        if path:
            try:
                export_csv(lab, path)
            except OSError as exc:
                self.feedback.setText(f"Measurements could not be saved: {exc}")
            else:
                self.feedback.setText(
                    "Measurements exported in scene units; camera data is excluded."
                )

    def toggle_pause(self):
        self.registry.current.paused = not self.registry.current.paused

    def finish_polygon(self):
        if self.live_mode():
            return
        self.cancel()
        self.registry.current.finish_polygon()
        self.refresh_inspector()
        self.viewport.update()

    def undo(self):
        if self.live_mode():
            return
        self.cancel()
        lab = self.registry.current
        if lab.points:
            lab.points.pop()
        elif lab.constructions:
            lab.constructions.pop()
        self.refresh_inspector()
        self.viewport.update()

    def commit_point(self):
        if self.live_mode():
            self.feedback.setText(
                "Live geometry follows all extended fingertips automatically; no point commit is needed."
            )
            return
        lab = self.registry.current
        if lab.tool == "Inspect":
            self.feedback.setText("Choose a measurement tool before adding points.")
            return
        if lab.preview is None:
            self.feedback.setText(
                "Point or move the mouse over the viewport before committing."
            )
            return
        point = lab.preview
        self.cancel(preserve_presentation=True)
        self._manual_cycle += 1
        self.deliver(
            Intent(
                Type.TOOL_COMMIT,
                Phase.BEGIN,
                world_or_scene_point=point,
                cycle_id=self._manual_cycle,
                tool_id=lab.tool,
                owner=Owner.TOOL,
            )
        )

    def manual(self, kind, value):
        if (
            self.page_name != "Explore"
            or not self.settings.mouse_fallback
            or QApplication.activeModalWidget() is not None
        ):
            return
        lab = self.registry.current
        if kind == "release":
            self._manual_active = False
            self.deliver(Intent(Type.RELEASE, Phase.END))
            return
        if self.viewport.mode == "HAND" and self.viewport.anchor is None:
            self.feedback.setText(
                "Choose WORLD for mouse controls, or open your palm for HAND."
            )
            return
        if kind == "point":
            if self.engine.active is not None:
                return
            self.deliver(
                Intent(
                    Type.POINT, world_or_scene_point=self.viewport.pick_viewport(value)
                )
            )
        elif kind == "begin":
            point = self.viewport.pick_viewport(value)
            self.cancel(preserve_presentation=True)
            self._manual_active = True
            if not self.live_mode() and lab.tool != "Inspect":
                self._manual_cycle += 1
                self.deliver(
                    Intent(
                        Type.TOOL_COMMIT,
                        Phase.BEGIN,
                        world_or_scene_point=point,
                        cycle_id=self._manual_cycle,
                        tool_id=lab.tool,
                        owner=Owner.TOOL,
                    )
                )
            else:
                self.deliver(Intent(Type.GRAB, Phase.BEGIN, world_or_scene_point=point))
        elif kind == "drag" and (self.live_mode() or lab.tool == "Inspect"):
            self.deliver(
                Intent(
                    Type.DRAG,
                    delta_xy=tuple(
                        v * self.settings.manipulation_sensitivity for v in value
                    ),
                )
            )
        elif kind == "scale":
            self.cancel(preserve_presentation=True)
            self.deliver(Intent(Type.SCALE, Phase.BEGIN))
            self.deliver(Intent(Type.SCALE, scale_factor=value[0]))

    def deliver(self, intent, *, record=True):
        if record:
            intent = replace(intent, input_source="MANUAL")
        self.registry.current.on_intent(intent)
        self.refresh_inspector()
        self.viewport.update()
        if record:
            self.record_intent(intent, "manual")

    def record_intent(self, intent, source):
        if self._journal is not None:
            try:
                self._journal.write(
                    json.dumps(
                        {
                            "identity": self.latest_identity,
                            "source": source,
                            "intent": asdict(intent),
                            "scene": self.registry.current.id,
                            "mode": self.viewport.mode,
                            "settings": asdict(self.settings),
                        },
                        default=str,
                        allow_nan=False,
                    )
                    + "\n"
                )
            except (OSError, ValueError) as exc:
                self.journal_failure(exc)

    def close_journal(self):
        journal, self._journal = self._journal, None
        if journal is not None:
            try:
                journal.close()
            except OSError as exc:
                self.journal_failure(exc)

    def journal_failure(self, exc):
        self._journal_failed = True
        self._journal_error = (
            f"Product intent log incomplete: {type(exc).__name__}: {exc}"
        )
        self.close_journal()
        self.feedback.setText(self._journal_error)
        self.diagnostics.setPlainText(self._journal_error)

    def ui_target(self, pointer):
        """Normalized presentation pointer -> native control hit, with one activation callback."""
        pos = QPoint(
            round(pointer[0] * self.width()), round(pointer[1] * self.height())
        )
        target = self.childAt(pos)
        if isinstance(target, QAbstractButton) and target.isEnabled():
            return target, target.click
        for control in (self.navigation, self.library):
            if not control.isVisible():
                continue
            local = control.viewport().mapFrom(self, pos)
            if control.viewport().rect().contains(local):
                item = control.itemAt(local)
                if item is not None:
                    row = control.row(item)
                    return (control, row), lambda c=control, r=row: c.setCurrentRow(r)
        if isinstance(target, QComboBox) and target.isEnabled() and target.count() > 1:
            return target, lambda c=target: c.setCurrentIndex(
                (c.currentIndex() + 1) % c.count()
            )
        return None, None

    def viewport_pointer(self, pointer):
        """Window-normalized control pointer -> viewport-local normalized coordinates.

        WORLD/UI use this mapping. HAND scene pointers use camera letterboxing.
        """
        origin = self.viewport.mapTo(self, QPoint(0, 0))
        return (
            (pointer[0] * self.width() - origin.x()) / self.viewport.width(),
            (pointer[1] * self.height() - origin.y()) / self.viewport.height(),
        )

    def scene_pointer(self, intent):
        if self.viewport.mode == "HAND":
            return self.viewport.source_pointer(intent.source_pointer_xy)
        return (
            None
            if intent.pointer_xy is None
            else self.viewport_pointer(intent.pointer_xy)
        )

    def interaction_context(self):
        return (
            self.epoch,
            self.page_name,
            self.registry.current.id,
            self.viewport.mode,
            self.ui_control_button.isChecked(),
            self.settings,
        )

    def live_mode(self):
        return (
            self.settings.engine == "PRODUCT" and self.settings.geometry_mode == "LIVE"
        )

    def _shortcuts(self):
        self.shortcuts = []
        commands = [
            (str(i + 1), lambda name=name: self.navigate(name))
            for i, name in enumerate(PAGES)
        ]
        commands.extend(
            (
                (
                    "H",
                    lambda: self.set_mode(
                        "HAND" if self.viewport.mode == "WORLD" else "WORLD"
                    ),
                ),
                ("M", lambda: self.tool_select.setCurrentText("Distance")),
                ("R", self.reset_view),
                ("Esc", self.escape_explore),
                ("G", lambda: self.show_guide(not self.guide_button.isChecked())),
                ("Ctrl+Shift+F", lambda: self.set_expanded(not self._expanded)),
                ("Return", self.commit_point),
                ("Space", self.toggle_pause),
                (
                    "F11",
                    lambda: (
                        self.showNormal()
                        if self.isFullScreen()
                        else self.showFullScreen()
                    ),
                ),
                ("Left", lambda: self.keyboard_motion(-0.08, 0)),
                ("Right", lambda: self.keyboard_motion(0.08, 0)),
                ("Up", lambda: self.keyboard_motion(0, -0.08)),
                ("Down", lambda: self.keyboard_motion(0, 0.08)),
                ("+", lambda: self.keyboard_scale(1.1)),
                ("-", lambda: self.keyboard_scale(1 / 1.1)),
            )
        )
        for key, callback in commands:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setProperty(
                "exploreOnly", key not in {"1", "2", "3", "4", "5", "6", "7", "F11"}
            )
            shortcut.activated.connect(
                lambda cb=callback, s=shortcut: (
                    cb() if self.shortcut_allowed(s) else None
                )
            )
            self.shortcuts.append(shortcut)
        self.refresh_shortcuts()

    def shortcuts_allowed(self):
        focus = QApplication.focusWidget()
        editing = isinstance(focus, (QLineEdit, QAbstractSpinBox, QComboBox)) or (
            isinstance(focus, QTextEdit) and not focus.isReadOnly()
        )
        return (
            self.settings.keyboard_shortcuts
            and not editing
            and QApplication.activeModalWidget() is None
        )

    def refresh_shortcuts(self, *_):
        for shortcut in self.shortcuts:
            shortcut.setEnabled(self.shortcut_allowed(shortcut))

    def shortcut_allowed(self, shortcut):
        if not self.shortcuts_allowed():
            return False
        if shortcut.key().toString() in {"Return", "Space"} and isinstance(
            QApplication.focusWidget(), QAbstractButton
        ):
            return False
        if shortcut.property("exploreOnly"):
            if isinstance(
                QApplication.focusWidget(), QTextBrowser
            ) and shortcut.key().toString() not in {
                "G",
                "Ctrl+Shift+F",
                "Esc",
            }:
                return False
            return self.page_name == "Explore" and QApplication.focusWidget() not in {
                self.library,
                self.navigation,
            }
        return True

    def keyboard_motion(self, x, y):
        if self.page_name == "Explore" and (
            self.viewport.mode == "WORLD" or self.viewport.anchor is not None
        ):
            self.cancel(preserve_presentation=True)
            self.deliver(Intent(Type.GRAB, Phase.BEGIN))
            self.deliver(Intent(Type.DRAG, delta_xy=(x, y)))
            self.deliver(Intent(Type.RELEASE, Phase.END))

    def keyboard_scale(self, factor):
        if self.page_name == "Explore" and (
            self.viewport.mode == "WORLD" or self.viewport.anchor is not None
        ):
            self.cancel(preserve_presentation=True)
            self.deliver(Intent(Type.SCALE, Phase.BEGIN))
            self.deliver(Intent(Type.SCALE, scale_factor=factor))

    def _application_state(self, state):
        if state != Qt.ApplicationState.ApplicationActive:
            self.cancel()

    def start_camera(self):
        if self.worker is not None and self.worker.isRunning():
            return
        self.cancel(clear_reference=True)
        self._camera_failure = None
        self._journal_failed = False
        self._journal_error = None
        self.worker = RuntimeWorker(
            self.config, self.settings.camera_index, self, engine=self.settings.engine
        )
        self.worker.failure.connect(self.camera_error)
        self.worker.status.connect(self.tracking_label.setText)
        self.worker.finished.connect(self.camera_finished)
        self.last_frame_time = None
        self.worker.start()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.recent.setText("Recent session: " + self.worker.run_id)

    def camera_error(self, message):
        self._camera_failure = message
        self.cancel()
        self.feedback.setText(
            "Camera or hand tracking unavailable. Open Analyze for the error details. Mouse and keyboard remain available."
        )
        self.diagnostics.setPlainText(message)
        self.tracking_label.setText("Tracking unavailable")

    def camera_finished(self):
        self.clear_tracking(
            "Camera unavailable — see Analyze"
            if self._camera_failure
            else "Camera stopped"
        )
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.cancel(clear_reference=True)
        self.close_journal()

    def stop_camera(self):
        self.cancel(clear_reference=True)
        if self.worker is not None:
            self.worker.stop()
            self.worker.take_latest()
        self.clear_tracking("Stopping camera")

    def clear_tracking(self, message):
        self.cancel()
        self.current_hands = ()
        self.last_tracking = self.latest_identity = None
        self.last_frame_time = None
        self.viewport.image = None
        self.viewport.live_sources = ()
        self.viewport.landmarks = {}
        self.environment_notice.hide()
        self.viewport.update()
        for camera in (self.analysis_camera, self.calibration_camera):
            camera.image = camera.frame = None
            camera.product_landmarks = {}
            camera.message = message
            camera.update()
        self.tracking_label.setText(message)
        self.home_status.setText(
            f"Tracking: {message}   ·   Gesture control paused; mouse controls remain available in WORLD."
        )
        if not self._camera_failure:
            self.diagnostics.setPlainText(self._journal_error or message)

    def tick(self):
        if isinstance(self.viewport, Viewport) and self.viewport.gpu_error:
            self.ensure_renderer()
        modal = QApplication.activeModalWidget() is not None
        if modal != self._modal_blocked:
            self.cancel()
            self._modal_blocked = modal
            self.refresh_shortcuts()
        now = time.monotonic()
        dt = min(0.1, now - self._last_tick)
        self._last_tick = now
        if not self.settings.reduced_motion:
            self.registry.current.update(dt)
        if (
            self.worker is not None
            and self.worker.isRunning()
            and not self.worker.stop_event.is_set()
        ):
            latest = self.worker.take_latest()
            if latest is not None:
                self.consume(*latest)
        if (
            self.last_frame_time is not None
            and now - self.last_frame_time > self.config.max_gap_s
        ):
            self.clear_tracking("Tracking stalled — release before resuming")
        if self.page_name == "Explore" and self.registry.current.id in {
            "orbital",
            "wave",
        }:
            self.viewport.update()

    def consume(self, packet, frame, legacy, filtered, valid, reason):
        self.last_frame_time = time.monotonic()
        self.last_tracking = frame
        self.update_environment(frame, reason)
        self.latest_identity = frame.run_id, frame.frame_id, frame.timestamp_s
        if self._journal is None and not self._journal_failed:
            try:
                directory = ROOT / "runs/product-v2" / frame.run_id
                directory.mkdir(parents=True, exist_ok=True)
                self._journal = (directory / "intents.jsonl").open(
                    "a", encoding="utf-8"
                )
                (directory / "settings.json").write_text(
                    json.dumps(asdict(self.settings), indent=2), encoding="utf-8"
                )
            except OSError as exc:
                self.journal_failure(exc)
        h, w = packet.image.shape[:2]
        hands = []
        for label, landmarks in filtered.items():
            role = "DOMINANT" if label == self.settings.dominant_hand else "SUPPORT"
            hand = describe(landmarks, w, h, self.config, track_id=label, role=role)
            if hand is not None:
                hands.append(hand)
        self.current_hands = tuple(hands)
        self.viewport.image = bgr_image(packet.image)
        self.viewport.landmarks = filtered
        for camera in (self.analysis_camera, self.calibration_camera):
            camera.mirror = self.settings.mirror
            camera.product_landmarks = filtered
            camera.set_packet(packet, frame)
        focused = (
            QApplication.applicationState() == Qt.ApplicationState.ApplicationActive
        )
        modal = QApplication.activeModalWidget() is not None
        if modal and self._manual_active:
            self.cancel()
        dominant = next((v for v in hands if v.role == "DOMINANT"), None)
        support = next((v for v in hands if v.role == "SUPPORT"), None)
        self.viewport.anchor = self.anchor.observe(
            hands,
            self.latest_identity,
            valid=valid and focused and not modal,
            allow_fingertips=self.live_mode() and self.page_name == "Explore",
        )
        self.viewport.reference_plane = (
            support.palm
            if support
            and support.pose == "OPEN_PALM"
            and valid
            and focused
            and not modal
            else None
        )
        if (
            self._manual_active
            and self.viewport.mode == "HAND"
            and self.viewport.anchor is None
        ):
            self.cancel()
        target = activation = None
        hand_scene = (
            self.page_name == "Explore"
            and self.viewport.mode == "HAND"
            and not self.ui_control_button.isChecked()
        )
        finger_scene = (
            self.page_name == "Explore"
            and self.live_mode()
            and not self.ui_control_button.isChecked()
        )
        if dominant and not (hand_scene or finger_scene):
            px, py = self.engine.pointer(dominant.pointer_xy, self.settings)
            target, activation = self.ui_target((px, py))
        ui = (
            activation is not None
            or self.page_name != "Explore"
            or (
                (self.viewport.mode == "HAND" or self.live_mode())
                and self.ui_control_button.isChecked()
            )
        )
        context = self.interaction_context()
        if self.settings.engine == "LEGACY":
            self.engine.reset()
            if (
                focused
                and not modal
                and not self._manual_active
                and self.page_name == "Explore"
                and legacy is not None
                and legacy.interaction_valid
            ):
                if self._legacy_rearm:
                    if not legacy.pinch_active:
                        self._legacy_rearm = False
                else:
                    lab = self.registry.current
                    lab.yaw += legacy.rotation_delta[0]
                    lab.pitch += legacy.rotation_delta[1]
                    lab.scale = min(
                        self.config.max_scale,
                        max(self.config.min_scale, lab.scale + legacy.scale_delta),
                    )
            else:
                self._legacy_rearm = True
            intent = Intent(
                Type.CANCEL, Phase.CANCEL, validity=False, reason="EXPLICIT_LEGACY"
            )
        else:
            self.engine.measure = self.registry.current.tool != "Inspect"
            intent = self.engine.update(
                hands,
                self.latest_identity,
                settings=self.settings,
                valid=valid and focused and not self._manual_active,
                context=context,
                ui=ui,
                calibration=self.page_name == "Calibrate",
                modal=modal,
                fingertip_geometry=self.live_mode() and self.page_name == "Explore",
            )
        self.viewport.pointer = self.scene_pointer(intent)
        self.viewport.live_sources = ()
        if (
            not self.live_mode()
            and hand_scene
            and dominant
            and valid
            and focused
            and not modal
        ):
            # Observed fingertip remains visible even when its pose cannot command.
            self.viewport.pointer_source = dominant.pointer_xy
        if (
            intent.owner is Owner.UI
            and intent.pointer_xy is not None
            and valid
            and focused
        ):
            px, py = intent.pointer_xy
            self.touch_cursor.move(
                round(px * self.width()) - 11, round(py * self.height()) - 11
            )
            self.touch_cursor.show()
            self.touch_cursor.raise_()
            self.viewport.pointer = None
        else:
            self.touch_cursor.hide()
        if intent.type is Type.CANCEL:
            self._dwell_target = self._dwell_since = None
            if not self._manual_active:
                self.registry.current.on_intent(intent)
                self.refresh_inspector()
        elif intent.owner is Owner.UI:
            if (
                intent.type is Type.SELECT
                and intent.phase is Phase.BEGIN
                and activation is not None
            ):
                key = (frame.run_id, intent.cycle_id)
                if key != self._ui_cycle:
                    self._ui_cycle = key
                    activation()
            self._dwell(
                target,
                activation,
                frame.timestamp_s,
                valid
                and focused
                and dominant is not None
                and dominant.pose == "POINT"
                and not self.registry.current.dragging,
            )
        elif (
            self.page_name == "Explore"
            and intent.owner in {Owner.SCENE, Owner.TOOL}
            and self.viewport.mode == "HAND"
            and self.viewport.anchor is None
        ):
            intent = replace(self.engine.reset(), reason="HAND_ANCHOR_REQUIRED")
            self.registry.current.on_intent(intent)
        elif self.page_name == "Explore" and intent.owner in {Owner.SCENE, Owner.TOOL}:
            if intent.live_geometry:
                mapped_points = tuple(
                    self.viewport.fingertip_pointer(p) for p in intent.source_points
                )
                points = tuple(
                    self.viewport.fingertip_point(p, z)
                    for p, z in zip(intent.source_points, intent.source_depths)
                )
                if any(p is None for p in points):
                    intent = replace(
                        self.engine.reset(), reason="FINGERTIP_PROJECTION_UNAVAILABLE"
                    )
                    self.registry.current.on_intent(intent)
                else:
                    # Outline order follows displayed vertices, retaining all tips.
                    centre = np.mean(points, axis=0)
                    cx, cy = self.viewport.projection().project(centre)[:2]
                    order = (
                        sorted(
                            range(len(points)),
                            key=lambda i: math.atan2(
                                mapped_points[i][1] * self.viewport.height() - cy,
                                mapped_points[i][0] * self.viewport.width() - cx,
                            ),
                        )
                        if len(points) >= 3
                        else range(len(points))
                    )
                    order = tuple(order)
                    intent = replace(
                        intent,
                        points=tuple(points[i] for i in order),
                        vertex_tokens=tuple(intent.vertex_tokens[i] for i in order),
                        source_points=tuple(intent.source_points[i] for i in order),
                        source_depths=tuple(intent.source_depths[i] for i in order),
                    )
                    self.viewport.live_sources = intent.source_points
                    self.deliver(intent, record=False)
            else:
                intent = self.consume_recorded_scene(intent)
        self.finish_frame_feedback(
            intent,
            hands,
            dominant,
            support,
            frame,
            legacy,
            valid,
            focused,
            modal,
            reason,
            hand_scene,
        )
        self.viewport.update()

    def consume_recorded_scene(self, intent):
        mapped = self.scene_pointer(intent)
        point = None if mapped is None else self.viewport.pick_point(mapped)
        mapped_points = (
            tuple(self.viewport.source_pointer(p) for p in intent.source_points)
            if self.viewport.mode == "HAND"
            else tuple(self.viewport_pointer(p[:2]) for p in intent.points)
        )
        points = tuple(
            None if p is None else self.viewport.scene_point(p) for p in mapped_points
        )
        if any(p is None for p in points):
            points = ()
            point = None
        plane_pose = intent.anchor_pose
        if plane_pose is not None and self.viewport.mode == "HAND":
            plane_pose = replace(plane_pose, pitch_rad=0.0, yaw_rad=0.0)
        intent = replace(
            intent,
            world_or_scene_point=point,
            points=points,
            tool_id=self.registry.current.tool,
            anchor_pose=plane_pose,
        )
        self.deliver(intent, record=False)
        if (
            intent.type is Type.MEASURE_BEGIN
            or self.registry.current.tool != self.tool_select.currentText()
        ):
            self.tool_select.blockSignals(True)
            self.tool_select.setCurrentText("Distance")
            self.tool_select.blockSignals(False)
            if not self.tools_button.isChecked():
                self.reveal_tools(True)
        return intent

    def finish_frame_feedback(
        self,
        intent,
        hands,
        dominant,
        support,
        frame,
        legacy,
        valid,
        focused,
        modal,
        reason,
        hand_scene,
    ):
        dp = self.engine.pinches["DOMINANT"]
        self.record_intent(
            intent, "product" if self.settings.engine == "PRODUCT" else "legacy"
        )
        if self.page_name == "Calibrate":
            if intent.type is Type.CANCEL:
                self._calibration_previous_active = False
                self._pose_checks_since.clear()
            if self.calibration_step >= 2 and dp.reference is None:
                self.calibration_step = 1
                self.calibration_checks.clear()
            if dp.active:
                self._calibration_previous_active = True
            if (
                self.calibration_step == 2
                and self._calibration_previous_active
                and dp.state == "READY"
            ):
                self.calibration_checks.add("cycle")
                self._calibration_previous_active = False
            for step, pose, check in ((3, "POINT", "point"), (4, "OPEN_PALM", "open")):
                if (
                    self.calibration_step == step
                    and dominant
                    and valid
                    and dominant.pose == pose
                ):
                    since = self._pose_checks_since.setdefault(check, frame.timestamp_s)
                    if frame.timestamp_s - since >= self.config.pose_dwell_s:
                        self.calibration_checks.add(check)
                else:
                    self._pose_checks_since.pop(check, None)
            self.refresh_calibration()
        legacy_usable = legacy is not None and legacy.interaction_valid
        tracking = (
            ("LEGACY_READY" if legacy_usable else frame.status.value)
            if self.settings.engine == "LEGACY"
            else "TRACKING" if valid else reason
        )
        self.tracking_label.setText(tracking + f" · {len(hands)} hand(s)")
        gesture = (
            ("LEGACY" if legacy_usable else "LOST")
            if self.settings.engine == "LEGACY"
            else dominant.pose if dominant else "LOST"
        )
        summary = f"{self.settings.dominant_hand}: dominant"
        if self.settings.gesture_labels:
            summary = f"{gesture}  ·  PINCH: {dp.state}  ·  " + summary
        if self.settings.diagnostics:
            summary += f"  ·  {intent.type.value} / {intent.owner.value}"
        elif intent.type is Type.CANCEL and intent.reason:
            summary += f"  ·  {intent.reason}"
        if (
            self.live_mode()
            and self.page_name == "Explore"
            and not self.ui_control_button.isChecked()
        ):
            count = len(self.viewport.live_sources)
            summary = f"LIVE · {count} extended fingertips · both hands supported"
        elif self.settings.engine == "PRODUCT" and valid:
            if dominant is None and support is not None:
                summary += f"  ·  Visible {support.track_id} hand is support; choose it as dominant in Settings"
            elif dp.reference is None:
                summary += "  ·  Calibrate hands to enable pinch commits"
            if hand_scene and self.viewport.anchor is None:
                summary += "  ·  Open palm once to anchor, then point/pinch"
            elif hand_scene:
                summary += "  ·  Fingertip controls scene; Control UI switches to menus"
        if self._journal_error:
            summary += "  ·  Intent log incomplete — see Analyze"
        self.feedback.setText(summary)
        if not valid or not focused or modal:
            hint = "Hand control paused. Restore tracking/focus, then open palm to anchor again."
        elif (
            self.live_mode()
            and self.page_name == "Explore"
            and not self.ui_control_button.isChecked()
        ):
            shape = self.registry.current.live_shape
            hint = (
                "Show extended fingertips on either hand; geometry appears automatically."
                if shape is None
                else f"{len(shape.points)} live vertices · {shape.kind} · move any fingertip to reshape. No Add point/pinch needed."
            )
        elif dominant is None and support is not None:
            hint = f"Visible {support.track_id} hand is support. Choose it as dominant in Settings to point or pinch."
        elif self.ui_control_button.isChecked():
            hint = "Menu control: POINT and calibrated PINCH select. Turn Control UI off to interact with the scene."
        elif self.viewport.anchor is None:
            hint = (
                "Open palm once to anchor, then extend only the index finger to point."
            )
        elif (
            dominant
            and dominant.pose == "UNKNOWN"
            and not dp.active
            and dp.state != "CLOSING"
        ):
            hint = "Pose unclear. Extend only the index finger to point; release before a new pinch."
        elif dominant and dominant.pose == "OPEN_PALM":
            hint = "Scene anchored. Fold the other fingers and extend the index finger to point."
        else:
            hint = f"{gesture}: fingertip controls the scene. Control UI switches to menus."
        if (
            dominant
            and valid
            and dp.reference is None
            and not (
                self.live_mode()
                and self.page_name == "Explore"
                and not self.ui_control_button.isChecked()
            )
        ):
            hint += " Calibrate hands to enable pinch commits."
        self.interaction_hint.setText(hint)
        self.home_status.setText(
            f"Tracking: {tracking}   ·   Live geometry: no pinch calibration needed   ·   Session: {frame.run_id}"
            if self.live_mode()
            else f"Tracking: {tracking}   ·   Pinch: {dp.state}   ·   Session: {frame.run_id}"
        )
        if self.page_name == "Analyze":
            diag = {
                "run": frame.run_id,
                "frame": frame.frame_id,
                "tracking": frame.status.value,
                "Core filter": frame.filter_diagnostics.mode.value,
                "illumination": (
                    None if frame.illumination is None else asdict(frame.illumination)
                ),
                "Core timing": asdict(frame.timings),
                "product filter": (
                    "canonical fixed 1-Euro / separate 2-hand pipeline"
                    if self.settings.engine == "PRODUCT"
                    else "not run in LEGACY"
                ),
                "quality": "unavailable",
                "product tracking": reason,
                "intent log": self._journal_error or "recording",
            }
            if self.settings.diagnostics:
                diag.update(
                    intent=asdict(intent),
                    pinch_states={k: v.state for k, v in self.engine.pinches.items()},
                )
            self.diagnostics.setPlainText(json.dumps(diag, indent=2, default=str))
        self.viewport.update()

    def update_environment(self, frame, reason):
        message = ""
        if reason == "TOO_MANY_HANDS":
            message = "More than two hands detected. Gesture control is paused; keep only your hands in view, then release to rearm."
        elif reason in {
            "AMBIGUOUS_OVERLAP",
            "ASSOCIATION_AMBIGUOUS",
            "ROLE_CHANGED",
            "HANDEDNESS_UNAVAILABLE",
        }:
            message = "Hand roles are ambiguous. Separate the hands and release before continuing."
        elif frame.illumination is not None and frame.illumination.state.value in {
            "LOW_LIGHT",
            "DIFFICULT",
        }:
            message = "Low light detected. Add light in front of your hands; contrast enhancement cannot restore missing image detail. Mouse controls remain available."
        if self.page_name == "Explore" and bool(message) != (
            not self.environment_notice.isHidden()
        ):
            self.cancel()  # The notice changes viewport height; never keep an old clutch across that layout.
        self.environment_notice.setText(message)
        self.environment_notice.setVisible(bool(message))

    def _dwell(self, target, activation, timestamp, valid):
        if not self.settings.dwell_select or not valid or activation is None:
            self._dwell_target = self._dwell_since = None
            return
        if target != self._dwell_target:
            self._dwell_target, self._dwell_since = target, timestamp
        elif (
            self._dwell_since is not None
            and timestamp - self._dwell_since >= self.config.dwell_select_s
        ):
            self._dwell_since = None
            activation()

    def closeEvent(self, event):
        self.timer.stop()
        self.cancel()
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            if not self.worker.wait(5000):
                event.ignore()
                self.feedback.setText("Waiting for camera/provider cleanup…")
                self.timer.start(16)
                QTimer.singleShot(1000, self.close)
                return
        self.close_journal()
        self.registry.close()
        if isinstance(self.viewport, Viewport):
            self.viewport.close_renderer()
        event.accept()

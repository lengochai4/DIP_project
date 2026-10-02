"""New native product shell: Explore, Analyze, Evidence, Calibrate, Settings, Help."""

from dataclasses import asdict, replace
import html
import json
import math
import time
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
        self._manual_cycle = 0
        self._manual_active = False
        self._modal_blocked = False
        self._legacy_rearm = True
        self._dwell_target = self._dwell_since = None
        self._ui_cycle = None
        self._ui_hover = None
        self._pose_checks_since = {}
        self._last_tick = time.monotonic()
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
        nav_dock = QDockWidget("Navigation", self)
        nav_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        nav_dock.setWidget(self.navigation)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, nav_dock)
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
        self.feedback = QLabel(
            "POINT: inspect   ·   PINCH: manipulate   ·   OPEN PALM: present   ·   V-SIGN: measure"
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
            "Tracking: stopped   ·   Calibration: required for pinch   ·   Mouse controls: available"
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
        row = QHBoxLayout()
        layout.addLayout(row)
        self.lab_title = QLabel(self.registry.current.title)
        self.lab_title.setObjectName("Title")
        row.addWidget(self.lab_title, 1)
        self.world_button = button(
            row, "WORLD", lambda: self.set_mode("WORLD"), checkable=True
        )
        self.hand_button = button(
            row, "HAND", lambda: self.set_mode("HAND"), checkable=True
        )
        self.world_button.setChecked(True)
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
        self.cancel(clear_reference=True)
        roles = {h.role for h in self.current_hands}
        if not roles:
            self.feedback.setText("Start camera and position a visible hand first.")
            return
        for role in roles:
            self.engine.pinches[role].calibrate()
        self.engine.last = self.latest_identity
        self.engine.context = (
            self.epoch,
            self.page_name,
            self.registry.current.id,
            self.viewport.mode,
            self.settings,
        )
        self.engine.hand_ids = tuple(
            sorted((h.role, h.track_id) for h in self.current_hands)
        )
        self.calibration_step = 1
        self.refresh_calibration()

    def next_calibration(self):
        self.cancel()
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
            bool(self.current_hands),
            self.engine.pinches["DOMINANT"].reference is not None,
            "cycle" in self.calibration_checks,
            "point" in self.calibration_checks,
            "open" in self.calibration_checks,
            False,
        )[self.calibration_step]
        self.calibration_next.setEnabled(ready)
        self.capture_button.setEnabled(self.calibration_step in {0, 1})

    def _settings(self):
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
                    "engine",
                    "pointer_sensitivity",
                    "manipulation_sensitivity",
                ),
            ),
            ("Visual", ("skeleton", "gesture_labels", "grid", "object_labels")),
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
                elif name in {"dominant_hand", "engine"}:
                    control = QComboBox()
                    control.addItems(
                        ("Left", "Right")
                        if name == "dominant_hand"
                        else ("PRODUCT", "LEGACY")
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
                form.addRow(name.replace("_", " ").capitalize(), control)
        button(layout, "Recalibrate", lambda: self.navigate("Calibrate"))
        self._add("Settings", widget)

    def set_preference(self, key, value):
        self.cancel(clear_reference=key in {"dominant_hand", "camera_index", "engine"})
        self.settings = replace(self.settings, **{key: value})
        self.viewport.settings = self.settings
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
            "A small gesture vocabulary, with mouse and keyboard fallback.",
        )
        text = QTextBrowser()
        text.setPlainText(
            "POINT — inspect and highlight. It never rotates the model.\n\nPINCH — after calibration and release/rearm, select or clutch. Hold and move to manipulate.\n\nOPEN PALM — present the active lab on your hand in HAND view. With two hands, the support palm provides the reference.\n\nV-SIGN — enter measure/create mode. POINT previews; PINCH commits. Both index fingers can preview a vector/distance; hold to lock, then pinch with the dominant hand to commit.\n\nTwo-hand scale — calibrate both hands, release/rearm, then pinch with both. Moving two open palms never scales.\n\nMouse — hover to inspect, drag to rotate, wheel to scale. In construction tools a click commits a point.\n\nKeyboard — 1–7 pages; H hand/world; M measure; Enter commit point; R reset; Esc cancel; arrows rotate; +/- scale; Space pause; F11 full screen.\n\nCamera/model errors — mouse and keyboard remain available. Check models/README.md and the selected camera source. Stop before reconnecting.\n\nLost/unknown tracking cancels immediately. Release before trying a new action. No metric camera depth or physical skin-contact detection is provided."
        )
        layout.addWidget(text, 1)
        self._add("Help", widget)

    def _inspector(self):
        self.inspector_dock = QDockWidget("Inspector", self)
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
        layout.addWidget(self.tool_select)
        row = QHBoxLayout()
        layout.addLayout(row)
        button(row, "Commit point", self.commit_point)
        button(row, "Cancel", self.cancel_tool)
        row = QHBoxLayout()
        layout.addLayout(row)
        button(row, "Finish polygon", self.finish_polygon)
        button(row, "Undo", self.undo)
        self.parameter_panel = QWidget()
        self.parameter_form = QFormLayout(self.parameter_panel)
        layout.addWidget(self.parameter_panel)
        self.pause_button = button(layout, "Pause / Resume", self.toggle_pause)
        button(layout, "Reset lab", self.reset_lab)
        self.inspector_text = QTextBrowser()
        layout.addWidget(self.inspector_text, 1)
        self.inspector_dock.setWidget(panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.inspector_dock)
        self.refresh_inspector(rebuild=True)

    def refresh_inspector(self, *, rebuild=False):
        lab = self.registry.current
        self.inspector_text.setPlainText("\n\n".join(lab.inspect()))
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
            names = {
                "orbital": ("radius", "time_rate"),
                "wave": ("amplitude", "frequency", "phase", "samples"),
                "optics": ("index", "focal"),
            }.get(lab.id, ())
            for name in names:
                control = QDoubleSpinBox()
                (
                    control.setRange(4, 128)
                    if name == "samples"
                    else control.setRange(0.1, 6.0)
                )
                control.setValue(
                    lab.time_rate if name == "time_rate" else lab.parameters[name]
                )
                control.setSingleStep(1.0 if name == "samples" else 0.1)
                control.valueChanged.connect(
                    lambda v, key=name: self.set_parameter(key, v)
                )
                self.parameter_form.addRow(name.capitalize(), control)
            self.pause_button.setVisible(lab.id in {"orbital", "wave"})

    def set_parameter(self, key, value):
        self.cancel()
        if key == "time_rate":
            self.registry.current.time_rate = value
        else:
            self.registry.current.parameters[key] = value
        self.viewport.update()
        self.refresh_inspector()

    def choose_preset(self, text):
        if text:
            self.cancel()
            self.registry.current.set_preset(text)
            self.viewport.update()
            self.refresh_inspector()

    def choose_tool(self, text):
        if text:
            self.cancel()
            self.registry.current.set_tool(text)
            self.engine.measure = text != "Inspect"
            self.refresh_inspector()

    def cancel(self, *, clear_reference=False):
        self.epoch += 1
        self._manual_active = False
        self._legacy_rearm = True
        intent = self.engine.reset(clear_reference=clear_reference)
        self.registry.current.on_intent(intent)
        self.anchor.reset()
        self.viewport.anchor = self.viewport.pointer = None
        self.viewport.reference_plane = None
        self._dwell_target = self._dwell_since = None
        self._ui_cycle = None
        if hasattr(self, "touch_cursor"):
            self.touch_cursor.hide()
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
        self.cancel()
        self.page_name = name
        self.stack.setCurrentWidget(self.pages[name])
        self.inspector_dock.setVisible(name == "Explore")
        if name == "Explore":
            QTimer.singleShot(100, self.ensure_renderer)
        if self.navigation.currentRow() != PAGES.index(name):
            self.navigation.blockSignals(True)
            self.navigation.setCurrentRow(PAGES.index(name))
            self.navigation.blockSignals(False)

    def ensure_renderer(self):
        if (
            self.page_name != "Explore"
            or not isinstance(self.viewport, Viewport)
            or self.viewport.isValid()
        ):
            return
        old = self.viewport
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
        self.lab_title.setText(lab.title)
        self.refresh_inspector(rebuild=True)
        self.viewport.update()

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
        self.viewport.update()

    def reset_lab(self):
        self.cancel()
        self.registry.current.reset()
        self.refresh_inspector(rebuild=True)
        self.viewport.update()

    def toggle_pause(self):
        self.registry.current.paused = not self.registry.current.paused

    def finish_polygon(self):
        self.cancel()
        self.registry.current.finish_polygon()
        self.refresh_inspector()
        self.viewport.update()

    def undo(self):
        self.cancel()
        lab = self.registry.current
        if lab.points:
            lab.points.pop()
        elif lab.constructions:
            lab.constructions.pop()
        self.refresh_inspector()
        self.viewport.update()

    def commit_point(self):
        lab = self.registry.current
        if lab.preview is None:
            self.feedback.setText(
                "Point or move the mouse over the viewport before committing."
            )
            return
        point = lab.preview
        self.cancel()
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
            self.cancel()
            self._manual_active = True
            if lab.tool != "Inspect":
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
        elif kind == "drag" and lab.tool == "Inspect":
            self.deliver(
                Intent(
                    Type.DRAG,
                    delta_xy=tuple(
                        v * self.settings.manipulation_sensitivity for v in value
                    ),
                )
            )
        elif kind == "release":
            self._manual_active = False
            self.deliver(Intent(Type.RELEASE, Phase.END))
        elif kind == "scale":
            self.cancel()
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

    def ui_target(self, pointer):
        """Normalized presentation pointer -> native control hit, with one activation callback."""
        pos = QPoint(
            round(pointer[0] * self.width()), round(pointer[1] * self.height())
        )
        target = self.childAt(pos)
        if isinstance(target, QAbstractButton) and target.isEnabled():
            return target, target.click
        for control in (self.navigation, self.library):
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

        UI hits and scene picking share a continuous screen cursor in both modes.
        Camera overlays and the palm anchor retain their source-image coordinates.
        """
        origin = self.viewport.mapTo(self, QPoint(0, 0))
        return (
            (pointer[0] * self.width() - origin.x()) / self.viewport.width(),
            (pointer[1] * self.height() - origin.y()) / self.viewport.height(),
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
                ("R", self.reset_lab),
                ("Esc", self.cancel_tool),
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
            shortcut.activated.connect(
                lambda cb=callback: cb() if self.shortcuts_allowed() else None
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
        enabled = self.shortcuts_allowed()
        for shortcut in self.shortcuts:
            shortcut.setEnabled(enabled)

    def keyboard_motion(self, x, y):
        if self.page_name == "Explore":
            self.cancel()
            self.deliver(Intent(Type.GRAB, Phase.BEGIN))
            self.deliver(Intent(Type.DRAG, delta_xy=(x, y)))
            self.deliver(Intent(Type.RELEASE, Phase.END))

    def keyboard_scale(self, factor):
        if self.page_name == "Explore":
            self.cancel()
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
        if self._journal is not None:
            self._journal.close()
            self._journal = None

    def stop_camera(self):
        self.cancel(clear_reference=True)
        if self.worker is not None:
            self.worker.stop()
            self.worker.take_latest()
        self.clear_tracking("Stopping camera")

    def clear_tracking(self, message):
        self.cancel()
        self.current_hands = ()
        self.last_frame_time = None
        self.viewport.image = None
        self.viewport.landmarks = {}
        self.viewport.update()
        for camera in (self.analysis_camera, self.calibration_camera):
            camera.image = camera.frame = None
            camera.product_landmarks = {}
            camera.message = message
            camera.update()
        self.tracking_label.setText(message)

    def tick(self):
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
        self.latest_identity = frame.run_id, frame.frame_id, frame.timestamp_s
        if self._journal is None:
            directory = ROOT / "runs/product-v2" / frame.run_id
            directory.mkdir(parents=True, exist_ok=True)
            self._journal = (directory / "intents.jsonl").open("a", encoding="utf-8")
            (directory / "settings.json").write_text(
                json.dumps(asdict(self.settings), indent=2), encoding="utf-8"
            )
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
        pose_hand = (
            support
            if support and support.pose == "OPEN_PALM"
            else dominant if dominant and dominant.pose == "OPEN_PALM" else None
        )
        self.viewport.anchor = self.anchor.update(
            pose_hand.palm if pose_hand and valid and focused and not modal else None,
            frame.timestamp_s,
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
        target = activation = None
        if dominant:
            px, py = self.engine.pointer(dominant.pointer_xy, self.settings)
            target, activation = self.ui_target((px, py))
        ui = activation is not None or self.page_name != "Explore"
        context = (
            self.epoch,
            self.page_name,
            self.registry.current.id,
            self.viewport.mode,
            self.settings,
        )
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
            )
        self.viewport.pointer = (
            None
            if intent.pointer_xy is None
            else self.viewport_pointer(intent.pointer_xy)
        )
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
            if not self._manual_active:
                self.registry.current.on_intent(intent)
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
        elif self.page_name == "Explore" and intent.owner in {Owner.SCENE, Owner.TOOL}:
            point = (
                None
                if intent.pointer_xy is None
                else self.viewport.pick_point(self.viewport_pointer(intent.pointer_xy))
            )
            points = tuple(
                self.viewport.scene_point(self.viewport_pointer(p[:2]))
                for p in intent.points
            )
            if any(p is None for p in points):
                # A two-point observation must never degrade into a one-point commit.
                points = ()
                point = None
            plane_pose = intent.anchor_pose
            if plane_pose is not None and self.viewport.mode == "HAND":
                # The shared scene frame already follows the palm in HAND mode.
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
        dp = self.engine.pinches["DOMINANT"]
        self.record_intent(
            intent, "product" if self.settings.engine == "PRODUCT" else "legacy"
        )
        if self.page_name == "Calibrate":
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
            else "READY" if valid else reason
        )
        self.tracking_label.setText(tracking + f" · {len(hands)} hand(s)")
        gesture = (
            ("LEGACY" if legacy_usable else "LOST")
            if self.settings.engine == "LEGACY"
            else dominant.pose if dominant else "LOST"
        )
        self.feedback.setText(
            f"{gesture}  ·  PINCH: {dp.state}  ·  {intent.type.value} / {intent.owner.value}  ·  {self.settings.dominant_hand}: dominant"
        )
        self.home_status.setText(
            f"Tracking: {tracking}   ·   Pinch: {dp.state}   ·   Session: {frame.run_id}"
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
                "product filter": "canonical fixed 1-Euro / separate 2-hand pipeline",
                "quality": "unavailable",
                "product tracking": reason,
                "intent": asdict(intent),
                "pinch states": {k: v.state for k, v in self.engine.pinches.items()},
            }
            self.diagnostics.setPlainText(json.dumps(diag, indent=2, default=str))
        self.viewport.update()

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
        if self._journal is not None:
            self._journal.close()
            self._journal = None
        self.registry.close()
        event.accept()

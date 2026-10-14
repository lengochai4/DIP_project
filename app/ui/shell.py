"""New native product shell: Explore, Analyze, Evidence, Calibrate, Settings, Help."""

from dataclasses import asdict, replace
import html
import json
import math
import time
import numpy as np
from PySide6.QtCore import Qt, QTimer, QPoint, Signal, QEvent
from PySide6.QtGui import QKeySequence, QShortcut, QPixmap, QColor
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
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
from app.extensions.base import FrozenShape
from app.extensions.registry import ExtensionRegistry
from app.interaction.contracts import (
    GestureIntent as Intent,
    IntentType as Type,
    Phase,
    Owner,
)
from app.interaction.engine import IntentEngine
from app.interaction.hand_geometry import describe
from app.interaction.shape_gestures import ShapeGestureEngine, find_hit_shape
from app.interaction.dwell_tracker import DwellTracker
from app.rendering.hand_anchor import HandAnchor
from app.rendering.viewport import Viewport, SoftwareViewport, bgr_image
from app.runtime.application_runtime import RuntimeWorker
from .camera import CameraWidget
from .theme import STYLE
from .lab_guides import PARAMETER_HINTS, guide_text
from .shape_toolbar import ShapeToolbar
from .orientation_gizmo import OrientationGizmo


class MathLibraryList(QListWidget):
    """Custom QListWidget preserving test key navigation semantics while hiding non-math labs."""

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Down:
            self.setCurrentRow(self.currentRow() + 1)
            event.accept()
            return
        elif event.key() == Qt.Key.Key_Up:
            self.setCurrentRow(self.currentRow() - 1)
            event.accept()
            return
        super().keyPressEvent(event)


_SHAPE_RULES = {
    "Circle": "1 tay (trỏ + cái) hoặc 2 tay (2 ngón trỏ) → bán kính.",
    "Square": "1 tay (trỏ + cái → cạnh) hoặc 2 tay (2 ngón trỏ → chéo).",
    "Rectangle": "1 tay (trỏ + cái → tỷ lệ 2:1) hoặc 2 tay (2 ngón trỏ → 2 góc chéo).",
    "Triangle": "1 tay (trỏ + cái + giữa) hoặc 2 tay (tay trỏ+cái gần = đỉnh, tay kia = 2 đỉnh đáy).",
    "Sphere": "Bắt buộc 2 tay: trỏ + cái mỗi tay (tâm = điểm giữa).",
    "Cube": "Bắt buộc 2 tay: trỏ + cái mỗi tay (chéo khối).",
    "Box": "Bắt buộc 2 tay: 4 ngón mỗi tay (chiều dài × chiều rộng khác nhau).",
    "Pyramid": "Bắt buộc 2 tay (mỗi tay 3 ngón trỏ, cái, giữa): tay trỏ-cái ngắn hơn = đỉnh, tay kia = 3 đỉnh đáy.",
}

_SIDEBAR_GUIDE_HTML = """
<div style="color: #a4b8c4; font-size: 11px; line-height: 1.4;">
  <div style="background: rgba(26, 42, 58, 0.7); border: 1px solid #284457; border-radius: 6px; padding: 7px 9px; margin-bottom: 8px;">
    <div style="color: #6ed0e0; font-weight: bold; font-size: 11px; margin-bottom: 3px;">✦ DIP TOUCHLESS STEM</div>
    <div style="color: #9ab3c0; font-size: 10.5px; line-height: 1.35;">
      Hệ thống học tập STEM không chạm: nhận diện bàn tay 3D thời gian thực qua camera RGB thông thường để tương tác trực quan với hình học không gian.
    </div>
  </div>

  <div style="color: #efca82; font-weight: bold; font-size: 10.5px; margin-bottom: 6px; letter-spacing: 0.5px;">
    QUY TRÌNH THAO TÁC CỬ CHỈ
  </div>

  <div style="background: rgba(18, 30, 42, 0.75); border-left: 3px solid #38bdf8; border-radius: 4px; padding: 5px 7px; margin-bottom: 6px;">
    <div style="color: #ffffff; font-weight: bold; font-size: 11px;">1. Chọn hình vẽ</div>
    <div style="color: #8fa6b2; font-size: 10px; line-height: 1.35;">Chỉ <b>1 ngón trỏ</b> vào nút <i>Chọn hình</i> (giữ 1.3s) ở góc trên để mở danh sách hình 2D/3D (ưu tiên khóa 1 tay).</div>
  </div>

  <div style="background: rgba(18, 30, 42, 0.75); border-left: 3px solid #38bdf8; border-radius: 4px; padding: 5px 7px; margin-bottom: 6px;">
    <div style="color: #ffffff; font-weight: bold; font-size: 11px;">2. Tạo hình & Đóng băng</div>
    <div style="color: #8fa6b2; font-size: 10px; line-height: 1.35;">Mở ngón tay theo quy tắc hình đã chọn; <b>giữ yên 1.8s</b> để ghim hình vào không gian. Sau khi tạo, hệ thống tự động ưu tiên khóa tay phải điều khiển.</div>
  </div>

  <div style="background: rgba(18, 30, 42, 0.75); border-left: 3px solid #f59e0b; border-radius: 4px; padding: 5px 7px; margin-bottom: 6px;">
    <div style="color: #ffffff; font-weight: bold; font-size: 11px;">3. Chọn hình điều khiển</div>
    <div style="color: #8fa6b2; font-size: 10px; line-height: 1.35;">
      Dù 1 hay nhiều hình, hình tạo xong luôn ở <b>trạng thái tĩnh</b>. Đặt đầu ngón trỏ vào hình và <b>giữ 0.6s</b>; khi <b>vật thể phát sáng</b> mới tiếp nhận tín hiệu điều khiển.
    </div>
  </div>

  <div style="background: rgba(18, 30, 42, 0.75); border-left: 3px solid #10b981; border-radius: 4px; padding: 5px 7px; margin-bottom: 6px;">
    <div style="color: #ffffff; font-weight: bold; font-size: 11px;">4. Di chuyển vật thể</div>
    <div style="color: #8fa6b2; font-size: 10px; line-height: 1.35;"><b>Chụm ngón cái + trỏ</b> chạm vào hình đang sáng (đã chọn) và kéo trong không gian để di chuyển.</div>
  </div>

  <div style="background: rgba(18, 30, 42, 0.75); border-left: 3px solid #818cf8; border-radius: 4px; padding: 5px 7px; margin-bottom: 6px;">
    <div style="color: #ffffff; font-weight: bold; font-size: 11px;">5. Xoay hình độc lập</div>
    <div style="color: #8fa6b2; font-size: 10px; line-height: 1.35;">Dùng <b>1 ngón trỏ</b> quét ngang/dọc để xoay hình. <b>Cất ngón tay</b>: hình lập tức về trạng thái tĩnh, vẩy tay qua lại không làm biến đổi hình.</div>
  </div>

  <div style="background: rgba(18, 30, 42, 0.75); border-left: 3px solid #ec4899; border-radius: 4px; padding: 5px 7px; margin-bottom: 8px;">
    <div style="color: #ffffff; font-weight: bold; font-size: 11px;">6. Tác vụ nâng cao</div>
    <div style="color: #8fa6b2; font-size: 10px; line-height: 1.35;">Chỉ vào nút <i>Tác vụ</i> để <b>Bung mặt phẳng</b> (trải các mặt khối 3D ra 2D) hoặc Xóa hình đã chọn.</div>
  </div>

  <div style="background: rgba(22, 36, 49, 0.5); border: 1px dashed #284457; border-radius: 5px; padding: 6px 8px;">
    <div style="color: #72bfcc; font-weight: bold; font-size: 10.5px; margin-bottom: 3px;">💡 Mẹo thông minh</div>
    <div style="color: #8fa6b2; font-size: 9.5px; line-height: 1.3;">
      • <b>Khóa tay gần nhất</b>: Bắt tay chính &lt; 1.5m, tự động bỏ qua người phía sau.<br>
      • <b>Ưu tiên tay phải</b>: Khi có cả 2 tay trên màn hình sau tạo hình, hệ thống tự động khóa tay phải điều khiển.<br>
      • <b>Khối xoay Gizmo</b>: Chạm vào mặt Trên/Trước/Trái/Phải để chuyển góc nhìn chuẩn.
    </div>
  </div>
</div>
"""

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
        self.shape_gesture_engine = ShapeGestureEngine()
        self.shape_toolbar = None
        self.orientation_gizmo = None
        self._drag_shape = None
        self._drag_offset = (0.0, 0.0)
        self._shape_select_dwell = DwellTracker(threshold_s=0.6)
        self._prev_rotate_xy = None
        self._view_locked = False
        self._manipulation_locked_hand_id = None
        self._primary_hand_id = None
        self._primary_hand_last_seen_time = None
        self._creation_locked_left_id = None
        self._creation_locked_right_id = None
        self._creation_left_last_seen_time = None
        self._creation_right_last_seen_time = None
        self._single_hand_controlling = False
        self.worker = None
        self._camera_failure = None
        self.page_name = "Home"
        self.epoch = 0
        self.last_frame_time = None
        self._prev_frame_time = None
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
        self._brightness_sampling_counter = 0
        self._brightness_samples = []
        self.average_scene_brightness = 128.0
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
        self._drag_shape = None
        self._drag_screen_xy = None
        self._drag_offset = (0.0, 0.0)
        self._prev_rotate_xy = None
        self._freeze_cooldown_s = 0.0
        self._freeze_cooldown_frames = 0
        self._prev_is_pinched = False
        self._has_env_notice = False
        import collections
        self._rotate_history = collections.deque(maxlen=6)
        self._was_rotating = False
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
        layout.setContentsMargins(14, 10, 14, 14)
        layout.setSpacing(8)

        # Hidden container preserving test/fixture control seams without cluttering the UI
        self._hidden_controls = QWidget(self)
        self._hidden_controls.hide()
        hidden_layout = QHBoxLayout(self._hidden_controls)
        self.guide_button = button(hidden_layout, "Hướng dẫn", self.show_guide, checkable=True)
        self.guide_button.setChecked(self.settings.lab_guide)
        self.expand_button = button(hidden_layout, "Phóng to", self.set_expanded, checkable=True)
        self.world_button = button(
            hidden_layout, "WORLD", lambda: self.set_mode("WORLD"), checkable=True
        )
        self.hand_button = button(
            hidden_layout, "HAND", lambda: self.set_mode("HAND"), checkable=True
        )
        self.world_button.setChecked(True)
        self.hand_button.setEnabled(self.settings.engine == "PRODUCT")
        self.ui_control_button = button(
            hidden_layout, "Control UI", self.set_ui_control, checkable=True
        )
        self.ui_control_button.setVisible(self.live_mode())
        self.tools_button = button(hidden_layout, "Tools", self.show_tools, checkable=True)
        self.reset_button = button(hidden_layout, "Reset view", self.reset_view)

        # Sleek academic presentation header bar (reserving space for logo, project name, 3 team members)
        header_bar = QFrame()
        header_bar.setObjectName("ExploreHeader")
        header_bar.setStyleSheet("""
            QFrame#ExploreHeader {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(20, 32, 44, 235),
                    stop:0.5 rgba(26, 42, 58, 240),
                    stop:1 rgba(20, 32, 44, 235));
                border: 1px solid #284457;
                border-radius: 8px;
                min-height: 42px;
                max-height: 42px;
            }
        """)
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(14, 0, 14, 0)

        self.school_label = QLabel("")
        self.school_label.setStyleSheet("color: #72bfcc; font-weight: bold; font-size: 11px;")
        header_layout.addWidget(self.school_label)

        header_layout.addStretch(1)

        self.lab_title = QLabel("")
        self.lab_title.setStyleSheet("color: #efca82; font-weight: bold; font-size: 12px;")
        header_layout.addWidget(self.lab_title)

        header_layout.addStretch(1)

        self.team_label = QLabel("")
        self.team_label.setStyleSheet("color: #8fa6b2; font-size: 11px; font-weight: 500;")
        header_layout.addWidget(self.team_label)

        layout.addWidget(header_bar)

        self.environment_notice = QLabel(self)
        self.environment_notice.hide()
        self.interaction_hint = QLabel(self)
        self.interaction_hint.hide()

        body = QHBoxLayout()
        layout.addLayout(body, 1)
        self.viewport_layout = body

        # Math library list preserved for automated tests and lab navigation compatibility
        self.library = MathLibraryList()
        self.library.setFixedSize(1, 1)
        self.library.setStyleSheet("border: none; background: transparent;")
        for key, lab in self.registry.extensions.items():
            self.library.addItem(lab.title.replace(" Lab", ""))
        self.library.setCurrentRow(0)
        self.library.currentRowChanged.connect(
            lambda i: (
                self.select_lab(tuple(self.registry.extensions)[i]) if i >= 0 else None
            )
        )

        # Gesture tutorial & project introduction sidebar frame (Item 1)
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setObjectName("SidebarFrame")
        self.sidebar_frame.setFixedWidth(248)
        self.sidebar_frame.setStyleSheet("""
            QFrame#SidebarFrame {
                background: #13202c;
                border: 1px solid #223847;
                border-radius: 8px;
            }
        """)
        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(10, 12, 10, 12)
        sidebar_layout.setSpacing(6)

        self.sidebar_title = QLabel("HƯỚNG DẪN & GIỚI THIỆU")
        self.sidebar_title.setStyleSheet("color: #72bfcc; font-weight: bold; font-size: 11px; letter-spacing: 0.5px;")
        sidebar_layout.addWidget(self.sidebar_title)

        sidebar_scroll = QScrollArea()
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                width: 5px;
                background: transparent;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #284457;
                border-radius: 2px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #3b637d;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        sidebar_container = QWidget()
        sidebar_container.setStyleSheet("background: transparent;")
        container_layout = QVBoxLayout(sidebar_container)
        container_layout.setContentsMargins(0, 2, 4, 2)
        container_layout.setSpacing(6)

        self.sidebar_content = QLabel()
        self.sidebar_content.setTextFormat(Qt.TextFormat.RichText)
        self.sidebar_content.setWordWrap(True)
        self.sidebar_content.setText(_SIDEBAR_GUIDE_HTML)
        container_layout.addWidget(self.sidebar_content)
        container_layout.addStretch(1)

        sidebar_scroll.setWidget(sidebar_container)
        sidebar_layout.addWidget(sidebar_scroll, 1)
        sidebar_layout.addWidget(self.library)

        body.addWidget(self.sidebar_frame)

        cls = SoftwareViewport if software else Viewport
        self.viewport = cls(self.registry, self.config, self.settings)
        self.viewport.manual.connect(self.manual)
        self.shape_toolbar = ShapeToolbar(self.viewport)
        self.orientation_gizmo = OrientationGizmo(self.viewport, self)
        self.orientation_gizmo.show()
        self.viewport.installEventFilter(self)
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
        if hasattr(self, "sidebar_frame") and self.sidebar_frame is not None:
            self.sidebar_frame.setVisible(not expanded)
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
        if hasattr(self, "shape_gesture_engine"):
            self.shape_gesture_engine.reset()
        if hasattr(self, "registry") and self.registry.current:
            self.registry.current.preview_frozen_shape = None
        if clear_reference or not preserve_presentation:
            self.anchor.reset()
            self.viewport.anchor = None
            self.viewport.reference_plane = None
        self._drag_shape = None
        self._prev_rotate_xy = None
        if hasattr(self, "_shape_select_dwell"):
            self._shape_select_dwell.reset()
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

    def eventFilter(self, watched, event):
        if hasattr(self, "viewport") and watched is self.viewport:
            if event.type() == QEvent.Type.Resize:
                if hasattr(self, "shape_toolbar") and self.shape_toolbar is not None:
                    self.shape_toolbar.setGeometry(0, 0, event.size().width(), event.size().height())
                if hasattr(self, "orientation_gizmo") and self.orientation_gizmo is not None:
                    self.orientation_gizmo.reposition()
            elif event.type() == QEvent.Type.MouseButtonPress:
                if (
                    hasattr(self, "shape_toolbar")
                    and self.shape_toolbar is not None
                    and self.shape_toolbar.isVisible()
                ):
                    pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
                    if self.shape_toolbar.handle_mouse_press(pos):
                        return True
        return super().eventFilter(watched, event)

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
        if hasattr(self, "shape_toolbar") and self.shape_toolbar is not None:
            is_coord = (
                hasattr(self, "registry")
                and self.registry.current is not None
                and self.registry.current.id == "coordinate"
            )
            self.shape_toolbar.setVisible(name == "Explore" and is_coord)
            if name == "Explore" and is_coord:
                self.shape_toolbar.setGeometry(self.viewport.rect())
        if hasattr(self, "orientation_gizmo") and self.orientation_gizmo is not None:
            self.orientation_gizmo.setVisible(name == "Explore")
            if name == "Explore":
                self.orientation_gizmo.reposition()
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
        if hasattr(self, "shape_toolbar") and self.shape_toolbar is not None:
            self.shape_toolbar.setParent(fallback)
            fallback.installEventFilter(self)
            self.shape_toolbar.setGeometry(fallback.rect())
            self.shape_toolbar.show()
        if hasattr(self, "orientation_gizmo") and self.orientation_gizmo is not None:
            self.orientation_gizmo.setParent(fallback)
            self.orientation_gizmo.reposition()
            self.orientation_gizmo.show()
        self.feedback.setText(
            "OpenGL unavailable. Software renderer active; all labs remain available."
        )

    def select_lab(self, key):
        self.cancel()
        lab = self.registry.select(key)
        self.library.blockSignals(True)
        self.library.setCurrentRow(tuple(self.registry.extensions).index(key))
        self.library.blockSignals(False)
        self.lab_title.setText("")
        self.refresh_inspector(rebuild=True)
        self.refresh_guide()
        if hasattr(self, "shape_toolbar") and self.shape_toolbar is not None:
            self.shape_toolbar.setVisible(self.page_name == "Explore" and key == "coordinate")
            if key != "coordinate":
                self.shape_toolbar.clear_selection()
        if hasattr(self, "orientation_gizmo") and self.orientation_gizmo is not None:
            self.orientation_gizmo.setVisible(self.page_name == "Explore")
            self.orientation_gizmo.update()
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
        if hasattr(lab, "frozen_shapes"):
            for s in lab.frozen_shapes:
                s.yaw = 0.0
                s.pitch = 0.0
        self._prev_rotate_xy = None
        if hasattr(self, "_rotate_history"):
            self._rotate_history.clear()
        self._was_rotating = False
        if hasattr(self, "orientation_gizmo") and self.orientation_gizmo is not None:
            self.orientation_gizmo.update()
        self.viewport.update()

    def _toggle_view_lock(self):
        self._view_locked = not getattr(self, "_view_locked", False)
        if hasattr(self, "orientation_gizmo") and self.orientation_gizmo is not None:
            self.orientation_gizmo.update()
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
                ("L", self._toggle_view_lock),
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
        if hasattr(self, "registry") and self.registry.current and self.registry.current.id == "coordinate":
            return
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
        self._prev_frame_time = None
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
        self._manipulation_locked_hand_id = None
        self._primary_hand_id = None
        self._primary_hand_last_seen_time = None
        self._creation_locked_left_id = None
        self._creation_locked_right_id = None
        self._creation_left_last_seen_time = None
        self._creation_right_last_seen_time = None
        if hasattr(self, "shape_toolbar") and self.shape_toolbar is not None:
            self.shape_toolbar.update_tip(None, 0.0)
        if hasattr(self, "shape_gesture_engine"):
            self.shape_gesture_engine.reset()
        if hasattr(self, "registry") and self.registry.current:
            self.registry.current.preview_frozen_shape = None
        self.current_hands = ()
        self.last_tracking = self.latest_identity = None
        self.last_frame_time = None
        self._prev_frame_time = None
        if hasattr(self, "_rotate_history"):
            self._rotate_history.clear()
        self._was_rotating = False
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
        now = time.monotonic()
        if self._prev_frame_time is not None:
            frame_dt = max(0.005, min(0.1, now - self._prev_frame_time))
        else:
            frame_dt = 0.033
        self._prev_frame_time = now
        self.last_packet = packet
        self.last_frame_time = now
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
        if hasattr(self, "registry") and self.registry.current is not None:
            self.registry.current.frame_aspect = float(w) / float(h) if h > 0 else 4.0 / 3.0
        hands = []
        for label, landmarks in filtered.items():
            role = "DOMINANT" if label == self.settings.dominant_hand else "SUPPORT"
            hand = describe(landmarks, w, h, self.config, track_id=label, role=role)
            if hand is not None:
                hands.append(hand)

        # 1. Depth estimation model and 1.5m real-world working range cutoff
        def _estimate_hand_depth(h):
            span = getattr(getattr(h, "palm", None), "span", 0.0)
            return 0.09 / max(span, 1e-4)

        in_range_hands = [h for h in hands if _estimate_hand_depth(h) <= 1.5]
        # Sort ascending by depth (closest hand first)
        in_range_hands.sort(key=_estimate_hand_depth)

        # 2. Check manipulation lock
        is_manipulating = (
            (self._drag_shape is not None)
            or (self._prev_rotate_xy is not None)
            or getattr(self, "_was_rotating", False)
        )

        if is_manipulating:
            # Manipulation mode: lock strictly to the initiating hand
            if self._manipulation_locked_hand_id is None and in_range_hands:
                self._manipulation_locked_hand_id = in_range_hands[0].track_id
            if self._manipulation_locked_hand_id is not None:
                hands = [h for h in in_range_hands if h.track_id == self._manipulation_locked_hand_id]
            else:
                hands = []
        else:
            self._manipulation_locked_hand_id = None

            is_shape_creation = (
                getattr(self, "shape_toolbar", None) is not None
                and getattr(self.shape_toolbar, "selected_shape", None) is not None
            )

            _hand_side = self._hand_side

            toolbar_controlling = (
                getattr(self, "shape_toolbar", None) is not None
                and (
                    getattr(self.shape_toolbar, "is_open", False)
                    or getattr(self.shape_toolbar, "hovering_trigger", False)
                    or getattr(self.shape_toolbar, "is_task_open", False)
                )
            )
            has_frozen = (
                hasattr(getattr(self, "registry", None), "current")
                and hasattr(self.registry.current, "frozen_shapes")
                and len(self.registry.current.frozen_shapes) > 0
            )
            gizmo_hover = getattr(getattr(self, "orientation_gizmo", None), "_hovering", False)
            not_explore = (getattr(self, "page_name", "") != "Explore")

            is_controlling = (
                is_manipulating
                or toolbar_controlling
                or has_frozen
                or gizmo_hover
                or not_explore
            )

            if is_controlling and not is_shape_creation:
                self._single_hand_controlling = True
                # Single controlling hand mode:
                # Strictly lock onto 1 controlling hand; reject any other hand (whether Left or Right)
                # unless the locked hand has been hidden from camera for >= 1.0s.
                self._creation_locked_left_id = None
                self._creation_locked_right_id = None

                if self._primary_hand_id is not None:
                    matching = next((h for h in in_range_hands if h.track_id == self._primary_hand_id), None)
                    if matching is not None:
                        self._primary_hand_last_seen_time = now
                        hands = [matching]
                    else:
                        lost_elapsed = now - (self._primary_hand_last_seen_time or now)
                        if lost_elapsed >= 1.0:
                            if in_range_hands:
                                right_cand = next(
                                    (h for h in in_range_hands if _hand_side(h) == "Right" or h.role == "DOMINANT"),
                                    in_range_hands[0],
                                )
                                self._primary_hand_id = right_cand.track_id
                                self._primary_hand_last_seen_time = now
                                hands = [right_cand]
                            else:
                                self._primary_hand_id = None
                                self._primary_hand_last_seen_time = None
                                self._single_hand_controlling = False
                                hands = []
                        else:
                            # Lost for < 1.0s: hold lock, do NOT recognize any other hand!
                            hands = []
                elif in_range_hands:
                    right_cand = next(
                        (h for h in in_range_hands if _hand_side(h) == "Right" or h.role == "DOMINANT"),
                        in_range_hands[0],
                    )
                    self._primary_hand_id = right_cand.track_id
                    self._primary_hand_last_seen_time = now
                    hands = [right_cand]
                else:
                    hands = []
            else:
                self._single_hand_controlling = False
                self._primary_hand_id = None
                self._primary_hand_last_seen_time = None

                left_candidates = [h for h in in_range_hands if _hand_side(h) == "Left"]
                right_candidates = [h for h in in_range_hands if _hand_side(h) == "Right"]

                # Left hand tracking & lock
                active_left = None
                if self._creation_locked_left_id is not None:
                    matching = next((h for h in left_candidates if h.track_id == self._creation_locked_left_id), None)
                    if matching is not None:
                        best_left = left_candidates[0]
                        if (
                            best_left.track_id != self._creation_locked_left_id
                            and _estimate_hand_depth(best_left) < _estimate_hand_depth(matching) - 0.15
                        ):
                            self._creation_locked_left_id = best_left.track_id
                            self._creation_left_last_seen_time = now
                            active_left = best_left
                        else:
                            self._creation_left_last_seen_time = now
                            active_left = matching
                    else:
                        lost_elapsed = now - (self._creation_left_last_seen_time or now)
                        if lost_elapsed >= 1.0:
                            self._creation_locked_left_id = left_candidates[0].track_id if left_candidates else None
                            self._creation_left_last_seen_time = now if left_candidates else None
                            active_left = left_candidates[0] if left_candidates else None
                        else:
                            active_left = None
                elif left_candidates:
                    self._creation_locked_left_id = left_candidates[0].track_id
                    self._creation_left_last_seen_time = now
                    active_left = left_candidates[0]

                # Right hand tracking & lock
                active_right = None
                if self._creation_locked_right_id is not None:
                    matching = next((h for h in right_candidates if h.track_id == self._creation_locked_right_id), None)
                    if matching is not None:
                        best_right = right_candidates[0]
                        if (
                            best_right.track_id != self._creation_locked_right_id
                            and _estimate_hand_depth(best_right) < _estimate_hand_depth(matching) - 0.15
                        ):
                            self._creation_locked_right_id = best_right.track_id
                            self._creation_right_last_seen_time = now
                            active_right = best_right
                        else:
                            self._creation_right_last_seen_time = now
                            active_right = matching
                    else:
                        lost_elapsed = now - (self._creation_right_last_seen_time or now)
                        if lost_elapsed >= 1.0:
                            self._creation_locked_right_id = right_candidates[0].track_id if right_candidates else None
                            self._creation_right_last_seen_time = now if right_candidates else None
                            active_right = right_candidates[0] if right_candidates else None
                        else:
                            active_right = None
                elif right_candidates:
                    self._creation_locked_right_id = right_candidates[0].track_id
                    self._creation_right_last_seen_time = now
                    active_right = right_candidates[0]

                hands = [h for h in (active_left, active_right) if h is not None]

        # Keep filtered landmarks synchronized with active hands to eliminate CPU & drawing overhead
        active_ids = {h.track_id for h in hands}
        filtered = {k: v for k, v in filtered.items() if k in active_ids}

        self.current_hands = tuple(hands)
        self.viewport.image = bgr_image(packet.image)

        # Sample average frame brightness over 5-10 frames when a task opens or starts
        if getattr(self, "_brightness_sampling_counter", 0) > 0:
            if getattr(packet, "image", None) is not None:
                sub = packet.image[::8, ::8]
                self._brightness_samples.append(float(np.mean(sub)))
                self._brightness_sampling_counter -= 1
                if self._brightness_sampling_counter == 0 and self._brightness_samples:
                    self.average_scene_brightness = float(np.mean(self._brightness_samples))
                    # Adjust text intensity (white -> black) to maximize contrast with background
                    if self.average_scene_brightness >= 128.0:
                        text_intensity = int(max(15, min(50, 255 - self.average_scene_brightness * 1.4)))
                    else:
                        text_intensity = int(min(245, max(200, 255 - self.average_scene_brightness * 0.4)))
                    if hasattr(self, "viewport") and self.viewport is not None:
                        self.viewport.label_color = QColor(text_intensity, text_intensity, text_intensity)
                        self.viewport.update()

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

        # Touchless Shape Toolbar update (Explore page)
        shape_drawing_active = False
        is_coord = (
            self.page_name == "Explore"
            and hasattr(self, "registry")
            and self.registry.current is not None
            and self.registry.current.id == "coordinate"
        )
        if self.page_name == "Explore":
            # Pointing fingertip drives touchless UI (Shape toolbar & Orientation gizmo)
            pointing_hand = next(
                (h for h in hands if self._is_pointing_hand(h) and h.role == "DOMINANT"),
                next((h for h in hands if self._is_pointing_hand(h)), None),
            )
            tip_xy = (
                self.viewport.fingertip_pointer(pointing_hand.pointer_xy)
                if pointing_hand is not None
                else None
            )

            is_dragging = (self._drag_shape is not None)
            toolbar_tip = (
                self._drag_screen_xy
                if (is_dragging and getattr(self, "_drag_screen_xy", None) is not None)
                else tip_xy
            )

            if hasattr(self, "orientation_gizmo") and self.orientation_gizmo is not None:
                self.orientation_gizmo.update_tip(tip_xy, frame_dt)

            if hasattr(self, "shape_toolbar") and self.shape_toolbar is not None and is_coord:
                frozen_shapes = getattr(self.registry.current, "frozen_shapes", [])
                selected_shape_id = getattr(self.registry.current, "selected_shape_id", None)
                self.shape_toolbar.update_tip(
                    toolbar_tip,
                    frame_dt,
                    is_dragging_shape=is_dragging,
                    frozen_shapes=frozen_shapes,
                    selected_shape_id=selected_shape_id,
                    shape_select_frac=getattr(self._shape_select_dwell, "fraction", 0.0),
                )
                animating_unfold = False
                for fs in frozen_shapes:
                    target_unfold = 1.0 if "unfold" in getattr(fs, "tasks", set()) else 0.0
                    curr_unfold = getattr(fs, "unfold_progress", 0.0)
                    if abs(curr_unfold - target_unfold) > 1e-4:
                        animating_unfold = True
                        step = 2.5 * max(0.001, frame_dt)
                        if curr_unfold < target_unfold:
                            fs.unfold_progress = min(target_unfold, curr_unfold + step)
                        else:
                            fs.unfold_progress = max(target_unfold, curr_unfold - step)
                if animating_unfold:
                    self.viewport.update()

                if getattr(self.shape_toolbar, "task_dropdown_opened", False) or getattr(self.shape_toolbar, "task_started", False):
                    self._brightness_sampling_counter = 8
                    self._brightness_samples = []
                    self.shape_toolbar.task_dropdown_opened = False
                    self.shape_toolbar.task_started = False

                if self.shape_toolbar.last_task_event:
                    self.feedback.setText(self.shape_toolbar.last_task_event)
                    self._shape_instruction = self.shape_toolbar.last_task_event
                    self.shape_toolbar.clear_task_event()
                    self.viewport.update()

            # Delete button events
            if self.shape_toolbar.delete_event == "ALL":
                self.registry.current.clear_frozen_shapes()
                self._drag_shape = None
                self._drag_screen_xy = None
                self.shape_toolbar.clear_delete_event()
                self._shape_instruction = "Đã xóa tất cả hình trên scene."
                self.feedback.setText("Đã xóa tất cả hình trên scene.")
                self.viewport.update()
            elif self.shape_toolbar.delete_event == "DRAG_SINGLE":
                if self._drag_shape is not None and hasattr(self.registry.current, "frozen_shapes"):
                    if self._drag_shape in self.registry.current.frozen_shapes:
                        self.registry.current.frozen_shapes.remove(self._drag_shape)
                    elif self.registry.current.frozen_shapes:
                        self.registry.current.frozen_shapes.pop()
                    self._shape_instruction = f"Đã xóa hình {self._drag_shape.kind}."
                    self.feedback.setText(self._shape_instruction)
                    self._drag_shape = None
                    self._drag_screen_xy = None
                elif hasattr(self.registry.current, "frozen_shapes") and self.registry.current.frozen_shapes:
                    removed = self.registry.current.frozen_shapes.pop()
                    self._shape_instruction = f"Đã xóa hình {removed.kind}."
                    self.feedback.setText(self._shape_instruction)
                self.shape_toolbar.clear_delete_event()
                self.viewport.update()

            # Shape drawing
            if self.shape_toolbar.selected_shape is not None:
                shape_drawing_active = True
                shape_type = self.shape_toolbar.selected_shape
                candidate = self.shape_gesture_engine.update(
                    hands, shape_type, mirror=self.settings.mirror, dt=frame_dt
                )
                if candidate.params is not None:
                    p = candidate.params
                    params_dict = {
                        "center_xy": p.center_xy,
                        "radius": p.radius,
                        "width": p.width,
                        "height": p.height,
                        "corners_xy": p.corners_xy,
                        "corners_3d": p.corners_3d,
                        "size": p.size,
                        "hands_used": p.hands_used,
                    }
                    if candidate.is_stable:
                        frozen = FrozenShape(kind=shape_type, params=params_dict)
                        self.registry.current.add_frozen_shape(frozen)
                        self.registry.current.selected_shape_id = None
                        self.registry.current.preview_frozen_shape = None
                        self.shape_toolbar.clear_selection()
                        self.shape_gesture_engine.reset()
                        self._freeze_cooldown_s = 1.5
                        self._freeze_cooldown_frames = 39  # cooldown matching ~1.5s
                        self._drag_shape = None
                        self._prev_is_pinched = True       # prevent immediate grab
                        self._prev_rotate_xy = None
                        self._shape_instruction = (
                            f"Đã đóng băng {shape_type} vào scene (trạng thái tĩnh). Giữ ngón trỏ lên vật thể để chọn."
                        )
                        self.feedback.setText(self._shape_instruction)
                        shape_drawing_active = False

                        # Lock immediately to the Right hand (Hand 1) upon freezing for subsequent control
                        right_cand = next(
                            (h for h in hands if self._hand_side(h) == "Right" or h.role == "DOMINANT"),
                            hands[0] if hands else None,
                        )
                        if right_cand is not None:
                            self._primary_hand_id = right_cand.track_id
                            self._primary_hand_last_seen_time = now
                            self._single_hand_controlling = True
                            hands = [right_cand]
                            self.current_hands = (right_cand,)
                    else:
                        self.registry.current.preview_frozen_shape = FrozenShape(
                            kind=shape_type, params=params_dict
                        )
                        pct = int(candidate.stable_fraction * 100)
                        self._last_candidate_pct = pct
                        self._shape_instruction = (
                            f"Vẽ {shape_type}: Giữ yên ngón tay... ({pct}%)"
                        )
                        self.feedback.setText(self._shape_instruction)
                else:
                    self.registry.current.preview_frozen_shape = None
                    if candidate.reason == "NEED_SECOND_HAND":
                        self._shape_instruction = (
                            f"Vẽ {shape_type}: {_SHAPE_RULES.get(shape_type, 'Cần đưa cả 2 tay vào khung hình.')}"
                        )
                    elif candidate.reason == "NO_DOMINANT_HAND":
                        self._shape_instruction = (
                            f"Vẽ {shape_type}: Cần nhận diện bàn tay trong khung hình."
                        )
                    else:
                        self._shape_instruction = (
                            f"Vẽ {shape_type}: {_SHAPE_RULES.get(shape_type, 'Mở các ngón tay theo quy tắc.')}"
                        )
                    self.feedback.setText(self._shape_instruction)
            else:
                self.registry.current.preview_frozen_shape = None

            # Direct manipulation of frozen shapes (Pinch to Move, Index Point to Rotate)
            if (
                self.shape_toolbar.selected_shape is None
                and hasattr(self.registry.current, "frozen_shapes")
            ):
                cooldown_s = getattr(self, "_freeze_cooldown_s", 0.0)
                if cooldown_s > 0.0 or getattr(self, "_freeze_cooldown_frames", 0) > 0:
                    self._freeze_cooldown_s = max(0.0, cooldown_s - frame_dt)
                    if getattr(self, "_freeze_cooldown_frames", 0) > 0:
                        self._freeze_cooldown_frames -= 1
                    self._drag_shape = None
                    self._prev_rotate_xy = None
                    self._prev_is_pinched = False
                else:
                    pointing_hand = next(
                        (h for h in hands if h.role == "DOMINANT"),
                        hands[0] if hands else None,
                    )
                    if pointing_hand is not None and len(pointing_hand.tip_samples) >= 2:
                        thb = pointing_hand.tip_samples[0]
                        idx = pointing_hand.tip_samples[1]
                        d_pinch = math.hypot(thb.xy[0] - idx.xy[0], thb.xy[1] - idx.xy[1])

                        # Tight pinch threshold: actual physical contact (0.045 to grab, 0.065 to release)
                        # No loose pinch_ratio so relaxed/curled hands never accidentally trigger
                        is_pinched = (d_pinch < 0.065) if (self._drag_shape is not None) else (d_pinch < 0.045)
                        was_pinched = getattr(self, "_prev_is_pinched", False)
                        self._prev_is_pinched = is_pinched

                        raw_px = (thb.xy[0] + idx.xy[0]) / 2
                        raw_py = (thb.xy[1] + idx.xy[1]) / 2
                        pinch_screen_x = 1.0 - raw_px if self.settings.mirror else raw_px
                        pinch_screen_y = raw_py
                        pinch_xy = (pinch_screen_x, pinch_screen_y)

                        # 1. MOVE SHAPE VIA PINCH TOUCH
                        # Only grab if user performs an explicit pinch-down transition while over the shape
                        if self._drag_shape is None and is_pinched and not was_pinched:
                            if self.registry.current.frozen_shapes:
                                hit = find_hit_shape(self.registry.current.frozen_shapes, pinch_xy)
                                cur_sel_id = getattr(self.registry.current, "selected_shape_id", None)
                                # Exclusive control: ONLY the selected shape can be moved via pinch!
                                if hit is not None and cur_sel_id is not None and hit.shape_id == cur_sel_id:
                                    self._drag_shape = hit
                                    self._manipulation_locked_hand_id = pointing_hand.track_id
                                    hcx, hcy = hit.params.get("center_xy", (0.5, 0.5))
                                    self._drag_offset = (hcx - pinch_xy[0], hcy - pinch_xy[1])

                        if is_pinched and self._drag_shape is not None:
                            self._prev_rotate_xy = None  # disable rotation while moving
                            if hasattr(self, "_shape_select_dwell"):
                                self._shape_select_dwell.reset()
                            if hasattr(self, "shape_toolbar") and self.shape_toolbar is not None:
                                self.shape_toolbar._shape_select_frac = 0.0
                            self._drag_screen_xy = pinch_xy
                            old_cx, old_cy = self._drag_shape.params.get("center_xy", (0.5, 0.5))
                            new_cx = min(0.95, max(0.05, pinch_xy[0] + self._drag_offset[0]))
                            new_cy = min(0.95, max(0.05, pinch_xy[1] + self._drag_offset[1]))
                            dx = new_cx - old_cx
                            dy = new_cy - old_cy
                            self._drag_shape.params["center_xy"] = (new_cx, new_cy)
                            if (
                                "corners_xy" in self._drag_shape.params
                                and self._drag_shape.params["corners_xy"]
                            ):
                                self._drag_shape.params["corners_xy"] = tuple(
                                    (c[0] + dx, c[1] + dy)
                                    for c in self._drag_shape.params["corners_xy"]
                                )
                            if (
                                "corners_3d" in self._drag_shape.params
                                and self._drag_shape.params["corners_3d"]
                            ):
                                self._drag_shape.params["corners_3d"] = tuple(
                                    (c[0] + dx, c[1] + dy, c[2])
                                    for c in self._drag_shape.params["corners_3d"]
                                )
                            self._shape_instruction = f"Đang di chuyển {self._drag_shape.kind}..."
                            self.feedback.setText(self._shape_instruction)
                            self.viewport.update()
                        else:
                            if self._drag_shape is not None:
                                self.registry.current.selected_shape_id = None
                                if hasattr(self, "shape_toolbar") and self.shape_toolbar is not None:
                                    self.shape_toolbar._selected_shape_id = None
                                self.viewport.update()
                            self._drag_shape = None
                            self._drag_screen_xy = None

                            # 2. ROTATE SCENE VIA INDEX FINGER (3 Solutions Applied)
                            raw_ix, raw_iy = idx.xy
                            screen_ix = 1.0 - raw_ix if self.settings.mirror else raw_ix
                            screen_iy = raw_iy
                            screen_ixy = (screen_ix, screen_iy)

                            is_pointing = pointing_hand.pose == "POINT" or (
                                len(pointing_hand.fingers) >= 5
                                and pointing_hand.fingers[1]
                                and not any(pointing_hand.fingers[2:])
                            )
                            # Solution 1: Buffer Zone (disable rotation when finger in top-right toolbar area)
                            in_toolbar_zone = screen_ix > 0.60 and screen_iy < 0.42

                            # Solution 2: Context-aware Lock (disable rotation while toolbar open, drawing shape, or gizmo hovered)
                            toolbar_busy = (
                                getattr(self.shape_toolbar, "hovering_trigger", False)
                                or getattr(self.shape_toolbar, "is_open", False)
                                or getattr(self.shape_toolbar, "is_task_open", False)
                            )
                            drawing_active = getattr(
                                self.shape_toolbar, "drawing_shape", False
                            ) or shape_drawing_active
                            gizmo_busy = getattr(
                                getattr(self, "orientation_gizmo", None), "_hovering", False
                            )

                            # Solution 3: Lock View Angle (_view_locked)
                            view_locked = getattr(self, "_view_locked", False)

                            can_rotate = (
                                is_pointing
                                and not is_pinched
                                and not toolbar_busy
                                and not drawing_active
                                and not gizmo_busy
                                and not in_toolbar_zone
                                and not view_locked
                            )

                            frozen_shapes = getattr(self.registry.current, "frozen_shapes", [])
                            cur_sel_id = getattr(self.registry.current, "selected_shape_id", None)
                            is_dwelling_selection = False

                            if frozen_shapes:
                                if can_rotate and self._prev_rotate_xy is None:
                                    hit = find_hit_shape(frozen_shapes, screen_ixy)
                                    if hit is not None and hit.shape_id != cur_sel_id:
                                        is_dwelling_selection = True
                                        if hasattr(self, "_shape_select_dwell"):
                                            dwell_ev = self._shape_select_dwell.update(hit.shape_id, frame_dt)
                                            frac = getattr(self._shape_select_dwell, "fraction", 0.0)
                                            if hasattr(self, "shape_toolbar") and self.shape_toolbar is not None:
                                                self.shape_toolbar._shape_select_frac = frac
                                                self.shape_toolbar.update()
                                            if (dwell_ev is not None and dwell_ev.state in ("ENTER", "HOLD")) or frac >= 1.0:
                                                self.registry.current.selected_shape_id = hit.shape_id
                                                cur_sel_id = hit.shape_id
                                                if hasattr(self, "shape_toolbar") and self.shape_toolbar is not None:
                                                    self.shape_toolbar._selected_shape_id = hit.shape_id
                                                self._shape_select_dwell.reset()
                                                if hasattr(self, "shape_toolbar") and self.shape_toolbar is not None:
                                                    self.shape_toolbar._shape_select_frac = 0.0
                                                    self.shape_toolbar.update()
                                                self._shape_instruction = f"Đã chọn {hit.kind}. Sẵn sàng điều khiển."
                                                self.feedback.setText(self._shape_instruction)
                                                self.viewport.update()
                                            else:
                                                pct = int(frac * 100)
                                                self._shape_instruction = f"Giữ ngón tay để chọn {hit.kind}... ({pct}%)"
                                                self.feedback.setText(self._shape_instruction)
                                                self.viewport.update()
                                    else:
                                        if hasattr(self, "_shape_select_dwell"):
                                            self._shape_select_dwell.reset()
                                        if hasattr(self, "shape_toolbar") and self.shape_toolbar is not None:
                                            self.shape_toolbar._shape_select_frac = 0.0
                                else:
                                    if hasattr(self, "_shape_select_dwell"):
                                        self._shape_select_dwell.reset()
                                    if hasattr(self, "shape_toolbar") and self.shape_toolbar is not None:
                                        self.shape_toolbar._shape_select_frac = 0.0

                            # Active target shape identification
                            active_shape = None
                            if frozen_shapes:
                                if cur_sel_id is not None:
                                    for fs in frozen_shapes:
                                        if fs.shape_id == cur_sel_id:
                                            active_shape = fs
                                            break

                            if is_dwelling_selection:
                                can_rotate = False

                            if can_rotate:
                                self._manipulation_locked_hand_id = pointing_hand.track_id
                                if self._prev_rotate_xy is not None:
                                    d_rx = screen_ix - self._prev_rotate_xy[0]
                                    d_ry = screen_iy - self._prev_rotate_xy[1]
                                    if math.hypot(d_rx, d_ry) < 0.15:
                                        ROTATION_SENSITIVITY = 2.64  # Increased by 20% (was 2.2)
                                        if active_shape is not None:
                                            active_shape.yaw = (
                                                active_shape.yaw + d_rx * ROTATION_SENSITIVITY
                                            ) % (2 * math.pi)
                                            new_pitch = (
                                                active_shape.pitch - d_ry * ROTATION_SENSITIVITY
                                            ) % (2 * math.pi)
                                            if active_shape.kind in ("Circle", "Square", "Triangle", "Rectangle"):
                                                if abs(math.cos(new_pitch)) < 0.08:
                                                    step = 0.10 if d_ry < 0 else -0.10
                                                    new_pitch = (new_pitch + step) % (2 * math.pi)
                                            active_shape.pitch = new_pitch
                                            if hasattr(self.registry.current, "yaw"):
                                                self.registry.current.yaw = active_shape.yaw
                                                self.registry.current.pitch = active_shape.pitch
                                            cur_rot = (active_shape.yaw, active_shape.pitch)
                                            self._shape_instruction = f"Xoay {active_shape.kind} độc lập theo ngón trỏ..."
                                            self._rotate_history.append(cur_rot)
                                            self._was_rotating = True
                                        elif not frozen_shapes:
                                            self.registry.current.yaw = (
                                                self.registry.current.yaw + d_rx * ROTATION_SENSITIVITY
                                            ) % (2 * math.pi)
                                            new_pitch = (
                                                self.registry.current.pitch - d_ry * ROTATION_SENSITIVITY
                                            ) % (2 * math.pi)
                                            has_planar = False
                                            if hasattr(self.registry.current, "frozen_shapes"):
                                                has_planar = any(
                                                    fs.kind in ("Circle", "Square", "Triangle", "Rectangle")
                                                    for fs in self.registry.current.frozen_shapes
                                                )
                                            if has_planar:
                                                if abs(math.cos(new_pitch)) < 0.08:
                                                    step = 0.10 if d_ry < 0 else -0.10
                                                    new_pitch = (new_pitch + step) % (2 * math.pi)
                                            self.registry.current.pitch = new_pitch
                                            cur_rot = (self.registry.current.yaw, self.registry.current.pitch)
                                            self._shape_instruction = "Xoay hình theo ngón trỏ..."
                                            self._rotate_history.append(cur_rot)
                                            self._was_rotating = True

                                        self.feedback.setText(self._shape_instruction)
                                        self.viewport.update()
                                        if hasattr(self, "orientation_gizmo") and self.orientation_gizmo is not None:
                                            self.orientation_gizmo.update()
                                if active_shape is not None or not frozen_shapes:
                                    self._prev_rotate_xy = screen_ixy
                                else:
                                    self._prev_rotate_xy = None
                            else:
                                if self._was_rotating:
                                    # Solution A Disengagement Rollback: Cancel out trailing curl flick
                                    if len(self._rotate_history) >= 3:
                                        rb_idx = 0 if len(self._rotate_history) <= 4 else -4
                                        rb_yaw, rb_pitch = self._rotate_history[rb_idx]
                                        if active_shape is not None:
                                            active_shape.yaw = rb_yaw
                                            active_shape.pitch = rb_pitch
                                        if hasattr(self.registry.current, "yaw"):
                                            self.registry.current.yaw = rb_yaw
                                            self.registry.current.pitch = rb_pitch
                                        self.viewport.update()
                                        if hasattr(self, "orientation_gizmo") and self.orientation_gizmo is not None:
                                            self.orientation_gizmo.update()
                                    self._rotate_history.clear()
                                    self._was_rotating = False
                                    # Finger put away -> shape enters static state immediately
                                    self.registry.current.selected_shape_id = None
                                    if hasattr(self, "shape_toolbar") and self.shape_toolbar is not None:
                                        self.shape_toolbar._selected_shape_id = None
                                    self._shape_instruction = "Vật thể ở trạng thái tĩnh. Giữ ngón trỏ vào vật thể để chọn lại."
                                    self.feedback.setText(self._shape_instruction)
                                    self.viewport.update()
                                elif not is_pointing and cur_sel_id is not None:
                                    # Disengagement without prior rotating: return shape to static state
                                    self.registry.current.selected_shape_id = None
                                    if hasattr(self, "shape_toolbar") and self.shape_toolbar is not None:
                                        self.shape_toolbar._selected_shape_id = None
                                    self.viewport.update()
                                self._prev_rotate_xy = None
                    else:
                        if self._was_rotating:
                            if len(self._rotate_history) >= 3:
                                rb_idx = 0 if len(self._rotate_history) <= 4 else -4
                                rb_yaw, rb_pitch = self._rotate_history[rb_idx]
                                active_shape = None
                                if hasattr(self.registry.current, "frozen_shapes") and self.registry.current.frozen_shapes:
                                    sel_id = getattr(self.registry.current, "selected_shape_id", None)
                                    for fs in self.registry.current.frozen_shapes:
                                        if fs.shape_id == sel_id:
                                            active_shape = fs
                                            break
                                if active_shape is not None:
                                    active_shape.yaw = rb_yaw
                                    active_shape.pitch = rb_pitch
                                if hasattr(self.registry.current, "yaw"):
                                    self.registry.current.yaw = rb_yaw
                                    self.registry.current.pitch = rb_pitch
                                self.viewport.update()
                                if hasattr(self, "orientation_gizmo") and self.orientation_gizmo is not None:
                                    self.orientation_gizmo.update()
                            self._rotate_history.clear()
                            self._was_rotating = False
                        if hasattr(self.registry.current, "selected_shape_id") and self.registry.current.selected_shape_id is not None:
                            self.registry.current.selected_shape_id = None
                        if hasattr(self, "shape_toolbar") and self.shape_toolbar is not None:
                            self.shape_toolbar._selected_shape_id = None
                        self._drag_shape = None
                        self._prev_rotate_xy = None
                        self._prev_is_pinched = False
                        if hasattr(self, "_shape_select_dwell"):
                            self._shape_select_dwell.reset()
                        if hasattr(self, "shape_toolbar") and self.shape_toolbar is not None:
                            self.shape_toolbar._shape_select_frac = 0.0

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
            if shape_drawing_active:
                self.registry.current.live_shape = None
                self.viewport.live_sources = ()
            elif is_coord and packet.source_name != "synthetic":
                self.registry.current.live_shape = None
                self.viewport.live_sources = ()
            elif intent.live_geometry:
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
        is_coord = (
            self.page_name == "Explore"
            and hasattr(self, "registry")
            and self.registry.current is not None
            and self.registry.current.id == "coordinate"
        )
        is_synthetic = (
            hasattr(self, "last_packet")
            and self.last_packet is not None
            and self.last_packet.source_name == "synthetic"
        )
        if is_coord and not is_synthetic:
            if (
                hasattr(self, "shape_toolbar")
                and self.shape_toolbar is not None
                and self.shape_toolbar.selected_shape is not None
            ):
                shape_type = self.shape_toolbar.selected_shape
                if self.registry.current.preview_frozen_shape is not None:
                    pct = int(getattr(self, "_last_candidate_pct", 0))
                    msg = f"Vẽ {shape_type}: Giữ yên ngón tay... ({pct}%)"
                else:
                    msg = getattr(
                        self,
                        "_shape_instruction",
                        f"Vẽ {shape_type}: {_SHAPE_RULES.get(shape_type, 'Mở các ngón tay để tạo hình.')}",
                    )
            elif getattr(self, "_drag_shape", None) is not None:
                msg = getattr(self, "_shape_instruction", f"Đang di chuyển hình {self._drag_shape.kind} theo tay chụm...")
            elif getattr(self, "_prev_rotate_xy", None) is not None:
                msg = getattr(self, "_shape_instruction", "Đang xoay góc nhìn theo ngón trỏ...")
            elif getattr(self, "_shape_instruction", None):
                msg = self._shape_instruction
            elif (
                hasattr(self.registry.current, "frozen_shapes")
                and self.registry.current.frozen_shapes
            ):
                msg = "Chụm ngón trỏ + cái chạm vào hình để di chuyển. Dùng 1 ngón trỏ để xoay."
            else:
                msg = getattr(
                    self,
                    "_shape_instruction",
                    "Chỉ ngón trỏ vào nút Chọn hình góc trên bên phải (giữ 1.3s) để chọn hình muốn vẽ.",
                )
            self.feedback.setText(msg)
            hint = msg
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

    @staticmethod
    def _is_pointing_hand(h) -> bool:
        if h is None:
            return False
        if h.pose == "POINT":
            return True
        if hasattr(h, "fingers") and len(h.fingers) >= 5:
            # Relaxed pointing: index finger extended, ring and pinky curled, not open palm
            _, idx, mid, ring, pnk = h.fingers[:5]
            if idx and not (ring and pnk) and not all(h.fingers[:5]):
                return True
        return False

    @staticmethod
    def _hand_side(h) -> str:
        if h is None:
            return "Right"
        tid = str(getattr(h, "track_id", "")).lower()
        role = str(getattr(h, "role", "")).upper()
        if "left" in tid:
            return "Left"
        if "right" in tid:
            return "Right"
        if role == "DOMINANT":
            return "Right"
        if role == "SUPPORT":
            return "Left"
        tips = getattr(h, "tips", ())
        if len(tips) >= 5:
            return "Right" if tips[0].position[0] > tips[4].position[0] else "Left"
        return "Right" if getattr(h, "pointer_xy", (0.5, 0.5))[0] > 0.5 else "Left"

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
        
        has_msg = bool(message)
        prev_has_msg = getattr(self, "_has_env_notice", False)
        self._has_env_notice = has_msg
        if self.page_name == "Explore" and has_msg and not prev_has_msg:
            self.cancel()
        self.environment_notice.setText(message)
        self.environment_notice.hide()

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

"""Extension Hub UI Page - Modern visual control panel for all 3 Extension pillars."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QScrollArea, QComboBox, QCheckBox, QSlider
)
from app.extensions.hub.manager import ExtensionManager
from app.extensions.interactive_3d.module import InteractiveStemExtension
from app.extensions.presentation.module import PresentationSupportExtension
from app.extensions.physics_2d.module import Physics2DSimulationExtension


class ExtensionHubPage(QWidget):
    """Trang điều khiển trung tâm cho toàn bộ 3 phân hệ Extension Layer."""

    def __init__(self, manager: ExtensionManager, parent=None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.ext_3d: InteractiveStemExtension = self.manager.get_module("interactive_3d_stem")
        self.ext_pres: PresentationSupportExtension = self.manager.get_module("presentation_support")
        self.ext_phys: Physics2DSimulationExtension = self.manager.get_module("physics_2d_simulation")

        self._init_ui()

        # Timer cập nhật trạng thái thời gian thực
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._refresh_status)
        self.update_timer.start(250)

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 1. Header Banner
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0f172a, stop:1 #1e293b);
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 12px;
            }
        """)
        h_layout = QVBoxLayout(header)
        title = QLabel("🚀 Extension Layer Hub")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #38bdf8;")
        desc = QLabel("Quản lý và kích hoạt 3 phân hệ mở rộng: Interactive 3D STEM, Presentation Support & 2D Physics.")
        desc.setStyleSheet("font-size: 12px; color: #94a3b8;")
        h_layout.addWidget(title)
        h_layout.addWidget(desc)
        main_layout.addWidget(header)

        # 2. Scroll area chứa 3 Cards phân hệ
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        container = QWidget()
        cards_layout = QVBoxLayout(container)
        cards_layout.setSpacing(16)

        # --- CARD 1: Interactive 3D STEM ---
        card_3d = self._create_card(
            title="1. Interactive 3D STEM (PyOpenGL + Shapely)",
            icon="🧊",
            color="#0284c7",
            desc="Dựng hình 3D Primitives, tính toán diện tích/góc/khoảng cách thời gian thực với Shapely và chạm đổi màu mặt."
        )
        self._setup_card_3d(card_3d)
        cards_layout.addWidget(card_3d)

        # --- CARD 2: Presentation Support ---
        card_pres = self._create_card(
            title="2. Presentation Support (PyAutoGUI + Pynput)",
            icon="📽️",
            color="#16a34a",
            desc="Điều khiển Slide từ xa, vẽ Virtual Laser Pointer nổi hệ điều hành, Whiteboard Ink và Quản lý cửa sổ."
        )
        self._setup_card_pres(card_pres)
        cards_layout.addWidget(card_pres)

        # --- CARD 3: 2D Physics Simulation ---
        card_phys = self._create_card(
            title="3. 2D Physics Simulation (Pymunk + Pygame)",
            icon="⚛️",
            color="#d97706",
            desc="Không gian vật lý Pymunk: Thả khối rigid-body, ngón tay Kinematic tương tác lực, vẽ vectơ động lực học & con lắc."
        )
        self._setup_card_phys(card_phys)
        cards_layout.addWidget(card_phys)

        cards_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_card(self, title: str, icon: str, color: str, desc: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: #111827;
                border: 1px solid #1f2937;
                border-left: 4px solid {color};
                border-radius: 8px;
                padding: 14px;
            }}
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(10)

        header_row = QHBoxLayout()
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet("font-size: 20px;")
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #f8fafc;")

        header_row.addWidget(lbl_icon)
        header_row.addWidget(lbl_title)
        header_row.addStretch()

        lbl_desc = QLabel(desc)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-size: 11px; color: #9ca3af; margin-bottom: 4px;")

        c_layout.addLayout(header_row)
        c_layout.addWidget(lbl_desc)
        return card

    def _setup_card_3d(self, card: QFrame) -> None:
        layout = card.layout()
        row = QHBoxLayout()

        self.btn_toggle_3d = QPushButton("Bật 3D STEM")
        self._style_button(self.btn_toggle_3d, "#0284c7")
        self.btn_toggle_3d.clicked.connect(self._toggle_3d)

        self.lbl_status_3d = QLabel("Trạng thái: Chưa bật")
        self.lbl_status_3d.setStyleSheet("color: #64748b; font-size: 11px;")

        # Presets selector
        self.combo_3d_preset = QComboBox()
        self.combo_3d_preset.addItems(["Cube (Lập phương)", "Sphere (Hình cầu)", "Cone (Hình nón)"])
        self.combo_3d_preset.currentIndexChanged.connect(self._change_3d_preset)

        # Tools selector
        self.combo_3d_tool = QComboBox()
        self.combo_3d_tool.addItems(["Interact (Chạm đổi màu)", "Measure (Đo khoảng cách)", "CrossSection (Shapely mặt cắt)"])
        self.combo_3d_tool.currentIndexChanged.connect(self._change_3d_tool)

        row.addWidget(self.btn_toggle_3d)
        row.addWidget(QLabel("Hình học:"))
        row.addWidget(self.combo_3d_preset)
        row.addWidget(QLabel("Công cụ:"))
        row.addWidget(self.combo_3d_tool)
        row.addStretch()
        row.addWidget(self.lbl_status_3d)
        layout.addLayout(row)

    def _setup_card_pres(self, card: QFrame) -> None:
        layout = card.layout()

        # Hàng 1: Nút bật & Trạng thái
        row1 = QHBoxLayout()
        self.btn_toggle_pres = QPushButton("Bật Presentation Support")
        self._style_button(self.btn_toggle_pres, "#16a34a")
        self.btn_toggle_pres.clicked.connect(self._toggle_pres)

        self.lbl_status_pres = QLabel("Trạng thái: Chưa bật")
        self.lbl_status_pres.setStyleSheet("color: #64748b; font-size: 11px;")

        row1.addWidget(self.btn_toggle_pres)
        row1.addStretch()
        row1.addWidget(self.lbl_status_pres)
        layout.addLayout(row1)

        # Hàng 2: Các tuỳ chọn con
        row2 = QHBoxLayout()
        self.chk_slides = QCheckBox("Task 2.1: Điều khiển Slide (Swipe)")
        self.chk_slides.setChecked(True)
        self.chk_slides.toggled.connect(lambda v: setattr(self.ext_pres, "enable_slides", v))

        self.chk_laser = QCheckBox("Task 2.2: Laser Pointer (Đỏ)")
        self.chk_laser.setChecked(True)
        self.chk_laser.toggled.connect(lambda v: setattr(self.ext_pres, "enable_laser", v))

        self.chk_whiteboard = QCheckBox("Task 2.3: Whiteboard Ink")
        self.chk_whiteboard.setChecked(False)
        self.chk_whiteboard.toggled.connect(lambda v: setattr(self.ext_pres, "enable_whiteboard", v))

        self.chk_win_mgr = QCheckBox("Task 2.4: Window Switcher (Alt+Tab)")
        self.chk_win_mgr.setChecked(True)
        self.chk_win_mgr.toggled.connect(lambda v: setattr(self.ext_pres, "enable_window_mgr", v))

        for chk in (self.chk_slides, self.chk_laser, self.chk_whiteboard, self.chk_win_mgr):
            chk.setStyleSheet("color: #cbd5e1; font-size: 11px;")
            row2.addWidget(chk)
        row2.addStretch()
        layout.addLayout(row2)

    def _setup_card_phys(self, card: QFrame) -> None:
        layout = card.layout()

        # Hàng 1: Bật / Tắt & Thí nghiệm
        row1 = QHBoxLayout()
        self.btn_toggle_phys = QPushButton("Bật 2D Physics")
        self._style_button(self.btn_toggle_phys, "#d97706")
        self.btn_toggle_phys.clicked.connect(self._toggle_phys)

        self.combo_phys_exp = QComboBox()
        self.combo_phys_exp.addItems(["Freeplay (Thả khối tự do)", "Collision (Va chạm đàn hồi)", "Pendulum (Con lắc đơn)"])
        self.combo_phys_exp.currentIndexChanged.connect(self._change_phys_exp)

        self.btn_reset_phys = QPushButton("🔄 Reset thế giới")
        self._style_button(self.btn_reset_phys, "#475569")
        self.btn_reset_phys.clicked.connect(self._reset_phys)

        self.lbl_status_phys = QLabel("Trạng thái: Chưa bật")
        self.lbl_status_phys.setStyleSheet("color: #64748b; font-size: 11px;")

        row1.addWidget(self.btn_toggle_phys)
        row1.addWidget(QLabel("Thí nghiệm:"))
        row1.addWidget(self.combo_phys_exp)
        row1.addWidget(self.btn_reset_phys)
        row1.addStretch()
        row1.addWidget(self.lbl_status_phys)
        layout.addLayout(row1)

        # Hàng 2: Trọng lực Slider
        row2 = QHBoxLayout()
        lbl_g = QLabel("Gia tốc trọng lực g:")
        lbl_g.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        self.slider_gravity = QSlider(Qt.Horizontal)
        self.slider_gravity.setRange(0, 1800)
        self.slider_gravity.setValue(800)
        self.lbl_g_val = QLabel("800 px/s²")
        self.lbl_g_val.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 11px;")
        self.slider_gravity.valueChanged.connect(self._update_gravity)

        row2.addWidget(lbl_g)
        row2.addWidget(self.slider_gravity)
        row2.addWidget(self.lbl_g_val)
        row2.addStretch()
        layout.addLayout(row2)

    def _style_button(self, btn: QPushButton, bg_color: str) -> None:
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {bg_color};
                color: #ffffff;
                font-weight: 600;
                font-size: 11px;
                padding: 6px 14px;
                border-radius: 6px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
            QPushButton:hover {{
                filter: brightness(1.15);
            }}
        """)

    def _toggle_3d(self) -> None:
        if self.ext_3d:
            new_state = not self.ext_3d.enabled
            self.manager.set_module_enabled(self.ext_3d.id, new_state)
            self.btn_toggle_3d.setText("Tắt 3D STEM" if new_state else "Bật 3D STEM")

    def _toggle_pres(self) -> None:
        if self.ext_pres:
            new_state = not self.ext_pres.enabled
            self.manager.set_module_enabled(self.ext_pres.id, new_state)
            self.btn_toggle_pres.setText("Tắt Presentation" if new_state else "Bật Presentation Support")

    def _toggle_phys(self) -> None:
        if self.ext_phys:
            new_state = not self.ext_phys.enabled
            self.manager.set_module_enabled(self.ext_phys.id, new_state)
            self.btn_toggle_phys.setText("Tắt 2D Physics" if new_state else "Bật 2D Physics")

    def _change_3d_preset(self, idx: int) -> None:
        presets = ["Cube", "Sphere", "Cone"]
        if self.ext_3d and self.ext_3d.lab:
            self.ext_3d.lab.set_preset(presets[idx])

    def _change_3d_tool(self, idx: int) -> None:
        tools = ["Interact", "Measure", "CrossSection"]
        if self.ext_3d and self.ext_3d.lab:
            self.ext_3d.lab.tool = tools[idx]

    def _change_phys_exp(self, idx: int) -> None:
        exps = ["Freeplay", "Collision", "Pendulum"]
        if self.ext_phys:
            self.ext_phys.load_experiment(exps[idx])

    def _reset_phys(self) -> None:
        if self.ext_phys and self.ext_phys.world:
            self.ext_phys.world.clear_bodies()

    def _update_gravity(self, val: int) -> None:
        self.lbl_g_val.setText(f"{val} px/s²")
        if self.ext_phys and self.ext_phys.world:
            self.ext_phys.world.set_gravity(float(val))

    def _refresh_status(self) -> None:
        if self.ext_3d:
            msg = self.ext_3d.status.message if self.ext_3d.enabled else "Đã tắt"
            self.lbl_status_3d.setText(f"Trạng thái: {msg}")
            self.lbl_status_3d.setStyleSheet("color: #38bdf8;" if self.ext_3d.enabled else "color: #64748b;")

        if self.ext_pres:
            last = f" (Vừa chạy: {self.ext_pres.status.last_action})" if self.ext_pres.status.last_action else ""
            msg = f"{self.ext_pres.status.message}{last}" if self.ext_pres.enabled else "Đã tắt"
            self.lbl_status_pres.setText(f"Trạng thái: {msg}")
            self.lbl_status_pres.setStyleSheet("color: #4ade80;" if self.ext_pres.enabled else "color: #64748b;")

        if self.ext_phys:
            msg = self.ext_phys.status.message if self.ext_phys.enabled else "Đã tắt"
            self.lbl_status_phys.setText(f"Trạng thái: {msg}")
            self.lbl_status_phys.setStyleSheet("color: #fbbf24;" if self.ext_phys.enabled else "color: #64748b;")

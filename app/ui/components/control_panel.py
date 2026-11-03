"""Interactive control panel for scene selection, filtering profiles, and sensitivity settings."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class ControlPanel(QFrame):
    """Control panel providing scene switches, filter configuration, and reset actions."""

    scene_changed = Signal(str)
    filter_changed = Signal(str)
    sensitivity_changed = Signal(float)
    reset_requested = Signal()
    camera_toggled = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1F2937;
                border-radius: 12px;
                padding: 12px;
            }
        """)
        self._camera_running = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(14)

        # Panel Title
        lbl_title = QLabel("BẢNG ĐIỀU KHIỂN & CẤU HÌNH")
        lbl_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #9CA3AF; letter-spacing: 0.5px;")
        layout.addWidget(lbl_title)

        # ---------------------------------------------------------
        # 1. 3D STEM Scene Selection
        # ---------------------------------------------------------
        scene_group = QVBoxLayout()
        scene_group.setSpacing(4)
        lbl_scene = QLabel("Mô hình STEM 3D:")
        lbl_scene.setStyleSheet("font-size: 11px; font-weight: 600; color: #E5E7EB;")

        self.combo_scene = QComboBox()
        self.combo_scene.addItem("📐 Không gian toạ độ 3D (Coordinate Geometry)", "coordinate")
        self.combo_scene.addItem("🧪 Mô hình phân tử H₂O (Molecular Structure)", "molecule")
        self.combo_scene.addItem("🪐 Quỹ đạo hành tinh (Orbital Mechanics)", "orbital")
        self.combo_scene.currentIndexChanged.connect(self._on_scene_changed)

        scene_group.addWidget(lbl_scene)
        scene_group.addWidget(self.combo_scene)
        layout.addLayout(scene_group)

        # ---------------------------------------------------------
        # 2. Filter Policy Selection (Raw / Fixed 1-Euro / Adaptive)
        # ---------------------------------------------------------
        filter_group = QVBoxLayout()
        filter_group.setSpacing(4)
        lbl_filter = QLabel("Thuật toán lọc tín hiệu:")
        lbl_filter.setStyleSheet("font-size: 11px; font-weight: 600; color: #E5E7EB;")

        self.combo_filter = QComboBox()
        self.combo_filter.addItem("✨ Bounded Adaptive 1-Euro (Khuyên dùng)", "adaptive")
        self.combo_filter.addItem("⚙️ Canonical Fixed 1-Euro (Baseline)", "fixed")
        self.combo_filter.addItem("⚡ Raw Landmarks (Không lọc)", "raw")
        self.combo_filter.currentIndexChanged.connect(self._on_filter_changed)

        filter_group.addWidget(lbl_filter)
        filter_group.addWidget(self.combo_filter)
        layout.addLayout(filter_group)

        # ---------------------------------------------------------
        # 3. Sensitivity Slider
        # ---------------------------------------------------------
        sens_group = QVBoxLayout()
        sens_group.setSpacing(4)
        sens_header = QHBoxLayout()

        lbl_sens = QLabel("Độ nhạy cử chỉ (Sensitivity):")
        lbl_sens.setStyleSheet("font-size: 11px; font-weight: 600; color: #E5E7EB;")

        self.lbl_sens_val = QLabel("1.0x")
        self.lbl_sens_val.setStyleSheet("font-size: 11px; font-weight: 700; color: #06B6D4;")

        sens_header.addWidget(lbl_sens)
        sens_header.addStretch()
        sens_header.addWidget(self.lbl_sens_val)

        self.slider_sens = QSlider(Qt.Orientation.Horizontal)
        self.slider_sens.setRange(5, 25)  # 0.5x to 2.5x
        self.slider_sens.setValue(10)
        self.slider_sens.valueChanged.connect(self._on_sensitivity_changed)

        sens_group.addLayout(sens_header)
        sens_group.addWidget(self.slider_sens)
        layout.addLayout(sens_group)

        # ---------------------------------------------------------
        # 4. Action Buttons (Camera & Reset)
        # ---------------------------------------------------------
        actions_row = QHBoxLayout()
        actions_row.setSpacing(10)

        self.btn_camera = QPushButton("Bật Camera")
        self.btn_camera.setProperty("class", "btn_primary")
        self.btn_camera.clicked.connect(self._toggle_camera)

        self.btn_reset = QPushButton("Reset Góc Nhìn (R)")
        self.btn_reset.clicked.connect(self.reset_requested.emit)

        actions_row.addWidget(self.btn_camera)
        actions_row.addWidget(self.btn_reset)
        layout.addLayout(actions_row)

    def _on_scene_changed(self, index: int) -> None:
        scene_key = self.combo_scene.currentData()
        self.scene_changed.emit(scene_key)

    def _on_filter_changed(self, index: int) -> None:
        filter_key = self.combo_filter.currentData()
        self.filter_changed.emit(filter_key)

    def _on_sensitivity_changed(self, value: int) -> None:
        factor = value / 10.0
        self.lbl_sens_val.setText(f"{factor:.1f}x")
        self.sensitivity_changed.emit(factor)

    def _toggle_camera(self) -> None:
        self._camera_running = not self._camera_running
        if self._camera_running:
            self.btn_camera.setText("Dừng Camera")
            self.btn_camera.setStyleSheet("background-color: #EF4444; color: white;")
        else:
            self.btn_camera.setText("Bật Camera")
            self.btn_camera.setStyleSheet("")
        self.camera_toggled.emit(self._camera_running)

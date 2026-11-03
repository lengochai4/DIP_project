"""ExploreView: Main interactive 3D STEM manipulation workspace."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..components.camera_widget import CameraWidget
from ..components.control_panel import ControlPanel
from ..components.gesture_indicator import GestureIndicator
from ..components.viewport_3d import Viewport3D


class ExploreView(QWidget):
    """Primary user workspace: Large 3D Viewport alongside live camera and gesture tracking."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # ---------------------------------------------------------
        # Left: Dominant 3D STEM Viewport
        # ---------------------------------------------------------
        left_container = QVBoxLayout()
        left_container.setSpacing(10)

        self.viewport_3d = Viewport3D()
        left_container.addWidget(self.viewport_3d, stretch=1)

        # Bottom Quick Guide Bar
        guide_bar = QFrame()
        guide_bar.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1F2937;
                border-radius: 10px;
                padding: 8px 14px;
            }
        """)
        g_layout = QHBoxLayout(guide_bar)
        g_layout.setContentsMargins(10, 4, 10, 4)
        g_layout.setSpacing(18)

        tips = [
            ("👆 Di chuyển ngón trỏ:", "Xoay mô hình 3D (Yaw / Pitch)"),
            ("🤏 Chụm ngón cái & trỏ:", "Thu phóng kích thước (Pinch Scale)"),
            ("⌨️ Phím R:", "Đặt lại góc nhìn mặc định"),
        ]

        for title, desc in tips:
            row = QHBoxLayout()
            row.setSpacing(6)
            lbl_t = QLabel(title)
            lbl_t.setStyleSheet("font-size: 11px; font-weight: 700; color: #06B6D4;")
            lbl_d = QLabel(desc)
            lbl_d.setStyleSheet("font-size: 11px; color: #9CA3AF;")
            row.addWidget(lbl_t)
            row.addWidget(lbl_d)
            g_layout.addLayout(row)

        g_layout.addStretch()
        left_container.addWidget(guide_bar)

        main_layout.addLayout(left_container, stretch=7)

        # ---------------------------------------------------------
        # Right: Camera Feed, Gesture Gauges & Control Deck
        # ---------------------------------------------------------
        right_container = QWidget()
        right_container.setMaximumWidth(420)
        right_container.setMinimumWidth(340)

        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(14)

        # 1. Camera Feed (PIP)
        self.camera_widget = CameraWidget()
        self.camera_widget.setFixedHeight(230)
        right_layout.addWidget(self.camera_widget)

        # 2. Gesture Gauge
        self.gesture_indicator = GestureIndicator()
        right_layout.addWidget(self.gesture_indicator)

        # 3. Control Panel
        self.control_panel = ControlPanel()
        right_layout.addWidget(self.control_panel)

        right_layout.addStretch()
        main_layout.addWidget(right_container, stretch=3)

        # Connect ControlPanel Signals to Viewport
        self.control_panel.scene_changed.connect(self.viewport_3d.set_scene)
        self.control_panel.reset_requested.connect(self.viewport_3d.reset_transform)

"""Modern top header bar displaying project title, team members, and live status."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class HeaderBar(QFrame):
    """Sleek header bar with project identity, team information, and live tracking status."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("header_container")
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(20)

        # ---------------------------------------------------------
        # Left: Project Brand & Full Title
        # ---------------------------------------------------------
        left_layout = QVBoxLayout()
        left_layout.setSpacing(4)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)

        badge = QLabel("DIP TOUCHLESS STEM")
        badge.setObjectName("project_badge")
        badge.setFixedHeight(22)

        course_label = QLabel("Digital Image Processing • Final Term Project")
        course_label.setObjectName("project_subtitle")

        brand_row.addWidget(badge)
        brand_row.addWidget(course_label)
        brand_row.addStretch()

        title_label = QLabel(
            "Real-Time Touchless 3D STEM Interaction Using Adaptive Image Preprocessing & Motion Signal Filtering"
        )
        title_label.setObjectName("project_title")
        title_label.setWordWrap(True)

        left_layout.addLayout(brand_row)
        left_layout.addWidget(title_label)
        layout.addLayout(left_layout, stretch=4)

        # ---------------------------------------------------------
        # Center: Team Members
        # ---------------------------------------------------------
        team_container = QWidget()
        team_layout = QVBoxLayout(team_container)
        team_layout.setContentsMargins(0, 0, 0, 0)
        team_layout.setSpacing(4)

        team_title = QLabel("NHÓM TÁC GIẢ")
        team_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #9CA3AF; letter-spacing: 0.5px;")

        chips_row = QHBoxLayout()
        chips_row.setSpacing(8)

        members = [
            ("Lê Ngọc Hải", "Architecture & DIP Core"),
            ("Nguyễn Đắc Lộc", "Interaction & Telemetry"),
            ("Trần Tuấn Kiệt", "Evaluation & 3D Extension"),
        ]

        for name, role in members:
            chip = QFrame()
            chip.setProperty("class", "member_card")
            chip.setStyleSheet("""
                QFrame {
                    background-color: #1F2937;
                    border: 1px solid #374151;
                    border-radius: 8px;
                    padding: 3px 8px;
                }
                QFrame:hover {
                    border: 1px solid #06B6D4;
                    background-color: #273549;
                }
            """)
            chip_layout = QVBoxLayout(chip)
            chip_layout.setContentsMargins(4, 2, 4, 2)
            chip_layout.setSpacing(1)

            lbl_name = QLabel(f"👤 {name}")
            lbl_name.setStyleSheet("font-size: 11px; font-weight: 600; color: #F9FAFB;")
            lbl_role = QLabel(role)
            lbl_role.setStyleSheet("font-size: 9px; color: #06B6D4;")

            chip_layout.addWidget(lbl_name)
            chip_layout.addWidget(lbl_role)
            chips_row.addWidget(chip)

        team_layout.addWidget(team_title)
        team_layout.addLayout(chips_row)
        layout.addWidget(team_container, stretch=3)

        # ---------------------------------------------------------
        # Right: Live Indicators (Tracking Status, FPS, Latency)
        # ---------------------------------------------------------
        status_box = QFrame()
        status_box.setStyleSheet("""
            QFrame {
                background-color: #1F2937;
                border: 1px solid #374151;
                border-radius: 10px;
                padding: 6px 12px;
            }
        """)
        status_layout = QHBoxLayout(status_box)
        status_layout.setContentsMargins(8, 4, 8, 4)
        status_layout.setSpacing(14)

        # Tracking state badge
        self._tracking_badge = QLabel("● NO HAND")
        self._tracking_badge.setStyleSheet("""
            color: #EF4444;
            font-weight: 700;
            font-size: 11px;
            background: rgba(239, 68, 68, 0.15);
            padding: 4px 8px;
            border-radius: 6px;
        """)

        # FPS counter
        self._fps_label = QLabel("60 FPS")
        self._fps_label.setStyleSheet("font-weight: 700; font-size: 12px; color: #10B981;")

        # Latency
        self._latency_label = QLabel("14 ms")
        self._latency_label.setStyleSheet("font-size: 11px; color: #9CA3AF;")

        status_layout.addWidget(self._tracking_badge)
        status_layout.addWidget(self._fps_label)
        status_layout.addWidget(self._latency_label)

        layout.addWidget(status_box, stretch=1)

    def set_tracking_status(self, status: str) -> None:
        """Update tracking indicator badge with colors."""
        status_upper = status.upper()
        if "VALID" in status_upper:
            self._tracking_badge.setText("● VALID")
            self._tracking_badge.setStyleSheet("""
                color: #10B981;
                font-weight: 700;
                font-size: 11px;
                background: rgba(16, 185, 129, 0.15);
                padding: 4px 8px;
                border-radius: 6px;
            """)
        elif "REACQUIR" in status_upper:
            self._tracking_badge.setText("● REACQUIRING")
            self._tracking_badge.setStyleSheet("""
                color: #F59E0B;
                font-weight: 700;
                font-size: 11px;
                background: rgba(245, 158, 11, 0.15);
                padding: 4px 8px;
                border-radius: 6px;
            """)
        else:
            self._tracking_badge.setText("● NO HAND")
            self._tracking_badge.setStyleSheet("""
                color: #EF4444;
                font-weight: 700;
                font-size: 11px;
                background: rgba(239, 68, 68, 0.15);
                padding: 4px 8px;
                border-radius: 6px;
            """)

    def set_fps(self, fps: float) -> None:
        """Update FPS display smoothly."""
        self._fps_label.setText(f"{fps:.0f} FPS")

    def set_latency(self, latency_ms: float) -> None:
        """Update latency display."""
        self._latency_label.setText(f"{latency_ms:.1f} ms")

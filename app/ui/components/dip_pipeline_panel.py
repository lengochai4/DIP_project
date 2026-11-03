"""Visual panel displaying each stage of the Digital Image Processing pipeline in real time."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class DIPPipelinePanel(QFrame):
    """Real-time diagnostic panel illustrating the 8 canonical DIP pipeline stages."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1F2937;
                border-radius: 12px;
                padding: 10px;
            }
        """)
        self._stage_labels: dict[str, QLabel] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        title = QLabel("DIP CORE PROCESSING PIPELINE")
        title.setStyleSheet("font-size: 11px; font-weight: 700; color: #9CA3AF; letter-spacing: 0.5px;")

        self.lbl_pipeline_status = QLabel("ONLINE")
        self.lbl_pipeline_status.setStyleSheet("color: #10B981; font-weight: 700; font-size: 10px;")

        header_row.addWidget(title)
        header_row.addStretch()
        header_row.addWidget(self.lbl_pipeline_status)
        layout.addLayout(header_row)

        # 8 Stages Grid
        grid = QGridLayout()
        grid.setSpacing(8)

        stages = [
            ("1. Frame Capture", "OpenCV / 60 FPS", "capture"),
            ("2. ROI Manager", "Hand BBox Tracking", "roi"),
            ("3. Illumination", "HSV V-channel Analysis", "illumination"),
            ("4. Preprocessing", "Adaptive CLAHE / Bypass", "preproc"),
            ("5. MediaPipe", "21 Hand Landmarks", "mediapipe"),
            ("6. Validator", "Explicit Quality Check", "validator"),
            ("7. 1-Euro Filter", "Adaptive Motion Damping", "filter"),
            ("8. Gesture Engine", "Pinch & Rotation Mapping", "gesture"),
        ]

        for i, (name, desc, key) in enumerate(stages):
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background-color: #1F2937;
                    border: 1px solid #374151;
                    border-radius: 8px;
                    padding: 6px;
                }
            """)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(6, 4, 6, 4)
            c_layout.setSpacing(2)

            name_lbl = QLabel(name)
            name_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #F9FAFB;")

            status_lbl = QLabel(desc)
            status_lbl.setStyleSheet("font-size: 9px; color: #06B6D4;")
            self._stage_labels[key] = status_lbl

            c_layout.addWidget(name_lbl)
            c_layout.addWidget(status_lbl)

            row = i // 2
            col = i % 2
            grid.addWidget(card, row, col)

        layout.addLayout(grid)

    def set_stage_status(self, key: str, text: str, color_hex: str = "#06B6D4") -> None:
        """Update diagnostic text for a specific pipeline stage."""
        if key in self._stage_labels:
            lbl = self._stage_labels[key]
            lbl.setText(text)
            lbl.setStyleSheet(f"font-size: 9px; color: {color_hex}; font-weight: 600;")

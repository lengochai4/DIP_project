"""Visual indicator widget showing real-time pinch ratio, gesture state, and motion dynamics."""

from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QFrame, QLabel, QProgressBar, QVBoxLayout, QHBoxLayout, QWidget


class GestureIndicator(QFrame):
    """Real-time gesture feedback widget showing pinch state, yaw/pitch deltas, and mode."""

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

        self.pinch_ratio: float = 0.0
        self.is_pinching: bool = False
        self.gesture_state: str = "IDLE"
        self.yaw_delta: float = 0.0
        self.pitch_delta: float = 0.0

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Title Row
        title_row = QHBoxLayout()
        lbl_title = QLabel("CHỈ SỐ THAO TÁC CỬ CHỈ")
        lbl_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #9CA3AF; letter-spacing: 0.5px;")

        self.lbl_gesture_badge = QLabel("IDLE")
        self.lbl_gesture_badge.setStyleSheet("""
            background-color: #1F2937;
            color: #9CA3AF;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 4px;
        """)

        title_row.addWidget(lbl_title)
        title_row.addStretch()
        title_row.addWidget(self.lbl_gesture_badge)
        layout.addLayout(title_row)

        # Custom Pinch Gauge Widget
        self.gauge_widget = PinchGauge()
        self.gauge_widget.setFixedHeight(36)
        layout.addWidget(self.gauge_widget)

        # Details Row: Yaw / Pitch deltas
        details_row = QHBoxLayout()
        details_row.setSpacing(8)

        self.lbl_yaw = QLabel("ΔYaw: 0.0°")
        self.lbl_yaw.setStyleSheet("font-size: 11px; color: #06B6D4; font-weight: 600;")

        self.lbl_pitch = QLabel("ΔPitch: 0.0°")
        self.lbl_pitch.setStyleSheet("font-size: 11px; color: #8B5CF6; font-weight: 600;")

        details_row.addWidget(self.lbl_yaw)
        details_row.addWidget(self.lbl_pitch)
        details_row.addStretch()
        layout.addLayout(details_row)

    def update_gestures(
        self,
        pinch_ratio: float,
        is_pinching: bool,
        yaw_delta: float,
        pitch_delta: float,
        is_valid_hand: bool,
    ) -> None:
        """Update indicators with latest frame values."""
        self.pinch_ratio = max(0.0, min(1.0, pinch_ratio))
        self.is_pinching = is_pinching
        self.yaw_delta = yaw_delta
        self.pitch_delta = pitch_delta

        if not is_valid_hand:
            self.gesture_state = "NO HAND"
            self.lbl_gesture_badge.setText("NO HAND")
            self.lbl_gesture_badge.setStyleSheet("background: rgba(239, 68, 68, 0.2); color: #EF4444; font-weight: 700; padding: 2px 8px; border-radius: 4px;")
        elif is_pinching:
            self.gesture_state = "PINCH (ZOOM)"
            self.lbl_gesture_badge.setText("PINCH / ZOOM")
            self.lbl_gesture_badge.setStyleSheet("background: rgba(139, 92, 246, 0.25); color: #A78BFA; font-weight: 700; padding: 2px 8px; border-radius: 4px;")
        elif abs(yaw_delta) > 0.05 or abs(pitch_delta) > 0.05:
            self.gesture_state = "ROTATING"
            self.lbl_gesture_badge.setText("ROTATING")
            self.lbl_gesture_badge.setStyleSheet("background: rgba(6, 182, 212, 0.25); color: #22D3EE; font-weight: 700; padding: 2px 8px; border-radius: 4px;")
        else:
            self.gesture_state = "POINTING"
            self.lbl_gesture_badge.setText("POINTING")
            self.lbl_gesture_badge.setStyleSheet("background: rgba(16, 185, 129, 0.2); color: #10B981; font-weight: 700; padding: 2px 8px; border-radius: 4px;")

        self.gauge_widget.set_value(self.pinch_ratio, is_pinching)
        self.lbl_yaw.setText(f"ΔYaw: {yaw_delta:+.1f}°")
        self.lbl_pitch.setText(f"ΔPitch: {pitch_delta:+.1f}°")


class PinchGauge(QWidget):
    """Smooth visual bar for pinch distance and trigger threshold."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value: float = 0.0
        self._is_pinching: bool = False

    def set_value(self, val: float, is_pinching: bool) -> None:
        self._value = val
        self._is_pinching = is_pinching
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Background track
        painter.setBrush(QColor("#1F2937"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 4, w, h - 8, 6, 6)

        # Fill bar
        fill_w = max(4.0, w * self._value)
        grad = QLinearGradient(0, 0, fill_w, 0)
        if self._is_pinching:
            grad.setColorAt(0.0, QColor("#8B5CF6"))
            grad.setColorAt(1.0, QColor("#EC4899"))
        else:
            grad.setColorAt(0.0, QColor("#06B6D4"))
            grad.setColorAt(1.0, QColor("#3B82F6"))

        painter.setBrush(QBrush(grad))
        painter.drawRoundedRect(0, 4, int(fill_w), h - 8, 6, 6)

        # Threshold marker at 0.5
        thresh_x = int(w * 0.5)
        painter.setPen(QPen(QColor("#F59E0B"), 2, Qt.PenStyle.DotLine))
        painter.drawLine(thresh_x, 2, thresh_x, h - 2)

        # Text label
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.drawText(10, h - 11, f"Pinch Ratio: {self._value * 100:.0f}%")

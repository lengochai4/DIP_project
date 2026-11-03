"""Live camera viewport with ROI overlays, landmark tracking, and DIP diagnostic badges."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class CameraWidget(QFrame):
    """High-performance camera preview with DIP landmark and ROI overlays."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #0B0F19;
                border: 1px solid #374151;
                border-radius: 12px;
            }
        """)
        self.setMinimumSize(320, 240)

        self._pixmap: QPixmap | None = None
        self._roi: tuple[int, int, int, int] | None = None  # x, y, w, h
        self._landmarks: list[tuple[float, float]] = []     # normalized (x, y)
        self._illumination_state: str = "NORMAL"
        self._clahe_active: bool = False
        self._status_text: str = "Camera Standby"

    def update_frame(
        self,
        bgr_frame: np.ndarray | None,
        roi: tuple[int, int, int, int] | None = None,
        landmarks: list[tuple[float, float]] | None = None,
        illumination_state: str = "NORMAL",
        clahe_active: bool = False,
    ) -> None:
        """Update frame buffer and tracking overlays."""
        self._roi = roi
        self._landmarks = landmarks or []
        self._illumination_state = illumination_state
        self._clahe_active = clahe_active

        if bgr_frame is not None:
            h, w, ch = bgr_frame.shape
            bytes_per_line = ch * w
            # Convert BGR to RGB
            rgb_frame = np.ascontiguousarray(bgr_frame[:, :, ::-1])
            q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self._pixmap = QPixmap.fromImage(q_img)
            self._status_text = "Live RGB Camera"
        else:
            self._pixmap = None
            self._status_text = "Camera Inactive"

        self.update()

    def paintEvent(self, event) -> None:
        """Custom paint event for crisp, high-framerate rendering."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        if self._pixmap is not None and not self._pixmap.isNull():
            # Scale pixmap maintaining aspect ratio
            scaled_pm = self._pixmap.scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            dx = (w - scaled_pm.width()) // 2
            dy = (h - scaled_pm.height()) // 2
            painter.drawPixmap(dx, dy, scaled_pm)

            # Draw Landmarks if present
            if self._landmarks:
                pen_point = QPen(QColor("#06B6D4"), 6)
                painter.setPen(pen_point)
                painter.setBrush(QColor("#22D3EE"))

                for idx, (lx, ly) in enumerate(self._landmarks):
                    px = dx + lx * scaled_pm.width()
                    py = dy + ly * scaled_pm.height()
                    # Highlight index fingertip (landmark 8) and thumb (landmark 4)
                    if idx in (4, 8):
                        pen_accent = QPen(QColor("#8B5CF6"), 8)
                        painter.setPen(pen_accent)
                        painter.setBrush(QColor("#A78BFA"))
                        painter.drawEllipse(QRectF(px - 5, py - 5, 10, 10))
                        painter.setPen(pen_point)
                        painter.setBrush(QColor("#22D3EE"))
                    else:
                        painter.drawEllipse(QRectF(px - 3, py - 3, 6, 6))

            # Draw ROI bounding box if available
            if self._roi is not None:
                rx, ry, rw, rh = self._roi
                # Map from original image coordinates to widget space
                scale_x = scaled_pm.width() / self._pixmap.width()
                scale_y = scaled_pm.height() / self._pixmap.height()
                box_x = dx + rx * scale_x
                box_y = dy + ry * scale_y
                box_w = rw * scale_x
                box_h = rh * scale_y

                roi_pen = QPen(QColor("#10B981"), 2, Qt.PenStyle.DashLine)
                painter.setPen(roi_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(QRectF(box_x, box_y, box_w, box_h))

                # ROI Tag
                painter.setPen(QColor("#10B981"))
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                painter.drawText(int(box_x + 4), int(box_y - 6), "DIP Tracking ROI")
        else:
            # Standby state with stylish placeholder
            painter.fillRect(0, 0, w, h, QColor("#111827"))
            painter.setPen(QColor("#6B7280"))
            painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, f"📷 {self._status_text}")

        # Draw Top-Left Diagnostics Overlay
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(17, 24, 39, 200))
        painter.drawRoundedRect(12, 12, 150, 28, 6, 6)

        painter.setPen(QColor("#10B981" if self._illumination_state == "NORMAL" else "#F59E0B"))
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        clahe_txt = "+ CLAHE" if self._clahe_active else ""
        painter.drawText(20, 30, f"LIGHT: {self._illumination_state} {clahe_txt}")

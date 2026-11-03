"""Mini Orientation Gizmo: 180x88 bottom-right coordinate reference widget.

Displays synchronous Oxyz axes and a mini wireframe cube rotating with
scene yaw/pitch, without cluttering the main camera viewport.
Touching or clicking this widget resets the view to default perspective.
"""

import math
import numpy as np
from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import QWidget

from app.interaction.dwell_tracker import DwellTracker
from app.rendering.transforms import rotation

GIZMO_W = 180   # width equal to delete button (px)
GIZMO_H = 88    # height equal to 2x delete button (px)
DWELL_RESET_S = 0.8


class OrientationGizmo(QWidget):
    """Miniature spatial orientation widget positioned at bottom-right of viewport."""

    def __init__(self, parent_viewport, shell):
        super().__init__(parent_viewport)
        self.viewport = parent_viewport
        self.shell = shell
        self.setFixedSize(GIZMO_W, GIZMO_H)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Khung định hướng Oxyz (Chạm 0.8s hoặc Click để khôi phục góc nhìn chuẩn)")

        self._dwell = DwellTracker(DWELL_RESET_S)
        self._dwell_frac: float = 0.0
        self._hovering: bool = False
        self._tip_px: QPoint | None = None
        self.setVisible(True)

    def reposition(self) -> None:
        """Keep anchored at bottom-right corner of viewport with 16px margin."""
        if self.parentWidget() is not None:
            vw = self.parentWidget().width()
            vh = self.parentWidget().height()
            self.move(max(10, vw - GIZMO_W - 16), max(10, vh - GIZMO_H - 16))

    def update_tip(self, tip_xy, dt: float) -> None:
        """Process fingertip hover in viewport-normalized coordinates."""
        if tip_xy is None:
            self._dwell.reset()
            self._dwell_frac = 0.0
            self._hovering = False
            self.update()
            return

        vw = self.viewport.width()
        vh = self.viewport.height()
        tip_global_px = QPoint(round(tip_xy[0] * vw), round(tip_xy[1] * vh))
        local_pos = self.mapFromParent(tip_global_px)

        inside = self.rect().contains(local_pos)
        self._hovering = inside
        ev = self._dwell.update("GIZMO", dt, inside=inside)
        self._dwell_frac = self._dwell.fraction

        if ev is not None and ev.state == "ENTER":
            self.shell.reset_view()
            self._dwell.reset()
            self._dwell_frac = 0.0

        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if user clicked the Lock toggle badge on the top right
            if event.pos().x() > GIZMO_W - 55 and event.pos().y() < 28:
                self.shell._view_locked = not getattr(self.shell, "_view_locked", False)
                self.viewport.update()
                self.update()
                return
            # Main body click resets view
            self.shell.reset_view()
            self._dwell.reset()
            self._dwell_frac = 0.0
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            self.shell._view_locked = not getattr(self.shell, "_view_locked", False)
            self.viewport.update()
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)

        # Background: sleek translucent glassmorphism
        bg_color = QColor(23, 37, 48, 225) if not self._hovering else QColor(28, 48, 62, 235)
        painter.setBrush(bg_color)
        border_color = QColor("#38596f") if self._hovering else QColor("#223847")
        painter.setPen(QPen(border_color, 1.5))
        painter.drawRoundedRect(rect, 8, 8)

        # Title: OXYZ
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.setPen(QColor("#72bfcc"))
        painter.drawText(QRect(10, 6, 80, 18), Qt.AlignmentFlag.AlignLeft, "HỆ TRỤC OXYZ")

        # Lock / Reset badge on top-right
        is_locked = getattr(self.shell, "_view_locked", False)
        painter.setFont(QFont("Segoe UI", 8))
        if is_locked:
            painter.setPen(QColor("#ec4899"))
            painter.drawText(QRect(GIZMO_W - 65, 6, 55, 18), Qt.AlignmentFlag.AlignRight, "🔒 Đã khóa")
        else:
            painter.setPen(QColor("#8fa6b2"))
            painter.drawText(QRect(GIZMO_W - 65, 6, 55, 18), Qt.AlignmentFlag.AlignRight, "↺ Đặt lại")

        # 3D axes projection center
        cx = 90
        cy = 50

        # Read rotation from active lab
        lab = getattr(self.viewport.registry, "current", None)
        yaw = getattr(lab, "yaw", 0.35)
        pitch = getattr(lab, "pitch", 0.35)
        R = rotation(yaw, pitch)

        # 1. Mini wireframe cube (S = 13 px)
        S = 13.0
        corners = []
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    p = R @ np.array([sx * S, sy * S, sz * S])
                    corners.append((cx + p[0], cy - p[1]))

        # Cube edges
        cube_edges = (
            (0, 1), (0, 2), (0, 4), (1, 3), (1, 5), (2, 3),
            (2, 6), (3, 7), (4, 5), (4, 6), (5, 7), (6, 7)
        )
        painter.setPen(QPen(QColor(52, 78, 96, 120), 1.0))
        for i1, i2 in cube_edges:
            painter.drawLine(QPoint(round(corners[i1][0]), round(corners[i1][1])),
                             QPoint(round(corners[i2][0]), round(corners[i2][1])))

        # 2. XYZ Axes (Length = 26 px)
        L = 26.0
        axes = (
            (np.array([1.0, 0.0, 0.0]), QColor("#ef4444"), "X"),  # X: Red
            (np.array([0.0, 1.0, 0.0]), QColor("#10b981"), "Y"),  # Y: Green
            (np.array([0.0, 0.0, 1.0]), QColor("#3b82f6"), "Z"),  # Z: Blue
        )

        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        for unit_vec, col, axis_label in axes:
            p = R @ (unit_vec * L)
            ex = cx + p[0]
            ey = cy - p[1]
            painter.setPen(QPen(col, 2.2))
            painter.drawLine(cx, cy, round(ex), round(ey))

            # Small arrow tip
            norm = math.hypot(p[0], -p[1])
            if norm > 1e-3:
                dx = p[0] / norm * 6.0
                dy = -p[1] / norm * 6.0
                px_t = -dy * 0.5
                py_t = dx * 0.5
                painter.drawLine(round(ex), round(ey), round(ex - dx + px_t), round(ey - dy + py_t))
                painter.drawLine(round(ex), round(ey), round(ex - dx - px_t), round(ey - dy - py_t))

            # Text label
            painter.setPen(col)
            painter.drawText(round(ex + (4 if p[0] >= 0 else -10)),
                             round(ey + (4 if -p[1] >= 0 else -2)), axis_label)

        # Origin point dot
        painter.setBrush(QColor("#efca82"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx - 3, cy - 3, 6, 6)

        # Dwell progress bar when hovering
        if self._dwell_frac > 0.0:
            bar_w = round((GIZMO_W - 8) * self._dwell_frac)
            painter.setBrush(QColor("#72bfcc"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(4, GIZMO_H - 5, bar_w, 3, 1, 1)

"""Task 2.2: Virtual Laser Pointer.

Vẽ chấm laser màu đỏ nổi đè lên màn hình hệ điều hành định vị theo đầu ngón tay trỏ.
"""

from typing import Optional, Tuple
from PySide6.QtCore import Qt, QPoint, QRectF
from PySide6.QtGui import QPainter, QColor, QRadialGradient, QPen
from PySide6.QtWidgets import QWidget, QApplication


class VirtualLaserPointerOverlay(QWidget):
    """Cửa sổ trong suốt đè lên toàn màn hình để hiển thị tia laser ảo."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.geometry())

        self.laser_pos: Optional[Tuple[int, int]] = None
        self.laser_color = QColor(255, 30, 30, 230)
        self.radius = 16

    def set_laser_pos_normalized(self, norm_x: float, norm_y: float) -> None:
        """Nhận toạ độ ngón tay chuẩn hoá [0, 1] và ánh xạ ra toàn màn hình."""
        w, h = self.width(), self.height()
        # Lật toạ độ X nếu camera ở chế độ gương
        screen_x = int(norm_x * w)
        screen_y = int(norm_y * h)
        self.laser_pos = (screen_x, screen_y)
        self.update()

    def hide_laser(self) -> None:
        self.laser_pos = None
        self.update()

    def paintEvent(self, event) -> None:
        if not self.laser_pos:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cx, cy = self.laser_pos
        # Tạo hiệu ứng phát sáng tròn dạng Gradient (Radial Glow)
        gradient = QRadialGradient(QPoint(cx, cy), self.radius)
        gradient.setColorAt(0.0, QColor(255, 255, 255, 255))
        gradient.setColorAt(0.2, QColor(255, 50, 50, 240))
        gradient.setColorAt(0.7, QColor(255, 0, 0, 120))
        gradient.setColorAt(1.0, QColor(255, 0, 0, 0))

        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPoint(cx, cy), self.radius, self.radius)

        # Tâm laser sáng nét
        painter.setBrush(QColor(255, 255, 255, 230))
        painter.drawEllipse(QPoint(cx, cy), 3, 3)

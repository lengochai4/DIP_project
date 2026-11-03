"""Task 3.3: Dynamic Vector Renderer.

Vẽ các vectơ động lực học:
- Vectơ vận tốc (Velocity Vector)
- Vectơ lực va chạm (Collision Force)
- Quỹ đạo chuyển động (Motion Trajectory)
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple
import pymunk
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen


@dataclass
class PhysicsVector:
    origin: Tuple[float, float]
    target: Tuple[float, float]
    color: QColor
    label: str = ""


class DynamicVectorRenderer:
    """Theo dõi và vẽ các vectơ động lực học cho các vật thể trong không gian."""

    def __init__(self, max_trajectory_points: int = 40) -> None:
        self.trajectories: Dict[int, List[Tuple[float, float]]] = {}
        self.max_points = max_trajectory_points
        self.velocity_scale = 0.08  # Hệ số vẽ độ dài vector vận tốc

    def record_step(self, bodies: List[pymunk.Body]) -> None:
        """Ghi nhận toạ độ để vẽ vết quỹ đạo chuyển động."""
        for b in bodies:
            b_id = id(b)
            if b_id not in self.trajectories:
                self.trajectories[b_id] = []
            pts = self.trajectories[b_id]
            pts.append((b.position.x, b.position.y))
            if len(pts) > self.max_points:
                pts.pop(0)

    def draw_vectors(self, painter: QPainter, bodies: List[pymunk.Body]) -> None:
        """Vẽ toàn bộ vector vận tốc và quỹ đạo lên QPainter."""
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. Vẽ quỹ đạo (Trajectory Trails)
        for b_id, pts in self.trajectories.items():
            if len(pts) > 1:
                pen = QPen(QColor(100, 150, 255, 100), 1.5, Qt.DashLine)
                painter.setPen(pen)
                for i in range(len(pts) - 1):
                    p1 = QPointF(pts[i][0], pts[i][1])
                    p2 = QPointF(pts[i + 1][0], pts[i + 1][1])
                    painter.drawLine(p1, p2)

        # 2. Vẽ vectơ vận tốc cho từng vật thể
        for b in bodies:
            vx, vy = b.velocity
            speed = math.hypot(vx, vy)
            if speed > 15.0:
                ox, oy = b.position.x, b.position.y
                tx = ox + vx * self.velocity_scale
                ty = oy + vy * self.velocity_scale

                # Đường mũi tên vận tốc (Màu xanh dương dạ quang)
                pen_v = QPen(QColor(0, 230, 255, 230), 2.2)
                painter.setPen(pen_v)
                painter.drawLine(QPointF(ox, oy), QPointF(tx, ty))

                # Vẽ chóp mũi tên
                angle = math.atan2(ty - oy, tx - ox)
                arrow_size = 8.0
                p_left = QPointF(
                    tx - arrow_size * math.cos(angle - math.pi / 6),
                    ty - arrow_size * math.sin(angle - math.pi / 6)
                )
                p_right = QPointF(
                    tx - arrow_size * math.cos(angle + math.pi / 6),
                    ty - arrow_size * math.sin(angle + math.pi / 6)
                )
                painter.drawLine(QPointF(tx, ty), p_left)
                painter.drawLine(QPointF(tx, ty), p_right)

                # Nhãn vận tốc
                painter.setPen(QColor(255, 255, 255, 220))
                painter.drawText(int(tx + 5), int(ty - 5), f"{speed:.0f} px/s")

    def clear(self) -> None:
        self.trajectories.clear()

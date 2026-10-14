"""2D Physics Simulation Extension Module."""

from typing import Any, List, Optional, Tuple
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from app.extensions.hub.base import ExtensionCategory, ExtensionModule
from .world import Physics2DWorld
from .kinematic_hand import KinematicFingerInteraction
from .vector_renderer import DynamicVectorRenderer
from .experiments import PhysicsExperiments


class Physics2DSimulationExtension(ExtensionModule):
    id = "physics_2d_simulation"
    name = "2D Physics Simulation"
    category = ExtensionCategory.PHYSICS_2D
    description = "Không gian vật lý Pymunk: Thả khối rigid-body, lực đẩy ngón tay, vectơ động lực học & thí nghiệm."
    icon = "⚛️"

    def __init__(self) -> None:
        super().__init__()
        self.world: Optional[Physics2DWorld] = None
        self.kinematic_finger: Optional[KinematicFingerInteraction] = None
        self.vector_renderer = DynamicVectorRenderer()
        self.last_pinch = False
        self.current_experiment = "Freeplay"

    def on_enable(self) -> bool:
        self.world = Physics2DWorld(width=1000, height=700, gravity=800.0)
        self.kinematic_finger = KinematicFingerInteraction(self.world.space, radius=26.0)
        self.vector_renderer.clear()
        self.status.message = "Không gian vật lý Pymunk sẵn sàng"
        return True

    def on_disable(self) -> None:
        if self.kinematic_finger:
            self.kinematic_finger.remove()
            self.kinematic_finger = None
        self.world = None
        self.vector_renderer.clear()

    def load_experiment(self, name: str) -> None:
        """Kích hoạt kịch bản thí nghiệm theo yêu cầu."""
        if not self.world:
            return
        self.current_experiment = name
        if name == "Collision":
            PhysicsExperiments.setup_elastic_collision(self.world)
            self.status.message = "Thí nghiệm va chạm đàn hồi"
        elif name == "Pendulum":
            PhysicsExperiments.setup_pendulum(self.world)
            self.status.message = "Thí nghiệm con lắc đơn"
        elif name == "Freeplay":
            self.world.clear_bodies()
            self.status.message = "Chế độ tự do (Pinch thả khối)"
        self.notify_status()

    def process_frame(
        self,
        hands: List[Any],
        interaction_state: Optional[Any],
        screen_size: Tuple[int, int],
        **kwargs: Any,
    ) -> None:
        if not self.world:
            return

        w_screen, h_screen = screen_size
        self.world.width = max(600, w_screen)
        self.world.height = max(400, h_screen)

        if hands:
            dominant = hands[0]
            px, py = dominant.pointer_xy
            world_x = px * self.world.width
            world_y = py * self.world.height

            # 1. Cập nhật vị trí ngón tay Kinematic để tạo lực đẩy
            if self.kinematic_finger:
                self.kinematic_finger.update_position((world_x, world_y))

            # 2. Cử chỉ Pinch để thả khối vật thể (Task 3.1)
            is_pinching = getattr(dominant, "is_pinched", False) or getattr(dominant, "pose", "") == "PINCH"
            if is_pinching and not self.last_pinch:
                # Thả luân phiên quả cầu hoặc hộp chữ nhật
                if len(self.world.bodies) % 2 == 0:
                    self.world.spawn_circle(world_x, world_y, radius=22.0)
                else:
                    self.world.spawn_box(world_x, world_y, size=(38.0, 38.0))
                self.status.message = f"Đã thả khối ({len(self.world.bodies)} vật thể)"
                self.notify_status()

            self.last_pinch = is_pinching

        # 3. Tiến trình vật lý
        self.world.step(1.0 / 60.0)
        self.vector_renderer.record_step(self.world.bodies)

    def render_overlay(self, painter: QPainter, rect: Tuple[int, int, int, int]) -> None:
        """Vẽ trực tiếp thế giới Pymunk lên viewport."""
        if not self.world:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. Vẽ các khối vật thể (Bodies & Shapes)
        for body in self.world.bodies:
            bx, by = body.position.x, body.position.y
            painter.save()
            painter.translate(bx, by)
            painter.rotate(body.angle * 57.2957795)  # Radian to degrees

            for shape in body.shapes:
                if hasattr(shape, "radius"):
                    # Hình tròn
                    r = shape.radius
                    painter.setBrush(QBrush(QColor(66, 135, 245, 220)))
                    painter.setPen(QPen(QColor(255, 255, 255, 200), 1.8))
                    painter.drawEllipse(QPointF(0, 0), r, r)
                    # Đường chỉ hướng xoay
                    painter.drawLine(QPointF(0, 0), QPointF(r, 0))
                elif hasattr(shape, "get_vertices"):
                    # Đa giác / Hộp
                    verts = shape.get_vertices()
                    qpoints = [QPointF(v.x, v.y) for v in verts]
                    painter.setBrush(QBrush(QColor(245, 164, 66, 220)))
                    painter.setPen(QPen(QColor(255, 255, 255, 200), 1.8))
                    painter.drawPolygon(qpoints)

            painter.restore()

        # 2. Vẽ ngón tay Kinematic
        if self.kinematic_finger:
            fx, fy = self.kinematic_finger.body.position
            painter.setBrush(QBrush(QColor(46, 204, 113, 160)))
            painter.setPen(QPen(QColor(255, 255, 255, 230), 2.2))
            painter.drawEllipse(QPointF(fx, fy), self.kinematic_finger.radius, self.kinematic_finger.radius)

        # 3. Vẽ các vectơ động lực học (Task 3.3)
        self.vector_renderer.draw_vectors(painter, self.world.bodies)

        painter.restore()

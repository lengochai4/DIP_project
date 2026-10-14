"""Task 3.2: Kinematic Hand Body Interaction.

Gắn đầu ngón tay làm vật thể động Kinematic trong Pymunk để đẩy và tương tác lực trực tiếp lên các khối hình.
"""

from typing import Tuple
import pymunk


class KinematicFingerInteraction:
    """Quản lý vật thể Kinematic gắn theo đầu ngón tay trỏ."""

    def __init__(self, space: pymunk.Space, radius: float = 28.0) -> None:
        self.space = space
        self.radius = radius

        # Tạo Kinematic body (không bị trọng lực tác động, nhưng truyền động lượng)
        self.body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.shape = pymunk.Circle(self.body, self.radius)
        self.shape.elasticity = 0.9
        self.shape.friction = 0.8
        self.shape.color = (46, 204, 113, 220)  # Xanh lục

        self.space.add(self.body, self.shape)
        self.prev_pos = (0.0, 0.0)

    def update_position(self, target_pos: Tuple[float, float], dt: float = 1.0 / 60.0) -> None:
        """Cập nhật vị trí và tính toán vận tốc Kinematic tức thời để truyền lực va chạm."""
        tx, ty = target_pos
        px, py = self.body.position

        if dt > 1e-4:
            # Vận tốc tức thời = độ dời / thời gian
            vx = (tx - px) / dt
            vy = (ty - py) / dt
            self.body.velocity = (vx, vy)

        self.body.position = (tx, ty)
        self.prev_pos = (tx, ty)

    def remove(self) -> None:
        if self.shape in self.space.shapes:
            self.space.remove(self.shape)
        if self.body in self.space.bodies:
            self.space.remove(self.body)

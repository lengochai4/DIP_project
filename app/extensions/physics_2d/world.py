"""Task 3.1: 2D Physics Space & Rigid Body Spawning with Pymunk.

Tạo không gian Pymunk và thả các vật thể vật lý (rigid-body: khối hộp, hình tròn, đa giác).
"""

import math
from typing import List, Optional, Tuple
import pymunk


class Physics2DWorld:
    """Quản lý không gian vật lý 2D, biên giới hạn và các vật thể rigid-body."""

    def __init__(self, width: int = 800, height: int = 600, gravity: float = 900.0) -> None:
        self.width = width
        self.height = height
        self.space = pymunk.Space()
        self.space.gravity = (0.0, gravity)
        self.bodies: List[pymunk.Body] = []
        self._setup_boundaries()

    def _setup_boundaries(self) -> None:
        """Tạo sàn và các vách tường ngăn rơi ra ngoài."""
        static_body = self.space.static_body
        thickness = 20.0
        # Sàn
        floor = pymunk.Segment(static_body, (0, self.height - 10), (self.width, self.height - 10), thickness)
        floor.elasticity = 0.8
        floor.friction = 0.6
        # Tường trái & phải
        left_wall = pymunk.Segment(static_body, (10, 0), (10, self.height), thickness)
        left_wall.elasticity = 0.8
        left_wall.friction = 0.5

        right_wall = pymunk.Segment(static_body, (self.width - 10, 0), (self.width - 10, self.height), thickness)
        right_wall.elasticity = 0.8
        right_wall.friction = 0.5

        self.space.add(floor, left_wall, right_wall)

    def spawn_circle(self, x: float, y: float, radius: float = 24.0, mass: float = 2.0) -> pymunk.Body:
        """Thả một quả cầu vật lý tại toạ độ (x, y)."""
        inertia = pymunk.moment_for_circle(mass, 0, radius)
        body = pymunk.Body(mass, inertia)
        body.position = (x, y)
        shape = pymunk.Circle(body, radius)
        shape.elasticity = 0.85
        shape.friction = 0.5
        shape.color = (66, 135, 245, 255)  # Xanh dương
        self.space.add(body, shape)
        self.bodies.append(body)
        return body

    def spawn_box(self, x: float, y: float, size: Tuple[float, float] = (40.0, 40.0), mass: float = 3.0) -> pymunk.Body:
        """Thả một khối hộp vuông vật lý tại toạ độ (x, y)."""
        w, h = size
        inertia = pymunk.moment_for_box(mass, (w, h))
        body = pymunk.Body(mass, inertia)
        body.position = (x, y)
        shape = pymunk.Poly.create_box(body, (w, h))
        shape.elasticity = 0.6
        shape.friction = 0.7
        shape.color = (245, 164, 66, 255)  # Cam
        self.space.add(body, shape)
        self.bodies.append(body)
        return body

    def set_gravity(self, g: float) -> None:
        """Điều chỉnh gia tốc trọng trường qua cử chỉ."""
        self.space.gravity = (0.0, g)

    def step(self, dt: float = 1.0 / 60.0) -> None:
        """Tiến hóa mô phỏng vật lý một bước thời gian."""
        self.space.step(dt)

    def clear_bodies(self) -> None:
        for b in self.bodies:
            for s in list(b.shapes):
                self.space.remove(s)
            self.space.remove(b)
        self.bodies.clear()

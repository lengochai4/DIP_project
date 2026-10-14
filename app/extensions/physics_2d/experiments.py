"""Task 3.4: Physics Experiments Simulation.

Các kịch bản thí nghiệm vật lý:
1. Va chạm đàn hồi (Elastic Collision)
2. Con lắc đơn (Simple Pendulum với PinJoint)
3. Trọng lực tuỳ chỉnh qua cử chỉ tay (Gesture Gravity Control)
"""

from typing import List, Optional, Tuple
import pymunk
from .world import Physics2DWorld


class PhysicsExperiments:
    """Khởi tạo và thiết lập các kịch bản thí nghiệm vật lý."""

    @staticmethod
    def setup_elastic_collision(world: Physics2DWorld) -> None:
        """Thiết lập thí nghiệm va chạm đàn hồi 2 vật thể tiến lại gần nhau."""
        world.clear_bodies()
        y_pos = world.height * 0.5

        # Quả bóng 1 (Bên trái, nặng hơn, vận tốc dương sang phải)
        b1 = world.spawn_circle(x=world.width * 0.25, y=y_pos, radius=32.0, mass=5.0)
        b1.velocity = (350.0, 0.0)
        for s in b1.shapes:
            s.elasticity = 1.0  # Hoàn toàn đàn hồi
            s.friction = 0.0

        # Quả bóng 2 (Bên phải, nhẹ hơn, đứng yên hoặc bay ngược lại)
        b2 = world.spawn_circle(x=world.width * 0.75, y=y_pos, radius=22.0, mass=1.5)
        b2.velocity = (-150.0, 0.0)
        for s in b2.shapes:
            s.elasticity = 1.0
            s.friction = 0.0

    @staticmethod
    def setup_pendulum(world: Physics2DWorld) -> Tuple[pymunk.Body, pymunk.PinJoint]:
        """Thiết lập thí nghiệm con lắc đơn dao động dưới tác dụng trọng lực."""
        world.clear_bodies()
        pivot = (world.width * 0.5, world.height * 0.2)
        bob_initial = (world.width * 0.5 + 180.0, world.height * 0.2 + 80.0)

        # Quả nặng con lắc
        bob = world.spawn_circle(bob_initial[0], bob_initial[1], radius=26.0, mass=4.0)

        # Dây treo nối tâm cố định với quả nặng
        joint = pymunk.PinJoint(world.space.static_body, bob, pivot, (0, 0))
        world.space.add(joint)
        return bob, joint

    @staticmethod
    def adjust_gravity_by_hand(world: Physics2DWorld, hand_norm_y: float) -> float:
        """Điều chỉnh gia tốc trọng lực dựa theo độ cao ngón tay (Hand Height).

        - Tay ở đỉnh màn hình (y ~ 0.1) -> Không trọng lực / Bay lơ lửng (g = 0 hoặc âm).
        - Tay ở đáy màn hình (y ~ 0.9) -> Trọng lực cực mạnh (g = 1800 px/s²).
        """
        # Ánh xạ từ [0.1, 0.9] -> [-200, 1800]
        clamped_y = max(0.1, min(0.9, hand_norm_y))
        gravity_val = -200.0 + (clamped_y - 0.1) * (2000.0 / 0.8)
        world.set_gravity(gravity_val)
        return gravity_val

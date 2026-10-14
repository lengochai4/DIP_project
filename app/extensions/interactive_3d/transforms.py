"""Task 1.2: Gesture to Deformation Matrix Mapping.

Bao gồm Quaternion Rotation, Tịnh tiến (Translation), và Pinch Zoom.
"""

import math
from dataclasses import dataclass
from typing import Tuple
import numpy as np


@dataclass
class Quaternion:
    w: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    @classmethod
    def from_axis_angle(cls, axis: Tuple[float, float, float], angle_rad: float) -> "Quaternion":
        norm = math.hypot(axis[0], axis[1], axis[2])
        if norm < 1e-9:
            return cls(1.0, 0.0, 0.0, 0.0)
        half = angle_rad * 0.5
        sin_half = math.sin(half)
        return cls(
            w=math.cos(half),
            x=(axis[0] / norm) * sin_half,
            y=(axis[1] / norm) * sin_half,
            z=(axis[2] / norm) * sin_half,
        )

    def multiply(self, other: "Quaternion") -> "Quaternion":
        w1, x1, y1, z1 = self.w, self.x, self.y, self.z
        w2, x2, y2, z2 = other.w, other.x, other.y, other.z
        return Quaternion(
            w=w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            x=w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            y=w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            z=w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        )

    def normalize(self) -> "Quaternion":
        norm = math.sqrt(self.w * self.w + self.x * self.x + self.y * self.y + self.z * self.z)
        if norm < 1e-9:
            return Quaternion(1.0, 0.0, 0.0, 0.0)
        return Quaternion(self.w / norm, self.x / norm, self.y / norm, self.z / norm)

    def to_rotation_matrix(self) -> np.ndarray:
        """Chuyển đổi sang ma trận xoay 3x3 chuẩn."""
        q = self.normalize()
        w, x, y, z = q.w, q.x, q.y, q.z
        return np.array([
            [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)],
            [2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)],
            [2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)],
        ], dtype=float)


class GestureTransformMapper:
    """Ánh xạ cử chỉ tay (Pinch, Drag, Rotate) sang ma trận chuyển đổi 3D."""

    def __init__(self) -> None:
        self.orientation = Quaternion(1.0, 0.0, 0.0, 0.0)
        self.translation = np.array([0.0, 0.0, 0.0], dtype=float)
        self.scale = 1.0
        self.min_scale = 0.3
        self.max_scale = 4.0

    def apply_rotation_delta(self, dx: float, dy: float, sensitivity: float = 3.5) -> None:
        """Cập nhật góc xoay mượt mà bằng tích Quaternion từ độ lệch cử chỉ."""
        if math.hypot(dx, dy) < 1e-5:
            return
        # Xoay quanh trục Y (trái/phải) và trục X (lên/xuống)
        rot_y = Quaternion.from_axis_angle((0.0, 1.0, 0.0), dx * sensitivity)
        rot_x = Quaternion.from_axis_angle((1.0, 0.0, 0.0), dy * sensitivity)
        delta_q = rot_y.multiply(rot_x)
        self.orientation = delta_q.multiply(self.orientation).normalize()

    def apply_translation_delta(self, dx: float, dy: float, gain: float = 1.2) -> None:
        """Tịnh tiến vật thể trong không gian 3D."""
        self.translation[0] += dx * gain
        self.translation[1] -= dy * gain  # Lật trục Y màn hình sang hệ toạ độ 3D

    def apply_pinch_zoom(self, pinch_delta: float, gain: float = 2.0) -> None:
        """Thu phóng tỷ lệ vật thể từ cử chỉ véo/bung ngón tay."""
        new_scale = self.scale * (1.0 + pinch_delta * gain)
        self.scale = max(self.min_scale, min(self.max_scale, new_scale))

    def get_transform_matrix_4x4(self) -> np.ndarray:
        """Tạo ma trận biến dạng tổng hợp 4x4 (Scale -> Rotate -> Translate)."""
        r3 = self.orientation.to_rotation_matrix()
        m = np.eye(4, dtype=float)
        m[:3, :3] = r3 * self.scale
        m[:3, 3] = self.translation
        return m

    def transform_vertices(self, vertices: np.ndarray) -> np.ndarray:
        """Biến đổi trực tiếp tập đỉnh 3D: P' = (R * P) * scale + T."""
        r3 = self.orientation.to_rotation_matrix()
        # vertices shape: (N, 3)
        rotated = (vertices @ r3.T) * self.scale
        return rotated + self.translation

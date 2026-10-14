"""Task 1.3: Realtime Geometric Calculations with Shapely.

Đo khoảng cách 3D, góc xoay (angles), và tính toán diện tích mặt cắt hình học phẳng.
"""

import math
from typing import List, Optional, Tuple
import numpy as np

try:
    from shapely.geometry import Polygon, Point, LineString
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False


class RealtimeGeometryCalculator:
    """Tính toán hình học thời gian thực hỗ trợ STEM."""

    @staticmethod
    def distance_3d(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
        """Đo khoảng cách Euclidean giữa 2 điểm trong không gian 3D."""
        return float(math.dist(p1, p2))

    @staticmethod
    def angle_between_vectors(v1: Tuple[float, float, float], v2: Tuple[float, float, float]) -> float:
        """Đo góc giữa 2 vector 3D (đơn vị độ - degrees)."""
        a = np.asarray(v1, dtype=float)
        b = np.asarray(v2, dtype=float)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a < 1e-9 or norm_b < 1e-9:
            return 0.0
        cos_val = np.dot(a, b) / (norm_a * norm_b)
        cos_val = np.clip(cos_val, -1.0, 1.0)
        return float(math.degrees(math.acos(cos_val)))

    @staticmethod
    def polygon_area_2d(points_2d: List[Tuple[float, float]]) -> float:
        """Tính diện tích đa giác 2D mặt cắt sử dụng Shapely hoặc công thức Shoelace."""
        if len(points_2d) < 3:
            return 0.0

        if HAS_SHAPELY:
            try:
                poly = Polygon(points_2d)
                if not poly.is_valid:
                    poly = poly.buffer(0)
                return float(poly.area)
            except Exception:
                pass

        # Thuật toán Shoelace dự phòng
        n = len(points_2d)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += points_2d[i][0] * points_2d[j][1]
            area -= points_2d[j][0] * points_2d[i][1]
        return float(abs(area) * 0.5)

    @classmethod
    def compute_plane_cross_section(
        cls,
        vertices: np.ndarray,
        plane_normal: Tuple[float, float, float] = (0.0, 1.0, 0.0),
        plane_offset: float = 0.0,
    ) -> Tuple[float, List[Tuple[float, float]]]:
        """Tính diện tích và các đỉnh của mặt cắt hình học qua một mặt phẳng."""
        # Chiếu các đỉnh lên mặt phẳng 2D gần mặt phẳng cắt
        norm = np.array(plane_normal, dtype=float)
        norm /= np.linalg.norm(norm) + 1e-9

        # Lọc các điểm gần mặt phẳng cắt trong khoảng epsilon
        distances = np.dot(vertices, norm) - plane_offset
        mask = np.abs(distances) < 0.25

        if np.count_nonzero(mask) < 3:
            return 0.0, []

        selected = vertices[mask]
        # Tạo toạ độ 2D trên mặt cắt bằng cách bỏ chiều tương quan chính
        axis_drop = int(np.argmax(np.abs(norm)))
        axes_keep = [i for i in range(3) if i != axis_drop]
        coords_2d = [(float(pt[axes_keep[0]]), float(pt[axes_keep[1]])) for pt in selected]

        # Sắp xếp các điểm theo góc cực quanh tâm để tạo đa giác lồi
        center = np.mean(coords_2d, axis=0)
        sorted_coords = sorted(
            coords_2d,
            key=lambda p: math.atan2(p[1] - center[1], p[0] - center[0])
        )

        area = cls.polygon_area_2d(sorted_coords)
        return area, sorted_coords

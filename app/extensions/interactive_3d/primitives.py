"""Task 1.1: 3D Primitives Construction (Cube, Sphere, Cone).

Tạo lưới hình học (vertices, faces, normals, colors) cho các khối hình học cơ bản.
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple
import numpy as np


@dataclass
class MeshFace:
    indices: Tuple[int, ...]
    normal: Tuple[float, float, float]
    color: str = "#4a90e2"
    hovered: bool = False
    name: str = ""


@dataclass
class PrimitiveMesh:
    name: str
    vertices: np.ndarray  # Shape: (N, 3)
    faces: List[MeshFace]
    center: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: float = 1.0


class PrimitivesFactory:
    """Xây dựng dữ liệu lưới 3D cho các khối hình học cơ bản."""

    @staticmethod
    def create_cube(size: float = 0.8, color: str = "#4a90e2") -> PrimitiveMesh:
        """Tạo khối lập phương với 6 mặt riêng biệt để tương tác bề mặt."""
        s = size / 2.0
        # 8 đỉnh cơ bản
        raw_verts = [
            (-s, -s, -s), (s, -s, -s), (s, s, -s), (-s, s, -s),
            (-s, -s, s), (s, -s, s), (s, s, s), (-s, s, s)
        ]
        vertices = np.array(raw_verts, dtype=float)

        face_definitions = [
            ((0, 1, 2, 3), (0.0, 0.0, -1.0), "Mặt Trước (-Z)"),
            ((4, 5, 6, 7), (0.0, 0.0, 1.0), "Mặt Sau (+Z)"),
            ((0, 4, 7, 3), (-1.0, 0.0, 0.0), "Mặt Trái (-X)"),
            ((1, 5, 6, 2), (1.0, 0.0, 0.0), "Mặt Phải (+X)"),
            ((3, 2, 6, 7), (0.0, 1.0, 0.0), "Mặt Trên (+Y)"),
            ((0, 1, 5, 4), (0.0, -1.0, 0.0), "Mặt Dưới (-Y)"),
        ]

        faces = [
            MeshFace(indices=idx, normal=n, color=color, name=name)
            for idx, n, name in face_definitions
        ]
        return PrimitiveMesh(name="Cube", vertices=vertices, faces=faces)

    @staticmethod
    def create_sphere(radius: float = 0.5, rings: int = 14, sectors: int = 18, color: str = "#e74c3c") -> PrimitiveMesh:
        """Tạo hình cầu UV với các phân đoạn kinh độ và vĩ độ."""
        vertices_list = []
        for r in range(rings + 1):
            theta = r * math.pi / rings
            sin_t = math.sin(theta)
            cos_t = math.cos(theta)
            for s in range(sectors):
                phi = s * 2.0 * math.pi / sectors
                x = radius * sin_t * math.cos(phi)
                y = radius * cos_t
                z = radius * sin_t * math.sin(phi)
                vertices_list.append((x, y, z))

        vertices = np.array(vertices_list, dtype=float)
        faces = []
        for r in range(rings):
            for s in range(sectors):
                first = r * sectors + s
                second = first + sectors
                next_s = (s + 1) % sectors
                first_next = r * sectors + next_s
                second_next = second - s + next_s

                # Mặt tứ giác xấp xỉ
                idx = (first, second, second_next, first_next)
                # Tính pháp tuyến tâm
                mid_pt = vertices[first] + vertices[second] + vertices[second_next] + vertices[first_next]
                norm = mid_pt / (np.linalg.norm(mid_pt) + 1e-9)
                faces.append(MeshFace(
                    indices=idx,
                    normal=(float(norm[0]), float(norm[1]), float(norm[2])),
                    color=color,
                    name=f"Vùng cầu ({r},{s})",
                ))

        return PrimitiveMesh(name="Sphere", vertices=vertices, faces=faces)

    @staticmethod
    def create_cone(radius: float = 0.5, height: float = 0.8, segments: int = 18, color: str = "#2ecc71") -> PrimitiveMesh:
        """Tạo hình nón gồm đỉnh chóp, đáy tròn và các mặt bên."""
        apex = (0.0, height / 2.0, 0.0)
        base_center = (0.0, -height / 2.0, 0.0)
        vertices_list = [apex, base_center]

        for s in range(segments):
            angle = s * 2.0 * math.pi / segments
            x = radius * math.cos(angle)
            z = radius * math.sin(angle)
            vertices_list.append((x, -height / 2.0, z))

        vertices = np.array(vertices_list, dtype=float)
        faces = []

        # Các mặt bên tam giác nối đỉnh chóp
        for s in range(segments):
            curr_idx = 2 + s
            next_idx = 2 + ((s + 1) % segments)
            mid = (vertices[curr_idx] + vertices[next_idx]) * 0.5
            norm = np.array([mid[0], radius / height, mid[2]])
            norm /= np.linalg.norm(norm) + 1e-9
            faces.append(MeshFace(
                indices=(0, curr_idx, next_idx),
                normal=(float(norm[0]), float(norm[1]), float(norm[2])),
                color=color,
                name=f"Mặt nón {s+1}",
            ))

        # Mặt đáy nón
        base_indices = tuple(range(2, 2 + segments))
        faces.append(MeshFace(
            indices=base_indices,
            normal=(0.0, -1.0, 0.0),
            color=color,
            name="Đáy nón",
        ))

        return PrimitiveMesh(name="Cone", vertices=vertices, faces=faces)

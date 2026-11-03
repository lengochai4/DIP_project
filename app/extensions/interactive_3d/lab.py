"""Interactive 3D STEM Lab - Integrating Primitives, Transforms, Geometry Calc & Surface Interaction."""

from typing import Tuple
import numpy as np
from app.extensions.base import Lab, Geometry, Line, Ball, Face
from .primitives import PrimitivesFactory, PrimitiveMesh
from .transforms import GestureTransformMapper
from .geometry_calc import RealtimeGeometryCalculator
from .surface_interaction import SurfaceInteractionManager


class InteractiveStemLab(Lab):
    id, title, category = "interactive_stem", "Interactive 3D STEM", "Geometry & Physics"
    dimensionality = "3D Primitives & Real-time Shapely Analytics"
    presets = ("Cube", "Sphere", "Cone")
    tools = ("Interact", "Measure", "CrossSection")

    def __init__(self, config=None) -> None:
        super().__init__(config)
        self.preset = "Cube"
        self.tool = "Interact"
        self.mapper = GestureTransformMapper()
        self.surface_mgr = SurfaceInteractionManager()
        self._current_mesh: PrimitiveMesh = PrimitivesFactory.create_cube()
        self._measured_distance: float = 0.0
        self._cross_section_area: float = 0.0
        self._touch_cursor_3d: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    def set_preset(self, name: str) -> None:
        super().set_preset(name)
        if name == "Cube":
            self._current_mesh = PrimitivesFactory.create_cube()
        elif name == "Sphere":
            self._current_mesh = PrimitivesFactory.create_sphere()
        elif name == "Cone":
            self._current_mesh = PrimitivesFactory.create_cone()

    def set_touch_point(self, pt: Tuple[float, float, float]) -> None:
        """Cập nhật vị trí chạm 3D từ đầu ngón tay."""
        self._touch_cursor_3d = pt
        verts = self.mapper.transform_vertices(self._current_mesh.vertices)
        self.surface_mgr.update_interaction(self._current_mesh, verts, pt)

    def geometry(self) -> Geometry:
        verts = self.mapper.transform_vertices(self._current_mesh.vertices)
        lines = []
        faces = []
        balls = []
        labels = []

        # 1. Dựng các mặt hình học
        for face in self._current_mesh.faces:
            color = self.surface_mgr.get_face_render_color(face)
            idx = face.indices
            # Tách đa giác thành các tam giác hiển thị
            for i in range(1, len(idx) - 1):
                p0 = tuple(verts[idx[0]])
                p1 = tuple(verts[idx[i]])
                p2 = tuple(verts[idx[i + 1]])
                faces.append(Face(p0, p1, p2, color))

            # Viền cạnh đa giác
            for i in range(len(idx)):
                p_start = tuple(verts[idx[i]])
                p_end = tuple(verts[idx[(i + 1) % len(idx)]])
                lines.append(Line(p_start, p_end, "#ffffff" if face.hovered else "#34495e", 1.8 if face.hovered else 1.0))

        # 2. Hiển thị thông số phân tích hình học
        if self.tool == "Measure":
            # Đo khoảng cách từ gốc toạ độ tới con trỏ chạm
            origin = (0.0, 0.0, 0.0)
            self._measured_distance = RealtimeGeometryCalculator.distance_3d(origin, self._touch_cursor_3d)
            lines.append(Line(origin, self._touch_cursor_3d, "#e74c3c", 2.5))
            balls.append(Ball(origin, 0.04, "#efca82", "O"))
            balls.append(Ball(self._touch_cursor_3d, 0.04, "#e74c3c", "Touch"))
            labels.append((self._touch_cursor_3d, f"d = {self._measured_distance:.2f}m"))

        elif self.tool == "CrossSection":
            # Tính diện tích mặt cắt phẳng Y = 0
            area, polygon_pts = RealtimeGeometryCalculator.compute_plane_cross_section(verts)
            self._cross_section_area = area
            labels.append(((0.0, 0.5, 0.0), f"Diện tích mặt cắt: {area:.3f} m²"))

        # Hiển thị tên mặt đang chạm nếu có
        if self.surface_mgr.touched_face_name:
            labels.append(((0.0, -0.6, 0.0), f"Đang chạm: {self.surface_mgr.touched_face_name}"))

        return Geometry(
            lines=tuple(lines),
            balls=tuple(balls),
            labels=tuple(labels),
            faces=tuple(faces),
        )

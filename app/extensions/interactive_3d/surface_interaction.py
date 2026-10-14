"""Task 1.4: 3D Surface Interaction.

Tương tác bề mặt: Đổi màu từng mặt hình học khi đầu ngón tay trỏ "chạm" vào toạ độ 3D.
"""

from typing import List, Optional, Tuple
import numpy as np
from .primitives import PrimitiveMesh, MeshFace


class SurfaceInteractionManager:
    """Quản lý việc nhận diện tương tác tiếp xúc và tô màu các mặt hình học."""

    DEFAULT_COLOR = "#4a90e2"
    HOVER_COLOR = "#f39c12"
    TOUCH_COLOR = "#00d2d3"

    def __init__(self) -> None:
        self.touched_face_name: Optional[str] = None
        self.touched_face_index: Optional[int] = None

    def update_interaction(
        self,
        mesh: PrimitiveMesh,
        transformed_vertices: np.ndarray,
        touch_point_3d: Optional[Tuple[float, float, float]],
        threshold: float = 0.22,
    ) -> Optional[int]:
        """Kiểm tra khoảng cách từ ngón tay tới tâm từng mặt, đổi màu mặt gần nhất."""
        if touch_point_3d is None:
            # Khôi phục màu gốc khi không chạm
            for face in mesh.faces:
                face.hovered = False
            self.touched_face_name = None
            self.touched_face_index = None
            return None

        tx, ty, tz = touch_point_3d
        closest_dist = float("inf")
        closest_idx = -1

        for idx, face in enumerate(mesh.faces):
            # Tính tâm mặt (Face Centroid)
            face_pts = transformed_vertices[list(face.indices)]
            centroid = np.mean(face_pts, axis=0)

            dist = float(np.linalg.norm(centroid - np.array([tx, ty, tz])))
            if dist < closest_dist:
                closest_dist = dist
                closest_idx = idx

        # Nếu khoảng cách nằm trong bán kính chạm (contact threshold)
        if closest_dist <= threshold and closest_idx >= 0:
            for i, face in enumerate(mesh.faces):
                if i == closest_idx:
                    face.hovered = True
                    self.touched_face_name = face.name
                    self.touched_face_index = closest_idx
                else:
                    face.hovered = False
            return closest_idx
        else:
            for face in mesh.faces:
                face.hovered = False
            self.touched_face_name = None
            self.touched_face_index = None
            return None

    def get_face_render_color(self, face: MeshFace) -> str:
        """Lấy mã màu hiển thị tuỳ theo trạng thái được chạm hay bình thường."""
        if face.hovered:
            return self.TOUCH_COLOR
        return face.color

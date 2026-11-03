"""Interactive 3D STEM Extension Module."""

from typing import Any, List, Optional, Tuple
from app.extensions.hub.base import ExtensionCategory, ExtensionModule
from .lab import InteractiveStemLab


class InteractiveStemExtension(ExtensionModule):
    id = "interactive_3d_stem"
    name = "Interactive 3D STEM"
    category = ExtensionCategory.STEM_3D
    description = "Dựng hình 3D Primitives, tính toán Shapely thời gian thực và tương tác bề mặt chạm đổi màu."
    icon = "🧊"

    def __init__(self) -> None:
        super().__init__()
        self.lab: Optional[InteractiveStemLab] = None

    def on_enable(self) -> bool:
        self.lab = InteractiveStemLab()
        self.status.message = "Đã kích hoạt 3D STEM Lab"
        return True

    def on_disable(self) -> None:
        self.lab = None

    def process_frame(
        self,
        hands: List[Any],
        interaction_state: Optional[Any],
        screen_size: Tuple[int, int],
        **kwargs: Any,
    ) -> None:
        if not self.lab or not hands:
            return

        dominant = hands[0]
        px, py = dominant.pointer_xy
        # Chuyển đổi từ tỉ lệ 2D sang toạ độ không gian 3D tương đối
        x_3d = (px - 0.5) * 2.0
        y_3d = -(py - 0.5) * 2.0
        z_3d = getattr(dominant, "relative_depth", 0.0)

        self.lab.set_touch_point((x_3d, y_3d, z_3d))

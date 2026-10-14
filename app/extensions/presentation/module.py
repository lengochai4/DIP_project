"""Presentation Support Extension Module."""

from typing import Any, List, Optional, Tuple
from app.extensions.hub.base import ExtensionCategory, ExtensionModule
from .slide_controller import SlideController
from .laser_pointer import VirtualLaserPointerOverlay
from .whiteboard_ink import VirtualWhiteboardInk
from .window_manager import WindowManagerExtension


class PresentationSupportExtension(ExtensionModule):
    id = "presentation_support"
    name = "Presentation Support"
    category = ExtensionCategory.PRESENTATION
    description = "Điều khiển Slide, Virtual Laser Pointer, Whiteboard Ink và Quản lý cửa sổ."
    icon = "📽️"

    def __init__(self) -> None:
        super().__init__()
        self.slide_ctrl = SlideController()
        self.laser_overlay: Optional[VirtualLaserPointerOverlay] = None
        self.whiteboard = VirtualWhiteboardInk()
        self.win_mgr = WindowManagerExtension()

        self.enable_laser = True
        self.enable_slides = True
        self.enable_whiteboard = False
        self.enable_window_mgr = True

    def on_enable(self) -> bool:
        if self.enable_laser and self.laser_overlay is None:
            try:
                self.laser_overlay = VirtualLaserPointerOverlay()
                self.laser_overlay.show()
            except Exception:
                pass
        self.status.message = "Đang hỗ trợ thuyết trình"
        return True

    def on_disable(self) -> None:
        if self.laser_overlay:
            try:
                self.laser_overlay.close()
            except Exception:
                pass
            self.laser_overlay = None
        self.whiteboard.clear()

    def process_frame(
        self,
        hands: List[Any],
        interaction_state: Optional[Any],
        screen_size: Tuple[int, int],
        **kwargs: Any,
    ) -> None:
        if not hands:
            if self.laser_overlay:
                self.laser_overlay.hide_laser()
            return

        dominant = hands[0]
        px, py = dominant.pointer_xy
        pose = getattr(dominant, "pose", "POINT")
        timestamp = kwargs.get("timestamp_s", 0.0)
        is_pinching = getattr(dominant, "is_pinched", False) or pose == "PINCH"

        # 1. Cập nhật Laser Pointer
        if self.enable_laser and self.laser_overlay:
            self.laser_overlay.set_laser_pos_normalized(px, py)

        # 2. Điều khiển Slide
        if self.enable_slides:
            slide_action = self.slide_ctrl.process((px, py), pose, timestamp)
            if slide_action:
                self.status.last_action = slide_action
                self.notify_status()

        # 3. Whiteboard Ink
        if self.enable_whiteboard:
            self.whiteboard.process((px, py), is_pinching, screen_size)

        # 4. Quản lý cửa sổ
        if self.enable_window_mgr:
            win_action = self.win_mgr.process(pose, timestamp)
            if win_action:
                self.status.last_action = win_action
                self.notify_status()

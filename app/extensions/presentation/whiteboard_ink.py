"""Task 2.3: Virtual Whiteboard Ink.

Vẽ nét bảng trắng ảo: Giữ cử chỉ "Pinch" hoặc "Chỉ vẽ" để giả lập Click & Drag chuột vẽ nét.
"""

from typing import List, Optional, Tuple

try:
    from pynput.mouse import Button, Controller
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False


class VirtualWhiteboardInk:
    """Giả lập chuột để vẽ bảng trắng (Whiteboard Ink) hoặc vẽ trên PowerPoint."""

    def __init__(self) -> None:
        self.mouse = Controller() if HAS_PYNPUT else None
        self.is_drawing = False
        self.stroke_history: List[List[Tuple[float, float]]] = []
        self.current_stroke: List[Tuple[float, float]] = []

    def process(
        self,
        pointer_xy: Tuple[float, float],
        is_pinching: bool,
        screen_size: Tuple[int, int],
    ) -> bool:
        """Cập nhật thao tác vẽ nét chuột thời gian thực."""
        sw, sh = screen_size
        target_x = int(pointer_xy[0] * sw)
        target_y = int(pointer_xy[1] * sh)

        if is_pinching:
            if not self.is_drawing:
                # Bắt đầu vẽ (Mouse Down)
                self.is_drawing = True
                self.current_stroke = [(pointer_xy[0], pointer_xy[1])]
                if self.mouse:
                    try:
                        self.mouse.position = (target_x, target_y)
                        self.mouse.press(Button.left)
                    except Exception:
                        pass
            else:
                # Đang kéo chuột vẽ (Mouse Drag)
                self.current_stroke.append((pointer_xy[0], pointer_xy[1]))
                if self.mouse:
                    try:
                        self.mouse.position = (target_x, target_y)
                    except Exception:
                        pass
        else:
            if self.is_drawing:
                # Nhả chuột kết thúc nét vẽ (Mouse Up)
                self.is_drawing = False
                if self.current_stroke:
                    self.stroke_history.append(list(self.current_stroke))
                    self.current_stroke.clear()
                if self.mouse:
                    try:
                        self.mouse.release(Button.left)
                    except Exception:
                        pass

        return self.is_drawing

    def clear(self) -> None:
        """Xoá toàn bộ lịch sử nét vẽ."""
        if self.is_drawing and self.mouse:
            try:
                self.mouse.release(Button.left)
            except Exception:
                pass
        self.is_drawing = False
        self.stroke_history.clear()
        self.current_stroke.clear()

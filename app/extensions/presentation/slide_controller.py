"""Task 2.1: Presentation Slide Controller.

Nhận diện cử chỉ:
- Swipe Trái / Phải -> Gửi phím Left / Right qua PyAutoGUI / Pynput.
- Xoè bàn tay (Open Palm) / Nắm tay (Fist) -> Play / Pause (Phím Space hoặc F5).
"""

import time
from typing import Optional, Tuple

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


class SlideController:
    """Điều khiển trình chiếu slide thuyết trình bằng cử chỉ tay không chạm."""

    def __init__(self, cooldown_seconds: float = 0.6) -> None:
        self.cooldown = cooldown_seconds
        self.last_action_time = 0.0
        self.prev_x: Optional[float] = None
        self.prev_time: Optional[float] = None
        self.prev_pose: Optional[str] = None
        self.swipe_threshold_speed = 0.65  # Tốc độ quét màn hình tối thiểu

    def process(self, pointer_xy: Tuple[float, float], pose: str, timestamp_s: float) -> Optional[str]:
        now = timestamp_s if timestamp_s > 0 else time.time()

        if self.prev_x is None or self.prev_time is None:
            self.prev_x = pointer_xy[0]
            self.prev_time = now
            self.prev_pose = pose
            return None

        dt = now - self.prev_time
        action_triggered = None

        if dt > 0.01:
            dx = pointer_xy[0] - self.prev_x
            velocity_x = dx / dt

            # 1. Nhận diện cử chỉ Vuốt (Swipe)
            if now - self.last_action_time > self.cooldown:
                if velocity_x > self.swipe_threshold_speed:
                    action_triggered = "NEXT_SLIDE"
                    self._send_key("right")
                    self.last_action_time = now
                elif velocity_x < -self.swipe_threshold_speed:
                    action_triggered = "PREV_SLIDE"
                    self._send_key("left")
                    self.last_action_time = now

            # 2. Nhận diện Open Palm -> Fist (Play / Pause)
            if now - self.last_action_time > self.cooldown:
                if self.prev_pose == "OPEN_PALM" and pose == "FIST":
                    action_triggered = "PLAY_PAUSE"
                    self._send_key("space")
                    self.last_action_time = now

        self.prev_x = pointer_xy[0]
        self.prev_time = now
        self.prev_pose = pose
        return action_triggered

    def _send_key(self, key_name: str) -> None:
        """Gửi phím an toàn tới hệ điều hành."""
        if HAS_PYAUTOGUI:
            try:
                pyautogui.press(key_name)
            except Exception:
                pass

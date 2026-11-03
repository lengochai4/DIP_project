"""Task 2.4: Window Management.

Chuyển đổi cửa sổ ứng dụng (Alt+Tab hoặc chuyển qua lại các cửa sổ) bằng cử chỉ vẫy tay giữ 1 giây.
"""

import time
from typing import Optional, Tuple

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


class WindowManagerExtension:
    """Quản lý và chuyển đổi cửa sổ hệ điều hành bằng cử chỉ tay."""

    def __init__(self, hold_duration: float = 1.0) -> None:
        self.hold_duration = hold_duration
        self.wave_start_time: Optional[float] = None
        self.last_switch_time = -100.0
        self.cooldown = 1.8

    def process(self, pose: str, timestamp_s: float) -> Optional[str]:
        now = timestamp_s if timestamp_s > 0 else time.time()

        # Cử chỉ vẫy tay hoặc mở lòng bàn tay hướng thẳng (OPEN_PALM / WAVE)
        if pose in {"OPEN_PALM", "FIVE", "WAVE"}:
            if self.wave_start_time is None:
                self.wave_start_time = now
            else:
                elapsed = now - self.wave_start_time
                if elapsed >= self.hold_duration and (now - self.last_switch_time > self.cooldown):
                    self.last_switch_time = now
                    self.wave_start_time = None
                    self._trigger_window_switch()
                    return "WINDOW_SWITCHED"
        else:
            self.wave_start_time = None

        return None

    def _trigger_window_switch(self) -> None:
        """Kích hoạt tổ hợp Alt+Tab chuyển cửa sổ."""
        if HAS_PYAUTOGUI:
            try:
                pyautogui.hotkey("alt", "tab")
            except Exception:
                pass

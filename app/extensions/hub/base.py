"""Extension Layer Hub - Base Contracts and Interfaces."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class ExtensionCategory(str, Enum):
    STEM_3D = "Interactive 3D STEM"
    PRESENTATION = "Presentation Support"
    PHYSICS_2D = "2D Physics Simulation"


@dataclass
class ExtensionStatus:
    active: bool = False
    message: str = "Sẵn sàng"
    fps: float = 0.0
    last_action: Optional[str] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)


class ExtensionModule(ABC):
    """Giao diện chuẩn cho tất cả các phân hệ Extension."""

    id: str = "base_extension"
    name: str = "Base Extension"
    category: ExtensionCategory = ExtensionCategory.STEM_3D
    description: str = ""
    icon: str = "🧩"

    def __init__(self) -> None:
        self.enabled: bool = False
        self.status: ExtensionStatus = ExtensionStatus()
        self.listeners: List[Callable[[ExtensionStatus], None]] = []

    def add_status_listener(self, listener: Callable[[ExtensionStatus], None]) -> None:
        if listener not in self.listeners:
            self.listeners.append(listener)

    def notify_status(self) -> None:
        for listener in self.listeners:
            try:
                listener(self.status)
            except Exception:
                pass

    def enable(self) -> bool:
        if not self.enabled:
            self.enabled = True
            success = self.on_enable()
            if not success:
                self.enabled = False
            else:
                self.status.active = True
                self.status.message = "Đang hoạt động"
                self.notify_status()
            return success
        return True

    def disable(self) -> None:
        if self.enabled:
            self.enabled = False
            self.on_disable()
            self.status.active = False
            self.status.message = "Đã tắt"
            self.notify_status()

    @abstractmethod
    def on_enable(self) -> bool:
        """Khởi tạo tài nguyên khi bật extension."""
        return True

    @abstractmethod
    def on_disable(self) -> None:
        """Giải phóng tài nguyên khi tắt extension."""
        pass

    @abstractmethod
    def process_frame(
        self,
        hands: List[Any],
        interaction_state: Optional[Any],
        screen_size: Tuple[int, int],
        **kwargs: Any,
    ) -> None:
        """Xử lý dữ liệu tracking của từng frame."""
        pass

    def render_overlay(self, painter: Any, rect: Tuple[int, int, int, int]) -> None:
        """Vẽ lớp phủ bổ trợ lên màn hình (nếu có)."""
        pass

"""Extension Manager - Lifecycle and dispatch coordination."""

from typing import Any, Dict, List, Optional, Tuple
from .base import ExtensionCategory, ExtensionModule


class ExtensionManager:
    """Quản lý vòng đời và điều phối sự kiện cho toàn bộ các Extension."""

    def __init__(self) -> None:
        self._modules: Dict[str, ExtensionModule] = {}

    def register(self, module: ExtensionModule) -> None:
        self._modules[module.id] = module

    def get_module(self, module_id: str) -> Optional[ExtensionModule]:
        return self._modules.get(module_id)

    def list_modules(self) -> List[ExtensionModule]:
        return list(self._modules.values())

    def list_by_category(self, category: ExtensionCategory) -> List[ExtensionModule]:
        return [m for m in self._modules.values() if m.category == category]

    def set_module_enabled(self, module_id: str, enabled: bool) -> bool:
        module = self.get_module(module_id)
        if not module:
            return False
        if enabled:
            return module.enable()
        else:
            module.disable()
            return True

    def dispatch_frame(
        self,
        hands: List[Any],
        interaction_state: Optional[Any],
        screen_size: Tuple[int, int],
        **kwargs: Any,
    ) -> None:
        """Phân phối frame từ pipeline sang các extension đang bật."""
        for module in self._modules.values():
            if module.enabled:
                try:
                    module.process_frame(hands, interaction_state, screen_size, **kwargs)
                except Exception:
                    pass

    def render_overlays(self, painter: Any, rect: Tuple[int, int, int, int]) -> None:
        """Vẽ lớp phủ của các extension đang kích hoạt."""
        for module in self._modules.values():
            if module.enabled:
                try:
                    module.render_overlay(painter, rect)
                except Exception:
                    pass

    def shutdown_all(self) -> None:
        """Tắt toàn bộ extension khi thoát ứng dụng."""
        for module in self._modules.values():
            if module.enabled:
                try:
                    module.disable()
                except Exception:
                    pass

"""Screen-space controls and the Extension-side interaction router."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from dip_touchless.core import InteractionState

from .layout import (
    Rect,
    calculate_dashboard_layout,
    map_normalized_point_to_rect,
)
from .presentation_model import DashboardMode
from .theme import THEME


class InteractionFocus(str, Enum):
    SCENE_FOCUS = "SCENE_FOCUS"
    UI_FOCUS = "UI_FOCUS"


@dataclass(frozen=True, slots=True)
class PanelButton:
    """A deterministic screen-space button region."""

    button_id: str
    label: str
    rect: Rect
    enabled: bool = True
    selected: bool = False


@dataclass(frozen=True, slots=True)
class SpatialPanelLayout:
    viewport: Rect
    buttons: tuple[PanelButton, ...]

    def button_at(
        self,
        point_xy: tuple[int, int] | None,
    ) -> PanelButton | None:
        """Return the button under a point; left/top edges are inclusive."""

        if point_xy is None:
            return None
        x, y = point_xy
        for button in self.buttons:
            rect = button.rect
            if (
                rect.x <= x < rect.right
                and rect.y <= y < rect.bottom
            ):
                return button
        return None

    def hit_test(
        self,
        point_xy: tuple[int, int] | None,
    ) -> str | None:
        """Return an enabled button ID, using right/bottom-exclusive edges."""

        button = self.button_at(point_xy)
        if button is None or not button.enabled:
            return None
        return button.button_id


@dataclass(frozen=True, slots=True)
class SpatialPanelViewState:
    open: bool
    focus: InteractionFocus
    cursor_xy: tuple[int, int] | None = None
    hovered_button: str | None = None
    pressed_button: str | None = None
    activated_button: str | None = None
    active_scene_id: str | None = None
    mode: DashboardMode = DashboardMode.DEMO


@dataclass(frozen=True, slots=True)
class InteractionRoute:
    consumed: bool
    forward_to_scene: bool
    action: str | None = None


def build_spatial_panel_layout(
    width: int,
    height: int,
    *,
    active_scene_id: str | None = None,
    mode: DashboardMode = DashboardMode.DEMO,
) -> SpatialPanelLayout:
    """Build the responsive panel over the dashboard's right workspace."""

    dashboard = calculate_dashboard_layout(width, height)
    viewport = Rect(
        x=dashboard.scene.x,
        y=dashboard.scene.y,
        width=dashboard.scene.width,
        height=(
            dashboard.interaction.bottom
            - dashboard.scene.y
        ),
    )
    padding = THEME.card_padding
    inner_x = viewport.x + padding
    inner_width = max(1, viewport.width - 2 * padding)
    button_height = 40
    scene_y = viewport.y + 75
    scene_ids = (
        "coordinate-geometry",
        "molecule",
        "orbital-system",
    )
    scene_labels = (
        "Coordinate Geometry",
        "Molecule",
        "Orbital System",
    )
    buttons: list[PanelButton] = []

    for index, (scene_id, label) in enumerate(
        zip(scene_ids, scene_labels, strict=True)
    ):
        buttons.append(
            PanelButton(
                button_id=f"scene:{scene_id}",
                label=label,
                rect=Rect(
                    inner_x,
                    scene_y + index * (button_height + 7),
                    inner_width,
                    button_height,
                ),
                selected=active_scene_id == scene_id,
            )
        )

    mode_y = viewport.y + 250
    small_gap = 10
    mode_gap = 8
    mode_button_width = max(
        1,
        (inner_width - 2 * mode_gap) // 3,
    )
    final_mode_button_width = max(
        1,
        inner_width - 2 * mode_button_width - 2 * mode_gap,
    )
    half_width = max(1, (inner_width - small_gap) // 2)
    buttons.extend(
        (
            PanelButton(
                button_id="mode:DEMO",
                label="Demo",
                rect=Rect(
                    inner_x,
                    mode_y,
                    mode_button_width,
                    button_height,
                ),
                selected=mode is DashboardMode.DEMO,
            ),
            PanelButton(
                button_id="mode:ANALYSIS",
                label="Analysis",
                rect=Rect(
                    inner_x + mode_button_width + mode_gap,
                    mode_y,
                    mode_button_width,
                    button_height,
                ),
                selected=mode is DashboardMode.ANALYSIS,
            ),
            PanelButton(
                button_id="mode:EVIDENCE",
                label="Evidence",
                rect=Rect(
                    inner_x + 2 * (mode_button_width + mode_gap),
                    mode_y,
                    final_mode_button_width,
                    button_height,
                ),
                selected=mode is DashboardMode.EVIDENCE,
            ),
        )
    )

    action_y = viewport.bottom - padding - button_height
    action_width = half_width
    buttons.extend(
        (
            PanelButton(
                button_id="reset",
                label="Reset scene",
                rect=Rect(
                    inner_x,
                    action_y,
                    action_width,
                    button_height,
                ),
            ),
            PanelButton(
                button_id="close",
                label="Close panel",
                rect=Rect(
                    inner_x + half_width + small_gap,
                    action_y,
                    inner_width - half_width - small_gap,
                    button_height,
                ),
            ),
        )
    )

    return SpatialPanelLayout(
        viewport=viewport,
        buttons=tuple(buttons),
    )


class InteractionRouter:
    """Route public InteractionState values to either scene or UI focus."""

    def __init__(self) -> None:
        self._open = False
        self._focus = InteractionFocus.SCENE_FOCUS
        self._armed = False
        self._previous_pinch = False
        self._require_scene_release = False
        self._layout_viewport: Rect | None = None
        self._cursor_xy: tuple[int, int] | None = None
        self._hovered_button: str | None = None
        self._pressed_button: str | None = None
        self._activated_button: str | None = None

    @property
    def is_open(self) -> bool:
        return self._open

    @property
    def focus(self) -> InteractionFocus:
        return self._focus

    def toggle(self) -> None:
        if self._open:
            self.close_panel()
        else:
            self.open_panel()

    def open_panel(self) -> None:
        self._open = True
        self._focus = InteractionFocus.UI_FOCUS
        self._require_scene_release = False
        self._reset_click_state(clear_cursor=True)
        self._layout_viewport = None

    def close_panel(self) -> None:
        self._open = False
        self._focus = InteractionFocus.SCENE_FOCUS
        self._require_scene_release = True
        self._reset_click_state(clear_cursor=True)
        self._layout_viewport = None

    def route(
        self,
        state: InteractionState,
        panel_layout: SpatialPanelLayout | None = None,
    ) -> InteractionRoute:
        self._activated_button = None
        if not self._open:
            if self._require_scene_release:
                if (
                    state.interaction_valid
                    and state.pinch_active is False
                ):
                    self._require_scene_release = False
                return InteractionRoute(
                    consumed=True,
                    forward_to_scene=False,
                )
            return InteractionRoute(
                consumed=False,
                forward_to_scene=True,
            )

        if panel_layout is None:
            raise ValueError(
                "UI focus requires a spatial panel layout"
            )

        if self._layout_viewport != panel_layout.viewport:
            self._reset_click_state(clear_cursor=True)
            self._layout_viewport = panel_layout.viewport

        if (
            not state.interaction_valid
            or not isinstance(state.pinch_active, bool)
        ):
            self._reset_click_state(clear_cursor=True)
            return InteractionRoute(
                consumed=True,
                forward_to_scene=False,
            )

        cursor = map_normalized_point_to_rect(
            state.pointer_xy,
            panel_layout.viewport,
            mirror_x=False,
            mirror_y=False,
        )
        if cursor is None:
            self._reset_click_state(clear_cursor=True)
            return InteractionRoute(
                consumed=True,
                forward_to_scene=False,
            )

        self._cursor_xy = cursor
        button = panel_layout.button_at(cursor)
        self._hovered_button = (
            None if button is None else button.button_id
        )

        if not state.pinch_active:
            self._armed = True
            self._previous_pinch = False
            self._pressed_button = None
            return InteractionRoute(
                consumed=True,
                forward_to_scene=False,
            )

        self._pressed_button = (
            None if button is None else button.button_id
        )
        rising_edge = not self._previous_pinch
        self._previous_pinch = True
        if (
            rising_edge
            and self._armed
            and button is not None
            and button.enabled
        ):
            self._armed = False
            self._activated_button = button.button_id
            return InteractionRoute(
                consumed=True,
                forward_to_scene=False,
                action=button.button_id,
            )

        return InteractionRoute(
            consumed=True,
            forward_to_scene=False,
        )

    def reset_after_action(self) -> None:
        """Clear stale hover/press and require a fresh valid release."""

        self._armed = False
        self._previous_pinch = True
        self._hovered_button = None
        self._pressed_button = None

    def view_state(
        self,
        *,
        active_scene_id: str | None,
        mode: DashboardMode,
    ) -> SpatialPanelViewState:
        return SpatialPanelViewState(
            open=self._open,
            focus=self._focus,
            cursor_xy=self._cursor_xy,
            hovered_button=self._hovered_button,
            pressed_button=self._pressed_button,
            activated_button=self._activated_button,
            active_scene_id=active_scene_id,
            mode=mode,
        )

    def _reset_click_state(
        self,
        *,
        clear_cursor: bool,
    ) -> None:
        self._armed = False
        self._previous_pinch = False
        self._hovered_button = None
        self._pressed_button = None
        self._activated_button = None
        if clear_cursor:
            self._cursor_xy = None

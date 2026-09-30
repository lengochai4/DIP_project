from __future__ import annotations

from dataclasses import replace

import cv2
import numpy as np
import pytest

from dip_touchless.core import InteractionState
from extensions.stem3d import (
    Stem3DApplicationController,
    Stem3DExtension,
    build_tier1_scene_registry,
)
from extensions.stem3d.ui import (
    ApplicationPhase,
    ApplicationState,
    DashboardMode,
    InteractionFocus,
    InteractionRouter,
    LiveDashboard,
    Rect,
    build_spatial_panel_layout,
    calculate_dashboard_layout,
    map_normalized_point_to_rect,
)


def _interaction(
    frame_id: int,
    *,
    pointer_xy: tuple[float, float] | None,
    pinch_active: bool,
    valid: bool = True,
    rotation_delta: tuple[float, float] = (0.02, -0.01),
    scale_delta: float = 0.03,
) -> InteractionState:
    return InteractionState(
        run_id="spatial-panel-test",
        frame_id=frame_id,
        timestamp_s=frame_id * 0.05,
        interaction_valid=valid,
        pointer_xy=pointer_xy,
        pinch_ratio=0.25 if pinch_active else 0.5,
        pinch_active=pinch_active,
        rotation_delta=rotation_delta,
        scale_delta=scale_delta,
    )


def _pointer_for_button(
    layout,
    button_id: str,
) -> tuple[float, float]:
    button = next(
        button
        for button in layout.buttons
        if button.button_id == button_id
    )
    x = button.rect.x + button.rect.width // 2
    y = button.rect.y + button.rect.height // 2
    return (
        (x - layout.viewport.x)
        / max(layout.viewport.width - 1, 1),
        (y - layout.viewport.y)
        / max(layout.viewport.height - 1, 1),
    )


def test_normalized_pointer_mapping_is_resize_safe_and_explicit() -> None:
    target = Rect(10, 20, 100, 50)

    assert map_normalized_point_to_rect(
        (0.0, 0.0),
        target,
    ) == (10, 20)
    assert map_normalized_point_to_rect(
        (1.0, 1.0),
        target,
    ) == (109, 69)
    assert map_normalized_point_to_rect(
        (0.25, 0.25),
        target,
        mirror_x=True,
    ) == (84, 32)
    assert map_normalized_point_to_rect(None, target) is None
    assert map_normalized_point_to_rect((-0.1, 0.5), target) is None
    assert map_normalized_point_to_rect((0.5, float("nan")), target) is None

    small = build_spatial_panel_layout(1024, 640)
    large = build_spatial_panel_layout(1600, 900)
    assert small.viewport != large.viewport
    for panel in (small, large):
        for button in panel.buttons:
            assert button.rect.x >= panel.viewport.x
            assert button.rect.y >= panel.viewport.y
            assert button.rect.right <= panel.viewport.right
            assert button.rect.bottom <= panel.viewport.bottom


def test_panel_hit_testing_edges_outside_and_disabled_controls() -> None:
    panel = build_spatial_panel_layout(1280, 720)
    button = next(
        item
        for item in panel.buttons
        if item.button_id == "scene:molecule"
    )
    rect = button.rect

    assert panel.hit_test((rect.x, rect.y)) == "scene:molecule"
    assert panel.hit_test(
        (rect.right - 1, rect.bottom - 1)
    ) == "scene:molecule"
    assert panel.hit_test((rect.right, rect.y)) is None
    assert panel.hit_test((rect.x, rect.bottom)) is None
    assert panel.hit_test((panel.viewport.x, panel.viewport.y)) is None
    assert panel.hit_test(None) is None

    disabled = replace(button, enabled=False)
    disabled_panel = replace(
        panel,
        buttons=tuple(
            disabled if item.button_id == button.button_id else item
            for item in panel.buttons
        ),
    )
    assert disabled_panel.button_at(
        (rect.x, rect.y)
    ) == disabled
    assert disabled_panel.hit_test((rect.x, rect.y)) is None

    pointer = (
        (rect.x + rect.width // 2 - panel.viewport.x)
        / (panel.viewport.width - 1),
        (rect.y + rect.height // 2 - panel.viewport.y)
        / (panel.viewport.height - 1),
    )
    router = InteractionRouter()
    router.open_panel()
    router.route(
        _interaction(0, pointer_xy=pointer, pinch_active=False),
        disabled_panel,
    )
    assert router.route(
        _interaction(1, pointer_xy=pointer, pinch_active=True),
        disabled_panel,
    ).action is None


def test_router_clicks_once_and_requires_release_between_clicks() -> None:
    panel = build_spatial_panel_layout(1280, 720)
    pointer = _pointer_for_button(panel, "reset")
    router = InteractionRouter()
    router.open_panel()

    assert router.focus is InteractionFocus.UI_FOCUS
    release = router.route(
        _interaction(0, pointer_xy=pointer, pinch_active=False),
        panel,
    )
    assert release.consumed is True
    assert release.forward_to_scene is False
    assert release.action is None

    first_pinch = router.route(
        _interaction(1, pointer_xy=pointer, pinch_active=True),
        panel,
    )
    assert first_pinch.action == "reset"

    held = router.route(
        _interaction(2, pointer_xy=pointer, pinch_active=True),
        panel,
    )
    assert held.action is None

    router.route(
        _interaction(3, pointer_xy=pointer, pinch_active=False),
        panel,
    )
    second_pinch = router.route(
        _interaction(4, pointer_xy=pointer, pinch_active=True),
        panel,
    )
    assert second_pinch.action == "reset"


def test_router_loss_reacquisition_and_unavailable_pointer_safety() -> None:
    panel = build_spatial_panel_layout(1280, 720)
    pointer = _pointer_for_button(panel, "scene:orbital-system")
    router = InteractionRouter()
    router.open_panel()

    router.route(
        _interaction(0, pointer_xy=pointer, pinch_active=False),
        panel,
    )
    invalid = router.route(
        _interaction(
            1,
            pointer_xy=pointer,
            pinch_active=True,
            valid=False,
        ),
        panel,
    )
    assert invalid.action is None
    assert router.view_state(
        active_scene_id=None,
        mode=DashboardMode.DEMO,
    ).cursor_xy is None

    reacquired_held = router.route(
        _interaction(2, pointer_xy=pointer, pinch_active=True),
        panel,
    )
    assert reacquired_held.action is None

    unavailable = router.route(
        _interaction(3, pointer_xy=None, pinch_active=False),
        panel,
    )
    assert unavailable.action is None
    assert router.view_state(
        active_scene_id=None,
        mode=DashboardMode.DEMO,
    ).hovered_button is None

    router.route(
        _interaction(4, pointer_xy=pointer, pinch_active=False),
        panel,
    )
    armed_click = router.route(
        _interaction(5, pointer_xy=pointer, pinch_active=True),
        panel,
    )
    assert armed_click.action == "scene:orbital-system"


def test_router_cancels_clicks_outside_controls_and_on_resize() -> None:
    first_layout = build_spatial_panel_layout(1024, 640)
    resized_layout = build_spatial_panel_layout(1600, 900)
    outside_control = (
        first_layout.viewport.x + 10,
        first_layout.viewport.y + 10,
    )
    pointer = (
        (outside_control[0] - first_layout.viewport.x)
        / (first_layout.viewport.width - 1),
        (outside_control[1] - first_layout.viewport.y)
        / (first_layout.viewport.height - 1),
    )

    router = InteractionRouter()
    router.open_panel()
    router.route(
        _interaction(0, pointer_xy=pointer, pinch_active=False),
        first_layout,
    )
    assert router.route(
        _interaction(1, pointer_xy=pointer, pinch_active=True),
        first_layout,
    ).action is None

    target = _pointer_for_button(
        resized_layout,
        "reset",
    )
    resized_held = router.route(
        _interaction(2, pointer_xy=target, pinch_active=True),
        resized_layout,
    )
    assert resized_held.action is None
    released = router.route(
        _interaction(3, pointer_xy=target, pinch_active=False),
        resized_layout,
    )
    assert released.action is None
    assert router.route(
        _interaction(4, pointer_xy=target, pinch_active=True),
        resized_layout,
    ).action == "reset"


class _Renderer:
    def __init__(self) -> None:
        self.rendered = []
        self.closed = False

    def open(self) -> None:
        pass

    def render(self, frame) -> None:
        self.rendered.append(frame)

    def close_requested(self) -> bool:
        return False

    def close(self) -> None:
        self.closed = True


def test_controller_routes_panel_actions_and_suppresses_scene_motion() -> None:
    renderer = _Renderer()
    extension = Stem3DExtension(
        scene_registry=build_tier1_scene_registry(
            initial_scale=1.0,
            min_scale=0.5,
            max_scale=2.0,
        ),
        renderer=renderer,
    )
    dashboard = LiveDashboard()
    controller = Stem3DApplicationController(
        run_id="spatial-panel-test",
        extension=extension,
        dashboard=dashboard,
    )

    controller.start()
    dashboard.handle_key(ord("a"))
    assert dashboard.mode is DashboardMode.ANALYSIS
    dashboard.handle_key(ord("d"))
    assert dashboard.mode is DashboardMode.DEMO
    controller.consume_interaction(
        _interaction(0, pointer_xy=(0.5, 0.5), pinch_active=False)
    )
    assert len(renderer.rendered) == 2

    dashboard.handle_key(ord("p"))
    assert dashboard.spatial_panel_state.open is True
    assert (
        dashboard.spatial_panel_state.focus
        is InteractionFocus.UI_FOCUS
    )

    panel = dashboard.spatial_panel_layout()
    molecule_pointer = _pointer_for_button(
        panel,
        "scene:molecule",
    )
    controller.consume_interaction(
        _interaction(1, pointer_xy=molecule_pointer, pinch_active=False)
    )
    assert (
        dashboard.spatial_panel_state.hovered_button
        == "scene:molecule"
    )
    before_select = len(renderer.rendered)
    controller.consume_interaction(
        _interaction(2, pointer_xy=molecule_pointer, pinch_active=True)
    )
    assert extension.active_scene_id == "molecule"
    assert len(renderer.rendered) == before_select + 1
    assert dashboard.spatial_panel_state.hovered_button is None
    assert dashboard.spatial_panel_state.pressed_button is None
    assert (
        dashboard.spatial_panel_state.activated_button
        == "scene:molecule"
    )

    held_count = len(renderer.rendered)
    controller.consume_interaction(
        _interaction(3, pointer_xy=molecule_pointer, pinch_active=True)
    )
    assert len(renderer.rendered) == held_count

    orbital_pointer = _pointer_for_button(
        dashboard.spatial_panel_layout(),
        "scene:orbital-system",
    )
    controller.consume_interaction(
        _interaction(4, pointer_xy=orbital_pointer, pinch_active=False)
    )
    controller.consume_interaction(
        _interaction(5, pointer_xy=orbital_pointer, pinch_active=True)
    )
    assert extension.active_scene_id == "orbital-system"

    geometry_pointer = _pointer_for_button(
        dashboard.spatial_panel_layout(),
        "scene:coordinate-geometry",
    )
    controller.consume_interaction(
        _interaction(6, pointer_xy=geometry_pointer, pinch_active=False)
    )
    controller.consume_interaction(
        _interaction(7, pointer_xy=geometry_pointer, pinch_active=True)
    )
    assert extension.active_scene_id == "coordinate-geometry"
    held_count = len(renderer.rendered)

    mode_pointer = _pointer_for_button(
        dashboard.spatial_panel_layout(),
        "mode:ANALYSIS",
    )
    controller.consume_interaction(
        _interaction(8, pointer_xy=mode_pointer, pinch_active=False)
    )
    controller.consume_interaction(
        _interaction(9, pointer_xy=mode_pointer, pinch_active=True)
    )
    assert dashboard.mode is DashboardMode.ANALYSIS
    assert len(renderer.rendered) == held_count

    reset_pointer = _pointer_for_button(
        dashboard.spatial_panel_layout(),
        "reset",
    )
    controller.consume_interaction(
        _interaction(10, pointer_xy=reset_pointer, pinch_active=False)
    )
    controller.consume_interaction(
        _interaction(11, pointer_xy=reset_pointer, pinch_active=True)
    )
    assert renderer.rendered[-1].transform.yaw_rad == pytest.approx(0.0)
    assert dashboard.spatial_panel_state.hovered_button is None
    assert dashboard.spatial_panel_state.pressed_button is None

    close_pointer = _pointer_for_button(
        dashboard.spatial_panel_layout(),
        "close",
    )
    controller.consume_interaction(
        _interaction(12, pointer_xy=close_pointer, pinch_active=False)
    )
    close_render_count = len(renderer.rendered)
    controller.consume_interaction(
        _interaction(13, pointer_xy=close_pointer, pinch_active=True)
    )
    assert dashboard.spatial_panel_state.open is False
    assert (
        dashboard.spatial_panel_state.focus
        is InteractionFocus.SCENE_FOCUS
    )
    assert dashboard.spatial_panel_state.hovered_button is None
    assert dashboard.spatial_panel_state.pressed_button is None
    controller.consume_interaction(
        _interaction(14, pointer_xy=close_pointer, pinch_active=True)
    )
    controller.consume_interaction(
        _interaction(15, pointer_xy=close_pointer, pinch_active=False)
    )
    assert len(renderer.rendered) == close_render_count

    controller.consume_interaction(
        _interaction(
            16,
            pointer_xy=close_pointer,
            pinch_active=False,
            rotation_delta=(0.12, 0.0),
        )
    )
    assert len(renderer.rendered) == close_render_count + 1
    dashboard.handle_key(ord("3"))
    assert extension.active_scene_id == "orbital-system"
    dashboard.handle_key(ord("1"))
    assert extension.active_scene_id == "coordinate-geometry"
    controller.close()
    assert renderer.closed is True


def test_dashboard_panel_toggle_button_uses_same_toggle_callback() -> None:
    dashboard = LiveDashboard()
    toggles = []
    dashboard.set_control_panel_toggle_action(
        lambda: toggles.append("toggle")
    )
    layout = calculate_dashboard_layout(1280, 720)
    dashboard._draw_footer(
        np.zeros(
            (layout.height, layout.width, 3),
            dtype=np.uint8,
        ),
        layout,
        ApplicationState(
            run_id="test",
            phase=ApplicationPhase.RUNNING,
        ),
        DashboardMode.DEMO,
    )
    rect = dashboard._control_panel_button
    dashboard.handle_mouse_event(
        rect.x,
        rect.y,
        cv2.EVENT_LBUTTONUP,
    )
    dashboard.handle_key(ord("p"))
    assert toggles == ["toggle", "toggle"]

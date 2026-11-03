from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import numpy as np
import pytest

from dip_touchless.core import InteractionState
from extensions.stem3d import (
    OpenGLStemRenderer,
    Stem3DApplicationController,
    Stem3DExtension,
    build_tier1_scene_registry,
)
from extensions.stem3d.application import RendererFailure
from extensions.stem3d.live_demo import (
    LiveComponentFailure,
    _GuardedCameraSource,
    _GuardedHandProvider,
)
from extensions.stem3d.ui import (
    ApplicationPhase,
    ApplicationState,
    DashboardMode,
    InteractionFocus,
    InteractionRouter,
    LiveDashboard,
    Rect,
    THEME,
    build_spatial_panel_layout,
    calculate_dashboard_layout,
)
from extensions.stem3d.ui.dashboard import (
    _tracking_badge_color,
)


class _Renderer:
    def __init__(
        self,
        *,
        fail_open: bool = False,
        fail_close: bool = False,
    ) -> None:
        self.fail_open = fail_open
        self.fail_close = fail_close
        self.opened = False
        self.close_count = 0
        self.frames = []
        self.key_consumer = None

    def open(self) -> None:
        if self.fail_open:
            raise RuntimeError("display initialization failed")
        self.opened = True

    def render(self, frame) -> None:
        self.frames.append(frame)

    def close_requested(self) -> bool:
        return False

    def close(self) -> None:
        self.close_count += 1
        self.opened = False
        if self.fail_close:
            raise RuntimeError("renderer cleanup failed")

    def set_key_consumer(self, consumer) -> None:
        self.key_consumer = consumer


class _Dashboard:
    def __init__(self) -> None:
        self.mode = DashboardMode.DEMO
        self.panel_state = None
        self.states = []
        self.closed = False
        self.key_events = []
        self.reset_action = None
        self.scene_action = None
        self.preset_action = None
        self.mode_action = None
        self.panel_action = None

    def set_reset_action(self, action) -> None:
        self.reset_action = action

    def set_scene_select_action(self, action) -> None:
        self.scene_action = action

    def set_molecule_preset_action(self, action) -> None:
        self.preset_action = action

    def set_mode_action(self, action) -> None:
        self.mode_action = action

    def set_control_panel_toggle_action(self, action) -> None:
        self.panel_action = action

    def set_spatial_panel_state(self, state) -> None:
        self.panel_state = state

    def set_mode_from_application(self, mode) -> None:
        self.mode = mode

    def spatial_panel_layout(self):
        return build_spatial_panel_layout(
            1280,
            720,
            active_scene_id=(
                None if self.panel_state is None
                else self.panel_state.active_scene_id
            ),
            mode=self.mode,
            interaction_available=(
                False if self.panel_state is None
                else self.panel_state.interaction_available
            ),
        )

    def handle_key(self, key: int) -> None:
        self.key_events.append(key)

    def show_application_state(self, state) -> bool:
        self.states.append(state)
        return True

    def wait_for_start(self, state) -> bool:
        return True

    def stop_requested(self) -> bool:
        return False

    def close(self) -> None:
        self.closed = True


def _interaction(
    frame_id: int,
    timestamp_s: float,
    *,
    valid: bool = True,
    pinch: bool = False,
) -> InteractionState:
    return InteractionState(
        run_id="u7-test",
        frame_id=frame_id,
        timestamp_s=timestamp_s,
        interaction_valid=valid,
        pointer_xy=(0.5, 0.5) if valid else None,
        pinch_ratio=0.25 if pinch else 0.5,
        pinch_active=pinch if valid else False,
        rotation_delta=(0.01, -0.01) if valid else (0.0, 0.0),
        scale_delta=0.02 if valid else 0.0,
    )


def _pointer_for_button(panel, button_id: str) -> tuple[float, float]:
    button = next(
        item for item in panel.buttons
        if item.button_id == button_id
    )
    x = button.rect.x + button.rect.width // 2
    y = button.rect.y + button.rect.height // 2
    return (
        (x - panel.viewport.x) / max(panel.viewport.width - 1, 1),
        (y - panel.viewport.y) / max(panel.viewport.height - 1, 1),
    )


def _controller(
    renderer: _Renderer,
) -> tuple[Stem3DApplicationController, _Dashboard, Stem3DExtension]:
    extension = Stem3DExtension(
        scene_registry=build_tier1_scene_registry(
            initial_scale=1.0,
            min_scale=0.5,
            max_scale=2.0,
        ),
        renderer=renderer,  # type: ignore[arg-type]
    )
    dashboard = _Dashboard()
    controller = Stem3DApplicationController(
        run_id="u7-test",
        extension=extension,
        dashboard=dashboard,  # type: ignore[arg-type]
    )
    return controller, dashboard, extension


def test_startup_state_advances_and_failure_components_are_distinct() -> None:
    renderer = _Renderer()
    controller, dashboard, _extension = _controller(renderer)

    controller.start()
    assert controller.state.phase is ApplicationPhase.STARTING
    assert controller.state.renderer_available is True
    assert dashboard.states[-1].status_message.startswith("Renderer ready")

    controller.report_startup_status("Opening camera")
    assert dashboard.states[-1].status_message == "Opening camera"

    controller.consume_interaction(_interaction(0, 0.0))
    assert controller.state.phase is ApplicationPhase.RUNNING
    assert controller.state.camera_available is True
    assert controller.state.provider_available is True

    controller.fail(RuntimeError("camera open failed"), component="camera")
    assert controller.state.phase is ApplicationPhase.ERROR
    assert controller.state.failure_component == "camera"
    assert controller.state.camera_available is False
    assert controller.state.status_message == "Camera unavailable"
    controller.close()
    controller.close()
    assert dashboard.closed is True
    assert renderer.close_count == 1


def test_renderer_initialization_failure_is_presented_and_released() -> None:
    renderer = _Renderer(fail_open=True)
    controller, dashboard, _extension = _controller(renderer)

    with pytest.raises(RendererFailure, match="display initialization failed"):
        controller.start()

    assert controller.state.phase is ApplicationPhase.ERROR
    assert controller.state.failure_component == "renderer"
    assert controller.state.renderer_available is False
    assert dashboard.states[-1].status_message == "3D renderer unavailable"
    assert renderer.close_count == 1
    controller.close()
    assert renderer.close_count == 1


def test_renderer_shutdown_failure_is_not_reported_as_clean_stop() -> None:
    renderer = _Renderer(fail_close=True)
    controller, dashboard, _extension = _controller(renderer)
    controller.start()
    controller.consume_interaction(_interaction(0, 0.0))

    with pytest.raises(RendererFailure, match="shutdown failed"):
        controller.close()

    assert controller.state.phase is ApplicationPhase.ERROR
    assert controller.state.failure_component == "renderer"
    assert controller.state.status_message == "3D renderer unavailable"
    assert dashboard.closed is True
    assert renderer.close_count == 1
    controller.close()
    assert renderer.close_count == 1


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("VALID", THEME.success),
        ("NO_HAND", THEME.warning),
        ("TEMPORARY_LOSS", THEME.warning),
        ("REACQUIRED", THEME.warning),
        ("INVALID", THEME.error),
    ],
)
def test_tracking_states_have_distinct_non_stale_badge_colors(
    status: str,
    expected: tuple[int, int, int],
) -> None:
    assert _tracking_badge_color(status) == expected


def test_disabled_spatial_controls_never_hover_or_activate() -> None:
    panel = build_spatial_panel_layout(
        1280,
        720,
        interaction_available=False,
    )
    router = InteractionRouter()
    router.open_panel()
    pointer = _pointer_for_button(panel, "scene:molecule")

    router.route(
        _interaction(0, 0.0, valid=True),
        panel,
    )
    route = router.route(
        _interaction(1, 0.05, valid=True, pinch=True),
        panel,
    )

    assert route.action is None
    state = router.view_state(
        active_scene_id=None,
        mode=DashboardMode.DEMO,
    )
    assert state.hovered_button is None
    assert state.pressed_button is None
    assert all(not button.enabled for button in panel.buttons)
    assert panel.hit_test(
        next(
            (button.rect.x + 1, button.rect.y + 1)
            for button in panel.buttons
            if button.button_id == "scene:molecule"
        )
    ) is None
    assert pointer is not None


def test_dashboard_keyboard_actions_are_gated_and_contextual() -> None:
    dashboard = LiveDashboard()
    actions = {"reset": 0, "panel": 0, "scene": [], "preset": [], "mode": []}
    dashboard.set_reset_action(lambda: actions.__setitem__("reset", actions["reset"] + 1))
    dashboard.set_control_panel_toggle_action(
        lambda: actions.__setitem__("panel", actions["panel"] + 1)
    )
    dashboard.set_scene_select_action(actions["scene"].append)
    dashboard.set_molecule_preset_action(actions["preset"].append)
    dashboard.set_mode_action(actions["mode"].append)

    dashboard._last_application_state = ApplicationState(
        run_id="u7-test",
        phase=ApplicationPhase.READY,
    )
    for key in ("r", "p", "2", "c"):
        dashboard.handle_key(ord(key))
    assert actions["reset"] == 0
    assert actions["panel"] == 0
    assert actions["scene"] == []
    assert actions["preset"] == []

    dashboard.handle_key(ord("e"))
    assert actions["mode"] == [DashboardMode.EVIDENCE]
    dashboard._last_application_state = ApplicationState(
        run_id="u7-test",
        phase=ApplicationPhase.RUNNING,
        active_scene="Coordinate Geometry",
    )
    dashboard.handle_key(ord("c"))
    dashboard.handle_key(ord("2"))
    assert actions["preset"] == []
    assert actions["scene"] == ["molecule"]
    dashboard.show_application_state(
        ApplicationState(
            run_id="u7-test",
            phase=ApplicationPhase.RUNNING,
            active_scene="Molecule",
        )
    )
    dashboard.handle_key(ord("h"))
    assert actions["preset"] == ["H2O"]


def test_application_error_screen_is_camera_free_and_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dashboard = LiveDashboard()
    shown_text: list[str] = []
    original_put_text = LiveDashboard._put_text

    def capture_text(cls, image, text, x, y, **kwargs):
        shown_text.append(text)
        original_put_text(image, text, x, y, **kwargs)

    monkeypatch.setattr(
        LiveDashboard,
        "_put_text",
        classmethod(capture_text),
    )
    screen = dashboard.build_application_state_screen(
        ApplicationState(
            run_id="u7-test",
            phase=ApplicationPhase.ERROR,
            camera_available=False,
            provider_available=True,
            renderer_available=True,
            status_message="Camera unavailable",
            failure_component="camera",
            error_message="failed to open camera index 9",
        ),
        width=1024,
        height=640,
    )

    assert screen.shape == (640, 1024, 3)
    assert "CAMERA UNAVAILABLE" in shown_text
    assert "Camera unavailable" in shown_text
    assert any("failed to open camera" in line for line in shown_text)
    assert "Q / ESC  Quit application" in shown_text
    assert not any(
        "Reset after startup" in line
        or "Control Space while running" in line
        for line in shown_text
    )
    assert not np.any(np.all(screen == (1, 255, 1), axis=2))


def test_dashboard_partial_open_is_cleaned_and_close_is_idempotent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"destroy": 0}
    monkeypatch.setattr("extensions.stem3d.ui.dashboard.cv2.namedWindow", lambda *a: None)

    def fail_resize(*_args) -> None:
        raise RuntimeError("resize failed")

    monkeypatch.setattr("extensions.stem3d.ui.dashboard.cv2.resizeWindow", fail_resize)
    monkeypatch.setattr(
        "extensions.stem3d.ui.dashboard.cv2.destroyWindow",
        lambda *_args: calls.__setitem__("destroy", calls["destroy"] + 1),
    )
    dashboard = LiveDashboard()

    with pytest.raises(RuntimeError, match="resize failed"):
        dashboard.open()
    dashboard.close()
    dashboard.close()

    assert dashboard._window_open is False
    assert calls["destroy"] == 1


@pytest.mark.parametrize("fail_in_init", [False, True])
def test_renderer_releases_partial_pygame_initialization(
    monkeypatch: pytest.MonkeyPatch,
    fail_in_init: bool,
) -> None:
    calls = {"init": 0, "quit": 0}
    pygame = ModuleType("pygame")
    pygame.DOUBLEBUF = 1
    pygame.OPENGL = 2

    def init() -> None:
        calls["init"] += 1
        if fail_in_init:
            raise RuntimeError("pygame initialization failed")

    def set_mode(*_args):
        raise RuntimeError("display initialization failed")

    pygame.init = init
    pygame.quit = lambda: calls.__setitem__("quit", calls["quit"] + 1)
    pygame.display = SimpleNamespace(set_mode=set_mode)
    open_gl = ModuleType("OpenGL")
    open_gl.GL = SimpleNamespace()
    open_gl.GLU = SimpleNamespace()
    monkeypatch.setitem(sys.modules, "pygame", pygame)
    monkeypatch.setitem(sys.modules, "OpenGL", open_gl)

    renderer = OpenGLStemRenderer(
        width=640,
        height=480,
        target_fps=30,
    )
    with pytest.raises(RuntimeError):
        renderer.open()
    renderer.close()

    assert calls["init"] == 1
    assert calls["quit"] == 1
    assert renderer.opened is False
    assert renderer._pygame is None


def test_renderer_forwards_keyboard_from_the_scene_window() -> None:
    events = [
        SimpleNamespace(type=1, key=ord("q"), unicode="q"),
        SimpleNamespace(type=1, key=ord("2"), unicode="2"),
    ]
    pygame = SimpleNamespace(
        KEYDOWN=1,
        QUIT=2,
        K_ESCAPE=27,
        event=SimpleNamespace(get=lambda: list(events)),
    )
    received: list[str] = []
    renderer = OpenGLStemRenderer(
        width=640,
        height=480,
        target_fps=30,
    )
    renderer._pygame = pygame
    renderer._opened = True
    renderer.set_key_consumer(received.append)

    assert renderer.close_requested() is False
    assert received == ["q", "2"]
    pygame.event.get = lambda: [
        SimpleNamespace(type=1, key=27, unicode="")
    ]
    assert renderer.close_requested() is True


def test_guarded_live_components_keep_failure_identity() -> None:
    class Camera:
        def open(self) -> None:
            raise RuntimeError("camera index unavailable")

        def read(self):
            raise AssertionError("read should not be reached")

        def close(self) -> None:
            pass

    class Provider:
        def process(self, _frame):
            raise RuntimeError("model execution failed")

        def close(self) -> None:
            pass

    with pytest.raises(LiveComponentFailure) as camera_error:
        _GuardedCameraSource(Camera()).open()  # type: ignore[arg-type]
    with pytest.raises(LiveComponentFailure) as provider_error:
        _GuardedHandProvider(Provider()).process(None)  # type: ignore[arg-type]

    assert camera_error.value.component == "camera"
    assert provider_error.value.component == "model/provider"


def test_repeated_scene_switches_keep_only_active_scene_running() -> None:
    renderer = _Renderer()
    registry = build_tier1_scene_registry(
        initial_scale=1.0,
        min_scale=0.5,
        max_scale=2.0,
    )
    extension = Stem3DExtension(
        scene_registry=registry,
        renderer=renderer,  # type: ignore[arg-type]
    )
    orbital = registry.get("orbital-system")
    extension.open()

    extension.activate_scene("orbital-system")
    extension.consume(_interaction(0, 0.0))
    extension.consume(_interaction(1, 0.1))
    phase_before_leave = orbital.phase_rad
    extension.activate_scene("coordinate-geometry")
    extension.consume(_interaction(2, 0.2))
    assert orbital.active is False
    assert orbital.phase_rad == pytest.approx(phase_before_leave)

    extension.activate_scene("molecule")
    extension.activate_scene("orbital-system")
    extension.consume(_interaction(3, 50.0))
    assert orbital.phase_rad == pytest.approx(phase_before_leave)
    extension.consume(_interaction(4, 50.1))
    assert orbital.phase_rad > phase_before_leave
    assert extension.active_scene_id == registry.active_scene_id
    assert registry.active_scene is orbital
    assert orbital.active is True
    extension.close()
    extension.close()
    assert orbital.active is False
    assert renderer.close_count == 1

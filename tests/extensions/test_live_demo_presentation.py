from datetime import datetime
from dataclasses import replace

import numpy as np
import pytest

from dip_touchless.core import (
    ColorSpace,
    CoordinateSpace,
    FilterDiagnostics,
    FilterMode,
    FramePacket,
    IlluminationMetrics,
    IlluminationState,
    InteractionState,
    Landmark,
    MeasurementQuality,
    ROI,
    ROIState,
    StageTimings,
    TrackingFrame,
    TrackingStatus,
)
from extensions.stem3d.live_demo import (
    LivePresentation,
    _new_live_demo_run_id,
)
from extensions.stem3d.ui import (
    ApplicationPhase,
    ApplicationState,
    DashboardMode,
    InteractionFocus,
    LiveDashboard,
    SpatialPanelViewState,
    THEME,
    build_presentation_state,
    build_runtime_identity,
    calculate_dashboard_layout,
    fit_aspect_rect,
    build_spatial_panel_layout,
)
from extensions.stem3d.ui.dashboard import (
    _ANALYSIS_PIPELINE_LINES,
    _frame_point_to_preview,
)


def _packet() -> FramePacket:
    return FramePacket(
        run_id="g7-demo-test",
        frame_id=7,
        timestamp_s=0.25,
        image=np.zeros(
            (120, 160, 3),
            dtype=np.uint8,
        ),
        color_space=ColorSpace.BGR,
        source_name="test-camera",
    )


def _tracking_frame() -> TrackingFrame:
    return TrackingFrame(
        run_id="g7-demo-test",
        frame_id=7,
        timestamp_s=0.25,
        status=TrackingStatus.VALID,
        raw_landmarks=(
            Landmark(
                index=8,
                x=0.25,
                y=0.25,
                z=-0.1,
                coordinate_space=(
                    CoordinateSpace.FRAME_NORMALIZED
                ),
            ),
        ),
        filtered_landmarks=(
            Landmark(
                index=8,
                x=0.5,
                y=0.5,
                z=-0.1,
                coordinate_space=(
                    CoordinateSpace.FRAME_NORMALIZED
                ),
            ),
        ),
        quality=(
            MeasurementQuality.unavailable()
        ),
        roi=ROI(
            x=20,
            y=25,
            width=80,
            height=70,
            state=ROIState.TRACKING,
        ),
        illumination=IlluminationMetrics(
            mean_v=100.0,
            std_v=20.0,
            p10_v=70.0,
            p90_v=135.0,
            robust_range_v=65.0,
            state=IlluminationState.NORMAL,
            enhancement_active=False,
        ),
        filter_diagnostics=FilterDiagnostics(
            mode=FilterMode.RAW,
            dt_s=None,
            speed=None,
            beta=None,
            min_cutoff_hz=None,
            final_cutoff_hz=None,
            signal_alpha=None,
            derivative_alpha=None,
            reset_occurred=False,
        ),
        timings=StageTimings(
            preprocess_ms=1.0,
            tracking_ms=2.0,
            filtering_ms=0.1,
            gesture_ms=0.2,
            compute_total_ms=3.3,
        ),
        events=(),
    )


def _interaction() -> InteractionState:
    return InteractionState(
        run_id="g7-demo-test",
        frame_id=7,
        timestamp_s=0.25,
        interaction_valid=True,
        pointer_xy=(0.5, 0.5),
        pinch_ratio=0.27,
        pinch_active=True,
        rotation_delta=(0.01, -0.02),
        scale_delta=0.03,
    )


def test_new_live_demo_run_id_uses_g8_prefix() -> None:
    assert _new_live_demo_run_id(
        datetime(2026, 9, 29, 21, 51, 52)
    ) == "g8-demo-20260929-215152"


def test_presentation_keyboard_controls() -> None:
    reset_count = 0

    def reset() -> None:
        nonlocal reset_count
        reset_count += 1

    presentation = LivePresentation(
        run_id="g7-demo-test",
        reset_action=reset,
    )

    assert (
        presentation.stop_requested()
        is False
    )

    presentation.handle_key(
        ord("r")
    )

    assert reset_count == 1
    assert (
        presentation.stop_requested()
        is False
    )

    presentation.handle_key(
        ord("q")
    )

    assert (
        presentation.stop_requested()
        is True
    )


def test_dashboard_uses_public_runtime_data_without_mutating_source() -> None:
    packet = _packet()

    presentation = LivePresentation(
        run_id="g7-demo-test",
        reset_action=lambda: None,
    )

    dashboard = (
        presentation.build_dashboard(
            packet,
            _tracking_frame(),
            _interaction(),
        )
    )

    assert dashboard.dtype == np.uint8

    assert dashboard.shape == (
        THEME.default_window_height,
        THEME.default_window_width,
        3,
    )

    assert np.all(
        packet.image == 0
    )

    assert not np.shares_memory(
        dashboard,
        packet.image,
    )


def test_presentation_adapter_returns_immutable_display_values() -> None:
    state = build_presentation_state(
        _packet(),
        _tracking_frame(),
        _interaction(),
    )

    assert state.run_id == "g7-demo-test"
    assert state.frame_id == 7
    assert state.tracking_status == "VALID"
    assert state.roi is not None
    assert state.roi.bounds_xywh == (20, 25, 80, 70)
    assert state.illumination is not None
    assert state.illumination.state == "NORMAL"
    assert state.filter.mode == "RAW"
    assert len(state.raw_landmarks) == 1
    assert len(state.filtered_landmarks) == 1
    assert state.raw_landmarks[0].coordinate_space == "FRAME_NORMALIZED"
    assert state.interaction.valid is True
    assert state.interaction.pointer_xy == (0.5, 0.5)
    with pytest.raises((AttributeError, TypeError)):
        state.frame_id = 8  # type: ignore[misc]


def test_presentation_adapter_rejects_mismatched_interaction() -> None:
    interaction = InteractionState(
        run_id="other-run",
        frame_id=7,
        timestamp_s=0.25,
        interaction_valid=False,
        pointer_xy=None,
        pinch_ratio=None,
        pinch_active=False,
        rotation_delta=(0.0, 0.0),
        scale_delta=0.0,
    )

    with pytest.raises(ValueError, match="identity must match"):
        build_presentation_state(
            _packet(),
            _tracking_frame(),
            interaction,
        )


@pytest.mark.parametrize(
    ("status", "expect_landmarks"),
    [
        (TrackingStatus.NO_HAND, False),
        (TrackingStatus.TEMPORARY_LOSS, False),
        (TrackingStatus.INVALID, False),
        (TrackingStatus.REACQUIRED, True),
    ],
)
def test_invalid_tracking_clears_stale_presentation_values(
    status: TrackingStatus,
    expect_landmarks: bool,
) -> None:
    tracking = replace(
        _tracking_frame(),
        status=status,
    )
    stale_interaction = replace(
        _interaction(),
        interaction_valid=False,
    )

    state = build_presentation_state(
        _packet(),
        tracking,
        stale_interaction,
    )

    assert bool(state.raw_landmarks) is expect_landmarks
    assert bool(state.filtered_landmarks) is expect_landmarks
    assert state.interaction.valid is False
    assert state.interaction.pointer_xy is None
    assert state.interaction.pinch_active is None
    assert state.interaction.pinch_ratio is None
    assert state.interaction.rotation_delta is None
    assert state.interaction.scale_delta is None


@pytest.mark.parametrize(
    ("width", "height"),
    [(1024, 640), (1280, 720), (1600, 900), (600, 400)],
)
def test_dashboard_layout_is_responsive_and_contained(
    width: int,
    height: int,
) -> None:
    layout = calculate_dashboard_layout(width, height)

    assert layout.width >= THEME.minimum_window_width
    assert layout.height >= THEME.minimum_window_height
    assert layout.header.x == THEME.margin
    assert layout.footer.bottom <= layout.height - THEME.margin
    assert layout.vision.right <= layout.scene.x
    assert layout.scene.bottom <= layout.pipeline.y
    assert layout.pipeline.bottom <= layout.interaction.y
    assert layout.interaction.bottom <= layout.footer.y

    preview = fit_aspect_rect(
        640,
        480,
        layout.vision_image,
    )
    assert preview.width <= layout.vision_image.width
    assert preview.height <= layout.vision_image.height
    assert preview.width / preview.height == pytest.approx(4 / 3, abs=0.01)


def test_dashboard_canvas_uses_requested_responsive_size() -> None:
    packet = _packet()
    state = build_presentation_state(
        packet,
        _tracking_frame(),
        _interaction(),
    )
    dashboard = LiveDashboard()
    application = ApplicationState(
        run_id=state.run_id,
        phase=ApplicationPhase.RUNNING,
    )

    canvas = dashboard.build_dashboard(
        packet.image,
        state,
        application,
        width=1600,
        height=900,
    )

    assert canvas.shape == (900, 1600, 3)


def test_dashboard_renders_screen_space_control_panel_at_responsive_sizes() -> None:
    packet = _packet()
    state = build_presentation_state(
        packet,
        _tracking_frame(),
        _interaction(),
    )
    dashboard = LiveDashboard()
    dashboard.set_spatial_panel_state(
        SpatialPanelViewState(
            open=True,
            focus=InteractionFocus.UI_FOCUS,
            cursor_xy=None,
            hovered_button="scene:molecule",
            pressed_button="scene:molecule",
            active_scene_id="molecule",
            mode=DashboardMode.DEMO,
        )
    )
    application = ApplicationState(
        run_id=state.run_id,
        phase=ApplicationPhase.RUNNING,
        active_scene="Molecule",
    )

    for width, height in ((1024, 640), (1600, 900)):
        canvas = dashboard.build_dashboard(
            packet.image,
            state,
            application,
            width=width,
            height=height,
        )
        panel = build_spatial_panel_layout(
            width,
            height,
            active_scene_id="molecule",
            mode=DashboardMode.DEMO,
        )
        assert canvas.shape == (height, width, 3)
        assert tuple(
            canvas[panel.viewport.y + 4, panel.viewport.x + 4]
        ) == (
            THEME.surface_raised
        )


def test_analysis_pipeline_labels_fit_minimum_dashboard_width() -> None:
    layout = calculate_dashboard_layout(
        THEME.minimum_window_width,
        THEME.minimum_window_height,
    )
    available_width = (
        layout.pipeline.width
        - 2 * THEME.card_padding
    )

    assert all(
        LiveDashboard._text_width(
            line,
            THEME.font_micro,
        )
        <= available_width
        for line in _ANALYSIS_PIPELINE_LINES
    )


def test_analysis_mode_explains_dip_and_preserves_camera_copy() -> None:
    packet = _packet()
    state = build_presentation_state(
        packet,
        _tracking_frame(),
        _interaction(),
    )
    identity = build_runtime_identity(
        {
            "spec_version": "canonical-v1.2",
            "code_revision": "0123456789abcdef",
            "log_schema_version": 1,
            "config_hash": "a" * 64,
            "python_version": "3.11.0",
            "dependency_versions": {
                "PyYAML": "6.0",
                "numpy": "2.0",
                "opencv-contrib-python": "4.14",
                "mediapipe": "1.0.1",
                "matplotlib": "3.9",
            },
            "provider": {
                "name": "mediapipe_hand_landmarker",
                "model_filename": "hand_landmarker.task",
                "model_checksum": "b" * 64,
            },
            "camera": {
                "backend": "default",
                "requested": {
                    "width": 640,
                    "height": 480,
                    "fps": 30.0,
                },
            },
        }
    )
    application = ApplicationState(
        run_id=state.run_id,
        phase=ApplicationPhase.RUNNING,
        runtime_identity=identity,
    )
    dashboard = LiveDashboard()

    dashboard.handle_key(ord("a"))
    analysis = dashboard.build_dashboard(
        packet.image,
        state,
        application,
    )
    assert dashboard.mode is DashboardMode.ANALYSIS

    dashboard.handle_key(ord("d"))
    demo = dashboard.build_dashboard(
        packet.image,
        state,
        application,
    )
    assert dashboard.mode is DashboardMode.DEMO
    assert not np.array_equal(analysis, demo)
    assert identity.code_revision == "0123456789abcdef"
    assert identity.config_sha256 == "a" * 64
    assert identity.model_sha256 == "b" * 64
    assert identity.dependency_versions[0] == ("PyYAML", "6.0")
    assert identity.camera_requested == "requested 640x480 @ 30 fps"
    assert np.all(packet.image == 0)

    layout = calculate_dashboard_layout(
        THEME.default_window_width,
        THEME.default_window_height,
    )
    preview = fit_aspect_rect(
        packet.image.shape[1],
        packet.image.shape[0],
        layout.vision_image,
    )
    assert _frame_point_to_preview(
        state.raw_landmarks[0],
        preview,
        image_width=packet.image.shape[1],
        image_height=packet.image.shape[0],
    ) == (
        preview.x + round(0.25 * (preview.width - 1)),
        preview.y + round(0.25 * (preview.height - 1)),
    )
    assert _frame_point_to_preview(
        type(state.raw_landmarks[0])(
            index=9,
            x=0.5,
            y=0.5,
            coordinate_space="NDC",
        ),
        preview,
        image_width=packet.image.shape[1],
        image_height=packet.image.shape[0],
    ) is None


class _ControllerDashboard:
    def __init__(self) -> None:
        self.reset_action = None
        self.scene_select_action = None
        self.molecule_preset_action = None
        self.mode_action = None
        self.control_panel_toggle_action = None
        self.panel_state = None
        self.started = True
        self.stop = False
        self.closed = False
        self.presentation = None
        self.mode = DashboardMode.DEMO

    def set_reset_action(self, action) -> None:
        self.reset_action = action

    def set_scene_select_action(self, action) -> None:
        self.scene_select_action = action

    def set_molecule_preset_action(self, action) -> None:
        self.molecule_preset_action = action

    def set_mode_action(self, action) -> None:
        self.mode_action = action

    def set_control_panel_toggle_action(self, action) -> None:
        self.control_panel_toggle_action = action

    def set_spatial_panel_state(self, state) -> None:
        self.panel_state = state

    def set_mode_from_application(self, mode) -> None:
        self.mode = mode

    def spatial_panel_layout(self):
        active_scene_id = (
            None
            if self.panel_state is None
            else self.panel_state.active_scene_id
        )
        return build_spatial_panel_layout(
            THEME.default_window_width,
            THEME.default_window_height,
            active_scene_id=active_scene_id,
            mode=self.mode,
        )

    def wait_for_start(self, state) -> bool:
        return self.started

    def stop_requested(self) -> bool:
        return self.stop

    def consume(self, image, presentation, application) -> None:
        self.presentation = (image, presentation, application)

    def close(self) -> None:
        self.closed = True


class _ControllerRenderer:
    def __init__(self) -> None:
        self.opened = False
        self.closed = False
        self.rendered = []

    def open(self) -> None:
        self.opened = True

    def render(self, frame) -> None:
        self.rendered.append(frame)

    def close_requested(self) -> bool:
        return False

    def close(self) -> None:
        self.closed = True


def test_application_controller_owns_lifecycle_reset_and_public_callbacks() -> None:
    from extensions.stem3d import (
        CoordinateCubeScene,
        SceneRegistry,
        Stem3DApplicationController,
        Stem3DExtension,
        Stem3DSceneState,
    )

    renderer = _ControllerRenderer()
    scene = CoordinateCubeScene(
        Stem3DSceneState(
            initial_scale=1.0,
            min_scale=0.5,
            max_scale=2.0,
        )
    )
    extension = Stem3DExtension(
        scene_registry=SceneRegistry(
            [scene],
            initial_scene_id=scene.id,
        ),
        renderer=renderer,
    )
    dashboard = _ControllerDashboard()
    controller = Stem3DApplicationController(
        run_id="g7-demo-test",
        extension=extension,
        dashboard=dashboard,  # type: ignore[arg-type]
        runtime_identity=build_runtime_identity(
            {
                "spec_version": "canonical-v1.2",
                "code_revision": "controller-test-revision",
            }
        ),
    )

    assert controller.wait_for_start() is True
    controller.start()
    controller.consume_interaction(_interaction())
    assert controller.state.phase is ApplicationPhase.RUNNING
    assert renderer.rendered[-1].transform.yaw_rad == pytest.approx(0.01)

    dashboard.reset_action()
    assert renderer.rendered[-1].transform.yaw_rad == 0.0
    assert renderer.rendered[-1].transform.scale == 1.0

    packet = _packet()
    controller.consume_presentation(
        packet,
        _tracking_frame(),
        _interaction(),
    )
    assert controller.latest_presentation is not None
    assert dashboard.presentation[0] is packet.image
    assert dashboard.presentation[2].camera_available is True
    assert (
        dashboard.presentation[2].runtime_identity.code_revision
        == "controller-test-revision"
    )

    dashboard.stop = True
    assert controller.stop_requested() is True
    assert controller.state.phase is ApplicationPhase.STOPPING
    controller.close()
    controller.close()
    assert controller.state.phase is ApplicationPhase.STOPPED
    assert dashboard.closed is True
    assert renderer.closed is True

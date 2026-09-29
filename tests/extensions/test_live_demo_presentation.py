import numpy as np

from dip_touchless.core import (
    ColorSpace,
    FilterDiagnostics,
    FilterMode,
    FramePacket,
    IlluminationMetrics,
    IlluminationState,
    InteractionState,
    MeasurementQuality,
    ROI,
    ROIState,
    StageTimings,
    TrackingFrame,
    TrackingStatus,
)
from extensions.stem3d.live_demo import (
    LivePresentation,
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
        raw_landmarks=(),
        filtered_landmarks=(),
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
        LivePresentation.MIN_DASHBOARD_HEIGHT,
        (
            packet.image.shape[1]
            + LivePresentation.SIDE_PANEL_WIDTH
        ),
        3,
    )

    assert np.all(
        packet.image == 0
    )

    assert not np.shares_memory(
        dashboard,
        packet.image,
    )

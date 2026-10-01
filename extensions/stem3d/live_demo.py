"""Compose the live webcam, DIP runtime, dashboard, and 3D extension."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from dip_touchless.capture import OpenCVCameraSource
from dip_touchless.configuration import resolve_config
from dip_touchless.core import (
    FramePacket,
    InteractionState,
    TrackingFrame,
)
from dip_touchless.filtering import RawLandmarkFilter
from dip_touchless.interaction import DeterministicGestureEngine
from dip_touchless.preprocessing import (
    AdaptivePreprocessor,
    IlluminationAnalyzer,
    IlluminationDecisionStabilizer,
    ROIManager,
)
from dip_touchless.runtime import RealtimeRuntime
from dip_touchless.telemetry import (
    FileRunLogger,
    build_run_metadata,
)
from dip_touchless.tracking import (
    MediaPipeHandLandmarkerProvider,
    MeasurementValidator,
)

from .application import Stem3DExtension
from .controller import Stem3DApplicationController
from .shell_renderer import ApplicationShellRenderer
from .ui.shell import ProductDashboard
from .scenes import build_tier1_scene_registry
from .ui import (
    ApplicationPhase,
    ApplicationState,
    LiveDashboard,
    THEME,
    build_runtime_identity,
    build_presentation_state,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "default.yaml"
MODEL_PATH = PROJECT_ROOT / "models" / "hand_landmarker.task"


class LiveComponentFailure(RuntimeError):
    """Identify a live-demo failure without changing Core diagnostics."""

    def __init__(self, component: str, message: str) -> None:
        super().__init__(message)
        self.component = component


class _GuardedCameraSource:
    def __init__(self, source: OpenCVCameraSource) -> None:
        self._source = source

    def open(self) -> None:
        try:
            self._source.open()
        except Exception as exc:
            raise LiveComponentFailure(
                "camera",
                f"Camera unavailable: {exc}",
            ) from exc

    def read(self):
        try:
            return self._source.read()
        except Exception as exc:
            raise LiveComponentFailure(
                "camera",
                f"Camera became unavailable: {exc}",
            ) from exc

    def close(self) -> None:
        self._source.close()


class _GuardedHandProvider:
    def __init__(self, provider: MediaPipeHandLandmarkerProvider) -> None:
        self._provider = provider

    def process(self, frame: FramePacket):
        try:
            return self._provider.process(frame)
        except Exception as exc:
            raise LiveComponentFailure(
                "model/provider",
                f"Hand model/provider failed while tracking: {exc}",
            ) from exc

    def close(self) -> None:
        self._provider.close()


def _new_live_demo_run_id(
    now: datetime | None = None,
) -> str:
    timestamp = datetime.now() if now is None else now
    return "g8-demo-" + timestamp.strftime("%Y%m%d-%H%M%S")


class LivePresentation(LiveDashboard):
    """Compatibility facade for the former public demo presentation API."""

    SIDE_PANEL_WIDTH = 460
    MIN_DASHBOARD_HEIGHT = THEME.minimum_window_height

    def __init__(
        self,
        *,
        run_id: str,
        reset_action: Callable[[], None],
    ) -> None:
        super().__init__(reset_action=reset_action)
        self._compat_state = ApplicationState(
            run_id=run_id,
            phase=ApplicationPhase.READY,
        )

    def wait_for_start(self) -> bool:
        return super().wait_for_start(self._compat_state)

    def build_dashboard(
        self,
        packet: FramePacket,
        tracking_frame: TrackingFrame,
        interaction_state: InteractionState | None,
    ):
        state = build_presentation_state(
            packet,
            tracking_frame,
            interaction_state,
        )
        application = ApplicationState(
            run_id=state.run_id,
            phase=ApplicationPhase.RUNNING,
            camera_available=True,
        )
        return super().build_dashboard(
            packet.image,
            state,
            application,
        )

    def consume(
        self,
        packet: FramePacket,
        tracking_frame: TrackingFrame,
        interaction_state: InteractionState | None,
    ) -> None:
        state = build_presentation_state(
            packet,
            tracking_frame,
            interaction_state,
        )
        application = ApplicationState(
            run_id=state.run_id,
            phase=ApplicationPhase.RUNNING,
            camera_available=True,
        )
        super().consume(
            packet.image,
            state,
            application,
        )


def _build_gesture_engine(
    gesture: Mapping[str, Any],
) -> DeterministicGestureEngine:
    return DeterministicGestureEngine(
        pointer_landmark_index=gesture["pointer_landmark_index"],
        pinch_thumb_landmark_index=(
            gesture["pinch_thumb_landmark_index"]
        ),
        pinch_index_landmark_index=(
            gesture["pinch_index_landmark_index"]
        ),
        hand_scale_landmark_a=gesture["hand_scale_landmark_a"],
        hand_scale_landmark_b=gesture["hand_scale_landmark_b"],
        hand_scale_epsilon=gesture["hand_scale_epsilon"],
        pinch_on=gesture["pinch_on"],
        pinch_off=gesture["pinch_off"],
        rotation_deadzone=gesture["rotation_deadzone"],
        rotation_gain=gesture["rotation_gain"],
        rotation_max_delta_rad=gesture["rotation_max_delta_rad"],
        scale_deadzone=gesture["scale_deadzone"],
        scale_gain=gesture["scale_gain"],
        scale_max_delta=gesture["scale_max_delta"],
    )


def _build_runtime(
    *,
    cfg: Mapping[str, Any],
    run_id: str,
    controller: Stem3DApplicationController,
) -> RealtimeRuntime:
    camera = cfg["camera"]
    roi = cfg["roi"]
    illumination = cfg["illumination"]
    clahe = cfg["clahe"]
    tracking = cfg["tracking"]
    gesture = cfg["gesture"]
    logging_cfg = cfg["logging"]

    try:
        provider = _GuardedHandProvider(
            MediaPipeHandLandmarkerProvider(
                model_path=tracking["model_path"],
                num_hands=tracking["num_hands"],
                min_hand_detection_confidence=(
                    tracking["min_hand_detection_confidence"]
                ),
                min_hand_presence_confidence=(
                    tracking["min_hand_presence_confidence"]
                ),
                min_tracking_confidence=(
                    tracking["min_tracking_confidence"]
                ),
            )
        )
    except Exception as exc:
        raise LiveComponentFailure(
            "model/provider",
            f"Hand model/provider could not initialize: {exc}",
        ) from exc

    source: _GuardedCameraSource | None = None
    logger: FileRunLogger | None = None
    try:
        source = _GuardedCameraSource(
            OpenCVCameraSource(
                run_id=run_id,
                camera_index=camera["index"],
                width=int(camera["width"]),
                height=int(camera["height"]),
                requested_fps=float(camera["requested_fps"]),
                backend=camera["backend"],
            )
        )
        logger = FileRunLogger(
            PROJECT_ROOT / logging_cfg["output_dir"]
        )
        return RealtimeRuntime(
            source=source,
            provider=provider,
            validator=MeasurementValidator(),
            landmark_filter=RawLandmarkFilter(),
            logger=logger,
            roi_manager=ROIManager(
                padding_ratio=roi["padding_ratio"],
                coast_expand_ratio=roi["coast_expand_ratio"],
                coast_frames=roi["coast_frames"],
                min_width=roi["min_width"],
                min_height=roi["min_height"],
            ),
            illumination_analyzer=IlluminationAnalyzer(),
            illumination_decision=IlluminationDecisionStabilizer(
                ema_alpha=illumination["ema_alpha"],
                low_light_enter_v=illumination["low_light_enter_v"],
                low_light_exit_v=illumination["low_light_exit_v"],
                low_contrast_enter_range_v=(
                    illumination["low_contrast_enter_range_v"]
                ),
                low_contrast_exit_range_v=(
                    illumination["low_contrast_exit_range_v"]
                ),
            ),
            adaptive_preprocessor=AdaptivePreprocessor(
                policy=clahe["policy"],
                clip_limit=clahe["clip_limit"],
                tile_grid_size=tuple(clahe["tile_grid_size"]),
            ),
            gesture_engine=_build_gesture_engine(gesture),
            interaction_consumer=controller.consume_interaction,
            presentation_consumer=controller.consume_presentation,
            stop_requested=controller.stop_requested,
        )
    except Exception as exc:
        for resource in (source, provider, logger):
            if resource is None:
                continue
            try:
                resource.close()
            except Exception as cleanup_error:
                exc.add_note(
                    f"partial runtime cleanup also failed: {cleanup_error}"
                )
        raise


def main() -> None:
    resolved = resolve_config(
        DEFAULT_CONFIG,
        overrides={
            "runtime": {
                "mode": "realtime",
                "replay_source": None,
            },
            "tracking": {"model_path": str(MODEL_PATH)},
            "filter": {"mode": "RAW"},
            "renderer": {
                "width": THEME.default_window_width,
                "height": THEME.default_window_height,
            },
        },
    )
    cfg = resolved.to_dict()
    renderer_cfg = cfg["renderer"]
    run_id = _new_live_demo_run_id()
    metadata = build_run_metadata(
        resolved,
        run_id=run_id,
    )

    scene_registry = build_tier1_scene_registry(
        initial_scale=renderer_cfg["initial_scale"],
        min_scale=renderer_cfg["min_scale"],
        max_scale=renderer_cfg["max_scale"],
    )

    renderer = ApplicationShellRenderer(
        width=int(renderer_cfg["width"]),
        height=int(renderer_cfg["height"]),
        target_fps=int(renderer_cfg["target_fps"]),
        title="DIP Touchless STEM",
    )
    extension = Stem3DExtension(
        scene_registry=scene_registry,
        renderer=renderer,
    )
    controller = Stem3DApplicationController(
        run_id=run_id,
        extension=extension,
        dashboard=ProductDashboard(window_host=renderer),
        runtime_identity=build_runtime_identity(metadata),
    )

    print("DIP Touchless STEM live demo.")
    print("Move index fingertip to rotate the active scene; pinch to scale.")
    print(
        "S/ENTER/SPACE starts; A/D/E selects modes; 1/2/3 selects scenes."
    )
    print(
        "P opens Control Space; H/C selects molecule presets only in Molecule; "
        "[ ] navigates Evidence; R resets; Q/ESC stops."
    )
    print(f"Run ID: {run_id}")

    failure: Exception | None = None
    try:
        if not controller.wait_for_start():
            print("Live demo cancelled before processing started.")
            return

        controller.start()
        controller.report_startup_status(
            "Initializing hand model and provider"
        )
        runtime = _build_runtime(
            cfg=cfg,
            run_id=run_id,
            controller=controller,
        )
        controller.report_startup_status(
            "Opening camera and waiting for the first frame"
        )
        processed = runtime.run(
            metadata=metadata,
            resolved_config=cfg,
        )
        print(f"Processed frames: {processed}")
    except Exception as exc:
        failure = exc
        component = getattr(exc, "component", None)
        if component is None and controller.state.phase is ApplicationPhase.ERROR:
            component = controller.state.failure_component
        controller.fail(
            exc,
            component=(
                component
                or (
                    "dashboard"
                    if controller.state.phase is ApplicationPhase.READY
                    else "runtime"
                )
            ),
        )
        print(
            f"{controller.state.status_message}: {exc}"
        )
        controller.wait_for_failure_dismiss()
    finally:
        try:
            controller.close()
        except Exception as close_error:
            failure = failure or close_error
            print(f"Shutdown cleanup error: {close_error}")

    if failure is None:
        print("Live demo closed cleanly.")
    else:
        print("Live demo closed after the reported failure.")


if __name__ == "__main__":
    main()

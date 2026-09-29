"""Live webcam → Core → InteractionState → STEM 3D demo."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import cv2
import numpy as np

from dip_touchless.capture import OpenCVCameraSource
from dip_touchless.core import (
    FramePacket,
    InteractionState,
    TrackingFrame,
)
from dip_touchless.configuration import resolve_config
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
from .renderer import OpenGLStemRenderer
from .scene_state import Stem3DSceneState


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CONFIG = PROJECT_ROOT / "config" / "default.yaml"

MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "hand_landmarker.task"
)


class LivePresentation:
    """OpenCV camera/status dashboard for the final live demo."""

    WINDOW_NAME = "DIP Touchless STEM - Camera / Status"
    SIDE_PANEL_WIDTH = 460
    MIN_DASHBOARD_HEIGHT = 640

    def __init__(
        self,
        *,
        run_id: str,
        reset_action: Callable[[], None],
    ) -> None:
        self._run_id = run_id
        self._reset_action = reset_action
        self._stop = False
        self._window_open = False

    def stop_requested(self) -> bool:
        """Whether the presentation window requested shutdown."""

        return self._stop

    def wait_for_start(self) -> bool:
        """Show an explicit start screen.

        Returns True when processing should start.
        Returns False when the user cancels.
        """

        cv2.namedWindow(
            self.WINDOW_NAME,
            cv2.WINDOW_NORMAL,
        )
        self._window_open = True

        canvas = np.zeros(
            (440, 820, 3),
            dtype=np.uint8,
        )

        while not self._stop:
            display = canvas.copy()

            self._put_text(
                display,
                "DIP Touchless STEM - Final Demo",
                36,
                48,
                scale=0.85,
            )

            self._put_text(
                display,
                f"Run ID: {self._run_id}",
                36,
                92,
            )

            self._put_text(
                display,
                "S / ENTER / SPACE : Start",
                36,
                168,
                scale=0.65,
            )

            self._put_text(
                display,
                "R : Reset 3D transform during demo",
                36,
                210,
                scale=0.65,
            )

            self._put_text(
                display,
                "Q / ESC : Stop",
                36,
                252,
                scale=0.65,
            )

            self._put_text(
                display,
                "3D window: move fingertip to rotate;",
                36,
                330,
            )

            self._put_text(
                display,
                "pinch and vary pinch distance to scale.",
                36,
                360,
            )

            cv2.imshow(
                self.WINDOW_NAME,
                display,
            )

            key = cv2.waitKey(30) & 0xFF

            if key in {
                ord("s"),
                ord("S"),
                13,
                32,
            }:
                return True

            self.handle_key(key)

            if self._window_closed():
                self._stop = True

        return False

    def consume(
        self,
        packet: FramePacket,
        tracking_frame: TrackingFrame,
        interaction_state: InteractionState | None,
    ) -> None:
        """Render one presentation frame.

        The supplied FramePacket is already a presentation-safe image
        copy created by RealtimeRuntime.
        """

        dashboard = self.build_dashboard(
            packet,
            tracking_frame,
            interaction_state,
        )

        cv2.imshow(
            self.WINDOW_NAME,
            dashboard,
        )

        key = cv2.waitKey(1) & 0xFF
        self.handle_key(key)

        if self._window_closed():
            self._stop = True

    def handle_key(
        self,
        key: int,
    ) -> None:
        """Handle presentation controls without changing Core state."""

        if key in {
            ord("q"),
            ord("Q"),
            27,
        }:
            self._stop = True
            return

        if key in {
            ord("r"),
            ord("R"),
        }:
            self._reset_action()

    def build_dashboard(
        self,
        packet: FramePacket,
        tracking_frame: TrackingFrame,
        interaction_state: InteractionState | None,
    ) -> np.ndarray:
        """Build a dashboard using public runtime contracts only."""

        frame = packet.image.copy()

        if (
            frame.ndim != 3
            or frame.shape[2] != 3
        ):
            raise ValueError(
                "presentation requires HxWx3 BGR image"
            )

        frame_height, frame_width = (
            frame.shape[:2]
        )

        roi = tracking_frame.roi

        if roi is not None:
            cv2.rectangle(
                frame,
                (roi.x, roi.y),
                (
                    roi.x + roi.width - 1,
                    roi.y + roi.height - 1,
                ),
                (0, 255, 255),
                2,
            )

        if (
            interaction_state is not None
            and interaction_state.pointer_xy
            is not None
        ):
            pointer_x, pointer_y = (
                interaction_state.pointer_xy
            )

            px = int(
                round(
                    pointer_x
                    * max(frame_width - 1, 0)
                )
            )

            py = int(
                round(
                    pointer_y
                    * max(frame_height - 1, 0)
                )
            )

            px = max(
                0,
                min(px, frame_width - 1),
            )

            py = max(
                0,
                min(py, frame_height - 1),
            )

            cv2.circle(
                frame,
                (px, py),
                7,
                (0, 255, 0),
                2,
            )

        dashboard_height = max(
            frame_height,
            self.MIN_DASHBOARD_HEIGHT,
        )

        dashboard = np.zeros(
            (
                dashboard_height,
                frame_width
                + self.SIDE_PANEL_WIDTH,
                3,
            ),
            dtype=np.uint8,
        )

        dashboard[
            :frame_height,
            :frame_width,
        ] = frame

        panel_x = frame_width + 18
        y = 28

        def line(
            label: str,
            value: str,
        ) -> None:
            nonlocal y

            self._put_text(
                dashboard,
                f"{label}: {value}",
                panel_x,
                y,
            )

            y += 23

        self._put_text(
            dashboard,
            "LIVE STATUS",
            panel_x,
            y,
            scale=0.68,
        )
        y += 32

        line(
            "Run",
            self._run_id,
        )

        line(
            "Frame",
            str(tracking_frame.frame_id),
        )

        line(
            "Tracking",
            tracking_frame.status.value,
        )

        if roi is None:
            line(
                "ROI",
                "n/a",
            )
        else:
            line(
                "ROI",
                (
                    f"{roi.state.value} "
                    f"x={roi.x} y={roi.y} "
                    f"{roi.width}x{roi.height}"
                ),
            )

        illumination = (
            tracking_frame.illumination
        )

        if illumination is None:
            line(
                "Illumination",
                "n/a",
            )
            line(
                "CLAHE active",
                "n/a",
            )
            line(
                "Mean V",
                "n/a",
            )
            line(
                "Robust V range",
                "n/a",
            )
        else:
            line(
                "Illumination",
                illumination.state.value,
            )

            line(
                "CLAHE active",
                str(
                    illumination
                    .enhancement_active
                ),
            )

            line(
                "Mean V",
                self._format_optional(
                    illumination.mean_v
                ),
            )

            line(
                "Robust V range",
                self._format_optional(
                    illumination
                    .robust_range_v
                ),
            )

        diagnostics = (
            tracking_frame
            .filter_diagnostics
        )

        line(
            "Filter",
            diagnostics.mode.value,
        )

        line(
            "dt (s)",
            self._format_optional(
                diagnostics.dt_s
            ),
        )

        line(
            "Speed",
            self._format_optional(
                diagnostics.speed
            ),
        )

        line(
            "Beta",
            self._format_optional(
                diagnostics.beta
            ),
        )

        line(
            "Cutoff (Hz)",
            self._format_optional(
                diagnostics
                .final_cutoff_hz
            ),
        )

        line(
            "Compute (ms)",
            self._format_optional(
                tracking_frame
                .timings
                .compute_total_ms
            ),
        )

        if interaction_state is None:
            line(
                "Interaction",
                "n/a",
            )
            line(
                "Pinch active",
                "n/a",
            )
            line(
                "Pinch ratio",
                "n/a",
            )
            line(
                "Rotation d",
                "n/a",
            )
            line(
                "Scale d",
                "n/a",
            )
        else:
            line(
                "Interaction",
                (
                    "VALID"
                    if (
                        interaction_state
                        .interaction_valid
                    )
                    else "NEUTRAL"
                ),
            )

            line(
                "Pinch active",
                str(
                    interaction_state
                    .pinch_active
                ),
            )

            line(
                "Pinch ratio",
                self._format_optional(
                    interaction_state
                    .pinch_ratio
                ),
            )

            yaw_delta, pitch_delta = (
                interaction_state
                .rotation_delta
            )

            line(
                "Rotation d",
                (
                    f"{yaw_delta:.4f}, "
                    f"{pitch_delta:.4f}"
                ),
            )

            line(
                "Scale d",
                (
                    f"{interaction_state.scale_delta:.4f}"
                ),
            )

        y += 10

        self._put_text(
            dashboard,
            "CONTROLS",
            panel_x,
            y,
            scale=0.62,
        )
        y += 28

        line(
            "R",
            "reset 3D transform",
        )

        line(
            "Q / ESC",
            "stop demo",
        )

        line(
            "3D window ESC",
            "stop demo",
        )

        return dashboard

    def close(self) -> None:
        """Release presentation-window resources."""

        if not self._window_open:
            return

        try:
            cv2.destroyWindow(
                self.WINDOW_NAME
            )
        except cv2.error:
            pass

        self._window_open = False

    def _window_closed(self) -> bool:
        if not self._window_open:
            return False

        try:
            return (
                cv2.getWindowProperty(
                    self.WINDOW_NAME,
                    cv2.WND_PROP_VISIBLE,
                )
                < 1.0
            )
        except cv2.error:
            return True

    @staticmethod
    def _format_optional(
        value: float | None,
    ) -> str:
        if value is None:
            return "n/a"

        return f"{value:.3f}"

    @staticmethod
    def _put_text(
        image: np.ndarray,
        text: str,
        x: int,
        y: int,
        *,
        scale: float = 0.48,
    ) -> None:
        cv2.putText(
            image,
            text,
            (x, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            (230, 230, 230),
            1,
            cv2.LINE_AA,
        )


def _build_gesture_engine(
    gesture: Mapping[str, Any],
) -> DeterministicGestureEngine:
    return DeterministicGestureEngine(
        pointer_landmark_index=(
            gesture["pointer_landmark_index"]
        ),
        pinch_thumb_landmark_index=(
            gesture["pinch_thumb_landmark_index"]
        ),
        pinch_index_landmark_index=(
            gesture["pinch_index_landmark_index"]
        ),
        hand_scale_landmark_a=(
            gesture["hand_scale_landmark_a"]
        ),
        hand_scale_landmark_b=(
            gesture["hand_scale_landmark_b"]
        ),
        hand_scale_epsilon=(
            gesture["hand_scale_epsilon"]
        ),
        pinch_on=gesture["pinch_on"],
        pinch_off=gesture["pinch_off"],
        rotation_deadzone=(
            gesture["rotation_deadzone"]
        ),
        rotation_gain=gesture["rotation_gain"],
        rotation_max_delta_rad=(
            gesture["rotation_max_delta_rad"]
        ),
        scale_deadzone=gesture["scale_deadzone"],
        scale_gain=gesture["scale_gain"],
        scale_max_delta=gesture["scale_max_delta"],
    )


def main() -> None:
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"MediaPipe model missing: {MODEL_PATH}"
        )

    resolved = resolve_config(
        DEFAULT_CONFIG,
        overrides={
            "runtime": {
                "mode": "realtime",
                "replay_source": None,
            },
            "tracking": {
                "model_path": str(MODEL_PATH),
            },
            "filter": {
                "mode": "RAW",
            },
        },
    )

    cfg = resolved.to_dict()

    camera = cfg["camera"]
    roi = cfg["roi"]
    illumination = cfg["illumination"]
    clahe = cfg["clahe"]
    tracking = cfg["tracking"]
    gesture = cfg["gesture"]
    renderer_cfg = cfg["renderer"]
    logging_cfg = cfg["logging"]

    run_id = (
        "g7-demo-"
        + datetime.now().strftime("%Y%m%d-%H%M%S")
    )

    scene_state = Stem3DSceneState(
        initial_scale=renderer_cfg["initial_scale"],
        min_scale=renderer_cfg["min_scale"],
        max_scale=renderer_cfg["max_scale"],
    )

    extension = Stem3DExtension(
        scene_state=scene_state,
        renderer=OpenGLStemRenderer(
            width=int(renderer_cfg["width"]),
            height=int(renderer_cfg["height"]),
            target_fps=int(renderer_cfg["target_fps"]),
            title="DIP Touchless STEM - Final Demo",
        ),
    )

    presentation = LivePresentation(
        run_id=run_id,
        reset_action=scene_state.reset,
    )

    print("DIP Touchless STEM final demo.")
    print("Move index fingertip to rotate.")
    print("Pinch and vary pinch distance to scale.")
    print("Remove/re-enter hand to test safe reacquisition.")
    print("Presentation controls: S=start, R=reset, Q/ESC=stop.")
    print("The existing live demo filter mode remains RAW.")
    print(f"Run ID: {run_id}")

    if not presentation.wait_for_start():
        presentation.close()
        print("Final demo cancelled before processing started.")
        return

    try:
        extension.open()

        provider = MediaPipeHandLandmarkerProvider(
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

        metadata = build_run_metadata(
            resolved,
            run_id=run_id,
        )

        runtime = RealtimeRuntime(
            source=OpenCVCameraSource(
                run_id=run_id,
                camera_index=camera["index"],
                width=int(camera["width"]),
                height=int(camera["height"]),
                requested_fps=float(
                    camera["requested_fps"]
                ),
                backend=camera["backend"],
            ),
            provider=provider,
            validator=MeasurementValidator(),
            landmark_filter=RawLandmarkFilter(),
            logger=FileRunLogger(
                PROJECT_ROOT / logging_cfg["output_dir"]
            ),
            roi_manager=ROIManager(
                padding_ratio=roi["padding_ratio"],
                coast_expand_ratio=roi["coast_expand_ratio"],
                coast_frames=roi["coast_frames"],
                min_width=roi["min_width"],
                min_height=roi["min_height"],
            ),
            illumination_analyzer=IlluminationAnalyzer(),
            illumination_decision=(
                IlluminationDecisionStabilizer(
                    ema_alpha=illumination["ema_alpha"],
                    low_light_enter_v=(
                        illumination["low_light_enter_v"]
                    ),
                    low_light_exit_v=(
                        illumination["low_light_exit_v"]
                    ),
                    low_contrast_enter_range_v=(
                        illumination[
                            "low_contrast_enter_range_v"
                        ]
                    ),
                    low_contrast_exit_range_v=(
                        illumination[
                            "low_contrast_exit_range_v"
                        ]
                    ),
                )
            ),
            adaptive_preprocessor=AdaptivePreprocessor(
                policy=clahe["policy"],
                clip_limit=clahe["clip_limit"],
                tile_grid_size=tuple(
                    clahe["tile_grid_size"]
                ),
            ),
            gesture_engine=_build_gesture_engine(gesture),
            interaction_consumer=extension.consume,
            presentation_consumer=presentation.consume,
            stop_requested=lambda: (
                presentation.stop_requested()
                or extension.close_requested()
            ),
        )

        processed = runtime.run(
            metadata=metadata,
            resolved_config=cfg,
        )

        print(f"Processed frames: {processed}")

    finally:
        presentation.close()
        extension.close()

    print("Final demo closed cleanly.")


if __name__ == "__main__":
    main()

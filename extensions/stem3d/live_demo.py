"""Live webcam → Core → InteractionState → STEM 3D demo."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from dip_touchless.capture import OpenCVCameraSource
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
        "g5-live-"
        + datetime.now().strftime("%Y%m%d-%H%M%S")
    )

    extension = Stem3DExtension(
        scene_state=Stem3DSceneState(
            initial_scale=renderer_cfg["initial_scale"],
            min_scale=renderer_cfg["min_scale"],
            max_scale=renderer_cfg["max_scale"],
        ),
        renderer=OpenGLStemRenderer(
            width=int(renderer_cfg["width"]),
            height=int(renderer_cfg["height"]),
            target_fps=int(renderer_cfg["target_fps"]),
            title="DIP Touchless STEM - Live G5 Demo",
        ),
    )

    print("Starting live touchless STEM demo.")
    print("Move index fingertip to rotate.")
    print("Pinch and vary pinch distance to scale.")
    print("Remove/re-enter hand to test safe reacquisition.")
    print("Press ESC or close the 3D window to stop.")
    print(f"Run ID: {run_id}")

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
            stop_requested=extension.close_requested,
        )

        processed = runtime.run(
            metadata=metadata,
            resolved_config=cfg,
        )

        print(f"Processed frames: {processed}")

    finally:
        extension.close()

    print("Live demo closed cleanly.")


if __name__ == "__main__":
    main()

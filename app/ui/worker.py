"""VisionWorker thread running the real DIP Core pipeline and MediaPipe Hand Landmarker."""

from __future__ import annotations

import math
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

from dip_touchless.capture import OpenCVCameraSource
from dip_touchless.core import (
    ColorSpace,
    FramePacket,
    InteractionState,
    TrackingFrame,
    TrackingStatus,
)
from dip_touchless.filtering import (
    AdaptiveOneEuroLandmarkFilter,
    FixedOneEuroLandmarkFilter,
    RawLandmarkFilter,
)
from dip_touchless.interaction import DeterministicGestureEngine
from dip_touchless.preprocessing import (
    AdaptivePreprocessor,
    IlluminationAnalyzer,
    IlluminationDecisionStabilizer,
    ROIManager,
)
from dip_touchless.runtime import RealtimeRuntime
from dip_touchless.tracking import (
    MediaPipeHandLandmarkerProvider,
    MeasurementValidator,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "models" / "hand_landmarker.task"


class NullRunLogger:
    """Non-disk logger for ultra-fast, zero-overhead GUI presentation."""

    def start_run(self, metadata: Any, resolved_config: Any) -> None:
        pass

    def log_tracking_frame(self, frame: Any) -> None:
        pass

    def log_interaction_state(self, state: Any) -> None:
        pass

    def log_event(self, event: Any) -> None:
        pass

    def close(self) -> None:
        pass


class VisionWorker(QThread):
    """Background worker executing the complete DIP processing pipeline at 30-60 FPS."""

    frame_ready = Signal(object, object, object)  # (bgr_frame, tracking_frame, interaction_state)
    error_occurred = Signal(str)
    status_changed = Signal(str)

    def __init__(
        self,
        *,
        camera_index: int = 0,
        filter_mode: str = "adaptive",
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self.camera_index = camera_index
        self.filter_mode = filter_mode
        self._stop_requested = False
        self._runtime: RealtimeRuntime | None = None

    def request_stop(self) -> None:
        """Signal thread to stop cleanly."""
        self._stop_requested = True

    def set_filter_mode(self, mode: str) -> None:
        """Update filter mode on next restart."""
        self.filter_mode = mode

    def run(self) -> None:
        """Main execution loop running the DIP pipeline."""
        if not MODEL_PATH.is_file():
            self.error_occurred.emit(f"Không tìm thấy model MediaPipe tại: {MODEL_PATH}")
            return

        run_id = f"gui-run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        try:
            self.status_changed.emit("Khởi tạo camera và MediaPipe...")

            # 1. External MediaPipe Landmark Provider
            provider = MediaPipeHandLandmarkerProvider(
                model_path=str(MODEL_PATH),
                num_hands=1,
                min_hand_detection_confidence=0.5,
                min_hand_presence_confidence=0.5,
                min_tracking_confidence=0.5,
            )

            # 2. Measurement Validator
            validator = MeasurementValidator()

            # 3. Temporal Filter Selection
            landmark_filter = self._create_filter(self.filter_mode)

            # 4. ROI Manager
            roi_manager = ROIManager(
                padding_ratio=0.20,
                coast_expand_ratio=0.15,
                coast_frames=5,
                min_width=1,
                min_height=1,
            )

            # 5. Illumination Analyzer & Stabilizer
            illum_analyzer = IlluminationAnalyzer()
            illum_decision = IlluminationDecisionStabilizer(
                ema_alpha=0.20,
                low_light_enter_v=70.0,
                low_light_exit_v=85.0,
                low_contrast_enter_range_v=35.0,
                low_contrast_exit_range_v=45.0,
            )

            # 6. Adaptive Preprocessor (CLAHE)
            preprocessor = AdaptivePreprocessor(
                policy="adaptive",
                clip_limit=2.0,
                tile_grid_size=(8, 8),
            )

            # 7. Gesture Engine
            gesture_engine = DeterministicGestureEngine(
                pointer_landmark_index=8,
                pinch_thumb_landmark_index=4,
                pinch_index_landmark_index=8,
                hand_scale_landmark_a=5,
                hand_scale_landmark_b=17,
                hand_scale_epsilon=1e-6,
                pinch_on=0.32,
                pinch_off=0.42,
                rotation_deadzone=0.005,
                rotation_gain=2.5,
                rotation_max_delta_rad=0.12,
                scale_deadzone=0.01,
                scale_gain=1.2,
                scale_max_delta=0.12,
            )

            # 8. Camera Source
            source = OpenCVCameraSource(
                run_id=run_id,
                camera_index=self.camera_index,
                width=640,
                height=480,
                requested_fps=30.0,
            )

            # 9. Assembly in RealtimeRuntime
            self._runtime = RealtimeRuntime(
                source=source,
                provider=provider,
                validator=validator,
                landmark_filter=landmark_filter,
                logger=NullRunLogger(),
                roi_manager=roi_manager,
                illumination_analyzer=illum_analyzer,
                illumination_decision=illum_decision,
                adaptive_preprocessor=preprocessor,
                gesture_engine=gesture_engine,
                presentation_consumer=self._on_presentation_frame,
                stop_requested=lambda: self._stop_requested,
            )

            self.status_changed.emit("Hệ thống nhận diện cử chỉ đang hoạt động.")
            self._runtime.run(
                metadata={"run_id": run_id, "mode": "realtime_gui"},
                resolved_config={},
            )

        except Exception as exc:
            self.error_occurred.emit(f"Lỗi VisionWorker: {exc}")
        finally:
            self.status_changed.emit("Camera đã dừng.")

    def _create_filter(self, mode: str):
        if mode == "fixed":
            return FixedOneEuroLandmarkFilter(
                min_cutoff_hz=1.0,
                beta=0.005,
                derivative_cutoff_hz=1.0,
                reset_gap_s=0.50,
            )
        elif mode == "raw":
            return RawLandmarkFilter()
        else:
            # Default: Bounded Adaptive 1-Euro
            return AdaptiveOneEuroLandmarkFilter(
                base_cutoff_hz=1.0,
                beta_min=0.0,
                beta_base=0.005,
                beta_max=1.0,
                velocity_gain=0.15,
                velocity_max=10.0,
                final_cutoff_min_hz=1.0,
                final_cutoff_max_hz=12.0,
                derivative_cutoff_hz=1.0,
                reset_gap_s=0.50,
            )

    def _on_presentation_frame(
        self,
        packet: FramePacket,
        tracking_frame: TrackingFrame,
        interaction_state: InteractionState | None,
    ) -> None:
        """Callback invoked once per processed frame by RealtimeRuntime."""
        if not self._stop_requested:
            # Emit copy to Qt Main Thread
            self.frame_ready.emit(
                packet.image.copy(),
                tracking_frame,
                interaction_state,
            )

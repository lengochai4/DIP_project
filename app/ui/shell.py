"""Main Application Window (ProductWindow) integrating Header, Views, and DIP VisionWorker."""

from __future__ import annotations

import math
import sys
import time
from typing import Any

import cv2
import numpy as np
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QCloseEvent, QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QTabBar,
    QVBoxLayout,
    QWidget,
)

from .header.header_bar import HeaderBar
from .theme import MAIN_STYLESHEET
from .views.analysis_view import AnalysisView
from .views.evidence_view import EvidenceView
from .views.explore_view import ExploreView
from .worker import VisionWorker


class ProductWindow(QMainWindow):
    """Flagship desktop application for DIP Touchless STEM interaction."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DIP Touchless STEM — Real-Time 3D Interaction Platform")
        self.resize(1380, 880)
        self.setMinimumSize(1024, 680)

        # Apply global theme
        self.setStyleSheet(MAIN_STYLESHEET)

        # Background Vision Worker & State
        self._vision_worker: VisionWorker | None = None
        self._camera_active: bool = False
        self._sensitivity: float = 1.0
        self._active_filter_mode: str = "adaptive"

        # Frame rate & latency measurement
        self._last_time = time.time()
        self._frame_count = 0
        self._current_fps = 60.0

        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Header Bar (Full project title, Team members, Live indicators)
        self.header_bar = HeaderBar(self)
        root_layout.addWidget(self.header_bar)

        # 2. Navigation Tab Bar
        self.tab_bar = QTabBar()
        self.tab_bar.addTab("🪐 Trải nghiệm Tương tác 3D (Explore)")
        self.tab_bar.addTab("🔬 Phân tích Pipeline DIP (Analysis)")
        self.tab_bar.addTab("📊 Kết quả Thử nghiệm (Evidence)")
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        root_layout.addWidget(self.tab_bar)

        # 3. Stacked Views Area
        self.stack = QStackedWidget()
        self.explore_view = ExploreView()
        self.analysis_view = AnalysisView()
        self.evidence_view = EvidenceView()

        self.stack.addWidget(self.explore_view)
        self.stack.addWidget(self.analysis_view)
        self.stack.addWidget(self.evidence_view)
        root_layout.addWidget(self.stack, stretch=1)

        # Connect Control Signals from ExploreView
        self.explore_view.control_panel.camera_toggled.connect(self._toggle_camera)
        self.explore_view.control_panel.sensitivity_changed.connect(self._on_sensitivity_changed)
        self.explore_view.control_panel.filter_changed.connect(self._on_filter_changed)

    def _setup_timer(self) -> None:
        """High-performance 60 FPS animation timer."""
        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60 FPS
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()

    def _on_tab_changed(self, index: int) -> None:
        self.stack.setCurrentIndex(index)

    def _on_sensitivity_changed(self, factor: float) -> None:
        self._sensitivity = factor

    def _on_filter_changed(self, filter_key: str) -> None:
        self._active_filter_mode = filter_key
        # If camera is currently active, restart worker with new filter
        if self._camera_active:
            self._stop_vision_worker()
            self._start_vision_worker()

    def _toggle_camera(self, start: bool) -> None:
        if start:
            self._start_vision_worker()
        else:
            self._stop_vision_worker()

    def _start_vision_worker(self) -> None:
        """Start the background DIP pipeline thread."""
        if self._vision_worker is not None and self._vision_worker.isRunning():
            return

        self._vision_worker = VisionWorker(
            camera_index=0,
            filter_mode=self._active_filter_mode,
            parent=self,
        )
        self._vision_worker.frame_ready.connect(self._on_vision_frame)
        self._vision_worker.error_occurred.connect(self._on_vision_error)
        self._vision_worker.status_changed.connect(self._on_vision_status)
        self._vision_worker.start()
        self._camera_active = True

    def _stop_vision_worker(self) -> None:
        """Stop worker cleanly."""
        if self._vision_worker is not None:
            self._vision_worker.request_stop()
            self._vision_worker.wait(1500)
            self._vision_worker = None

        self._camera_active = False
        self.header_bar.set_tracking_status("NO HAND")
        self.explore_view.camera_widget.update_frame(None)
        self.analysis_view.camera_widget.update_frame(None)

    def _on_vision_frame(
        self,
        bgr_frame: np.ndarray,
        tracking_frame: Any,
        interaction_state: Any,
    ) -> None:
        """Handle real-time processed frame from the DIP pipeline."""
        now = time.time()
        dt = now - self._last_time
        self._last_time = now

        # Update FPS display
        self._frame_count += 1
        if dt > 0:
            instant_fps = 1.0 / dt
            self._current_fps = 0.9 * self._current_fps + 0.1 * instant_fps
            if self._frame_count % 10 == 0:
                self.header_bar.set_fps(self._current_fps)
                self.header_bar.set_latency(dt * 1000.0)

        # Extract ROI Bounding Box
        roi_tuple = None
        if tracking_frame.roi is not None:
            r = tracking_frame.roi
            roi_tuple = (r.x, r.y, r.width, r.height)

        # Extract Landmarks (Index, Thumb, Wrist, etc.)
        landmarks_norm = []
        lms = tracking_frame.filtered_landmarks or tracking_frame.raw_landmarks
        if lms:
            landmarks_norm = [(lm.x, lm.y) for lm in lms]

        # Illumination & CLAHE Status
        illum_state = "NORMAL"
        clahe_active = False
        if tracking_frame.illumination is not None:
            illum_state = tracking_frame.illumination.state.name
            clahe_active = (illum_state != "NORMAL")

        # 1. Update Camera Widget (Preview + Overlays)
        self.explore_view.camera_widget.update_frame(
            bgr_frame,
            roi=roi_tuple,
            landmarks=landmarks_norm,
            illumination_state=illum_state,
            clahe_active=clahe_active,
        )

        if self.stack.currentIndex() == 1:
            self.analysis_view.camera_widget.update_frame(
                bgr_frame,
                roi=roi_tuple,
                landmarks=landmarks_norm,
                illumination_state=illum_state,
                clahe_active=clahe_active,
            )
            self.analysis_view.update_telemetry(tracking_frame, interaction_state)

        # 2. Update Header Status Badge
        status_name = tracking_frame.status.name
        self.header_bar.set_tracking_status(status_name)

        # 3. INTERACTIVE 3D MANIPULATION (Real-time Hand Control)
        if interaction_state is not None and interaction_state.interaction_valid:
            yaw_rad, pitch_rad = interaction_state.rotation_delta
            yaw_deg = math.degrees(yaw_rad) * self._sensitivity
            pitch_deg = math.degrees(pitch_rad) * self._sensitivity

            # Handle Pinch to Scale
            if interaction_state.pinch_active:
                scale_delta = interaction_state.scale_delta
                # Apply scale delta
                self.explore_view.viewport_3d.set_transform(0.0, 0.0, scale_delta)
            else:
                # Rotate with finger motion (Negative yaw aligns with intuitive mirror view)
                self.explore_view.viewport_3d.set_transform(-yaw_deg, pitch_deg, 1.0)

        # 4. Update Gesture Indicator
        pinch_ratio = 0.0
        is_pinching = False
        yaw_delta_deg = 0.0
        pitch_delta_deg = 0.0

        if interaction_state is not None:
            if interaction_state.pinch_ratio is not None:
                pinch_ratio = interaction_state.pinch_ratio
            is_pinching = interaction_state.pinch_active
            yaw_delta_deg = math.degrees(interaction_state.rotation_delta[0])
            pitch_delta_deg = math.degrees(interaction_state.rotation_delta[1])

        is_valid_hand = (status_name in ("VALID", "REACQUIRED"))
        self.explore_view.gesture_indicator.update_gestures(
            pinch_ratio=pinch_ratio,
            is_pinching=is_pinching,
            yaw_delta=yaw_delta_deg,
            pitch_delta=pitch_delta_deg,
            is_valid_hand=is_valid_hand,
        )

    def _on_vision_error(self, err_msg: str) -> None:
        self.header_bar.set_tracking_status("NO HAND")
        QMessageBox.warning(self, "Lỗi Camera / Pipeline", err_msg)

    def _on_vision_status(self, msg: str) -> None:
        pass

    def _on_tick(self) -> None:
        """Periodic background animation."""
        self.explore_view.viewport_3d.tick()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Global keyboard shortcuts."""
        key = event.key()
        if key == Qt.Key.Key_R:
            self.explore_view.viewport_3d.reset_transform()
        elif key in (Qt.Key.Key_Q, Qt.Key.Key_Escape):
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Ensure clean resource release upon exit."""
        self._stop_vision_worker()
        event.accept()


def run_app() -> int:
    """Launch application entry point."""
    app = QApplication.instance() or QApplication(sys.argv)
    window = ProductWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run_app())

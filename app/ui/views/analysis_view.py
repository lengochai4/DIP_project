"""AnalysisView: Deep-dive inspection into the 8-stage DIP pipeline and landmark telemetry."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..components.camera_widget import CameraWidget
from ..components.dip_pipeline_panel import DIPPipelinePanel


class AnalysisView(QWidget):
    """Academic analysis screen displaying DIP preprocessing, landmark metrics, and filter states."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # ---------------------------------------------------------
        # Top Row: Camera Feed with Overlays + DIP Stage Diagram
        # ---------------------------------------------------------
        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        # Camera View
        cam_box = QFrame()
        cam_box.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1F2937;
                border-radius: 12px;
                padding: 10px;
            }
        """)
        c_layout = QVBoxLayout(cam_box)
        c_layout.setContentsMargins(8, 8, 8, 8)
        lbl_cam = QLabel("KHUNG NHÌN CAMERA & ROI OVERLAY (DIP VISION)")
        lbl_cam.setStyleSheet("font-size: 11px; font-weight: 700; color: #9CA3AF;")
        self.camera_widget = CameraWidget()
        self.camera_widget.setMinimumHeight(280)
        c_layout.addWidget(lbl_cam)
        c_layout.addWidget(self.camera_widget)
        top_row.addWidget(cam_box, stretch=5)

        # Pipeline Flow Card
        self.pipeline_panel = DIPPipelinePanel()
        top_row.addWidget(self.pipeline_panel, stretch=5)

        main_layout.addLayout(top_row, stretch=5)

        # ---------------------------------------------------------
        # Bottom Row: Landmark Telemetry & Filter Performance
        # ---------------------------------------------------------
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(14)

        # Landmark Coordinates Table
        table_box = QFrame()
        table_box.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1F2937;
                border-radius: 12px;
                padding: 10px;
            }
        """)
        t_layout = QVBoxLayout(table_box)
        t_layout.setContentsMargins(8, 8, 8, 8)
        t_title = QLabel("TỌA ĐỘ KEY LANDMARKS THỜI GIAN THỰC [0.0 - 1.0]")
        t_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #9CA3AF;")

        self.table = QTableWidget(5, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Tên Điểm (Key Landmark)", "Tọa độ X", "Tọa độ Y"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1F2937;
                border: 1px solid #374151;
                border-radius: 8px;
                color: #F9FAFB;
                gridline-color: #374151;
            }
            QHeaderView::section {
                background-color: #111827;
                color: #06B6D4;
                font-weight: 700;
                padding: 4px;
                border: 1px solid #374151;
            }
        """)

        sample_points = [
            ("0", "Cổ tay (Wrist)", "—", "—"),
            ("4", "Đầu ngón cái (Thumb Tip)", "—", "—"),
            ("8", "Đầu ngón trỏ (Index Tip)", "—", "—"),
            ("12", "Đầu ngón giữa (Middle Tip)", "—", "—"),
            ("20", "Đầu ngón út (Pinky Tip)", "—", "—"),
        ]

        for row, (lid, name, x, y) in enumerate(sample_points):
            self.table.setItem(row, 0, QTableWidgetItem(lid))
            self.table.setItem(row, 1, QTableWidgetItem(name))
            self.table.setItem(row, 2, QTableWidgetItem(x))
            self.table.setItem(row, 3, QTableWidgetItem(y))

        t_layout.addWidget(t_title)
        t_layout.addWidget(self.table)
        bottom_row.addWidget(table_box, stretch=6)

        # Signal Filtering Specs
        filter_box = QFrame()
        filter_box.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1F2937;
                border-radius: 12px;
                padding: 12px;
            }
        """)
        f_layout = QVBoxLayout(filter_box)
        f_title = QLabel("THÔNG SỐ BỘ LỌC 1-EURO (DIP FILTERING)")
        f_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #9CA3AF;")

        self.lbl_filter_mode = QLabel("Bounded Adaptive 1-Euro Filter")
        self.lbl_filter_mode.setStyleSheet("font-size: 11px; font-weight: 600; color: #10B981;")

        self.lbl_jitter_stat = QLabel("Giảm ~42% so với Raw")
        self.lbl_jitter_stat.setStyleSheet("font-size: 11px; font-weight: 600; color: #F9FAFB;")

        self.lbl_speed_val = QLabel("0.0 mm/s")
        self.lbl_speed_val.setStyleSheet("font-size: 11px; font-weight: 600; color: #06B6D4;")

        self.lbl_cutoff_val = QLabel("1.0 Hz")
        self.lbl_cutoff_val.setStyleSheet("font-size: 11px; font-weight: 600; color: #A78BFA;")

        specs = [
            ("Mô hình lọc hiện tại:", self.lbl_filter_mode),
            ("Độ giảm rung Jitter (A1):", self.lbl_jitter_stat),
            ("Vận tốc ngón trỏ:", self.lbl_speed_val),
            ("Tần số cắt hiện thời:", self.lbl_cutoff_val),
        ]

        f_layout.addWidget(f_title)
        for label, widget in specs:
            row = QHBoxLayout()
            l1 = QLabel(label)
            l1.setStyleSheet("font-size: 11px; color: #9CA3AF;")
            row.addWidget(l1)
            row.addStretch()
            row.addWidget(widget)
            f_layout.addLayout(row)

        f_layout.addStretch()
        bottom_row.addWidget(filter_box, stretch=4)

        main_layout.addLayout(bottom_row, stretch=5)

    def update_telemetry(self, tracking_frame, interaction_state) -> None:
        """Update live telemetry values from processed tracking frame."""
        # Update Table with key landmarks
        lms = tracking_frame.filtered_landmarks or tracking_frame.raw_landmarks
        lm_map = {lm.index: lm for lm in lms}

        key_indices = [(0, 0), (1, 4), (2, 8), (3, 12), (4, 20)]
        for row, idx in key_indices:
            if idx in lm_map:
                p = lm_map[idx]
                self.table.item(row, 2).setText(f"{p.x:.3f}")
                self.table.item(row, 3).setText(f"{p.y:.3f}")
            else:
                self.table.item(row, 2).setText("—")
                self.table.item(row, 3).setText("—")

        # Update Timings in Pipeline Panel
        t = tracking_frame.timings
        self.pipeline_panel.set_stage_status("capture", "Live RGB Capture", "#10B981")
        self.pipeline_panel.set_stage_status("roi", f"ROI Box ({t.preprocess_ms:.1f}ms)", "#06B6D4")
        if tracking_frame.illumination:
            ill_st = tracking_frame.illumination.state.name
            v_val = tracking_frame.illumination.mean_v
            self.pipeline_panel.set_stage_status("illumination", f"{ill_st} (V={v_val:.0f})", "#10B981" if ill_st == "NORMAL" else "#F59E0B")
        self.pipeline_panel.set_stage_status("mediapipe", f"21 Pts ({t.tracking_ms:.1f}ms)", "#10B981")
        self.pipeline_panel.set_stage_status("filter", f"Filtered ({t.filtering_ms:.1f}ms)", "#A78BFA")
        self.pipeline_panel.set_stage_status("gesture", f"Ready ({t.gesture_ms:.1f}ms)", "#06B6D4")

        # Update Filter Diagnostics
        f_diag = tracking_frame.filter_diagnostics
        if f_diag.speed is not None:
            self.lbl_speed_val.setText(f"{f_diag.speed:.2f}")
        if f_diag.final_cutoff_hz is not None:
            self.lbl_cutoff_val.setText(f"{f_diag.final_cutoff_hz:.2f} Hz")

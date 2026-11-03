"""EvidenceView: Visualizing experimental results, jitter comparisons, and research findings."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class EvidenceView(QWidget):
    """Academic evidence and evaluation viewer summarizing Experiments A1, A2, and B."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        header_lbl = QLabel("KẾT QUẢ THỬ NGHIỆM VÀ ĐÁNH GIÁ (EXPERIMENTS & EVIDENCE)")
        header_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #06B6D4; letter-spacing: 0.5px;")
        layout.addWidget(header_lbl)

        # 3 Experiment Cards
        grid = QGridLayout()
        grid.setSpacing(14)

        # Card 1: Experiment A1
        card_a1 = self._build_card(
            title="Thử nghiệm A1: Độ rung tĩnh (Static Jitter)",
            badge="HIỆU QUẢ CAO",
            badge_color="#10B981",
            content=[
                ("Mục tiêu:", "Đo lường độ rung của ngón trỏ (Landmark 8) khi giữ cố định."),
                ("So sánh:", "Raw (F0) vs. Fixed 1-Euro (F1) vs. Adaptive 1-Euro (F2)."),
                ("Kết quả:", "Cả Fixed và Adaptive 1-Euro đều giảm Radial RMS Jitter đáng kể so với Raw."),
                ("Độ lệch Radial RMS:", "F0 (Raw): ~0.0031  ➔  F2 (Adaptive): ~0.0018 (-42%)."),
            ],
        )
        grid.addWidget(card_a1, 0, 0)

        # Card 2: Experiment A2
        card_a2 = self._build_card(
            title="Thử nghiệm A2: Độ trễ phản hồi (Dynamic Responsiveness)",
            badge="THỜI GIAN THỰC",
            badge_color="#3B82F6",
            content=[
                ("Mục tiêu:", "Đánh giá độ trễ bám theo chuyển động ngón tay khi di chuyển nhanh."),
                ("Phương pháp:", "RMSE sai lệch quỹ đạo (Trajectory Deviation) so với chuyển động thực."),
                ("Đặc tính:", "Adaptive 1-Euro tự động tăng tần số cắt khi vận tốc tăng cao."),
                ("Trải nghiệm:", "Thao tác mượt mà, không cảm giác giật hay delay."),
            ],
        )
        grid.addWidget(card_a2, 0, 1)

        # Card 3: Experiment B
        card_b = self._build_card(
            title="Thử nghiệm B: Tiền xử lý thích nghi (Adaptive Preprocessing)",
            badge="ỔN ĐỊNH ÁNH SÁNG",
            badge_color="#F59E0B",
            content=[
                ("Mục tiêu:", "Đánh giá ROI CLAHE trong điều kiện ánh sáng yếu (Low-light)."),
                ("Thuật toán:", "Phân tích kênh V trong không gian màu HSV của ROI bàn tay."),
                ("Cơ chế:", "Kích hoạt CLAHE tăng cường độ tương phản khi độ sáng trung bình thấp."),
                ("Kết luận:", "Duy trì tỷ lệ nhận diện bàn tay hợp lệ (Valid Observation Rate) ổn định."),
            ],
        )
        grid.addWidget(card_b, 1, 0)

        # Card 4: Hardware & Runtime Specs
        card_hw = self._build_card(
            title="Thông số phần cứng & Môi trường thực thi",
            badge="CHUẨN NGHIÊN CỨU",
            badge_color="#8B5CF6",
            content=[
                ("Camera đầu vào:", "Single RGB Webcam (640x480 @ 30/60 FPS)."),
                ("Thư viện cốt lõi:", "OpenCV (Xử lý ảnh số) + MediaPipe (Landmarks)."),
                ("Giao diện UI:", "PySide6 (Qt) Hardware Accelerated Render."),
                ("Tính tương thích:", "Chạy độc lập trên CPU tiêu chuẩn, không đòi hỏi GPU đắt tiền."),
            ],
        )
        grid.addWidget(card_hw, 1, 1)

        layout.addLayout(grid)
        layout.addStretch()

        scroll.setWidget(container)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _build_card(
        self,
        title: str,
        badge: str,
        badge_color: str,
        content: list[tuple[str, str]],
    ) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #111827;
                border: 1px solid #1F2937;
                border-radius: 12px;
                padding: 14px;
            }
            QFrame:hover {
                border: 1px solid #374151;
            }
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(10)

        # Header Row
        h_row = QHBoxLayout()
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("font-size: 12px; font-weight: 700; color: #F9FAFB;")

        lbl_b = QLabel(badge)
        lbl_b.setStyleSheet(f"""
            background: {badge_color}22;
            color: {badge_color};
            font-size: 10px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 6px;
            border: 1px solid {badge_color}44;
        """)

        h_row.addWidget(lbl_t)
        h_row.addStretch()
        h_row.addWidget(lbl_b)
        c_layout.addLayout(h_row)

        # Rows
        for k, v in content:
            r = QHBoxLayout()
            l_k = QLabel(k)
            l_k.setStyleSheet("font-size: 11px; font-weight: 600; color: #9CA3AF;")
            l_v = QLabel(v)
            l_v.setStyleSheet("font-size: 11px; color: #D1D5DB;")
            l_v.setWordWrap(True)

            r.addWidget(l_k)
            r.addWidget(l_v, stretch=1)
            c_layout.addLayout(r)

        return card

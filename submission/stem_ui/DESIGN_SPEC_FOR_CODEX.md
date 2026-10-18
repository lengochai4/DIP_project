# ĐẶC TẢ TÁI CẤU TRÚC GIAO DIỆN HÓA HỌC AR & STEM 3D CHO CODEX
*(Hệ thống: DIP Touchless STEM — Phiên bản Giao diện Cao cấp 2026)*

Tài liệu này dựa trên ảnh thiết kế chuẩn mẫu: **`submission/stem_ui/assets/ui_mockup_chemistry_ar.jpg`**.
Codex cần đối chiếu chính xác các thành phần, hệ màu và phân cấp layout dưới đây khi code lại trong `submission/stem_ui/renderer.py` và `chemistry_view.py`.

---

## 1. Thông tin chung & Nhóm tác giả (Top Bar)

### Vị trí: Đỉnh màn hình, chiều cao cố định 64px.
* **Bên trái**:
  * Logo biểu tượng nguyên tử/quỹ đạo hạt nhân công nghệ cao (màu Gradient Cyan-Teal).
  * Tiêu đề ứng dụng: `DIP TOUCHLESS STEM` (Font chữ không chân đậm, tracking rộng, màu trắng sáng `#FFFFFF`).
  * Phụ đề: `Không gian hình học & Hóa học AR • Webcam RGB` (Font chữ thường, màu xám xanh `#94A3B8`, 11px).
* **Ở giữa (Trung tâm danh dự - Author Badge)**:
  * Khối capsule/pill kính mờ sang trọng (`background: rgba(22, 33, 55, 0.75)`, viền mảnh `1px solid rgba(255, 255, 255, 0.12)`, bo góc tròn hoàn hảo `border-radius: 9999px`).
  * Văn bản hiển thị trang trọng:
    **`Nhóm tác giả: 24110107 - Nguyễn Đăk Lộc | 24110103 - Trần Gia Kiệt | 24110089 - Lê Ngọc Hải`**
    *(Màu chữ: Trắng ngà, mã số sinh viên dùng font monospace, phân tách bằng dấu gạch đứng tinh tế)*.
* **Bên phải**:
  * Nhóm 4 nút thao tác hệ thống dạng kính bo tròn:
    * `[Dừng camera]` (hoặc `Mở camera`): Khi mở có chấm tròn đỏ cảnh báo, viền mờ.
    * `[Camera]`: Icon máy quay.
    * `[Hướng dẫn]`: Icon cuốn sách.
    * `[Toàn màn]`: Icon mở rộng màn hình (F11).

---

## 2. Thanh chuyển đổi chế độ (Sub-Header Row 2)

### Vị trí: Ngay dưới Top Bar, chiều cao 48px.
* **Bên trái - 3 Chế độ cốt lõi của ứng dụng**:
  1. `[Khối 3D]` (Hình học không gian kinh điển: Lập phương, Tứ diện, Cầu).
  2. `[Đầu ngón]` (Live fingertip geometry: Đỉnh sống theo đầu ngón tay).
  3. `[Hóa học AR]` **(ĐANG ĐƯỢC CHỌN - ACTIVE)**:
     * Viền phát sáng 2 lớp: Viền trong xanh ngọc Cyan (`#00F5D4`), viền ngoài tỏa vầng sáng vàng hổ phách (`#FFB703`).
     * Nền nút chuyển sang màu xanh rêu sẫm trong suốt (`rgba(16, 60, 65, 0.8)`).
* **Bên phải**:
  * Nút `[Đặt lại góc nhìn]` (Phím tắt `R`).
  * Huy hiệu trạng thái thời gian thực: `2 tay • 10 đầu ngón duỗi • 60 FPS 🟢`.

---

## 3. Không gian làm việc chính (Main Chemistry AR Workspace)

### 3.1. Nền AR hòa quyện (Camera Stream Canvas)
* Nền luồng camera webcam toàn cảnh được tích hợp mượt mà, khử viền xám thô ráp.
* Bàn tay người dùng được nhận diện thời gian thực.
* **Con trỏ tương tác đầu ngón tay**:
  * Khi trỏ vào nguyên tử hoặc menu: Đầu ngón trỏ xuất hiện một **vòng tròn mục tiêu phát sáng (Target Ring Halo)** màu xanh ngọc Cyan (`#00F5D4`), giúp người dùng nhận biết ngay điểm chạm chuẩn xác trong không gian 3D.

### 3.2. Panel Hóa học không gian nổi (Floating Spatial Panel bên trái)
* **Kích thước**: Rộng khoảng `360px - 380px`, đặt lơ lửng ở mạn trái, bo góc lớn `24px`, hiệu ứng kính mờ `backdrop-filter: blur(24px)`, viền mạ bạc siêu mảnh `rgba(255, 255, 255, 0.15)`.
* **Tiêu đề panel**: `Trỏ vào ô → chụm cái–trỏ` (Font 14px, màu trắng bạc).
* **2 Thẻ chức năng lớn (Hero Cards)**:
  1. `[BẢNG NGUYÊN TỐ]`: Icon bảng tuần hoàn dạng lưới, có nhãn số `1` ở góc phải trên.
  2. `[MẪU PHÂN TỬ 3D]` **(ĐANG CHỌN)**:
     * Icon mô hình phân tử 3D phát sáng màu vàng cam.
     * Viền vàng kim rực rỡ (`#FFB703`), nhãn số `2` nổi bật.
* **Hộp hướng dẫn 3 bước thao tác chuẩn hóa**:
  * `1. Chọn nguyên tử, kéo ra không gian`
  * `2. Bật Ghép/tách để chỉnh từng nguyên tử`
  * `3. Thả gần để ghép; kéo xa để tháo`
  *(Font chữ 12.5px, màu xám sáng `#E2E8F0`, đánh số thứ tự rõ ràng, không bị tràn dòng hay cắt chữ)*.
* **Lưới nút bấm thao tác phân tử (Molecular Tool Grid)**:
  * Hàng 1: `[Ghép/tách]` & `[Nguyên tử / e]` (Nút bo tròn, viền kính mờ).
  * Hàng 2: `[Liên kết 1]` & `[Hoàn tác]` & `[Lưu]`.
  * Hàng 3 (khi mở rộng): `[Xóa chọn]`, `[Về panel]`, `[Mở đã lưu]`.

### 3.3. Mô hình phân tử hóa học 3D (3D Molecular Rendering)
* Các nguyên tử được dựng thành khối cầu 3D có độ bóng đổ và phản xạ ánh sáng (Specular Phong lighting):
  * Nguyên tử O (Oxy): Màu đỏ rực (`#EF4444`).
  * Nguyên tử C (Cacbon): Màu xám đen sang trọng (`#334155`).
  * Nguyên tử H (Hydro): Màu trắng ngà (`#F8FAFC`).
* Liên kết hóa học (Bonds): Ống trụ hình học nối liền giữa các nguyên tử, có hiệu ứng luồng năng lượng phát sáng nhẹ.

---

## 4. Chân trang (Bottom Footer Bar)

### Vị trí: Đáy cửa sổ, chiều cao 40px, nền kính mờ đồng bộ.
* **Bên trái**:
  * Dòng trạng thái ngữ cảnh: `Chọn bảng nguyên tố để bắt đầu`.
  * Danh mục phím tắt hướng dẫn: `• E: ghép/tách • O: e • Z/Y: hoàn tác/làm lại`.
* **Bên phải**:
  * Nhãn xác nhận trạng thái: `CAMERA AR MINH HỌA • Xử lý cục bộ`.

---

## 5. Bảng mã màu Hex chuẩn hóa cho lập trình viên (Codex Palette)

```python
UI_THEME = {
    # Nền và mặt kính
    "BG_DARK": (9, 16, 29),             # #09101d - Nền sâu nhất
    "PANEL_GLASS": (14, 23, 40, 210),    # rgba(14, 23, 40, 0.82) - Nền panel kính
    "BORDER_SUBTLE": (255, 255, 255, 25),# Viền kính mờ
    "BORDER_GOLD": (255, 183, 3),       # #ffb703 - Viền active/gold
    "BORDER_CYAN": (0, 245, 212),       # #00f5d4 - Viền active/cyan

    # Màu nút và tương tác
    "BTN_NORMAL": (28, 44, 70, 180),    # Nút trạng thái bình thường
    "BTN_HOVER": (38, 60, 95, 220),     # Nút khi di chuột
    "BTN_ACTIVE": (20, 80, 85, 230),    # Nút khi kích hoạt (Hóa học AR)

    # Chữ và nhãn
    "TEXT_TITLE": (255, 255, 255),      # Trắng tuyệt đối
    "TEXT_SUB": (148, 163, 184),        # Xám xanh nhạt
    "TEXT_ACCENT": (0, 245, 212),       # Xanh ngọc phát sáng
    "TEXT_WARNING": (251, 191, 36),     # Vàng cảnh báo/chú ý

    # Nguyên tử 3D
    "ATOM_OXYGEN": (239, 68, 68),       # Đỏ
    "ATOM_CARBON": (51, 65, 85),        # Xám đậm
    "ATOM_HYDROGEN": (248, 250, 252),   # Trắng
}
```
CHỈ THAM KHẢO UI, MỌI CHỨC NĂNG NHƯ CŨ!

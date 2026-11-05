# Phân hệ Mô phỏng Thí nghiệm Quang học STEM (Optics Simulation)

Mô-đun thí nghiệm ảo **Quang học (Optics)** tương tác thời gian thực dành cho hệ thống giáo dục STEM không chạm (Touchless STEM). Toàn bộ phép tính dựa trên **quang hình học giải tích chuẩn xác (Analytical Geometric Optics)**, tối ưu hiển thị tia sáng laser phát quang (laser glow rays) và giao diện kính mờ (Glassmorphism) đồng bộ với phong cách thiết kế của dự án.

---

## 1. Cấu trúc thư mục (`submission/stem_ui/optics/`)

```
submission/stem_ui/optics/
├── __init__.py               # Khai báo gói và các hàm API chính
├── optics_engine.py          # Bộ nhân tính toán vật lý quang học thuần túy (Snell, Lens, Prism)
├── optics_labs.yaml          # Danh mục cấu hình bài lab, công thức, giới hạn thông số, thử thách
├── optics_experiments.py     # Quản lý phiên thí nghiệm, thông số và các bộ mẫu chuẩn (presets)
├── optics_view.py            # Giao diện đồ họa Pygame tương tác thời gian thực
└── README.md                 # Tài liệu hướng dẫn chi tiết (file này)
```

Ngoài ra, tại thư mục gốc của dự án có script khởi chạy trực tiếp:
* **`run_optics.py`**: Trình chạy độc lập cho phép người dùng mở và tương tác ngay lập tức với 3 thí nghiệm.

---

## 2. Chi tiết 3 bài thí nghiệm quang học

### Thí nghiệm 1: Khúc xạ ánh sáng & Phản xạ toàn phần (Snell's Law & TIR)
* **Mục tiêu**: Khảo sát đường truyền tia sáng khi đi qua ranh giới giữa hai môi trường trong suốt và hiện tượng phản xạ toàn phần.
* **Công thức vật lý**:
  $$\begin{aligned}
  & n_1 \sin(i) = n_2 \sin(r) \\
  & \sin(i_{\text{gh}}) = \frac{n_2}{n_1} \quad (\text{khi } n_1 > n_2)
  \end{aligned}$$
* **Hiện tượng quan sát**:
  - Khi $i < i_{\text{gh}}$: Xuất hiện đồng thời **tia khúc xạ** truyền vào môi trường 2 và **tia phản xạ một phần** trở lại môi trường 1 (tính toán chính xác hệ số phản xạ Fresnel $R$).
  - Khi $i = i_{\text{gh}}$: Tia khúc xạ đi là là sát mặt phân cách ($r = 90^\circ$).
  - Khi $i > i_{\text{gh}}$: **Phản xạ toàn phần (TIR)** — 100% cường độ ánh sáng bị phản xạ trở lại môi trường 1, tia khúc xạ hoàn toàn biến mất.
* **Các mẫu chuẩn (Presets)**:
  - *Không khí $\rightarrow$ Nước*: Khúc xạ thông thường ($n_1=1.000, n_2=1.333$).
  - *Thủy tinh $\rightarrow$ Không khí (i < i_gh)*: Tia khúc xạ lệch xa pháp tuyến ($r > i$).
  - *Thủy tinh $\rightarrow$ Không khí (TIR)*: $i = 50^\circ > i_{\text{gh}} \approx 41.1^\circ$, toàn bộ tia sáng bật ngược lại.
  - *Kim cương $\rightarrow$ Không khí*: Góc tới hạn cực nhỏ $i_{\text{gh}} \approx 24.4^\circ$, minh họa nguyên lý lấp lánh của giác cắt kim cương.

---

### Thí nghiệm 2: Thấu kính mỏng Hội tụ & Phân kì (Thin Lens Imaging)
* **Mục tiêu**: Xác định vị trí, chiều và độ lớn của ảnh tạo bởi thấu kính mỏng thông qua đường truyền của **3 tia sáng đặc biệt**.
* **Công thức vật lý**:
  $$\begin{aligned}
  & \frac{1}{f} = \frac{1}{d} + \frac{1}{d'} \implies d' = \frac{d \cdot f}{d - f} \\
  & k = -\frac{d'}{d}, \quad h' = k \cdot h
  \end{aligned}$$
* **3 Tia sáng đặc biệt được vẽ mô phỏng thời gian thực**:
  1. **Tia 1 (Màu lam Cyan)**: Đi từ đỉnh vật song song trục chính $\rightarrow$ khúc xạ đi qua tiêu điểm $F'$.
  2. **Tia 2 (Màu vàng Yellow)**: Đi từ đỉnh vật thẳng qua quang tâm $O$ $\rightarrow$ truyền thẳng không đổi hướng.
  3. **Tia 3 (Màu hồng Magenta)**: Đi từ đỉnh vật qua tiêu điểm vật $F$ $\rightarrow$ khúc xạ đi song song trục chính.
* **Tính chất ảnh**:
  - Thấu kính hội tụ ($f > 0$):
    - $d > 2f$: Ảnh **thật**, ngược chiều, nhỏ hơn vật.
    - $d = 2f$: Ảnh **thật**, ngược chiều, độ lớn **bằng vật** ($k = -1$).
    - $f < d < 2f$: Ảnh **thật**, ngược chiều, **phóng đại**.
    - $d = f$: Ảnh ở **vô cực ($\infty$)**, các tia ló song song nhau.
    - $d < f$: Ảnh **ảo**, cùng chiều, phóng đại (Nguyên lý kính lúp).
  - Thấu kính phân kì ($f < 0$): Luôn cho ảnh **ảo**, cùng chiều, nhỏ hơn vật nằm trong khoảng tiêu cự.

---

### Thí nghiệm 3: Tán sắc ánh sáng qua Lăng kính (Prism Dispersion)
* **Mục tiêu**: Khảo sát hiện tượng ánh sáng trắng bị tách thành dải quang phổ 7 màu cầu vồng khi đi qua lăng kính thủy tinh.
* **Công thức vật lý**:
  $$\begin{aligned}
  & \sin(i_1) = n(\lambda) \cdot \sin(r_1) \\
  & r_1 + r_2 = A \\
  & n(\lambda) \cdot \sin(r_2) = \sin(i_2) \\
  & D(\lambda) = i_1 + i_2 - A
  \end{aligned}$$
* **Cơ chế tán sắc**:
  - Chiết suất $n$ của thủy tinh phụ thuộc vào bước sóng ánh sáng (theo định luật tán sắc Cauchy):
    $$n(\text{đỏ}) < n(\text{cam}) < n(\text{vàng}) < n(\text{lục}) < n(\text{lam}) < n(\text{chàm}) < n(\text{tím})$$
  - Ánh sáng đỏ lệch ít nhất ($D_{\text{đỏ}}$ nhỏ nhất), ánh sáng tím lệch nhiều nhất ($D_{\text{tím}}$ lớn nhất).
  - Bề rộng dải quang phổ trên màn hứng: $\Delta D = D_{\text{tím}} - D_{\text{đỏ}}$.
* **Các loại vật liệu lăng kính**:
  - *Thủy tinh Flint*: Độ tán sắc cao, dải màu cầu vồng tách rộng và rõ nét nhất.
  - *Thủy tinh Crown*: Kính quang học tiêu chuẩn.
  - *Kim cương*: Chiết suất cao làm tia sáng bẻ góc gắt.

---

## 3. Hướng dẫn khởi chạy & Tương tác trong Chương trình chính

Phân hệ Quang học đã được **tích hợp sâu trực tiếp vào phân hệ Vật lý (Physics)** của chương trình chính (`submission.stem_ui.app`), hỗ trợ đầy đủ **Webcam AR (Thực tế tăng cường)** và **Tương tác không chạm bằng cử chỉ bàn tay (Touchless Hand Tracking)** thay thế hoàn toàn chuột!

### A. Tích hợp trong phân hệ Vật lý (Physics Module Integration)
1. **Chuyển đổi qua lại giữa Cơ học & Quang học ngay trong Vật lý**:
   - Khi đang ở phân hệ Vật lý (`VẬT LÝ • KHÁM PHÁ`), nhấp vào nút tên bài lab (ví dụ `Lực và Gia tốc v`):
     - Ở thanh điều hướng thư viện có nút **`[ Quang học › ]`**.
     - Nhấp vào để xem ngay danh sách 3 bài thí nghiệm Quang học:
       - `1. Khúc xạ & Phản xạ TP`
       - `2. Thấu kính mỏng (HT / PK)`
       - `3. Tán sắc qua Lăng kính`
     - Chọn bất kỳ bài nào để vào thẳng bài thí nghiệm đó!
   - Khi đang ở phân hệ Quang học, tại góc trên tiêu đề có sẵn nút **`[ ‹ Cơ học (8 bài) ]`** để lập tức quay về 8 bài cơ học cổ điển.
2. **Nút Home Hub ảo (5 cánh tròn)**:
   - Đưa tay hoặc rê chuột vào vòng tròn góc trên bên phải để bung menu 5 cánh: *Hình học 3D, Khung xương tay, Hóa học, Vật lý, Quang học*. Dừng (dwell) 0.6s hoặc click vào cánh **`QUANG HỌC`**.
3. **Phím tắt nhanh**:
   - Nhấn **`O`** để mở Quang học, nhấn **`V`** để mở Vật lý (Cơ học).
   - Nhấn **`TAB`** để xoay vòng các môn (*Hình học $\rightarrow$ Hóa học $\rightarrow$ Quang học $\rightarrow$ Vật lý*).
   - Nhấn các phím số **`1`**, **`2`**, **`3`** để đổi nhanh giữa 3 bài quang học.

---

### B. Bật Webcam AR & Tương tác Bàn tay Không chạm (Touchless Interaction)

1. **Bật Camera nền thực tế tăng cường (Webcam AR Mode)**:
   - Nhấn phím **`C`** hoặc nhấp nút **`Camera`** / **`Bật camera`** trên thanh tiêu đề trên cùng.
   - Hình ảnh webcam phòng học của bạn sẽ hiển thị trực tiếp làm nền, tạo không gian thực tế tăng cường sống động.
   - Khung thí nghiệm và bảng điều khiển được thiết kế kính mờ cao cấp (Glassmorphism), cho phép chùm tia laser, thấu kính và lăng kính nổi bật rực rỡ trên không gian thực tế.

2. **Cử chỉ bàn tay điều khiển không chạm (Touchless Gestures)**:
   - **Tâm trỏ Laser (Reticle Pointer)**: Bám theo đầu ngón tay trỏ (Fingertip index 8) với vòng tròn ánh sáng phát quang màu xanh lơ `ACCENT`.
   - **Cử chỉ chụm (Air Pinch — ngón cái chạm ngón trỏ)**:
     - Khi chụm ngón tay, tâm trỏ chuyển sang màu vàng kim `GOLD` rực rỡ và phát xung xác nhận tương tác.
     - **Bấm nút điều khiển**: Chụm ngón tay để nhấp các nút `[− Giảm]`, `[+ Tăng]`, đổi vật liệu lăng kính, chọn các mẫu chuẩn (Presets) hoặc chuyển sang bài khác.
   - **Thao tác kéo trực tiếp trên khung thí nghiệm (Direct Stage Manipulation)**:
     - **Khúc xạ ánh sáng**: Chụm ngón tay và di chuyển ở nửa trên mặt nước/thủy tinh $\rightarrow$ **tia laser xoay theo góc di chuyển của bàn tay**, lập tức thấy tia khúc xạ và phản xạ toàn phần biến đổi liên tục!
     - **Thấu kính mỏng**: Chụm ngón tay vào mũi tên vật sáng $AB$, kéo sang trái/phải để **thay đổi khoảng cách $d$**, kéo lên/xuống để **thay đổi chiều cao $h$** $\rightarrow$ xem ảnh thật/ảo $A'B'$ lật ngược, thu nhỏ hoặc phóng đại trực tiếp trong không gian!
     - **Lăng kính**: Chụm ngón tay di chuyển chùm sáng trắng tới $\rightarrow$ dải cầu vồng 7 màu tán sắc quét qua quét lại trên màn hứng!
   - **Khung xương tay phát quang (Hand Skeleton)**: Hệ thống tự động vẽ khung xương bàn tay và điểm nối giữa các ngón, giúp người dùng định vị trực quan vị trí tay trong không gian.

---

### C. Chạy bộ Test độc lập (Standalone Runner)

```bash
# Mở ở chế độ cửa sổ mặc định (1280x800)
python run_optics.py

# Mở ở chế độ Toàn màn hình (Fullscreen)
python run_optics.py --fullscreen

# Mở trực tiếp bài Thấu kính / Lăng kính
python run_optics.py --lab lens
python run_optics.py --lab prism
```
*(Hoặc click đúp file `Chay_Optics.bat` trên Windows)*.

### Phím tắt điều khiển:
* **`1`**: Mở bài 1 — Khúc xạ & Phản xạ toàn phần.
* **`2`**: Mở bài 2 — Thấu kính mỏng hội tụ & phân kì.
* **`3`**: Mở bài 3 — Tán sắc qua lăng kính.
* **`O`**: Chuyển ngay sang phân hệ Quang học (khi đang ở bất kỳ chế độ nào).
* **`F` / `F11`**: Bật / Tắt chế độ toàn màn hình.
* **`Q` / `ESC`**: Thoát chương trình.

### Thao tác chuột / Giao diện:
* Nhấp vào các Tab ở trên thanh tiêu đề để chuyển đổi giữa 3 thí nghiệm.
* Sử dụng các nút **`[− Giảm]`** và **`[+ Tăng]`** bên bảng điều khiển phải để thay đổi các thông số vật lý (chiết suất, góc tới, tiêu cự, khoảng cách vật,...).
* Nhấp vào danh sách **`CÁC MẪU THÍ NGHIỆM CHUẨN`** để tải nhanh các tình huống kinh điển (Kính lúp, Phản xạ toàn phần, Tán sắc Flint,...).
* Hộp thoại **`KẾT QUẢ VẬT LÝ`** ở góc dưới bên phải cập nhật tức thời các đại lượng đo đạc lý thuyết chính xác theo thời gian thực.


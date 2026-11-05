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

## 3. Hướng dẫn khởi chạy & Tương tác

### Cách chạy nhanh bằng lệnh Terminal

Từ thư mục gốc dự án, chạy:

```bash
# Mở ở chế độ cửa sổ mặc định (1280x800)
python run_optics.py

# Mở ở chế độ Toàn màn hình (Fullscreen)
python run_optics.py --fullscreen

# Mở trực tiếp bài Thấu kính
python run_optics.py --lab lens

# Mở trực tiếp bài Lăng kính
python run_optics.py --lab prism
```

### Phím tắt điều khiển:
* **`1`**: Mở bài 1 — Khúc xạ & Phản xạ toàn phần.
* **`2`**: Mở bài 2 — Thấu kính mỏng hội tụ & phân kì.
* **`3`**: Mở bài 3 — Tán sắc qua lăng kính.
* **`F` / `F11`**: Bật / Tắt chế độ toàn màn hình.
* **`Q` / `ESC`**: Thoát chương trình.

### Thao tác chuột / Giao diện:
* Nhấp vào các Tab ở trên thanh tiêu đề để chuyển đổi giữa 3 thí nghiệm.
* Sử dụng các nút **`[− Giảm]`** và **`[+ Tăng]`** bên bảng điều khiển phải để thay đổi các thông số vật lý (chiết suất, góc tới, tiêu cự, khoảng cách vật,...).
* Nhấp vào danh sách **`CÁC MẪU THÍ NGHIỆM CHUẨN`** để tải nhanh các tình huống kinh điển (Kính lúp, Phản xạ toàn phần, Tán sắc Flint,...).
* Hộp thoại **`KẾT QUẢ VẬT LÝ`** ở góc dưới bên phải cập nhật tức thời các đại lượng đo đạc lý thuyết chính xác theo thời gian thực.


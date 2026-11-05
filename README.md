# DIP Touchless STEM

**Real-Time Touchless 3D STEM Interaction Using Adaptive Image Preprocessing and Motion Signal Filtering with a Single RGB Camera**

## 1. Tổng quan & Khởi chạy nhanh (Quick Start)

DIP Touchless STEM là đồ án Xử lý ảnh số (Digital Image Processing) ứng dụng camera RGB thông thường để tương tác không chạm thời gian thực với các mô hình 3D và thí nghiệm STEM (Vật lý, Hóa học, Khối không gian).

### Cách cài đặt và chạy ứng dụng

1. **Cài đặt môi trường (chỉ cần chạy 1 lần):**
   - Nhấp đúp vào file `Cai_dat_UI.bat`
   - Hoặc chạy lệnh trong PowerShell:
     ```powershell
     python -X utf8 -m submission.setup_ui
     ```
   *(Yêu cầu Python >= 3.11 64-bit có trong PATH).*

2. **Khởi chạy ứng dụng:**
   - Nhấp đúp vào file `Chay_UI.bat`
   - Hoặc chạy lệnh:
     ```powershell
     .\.venv-ui\Scripts\python.exe -X utf8 -m submission.stem_ui.app
     ```
   - (Nếu dùng môi trường `.venv` phát triển: `.\.venv\Scripts\python.exe -X utf8 -m submission.stem_ui.app`).

3. **Thao tác trong ứng dụng:**
   - Bấm **Bật camera** để kết nối webcam máy tính, hoặc bấm **DroidCam** để kết nối camera điện thoại qua Wi-Fi.
   - Menu chính (Home Hub) gồm 4 phân khu: **Khối 3D**, **Hóa học**, **Bắt điểm cử chỉ**, **Vật lí**.
   - Cử chỉ tay: Di chuyển tay để di chuyển con trỏ/tâm ngắm; chụm ngón cái và ngón trỏ (Pinch) hoặc giữ yên (Dwell) để chọn nút/cầm nắm vật thể 3D.

---

## 2. Requirements

Recommended development environment:

```text
Python 3.11+ (64-bit)
Git
Windows PowerShell
```

Python compatibility is defined by `pyproject.toml`.

---

## 3. Development Setup & Testing

Cài đặt môi trường phát triển đầy đủ:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,demo3d]"
```

Kiểm tra toàn bộ test suite tự động:

```powershell
pytest
```

---

## 4. Project Structure

```text
DIP_project/
├── src/dip_touchless/         # DIP Core: thu ảnh, tiền xử lý, tracking, lọc, tương tác
├── submission/stem_ui/       # App bốn tab, OpenGL, cử chỉ và dữ liệu STEM
│   ├── app.py                # Điểm chạy UI
│   ├── chemistry*.py         # Dữ liệu/đồ thị và tương tác Hóa học
│   ├── physics*.py           # Mô hình SI, tương tác và trình bày Vật lý
│   └── physics_labs.yaml     # Tham số, giả thiết, công thức và nguồn tám bài
├── config/                   # Cấu hình Core và thực nghiệm
├── experiments/              # Replay/thực nghiệm; UI dùng hàm tạo bộ lọc ở đây
├── analysis/                 # Phân tích và dựng kết quả nghiên cứu
├── tests/                    # Kiểm tra tự động
├── models/README.md          # Nguồn/checksum model; binary tải lúc cài
├── Cai_dat_UI.bat            # Script cài đặt môi trường UI tự động
├── Chay_UI.bat               # Script khởi chạy ứng dụng 1-click
└── README.md                 # Tài liệu hướng dẫn chính
```

---

## 5. Kiểm chứng đã thực hiện

Toàn bộ **1.703 test tự động đã vượt qua (100% pass rate)** trên Python 3.11 và Python 3.13:
- Kiểm tra toàn diện pipeline tiền xử lý ảnh (Adaptive CLAHE, ROI Manager, Illumination).
- Kiểm tra tính ổn định của bộ lọc Fixed & Adaptive 1-Euro.
- Kiểm tra các tương tác cử chỉ Pinch, Dwell, Grip và chuyển trạng thái không chạm.
- Kiểm tra tính toán cơ học SI, va chạm, bảo toàn năng lượng và động học trong tab Vật lý.
- Kiểm tra mô hình bảng tuần hoàn 118 nguyên tố, 72 hợp chất và 10 phản ứng tương tác trong tab Hóa học.

Để tự kiểm tra cài đặt hoặc chạy bộ test khi cần:

```powershell
pytest
git status
git diff

git add <task-files>
git commit -m "feat: describe the completed task"
```

Do not claim tests passed unless they were actually executed.

---

## 7. Branch workflow

`main` contains stable shared work.

Each team member should develop on their own branch.

Example:

```text
main
loc
member-a
member-b
```

Typical workflow:

```powershell
git switch loc

# work + commits

pytest
git status
git push
```

For this project, small commits may be kept locally during a gate and pushed when the gate is complete or when a remote backup/share point is needed.

Merge into `main` only after the relevant tests pass and the changes have been reviewed.

---

## 8. Important project rules

- DIP Core is the academic center of the project.
- The 3D application consumes `InteractionState` and must not control Core algorithms directly.
- Raw and canonical Fixed 1-Euro must remain available as baselines.
- Canonical Fixed 1-Euro includes derivative low-pass filtering with `d_cutoff`.
- Missing hand tracking must not be represented by fake zero landmarks.
- Do not invent tracking confidence or measurement quality.
- Handedness score is not tracking confidence.
- Do not silently change algorithm equations, contracts or experiment protocol.
- Do not fabricate FPS, latency, jitter reduction, accuracy or other experimental results.
- Do not add YOLO, depth cameras, Transformers, cloud inference or multi-camera processing unless the project scope is explicitly changed.
- Any quantitative result must come from an actual recorded experiment.
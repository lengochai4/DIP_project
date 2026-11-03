# DIP Touchless STEM

**V2 product frontend:** new PySide6 application with semantic gestures and nine
STEM labs. Run `.\setup_v2.ps1` then `.\launch_v2.ps1`. See
[V2 setup and walkthrough](release/v2/README.md) and
[product specification](docs/07_V2_PRODUCT_SPEC.md). Physical usability testing
is deferred; the frozen G7 research and v1.0 fallback remain unchanged.

**Real-Time Touchless 3D STEM Interaction Using Adaptive Image Preprocessing and Motion Signal Filtering with a Single RGB Camera**

## 1. Overview

DIP Touchless STEM is a Digital Image Processing final-term project that uses a single RGB webcam for real-time touchless interaction with rendered 3D STEM objects.

The project focuses on the processing pipeline rather than building a feature-heavy 3D application.

Main topics:

- ROI-based image processing;
- illumination assessment;
- adaptive CLAHE;
- hand landmark tracking through MediaPipe;
- canonical Fixed 1-Euro filtering;
- bounded Adaptive 1-Euro filtering;
- gesture mapping;
- renderer-independent `InteractionState`;
- reproducible comparison of Raw / Fixed / Adaptive processing.

The 3D STEM application is an extension/demo layer. The DIP Core is the primary academic component.

---

## 2. Requirements

Recommended development environment:

```text
Python 3.11
Git
Windows PowerShell
```

Python compatibility is defined by `pyproject.toml`.

Do not assume that a globally installed Python package is part of the project environment.

---

## 3. Setup

Clone the repository:

```powershell
python -X utf8 -m submission.setup_ui
```

**Cài xong — một lệnh mở app, cũng là lệnh dùng cho các lần sau:**

```powershell
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Upgrade pip:

```powershell
python -m pip install --upgrade pip
```

Install the project and development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Verify the environment:

```powershell
python --version
pytest --version
```

Run the test suite:

```powershell
pytest
```

---

## 4. Project structure

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
├── docs/                     # Sáu đặc tả chuẩn và trạng thái dự án
├── reports/core-final/       # Nguồn báo cáo Core
└── HUONG_DAN_CHAY.md          # Cài/chạy và xử lý lỗi
```

**Giữ nguyên source khi nộp**, không xóa `experiments/` hay các thư mục vì nghĩ UI
không dùng. ZIP GitHub không có môi trường Python, model binary, log/video `runs/`
hoặc Word/PDF/PowerPoint cục bộ; tài liệu nộp và dữ liệu thực nghiệm nếu được yêu cầu
phải gửi kèm riêng. Đổi tên thư mục được, chạy từ nơi chứa `pyproject.toml`.

## Kiểm chứng đã thực hiện

Trước khi chốt bản sửa buông vật thể Hóa học `688f6b4`, toàn bộ **1.091 test đã
qua trên Python 3.11.9 và 3.12.14**. Có kiểm tra native OpenGL, chuyển tab,
resize/F11, lưu/xuất, cầm/buông, mất tay và nhập lại. Hồ sơ/giới hạn bằng chứng:
[QA_CHECKLIST.md](submission/stem_ui/QA_CHECKLIST.md). Theo yêu cầu người dùng,
lần bàn giao/merge này không chạy thêm test, không đổi mã thực thi so với bản đã chốt.

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

---

## 9. Current status

See:

```text
docs/05_PROJECT_STATUS_AND_ROADMAP.md
```

for the current project gate, task, blockers and Definition of Done.

Do not infer implementation completion from this README.
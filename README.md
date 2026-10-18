# DIP Touchless STEM

Ứng dụng học tập STEM với mô hình 3D điều khiển bằng một webcam RGB, hỗ trợ
một hoặc hai tay của cùng người dùng. Phần nghiên cứu tập trung vào xử lý ảnh
và lọc tín hiệu chuyển động; bốn tab ứng dụng minh họa khả năng tương tác.

**Bản chốt sau vấn đáp ngày 18/10/2026:** nhánh `main`, tag
[`submission-2026-10-18`](https://github.com/lengochai4/DIP_project/tree/submission-2026-10-18).
Các tag `submission-2026-10-16` và `submission-2026-10-16-r2` giữ nguyên bản cũ.

## Cài và chạy nhanh

Windows 10/11, Python **>=3.11 64-bit** theo `pyproject.toml`, webcam và driver
đồ họa hỗ trợ OpenGL. Bộ kiểm tra đã chạy bằng Python 3.11.9 và 3.12.14;
phiên bản Python khác còn phụ thuộc wheel của các thư viện native.

Clone repo, hoặc tải ZIP của `main`/tag bản chốt rồi giải nén. Mở terminal tại
thư mục chứa `pyproject.toml`:

```powershell
git clone https://github.com/lengochai4/DIP_project.git
cd DIP_project
python -X utf8 -m submission.setup_ui
.\.venv-ui\Scripts\python.exe -X utf8 -m submission.stem_ui.app
```

Nếu tải ZIP thì bỏ hai lệnh `git clone`/`cd`, mở terminal trong thư mục source
đã giải nén. Có nhiều Python thì dùng `py -3.11 -X utf8 -m submission.setup_ui`
hoặc `py -3.12 -X utf8 -m submission.setup_ui` để chọn môi trường cài.

Hoặc nhấp đúp **Cai_dat_UI.bat** một lần, sau đó **Chay_UI.bat**. Bộ cài tạo
`.venv-ui`, cài thư viện theo `pyproject.toml`, tải model và kiểm tra SHA-256.
Cần Internet lần cài đầu; webcam xử lý trên máy sau khi cài. Camera chỉ mở khi
bấm **Bật camera**. Không cần thư mục `.venv-research` của người phát triển.

Hướng dẫn đầy đủ, cập nhật source và xử lý lỗi:
**[HUONG_DAN_CHAY.md](HUONG_DAN_CHAY.md)**.

## Bốn tab của ứng dụng

| Tab | Chức năng chính | Cách thao tác |
|---|---|---|
| **Khối 3D** | Lập phương, tứ diện, bát diện, cầu; di chuyển, xoay, đổi cỡ, kéo dãn | Chụm cái–trỏ để cầm, mở để buông; hai tay để phối hợp. Xòe tay ở mép trống khoảng 0,45 giây gọi bảng đổi khối, nhắm lại rồi giữ trỏ 1 giây hoặc chụm chọn. Đổi khối giữ nguyên tư thế/cỡ. |
| **Đầu ngón** | Các ngón đang duỗi tạo đỉnh sống; điểm, đoạn, mặt hoặc khối | Duỗi/gập ngón để thay đỉnh, tận dụng một/hai tay. Có số ngón từng tay và nhãn theo hình; không thêm đỉnh hoặc độ dày giả. |
| **Hóa học AR** | Bảng nguyên tố nổi, nguyên tử/electron, mẫu phân tử và ghép/tách liên kết | Trỏ 1 giây hoặc mở–nhắm–chụm để chọn. Cầm cả khối bằng một/hai tay; Ghép/tách để kéo từng nguyên tử. Bảng kéo/đổi cỡ/thu ra viền và mở lại được; có hoàn tác, lưu/mở. |
| **Vật lý** | Tám bài cơ học, tay nắm thông số, vector, đồ thị, năng lượng, thử thách, A/B, lưu/xuất | Chụm kéo vật/tay nắm, mở để buông. Có xem cảnh một/hai tay, bảng thu gọn và bảng lệnh nhanh bằng xòe tay ở mép. |

Tám bài Vật lý: lực–ma sát, mặt phẳng nghiêng, rơi–ném xiên, va chạm 1D,
lò xo–giảm chấn, con lắc, đòn bẩy và ròng rọc lý tưởng. Mỗi bài có tham số SI,
giả thiết, công thức và tình huống học tập. Bài tĩnh dùng **Kiểm tra**; bài động
dùng **Chạy/Dừng**. Một số vật hỗ trợ thả để chạy sau lượt chỉnh có chủ ý.

Phím chung: **H** ẩn/hiện hướng dẫn, **F11** phóng to/thu khung, **Tab** đổi tab,
**Enter** bật/tắt camera. Chuột là đường điều khiển dự phòng. **DroidCam** cho
nhập IP/port Wi-Fi của điện thoại; chỉ một nguồn camera hoạt động tại một thời điểm.

[Hướng dẫn thao tác](submission/stem_ui/README.md) ·
[Đối chiếu công thức Vật lý](submission/stem_ui/PHYSICS_AUDIT.md) ·
[Kịch bản quay video 3 phút rưỡi](submission/KICH_BAN_VIDEO.md)

## Luồng xử lý và giới hạn

```text
Webcam RGB / video phát lại
  → frame, màu và timestamp
  → ROI + đánh giá ánh sáng HSV + CLAHE/bypass theo điều kiện
  → MediaPipe: điểm mốc bàn tay
  → kiểm tra quan sát + lọc tín hiệu theo thời gian
  → cử chỉ / ánh xạ tọa độ
  → giao diện STEM 3D
```

`src/dip_touchless/` chứa DIP Core và các baseline Raw / canonical Fixed 1-Euro /
bounded Adaptive 1-Euro. `submission/stem_ui/` là lớp trình bày riêng, có snapshot
và cấu hình tương tác phục vụ UI; không gộp log hai tay/UI vào kết quả nghiên cứu.

- Mất tay là trạng thái thiếu quan sát, không thay bằng điểm bằng 0 hay tự đoán chuyển động.
- z của model là tương đối, **không phải độ sâu camera đo bằng mét**. Nền camera
  là ghép hiển thị, không định vị vật trong phòng như kính AR.
- Hóa học dùng dữ liệu có nguồn và đối chiếu topology cho mẫu đã hỗ trợ;
  ghép/tách không tạo nguyên tố mới hay chứng minh phản ứng/độ bền phân tử.
- Số đo SI thuộc mô hình Vật lý lý tưởng, không đo lực/chiều dài thật từ tay.
  Đòn bẩy kiểm tra tĩnh; ròng rọc nâng chậm, bỏ qua ma sát/quán tính.
- Đây là nguyên mẫu học tập có kiểm tra phần mềm, phục vụ trình diễn và phát triển
  tiếp; chưa có cơ sở cam kết tỷ lệ nhận đúng hoặc độ trễ trên mọi máy.

## Code và tài liệu

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
├── HUONG_DAN_CHAY.md          # Cài/chạy và xử lý lỗi
└── submission/KICH_BAN_VIDEO.md
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
.\.venv-ui\Scripts\python.exe -X utf8 -m submission.check_setup
.\.venv-ui\Scripts\python.exe -X utf8 -m pytest -q
```

Test phần mềm/phát lại không thay thế đánh giá thao tác thật trên webcam.
Nguồn báo cáo nghiên cứu: [BAO_CAO_CORE.md](reports/core-final/BAO_CAO_CORE.md).

## Phát triển và đặc tả

Sáu file `docs/00_GOVERNANCE.md` đến `docs/05_PROJECT_STATUS_AND_ROADMAP.md` là
nguồn quyết định chuẩn; README chỉ hướng dẫn sử dụng. Đọc [AGENTS.md](AGENTS.md)
trước khi sửa. Làm thay đổi mới trên nhánh riêng, giữ `main` và tag bản nộp
làm mốc đối chiếu; không sửa lịch sử các tag đã chia sẻ.

## Nhóm tác giả

- **24110107 — Nguyễn Đăk Lộc**
- **24110103 — Trần Gia Kiệt**
- **24110089 — Lê Ngọc Hải**

This project is supported by Assoc.Prof. Hoang Van Dung and Ho Chi Minh City
University of Technology and Engineering.

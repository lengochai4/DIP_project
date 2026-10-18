# Cài và chạy bản nộp DIP Touchless STEM

Bản ứng dụng đã chốt nằm trong `submission/stem_ui/`. DIP Core nằm trong
`src/dip_touchless/`; UI minh họa không thay đổi số liệu và các baseline nghiên cứu.

## 1. Yêu cầu

- Windows 10/11, Python **>=3.11 64-bit** theo `pyproject.toml`.
  Git chỉ cần nếu clone/cập nhật repo; tải ZIP thì không cần Git để chạy app.
- Cài Python từ [python.org](https://www.python.org/downloads/windows/), bật
  thêm Python vào PATH. Kiểm tra bằng `python --version`; nếu dùng Launcher,
  `py -3.11 --version` hoặc `py -3.12 --version` chọn phiên bản cụ thể.
- Internet cho lần cài thư viện/model đầu tiên; webcam và driver đồ họa hỗ trợ
  OpenGL để tương tác. Webcam chạy offline sau khi cài; DroidCam dùng Wi-Fi nội bộ.
- `>=3.11` là phiên bản tối thiểu của source; còn phải có thư viện native tương
  thích với Python/hệ điều hành. Bộ cài không ép dùng đúng 3.12 và không tự đổi
  model, ngưỡng hay thuật toán nghiên cứu khi chọn phiên bản Python khác.

## 2. Lấy source

Từ PowerShell hoặc terminal VS Code:

```powershell
git clone https://github.com/lengochai4/DIP_project.git
cd DIP_project
```

Bản chốt sau vấn đáp ngày **18/10/2026** nằm trên `main`, được đánh dấu bằng tag
`submission-2026-10-18`, gồm đủ bốn tab và bản sửa buông vật thể Hóa học.
Các tag ngày 16/10 vẫn giữ bản cũ. Nếu đã có repo, giữ/commit các thay đổi đang làm trước
khi chuyển nhánh rồi cập nhật:

```powershell
git fetch origin --tags
git switch main
git pull --ff-only
```

Để lấy đúng bản nộp đã chốt dù `main` có thay đổi về sau:

```powershell
git clone --branch submission-2026-10-18 https://github.com/lengochai4/DIP_project.git DIP_submission
cd DIP_submission
```

Clone theo tag ở trạng thái detached HEAD là bình thường khi chỉ chạy bản nộp.
Các nhánh thử UI khác là lịch sử thử nghiệm, không cần merge/xóa để chạy bản này.

## 3. Cài một lần

Nhấp đúp **Cai_dat_UI.bat**, hoặc chạy:

```powershell
python -X utf8 -m submission.setup_ui
```

Nếu có nhiều Python, chọn cụ thể bằng `py -3.11 -X utf8 -m submission.setup_ui`
hoặc `py -3.12 -X utf8 -m submission.setup_ui`. `.venv-ui` phải cùng phiên bản
Python bạn chọn; nếu khác, dùng lại Python cũ hoặc đổi tên môi trường trước khi
cài mới. Không cần đổi Python của hệ thống để chạy một môi trường đã tạo.

Bộ cài tạo `.venv-ui`, cài theo `pyproject.toml`; pip chọn phiên bản thư viện
có wheel tương thích với Python đang dùng. Bộ cài tải model chính thức của Google và đối chiếu
SHA-256 với model đã dùng. Cuối cùng kiểm tra thư viện, tài nguyên và việc
khởi tạo MediaPipe. Bộ cài không yêu cầu activate PowerShell và không mở camera.
Thư mục `.venv-ui` và model là dữ liệu cục bộ, không đưa vào Git.

Chỉ khi muốn tái hiện snapshot đã kiểm tra trên Python 3.12, dùng:

```powershell
py -3.12 -X utf8 -m submission.setup_ui --locked
```

`requirements-ui.lock.txt` là snapshot riêng của 3.12, không ép lên Python 3.11.
Phiên bản thư viện sau cài được ghi ở `runs/ui-install/environment.json`; số liệu
nghiên cứu cũ vẫn gắn với môi trường đã dùng để thu/phát lại, không thay bằng
kết quả của một môi trường mới.

## 4. Mở ứng dụng

Nhấp đúp **Chay_UI.bat**, hoặc chạy từ gốc repo:

```powershell
.\.venv-ui\Scripts\python.exe -X utf8 -m submission.stem_ui.app
```

Camera mặc định đang tắt. Bấm **Bật camera**, chọn chế độ:

- **Khối 3D:** chụm cái–trỏ để cầm, di chuyển/xoay tay để điều khiển; mở ngón
  để buông. Hai tay cùng chụm để đổi cỡ. Các chế độ kéo dãn/tiến lùi có hướng dẫn.
  Xòe tay tại mép trống khoảng 0,45 giây để gọi bảng đổi khối; di tay nhắm lại
  rồi giữ trỏ 1 giây hoặc chụm chọn. Mở ngón sau chọn rồi chụm lại để cầm.
- **Đầu ngón:** ngón đang duỗi tạo các đỉnh trực tiếp; hỗ trợ một/hai tay cùng
  người dùng. Có số ngón từng tay và trạng thái điểm/đoạn/mặt/khối; không thêm điểm thủ công.
- **Hóa học AR:** giữ trỏ trên nút khoảng 1 giây hoặc mở–nhắm–chụm để chọn mẫu phân tử hoặc
  nguyên tố. **Cầm cả khối** để di chuyển/đổi cỡ; **Ghép/tách** để sửa liên kết.
  Bảng kéo/đổi cỡ và thu ra viền được, chọn mũi tên để mở lại. Tách trỏ–cái
  đóng băng vật trong lúc xác nhận buông. Có chuột dự phòng, hoàn tác, lưu/mở.
- **Vật lý:** thư viện tám bài cơ học. Chụm kéo vật/tay nắm, mở để buông;
  **Điều chỉnh** đổi thông số, **Đo / Lưu** mở vector/đồ thị/năng lượng, A/B
  và xuất CSV/ảnh, **Bài học** nêu giả thiết/công thức/thử thách. Có bảng lệnh
  nhanh bằng xòe tay ở mép trống và xem cảnh một/hai tay khi đang dừng.

**H** ẩn/hiện hướng dẫn; **F11** hoặc nút phóng to mở toàn màn hình, **Esc** trở
về cửa sổ khi đang toàn màn hình (đóng bảng chọn khối đang mở trước).
**Tab** qua bốn chế độ; **V** mở Vật lý, **P** mở Hóa học. Thao tác chi tiết:
[submission/stem_ui/README.md](submission/stem_ui/README.md).

## 5. Chọn camera khác hoặc DroidCam

```powershell
.\.venv-ui\Scripts\python.exe -X utf8 -m submission.stem_ui.app --camera 1
```

Với điện thoại: mở DroidCam trên điện thoại, cho hai máy cùng Wi-Fi, bấm
**DroidCam** trong app rồi nhập IP và port hiện trên điện thoại (thường 4747).
App đọc `http://IP:PORT/video`; không cần cài phần mềm DroidCam PC cho đường
kết nối này. Dùng **Dùng webcam máy** để chuyển lại. Mỗi lần chỉ dùng một nguồn.

## 6. Kiểm tra cài đặt hoặc chạy test

```powershell
.\.venv-ui\Scripts\python.exe -X utf8 -m submission.check_setup
.\.venv-ui\Scripts\python.exe -m pip check
.\.venv-ui\Scripts\python.exe -X utf8 -m pytest -q
```

`check_setup` không mở camera hoặc cửa sổ, kiểm tra thư viện theo khai báo và model;
nó chưa xác nhận quyền webcam và khả năng dựng OpenGL trên máy khác. Bộ test có
một regression cửa sổ Windows, có thể hiện cửa sổ ngắn để kiểm tra khởi động/F11.
Các test tự động không thay số liệu đánh giá độ chính xác nhận tay.
Với snapshot 3.12 có thể chạy thêm `submission.check_setup --locked`.

## 7. Khi gặp lỗi

| Hiện tượng | Cách xử lý |
|---|---|
| Không tìm thấy `python`/`py` | Cài Python từ 3.11 64-bit kèm PATH/Launcher, mở terminal mới |
| Thiếu pygame/OpenGL/MediaPipe | Chạy lại bộ cài; dùng đúng `.venv-ui\Scripts\python.exe` |
| Thiếu model hoặc SHA-256 khác | Xem [models/README.md](models/README.md); giữ bản sao model cũ trước khi tải lại |
| `failed to open/read camera` | Đóng Teams/Zoom/app Camera; bật quyền camera cho desktop apps trong Windows; thử camera index khác |
| Không tạo được OpenGL context | Cập nhật driver đồ họa và chạy trên desktop có OpenGL; máy ảo/phiên remote có thể khác máy thật |
| Không nối được điện thoại | Đối chiếu IP/port, cùng Wi-Fi, điện thoại đang bật stream; thử URL `/video` trong trình duyệt |
| Không tìm được wheel tương thích | Kiểm tra Python 64-bit và phiên bản thư viện báo lỗi; thử Python 3.11/3.12 thay vì giả định mọi bản mới đều hỗ trợ |
| Cài thư viện lỗi mạng | Xem log pip, kiểm tra Internet rồi chạy lại; không thay model/tham số hoặc dùng môi trường mới để sửa số liệu nghiên cứu cũ |

## 8. Tài liệu và dữ liệu nộp

- Báo cáo Core: [reports/core-final/BAO_CAO_CORE.md](reports/core-final/BAO_CAO_CORE.md).
  Bản Word nộp riêng; Word trong `output/` là file cục bộ, không tự xuất hiện khi clone.
- Dữ liệu nguyên tố/mẫu hóa học nằm trong repo; model được tải theo checksum.
- Nguồn video, log trong `runs/` và báo cáo dựng ra trong `output/` không đưa vào
  source Git. Máy mới không cần video thực nghiệm để chạy UI.
- `submission/README.md` lưu cách tái hiện demo G7 cũ. Để chạy giao diện đã chốt,
  dùng lệnh ở mục 4 của tài liệu này.

## 9. Nộp chương trình mã code và dữ liệu kèm theo

Giữ nguyên ZIP source từ GitHub `main` hoặc tag bản nộp. Không tự xóa `experiments/`:
UI dùng `experiments.run_replay.build_landmark_filter` để tạo bộ lọc. Các thư mục
`src/`, `submission/`, `config/` và file `pyproject.toml` phải đi cùng nhau.
Tests, đặc tả và hồ sơ thực nghiệm giúp người chấm đối chiếu đồ án, không phải
file tạm cần xóa. ZIP GitHub không chứa `.git/`, môi trường Python, model binary,
video/log hoặc tài liệu ôn riêng chỉ lưu cục bộ.

Dữ liệu 118 nguyên tố và mẫu phân tử đã nằm trong source. Model nhận tay được tải
tự động theo SHA-256 khi cài; vì vậy source ZIP cần Internet ở lần cài đầu.
Không cần đóng gói `.venv`, `.venv-research`, `.venv-ui` hoặc `__pycache__`.
Nộp báo cáo Word riêng. Nếu thầy yêu cầu tái hiện số liệu từ video gốc, cần gửi
thêm bộ dữ liệu thực nghiệm riêng; ZIP source không tự chứa video trong `runs/`.

Gợi ý thư mục nộp chung theo yêu cầu lớp (điền số nhóm và thông tin người đại diện):

```text
[GsoNhom]_[MSSV]_[HoTenKhongDau]/
├── Source/              # Nguyên source giải nén, có README.md và pyproject.toml
├── Bao_cao.docx
├── Bao_cao.pdf
├── Trinh_chieu.pptx
└── Demo.mp4             # Video nếu được yêu cầu gửi kèm
```

Nén thư mục ngoài thành ZIP; một người đại diện nộp. Các file báo cáo/trình chiếu
do nhóm đặt vào, không tự sinh từ ZIP GitHub. Kịch bản quay ngắn:
[submission/KICH_BAN_VIDEO.md](submission/KICH_BAN_VIDEO.md).

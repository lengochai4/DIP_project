# Cài và chạy bản nộp DIP Touchless STEM

Bản ứng dụng đã chốt nằm trong `submission/stem_ui/`. DIP Core nằm trong
`src/dip_touchless/`; UI minh họa không thay đổi số liệu và các baseline nghiên cứu.

## 1. Yêu cầu

- Windows 10/11, Python **3.12 64-bit** và Git.
- Cài Python từ [python.org](https://www.python.org/downloads/windows/), bật
  Python Launcher (`py`). Kiểm tra bằng `py -3.12 --version`.
- Internet cho lần cài thư viện/model đầu tiên; webcam và driver đồ họa hỗ trợ
  OpenGL để tương tác. Webcam chạy offline sau khi cài; DroidCam dùng Wi-Fi nội bộ.
- Hướng dẫn này kiểm tra trên Python 3.12; yêu cầu `>=3.11` của Core không có
  nghĩa mọi phiên bản Python mới đều đã được kiểm tra với bộ thư viện UI này.

## 2. Lấy source

Từ PowerShell hoặc terminal VS Code:

```powershell
git clone --branch feat/submission-ui-clean https://github.com/lengochai4/DIP_project.git
cd DIP_project
```

Nếu đã có repo và đang ở nhánh nộp, cập nhật bằng `git pull --ff-only`.
Sau khi nhánh nộp được merge vào `main`, có thể clone mặc định không cần
`--branch`, hoặc chuyển sang `main` rồi `git pull --ff-only`. Các nhánh thử UI
khác là lịch sử thử nghiệm, không cần merge/xóa để chạy bản này.

## 3. Cài một lần

Nhấp đúp **Cai_dat_UI.bat**, hoặc chạy:

```powershell
py -3.12 -X utf8 -m submission.setup_ui
```

Bộ cài tạo `.venv-ui`, cài project với phiên bản thư viện trong
`requirements-ui.lock.txt`, tải model chính thức của Google và đối chiếu
SHA-256 với model đã dùng. Cuối cùng kiểm tra thư viện, tài nguyên và việc
khởi tạo MediaPipe. Bộ cài không yêu cầu activate PowerShell và không mở camera.
Thư mục `.venv-ui` và model là dữ liệu cục bộ, không đưa vào Git.

## 4. Mở ứng dụng

Nhấp đúp **Chay_UI.bat**, hoặc chạy từ gốc repo:

```powershell
.\.venv-ui\Scripts\python.exe -X utf8 -m submission.stem_ui.app
```

Camera mặc định đang tắt. Bấm **Bật camera**, chọn chế độ:

- **Khối 3D:** chụm cái–trỏ để cầm, di chuyển/xoay tay để điều khiển; mở ngón
  để buông. Hai tay cùng chụm để đổi cỡ. Các chế độ kéo dãn/tiến lùi có hướng dẫn.
- **Đầu ngón:** ngón đang duỗi tạo các đỉnh trực tiếp; hỗ trợ một/hai tay cùng
  người dùng. Không cần thêm điểm thủ công.
- **Hóa học AR:** giữ trỏ trên nút khoảng 1 giây để chọn; chọn mẫu phân tử hoặc
  nguyên tố. **Cầm cả khối** để di chuyển/đổi cỡ; **Ghép/tách** để sửa liên kết.
  Có chuột dự phòng, hoàn tác, lưu/mở trên máy.

**H** ẩn/hiện hướng dẫn; **F11** hoặc nút phóng to mở toàn màn hình, **Esc** trở
về cửa sổ khi đang toàn màn hình. Thao tác chi tiết:
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

`check_setup` không mở camera hoặc cửa sổ, kiểm tra đúng bộ thư viện/model;
nó chưa xác nhận quyền webcam và khả năng dựng OpenGL trên máy khác. Bộ test có
một regression cửa sổ Windows, có thể hiện cửa sổ ngắn để kiểm tra khởi động/F11.
Các test tự động không thay số liệu đánh giá độ chính xác nhận tay.

## 7. Khi gặp lỗi

| Hiện tượng | Cách xử lý |
|---|---|
| Không tìm thấy `py` hoặc Python 3.12 | Cài Python 3.12 64-bit kèm Launcher, mở terminal mới |
| Thiếu pygame/OpenGL/MediaPipe | Chạy lại bộ cài; dùng đúng `.venv-ui\Scripts\python.exe` |
| Thiếu model hoặc SHA-256 khác | Xem [models/README.md](models/README.md); giữ bản sao model cũ trước khi tải lại |
| `failed to open/read camera` | Đóng Teams/Zoom/app Camera; bật quyền camera cho desktop apps trong Windows; thử camera index khác |
| Không tạo được OpenGL context | Cập nhật driver đồ họa và chạy trên desktop có OpenGL; máy ảo/phiên remote có thể khác máy thật |
| Không nối được điện thoại | Đối chiếu IP/port, cùng Wi-Fi, điện thoại đang bật stream; thử URL `/video` trong trình duyệt |
| Cài thư viện lỗi mạng | Xem log pip, kiểm tra Internet rồi chạy lại; không đổi phiên bản khóa tùy ý để giữ môi trường so sánh |

## 8. Tài liệu và dữ liệu nộp

- Báo cáo Core: [reports/core-final/BAO_CAO_CORE.md](reports/core-final/BAO_CAO_CORE.md).
  Bản Word nộp riêng; Word trong `output/` là file cục bộ, không tự xuất hiện khi clone.
- Dữ liệu nguyên tố/mẫu hóa học nằm trong repo; model được tải theo checksum.
- Nguồn video, log trong `runs/` và báo cáo dựng ra trong `output/` không đưa vào
  source Git. Máy mới không cần video thực nghiệm để chạy UI.
- `submission/README.md` lưu cách tái hiện demo G7 cũ. Để chạy giao diện đã chốt,
  dùng lệnh ở mục 4 của tài liệu này.

# Checklist rà soát UI nộp đồ án

## Bổ sung tương thích Python ngày 16/10/2026

- Đối chiếu `pyproject.toml`: source khai báo `requires-python = ">=3.11"`.
  Bộ cài thường dùng Python đang chọn từ 3.11 64-bit trên Windows, giải thư viện
  theo pyproject và chỉ dùng wheel; không còn bắt buộc đúng 3.12. Snapshot
  `requirements-ui.lock.txt` giữ riêng cho `--locked` trên Python 3.12.
- Chuẩn bị runtime Python 3.11.9 riêng bằng cách giải nén core/exe/lib từ các
  MSI chính thức của python.org vào `runs/`; không đổi Python mặc định của máy.
  Source QA riêng tạo venv mới, cài theo pyproject, tải model đúng SHA-256;
  checker và `pip check` đạt. Resolver chọn NumPy 2.4.6/contourpy 1.3.3 cho 3.11,
  khác snapshot 3.12. Đây là môi trường chạy app, không thay môi trường của các
  số liệu nghiên cứu đã ghi.
- **667 test đạt trên Python 3.11.9**, **667 test đạt trên Python 3.12.14**.
  Có thêm kiểm tra sàn phiên bản/kiến trúc và snapshot chỉ áp dụng khi chọn.
- App thật trên 3.11 chạy 30 vòng sự kiện mỗi chế độ solid/tips/chemistry,
  camera tắt, thoát sạch; đã xem cả ba ảnh. Không thu phiên tay mới.
- Bộ cài ghi môi trường đã resolve vào `runs/ui-install/environment.json`.
  Chưa kiểm tra thực thi mọi phiên bản Python mới hơn; `>=3.11` không bảo đảm
  wheel/driver của mọi hệ điều hành hoặc mọi phiên bản tương lai.
- Không đổi `src/`, config nghiên cứu, UI settings/renderer hay thuật toán thao tác.
  Bản sửa được gắn tag `submission-2026-10-16-r2`; tag trước giữ nguyên.

## Kiểm tra cài từ source sạch ngày 16/10/2026

- Export 208 file source/tài nguyên từ bản nộp sang thư mục QA, không mang theo
  môi trường, model hoặc log. Tạo `.venv-ui` mới bằng Python 3.12.14 64-bit.
- Chạy `python -X utf8 -m submission.setup_ui`: cài đúng 27 thư viện trong
  `requirements-ui.lock.txt` và project editable; tải model phiên bản 1 từ
  Google và kiểm tra SHA-256 khớp bản nghiên cứu.
- `submission.check_setup` đạt: import thư viện, đủ tài nguyên, model khởi tạo
  MediaPipe VIDEO hai tay được mà không cần mở webcam.
- `pip check`: `No broken requirements found`.
- Toàn bộ **659 test đạt** trong môi trường mới, gồm 5 kiểm tra bổ sung về
  checksum, không ghi đè model khác và dọn file tải dở khi có lỗi.
- Gọi app thật ở cả `solid`, `tips`, `chemistry`, mỗi chế độ 30 vòng sự kiện,
  camera tắt, thoát sạch. Đã xem ảnh của cả ba chế độ.
- Không đổi `src/`, `config/`, settings, renderer hoặc logic thao tác so với
  bản UI đã chốt `92d0831`. Không thu phiên tay thật mới hoặc công bố thêm
  số đo FPS/latency/độ chính xác. Môi trường mới trên cùng máy kiểm tra không
  bảo đảm mọi driver camera/OpenGL trên máy khác giống hệt.
- Hướng dẫn cài/chạy cho người nhận: [HUONG_DAN_CHAY.md](../../HUONG_DAN_CHAY.md).
  Word nộp riêng; không đưa môi trường, model binary, video/log và tài liệu
  ôn cá nhân vào commit đóng gói.

## Hồ sơ kiểm tra giao diện ngày 14/10/2026

Kiểm tra ngày 14/10/2026 trên working tree của `feat/submission-ui-clean`,
Python 3.12.14 trong `.venv-research`. Đây là biên bản kiểm tra phần ứng dụng;
không thay thế đặc tả canonical hoặc số liệu thực nghiệm Core.

| Hạng mục | Kết quả kiểm tra |
|---|---|
| Core, filtering, replay, cấu hình, dữ liệu và extension | Toàn bộ 654 test dự án đạt; compile Python đạt |
| Nhận ngón, 0–10 đỉnh, raw/filtered, mất tay/tái nhận | Regression đạt; hai lượt replay qua MediaPipe, mỗi lượt 30 frame, nhận hai tay/tối đa 10 ngón; không tự thêm đỉnh hoặc auto-zoom theo span |
| Cầm bằng một/hai tay, xoay, đổi cỡ, kéo dãn, buông | Regression về hysteresis, giới hạn và rebase đạt |
| Ghép/tách, hóa trị, công thức, tên phân tử | Đối chiếu đồ thị; sửa lỗi liên kết cũ gần nhất chặn ghép mới |
| Thư viện phân tử | 32 mẫu/4 trang; kiểm đầy đủ liên kết, hóa trị trung hòa, công thức và nhận dạng sau đổi ID; etanol/đimetyl ete không lẫn tên; render thật cả 32 mẫu đạt |
| Nhãn hóa học khi đổi mẫu/ghép/tách | Refresh ngay khi nội dung đổi; cache chỉ theo topology, không xét vị trí/cỡ hiển thị |
| Độ liên tục AR | Bỏ repaint panel theo atom hover/graph; gate pinch không tính pose thừa và giữ nguyên hysteresis; chạy 180 frame GL với cầm một/hai tay, mở ngón, pose hữu hạn/cỡ bị chặn |
| Lưu/mở, undo/redo | Import lỗi không ghi đè cảnh; lỗi ghi file được hiển thị, không làm UI dừng |
| Chọn hóa học | Dwell 1 giây; có hủy khi mất tay/chuyển mục tiêu và latch chống lặp |
| Webcam ↔ DroidCam | Test đóng nguồn chậm; nguồn mới chờ nguồn cũ đóng hoàn toàn |
| Dừng/thoát trong khi chuyển nguồn | Sửa và test: hủy pending, không mở camera ngoài ý muốn |
| DroidCam IP/port | Kiểm tra đầu vào; từ chối IP số sai, URL/path lẫn trong ô host, port sai |
| Cấu hình lưu hỏng | Bỏ qua dữ liệu không đúng kiểu; UI vẫn khởi động |
| Đường mạng thật qua OpenCV/FFmpeg | Stream MJPEG loopback: đọc 3 frame thật, BGR/timestamp hợp lệ |
| Network burst | Bỏ frame live trùng millisecond trước Core; không tạo timestamp giả; replay giữ kiểm tra nghiêm |
| Hộp cài camera | Tạm dừng thao tác tay/chuột lên cảnh phía sau; không xóa công việc |
| UI ở 960×660, 1120×740, 1360×860 | Render thật, ảnh đã kiểm; thanh tác giả theo chiều rộng, footer căn giữa |
| Ba chế độ, F11, fullscreen, resize | Chạy renderer 90 frame tổng hợp; sửa offset fullscreen; khôi phục cả vị trí/kích thước cũ; chặn resize cũ; có test chọn đúng monitor |
| Crash bộ nhớ khi khởi động/vòng sự kiện | Tái hiện và sửa vòng đời SDL Window; test subprocess thực có GC/event polling/F11 và exit code đạt; kiểm tra cửa sổ app thường responding |
| Thực thi lệnh và dữ liệu nhập | Không thấy eval/exec/pickle/shell=True trong mã app/Core/extension được quét; IP không đi vào shell |
| Git | Chỉ stage mã/docs/test thuộc task; môi trường, video, logs và report artifacts cục bộ không đưa vào commit |

Các kết quả tự động không chứng minh không còn mọi lỗi, cũng không thay thế
kiểm toán bảo mật chuyên sâu. Điện thoại thật chưa được kết nối trong đợt này;
độ trễ, chất lượng Wi-Fi và độ chính xác nhận tay thực tế chưa được đo mới.

Chạy trực tiếp từ terminal PowerShell tại thư mục gốc dự án:

```powershell
.\.venv-research\Scripts\python.exe -X utf8 -m submission.stem_ui.app
```

Kết nối DroidCam: cùng Wi-Fi, nhập IP/port điện thoại rồi bấm **Kết nối Wi-Fi**.
Endpoint `/video` theo [hướng dẫn chính thức DroidCam](https://droidcam.app/help/).

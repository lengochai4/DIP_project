# Checklist rà soát UI nộp đồ án

Kiểm tra ngày 14/10/2026 trên working tree của `feat/submission-ui-clean`,
Python 3.12.14 trong `.venv-research`. Đây là biên bản kiểm tra phần ứng dụng;
không thay thế đặc tả canonical hoặc số liệu thực nghiệm Core.

| Hạng mục | Kết quả kiểm tra |
|---|---|
| Core, filtering, replay, cấu hình, dữ liệu và extension | Toàn bộ 579 test dự án đạt; compile Python đạt |
| Nhận ngón, 0–10 đỉnh, raw/filtered, mất tay/tái nhận | Regression đạt; hai lượt replay qua MediaPipe, mỗi lượt 30 frame, nhận hai tay/tối đa 10 ngón; không tự thêm đỉnh hoặc auto-zoom theo span |
| Cầm bằng một/hai tay, xoay, đổi cỡ, kéo dãn, buông | Regression về hysteresis, giới hạn và rebase đạt |
| Ghép/tách, hóa trị, công thức, tên phân tử | Đối chiếu đồ thị; sửa lỗi liên kết cũ gần nhất chặn ghép mới |
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

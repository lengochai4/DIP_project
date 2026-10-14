# Công cụ thu ROUND2

Kế hoạch: `PLAN.md`. Thu chín nguồn có xem trước, chạy paired replay và phân tích bằng các công cụ đã có. Video và kết quả lưu riêng trong `runs/round2`, không ghi đè G7. Không thay Core hoặc yêu cầu giao diện mới để thu dữ liệu.

## Chạy trên máy này

```powershell
$env:MPLCONFIGDIR = (Join-Path (Get-Location).Path 'runs/mpl-cache')
.\.venv-research\Scripts\python.exe -m experiments.round2.session all
```

Ở mỗi lượt, xem hướng dẫn và điểm mốc trong cửa sổ camera rồi nhấn SPACE khi đã sẵn sàng. Công cụ mở lại camera, chờ 3 giây và ghi 360 khung nguyên bản. Thực hiện nhiệm vụ đến khi cửa sổ trở về xem trước lượt tiếp theo. Ba lượt đứng yên, ba lượt chuyển động ngang chậm, ba lượt đứng yên với ánh sáng phía trước giảm. Khi hoàn thành chín video, công cụ đóng camera và tự phân tích.

Trong lúc ghi, không hiển thị trạng thái nhận tay cũ như trạng thái đang đo. Dữ liệu ghi giữ nguyên toàn bộ ảnh, kể cả khung không nhận được tay. Trạng thái nhận tay và CLAHE dùng để kết luận được tính từ replay sau khi thu.

ESC hoặc Q dừng. Đóng cửa sổ cũng dừng. Video đang ghi dở được hủy; video đã hoàn thành giữ nguyên. Tiếp tục phiên dở bằng đường dẫn đã in:

```powershell
.\.venv-research\Scripts\python.exe -m experiments.round2.session all --session '<đường dẫn phiên>'
```

Tách bước nếu cần: `prepare`, `collect --session ...`, `analyze --session ...`. `prepare` không mở camera. Backend/index khác phải chọn khi chuẩn bị phiên bằng `--backend dshow` hoặc `--camera-index 1`; không thay ngầm sau khi khóa kế hoạch.

Mỗi phiên giữ kế hoạch, manifest, thông tin môi trường, mã băm Core/config/model, các lượt xem trước, xác nhận bố trí, video+JSON+dấu thời gian thu, replay logs, batch indexes và kết quả phân tích. Việc đổi kế hoạch, mã nghiên cứu, cấu hình hoặc mô hình sau khi chuẩn bị khiến công cụ từ chối tiếp tục phiên đó. Môi trường chạy phải được giữ theo `environment.lock.txt`; khác Python hoặc phụ thuộc phải lập phiên riêng và ghi rõ.

Core ở main đã vượt 433 kiểm thử trong môi trường riêng trước khi bổ sung công cụ. Số liệu kiểm thử không phải bằng chứng cải thiện thuật toán; kết luận nghiên cứu chờ dữ liệu và phân tích ROUND2.

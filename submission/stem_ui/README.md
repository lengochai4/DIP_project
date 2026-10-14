# UI nộp đồ án — phần ứng dụng riêng

Chạy ở thư mục gốc với môi trường đã cài `.[dev,demo3d]`:

```powershell
.\.venv-research\Scripts\python.exe -X utf8 -m submission.stem_ui.app
```

Hoặc chạy `Chay_UI.ps1`. Camera chỉ mở sau khi bấm **Mở camera**. Nếu camera
bận, đóng ứng dụng đang dùng camera rồi thử lại; có thể đổi Camera 0–3 khi
đang dừng. Không có phiên tay mới bắt buộc khi chạy kiểm tra tự động.

## Cách thao tác

- **Khối 3D**: chụm cái–trỏ để giữ. Khi giữ một tay, di chuyển tay để dời
  khối, xoay lòng bàn tay để xoay khối. Thả chụm để buông, khối giữ trạng thái.
- **Hai tay cùng chụm**: tách/khép hai tay để đổi kích thước, vặn đường nối
  hai tay để xoay, di chuyển điểm giữa để dời khối. Thêm/bỏ một tay sẽ đặt
  lại mốc giữ ở trạng thái hiện tại, tránh nhảy.
- **Đầu ngón**: các đầu ngón duỗi của một hoặc hai tay tạo đỉnh sống tự động.
  Không cần thêm điểm. Một đỉnh là điểm, hai đỉnh nối đoạn, từ ba đỉnh tạo
  mặt và khối có độ dày minh họa. Các điểm nằm trong đường bao vẫn giữ nút.
- Có lập phương, tứ diện, bát diện, cầu. Menu khối và phím 1–4 chọn vật thể.
- Kéo chuột đổi góc nhìn, cuộn thu/phóng, R đặt lại; Tab đổi chế độ;
  H ẩn/hiện hướng dẫn; C ẩn/hiện camera; F11 phóng to/thu nhỏ; Enter mở/dừng.

## Phạm vi và độ tin cậy

UI này viết mới từ nhánh Core đã chốt, không dùng nhánh UI cũ. OpenGL có
phối cảnh, kiểm tra độ sâu, các mặt và ánh sáng. Camera xử lý tuần tự trên
một worker; giao diện đọc snapshot mới nhất, không xếp hàng các hình cũ.
Mesh khối được biên dịch trước và nhãn lặp lại được cache để giảm việc vẽ.

Mỗi tay có bộ lọc F2 và trạng thái cử chỉ riêng, dùng thành phần Core công
khai không sửa công thức. Ghép tay theo vị trí lòng bàn tay, không theo thứ
tự kết quả detector; trường hợp mơ hồ hoặc đổi danh tính bị trung tính hóa.
Mất tay/xuất hiện lại không sinh xung giữ hay chuyển động từ trạng thái cũ.

Điểm x/y và hình camera dùng cùng phép mirror; overlay camera có letterbox,
không kéo giãn sai tỷ lệ. Khối đầu ngón tự vừa khung 3D. Giá trị z là tương
đối của mô hình; độ dày khối do trình bày thêm. Xoay lòng bàn tay là hướng
minh họa từ hình học điểm mốc; chuyển vị trí dùng mặt phẳng x/y, không gọi
là vị trí vật lý của tay trong không gian. Hai tay của cùng một người không
phải chức năng nhiều người dùng.

Nhận ngón duỗi dùng góc khớp và hysteresis, là quy tắc trình bày có thể sai
khi bị che, ngón ở sát nhau hoặc góc nhìn khó. Không có cam kết nhận đủ mọi
ngón trong mọi khung hình. Các tham số UI nằm trong settings.yaml; metadata
ghi lại cấu hình. Camera và dữ liệu ghi từ nghiên cứu không bị thay đổi.

Đã chạy 18 kiểm tra tự động mới và toàn bộ 472 kiểm tra đạt. Camera vật lý
đã mở, xử lý 10 khung và đóng sạch. Smoke nguồn đã ghi có một tay; smoke
ảnh ghép có hai hình tay đi qua provider thật và ghi nhận tối đa 10 đầu
ngón duỗi. Đã kiểm tra đổi bốn khối, ẩn/hiện camera và hướng dẫn, resize,
phóng to rồi khôi phục. Chế độ phóng to dùng cửa sổ không viền bằng kích
thước desktop để tránh lỗi chuyển độ phân giải độc quyền trên Windows.

Metadata và nhật ký riêng nằm ở `runs/ui/<run_id>`; mặc định không lưu video.
Nhật ký UI không tương đương schema thực nghiệm một tay G7/ROUND2. Các
kết quả Core trong báo cáo giữ nguyên, không gộp dữ liệu UI vào chúng.

Tham khảo hành vi giữ/thả và phối hợp hai tay từ Unity XR Interaction Toolkit:
https://docs.unity.cn/Packages/com.unity.xr.interaction.toolkit%403.6/manual/xr-grab-interactable.html
Đây là tham khảo thiết kế tương tác, không tích hợp Unity hoặc giả lập camera
chiều sâu của kính VR.

## Kiểm tra bằng nguồn đã ghi

```powershell
.\.venv-research\Scripts\python.exe -m pytest tests/submission -q
.\.venv-research\Scripts\python.exe -m submission.stem_ui.app --replay <video.avi> --mode tips --smoke-frames 60 --screenshot runs/ui-smoke/check.png
```

Smoke hai tay bằng ảnh ghép đối xứng chỉ kiểm tra đường nhận dạng và dựng
hình với đầu vào có hai hình tay. Nó không thay thế kiểm chứng hai tay thật
đồng thời trên nhiều tư thế. Báo cáo phạm vi kiểm tra đúng theo nguồn đã chạy.

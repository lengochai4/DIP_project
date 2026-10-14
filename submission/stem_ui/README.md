# UI nộp đồ án — phần ứng dụng riêng

Chạy ở thư mục gốc với môi trường đã cài `.[dev,demo3d]`:

```powershell
.\.venv-research\Scripts\python.exe -X utf8 -m submission.stem_ui.app
```

Hoặc nhấp đúp `Chay_UI.bat`, hay chạy `Chay_UI.ps1` trong PowerShell.
Camera chỉ mở sau khi bấm **Mở camera**. Nếu camera
bận, đóng ứng dụng đang dùng camera rồi thử lại; có thể đổi Camera 0–3 khi
đang dừng. Không có phiên tay mới bắt buộc khi chạy kiểm tra tự động.

## Cách thao tác

- **Khối 3D**: chụm cái–trỏ để giữ. Khi giữ một tay, di chuyển tay để dời
  khối, xoay lòng bàn tay để xoay khối. Thả chụm để buông, khối giữ trạng thái.
- **Hai tay cùng chụm**: tách/khép hai tay để đổi kích thước, vặn đường nối
  hai tay để xoay, di chuyển điểm giữa để dời khối. Thêm/bỏ một tay sẽ đặt
  lại mốc giữ ở trạng thái hiện tại, tránh nhảy.
- Nút **2 tay: cỡ đều** đổi chế độ (hoặc phím S): **cỡ đều**, **kéo dãn**,
  **1 tay: đổi cỡ**. Kéo dãn dùng hai tay để kéo một chiều của khối; không
  phóng đồng đều cả ba chiều. Chế độ một tay đổi cỡ dùng kích thước lòng
  bàn tay trong ảnh: giữ chụm, hướng lòng tay về camera rồi đưa gần/xa.
  Đây là thay đổi kích thước biểu kiến, không phải đo khoảng cách camera.
- Vòng vàng và chữ **GIỮ** ở từng tay báo đã bắt được thao tác. Thu/phóng
  hai tay chỉ bắt đầu khi cả hai tay đều báo giữ. Mở ngón để buông. Thông
  báo phía trên cảnh cho biết đang giữ một/hai tay, đang buông hay tạm mất tay.
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

Sửa liên tục thao tác: nhận chụm riêng cho UI với ngưỡng vào/ra và thời gian
xác nhận; mất dấu ngắn đóng băng vật thể, không dự đoán tay bị mất. Tay trở
lại được gắn mốc mới tại trạng thái đang giữ. Thay danh tính, mất lâu, dừng
camera hoặc ảnh cũ sẽ kết thúc giữ. Khi đang mở ngón để buông, vật thể cũng
được đóng băng để việc tách hai đầu ngón không làm nó nhảy.

Input chỉ cập nhật đích; vị trí, quaternion xoay và kích thước được làm
mượt ở mỗi khung vẽ, độc lập tốc độ camera. Các đầu ngón và cách vừa khung
cũng có làm mượt trình bày riêng. Bộ lọc ứng dụng dùng giá trị cấu hình riêng
ở filter_overrides để giảm độ chậm đáp ứng. Công thức F2 không đổi, nhưng
các giá trị này **khác profile F2 nghiên cứu**, được ghi dưới điều kiện
UI_INTERACTION; không đưa vào số liệu báo cáo G7/ROUND2 và không gọi là tối ưu
đã đo được. Profile/config/mã Core nghiên cứu vẫn nguyên vẹn.

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

Đợt UI đầu có 18 kiểm tra mới, toàn bộ 472 kiểm tra đạt. Camera vật lý
đã mở, xử lý 10 khung và đóng sạch. Smoke nguồn đã ghi có một tay; smoke
ảnh ghép có hai hình tay đi qua provider thật và ghi nhận tối đa 10 đầu
ngón duỗi. Đã kiểm tra đổi bốn khối, ẩn/hiện camera và hướng dẫn, resize,
phóng to rồi khôi phục. Chế độ phóng to dùng cửa sổ không viền bằng kích
thước desktop để tránh lỗi chuyển độ phân giải độc quyền trên Windows.

Đợt sửa liên tục giữ/thu-phóng/kéo dãn có tổng 33 kiểm tra UI và toàn bộ
487 kiểm tra đạt. Kiểm tra tổng hợp đưa 205 khung qua bộ vẽ OpenGL và xác
nhận phóng lớn, thu nhỏ, kéo dãn một trục, đóng băng khi mất tay ngắn và
đóng sạch. Nguồn một tay đã ghi và nguồn ghép hai tay cũng chạy lại qua
provider thật. Các kiểm tra này không chứng minh độ chính xác mọi cử chỉ,
không đo độ trễ tay–màn hình và không chứng nhận tương đương kính VR.

Metadata và nhật ký riêng nằm ở `runs/ui/<run_id>`; mặc định không lưu video.
Nhật ký UI không tương đương schema thực nghiệm một tay G7/ROUND2. Các
kết quả Core trong báo cáo giữ nguyên, không gộp dữ liệu UI vào chúng.

Tham khảo hành vi giữ/thả và phối hợp hai tay từ Unity XR Interaction Toolkit:
https://docs.unity3d.com/Packages/com.unity.xr.interaction.toolkit@3.0/manual/xr-grab-interactable.html
Làm mượt độc lập tốc độ cập nhật, vị trí/xoay/kích thước và chuyển một/hai tay:
https://learn.microsoft.com/en-us/windows/mixed-reality/mrtk-unity/mrtk2/features/ux-building-blocks/object-manipulator?view=mrtkunity-2022-05
Nguyên tắc cân bằng jitter/lag khi đặt tham số 1-Euro:
https://gery.casiez.net/1euro/
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

Nhật ký phiên mới bổ sung hand_states (thế hệ tay và tỷ lệ chụm UI) trong
frames.jsonl, và trạng thái giữ, kích thước/kéo dãn trong interactions.jsonl.
Các giá trị là trạng thái ứng dụng; không phải tracking confidence hay số
liệu đánh giá nghiên cứu. Không cần ghi video để đối chiếu thao tác.

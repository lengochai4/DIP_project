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
  hai tay để xoay và nghiêng hai lòng tay để xoay ra khỏi mặt phẳng màn hình;
  di chuyển điểm giữa để dời khối. Thêm/bỏ một tay sẽ đặt
  lại mốc giữ ở trạng thái hiện tại, tránh nhảy.
- Nút **2 tay: cỡ đều** đổi chế độ (hoặc phím S): **cỡ đều**, **kéo dãn**,
  **1 tay: đổi cỡ**, **1 tay: tiến/lùi**. Kéo dãn dùng hai tay để kéo một chiều của khối; không
  phóng đồng đều cả ba chiều. Chế độ một tay đổi cỡ dùng kích thước lòng
  bàn tay trong ảnh: giữ chụm, hướng lòng tay về camera rồi đưa gần/xa.
  Đây là thay đổi kích thước biểu kiến, không phải đo khoảng cách camera.
- **1 tay: tiến/lùi**: giữ chụm và hướng lòng tay về camera; đưa tay gần/xa
  để đẩy/kéo khối trong cảnh theo hướng nhìn. Kích thước khối giữ nguyên,
  hình trên màn hình thay đổi theo phối cảnh. Đây là ánh xạ từ kích thước
  lòng tay biểu kiến, không đo chiều sâu thật. Hai tay vẫn đổi cỡ như mặc định.
- Vòng vàng và chữ **GIỮ** ở từng tay báo đã bắt được thao tác. Thu/phóng
  hai tay chỉ bắt đầu khi cả hai tay đều báo giữ. Mở ngón để buông. Thông
  báo phía trên cảnh cho biết đang giữ một/hai tay, đang buông hay tạm mất tay.
- **Đầu ngón**: các đầu ngón duỗi của một hoặc hai tay tạo đỉnh sống tự động.
  Không cần thêm điểm. Một đỉnh là điểm, hai đỉnh nối đoạn, từ ba đỉnh tạo
  mặt; các đỉnh không đồng phẳng tạo hình bao 3D. Khi đầu ngón gần đồng phẳng,
  thêm độ dày minh họa theo mặt phẳng tay, có dòng trạng thái phân biệt.
  Các điểm nằm trong đường bao vẫn giữ nút. Khớp và xương ngón có thể tích,
  ánh sáng và kiểm tra độ sâu giúp thấy hướng gập/duỗi. Khung giữ mốc trong
  phiên tay liên tục để chuyển động và thay đổi cỡ tay không bị tự căn mất.
- Có lập phương, tứ diện, bát diện, cầu. Menu khối và phím 1–4 chọn vật thể.
- Kéo chuột đổi góc nhìn, cuộn thu/phóng, R đặt lại; Tab đổi chế độ;
  H ẩn/hiện hướng dẫn; C ẩn/hiện camera; F11 phóng to/thu nhỏ; Enter mở/dừng.

## Phạm vi và độ tin cậy

UI này viết mới từ nhánh Core đã chốt, không dùng nhánh UI cũ. OpenGL có
phối cảnh, kiểm tra độ sâu, các mặt, ánh sáng và bóng trên mặt sàn minh họa.
Camera có một luồng sở hữu mở/đọc/đóng; chỉ giữ một ảnh chờ mới nhất. Luồng
xử lý nhận các ảnh đó theo thứ tự thời gian; ảnh chưa xử lý có thể bị bỏ nếu
không theo kịp. Số ảnh bỏ và thời gian chờ được ghi lại. Replay giữ toàn bộ
thứ tự ảnh, không dùng cơ chế bỏ ảnh này. Giao diện đọc snapshot mới nhất.
Mesh khối/khớp/xương được biên dịch trước; nhãn và ảnh preview được cache.
Surface/texture tái sử dụng, UI cập nhật riêng ở overlay_fps, trong khi khối
vẫn đi theo tay ở mỗi khung vẽ. Hình cầu có mặt kín và pháp tuyến trơn.

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
mượt ở mỗi khung vẽ, độc lập tốc độ camera. Khi sai khác với đích lớn, tốc độ
bám tăng trong giới hạn cấu hình; không dự đoán tay bị mất hoặc tạo quán tính
sau thả. z của hướng lòng tay có làm mượt riêng trong ứng dụng. Core vẫn
giữ nguyên z đầu ra. Bộ lọc ứng dụng dùng giá trị cấu hình riêng
ở filter_overrides để giảm độ chậm đáp ứng. Công thức F2 không đổi, nhưng
các giá trị này **khác profile F2 nghiên cứu**, được ghi dưới điều kiện
UI_INTERACTION; không đưa vào số liệu báo cáo G7/ROUND2 và không gọi là tối ưu
đã đo được. Profile/config/mã Core nghiên cứu vẫn nguyên vẹn.

Điểm x/y và hình camera dùng cùng phép mirror; overlay camera có letterbox,
không kéo giãn sai tỷ lệ. Khối đầu ngón vừa khung khi bắt đầu phiên; thêm/bớt
tay hoặc gập hết ngón không căn lại liên tục. Giá trị z là tương
đối của mô hình; độ dày khối do trình bày thêm. Xoay lòng bàn tay là hướng
minh họa từ hình học điểm mốc; chuyển vị trí dùng mặt phẳng x/y, không gọi
là vị trí vật lý của tay trong không gian. Không dùng z để đo khoảng cách
giữa hai bàn tay; hình bao chung là minh họa. Hai tay của cùng một người không
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

Đợt không gian/độ trễ bổ sung có 50 kiểm tra UI và toàn bộ 504 kiểm tra đạt;
vòng đổi chế độ đi qua đủ bốn thao tác. Kiểm tra OpenGL 130
khung tổng hợp xác nhận nghiêng hai tay ra ngoài mặt phẳng, tiến/lùi, hình
bao 3D và khung ổn định. Camera thật nhận 12 snapshot và đóng sạch, không
đòi người dùng thao tác. Nguồn ghép hai tay đi qua provider thật nhận tối đa
10 đầu ngón trong 60 khung quan sát. Số khung trên là phạm vi smoke thực chạy,
không phải đo tốc độ, độ chính xác hay độ trễ vật lý. Nhật ký schema 3 ghi
chính sách nhận ảnh, số ảnh camera bỏ, chờ hàng đợi và trạng thái dựng hình.

MediaPipe đã dùng mô hình học sâu nhận lòng bàn tay/điểm mốc. Đợt này không
thêm mạng mới hoặc dữ liệu huấn luyện. Tham khảo nguồn chính thức về chạy
video/live và ý nghĩa tọa độ:
https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/python
Tách xoay, dịch chuyển, cỡ và làm mượt theo MRTK3:
https://learn.microsoft.com/en-us/windows/mixed-reality/mrtk-unity/mrtk3-spatialmanipulation/packages/spatialmanipulation/object-manipulator

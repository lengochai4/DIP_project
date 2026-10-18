# UI nộp đồ án — phần ứng dụng riêng

Máy mới: xem **[HUONG_DAN_CHAY.md](../../HUONG_DAN_CHAY.md)**. Cài một lần bằng
`python -X utf8 -m submission.setup_ui` với Python >=3.11 64-bit, sau đó chạy:

```powershell
.\.venv-ui\Scripts\python.exe -X utf8 -m submission.stem_ui.app
```

Các lệnh `.venv-research` và số kiểm tra ở cuối tài liệu là hồ sơ môi trường
phát triển. Môi trường nộp mới dùng `.venv-ui`, thư viện giải theo `pyproject.toml`;
snapshot 3.12 chỉ áp dụng nếu cài bằng `--locked`.

Chạy ở thư mục gốc với môi trường đã cài `.[dev,demo3d]`:

```powershell
.\.venv-research\Scripts\python.exe -X utf8 -m submission.stem_ui.app
```

Hoặc nhấp đúp `Chay_UI.bat`, hay chạy `Chay_UI.ps1` trong PowerShell.
Camera chỉ mở sau khi bấm **Bật camera**. Nếu camera
bận, đóng ứng dụng đang dùng camera rồi thử lại; có thể đổi Camera 0–3 khi
đang dừng. Không có phiên tay mới bắt buộc khi chạy kiểm tra tự động.
Nút **DroidCam** mở hộp nhập **Wi-Fi IP** và **Port** đang hiện trên ứng dụng
DroidCam ở điện thoại. Port mặc định là `4747`; UI kết nối trực tiếp tới
`http://IP:PORT/video`, không cần đoán camera index của Windows. IP/port hợp lệ
được lưu cục bộ vào `runs/ui/droidcam.json` để lần sau không phải nhập lại.
Nút **Dùng webcam máy** trong cùng hộp chuyển ngược về webcam. Khi đổi nguồn,
app luôn yêu cầu worker/camera cũ dừng hẳn rồi mới mở nguồn mới, nên không có
hai capture session chạy chồng. Đây chỉ là đổi nguồn RGB đầu vào; preprocessing,
tracking, filter, gesture và logic 3D/chemistry giữ nguyên.

## Cách thao tác

Thư viện **Mẫu phân tử 3D** có 32 mẫu, chia 4 trang; dùng **Trang trước/Trang sau**
để chọn. Nhận tên dựa trên đồ thị liên kết, phân biệt etanol và đimetyl ete cùng
công thức C₂H₆O. Vị trí là hình học minh họa; không tính phản ứng/năng lượng.
Panel AR tái sử dụng texture khi chỉ di chuyển/trỏ qua nguyên tử; thông tin
nguyên tố, trang và các điều khiển đổi thì cập nhật ngay. Nhận pinch dùng gate
nhẹ riêng; các ngưỡng chụm/nhả và thời gian xác nhận không đổi.

### Hóa học AR — panel và vật thể trực tiếp trên hình camera

Chọn **Hóa học AR** (hoặc P). Camera là nền của cảnh; panel có phối cảnh
và nằm trong cùng cảnh với các nguyên tử, không phải một cửa sổ webcam nhỏ.
Khi mới vào, panel có nút **Bảng nguyên tố**. Trỏ ngón trỏ lên ô và giữ
liên tục khoảng **1 giây**; vòng và thanh tiến trình báo đang chọn. Đi ngang
qua ô không kích hoạt. Sau khi chọn, cần di chuyển rõ sang vùng khác hoặc
rời mục tiêu trước khi chọn lần nữa; đổi trang không tự nhấn tiếp nút mới
dưới cùng vị trí ngón. Mất tay hoặc ngắt thời gian hủy tiến trình. Chuột
vẫn chọn/kéo trực tiếp làm cách dự phòng.

1. Chọn H, C, N, O, F, P, S, Cl trong bảng thường dùng hoặc mở bảng tuần
   hoàn đầy đủ 118 nguyên tố. Mỗi lượt chọn tạo một nguyên tử ở vùng thao tác.
2. Bật **Ghép/tách**, chụm sát cái–trỏ ngay trên nguyên tử để kéo nó. Thả gần nguyên
   tử khác để ghép liên kết được hỗ trợ; kéo xa để tháo liên kết. Nút
   **Liên kết 1/2/3** (phím S) chọn bậc của liên kết mới.
3. Đổi sang **Cầm cả khối** để dời/xoay cả thành phần liên thông. Hai tay
   thao tác: tay đầu cầm nguyên tử/phân tử, tay còn lại chụm trong vùng trống
   của cảnh rồi tách/khép để đổi cỡ; vặn/nghiêng để xoay cả khối. Tay thứ hai
   không cần bắt lại một nguyên tử nhỏ. Trong
   Ghép/tách, hai tay có thể kéo hai nguyên tử khác nhau độc lập.

**Nguyên tử / e** (O) hiện lớp electron minh họa cho nguyên tử đang chọn.
Đổi cỡ bằng hai tay dùng **Cầm cả khối**: hạt nhân, vòng electron và các
electron cùng đổi cỡ. Có thể bắt trong vùng lớp e đang hiện. **Về giữa cảnh**
tính cả kích thước lớp e khi thu mô hình quá lớn về khung. Trong Ghép/tách,
hai tay kéo từng nguyên tử riêng; chuyển sang Cầm cả khối để thu/phóng.
Thông tin là của nguyên tử trung hòa riêng lẻ, không phải orbital phân tử
hay đường đi electron. Panel ghi Z, số proton/electron và cấu hình nguồn;
không tự đoán số neutron. Mẫu 3D có H₂O, CO₂, CH₄, NH₃, H₂, O₂, N₂, HCl.
Tên mẫu được đối chiếu đồ thị liên kết; công thức cùng số nguyên tử chưa
đủ để gọi tên phân tử. Hình học do người dùng kéo và tọa độ mẫu chỉ minh họa.

**Thu bảng** (B) giữ một nút nhỏ trong cảnh để mở lại. **Về giữa cảnh** (R)
đưa vật thể bị kéo ra ngoài về vùng thao tác. H ẩn/hiện hướng dẫn trong
panel. Hoàn tác/làm lại dùng Z/Y; Backspace xóa nguyên tử đang chọn trong
Ghép/tách, hoặc cả thành phần liên thông trong Cầm cả khối.

**Lưu / Mở đã lưu** (L/J) dùng `runs/ui-chemistry/workspace.json` trên máy.
Lưu gồm nguyên tử, vị trí ở đơn vị cảnh và liên kết; không lưu video. Bản
mở được kiểm tra trước khi thay không gian hiện tại. Chuyển chế độ vẫn giữ
không gian đang xây. Mất tay/dừng camera kết thúc thao tác mà không tự ghép.
Mất dấu ngắn đóng băng nguyên tử; nhận lại tay gắn mốc mới, không nhảy.
Ngưỡng vào/ra riêng giúp chụm sát để bắt nhưng không buông vì dao động nhỏ;
mở ngón rõ và liên tục mới buông. Đây là nhận dạng độ gần trong ảnh, không
phải cảm biến xác nhận hai đầu ngón thật sự tiếp xúc.

## Giao diện mới theo mẫu thiết kế

Ba chế độ và chức năng lưu/hoàn tác/ghép/tách được giữ. Thanh tác giả hiển thị
đúng ba tên và MSSV; bố cục xuống dòng ở cửa sổ nhỏ để không chồng nút.
Panel kính có sắc xanh bạc, hơi trong suốt; nút/chữ có nền tương phản và
nguyên tử dùng khối cầu nhiều mặt với vật liệu bóng. H ẩn/hiện hướng dẫn,
C ẩn/hiện camera phụ; nút Phóng to và F11 dùng cùng đường chuyển trạng thái,
Esc trả về kích thước cửa sổ trước đó khi đang phóng to.

UI chỉ hiện trạng thái camera/tay, hướng dẫn thao tác và thông tin khoa học
cần cho bài học. FPS, CLAHE, ROI, tham số lọc và số đo xử lý nằm trong nhật ký.
Mặt kính/mesh/chữ được cache. Tiến trình chọn vẽ trực tiếp bằng OpenGL;
không vẽ và tải lại cả ảnh bảng 118 nguyên tố để chạy thanh tiến trình.

Giới hạn: đây là camera-composited AR minh họa trên một webcam RGB. Panel
neo theo cảnh hiển thị; app không định vị phòng, đo chiều sâu, biết tay đang
che vật thể hay mô phỏng phản ứng. Ghép/tách không làm đổi nguyên tố. Các
giới hạn cộng hóa trị trung hòa trong settings không thay thế kiểm chứng
hóa học tổng quát; nguyên tố khác vẫn xem được nhưng không đoán liên kết.

Luồng tham khảo Nanome Builder/Periodic Table và Microsoft hand interaction:
https://help.nanome.ai/nanome_v2/toolspanel
https://help.nanome.ai/nanome1x/navigation/toolsmenu
https://learn.microsoft.com/en-us/previous-versions/mixed-reality/mrtk-unreal/ux-tools/features/hand-interaction

Dữ liệu offline và nguồn hóa học: [data/README.md](data/README.md).
Chạy phát lại riêng với `--mode chemistry`.

### Khối và đầu ngón

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
  mặt; các đỉnh không đồng phẳng tạo hình bao 3D. Đầu ngón gần đồng phẳng tạo
  mặt ngay trên các đỉnh đó; không tự thêm đáy hay đỉnh khác. Các điểm nằm
  trong đường bao vẫn giữ nút. Mặc định chỉ hiện các đầu ngón đang duỗi,
  tránh nhầm khớp/xương của ngón gập với đỉnh hình. Khung giữ mốc trong
  phiên tay liên tục; tỷ lệ cảnh cố định, không tự phóng theo số ngón duỗi.
- Có lập phương, tứ diện, bát diện, cầu. Menu khối và phím 1–4 chọn vật thể.
- Kéo chuột đổi góc nhìn, cuộn thu/phóng, R đặt lại; Tab qua ba chế độ;
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
đối của mô hình; hình đầu ngón không tự thêm độ dày. Xoay lòng bàn tay là hướng
minh họa từ hình học điểm mốc; chuyển vị trí dùng mặt phẳng x/y, không gọi
là vị trí vật lý của tay trong không gian. Không dùng z để đo khoảng cách
giữa hai bàn tay; hình bao chung là minh họa. Hai tay của cùng một người không
phải chức năng nhiều người dùng.

Nhận ngón duỗi dùng góc khớp, độ vươn khỏi lòng tay và hysteresis, có thể sai
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

Đợt hóa học thêm các kiểm tra dữ liệu 118 nguyên tố, electron, phép chiếu
panel, ngưỡng liên kết, topology/nhãn, lịch sử, bản lưu không hợp lệ, latch
chọn bằng tay, ghép/tháo, danh tính/mất tay và một/hai tay cầm phân tử.
Kiểm tra OpenGL 179 khung dùng tay tổng hợp trên nền ảnh đã ghi đã thực hiện
mở panel, tạo H/O/H, ghép H₂O, tháo nguyên tử, hoàn tác, bảng 118, resize và
toàn màn. Nguồn ảnh ghép hai tay đi qua provider thật cũng chạy chế độ này.
Các lượt tổng hợp không chứng minh người dùng thật hoàn tất mọi cử chỉ.
Schema UI 4 ghi đồ thị hóa học và SHA dữ liệu nguyên tố, tách khỏi Core.
33 kiểm tra mới trong đợt này đạt; tổng 83 kiểm tra UI và 537 kiểm tra toàn
dự án đạt. Có cả kiểm tra bản lưu lỗi không thay thế không gian đang làm.

Đợt giao diện mới/chọn bằng giữ trỏ có 96 kiểm tra UI và 550 kiểm tra toàn
dự án đạt. OpenGL tổng hợp 697 khung xác nhận chọn/ghép/tháo/hoàn tác/bảng
118 và cửa sổ; lượt bổ sung 139 khung xác nhận tiến trình, nguyên tử có e
phóng/thu bằng hai tay, mất tay ngắn và nút/F11/Esc ở cả ba chế độ. Đã xem
ảnh bố cục 960×660, 1360×860, 1920×1080. Provider thật phát lại 60 khung của
ảnh ghép hai tay, quan sát hai tay và tối đa 10 đầu ngón, dừng sạch
(`ui-20261014-173237-405165`). Không suy ra FPS hay độ trễ tay thật từ các
lượt này. Schema UI 5 ghi thêm trạng thái dwell/claim/group thực tế trong
`chemistry_controls`; bộ dữ liệu/báo cáo Core không đổi.

Đợt sửa răng cưa/buông/đỉnh thừa: chụm và duỗi đọc điểm mốc gốc hợp lệ,
còn chuyển động dùng điểm đã lọc. Khi thấy mở ngón, vật thể đóng băng ngay
trong lúc chờ xác nhận buông; không để bộ lọc chuyển động giữ trạng thái chụm
thêm. Hình đầu ngón luôn có đúng một đỉnh cho mỗi ngón được chọn. Không thêm
đỉnh đáy hoặc hiện toàn bộ khớp ngón mặc định.

Render yêu cầu MSAA, có đường dự phòng khi không tạo được context; giá trị
thực tế ghi trong nhật ký. Windows yêu cầu DPI awareness trước khi mở cửa
sổ. Card/logo được vẽ lớn, thu một lần và cache; chữ bảng nổi dựng theo kích
thước pixel chiếu thực tế, có mipmap/anisotropic khi được hỗ trợ. UI tĩnh
không tải lại texture khi electron chạy; camera/tiến trình/vật thể cập nhật riêng.

Đã chạy 111 kiểm tra UI và 565 kiểm tra toàn dự án đạt. Lượt GL 76 khung tổng
hợp kiểm tra mở ngón khi điểm đã lọc vẫn chụm, đúng hai đỉnh khi chỉ hai ngón
duỗi, cache overlay và context dự phòng với lỗi được tiêm để kiểm tra. Context
mặc định trên máy báo 4 mẫu; context dự phòng báo 0. Lượt 139 khung kiểm tra
lại cửa sổ/chọn/thu-phóng và lượt 697 khung kiểm tra đồ thị hóa học. Provider
thật phát lại 60 khung nhận hai tay/tối đa 10 đầu ngón, dừng sạch
(`ui-20261014-175453-431303`). Schema UI 6 ghi cơ sở trạng thái ngón là raw hợp
lệ và hình chỉ dùng đỉnh quan sát; không sửa dữ liệu/báo cáo Core. Đây không
phải phiên thao tác thật mới hay số đo độ trễ vật lý.

Tham khảo render:
https://www.pygame.org/docs/ref/display.html
https://wiki.libsdl.org/SDL2/SDL_HINT_WINDOWS_DPI_AWARENESS
https://wikis.khronos.org/opengl/Multisample

Tham khảo tiến trình và hủy dwell:
https://learn.microsoft.com/en-us/windows/mixed-reality/design/gaze-and-dwell
Đây là áp dụng phản hồi dwell cho trỏ bằng ngón, không nhận ánh mắt.

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

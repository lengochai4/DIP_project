# Checklist rà soát UI nộp đồ án

## Hai tab đầu và hồi quy bốn tab — 18/10/2026

- UI schema 20: **1084 test qua trên Python 3.11.9 và 3.12.14**, thêm 55 ca.
  Sau chỉnh tương phản nhãn, chạy lại **77 ca** trình bày/native/buông tay: qua.
- Bảng bốn khối: xòe tay ở mép, nhắm lại, dwell 1 giây/chụm chọn; giữ nguyên
  pose/cỡ/kéo dãn. Kiểm tra ưu tiên cầm, mất dấu, đổi nhận dạng, thời gian,
  đổi nguồn/khung hình, chặn chọn/cầm xuyên, đóng bằng chuột và cả hai tay.
- Đầu ngón: phân loại điểm/đoạn/mặt/khối theo hình hiện có; số đỉnh từng tay;
  phép chiếu đối chiếu ma trận độc lập, nhãn nhỏ có nền tương phản và bám theo
  render. Hình vẫn chỉ dùng đỉnh quan sát, không tự thêm độ dày/đỉnh.
- UI tĩnh hai tab đầu không tải lại theo mỗi ảnh; preview/xương tay dùng
  texture nhỏ tái sử dụng. Kiểm tra cấp phát/cập nhật/đổi cỡ/xóa context và
  cache, cả khi camera phụ bật/tắt. Không thay ngưỡng/lọc chuyển động cũ.
- Native QA 320 frame, bốn kích thước 640×600 đến 1360×860, cả bốn tab,
  tám bài Vật lý, camera phụ, bảng hai mép và F11: không lỗi GL/chồng nút.
  App thật phát lại 30 frame qua MediaPipe cho mỗi tab, dừng worker sạch,
  nhật ký schema 20 đọc được. Artifact cục bộ: `runs/solid-palette-qa`.
- Core, profile nghiên cứu, code Hóa học, mô hình/catalog Vật lý và bộ nhận
  cầm dùng chung không thay đổi. Các ca giả lập/phát lại không chứng minh
  tỷ lệ nhận đúng tay thật hay không lag ở mọi webcam/máy.

## Nhánh phát triển Vật lý sau vấn đáp — 18/10/2026

Lượt đường tắt UI schema 19: **1029 test qua trên Python 3.11.9 và 3.12.14**,
gồm 57 ca thêm cho gọi lệnh bằng xòe tay, bảng nhanh có nhắm lại, hai tay
chụm vùng trống, chặn cầm xuyên và hủy khi mất dấu/đổi nhận dạng. Native
GL thực hiện cả hai đường tắt; QA 780 frame ở bốn kích thước, tám bài và
F11 khi bảng nhanh mở đều không báo lỗi GL. App replay 30 frame và xuất/mở
bốn tệp đều qua. Catalog/model 3/Core/Hóa học giữ nguyên; không suy tỷ lệ
nhận đúng hoặc tốc độ tay thật từ test giả lập.

Lượt nâng cấp tương tác sau rà công thức: **972 test qua trên Python 3.11.9
và 3.12.14**. UI schema 18, model revision 3. Đã kiểm tra cầm thân vật,
tay nắm vận tốc/khối lượng/đích, thả để chạy có điều kiện, hoàn tác/hủy,
hai tay xem cảnh và các trường hợp mất dấu/chuyển số tay/đổi ngữ cảnh.
Native QA 676 frame, bốn kích thước, tám bài, F11 không báo lỗi GL; xuất/mở
bốn tệp và app replay 30 frame đều hoàn tất. Chi tiết và giới hạn bằng chứng:
[PHYSICS_AUDIT.md](PHYSICS_AUDIT.md). Các số dưới đây là lượt triển khai đầu.

Nhánh `feat/physics-lab` kế thừa Hóa học `825ac93`; không thay bản main/tag nộp
16/10. Tám bài cơ học có mô hình SI độc lập, tham số/giả thiết/nguồn trong
`physics_labs.yaml`; mô hình là các trường hợp lý tưởng có giới hạn.

- **867 test đạt trên Python 3.11.9 và 3.12.14**, gồm 78 kiểm tra Vật lý mới.
  Có nghiệm ném/rơi, dừng/đổi chiều ma sát, bảo toàn động lượng/năng lượng,
  con lắc góc lớn, lò xo có cản, mômen, quan hệ lực–đường đi–công ròng rọc,
  biên tham số, bước thời gian và dữ liệu nhập sai.
- Kiểm tra chọn một lần, mở/nhắm lại, hai tay sở hữu riêng tay nắm, mất tay
  không sinh cú ném, rebase, đo SI không đổi khi zoom, phân trang thông số/
  công cụ/hướng dẫn. Kiểm tra native Windows render 8 bài, bảng chọn bằng
  tay giả lập, thu/mở, HUD đổi bài ngay và F11 khôi phục.
- QA bổ sung 652 frame cảnh/công cụ ở bốn kích thước, 1130 frame thao tác
  giả lập ở ba kích thước; GL không báo lỗi. Có thử khung 768×520, bật
  preview camera, kéo bảng/thông số và mất tay. Đã xem ảnh đại diện.
- App chạy phát lại thật qua MediaPipe, 30 frame mỗi interpreter; có ảnh,
  worker dừng sạch, không báo lỗi. Không thu phiên tay mới hay suy tỷ lệ
  nhận diện từ dữ liệu giả lập. Artifact giữ cục bộ tại `runs/physics-qa/`.
- Bộ kiểm tra cài Python 3.11 đạt, pip không báo hỏng phụ thuộc; kiểm đủ
  catalog 8 bài. Không thêm dependency mới.
- Xuất JSON/CSV có cấu hình/giả thiết/nguồn và dữ liệu SI mô phỏng; giữ
  lượt A độc lập, ghi khác thời điểm/lịch sử lực. Dữ liệu này không phải
  số liệu thực nghiệm DIP Core. Không sửa Core, filter, replay, dữ liệu
  báo cáo hoặc logic Hóa học đã chốt.
- Chỉ stage source/docs/test thuộc task; `runs/`, môi trường và tài liệu
  cá nhân không vào commit. Chưa xác nhận độ ổn định tay thật trên nhiều
  máy hoặc mức sẵn sàng thương mại.

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

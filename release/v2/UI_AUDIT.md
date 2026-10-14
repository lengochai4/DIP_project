# Rà soát giao diện và chức năng V2 — 2026-10-03

Phạm vi: mã nguồn V2 hiện tại, 7 trang, 9 lab, WORLD/HAND, chuột/phím/cử chỉ,
hiệu chuẩn, trạng thái camera, renderer, log cục bộ và công cụ đóng gói. Đây là
rà soát kỹ thuật với kiểm thử tự động và ảnh giao diện tổng hợp; không phải
chứng nhận bảo mật, kiểm thử xâm nhập hay nghiệm thu sử dụng với tay thật.

## Các vấn đề xác nhận được và đã sửa

| Nhóm | Điểm yếu trước khi sửa | Hành vi hiện tại |
| --- | --- | --- |
| Phím tắt | R/M/H/Space tác động scene khi ở trang khác | Lệnh scene chỉ áp dụng trong Explore |
| Điều khiển native | Space/Enter có thể giành phím của nút; mũi tên giành phím danh sách | Nút và danh sách giữ thao tác bàn phím native |
| Hiệu chuẩn | Kết quả cũ còn sau recapture; pinch bị ngắt có thể được tính hoàn tất khi nhả lại | Làm mới kiểm tra theo tham chiếu; mất tracking hủy chu kỳ đang kiểm tra |
| Tay chủ đạo/LEGACY | Support-only có thể vào luồng chưa đủ tay chủ đạo; LEGACY hiện nút hiệu chuẩn | Hướng dẫn chọn tay chủ đạo; vô hiệu hóa hiệu chuẩn PRODUCT trong LEGACY |
| HAND | Scene bị ẩn khi thiếu anchor nhưng vẫn nhận thao tác | Chặn thao tác scene khi chưa có anchor; hướng dẫn dùng WORLD |
| Log GUI | Lỗi mở/ghi/đóng journal chưa được chặn trong slot Qt | Giữ UI hoạt động, đánh dấu log không đầy đủ trong Analyze; không tự báo đã ghi thành công |
| Trạng thái | Home/Analyze có thể còn READY hoặc frame cũ sau Stop | Xóa trạng thái/frame cũ và hiện lý do dừng |
| Settings | Gesture labels/Diagnostics chưa ảnh hưởng hiển thị | Hai tùy chọn điều khiển nội dung hiển thị; LEGACY báo product filter không chạy |
| Renderer | Lỗi GPU sau khởi tạo chưa kích hoạt thay thế widget | Chuyển sang software, hủy clutch; có test mô phỏng lỗi muộn |
| Rectangle | Bốn điểm tùy ý đều mang tên Rectangle | Kiểm tra cạnh/góc; hình không hợp lệ báo rõ; thêm Quadrilateral |
| Optics placement | Nhận lặp cycle hoặc lệnh khi lab đã deactivate | Commit idempotent và chỉ nhận khi lab active |
| Thấu kính | Tia qua tâm bị bẻ theo tiêu cự; tọa độ probe bị cộng vị trí element hai lần | Tia tâm đi thẳng; tia song song đi qua tiêu điểm; probe dùng đúng tọa độ scene |
| Trường điện | Mẫu 3D dùng bán kính XY | Dùng bán kính XYZ; vẫn là mô hình lý tưởng, regularize gần gốc |
| Vector | Phép chiếu lên vector 0 hiện kết quả 0 gây hiểu nhầm | Báo unavailable vì vector tham chiếu bằng 0 |
| Tham số | Phase không chọn được 0; Samples nhận số lẻ; khung nhìn chưa theo biên độ/bán kính lớn | Phase chọn được 0; Samples là số nguyên; extent theo tham số phù hợp |
| Đồng bộ UI | Chuyển scene/preset/tool/tham số bằng API nội bộ có thể để selector cũ | Selector, Inspector và scene thống nhất; được kiểm tra bằng test và ảnh |
| Gói nguồn | Verifier chỉ kiểm CRC và đường dẫn | Kiểm hash từng file, manifest, file thừa và đường dẫn trùng/thoát thư mục trước khi chạy smoke |

Checksum trong manifest chỉ kiểm tính toàn vẹn; không phải chữ ký xác thực nhà
phát hành. Việc kiểm dependency ở đây là `pip check`, không phải quét CVE.

## Tiện ích nhỏ đã bổ sung

- **Reset view:** đưa hướng nhìn/zoom về mặc định, giữ bài làm và tham số.
  Reset lab được tách riêng trong Tools và hỏi xác nhận trước khi xóa bài làm.
- **Snap free points:** tùy chọn tắt mặc định, giúp dựng góc vuông bằng chuột/tay
  trên lưới của mặt phẳng dựng hình. Bước lưới mặc định 0.25 scene units nằm trong
  cấu hình; giữ nguyên các điểm bắt chính xác vào tâm atom/sphere.
- **Export measurements:** CSV tại đường dẫn người dùng chọn, chứa điểm dựng,
  khoảng cách/vector của hai điểm đầu, góc/diện tích tam giác của ba điểm đầu khi
  áp dụng. Trường hợp góc suy biến để trống. Không xuất camera, landmarks hay
  tham chiếu hiệu chuẩn. Bài làm chưa được lưu tự động qua lần thoát app.

## Phạm vi kiểm tra chức năng

| Khu vực | Bằng chứng tự động / đọc mã |
| --- | --- |
| Home, Explore, Analyze, Evidence, Calibrate, Settings, Help | Chuyển trang/render; trạng thái lỗi; shortcut và focus; Evidence đọc tài nguyên gốc |
| Coordinate | Dựng hình, tính độ dài/góc, chống commit lặp, Rectangle/Quadrilateral, grid snap và Undo |
| Molecular | Tất cả preset render dữ liệu hữu hạn; pick tâm atom; H2O/CH4 dùng định nghĩa legacy nguyên vẹn |
| Orbital | Render/update/reset; extent theo radius; mô hình động học minh họa, không mô phỏng hấp dẫn |
| Vector | Tích vô hướng/tích có hướng; phép chiếu; trường hợp vector 0 |
| Function Surface | Các preset; gradient so với sai phân; mesh mặt tam giác, contour/section |
| Wave & Signal | Các preset; phase 0, Samples nguyên, framing theo amplitude; filter response là minh họa analytic riêng |
| Vector Field | Các preset; field XYZ, regularization; hình trường chỉ là minh họa lý tưởng |
| Optics | Snell/TIR; tia thấu kính; probe/element tọa độ; idempotence và deactivate |
| Crystal Lattice | Các preset; vị trí atom không trùng; số site SC/BCC/FCC trong khối 2×2×2 đúng theo cấu trúc đã triển khai |
| Tracking/interaction | Provider/model seams; mất tay/gap/modal; manual takeover; rearm; third-hand rejection; chuột và semantic intents |
| GPU/software | GPU framebuffer depth; math chiếu/picking; fallback khi lỗi; ảnh WORLD/HAND tổng hợp |
| Delivery | Archive hash/path validation; smoke UI/model từ source đã giải nén |

Không suy ra độ chính xác ngoài đời từ việc các test này pass. Các lab đồ thị,
quang học và mặt phẳng vốn có nội dung 2D trong workspace 3D; không cần biến
chúng thành hình khối để chứng minh renderer 3D.

## Những giới hạn còn lại

1. **Tay thật, thiếu sáng và người đứng cạnh:** chưa đo mức thành công/sai kích
   hoạt của V2 trong các điều kiện này. Guard chặn khi provider báo nhiều hơn
   hai tay, không bảo đảm thấy mọi tay và không xác định hai tay thuộc cùng người.
2. **HAND:** mở lòng bàn tay một lần để lấy anchor, rồi anchor theo cùng tay còn
   được quan sát hợp lệ khi POINT/pinch. Mất tay/context vẫn hủy; không dự đoán
   anchor qua mất theo dõi. RGB/model-relative z
   không cung cấp camera depth theo mét hay phép đo cơ thể.
3. **Hiệu chuẩn support:** capture cùng tay chủ đạo khi muốn dùng thao tác hai
   tay. Thay đổi tập tay trong lúc capture có thể làm luồng cần capture lại;
   chỉ dẫn hiện tại không phải hướng dẫn onboarding đã được kiểm chứng với người mới.
4. **Thiết bị/driver:** các lượt Start/Stop tự động trước chỉ có mẫu NO_HAND.
   Nhật ký sử dụng do người dùng ghi sau đó có landmarks tay và đã được đọc để
   chẩn đoán lỗi; chưa có gán nhãn/nghiệm thu hay ma trận thiết bị/phòng học.
   Driver bị kẹt trong lời gọi capture có thể khiến shutdown phải chờ; chưa có
   cơ chế process watchdog cho camera. Source package vẫn cần Python/dependencies.
5. **Học liệu:** các mô hình dùng scene units và giả định minh họa; cần thẩm định
   nội dung giáo dục trước khi dùng để đánh giá kiến thức vật lý/hóa học chính xác.
6. **UX:** chưa đo tác vụ của người mới; giao diện còn tiếng Anh. Việc giảm nút và
   test focus không chứng minh mọi nhóm người dùng đều thao tác dễ dàng.
7. **Dữ liệu cục bộ:** không lưu raw video, nhưng có observation/intent logs chứa
   landmarks và trạng thái chuyển động. Chưa có quản lý retention/dung lượng trong
   UI. Lỗi đĩa được báo; không tự xóa log hay dữ liệu thí nghiệm để lấy chỗ trống.
8. **Renderer:** software chỉ xấp xỉ occlusion; nhãn 2D phủ lên GPU geometry và
   có thể chồng nhau. Zoom lớn có thể clip scene; không phải renderer vật lý.
9. **Recovery:** preferences JSON hỏng vẫn cần sửa/đổi tên file hoặc chọn đường
   dẫn preferences mới; chưa có trình phục hồi riêng trong UI.

## Tiện ích nên ưu tiên sau

1. **Lưu/mở workspace cục bộ:** giữ preset, tham số, điểm dựng, view; không lưu
   camera/calibration. Có version schema, validation và recovery trước khi nhận file.
2. **Onboarding ngắn và phản hồi hiệu chuẩn rõ hơn:** chỉ rõ tay nào chưa sẵn sàng,
   mất anchor và cách capture lại; bổ sung tiếng Việt theo nhu cầu lớp học.
3. **Quản lý log và chẩn đoán cục bộ:** xem dung lượng, thư mục run, chọn xóa dữ
   liệu của mình bằng hành động có xác nhận; không tác động frozen G7 evidence.
4. **Cài đặt/phục hồi thuận tiện:** app launcher/installer và xử lý preferences
   hỏng. Cần xét ma trận thiết bị trước khi gắn nhãn production/enterprise.

Đây là đề xuất tiếp theo, chưa được triển khai trong đợt audit này. Không đưa
account, cloud, telemetry hay multi-user tracking thành yêu cầu mặc định.

## Kết quả đã thực thi

- Full regression hiện tại: **697 passed**, gồm **142 test V2**; GPU depth test không skip
  trên máy này. Các test mới bao phủ lỗi xác nhận được, không mô phỏng nghiệm thu tay thật.
- Native GPU và software visual QA: **82 ảnh tổng hợp mỗi renderer**, ở hai kích
  thước yêu cầu 1280×720 / 1600×900; manifest ghi kích thước thực tế và hash ảnh.
  Đã xem trực tiếp ảnh Inspector/Wave, Optics Lens và export measurements.
- Mã Core, cấu hình G7, kết quả thí nghiệm/evidence và tag `g7-final` được giữ nguyên.
- Không yêu cầu người dùng test tay thật. Camera/hand physical acceptance của
  V2 tiếp tục deferred; các run webcam NO_HAND trước đây chỉ xác nhận camera integration.

Các thư mục QA/log/archive trong `runs/` là artifact cục bộ, không được commit.
Trạng thái kiểm tra package/format/dependencies bổ sung nằm trong `QA_STATUS.md`.

## Lượt rà soát bổ sung theo yêu cầu lặp lại — 2026-10-03

Ba nhóm lỗi mới được xác nhận bằng test tái hiện trước khi sửa:

| Vấn đề | Bản sửa và xác minh |
| --- | --- |
| Bắt đầu kéo HAND bằng chuột xóa anchor; mất anchor có thể giữ manual clutch và chặn release | Chỉ hủy ownership cử chỉ khi chuyển sang chuột, giữ presentation đang được quan sát; mất anchor hủy clutch; release luôn kết thúc lượt kéo. Xoay/zoom bàn phím và commit được kiểm tra thêm. Clear-reference vẫn xóa anchor dù có yêu cầu giữ presentation |
| Ghi CSV trực tiếp làm mất bản xuất cũ khi lỗi giữa chừng | Ghi vào file tạm riêng cùng thư mục; chỉ thay destination sau khi đóng thành công; lỗi ghi hoặc file đích bị khóa giữ nguyên bản cũ và dọn đúng file tạm của lần xuất |
| Verifier cho qua các alias như `app/../app/main.py`, tên kết thúc bằng dấu chấm/khoảng trắng và tên device Windows | Chặn path segments không canonical, ký tự không hợp lệ và reserved device names trước khi giải nén/chạy smoke |

Quy tắc tên Windows được đối chiếu với
[Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file).
Không suy ra rằng hash/kiểm đường dẫn có thể xác thực một nhà phát hành hay biến
source archive không tin cậy thành an toàn để chạy.

Lượt bổ sung thêm 15 test; full suite **697 passed**, V2 **142 passed**. Camera
không được mở trong lượt này; các giới hạn và ưu tiên tiện ích bên trên còn hiệu lực.
Rà soát trước đã chụp 82 ảnh mỗi renderer; không coi những ảnh đó là nghiệm thu
khả năng kéo HAND với người thật.

## Đối chiếu docs sau audit — 2026-10-03

Ranh giới nghiên cứu/Core/G7 vẫn giữ nguyên. Tuy nhiên, mô tả hai pinch để scale
trong đặc tả V2 chưa nêu rõ giới hạn theo mode của bản hiện tại: WORLD nhận
bimanual SCALE; HAND yêu cầu anchor từ OPEN_PALM, nên khi hai tay đều pinch,
anchor không còn và UI hủy lệnh với `HAND_ANCHOR_REQUIRED`.

Kiểm tra tổng hợp qua GUI/intent thực đã tái hiện khác biệt này; artifact tổng
hợp nằm trong `runs/docs-conformance-check`. Không mở webcam, không xác nhận
độ chính xác tay thật. Đây là giới hạn hành vi cần giải quyết hoặc được quyết
định rõ ở cấp sản phẩm, không phải căn cứ tự thay đổi yêu cầu docs để báo hoàn tất.
697 test pass không bao phủ yêu cầu scale bằng hai pinch trong HAND.

## Sửa lỗi theo ảnh và nhật ký sử dụng — 2026-10-03

Phản ánh của người dùng xác nhận cần sửa trải nghiệm ngón, thay vì tiếp tục suy
ra độ ổn định từ test tổng hợp. Đã đọc run `stem-v2-20261003-082757-256103`;
journal cũ có 352 CANCEL với `HAND_ANCHOR_REQUIRED`. Đây là số sự kiện trong
run cụ thể, không phải tỷ lệ lỗi hay độ chính xác có ground truth.

| Lỗi xác nhận được | Sửa và kiểm tra |
| --- | --- |
| Con trỏ HAND dùng tọa độ toàn cửa sổ, không trùng đầu ngón trong camera | Thêm source-pointer/source-pair snapshot bất biến; mirror/letterbox đúng một lần, bỏ gain cho HAND scene; cùng phép chiếu để vẽ và pick |
| Chuyển OPEN sang POINT/pinch làm mất scene | OPEN để lấy neo; tiếp tục theo palm cùng tay còn valid. Test một tay tạo hình và hai pinch scale HAND; mất tay/identity/context vẫn xóa neo |
| Đếm ngón chỉ dùng góc 2D, bỏ qua khớp bị khuất theo chiều z | Góc/độ thẳng khớp tương đối xyz có aspect correction; test tay nghiêng và ngón gập trong z. Không dùng z để đo khoảng cách scene/camera |
| Điểm đo đã khóa bị xóa khi ngón di chuyển tự nhiên lúc pinch; mở Inspector tự động hủy neo | Giữ snapshot qua CLOSING; tự mở Inspector chỉ thay đổi presentation sau intent đo. Test pair commit sau mở dock và chuyển pinch |
| Cursor lệch sau layout/HiDPI đổi kích thước viewport | Resolve source tip theo image rect hiện tại lúc vẽ; test classifier → GUI → pixel thật |
| READY chỉ nói có tracking, nhưng thiếu hiệu chuẩn/tay chủ đạo nên không commit | Đổi trạng thái thành TRACKING; hint nói rõ POINT, neo, calibration, tay phụ và Control UI độc quyền |

Kết quả: **749 full-suite test passed**, **194 product test passed**, thêm 52 test
so với lượt 697. Bao phủ 9 lab và 8 công cụ Distance/Vector/Angle/Plane/Triangle/
Rectangle/Quadrilateral/Polygon trong HAND. QA OpenGL chụp lại 82 surfaces tổng hợp.
`runs/hand-fix-validation/report.json` ghi diagnostic landmarks đã lưu, replay các
snapshot trên nền trống với thời gian tổng hợp và chụp cả GPU/software. Đã xem ảnh
GPU: vòng cursor đúng đầu index skeleton, Probe/preview khả dụng, neo còn sau POINT.
Không mở webcam hoặc yêu cầu người dùng test trong lượt sửa này. Không dùng số
pose hay ảnh replay để kết luận độ chính xác tay thật/thiếu sáng hoặc hoàn thành P9.
Giới hạn OPEN-every-frame của mục đối chiếu trước đã được giải quyết; Core/G7
không thay đổi. Manifest product-v2-3 và source hash phân biệt hành vi mới.

## Yêu cầu mới: hình bám trực tiếp mọi đầu ngón — 2026-10-03

Người dùng xác nhận **hình bám trực tiếp các đầu ngón**, không thêm điểm thủ công
và không giữ tay để tự lưu hình. Vì vậy luồng index/pinch đã mô tả ở các mục lịch
sử trên chỉ còn là RECORDED tùy chọn; PRODUCT/LIVE là mặc định mới.

- Quan sát đủ 5 đầu ngón mỗi tay, dùng mọi đầu ngón đang duỗi từ 1–2 tay làm đỉnh
  sống, tối đa 10 đỉnh. Tay phụ đứng riêng cũng dùng được; không buộc ngón trỏ.
- 1 đỉnh: điểm; 2: đoạn/vector; 3: tam giác; 4: tứ giác; 5–10: đa giác không gian.
  Hình cập nhật trực tiếp khi di chuyển/duỗi/gập ngón; không ép thành hình đều.
- Cả 9 lab dùng chung lớp hình học sống. LIVE ẩn công cụ thêm điểm thủ công;
  không cần pinch hay hiệu chuẩn trước khi dựng hình. Control UI độc quyền và
  RECORDED giữ luồng menu/công cụ cũ khi chọn rõ ràng trong Settings.
- Đỉnh chiếu ngược đúng vị trí ảnh đầu ngón với mirror/letterbox một lần. HAND
  lấy neo từ palm đang được quan sát với bất kỳ ngón duỗi nào. Relative-z chỉ tạo
  chiều sâu thị giác có giới hạn, không phải độ sâu camera hay đo tay thật.
- Mất theo dõi, hết ngón duỗi hoặc chuyển chủ điều khiển xóa hình sống. CSV lấy
  snapshot scene trước khi hộp thoại hủy tương tác. Mặt đa giác lõm dùng tâm chung
  để tránh tô tam giác vượt biên; tâm render không trở thành đầu ngón thứ 11.

Kiểm tra thực thi: **863 full-suite / 308 product tests passed**, thêm 114 test
so với lượt 749. Bao phủ mọi tập ngón không rỗng ở hai vai trò, classifier → GUI
với 1–10 đỉnh ở WORLD/HAND, thay đổi ngón, ngón gập, loss/UI/modal/context, 9 lab,
chiếu chiều sâu và CSV snapshot. GPU/software mỗi bên chụp 24 ảnh tổng hợp ở hai
kích thước cửa sổ; đã xem ảnh để kiểm tra đỉnh sống và các nút được ẩn.
Manifest là product-v2-4. Không mở camera, không yêu cầu người dùng test, không
đưa ra tỷ lệ chính xác tay thật hoặc chứng nhận doanh nghiệp.

## Rà toàn bộ extension/UI và cảm giác 3D — 2026-10-03

Đã sửa lớp hình sống chỉ là mặt mở, Vector LIVE lấy construction ẩn, xoay chuột
bị tool RECORDED cũ chặn, nhãn/probe đổi theo biên, overlay che mô hình, thông tin
kỹ thuật lấn số liệu học tập và NH3 có góc minh họa sai. UI phân biệt nội dung
phẳng/không gian và GPU/software. Báo cáo từng lab, thay đổi và giới hạn ở
[EXTENSION_3D_REVIEW.md](EXTENSION_3D_REVIEW.md).

Hồi quy: 886 passed (331 product cases); module audit mới 23 passed. Final QA
29 preset × 2 mode × 4 input: 232 GPU và 232 software; thêm 24 layout và 82
navigation/RECORDED/evidence/failure captures. Không mở webcam. Không biến số
ảnh/test thành tỷ lệ đúng tay thật, tối ưu UX hay readiness doanh nghiệp.

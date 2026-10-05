# Rà soát extension, UI và trải nghiệm 3D — 2026-10-03

Đã rà mã triển khai, hợp đồng dữ liệu, phương trình scene, tương tác LIVE/RECORDED,
các preset, renderer GPU/phần mềm và giao diện Qt. Đây là kiểm tra phần mềm của
prototype STEM, không phải chứng nhận doanh nghiệp hoặc tỷ lệ chính xác tay thật.
Người dùng tiếp tục hoãn kiểm tra vật lý; lượt này không mở webcam.

## Vì sao trước đó trông như 2D

Các scene có XYZ, phép chiếu phối cảnh, sphere/bond/surface mesh và depth test GPU.
Tuy nhiên lớp hình học bám ngón chỉ nối đỉnh thành một mặt đa giác mở; chưa dựng
khối kín khi các đỉnh không đồng phẳng. Tọa độ xy luôn chiếu về đầu ngón theo yêu
cầu bám trực tiếp nên orbit không làm đỉnh rời ngón; đây không phải chế độ lưu
vật thể rồi xoay vật thể độc lập. Một số nội dung vốn là đồ thị/sơ đồ phẳng.

Đã sửa: ít nhất 4 đỉnh không đồng phẳng tự dựng convex hull kín. Tứ diện có 4 đỉnh
biên; tập lớn hơn tạo đa diện lồi. Đỉnh nằm trong khối vẫn được giữ làm điểm sống,
không buộc thành mặt biên. Các tập gần đồng phẳng giữ mặt/đa giác; 3 điểm chỉ tạo
tam giác, không tự phát sinh chiều dày. Tất cả đỉnh vẫn theo đầu ngón trực tiếp.
Phân loại dùng tỷ lệ SVD trong product profile; đó là mặc định kỹ thuật.

## Rà từng lab

| Lab | Nội dung và chiều không gian | Tương tác/giới hạn thực tế |
| --- | --- | --- |
| Coordinate | Trục XYZ, lưới XY; hình sống điểm/đoạn/mặt/khối | Tự dựng và tô khối đủ điều kiện; dài/thể tích chỉ theo scene |
| Molecular | 4 preset; CH4/NH3 không đồng phẳng; H2O/CO2 phẳng, atom mesh 3D | Hình học lý tưởng hóa, không đo liên kết; H2O/CH4 gốc giữ nguyên; NH3 đã sửa góc |
| Orbital | Quỹ đạo tròn phẳng, hai thiên thể 3D | Radius, phase, pause và time rate; minh họa động học, không tích phân hấp dẫn |
| Vector | Vector XYZ, tổng, dot, cross, projection | LIVE dùng A→B và C→D ổn định; thiếu cặp báo unavailable, không lấy dữ liệu RECORDED ẩn |
| Function Surface | 5 mặt z=f(x,y), gradient, contour, section | Probe từ một đỉnh semantic ổn định; mặt phẳng là preset có chủ ý |
| Wave & Signal | 5 đồ thị XY; sampling và low-pass minh họa | Không phải vật thể thể tích; filter response độc lập với Core; không mô phỏng môi trường sóng đầy đủ |
| Vector Field | 5 field, 3 lớp z và streamline minh họa | Giá trị scene lý tưởng hóa; regularize vùng kỳ dị, không solver điện từ/chất lưu đầy đủ |
| Optics | 4 sơ đồ tia XY, reflection/Snell/thin lens | Sơ đồ tiết diện có chủ ý; không wave optics hay mô phỏng vật liệu đầy đủ |
| Crystal | 3 lattice, lặp 2×2×2 và mặt tham chiếu z=0 | Tọa độ 3D/sites dùng chung biên; không kích thước nguyên tử của vật liệu đo được |

NH3 trước đây có chiều cao hình chóp khiến góc H–N–H sai so với nội dung học tập.
Preset giờ dùng tham chiếu **106.7°** từ
[NIST CCCBDB](https://cccbdb.nist.gov/listangleexp3x.asp?bi=16&descript=aHNH&mi=16);
độ dài vẫn dùng scene units. Không thay dữ liệu phân tử G7 hoặc đưa ra kết quả
thực nghiệm hóa học mới.

## Các lỗi/điểm yếu đã sửa

- Dựng hình: mặt mở được thay bằng khối kín khi phù hợp; facet hướng ra ngoài,
  mặt đồng phẳng được gộp, không vẽ đường chéo facet thành cạnh khối.
- Vector LIVE: bỏ phụ thuộc vào construction lưu cũ; cặp thiếu luôn unavailable.
  Các vector u/v/tổng/cross có nhãn và điểm đầu vào rõ ràng.
- Mode switch: mouse orbit không còn bị chặn bởi tool RECORDED cũ khi về LIVE.
- Nhãn đỉnh/probe: đi theo token semantic ổn định, không thay theo thứ tự biên khi
  tay xoay. Khi tập ngón active thay đổi, nhãn được cập nhật cho tập mới.
- Overlay: Coordinate/Vector tô hình; lab còn lại dùng khung cạnh/đỉnh để tránh
  mặt hình sống che mô hình STEM. Vẫn giữ đầy đủ dữ liệu đỉnh và topology.
- Inspector: số liệu học tập xuất hiện trước danh sách XYZ. Full XYZ ở cuối khi
  bật diagnostics; CSV vẫn xuất đầy đủ snapshot scene trước hộp thoại.
- Giao diện: nói rõ renderer GPU/phần mềm và nội dung phẳng/không gian; Help/
  hướng dẫn mô tả khối kín, direct follow, cặp vector và giới hạn đo đạc.
- NH3: sửa hình chóp theo góc tham chiếu đã dẫn nguồn và kiểm tra đủ ba góc.

## Ranh giới cần hiểu đúng

[MediaPipe](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python)
mô tả normalized z tương đối với wrist và có thang gần normalized x. App sử dụng
cue relative-z có giới hạn so với palm để trình bày, không có camera depth đo đạc
hay khoảng cách vật lý giữa hai tay. Khối được dựng trong scene không phải scan
vật thể 3D, hand reconstruction chuẩn đo lường hoặc volume tay thật.

GPU có depth test theo pixel; phần mềm chỉ sắp xếp primitive và xấp xỉ occlusion.
Caption phân biệt hai đường render. Cả hai dùng cùng projection/picking; software
không được mô tả có chất lượng che khuất tương đương GPU.

LIVE geometry sở hữu TOOL độc quyền. Control UI và RECORDED là lựa chọn rõ ràng
cho menu/pinch/model clutch; không đồng thời phát tất cả các lệnh khi giơ tay.
Các lab probe dùng một điểm ổn định; mọi đầu ngón vẫn tham gia hình học sống,
không có cam kết mọi ngón điều khiển một tham số STEM độc lập.

Chưa có dữ liệu để khẳng định tối ưu nhận tay/UX, độ chính xác thiếu sáng,
độ ổn định qua che khuất/tay chéo, hoặc readiness doanh nghiệp. At-most-two-hand
acceptance và third-hand guard không bảo đảm thấy mọi người đứng ngoài camera.
Không đổi thuật toán/filter/model/G7 để tạo cảm giác đạt chứng nhận.

## Kiểm tra và bàn giao

Đã thực thi: **886 full-suite tests passed** (331 product cases), **23 focused
audit tests passed**. Native GPU/software mỗi bên chụp 232 ảnh mọi preset;
thêm 24 ảnh layout và 82 ảnh trang/RECORDED. Bản nguồn có 244 file đã kiểm tra
CRC/hash; UI/model smoke và toàn bộ 886 test của bản giải nén cũng đạt bằng môi
trường phụ thuộc riêng đã có. Compile/dependency/format/whitespace checks đạt.
Core/evidence diff rỗng và release tag commits không đổi. Không commit/push/tag.

Kết quả lệnh thực thi, QA manifests và kiểm tra gói nguồn được ghi ở
[QA_STATUS.md](QA_STATUS.md). Tests mới kiểm tra volume chuẩn của tứ diện/lập
phương, mặt hướng ra ngoài, manifold kín, hull ngẫu nhiên 10 điểm, điểm trong
khối được giữ, coplanarity, pipeline landmark thật dạng mô phỏng → GUI, Vector
LIVE, mouse ownership, nhãn ổn định, Inspector và NH3.

QA `--all-presets` đi qua 29 preset × 2 mode × 4 dạng input (1/3/4/10 đỉnh),
tức 232 ảnh tổng hợp mỗi renderer. QA layout và trang navigation/RECORDED bổ sung
được ghi riêng, không dùng số ảnh làm tỷ lệ đúng tay thật. Frozen Core/G7/evidence
và hai release tags phải giữ nguyên. Không cần người dùng test để hoàn tất lượt
sửa phần mềm này; physical acceptance vẫn deferred.

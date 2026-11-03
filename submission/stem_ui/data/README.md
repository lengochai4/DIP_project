# Dữ liệu nguyên tố dùng trong bản demo

Nguồn chính: PubChem, National Center for Biotechnology Information.

https://pubchem.ncbi.nlm.nih.gov/rest/pug/periodictable/JSON

Bản snapshot đọc ngày 2026-10-14 qua trình duyệt nghiên cứu của phiên làm
việc, giữ đầy đủ 118 hàng và 17 cột. Tải trực tiếp trên máy trả trang chặn
NCBI; trang đó đã bị bỏ, không dùng làm dữ liệu. JSON hiện tại được trích
từ toàn bộ 2.505 dòng phản hồi JSON đọc được qua công cụ web, phân tích và
ghi lại thành UTF-8 có thụt dòng. Không tự điền hay sửa cấu hình electron.

SHA-256 của file JSON chuẩn hóa UTF-8/LF tại lúc nhập:

`ff0f75976583b8a6493b18d0b42e83e1b68bd6e112b45d33578d98494ed5d321`

Metadata UI ghi SHA-256 thực tế của file đang chạy. App chạy offline; không
gửi ảnh camera hay cấu trúc người dùng lên PubChem/Nanome.

App dùng số hiệu, ký hiệu, tên tiếng Anh, cấu hình electron, nhóm phân loại
và màu CPK. Màu thiếu có giá trị minh họa trung tính; màu quá tối được nâng
độ sáng để đọc trên nền tối. Màu hiển thị không phải tính chất quang học thật.
Các cấu hình có chữ predicted trong nguồn vẫn giữ chữ đó. Mở rộng ký hiệu
khí hiếm và cộng electron theo số lượng tử chính; kiểm tra tổng bằng Z cho
cả 118 nguyên tố. Không suy ra số neutron từ nguyên tử khối trung bình.

Bảng tuần hoàn đối chiếu bố cục/ký hiệu với IUPAC:
https://iupac.org/what-we-do/periodic-table-of-elements/

Giới hạn liên kết ở settings.yaml là quy tắc demo bảo thủ cho nguyên tử
cộng hóa trị trung hòa, không phải danh sách mọi hóa trị hoặc trạng thái
oxy hóa của nguyên tố. Không dùng cột OxidationStates làm số liên kết.
Các nguyên tố ngoài nhóm hỗ trợ vẫn xem được nguyên tử/electron nhưng
không tự tạo liên kết không được định nghĩa.

Nguồn quy tắc liên kết đơn/đôi/ba và các trường hợp H/C/N/O/halogen:
https://openstax.org/books/organic-chemistry/pages/1-4-development-of-chemical-bonding-theory
https://openstax.org/books/chemistry-2e/pages/7-2-covalent-bonding

Thư viện hiện có 32 đồ thị liên kết giáo khoa:

- Cơ bản: H₂O, CO₂, CH₄, NH₃, H₂, O₂, N₂, HCl.
- Halogen và hydrogen halide: F₂, Cl₂, Br₂, I₂, HF, HBr, HI.
- Phân tử nhỏ khác: H₂S, H₂O₂, PH₃, HCN, CS₂.
- Hydrocarbon: C₂H₆, C₂H₄, C₂H₂, C₃H₈.
- Có oxygen: CH₃OH, C₂H₅OH, CH₃OCH₃, CH₂O, CH₃CHO, CH₃COCH₃,
  HCOOH, CH₃COOH.

Các đồ thị được biên soạn trực tiếp theo cấu trúc liên kết cơ bản và giới hạn
cộng hóa trị trung hòa đã ghi ở trên. Mỗi mẫu mới có `formula` dạng đếm nguyên
tử và `source_url` để tra tên/cấu trúc trên PubChem. Đây không phải dữ liệu 3D
tải từ PubChem: API truy cập từ máy trả trang chặn, trang đó không được dùng.
Ví dụ tra đối chiếu:

- [Etanol](https://pubchem.ncbi.nlm.nih.gov/compound/702): C–C–O, hydrogen ghi tường minh trong mẫu.
- [Đimetyl ete](https://pubchem.ncbi.nlm.nih.gov/compound/8254): C–O–C; cùng C₂H₆O với etanol nhưng khác đồ thị.
- [Acetone](https://pubchem.ncbi.nlm.nih.gov/compound/180): CH₃–C(=O)–CH₃.
- [Formaldehyde](https://pubchem.ncbi.nlm.nih.gov/compound/712): H₂C=O.
- [Axit fomic](https://pubchem.ncbi.nlm.nih.gov/compound/284): H–C(=O)–O–H.

Mẫu được kiểm tra khi khởi tạo: đủ vị trí hữu hạn, một thành phần liên thông,
không liên kết trùng, tổng bậc liên kết đúng giới hạn trung hòa H/C/N/O/P/S/halogen.
Nhận tên bằng đồ thị có nhãn nguyên tố và bậc liên kết; không phân biệt đồng phân
lập thể, ion hoặc cộng hưởng. Thư viện hiện tại không thêm các trường hợp đó.
Tọa độ đặt trong settings là hình học minh họa ở đơn vị cảnh. App không
tính năng lượng, tối ưu cấu dạng, quỹ đạo lượng tử hay phản ứng hóa học.

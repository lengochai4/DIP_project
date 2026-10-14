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

Mẫu H₂O, CO₂, CH₄, NH₃, H₂, O₂, N₂ và HCl là đồ thị liên kết giáo khoa.
Tọa độ đặt trong settings là hình học minh họa ở đơn vị cảnh. App không
tính năng lượng, tối ưu cấu dạng, quỹ đạo lượng tử hay phản ứng hóa học.

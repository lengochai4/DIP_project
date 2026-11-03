# Đợt dữ liệu bổ sung ROUND2

Kế hoạch lập ngày 14/10/2026, trước khi thu dữ liệu ROUND2. Đây là đợt mới được người dùng yêu cầu để hoàn thiện báo cáo và bản nộp. Không thay nguồn, số liệu hoặc tag của G7.

## Phạm vi và quyết định Core

Giữ canonical v1.2, mô hình G7, cấu hình mặc định và các profile F0/F1/F2/P0/P1. Không chỉnh ngưỡng để làm kết quả có lợi. Không thêm độ tin cậy giả, độ sâu vật lý, mô hình nhận dạng mới hoặc thống kê suy luận.

Core được kiểm tra bằng bộ kiểm thử và một phiên nhận dạng thực. Nâng cấp thuật toán chỉ xem xét khi có lỗi được tái hiện hoặc bằng chứng cho thấy hợp đồng hiện tại không đáp ứng nhiệm vụ. Nếu sửa hành vi, lập hồ sơ thay đổi và định danh đợt mới trước khi thu tiếp.

Môi trường ROUND2 dùng Python 3.12 vì Python 3.11 của `.venv` cũ không còn ở đường dẫn đã cấu hình. Phiên bản phụ thuộc, mã nguồn và mô hình được ghi riêng; không gộp kết quả ROUND2 với G7 như cùng môi trường. Camera chỉ số 0, yêu cầu 640 × 480, 30 FPS, backend mặc định, MJPG AVI BGR nguyên bản. Camera tự phơi sáng/cân bằng trắng để `unknown` nếu chưa xác minh.

## Kế hoạch thu cố định

Chín video nguồn, ba lượt mỗi nhóm:

1. `static_normal`: đủ ánh sáng theo bố trí của người thực hiện, bàn tay đầy đủ trong khung, đầu ngón trỏ gần đứng yên; đỡ cổ tay khi thuận tiện. Dùng chung cho A1 và B-normal.
2. `dynamic_normal`: cùng bố trí ánh sáng, bàn tay đầy đủ; di chuyển chậm và liên tục theo chiều ngang giữa hai mốc trong khung, giữ khoảng cách và hướng bàn tay gần ổn định. Dùng cho A2.
3. `static_lowlight`: giảm chiếu sáng phía trước, giữ bố trí camera và tư thế tĩnh như nhóm đầu; người thực hiện xác nhận điều kiện trước khi bắt đầu. Dùng cho B-lowlight. Không giả định có số đo lux.

Trước mỗi lượt, cửa sổ xem trước chạy đường P1 thật và hiển thị điểm mốc, ROI, mô tả ánh sáng và trạng thái CLAHE. SPACE bắt đầu khi người thực hiện đã bố trí đúng nhiệm vụ; không ghi tự động khi vừa mở camera. Xem trước là kiểm tra bố trí, không phải nguồn tính kết quả.

Mỗi lượt: camera ổn định 3 giây, ghi 360 khung tại tốc độ mã hóa 30 FPS; thời lượng mã hóa 12 giây. Ghi cả dấu thời gian thu thực để phân biệt thời lượng mã hóa với thời gian thu. Trong lúc ghi, chỉ xem ảnh thô, không chạy nhận dạng gây chậm thu. Overlay chỉ vẽ trên bản sao, không ghi vào video.

Thời gian replay được dựng bằng quy tắc cố định `frame_id / encoded_fps`, giống quy tắc G7. Cửa sổ chính 2,0–10,0 giây, gồm biên, warmup 2 giây. Không diễn giải tốc độ mã hóa thành FPS xử lý hoặc độ trễ vật lý.

## So sánh và chỉ số chính

- A1: F0/F1/F2, tiền xử lý P1 cố định; radial RMS jitter, điểm mốc 8, filtered, FRAME_NORMALIZED, cùng tập khung dùng được.
- A2: F0/F1/F2, tiền xử lý P1 cố định; RMSE quỹ đạo so với F0, cùng tập khung dùng được. Không phải sai số vị trí thật hoặc độ trễ.
- B-normal và B-lowlight: P0/P1, lọc F0 cố định; tỷ lệ VALID hoặc REACQUIRED trên tổng khung trong cửa sổ. Kiểm tra riêng số khung CLAHE thực sự hoạt động.

Mỗi phiên có ID riêng, kế hoạch/manifest/config/model/source có SHA-256, metadata ghi phiên bản mã và phụ thuộc. Khóa kế hoạch khi chuẩn bị phiên. Chỉ bắt đầu phân tích sau khi thu đủ nguồn theo kế hoạch; công cụ không tự chọn lại nguồn theo kết quả.

## Lượt thất bại và dừng phiên

Không bỏ lượt vì NO_HAND, nhiều rung, ít mẫu hoặc kết quả bất lợi. A1/A2 thiếu khung chung được giữ với `no_common_usable_frames`. B có thể bằng 0 một cách hợp lệ. Chỉ loại toàn lượt khi tệp hỏng, timestamp/pairing không hợp lệ hoặc thu hoàn toàn thất bại, theo chính sách G7.

ESC/Q hủy lượt đang ghi và dừng phiên. Các lượt đã hoàn thành được giữ nguyên. Phiên hủy được ghi trạng thái `interrupted`; không phân tích như một phiên đủ chín nguồn. Tiếp tục phiên có sẵn chỉ thu các lượt chưa có, không ghi đè video/sidecar của lượt đã hoàn thành.

Nếu cả đợt vẫn thiếu nhận dạng hoặc CLAHE không kích hoạt, báo cáo phải ghi đúng hạn chế này. Không thu thay một lượt chỉ vì biết kết quả không thuận lợi. Đợt thu tiếp theo, nếu cần, phải có kế hoạch riêng.

## Sau khi có dữ liệu

Chạy paired replay bằng công cụ G6/G7 hiện có, tái tạo bảng và hình từ nhật ký, đối chiếu danh tính nguồn/cấu hình, rồi cập nhật bản Word/PDF. Giữ G7 thành hồ sơ cũ riêng. Chốt Core sau khi kiểm tra và đánh giá thực tế. UI mới làm trên phần Extension, tối giản theo mục tiêu bản nộp, giữ ranh giới xử lý nghiên cứu.

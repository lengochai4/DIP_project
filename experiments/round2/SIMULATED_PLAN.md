# ROUND2 với đầu vào tối giả lập

Kế hoạch bổ sung lập ngày 14/10/2026 theo yêu cầu trực tiếp của người dùng, trước khi tạo nguồn biến đổi và xem kết quả P0/P1 của điều kiện giả lập.

## Lý do và phạm vi kết luận

Người thực hiện xác nhận không thể giảm ánh sáng môi trường trực tiếp. Phiên ROUND2 đầu đã thu đủ ba nguồn tĩnh và ba nguồn động ánh sáng thường, cùng hai nguồn trong nhóm dự kiến giảm sáng, rồi dừng trước lượt cuối. Hai lượt dự kiến giảm sáng chưa xác nhận được điều kiện; chúng được giữ nguyên với ghi chú sai khác kế hoạch, không dùng như bằng chứng thiếu sáng thực.

Đợt bổ sung dùng sáu video thật của hai nhóm ánh sáng thường. Tạo ba video tối giả lập từ chính ba video tĩnh bằng phép giảm cường độ BGR. Tổng cộng phân tích chín nguồn, trong đó chỉ sáu nguồn được camera ghi mới và ba nguồn là bản biến đổi có thể tái tạo. B-normal và B-simulated dùng chung ba nguồn gốc; chúng không phải các phiên camera độc lập.

Đây là thử nghiệm đáp ứng với đầu vào ảnh tối có kiểm soát. Nó không tái hiện đầy đủ nhiễu cảm biến, phơi sáng, mất thông tin hoặc nhòe chuyển động do thiếu sáng vật lý. Không gọi kết quả là khả năng hoạt động trong phòng thiếu sáng đã được kiểm chứng. Báo cáo phải phân biệt điều kiện giả lập và điều kiện thật.

## Phép biến đổi khóa trước phân tích

Với mỗi khung BGR uint8 đã giải mã từ nguồn tĩnh:

`output = round(input × 0.35)`, trên toàn bộ ba kênh.

Hệ số 0,35 là mức giảm cường độ được chọn cho phép thử này, không phải mức tối ưu hoặc một số đo lux. Giữ thứ tự, kích thước và số khung, mã hóa MJPG ở FPS nguồn 30. Quy tắc dấu thời gian replay vẫn là `frame_id / encoded_fps`. Không lọc, cắt, đảo hoặc chọn khung theo kết quả nhận dạng. Mã hóa lại là một hạn chế được ghi nhận.

## So sánh

- A1 và A2 dùng ba nguồn thật của từng nhóm, F0/F1/F2, P1 cố định; các chỉ số chính G7 giữ nguyên.
- B-normal dùng ba nguồn tĩnh thật, P0/P1, F0 cố định.
- B-simulated dùng ba bản giảm cường độ từ nguồn tĩnh, P0/P1, F0 cố định.
- Cửa sổ 2,0–10,0 giây, warmup 2 giây, ba lượt mỗi nhóm; giữ mọi lượt không nhận tay và chỉ số chưa có. Không thống kê suy luận hoặc ngưỡng thắng/thua.

Giữ nguồn gốc/biến đổi, hệ số, mã băm đầu vào/đầu ra, cấu hình, model, môi trường và phiên bản mã. Tái tạo bảng/hình từ log, không sửa CSV. Nếu CLAHE không kích hoạt hoặc không cải thiện, ghi đúng kết quả; không thay hệ số để tìm kết quả thuận lợi.

## Tương thích và hồ sơ cũ

Không sửa Core, các profile nghiên cứu, nguồn G7 hoặc video ROUND2 đã ghi. Hồ sơ G7 vẫn độc lập. Đây là thay đổi thiết kế thu nguồn cho một nghiên cứu bổ sung được người dùng cho phép; kết quả không gộp như cùng điều kiện vật lý với G7.

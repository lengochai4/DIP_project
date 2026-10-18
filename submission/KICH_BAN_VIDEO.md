# Kịch bản demo DIP Touchless STEM — khoảng 3 phút 30 giây

Mục tiêu: cho thấy chương trình chạy thật, thao tác không chạm có ích cho
học tập và một luồng thí nghiệm có kết quả giải thích được. Dùng bản
`submission-2026-10-18` trên `main`. Đây là kịch bản để nhóm quay, không phải
biên bản đã quay thành công hoặc cam kết thương mại.

## Chuẩn bị trước khi bấm quay

- Mở app, chọn đúng camera, ánh sáng đủ thấy ngón; nền ít vật giống bàn tay.
- F11 phóng to, H ẩn hướng dẫn khi cần thêm chỗ; giữ thanh tác giả trong hình.
- Ghi màn hình và tiếng nói; để thấy tay trong camera phụ ở hai tab đầu.
  Giữ vài đoạn cầm–di chuyển–buông liên tục để người xem đánh giá được.
- Chuột có thể dùng để chuyển tab/chuẩn bị thông số; quay rõ phần điều khiển
  bằng tay. Không ghép cảnh khiến thao tác chuột trông thành thao tác tay.
- Chuẩn bị mẫu H₂O; xác định vị trí các trang Đo / Lưu và nút Giữ lượt A,
  Đồ thị, Xuất CSV/ảnh. Nút có thể ở trang sau khi cửa sổ nhỏ.

## Thứ tự quay và lời nói gợi ý

| Thời gian | Hình/thao tác cần quay | Lời nói gợi ý |
|---|---|---|
| **0:00–0:15** | Giao diện, tên nhóm, bật camera. | “Nhóm em xây dựng DIP Touchless STEM, dùng một webcam RGB để điều khiển mô hình STEM bằng tay. Ứng dụng có bốn không gian học tập.” |
| **0:15–0:40** | Khối 3D: chụm cầm, di chuyển/xoay, hai tay đổi cỡ, mở để buông. Xòe ở mép mở bảng, nhắm lại rồi chọn khối khác. | “Một tay để cầm và xoay, hai tay phối hợp đổi cỡ. Có thể đổi khối bằng tay, giữ nguyên vị trí và tư thế đang thao tác.” |
| **0:40–1:00** | Đầu ngón: một rồi hai tay, duỗi/gập vài ngón, cho thấy số đỉnh và nhãn. Đổi góc quan sát. | “Mỗi đầu ngón đang duỗi là một đỉnh sống. Hình cập nhật trực tiếp theo tay; gần đồng phẳng tạo mặt, có đủ độ lệch tương đối mới tạo khối.” |
| **1:00–1:40** | Hóa học: chọn H₂O; cầm cả khối, hai tay đổi cỡ, mở ngón và giữ tay ở nơi khác để thấy vật đứng lại. Ghép/tách một nguyên tử rồi Hoàn tác. Kéo bảng ra viền, chọn mũi tên mở lại. | “Bảng nguyên tố nằm trong khung camera và thu gọn được. Người học thao tác mô hình nguyên tử, phân tử và liên kết. Tên phân tử chỉ được gọi khi cấu trúc khớp mẫu đã hỗ trợ; ghép hóa học không làm đổi nguyên tố.” |
| **1:40–2:25** | Vật lý: mở thư viện cho thấy tám bài, chọn Lò xo và giảm chấn. Làm so sánh A/B như hướng dẫn dưới. | “Tab Vật lý gắn thao tác với bài toán học tập. Với mô hình dao động ngang này, em giữ cùng điều kiện đầu, đổi giảm chấn để quan sát dao động và đối chiếu đồ thị hai lượt.” |
| **2:25–2:55** | Ròng rọc: giữ cùng khối lượng, đổi n từ 1 đến 4, kéo dây và cho thấy số đo lực/độ nâng. Mở Bài học để hiện công thức. | “Trong hệ lý tưởng, tăng nhánh đỡ tải làm giảm lực cần kéo. Đổi lại phải kéo dây dài hơn cho cùng độ nâng; mô hình giúp giải thích sự đánh đổi này.” |
| **2:55–3:10** | Đo / Lưu → Xuất CSV/ảnh; cho thấy thư mục kết quả hoặc ảnh xuất. | “Một lượt thí nghiệm có thể lưu cấu hình, số đo và hình, giúp người học xem lại và trình bày kết quả.” |
| **3:10–3:30** | Trở về mô hình. Nói ngắn luồng xử lý và hướng phát triển. | “Phía sau là thu ảnh, ROI, đánh giá ánh sáng và tiền xử lý theo điều kiện, MediaPipe rồi lọc tín hiệu để hỗ trợ tương tác. Nhóm mong được tiếp tục đánh giá trải nghiệm với lớp học và thiết bị khác để phát triển sản phẩm.” |

## So sánh giảm chấn A/B cho đoạn Vật lý

1. Chọn **Lò xo và giảm chấn**. Trong Đo / Lưu, bật **Đồ thị** và **Năng lượng**,
   tắt **Thả để chạy** để dễ giữ cùng điều kiện đầu cho hai lượt.
2. Đặt **m = 1 kg**, **k = 15 N/m**, **kéo lệch đầu = 0,8 m**, **c = 0**.
   Chọn Đặt lại, Chạy vài chu kỳ, Dừng rồi **Giữ lượt A**.
3. Chỉ đổi **c = 4 N·s/m**, giữ nguyên m, k và độ lệch đầu. Đặt lại và chạy B;
   quan sát đường A vàng/B xanh ở cùng khoảng thời gian mô phỏng.
4. Giải thích xu hướng biên độ và năng lượng trên hình thực tế; đây là mô hình
   tuyến tính có cản nhớt, minh họa nguyên lý giảm rung, không phải mô phỏng
   toàn bộ hệ thống giảm xóc ô tô. Đừng kết luận “càng nhiều cản càng tốt”.

## Các điểm nói đúng khi quay

- Số đo SI thuộc mô phỏng; webcam không đo lực, độ dài hoặc độ sâu thật của tay.
- Mô hình electron là minh họa; thao tác ghép/tách không chứng minh phản ứng hóa học.
- Thể hiện thao tác và kết quả thật. Không tự ghi “nhận đúng 99%”, “không lag”
  hay “đã đạt chuẩn thương mại” khi chưa có dữ liệu kiểm chứng tương ứng.
- Nếu chưa quay được một đoạn, sửa đoạn thao tác/lời nói cho đúng những gì đã
  ghi hình; không cần cố nhồi cả tám bài vào video ngắn.

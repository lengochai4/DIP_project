# Bổ sung A1 giữ tay có điểm tựa

Lập ngày 14/10/2026 trước khi thu bổ sung, được người dùng chấp thuận sau khi kiểm tra ảnh và quỹ đạo của các nguồn dự kiến tĩnh ban đầu.

Ba nguồn A1 ban đầu có chuyển động tay đáng kể. Chỉ số radial RMS vẫn tính được nhưng gồm cả chuyển động thật, nên chưa tách tốt dao động của nhận dạng. Giữ nguyên các nguồn và kết quả này; không loại chúng vì bộ lọc thắng hoặc thua. Đợt mới cải thiện việc thực hiện tác vụ tĩnh, có định danh riêng.

Thu đúng ba lượt mới. Kê cổ tay hoặc cẳng tay lên điểm tựa, bàn tay và đầu ngón trỏ vẫn đầy đủ trong khung. Sau khi nhấn SPACE, giữ nguyên tư thế trong 3 giây ổn định và 360 khung ghi. Không vẫy tay, xoay bàn tay hoặc thử cử chỉ khi đang ghi. Kích thước yêu cầu 640 × 480, tốc độ mã hóa 30 FPS, ảnh BGR MJPG chưa xử lý.

Core, mô hình, profile F0/F1/F2 với P1 cố định, chỉ số radial RMS của điểm 8 và cửa sổ 2,0–10,0 giây giữ nguyên. Không đặt ngưỡng cải thiện hoặc điều chỉnh tham số theo kết quả. Cả ba lượt đều được giữ, kể cả nếu nhiệm vụ vẫn chưa đủ tĩnh hoặc tracking kém. Nhật ký ghi danh tính nguồn, phiên bản và cấu hình; video/sidecar không ghi đè.

Đợt này được trình bày riêng với lần thu ban đầu. Rung đầu ra vẫn có thể gồm vi chuyển động của người giữ tay; không có ground truth độc lập để kết luận toàn bộ dao động là nhiễu cảm biến.

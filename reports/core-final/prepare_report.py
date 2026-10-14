"""Assemble the Vietnamese Core report; numeric tables remain verified CSV data."""
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
old = (ROOT / 'reports/temporary/BAO_CAO_TAM.md').read_text(encoding='utf-8')
body = old.split('# CHƯƠNG 3 ')[0]
replacement = '''## 2.3 Nguồn dữ liệu nghiên cứu

Đợt bổ sung ngày 14/10/2026 được tổ chức trên kế hoạch riêng [8]. Ban đầu đã thu ba lượt tay gần tĩnh và ba lượt chuyển động trong ánh sáng thường, cùng hai lượt dự kiến giảm sáng. Người thực hiện sau đó xác nhận không thể giảm trực tiếp ánh sáng môi trường. Hai nguồn sau được giữ lại với điều kiện thiếu sáng chưa xác nhận, không được dùng để chứng minh độ bền vững trong phòng tối.

Thay cho điều kiện thiếu sáng vật lý, một nghiên cứu bổ sung dùng ba bản làm tối từ ba nguồn tĩnh ánh sáng thường. Phép biến đổi cố định là làm tròn từng kênh BGR nhân 0,35, lưu uint8 và mã hóa MJPG. Hệ số được ghi trong kế hoạch trước khi tạo và phân tích kết quả. Bản dẫn xuất giữ kích thước, số khung và dòng thời gian của nguồn gốc; nguồn, phép biến đổi và mã băm được ghi riêng.

Khi kiểm tra chất lượng ba lượt tĩnh ban đầu, chúng tôi quan sát thấy chuyển động thật của tay. Do vậy, nhóm đã đăng ký và thu thêm ba lượt có kê cổ tay, cẳng tay để hạn chế chuyển động. Các lượt đầu không bị xóa hoặc ghi đè. Báo cáo dùng nhóm kê cổ tay cho A1 chính, giữ nhóm đầu trong phụ lục và tiếp tục dùng chúng cho B-normal.

Bảng 2.2 Nguồn của các nhóm đánh giá bổ sung

| Nhóm nguồn | Số lượt | Phép phân tích | So sánh |
|---|---|---|---|
| Kê cổ tay, ánh sáng thường | 3 | A1 chính | F0/F1/F2 |
| Chuyển động, ánh sáng thường | 3 | A2 | F0/F1/F2 |
| Gần tĩnh ban đầu, còn chuyển động | 3 | B-normal; A1 kiểm tra thu | P0/P1; F0/F1/F2 |
| Làm tối từ ba nguồn ban đầu | 3 dẫn xuất | B tối giả lập | P0/P1 |

Tổng cộng có chín video webcam khác nhau dùng cho các nhóm phân tích trên và ba video dẫn xuất tối giả lập; ngoài ra hai nguồn dự kiến giảm sáng được bảo lưu nhưng không xác nhận điều kiện vật lý. Không xem ba video dẫn xuất là ba lần thu webcam mới hoặc ba nguồn độc lập với nguồn thường.

Camera chỉ số 0 được yêu cầu 640 × 480 và 30 FPS; hồ sơ nguồn ghi nhận kích thước và tốc độ danh nghĩa đó. Mỗi lượt lưu 360 khung BGR chưa tiền xử lý sau ba giây ổn định thiết bị, cùng dấu thời gian thu thực. Tốc độ danh nghĩa của tệp không được dùng làm FPS xử lý hoặc độ trễ tương tác. Replay dùng dòng thời gian xác định của nguồn, giữ nguyên giữa các profile; dấu thời gian thu được lưu để đối chiếu.

Các nguồn có siêu dữ liệu, mã băm và kiểm tra giải mã trước khi phân tích. Phơi sáng tự động, cân bằng trắng và độ rọi không được giả định từ cảm nhận sáng tối của ảnh. Do chưa có phép đo điều kiện phòng, báo cáo chỉ gọi nhóm dẫn xuất là đầu vào tối giả lập.

'''
body = re.sub(r'## 2\.3 Nguồn dữ liệu nghiên cứu\n.*?(?=## 2\.4)', replacement, body, flags=re.S)
body = body.replace('A2 dự kiến dùng RMSE', 'A2 dùng RMSE')
refs = '# TÀI LIỆU THAM KHẢO\n' + old.split('# TÀI LIỆU THAM KHẢO\n', 1)[1].split('# PHỤ LỤC')[0]
refs += '[8] Hồ sơ thực nghiệm bổ sung DIP Touchless STEM ngày 14/10/2026: PLAN.md, SIMULATED_PLAN.md, HELD_STATIC_PLAN.md và environment.lock.txt tại experiments/round2; các nguồn, nhật ký và phân tích riêng tại runs/round2/ROUND2-20261014-SUBMISSION, ROUND2-20261014-SIM035 và ROUND2-20261014-HELD-STATIC. Đường dẫn đối chiếu trình bày ở Phụ lục 1.\n\n'
tail = (HERE / 'final_sections.md').read_text(encoding='utf-8')
tail = tail.replace('# PHỤ LỤC\n', refs + '# PHỤ LỤC\n', 1)
(HERE / 'BAO_CAO_CORE.md').write_text(body + tail, encoding='utf-8')
print(HERE / 'BAO_CAO_CORE.md')

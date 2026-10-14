# CHƯƠNG 3 KẾT QUẢ THỰC NGHIỆM VÀ ĐÁNH GIÁ

## 3.1 Phạm vi dữ liệu kết quả

Chương này trình bày đợt thực nghiệm bổ sung ngày 14/10/2026 [8]. Các bảng lấy số liệu từ metrics.csv của từng nhóm phát lại; kiểm tra nhánh tiền xử lý lấy từ frames.csv. Kết quả G7 trước đó được lưu riêng và tóm tắt trong phụ lục, không gộp với đợt mới để tính một kết quả chung.

Mỗi nhóm có ba lượt. A1 chính sử dụng các lượt mới có kê cổ tay và cẳng tay; A2 sử dụng ba lượt chuyển động; B sử dụng ba nguồn ánh sáng thường và ba bản làm tối tương ứng. Mỗi lượt đều có 241 khung trong cửa sổ 2,0–10,0 giây. Với A1 và A2, cả ba đường F0/F1/F2 có đủ 241 khung hợp lệ chung. Đây là số khung ghép cặp trong một video, không phải 241 mẫu người dùng độc lập.

Không có thiết bị đo vị trí đầu ngón tay thật để làm chuẩn. Vì vậy, các chỉ số tọa độ được diễn giải là độ phân tán trong lượt gần tĩnh và sai lệch so với tọa độ thô. Tỷ lệ quan sát hợp lệ là tỷ lệ trạng thái của đường xử lý, không phải độ chính xác định vị hoặc độ chính xác phân loại cử chỉ.

## 3.2 Kết quả độ rung tĩnh A1

Bảng 3.1 Radial RMS của ba lượt kê cổ tay trong hệ tọa độ chuẩn hóa

| Lượt | Khung chung | F0 | F1 | F2 |
|---|---|---|---|---|
| trial-001 | 241 | 0,003445909 | 0,003538419 | 0,003538462 |
| trial-002 | 241 | 0,002442745 | 0,002319375 | 0,002319410 |
| trial-003 | 241 | 0,002530234 | 0,002362836 | 0,002362840 |

Ở trial-002 và trial-003, hai đường lọc có độ phân tán nhỏ hơn Raw. Ở trial-001, cả F1 và F2 lại lớn hơn Raw một lượng nhỏ. Báo cáo giữ nguyên lượt này: kết quả không chứng minh bộ lọc luôn giảm radial RMS trong mọi lượt gần tĩnh.

![Hình 3.1 Độ phân tán của đầu ngón trỏ trong ba lượt kê cổ tay](assets/a1_jitter.png)

F1 và F2 gần như trùng nhau trong cả ba lượt. Điều này phù hợp với việc F2 giữ tần số cắt gần giá trị nền khi tốc độ nhỏ, nhưng số liệu hiện tại không cho phép kết luận F2 có ưu thế giảm rung so với F1. Radial RMS quanh trung bình của cả cửa sổ còn chứa chuyển động nhỏ thật của tay; kê cổ tay giúp hạn chế chuyển động, không tạo một điểm chuẩn tuyệt đối đứng yên.

Ba lượt tĩnh đầu tiên của đợt thu được kiểm tra thấy tay có chuyển động rõ. Chúng tôi đã lưu nguyên nguồn, nhật ký và kết quả, đồng thời đăng ký một nhóm bổ sung riêng trước khi thu ba lượt kê cổ tay. Kết quả ban đầu nằm ở Phụ lục 2 và được xem là kiểm tra chất lượng thao tác thu, không dùng thay cho ba lượt gần tĩnh trong bảng 3.1.

## 3.3 Kết quả quỹ đạo động A2

Bảng 3.2 RMSE so với Raw trên các khung hợp lệ chung

| Lượt | Khung chung | F0 | F1 | F2 |
|---|---|---|---|---|
| trial-001 | 241 | 0,000000000 | 0,042348031 | 0,037501923 |
| trial-002 | 241 | 0,000000000 | 0,074392649 | 0,056818227 |
| trial-003 | 241 | 0,000000000 | 0,044816703 | 0,037578966 |

F0 bằng không vì quỹ đạo thô được so với chính nó. Cả ba lượt đều tính được chỉ số, khắc phục tình trạng thiếu quan sát dùng được của nhóm A2 trong hồ sơ G7. F2 có RMSE so với Raw nhỏ hơn F1 ở cả ba lượt mới. Trong phạm vi phép đo này, bộ lọc thích ứng giữ quỹ đạo gần đầu vào thô hơn bộ lọc cố định khi tay chuyển động.

![Hình 3.2 Sai lệch quỹ đạo của F1 và F2 so với Raw trong ba lượt động](assets/a2_rmse.png)

Giá trị thấp hơn không đồng nghĩa tọa độ đúng hơn vị trí thật: Raw cũng chứa nhiễu của bộ nhận dạng. Chỉ số này còn không đo trực tiếp số mili giây từ chuyển động tay đến màn hình. Kết hợp A1 và A2 cho thấy một sự đánh đổi mô tả: F1/F2 gần nhau trong các lượt gần tĩnh, còn F2 ít cách xa Raw hơn trong các lượt chuyển động. Chưa có cơ sở để biến kết quả đó thành khẳng định tối ưu cho mọi người dùng hoặc mọi quỹ đạo.

## 3.4 Kết quả tiền xử lý trong ánh sáng thường

Bảng 3.3 Tỷ lệ quan sát hợp lệ và nhánh CLAHE trong ánh sáng thường

| Lượt | Khung mỗi profile | P0 | P1 | Khung P1 bật CLAHE |
|---|---|---|---|---|
| trial-001 | 241 | 100% | 100% | 0 |
| trial-002 | 241 | 100% | 100% | 0 |
| trial-003 | 241 | 100% | 100% | 0 |

P0 và P1 đều có quan sát hợp lệ trên toàn bộ khung phân tích. Nhật ký P1 ghi NORMAL và enhancement_active bằng false ở cả 723 khung của ba lượt. Chính sách thích ứng đã bỏ qua CLAHE trong điều kiện này. Kết quả thể hiện đường nhận dạng làm việc ổn định trên các nguồn đã thu, không chứng minh tỷ lệ 100% cho mọi điều kiện sử dụng.

## 3.5 Kết quả tiền xử lý với đầu vào tối giả lập

Bảng 3.4 Tỷ lệ quan sát hợp lệ và nhánh CLAHE với ảnh giảm cường độ 0,35

| Lượt | Khung mỗi profile | P0 | P1 | Khung P1 bật CLAHE |
|---|---|---|---|---|
| trial-001 | 241 | 100% | 100% | 241 |
| trial-002 | 241 | 100% | 100% | 241 |
| trial-003 | 241 | 100% | 100% | 241 |

Trong cả 723 khung phân tích của P1, trạng thái ánh sáng là DIFFICULT và enhancement_active bằng true. Như vậy, đầu vào làm tối đã thực sự đi qua nhánh CLAHE của chính sách thích ứng. Khác với nhóm thường, phép so sánh ở đây đã kiểm tra một nhánh tăng cường đang hoạt động.

Tuy nhiên, P0 cũng đạt tỷ lệ hợp lệ 100%. Không ghi nhận cải thiện ở chỉ số chính khi bật CLAHE trên bộ nguồn này. Cần phân biệt hai kết luận: cơ chế kích hoạt đã được kiểm tra bằng nhật ký; lợi ích đối với tỷ lệ quan sát chưa được thể hiện vì đường bỏ qua vốn đã đạt 100% trong cửa sổ đánh giá.

Việc nhân cường độ ảnh với 0,35 chỉ tạo một điều kiện ảnh tối được kiểm soát. Nó không tái tạo đầy đủ nhiễu cảm biến, nhòe do phơi sáng, cân bằng trắng hoặc biến đổi chiếu sáng trong phòng. Ba nguồn giả lập còn xuất phát từ ba nguồn thường, nên là dữ liệu ghép cặp, không phải ba phiên vật lý độc lập. Kết quả không được gọi là kiểm chứng độ bền vững trong môi trường thiếu sáng thực tế.

## 3.6 Minh họa xử lý ảnh và khả năng tích hợp 3D

Hình 3.3 được tạo từ khung 161 của lượt tối giả lập trial-001, profile P1. Vùng ảnh được lấy theo ROI đã ghi; mô tả ánh sáng được đối chiếu lại từ nguồn có mã băm khớp nhật ký. Bộ tiền xử lý sử dụng chính sách adaptive và thông tin DIFFICULT của khung. Nhật ký gốc tại khung này ghi enhancement_active bằng true.

![Hình 3.3 ROI và phân bố kênh V trước và sau CLAHE trên đầu vào tối giả lập](assets/clahe_roi.png)

Hình minh họa làm rõ bước biến đổi kênh V trong ROI. Việc nhìn thấy ảnh thay đổi không thay thế cho đánh giá nhận dạng: kết quả B vẫn là 100% ở cả P0 và P1. Hình này không dùng một nhánh CLAHE cưỡng bức để thay cho kết quả của chính sách thích ứng.

Về tích hợp, hồ sơ G7 ghi nhận phiên chạy thực tế ngày 29/09/2026 có thao tác xoay và thay đổi kích thước vật thể qua InteractionState [7]. Hồ sơ đó cũng ghi nhận một số quan sát giống bàn tay tại vùng mặt hoặc nền, gây xoay nhỏ ngoài ý muốn. Đây là bằng chứng đường xử lý đã nối tới cảnh 3D, đồng thời cho thấy hạn chế cần chú ý khi thiết kế tương tác. Đợt mới tập trung phát lại để đánh giá Core; không có một đợt đánh giá người dùng hoặc kiểm chứng giao diện mới trong báo cáo này.

## 3.7 Đánh giá theo các câu hỏi nghiên cứu

Với câu hỏi về tiền xử lý, chính sách thích ứng bỏ qua CLAHE trên nguồn thường và bật CLAHE trên nguồn tối giả lập. Cả hai cấu hình P0/P1 có tỷ lệ hợp lệ bằng nhau. Dữ liệu xác nhận hành vi xử lý theo điều kiện đầu vào, nhưng không chứng minh tăng tỷ lệ quan sát hay khả năng nhận tay trong phòng thiếu sáng thực.

Với câu hỏi về lọc thời gian, hai trong ba lượt kê cổ tay có radial RMS thấp hơn Raw sau lọc; lượt còn lại tăng nhẹ. F1 và F2 cho kết quả gần nhau trong A1. A2 cho thấy F2 có sai lệch so với Raw nhỏ hơn F1 ở cả ba lượt. Các quan sát này cung cấp bằng chứng mô tả về hành vi lọc; chúng không xác lập ưu thế phổ quát hoặc độ chính xác vật lý.

Với câu hỏi về tương tác 3D, bản minh họa G7 đã chứng minh khả năng chuyển trạng thái xử lý thành thao tác xoay và thay đổi kích thước. Hiệu quả học tập, tính dễ sử dụng và chất lượng giao diện nộp đồ án chưa được đo. Phát triển giao diện là công việc tiếp nối nền xử lý đã được kiểm tra, không phải kết quả đã hoàn thành của đợt báo cáo Core này.

## 3.8 Kiểm tra triển khai và quyết định chốt Core

Môi trường nghiên cứu mới chạy được toàn bộ bộ kiểm tra tự động: 454 kiểm tra đạt sau khi bổ sung công cụ thu nguồn, tạo ảnh tối và nhóm kê cổ tay. Bản main không thay đổi thuật toán đã đạt 433 kiểm tra trước khi thêm các công cụ này. Kiểm tra bao phủ công thức lọc, dấu thời gian, thiếu quan sát, mất và nhận lại tay, hình học ROI, hợp đồng dữ liệu và khả năng giữ nguồn phát lại. Kết quả kiểm tra phần mềm không được diễn giải thành độ chính xác nhận dạng trên người dùng.

Không có bằng chứng từ đợt mới buộc phải thay công thức lọc, hợp đồng dữ liệu hoặc tham số nghiên cứu trước khi làm giao diện nộp đồ án. Chúng tôi giữ nguyên Core của bản G7 và chốt phạm vi đó cho bước phát triển tiếp theo. Các bổ sung trong đợt này nằm ở công cụ thu, lập kế hoạch, kiểm tra nguồn và phân tích; không sửa thuật toán để làm đẹp kết quả.

Quyết định này có phạm vi: Core đủ làm nền triển khai đồ án theo đặc tả hiện tại, còn các hạn chế thực nghiệm vẫn được giữ công khai. Nó không đồng nghĩa chứng nhận chất lượng doanh nghiệp, khả năng phục vụ mọi môi trường hoặc hoàn thiện toàn bộ sản phẩm giao diện.

# KẾT LUẬN VÀ KIẾN NGHỊ

## Kết luận

Đề tài đã triển khai nền xử lý từ webcam RGB gồm quản lý ROI, phân tích ánh sáng, tiền xử lý CLAHE theo chính sách, nhận điểm mốc, kiểm tra quan sát, lọc tọa độ và sinh trạng thái tương tác. Đường xử lý trực tiếp và phát lại dùng các hợp đồng dữ liệu riêng; nguồn, cấu hình và kết quả đều có định danh để đối chiếu.

Đợt bổ sung đã tạo dữ liệu có đủ quan sát để tính A1 và A2 trên ba lượt mỗi nhóm. Hai bộ lọc giảm độ phân tán so với Raw ở hai trong ba lượt kê cổ tay và tăng nhẹ ở lượt còn lại. F1/F2 gần nhau trong A1; F2 có RMSE so với Raw nhỏ hơn F1 ở cả ba lượt động. Báo cáo không quy các chỉ số này thành độ chính xác vị trí hoặc độ trễ vật lý.

Trong thực nghiệm tiền xử lý, CLAHE không bật trên nguồn thường và bật trên toàn bộ cửa sổ của nguồn tối giả lập. P0/P1 đều đạt tỷ lệ quan sát hợp lệ 100% ở các lượt đã thử, nên chưa ghi nhận cải thiện của tiền xử lý ở chỉ số chính. Kết quả giả lập được giữ tách biệt với điều kiện thiếu sáng môi trường.

Các kiểm tra tự động và thực nghiệm mới cho phép chốt Core hiện tại để tiếp tục xây dựng giao diện đồ án, không yêu cầu đổi thuật toán ở thời điểm này. Bản minh họa G7 là bằng chứng tích hợp 3D đã có; giao diện mới và đánh giá trải nghiệm người dùng được để ở giai đoạn tiếp theo.

## Hạn chế của đề tài

Mỗi nhóm chỉ có ba lượt; dữ liệu chưa bao phủ nhiều người dùng, camera, nền hoặc góc nhìn. Kê cổ tay không loại bỏ hết chuyển động nhỏ thật, còn quỹ đạo Raw không phải chuẩn vị trí độc lập. Các khung trong cùng nguồn có tương quan thời gian, nên không thể xem số khung lớn là số mẫu độc lập lớn.

Điều kiện thiếu sáng thực không được kiểm soát trong đợt mới. Ảnh giảm cường độ chỉ kiểm tra một biến đổi đầu vào; quá trình lưu MJPG còn có ảnh hưởng nén. Chưa có dữ liệu để kết luận về nhiễu cảm biến, che khuất, nhiều tay hoặc độ ổn định trong mọi môi trường. Core nghiên cứu vẫn sử dụng một bàn tay theo cấu hình; báo cáo không đưa các chức năng nhiều tay ở nhánh giao diện vào phạm vi đã kiểm chứng.

Tọa độ z của mô hình là tương đối, không phải chiều sâu camera theo mét. Cảnh 3D là ứng dụng dựng hình nhận lệnh. Báo cáo chưa đánh giá độ chính xác cử chỉ theo bộ nhãn độc lập, độ trễ đầu cuối, hiệu quả học tập hoặc khả năng triển khai doanh nghiệp.

## Kiến nghị và hướng phát triển

Bước tiếp theo là giao diện gọn tập trung vào vật thể 3D, có hướng dẫn ẩn hiện và tùy chọn phóng to vùng quan sát. Phần ứng dụng tiếp tục tách khỏi Core. Những chức năng sử dụng nhiều đầu ngón hoặc hai tay cần hợp đồng và kiểm tra riêng trước khi được ghi nhận là đã hoàn thành.

Nếu mở rộng đánh giá sau đồ án, cần thu dữ liệu ở điều kiện ánh sáng vật lý được mô tả rõ, đa dạng người dùng và tình huống mất tay, đồng thời đo các chỉ số phù hợp với nhiệm vụ tương tác. Các nhóm mới phải có kế hoạch trước khi xem kết quả. Không thay nguồn, cửa sổ hoặc tham số của hồ sơ đã chốt để tìm một kết quả có lợi hơn.

# PHỤ LỤC

## Phụ lục 1 Danh mục hồ sơ và cách đối chiếu

Các thư mục dưới đây tính từ gốc dự án. Hai tiền tố được viết gọn để bảng dễ đọc: S là runs/round2/ROUND2-20261014-SIM035; H là runs/round2/ROUND2-20261014-HELD-STATIC. Tệp analysis_index.json trong mỗi thư mục trỏ tới thư mục phân tích đầy đủ, gồm metrics.csv, provenance.json và các hình thực nghiệm.

Bảng PL1 Nguồn của kết quả trong báo cáo

| Nội dung | Hồ sơ |
|---|---|
| A1 chính, bảng 3.1 | H/analysis_index.json, khóa a1_static |
| A2, bảng 3.2 | S/analysis_index.json, khóa a2_dynamic |
| B thường, bảng 3.3 | S/analysis_index.json, khóa b_normal |
| B tối giả lập, bảng 3.4 | S/analysis_index.json, khóa b_simulated |
| Kiểm tra nhánh CLAHE | S/activation_audit.json và frames.csv mỗi run |
| A1 ban đầu, bảng PL2 | S/analysis_index.json, khóa a1_static |
| Kế hoạch nguồn bổ sung | experiments/round2/PLAN.md |
| Kế hoạch ảnh tối | experiments/round2/SIMULATED_PLAN.md |
| Kế hoạch kê cổ tay | experiments/round2/HELD_STATIC_PLAN.md |
| Môi trường đã dùng | experiments/round2/environment.lock.txt |

Nguồn gốc ban đầu nằm trong runs/round2/ROUND2-20261014-SUBMISSION. Các lượt có video AVI, bản mô tả nguồn và tệp dấu thời gian thu. Thư mục này còn giữ hai lượt dự kiến thiếu sáng, nhưng điều kiện vật lý không được xác nhận; chúng không được đưa vào bảng 3.4. Hồ sơ lighting_deviation.json ghi rõ lý do chuyển sang điều kiện ảnh tối giả lập.

Giá trị tọa độ trong các bảng được làm tròn đến chín chữ số thập phân. Tỷ lệ B được đổi từ khoảng 0–1 sang phần trăm. CSV giữ giá trị gốc; các mã băm trong siêu dữ liệu giúp xác nhận nguồn video, cấu hình và mô hình đã dùng.

## Phụ lục 2 Các lượt ban đầu và hồ sơ G7 được giữ lại

Bảng PL2 Radial RMS của các lượt ban đầu còn chuyển động tay

| Lượt | Khung chung | F0 | F1 | F2 |
|---|---|---|---|---|
| trial-001 | 241 | 0,096214727 | 0,073141834 | 0,085126615 |
| trial-002 | 241 | 0,138602945 | 0,132160084 | 0,133910893 |
| trial-003 | 241 | 0,156381629 | 0,143007205 | 0,150410823 |

Các giá trị này chứa chuyển động thật của tay trong thao tác thu, nên không được trình bày như phép đo rung thuần túy. Ba nguồn vẫn được dùng cho phép so sánh nhận dạng B, vì chuyển động không làm mất ý nghĩa của tỷ lệ quan sát hợp lệ. Nhóm kê cổ tay là thực nghiệm bổ sung độc lập, không ghi đè nguồn hay thay một lượt chỉ vì số liệu bất lợi.

Hồ sơ G7 tại submission/evidence vẫn được bảo toàn. A1 của hồ sơ đó chỉ có hai lượt tính được, với lần lượt 5 và 128 khung chung; lượt còn lại không có khung dùng được. A2 không tính được chỉ số chính ở cả ba lượt. P0/P1 có tỷ lệ bằng nhau và CLAHE không bật trong các cửa sổ B. Những giới hạn này là lý do thực hiện đợt thu bổ sung, không bị xóa khỏi lịch sử nghiên cứu.

## Phụ lục 3 Chương trình và định danh phiên bản

Mã Core nằm trong src/dip_touchless; cấu hình trong config; công cụ đợt mới trong experiments/round2; chương trình phân tích trong analysis. Phần minh họa G7 nằm trong extensions/stem3d. Các thuật toán và hợp đồng Core của đợt này được giữ từ commit f454c6b8325c85199c0122c0e822fe8e76c1526c, tương ứng bản phát hành g7-final. Các commit công cụ bổ sung không thay thế định danh thuật toán nền.

Python khuyến nghị của kho mã là 3.11. Môi trường cũ trên máy tham chiếu một executable không còn tồn tại, nên đợt bổ sung thực tế dùng môi trường .venv-research với Python 3.12.14. Các phiên bản chính đã ghi nhận gồm NumPy 2.5.4, MediaPipe 1.0.1, OpenCV-contrib-python 4.14.0.94 và Matplotlib 3.11.2. Đây là thông tin thực thi, không phải bằng chứng các phiên bản cho kết quả tương đương nhau. Kết quả G7 và ROUND2 vì thế được trình bày tách biệt.

Các lệnh dưới đây sử dụng môi trường nghiên cứu đã chuẩn bị tại gốc dự án. Phát lại cần các nguồn video và mô hình đã lưu; kiểm tra tự động không cần thu thêm một phiên tay mới.

```powershell
.\.venv-research\Scripts\python.exe -m pytest
.\.venv-research\Scripts\python.exe -m pip check
```

Ba mốc công cụ của đợt bổ sung là 20c363c (thu có hướng dẫn), dcf8861 (ảnh tối giả lập) và 957efe5 (kê cổ tay). Mỗi run giữ phiên bản thực thi đầy đủ trong metadata.json. Tệp hand_landmarker.task có SHA-256 fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1, khớp tài nguyên mô hình G7. Mã băm xác nhận tài nguyên, không biểu thị độ chính xác của mô hình.

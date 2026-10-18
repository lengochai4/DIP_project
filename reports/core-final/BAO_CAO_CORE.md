# PHẦN MỞ ĐẦU

## 1.1 Tổng quan tình hình nghiên cứu

### 1.1.1 Tình hình nghiên cứu trong nước

Nhận dạng cử chỉ bàn tay từ camera đã được nghiên cứu tại Việt Nam trong các bài toán hỗ trợ giao tiếp và điều khiển thiết bị. Phạm Kim Don và Dương Thanh Linh sử dụng MediaPipe để trích xuất điểm mốc bàn tay, sau đó phân loại ký hiệu bằng SVM [1]. Công trình này cho thấy một cách tiếp cận phù hợp với thiết bị phổ thông: sử dụng đặc trưng hình học thay vì xây dựng toàn bộ bộ nhận dạng từ ảnh đầu vào.

Bài toán của đề tài này có mục đích khác. Hệ thống cần chuyển chuyển động bàn tay thành lệnh điều khiển liên tục cho vật thể trong cảnh 3D. Vì vậy, ngoài việc phát hiện được bàn tay, chúng tôi còn phải xem xét sự dao động của tọa độ, khoảng thời gian giữa các khung hình và cách hệ thống xử lý lúc mất dấu tay. Kết quả phân loại ký hiệu của công trình khác không thể dùng trực tiếp để chứng minh chất lượng tương tác của hệ thống này.

### 1.1.2 Tình hình nghiên cứu ngoài nước

MediaPipe Hands của Zhang và cộng sự sử dụng một bộ phát hiện lòng bàn tay kết hợp với mô hình ước lượng điểm mốc, làm cơ sở cho theo dõi bàn tay từ một camera RGB [2]. Đề tài sử dụng MediaPipe như một thành phần cung cấp quan sát. Chúng tôi không huấn luyện lại mô hình nhận dạng bàn tay.

Trong xử lý ảnh, CLAHE tăng cường tương phản cục bộ và giới hạn sự khuếch đại nhiễu [4]. Trong xử lý chuyển động, bộ lọc 1-Euro của Casiez, Roussel và Vogel điều chỉnh tần số cắt theo tốc độ tín hiệu để cân bằng độ mượt và độ đáp ứng [3]. Hai hướng này giải quyết hai giai đoạn khác nhau: tiền xử lý tác động lên ảnh trước nhận dạng; lọc thời gian tác động lên chuỗi tọa độ sau nhận dạng.

### 1.1.3 Những vấn đề cần tiếp tục đánh giá

Một mô hình nhận dạng có thể trả về bàn tay ở một khung hình nhưng không trả về ở khung hình kế tiếp. Nếu ứng dụng chỉ quan tâm tọa độ và bỏ qua trạng thái hợp lệ, vật thể có thể nhảy vị trí hoặc tiếp tục chuyển động khi tay đã rời camera. Lọc tọa độ cũng không khôi phục được một quan sát mà bộ nhận dạng không tạo ra.

Mặt khác, làm ảnh sáng hơn chưa đủ để kết luận bộ nhận dạng hoạt động tốt hơn. Chính sách tăng cường cần được kiểm tra xem có thực sự kích hoạt trong điều kiện thử hay không. Một phép so sánh giữa hai cấu hình xử lý ảnh chỉ có ý nghĩa khi biết các nhánh đã thực thi, nguồn ảnh đầu vào và số khung hình dùng để đánh giá.

### 1.1.4 Hướng tiếp cận của đề tài

Chúng tôi xây dựng một đường xử lý có thể chạy trực tiếp từ webcam hoặc phát lại dữ liệu đã ghi. Vùng quan tâm, mô tả ánh sáng, trạng thái theo dõi và các tham số lọc đều được ghi cùng định danh khung hình. Các cấu hình so sánh dùng chung nguồn phát lại, nhờ đó có thể kiểm tra khác biệt mà không yêu cầu người thực hiện lặp lại chính xác cùng một chuyển động.

Phần ứng dụng 3D nhận trạng thái tương tác từ đường xử lý. Cách tách này giúp chúng tôi đánh giá thuật toán mà không phụ thuộc vào thiết kế giao diện. Trong báo cáo, phần trình bày tập trung vào nền xử lý và thực nghiệm đã có; thiết kế giao diện mới là công việc tiếp theo.

## 1.2 Lý do chọn đề tài

Một webcam RGB là thiết bị dễ tiếp cận để thử nghiệm tương tác không chạm. Khi quan sát hoặc trình bày mô hình STEM, người dùng có thể cần thay đổi góc nhìn và kích thước vật thể trong lúc đứng trước màn hình. Chuyển động bàn tay có thể cung cấp tín hiệu cho các thao tác đó, nhưng độ ổn định của tín hiệu ảnh hưởng trực tiếp đến cảm giác điều khiển.

Đề tài được lựa chọn để nghiên cứu vấn đề này từ góc nhìn xử lý ảnh số. Chúng tôi quan tâm đến cách xác định vùng cần xử lý, đánh giá độ sáng và tương phản, lọc dao động tọa độ và xử lý mất theo dõi. Các thành phần nhận dạng và hiển thị được sử dụng để kiểm chứng đường xử lý, không được xem là thuật toán mới do nhóm xây dựng.

## 1.3 Mục tiêu đề tài

Mục tiêu là xây dựng và đánh giá một hệ thống tương tác với cảnh STEM 3D từ một webcam RGB, trong đó các quyết định xử lý và kết quả thực nghiệm có thể kiểm tra lại. Hệ thống phải phân biệt dữ liệu hợp lệ với dữ liệu thiếu, tính thời gian lọc từ dấu thời gian và tách xử lý ảnh khỏi phần hiển thị.

Ba câu hỏi nghiên cứu được đặt ra. Thứ nhất, chính sách tiền xử lý thích ứng theo ánh sáng có cải thiện tỷ lệ quan sát bàn tay hợp lệ so với không tăng cường ảnh trong những điều kiện đã thử không? Thứ hai, các bộ lọc thời gian thay đổi độ rung và sai lệch quỹ đạo như thế nào so với tọa độ thô? Thứ ba, tín hiệu sau xử lý có thể điều khiển thao tác xoay và thay đổi kích thước vật thể trong một phiên chạy thực tế không?

Chúng tôi không đặt trước tỷ lệ cải thiện hoặc yêu cầu thuật toán đề xuất phải thắng các đường cơ sở. Kết luận được rút ra từ dữ liệu đã ghi, kể cả khi một chỉ số chưa thể tính hoặc một chính sách chưa kích hoạt như dự kiến.

## 1.4 Phương pháp nghiên cứu đối tượng và phạm vi

Đối tượng nghiên cứu là khung hình webcam, tọa độ điểm mốc bàn tay và chuỗi trạng thái tương tác sinh ra từ các tọa độ đó. Phương pháp gồm khảo sát tài liệu, triển khai các thành phần xử lý, kiểm tra bằng tín hiệu tổng hợp, phát lại dữ liệu để so sánh cấu hình và đối chiếu với một phiên tương tác thực tế.

Phạm vi sử dụng một camera RGB và một bàn tay theo cấu hình nghiên cứu. Tọa độ x, y được xử lý trong hệ tọa độ ảnh chuẩn hóa. Giá trị z của mô hình được giữ với ý nghĩa tương đối; báo cáo không diễn giải thành khoảng cách vật lý đến camera. Phần 3D là cảnh được dựng để nhận lệnh tương tác.

Hệ thống không thu thập dữ liệu để huấn luyện mạng nhận dạng mới. Các thực nghiệm không sử dụng camera chiều sâu, nhiều camera hoặc mô phỏng vật lý đầy đủ. Dữ liệu hiện có phục vụ đánh giá mô tả trong phạm vi đề tài, chưa đủ để đưa ra kết luận cho một quần thể người dùng.

# PHẦN NỘI DUNG

# CHƯƠNG 1 CƠ SỞ LÝ THUYẾT

## 1.1 Tương tác từ ảnh và tín hiệu chuyển động

Ảnh webcam cung cấp một chuỗi khung hình, còn ứng dụng tương tác cần một chuỗi lệnh. Giữa hai dạng dữ liệu này có nhiều bước: nhận dạng bàn tay, kiểm tra quan sát, làm mượt tọa độ và ánh xạ chuyển động. Sai sót ở một bước có thể đi đến màn hình dưới dạng chuyển động không mong muốn.

Với tọa độ điểm mốc p tại thời điểm t, thay đổi vị trí giữa hai khung hình có thể làm cơ sở cho lệnh xoay. Tuy nhiên, dao động ngẫu nhiên của điểm mốc cũng tạo ra thay đổi vị trí. Bộ lọc thời gian được dùng để giảm thành phần này, đồng thời cần giữ đủ đáp ứng với chuyển động có chủ ý.

## 1.2 Vùng quan tâm và không gian màu

Vùng quan tâm, gọi tắt là ROI, là một hình chữ nhật trong khung hình đầy đủ. Khi đã có quan sát bàn tay hợp lệ, vùng này được xác định từ vị trí bàn tay trước đó và mở rộng theo tỷ lệ đệm. Khi chưa thấy tay, hệ thống tìm kiếm trên toàn bộ khung hình.

Trong thiết kế của đề tài, ROI giới hạn vùng phân tích và tăng cường ảnh. Mô hình MediaPipe vẫn nhận ảnh đầy đủ sau khi vùng đã xử lý được ghép trở lại. Kích thước ảnh và quy ước tọa độ vì thế được giữ nguyên giữa các cấu hình tiền xử lý.

Ảnh OpenCV được đưa vào dưới dạng BGR. Hệ thống chuyển vùng ảnh sang HSV để phân tích kênh V, sau đó chuyển lại BGR khi cần ghép vùng xử lý. Việc chuyển BGR sang RGB diễn ra ở bộ chuyển tiếp MediaPipe. Mỗi phép chuyển có vị trí xác định để tránh dùng nhầm thứ tự kênh màu.

## 1.3 Mô tả ánh sáng và CLAHE

Độ sáng của ROI được mô tả bởi trung bình kênh V. Khoảng P90 trừ P10 mô tả độ trải cường độ theo cách giảm ảnh hưởng của một số điểm quá sáng hoặc quá tối. Độ lệch chuẩn và các phân vị vẫn được ghi để phục vụ phân tích.

Hai đại lượng dùng cho quyết định được làm ổn định bằng trung bình trượt lũy thừa. Khi trạng thái ánh sáng đã chuyển sang khó, ngưỡng để trở lại bình thường khác ngưỡng để đi vào trạng thái khó. Khoảng trễ này giúp hạn chế bật, tắt xử lý liên tục quanh một ngưỡng.

CLAHE được áp dụng trên kênh V trong ROI. Cấu hình có ba chính sách: bỏ qua, luôn tăng cường và thích ứng. Trong chính sách thích ứng, hệ thống chỉ yêu cầu tăng cường khi trạng thái ánh sáng khác NORMAL. Giá trị enhancement_active trong nhật ký biểu thị CLAHE thực sự đã được áp dụng sau khi giải quyết chính sách, chứ không chỉ là một đề nghị xử lý.

## 1.4 Điểm mốc bàn tay và tính hợp lệ

MediaPipe Hand Landmarker trả về 21 điểm mốc cho bàn tay được phát hiện [5]. Trong triển khai của đề tài, quan sát được đổi sang kiểu dữ liệu riêng, có định danh khung hình, dấu thời gian và trạng thái. Các thành phần lọc và tương tác không nhận trực tiếp đối tượng của thư viện MediaPipe.

Không có tay là một trạng thái riêng, không phải 21 điểm cùng nằm ở gốc tọa độ. Tương tự, thông tin phân loại tay trái hay tay phải không được dùng làm độ tin cậy theo dõi. Đường xử lý phải hoạt động khi không có một tín hiệu chất lượng đo lường phù hợp.

## 1.5 Lọc thông thấp và bộ lọc 1 Euro

Lọc thông thấp kết hợp mẫu mới với trạng thái trước đó. Hệ số kết hợp phụ thuộc tần số cắt và khoảng thời gian thực giữa các mẫu. Trong phần dưới, x là tọa độ thô, x̂ là tọa độ đã lọc, Δt là khoảng thời gian giữa hai mẫu hợp lệ và fc là tần số cắt.

> τ = 1 / (2πfc); α = 1 / (1 + τ/Δt).
> x̂(t) = αx(t) + (1 − α)x̂(t−1).

Đường cơ sở F1 triển khai cấu trúc 1-Euro với bộ lọc đạo hàm riêng [3]. Các tham số min_cutoff, beta và d_cutoff giữ cố định theo cấu hình. Đạo hàm được tính từ mẫu hiện tại và đầu ra đã lọc trước đó, sau đó mới được làm mượt.

> d(t) = [x(t) − x̂(t−1)] / Δt.
> d̂(t) = αd d(t) + (1 − αd)d̂(t−1).
> fc(t) = fmin + β|d̂(t)|.

Trong mã dự án, mỗi điểm mốc có trạng thái x, y độc lập. Tốc độ của một điểm được tính từ hai đạo hàm đã lọc; một tần số cắt chung được áp dụng cho x và y của chính điểm đó. Chuyển động của một điểm không được dùng để điều chỉnh toàn bộ 21 điểm. Giá trị z tương đối của mô hình không tham gia chuẩn tốc độ và được truyền qua không lọc [6].

## 1.6 Bộ lọc thích ứng có giới hạn của đề tài

F2 giữ cấu trúc lọc đạo hàm của F1 và bổ sung cách điều chỉnh beta theo tốc độ. Đây là thiết kế của dự án trên nền 1-Euro, không phải một phần được quy cho thuật toán gốc. Ký hiệu v là tốc độ x, y của một điểm mốc, gv là hệ số điều chỉnh và clip là phép chặn một giá trị trong khoảng cho trước.

> vβ = min(v, vmax).
> β(t) = clip[βbase + gv vβ, βmin, βmax].
> fc(t) = clip[fbase + β(t)v, fc,min, fc,max].

Giới hạn tốc độ đầu vào cho beta và giới hạn tần số cắt là hai ràng buộc khác nhau. Chúng tôi giữ cả hai để tránh một mẫu có tốc độ lớn làm tham số lọc tăng không giới hạn. Khi tốc độ bằng không, beta trở về giá trị nền.

Thiết kế có vị trí dành cho điều chỉnh theo chất lượng quan sát, nhưng nhánh đó bị tắt trong so sánh chính vì không có nguồn chất lượng theo khung hình được xác nhận phù hợp. Khi chất lượng không có, F2 dùng fbase thay vì điền một giá trị tin cậy giả định. Các công thức và quy ước x, y được xác định trong đặc tả thuật toán của dự án [6].

## 1.7 Mất theo dõi và nhận lại bàn tay

Khi quan sát không hợp lệ, hệ thống không cập nhật bộ lọc bằng tọa độ giả và không phát lệnh chuyển động. Với khoảng mất ngắn, trạng thái lọc có thể được giữ; với mất kéo dài hoặc dấu thời gian không hợp lệ, trạng thái được đặt lại theo cấu hình.

Mẫu hợp lệ đầu tiên sau khi khởi tạo lại được dùng để tạo trạng thái mới. Lệnh xoay và thay đổi kích thước ở thời điểm này là trung tính. Cách xử lý đó tránh việc lấy một tọa độ cũ và một tọa độ mới ở xa nhau để tạo ra lệnh đột ngột.

## 1.8 Ánh xạ chuyển động và cử chỉ pinch

Trong đường nghiên cứu, đầu ngón trỏ là điểm điều khiển xoay. Chênh lệch tọa độ x, y qua các mẫu hợp lệ được đưa qua vùng chết, hệ số khuếch đại và giới hạn độ thay đổi. Lệnh sau cùng được biểu diễn độc lập với thư viện dựng hình.

Pinch được mô tả bằng khoảng cách giữa đầu ngón cái và đầu ngón trỏ chia cho độ rộng bàn tay đo giữa hai điểm mốc lòng bàn tay. Hai ngưỡng vào và ra khác nhau giữ trạng thái pinch ổn định hơn quanh biên. Thay đổi tỷ lệ pinch trong lúc pinch liên tục tạo ra lệnh thay đổi kích thước.

Phần hiển thị tích lũy các lệnh thành góc xoay và kích thước của vật thể. Nó nhận InteractionState, không tự tính lại tốc độ lọc hoặc đọc cấu trúc nội bộ của bộ nhận dạng.

# CHƯƠNG 2 PHƯƠNG PHÁP NGHIÊN CỨU VÀ TRIỂN KHAI HỆ THỐNG

## 2.1 Kiến trúc hệ thống

Chúng tôi chia hệ thống thành nền xử lý ảnh và phần ứng dụng minh họa. Nền xử lý chịu trách nhiệm từ thu ảnh đến sinh trạng thái tương tác và nhật ký. Phần ứng dụng nhận lệnh để dựng cảnh. Phân tích thực nghiệm đọc dữ liệu đã ghi, không đọc trạng thái nội bộ của ứng dụng hiển thị.

![Hình 2.1 Luồng xử lý và các đầu ra của hệ thống](assets/pipeline.png)

FramePacket giữ ảnh, màu, định danh và thời gian cùng nhau. TrackingFrame giữ tọa độ thô, tọa độ đã lọc và trạng thái từng bước. InteractionState giữ con trỏ, tỷ lệ pinch và các lệnh chuyển động. Ba kiểu dữ liệu giúp kiểm tra một lệnh trên màn hình được tạo từ khung hình nào và dữ liệu quan sát nào.

## 2.2 Triển khai vùng quan tâm và tiền xử lý

ROI có ba trạng thái. SEARCHING dùng toàn bộ khung hình. TRACKING dùng vùng bàn tay đã quan sát cùng phần đệm. COASTING mở rộng vùng trước đó trong số khung hình giới hạn khi mất dấu. Vùng không hợp lệ hoặc hết thời gian giữ khiến hệ thống trở lại SEARCHING.

Kích thước và biên ROI luôn được kiểm tra với khung hình. Tỷ lệ đệm được cấu hình bên ngoài thuật toán. Khi có tăng cường, chỉ ROI được thay đổi, sau đó được ghép vào ảnh đầy đủ có cùng kích thước để chuyển tới bộ nhận dạng.

Các tham số dưới đây là giá trị cấu hình của bản nghiên cứu, không phải những ngưỡng đã được chứng minh tối ưu.

Bảng 2.1 Một số tham số cấu hình của nền xử lý

| Nhóm | Tham số | Giá trị |
|---|---|---|
| ROI | Tỷ lệ đệm khi theo dõi | 0,20 |
| ROI | Tỷ lệ mở rộng khi giữ vùng | 0,15 |
| ROI | Số khung hình giữ vùng | 5 |
| Ánh sáng | Hệ số EMA | 0,20 |
| Ánh sáng | Ngưỡng vào / ra thiếu sáng | 70 / 85 trên kênh V |
| Ánh sáng | Ngưỡng vào / ra tương phản thấp | 35 / 45 cho P90 − P10 |
| CLAHE | clip_limit / tile_grid_size | 2,0 / 8 × 8 |
| F1 | fmin / beta / d_cutoff | 1 Hz / 0 / 1 Hz |
| F2 | beta_min / beta_base / beta_max | 0 / 0 / 1 |
| F2 | velocity_gain / velocity_max | 0,1 / 10 |
| F2 | Giới hạn tần số cắt | 1 đến 10 Hz |
| Thời gian | Khoảng trống gây đặt lại | 0,50 giây |
| Pinch | Ngưỡng bật / tắt | 0,30 / 0,40 |

## 2.3 Nguồn dữ liệu nghiên cứu

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

## 2.4 Các đường cơ sở và cách so sánh

F0 sử dụng tọa độ thô và không làm mượt thời gian. F1 sử dụng bộ lọc 1-Euro cố định theo cấu hình. F2 sử dụng bộ lọc thích ứng có giới hạn của dự án. Các profile F0, F1, F2 giữ chung chính sách tiền xử lý thích ứng để phép so sánh tập trung vào phần lọc.

P0 bỏ qua CLAHE, còn P1 dùng chính sách CLAHE thích ứng. Trong so sánh P0/P1, lọc thời gian được giữ ở F0. Cách tách này tránh thay đồng thời tiền xử lý và bộ lọc rồi không biết khác biệt đến từ thành phần nào.

Mỗi cấu hình được phát lại trên cùng nguồn của một lượt. Khi chỉ số cần tọa độ ở cả hai cấu hình, dữ liệu được ghép theo định danh khung hình và dấu thời gian. Các khung không dùng được không được biến thành tọa độ bằng không.

## 2.5 Thiết lập thực nghiệm và tiêu chí loại trừ

Cửa sổ phân tích chính được cố định từ 2,0 đến 10,0 giây. Phần đầu và cuối nguồn nằm ngoài cửa sổ này. Các lựa chọn về nguồn, cửa sổ và chỉ số không được đổi sau khi xem một kết quả bất lợi.

Một lượt chỉ bị loại hoàn toàn khi nguồn hỏng, thời gian không hợp lệ, ghép cặp thất bại do lỗi nguồn hoặc hệ thống, hoặc thu nguồn thất bại hoàn toàn. Theo dõi kém, nhiều khung NO_HAND hay độ rung cao không phải lý do để bỏ lượt. Trường hợp không tính được chỉ số vẫn có bản ghi riêng cùng nguyên nhân.

Thực nghiệm hiện tại sử dụng thống kê mô tả. Chúng tôi không thực hiện kiểm định suy luận hoặc xem các khung hình của một video như các người tham gia độc lập. Số lượt đánh giá nhỏ là một giới hạn của kết luận.

## 2.6 Các chỉ số đánh giá

### 2.6.1 Độ rung tĩnh

A1 sử dụng radial RMS jitter của điểm mốc 8 trong hệ tọa độ ảnh chuẩn hóa. Với N khung hình hợp lệ chung và vị trí trung bình p̄ trong cửa sổ, chỉ số được tính như sau:

> J = √[(1/N) Σ ||p(t) − p̄||²].

Một giá trị nhỏ hơn biểu thị chuỗi tọa độ ít phân tán hơn trong lượt tĩnh đang xét. Chỉ số không có đơn vị centimet và cũng không phải sai số so với vị trí thật của đầu ngón tay.

### 2.6.2 Sai lệch quỹ đạo động

A2 dùng RMSE giữa quỹ đạo đã lọc và quỹ đạo F0 trên các khung hình hợp lệ chung. Với đầu ra lọc pF và tọa độ thô p0, chỉ số là:

> R = √[(1/N) Σ ||pF(t) − p0(t)||²].

Quỹ đạo F0 là tham chiếu để mô tả tác động của làm mượt, không phải quỹ đạo thật đã được đo độc lập. Chỉ số này không trực tiếp đo độ trễ đầu cuối từ tay tới màn hình. Nếu N bằng không, phép đo chưa có giá trị thay vì được gán bằng không.

### 2.6.3 Tỷ lệ quan sát bàn tay hợp lệ

Thực nghiệm B dùng tỷ lệ số khung có trạng thái VALID hoặc REACQUIRED trên tổng số khung hình được phân tích. Mỗi lượt có 241 khung trong cửa sổ đã lưu. Ngoài tỷ lệ này, chúng tôi kiểm tra trạng thái ánh sáng và enhancement_active để biết đường xử lý thực tế.

> Tỷ lệ hợp lệ = số khung VALID hoặc REACQUIRED / tổng số khung phân tích.

## 2.7 Ghi dữ liệu và khả năng kiểm tra lại

Mỗi lần chạy lưu cấu hình đã giải quyết, mã băm cấu hình, định danh nguồn, phiên bản mã, điểm mốc và các sự kiện. Các tệp chính là metadata.json, resolved_config.yaml, frames.csv, landmarks.csv và events.csv. Bảng kết quả phân tích giữ cả những chỉ số không có giá trị.

Hồ sơ kèm biểu đồ còn giữ profile, run_id, cửa sổ phân tích và số mẫu. Do đó, một số liệu trong báo cáo có thể được đối chiếu về tệp nguồn thay vì chỉ dựa vào ảnh chụp màn hình. Phụ lục trình bày các đường dẫn tương đối cần dùng để kiểm tra.

## 2.8 Kiểm tra triển khai và vai trò phần 3D

Các kiểm tra tự động của dự án bao phủ công thức lọc, thời gian không đều, mất quan sát, nhận lại tay, vùng ảnh hợp lệ và định dạng nhật ký. Tín hiệu tổng hợp được dùng để kiểm tra tính chất của thuật toán, nhưng không thay cho dữ liệu webcam trong kết luận thực nghiệm.

Phần 3D sử dụng lệnh xoay và thay đổi kích thước từ InteractionState. Báo cáo sử dụng quan sát của bản minh họa G7 để mô tả khả năng tích hợp. Không đưa các chức năng giao diện và extension ở những nhánh phát triển sau vào kết quả của nền nghiên cứu này.

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

# TÀI LIỆU THAM KHẢO

[1] Phạm Kim Don và Dương Thanh Linh, “Ứng dụng MediaPipe và SVM trong nhận dạng ngôn ngữ ký hiệu hỗ trợ người khiếm thính”, Tạp chí Khoa học Lạc Hồng, số 22, tr. 19–24, 2025. DOI: 10.61591/jslhu.22.711. https://vjol.info.vn/index.php/jslhu/article/download/120016/99840/

[2] F. Zhang, V. Bazarevsky, A. Vakunov, A. Tkachenka, G. Sung, C.-L. Chang và M. Grundmann, “MediaPipe Hands: On-device Real-time Hand Tracking”, arXiv:2006.10214, 2020. https://arxiv.org/abs/2006.10214

[3] G. Casiez, N. Roussel và D. Vogel, “1€ Filter: A Simple Speed-based Low-pass Filter for Noisy Input in Interactive Systems”, Proceedings of CHI 2012, tr. 2527–2530, 2012. DOI: 10.1145/2207676.2208639. https://gery.casiez.net/1euro/

[4] OpenCV, “Histograms - 2: Histogram Equalization”, tài liệu OpenCV 4.x, phần CLAHE. Truy cập ngày 13/10/2026. https://docs.opencv.org/4.x/d5/daf/tutorial_py_histogram_equalization.html

[5] Google AI Edge, “Hand landmarks detection guide for Python”, tài liệu MediaPipe Hand Landmarker. Truy cập ngày 13/10/2026. https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python

[6] Hồ sơ đặc tả DIP Touchless STEM, canonical v1.2, các tài liệu 00 đến 05 và cấu hình nghiên cứu trong mã nguồn tại bản G7. Các công thức lọc, không gian tọa độ và trạng thái được mô tả trong docs/02_ARCHITECTURE_AND_CONTRACTS.md và docs/03_ALGORITHM_AND_EXPERIMENTS.md.

[7] Hồ sơ thực nghiệm G7 của DIP Touchless STEM: kế hoạch thu cuối, manifest A1/A2/B, các bảng metrics.csv, provenance.json và nhật ký minh họa ngày 29/09/2026. Bản phát hành g7-final; commit f454c6b8325c85199c0122c0e822fe8e76c1526c. Thư mục experiments/final và submission/evidence trong mã nguồn.

[8] Hồ sơ thực nghiệm bổ sung DIP Touchless STEM ngày 14/10/2026: PLAN.md, SIMULATED_PLAN.md, HELD_STATIC_PLAN.md và environment.lock.txt tại experiments/round2; các nguồn, nhật ký và phân tích riêng tại runs/round2/ROUND2-20261014-SUBMISSION, ROUND2-20261014-SIM035 và ROUND2-20261014-HELD-STATIC. Đường dẫn đối chiếu trình bày ở Phụ lục 1.

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

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

Dữ liệu phát lại được chia thành ba nhóm nguồn: tay gần đứng yên ở ánh sáng thường, tay chuyển động ở ánh sáng thường và tay gần đứng yên trong phòng được ghi nhận là thiếu sáng. Mỗi nhóm có ba lượt ghi. Các tệp được dùng theo kế hoạch đã xác định trước khi xem kết quả [7].

Nhóm nguồn tĩnh ánh sáng thường được dùng lại cho A1 và B-normal. Vì vậy, bốn nhóm phân tích A1, A2, B-normal và B-lowlight không tương ứng với bốn bộ nguồn độc lập. Tổng cộng kế hoạch có chín tệp nguồn trong ba nhóm; cùng một tệp có thể đi qua nhiều cấu hình.

Bảng 2.2 Nguồn ghi và mục đích phân tích

| Nhóm nguồn | Số lượt | Phép phân tích | Cấu hình so sánh |
|---|---|---|---|
| static_normal | 3 | A1 và B-normal | F0/F1/F2; P0/P1 |
| dynamic_normal | 3 | A2 | F0/F1/F2 |
| static_lowlight | 3 | B-lowlight | P0/P1 |

Kế hoạch thu dùng camera chỉ số 0, yêu cầu khung hình 640 × 480 và 30 FPS, lưu MJPG AVI ở dạng BGR chưa tiền xử lý. Mỗi lượt có thời gian ghi dự kiến 12 giây sau 3 giây ổn định thiết bị. Giá trị yêu cầu và giá trị quan sát của camera là hai loại thông tin khác nhau; báo cáo không suy từ cấu hình 30 FPS thành tốc độ xử lý thực tế.

Ảnh nguồn và siêu dữ liệu có định danh và mã băm. Trạng thái phơi sáng tự động hoặc cân bằng trắng tự động được giữ là unknown nếu chưa kiểm chứng. Chúng tôi không gán một trạng thái thiết bị dựa trên việc ảnh nhìn sáng hay tối.

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

A2 dự kiến dùng RMSE giữa quỹ đạo đã lọc và quỹ đạo F0 trên các khung hình hợp lệ chung. Với đầu ra lọc pF và tọa độ thô p0, chỉ số là:

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

Các kết quả trong chương này được đối chiếu từ bảng metrics.csv và provenance.json của bốn nhóm A1, A2, B-normal và B-lowlight [7]. Mỗi nhóm giữ ba lượt theo kế hoạch. Giá trị được trình bày với số chữ số phù hợp để đọc; tệp CSV giữ độ chính xác gốc.

Không có một bộ dữ liệu kiểm chứng vị trí tay thật độc lập cho các lượt này. Chúng tôi vì thế đánh giá độ rung của đầu ra, sai lệch so với đường thô và tính hợp lệ của quan sát, thay vì gọi các kết quả là độ chính xác định vị vật lý.

## 3.2 Kết quả độ rung tĩnh A1

Bảng 3.1 Radial RMS jitter của các đường F0 F1 F2

| Lượt | Số khung chung | F0 | F1 | F2 |
|---|---|---|---|---|
| trial-001 | 5 | 0,006607584 | 0,001628449 | 0,001629071 |
| trial-002 | 0 | Chưa tính được | Chưa tính được | Chưa tính được |
| trial-003 | 128 | 0,030597142 | 0,026704461 | 0,026753300 |

Ở trial-001 và trial-003, F1 và F2 đều có độ rung nhỏ hơn F0. Kết quả phù hợp với vai trò làm mượt của lọc thông thấp trên những nguồn tĩnh được giữ lại. Tuy nhiên, hai bộ lọc cho giá trị rất gần nhau; dữ liệu hiện tại không cho cơ sở để kết luận F2 vượt trội hơn F1.

![Hình 3.1 Độ rung tĩnh trên hai lượt có dữ liệu ghép cặp](assets/a1_jitter.png)

Trial-001 chỉ có năm khung hình hợp lệ chung. Đây là một lượng dữ liệu nhỏ trong cửa sổ tám giây, nên kết quả của lượt này chỉ nên được đọc như một quan sát mô tả yếu. Trial-002 không có khung hợp lệ chung và được giữ với nguyên nhân no_common_usable_frames.

Trial-003 có nhiều khung chung hơn nhưng vẫn là một lượt ghi. Sự khác nhau giữa hai lượt có dữ liệu nhắc lại rằng tính ổn định của bộ nhận dạng và điều kiện nguồn ảnh ảnh hưởng đến lượng dữ liệu đánh giá. Báo cáo không lấy hai lượt này để suy ra một tỷ lệ cải thiện chung cho mọi điều kiện sử dụng.

## 3.3 Kết quả quỹ đạo động A2

Bảng 3.2 Khả năng tính chỉ số chính của A2

| Lượt | Khung hợp lệ chung trong cửa sổ | RMSE chính | Nguyên nhân |
|---|---|---|---|
| trial-001 | 0 | Chưa tính được | Không có khung hợp lệ chung |
| trial-002 | 0 | Chưa tính được | Không có khung hợp lệ chung |
| trial-003 | 0 | Chưa tính được | Không có khung hợp lệ chung |

Không lượt nào của A2 cung cấp đủ quan sát trong cửa sổ 2,0 đến 10,0 giây để tính chỉ số chính. Chẩn đoán đã lưu cho thấy trial-001 và trial-002 có toàn bộ 360 khung phát lại ở trạng thái NO_HAND. Trial-003 có một khung tọa độ thô hợp lệ ở khung 33, nằm ngoài cửa sổ chính.

Trong từng lượt, tập khung có quan sát thô dùng được giống nhau giữa F0, F1 và F2. Vì vậy, việc không tính được A2 không phải bằng chứng cho một lỗi ghép cặp riêng của một bộ lọc. Vấn đề trước hết là thiếu quan sát bàn tay để tạo ra quỹ đạo so sánh.

Chúng tôi giữ nguyên nguồn và cửa sổ đã định. Kết quả này là một phần của thực nghiệm, không được thay bằng giá trị RMSE bằng không. Do A2 chưa đánh giá được, kết luận về sự cân bằng giữa giảm rung và đáp ứng chuyển động của F2 vẫn chưa đầy đủ.

## 3.4 Kết quả tiền xử lý trong ánh sáng thường

Bảng 3.3 Tỷ lệ quan sát hợp lệ của B normal

| Lượt | Khung phân tích mỗi điều kiện | P0 | P1 |
|---|---|---|---|
| trial-001 | 241 | 2,074689% | 2,074689% |
| trial-002 | 241 | 0% | 0% |
| trial-003 | 241 | 53,112033% | 53,112033% |

![Hình 3.2 So sánh P0 và P1 trong nhóm ánh sáng thường](assets/b_normal.png)

P0 và P1 có cùng tỷ lệ hợp lệ trong từng lượt. Hai lượt đầu có tỷ lệ rất thấp, còn lượt thứ ba cao hơn nhưng vẫn có nhiều khung không có quan sát dùng được. Kết quả thể hiện độ nhạy của đường nhận dạng với nguồn ảnh đang xét và không chứng minh một tỷ lệ nhận tay ổn định trên mọi điều kiện.

## 3.5 Kết quả tiền xử lý trong nhóm thiếu sáng

Bảng 3.4 Tỷ lệ quan sát hợp lệ của B lowlight

| Lượt | Khung phân tích mỗi điều kiện | P0 | P1 |
|---|---|---|---|
| trial-001 | 241 | 0% | 0% |
| trial-002 | 241 | 0% | 0% |
| trial-003 | 241 | 0% | 0% |

Cả ba lượt của nhóm được ghi nhãn low-light-room đều có tỷ lệ hợp lệ bằng không cho P0 và P1. Kiểm tra kích hoạt cho thấy trong cả B-normal lẫn B-lowlight, P1 ở trạng thái NORMAL và enhancement_active bằng false trên toàn bộ 723 khung phân tích của mỗi nhóm.

Như vậy, chính sách thích ứng không áp dụng CLAHE trong cửa sổ đánh giá. Đây là giới hạn của quyết định kích hoạt trên các nguồn và cấu hình đã dùng. Dữ liệu không cho phép diễn giải rằng CLAHE đã được áp dụng nhưng không hiệu quả.

Trạng thái phơi sáng và cân bằng trắng tự động của các nguồn thiếu sáng được ghi là unknown. Có thể đặt câu hỏi về tác động của thiết bị hoặc cách xác định ROI tới các mô tả ánh sáng, nhưng chưa có bằng chứng đủ để khẳng định một nguyên nhân cụ thể. Chúng tôi giữ điều này ở mức vấn đề cần kiểm tra trong lần thu dữ liệu tiếp theo.

## 3.6 Minh họa phương pháp và quan sát tương tác

Hồ sơ G7 có một hình minh họa ROI và kênh V trước, sau xử lý được tạo ở khung 161 bằng chính bộ tiền xử lý của dự án. Trong hình đó, chính sách được ép thành always để quan sát tác động CLAHE. Nhật ký P1 gốc của cùng khung vẫn ghi NORMAL và enhancement_active bằng false. Vì vậy, hình minh họa không được dùng thay cho kết quả chính của B [7].

Phiên minh họa thực tế ngày 29/09/2026 đã ghi nhận thao tác xoay và thay đổi kích thước vật thể cùng việc đóng hệ thống sạch. Một lần chạy kiểm tra hành vi xử lý 4.947 khung hình; lần chạy sau khi lưu mã xử lý 1.188 khung và có định danh phiên bản thực thi cụ thể. Các số khung này là dữ liệu nhật ký của phiên, không phải FPS hoặc tỷ lệ thành công.

Hồ sơ cũng ghi nhận một số quan sát giống bàn tay ở vùng mặt hoặc nền, gây xoay nhỏ ngoài ý muốn. Đây là hạn chế thực tế của bộ nhận dạng và đường tương tác đang dùng. Phiên chạy chứng minh đường xử lý có thể nối tới cảnh 3D, nhưng không đủ để định lượng độ chính xác cử chỉ hoặc độ ổn định ở mọi môi trường.

## 3.7 Đánh giá theo các câu hỏi nghiên cứu

Đối với câu hỏi về tiền xử lý, chỉ số hợp lệ đã có ở tất cả lượt B, nhưng không ghi nhận cải thiện giữa P0 và P1. Do CLAHE không kích hoạt, kết luận giới hạn ở chính sách thích ứng và dữ liệu đã thử; chưa có một phép so sánh trực tiếp giữa CLAHE đang hoạt động và bỏ qua tăng cường.

Đối với câu hỏi về lọc thời gian, A1 cung cấp hai lượt mô tả việc giảm rung của F1 và F2 so với Raw. F1 và F2 gần nhau, trong khi A2 chưa có chỉ số. Chúng tôi chưa thể kết luận F2 có ưu thế đầy đủ về cả độ ổn định và đáp ứng.

Đối với câu hỏi về tương tác, bản minh họa đã thực thi chuỗi xử lý từ camera tới lệnh 3D. Quan sát đó xác nhận khả năng tích hợp của nguyên mẫu. Các lỗi nhận dạng ngoài ý muốn vẫn được giữ trong phần hạn chế.

## 3.8 Hạn chế của thực nghiệm

Số nguồn ghi và số lượt có thể đánh giá còn ít. A1 có một lượt chỉ gồm năm mẫu chung; A2 hoàn toàn chưa có quỹ đạo chính để so sánh. Không có phép đo vị trí thật, độ trễ đầu cuối hoặc một nhóm người tham gia được thiết kế để đánh giá khả năng khái quát.

Điều kiện thiếu sáng được mô tả theo hoàn cảnh thu nguồn, chưa có số đo ánh sáng môi trường độc lập. Chính sách kích hoạt dựa trên ROI không vào nhánh CLAHE ở các cửa sổ đã phân tích. Những yếu tố này cần được làm rõ trước khi thu thêm dữ liệu, thay vì chỉ thay đổi bộ lọc để tìm một kết quả tốt hơn.

Các phiên ghi nhận phần ứng dụng hiện tại không phải một đánh giá trải nghiệm người dùng có cấu trúc. Báo cáo chưa đưa ra kết luận về hiệu quả học tập, độ thuận tiện của giao diện mới hoặc khả năng triển khai cho nhiều thiết bị.

# KẾT LUẬN VÀ KIẾN NGHỊ

## Kết luận

Đề tài đã xây dựng nền xử lý ảnh webcam, gồm quản lý ROI, chính sách CLAHE, nhận dạng qua MediaPipe, lọc thời gian và xử lý mất dấu tay. Nền xử lý tách khỏi cảnh 3D và lưu định danh để kiểm tra lại thực nghiệm.

F1 và F2 giảm radial RMS jitter so với Raw ở hai lượt tĩnh có dữ liệu, nhưng cho kết quả gần nhau và một lượt chỉ có năm mẫu. A2 chưa có chỉ số chính, nên lợi ích về đáp ứng của F2 chưa được chứng minh.

P0 và P1 có cùng tỷ lệ quan sát hợp lệ; CLAHE không kích hoạt trong các cửa sổ đã thử. Phiên minh họa xác nhận khả năng điều khiển cảnh 3D, đồng thời ghi nhận nhận dạng ngoài ý muốn.

## Hạn chế của đề tài

Dữ liệu còn ít, thiếu quỹ đạo A2 và điều kiện CLAHE thực sự hoạt động, nên chưa đủ để khẳng định ưu thế tổng quát. Độ sâu bàn tay và đại lượng trong cảnh không có ý nghĩa đo đạc vật lý.

Phần ứng dụng cần được thiết kế lại theo mục tiêu sử dụng cụ thể và đánh giá riêng về trải nghiệm người dùng.

## Kiến nghị và hướng phát triển

Cần kiểm tra đầu vào, khả năng nhận tay và điều kiện thu trước khi đánh giá lại quỹ đạo động. Bộ nguồn mới phải có kế hoạch xác định trước và được lưu như một đợt thực nghiệm mới, không thay nguồn trong hồ sơ G7.

Với tiền xử lý, cần kiểm tra ROI, ngưỡng kích hoạt và nhánh CLAHE thực thi trước khi diễn giải ảnh hưởng tới nhận dạng. Thông tin phơi sáng và điều kiện ánh sáng cần được ghi rõ hơn khi có khả năng đo.

Giao diện mới có thể phát triển trên nhánh riêng và tiếp tục nhận dữ liệu qua hợp đồng của nền xử lý. Thay đổi thuật toán hoặc tham số nghiên cứu cần có phiên bản và bằng chứng đánh giá tương ứng.

# TÀI LIỆU THAM KHẢO

[1] Phạm Kim Don và Dương Thanh Linh, “Ứng dụng MediaPipe và SVM trong nhận dạng ngôn ngữ ký hiệu hỗ trợ người khiếm thính”, Tạp chí Khoa học Lạc Hồng, số 22, tr. 19–24, 2025. DOI: 10.61591/jslhu.22.711. https://vjol.info.vn/index.php/jslhu/article/download/120016/99840/

[2] F. Zhang, V. Bazarevsky, A. Vakunov, A. Tkachenka, G. Sung, C.-L. Chang và M. Grundmann, “MediaPipe Hands: On-device Real-time Hand Tracking”, arXiv:2006.10214, 2020. https://arxiv.org/abs/2006.10214

[3] G. Casiez, N. Roussel và D. Vogel, “1€ Filter: A Simple Speed-based Low-pass Filter for Noisy Input in Interactive Systems”, Proceedings of CHI 2012, tr. 2527–2530, 2012. DOI: 10.1145/2207676.2208639. https://gery.casiez.net/1euro/

[4] OpenCV, “Histograms - 2: Histogram Equalization”, tài liệu OpenCV 4.x, phần CLAHE. Truy cập ngày 13/10/2026. https://docs.opencv.org/4.x/d5/daf/tutorial_py_histogram_equalization.html

[5] Google AI Edge, “Hand landmarks detection guide for Python”, tài liệu MediaPipe Hand Landmarker. Truy cập ngày 13/10/2026. https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python

[6] Hồ sơ đặc tả DIP Touchless STEM, canonical v1.2, các tài liệu 00 đến 05 và cấu hình nghiên cứu trong mã nguồn tại bản G7. Các công thức lọc, không gian tọa độ và trạng thái được mô tả trong docs/02_ARCHITECTURE_AND_CONTRACTS.md và docs/03_ALGORITHM_AND_EXPERIMENTS.md.

[7] Hồ sơ thực nghiệm G7 của DIP Touchless STEM: kế hoạch thu cuối, manifest A1/A2/B, các bảng metrics.csv, provenance.json và nhật ký minh họa ngày 29/09/2026. Bản phát hành g7-final; commit f454c6b8325c85199c0122c0e822fe8e76c1526c. Thư mục experiments/final và submission/evidence trong mã nguồn.

# PHỤ LỤC

## Phụ lục 1 Danh mục dữ liệu và nguồn số liệu

Bảng PL1 Đường dẫn tương đối tới hồ sơ đánh giá

| Nội dung | Thư mục hoặc tệp |
|---|---|
| Kế hoạch thu nguồn | experiments/final/G7_FINAL_TRIAL_PLAN.md |
| A1 | submission/evidence/a1_static/metrics.csv |
| A2 | submission/evidence/a2_dynamic/metrics.csv |
| B ánh sáng thường | submission/evidence/b_normal/metrics.csv |
| B thiếu sáng | submission/evidence/b_lowlight/metrics.csv |
| Nguồn gốc mỗi nhóm | provenance.json trong các thư mục trên |
| Minh họa CLAHE cưỡng bức | submission/evidence/dip_visual/dip_clahe_frame161.json |

Các bảng trong báo cáo dùng số liệu của những tệp trên. Riêng tỷ lệ B được đổi từ tỷ lệ trong khoảng 0 đến 1 sang phần trăm để trình bày; các giá trị chưa có không được đổi thành số không. Mã băm nguồn và quy tắc loại trừ được giữ trong provenance.json.

## Phụ lục 2 Chương trình máy tính

Mã nguồn chính nằm trong src/dip_touchless. Cấu hình được đặt tại config, công cụ thực nghiệm tại experiments và phân tích tại analysis. Phần minh họa G7 nằm trong extensions/stem3d. Các thành phần giao tiếp qua hợp đồng dữ liệu của dự án.

Để chuẩn bị môi trường nghiên cứu, sử dụng Python 3.11 theo hướng dẫn của kho mã. Các lệnh cơ bản dưới đây được dùng tại thư mục gốc dự án; tài nguyên mô hình MediaPipe cần được đặt đúng đường dẫn cấu hình trước khi chạy có nhận dạng.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pytest
```

Lệnh kiểm tra tự động không yêu cầu một phiên thao tác tay mới. Các thực nghiệm phát lại còn cần tệp nguồn video đã được ghi trong kế hoạch. Tên tệp, dấu thời gian và cấu hình không được thay sau khi xem kết quả để làm phép so sánh có lợi hơn.

## Phụ lục 3 Định danh phiên bản nghiên cứu

Bản phát hành nghiên cứu là g7-final, tương ứng commit f454c6b8325c85199c0122c0e822fe8e76c1526c. Phiên minh họa có định danh đầy đủ g7-demo-20260929-192030 được thực thi ở commit 6a87dc50f9d3920ed9fd39a2669e266be00f9735. Hai mốc có vai trò khác nhau: một mốc phát hành và một mốc thực thi đã được nhật ký ghi nhận.

Tệp mô hình được ghi là hand_landmarker.task với SHA-256 fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1. Thông tin này dùng để xác nhận tài nguyên thực thi, không biểu thị chất lượng nhận dạng của mô hình trên các nguồn đã thử.

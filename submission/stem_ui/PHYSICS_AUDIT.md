# Rà soát Vật lý — 18/10/2026

Đây là bản ghi kiểm tra, không thay thế đặc tả chuẩn trong `docs/01..05`.
Phạm vi: tám mô hình cơ học lý tưởng, đơn vị SI. Tay đặt thông số mô phỏng,
không đo lực, độ dài hay vận tốc thật từ webcam. Không thay đổi Core hoặc số
liệu báo cáo DIP. Model revision hiện tại: **2**.

| Bài | Quan hệ đã đối chiếu | Giới hạn cần nhớ |
|---|---|---|
| Lực, ma sát | ΣF=ma; ma sát nghỉ cân bằng lực trong giới hạn μsN; ma sát trượt có độ lớn μkN, ngược vận tốc. Tách bước ở thời điểm dừng và tính công/tiêu hao trên từng đoạn. | Ma sát Coulomb, không mô phỏng vật liệu hay lăn. |
| Mặt phẳng nghiêng | N=mg cosθ; ma=F−mg sinθ+fms; h=s sinθ; Δ(K+U)+Q=W lực kéo. Vận tốc nằm dọc dốc, có dấu. | F song song dốc; gốc dốc là mốc thế năng, U có thể âm. |
| Rơi, ném xiên | x=v₀ cosθ·t; y=h+v₀ sinθ·t−gt²/2; vx không đổi, vy=v₀ sinθ−gt. Giải thời điểm chạm đất nằm trong bước. | Không cản khí/nảy đất; vận tốc cuối là ngay trước chạm. Hết thời gian không đồng nghĩa đã rơi trúng đích. |
| Va chạm 1D | Bảo toàn động lượng; v₂′−v₁′=e(v₁−v₂); tổn hao ΔK=μ(1−e²)(v₁−v₂)²/2, μ=m₁m₂/(m₁+m₂). | Một va chạm tức thời trên ray; không tính dạng xung lực, biến dạng hoặc quay. |
| Lò xo, giảm chấn | mx″+cx′+kx=0; E=mv²/2+kx²/2; dQ/dt=cv². Đối chiếu nghiệm giải tích dưới/tới hạn/quá tắt dần. | Dao động ngang tuyến tính. T₀=2π√(m/k) là giá trị riêng khi c=0, không phải chu kỳ thực khi có cản. |
| Con lắc | θ″=−(g/L)sinθ−bθ′/(mL²); K=mL²ω²/2; U=mgL(1−cosθ); dQ/dt=bω². Lực căng T=m(g cosθ+Lω²); lực cản tiếp tuyến −bω/L. | Dây lý tưởng, vật điểm, góc thả trong miền cấu hình. T₀ góc nhỏ, không cản khác chu kỳ đo. |
| Đòn bẩy | τnet=m₁gr₁−m₂gr₂; cân bằng khi τnet≈0 theo dung sai bài; phản lực tựa R=(m₁+m₂)g. | Sơ đồ kiểm tra tĩnh giữ ngang; chưa cân bằng không có nghĩa app đang mô phỏng động lực học thanh nghiêng. |
| Ròng rọc | nT=mg; h=s/n; W=Ts=mgh cho n=1..4. | Nâng chậm, không ma sát/quán tính; hình biểu diễn lực tương đương, không phải hướng dẫn luồn một hệ dây thực tế. |

## Những chỗ đã sửa trong lượt này

- Mũi tên vận tốc trên dốc từng nằm ngang: sửa theo tiếp tuyến dốc, cả hai chiều.
- Con lắc có cản từng chỉ vẽ trọng lực/lực căng: thêm lực cản đúng đơn vị quay.
- Đòn bẩy thiếu mũi tên phản lực tựa: bổ sung hướng lên tại điểm tựa.
- Bài con lắc từng so với số 2 viết trực tiếp: đọc `pendulum_target_s` trong cấu hình.
- Nhãn phân biệt tốc độ ném xiên, vận tốc tiếp tuyến con lắc, vị trí dọc dốc và chu kỳ tham chiếu không cản. Đồ thị dùng cùng quy ước.
- Công thức ma sát trên dốc ghi rõ thành phần có dấu. Làm rõ giới hạn sơ đồ đòn bẩy/ròng rọc và thử thách chu kỳ đo.

## Cách kiểm tra

Các kiểm tra cũ về dừng/đảo chiều ma sát, bảo toàn năng lượng/động lượng,
trạng thái mất tay, dừng thời gian và xuất dữ liệu vẫn được giữ. Bổ sung
`tests/submission/test_physics_audit.py` để đối chiếu các nghiệm độc lập:

- Lò xo: nghiệm giải tích ứng với c=0, 2, 4, 8 khi m=1, k=4.
- Con lắc không cản: chu kỳ góc 5°, 45°, 80° so với tích phân elliptic tính bằng AGM; bộ chạy vẫn dùng RK4 và đo qua vị trí cân bằng.
- Ném xiên từ độ cao khác 0: điểm rơi/thời gian/vận tốc tại các góc 0°, 30°, 90°.
- Kiểm tra tổng lực con lắc bằng Newton trong hệ tọa độ Cartesian, tổn hao va chạm bằng công thức khối lượng giảm và cả bốn tỉ số ròng rọc.
- Kiểm tra hướng vector qua bộ vẽ, mục tiêu chu kỳ tùy cấu hình và mở thiết lập cũ đã biết; từ chối hash không rõ nguồn.

RK4 là phép tính gần đúng. Các test kiểm tra sai số với nghiệm tham chiếu trong
những ca đã chạy; chúng không chứng minh mọi cấu hình đều không có sai số số học.
Vector có giới hạn độ dài để dễ nhìn; số đo SI không bị giới hạn theo mũi tên.
Đạt thử thách chỉ là đạt điều kiện mô phỏng, không thay phần giải thích kiến thức.

Kết quả đã chạy: **923 test qua trên Python 3.11.9 và 3.12.14**, trong đó có 23
ca bổ sung cho lượt rà soát này. Đồ họa native chạy 652 frame trên bốn kích thước
cửa sổ, tám bài và F11, không báo lỗi OpenGL. Kiểm tra lưu/mở, JSON/CSV/ảnh và
chạy app bằng replay 30 frame đều hoàn tất; worker dừng sạch. Đây là kiểm tra
phần mềm và mô hình lý tưởng, không phải kiểm định thiết bị đo thực tế.

## Nguồn đối chiếu

- [OpenStax — Ma sát](https://openstax.org/books/university-physics-volume-1/pages/6-2-friction).
- [OpenStax — Ném xiên](https://openstax.org/books/physics/pages/5-3-projectile-motion).
- [OpenStax — Va chạm không đàn hồi](https://openstax.org/books/college-physics-2e/pages/8-5-inelastic-collisions-in-one-dimension).
- [OpenStax — Dao động tắt dần](https://openstax.org/books/university-physics-volume-1/pages/15-5-damped-oscillations).
- [OpenStax — Con lắc đơn](https://openstax.org/books/college-physics-2e/pages/16-4-the-simple-pendulum).
- [OpenStax — Máy cơ đơn giản](https://openstax.org/books/college-physics-2e/pages/9-5-simple-machines).
- [NIST DLMF 19.8.5 — Liên hệ tích phân elliptic K với AGM](https://dlmf.nist.gov/19.8.E5), dùng làm tham chiếu toán học độc lập cho chu kỳ con lắc.

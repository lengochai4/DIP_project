"""Contextual learning instructions; presentation only, no provider/Core inputs."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LabGuide:
    purpose: str
    live: str
    steps: tuple[str, ...]
    result: str
    limitation: str


GUIDES = {
    "coordinate": LabGuide(
        "Khám phá không gian hình học 3D bằng cử chỉ tay không chạm (DIP Touchless STEM).",
        "Nhận diện bàn tay chính (<1.5m). Chọn hình, tạo hình, chọn vật thể điều khiển, di chuyển và xoay độc lập.",
        (
            "Bước 1 (Chọn hình): Chỉ ngón trỏ vào nút 'Chọn hình' (giữ 1.3s) để mở bảng chọn hình 2D/3D (ưu tiên khóa 1 tay).",
            "Bước 2 (Tạo & Đóng băng): Mở ngón tay theo quy tắc tạo hình và giữ yên 1.8s để ghim vào không gian (ưu tiên khóa tay phải sau khi tạo).",
            "Bước 3 (Chọn vật thể): Dù 1 hay nhiều hình, chỉ ngón trỏ vào hình giữ 0.6s cho hình phát sáng để kích hoạt điều khiển.",
            "Bước 4 (Di chuyển): Chụm ngón cái + trỏ vào hình đã chọn để kéo di chuyển trong không gian 3D.",
            "Bước 5 (Xoay hình): Dùng 1 ngón trỏ quét để xoay hình; cất ngón tay hình lập tức về trạng thái tĩnh tuyệt đối.",
            "Bước 6 (Tác vụ nâng cao): Vào nút 'Tác vụ' để Bung mặt phẳng khối 3D hoặc Xóa hình đã chọn.",
        ),
        "Hình 3D xuất hiện, xoay, di chuyển và bung lưới mặt phẳng mượt mà theo cử chỉ tay.",
        "Hệ thống ưu tiên tay gần camera nhất (<1.5m) để loại bỏ nhiễu người phía sau. Giữ khoảng cách ổn định.",
    ),
    "molecule": LabGuide(
        "Quan sát hình dạng phân tử và góc liên kết.",
        "Các ngón tạo lớp hình học độc lập để so sánh với phân tử; không thay thế nguyên tử hoặc tạo liên kết hóa học.",
        (
            "Mở Tools và chọn CH4, H2O, CO2 hoặc NH3.",
            "Dùng WORLD và kéo chuột để quan sát từ nhiều phía; cuộn để đổi kích thước.",
            "Đọc Bond / Angle trong Tools và so sánh phân tử phẳng với phân tử không gian.",
        ),
        "CH4 có dạng tứ diện; NH3 dạng chóp; H2O và CO2 có các tâm nguyên tử đồng phẳng.",
        "Mô hình học tập lý tưởng hóa; độ dài hiển thị không phải độ dài liên kết thực.",
    ),
    "orbital": LabGuide(
        "Quan sát chuyển động tuần hoàn của một vật quanh tâm.",
        "Hình từ các ngón là lớp so sánh; chuyển động quỹ đạo chạy theo thời gian của lab.",
        (
            "Mở Tools; thay Radius để đổi bán kính quỹ đạo.",
            "Thay Time rate để đổi tốc độ chạy; Pause / Resume để dừng hoặc tiếp tục.",
            "Xoay góc nhìn bằng chuột trong WORLD; đọc chu kỳ và pha trong Tools.",
        ),
        "Thấy vật chuyển động trên quỹ đạo và các giá trị thay đổi theo thời gian.",
        "Đây là minh họa động học, không phải mô phỏng hấp dẫn.",
    ),
    "vector": LabGuide(
        "So sánh vector, tổng, tích vô hướng và tích có hướng.",
        "Duỗi ít nhất 2 ngón cho u = A → B; ít nhất 4 ngón cho thêm v = C → D.",
        (
            "Bắt đầu với 2 đầu ngón để thấy u; sau đó duỗi thêm đến 4 đầu ngón.",
            "Di chuyển các ngón để thay đổi hướng và độ dài của u, v.",
            "Mở Tools để đọc u + v, Dot, Cross và Projection; đối chiếu các mũi tên.",
        ),
        "Tổng và tích có hướng xuất hiện khi đủ cả hai vector.",
        "A–D là nhãn đỉnh, không phải tên ngón cố định. Gập ngón có thể thay đổi tập nhãn; thiếu đỉnh thì phép tính chưa có.",
    ),
    "surface": LabGuide(
        "Khám phá mặt z = f(x, y), lát cắt và gradient.",
        "Một đầu ngón đang duỗi làm điểm dò A; các ngón còn lại vẫn tạo hình học để so sánh.",
        (
            "Mở Tools; chọn Plane, Paraboloid, Saddle, Wave surface hoặc Gaussian.",
            "Di chuyển đầu ngón A để thay vị trí dò; hoặc rê chuột khi camera không dùng.",
            "Đọc f(x,y) / Gradient trong Tools; quan sát điểm Probe, lát cắt và mũi tên.",
        ),
        "Giá trị hàm và gradient thay đổi theo tọa độ điểm dò.",
        "Điểm dò trên mặt được tính từ x,y. Độ cao của mặt là giá trị hàm, không phải độ sâu camera.",
    ),
    "wave": LabGuide(
        "Khám phá dạng sóng, lấy mẫu và đáp ứng lọc minh họa.",
        "Đầu ngón A chọn tọa độ x để đọc tín hiệu; hình học các ngón không quyết định biên độ hoặc tần số.",
        (
            "Mở Tools; chọn dạng sóng, Sampling hoặc Filter response.",
            "Thay Amplitude, Frequency, Phase và Samples; quan sát đường sóng và các điểm lấy mẫu.",
            "Di chuyển A sang trái/phải để đọc tín hiệu. Standing wave có thể Pause / Resume.",
        ),
        "Biên độ đổi chiều cao sóng; tần số đổi số chu kỳ; số mẫu đổi mật độ điểm.",
        "Đồ thị sóng nằm trên mặt phẳng. Filter response là ví dụ lọc thông thấp riêng, không phải kết quả lọc DIP Core.",
    ),
    "vector-field": LabGuide(
        "Khám phá hướng, độ lớn của trường vector và đường dòng minh họa.",
        "Đầu ngón A chọn điểm dò trường và điểm bắt đầu đường dòng.",
        (
            "Mở Tools; chọn Radial, Rotational, Electric, Magnetic hoặc Fluid-like.",
            "Di chuyển A đến các vùng khác nhau; quan sát đường dòng màu vàng.",
            "Đọc Field / Magnitude trong Tools và so sánh với hướng các mũi tên.",
        ),
        "Trường tại điểm dò và đường dòng đổi theo vị trí.",
        "Trường lý tưởng hóa, có làm mềm điểm kỳ dị; không phải mô phỏng vật lý của một vật liệu cụ thể.",
    ),
    "optics": LabGuide(
        "Khám phá phản xạ, khúc xạ và sơ đồ tia qua thấu kính.",
        "Đầu ngón A điều khiển nguồn tia; các ngón khác tạo lớp hình học độc lập.",
        (
            "Mở Tools; chọn Reflection, Refraction, Lens hoặc Mirror.",
            "Di chuyển A ở phía trái phần tử quang học để thay đổi nguồn và góc tia.",
            "Refraction: thay Index. Lens: thay Focal. Quan sát tia vàng tới và tia xanh ra.",
        ),
        "Hướng tia cập nhật theo nguồn và tham số của preset.",
        "Sơ đồ tia là 2D trong cảnh 3D. Nguồn bị giới hạn ở phía trái; mô hình thấu kính dùng xấp xỉ cận trục.",
    ),
    "crystal": LabGuide(
        "So sánh cấu trúc mạng tinh thể lập phương.",
        "Các ngón tạo hình học so sánh; không thêm hoặc di chuyển các nút mạng.",
        (
            "Mở Tools; chọn Simple cubic, Body-centered cubic hoặc Face-centered cubic.",
            "Trong WORLD, kéo chuột để thấy các lớp trước/sau; cuộn để đổi kích thước.",
            "So sánh nút ở góc, tâm khối và tâm mặt; mặt tham chiếu z=0 có viền tím.",
        ),
        "Thấy khác biệt vị trí các nút giữa ba kiểu mạng.",
        "Cấu trúc minh họa lặp 2 × 2 × 2 ô; không có kích thước nguyên tử hay tính chất vật liệu thực.",
    ),
}

PARAMETER_HINTS = {
    "radius": "Bán kính quỹ đạo, theo đơn vị cảnh.",
    "time_rate": "Tốc độ thời gian minh họa; tăng giá trị để chuyển động nhanh hơn.",
    "amplitude": "Biên độ: chiều cao của tín hiệu.",
    "frequency": "Tần số góc theo radian / đơn vị trục x.",
    "phase": "Pha ban đầu theo radian; dịch sóng theo phương ngang.",
    "samples": "Số điểm lấy mẫu hiển thị trên đường sóng.",
    "index": "Chiết suất môi trường thứ hai trong preset Refraction.",
    "focal": "Tiêu cự minh họa theo đơn vị cảnh trong preset Lens.",
}


def guide_text(lab, *, live, engine, mode, ui_control):
    guide = GUIDES[lab.id]
    steps, result = guide.steps, guide.result
    if not live:
        if lab.id == "coordinate":
            steps = (
                "Mở Tools; chọn Distance, Triangle hoặc công cụ hình học muốn thử.",
                "Rê chuột để xem điểm dự kiến; nhấp trong khung để thêm từng điểm.",
                "Đọc số đo trong Tools; Undo để sửa điểm cuối, Finish polygon để kết thúc đa giác.",
            )
            result = "Hình đã tạo giữ nguyên sau khi bỏ tay hoặc con trỏ; Reset lab xóa công việc."
        elif lab.id == "vector":
            steps = (
                "Mở Tools; chọn Vector và nhấp hai điểm cho đoạn đầu, rồi thêm hai điểm cho đoạn thứ hai.",
                "Đọc u, v, Dot, Cross và Projection trong Tools.",
                "Undo để bỏ đoạn cuối; Reset lab để bắt đầu lại.",
            )
            result = "Khi chưa đủ dữ liệu có vector minh họa mặc định; hai đoạn đã tạo cung cấp u và v của bạn."
        else:
            steps = tuple(
                step.replace("đầu ngón A", "con trỏ").replace("Di chuyển A", "Rê chuột")
                for step in steps
            )
    if engine == "LEGACY":
        interaction = (
            "LEGACY / WORLD: dùng tương tác cũ hoặc chuột. Chọn PRODUCT / LIVE trong Settings "
            "để hình tự bám mọi đầu ngón; HAND không có trong LEGACY."
        )
    elif live:
        interaction = "LIVE: " + guide.live
    else:
        interaction = (
            "RECORDED: rê chuột để dò; kéo để xoay, cuộn để đổi kích thước. "
            "Tools có các công cụ tạo điểm thủ công. Chuyển Settings > Geometry mode > LIVE "
            "nếu muốn hình tự bám mọi đầu ngón."
        )
    if ui_control and engine == "PRODUCT":
        interaction += (
            "\nControl UI đang bật: hình từ tay tạm dừng. POINT + PINCH đã hiệu chuẩn "
            "để chọn menu; tắt Control UI để trở lại lab."
        )
    view = (
        "HAND: cảnh đặt theo lòng bàn tay đang được theo dõi. Điểm dò dựa trên vị trí "
        "trong cảnh, nên có thể khác vị trí tương đối trên vật thể; WORLD thuận tiện để học số đo."
        if mode == "HAND"
        else "WORLD: cảnh độc lập với lòng bàn tay; hình LIVE vẫn bám các đầu ngón trong camera."
    )
    return "\n\n".join(
        (
            f"{lab.title} · {lab.preset}",
            "MỤC ĐÍCH\n" + guide.purpose,
            "TƯƠNG TÁC HIỆN TẠI\n" + interaction,
            "THỬ THEO CÁC BƯỚC\n"
            + "\n".join(f"{i}. {step}" for i, step in enumerate(steps, 1)),
            "BẠN SẼ THẤY\n" + result,
            "GÓC NHÌN\n" + view,
            "LƯU Ý\n" + guide.limitation,
            "Ẩn/hiện bằng Hướng dẫn (G). Phóng to khung: Ctrl+Shift+F; Thu gọn hoặc Esc để trở lại. "
            "F11 bật/tắt toàn màn hình. LIVE không cần Add point hay hiệu chuẩn pinch. "
            "Chỉ mở Tools khi cần preset, tham số hoặc số đo. Độ sâu bàn tay là tương đối, không phải phép đo vật lý.",
        )
    )

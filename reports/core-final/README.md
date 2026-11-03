# Báo cáo chốt phần Core

`BAO_CAO_CORE.md` là bản thảo tiếng Việt. Báo cáo dùng bố cục học thuật của
PDF người dùng cung cấp, chỉ giữ bố cục và để trống thông tin cá nhân.
Các kết quả được lấy từ ROUND2 thực sự đã chạy; G7 được giữ riêng.
Giao diện mới chưa thuộc kết quả hoàn thành của báo cáo.

Các công cụ nguồn:

- `prepare_report.py`: ghép phần lý thuyết đã có và `final_sections.md`.
- `make_figures.py`: đọc CSV, đối chiếu nguồn/ROI và chạy CLAHE adaptive
  trên khung đã ghi để tạo hình phương pháp; chạy bằng `.venv-research`.
- `build_report.py`: dùng bố cục Word ở `reports/temporary/build_report.py`;
  chạy bằng Python primary runtime có python-docx/ReportLab.
- `verify_report.py`: đối chiếu số liệu, mã băm, công thức Word và số trang
  mục lục sau khi render bằng `render_docx.py` của skill documents.

Đầu ra chỉnh sửa được: `output/documents/Bao_cao_Core_DIP_Touchless_STEM.docx`.
PDF/ảnh render chỉ phục vụ kiểm tra nội bộ. Dữ liệu nguồn, hình sinh,
provenance và tài liệu xuất là artifact cục bộ, không đưa vào Git.

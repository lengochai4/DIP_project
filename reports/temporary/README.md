# Báo cáo tạm DIP Touchless STEM

Báo cáo tiếng Việt theo bố cục PDF mẫu được cung cấp, tập trung vào nền nghiên cứu G7. Thông tin trường, thành viên, mã sinh viên, lớp, khoa, giảng viên và mã đề tài để trống để điền sau. Danh tính, đề tài và kết quả của PDF mẫu không được dùng làm thông tin của dự án.

Nhánh làm việc: `docs/report-temp-from-main`, tạo từ `main` tại commit `f454c6b8325c85199c0122c0e822fe8e76c1526c`. Các nhánh UI cũ và tag G7 giữ nguyên. Không sửa mã Core, Extension, đặc tả chuẩn hoặc dữ liệu thực nghiệm.

## Tệp bàn giao

- Word chỉnh sửa được: `output/documents/Bao_cao_tam_DIP_Touchless_STEM.docx`.
- PDF xuất từ chính bản Word: `output/pdf/Bao_cao_tam_DIP_Touchless_STEM.pdf`.
- Nội dung nguồn: `reports/temporary/BAO_CAO_TAM.md`.
- Ba hình kiến trúc và biểu đồ: `reports/temporary/assets/`.
- Danh mục mã băm dữ liệu nguồn: `reports/temporary/provenance.json`.

Bản hiện tại có 30 trang, gồm hai bìa, mục lục, danh mục bảng biểu, từ viết tắt, thông tin kết quả nghiên cứu, mở đầu, ba chương, kết luận, tài liệu tham khảo và phụ lục. Mục lục là trường Word có thể cập nhật sau khi chỉnh sửa. Công thức và bảng là thành phần Word, không phải ảnh chụp. Ba hình được tạo từ kiến trúc và số liệu đã có.

## Đối chiếu số liệu

A1 giữ cả lượt không có dữ liệu và số mẫu nhỏ. A2 giữ trạng thái chưa tính được thay vì gán RMSE bằng không. Các tỷ lệ B đổi từ tỷ lệ gốc sang phần trăm; P0/P1 bằng nhau và CLAHE không kích hoạt trong cửa sổ đánh giá. Không khẳng định F2 vượt F1, hiệu quả học tập, độ sâu vật lý, tốc độ xử lý hoặc mức sẵn sàng thương mại khi chưa có bằng chứng.

## Tạo và kiểm tra

Chạy các script bằng Python trong Codex primary runtime, có `python-docx`, ReportLab, pypdf và lxml. Builder sử dụng Times New Roman của Windows và Poppler trong runtime. Không cài phụ thuộc vào môi trường chạy ứng dụng.

```powershell
& '<primary-runtime>/dependencies/python/python.exe' -X utf8 reports/temporary/build_report.py
# Render DOCX bằng render_docx.py của skill documents, có --emit_pdf.
& '<primary-runtime>/dependencies/python/python.exe' -X utf8 reports/temporary/build_report.py --pages '<PDF vừa render>'
# Render lại để đối chiếu mục lục và kiểm tra từng trang.
& '<primary-runtime>/dependencies/python/python.exe' -X utf8 reports/temporary/verify_report.py
```

LibreOffice dùng để chuyển đổi được giải nén riêng trong `runs/report-temp/renderer/extracted`, không cài vào hệ thống. Ảnh kiểm tra và hồ sơ kiểm tra nằm trong `runs/report-temp/`; đây là dữ liệu cục bộ được Git bỏ qua. PDF bàn giao được sao chép từ lần render cuối, không tạo bằng đường dựng PDF riêng.

Đã thực hiện đối chiếu CSV, mã băm 22 tệp nguồn, 52 mục lục, 10 công thức Word và 3 hình. Đã kiểm tra ảnh của toàn bộ 30 trang và sửa lỗi bố cục tìm thấy. Không chạy lại thí nghiệm webcam hoặc báo rằng đã kiểm thử một giao diện mới trong tác vụ báo cáo này.

"""Build editable Word using the already verified sample-derived academic layout."""
from pathlib import Path
import importlib.util
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('report_layout', ROOT / 'reports/temporary/build_report.py')
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)
layout.HERE = HERE
layout.ASSETS = HERE / 'assets'
layout.BODY_PATH = HERE / 'BAO_CAO_CORE.md'
layout.OUTPUT = ROOT / 'output/documents/Bao_cao_Core_DIP_Touchless_STEM.docx'
layout.TMP = ROOT / 'runs/report-core-final'
layout.TMP.mkdir(parents=True, exist_ok=True)
layout.COVER_STATUS = 'PHẦN CORE VÀ THỰC NGHIỆM'
layout.RESULT_SUMMARY = ('Đợt bổ sung có ba lượt cho mỗi nhóm. Hai bộ lọc giảm độ phân tán ở hai trong ba lượt kê cổ tay và tăng nhẹ ở lượt còn lại; F1/F2 gần nhau. F2 có RMSE so với Raw nhỏ hơn F1 ở cả ba lượt động. CLAHE bật trên nguồn tối giả lập, nhưng P0/P1 đều đạt tỷ lệ quan sát hợp lệ 100% trong các cửa sổ đã thử. Core giữ nguyên thuật toán G7; giao diện mới là bước tiếp theo.')
if len(sys.argv) > 1:
    layout.main()
else:
    layout.build_docx()
from docx import Document
doc = Document(layout.OUTPUT)
doc.core_properties.title = 'Báo cáo Core và thực nghiệm DIP Touchless STEM'
doc.core_properties.comments = 'Số liệu ROUND2 ngày 14/10/2026; giao diện mới chưa thuộc kết quả báo cáo.'
doc.save(layout.OUTPUT)
print(layout.OUTPUT)

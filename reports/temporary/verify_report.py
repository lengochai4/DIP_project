"""Check the report against frozen source records without rerunning experiments."""
from pathlib import Path
import hashlib
import json
import re
from zipfile import ZipFile
from lxml import etree
from pypdf import PdfReader
from build_report import ROOT, HERE, validate_evidence


def main():
    validate_evidence()
    docx = ROOT / "output/documents/Bao_cao_tam_DIP_Touchless_STEM.docx"
    pdf = ROOT / "output/pdf/Bao_cao_tam_DIP_Touchless_STEM.pdf"
    provenance = json.loads((HERE / "provenance.json").read_text(encoding="utf-8"))
    for path, expected in provenance["source_hashes"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main", "m": "http://schemas.openxmlformats.org/officeDocument/2006/math"}
    with ZipFile(docx) as z:
        tree = etree.fromstring(z.read("word/document.xml"))
        styles = etree.fromstring(z.read("word/styles.xml"))
        word_text = " ".join(" ".join(tree.xpath("//w:t/text()", namespaces=ns)).split())
        equations = len(tree.xpath("//m:oMath", namespaces=ns))
        assert equations == 10, equations
        assert len(tree.xpath("//w:drawing", namespaces=ns)) == 3
        assert any("TOC" in s for s in tree.xpath("//w:instrText/text()", namespaces=ns))
        assert not styles.xpath("//w:style[@w:styleId='Title']//w:pBdr", namespaces=ns)
        assert not tree.xpath("//w:documentProtection", namespaces=ns)
    reader = PdfReader(pdf)
    assert len(reader.pages) == 30
    pdf_text = "\n".join(p.extract_text() or "" for p in reader.pages)
    for unwanted in ("SV2026-468", "Trần Gia Kiệt", "Trần Quang Khải", "24110103", "24110FIE4", "97.20%", "89.58%", "MLP–BiLSTM", "ChatGPT", "TODO", "�"):
        assert unwanted not in word_text + pdf_text, unwanted
    assert all(str(round(float(r["value"]), 9)).replace(".", ",") in word_text
               for r in validate_evidence()[0] if r["available"] == "true")
    lines = [(p.extract_text() or "").splitlines() for p in reader.pages]
    def matches(rows, h):
        return any(" ".join(" ".join(rows[j:j+n]).split()) == h
                   for j in range(len(rows)) for n in (1, 2, 3))
    start = next(i for i, rows in enumerate(lines) if matches(rows, "DANH MỤC BẢNG BIỂU"))
    page_map = json.loads((ROOT / "runs/report-temp/page_map.json").read_text(encoding="utf-8"))
    for heading, page in page_map.items():
        actual = next(i for i in range(start, len(lines)) if matches(lines[i], heading)) - start + 1
        assert actual == page, (heading, page, actual)
        assert heading + " " + str(page) in word_text, (heading, page)
    result = {"pages": len(reader.pages), "toc_entries_verified": len(page_map),
              "native_equations": equations, "figures": 3,
              "source_files_sha256_verified": len(provenance["source_hashes"]),
              "metrics_match_frozen_csv": True, "sample_identity_excluded": True,
              "docx_sha256": hashlib.sha256(docx.read_bytes()).hexdigest(),
              "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest()}
    (ROOT / "runs/report-temp/verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

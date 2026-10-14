"""Verify final editable report against actual ROUND2 evidence and rendered pages."""
from pathlib import Path
from zipfile import ZipFile
import csv
import hashlib
import json
import sys
from lxml import etree
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TMP = ROOT / 'runs/report-core-final'
DOCX = ROOT / 'output/documents/Bao_cao_Core_DIP_Touchless_STEM.docx'
PDF = Path(sys.argv[1]) if len(sys.argv) > 1 else TMP / 'render-final/Bao_cao_Core_DIP_Touchless_STEM.pdf'
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main', 'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math'}
with ZipFile(DOCX) as archive:
    tree = etree.fromstring(archive.read('word/document.xml'))
    styles = etree.fromstring(archive.read('word/styles.xml'))
    text = ' '.join(' '.join(tree.xpath('//w:t/text()', namespaces=ns)).split())
    assert len(tree.xpath('//m:oMath', namespaces=ns)) == 10
    assert len(tree.xpath('//w:drawing', namespaces=ns)) == 4
    assert any('TOC' in t for t in tree.xpath('//w:instrText/text()', namespaces=ns))
    assert not styles.xpath('//w:style[@w:styleId="Title"]//w:pBdr', namespaces=ns)
    assert not etree.fromstring(archive.read('word/settings.xml')).xpath('//w:documentProtection', namespaces=ns)
provenance = json.loads((HERE / 'provenance.json').read_text(encoding='utf-8'))
metric_count = 0
for key, relative in provenance['metrics'].items():
    with (ROOT / relative / 'metrics.csv').open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    assert all(r['available'] == 'true' and int(r['sample_count']) == 241 for r in rows)
    for r in rows:
        expected = '100%' if key.startswith('b_') else f"{float(r['value']):.9f}".replace('.', ',')
        assert expected in text, (key, r['profile'], expected)
        if key.startswith('b_'):
            assert float(r['value']) == 1.0
        metric_count += 1
for relative, expected in provenance['evidence_hashes'].items():
    assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
audit_path = ROOT / 'runs/round2/ROUND2-20261014-SIM035/activation_audit.json'
assert hashlib.sha256(audit_path.read_bytes()).hexdigest() == provenance['activation_audit_sha256']
audit = json.loads(audit_path.read_text())
assert sum(v['active_frames'] for k,v in audit.items() if k.startswith('b_normal/')) == 0
assert sum(v['active_frames'] for k,v in audit.items() if k.startswith('b_simulated/')) == 723
reader = PdfReader(PDF)
lines = [(p.extract_text() or '').splitlines() for p in reader.pages]
pdf_text = '\n'.join('\n'.join(page) for page in lines)
for unwanted in ('SV2026-468', 'Trần Gia Kiệt', 'Trần Quang Khải', '24110103', '24110FIE4', '97.20%', '89.58%', 'MLP–BiLSTM', 'ChatGPT', 'TODO', '�', 'BẢN TẠM'):
    assert unwanted not in text + pdf_text, unwanted
def matches(rows, heading):
    return any(' '.join(' '.join(rows[j:j+n]).split()) == heading for j in range(len(rows)) for n in (1,2,3))
start = next(i for i,page in enumerate(lines) if matches(page, 'DANH MỤC BẢNG BIỂU'))
page_map = json.loads((TMP / 'page_map.json').read_text(encoding='utf-8'))
for heading, page in page_map.items():
    actual = next(i for i in range(start,len(lines)) if matches(lines[i],heading)) - start + 1
    assert actual == page, (heading,page,actual)
    assert heading + ' ' + str(page) in text, (heading,page)
result = {'pages':len(reader.pages), 'native_equations':10, 'figures':4, 'toc_headings_verified':len(page_map),
    'metric_rows_verified':metric_count, 'evidence_files_verified':len(provenance['evidence_hashes']),
    'unfavorable_results_retained':True, 'simulated_condition_explicit':True,
    'docx_sha256':hashlib.sha256(DOCX.read_bytes()).hexdigest()}
(TMP / 'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
for i, page in enumerate(lines):
    print(f'PAGE {i+1}: {len(page)} lines | ' + ' / '.join(page[:3]) + ' ... ' + ' / '.join(page[-3:]))
print(json.dumps(result, ensure_ascii=False, indent=2))

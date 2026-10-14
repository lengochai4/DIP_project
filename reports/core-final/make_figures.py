"""Make report figures from recorded metrics and a logged adaptive CLAHE frame."""
from pathlib import Path
import csv
import hashlib
import json
import shutil

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import yaml
from analysis.dip_visual import (_load_frame_row, _read_video_frame,
    _logged_illumination, _validate_descriptors)
from dip_touchless.core import ColorSpace, FramePacket, ROI, ROIState
from dip_touchless.preprocessing.adaptive_preprocessor import AdaptivePreprocessor
from dip_touchless.preprocessing.illumination import IlluminationAnalyzer

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ASSETS = HERE / 'assets'
ASSETS.mkdir(parents=True, exist_ok=True)
S = ROOT / 'runs/round2/ROUND2-20261014-SIM035'
H = ROOT / 'runs/round2/ROUND2-20261014-HELD-STATIC'
indices = {key: Path(value) for key, value in json.loads((S / 'analysis_index.json').read_text()).items()}
held = Path(json.loads((H / 'analysis_index.json').read_text())['a1_static'])

def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

plt.rcParams.update({'font.family': 'Times New Roman', 'font.size': 13})
for name, path, profiles, ylabel in (
    ('a1_jitter', held, ['F0','F1','F2'], 'Radial RMS (tọa độ chuẩn hóa)'),
    ('a2_rmse', indices['a2_dynamic'], ['F1','F2'], 'RMSE so với Raw (tọa độ chuẩn hóa)'),
):
    data = rows(path / 'metrics.csv')
    fig, ax = plt.subplots(figsize=(7.8,4.4), layout='constrained')
    x = np.arange(3); width = .24
    for j, profile in enumerate(profiles):
        values = [float(next(r['value'] for r in data if r['trial_id'] == f'trial-{i:03d}' and r['profile'] == profile)) for i in (1,2,3)]
        ax.bar(x + (j-(len(profiles)-1)/2)*width, values, width, label=profile,
               color=['#656565','#A8A8A8','#E3E3E3'][j], edgecolor='black', linewidth=.65)
    ax.set_xticks(x, ['Lượt 1','Lượt 2','Lượt 3']); ax.set_ylabel(ylabel)
    ax.set_ylim(bottom=0); ax.grid(axis='y', alpha=.2); ax.set_axisbelow(True)
    ax.legend(frameon=False, ncol=len(profiles)); ax.set_xlabel('241 khung hợp lệ chung / lượt')
    fig.savefig(ASSETS / f'{name}.png', dpi=230); plt.close(fig)

pipeline = ROOT / 'reports/temporary/assets/pipeline.png'
if not pipeline.is_file():
    # Architecture figure is generated from source if local temporary assets
    # are absent; no generated experiment image needs to be committed.
    import importlib.util
    spec = importlib.util.spec_from_file_location('report_layout', ROOT / 'reports/temporary/build_report.py')
    layout = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(layout)
    layout.make_assets(*layout.validate_evidence())
shutil.copyfile(pipeline, ASSETS / 'pipeline.png')
run = S / 'replay/20261014T023607403494Z-c8bc638e'
row = _load_frame_row(run / 'frames.csv', 161)
metadata = json.loads((run / 'metadata.json').read_text())
source = Path(metadata['source_data']['identity'])
assert hashlib.sha256(source.read_bytes()).hexdigest() == metadata['source_data']['sha256']
image = _read_video_frame(source, 161)
roi = ROI(x=int(row['roi_x']), y=int(row['roi_y']), width=int(row['roi_width']), height=int(row['roi_height']), state=ROIState[row['roi_state']])
packet = FramePacket(run_id=row['run_id'], frame_id=161, timestamp_s=float(row['timestamp_s']), image=image, color_space=ColorSpace.BGR, source_name=str(source))
illumination = _logged_illumination(row)
_validate_descriptors(analyzer=IlluminationAnalyzer(), packet=packet, roi=roi, logged=illumination)
assert row['illumination_state'] == 'DIFFICULT' and row['enhancement_active'].lower() == 'true'
original = image[roi.y:roi.y+roi.height, roi.x:roi.x+roi.width].copy()
config = yaml.safe_load((run / 'resolved_config.yaml').read_text())['clahe']
processed = AdaptivePreprocessor(policy='adaptive', clip_limit=float(config['clip_limit']), tile_grid_size=tuple(config['tile_grid_size'])).process_roi(original, illumination)
assert processed.illumination.enhancement_active
fig, axes = plt.subplots(2,2, figsize=(7.8,6.4), layout='constrained')
for col, (bgr, title) in enumerate(((original,'ROI đầu vào tối giả lập'), (processed.image_bgr,'ROI sau CLAHE thích ứng'))):
    axes[0,col].imshow(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)); axes[0,col].axis('off'); axes[0,col].set_title(title)
    v = cv2.cvtColor(bgr,cv2.COLOR_BGR2HSV)[:,:,2]
    axes[1,col].hist(v.ravel(), bins=64, range=(0,256), color='#656565')
    axes[1,col].set_xlim(0,255); axes[1,col].set_xlabel('Cường độ V'); axes[1,col].set_ylabel('Số điểm ảnh')
    axes[1,col].set_title('Phân bố kênh V ' + ('trước xử lý' if col == 0 else 'sau xử lý'))
fig.savefig(ASSETS / 'clahe_roi.png', dpi=230); plt.close(fig)
provenance = {'report_date': '2026-10-14', 'algorithm_base': 'f454c6b8325c85199c0122c0e822fe8e76c1526c',
    'metrics': {key: str(path.relative_to(ROOT)) for key,path in {'a1_held': held, **indices}.items()},
    'illustration': {'run_id': row['run_id'], 'frame_id':161, 'policy':'adaptive', 'logged_active':True, 'source_sha256': metadata['source_data']['sha256']},
    'evidence_hashes': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for path in [held, *indices.values()] for p in (path/'metrics.csv',path/'provenance.json')},
    'activation_audit_sha256': hashlib.sha256((S/'activation_audit.json').read_bytes()).hexdigest()}
(HERE / 'provenance.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding='utf-8')
print('Verified figures and provenance:', ASSETS)

"""Session and state management for the 3 Optics Experiments."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from .optics_engine import (
    RefractionResult,
    ThinLensResult,
    PrismDispersionResult,
    compute_refraction,
    compute_thin_lens,
    compute_prism_dispersion,
    OPTICS_MATERIALS,
)

CATALOG_PATH = Path(__file__).with_name('optics_labs.yaml')


class OpticsLabSession:
    """Session managing current experiment, parameters, evaluation, and presets."""

    PRESETS = {
        'refraction': {
            'air_to_water': {
                'name': 'Không khí → Nước (Khúc xạ)',
                'params': {'n1': 1.000, 'n2': 1.333, 'incident_angle': 45.0}
            },
            'glass_to_air_refr': {
                'name': 'Thủy tinh → Không khí (i < i_gh)',
                'params': {'n1': 1.517, 'n2': 1.000, 'incident_angle': 30.0}
            },
            'glass_to_air_tir': {
                'name': 'Thủy tinh → Không khí (Phản xạ toàn phần)',
                'params': {'n1': 1.517, 'n2': 1.000, 'incident_angle': 50.0}
            },
            'diamond_tir': {
                'name': 'Kim cương → Không khí (TIR lấp lánh)',
                'params': {'n1': 2.417, 'n2': 1.000, 'incident_angle': 35.0}
            },
        },
        'lens': {
            'real_smaller': {
                'name': 'Ảnh thật thu nhỏ (d > 2f)',
                'params': {'focal_length': 15.0, 'object_distance': 38.0, 'object_height': 4.0}
            },
            'real_equal': {
                'name': 'Ảnh thật bằng vật (d = 2f = 30cm)',
                'params': {'focal_length': 15.0, 'object_distance': 30.0, 'object_height': 4.0}
            },
            'real_magnified': {
                'name': 'Ảnh thật phóng đại (f < d < 2f)',
                'params': {'focal_length': 15.0, 'object_distance': 22.0, 'object_height': 3.0}
            },
            'virtual_magnifier': {
                'name': 'Kính lúp: Ảnh ảo phóng đại (d < f)',
                'params': {'focal_length': 15.0, 'object_distance': 8.0, 'object_height': 3.0}
            },
            'diverging_lens': {
                'name': 'Thấu kính phân kì (f = -15cm)',
                'params': {'focal_length': -15.0, 'object_distance': 24.0, 'object_height': 4.0}
            },
        },
        'prism': {
            'flint_dispersion': {
                'name': 'Thủy tinh Flint (Tán sắc mạnh)',
                'params': {'apex_angle': 60.0, 'incident_angle': 48.0, 'material': 'flint_glass'}
            },
            'crown_dispersion': {
                'name': 'Thủy tinh Crown chuẩn (A=60°)',
                'params': {'apex_angle': 60.0, 'incident_angle': 45.0, 'material': 'crown_glass'}
            },
            'acute_prism': {
                'name': 'Lăng kính góc nhỏ (A=45°)',
                'params': {'apex_angle': 45.0, 'incident_angle': 35.0, 'material': 'flint_glass'}
            },
            'diamond_prism': {
                'name': 'Lăng kính Kim cương (Tán sắc rực rỡ)',
                'params': {'apex_angle': 40.0, 'incident_angle': 52.0, 'material': 'diamond'}
            },
        }
    }

    def __init__(self, initial_lab: str = 'refraction'):
        self.catalog = self._load_catalog()
        self.current_lab = initial_lab if initial_lab in self.catalog['labs'] else 'refraction'
        self.params: Dict[str, Dict[str, Any]] = {}
        self._init_default_params()

    def _load_catalog(self) -> dict:
        try:
            return yaml.safe_load(CATALOG_PATH.read_text(encoding='utf-8'))
        except Exception:
            return {'labs': {}}

    def _init_default_params(self):
        for lab_id, lab in self.catalog.get('labs', {}).items():
            self.params[lab_id] = {}
            for p_name, p_data in lab.get('params', {}).items():
                self.params[lab_id][p_name] = p_data.get('default')

    def select_lab(self, lab_id: str):
        if lab_id in self.catalog.get('labs', {}):
            self.current_lab = lab_id

    def set_param(self, name: str, value: Any, lab_id: Optional[str] = None):
        target_lab = lab_id or self.current_lab
        if target_lab in self.params:
            self.params[target_lab][name] = value

    def get_param(self, name: str, lab_id: Optional[str] = None) -> Any:
        target_lab = lab_id or self.current_lab
        return self.params.get(target_lab, {}).get(name)

    def apply_preset(self, preset_key: str):
        presets = self.PRESETS.get(self.current_lab, {})
        if preset_key in presets:
            for k, v in presets[preset_key]['params'].items():
                self.params[self.current_lab][k] = v

    def evaluate(self, center: tuple = (0.0, 0.0), scale_factor: float = 1.0):
        """Run the analytical physics calculation for the current active lab."""
        p = self.params[self.current_lab]
        if self.current_lab == 'refraction':
            return compute_refraction(
                n1=float(p['n1']),
                n2=float(p['n2']),
                i_deg=float(p['incident_angle']),
                origin=center,
                ray_len=240.0 * scale_factor
            )
        elif self.current_lab == 'lens':
            return compute_thin_lens(
                f=float(p['focal_length']),
                d=float(p['object_distance']),
                h=float(p['object_height']),
                center=center,
                scale_px=7.0 * scale_factor
            )
        elif self.current_lab == 'prism':
            return compute_prism_dispersion(
                apex_deg=float(p['apex_angle']),
                i1_deg=float(p['incident_angle']),
                material=str(p.get('material', 'flint_glass')),
                center=center,
                size=180.0 * scale_factor
            )
        raise ValueError(f"Unknown lab: {self.current_lab}")

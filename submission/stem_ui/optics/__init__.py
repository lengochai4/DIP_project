"""Optics Simulation Module for DIP STEM UI.

Provides interactive optical experiments:
1. Refraction & Total Internal Reflection (Định luật Khúc xạ & Phản xạ toàn phần)
2. Thin Lens Imaging (Thấu kính mỏng hội tụ & phân kì)
3. Prism Light Dispersion (Tán sắc ánh sáng qua lăng kính)
"""

from .optics_engine import (
    RefractionResult,
    ThinLensResult,
    PrismDispersionResult,
    compute_refraction,
    compute_thin_lens,
    compute_prism_dispersion,
    OPTICS_MATERIALS,
    SPECTRAL_COLORS,
)
from .optics_experiments import OpticsLabSession

__all__ = [
    'RefractionResult',
    'ThinLensResult',
    'PrismDispersionResult',
    'compute_refraction',
    'compute_thin_lens',
    'compute_prism_dispersion',
    'OPTICS_MATERIALS',
    'SPECTRAL_COLORS',
    'OpticsLabSession',
]


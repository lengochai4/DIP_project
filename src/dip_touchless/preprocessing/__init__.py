"""Digital image preprocessing components."""

from .illumination import (
    IlluminationAnalyzer,
    IlluminationDescriptors,
)
from .illumination_decision import (
    IlluminationDecisionStabilizer,
)
from .adaptive_preprocessor import (
    AdaptivePreprocessor,
    ROIPreprocessResult,
)
from .roi import ROIManager

__all__ = [
    "AdaptivePreprocessor",
    "IlluminationAnalyzer",
    "IlluminationDecisionStabilizer",
    "IlluminationDescriptors",
    "ROIPreprocessResult",
    "ROIManager",
]
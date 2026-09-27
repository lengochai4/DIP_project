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
    FramePreprocessResult,
    ROIPreprocessResult,
)
from .roi import ROIManager

__all__ = [
    "AdaptivePreprocessor",
    "FramePreprocessResult",
    "IlluminationAnalyzer",
    "IlluminationDecisionStabilizer",
    "IlluminationDescriptors",
    "ROIPreprocessResult",
    "ROIManager",
]
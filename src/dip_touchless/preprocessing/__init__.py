"""Digital image preprocessing components."""

from .illumination import (
    IlluminationAnalyzer,
    IlluminationDescriptors,
)
from .roi import ROIManager

__all__ = [
    "IlluminationAnalyzer",
    "IlluminationDescriptors",
    "ROIManager",
]
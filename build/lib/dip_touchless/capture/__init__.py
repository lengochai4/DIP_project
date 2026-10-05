"""Frame acquisition implementations."""

from .camera import OpenCVCameraSource
from .replay import ReplayFrameSource

__all__ = [
    "OpenCVCameraSource",
    "ReplayFrameSource",
]
"""Additive full-hand geometry; deliberately not wired into the application."""

from .contracts import (
    Finger, FingerGeometry, FrameGeometry, GeometryReason, HandGeometry,
    PalmGeometry, ThumbGeometry,
)
from .geometry import extract_hand_geometry

__all__ = [
    "Finger", "FingerGeometry", "FrameGeometry", "GeometryReason",
    "HandGeometry", "PalmGeometry", "ThumbGeometry", "extract_hand_geometry",
]

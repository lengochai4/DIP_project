"""Renderer-independent gesture mapping."""

from .gesture_engine import (
    DeterministicGestureEngine,
)
from .gesture_math import (
    apply_deadzone,
    bounded_rotation_delta,
    bounded_scale_delta,
    distance_xy,
    normalized_pinch_ratio,
)

__all__ = [
    "DeterministicGestureEngine",
    "apply_deadzone",
    "bounded_rotation_delta",
    "bounded_scale_delta",
    "distance_xy",
    "normalized_pinch_ratio",
]
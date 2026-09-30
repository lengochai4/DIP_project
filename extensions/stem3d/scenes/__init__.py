"""Extension-owned STEM scene contracts and implementations."""

from .base import STEMScene
from .coordinate_cube import CoordinateCubeScene
from .registry import SceneRegistry

__all__ = [
    "CoordinateCubeScene",
    "SceneRegistry",
    "STEMScene",
]

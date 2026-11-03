"""Extension-owned STEM scene contracts and implementations."""

from .base import STEMScene
from .coordinate_cube import CoordinateCubeScene
from .coordinate_geometry import CoordinateGeometryScene
from .factory import build_tier1_scene_registry
from .metadata import SceneMetadata
from .molecule import (
    AtomDefinition,
    BondDefinition,
    MOLECULE_PRESETS,
    MoleculePreset,
    MolecularGeometryScene,
)
from .orbital import OrbitalSystemScene
from .registry import SceneRegistry
from .visuals import SceneFrame, SceneLine, SceneSphere

__all__ = [
    "AtomDefinition",
    "BondDefinition",
    "CoordinateCubeScene",
    "CoordinateGeometryScene",
    "MOLECULE_PRESETS",
    "MoleculePreset",
    "MolecularGeometryScene",
    "OrbitalSystemScene",
    "SceneRegistry",
    "SceneFrame",
    "SceneLine",
    "SceneMetadata",
    "SceneSphere",
    "STEMScene",
    "build_tier1_scene_registry",
]

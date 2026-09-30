"""Create the deterministic built-in Tier-1 STEM scene package."""

from __future__ import annotations

from ..scene_state import Stem3DSceneState
from .coordinate_geometry import CoordinateGeometryScene
from .molecule import MolecularGeometryScene
from .orbital import OrbitalSystemScene
from .registry import SceneRegistry


def build_tier1_scene_registry(
    *,
    initial_scale: float,
    min_scale: float,
    max_scale: float,
) -> SceneRegistry:
    """Register coordinate geometry, molecular geometry, and orbit scenes."""

    def new_scene_state() -> Stem3DSceneState:
        return Stem3DSceneState(
            initial_scale=initial_scale,
            min_scale=min_scale,
            max_scale=max_scale,
        )

    scenes = (
        CoordinateGeometryScene(new_scene_state()),
        MolecularGeometryScene(new_scene_state()),
        OrbitalSystemScene(new_scene_state()),
    )
    return SceneRegistry(
        scenes,
        initial_scene_id=CoordinateGeometryScene.metadata.scene_id,
    )

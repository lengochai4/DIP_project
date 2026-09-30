"""Visible synthetic smoke demo for the STEM 3D extension."""

from __future__ import annotations

from pathlib import Path

from dip_touchless.configuration import resolve_config
from dip_touchless.core import InteractionState

from .application import Stem3DExtension
from .renderer import OpenGLStemRenderer
from .scenes import (
    CoordinateCubeScene,
    SceneRegistry,
)
from .scene_state import Stem3DSceneState


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CONFIG = (
    PROJECT_ROOT
    / "config"
    / "default.yaml"
)


def _synthetic_interaction(
    frame_id: int,
) -> InteractionState:
    """Generate a deterministic renderer smoke command."""

    cycle = frame_id % 240

    scale_delta = (
        0.002
        if cycle < 120
        else -0.002
    )

    return InteractionState(
        run_id="stem3d-smoke",
        frame_id=frame_id,
        timestamp_s=(
            frame_id / 60.0
        ),
        interaction_valid=True,
        pointer_xy=(0.5, 0.5),
        pinch_ratio=0.25,
        pinch_active=True,
        rotation_delta=(
            0.01,
            0.004,
        ),
        scale_delta=scale_delta,
    )


def main() -> None:
    resolved = resolve_config(
        DEFAULT_CONFIG
    )

    renderer_config = resolved.data[
        "renderer"
    ]

    scene_state = Stem3DSceneState(
        initial_scale=(
            renderer_config[
                "initial_scale"
            ]
        ),
        min_scale=(
            renderer_config[
                "min_scale"
            ]
        ),
        max_scale=(
            renderer_config[
                "max_scale"
            ]
        ),
    )

    renderer = OpenGLStemRenderer(
        width=int(
            renderer_config["width"]
        ),
        height=int(
            renderer_config["height"]
        ),
        target_fps=int(
            renderer_config[
                "target_fps"
            ]
        ),
        title=(
            "DIP Touchless STEM "
            "- G5 Renderer Smoke"
        ),
    )

    scene_registry = SceneRegistry(
        [CoordinateCubeScene(scene_state)],
        initial_scene_id=CoordinateCubeScene.id,
    )

    extension = Stem3DExtension(
        scene_registry=scene_registry,
        renderer=renderer,
    )

    print(
        "Opening STEM 3D smoke demo..."
    )
    print(
        "Expected: rotating cube + XYZ axes "
        "with cyclic scale."
    )
    print(
        "Press ESC or close the window to exit."
    )

    extension.open()

    frame_id = 0

    try:
        while not extension.close_requested():
            extension.consume(
                _synthetic_interaction(
                    frame_id
                )
            )

            frame_id += 1

    finally:
        extension.close()

    print(
        "STEM 3D renderer closed cleanly."
    )


if __name__ == "__main__":
    main()

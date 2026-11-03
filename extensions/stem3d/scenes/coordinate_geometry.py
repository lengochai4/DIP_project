"""Educational axes, grid, and orientation reference geometry."""

from __future__ import annotations

from dip_touchless.core import InteractionState

from ..scene_state import Stem3DSceneState
from .base import SceneViewport
from .metadata import SceneMetadata
from .visuals import SceneFrame, SceneLine, SceneSphere


_AXES = (
    ((1.0, 0.32, 0.28), (0.43, 0.17, 0.16), (1.0, 0.0, 0.0)),
    ((0.32, 0.88, 0.5), (0.16, 0.38, 0.25), (0.0, 1.0, 0.0)),
    ((0.32, 0.58, 1.0), (0.16, 0.28, 0.48), (0.0, 0.0, 1.0)),
)
_GRID_COLOR = (0.22, 0.27, 0.34)
_CUBE_COLOR = (0.72, 0.78, 0.86)
_ORIGIN_COLOR = (1.0, 0.82, 0.34)


class CoordinateGeometryScene:
    """Teach 3D axes, reference grids, and spatial orientation."""

    metadata = SceneMetadata(
        scene_id="coordinate-geometry",
        title="Coordinate Geometry",
        category="Mathematics / Geometry",
        description=(
            "A 3D coordinate frame with colored positive axes, a reference "
            "grid, an origin marker, and an orientation cube."
        ),
        educational_topic=(
            "Coordinate systems, axis directions, spatial orientation, "
            "and view transforms."
        ),
        interaction_hint=(
            "Move the index fingertip to rotate the view; pinch to scale."
        ),
    )

    def __init__(self, scene_state: Stem3DSceneState) -> None:
        self._scene_state = scene_state
        self._active = False

    @property
    def id(self) -> str:
        return self.metadata.scene_id

    @property
    def title(self) -> str:
        return self.metadata.title

    @property
    def category(self) -> str:
        return self.metadata.category

    @property
    def active(self) -> bool:
        return self._active

    @property
    def transform(self):
        return self._scene_state.transform

    @property
    def frame(self) -> SceneFrame:
        return SceneFrame(
            scene_id=self.id,
            title=self.title,
            subtitle="+X red · +Y green · +Z blue · origin gold",
            transform=self._scene_state.transform,
            lines=self._build_lines(),
            spheres=(
                SceneSphere(
                    center=(0.0, 0.0, 0.0),
                    radius=0.075,
                    color=_ORIGIN_COLOR,
                ),
                SceneSphere(
                    center=(1.62, 0.0, 0.0),
                    radius=0.045,
                    color=_AXES[0][0],
                ),
                SceneSphere(
                    center=(0.0, 1.62, 0.0),
                    radius=0.045,
                    color=_AXES[1][0],
                ),
                SceneSphere(
                    center=(0.0, 0.0, 1.62),
                    radius=0.045,
                    color=_AXES[2][0],
                ),
            ),
        )

    def activate(self) -> None:
        self._active = True

    def deactivate(self) -> None:
        self._active = False

    def reset(self) -> None:
        self._scene_state.reset()

    def update(self, dt_s: float) -> None:
        del dt_s
        self._require_active()

    def apply_interaction(self, state: InteractionState) -> None:
        self._require_active()
        self._scene_state.consume(state)

    def render(self, viewport: SceneViewport) -> None:
        self._require_active()
        viewport.render(self.frame)

    def _build_lines(self) -> tuple[SceneLine, ...]:
        lines: list[SceneLine] = []
        grid_y = -0.72
        grid_coordinates = (-1.5, -1.0, -0.5, 0.5, 1.0, 1.5)
        for coordinate in grid_coordinates:
            lines.append(
                SceneLine(
                    start=(-1.65, grid_y, coordinate),
                    end=(1.65, grid_y, coordinate),
                    color=_GRID_COLOR,
                )
            )
            lines.append(
                SceneLine(
                    start=(coordinate, grid_y, -1.65),
                    end=(coordinate, grid_y, 1.65),
                    color=_GRID_COLOR,
                )
            )

        cube_vertices = (
            (-0.52, -0.52, -0.52),
            (0.52, -0.52, -0.52),
            (0.52, 0.52, -0.52),
            (-0.52, 0.52, -0.52),
            (-0.52, -0.52, 0.52),
            (0.52, -0.52, 0.52),
            (0.52, 0.52, 0.52),
            (-0.52, 0.52, 0.52),
        )
        cube_edges = (
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7),
        )
        lines.extend(
            SceneLine(
                start=cube_vertices[start],
                end=cube_vertices[end],
                color=_CUBE_COLOR,
                width=1.5,
            )
            for start, end in cube_edges
        )

        endpoints = (
            (1.62, 0.0, 0.0),
            (0.0, 1.62, 0.0),
            (0.0, 0.0, 1.62),
        )
        negative_endpoints = (
            (-1.62, 0.0, 0.0),
            (0.0, -1.62, 0.0),
            (0.0, 0.0, -1.62),
        )
        for index, (positive, negative) in enumerate(
            zip(endpoints, negative_endpoints, strict=True)
        ):
            positive_color, negative_color, _unit = _AXES[index]
            lines.append(
                SceneLine(
                    start=(0.0, 0.0, 0.0),
                    end=positive,
                    color=positive_color,
                    width=2.5,
                )
            )
            lines.append(
                SceneLine(
                    start=(0.0, 0.0, 0.0),
                    end=negative,
                    color=negative_color,
                )
            )

            base = tuple(component * 0.91 for component in positive)
            if index == 0:
                perpendiculars = ((0.0, 0.08, 0.0), (0.0, 0.0, 0.08))
            elif index == 1:
                perpendiculars = ((0.08, 0.0, 0.0), (0.0, 0.0, 0.08))
            else:
                perpendiculars = ((0.08, 0.0, 0.0), (0.0, 0.08, 0.0))
            for offset in perpendiculars:
                for sign in (-1.0, 1.0):
                    wing = tuple(
                        end + sign * delta
                        for end, delta in zip(positive, offset, strict=True)
                    )
                    lines.append(
                        SceneLine(
                            start=positive,
                            end=wing,
                            color=positive_color,
                            width=2.0,
                        )
                    )
                    lines.append(
                        SceneLine(
                            start=base,
                            end=wing,
                            color=positive_color,
                            width=2.0,
                        )
                    )
        return tuple(lines)

    def _require_active(self) -> None:
        if not self._active:
            raise RuntimeError(f"STEM scene {self.id!r} is not active")

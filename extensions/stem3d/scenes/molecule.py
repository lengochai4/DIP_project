"""Deterministic educational molecular geometry presets."""

from __future__ import annotations

from dataclasses import dataclass
import math
from types import MappingProxyType
from typing import Mapping

from dip_touchless.core import InteractionState

from ..scene_state import Stem3DSceneState
from .base import SceneViewport
from .metadata import SceneMetadata
from .visuals import RGB, SceneFrame, SceneLine, SceneSphere, Vector3


@dataclass(frozen=True, slots=True)
class AtomDefinition:
    element: str
    position: Vector3
    radius: float
    color: RGB


@dataclass(frozen=True, slots=True)
class BondDefinition:
    atom_a: int
    atom_b: int


@dataclass(frozen=True, slots=True)
class MoleculePreset:
    key: str
    name: str
    formula: str
    geometry_name: str
    approximate_bond_angle_deg: float
    atoms: tuple[AtomDefinition, ...]
    bonds: tuple[BondDefinition, ...]

    def __post_init__(self) -> None:
        for field_name in ("key", "name", "formula", "geometry_name"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"molecule preset {field_name} is required")
        if len(self.atoms) < 2 or not self.bonds:
            raise ValueError("molecule preset needs atoms and bonds")
        if not math.isfinite(self.approximate_bond_angle_deg):
            raise ValueError("molecule bond angle must be finite")
        for bond in self.bonds:
            if (
                bond.atom_a == bond.atom_b
                or not 0 <= bond.atom_a < len(self.atoms)
                or not 0 <= bond.atom_b < len(self.atoms)
            ):
                raise ValueError("molecule bond references invalid atoms")


_HYDROGEN = AtomDefinition(
    element="H",
    position=(0.0, 0.0, 0.0),
    radius=0.17,
    color=(0.88, 0.92, 0.97),
)
_OXYGEN_COLOR = (0.92, 0.23, 0.19)
_CARBON_COLOR = (0.36, 0.47, 0.60)
_BOND_COLOR = (0.60, 0.67, 0.76)


def _water_preset() -> MoleculePreset:
    angle_half_rad = math.radians(104.5 / 2.0)
    bond_length = 0.92
    x = bond_length * math.sin(angle_half_rad)
    y = bond_length * math.cos(angle_half_rad)
    return MoleculePreset(
        key="H2O",
        name="Water",
        formula="H2O",
        geometry_name="bent",
        approximate_bond_angle_deg=104.5,
        atoms=(
            AtomDefinition(
                element="O",
                position=(0.0, 0.0, 0.0),
                radius=0.31,
                color=_OXYGEN_COLOR,
            ),
            AtomDefinition(
                element="H",
                position=(-x, y, 0.0),
                radius=_HYDROGEN.radius,
                color=_HYDROGEN.color,
            ),
            AtomDefinition(
                element="H",
                position=(x, y, 0.0),
                radius=_HYDROGEN.radius,
                color=_HYDROGEN.color,
            ),
        ),
        bonds=(BondDefinition(0, 1), BondDefinition(0, 2)),
    )


def _methane_preset() -> MoleculePreset:
    bond_length = 0.98
    tetrahedral_signs = (
        (1.0, 1.0, 1.0),
        (1.0, -1.0, -1.0),
        (-1.0, 1.0, -1.0),
        (-1.0, -1.0, 1.0),
    )
    hydrogen_atoms = tuple(
        AtomDefinition(
            element="H",
            position=tuple(
                sign * bond_length / math.sqrt(3.0)
                for sign in signs
            ),
            radius=_HYDROGEN.radius,
            color=_HYDROGEN.color,
        )
        for signs in tetrahedral_signs
    )
    return MoleculePreset(
        key="CH4",
        name="Methane",
        formula="CH4",
        geometry_name="tetrahedral",
        approximate_bond_angle_deg=109.47,
        atoms=(
            AtomDefinition(
                element="C",
                position=(0.0, 0.0, 0.0),
                radius=0.32,
                color=_CARBON_COLOR,
            ),
            *hydrogen_atoms,
        ),
        bonds=tuple(BondDefinition(0, index) for index in range(1, 5)),
    )


MOLECULE_PRESETS: Mapping[str, MoleculePreset] = MappingProxyType(
    {
        "H2O": _water_preset(),
        "CH4": _methane_preset(),
    }
)


class MolecularGeometryScene:
    """Render hard-coded, approximate water and methane geometries."""

    id = "molecule"
    category = "Chemistry / Molecular Geometry"

    def __init__(self, scene_state: Stem3DSceneState) -> None:
        self._scene_state = scene_state
        self._active = False
        self._preset_key = "H2O"

    @property
    def metadata(self) -> SceneMetadata:
        preset = self.preset
        return SceneMetadata(
            scene_id=self.id,
            title=f"Molecular Geometry - {preset.name} ({preset.formula})",
            category=self.category,
            description=(
                f"{preset.name} represented by atom spheres and bonds; "
                f"approximate {preset.geometry_name} geometry with a "
                f"{preset.approximate_bond_angle_deg:.2f} degree angle."
            ),
            educational_topic=(
                "Atom types, molecular shape, and approximate bond geometry."
            ),
            interaction_hint=(
                "Move the index fingertip to rotate; pinch to scale. "
                "Press H for water or C for methane."
            ),
        )

    @property
    def title(self) -> str:
        return self.metadata.title

    @property
    def active(self) -> bool:
        return self._active

    @property
    def preset(self) -> MoleculePreset:
        return MOLECULE_PRESETS[self._preset_key]

    @property
    def preset_key(self) -> str:
        return self._preset_key

    @property
    def available_presets(self) -> tuple[str, ...]:
        return tuple(MOLECULE_PRESETS)

    @property
    def transform(self):
        return self._scene_state.transform

    @property
    def frame(self) -> SceneFrame:
        preset = self.preset
        lines = tuple(
            SceneLine(
                start=preset.atoms[bond.atom_a].position,
                end=preset.atoms[bond.atom_b].position,
                color=_BOND_COLOR,
                width=5.0,
            )
            for bond in preset.bonds
        )
        spheres = tuple(
            SceneSphere(
                center=atom.position,
                radius=atom.radius,
                color=atom.color,
            )
            for atom in preset.atoms
        )
        return SceneFrame(
            scene_id=self.id,
            title=self.title,
            subtitle=(
                f"{preset.formula} - approximate {preset.geometry_name} "
                f"geometry, {preset.approximate_bond_angle_deg:.2f} deg"
            ),
            transform=self._scene_state.transform,
            lines=lines,
            spheres=spheres,
        )

    def select_preset(self, key: str) -> None:
        normalized = key.strip().upper()
        if normalized not in MOLECULE_PRESETS:
            raise ValueError(f"unknown molecule preset: {key}")
        self._preset_key = normalized

    def activate(self) -> None:
        self._active = True

    def deactivate(self) -> None:
        self._active = False

    def reset(self) -> None:
        self._scene_state.reset()
        self._preset_key = "H2O"

    def update(self, dt_s: float) -> None:
        del dt_s
        self._require_active()

    def apply_interaction(self, state: InteractionState) -> None:
        self._require_active()
        self._scene_state.consume(state)

    def render(self, viewport: SceneViewport) -> None:
        self._require_active()
        viewport.render(self.frame)

    def _require_active(self) -> None:
        if not self._active:
            raise RuntimeError(f"STEM scene {self.id!r} is not active")

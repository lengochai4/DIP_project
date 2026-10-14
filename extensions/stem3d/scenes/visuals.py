"""Immutable renderer-independent geometry for STEM scenes."""

from __future__ import annotations

from dataclasses import dataclass
import math

from ..scene_state import SceneTransform


Vector3 = tuple[float, float, float]
RGB = tuple[float, float, float]


def _validate_vector(value: Vector3, *, name: str) -> None:
    if len(value) != 3 or not all(
        isinstance(component, (int, float))
        and not isinstance(component, bool)
        and math.isfinite(component)
        for component in value
    ):
        raise ValueError(f"{name} must contain three finite numbers")


def _validate_color(value: RGB) -> None:
    if len(value) != 3 or not all(
        isinstance(component, (int, float))
        and not isinstance(component, bool)
        and math.isfinite(component)
        and 0.0 <= component <= 1.0
        for component in value
    ):
        raise ValueError("scene color components must be finite values in [0, 1]")


@dataclass(frozen=True, slots=True)
class SceneLine:
    start: Vector3
    end: Vector3
    color: RGB
    width: float = 1.0

    def __post_init__(self) -> None:
        _validate_vector(self.start, name="line start")
        _validate_vector(self.end, name="line end")
        _validate_color(self.color)
        if (
            isinstance(self.width, bool)
            or not isinstance(self.width, (int, float))
            or not math.isfinite(self.width)
            or self.width <= 0.0
        ):
            raise ValueError("line width must be finite and positive")


@dataclass(frozen=True, slots=True)
class SceneSphere:
    center: Vector3
    radius: float
    color: RGB

    def __post_init__(self) -> None:
        _validate_vector(self.center, name="sphere center")
        _validate_color(self.color)
        if (
            isinstance(self.radius, bool)
            or not isinstance(self.radius, (int, float))
            or not math.isfinite(self.radius)
            or self.radius <= 0.0
        ):
            raise ValueError("sphere radius must be finite and positive")


@dataclass(frozen=True, slots=True)
class SceneFrame:
    scene_id: str
    title: str
    subtitle: str
    transform: SceneTransform
    lines: tuple[SceneLine, ...] = ()
    spheres: tuple[SceneSphere, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("scene_id", "title", "subtitle"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"scene frame {field_name} must be non-empty")
        if not isinstance(self.transform, SceneTransform):
            raise ValueError("scene frame requires a SceneTransform")
        values = (
            self.transform.yaw_rad,
            self.transform.pitch_rad,
            self.transform.scale,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("scene transform values must be finite")
        if self.transform.scale <= 0.0:
            raise ValueError("scene scale must be positive")
        if not isinstance(self.lines, tuple) or not all(
            isinstance(line, SceneLine) for line in self.lines
        ):
            raise ValueError("scene frame lines must be a tuple of SceneLine")
        if not isinstance(self.spheres, tuple) or not all(
            isinstance(sphere, SceneSphere) for sphere in self.spheres
        ):
            raise ValueError("scene frame spheres must be a tuple of SceneSphere")

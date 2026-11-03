"""Presentation-safe descriptive metadata for educational scenes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SceneMetadata:
    scene_id: str
    title: str
    category: str
    description: str
    educational_topic: str
    interaction_hint: str

    def __post_init__(self) -> None:
        for field_name in (
            "scene_id",
            "title",
            "category",
            "description",
            "educational_topic",
            "interaction_hint",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"scene metadata {field_name} must be non-empty"
                )

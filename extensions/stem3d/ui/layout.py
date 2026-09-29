"""Deterministic responsive layout calculations for the live dashboard."""

from __future__ import annotations

from dataclasses import dataclass

from .theme import THEME


@dataclass(frozen=True, slots=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height


@dataclass(frozen=True, slots=True)
class DashboardLayout:
    width: int
    height: int
    requested_width: int
    requested_height: int
    header: Rect
    vision: Rect
    vision_image: Rect
    scene: Rect
    pipeline: Rect
    interaction: Rect
    footer: Rect

    @property
    def minimum_size_applied(self) -> bool:
        return (
            self.width != self.requested_width
            or self.height != self.requested_height
        )


def calculate_dashboard_layout(
    width: int,
    height: int,
) -> DashboardLayout:
    """Return deterministic panel rectangles for a requested window size.

    Dimensions smaller than the supported minimum are raised to that
    minimum so every returned rectangle remains usable and non-negative.
    """

    _require_positive_integer(width, name="width")
    _require_positive_integer(height, name="height")

    requested_width = width
    requested_height = height
    width = max(width, THEME.minimum_window_width)
    height = max(height, THEME.minimum_window_height)

    margin = THEME.margin
    gap = THEME.gap
    header_height = THEME.header_height
    footer_height = THEME.footer_height

    content_width = width - 2 * margin
    header = Rect(
        x=margin,
        y=margin,
        width=content_width,
        height=header_height,
    )
    footer = Rect(
        x=margin,
        y=height - margin - footer_height,
        width=content_width,
        height=footer_height,
    )

    content_top = header.bottom + gap
    content_bottom = footer.y - gap
    content_height = content_bottom - content_top

    columns_width = content_width - gap
    vision_width = int(
        round(
            columns_width
            * THEME.vision_column_share
        )
    )
    side_width = columns_width - vision_width
    vision = Rect(
        x=margin,
        y=content_top,
        width=vision_width,
        height=content_height,
    )

    side_x = vision.right + gap
    scene_height = max(
        THEME.minimum_scene_height,
        int(round(content_height * 0.21)),
    )
    scene = Rect(
        x=side_x,
        y=content_top,
        width=side_width,
        height=scene_height,
    )

    lower_top = scene.bottom + gap
    lower_height = content_bottom - lower_top
    pipeline_height = int(
        round(
            lower_height
            * THEME.pipeline_card_share
        )
    )
    pipeline = Rect(
        x=side_x,
        y=lower_top,
        width=side_width,
        height=pipeline_height,
    )
    interaction = Rect(
        x=side_x,
        y=pipeline.bottom + gap,
        width=side_width,
        height=content_bottom - (pipeline.bottom + gap),
    )

    padding = THEME.card_padding
    title_height = THEME.card_title_height
    vision_image = Rect(
        x=vision.x + padding,
        y=vision.y + padding + title_height,
        width=vision.width - 2 * padding,
        height=(
            vision.height
            - 2 * padding
            - title_height
        ),
    )

    return DashboardLayout(
        width=width,
        height=height,
        requested_width=requested_width,
        requested_height=requested_height,
        header=header,
        vision=vision,
        vision_image=vision_image,
        scene=scene,
        pipeline=pipeline,
        interaction=interaction,
        footer=footer,
    )


def fit_aspect_rect(
    source_width: int,
    source_height: int,
    bounds: Rect,
) -> Rect:
    """Fit a source rectangle inside bounds without changing its aspect."""

    _require_positive_integer(
        source_width,
        name="source_width",
    )
    _require_positive_integer(
        source_height,
        name="source_height",
    )
    _require_positive_integer(
        bounds.width,
        name="bounds.width",
    )
    _require_positive_integer(
        bounds.height,
        name="bounds.height",
    )

    scale = min(
        bounds.width / source_width,
        bounds.height / source_height,
    )
    fitted_width = max(
        1,
        int(round(source_width * scale)),
    )
    fitted_height = max(
        1,
        int(round(source_height * scale)),
    )

    return Rect(
        x=bounds.x + (bounds.width - fitted_width) // 2,
        y=bounds.y + (bounds.height - fitted_height) // 2,
        width=fitted_width,
        height=fitted_height,
    )


def _require_positive_integer(
    value: int,
    *,
    name: str,
) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
    ):
        raise ValueError(f"{name} must be a positive integer")

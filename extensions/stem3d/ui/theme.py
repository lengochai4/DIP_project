"""Centralized visual tokens for the OpenCV dashboard.

Color tuples use OpenCV's BGR channel order.
"""

from __future__ import annotations

from dataclasses import dataclass


Color = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class ThemeTokens:
    background: Color = (19, 23, 30)
    surface: Color = (29, 35, 44)
    surface_raised: Color = (39, 47, 59)
    border: Color = (67, 78, 92)
    text_primary: Color = (239, 243, 245)
    text_secondary: Color = (189, 199, 208)
    text_muted: Color = (132, 147, 160)
    accent: Color = (195, 174, 92)
    landmark_raw: Color = (49, 194, 239)
    landmark_filtered: Color = (118, 229, 165)
    success: Color = (103, 190, 132)
    warning: Color = (67, 177, 231)
    error: Color = (79, 87, 226)

    margin: int = 20
    gap: int = 14
    card_padding: int = 14
    corner_radius: int = 10
    border_width: int = 1
    line_height: int = 18
    row_height: int = 20
    header_height: int = 72
    footer_height: int = 78
    card_title_height: int = 28
    minimum_scene_height: int = 92
    vision_column_share: float = 0.58
    pipeline_card_share: float = 0.59
    analysis_flow_y: int = 44
    analysis_rows_y: int = 76
    preview_background: Color = (13, 17, 22)
    tracking_valid: Color = (103, 190, 132)
    tracking_neutral: Color = (67, 177, 231)

    font_face: int = 0
    font_small: float = 0.42
    font_micro: float = 0.30
    font_body: float = 0.48
    font_section: float = 0.56
    font_title: float = 0.82
    font_weight: int = 1
    font_weight_emphasis: int = 2

    minimum_window_width: int = 1024
    minimum_window_height: int = 640
    default_window_width: int = 1280
    default_window_height: int = 720


THEME = ThemeTokens()

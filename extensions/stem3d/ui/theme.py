"""Centralized visual tokens for the application shell and dashboard.

Color tuples use OpenCV's BGR channel order.
"""

from __future__ import annotations

from dataclasses import dataclass


Color = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class ThemeTokens:
    background: Color = (30, 23, 19)
    surface: Color = (44, 35, 29)
    surface_raised: Color = (59, 47, 39)
    border: Color = (92, 78, 67)
    text_primary: Color = (245, 243, 239)
    text_secondary: Color = (208, 199, 189)
    text_muted: Color = (160, 147, 132)
    accent: Color = (222, 153, 75)
    surface_elevated: Color = (59, 47, 39)
    surface_overlay: Color = (52, 41, 34)
    divider: Color = (72, 58, 48)
    accent_hover: Color = (238, 173, 95)
    accent_selected: Color = (76, 57, 35)
    disabled: Color = (123, 108, 95)
    control_hover: Color = (82, 65, 53)
    control_pressed: Color = (83, 68, 44)
    spacing_xs: int = 4
    spacing_sm: int = 8
    spacing_md: int = 16
    spacing_lg: int = 24
    spacing_xl: int = 32
    radius_sm: int = 6
    radius_md: int = 10
    radius_lg: int = 14
    icon_sm: int = 16
    icon_md: int = 20
    icon_lg: int = 28
    font_caption: float = 0.46
    font_view: float = 0.68
    font_heading: float = 0.56
    hover_duration_s: float = 0.15
    press_duration_s: float = 0.16
    shell_header_height: int = 56
    shell_footer_height: int = 48
    shell_sidebar_width: int = 168
    shell_vision_width: int = 216
    shell_drawer_width: int = 320
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
    preview_background: Color = (22, 17, 13)
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

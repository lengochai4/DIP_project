"""Presentation-only user interface for the STEM 3D extension."""

from .dashboard import LiveDashboard
from .layout import (
    DashboardLayout,
    Rect,
    calculate_dashboard_layout,
    fit_aspect_rect,
    map_normalized_point_to_rect,
)
from .presentation_model import (
    ApplicationPhase,
    ApplicationState,
    DashboardMode,
    FilterPresentation,
    IlluminationPresentation,
    InteractionPresentation,
    LandmarkPresentation,
    PresentationState,
    RoiPresentation,
    RuntimeIdentityPresentation,
    build_runtime_identity,
    build_presentation_state,
)
from .theme import THEME, ThemeTokens
from .spatial_panel import (
    InteractionFocus,
    InteractionRouter,
    PanelButton,
    SpatialPanelLayout,
    SpatialPanelViewState,
    build_spatial_panel_layout,
)

__all__ = [
    "ApplicationPhase",
    "ApplicationState",
    "DashboardMode",
    "DashboardLayout",
    "FilterPresentation",
    "IlluminationPresentation",
    "InteractionPresentation",
    "InteractionFocus",
    "InteractionRouter",
    "LandmarkPresentation",
    "LiveDashboard",
    "PresentationState",
    "PanelButton",
    "Rect",
    "RoiPresentation",
    "RuntimeIdentityPresentation",
    "THEME",
    "ThemeTokens",
    "SpatialPanelLayout",
    "SpatialPanelViewState",
    "build_runtime_identity",
    "build_presentation_state",
    "calculate_dashboard_layout",
    "fit_aspect_rect",
    "map_normalized_point_to_rect",
    "build_spatial_panel_layout",
]

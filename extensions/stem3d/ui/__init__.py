"""Presentation-only user interface for the STEM 3D extension."""

from .dashboard import LiveDashboard
from .layout import (
    DashboardLayout,
    Rect,
    calculate_dashboard_layout,
    fit_aspect_rect,
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

__all__ = [
    "ApplicationPhase",
    "ApplicationState",
    "DashboardMode",
    "DashboardLayout",
    "FilterPresentation",
    "IlluminationPresentation",
    "InteractionPresentation",
    "LandmarkPresentation",
    "LiveDashboard",
    "PresentationState",
    "Rect",
    "RoiPresentation",
    "RuntimeIdentityPresentation",
    "THEME",
    "ThemeTokens",
    "build_runtime_identity",
    "build_presentation_state",
    "calculate_dashboard_layout",
    "fit_aspect_rect",
]

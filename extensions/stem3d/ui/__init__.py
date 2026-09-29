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
    FilterPresentation,
    IlluminationPresentation,
    InteractionPresentation,
    PresentationState,
    RoiPresentation,
    build_presentation_state,
)
from .theme import THEME, ThemeTokens

__all__ = [
    "ApplicationPhase",
    "ApplicationState",
    "DashboardLayout",
    "FilterPresentation",
    "IlluminationPresentation",
    "InteractionPresentation",
    "LiveDashboard",
    "PresentationState",
    "Rect",
    "RoiPresentation",
    "THEME",
    "ThemeTokens",
    "build_presentation_state",
    "calculate_dashboard_layout",
    "fit_aspect_rect",
]

"""Presentation Support Extension Package."""

from .slide_controller import SlideController
from .laser_pointer import VirtualLaserPointerOverlay
from .whiteboard_ink import VirtualWhiteboardInk
from .window_manager import WindowManagerExtension
from .module import PresentationSupportExtension

__all__ = [
    "SlideController",
    "VirtualLaserPointerOverlay",
    "VirtualWhiteboardInk",
    "WindowManagerExtension",
    "PresentationSupportExtension",
]

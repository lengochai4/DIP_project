"""One responsive application shell; all rectangles use viewport pixels."""

from dataclasses import dataclass
from functools import lru_cache

from .layout import Rect
from .presentation_model import DashboardMode
from .theme import THEME


@dataclass(frozen=True, slots=True)
class ShellLayout:
    width: int
    height: int
    header: Rect
    sidebar: Rect
    content: Rect
    stem: Rect | None
    vision: Rect | None
    pipeline: Rect | None
    diagnostics: Rect | None
    footer: Rect
    drawer: Rect


@lru_cache(maxsize=32, typed=True)
def calculate_shell_layout(
    width: int, height: int, mode: DashboardMode = DashboardMode.DEMO,
) -> ShellLayout:
    if isinstance(width, bool) or not isinstance(width, int) or width <= 0:
        raise ValueError("width must be a positive integer")
    if isinstance(height, bool) or not isinstance(height, int) or height <= 0:
        raise ValueError("height must be a positive integer")
    width = max(width, THEME.minimum_window_width)
    height = max(height, THEME.minimum_window_height)
    s = THEME.spacing_md
    header = Rect(0, 0, width, THEME.shell_header_height)
    footer = Rect(0, height - THEME.shell_footer_height, width,
                  THEME.shell_footer_height)
    # Retain the layout field for callers; scene navigation is now a compact
    # horizontal strip, leaving desktop width to the scientific viewport.
    sidebar = Rect(s, header.bottom + s, width - 2*s,
                   THEME.shell_scene_bar_height)
    content = Rect(s, sidebar.bottom+s, width-2*s,
                   footer.y-sidebar.bottom-2*s)
    drawer = Rect(width - THEME.shell_drawer_width - s, content.y,
                  THEME.shell_drawer_width, content.height)
    if mode is DashboardMode.EVIDENCE:
        content = Rect(s, header.bottom+s, width-2*s, footer.y-header.bottom-2*s)
        drawer = Rect(width-THEME.shell_drawer_width-s, content.y,
                      THEME.shell_drawer_width, content.height)
        return ShellLayout(width, height, header, sidebar, content, None,
                           None, None, None, footer, drawer)
    extra_height = THEME.shell_analysis_height if mode is DashboardMode.ANALYSIS else 0
    area = Rect(content.x, content.y, content.width,
                content.height - extra_height)
    vision_width = (
        int(area.width * 0.36) if mode is DashboardMode.ANALYSIS
        else max(THEME.shell_vision_width, round(area.width * .22))
    )
    stem = Rect(area.x, area.y, area.width - vision_width - s, area.height)
    vision = Rect(stem.right + s, area.y, vision_width,
                  area.height if mode is DashboardMode.ANALYSIS else
                  min(area.height, THEME.shell_vision_max_height))
    pipeline = diagnostics = None
    if mode is DashboardMode.ANALYSIS:
        pipeline = Rect(content.x, area.bottom + s, content.width, 76)
        diagnostics = Rect(content.x, pipeline.bottom + s, content.width,
                           content.bottom - pipeline.bottom - s)
    return ShellLayout(width, height, header, sidebar, content, stem,
                       vision, pipeline, diagnostics, footer, drawer)

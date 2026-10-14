"""Cached code-native glass surfaces; no processing telemetry in the UI."""
from functools import lru_cache
import pygame

BG = (8, 16, 25)
PANEL = (18, 32, 46)
INK = (234, 244, 250)
MUTED = (152, 176, 194)
ACCENT = (95, 221, 245)
GOLD = (244, 202, 126)
AUTHORS = 'Nhóm tác giả: 24110107 - Nguyễn Đăk Lộc | 24110103 - Trần Gia Kiệt | 24110089 - Lê Ngọc Hải'


@lru_cache(maxsize=40)
def glass(size, alpha=235, radius=16, bright=False):
    """Static gradient/facets cached by size, uploaded only when UI changes."""
    w, h = size
    surface = pygame.Surface(size, pygame.SRCALPHA)
    for y in range(h):
        t = y / max(1, h - 1)
        color = tuple(round(a * (1-t) + b*t) for a,b in zip(
            (42, 66, 85) if bright else (28, 45, 60), (12, 24, 37)))
        pygame.draw.line(surface, (*color, alpha), (0,y), (w,y))
    sheen = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.polygon(sheen, (183, 234, 255, 13), ((0,0),(w,0),(w*.64,h*.38),(0,h*.7)))
    surface.blit(sheen,(0,0))
    mask = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.rect(mask, (255,255,255,255), mask.get_rect(), border_radius=radius)
    surface.blit(mask, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
    pygame.draw.rect(surface, (130,197,220,100), surface.get_rect(), 1, border_radius=radius)
    pygame.draw.line(surface, (206,241,255,130), (radius,1), (w-radius,1))
    return surface


def card(surface, rect, alpha=235, bright=False):
    rect = pygame.Rect(rect)
    surface.blit(glass(rect.size, alpha, 16, bright), rect)


def header_height(width):
    return 96 if width < 1120 else 80


def scene_rect(size, camera):
    w,h = size
    sidebar = min(300, w//4) if camera else 0
    y = header_height(w) + 68
    return (20, y, w-40-sidebar-(16 if sidebar else 0), h-y-68)

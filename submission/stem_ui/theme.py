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
def glass(size, alpha=235, radius=16, bright=False, samples=2):
    """Static gradient/facets cached by size, uploaded only when UI changes."""
    w, h = size
    if samples>1:
        high=glass((w*samples,h*samples),alpha,radius*samples,bright,1)
        return pygame.transform.smoothscale(high,size)
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


def card(surface, rect, alpha=235, bright=False, samples=2):
    rect = pygame.Rect(rect)
    surface.blit(glass(rect.size, alpha, 16, bright, samples), rect)


@lru_cache(maxsize=40)
def outline(size,color,radius=10,width=1,samples=2):
    w,h=size
    high=pygame.Surface((w*samples,h*samples),pygame.SRCALPHA)
    pygame.draw.rect(high,color,high.get_rect(),width*samples,border_radius=radius*samples)
    return pygame.transform.smoothscale(high,size) if samples>1 else high


@lru_cache(maxsize=4)
def atom_mark(samples=2):
    high=pygame.Surface((42*samples,42*samples),pygame.SRCALPHA)
    pygame.draw.ellipse(high,ACCENT,tuple(v*samples for v in (2,13,38,18)),2*samples)
    pygame.draw.ellipse(high,GOLD,tuple(v*samples for v in (12,2,18,38)),2*samples)
    pygame.draw.circle(high,INK,(21*samples,22*samples),4*samples)
    return pygame.transform.smoothscale(high,(42,42)) if samples>1 else high


def header_height(width):
    return 144 if width < 960 else 96 if width < 1120 else 80


def fit_desktop_window(size,desktop,margin):
    """Leave room for window chrome/taskbar without enlarging a requested size."""
    return tuple(max(1,min(int(wanted),int(screen)-int(gap)))
                 for wanted,screen,gap in zip(size,desktop,margin))


def scene_rect(size, camera,mode='solid'):
    w,h = size
    sidebar = min(300, w//4) if camera else 0
    y = header_height(w) + (116 if w<960 and mode=='solid' else 68)
    return (20, y, w-40-sidebar-(16 if sidebar else 0), h-y-68)

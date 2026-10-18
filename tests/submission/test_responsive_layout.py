"""Readable author badge and startup sizing on common laptop displays."""
from pathlib import Path
from types import SimpleNamespace
import pygame
import pytest
from test_stem_ui import SETTINGS
from submission.stem_ui.renderer import SubmissionRenderer
from submission.stem_ui.theme import fit_desktop_window,header_height,scene_rect


@pytest.mark.parametrize('desktop,expected',[
    ((1366,768),(1334,688)),((1280,720),(1248,640)),
    ((1920,1080),(1360,860)),((800,600),(768,520))])
def test_startup_window_fits_desktop_with_room_for_chrome(desktop,expected):
    size=fit_desktop_window((1360,860),desktop,SETTINGS['window_desktop_margin'])
    assert size==expected
    for camera in (False,True):
        x,y,w,h=scene_rect(size,camera)
        assert x>=0 and y>=0 and w>0 and h>0
        assert x+w<=size[0] and y+h<=size[1]


@pytest.mark.parametrize('width',(640,768,800,960,1024,1119,1120,1280,1366,1920))
def test_all_author_lines_stay_inside_badge_without_overlapping(width):
    pygame.font.init()
    r=SubmissionRenderer(SETTINGS)
    path=Path('C:/Windows/Fonts/segoeui.ttf')
    r.fonts={s:pygame.font.Font(str(path) if path.is_file() else None,s) for s in (12,13)}
    controls=110+70+72+94+94+4*6
    compact=width<960; hh=header_height(width)
    left=275 if width>=1120 else 225
    badge=pygame.Rect(left,17,(width-20 if compact else width-controls-20-16)-left,
                      60 if compact else hh-20)
    try:
        labels=r._author_badge_labels(badge,13 if width>=1120 else 12)
        assert len(labels) in (2,4)
        for glyph,rect in labels: assert badge.contains(rect)
        for (_,a),(_,b) in zip(labels,labels[1:]): assert a.bottom<=b.top
    finally: r._label.cache_clear()


def test_resize_on_720p_desktop_does_not_force_client_height_back_above_available_space(monkeypatch):
    r=SubmissionRenderer(SETTINGS); r.size=(1248,640)
    event=SimpleNamespace(type=pygame.VIDEORESIZE,w=1264,h=649)
    monkeypatch.setattr(pygame.event,'get',lambda:[event])
    monkeypatch.setattr(pygame.display,'get_window_size',lambda:(1264,649))
    monkeypatch.setattr(pygame.display,'get_desktop_sizes',lambda:[(1280,720)])
    monkeypatch.setattr(r,'_set_display',lambda:None)
    r.events()
    assert r.size==r.windowed==(1264,649)

"""Fullscreen remembers monitor/position and rejects stale resize events."""
from types import SimpleNamespace
import pygame
from test_stem_ui import SETTINGS
import submission.stem_ui.renderer as renderer


def test_fullscreen_tracks_current_display_and_restores_original_position(monkeypatch):
    r=renderer.SubmissionRenderer(SETTINGS)
    window=SimpleNamespace(position=(2100,180),display_index=1)
    calls=[]
    window.set_windowed=lambda:calls.append('windowed')
    monkeypatch.setattr(renderer,'Window',SimpleNamespace(from_display_module=lambda:window))
    monkeypatch.setattr(pygame.display,'get_window_size',lambda:(1360,860))
    monkeypatch.setattr(pygame.display,'get_desktop_sizes',lambda:[(1920,1200),(2560,1440)])
    monkeypatch.setattr(r,'_set_display',lambda:calls.append((r.fullscreen,r.size,r.restore_window_position)))
    r.toggle_fullscreen()
    assert r.fullscreen and r.size==(2560,1440) and r.display_index==1
    assert r.windowed_position==(2100,180)
    r.toggle_fullscreen()
    assert not r.fullscreen and r.size==(1360,860) and r.restore_window_position
    assert calls==[(True,(2560,1440),False),'windowed',(False,(1360,860),True)]


def test_old_fullscreen_resize_cannot_enlarge_the_restored_window(monkeypatch):
    r=renderer.SubmissionRenderer(SETTINGS)
    monkeypatch.setattr(pygame.display,'get_window_size',lambda:r.size)
    event=SimpleNamespace(type=pygame.VIDEORESIZE,w=1920,h=1200)
    monkeypatch.setattr(pygame.event,'get',lambda:[event])
    def forbidden(): raise AssertionError('stale fullscreen size must not recreate window')
    monkeypatch.setattr(r,'_set_display',forbidden)
    r.events()
    assert r.size==tuple(SETTINGS['window'])

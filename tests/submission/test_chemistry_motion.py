"""Continuous chemistry ownership, grip anchors, and resize hot paths."""
from dataclasses import replace
from types import SimpleNamespace
import numpy as np
import pygame
import pytest
from test_stem_ui import SETTINGS
from test_chemistry import aim,with_ratio
from submission.stem_ui.camera_space import CameraSpace,SpatialPanel
from submission.stem_ui.chemistry import ChemistryScene
from submission.stem_ui.chemistry_input import ChemistryInput
from submission.stem_ui.chemistry_view import CameraChemistryView


def panel_input():
    c=ChemistryInput(ChemistryScene(SETTINGS),SETTINGS); c.page='elements'
    space=CameraSpace(4/3); panel=SpatialPanel(space=space)
    panel.targets=[((0,0,*panel.pixels),'panel:drag')]; c.panel=panel
    return c,space,space.project(panel.center)


def test_panel_reacquires_off_header_without_jump_after_short_tracking_loss():
    c,space,(nx,ny)=panel_input()
    c.update([aim(nx,ny)],1.,space); c.update([aim(nx,ny)],1.05,space)
    c.update([],1.1,space); c.advance(.1)
    anchor=c.layout.anchor.copy()
    assert c.claims[0].paused
    # Neither re-hitting the original header nor a new pinch is required.
    c.panel.targets=[]
    c.update([aim(nx+.12,ny)],1.15,space); c.advance(.1)
    assert not c.claims[0].paused
    np.testing.assert_allclose(c.layout.anchor,anchor)
    c.update([aim(nx+.14,ny)],1.2,space); c.advance(.1)
    assert c.layout.anchor[0]>anchor[0]+.019


def test_panel_opening_freezes_pending_release_and_bounce_rebases():
    c,space,(nx,ny)=panel_input()
    c.update([aim(nx,ny)],1.,space); c.update([aim(nx,ny)],1.05,space)
    anchor=c.layout.anchor.copy()
    c.update([aim(nx+.1,ny,pinch=False)],1.1,space); c.advance(.1)
    assert c.claims[0].paused
    np.testing.assert_allclose(c.layout.anchor,anchor)
    c.update([aim(nx+.1,ny)],1.13,space); c.advance(.1)
    np.testing.assert_allclose(c.layout.anchor,anchor)
    c.update([aim(nx+.12,ny)],1.18,space); c.advance(.1)
    assert c.layout.anchor[0]>anchor[0]+.019
    c.update([aim(nx+.2,ny,pinch=False)],1.22,space)
    frozen=c.layout.anchor.copy(); c.advance(.1)
    c.update([aim(nx+.2,ny,pinch=False)],1.3,space); c.advance(.1)
    assert not c.claims
    np.testing.assert_allclose(c.layout.anchor,frozen)


def test_panel_long_loss_and_identity_change_cancel_claims():
    for identity_change in (False,True):
        c,space,(nx,ny)=panel_input()
        c.update([aim(nx,ny)],1.,space); c.update([aim(nx,ny)],1.05,space)
        if identity_change: c.update([aim(nx,ny,generation=1)],1.1,space)
        else:
            c.update([],1.1,space); c.update([],1.25,space); c.update([],1.35,space)
        assert not c.claims


def test_two_hand_panel_loss_freezes_all_and_rebases_returning_span():
    c,space,_=panel_input()
    points=[space.project(c.panel.world(x,200)) for x in (200,500)]
    hands=[aim(*point,slot=i) for i,point in enumerate(points)]
    c.update(hands,1.,space); c.update(hands,1.05,space)
    assert len(c.claims)==2
    anchor=c.layout.anchor.copy(); scale=c.layout.scale
    c.update([aim(points[0][0]+.05,points[0][1])],1.1,space); c.advance(.1)
    assert c.claims[1].paused and len(c.claims)==2
    np.testing.assert_allclose(c.layout.anchor,anchor)
    assert c.layout.scale==scale
    moved=[aim(point[0]+.1,point[1],slot=i) for i,point in enumerate(points)]
    c.update(moved,1.15,space); c.advance(.1)
    np.testing.assert_allclose(c.layout.anchor,anchor)
    assert c.layout.scale==scale


@pytest.mark.parametrize('edit',(False,True))
def test_fingertip_contact_noise_does_not_move_held_atom_or_break_links(edit):
    scene=ChemistryScene(SETTINGS); scene.add_template('H2O'); scene.edit=edit
    c=ChemistryInput(scene,SETTINGS); space=CameraSpace(4/3)
    nx,ny=space.project(scene.atoms[scene.selected].position)
    h=with_ratio(aim(nx,ny),.1)
    c.update([h],1.,space); c.update([h],1.05,space); c.advance(.02)
    before={i:a.position.copy() for i,a in scene.atoms.items()}; bonds=dict(scene.bonds)
    for step in range(20):
        noisy=with_ratio(h,.4 if step%2 else .1)
        p=list(noisy.landmarks)
        for i in (4,8): p[i]=replace(p[i],x=p[i].x+(.009 if step%2 else -.009))
        noisy=replace(noisy,landmarks=tuple(p),raw_landmarks=tuple(p))
        c.update([noisy],1.1+step/30,space); c.advance(1/30)
    assert scene.bonds==bonds and 0 in c.claims
    for i,p in before.items(): np.testing.assert_allclose(scene.atoms[i].position,p,atol=1e-10)
    c.update([with_ratio(aim(nx+.08,ny),.1)],1.8,space); c.advance(.1)
    assert scene.atoms[scene.selected].position[0]>before[scene.selected][0]+.3


def test_releasing_second_hand_does_not_stall_remaining_hand_for_loss_grace():
    scene=ChemistryScene(SETTINGS); scene.add_template('H2O')
    c=ChemistryInput(scene,SETTINGS); space=CameraSpace(4/3)
    nx,ny=space.project(scene.atoms[scene.selected].position)
    one=aim(nx,ny); two=aim(.88,.55,slot=1)
    for t,hands in ((1.,[one]),(1.05,[one]),(1.1,[one,two]),(1.15,[one,two])):
        c.update(hands,t,space); c.advance(.02)
    assert len(c.claims)==2
    for t in (1.2,1.28):
        c.update([one,aim(.88,.55,slot=1,pinch=False)],t,space); c.advance(.02)
    controller=next(iter(c.groups.values()))['controller']
    assert set(c.claims)=={0} and controller.slots==(0,) and not controller.suspended
    before=scene.atoms[scene.selected].position.copy()
    c.update([aim(nx+.05,ny)],1.3,space); c.advance(.05)
    assert scene.atoms[scene.selected].position[0]>before[0]+.1


def test_captured_motion_skips_redundant_scene_picking(monkeypatch):
    c,space,(nx,ny)=panel_input()
    c.update([aim(nx,ny)],1.,space); c.update([aim(nx,ny)],1.05,space)
    def unexpected(*args): raise AssertionError('captured motion must not require hit testing again')
    monkeypatch.setattr(c,'hit',unexpected)
    for t in (1.1,1.15,1.2): c.update([aim(nx,ny)],t,space)
    assert c.claims[0].kind=='panel_move'


def test_panel_resize_reuses_texture_and_repaints_final_resolution_once(monkeypatch):
    view=CameraChemistryView(SETTINGS,SimpleNamespace(help_visible=True))
    view.content=(0,0,1360,700); view.panel_texture=1
    c=view.input; c.layout.scale=.6
    surface=pygame.Surface((2,2),pygame.SRCALPHA); uploads=[]
    monkeypatch.setattr(view,'_panel',lambda:(view._geometry(),surface))
    monkeypatch.setattr(view,'_upload',lambda *a,**k:uploads.append(1))
    view._ensure_panel(); initial=view.panel_raster
    c.press('mouse',0,'panel:resize',view.space,.3,.7,1.)
    for scale in np.linspace(.6,1.8,60):
        c.layout.scale=float(scale); view._ensure_panel()
    assert len(uploads)==1 and view.panel_raster==initial
    c.end('mouse'); view._ensure_panel()
    assert len(uploads)==2 and view.panel_raster>initial


@pytest.mark.parametrize('timestamp',(1.0,1.5,float('nan')))
def test_time_discontinuity_cancels_drag_without_linking_or_recovery_jump(timestamp):
    scene=ChemistryScene(SETTINGS); scene.edit=True
    i=scene.add('H',(.5,0,0)); scene.add('O',(1.,0,0))
    c=ChemistryInput(scene,SETTINGS); space=CameraSpace(4/3)
    nx,ny=space.project(scene.atoms[i].position); h=aim(nx,ny)
    c.update([h],1.,space); c.update([h],1.05,space)
    assert c.claims[0].kind=='atom'
    before=scene.atoms[i].position.copy()
    c.update([h],timestamp,space); c.advance(.1)
    assert not c.claims and not scene.bonds
    np.testing.assert_allclose(scene.atoms[i].position,before)

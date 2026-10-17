"""Continuous chemistry ownership, observed contact motion, and resize hot paths."""
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
from submission.stem_ui.manipulation import GrabController


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
def test_observed_contact_can_move_object_without_moving_palm(edit):
    scene=ChemistryScene(SETTINGS); scene.add_template('H2O'); scene.edit=edit
    c=ChemistryInput(scene,SETTINGS); space=CameraSpace(4/3)
    nx,ny=space.project(scene.atoms[scene.selected].position)
    h=with_ratio(aim(nx,ny),.1)
    c.update([h],1.,space); c.update([h],1.05,space); c.advance(.02)
    before={i:a.position.copy() for i,a in scene.atoms.items()}; bonds=dict(scene.bonds)
    # A real contact movement must not be discarded by an artificial palm anchor.
    p=list(h.landmarks)
    for i in (4,8): p[i]=replace(p[i],x=p[i].x-.02)
    moved=replace(h,landmarks=tuple(p),raw_landmarks=tuple(p))
    for step in range(5):
        c.update([moved],1.1+step/30,space); c.advance(1/30)
    assert scene.bonds==bonds and 0 in c.claims
    assert scene.atoms[scene.selected].position[0]>before[scene.selected][0]+.08
    assert moved.landmarks==tuple(p)


@pytest.mark.parametrize('kind',('panel','group','atom'))
def test_small_recorded_threshold_crossings_do_not_interrupt_confirmed_hold(kind):
    # Values observed in schema-9 user logs; they are NOT ground-truth gestures.
    ratios=(.4559,.5139,.4785,.4731,.4671,.4970,.4616,.5228,.5997,.5679)
    if kind=='panel':
        c,space,(nx,ny)=panel_input()
    else:
        scene=ChemistryScene(SETTINGS); i=scene.add('C',(.6,0,0)); scene.edit=kind=='atom'
        c=ChemistryInput(scene,SETTINGS); space=CameraSpace(4/3)
        nx,ny=space.project(scene.atoms[i].position)
    h=with_ratio(aim(nx,ny),.1)
    c.update([h],1.,space); c.update([h],1.05,space)
    for i,ratio in enumerate(ratios):
        c.update([with_ratio(aim(nx+.001*i,ny),ratio)],1.1+i*.05,space)
        assert 0 in c.claims and not c.claims[0].paused and not c.gates[0].suspended
        assert all(not g['controller'].suspended for g in c.groups.values())
    # This tolerance does not acquire a new grip at the same partial opening.
    c.release()
    for t in (2.,2.1): c.update([with_ratio(aim(nx,ny),.52)],t,space)
    assert not c.claims


def test_panel_cursor_stays_on_observed_index_during_capture():
    c,space,(nx,ny)=panel_input()
    h=with_ratio(aim(nx,ny),.2)
    c.update([h],1.,space); c.update([h],1.05,space)
    assert c.pointers[0]==pytest.approx((nx,ny))
    assert c.grip_points[0]!=pytest.approx((nx,ny))


@pytest.mark.parametrize('kind',('panel','group','atom'))
def test_clear_opening_freezes_immediately_and_releases_without_post_drop_drift(kind):
    if kind=='panel':
        c,space,(nx,ny)=panel_input()
        position=lambda:c.layout.anchor.copy()
    else:
        scene=ChemistryScene(SETTINGS); i=scene.add('C',(.6,0,0)); scene.edit=kind=='atom'
        c=ChemistryInput(scene,SETTINGS); space=CameraSpace(4/3)
        nx,ny=space.project(scene.atoms[i].position)
        position=lambda:scene.atoms[i].position.copy()
    h=with_ratio(aim(nx,ny),.1)
    c.update([h],1.,space); c.update([h],1.05,space)
    c.update([with_ratio(aim(nx+.02,ny),.1)],1.1,space); c.advance(.01)
    frozen=position()
    opened=with_ratio(aim(nx+.08,ny),.65)
    c.update([opened],1.15,space); c.advance(.2)
    assert c.claims[0].paused
    np.testing.assert_allclose(position(),frozen)
    c.update([opened],1.22,space); c.advance(.2)
    assert not c.claims
    np.testing.assert_allclose(position(),frozen)


def test_component_pose_matches_original_controller_on_identical_observations():
    scene=ChemistryScene(SETTINGS); scene.add_template('H2O')
    c=ChemistryInput(scene,SETTINGS); space=CameraSpace(4/3)
    nx,ny=space.project(scene.atoms[scene.selected].position); h=aim(nx,ny)
    c.update([h],1.,space); c.update([h],1.05,space)
    group=next(iter(c.groups.values()))['controller']
    # Original main rates and actual contact landmarks, no substituted palm XY.
    reference=GrabController({**group.settings,'pose_response_hz':SETTINGS['pose_response_hz'],
        'rotation_response_hz':SETTINGS['rotation_response_hz'],'scale_response_hz':SETTINGS['scale_response_hz']})
    reference.adopt_confirmed_grip(h,1.05,space.aspect); reference.update([h],1.05,space.aspect)
    for i in range(10):
        h=aim(nx+.002*i,ny+.001*i); t=1.1+i/30
        c.update([h],t,space); reference.update([h],t,space.aspect)
        c.advance(1/30); reference.advance(1/30)
        np.testing.assert_allclose(group.pose.position,reference.pose.position)
        np.testing.assert_allclose(group.pose.rotation,reference.pose.rotation)
        assert group.pose.scale==pytest.approx(reference.pose.scale)


@pytest.mark.parametrize('reason',('valid','expired','far','identity','button','page'))
def test_header_aim_survives_pinching_only_within_bounded_time_position_identity(reason):
    c,space,(nx,ny)=panel_input()
    # Aim at the real narrow header, then closing fingers moves the tip below it.
    c.panel.targets=[((0,0,c.panel.pixels[0],68),'panel:drag')]
    nx,ny=space.project(c.panel.world(200,60))
    c.update([aim(nx,ny,pinch=False)],1.,space)
    dx=.2 if reason=='far' else .005
    dropped_y=space.project(c.panel.world(200,95))[1]
    generation=1 if reason=='identity' else 0
    if reason=='button': c.panel.targets.append(((0,70,*c.panel.pixels),'compact'))
    if reason=='page': c.page='home'
    start=1.24 if reason=='expired' else 1.05
    h=aim(nx+dx,dropped_y,generation=generation)
    c.update([h],start,space); c.update([h],start+.05,space)
    assert bool(c.claims)==(reason=='valid')
    if reason=='valid': assert c.claims[0].kind=='panel_move'


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

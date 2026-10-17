"""Cover alignment, observed index taps, and exclusive spatial-panel controls."""
from dataclasses import replace
from types import SimpleNamespace
import math
import numpy as np
import pygame
import pytest
from test_stem_ui import SETTINGS,hand
from test_chemistry import aim,with_ratio
from submission.stem_ui.camera_space import CameraCover,CameraSpace,SpatialPanel
from submission.stem_ui.chemistry_controls import IndexTap,PanelLayout
from submission.stem_ui.chemistry import ChemistryScene
from submission.stem_ui.chemistry_input import ChemistryInput
from submission.stem_ui.chemistry_view import CameraChemistryView
from submission.stem_ui.manipulation import pinch_ratio


def index_pose(angle=180,slot=0,generation=0):
    h=hand(slot,pinch=False)
    p=list(h.landmarks); joint=p[6]; length=.15
    p[8]=replace(p[8],x=joint.x+math.sin(math.radians(angle))*length,
                 y=joint.y+math.cos(math.radians(angle))*length)
    return replace(h,landmarks=tuple(p),raw_landmarks=tuple(p),generation=generation)


@pytest.mark.parametrize('source,dest',[(4/3,16/9),(16/9,4/3),(9/16,16/9),(4/3,4/3)])
def test_cover_crop_preserves_image_geometry_and_snapshot(source,dest):
    cover=CameraCover(source,dest)
    assert cover.width/cover.height*source==pytest.approx(dest)
    assert cover.point(cover.left,cover.top)==pytest.approx((0,0))
    assert cover.point(1-cover.left,1-cover.top)==pytest.approx((1,1))
    original=index_pose(); transformed=cover.hand(original)
    p=original.landmarks[8]; q=transformed.landmarks[8]
    assert (q.x,q.y)==pytest.approx(cover.point(p.x,p.y))
    # Central crop and the single display mirror commute.
    assert 1-q.x==pytest.approx(cover.point(1-p.x,p.y)[0])
    assert original.landmarks[8]==p and q.z==p.z
    assert transformed.raw_landmarks==transformed.landmarks
    assert pinch_ratio(transformed,dest)==pytest.approx(pinch_ratio(original,source))


@pytest.mark.parametrize('aspect',(.6,4/3,16/9,2.5))
@pytest.mark.parametrize('page',('elements','table','compact'))
def test_panel_bounds_keep_title_and_handles_reachable_after_resize(aspect,page):
    space=CameraSpace(aspect); layout=PanelLayout(SETTINGS)
    layout.anchor=np.array((1.3,-.7)); layout.scale=1.8
    panel=SpatialPanel(page=='table',space)
    layout.place(panel,space,(0,0,1000,round(1000/aspect)),page=='compact')
    bounds=np.array([space.project(panel.world(x,y)) for x,y in
        ((0,0),(panel.pixels[0],0),(panel.pixels[0],panel.pixels[1]),(0,panel.pixels[1]))])
    assert bounds.min()>=.015 and bounds.max()<=.985
    assert np.ptp(bounds[:,0])>0 and np.ptp(bounds[:,1])>0


def arm(tap,target=('elements','element:H')):
    for t in (1.,1.05,1.13):
        assert tap.update(0,index_pose(),target,t,(.3,.3),4/3)==((.3,.3),None)


def test_quick_tap_freezes_before_bend_fires_once_and_requires_extension():
    tap=IndexTap(SETTINGS); target=('elements','element:H'); arm(tap,target)
    # The visible tip moves out of the button while bending; aim remains locked.
    assert tap.update(0,index_pose(110),None,1.16,(.39,.4),4/3)==((.3,.3),None)
    assert tap.update(0,index_pose(110),None,1.20,(.39,.4),4/3)==((.3,.3),target)
    for t in (1.3,1.4,1.5):
        assert tap.update(0,index_pose(110),('table','element:C'),t,(.4,.4),4/3)[1] is None
    tap.update(0,index_pose(),target,1.55,(.3,.3),4/3)
    assert 0 not in tap.states


def test_quick_tap_and_dwell_share_latch_no_repeat_on_page_change():
    c=ChemistryInput(ChemistryScene(SETTINGS),SETTINGS); c.page='elements'
    space=CameraSpace(4/3); panel=SpatialPanel(space=space)
    panel.targets=[((0,0,*panel.pixels),'element:H')]; c.panel=panel
    nx,ny=space.project(panel.center)
    straight=index_pose(); origin=straight.landmarks[8]
    dx,dy=1-nx-origin.x,ny-origin.y
    def pose(angle):
        h=index_pose(angle)
        p=tuple(replace(p,x=p.x+dx,y=p.y+dy) for p in h.landmarks)
        return replace(h,landmarks=p,raw_landmarks=p)
    for t,angle in ((1.,180),(1.05,180),(1.13,180),(1.16,110),(1.20,110)):
        c.update([pose(angle)],t,space)
    assert len(c.scene.atoms)==1 and c.dwell.states[0].latched
    assert c.pointers[0]==pytest.approx((nx,ny))
    c.page='table'; panel.targets=[((0,0,*panel.pixels),'element:C')]
    for t in np.arange(1.25,2.8,.05): c.update([pose(110)],float(t),space)
    assert len(c.scene.atoms)==1


@pytest.mark.parametrize('reason',('generation','gap','reverse','blocked','pinch','palm_motion'))
def test_tap_cancel_conditions_cannot_fire(reason):
    tap=IndexTap(SETTINGS); arm(tap)
    h=index_pose(110); t=1.16; blocked=False
    if reason=='generation': h=replace(h,generation=1)
    if reason=='gap': t=2.
    if reason=='reverse': t=1.1
    if reason=='blocked': blocked=True
    if reason=='pinch': h=with_ratio(h,.1); h=replace(h,raw_landmarks=h.landmarks)
    if reason=='palm_motion':
        p=tuple(replace(p,x=p.x+.3) for p in h.landmarks)
        h=replace(h,landmarks=p,raw_landmarks=p)
    assert tap.update(0,h,None,t,(.4,.4),4/3,blocked)[1] is None
    assert tap.update(0,h,None,t+.05,(.4,.4),4/3,blocked)[1] is None


def test_cancelled_slow_press_stays_cancelled_until_extension():
    tap=IndexTap(SETTINGS); arm(tap)
    for t in (1.16,1.3,1.5,1.65,1.8,2.0):
        assert tap.update(0,index_pose(140),('elements','element:H'),t,(.3,.3),4/3)[1] is None
    assert tap.states[0].phase=='cancelled'
    for t in (2.1,2.2):
        assert tap.update(0,index_pose(110),('elements','element:H'),t,(.3,.3),4/3)[1] is None
    tap.update(0,index_pose(),None,2.25,(.4,.4),4/3)
    assert not tap.states


def test_panel_controls_are_exclusive_from_atom_claims_and_preserve_history():
    scene=ChemistryScene(SETTINGS); c=ChemistryInput(scene,SETTINGS); space=CameraSpace(4/3)
    atom=scene.add('H',(1,0,0)); before=scene.state()
    c.press('mouse',0,'panel:drag',space,.2,.2,1.)
    c.press(0,0,'atom:'+str(atom),space,.7,.5,1.)
    assert set(c.claims)=={'mouse'}
    c._panel_motion(space); c.mouse('move',.4,.3,space); c.advance(.1)
    assert c.layout.anchor==pytest.approx((.235,.145),abs=.001)
    c.mouse('up',.4,.3,space)
    assert c.panel_target is None and scene.state()==before
    c.press('mouse',0,'atom:'+str(atom),space,.7,.5,2.)
    c.press(0,0,'panel:resize',space,.2,.2,2.)
    assert set(c.claims)=={'mouse'} and c.claims['mouse'].kind=='group'


def test_two_hand_panel_scale_is_bounded_and_rebases_when_one_leaves():
    c=ChemistryInput(ChemistryScene(SETTINGS),SETTINGS); space=CameraSpace(4/3)
    for slot,x in ((0,.2),(1,.6)):
        c.press(slot,0,'panel:drag',space,x,.2,1.)
    c._panel_motion(space); c.pointers={0:(-.5,.2),1:(1.3,.2)}
    c._panel_motion(space); c.advance(.2)
    assert c.layout.scale==pytest.approx(SETTINGS['chemistry_panel_max_scale'],abs=.001)
    c.end(1); anchor=c.layout.anchor.copy(); scale=c.layout.scale
    c._panel_motion(space); c.advance(.1)
    assert c.layout.anchor==pytest.approx(anchor) and c.layout.scale==pytest.approx(scale)


def test_compact_remembers_page_and_reset_does_not_change_molecules():
    scene=ChemistryScene(SETTINGS); c=ChemistryInput(scene,SETTINGS)
    scene.add_template('H2O'); before=scene.state()
    c.command('table'); c.command('toggle_panel'); assert c.page=='compact'
    c.command('restore_panel'); assert c.page=='table'
    c.command('compact'); c.layout.anchor=np.array((2.,2.)); c.layout.scale=1.8
    c.command('panel_reset')
    assert c.page=='table' and c.layout.scale==1. and scene.state()==before


def test_panel_lost_hand_cancels_movement_without_extrapolation():
    c=ChemistryInput(ChemistryScene(SETTINGS),SETTINGS); space=CameraSpace(4/3)
    panel=SpatialPanel(space=space); panel.targets=[((0,0,*panel.pixels),'panel:drag')]; c.panel=panel
    nx,ny=space.project(panel.center)
    h=aim(nx,ny)
    c.update([h],1.,space); c.update([h],1.05,space)
    assert c.claims[0].kind=='panel_move'
    anchor=c.layout.anchor.copy()
    c.update([],1.1,space); c.advance(.2)
    assert not c.claims and c.layout.anchor==pytest.approx(anchor)


def test_panel_drag_does_not_upload_texture_or_mutate_scene(monkeypatch):
    view=CameraChemistryView(SETTINGS,SimpleNamespace(help_visible=True))
    view.content=(0,0,1360,700); view.panel_texture=1
    uploads=[]
    surface=pygame.Surface((2,2),pygame.SRCALPHA)
    monkeypatch.setattr(view,'_panel',lambda:(view._geometry(),surface))
    monkeypatch.setattr(view,'_upload',lambda *a,**k:uploads.append(1))
    view._ensure_panel()
    for x in np.linspace(.04,.4,50):
        view.input.layout.anchor=np.array((x,.05)); view._ensure_panel()
    assert len(uploads)==1


def test_tap_freezes_the_actual_smoothed_visual_cursor_before_bend():
    view=CameraChemistryView(SETTINGS,SimpleNamespace(help_visible=True))
    arm(view.input.tap)
    view.input.tap.update(0,index_pose(110),None,1.16,(.4,.4),4/3)
    view.cursor_points={(0,0):view.space.point(.29,.298,.6)}
    view._anchor_press_cursor()
    assert view.input.pointers[0]==pytest.approx((.29,.298))
    assert view.input.tap.states[0].anchor==pytest.approx((.29,.298))
    # A render loop must not continuously move that anchor toward the bent tip.
    view.cursor_points[(0,0)]=view.space.point(.4,.4,.6)
    view._anchor_press_cursor()
    assert view.input.tap.states[0].anchor==pytest.approx((.29,.298))


def test_stationary_panel_reuses_projection_and_motion_invalidates_it():
    view=CameraChemistryView(SETTINGS,SimpleNamespace(help_visible=True))
    view.content=(0,0,1360,700)
    first=view._geometry()
    for _ in range(30): assert view._geometry() is first
    view.input.layout.anchor+=np.array((.05,0.))
    assert view._geometry() is not first

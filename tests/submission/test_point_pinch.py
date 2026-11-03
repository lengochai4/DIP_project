"""Observed menu confirmation, independent of model-relative depth."""
from dataclasses import replace
from types import SimpleNamespace
import math
import numpy as np
import pytest
from test_stem_ui import SETTINGS
from test_chemistry import aim,with_ratio
from submission.stem_ui.camera_space import CameraSpace,SpatialPanel
from submission.stem_ui.chemistry import ChemistryScene
from submission.stem_ui.chemistry_controls import PointPinch
from submission.stem_ui.chemistry_input import ChemistryInput
from submission.stem_ui.chemistry_view import CameraChemistryView

TARGET=('elements','element:H')


def sample(ratio,slot=0,generation=0,nx=.3,ny=.3):
    return with_ratio(aim(nx,ny,slot=slot,generation=generation),ratio)


def arm(selector,target=TARGET):
    for t in (1.,1.06,1.12):
        assert selector.update(0,sample(1.),target,t,(.3,.3),4/3)[1] is None
    assert selector.states[0].phase=='armed'


def test_gradual_close_captures_aim_confirms_once_and_unlocks_without_waiting_for_open():
    s=PointPinch(SETTINGS); arm(s)
    assert s.update(0,sample(.55),TARGET,1.17,(.305,.31),4/3)[1] is None
    assert s.update(0,sample(.4),None,1.2,(.31,.32),4/3)==((.3,.3),None)
    assert s.update(0,sample(.1),None,1.24,(.32,.33),4/3)[1] is None
    assert s.update(0,sample(.1),None,1.29,(.32,.33),4/3)==((.3,.3),TARGET)
    for t in (1.5,1.6,1.7):
        point,chosen=s.update(0,sample(.1),('table','edit'),t,(.4,.4),4/3)
        assert point==(.4,.4) and chosen is None and not s.states[0].locked
    # Release, re-aim, then a fresh pinch may explicitly choose the same tile.
    for t in (1.8,1.9,2.02): s.update(0,sample(1.),TARGET,t,(.3,.3),4/3)
    s.update(0,sample(.1),TARGET,2.07,(.3,.3),4/3)
    assert s.update(0,sample(.1),TARGET,2.12,(.3,.3),4/3)[1]==TARGET


@pytest.mark.parametrize('reason',('already_closed','too_soon','open_shake','partial','sideways','spike'))
def test_ambiguous_motion_does_not_confirm_a_menu_action(reason):
    s=PointPinch(SETTINGS); chosen=[]
    if reason not in ('already_closed','too_soon'): arm(s)
    elif reason=='too_soon': s.update(0,sample(1.),TARGET,1.,(.3,.3),4/3)
    for i in range(14):
        t=(1.02 if reason=='too_soon' else 1.2)+i*.04
        ratio=1. if reason=='open_shake' else .4 if reason=='partial' else .1
        if reason=='spike' and i>0: ratio=1.
        point=(.5,.5) if reason=='sideways' else (.3,.3)
        chosen.append(s.update(0,sample(ratio),TARGET,t,point,4/3)[1])
    assert not any(chosen)
    if reason=='partial': assert s.states[0].phase=='cancelled' and not s.states[0].locked


@pytest.mark.parametrize('reason',('generation','gap','reverse','missing','blocked','invalid'))
def test_capture_cancels_safely_on_input_discontinuity(reason):
    s=PointPinch(SETTINGS); arm(s)
    s.update(0,sample(.1),TARGET,1.2,(.3,.3),4/3)
    if reason=='missing': s.retain(())
    t=1.5 if reason=='gap' else 1.1 if reason=='reverse' else 1.24
    if reason=='invalid': t=float('nan')
    h=sample(.1,generation=1 if reason=='generation' else 0)
    assert s.update(0,h,TARGET,t,(.3,.3),4/3,reason=='blocked')[1] is None
    assert not s.states or (s.states[0].phase=='cancelled' and not s.states[0].locked)
    if s.states: assert math.isfinite(s.states[0].last)


def test_menu_confirmation_does_not_depend_on_model_z():
    s=PointPinch(SETTINGS); arm(s)
    for t in (1.2,1.25):
        h=sample(.1)
        points=tuple(replace(p,z=float(np.sin(p.index))) for p in h.landmarks)
        chosen=s.update(0,replace(h,landmarks=points,raw_landmarks=points),TARGET,t,(.3,.3),4/3)[1]
    assert chosen==TARGET


def palette(action='element:H',page='elements'):
    c=ChemistryInput(ChemistryScene(SETTINGS),SETTINGS); c.page=page
    space=CameraSpace(4/3); panel=SpatialPanel(space=space)
    panel.targets=[((0,0,*panel.pixels),action)]; c.panel=panel
    return c,space,space.project(panel.center)


def select(c,space,point,start=1.):
    for dt,ratio in ((0,1.),(.06,1.),(.12,1.),(.17,.55),(.2,.4),(.24,.1),(.29,.1)):
        c.update([sample(ratio,nx=point[0],ny=point[1])],start+dt,space)


def test_button_selection_consumes_pinch_and_cannot_grab_atom_after_page_change(monkeypatch):
    c,space,p=palette(); select(c,space,p)
    assert len(c.scene.atoms)==1 and not c.claims and c.dwell.states[0].latched
    c.page='table'
    monkeypatch.setattr(c,'hit',lambda *a:'atom:1')
    for t in np.arange(1.35,2.,.05):
        c.update([sample(.1,nx=p[0],ny=p[1])],float(t),space)
        assert not c.claims and len(c.scene.atoms)==1


def test_dwell_and_pinch_do_not_double_select_but_a_new_release_cycle_can_select_again():
    c,space,p=palette()
    for t in np.arange(1.,2.01,.05): c.update([sample(1.,nx=p[0],ny=p[1])],float(t),space)
    assert len(c.scene.atoms)==1
    for t in (2.04,2.1): c.update([sample(.1,nx=p[0],ny=p[1])],t,space)
    assert len(c.scene.atoms)==1
    # A held latch needs release confirmation, then a fresh stable aim.
    for t,ratio in ((2.15,1.),(2.23,1.),(2.35,1.),(2.4,.4),(2.45,.1),(2.5,.1)):
        c.update([sample(ratio,nx=p[0],ny=p[1])],t,space)
    assert len(c.scene.atoms)==2


def test_collapsed_edge_arrow_accepts_explicit_menu_pinch():
    c,space,p=palette('restore_panel','compact'); c.expanded_page='elements'
    select(c,space,p)
    assert c.page=='elements' and not c.claims


def test_point_pinch_captures_actual_smoothed_cursor_without_following_closed_tip():
    view=CameraChemistryView(SETTINGS,SimpleNamespace(help_visible=True)); s=view.input.tap
    view.input.page='elements'
    view.input.panel=SpatialPanel(space=view.space)
    view.input.panel.targets=[((0,0,*view.input.panel.pixels),'element:H')]
    arm(s); s.update(0,sample(.4),TARGET,1.2,(.31,.31),4/3)
    view.cursor_points={(0,0):view.space.point(.29,.298,.6)}
    view._anchor_press_cursor()
    assert s.states[0].anchor==pytest.approx((.29,.298))
    view.cursor_points[(0,0)]=view.space.point(.4,.4,.6)
    view._anchor_press_cursor()
    assert s.states[0].anchor==pytest.approx((.29,.298))


def test_incomplete_menu_pinch_times_out_and_one_second_hover_still_works():
    c,space,p=palette()
    for t in (1.,1.06,1.12): c.update([sample(1.,nx=p[0],ny=p[1])],t,space)
    for t in np.arange(1.2,3.31,.05):
        c.update([sample(.4,nx=p[0],ny=p[1])],float(t),space)
    assert len(c.scene.atoms)==1 and not c.claims
    assert not c.tap.states[0].locked


@pytest.mark.parametrize('reason',('brief_loss_after_click','page_change_during_close'))
def test_consumed_menu_close_cannot_become_grab_after_interruption(reason,monkeypatch):
    c,space,p=palette()
    if reason=='brief_loss_after_click':
        select(c,space,p)
        c.update([],1.35,space)
        start=1.4
    else:
        c.scene.add('H',(.5,0,0))
        for t in (1.,1.06,1.12): c.update([sample(1.,nx=p[0],ny=p[1])],t,space)
        c.update([sample(.4,nx=p[0],ny=p[1])],1.2,space)
        start=1.24
    c.page='table'
    monkeypatch.setattr(c,'hit',lambda *a:'atom:1')
    for t in np.arange(start,start+.2,.04):
        c.update([sample(.1,nx=p[0],ny=p[1])],float(t),space)
        assert not c.claims


def test_recorded_tight_close_survives_small_contact_threshold_crossing():
    # Scalar sequence from schema-12 session ui-20261018-074810-827878,
    # 12.664..12.793s. Geometry is synthetic: this is not a labeled replay.
    s=PointPinch(SETTINGS); arm(s)
    chosen=[]
    for t,ratio in ((1.2,.4013318),(1.232,.1286818),(1.265,.1903525),(1.329,.2801674)):
        chosen.append(s.update(0,sample(ratio),TARGET,t,(.3,.3),4/3)[1])
    assert chosen==[None,None,None,TARGET]


@pytest.mark.parametrize('ratios',((.1,.33,.33,.33),(.33,.33,.33,.33),(.1,.38,.1,.38)))
def test_partial_contact_or_one_tight_spike_never_accumulates_confirmation(ratios):
    s=PointPinch(SETTINGS); arm(s)
    s.update(0,sample(.4),TARGET,1.2,(.3,.3),4/3)
    for n,ratio in enumerate(ratios):
        assert s.update(0,sample(ratio),TARGET,1.23+n*.03,(.3,.3),4/3)[1] is None


def test_armed_aim_can_follow_small_motion_inside_same_button_without_periodic_reset():
    s=PointPinch(SETTINGS); arm(s)
    for n in range(1,8):
        point=(.3+n*.01,.3)
        s.update(0,sample(1.,nx=point[0]),TARGET,1.12+n*.03,point,4/3)
        assert s.states[0].phase=='armed'
    # Entering another button still requires its own stable aim.
    s.update(0,sample(1.,nx=.38),('elements','element:O'),1.39,(.38,.3),4/3)
    assert s.states[0].phase=='aim'


def test_folded_contact_finger_does_not_cancel_while_observed_palm_stays_still():
    s=PointPinch(SETTINGS); arm(s)
    s.update(0,sample(.4),TARGET,1.2,(.3,.3),4/3)
    for t in (1.23,1.28):
        h=sample(.1)
        points=list(h.landmarks)
        for i in (4,8): points[i]=replace(points[i],y=points[i].y+.09)
        chosen=s.update(0,replace(h,landmarks=tuple(points)),None,t,(.3,.39),4/3)[1]
    assert chosen==TARGET


def test_rigid_hand_translation_during_capture_cancels_without_click():
    s=PointPinch(SETTINGS); arm(s)
    s.update(0,sample(.4),TARGET,1.2,(.3,.3),4/3)
    assert s.update(0,sample(.1,nx=.44),TARGET,1.24,(.44,.3),4/3)[1] is None
    assert s.states[0].phase=='cancelled' and s.states[0].reason=='palm_motion'


def test_lagging_display_cursor_cannot_replace_capture_with_neighboring_button(monkeypatch):
    view=CameraChemistryView(SETTINGS,SimpleNamespace(help_visible=True)); s=view.input.tap
    arm(s); s.update(0,sample(.4),TARGET,1.2,(.31,.31),4/3)
    view.cursor_points={(0,0):view.space.point(.29,.298,.6)}
    monkeypatch.setattr(view.input,'hit',lambda *args:'element:O')
    view._anchor_press_cursor()
    assert s.states[0].anchor==(.3,.3)


def test_captured_button_dispatch_ignores_neighbor_under_display_anchor(monkeypatch):
    c,space,p=palette()
    for t in (1.,1.06,1.12): c.update([sample(1.,nx=p[0],ny=p[1])],t,space)
    c.update([sample(.4,nx=p[0],ny=p[1])],1.2,space)
    c.tap.states[0].anchor=(p[0]+.01,p[1])
    monkeypatch.setattr(c,'hit',lambda *args:'element:O')
    for t in (1.24,1.29): c.update([sample(.1,nx=p[0],ny=p[1])],t,space)
    assert [a.symbol for a in c.scene.atoms.values()]==['H']
    assert not c.claims

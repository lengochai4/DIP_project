"""Observed shortcut gates, ownership priority and modal command selection."""
from dataclasses import replace
import numpy as np
import pygame
import pytest
from test_stem_ui import SETTINGS,hand,palm
from test_point_pinch import sample
from test_physics_view import view
from submission.stem_ui.camera_space import CameraCover
from submission.stem_ui.physics_shortcuts import PhysicsShortcuts
from submission.stem_ui.manipulation import palm_size


def with_ratio(h,ratio):
    points=list(h.landmarks)
    points[4]=replace(points[4],x=points[8].x+palm_size(h,4/3)*ratio,y=points[8].y)
    return replace(h,landmarks=tuple(points))


def open_hand(nx=.88,ny=.35,slot=0,generation=0,scale=.30):
    # Complete, front-facing XY skeleton, with thumb spread and straight fingers.
    points=tuple(replace(p,x=1-nx+(p.x-.5)*scale,y=ny+(p.y-.53)*scale) for p in palm())
    return replace(hand(slot,pinch=False),landmarks=points,generation=generation)


def tick(control,hands,t,can_quick=True,can_scene=False,free=True,observed=None,aspect=4/3):
    hands={h.slot:h for h in hands}
    return control.update(hands,hands if observed is None else observed,t,aspect,4/3,
                          {k:free for k in hands},can_quick,can_scene)


@pytest.mark.parametrize('nx',(.12,.88))
@pytest.mark.parametrize('scale',(.20,.30))
def test_open_palm_has_scale_normalized_pose_and_summons_once(nx,scale):
    c=PhysicsShortcuts(SETTINGS); h=open_hand(nx=nx,scale=scale)
    assert c.features(h,4/3)[1]
    events=[event for t in np.arange(1,3,.04) if (event:=tick(c,[h],float(t)))]
    assert events==[('quick','left' if nx<.5 else 'right')]


@pytest.mark.parametrize('cause',('folded','pinch','edge_on','tiny','out_of_frame','center','busy','moving','gap','identity','invalid'))
def test_ambiguous_or_interrupted_palm_never_summons(cause):
    c=PhysicsShortcuts(SETTINGS); h=open_hand()
    if cause=='folded':
        h=replace(h,landmarks=tuple(replace(p,y=h.landmarks[6].y+.02) if p.index==8 else p for p in h.landmarks))
    elif cause=='pinch': h=with_ratio(h,.1)
    elif cause=='tiny': h=open_hand(scale=.01)
    elif cause=='out_of_frame': h=open_hand(nx=.99)
    elif cause=='center': h=open_hand(nx=.5)
    elif cause=='edge_on': h=replace(h,landmarks=tuple(replace(p,x=.12) for p in h.landmarks))
    elif cause=='invalid': h=replace(h,landmarks=h.landmarks[:-1])
    events=[]
    for i in range(24):
        current=h; t=1+i*(.35 if cause=='gap' else .04)
        if cause=='identity': current=replace(h,generation=i//5)
        if cause=='moving': current=open_hand(ny=.25+(i%2)*.1)
        result=tick(c,[current],t,free=cause!='busy')
        if result: events.append(result)
    assert not events


def test_palm_latch_survives_loss_and_requires_observed_pose_departure_to_rearm():
    c=PhysicsShortcuts(SETTINGS); h=open_hand()
    events=[]
    for t in np.arange(1,1.8,.04):
        if event:=tick(c,[h],float(t)): events.append(event)
    tick(c,[],1.82)
    for t in np.arange(1.86,2.5,.04):
        if event:=tick(c,[h],float(t)): events.append(event)
    assert len(events)==1
    for t in np.arange(2.54,2.9,.04): tick(c,[open_hand(nx=.6)],float(t))
    for t in np.arange(2.94,3.6,.04):
        if event:=tick(c,[h],float(t)): events.append(event)
    assert len(events)==2


@pytest.mark.parametrize('aspect',(1.,16/9,9/16))
def test_source_pose_is_unchanged_by_display_cover_crop(aspect):
    source=open_hand(); display=CameraCover(4/3,aspect).hand(source); c=PhysicsShortcuts(SETTINGS)
    assert c.features(source,4/3)[1]
    # Use a middle display edge position for this crop: pose comes from source.
    events=[]
    for t in np.arange(1,1.7,.04):
        event=tick(c,[display],float(t),aspect=aspect,observed={0:source})
        if event: events.append(event)
    center=np.mean([display.landmarks[i].x for i in (0,5,9,13,17)])
    visible=0<=center<=1
    assert bool(events)==visible


def two_hands(closed=False,generation=0):
    hands=[open_hand(nx=.55,slot=0,generation=generation),open_hand(nx=.85,slot=1)]
    return [with_ratio(h,.1) for h in hands] if closed else hands


def test_two_hand_shortcut_requires_fresh_open_then_closed_hold_and_no_target():
    c=PhysicsShortcuts(SETTINGS)
    for t in np.arange(1,1.5,.04): assert tick(c,two_hands(True),float(t),False,True) is None
    for t in np.arange(1.54,1.74,.04): assert tick(c,two_hands(),float(t),False,True) is None
    events=[e for t in np.arange(1.78,2.1,.04) if (e:=tick(c,two_hands(True),float(t),False,True))]
    assert events==[('scene',(0,1))]


@pytest.mark.parametrize('cause',('loss','identity','busy','running','stale','one_hand','invalid'))
def test_pair_pending_state_does_not_cross_a_discontinuity_or_busy_target(cause):
    c=PhysicsShortcuts(SETTINGS)
    for t in np.arange(1,1.2,.04): tick(c,two_hands(),float(t),False,True)
    tick(c,two_hands(True),1.24,False,True)
    if cause=='loss': tick(c,[],1.27,False,True)
    events=[]
    for i in range(8):
        hands=two_hands(True,generation=4 if cause=='identity' else 0)
        if cause=='one_hand': hands=hands[:1]
        if cause=='invalid': hands[0]=replace(hands[0],landmarks=())
        event=tick(c,hands,1.28+i*(.35 if cause=='stale' else .04),False,cause!='running',free=cause!='busy')
        if event: events.append(event)
    assert not events


def summon(v,start=1.):
    for t in np.arange(start,start+.65,.04):
        v.input.update([open_hand()],float(t),v.space.aspect)
        v.input.advance(1/60)
    assert v.quick_open
    v.layout(); v._paint_quick()


def select_quick(v,action,start=2.):
    rect=next(r for r,a in v.quick_targets if a=='quick:'+action)
    x,y=rect.centerx/v.content[2],rect.centery/v.content[3]
    for i in range(3): v.input.update([sample(1,nx=.5,ny=.8)],start+i*.04,v.space.aspect)
    for i,ratio in enumerate([1.]*8+[.4,.1,.1,.1]):
        v.input.update([sample(ratio,nx=x,ny=y)],start+.12+i*.04,v.space.aspect)
        v.input.advance(1/60)
    return x,y


def test_menu_summon_never_activates_under_stationary_hand_and_selection_is_one_shot():
    v=view(); summon(v)
    for t in np.arange(1.7,3.2,.04): v.input.update([open_hand()],float(t),v.space.aspect)
    assert v.quick_open and not v.model.running and not v.input.claims
    x,y=select_quick(v,'run',3.3)
    assert not v.quick_open and v.model.running and not v.input.claims
    v.hit=lambda p:'drag:force'  # A newly exposed target must not catch the same pinch.
    for t in np.arange(3.9,4.8,.04):
        v.input.update([sample(.1,nx=x,ny=y)],float(t),v.space.aspect); v.input.advance(.02)
    assert v.model.running and not v.input.claims


def test_new_hand_at_quick_button_does_not_start_dwell_until_open_reaim():
    v=view(); v.command('quick_open:right'); v._paint_quick()
    r=next(r for r,a in v.quick_targets if a=='quick:run'); x,y=r.centerx/v.content[2],r.centery/v.content[3]
    for t in np.arange(1,3,.04): v.input.update([sample(1,nx=x,ny=y)],float(t),v.space.aspect)
    assert not v.model.running and v.quick_open
    for t in np.arange(3.04,3.28,.04): v.input.update([sample(1,nx=.5,ny=.8)],float(t),v.space.aspect)
    for t in np.arange(3.32,4.7,.04): v.input.update([sample(1,nx=x,ny=y)],float(t),v.space.aspect)
    assert v.model.running and not v.quick_open


def test_free_palm_never_summons_over_another_hands_active_parameter_edit():
    v=view(); v.hit=lambda p:'drag:force'
    for t in (1.,1.05): v.input.update([sample(.1,nx=.6,ny=.6)],t,v.space.aspect)
    assert v.input.claims
    for t in np.arange(1.1,2.1,.04):
        v.input.update([sample(.1,nx=.6,ny=.6),open_hand(slot=1)],float(t),v.space.aspect)
    assert not v.quick_open and v.input.claims[0].target=='drag:force'


def test_palette_check_and_show_panel_keep_static_model_static():
    v=view(); v.command('lab:lever'); v.command('challenge')
    v.model.set_parameter('arm2',1); v.command('quick_open:right'); v._paint_quick()
    select_quick(v,'run'); assert v.model.achieved and not v.model.running and v.model.time==0
    v.command('compact'); v.command('quick_open:right'); v._paint_quick()
    select_quick(v,'panel',3.); assert not v.collapsed and not v.quick_open


def test_busy_shortcut_path_does_not_evaluate_new_pose_features(monkeypatch):
    c=PhysicsShortcuts(SETTINGS)
    monkeypatch.setattr(c,'features',lambda *args:pytest.fail('Pose work during an ordinary active grab'))
    assert tick(c,[open_hand()],1.,False,False) is None


def test_mouse_palette_selection_preserves_guards_for_present_hands():
    v=view(); summon(v); r=next(r for r,a in v.quick_targets if a=='quick:close')
    v.mouse('down',(v.content[0]+r.centerx,v.content[1]+r.centery))
    assert not v.quick_open and v.input.menu_anchors
    v.hit=lambda p:'drag:force'
    for t in np.arange(1.7,2.2,.04):
        v.input.update([with_ratio(open_hand(),.1)],float(t),v.space.aspect)
    assert not v.input.claims


def test_mouse_wheel_does_not_edit_background_under_modal_palette():
    v=view(); v.command('quick_open:right'); before=(v.zoom,v.panel_scale)
    v.wheel(1,(v.content[0]+.8*v.content[2],v.content[1]+.5*v.content[3]))
    assert (v.zoom,v.panel_scale)==before and v.quick_open


def test_after_palette_closes_observed_opening_releases_guard_without_extra_motion():
    v=view(); summon(v); x,y=select_quick(v,'close')
    assert v.input.menu_anchors
    for t in (2.7,2.74): v.input.update([sample(1,nx=x,ny=y)],t,v.space.aspect)
    assert not v.input.menu_anchors and not v.input.claims


@pytest.mark.parametrize('action',('run','undo','panel','frame','close'))
def test_quick_palette_reuses_existing_commands(action):
    v=view(); v.command('inc:force'); force=v.model.params['force']
    v.yaw=30; v.zoom=1.5; v.command('quick_open:right'); v._paint_quick()
    select_quick(v,action)
    assert not v.quick_open and not v.input.claims
    if action=='run': assert v.model.running
    elif action=='undo': assert v.model.params['force']<force
    elif action=='panel': assert v.collapsed
    elif action=='frame': assert v.zoom==1 and v.yaw==v.cfg['default_yaw_deg']
    else: assert v.model.params['force']==force and v.zoom==1.5


@pytest.mark.parametrize('size',((424,240),(600,320),(920,416),(1320,644)))
@pytest.mark.parametrize('side',('left','right'))
def test_palette_is_modal_and_fits_both_edges_at_compact_sizes(size,side):
    v=view(*size); original=v.targets.copy(); v.command('quick_open:'+side); v.layout(); v._paint_quick()
    bounds=pygame.Rect(0,0,*size); assert bounds.contains(v.quick_rect)
    assert {a for _,a in v.quick_targets}=={'quick:run','quick:undo','quick:panel','quick:frame','quick:close'}
    for r,a in v.quick_targets:
        assert v.quick_rect.contains(r)
        assert v.hit((r.centerx/size[0],r.centery/size[1]))==a
    for i,(r,a) in enumerate(v.quick_targets):
        for other,_ in v.quick_targets[i+1:]: assert not r.colliderect(other)
    assert v.targets==original
    assert v.hit((.5 if side=='left' else .02,.02)) is None


def test_automatic_scene_uses_existing_follow_and_returns_to_edit_on_both_release():
    v=view(); before=v.model.snapshot()
    for t in np.arange(1,1.2,.04): v.input.update(two_hands(),float(t),v.space.aspect)
    for t in np.arange(1.24,1.5,.04):
        v.input.update(two_hands(True),float(t),v.space.aspect); v.input.advance(.02)
    assert v.input.auto_scene and v.tool=='scene' and len(v.input.claims)==2
    for i in range(6):
        hands=[with_ratio(open_hand(nx=.5),.1),with_ratio(open_hand(nx=.9,slot=1),.1)]
        v.input.update(hands,1.52+i*.04,v.space.aspect); v.input.advance(.02)
    assert v.zoom>1 and v.model.snapshot()==before
    for t in np.arange(1.8,2.1,.04):
        v.input.update(two_hands(),float(t),v.space.aspect); v.input.advance(.02)
    assert not v.input.auto_scene and v.tool=='edit' and not v.input.claims
    assert not v.model.running and v.model.snapshot()==before


@pytest.mark.parametrize('cause',('loss','identity','stale','release'))
def test_temporary_scene_cancels_without_pending_view_motion(cause):
    v=view()
    for t in np.arange(1,1.2,.04): v.input.update(two_hands(),float(t),v.space.aspect)
    for t in np.arange(1.24,1.5,.04):
        v.input.update(two_hands(True),float(t),v.space.aspect); v.input.advance(.01)
    assert v.input.auto_scene
    before=(v.yaw,v.pitch,v.zoom,v.roll,*v.scene_pan)
    if cause=='loss': v.input.update(two_hands(True)[1:],1.52,v.space.aspect)
    elif cause=='identity': v.input.update(two_hands(True,generation=9),1.52,v.space.aspect)
    elif cause=='stale': v.input.update(two_hands(True),2.,v.space.aspect)
    else: v.input.release()
    for _ in range(20): v.input.advance(.01)
    assert not v.input.auto_scene and v.tool=='edit' and not v.input.claims
    assert (v.yaw,v.pitch,v.zoom,v.roll,*v.scene_pan)==pytest.approx(before)


def test_shortcuts_do_not_steal_a_parameter_or_running_simulation():
    v=view(); v.model.running=True
    for t in np.arange(1,1.2,.04): v.input.update(two_hands(),float(t),v.space.aspect)
    for t in np.arange(1.24,1.6,.04): v.input.update(two_hands(True),float(t),v.space.aspect)
    assert not v.input.auto_scene and v.model.running
    v.model.running=False; v.hit=lambda p:'drag:force'
    for t in np.arange(1.64,1.9,.04): v.input.update(two_hands(),float(t),v.space.aspect)
    for t in np.arange(1.94,2.3,.04): v.input.update(two_hands(True),float(t),v.space.aspect)
    assert not v.input.auto_scene and len(v.input.claims)==1
    assert v.input.claims[0].target=='drag:force'


@pytest.mark.parametrize('new_generation',(0,9))
def test_lost_temporary_grip_cannot_regrab_exposed_objects_while_still_closed(new_generation):
    v=view()
    for t in np.arange(1,1.2,.04): v.input.update(two_hands(),float(t),v.space.aspect)
    for t in np.arange(1.24,1.5,.04):
        v.input.update(two_hands(True),float(t),v.space.aspect); v.input.advance(.01)
    assert v.input.auto_scene
    v.input.update([],1.52,v.space.aspect); v.hit=lambda p:'drag:force'
    for t in np.arange(1.56,1.9,.04):
        v.input.update(two_hands(True,generation=new_generation),float(t),v.space.aspect); v.input.advance(.01)
    assert not v.input.auto_scene and not v.input.claims
    assert v.model.params['force']==10

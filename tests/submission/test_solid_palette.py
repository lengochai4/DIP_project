"""Modal shape selection, no grab-through, and observed geometry descriptions."""
from dataclasses import replace
from types import SimpleNamespace
import math
import numpy as np
import pygame
import pytest
from test_stem_ui import SETTINGS, hand
from test_point_pinch import sample
from test_physics_shortcuts import open_hand
from submission.stem_ui.solid_palette import SolidPalette, tip_summary
from submission.stem_ui.geometry import Tip, project_live_tip
from submission.stem_ui.renderer import SubmissionRenderer
from submission.stem_ui.runtime import Snapshot

VIEW=(20,180,800,440)


def summon(c, nx=.88):
    h=open_hand(nx=nx)
    for t in np.arange(1,1.7,.04): c.update((h,),float(t),4/3,VIEW)
    assert c.open
    return h


def target(c, action):
    rect=next(rect for rect,a in c.targets if a==action)
    x,y,w,h=VIEW
    return (rect.centerx-x)/w,(rect.centery-y)/h


def at(c,action,ratio=1.):
    nx,ny=target(c,action)
    return sample(ratio,nx=nx,ny=ny)


@pytest.mark.parametrize('nx',(.12,.88))
def test_palm_summons_but_stationary_summoning_hand_cannot_select(nx):
    c=SolidPalette(SETTINGS); h=summon(c,nx)
    assert c.edge==('left' if nx<.5 else 'right')
    for t in np.arange(1.72,3,.04): assert c.update((h,),float(t),4/3,VIEW) is None
    assert c.open and c.anchors and not c.dwell.states


@pytest.mark.parametrize('action',('cube','tetra','octa','sphere','close'))
@pytest.mark.parametrize('method',('pinch','dwell'))
def test_reaim_then_select_once_by_pinch_or_one_second_dwell(action,method):
    c=SolidPalette(SETTINGS); summon(c)
    for t in np.arange(1.72,1.96,.04): assert c.update((at(c,action),),float(t),4/3,VIEW) is None
    assert not c.anchors
    selected=[]
    for i in range(40):
        h=at(c,action,.1 if method=='pinch' else 1.)
        result=c.update((h,),2+i*.04,4/3,VIEW)
        if result: selected.append(result)
    assert selected==[action] and not c.open
    if method=='pinch':
        assert not c.grab_hands((h,),4/3)
        # A closed reacquired generation is still the consumed menu intent.
        assert not c.grab_hands((replace(h,generation=9),),4/3)
        assert c.grab_hands((at(c,action),),4/3)


@pytest.mark.parametrize('reason',('busy','closed','folded','center','missing','generation','gap'))
def test_ambiguous_or_busy_input_does_not_open(reason):
    c=SolidPalette(SETTINGS)
    for i in range(30):
        h=open_hand(nx=.5 if reason=='center' else .88)
        if reason=='closed': h=sample(.1,nx=.88)
        if reason=='folded':
            points=list(h.landmarks); points[8]=replace(points[8],y=points[6].y+.02)
            h=replace(h,landmarks=tuple(points))
        if reason=='generation': h=replace(h,generation=i//5)
        hands=() if reason=='missing' and i%4==0 else (h,)
        c.update(hands,1+i*(.3 if reason=='gap' else .04),4/3,VIEW,busy=reason=='busy')
    assert not c.open


@pytest.mark.parametrize('reason',('missing','generation','gap','reverse','stale','viewport'))
def test_pending_selection_cancels_and_closed_hand_cannot_catch_object(reason):
    c=SolidPalette(SETTINGS); summon(c)
    for t in np.arange(1.72,1.96,.04): c.update((at(c,'sphere'),),float(t),4/3,VIEW)
    c.update((at(c,'sphere',.1),),2.,4/3,VIEW)
    if reason=='missing': c.update((),2.02,4/3,VIEW)
    elif reason in ('stale','viewport'): c.suspend()
    t=2.4 if reason=='gap' else 1.9 if reason=='reverse' else 2.05
    h=at(c,'sphere',.1)
    if reason=='generation': h=replace(h,generation=5)
    assert c.update((h,),t,4/3,VIEW) is None
    if c.open: c.transition(False)
    assert not c.grab_hands((h,),4/3)


@pytest.mark.parametrize('view',((20,180,424,240),(20,180,600,320),(20,148,920,416),(20,148,1320,644)))
@pytest.mark.parametrize('edge',('left','right'))
def test_palette_tiles_fit_scene_and_do_not_overlap(view,edge):
    c=SolidPalette(SETTINGS); c.edge=edge; c.layout(view)
    assert pygame.Rect(view).contains(c.rect)
    for rect,_ in c.targets: assert c.rect.contains(rect)
    for i,(rect,_) in enumerate(c.targets):
        assert not any(rect.colliderect(other) for other,_ in c.targets[i+1:])


@pytest.mark.parametrize('count,mode,label',((0,'points','Chưa có đỉnh'),(1,'points','Điểm'),
    (2,'points','Đoạn'),(3,'segment','Đoạn'),(3,'surface','Mặt'),(4,'hull3d','Khối'),(10,'surface','Mặt')))
def test_tip_summary_uses_observed_nodes_and_real_mesh_classification(count,mode,label):
    tips=[Tip(i//5,i,(0,0,0)) for i in range(count)]
    text=tip_summary(tips,mode)
    assert text.startswith(label) and f'{count} đầu ngón' in text
    assert f'Tay 1: {min(count,5)} | Tay 2: {max(0,count-5)}' in text


@pytest.mark.parametrize('size',((920,416),(1320,644)))
@pytest.mark.parametrize('zoom',(.55,1.,1.8))
def test_analytic_tip_projection_matches_independent_homogeneous_matrix(size,zoom):
    w,h=size; center=np.array((.2,-.1,.3)); fit=1.5
    a,b=.3,.6
    rx=np.array(((1,0,0),(0,math.cos(a),-math.sin(a)),(0,math.sin(a),math.cos(a))))
    ry=np.array(((math.cos(b),0,math.sin(b)),(0,1,0),(-math.sin(b),0,math.cos(b))))
    rotation=rx@ry; f=1/math.tan(math.radians(44)/2)
    projection=np.array(((f/(w/h),0,0,0),(0,f,0,0),(0,0,-100.1/99.9,-20/99.9),(0,0,-1,0)))
    model=np.eye(4); model[:3,:3]=rotation*fit; model[:3,3]=-rotation@center*fit+(0,-.1,-9/zoom)
    for p in ((0,0,0),(.5,.4,-.2),(-.7,-.2,.5)):
        clip=projection@model@np.array((*p,1)); ndc=clip[:3]/clip[3]
        expected=(20+(ndc[0]+1)*w/2,148+(1-ndc[1])*h/2)
        assert project_live_tip(p,(20,148,w,h),rotation,center,fit,zoom)==pytest.approx(expected)
    assert project_live_tip((100,0,0),(20,148,w,h),rotation,center,fit,zoom) is None


def test_switching_basic_tabs_keeps_object_pose_but_cancels_pending_input():
    r=SubmissionRenderer(SETTINGS); r.grab.pose.position[:]=(.2,.3,.4)
    r.dragging=True; r.solid_palette.hands={0:sample(.1)}; r.solid_palette.transition(True)
    r.enter_basic('tips')
    assert not r.dragging and not r.solid_palette.open and not r.grab.slots
    r.enter_basic('solid')
    np.testing.assert_allclose(r.grab.pose.position,(.2,.3,.4))
    assert not r.solid_palette.grab_hands((sample(.1),),4/3)


def test_dismissing_menu_consumes_both_hands_and_mouse_does_not_grab_through(monkeypatch):
    r=SubmissionRenderer(SETTINGS); c=r.solid_palette
    c.hands={0:sample(.1),1:sample(.1,slot=1)}; c.layout(VIEW); c.transition(True)
    event=SimpleNamespace(type=pygame.MOUSEBUTTONDOWN,button=1,
                         pos=next(rect.center for rect,a in c.targets if a=='octa'))
    monkeypatch.setattr(pygame.event,'get',lambda:[event])
    r.events()
    assert r.kind=='octa' and not c.open and not r.dragging
    assert c.blocked=={0,1} and not c.grab_hands(tuple(c.hands.values()),4/3)


@pytest.mark.parametrize('reason',('raw_short','filtered_nan','raw_nan'))
def test_invalid_geometry_cannot_advance_menu_selection(reason):
    c=SolidPalette(SETTINGS); summon(c)
    h=at(c,'sphere')
    if reason=='raw_short': h=replace(h,raw_landmarks=h.landmarks[:-1])
    else:
        # The public Landmark contract rejects NaN at construction. Deliberately
        # malformed external objects exercise this extra presentation guard.
        invalid=tuple(SimpleNamespace(index=p.index,x=float('nan'),y=p.y,z=p.z) if p.index==8 else p for p in h.landmarks)
        h=replace(h,**({'landmarks':invalid} if reason=='filtered_nan' else {'raw_landmarks':invalid}))
    for t in np.arange(1.72,3,.04): assert c.update((h,),float(t),4/3,VIEW) is None
    assert c.open and not c.dwell.states and not c.pointers


@pytest.mark.parametrize('camera',(False,True))
def test_basic_static_controls_do_not_rasterize_on_camera_frames(monkeypatch,camera):
    import submission.stem_ui.renderer as module
    r=SubmissionRenderer(SETTINGS); r.camera_visible=camera
    r.clock=SimpleNamespace(tick=lambda *a:None); r.solid_lists={'cube':1}
    overlays=[]
    monkeypatch.setattr(r,'_draw_ui',lambda *a:overlays.append(1) or 'surface')
    monkeypatch.setattr(r,'_overlay',lambda *a:None)
    monkeypatch.setattr(r,'_floor',lambda:None); monkeypatch.setattr(r,'_shadow',lambda *a:None)
    for name in dir(module.gl):
        if name.startswith('gl') and callable(getattr(module.gl,name)):
            monkeypatch.setattr(module.gl,name,lambda *a:None)
    monkeypatch.setattr(module.glu,'gluPerspective',lambda *a:None)
    monkeypatch.setattr(pygame.display,'flip',lambda:None)
    monkeypatch.setattr(pygame.mouse,'get_pos',lambda:(0,0))
    image=np.zeros((480,640,3),dtype=np.uint8)
    for i in range(15):
        monkeypatch.setattr(module.time,'monotonic',lambda:100+i*.05)
        r.draw(Snapshot(i,1+i*.05,100+i*.05,image,(),None,None),'On',active=True,run_id='qa')
    assert len(overlays)==1
    if camera:
        assert ('basic-preview',) in r.sprites.items
        assert r.sprites.versions[('basic-preview',)][1]==14
    r.help_visible=False; r.draw(None,'Off')
    assert len(overlays)==2


def test_small_dynamic_sprite_reuses_texture_until_size_or_context_changes(monkeypatch):
    from submission.stem_ui.screen_sprites import ScreenSprites
    from OpenGL import GL as gl
    calls=[]
    for name in dir(gl):
        if name.startswith('gl') and callable(getattr(gl,name)): monkeypatch.setattr(gl,name,lambda *a:None)
    monkeypatch.setattr(gl,'glGenTextures',lambda *a:17)
    monkeypatch.setattr(gl,'glTexImage2D',lambda *a:calls.append(('allocate',a[3:5])))
    monkeypatch.setattr(gl,'glTexSubImage2D',lambda *a:calls.append(('update',a[4:6])))
    monkeypatch.setattr(gl,'glDeleteTextures',lambda ids:calls.append(('delete',tuple(ids))))
    sprites=ScreenSprites(2); surface=pygame.Surface((100,75),pygame.SRCALPHA)
    sprites.draw('preview',surface,(0,0),version=1)
    sprites.draw('preview',surface,(20,20),version=1)
    sprites.draw('preview',surface,(20,20),version=2)
    assert calls==[('allocate',(100,75)),('update',(100,75))]
    sprites.draw('preview',pygame.Surface((80,60),pygame.SRCALPHA),(0,0),version=3)
    assert calls[-2:]==[('delete',(17,)),('allocate',(80,60))]
    sprites.close(); assert not sprites.items and not sprites.versions

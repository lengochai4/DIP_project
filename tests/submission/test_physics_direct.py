"""Direct model edits and coordinated view changes, without a physical camera."""
import copy
import math
import numpy as np
import pytest
from test_stem_ui import SETTINGS
from test_point_pinch import sample
from test_physics_view import view
from submission.stem_ui.physics_view import BodyTarget


def grab(v,action='drag:body',slot=0,start=1.,nx=.65,ny=.5):
    v.hit=lambda p:action
    for t in (start,start+.05):
        v.input.update([sample(.1,slot=slot,nx=nx,ny=ny)],t,v.space.aspect)
        v.input.advance(1/60)
    assert v.input.claims[slot].target==action


def move(v,slot=0,start=1.1,nx=.71,ny=.5):
    for i in range(5):
        v.input.update([sample(.1,slot=slot,nx=nx,ny=ny)],start+i*.03,v.space.aspect)
        v.input.advance(1/60)


def open_hand(v,start=1.3,nx=.75,ny=.5):
    for i,ratio in enumerate((.364,.38,.4,1.)):
        v.input.update([sample(ratio,nx=nx,ny=ny)],start+i*.03,v.space.aspect)
        v.input.advance(1/60)


@pytest.mark.parametrize('lab,action',(('spring','drag:body'),('pendulum','drag:body'),('projectile','drag:launch')))
def test_observed_meaningful_release_starts_only_selected_dynamic_models(lab,action):
    v=view(); v.command('lab:'+lab); v.setup_projection()
    before=v.model.params.copy(); grab(v,action); move(v)
    assert v.model.params!=before and not v.model.running
    open_hand(v)
    assert not v.input.claims and v.model.running and len(v.undo)==1
    assert v.model.time==0  # No time or hand-derived impulse is injected.


@pytest.mark.parametrize('cause',('loss','generation','timestamp','suspend','cancel','small','disabled','slider'))
def test_automatic_start_requires_uninterrupted_deliberate_eligible_release(cause):
    v=view(); v.command('lab:spring'); v.setup_projection()
    grab(v,'drag:param:displacement' if cause=='slider' else 'drag:body')
    if cause!='small': move(v)
    if cause=='loss':
        v.input.update([],1.25,v.space.aspect)
        v.input.update([sample(.1,nx=.71)],1.28,v.space.aspect)
        open_hand(v,start=1.32)
    elif cause=='generation': v.input.update([sample(1,generation=9)],1.3,v.space.aspect)
    elif cause=='timestamp': v.input.update([],float('nan'),v.space.aspect)
    elif cause=='suspend': v.suspend()
    elif cause=='cancel': v.command('cancel_edit')
    else:
        if cause=='disabled': v.command('release_mode')
        open_hand(v)
    assert not v.model.running


def test_undo_restores_actual_running_state_measurements_and_independent_reference_paused():
    v=view(); v.command('lab:spring')
    for _ in range(30): v.model.step()
    v.model.keep_reference(); reference=copy.deepcopy(v.model.reference)
    before=v.model.snapshot(); original_q=list(v.model.q)
    grab(v); move(v); open_hand(v)
    assert v.model.running
    v.command('undo_edit')
    assert not v.model.running and v.model.q==original_q
    assert v.model.snapshot()==before
    assert v.model.reference==reference and not v.undo


def test_cancel_held_edit_restores_checkpoint_and_requires_open_before_regrab():
    v=view(); v.command('lab:spring'); v.setup_projection(); before=v.model.configuration()
    grab(v); move(v); v.command('cancel_edit')
    assert v.model.configuration()==before and not v.undo and not v.input.claims
    for t in (1.3,1.35,1.4): v.input.update([sample(.1)],t,v.space.aspect)
    assert not v.input.claims
    v.input.update([sample(1)],1.45,v.space.aspect)
    for t in (1.5,1.55): v.input.update([sample(.1)],t,v.space.aspect)
    assert v.input.claims


def test_cancel_is_selectable_by_free_second_hand_while_first_edits():
    v=view(); v.command('lab:spring'); before=v.model.configuration(); grab(v); move(v)
    v.hit=lambda p:'cancel_edit'
    for i,ratio in enumerate([1.]*9+[.4,.1,.1,.1]):
        v.input.update([sample(.1,nx=.71),sample(ratio,slot=1,nx=.25)],1.25+i*.04,v.space.aspect)
    assert not v.input.claims and v.model.configuration()==before and not v.model.running


def test_mouse_release_and_wheel_cancellation_share_safe_lifecycle():
    v=view(); v.command('lab:spring'); v.hit=lambda p:'drag:body'; x,y,w,h=v.content
    v.mouse('down',(x+.6*w,y+.5*h)); v.mouse('move',(x+.7*w,y+.5*h))
    v.wheel(1,(x+.8*w,y+.5*h)); v.mouse('up',(x+.7*w,y+.5*h))
    assert v.edit_session is None and not v.model.running and len(v.undo)==1
    v.mouse('down',(x+.7*w,y+.5*h)); v.mouse('move',(x+.65*w,y+.5*h)); v.mouse('up',(x+.65*w,y+.5*h))
    assert v.model.running


def test_two_parameter_edits_share_one_undo_and_slider_release_does_not_launch():
    v=view(); v.command('lab:pendulum'); before=v.model.configuration()
    v.begin_edit('drag:body'); v.model.set_parameter('angle',45)
    v.begin_edit('drag:length'); v.model.set_parameter('length',2)
    v.edit_session['travel']=.1
    v.end_edit('drag:body',True,True); v.end_edit('drag:length',True,False)
    assert not v.model.running and len(v.undo)==1
    v.command('undo_edit'); assert v.model.configuration()==before


def test_measurement_claim_cannot_orphan_model_transaction_or_start_it_on_release():
    v=view(); v.command('lab:spring'); before=v.model.configuration()
    v.begin_edit('drag:body'); v.model.set_parameter('displacement',.5); v.edit_session['travel']=.1
    v.end_edit('drag:body',True,True); assert v.edit_session is not None
    v.end_edit('drag:measure_a',True,False)
    assert v.edit_session is None and not v.model.running and len(v.undo)==1
    v.command('undo_edit'); assert v.model.configuration()==before


def test_undo_capacity_is_bounded_and_changing_lab_clears_previous_history():
    v=view()
    for i in range(SETTINGS['physics_undo_capacity']+5):
        v.command('inc:force' if i%2 else 'dec:force')
    assert len(v.undo)==SETTINGS['physics_undo_capacity']
    v.command('lab:pendulum'); assert not v.undo


def test_new_view_tool_consumes_its_menu_pinch_until_open_then_fresh_grab():
    v=view(); v.page='tools'; v._paint_panel()
    rect=next(r for r,a in v.targets if a=='tool:scene'); x=rect.centerx/v.content[2]; y=rect.centery/v.content[3]
    for dt,ratio in ((0,1),(.06,1),(.12,1),(.17,.4),(.22,.1),(.27,.1)):
        v.input.update([sample(ratio,nx=x,ny=y)],1+dt,v.space.aspect)
    assert v.tool=='scene'
    for t in (1.3,1.35,1.4): v.input.update([sample(.1,nx=.85,ny=.6)],t,v.space.aspect)
    assert not v.input.claims
    for t in (1.5,1.58,1.65): v.input.update([sample(1,nx=.85,ny=.6)],t,v.space.aspect)
    for t in (1.7,1.75): v.input.update([sample(.1,nx=.85,ny=.6)],t,v.space.aspect)
    assert v.input.claims[0].target=='drag:scene'


@pytest.mark.parametrize('lab',('forces','incline','collision','lever','pulley'))
def test_other_model_releases_never_start_or_change_physics_equations(lab):
    v=view(); v.command('lab:'+lab); v.setup_projection()
    action='drag:velocity1' if lab=='collision' else 'drag:body'
    grab(v,action); move(v); open_hand(v)
    assert not v.model.running
    assert v.model.catalog['model_revision']==3


def test_body_surface_pick_extends_beyond_center_handle_and_panel_still_wins():
    v=view(); v.targets=[]; v.handles=[]
    center=v.space.point(.75,.5)
    v.body_targets=[BodyTarget(center,.35,'drag:body')]
    point=(.75+.2/v.space.width,.5)
    assert math.hypot((point[0]-.75)*v.content[2],0)>v.cfg['handle_radius_px']
    assert v.hit(point)=='drag:body'
    assert v.hit((.98,.05)) is None
    v.body_targets=[BodyTarget(v.space.point(.1,.2),1.,'drag:body')]
    assert v.hit((.1,.2)) is None  # Expanded panel blocks everything behind it.


def test_rotated_box_picking_uses_faces_instead_of_empty_circumsphere_corners():
    angle=math.pi/4; rotation=np.array(((math.cos(angle),-math.sin(angle),0),(math.sin(angle),math.cos(angle),0),(0,0,1)))
    target=BodyTarget(np.zeros(3),1.,'drag:body',rotation)
    assert target.intersect(np.array((1.,1.,4.)),np.array((0.,0.,-1.))) is None
    assert target.intersect(np.array((1.,0.,4.)),np.array((0.,0.,-1.)))==pytest.approx(3.)
    assert target.intersect(np.array((1.,0.,4.)),np.array((0.,0.,1.))) is None


def test_new_parameter_handles_edit_only_their_declared_quantity():
    v=view(); v.command('lab:collision'); v.setup_projection(); initial=v.model.params.copy()
    start=(.7,.5); end=(.75,.5)
    v.drag('drag:velocity1',start,end,v.capture('drag:velocity1'))
    assert v.model.params['velocity1']>initial['velocity1']
    assert v.model.params['velocity2']==initial['velocity2']
    v.drag('drag:mass2',start,(.7,.4),v.capture('drag:mass2'))
    assert v.model.params['mass2']>initial['mass2'] and v.model.params['mass']==initial['mass']
    v.command('lab:projectile'); v.setup_projection(); target=v.model.params['target']
    v.drag('drag:target',start,end,v.capture('drag:target'))
    assert v.model.params['target']>target


def test_velocity_control_moves_continuously_through_zero_instead_of_flipping_sides():
    v=view(); v.command('lab:collision'); v.setup_projection(); position=v.world(v.body_position())
    v.model.set_parameter('velocity1',-.001); _,left=v.velocity_handle_position(1,position)
    v.model.set_parameter('velocity1',.001); _,right=v.velocity_handle_position(1,position)
    assert np.linalg.norm(left-right)<.001
    assert np.dot(right-left,v.rotation[:,0])>0


def test_two_hand_view_has_known_scale_pan_twist_and_preserves_si():
    v=view(); original=v.model.snapshot(); value=v.capture('drag:scene')
    base=np.array(((.5,.5),(.7,.5)))
    # Double span, move midpoint .05 right / .03 up.
    now=np.array(((.45,.47),(.85,.47)))
    v.drag_scene_pair(base,now,value)
    assert v.zoom==pytest.approx(min(2,v.cfg['max_scene_zoom']))
    assert v.scene_pan==pytest.approx([.05,-.03]) and v.roll==0
    v.drag_scene_pair(base,((.6,.4),(.6,.6)),value)
    assert v.roll==-SETTINGS['physics_scene_roll_limit_deg']
    v.setup_projection(); xy=np.array((.3,.7))
    assert v.to_model(v.space.project(v.world(xy)))==pytest.approx(xy)
    assert v.model.snapshot()==original
    v.command('frame'); assert v.roll==0 and v.scene_pan==pytest.approx([0,0])


def scene_hands(x1=.55,x2=.85,ratio1=.1,ratio2=.1):
    return [sample(ratio1,nx=x1,ny=.55),sample(ratio2,slot=1,nx=x2,ny=.55)]


def pose(v): return np.array([v.yaw,v.pitch,v.zoom,v.roll,*v.scene_pan])


def test_pair_join_release_and_loss_rebase_without_pose_jump_or_pending_motion():
    v=view(); v.command('tool:scene'); v.hit=lambda p:'drag:scene'
    grab(v,'drag:scene',nx=.55,ny=.55)
    move(v,nx=.58,ny=.55); before=pose(v)
    v.input.update(scene_hands(.58,.85),1.25,v.space.aspect); v.input.advance(1/60)
    before=pose(v)  # One-hand follow may continue while the second pinch arms.
    v.input.update(scene_hands(.58,.85),1.3,v.space.aspect); v.input.advance(1/60)
    assert len(v.input.claims)==2 and pose(v)==pytest.approx(before)
    for t in (1.35,1.4):
        v.input.update(scene_hands(.55,.9),t,v.space.aspect); v.input.advance(1/60)
    assert v.zoom>before[2]
    frozen=pose(v)
    v.input.update(scene_hands(.5,.95,ratio2=.5),1.43,v.space.aspect)
    for _ in range(20): v.input.advance(1/60)
    assert pose(v)==pytest.approx(frozen)
    for t in (1.46,1.49):
        v.input.update(scene_hands(.5,.95,ratio2=.5),t,v.space.aspect); v.input.advance(1/60)
    assert len(v.input.claims)==1 and pose(v)==pytest.approx(frozen)
    v.input.update([],1.52,v.space.aspect); v.input.advance(.1)
    v.input.update([sample(.1,nx=.7,ny=.55)],1.56,v.space.aspect); v.input.advance(.1)
    assert pose(v)==pytest.approx(frozen)


def test_close_or_crossed_hands_freeze_then_rebase_without_zoom_explosion():
    v=view(); v.command('tool:scene'); v.hit=lambda p:'drag:scene'
    for t in (1.,1.05):
        v.input.update(scene_hands(.6,.62),t,v.space.aspect); v.input.advance(.1)
    original=pose(v)
    for t in (1.1,1.15,1.2):
        v.input.update(scene_hands(.5,.85),t,v.space.aspect); v.input.advance(.1)
    assert v.cfg['min_scene_zoom']<=v.zoom<=v.cfg['max_scene_zoom']
    assert np.all(np.isfinite(pose(v)))
    assert abs(v.roll)<=SETTINGS['physics_scene_roll_limit_deg']
    assert v.zoom<1.1*original[2]  # Establish a usable baseline after separation.


def test_context_hints_and_release_toggle_are_available_for_all_eight_models():
    v=view()
    for lab in v.model.catalog['labs']:
        v.command('lab:'+lab); v.layout(); v.setup_projection(); v._paint_panel()
        assert v.interaction_hint()
        assert 'undo_edit' in {a for _,a in v.targets}
    v.page='tools'; v._paint_panel(); actions=set()
    for _ in range(v.tools_pages):
        v._paint_panel(); actions.update(a for _,a in v.targets); v.command('tools_next')
    assert {'tool:scene','release_mode','cancel_edit','undo_edit'}<=actions


def test_projectile_preview_matches_analytic_ground_contact_without_advancing_model():
    v=view(); v.command('lab:projectile'); v.setup_projection(); before=v.model.snapshot()
    lines=[]; v._line=lambda points,*args:lines.append(points)
    v._projectile_preview(); points=lines[0]; p=v.model.params; a=math.radians(p['angle'])
    vy=p['speed']*math.sin(a); duration=(vy+math.sqrt(vy*vy+2*p['gravity']*p['height']))/p['gravity']
    assert len(points)==SETTINGS['physics_preview_steps']
    assert points[0]==pytest.approx(v.world((0,p['height']),.02))
    assert points[-1]==pytest.approx(v.world((p['speed']*math.cos(a)*duration,0),.02))
    assert v.model.snapshot()==before


def test_moving_label_positions_do_not_rasterize_text_at_every_render_frame(monkeypatch):
    v=view(); uploads=[]; clock=[1.]
    monkeypatch.setattr('submission.stem_ui.physics_view.time.perf_counter',lambda:clock[0])
    monkeypatch.setattr('submission.stem_ui.physics_view.gl.glBindTexture',lambda *args:None)
    def upload(name,surface,key):
        uploads.append(key); v.textures[name]={'id':1,'key':key,'size':surface.get_size()}
    v._texture=upload; v._quad=lambda *args:None
    v.object_labels=[('mass',v.world((1,0)),'m=1')]; v._draw_object_labels()
    for i in range(5):
        v.object_labels=[('mass',v.world((1+i*.01,0)),'m='+str(2+i))]; v._draw_object_labels()
    assert len(uploads)==1
    clock[0]+=.1; v._draw_object_labels(); assert len(uploads)==2


@pytest.mark.parametrize('action',('frame','tool:scene','lab:pendulum','reset'))
def test_context_commands_cancel_pending_mouse_autostart(action):
    v=view(); v.command('lab:spring'); v.hit=lambda p:'drag:body'; x,y,w,h=v.content
    v.mouse('down',(x+.6*w,y+.5*h)); v.mouse('move',(x+.65*w,y+.5*h)); v.command(action)
    v.mouse('up',(x+.65*w,y+.5*h))
    assert v.edit_session is None and not v.model.running

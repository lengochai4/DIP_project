"""Projection, typed controls and compact teaching-panel accessibility."""
from types import SimpleNamespace
import math
import numpy as np
import pygame
import pytest
from test_stem_ui import SETTINGS
from submission.stem_ui.camera_space import CameraSpace
from submission.stem_ui.physics_view import PhysicsView


def view(width=960,height=600):
    pygame.font.init()
    host=SimpleNamespace(help_visible=True,screenshot=lambda path:None)
    v=PhysicsView(SETTINGS,host); v.content=(20,100,width,height)
    v.space=CameraSpace(width/height); v.layout(); v.setup_projection()
    return v


@pytest.mark.parametrize('size',((424,240),(600,320),(760,320),(920,416),(1320,644),(1880,920)))
def test_every_scenario_and_parameter_tool_are_reachable_in_compact_panels(size):
    v=view(*size)
    for lab in v.model.catalog['labs']:
        v.command('lab:'+lab); v.layout(); v.setup_projection()
        seen=set()
        for page in range(v.page_count):
            v._paint_panel(); seen|={a.split(':')[-1] for r,a in v.targets if a.startswith('drag:param:')}
            for r,a in v.targets: assert v.panel_rect.contains(r),(size,lab,a,r)
            v.command('param_next')
        assert seen==set(v.model.params)
        v.page='tools'; v._paint_panel(); actions=set()
        for page in range(v.tools_pages):
            v._paint_panel(); actions|={a for r,a in v.targets}; v.command('tools_next')
        assert {'save','load','export','keep','step','graph_next','predict:yes','predict:no'}<=actions
        assert {'panel_larger','panel_smaller','zoom_in','zoom_out','tool:orbit','tool:zoom','tool:edit'}<=actions
        v.page='lesson'; v._paint_panel(); lesson=[]
        for _ in range(v.lesson_pages):
            v._paint_panel(); lesson.extend(v.visible_lesson_lines); v.command('lesson_next')
        assert ' '.join(v.model.spec['assumptions'].split()) in ' '.join(lesson)
        v.page='adjust'; v.library=True; v._paint_panel(); found=set()
        for _ in range(8):
            v._paint_panel(); found|={a[4:] for r,a in v.targets if a.startswith('lab:')}; v.command('library_next')
        assert found==set(v.model.catalog['labs']); v.library=False


@pytest.mark.parametrize('lab',('forces','incline','projectile','collision','spring','pendulum','lever','pulley'))
def test_si_projection_round_trip_and_visual_zoom_preserve_measurement(lab):
    v=view(); v.command('lab:'+lab); v.setup_projection()
    xy=np.array((.4,.8)); point=v.space.project(v.world(xy))
    assert v.to_model(point)==pytest.approx(xy)
    original=v.model.configuration(); distance=np.linalg.norm(v.measure_points[1]-v.measure_points[0])
    v.zoom=1.7; v.setup_projection()
    assert v.to_model(v.space.project(v.world(xy)))==pytest.approx(xy)
    assert np.linalg.norm(v.measure_points[1]-v.measure_points[0])==distance
    assert v.model.configuration()==original


def test_pendulum_drag_uses_captured_angle_not_accumulating_each_frame():
    v=view(); v.command('lab:pendulum'); v.setup_projection()
    start=v.space.project(v.world(v.body_position())); value=v.capture('drag:body')
    end=(start[0]+.02,start[1]); v.drag('drag:body',start,end,value); first=v.model.params['angle']
    v.setup_projection(); v.drag('drag:body',start,end,value)
    assert v.model.params['angle']==pytest.approx(first)


def test_pulley_load_moves_up_and_rope_end_moves_down_for_lifting():
    v=view(); v.command('lab:pulley'); v.setup_projection()
    start=(.6,.6); up=(.6,.57); value=v.capture('drag:body')
    v.drag('drag:body',start,up,value); assert v.model.params['pull']>0
    v.model.reset(); v.model.set_parameter('pull',0); v.setup_projection()
    value=v.capture('drag:rope'); v.drag('drag:rope',start,(.6,.63),value)
    assert v.model.params['pull']>0


def test_panel_movement_clamps_to_view_and_compact_arrow_can_restore():
    v=view(); v.panel_offset[:]=[4,-4]; v.layout()
    assert pygame.Rect((0,0),v.content[2:]).contains(v.panel_rect)
    v.command('compact'); v.layout(); v._paint_panel()
    assert {action for r,action in v.targets}=={'restore'}
    point=v.panel_rect.center; assert v.hit((point[0]/v.content[2],point[1]/v.content[3]))=='restore'


def test_static_challenge_begins_as_an_actual_problem_and_accepts_prediction():
    v=view(); v.command('lab:lever'); v.command('challenge')
    assert not v.model.achieved and abs(v.model.metrics()['torque_net_nm'])>1
    v.command('predict:yes'); assert v.model.snapshot()['prediction']=='yes'
    v.model.set_parameter('arm2',1); assert not v.model.achieved
    v.command('predict:yes'); v.command('run'); assert v.model.achieved


def test_keyboard_run_does_not_start_simulation_while_a_handle_is_owned():
    v=view(); v.input.claims[0]=object(); v.command('run')
    assert not v.model.running


@pytest.mark.parametrize('edge,delta',(('left',(-.09,0)),('right',(1.,0)),('top',(0,-.09)),('bottom',(0,.09))))
def test_throw_panel_docks_on_correct_edge_and_restores_inside_view(edge,delta):
    v=view(); v.layout(); value=v.capture('drag:panel')
    assert v.drag('drag:panel',(.3,.3),tuple(np.array((.3,.3))+delta),value) is False
    assert v.collapsed and v.dock_edge==edge
    v.layout(); v._paint_panel()
    assert pygame.Rect((0,0),v.content[2:]).contains(v.panel_rect)
    assert v.hit((v.panel_rect.centerx/v.content[2],v.panel_rect.centery/v.content[3]))=='restore'
    v.command('restore'); v.layout()
    assert not v.collapsed and pygame.Rect((0,0),v.content[2:]).contains(v.panel_rect)


def test_near_border_drag_requires_hold_and_horizontal_header_does_not_dock(monkeypatch):
    v=view(); clock=[1.]; monkeypatch.setattr('submission.stem_ui.physics_view.time.perf_counter',lambda:clock[0])
    value=v.capture('drag:panel'); v.drag('drag:panel',(.3,.3),(.32,.3),value)
    assert not v.collapsed
    # A small excursion past the left border must persist, unlike a fast throw.
    end=(.3-(12/v.content[2]+.03),.3)
    v.drag('drag:panel',(.3,.3),end,value); assert not v.collapsed
    clock[0]+=.1; v.drag('drag:panel',(.3,.3),end,value); assert not v.collapsed
    clock[0]+=.06; v.drag('drag:panel',(.3,.3),end,value); assert v.collapsed


def test_world_edit_does_not_reframe_on_drag_or_release_and_frame_resets_angles():
    v=view(); before=(v.mid.copy(),v.scale); value=v.capture('drag:body')
    v.drag('drag:body',(.6,.5),(1.2,.5),value); v.setup_projection()
    assert v.mid==pytest.approx(before[0]) and v.scale==pytest.approx(before[1])
    v.input.release(); v.setup_projection()
    assert v.mid==pytest.approx(before[0]) and v.scale==pytest.approx(before[1])
    v.yaw=60; v.pitch=40; v.zoom=1.7; v.command('frame')
    assert v.edit_bounds is None and v.zoom==1 and v.yaw==v.cfg['default_yaw_deg'] and v.pitch==v.cfg['default_pitch_deg']


def test_orbit_zoom_remain_editable_and_preserve_physical_state():
    v=view(); before=v.model.configuration(); original=v.model.metrics(); value=v.capture('drag:orbit')
    for end in ((-2,-2),(2,2),(.7,.4)):
        v.drag('drag:orbit',(.5,.5),end,value); v.setup_projection()
        xy=np.array((.3,.7)); assert v.to_model(v.space.project(v.world(xy)))==pytest.approx(xy)
        assert abs(v.yaw)<=SETTINGS['physics_yaw_limit_deg'] and abs(v.pitch)<=SETTINGS['physics_pitch_limit_deg']
    value=v.capture('drag:zoom')
    for y in (-10,10):
        v.drag('drag:zoom',(.5,.5),(.5,y),value)
        assert v.cfg['min_scene_zoom']<=v.zoom<=v.cfg['max_scene_zoom']
    assert v.model.configuration()==before and v.model.metrics()==original


def test_panel_translation_reuses_pixels_and_moves_hit_regions(monkeypatch):
    v=view(); uploads=[]; clock=[1.]
    monkeypatch.setattr('submission.stem_ui.physics_view.time.perf_counter',lambda:clock[0])
    def upload(name,surface,key):
        uploads.append((name,surface.get_size())); v.textures[name]={'id':1}
    monkeypatch.setattr(v,'_texture',upload)
    monkeypatch.setattr('submission.stem_ui.physics_view.gl.glBindTexture',lambda *args:None)
    v._sync_panel(); targets=[(r.copy(),a) for r,a in v.targets]
    v.panel_offset[0]=.1; v.layout(); v._sync_panel()
    assert len(uploads)==1
    for (old,action),(new,now) in zip(targets,v.targets):
        assert action==now and new.x-old.x==96 and new.y==old.y
    v.model.set_parameter('mass',3); v._sync_panel(); assert len(uploads)==1
    clock[0]+=.1; v._sync_panel(); assert len(uploads)==2


def test_overlapping_handle_hit_uses_nearest_visible_center():
    v=view(); v.targets=[]; point=(.75,.5)
    v.handles=[(v.space.point(*point,0),'drag:body'),
               (v.space.point(point[0]+.015,point[1],0),'drag:force')]
    assert v.hit(point)=='drag:body'
    assert v.hit((point[0]+.015,point[1]))=='drag:force'


def test_near_parallel_or_backward_plane_edit_freezes_without_extreme_values():
    v=view(); v.yaw=90; v.pitch=0; v.setup_projection()
    assert v.to_model((.5,.5)) is None
    value=v.capture('drag:body'); original=v.model.configuration()
    v.drag('drag:body',(.5,.5),(.6,.6),value)
    assert v.model.configuration()==original
    v.yaw=0; v.setup_projection()
    projection=(np.array((0.,0.,v.space.distance+1)),v.rotation,v.mid,v.scale,v.space)
    assert v.to_model((.5,.5),projection) is None


@pytest.mark.parametrize('tool',('orbit','zoom'))
def test_view_tool_selects_camera_canvas_and_preserves_panel_controls(tool):
    v=view(); before=v.model.configuration(); v.page='tools'; v._paint_panel()
    assert {'tool:orbit','tool:zoom','tool:edit'}<={a for r,a in v.targets}
    v.command('tool:'+tool); v._paint_panel()
    assert v.hit((.85,.6))=='drag:'+tool
    rect=next(r for r,a in v.targets if a=='tool:edit')
    assert v.hit((rect.centerx/v.content[2],rect.centery/v.content[3]))=='tool:edit'
    assert v.hit((-.1,.6)) is None
    v.command('tool:edit'); assert v.tool=='edit' and v.model.configuration()==before


def test_tool_menu_pinch_does_not_become_scene_drag_until_open_and_close_again():
    from test_point_pinch import sample
    v=view(); v.page='tools'; v._paint_panel()
    rect=next(r for r,a in v.targets if a=='tool:orbit')
    x,y=rect.centerx/v.content[2],rect.centery/v.content[3]
    for delta,ratio in ((0,1),(.06,1),(.12,1),(.17,.4),(.22,.1),(.27,.1)):
        v.input.update([sample(ratio,nx=x,ny=y)],1+delta,4/3)
    assert v.tool=='orbit'
    for t in (1.3,1.35,1.4): v.input.update([sample(.1,nx=.85,ny=.6)],t,4/3)
    assert not v.input.claims
    for t in (1.5,1.58,1.65): v.input.update([sample(1,nx=.85,ny=.6)],t,4/3)
    for t in (1.7,1.75): v.input.update([sample(.1,nx=.85,ny=.6)],t,4/3)
    assert v.input.claims[0].target=='drag:orbit'
    v.input.update([sample(.1,nx=.9,ny=.65)],1.8,4/3); v.input.advance(.05)
    assert v.yaw>v.cfg['default_yaw_deg']


def test_dwell_tool_choice_stays_selected_without_toggling_on_continued_hover():
    from test_point_pinch import sample
    v=view(); v.page='tools'; v._paint_panel()
    rect=next(r for r,a in v.targets if a=='tool:zoom')
    x,y=rect.centerx/v.content[2],rect.centery/v.content[3]
    for t in np.arange(1,4,.04): v.input.update([sample(1,nx=x,ny=y)],float(t),4/3)
    assert v.tool=='zoom' and not v.input.claims


def test_incline_velocity_vector_follows_track_in_both_directions():
    v=view(); v.command('lab:incline'); v.model.params['angle']=30
    vectors=[]; v._arrow=lambda start,vector,color:vectors.append(np.array(vector))
    axis=v.rotation@np.array((math.cos(math.pi/6),math.sin(math.pi/6),0))
    for speed in (2.,-2.):
        v.model.q=[0.,speed]; vectors.clear(); v._draw_vectors(np.zeros(3))
        velocity=vectors[-2]
        assert np.cross(velocity,axis)==pytest.approx(np.zeros(3),abs=1e-12)
        assert np.dot(velocity,axis)*speed>0


def test_pendulum_force_arrows_include_tangential_drag_and_balance_acceleration():
    v=view(); v.command('lab:pendulum'); v.model.params.update(damping=.4,length=1.3,mass=1.7)
    v.model.q=[.6,-1.2,0.]; v.cfg={**v.cfg,'force_vector_max_n':1000}
    vectors=[]; v._arrow=lambda start,vector,color:vectors.append(np.array(vector))
    v._draw_vectors(np.zeros(3))
    assert len(vectors)==5  # tension, gravity, drag, velocity, total acceleration
    length=min(v.cfg['force_vector_length'],v.space.height*v.stage.h/v.content[3]*v.cfg['vector_stage_fraction'])
    force=sum(vectors[:3])*1000/length
    theta,omega=v.model.q[:2]; m=v.model.params['mass']; l=v.model.params['length']; b=.4; g=v.model.params['gravity']
    alpha=-g/l*math.sin(theta)-b*omega/(m*l*l)
    acceleration=l*np.array((alpha*math.cos(theta)-omega**2*math.sin(theta),alpha*math.sin(theta)+omega**2*math.cos(theta),0))
    assert force==pytest.approx(v.rotation@(m*acceleration))


def test_static_lever_arrows_show_upward_pivot_reaction():
    v=view(); v.command('lab:lever'); v.cfg={**v.cfg,'force_vector_max_n':1000}
    vectors=[]; v._arrow=lambda start,vector,color:vectors.append(np.array(vector))
    v._draw_vectors(v.world(v.body_position()))
    assert sum(vectors[:3])==pytest.approx(np.zeros(3),abs=1e-12)
    assert np.dot(vectors[2],v.rotation[:,1])>0


def test_physics_readouts_distinguish_scalar_components_and_ideal_periods():
    v=view(); v.command('lab:pendulum')
    assert 'tiếp tuyến' in v.measurement_label('velocity_m_s')[0]
    assert 'b=0' in v.measurement_label('period_small_s')[0]
    v.command('lab:projectile'); assert v.measurement_label('velocity_m_s')[0]=='Tốc độ'
    v.command('lab:spring'); assert 'c=0' in v.measurement_label('period_small_s')[0]


@pytest.mark.parametrize('delta,expected',(((-1.,.2),(0.,.6)),((1.,-.2),(3.,0.)),((-1.,-.2),(0.,0.))))
def test_launch_handle_projects_into_allowed_quadrant_before_computing_speed(delta,expected):
    v=view(); v.command('lab:projectile'); v.model.set_parameter('speed',0.); v.setup_projection()
    a=np.array((0.,v.model.params['height'])); b=a+delta
    start,end=v.space.project(v.world(a)),v.space.project(v.world(b))
    v.drag('drag:launch',start,end,v.capture('drag:launch'))
    angle=math.radians(v.model.params['angle']); speed=v.model.params['speed']
    assert (speed*math.cos(angle),speed*math.sin(angle))==pytest.approx(expected,abs=1e-10)

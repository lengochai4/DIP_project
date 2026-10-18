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
        assert {'panel_larger','panel_smaller','zoom_in','zoom_out'}<=actions
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

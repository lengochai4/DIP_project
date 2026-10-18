"""Presentation timing and moving labels must not introduce stepped UI work."""
from types import SimpleNamespace
import time
import numpy as np
import pytest
from test_stem_ui import SETTINGS
from submission.stem_ui.camera_space import CameraSpace
from submission.stem_ui.chemistry_view import CameraChemistryView
from submission.stem_ui.renderer import SubmissionRenderer
from submission.stem_ui.runtime import Snapshot
from submission.stem_ui.chemistry_input import Claim


def test_animation_uses_high_resolution_elapsed_time_even_when_monotonic_stands_still(monkeypatch):
    import submission.stem_ui.renderer as module
    renderer=SubmissionRenderer(SETTINGS); renderer.mode='chemistry'; elapsed=[]
    monkeypatch.setattr(module.time,'monotonic',lambda:100.)
    clock=iter((1000.,1000.008,1000.017))
    monkeypatch.setattr(module.time,'perf_counter',lambda:next(clock))
    def draw(*args):
        elapsed.append(args[-2]); return 0,0
    monkeypatch.setattr(renderer,'_draw_chemistry',draw)
    for _ in range(3): renderer.draw(None,'Camera off')
    assert elapsed==pytest.approx((0.,.008,.009))


@pytest.mark.parametrize('aspect',(.6,4/3,16/9,2.5))
def test_atom_label_projection_culls_camera_plane_and_tracks_viewport_offsets(aspect):
    view=CameraChemistryView(SETTINGS,SimpleNamespace())
    view.space=CameraSpace(aspect); view.content=(20,148,1000,round(1000/aspect))
    positions=[view.space.point(.2,.3,.2),view.space.point(.8,.7,-.3),
        view.space.point(-.1,.5),np.array((0.,0.,view.space.distance-.05)),
        np.array((0.,0.,view.space.distance+.1))]
    view.scene.atoms={i:SimpleNamespace(symbol=str(i),position=p) for i,p in enumerate(positions)}
    view._update_labels()
    assert [symbol for symbol,pos in view.labels]==['0','1']
    for (symbol,pos),(nx,ny) in zip(view.labels,((.2,.3),(.8,.7))):
        assert pos==pytest.approx((20+nx*1000+9,148+ny*view.content[3]-18),abs=1)


def test_moving_labels_and_camera_background_do_not_rasterize_static_window_ui(monkeypatch):
    import submission.stem_ui.renderer as module
    r=SubmissionRenderer(SETTINGS); r.enter_chemistry()
    r.clock=SimpleNamespace(tick=lambda *a:None); r.actual_msaa_samples=0
    r.chemistry.scene.add_template('H2O')
    updates=[]; label_draws=[]; overlays=[]
    monkeypatch.setattr(r,'_draw_ui',lambda *a:updates.append(1) or 'surface')
    monkeypatch.setattr(r,'_overlay',lambda surface:overlays.append(surface))
    monkeypatch.setattr(r.chemistry,'draw_labels',lambda:label_draws.append(1))
    def scene_draw(snapshot,*args):
        r.chemistry.labels=[('H',(100+snapshot.frame_id,200))]
    monkeypatch.setattr(r.chemistry,'draw',scene_draw)
    for name in ('glViewport','glClearColor','glClear'):
        monkeypatch.setattr(module.gl,name,lambda *a:None)
    monkeypatch.setattr(module.pygame.display,'flip',lambda:None)
    monkeypatch.setattr(module.pygame.mouse,'get_pos',lambda:(0,0))
    image=np.zeros((480,640,3),dtype=np.uint8)
    def draw(i):
        now=100+i*.05
        snap=Snapshot(i,1+i*.05,now,image,(),None,None)
        r._draw_chemistry(snap,'Camera on',True,None,'qa',0,False,'webcam',
            (20,148,1000,600),now,.05,time.perf_counter())
    for i in range(10): draw(i)
    assert len(updates)==1 and len(label_draws)==10
    assert overlays==['surface']+[None]*9
    # Actual content changes refresh immediately; optional side preview keeps
    # receiving new images rather than reusing an old camera bitmap forever.
    r.chemistry.scene.edit=True; draw(10)
    assert len(updates)==2
    r.camera_visible=True; draw(11); draw(12)
    assert len(updates)==4


def test_pending_opening_is_not_reported_as_missing_hand():
    r=SubmissionRenderer(SETTINGS); c=r.chemistry.input
    c.claims={0:Claim(0,'atom',1,paused=True)}; c.pointers={0:(.5,.5)}
    assert 'xác nhận buông' in r._chemistry_pause_message()
    c.pointers.clear()
    assert 'mất tay' in r._chemistry_pause_message()
    c.claims.clear(); c.groups={1:{'controller':SimpleNamespace(suspended=True)}}
    assert 'quá gần' in r._chemistry_pause_message()
    c.groups.clear()
    assert r._chemistry_pause_message() is None

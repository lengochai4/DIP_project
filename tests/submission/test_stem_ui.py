from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import yaml
from dip_touchless.core import CoordinateSpace, Landmark, InteractionState
from submission.stem_ui.geometry import (Tip, FingerSelection, world_position,
    preview_position, live_mesh, solid_mesh)
from submission.stem_ui.manipulation import GrabController
from submission.stem_ui.runtime import HandView, associate, convert_result

SETTINGS=yaml.safe_load((Path(__file__).resolve().parents[2]/'submission/stem_ui/settings.yaml').read_text())

def palm(x=.5,y=.5):
    p=[(x,y,0.) for _ in range(21)]
    p[0]=(x,y+.15,0.)
    for base,px in ((5,x-.12),(9,x-.04),(13,x+.04),(17,x+.12)):
        for j in range(4): p[base+j]=(px,y-j*.075,0.)
    for j,index in enumerate((1,2,3,4)):
        p[index]=(x-.04-j*.1,y+.14-j*.025,0.)
    return tuple(Landmark(i,*v,CoordinateSpace.FRAME_NORMALIZED) for i,v in enumerate(p))

def hand(slot=0,x=.5,y=.5,pinch=True,valid=True):
    state=InteractionState('test',1,1.,valid,(x,y),.2,pinch,(0.,0.),0.)
    points=list(palm(x,y))
    if pinch:
        points[4]=replace(points[4],x=points[8].x+.02,y=points[8].y)
    return HandView(slot,tuple(points),state,None)

def attach(c,hands,t=1.):
    c.update(hands,t,4/3)
    c.update(hands,t+.05,4/3)

def test_all_five_extended_fingers_and_folded_finger_release():
    selection=FingerSelection(SETTINGS)
    p=palm()
    assert selection.update(p)==(4,8,12,16,20)
    folded=list(p)
    folded[8]=replace(folded[8],x=folded[6].x+.04,y=folded[6].y+.07)
    assert 8 not in selection.update(tuple(folded))
    assert selection.update(())==()

def test_mirror_pixel_and_world_coordinates_agree_for_letterboxed_preview():
    p=Landmark(8,.25,.75,-.1,CoordinateSpace.FRAME_NORMALIZED)
    assert preview_position(p,(100,50,320,240))==(340,230)
    assert world_position(p,4/3,SETTINGS)==pytest.approx((1.25,-.9375,.4))
    settings={**SETTINGS,'mirror':False}
    assert world_position(p,4/3,settings)[0]==-1.25

def test_collinear_fingertips_do_not_make_invalid_faces():
    tips=[Tip(0,i,(float(i),0,0)) for i in range(3)]
    assert not live_mesh(tips,.5).faces

def test_live_mesh_preserves_nodes_and_extrusion_is_positive_volume():
    tips=[Tip(0,i,p) for i,p in enumerate(((0,0,0),(1,0,.1),(1,1,.2),(0,1,0),(.5,.5,.1)))]
    mesh=live_mesh(tips,.65)
    assert len(tips)==5 and len(mesh.vertices)==8
    assert min(v[2] for v in mesh.vertices)<min(t.position[2] for t in tips)
    assert all(len(face)>=3 for face in mesh.faces)

@pytest.mark.parametrize('kind',('cube','tetra','octa','sphere'))
def test_solids_have_three_dimensional_vertices_and_valid_faces(kind):
    mesh=solid_mesh(kind)
    assert np.linalg.matrix_rank(np.array(mesh.vertices)-np.mean(mesh.vertices,axis=0))==3
    assert all(0<=i<len(mesh.vertices) for face in mesh.faces for i in face)

def test_hand_association_survives_provider_order_reversal():
    previous={0:(.2,.5),1:(.8,.5)}
    a,b=SimpleNamespace(landmarks=palm(.2)),SimpleNamespace(landmarks=palm(.8))
    assignment,resets,_=associate(previous,[b,a],.25)
    assert assignment=={1:0,0:1}
    assert not resets

def test_ambiguous_crossing_neutralizes_both_slots():
    a,b=SimpleNamespace(landmarks=palm(.5)),SimpleNamespace(landmarks=palm(.5))
    _,resets,_=associate({0:(.45,.5),1:(.55,.5)},[a,b],.25)
    assert resets=={0,1}

def test_provider_conversion_never_invents_quality_and_rejects_nonfinite():
    packet=SimpleNamespace(frame_id=1,timestamp_s=1.)
    points=[SimpleNamespace(x=.5,y=.5,z=0.) for _ in range(21)]
    result=SimpleNamespace(hand_landmarks=[points],handedness=[[SimpleNamespace(category_name='Left',score=.99)]])
    observation=convert_result(result,packet)[0]
    assert observation.quality.valid is False and observation.quality.value is None
    points[4].x=float('nan')
    assert convert_result(result,packet)==[]

def test_grab_attaches_without_snap_and_releases_without_motion():
    c=GrabController(SETTINGS)
    attach(c,[hand()])
    np.testing.assert_allclose(c.pose.position,0)
    c.update([hand(x=.6)],1.1,4/3)
    c.advance(1/60)
    assert c.pose.position[0]<0
    before=c.pose.position.copy()
    c.update([],1.2,4/3)
    c.update([hand(x=.9)],1.3,4/3)
    np.testing.assert_allclose(c.pose.position,before)

def test_two_hand_grab_scales_and_neutralizes_on_single_hand_transition():
    c=GrabController(SETTINGS)
    attach(c,[hand(0,.4),hand(1,.6)])
    c.update([hand(1,.7),hand(0,.3)],1.1,4/3)
    c.advance(1/60)
    assert 1<c.pose.scale<=SETTINGS['grab_max_scale']
    before=replace(c.pose,position=c.pose.position.copy(),rotation=c.pose.rotation.copy())
    c.update([hand(1,.7)],1.2,4/3)
    assert c.pose.scale==before.scale
    np.testing.assert_allclose(c.pose.position,before.position)
    assert np.linalg.det(c.pose.rotation)==pytest.approx(1.)

def test_reacquisition_neutral_frame_does_not_grab():
    c=GrabController(SETTINGS)
    c.update([hand(valid=False)],1.,4/3)
    assert c.slots==()

def test_all_ten_fingertips_are_supported_without_adding_points():
    selections=[FingerSelection(SETTINGS),FingerSelection(SETTINGS)]
    assert sum(len(s.update(palm(x))) for s,x in zip(selections,(.3,.7)))==10

def test_two_hand_twist_rotates_and_retains_orthogonal_matrix():
    c=GrabController(SETTINGS)
    attach(c,[hand(0,.3,.5),hand(1,.7,.5)])
    c.update([hand(0,.5,.3),hand(1,.5,.7)],1.1,4/3)
    c.advance(1/60)
    assert not np.allclose(c.pose.rotation,np.eye(3))
    np.testing.assert_allclose(c.pose.rotation.T@c.pose.rotation,np.eye(3),atol=1e-10)

def test_worker_uses_validated_snapshots_and_closes_resources_on_loss(tmp_path,monkeypatch):
    import shutil
    import submission.stem_ui.runtime as runtime
    from dip_touchless.core import FramePacket,ColorSpace
    root=Path(__file__).resolve().parents[2]
    shutil.copytree(root/'config',tmp_path/'config')
    (tmp_path/'models').mkdir(); (tmp_path/'models/hand_landmarker.task').write_bytes(b'test model')
    monkeypatch.setattr(runtime,'ROOT',tmp_path)
    image=np.full((32,32,3),127,np.uint8)
    packets=[FramePacket('test',i,i/30,image,ColorSpace.BGR,'fixture') for i in range(3)]
    class Source:
        closed=False
        def __init__(self,**kwargs): self.i=0
        def open(self): pass
        def read(self):
            if self.i==3: return None
            p=packets[self.i]; self.i+=1; return p
        def close(self): Source.closed=True
    class Landmarker:
        closed=False
        def __init__(self): self.i=0
        def detect_for_video(self,image,timestamp):
            self.i+=1
            hands=[] if self.i==2 else [[SimpleNamespace(x=l.x,y=l.y,z=l.z) for l in palm(.4 if self.i==1 else .8)]]
            return SimpleNamespace(hand_landmarks=hands,handedness=[])
        def close(self): Landmarker.closed=True
    snapshots=[]
    real_snapshot=runtime.Snapshot
    def snapshot(*args):
        value=real_snapshot(*args); snapshots.append(value); return value
    monkeypatch.setattr(runtime,'Snapshot',snapshot)
    monkeypatch.setattr(runtime,'OpenCVCameraSource',Source)
    monkeypatch.setattr(runtime.mp.tasks.vision.HandLandmarker,'create_from_options',lambda options:Landmarker())
    worker=runtime.CaptureWorker(SETTINGS); worker._run()
    assert worker.error is None and worker.finished
    assert Source.closed and Landmarker.closed
    assert not snapshots[1].hands
    assert not snapshots[0].hands[0].interaction.interaction_valid
    assert not snapshots[2].hands[0].interaction.interaction_valid
    assert snapshots[2].hands[0].landmarks[0].x==.8
    assert not np.shares_memory(snapshots[0].image,image)
    assert not snapshots[0].image.flags.writeable

def test_stopping_unstarted_worker_is_safe_and_worker_cannot_start_twice(monkeypatch):
    from submission.stem_ui.runtime import CaptureWorker
    worker=CaptureWorker(SETTINGS)
    worker.stop()
    monkeypatch.setattr(worker,'_run',lambda:None)
    worker.start(); worker.thread.join()
    with pytest.raises(RuntimeError,match='already started'):
        worker.start()

"""Spatial UI invariants; no physical depth/latency claims."""
from dataclasses import replace
import math
import numpy as np
import pytest
from test_stem_ui import SETTINGS, hand, attach
from submission.stem_ui.geometry import Tip,live_mesh,solid_mesh
from submission.stem_ui.manipulation import GrabController,average_palm_tilt


def tips(points):
    return [Tip(0,i,tuple(p)) for i,p in enumerate(points)]


def test_nonplanar_tips_form_tetrahedron_without_extruded_fake_vertices():
    p=((0,0,0),(1,0,0),(0,1,0),(0,0,1))
    mesh=live_mesh(tips(p),.65)
    assert mesh.mode=='hull3d' and len(mesh.vertices)==4 and len(mesh.faces)==4
    center=np.mean(p,axis=0)
    for f in mesh.faces:
        a,b,c=(np.array(mesh.vertices[i]) for i in f)
        assert np.dot(np.cross(b-a,c-a),a-center)>0


def test_cube_coplanar_triangles_merge_into_six_closed_support_faces():
    p=[(x,y,z) for x in (-1,1) for y in (-1,1) for z in (-1,1)]
    mesh=live_mesh(tips(p),.65)
    assert mesh.mode=='hull3d' and len(mesh.faces)==6
    edges={}
    for f in mesh.faces:
        assert len(f)==4
        for a,b in zip(f,f[1:]+f[:1]):
            e=tuple(sorted((a,b))); edges[e]=edges.get(e,0)+1
    assert set(edges.values())=={2}


def test_vertical_near_planar_hand_uses_its_plane_normal_for_display_thickness():
    p=((0,0,0),(0,1,0),(0,1,1),(0,0,1))
    mesh=live_mesh(tips(p),.65)
    assert mesh.mode=='display_prism'
    top=np.array(mesh.vertices[:4]); bottom=np.array(mesh.vertices[4:])
    delta=bottom-top
    assert np.abs(delta[:,0])==pytest.approx([.65]*4)
    np.testing.assert_allclose(delta[:,1:],0,atol=1e-12)


def test_hull_keeps_interior_fingertip_as_node_without_invalid_surface():
    p=((0,0,0),(1,0,0),(0,1,0),(0,0,1),(.1,.1,.1))
    mesh=live_mesh(tips(p),.65)
    assert len(mesh.vertices)==5 and len(mesh.faces)==4
    assert all(4 not in f for f in mesh.faces)


def test_sphere_has_closed_nondegenerate_faces_including_poles():
    mesh=solid_mesh('sphere'); edges={}
    for f in mesh.faces:
        a,b,c=(np.array(mesh.vertices[i]) for i in f[:3])
        assert np.linalg.norm(np.cross(b-a,c-a))>1e-10
        for a,b in zip(f,f[1:]+f[:1]):
            e=tuple(sorted((a,b))); edges[e]=edges.get(e,0)+1
    assert set(edges.values())=={2}


def tilted(h,angle):
    # Isotropic image-x units; tilt around the screen horizontal axis.
    c,s=math.cos(angle),math.sin(angle)
    out=[]
    for l in h.landmarks:
        y=(l.y-.5)/(4/3)
        out.append(replace(l,y=.5+(c*y-s*l.z)*(4/3),z=s*y+c*l.z))
    return replace(h,landmarks=tuple(out))


def test_two_hand_palm_tilt_rotates_out_of_screen_plane():
    c=GrabController(SETTINGS); attach(c,[hand(0,.3),hand(1,.7)])
    c.update([tilted(hand(0,.3),.5),tilted(hand(1,.7),.5)],1.15,4/3)
    assert abs(c.target.rotation[2,1])>.1
    np.testing.assert_allclose(c.target.rotation.T@c.target.rotation,np.eye(3),atol=1e-12)
    assert c.target.scale==pytest.approx(1.)


def test_average_palm_roll_is_reserved_for_baseline_twist():
    theta=.5; c,s=math.cos(theta),math.sin(theta)
    roll=np.array(((c,-s,0),(s,c,0),(0,0,1)))
    np.testing.assert_allclose(average_palm_tilt([roll,roll],[np.eye(3)]*2),np.eye(3),atol=1e-12)


def test_explicit_push_pull_changes_display_depth_without_changing_scale():
    c=GrabController(SETTINGS); c.set_scale_mode('depth'); attach(c,[hand()])
    h=hand()
    bigger=replace(h,landmarks=tuple(replace(l,x=.5+1.5*(l.x-.5),y=.5+1.5*(l.y-.5)) for l in h.landmarks))
    c.update([bigger],1.1,4/3)
    assert c.target.position[2]==pytest.approx(math.log(1.5)*SETTINGS['depth_translation_gain'])
    assert c.target.scale==1
    smaller=replace(h,landmarks=tuple(replace(l,x=.5+.5*(l.x-.5),y=.5+.5*(l.y-.5)) for l in h.landmarks))
    c.update([smaller],1.2,4/3)
    assert c.target.position[2]<0


def test_default_mode_keeps_depth_neutral_and_fast_motion_response_bounded():
    c=GrabController(SETTINGS); attach(c,[hand()])
    c.update([hand(x=.9)],1.1,4/3)
    assert c.target.position[2]==0
    assert SETTINGS['pose_response_hz']<c.response[0]<=SETTINGS['display_response_max_hz']
    c.advance(.1)
    assert np.linalg.norm(c.pose.position)<=np.linalg.norm(c.target.position)


def test_push_pull_repeated_attachment_cannot_pass_scene_depth_limit():
    c=GrabController(SETTINGS); c.set_scale_mode('depth')
    c.pose.position[2]=SETTINGS['depth_translation_limit']-.1
    attach(c,[hand()])
    h=hand()
    bigger=replace(h,landmarks=tuple(replace(l,x=.5+1.5*(l.x-.5),y=.5+1.5*(l.y-.5)) for l in h.landmarks))
    c.update([bigger],1.1,4/3)
    assert c.target.position[2]==SETTINGS['depth_translation_limit']


def test_orientation_depth_smoothing_does_not_modify_input_landmarks():
    c=GrabController(SETTINGS); attach(c,[hand()])
    h=tilted(hand(),.5); before=tuple(l.z for l in h.landmarks)
    c.update([h],1.1,4/3)
    assert tuple(l.z for l in h.landmarks)==before
    assert not np.allclose(c.orientation_z[(0,0)],before)


def test_ui_mode_cycle_reaches_push_pull_and_returns_to_default():
    from submission.stem_ui.renderer import SubmissionRenderer
    r=SubmissionRenderer(SETTINGS)
    modes=[]
    for _ in range(4):
        r.cycle_scale_mode(); modes.append(r.grab.scale_mode)
    assert modes==['stretch','distance','depth','uniform']

"""Regression cases for reported release jitter and missing size operations."""
from dataclasses import replace
from types import SimpleNamespace
import math
import numpy as np
import pytest
from test_stem_ui import SETTINGS, hand, attach
from submission.stem_ui.manipulation import GrabController, pinch_ratio, slerp_rotation


def test_brief_open_ratio_flicker_does_not_drop_grab():
    c=GrabController(SETTINGS); attach(c,[hand()])
    c.update([hand(pinch=False)],1.08,4/3)
    assert c.slots==(0,)
    c.update([hand()],1.12,4/3)
    assert c.slots==(0,) and c.grips[0].held


def test_confirmed_release_stops_pose_without_post_release_drift():
    c=GrabController(SETTINGS); attach(c,[hand()])
    c.update([hand(x=.7)],1.1,4/3); c.advance(.016)
    c.update([hand(x=.7,pinch=False)],1.12,4/3)
    c.update([hand(x=.7,pinch=False)],1.23,4/3)
    before=c.pose.copy()
    for _ in range(60): c.advance(1/60)
    assert not c.slots
    np.testing.assert_allclose(c.pose.position,before.position)


def test_opening_fingers_cannot_kick_object_during_release_confirmation():
    c=GrabController(SETTINGS); attach(c,[hand()])
    c.update([hand(x=.6)],1.1,4/3); c.advance(.016)
    before=c.pose.position.copy()
    c.update([hand(x=.9,pinch=False)],1.12,4/3); c.advance(.03)
    assert c.suspended
    np.testing.assert_allclose(c.pose.position,before)


def test_short_tracking_dropout_freezes_and_recovers_without_snap():
    c=GrabController(SETTINGS); attach(c,[hand()])
    c.update([hand(x=.6)],1.1,4/3); c.advance(.016)
    before=c.pose.copy()
    c.update([],1.13,4/3)
    c.advance(.1)
    assert c.suspended and c.slots==(0,)
    np.testing.assert_allclose(c.pose.position,before.position)
    c.update([hand(x=.8)],1.18,4/3); c.advance(.016)
    assert not c.suspended
    np.testing.assert_allclose(c.pose.position,before.position)


def test_long_loss_expires_hold_and_does_not_apply_old_anchor():
    c=GrabController(SETTINGS); attach(c,[hand()])
    c.update([],1.4,4/3)
    assert not c.slots
    c.update([hand(x=.9)],1.5,4/3)
    assert not c.slots
    c.update([hand(x=.9)],1.55,4/3)
    np.testing.assert_allclose(c.target.position,0)


def test_identity_generation_replacement_cannot_inherit_grab():
    c=GrabController(SETTINGS); attach(c,[hand()])
    changed=replace(hand(x=.9),generation=1)
    c.update([changed],1.1,4/3)
    assert not c.slots and not c.grips[0].held
    c.update([changed],1.15,4/3)
    np.testing.assert_allclose(c.target.position,c.pose.position)


def test_a_lost_second_hand_does_not_immediately_change_manipulation():
    c=GrabController(SETTINGS); attach(c,[hand(0,.3),hand(1,.7)])
    c.update([hand(0,.2)],1.1,4/3)
    assert c.suspended and c.slots==(0,1)
    c.update([hand(0,.2)],1.4,4/3)
    assert not c.suspended and c.slots==(0,)
    np.testing.assert_allclose(c.target.position,c.pose.position)


def test_two_hand_uniform_size_both_enlarges_and_shrinks():
    c=GrabController(SETTINGS); attach(c,[hand(0,.4),hand(1,.6)])
    c.update([hand(0,.2),hand(1,.8)],1.1,4/3)
    assert c.target.scale==pytest.approx(3.)
    c.update([hand(0,.45),hand(1,.55)],1.2,4/3)
    assert c.target.scale==pytest.approx(.5)


def test_two_hand_stretch_changes_one_axis_and_preserves_uniform_scale():
    c=GrabController(SETTINGS); c.set_scale_mode('stretch')
    attach(c,[hand(0,.4),hand(1,.6)])
    c.update([hand(0,.3),hand(1,.7)],1.1,4/3)
    assert c.target.scale==1.
    np.testing.assert_allclose(c.target.stretch,(2,1,1))
    c.advance(.016)
    assert c.pose.stretch[0]>1 and c.pose.stretch[1]==1


def test_one_hand_apparent_size_mode_works_without_second_hand():
    c=GrabController(SETTINGS); c.set_scale_mode('distance'); attach(c,[hand()])
    h=hand()
    enlarged=replace(h,landmarks=tuple(replace(l,x=.5+(l.x-.5)*1.5,y=.5+(l.y-.5)*1.5) for l in h.landmarks))
    c.update([enlarged],1.1,4/3)
    assert c.target.scale==pytest.approx(1.5)


def test_uniform_mode_does_not_scale_single_hand_while_rotating():
    c=GrabController(SETTINGS); attach(c,[hand()])
    h=hand()
    bigger=replace(h,landmarks=tuple(replace(l,x=.5+(l.x-.5)*1.3) for l in h.landmarks))
    c.update([bigger],1.1,4/3)
    assert c.target.scale==1.


def test_pose_follows_between_camera_updates_and_is_frame_rate_independent():
    results=[]
    for rate in (30,60,144):
        c=GrabController(SETTINGS); attach(c,[hand()])
        c.update([hand(x=.7)],1.1,4/3)
        for _ in range(rate): c.advance(1/rate)
        results.append(c.pose.position.copy())
    for p in results[1:]: np.testing.assert_allclose(p,results[0],atol=1e-10)
    c=GrabController(SETTINGS); attach(c,[hand()]); c.update([hand(x=.7)],1.1,4/3)
    c.advance(1/60); first=c.pose.position.copy(); c.advance(1/60)
    assert np.linalg.norm(c.pose.position)>np.linalg.norm(first)


def test_rotation_slerp_handles_180_degree_without_svd_flip():
    end=np.diag((-1.,-1.,1.))
    mid=slerp_rotation(np.eye(3),end,.5)
    np.testing.assert_allclose(mid.T@mid,np.eye(3),atol=1e-12)
    assert np.linalg.det(mid)==pytest.approx(1.)
    assert np.trace(mid)==pytest.approx(1.)


def test_screen_plane_translation_follows_view_after_camera_orbit():
    angle=math.pi/4
    camera=np.array(((math.cos(angle),0,math.sin(angle)),(0,1,0),(-math.sin(angle),0,math.cos(angle))))
    c=GrabController(SETTINGS)
    c.update([hand()],1.,4/3,camera); c.update([hand()],1.05,4/3,camera)
    c.update([hand(x=.6)],1.1,4/3,camera)
    screen=camera@c.target.position
    assert screen[0]<0 and abs(screen[2])<1e-12


def test_sideways_palm_denominator_does_not_force_false_release():
    h=hand(); points=list(h.landmarks)
    points[17]=replace(points[17],x=points[5].x+.001,y=points[5].y)
    assert pinch_ratio(replace(h,landmarks=tuple(points)),4/3)<SETTINGS['grip_release_ratio']

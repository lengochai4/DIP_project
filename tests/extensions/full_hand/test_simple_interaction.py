"""Application finger-count semantics; synthetic, not physical validation."""

from dataclasses import replace, asdict
from types import SimpleNamespace as NS
from pathlib import Path
import pytest
from dip_touchless.core import TrackingStatus
from extensions.stem3d.full_hand import extract_hand_geometry
from extensions.stem3d.full_hand.contracts import Finger
from extensions.stem3d.full_hand.pose_contracts import FingerState as F
from extensions.stem3d.product.simple_interaction import SimpleHandControls, practical_pose
from extensions.stem3d.product.settings import InputMode, UserSettings, load_application_profile
from extensions.stem3d.ui.spatial_panel import SpatialPanelLayout, PanelButton
from extensions.stem3d.ui.layout import Rect
from test_geometry import _fixture


def observation(pose="OPEN", thumb=F.INTERMEDIATE):
    states = {f: F.EXTENDED for f in Finger}
    states[Finger.THUMB] = thumb
    if pose == "POINT":
        states.update({f:F.FLEXED for f in (Finger.MIDDLE, Finger.RING, Finger.PINKY)})
    if pose == "UNKNOWN": states[Finger.RING] = F.INTERMEDIATE
    return NS(fingers=tuple(NS(finger=f, state=s) for f,s in states.items()))


def controls():
    return SimpleHandControls(load_application_profile(Path("config/extensions/application.yaml"))[0])


def tick(m, i, pose="OPEN", *, dx=0., status=TrackingStatus.VALID, focus="SCENE", context=(),
         panel=None, mirror=False, stale=False):
    frame, fg = _fixture(transform=lambda x,y:(x+dx,y))
    fg = replace(fg, frame_id=i, timestamp_s=i*.1)
    frame = replace(frame, frame_id=i, timestamp_s=i*.1, status=status)
    full = NS(analysis_valid=True, hand=extract_hand_geometry(frame,fg),
              frame_geometry=replace(fg,frame_id=99) if stale else fg, pose=observation(pose))
    return m.update(frame, full, settings=UserSettings(InputMode.SIMPLE,mirror=mirror),
                    focus=focus,context=context,panel=panel)


@pytest.mark.parametrize("thumb", list(F))
def test_practical_finger_counts_do_not_require_thumb_stretch_or_contact(thumb):
    assert practical_pose(observation("OPEN",thumb)) == "OPEN"
    assert practical_pose(observation("POINT",thumb)) == "POINT"
    assert practical_pose(observation("UNKNOWN",thumb)) == "UNKNOWN"


def test_point_dwell_rotation_first_anchor_zero_and_open_stops_rotation():
    m = controls()
    for i in range(3): assert tick(m,i,"POINT").rotation_delta == (0.,0.)
    assert tick(m,3,"POINT").rotation_delta == (0.,0.)
    out = tick(m,4,"POINT",dx=.04)
    assert out.rotation_delta[0] > 0 and out.scale_delta == 0 and not out.pinch_active
    assert tick(m,5,"OPEN",dx=.08).rotation_delta == (0.,0.)
    assert not tick(m,6,"UNKNOWN").interaction_valid


def test_open_palm_requests_menu_once_and_close_does_not_reopen_until_fresh_gesture():
    m = controls()
    requests = []
    for i in range(15):
        tick(m,i)
        requests.append(m.feedback.open_panel)
    assert sum(requests) == 1
    for i in range(15,25):
        tick(m,i,focus="UI")
        assert not m.feedback.open_panel
    for i in range(25,35):
        tick(m,i)
        assert not m.feedback.open_panel
    tick(m,35,"POINT")
    for i in range(36,47):
        tick(m,i)
        requests.append(m.feedback.open_panel)
    assert sum(requests) == 2


def test_hover_selection_is_ui_only_once_until_leave_and_survives_scene_context_change():
    panel = SpatialPanelLayout(Rect(0,0,100,100), (
        PanelButton("scene:a","A",Rect(0,0,100,100)),))
    m = controls()
    pulses = []
    for i in range(25):
        out = tick(m,i,focus="UI",panel=panel,dx=.05 if i >= 5 else 0.)
        pulses.append(out.pinch_active)
        assert out.rotation_delta == (0.,0.) and out.scale_delta == 0
    assert sum(pulses) == 1
    for i in range(25,45):
        assert not tick(m,i,focus="UI",panel=panel,context=("new-scene",),dx=.05).pinch_active
    tick(m,45,"UNKNOWN",focus="UI",panel=panel)
    for i in range(46,69): pulses.append(tick(m,i,focus="UI",panel=panel,dx=.05 if i >= 51 else 0.).pinch_active)
    assert sum(pulses) == 2


def test_opening_menu_does_not_select_button_under_stationary_hand():
    panel = SpatialPanelLayout(Rect(0,0,100,100),(PanelButton("reset","Reset",Rect(0,0,100,100)),))
    m = controls()
    for i in range(60):
        assert not tick(m,i,focus="UI",panel=panel).pinch_active
        assert m.feedback.hover_progress == 0.
    assert not m.feedback.navigation_armed


@pytest.mark.parametrize("status", [TrackingStatus.NO_HAND,TrackingStatus.REACQUIRED,
                                   TrackingStatus.TEMPORARY_LOSS,TrackingStatus.INVALID])
def test_loss_reacquisition_revoke_and_require_new_dwell(status):
    m = controls()
    for i in range(5): tick(m,i,"POINT")
    assert not tick(m,5,"POINT",status=status).interaction_valid
    assert not tick(m,6,"POINT",dx=.2).interaction_valid
    assert tick(m,9,"POINT",dx=.2).rotation_delta == (0.,0.)


@pytest.mark.parametrize("bad", ["duplicate","out-of-order","gap","stale"])
def test_bad_identity_is_neutral(bad):
    m = controls()
    for i in range(5): tick(m,i,"POINT")
    i = {"duplicate":4,"out-of-order":3,"gap":20,"stale":5}[bad]
    out = tick(m,i,"POINT",dx=.2,stale=bad=="stale")
    assert not out.interaction_valid and out.rotation_delta == (0.,0.)


def test_mirror_changes_pointer_and_rotation_together_and_replay_is_deterministic():
    def replay(mirror):
        m = controls()
        return tuple(tick(m,i,"POINT",dx=i*.01,mirror=mirror) for i in range(8))
    a,b = replay(False),replay(True)
    assert a == replay(False)
    assert a[-1].pointer_xy[0] == pytest.approx(1.-b[-1].pointer_xy[0])
    assert a[-1].rotation_delta[0] == -b[-1].rotation_delta[0]


def test_composition_simple_has_no_calibration_dependency_and_pairs_exclude_ui(tmp_path):
    from test_application_product import composition, dashboard
    from test_observe import _run, _execute
    from test_two_hand_product import tracker, frame as pair_frame
    observed = _run(True)
    _execute(observed)
    d = dashboard(tmp_path,UserSettings(InputMode.SIMPLE,two_hand=True))
    c,d,received,_ = composition(tmp_path,observed,d)
    c.two_hand_provider = NS(process=lambda packet: pair_frame(0)[1],close=lambda:None)
    c.two_hand_association = tracker()
    for packet,frame,legacy in zip(observed.source.packets,observed.logger.tracking,observed.received):
        c.observer.capture(packet)
        c.consume(packet,frame,legacy)
    assert c.session.reference is None
    assert all(not v.pinch_active and v.rotation_delta == (0.,0.) for v in received)
    assert c.intent_journal.counts["legacy_parity_mismatches"] == 0
    c.close()

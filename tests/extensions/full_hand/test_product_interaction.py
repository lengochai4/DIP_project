from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from dip_touchless.core import InteractionState, TrackingStatus
from extensions.stem3d.full_hand import extract_hand_geometry, HandPose
from extensions.stem3d.full_hand.intent_temporal import IntentPinchState as S
from extensions.stem3d.product.settings import (
    InputMode, UserSettings, load_application_profile, save_settings, load_settings,
)
from extensions.stem3d.product.interaction import FullHandCommandMapper, response
from test_geometry import _fixture

PROFILE = Path("config/extensions/application.yaml")


def tick(mapper, i, *, pose=HandPose.POINT, state=S.RELEASED, dx=0., dy=0.,
         settings=UserSettings(InputMode.FULL_HAND), focus="SCENE", status=TrackingStatus.VALID,
         ref=True, context=(), stable=None):
    frame, fg = _fixture(transform=lambda x, y: (x+dx, y+dy))
    fg = replace(fg, frame_id=i, timestamp_s=i*.1)
    frame = replace(frame, frame_id=i, timestamp_s=i*.1, status=status)
    hand = extract_hand_geometry(frame, fg)
    full = NS(analysis_valid=hand.valid, hand=hand, frame_geometry=fg,
              pose=NS(pose=pose), temporal=NS(stable_pose=stable or pose))
    intent = NS(reference=NS(valid=ref, reference_id="r"), observation=NS(geometry_valid=hand.valid),
                temporal=NS(state=state, armed=state is not S.UNKNOWN,
                            active_evidence=state in (S.PINCH_ACTIVE, S.HOLD)))
    legacy = InteractionState(frame.run_id, i, i*.1, status is TrackingStatus.VALID,
                              (.2, .4), .3, False, (.01, .02), .02)
    out = mapper.update(frame, legacy, full, intent, settings=settings, focus=focus, context=context)
    return out, legacy


def mapper():
    return FullHandCommandMapper(load_application_profile(PROFILE)[0])


@pytest.mark.parametrize("mode", [InputMode.LEGACY, InputMode.OBSERVE])
@pytest.mark.parametrize("status", list(TrackingStatus))
def test_exact_legacy_field_parity_for_every_status(mode, status):
    out, legacy = tick(mapper(), 1, settings=UserSettings(mode), status=status)
    assert out is legacy and asdict(out) == asdict(legacy)


def test_point_rotation_and_ui_exclusion():
    m = mapper()
    assert tick(m, 1)[0].rotation_delta == (0., 0.)
    out = tick(m, 2, dx=.05)[0]
    assert out.rotation_delta[0] > 0 and out.scale_delta == 0 and not out.pinch_active
    assert tick(m, 3, dx=.1, focus="UI")[0].rotation_delta == (0., 0.)
    assert tick(m, 4, dx=.2, focus="UI")[0].rotation_delta == (0., 0.)


def test_pinch_scale_hold_release_and_unknown_neutral():
    m = mapper()
    tick(m, 1)
    entered = tick(m, 2, state=S.PINCH_ACTIVE)[0]
    assert entered.pinch_active and entered.scale_delta == 0
    held = tick(m, 3, state=S.HOLD, dy=-.04)[0]
    assert held.pinch_active and held.scale_delta > 0 and held.rotation_delta == (0., 0.)
    lost = tick(m, 4, state=S.UNKNOWN)[0]
    assert not lost.interaction_valid and not lost.pinch_active and lost.scale_delta == 0
    assert not tick(m, 5, state=S.HOLD)[0].pinch_active
    tick(m, 6)
    assert tick(m, 7, state=S.PINCH_ACTIVE)[0].pinch_active


def test_focus_and_scene_switch_during_hold_require_release():
    m = mapper()
    tick(m, 1)
    tick(m, 2, state=S.PINCH_ACTIVE)
    assert not tick(m, 3, state=S.HOLD, focus="UI")[0].pinch_active
    assert not tick(m, 4, state=S.HOLD, focus="UI")[0].pinch_active
    tick(m, 5, focus="UI")
    assert tick(m, 6, state=S.PINCH_ACTIVE, focus="UI")[0].pinch_active
    assert not tick(m, 7, state=S.HOLD, focus="UI", context=("molecule",))[0].pinch_active


@pytest.mark.parametrize("status", [TrackingStatus.NO_HAND, TrackingStatus.REACQUIRED, TrackingStatus.INVALID])
def test_loss_reacquisition_cannot_resume_hold(status):
    m = mapper()
    tick(m, 1)
    tick(m, 2, state=S.PINCH_ACTIVE)
    assert not tick(m, 3, status=status)[0].interaction_valid
    assert not tick(m, 4, state=S.HOLD)[0].interaction_valid
    tick(m, 5)
    assert tick(m, 6, state=S.PINCH_ACTIVE)[0].pinch_active


def test_timestamp_gap_duplicate_and_out_of_order_revoke():
    m = mapper()
    tick(m, 1)
    tick(m, 2, state=S.PINCH_ACTIVE)
    for i in (2, 1, 20):
        assert not tick(m, i, state=S.HOLD)[0].pinch_active


def test_mirror_pointer_and_rotation_share_direction():
    m = mapper()
    settings = UserSettings(InputMode.FULL_HAND, mirror=True)
    first = tick(m, 1, settings=settings)[0]
    second = tick(m, 2, dx=.05, settings=settings)[0]
    assert second.pointer_xy[0] < first.pointer_xy[0] and second.rotation_delta[0] < 0


def test_unknown_pose_never_rotates_and_fist_has_no_command():
    m = mapper()
    tick(m, 1)
    for i, pose in enumerate((HandPose.UNKNOWN, HandPose.FIST, HandPose.OPEN), 2):
        out = tick(m, i, pose=pose, dx=i*.01)[0]
        assert out.rotation_delta == (0., 0.) and out.scale_delta == 0


def test_missing_reference_explicit_fallback_and_handoff_neutral():
    m = mapper()
    out, legacy = tick(m, 1, ref=False)
    assert out is legacy
    tick(m, 2)
    out, legacy = tick(m, 3, ref=False)
    assert out is legacy and m.diagnostics.owner == "LEGACY"


@pytest.mark.parametrize("value, expected", [(0., 0.), (.001, 0.), (.011, .02), (-.011, -.02), (1., .08)])
def test_response_units_and_limits(value, expected):
    assert response(value, .001, 2., .08) == pytest.approx(expected)


def test_preferences_save_explicitly_never_restore_actions_or_reference(tmp_path):
    p = tmp_path / "settings.json"
    s = UserSettings(InputMode.FULL_HAND, "responsive", True, True)
    save_settings(p, s)
    loaded = load_settings(p)
    assert loaded == UserSettings(InputMode.OBSERVE, "responsive", True, False)
    assert "reference" not in p.read_text() and "threshold" not in p.read_text()


def test_settings_validation_and_profile():
    with pytest.raises(ValueError):
        UserSettings(sensitivity="infinite")
    motion, gains, two = load_application_profile(PROFILE)
    assert motion.rotation_gain > 0 and gains["standard"] == 1 and two["scale_gain"] > 0

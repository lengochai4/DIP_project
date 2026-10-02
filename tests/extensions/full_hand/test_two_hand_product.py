from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace as NS
import numpy as np
import pytest
from dip_touchless.core import ColorSpace, FramePacket
from extensions.stem3d.product.settings import load_application_profile
from extensions.stem3d.product.two_hand import TwoHandAssociation, TwoHandProfile
from application_adapters.two_hand_provider import TwoHandProvider
from extensions.stem3d.full_hand.observe import load_observe_profile
from test_geometry import _fixture


def tracker():
    profile = load_application_profile(Path("config/extensions/application.yaml"))[2]
    pose = load_observe_profile(Path("config/extensions/full_hand_observe.yaml")).pose
    return TwoHandAssociation(TwoHandProfile(**profile), pose)


def frame(i, offsets=(-.25, .25), *, reverse=False, width=1600, run="synthetic-a2"):
    sets = tuple(_fixture(transform=lambda x, y, offset=offset: (x+offset, y))[0].filtered_landmarks
                 for offset in offsets)
    fg = replace(_fixture()[1], run_id=run, frame_id=i, timestamp_s=i*.1, width=width)
    return fg, tuple(reversed(sets)) if reverse else sets


def test_two_hands_42_landmarks_dwell_scale_and_provider_order_independent():
    t = tracker()
    first = t.update(*frame(0))
    assert len(first.hands) == 2 and sum(len(h.landmarks) for h in first.hands) == 42
    assert not first.armed and first.scale_delta == 0
    ids = tuple(h.track_id for h in first.hands)
    for i in range(1, 5):
        result = t.update(*frame(i, reverse=bool(i%2)))
        assert tuple(h.track_id for h in result.hands) == ids
    assert result.armed and result.scale_delta == 0
    assert t.update(*frame(5, (-.28,.28))).scale_delta > 0
    assert t.update(*frame(6, (-.25,.25))).scale_delta < 0


def test_tracking_loss_reacquisition_requires_new_ids_and_dwell():
    t = tracker()
    for i in range(5): result = t.update(*frame(i))
    ids = tuple(h.track_id for h in result.hands)
    fg, hands = frame(5)
    lost = t.update(fg, hands[:1])
    assert not lost.armed and not lost.scale_delta
    returned = t.update(*frame(6))
    assert not returned.armed and returned.scale_delta == 0
    assert tuple(h.track_id for h in returned.hands) != ids


@pytest.mark.parametrize("bad", ["overlap", "large-jump", "duplicate", "gap", "dimensions", "run"])
def test_ambiguous_or_discontinuous_pair_never_scales(bad):
    t = tracker()
    for i in range(5): t.update(*frame(i))
    args = frame(5)
    if bad == "overlap": args = frame(5, (0., .01))
    if bad == "large-jump": args = frame(5, (-.9,.9))
    if bad == "duplicate": args = frame(4)
    if bad == "gap": args = frame(15)
    if bad == "dimensions": args = frame(5, width=640)
    if bad == "run": args = frame(5, run="new-run")
    result = t.update(*args)
    assert not result.armed and result.scale_delta == 0


def test_non_open_pose_and_invalid_geometry_are_neutral():
    t = tracker()
    fg, hands = frame(0)
    invalid = tuple(replace(p, x=0., y=0.) for p in hands[0])
    assert not t.update(fg, (invalid, hands[1])).armed
    fg, hands = frame(1)
    # Move thumb onto index to force scalar PINCH, not OPEN.
    closed = tuple(replace(p, x=hands[0][8].x, y=hands[0][8].y) if p.index == 4 else p for p in hands[0])
    result = t.update(fg, (closed, hands[1]))
    assert not result.armed and result.reason == "BOTH_OPEN_REQUIRED"


def test_provider_explicit_color_coordinates_no_quality_and_cleanup():
    frame_data, fg = _fixture()
    points = [NS(x=p.x, y=p.y, z=p.z) for p in frame_data.filtered_landmarks]
    calls = []
    class Landmarker:
        def detect_for_video(self, image, timestamp):
            calls.append(timestamp)
            return NS(hand_landmarks=[points, points])
        def close(self): calls.append("closed")
    p = TwoHandProvider(None, {}, landmarker=Landmarker())
    packet = FramePacket(fg.run_id, 0, 1., np.zeros((90,160,3),np.uint8), ColorSpace.BGR, "synthetic")
    hands = p.process(packet)
    assert len(hands) == 2 and all(len(h) == 21 for h in hands)
    assert hands[0] == frame_data.filtered_landmarks
    with pytest.raises(ValueError, match="increase"):
        p.process(packet)
    with pytest.raises(ValueError, match="BGR"):
        p.process(replace(packet, color_space=ColorSpace.RGB))
    p.close()
    p.close()
    assert calls == [1000, "closed"]
    with pytest.raises(RuntimeError, match="closed"):
        p.process(replace(packet, timestamp_s=2.))


def test_deterministic_replay_and_input_immutability():
    before = frame(0)
    source = [frame(i, reverse=i%2==0) for i in range(8)]
    first, second = tracker(), tracker()
    assert [first.update(*v) for v in source] == [second.update(*v) for v in source]
    assert before == frame(0)

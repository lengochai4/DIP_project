"""Product behavior invariants; synthetic evidence is never a physical success rate."""

from dataclasses import replace
import math
import numpy as np
import pytest
from dip_touchless.core import Landmark, CoordinateSpace
from app.config import ProductConfig, Settings
from app.interaction.contracts import (
    AnchorPose,
    HandState,
    GestureIntent,
    IntentType,
    Phase,
    Owner,
)
from app.interaction.intentional_pinch import IntentionalPinch
from app.interaction.engine import IntentEngine
from app.interaction.router import IntentRouter
from app.interaction.hand_geometry import describe
from app.interaction.bimanual import Detection, HandAssociation
from app.rendering.transforms import Projection, rotation, fit_rect
from app.rendering.hand_anchor import HandAnchor

C = ProductConfig()


def hand(
    ratio=1.0, pose="POINT", role="DOMINANT", center=(0.65, 0.55), pointer=(0.6, 0.3)
):
    fingers = (
        (False, True, False, False, False)
        if pose == "POINT"
        else (
            (True,) * 5
            if pose == "OPEN_PALM"
            else (False, True, True, False, False) if pose == "V_SIGN" else (False,) * 5
        )
    )
    return HandState(
        role, role, pose, fingers, pointer, AnchorPose(center, 0.2, 0), ratio
    )


def reference(pinch):
    pinch.calibrate()
    for t in np.arange(0, 1.31, 0.05):
        pinch.update(hand(), float(t))
    assert pinch.reference == pytest.approx(1.0)
    for t in (1.4, 1.55, 1.7):
        pinch.update(hand(), t)
    assert pinch.armed


def test_intentional_pinch_requires_reference_progress_dwell_and_rearm():
    p = IntentionalPinch(C)
    for i in range(20):
        p.update(hand(0.1), i * 0.05)
    assert not p.active
    reference(p)
    p.update(hand(0.35), 1.8)
    assert not p.active
    p.update(hand(0.35), 1.95)
    assert not p.active
    p.update(hand(0.35), 2.05)
    assert p.active and p.cycle_id == 1
    p.update(hand(0.3), 2.1)
    assert p.state == "HOLD" and p.cycle_id == 1
    p.update(hand(1.0), 2.2)
    assert not p.active and not p.armed
    p.update(hand(0.2), 2.3)
    assert not p.active
    p.update(hand(1.0), 2.4)
    p.update(hand(1.0), 2.7)
    assert p.armed


@pytest.mark.parametrize(
    "timestamp,valid", [(3.0, True), (2.05, True), (math.nan, True), (2.1, False)]
)
def test_pinch_discontinuities_revoke_active_and_require_release(timestamp, valid):
    p = IntentionalPinch(C)
    reference(p)
    p.update(hand(0.2), 1.8)
    p.update(hand(0.2), 2.05)
    assert p.active
    p.update(hand(0.2), timestamp, valid=valid)
    assert not p.active and not p.armed
    p.update(hand(0.2), 3.1)
    assert not p.active


def test_projection_domain_change_invalidates_reference():
    p = IntentionalPinch(C)
    p.calibrate()
    for t in np.arange(0, 1.3, 0.05):
        p.update(replace(hand(), palm_signature=(1.0, 2.0)), float(t))
    assert p.reference is not None
    p.update(replace(hand(0.1), palm_signature=(1.0, 3.0)), 1.35)
    assert p.reference is None and not p.active


def engine_ready(hands=None):
    engine = IntentEngine(C)
    hands = hands or [hand()]
    engine.update(hands, ("run", 0, 0.0), settings=Settings())
    for p in engine.pinches.values():
        p.reference = 1.0
    engine.update(hands, ("run", 1, 0.1), settings=Settings())
    engine.update(hands, ("run", 2, 0.4), settings=Settings())
    return engine


def test_point_inspects_only_and_unknown_cancels():
    e = engine_ready()
    result = e.update([hand(pointer=(0.7, 0.5))], ("run", 3, 0.45), settings=Settings())
    assert result.type is IntentType.POINT and result.delta_xy == (0.0, 0.0)
    result = e.update([hand(pose="UNKNOWN")], ("run", 4, 0.5), settings=Settings())
    assert result.type is IntentType.CANCEL and not result.validity


def test_one_pinch_cycle_grab_drag_release_and_context_rearm():
    e = engine_ready()
    e.update([hand(0.3)], ("run", 3, 0.5), settings=Settings())
    result = e.update([hand(0.3)], ("run", 4, 0.75), settings=Settings())
    assert result.type is IntentType.GRAB and result.phase is Phase.BEGIN
    result = e.update(
        [hand(0.3, pointer=(0.7, 0.4))], ("run", 5, 0.8), settings=Settings()
    )
    assert result.type is IntentType.DRAG
    result = e.update(
        [hand(0.3)], ("run", 6, 0.85), settings=Settings(), context=("new_scene",)
    )
    assert result.type is IntentType.CANCEL
    result = e.update(
        [hand(0.3)], ("run", 7, 0.9), settings=Settings(), context=("new_scene",)
    )
    assert result.type not in {IntentType.GRAB, IntentType.DRAG}


def test_open_pair_never_scales_and_both_pinches_scale_relative_to_entry():
    d, s = hand(pose="OPEN_PALM"), hand(
        pose="OPEN_PALM", role="SUPPORT", center=(0.25, 0.55)
    )
    e = engine_ready([d, s])
    result = e.update(
        [replace(d, palm=AnchorPose((0.8, 0.5), 0.2, 0)), s],
        ("run", 3, 0.45),
        settings=Settings(),
    )
    assert result.type is IntentType.ANCHOR
    d, s = hand(0.3), hand(0.3, role="SUPPORT", center=(0.25, 0.55))
    e.update([d, s], ("run", 4, 0.5), settings=Settings())
    result = e.update([d, s], ("run", 5, 0.75), settings=Settings())
    assert result.type is IntentType.SCALE and result.phase is Phase.BEGIN
    result = e.update(
        [replace(d, palm=AnchorPose((0.85, 0.55), 0.2, 0)), s],
        ("run", 6, 0.8),
        settings=Settings(),
    )
    assert result.scale_factor == pytest.approx(1.5)
    result = e.update(
        [d, replace(s, pinch_ratio=1.0)], ("run", 7, 0.85), settings=Settings()
    )
    assert result.type is IntentType.RELEASE
    result = e.update([d, s], ("run", 8, 0.9), settings=Settings())
    assert result.type not in {IntentType.GRAB, IntentType.SCALE, IntentType.DRAG}


def test_two_index_lock_then_dominant_pinch_commits_pair_once():
    d, s = hand(), hand(role="SUPPORT", center=(0.25, 0.55), pointer=(0.2, 0.3))
    e = engine_ready([d, s])
    e.update([d, s], ("run", 3, 0.6), settings=Settings())
    e.update([d, s], ("run", 4, 0.9), settings=Settings())
    result = e.update([d, s], ("run", 5, 1.2), settings=Settings())
    assert result.reason == "LOCKED"
    e.update([replace(d, pinch_ratio=0.3), s], ("run", 6, 1.3), settings=Settings())
    result = e.update(
        [replace(d, pinch_ratio=0.3), s], ("run", 7, 1.55), settings=Settings()
    )
    assert result.type is IntentType.MEASURE_COMMIT and len(result.points) == 2
    result = e.update(
        [replace(d, pinch_ratio=0.3), s], ("run", 8, 1.6), settings=Settings()
    )
    assert result.type is not IntentType.MEASURE_COMMIT


def test_router_captures_owner_and_modal_preempts():
    r = IntentRouter()
    begin = GestureIntent(IntentType.GRAB, Phase.BEGIN, cycle_id=1)
    assert r.route(begin, ui=True).owner is Owner.UI
    assert r.route(GestureIntent(IntentType.DRAG, cycle_id=1)).owner is Owner.UI
    assert r.route(begin, modal=True).type is IntentType.CANCEL
    assert r.owner is None


def test_modal_cancels_active_clutch_and_held_pinch_cannot_resume():
    e = engine_ready()
    e.update([hand(0.3)], ("run", 3, 0.5), settings=Settings())
    assert (
        e.update([hand(0.3)], ("run", 4, 0.75), settings=Settings()).type
        is IntentType.GRAB
    )
    result = e.update([hand(0.3)], ("run", 5, 0.8), settings=Settings(), modal=True)
    assert result.type is IntentType.CANCEL and result.owner is Owner.SYSTEM_MODAL
    assert not e.pinches["DOMINANT"].armed
    result = e.update([hand(0.3)], ("run", 6, 0.9), settings=Settings())
    assert result.type not in {IntentType.GRAB, IntentType.DRAG, IntentType.SELECT}


@pytest.mark.parametrize("mirror", [False, True])
def test_two_index_preview_and_commit_share_pointer_gain_and_mirror(mirror):
    d, s = hand(pointer=(0.6, 0.3)), hand(role="SUPPORT", pointer=(0.2, 0.4))
    e = engine_ready([d, s])
    settings = Settings(mirror=mirror, pointer_sensitivity=2.0)
    # Keep engine context fixed; the supplied settings affect presentation only here.
    result = e.update([d, s], ("run", 3, 0.6), settings=settings)
    expected = tuple((*e.pointer(h.pointer_xy, settings), 0.0) for h in (s, d))
    assert result.points == expected
    assert result.pointer_xy == expected[1][:2]
    e.update([d, s], ("run", 4, 0.9), settings=settings)
    assert e.update([d, s], ("run", 5, 1.2), settings=settings).reason == "LOCKED"
    e.update([replace(d, pinch_ratio=0.3), s], ("run", 6, 1.3), settings=settings)
    result = e.update(
        [replace(d, pinch_ratio=0.3), s], ("run", 7, 1.55), settings=settings
    )
    assert result.type is IntentType.MEASURE_COMMIT and result.points == expected


@pytest.mark.parametrize(
    "scenario", ["loss", "gap", "repeated_frame", "run_restart", "support_loss"]
)
def test_active_pair_interruption_neutralizes_without_resume_from_held_pinch(scenario):
    d, s = hand(), hand(role="SUPPORT", center=(0.25, 0.55))
    e = engine_ready([d, s])
    d, s = replace(d, pinch_ratio=0.3), replace(s, pinch_ratio=0.3)
    e.update([d, s], ("run", 3, 0.5), settings=Settings())
    result = e.update([d, s], ("run", 4, 0.75), settings=Settings())
    assert result.type is IntentType.SCALE
    hands = [] if scenario == "loss" else [d] if scenario == "support_loss" else [d, s]
    identity = (
        ("new", 5, 0.8)
        if scenario == "run_restart"
        else (
            ("run", 4, 0.75)
            if scenario == "repeated_frame"
            else ("run", 5, 1.8) if scenario == "gap" else ("run", 5, 0.8)
        )
    )
    result = e.update(hands, identity, settings=Settings())
    assert result.type is IntentType.CANCEL
    result = e.update(
        [d, s], (identity[0], identity[1] + 1, identity[2] + 0.1), settings=Settings()
    )
    assert result.type not in {
        IntentType.GRAB,
        IntentType.SCALE,
        IntentType.DRAG,
        IntentType.MEASURE_COMMIT,
    }


def test_ui_pinch_activates_once_and_never_leaks_to_scene():
    e = engine_ready()
    e.update([hand(0.3)], ("run", 3, 0.5), settings=Settings(), ui=True)
    result = e.update([hand(0.3)], ("run", 4, 0.75), settings=Settings(), ui=True)
    assert result.type is IntentType.SELECT and result.owner is Owner.UI
    result = e.update([hand(0.3)], ("run", 5, 0.8), settings=Settings(), ui=False)
    assert result.owner is Owner.UI and result.type is not IntentType.DRAG


@pytest.mark.parametrize("mirror", [False, True])
def test_scene_projection_roundtrip_and_letterbox(mirror):
    p = Projection(1200, 800, (600.0, 400.0), 100.0, rotation(0.4, 0.3, 0.2))
    point = (0.7, -0.3, 0.0)
    x, y, _ = p.project(point)
    assert p.plane_point((x / 1200, y / 800)) == pytest.approx(point)
    assert fit_rect(1000, 1000, 640, 480) == pytest.approx((0, 125, 1000, 750))


def test_anchor_wrap_smoothing_and_loss():
    a = HandAnchor(C)
    a.update(AnchorPose((0.2, 0.5), 0.2, math.pi - 0.02), 0.0)
    pose = a.update(AnchorPose((0.8, 0.5), 0.4, -math.pi + 0.02), 0.05)
    assert abs(pose.roll_rad) > 3 and 0.2 < pose.center_xy[0] < 0.8
    assert a.update(None, 0.1) is None


def test_support_open_palm_keeps_dominant_point_and_projects_reference_plane():
    d, s = hand(), hand(pose="OPEN_PALM", role="SUPPORT", center=(0.25, 0.55))
    e = engine_ready([d, s])
    result = e.update([d, s], ("run", 3, 0.45), settings=Settings())
    assert result.type is IntentType.POINT and result.anchor_pose == s.palm
    projection = Projection(800, 600, (400.0, 300.0), 100.0, rotation(0.3, 0.2))
    normal = (0.1, 0.2, 1.0)
    point = projection.plane_point((0.7, 0.6), normal)
    assert np.dot(normal, point) == pytest.approx(0.0, abs=1e-8)


def test_geometry_missing_indices_nonfinite_and_degenerate_are_explicit():
    assert describe((), 640, 480, C) is None
    lm = tuple(
        Landmark(i, 0.0, 0.0, 0.0, CoordinateSpace.FRAME_NORMALIZED) for i in range(21)
    )
    assert describe(lm, 640, 480, C) is None
    with pytest.raises(ValueError):
        replace(lm[0], x=math.nan)
    from types import SimpleNamespace

    malformed = tuple(
        SimpleNamespace(
            index=i,
            x=math.nan,
            y=0.0,
            z=0.0,
            coordinate_space=CoordinateSpace.FRAME_NORMALIZED,
        )
        for i in range(21)
    )
    assert describe(malformed, 640, 480, C) is None


def geometry_fixture(pose):
    xy = [
        (0.5, 0.85),
        (0.44, 0.77),
        (0.34, 0.69),
        (0.25, 0.62),
        (0.17, 0.55),
        (0.4, 0.62),
        (0.4, 0.42),
        (0.4, 0.30),
        (0.4, 0.20),
        (0.5, 0.6),
        (0.5, 0.37),
        (0.5, 0.24),
        (0.5, 0.12),
        (0.6, 0.62),
        (0.6, 0.4),
        (0.6, 0.27),
        (0.6, 0.18),
        (0.7, 0.66),
        (0.7, 0.49),
        (0.7, 0.39),
        (0.7, 0.30),
    ]
    extended = {"OPEN_PALM": {1, 2, 3, 4}, "POINT": {1}, "V_SIGN": {1, 2}}[pose]
    for finger, base in enumerate((5, 9, 13, 17), start=1):
        if finger not in extended:
            x, y = xy[base]
            xy[base + 1 : base + 4] = [
                (x + 0.02, y - 0.08),
                (x + 0.03, y + 0.04),
                (x + 0.03, y + 0.12),
            ]
    return tuple(
        Landmark(i, x, y, 0.0, CoordinateSpace.FRAME_NORMALIZED)
        for i, (x, y) in enumerate(xy)
    )


@pytest.mark.parametrize("pose", ["POINT", "V_SIGN", "OPEN_PALM"])
@pytest.mark.parametrize("mirror", [False, True])
def test_actual_21_point_classifier_is_translation_scale_mirror_invariant(pose, mirror):
    landmarks = geometry_fixture(pose)
    original = describe(landmarks, 640, 480, C)
    assert original is not None and original.pose == pose
    transformed = tuple(
        replace(p, x=(1 - p.x if mirror else p.x) * 0.8 + 0.07, y=p.y * 0.8 + 0.05)
        for p in landmarks
    )
    moved = describe(transformed, 640, 480, C)
    assert moved.pose == pose and moved.pinch_ratio == pytest.approx(
        original.pinch_ratio
    )


def detection(x, label):
    points = tuple(
        Landmark(
            i, x + i * 0.001, 0.5 + i * 0.002, 0.0, CoordinateSpace.FRAME_NORMALIZED
        )
        for i in range(21)
    )
    return Detection(points, label)


@pytest.mark.parametrize("pose", ["POINT", "V_SIGN", "OPEN_PALM"])
@pytest.mark.parametrize("aspect", [1.0, 4 / 3, 16 / 9])
@pytest.mark.parametrize("mirror", [False, True])
def test_relative_3d_finger_joints_survive_tilt(pose, aspect, mirror):
    landmarks = geometry_fixture(pose)
    # Rigid rotation of the model-relative hand, then conversion back to source
    # normalization. Depth supplies bend cues; it is never a metric measurement.
    xyz = np.array([(p.x * aspect, p.y, p.z * aspect) for p in landmarks])
    xyz -= xyz[0].copy()
    xyz = xyz @ rotation(0.65, 1.1).T
    transformed = tuple(
        replace(
            p,
            x=(0.55 - q[0] / aspect if mirror else 0.45 + q[0] / aspect),
            y=0.7 + q[1],
            z=q[2] / aspect,
        )
        for p, q in zip(landmarks, xyz)
    )
    result = describe(transformed, round(aspect * 900), 900, C)
    assert result is not None and result.pose == pose


def test_projected_straight_but_depth_folded_finger_is_not_extended():
    landmarks = list(geometry_fixture("OPEN_PALM"))
    # Middle finger projects to a straight image line, but its relative joints
    # double back in z. The former 2D-only classifier marked it extended.
    landmarks[10] = replace(landmarks[10], z=-0.3)
    landmarks[11] = replace(landmarks[11], z=0.1)
    result = describe(landmarks, 640, 480, C)
    assert result is not None and not result.fingers[2]
    assert result.pose == "UNKNOWN"


def test_real_landmark_classifier_to_gui_keeps_index_tip_and_anchor(
    tmp_path, monkeypatch
):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from dip_touchless.core import (
        FramePacket,
        ColorSpace,
        TrackingFrame,
        TrackingStatus,
        MeasurementQuality,
        FilterDiagnostics,
        FilterMode,
        StageTimings,
    )
    import app.ui.shell as shell

    qt = QApplication.instance() or QApplication([])
    monkeypatch.setattr(shell, "ROOT", tmp_path)
    monkeypatch.setattr(
        QApplication, "applicationState", lambda: Qt.ApplicationState.ApplicationActive
    )
    window = shell.ProductWindow(
        C,
        Settings(geometry_mode="RECORDED"),
        software=True,
        preferences_path=tmp_path / "preferences.json",
    )
    window.show()
    qt.applicationStateChanged.disconnect(window._application_state)
    try:
        window.navigate("Explore")
        window.set_mode("HAND")
        qt.processEvents()
        # Actual describe() is used, not the semantic HandState seam.
        for i, pose in enumerate(("OPEN_PALM", "OPEN_PALM", "POINT")):
            ts = 1 + i * 0.1
            packet = FramePacket(
                "landmarks-ui",
                i,
                ts,
                np.zeros((480, 640, 3), np.uint8),
                ColorSpace.BGR,
                "synthetic",
            )
            frame = TrackingFrame(
                "landmarks-ui",
                i,
                ts,
                TrackingStatus.VALID,
                (),
                (),
                MeasurementQuality.unavailable(),
                None,
                None,
                FilterDiagnostics(
                    FilterMode.RAW, None, None, None, None, None, None, None, False
                ),
                StageTimings(0, 0, 0, 0, 0),
                (),
            )
            window.consume(
                packet, frame, None, {"Right": geometry_fixture(pose)}, True, "TRACKING"
            )
        assert window.current_hands[0].pose == "POINT"
        assert (
            window.viewport.anchor is not None
            and window.registry.current.preview is not None
        )
        tip = geometry_fixture("POINT")[8]
        x, y, w, h = window.viewport.image_rect()
        expected = (
            (x + (1 - tip.x) * w) / window.viewport.width(),
            (y + tip.y * h) / window.viewport.height(),
        )
        assert window.viewport.pointer == pytest.approx(expected)
        qt.processEvents()
        # The wrapped live hint may resize the viewport after consume(). Both
        # overlay and cursor must still use the new displayed camera rect.
        x, y, w, h = window.viewport.image_rect()
        expected = (
            (x + (1 - tip.x) * w) / window.viewport.width(),
            (y + tip.y * h) / window.viewport.height(),
        )
        assert window.viewport.pointer == pytest.approx(expected)
        image = window.viewport.grab().toImage()
        ratio = image.devicePixelRatio()
        cx = round((expected[0] * window.viewport.width() + 9) * ratio)
        cy = round(expected[1] * window.viewport.height() * ratio)
        colors = [
            image.pixelColor(cx + dx, cy + dy)
            for dx in range(-2, 3)
            for dy in range(-2, 3)
        ]
        assert any(c.red() > 180 and c.green() > 160 and c.blue() < 180 for c in colors)
    finally:
        window.close()
        qt.processEvents()


def test_hand_anchor_follows_same_live_palm_through_point_and_pinch_shapes():
    anchor = HandAnchor(C)
    opened = hand(pose="OPEN_PALM")
    assert anchor.observe([opened], ("run", 0, 0)) is not None
    for i, pose in enumerate(("POINT", "V_SIGN", "UNKNOWN"), 1):
        observed = replace(hand(pose=pose), palm=AnchorPose((0.7, 0.5), 0.25, 0.1))
        assert anchor.observe([observed], ("run", i, i * 0.1)) is not None
    assert anchor.pose.center_xy[0] > opened.palm.center_xy[0]
    assert anchor.observe([], ("run", 4, 0.4), valid=False) is None
    assert anchor.observe([hand()], ("run", 5, 0.5)) is None
    assert anchor.observe([opened], ("run", 6, 0.6)) is not None


@pytest.mark.parametrize("change", ["run", "time", "track", "role"])
def test_hand_anchor_identity_and_time_changes_require_open_acquisition(change):
    anchor = HandAnchor(C)
    anchor.observe([hand(pose="OPEN_PALM")], ("run", 0, 0))
    observed = hand()
    identity = ("run", 1, 0.1)
    if change == "run":
        identity = ("new", 1, 0.1)
    elif change == "time":
        identity = ("run", 1, 1.0)
    elif change == "track":
        observed = replace(observed, track_id="new")
    else:
        observed = replace(observed, role="SUPPORT")
    assert anchor.observe([observed], identity) is None


def test_bimanual_source_points_keep_locked_snapshot_without_gain_or_clamping():
    d = hand(pointer=(0.9, 0.3))
    s = hand(role="SUPPORT", pointer=(0.1, 0.7))
    e = engine_ready([d, s])
    settings = Settings(pointer_sensitivity=3.0)
    for i in range(3, 12):
        result = e.update([d, s], ("run", i, i * 0.2), settings=settings)
    assert result.reason == "LOCKED"
    assert result.source_points == (s.pointer_xy, d.pointer_xy)
    closed = replace(d, pinch_ratio=0.3, pointer_xy=(0.8, 0.4))
    e.update([closed, s], ("run", 12, 2.4), settings=settings)
    commit = e.update([closed, s], ("run", 13, 2.7), settings=settings)
    assert commit.type is IntentType.MEASURE_COMMIT
    assert commit.source_points == (s.pointer_xy, d.pointer_xy)
    assert commit.source_pointer_xy == closed.pointer_xy


def test_association_survives_provider_order_and_rejects_crossing_overlap():
    association = HandAssociation(C)
    first = association.update([detection(0.2, "Left"), detection(0.7, "Right")])
    assert set(first) == {"Left", "Right"}
    second = association.update([detection(0.71, "Right"), detection(0.21, "Left")])
    assert second["Left"].landmarks[0].x == pytest.approx(0.21)
    assert association.update([detection(0.5, "Right"), detection(0.51, "Left")]) == {}


def test_extra_hands_cancel_association_then_reacquire_explicitly():
    association = HandAssociation(C)
    pair = [detection(0.2, "Left"), detection(0.7, "Right")]
    association.update(pair)
    association.update(pair)
    assert association.reason == "TRACKING"
    assert association.update([*pair, detection(0.5, "Right")]) == {}
    assert association.reason == "TOO_MANY_HANDS" and association.previous == {}
    assert set(association.update(pair)) == {"Left", "Right"}
    assert association.reason == "ACQUIRING"


@pytest.mark.parametrize("normal", [(0, 0, 1), (0.1, 0.2, 1)])
def test_perspective_plane_roundtrip_and_gpu_clip_mapping(normal):
    p = Projection(1200, 800, (610, 390), 110, rotation(0.4, 0.3, 0.2), 8.0)
    point = (0.7, -0.3, -(normal[0] * 0.7 - normal[1] * 0.3) / normal[2])
    x, y, _ = p.project(point)
    assert p.plane_point((x / 1200, y / 800), normal) == pytest.approx(point)
    clip = p.clip_matrix() @ np.array((*point, 1.0))
    ndc = clip[:3] / clip[3]
    assert ((ndc[0] + 1) * 600, (1 - ndc[1]) * 400) == pytest.approx((x, y), abs=1e-5)


def test_perspective_foreshortening_and_clipping_are_explicit():
    p = Projection(1200, 800, (600, 400), 100, np.eye(3), 8.0)
    assert p.project((1, 0, 4))[0] - 600 == pytest.approx(
        2 * (p.project((1, 0, 0))[0] - 600)
    )
    assert p.radius((0, 0, 4), 0.3) == pytest.approx(2 * p.radius((0, 0, 0), 0.3))
    assert not p.visible((0, 0, 8)) and not p.visible((0, 0, 9))
    assert p.plane_point((0.5, 0.5), (1, 0, 0)) is None


@pytest.mark.parametrize(
    "change",
    [
        {"pinch_exit": 0.9},
        {"max_gap_s": math.nan},
        {"release_min_samples": 1},
        {"finger_angle_rad": 4.0},
    ],
)
def test_config_rejects_unsafe_policies(change):
    with pytest.raises(ValueError):
        replace(C, **change)


def test_settings_roundtrip_and_no_reference_persistence(tmp_path):
    path = tmp_path / "settings.json"
    settings = Settings(dominant_hand="Left", mirror=False)
    settings.save(path)
    assert Settings.load(path) == settings
    assert "reference" not in path.read_text()
    with pytest.raises(ValueError):
        Settings(mirror="false")

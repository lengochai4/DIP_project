import pytest

from dip_touchless.core import (
    CoordinateSpace,
    FilterDiagnostics,
    FilterMode,
    Landmark,
    MeasurementQuality,
    StageTimings,
    TrackingFrame,
    TrackingStatus,
)
from dip_touchless.interaction import (
    DeterministicGestureEngine,
)


def _engine() -> DeterministicGestureEngine:
    return DeterministicGestureEngine(
        pointer_landmark_index=8,
        pinch_thumb_landmark_index=4,
        pinch_index_landmark_index=8,
        hand_scale_landmark_a=5,
        hand_scale_landmark_b=17,
        hand_scale_epsilon=1e-6,
        pinch_on=0.30,
        pinch_off=0.40,
        rotation_deadzone=0.01,
        rotation_gain=2.0,
        rotation_max_delta_rad=0.10,
        scale_deadzone=0.01,
        scale_gain=2.0,
        scale_max_delta=0.10,
    )


def _landmark(
    index: int,
    x: float,
    y: float,
) -> Landmark:
    return Landmark(
        index=index,
        x=x,
        y=y,
        z=-0.1,
        coordinate_space=(
            CoordinateSpace.FRAME_NORMALIZED
        ),
    )


def _landmarks(
    *,
    pointer_x: float = 0.50,
    pointer_y: float = 0.50,
    pinch_ratio: float = 0.50,
) -> tuple[Landmark, ...]:
    return (
        _landmark(
            4,
            pointer_x - pinch_ratio,
            pointer_y,
        ),
        _landmark(
            5,
            0.0,
            0.0,
        ),
        _landmark(
            8,
            pointer_x,
            pointer_y,
        ),
        _landmark(
            17,
            1.0,
            0.0,
        ),
    )


def _frame(
    *,
    frame_id: int,
    status: TrackingStatus = TrackingStatus.VALID,
    pointer_x: float = 0.50,
    pointer_y: float = 0.50,
    pinch_ratio: float = 0.50,
    reset_occurred: bool = False,
    landmarks: tuple[Landmark, ...] | None = None,
) -> TrackingFrame:
    filtered = (
        _landmarks(
            pointer_x=pointer_x,
            pointer_y=pointer_y,
            pinch_ratio=pinch_ratio,
        )
        if landmarks is None
        else landmarks
    )

    return TrackingFrame(
        run_id="run-gesture",
        frame_id=frame_id,
        timestamp_s=frame_id * 0.05,
        status=status,
        raw_landmarks=filtered,
        filtered_landmarks=filtered,
        quality=MeasurementQuality.unavailable(),
        roi=None,
        illumination=None,
        filter_diagnostics=FilterDiagnostics(
            mode=FilterMode.RAW,
            dt_s=None,
            speed=None,
            beta=None,
            min_cutoff_hz=None,
            final_cutoff_hz=None,
            signal_alpha=None,
            derivative_alpha=None,
            reset_occurred=reset_occurred,
        ),
        timings=StageTimings(
            preprocess_ms=0.0,
            tracking_ms=0.0,
            filtering_ms=0.0,
            gesture_ms=0.0,
            compute_total_ms=0.0,
        ),
        events=(),
    )


def test_first_usable_frame_is_neutral_initialization() -> None:
    engine = _engine()

    state = engine.update(
        _frame(
            frame_id=0,
            pointer_x=0.4,
            pointer_y=0.3,
            pinch_ratio=0.2,
        )
    )

    assert state.interaction_valid is False

    assert state.pointer_xy == pytest.approx(
        (0.4, 0.3)
    )

    assert state.pinch_ratio == pytest.approx(
        0.2
    )

    assert state.pinch_active is False
    assert state.rotation_delta == (0.0, 0.0)
    assert state.scale_delta == 0.0


def test_ordinary_frame_emits_rotation() -> None:
    engine = _engine()

    engine.update(
        _frame(
            frame_id=0,
            pointer_x=0.50,
            pointer_y=0.50,
        )
    )

    state = engine.update(
        _frame(
            frame_id=1,
            pointer_x=0.53,
            pointer_y=0.52,
        )
    )

    assert state.interaction_valid is True

    assert state.rotation_delta[0] == pytest.approx(
        0.04
    )

    assert state.rotation_delta[1] == pytest.approx(
        -0.02
    )


def test_pinch_hysteresis_uses_strict_boundaries() -> None:
    engine = _engine()

    engine.update(
        _frame(
            frame_id=0,
            pinch_ratio=0.50,
        )
    )

    at_on = engine.update(
        _frame(
            frame_id=1,
            pinch_ratio=0.30,
        )
    )

    assert at_on.pinch_active is False

    activated = engine.update(
        _frame(
            frame_id=2,
            pinch_ratio=0.29,
        )
    )

    assert activated.pinch_active is True

    middle = engine.update(
        _frame(
            frame_id=3,
            pinch_ratio=0.35,
        )
    )

    assert middle.pinch_active is True

    at_off = engine.update(
        _frame(
            frame_id=4,
            pinch_ratio=0.40,
        )
    )

    assert at_off.pinch_active is True

    released = engine.update(
        _frame(
            frame_id=5,
            pinch_ratio=0.41,
        )
    )

    assert released.pinch_active is False


def test_pinch_activation_frame_is_scale_neutral() -> None:
    engine = _engine()

    engine.update(
        _frame(
            frame_id=0,
            pinch_ratio=0.50,
        )
    )

    state = engine.update(
        _frame(
            frame_id=1,
            pinch_ratio=0.20,
        )
    )

    assert state.pinch_active is True
    assert state.scale_delta == 0.0


def test_continuously_active_pinch_emits_scale_delta() -> None:
    engine = _engine()

    engine.update(
        _frame(
            frame_id=0,
            pinch_ratio=0.50,
        )
    )

    engine.update(
        _frame(
            frame_id=1,
            pinch_ratio=0.20,
        )
    )

    state = engine.update(
        _frame(
            frame_id=2,
            pinch_ratio=0.25,
        )
    )

    assert state.pinch_active is True

    assert state.scale_delta == pytest.approx(
        0.08
    )


def test_pinch_release_frame_is_scale_neutral() -> None:
    engine = _engine()

    engine.update(
        _frame(
            frame_id=0,
            pinch_ratio=0.50,
        )
    )

    engine.update(
        _frame(
            frame_id=1,
            pinch_ratio=0.20,
        )
    )

    state = engine.update(
        _frame(
            frame_id=2,
            pinch_ratio=0.50,
        )
    )

    assert state.pinch_active is False
    assert state.scale_delta == 0.0


def test_tracking_loss_invalidates_and_releases_pinch() -> None:
    engine = _engine()

    engine.update(
        _frame(
            frame_id=0,
            pinch_ratio=0.50,
        )
    )

    active = engine.update(
        _frame(
            frame_id=1,
            pinch_ratio=0.20,
        )
    )

    assert active.pinch_active is True

    lost = engine.update(
        _frame(
            frame_id=2,
            status=TrackingStatus.TEMPORARY_LOSS,
            landmarks=(),
        )
    )

    assert lost.interaction_valid is False
    assert lost.pointer_xy is None
    assert lost.pinch_ratio is None
    assert lost.pinch_active is False
    assert lost.rotation_delta == (0.0, 0.0)
    assert lost.scale_delta == 0.0

    reacquired_valid = engine.update(
        _frame(
            frame_id=3,
            status=TrackingStatus.VALID,
            pointer_x=0.90,
            pointer_y=0.10,
            pinch_ratio=0.10,
        )
    )

    assert reacquired_valid.interaction_valid is False
    assert reacquired_valid.pinch_active is False
    assert reacquired_valid.rotation_delta == (
        0.0,
        0.0,
    )
    assert reacquired_valid.scale_delta == 0.0


def test_reacquired_status_is_always_neutral() -> None:
    engine = _engine()

    engine.update(
        _frame(
            frame_id=0,
        )
    )

    engine.update(
        _frame(
            frame_id=1,
            pointer_x=0.55,
        )
    )

    state = engine.update(
        _frame(
            frame_id=2,
            status=TrackingStatus.REACQUIRED,
            pointer_x=0.95,
            pointer_y=0.05,
            pinch_ratio=0.10,
        )
    )

    assert state.interaction_valid is False
    assert state.pointer_xy == pytest.approx(
        (0.95, 0.05)
    )
    assert state.pinch_active is False
    assert state.rotation_delta == (0.0, 0.0)
    assert state.scale_delta == 0.0


def test_filter_reset_frame_is_neutral() -> None:
    engine = _engine()

    engine.update(
        _frame(
            frame_id=0,
        )
    )

    engine.update(
        _frame(
            frame_id=1,
            pointer_x=0.55,
        )
    )

    state = engine.update(
        _frame(
            frame_id=2,
            pointer_x=0.90,
            reset_occurred=True,
        )
    )

    assert state.interaction_valid is False
    assert state.rotation_delta == (0.0, 0.0)
    assert state.scale_delta == 0.0
    assert state.pinch_active is False


def test_missing_required_landmark_invalidates_frame() -> None:
    engine = _engine()

    incomplete = (
        _landmark(4, 0.2, 0.5),
        _landmark(5, 0.0, 0.0),
        _landmark(8, 0.5, 0.5),
    )

    state = engine.update(
        _frame(
            frame_id=0,
            landmarks=incomplete,
        )
    )

    assert state.interaction_valid is False
    assert state.pointer_xy is None
    assert state.pinch_ratio is None


def test_manual_reset_makes_next_frame_neutral() -> None:
    engine = _engine()

    engine.update(
        _frame(
            frame_id=0,
        )
    )

    ordinary = engine.update(
        _frame(
            frame_id=1,
            pointer_x=0.55,
        )
    )

    assert ordinary.interaction_valid is True

    engine.reset()

    state = engine.update(
        _frame(
            frame_id=2,
            pointer_x=0.90,
        )
    )

    assert state.interaction_valid is False
    assert state.rotation_delta == (0.0, 0.0)
    assert state.scale_delta == 0.0
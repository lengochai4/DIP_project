import pytest

from dip_touchless.core import ROI, ROIState
from dip_touchless.preprocessing import ROIManager


def _manager(
    *,
    coast_frames: int = 2,
    min_width: int = 1,
    min_height: int = 1,
) -> ROIManager:
    return ROIManager(
        padding_ratio=0.20,
        coast_expand_ratio=0.15,
        coast_frames=coast_frames,
        min_width=min_width,
        min_height=min_height,
    )


def _bbox(
    x: int,
    y: int,
    width: int,
    height: int,
) -> ROI:
    return ROI(
        x=x,
        y=y,
        width=width,
        height=height,
        state=ROIState.TRACKING,
    )


def test_initial_missing_hand_uses_full_frame_searching() -> None:
    manager = _manager()

    roi = manager.update(
        frame_width=100,
        frame_height=80,
        hand_bbox=None,
    )

    assert roi == ROI(
        x=0,
        y=0,
        width=100,
        height=80,
        state=ROIState.SEARCHING,
    )

    assert manager.state is ROIState.SEARCHING


def test_valid_bbox_enters_tracking_with_ratio_padding() -> None:
    manager = _manager()

    roi = manager.update(
        frame_width=100,
        frame_height=80,
        hand_bbox=_bbox(
            30,
            20,
            20,
            10,
        ),
    )

    assert roi == ROI(
        x=26,
        y=18,
        width=28,
        height=14,
        state=ROIState.TRACKING,
    )

    assert manager.state is ROIState.TRACKING


def test_tracking_roi_is_kept_inside_frame_bounds() -> None:
    manager = _manager()

    roi = manager.update(
        frame_width=100,
        frame_height=80,
        hand_bbox=_bbox(
            95,
            75,
            10,
            10,
        ),
    )

    assert roi.state is ROIState.TRACKING

    assert roi.x >= 0
    assert roi.y >= 0

    assert (
        roi.x + roi.width
        <= 100
    )

    assert (
        roi.y + roi.height
        <= 80
    )


def test_temporary_loss_enters_coasting() -> None:
    manager = _manager(
        coast_frames=2
    )

    tracking_roi = manager.update(
        frame_width=100,
        frame_height=80,
        hand_bbox=_bbox(
            30,
            20,
            20,
            10,
        ),
    )

    coast_roi = manager.update(
        frame_width=100,
        frame_height=80,
        hand_bbox=None,
    )

    assert tracking_roi.state is ROIState.TRACKING
    assert coast_roi.state is ROIState.COASTING

    assert coast_roi.width >= tracking_roi.width
    assert coast_roi.height >= tracking_roi.height

    assert manager.coast_count == 1


def test_coasting_timeout_returns_to_searching() -> None:
    manager = _manager(
        coast_frames=2
    )

    manager.update(
        frame_width=100,
        frame_height=80,
        hand_bbox=_bbox(
            30,
            20,
            20,
            10,
        ),
    )

    first_loss = manager.update(
        frame_width=100,
        frame_height=80,
        hand_bbox=None,
    )

    second_loss = manager.update(
        frame_width=100,
        frame_height=80,
        hand_bbox=None,
    )

    third_loss = manager.update(
        frame_width=100,
        frame_height=80,
        hand_bbox=None,
    )

    assert first_loss.state is ROIState.COASTING
    assert second_loss.state is ROIState.COASTING

    assert third_loss == ROI(
        x=0,
        y=0,
        width=100,
        height=80,
        state=ROIState.SEARCHING,
    )

    assert manager.state is ROIState.SEARCHING
    assert manager.coast_count == 0


def test_reacquisition_from_coasting_returns_to_tracking() -> None:
    manager = _manager()

    manager.update(
        frame_width=100,
        frame_height=80,
        hand_bbox=_bbox(
            20,
            20,
            20,
            20,
        ),
    )

    manager.update(
        frame_width=100,
        frame_height=80,
        hand_bbox=None,
    )

    reacquired = manager.update(
        frame_width=100,
        frame_height=80,
        hand_bbox=_bbox(
            50,
            30,
            20,
            20,
        ),
    )

    assert reacquired.state is ROIState.TRACKING
    assert manager.state is ROIState.TRACKING
    assert manager.coast_count == 0


def test_unusable_bbox_falls_back_to_searching() -> None:
    manager = _manager()

    manager.update(
        frame_width=100,
        frame_height=80,
        hand_bbox=_bbox(
            20,
            20,
            20,
            20,
        ),
    )

    invalid_for_frame = _bbox(
        150,
        100,
        10,
        10,
    )

    roi = manager.update(
        frame_width=100,
        frame_height=80,
        hand_bbox=invalid_for_frame,
    )

    assert roi == ROI(
        x=0,
        y=0,
        width=100,
        height=80,
        state=ROIState.SEARCHING,
    )

    assert manager.state is ROIState.SEARCHING


def test_minimum_roi_dimensions_are_enforced() -> None:
    manager = _manager(
        min_width=20,
        min_height=16,
    )

    roi = manager.update(
        frame_width=100,
        frame_height=80,
        hand_bbox=_bbox(
            50,
            40,
            2,
            2,
        ),
    )

    assert roi.width >= 20
    assert roi.height >= 16


def test_reset_returns_manager_to_searching() -> None:
    manager = _manager()

    manager.update(
        frame_width=100,
        frame_height=80,
        hand_bbox=_bbox(
            20,
            20,
            20,
            20,
        ),
    )

    manager.reset()

    assert manager.state is ROIState.SEARCHING
    assert manager.coast_count == 0


def test_invalid_frame_dimensions_are_rejected() -> None:
    manager = _manager()

    with pytest.raises(ValueError):
        manager.update(
            frame_width=0,
            frame_height=80,
            hand_bbox=None,
        )
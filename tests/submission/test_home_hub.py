"""Unit tests for VirtualHomeHub (AssistiveTouch floating button and radial app launcher)."""
import numpy as np
import pytest
import yaml
from submission.stem_ui.home_hub import VirtualHomeHub, _sector_polygon

SETTINGS = {
    'stale_after_s': 0.5,
    'mirror': True,
}


def test_sector_polygon_geometry():
    poly = _sector_polygon(100, 100, 20, 50, 0, 90, steps=8)
    assert len(poly) == 16
    # First point on outer rim at angle 0 -> (150, 100)
    assert pytest.approx(poly[0][0]) == 150.0
    assert pytest.approx(poly[0][1]) == 100.0


def test_virtual_home_hub_default_pos_and_center_snap():
    hub = VirtualHomeHub(SETTINGS)
    screen_size = (1280, 800)
    header_h = 70
    pos0 = hub.default_pos(screen_size, header_h)
    assert pos0[0] == 1280 - 95.0
    assert pos0[1] == 70 + 55.0

    # Test center detection
    assert hub.is_center_region(np.array([640.0, 400.0]), screen_size) is True
    assert hub.is_center_region(pos0, screen_size) is False

    # Simulate drag to center and release -> snaps back
    hub.pos = np.array([640.0, 400.0])
    hub.dragging = True
    hub.update(0.05, screen_size, header_h, hands=(), mouse_pos=None, mouse_down=False)
    assert hub.dragging is False
    assert np.allclose(hub.pos, pos0)


def test_virtual_home_hub_dwell_expand_and_select():
    hub = VirtualHomeHub(SETTINGS)
    screen_size = (1000, 700)
    header_h = 60
    hub.pos = hub.default_pos(screen_size, header_h)

    # 1. Hover on home button for dwell_duration -> expands
    ptr = (hub.pos[0], hub.pos[1])
    action = None
    for _ in range(15):
        action = hub.update(0.06, screen_size, header_h, mouse_pos=ptr, mouse_down=False)
    assert hub.expanded is True
    assert action is None

    # 2. Hover on sector (e.g., Physics at top: 270 deg)
    physics_ptr = (hub.pos[0], hub.pos[1] - 80.0)
    triggered = []
    for _ in range(15):
        act = hub.update(0.06, screen_size, header_h, mouse_pos=physics_ptr, mouse_down=False)
        if act:
            triggered.append(act)
    assert 'physics' in triggered
    assert hub.expanded is False

    # 3. Expand again and hover on Tracking sector (left: 180 deg)
    for _ in range(15):
        hub.update(0.06, screen_size, header_h, mouse_pos=ptr, mouse_down=False)
    assert hub.expanded is True
    tracking_ptr = (hub.pos[0] - 80.0, hub.pos[1])
    triggered_tracking = []
    for _ in range(15):
        act = hub.update(0.06, screen_size, header_h, mouse_pos=tracking_ptr, mouse_down=False)
        if act:
            triggered_tracking.append(act)
    assert 'tracking' in triggered_tracking
    assert hub.expanded is False


def test_virtual_home_hub_click():
    hub = VirtualHomeHub(SETTINGS)
    screen_size = (1000, 700)
    header_h = 60
    hub.pos = hub.default_pos(screen_size, header_h)

    # Click on closed hub -> expands
    hub.handle_click((hub.pos[0], hub.pos[1]), screen_size, header_h)
    assert hub.expanded is True

    # Click on center hub -> closes
    hub.handle_click((hub.pos[0], hub.pos[1]), screen_size, header_h)
    assert hub.expanded is False


def test_virtual_home_hub_close_reentry_requirement():
    hub = VirtualHomeHub(SETTINGS)
    screen_size = (1000, 700)
    header_h = 60
    hub.pos = hub.default_pos(screen_size, header_h)

    # 1. Expand via dwell at center
    center_ptr = (hub.pos[0], hub.pos[1])
    for _ in range(15):
        hub.update(0.06, screen_size, header_h, mouse_pos=center_ptr, mouse_down=False)
    assert hub.expanded is True
    assert hub.close_armed is False

    # 2. Lingering at center does NOT trigger close or arm
    for _ in range(15):
        hub.update(0.06, screen_size, header_h, mouse_pos=center_ptr, mouse_down=False)
    assert hub.expanded is True
    assert hub.close_armed is False
    assert hub.dwell_target != 'close'

    # 3. Move outside center circle (dist > inner_radius + 6.0)
    outside_ptr = (hub.pos[0] + 50.0, hub.pos[1])
    hub.update(0.06, screen_size, header_h, mouse_pos=outside_ptr, mouse_down=False)
    assert hub.close_armed is True

    # 4. Move back to center and dwell
    for _ in range(15):
        hub.update(0.06, screen_size, header_h, mouse_pos=center_ptr, mouse_down=False)
    assert hub.expanded is False
    assert hub.close_armed is False


def test_virtual_home_hub_hand_camera_alignment_no_rightward_offset():
    from dataclasses import dataclass
    from submission.stem_ui.camera_space import CameraCover

    @dataclass(frozen=True)
    class Point:
        x: float
        y: float
        z: float = 0.0
        index: int = 0

    @dataclass(frozen=True)
    class MockHand:
        slot: int
        landmarks: tuple
        raw_landmarks: tuple = ()

    hub = VirtualHomeHub(SETTINGS)
    screen_size = (1280, 800)
    view = (20, 68, 1240, 712)
    header_h = 68
    hub.pos = hub.default_pos(screen_size, header_h, view)

    # Landmark 8 placed so its rendered screen position matches hub.pos exactly
    vx, vy, vw, vh = view
    source_aspect = 1.333
    cover = CameraCover(source_aspect, vw / vh)

    target_lx = (hub.pos[0] - vx) / vw
    target_rx = 1.0 - target_lx
    target_ry = (hub.pos[1] - vy) / vh

    raw_x = cover.left + target_rx * cover.width
    raw_y = cover.top + target_ry * cover.height

    lms = [Point(0.5, 0.5, 0.0, i) for i in range(21)]
    lms[8] = Point(raw_x, raw_y, 0.0, 8)
    lms[4] = Point(raw_x + 0.1, raw_y, 0.0, 4)
    hand = MockHand(slot=0, landmarks=tuple(lms))

    # Update with this hand observation
    hub.update(0.05, screen_size, header_h, hands=(hand,), mirror=True, view=view, source_aspect=source_aspect)

    # The hub MUST recognize the dwell target as 'home' because the hand is dead-center on the button!
    assert hub.dwell_target == 'home'


def test_tracking_mode_shows_only_camera_landmarks_and_home_hub():
    import pygame
    from submission.stem_ui.renderer import SubmissionRenderer
    from submission.stem_ui.theme import scene_rect

    pygame.font.init()
    full_settings = yaml.safe_load(open('submission/stem_ui/settings.yaml', encoding='utf-8'))
    r = SubmissionRenderer(full_settings)
    r.enter_chemistry()
    assert r.camera_visible is False

    # Switching to 'tracking' via enter_basic re-enables camera_visible and sets mode='tracking'
    r.enter_basic('tracking')
    assert r.mode == 'tracking'
    assert r.camera_visible is True

    # Full-width scene rect (no right-side camera sidebar)
    view = scene_rect(r.size, r.camera_visible, r.mode)
    assert view[2] == r.size[0] - 40


def test_solid_finger_button_smooth_hysteresis_and_busy_lock():
    from dataclasses import dataclass
    import pygame
    from submission.stem_ui.renderer import SubmissionRenderer

    @dataclass(frozen=True)
    class Point:
        x: float
        y: float
        z: float = 0.0
        index: int = 0

    @dataclass(frozen=True)
    class MockHand:
        slot: int
        landmarks: tuple
        generation: int = 1

    full_settings = yaml.safe_load(open('submission/stem_ui/settings.yaml', encoding='utf-8'))
    full_settings['mirror'] = False
    r = SubmissionRenderer(full_settings)
    r.size = (1000, 700)
    btn_rect = pygame.Rect(30, 120, 190, 32)
    r.buttons = [(btn_rect, 'geom_dropdown')]

    def make_hand(px, py):
        lms = [Point(0.5, 0.5, 0.0, i) for i in range(21)]
        lms[8] = Point(px / 1000.0, py / 700.0, 0.0, 8)
        lms[4] = Point((px + 90.0) / 1000.0, py / 700.0, 0.0, 4)
        return MockHand(slot=0, landmarks=tuple(lms))

    # Hover inside button for 0.30s -> accumulates dwell smoothly and locks _solid_ui_busy
    for _ in range(6):
        r._update_solid_finger_buttons(0.05, (make_hand(100.0, 136.0),))
    assert r._solid_btn_target == 'geom_dropdown'
    assert r._solid_ui_busy is True
    assert pytest.approx(r._solid_btn_dwell, rel=1e-2) == 0.30

    # Brief micro-tremor 4px outside button bottom edge stays captured by magnetic hysteresis
    r._update_solid_finger_buttons(0.05, (make_hand(100.0, 156.0),))
    assert r._solid_btn_target == 'geom_dropdown'
    assert r._solid_btn_dwell > 0.30

    # Completing the 0.65s dwell opens the dropdown
    for _ in range(7):
        r._update_solid_finger_buttons(0.05, (make_hand(100.0, 136.0),))
    assert r.geometry_dropdown_open is True


def test_widescreen_camera_fov_and_isotropic_spatial_mapping():
    from submission.stem_ui.camera_space import CameraCover
    from submission.stem_ui.theme import header_height, scene_rect

    full_settings = yaml.safe_load(open('submission/stem_ui/settings.yaml', encoding='utf-8'))
    assert full_settings['camera_width'] == 1280
    assert full_settings['camera_height'] == 720

    size = (1360, 860)
    vx, vy, vw, vh = scene_rect(size, True, 'solid')
    assert vy == header_height(size[0]) + 12

    source_w, source_h = 1280, 720
    cover = CameraCover(source_w / source_h, vw / vh)
    px_per_cam_x = vw / (cover.width * source_w)
    px_per_cam_y = vh / (cover.height * source_h)
    assert pytest.approx(px_per_cam_x, rel=1e-6) == px_per_cam_y
    assert cover.width == pytest.approx(1.0)
    assert cover.height > 0.90

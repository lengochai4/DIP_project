"""Unit tests for the STEM Optics simulation module."""

import math
import pytest
import pygame

from submission.stem_ui.optics.optics_engine import (
    compute_refraction,
    compute_thin_lens,
    compute_prism_dispersion,
    OPTICS_MATERIALS,
    SPECTRAL_COLORS,
)
from submission.stem_ui.optics.optics_experiments import OpticsLabSession
from submission.stem_ui.optics.optics_view import OpticsVisualizer


def test_refraction_snells_law():
    """Verify Snell's law: n1 * sin(i) = n2 * sin(r)."""
    # Air (1.0) to Glass (1.5), i = 30 deg
    res = compute_refraction(n1=1.0, n2=1.5, i_deg=30.0)
    assert res.is_tir is False
    assert res.r_deg is not None
    # sin(r) = (1.0 / 1.5) * sin(30) = 0.5 / 1.5 = 1/3
    expected_r = math.degrees(math.asin(1.0 / 3.0))
    assert pytest.approx(res.r_deg, 0.01) == expected_r
    assert res.critical_angle_deg is None  # n1 < n2, no critical angle
    assert 0.0 < res.reflectance < 1.0
    assert pytest.approx(res.reflectance + res.transmittance, 1e-5) == 1.0


def test_refraction_total_internal_reflection():
    """Verify Total Internal Reflection when n1 > n2 and i > i_gh."""
    # Glass (1.5) to Air (1.0)
    # sin(i_gh) = 1.0 / 1.5 = 2/3 => i_gh ~ 41.81 deg
    crit_angle = math.degrees(math.asin(1.0 / 1.5))

    # Case 1: i = 30 deg (< i_gh) -> Refraction
    res_sub = compute_refraction(n1=1.5, n2=1.0, i_deg=30.0)
    assert res_sub.is_tir is False
    assert pytest.approx(res_sub.critical_angle_deg, 0.01) == crit_angle
    assert res_sub.r_deg is not None
    assert res_sub.r_deg > 30.0  # bends away from normal

    # Case 2: i = 50 deg (> i_gh) -> Total Internal Reflection
    res_tir = compute_refraction(n1=1.5, n2=1.0, i_deg=50.0)
    assert res_tir.is_tir is True
    assert res_tir.r_deg is None
    assert res_tir.refracted_ray is None
    assert res_tir.reflectance == 1.0
    assert res_tir.transmittance == 0.0


def test_thin_lens_converging_real_image():
    """Verify converging lens (f > 0) producing real image at d = 2f."""
    f = 15.0
    d = 30.0  # d = 2f
    h = 4.0
    res = compute_thin_lens(f=f, d=d, h=h)

    assert res.is_converging is True
    assert res.is_real is True
    assert res.is_virtual is False
    assert res.is_infinity is False
    # d' = (30 * 15) / (30 - 15) = 450 / 15 = 30.0 cm
    assert pytest.approx(res.d_prime, 0.01) == 30.0
    # k = -d' / d = -1.0 (inverted, same size)
    assert pytest.approx(res.k, 0.01) == -1.0
    assert pytest.approx(res.h_prime, 0.01) == -4.0


def test_thin_lens_virtual_magnifier():
    """Verify converging lens producing virtual magnified image when d < f."""
    f = 15.0
    d = 10.0  # d < f
    h = 3.0
    res = compute_thin_lens(f=f, d=d, h=h)

    assert res.is_real is False
    assert res.is_virtual is True
    # d' = (10 * 15) / (10 - 15) = 150 / -5 = -30.0 cm
    assert pytest.approx(res.d_prime, 0.01) == -30.0
    # k = -(-30) / 10 = +3.0 (upright, 3x magnified)
    assert pytest.approx(res.k, 0.01) == 3.0
    assert pytest.approx(res.h_prime, 0.01) == 9.0


def test_thin_lens_diverging():
    """Verify diverging lens (f < 0) always gives virtual, upright, diminished image."""
    f = -15.0
    d = 30.0
    h = 4.0
    res = compute_thin_lens(f=f, d=d, h=h)

    assert res.is_converging is False
    assert res.is_real is False
    assert res.is_virtual is True
    # d' = (30 * -15) / (30 - (-15)) = -450 / 45 = -10.0 cm
    assert pytest.approx(res.d_prime, 0.01) == -10.0
    # k = -(-10) / 30 = +1/3 (diminished)
    assert pytest.approx(res.k, 0.01) == (1.0 / 3.0)


def test_prism_dispersion():
    """Verify prism dispersion: violet deviates more than red."""
    res = compute_prism_dispersion(apex_deg=60.0, i1_deg=48.0, material='flint_glass')
    assert len(res.color_rays) == 7
    assert res.apex_angle_deg == 60.0

    # Get red and violet deviation
    d_red = res.color_rays[0].deviation_deg
    d_violet = res.color_rays[-1].deviation_deg

    assert d_red is not None
    assert d_violet is not None
    # Cauchy dispersion: Violet bends more than red
    assert d_violet > d_red
    assert res.angular_spread_deg > 0.5


def test_optics_session_and_presets():
    """Verify session state management, catalog loading and preset application."""
    session = OpticsLabSession(initial_lab='refraction')
    assert session.current_lab == 'refraction'

    # Apply preset
    session.apply_preset('glass_to_air_tir')
    assert session.get_param('incident_angle') == 50.0

    res = session.evaluate()
    assert isinstance(res, compute_refraction.__annotations__['return'])
    assert res.is_tir is True

    # Switch to lens
    session.select_lab('lens')
    assert session.current_lab == 'lens'
    session.apply_preset('virtual_magnifier')
    res_lens = session.evaluate()
    assert res_lens.is_virtual is True

    # Switch to prism
    session.select_lab('prism')
    assert session.current_lab == 'prism'
    res_prism = session.evaluate()
    assert len(res_prism.color_rays) == 7


def test_optics_visualizer_rendering():
    """Verify Pygame visualizer renders all 3 labs without exceptions."""
    pygame.font.init()
    surf = pygame.Surface((1280, 800))
    session = OpticsLabSession()
    vis = OpticsVisualizer(session=session)

    # 1. Test Refraction render
    session.select_lab('refraction')
    vis.draw(surf, (100, 100))

    # 2. Test Lens render
    session.select_lab('lens')
    vis.draw(surf, (100, 100))

    # 3. Test Prism render
    session.select_lab('prism')
    vis.draw(surf, (100, 100))


def test_optics_home_hub_and_renderer_integration():
    """Verify that Optics is fully integrated into VirtualHomeHub and SubmissionRenderer."""
    from submission.stem_ui.home_hub import VirtualHomeHub
    settings = {'stale_after_s': 0.5, 'mirror': True}
    hub = VirtualHomeHub(settings)

    # Check that 'optics' is one of the sectors
    sector_ids = [s['id'] for s in hub.sectors]
    assert 'optics' in sector_ids
    assert 'solid' in sector_ids
    assert 'chemistry' in sector_ids
    assert 'physics' in sector_ids
    assert 'tracking' in sector_ids

    # Check hovering on optics sector (angle around 120 deg)
    screen_size = (1000, 700)
    header_h = 60
    hub.pos = hub.default_pos(screen_size, header_h)
    hub.expanded = True

    optics_ptr = (hub.pos[0] + 80.0 * math.cos(math.radians(120)),
                  hub.pos[1] + 80.0 * math.sin(math.radians(120)))
    triggered = []
    for _ in range(15):
        act = hub.update(0.06, screen_size, header_h, mouse_pos=optics_ptr, mouse_down=False)
        if act:
            triggered.append(act)
    assert 'optics' in triggered


def test_physics_view_optics_category_and_integration():
    """Verify Optics labs are directly discoverable and selectable from PhysicsView."""
    from types import SimpleNamespace
    from test_stem_ui import SETTINGS
    from submission.stem_ui.camera_space import CameraSpace
    from submission.stem_ui.physics_view import PhysicsView

    pygame.font.init()
    switched = []
    host = SimpleNamespace(
        help_visible=True,
        screenshot=lambda path: None,
        enter_optics=lambda lab: switched.append(lab),
    )
    v = PhysicsView(SETTINGS, host)
    v.content = (20, 100, 960, 600)
    v.space = CameraSpace(960 / 600)
    v.layout()
    v.setup_projection()

    # Default category is mechanics
    assert v.library_category == 'mechanics'

    # Switch category to optics
    v.command('category:optics')
    assert v.library_category == 'optics'
    v.library = True
    v._paint_panel()

    # Verify optics lab targets are present
    optics_targets = [act for r, act in v.targets if act.startswith('optics:')]
    assert 'optics:refraction' in optics_targets
    assert 'optics:lens' in optics_targets
    assert 'optics:prism' in optics_targets

    # Select optics:lens
    v.command('optics:lens')
    assert switched == ['lens']

    # Switch back to mechanics
    v.command('category:mechanics')
    assert v.library_category == 'mechanics'
    v.library = True
    v._paint_panel()
    mech_targets = [act for r, act in v.targets if act.startswith('lab:')]
    assert len(mech_targets) > 0


def test_optics_visualizer_camera_ar_and_touchless_drag():
    """Verify camera AR backdrop rendering and touchless drag interaction in OpticsVisualizer."""
    pygame.font.init()
    surf = pygame.Surface((1280, 800), pygame.SRCALPHA)
    session = OpticsLabSession(initial_lab='refraction')
    vis = OpticsVisualizer(session=session)

    # 1. Draw with camera_active=True (AR mode)
    vis.draw(surf, (100, 100), camera_active=True)
    assert vis.last_stage_rect is not None
    assert vis.last_panel_rect is not None

    # 2. Test touchless drag for Refraction (rotating incident angle)
    sr = vis.last_stage_rect
    cx, cy = sr.centerx, sr.centery
    # Point in upper-left quadrant
    drag_pt = (cx - 100, cy - 100)
    vis.handle_drag(drag_pt, is_pinch=True)
    # Incident angle should be around 45 degrees
    assert 40.0 <= session.get_param('incident_angle') <= 50.0

    # 3. Test touchless drag for Thin Lens (moving object distance & height)
    session.select_lab('lens')
    vis.draw(surf, (100, 100), camera_active=True)
    lens_pt = (cx - 150, cy - 80)
    vis.handle_drag(lens_pt, is_pinch=True)
    assert session.get_param('object_distance') > 5.0
    assert session.get_param('object_height') > 1.0

    # 4. Test touchless drag for Prism (rotating beam angle)
    session.select_lab('prism')
    vis.draw(surf, (100, 100), camera_active=True)
    prism_pt = (cx - 80, cy + 50)
    vis.handle_drag(prism_pt, is_pinch=True)
    assert 30.0 <= session.get_param('incident_angle') <= 75.0

    # 5. Test switch to mechanics button click
    click_res = vis.handle_click(vis.tab_targets[0][0].center)
    assert click_res == 'mechanics'



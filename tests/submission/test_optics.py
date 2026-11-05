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


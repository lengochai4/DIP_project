"""Mesh invariants and actual framebuffer depth occlusion where OpenGL is available."""

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication
from app.config import ProductConfig, Settings
from app.extensions.base import Geometry, Ball, Face, Line
from app.extensions.registry import ExtensionRegistry
from app.rendering.gpu import mesh, sphere
from app.rendering.transforms import Projection
from app.rendering.viewport import Viewport


def test_sphere_and_surface_mesh_has_finite_positions_and_unit_normals():
    unit = sphere()
    assert np.linalg.norm(unit, axis=1) == pytest.approx(np.ones(len(unit)), abs=1e-6)
    geometry = Geometry(
        balls=(Ball((0, 0, 0), 0.5),),
        lines=(Line((0, 0, 0), (0, 0, 1), width=6),),
        faces=(Face((0, 0, 0), (1, 0, 0), (0, 1, 0)),),
    )
    triangles, lines = mesh(
        geometry, Projection(640, 480, (320, 240), 100, np.eye(3), 8), True
    )
    assert triangles.shape[1] == 9 and len(triangles) % 3 == 0
    assert np.isfinite(triangles).all()
    assert np.linalg.norm(triangles[:, 3:6], axis=1) == pytest.approx(
        np.ones(len(triangles)), abs=1e-6
    )


def test_gpu_depth_occludes_far_sphere_even_when_far_sphere_drawn_last():
    qt = QApplication.instance() or QApplication([])
    registry = ExtensionRegistry(ProductConfig())
    lab = registry.current
    lab.yaw = lab.pitch = 0.0
    original = lab.render
    lab.render = lambda: Geometry(
        balls=(Ball((0, 0, 1), 0.5, "#0000ff"), Ball((0, 0, 0), 0.5, "#ff0000"))
    )
    view = Viewport(registry, ProductConfig(), Settings(object_labels=False))
    view.resize(640, 480)
    view.show()
    qt.processEvents()
    try:
        if not view.isValid() or view.gpu_renderer is None or view.gpu_error:
            pytest.skip("This platform has no usable mesh OpenGL context")
        image = view.grabFramebuffer()
        center = image.pixelColor(image.width() // 2, image.height() // 2)
        assert center.blue() > center.red() * 2
        assert view.gpu_error is None
    finally:
        view.close_renderer()
        view.close()
        lab.render = original
        registry.close()
        qt.processEvents()

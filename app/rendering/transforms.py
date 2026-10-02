"""One invertible orthographic scene projection shared by painting and picking."""

from dataclasses import dataclass
import math
import numpy as np


def rotation(yaw, pitch, roll=0.0):
    cy, sy, cp, sp, cr, sr = (
        math.cos(yaw),
        math.sin(yaw),
        math.cos(pitch),
        math.sin(pitch),
        math.cos(roll),
        math.sin(roll),
    )
    return (
        np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1.0]])
        @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
        @ np.array([[1.0, 0, 0], [0, cp, -sp], [0, sp, cp]])
    )


@dataclass
class Projection:
    width: int
    height: int
    center: tuple[float, float]
    pixels_per_unit: float
    matrix: np.ndarray

    def project(self, point):
        p = self.matrix @ np.asarray(point, dtype=float)
        return (
            self.center[0] + p[0] * self.pixels_per_unit,
            self.center[1] - p[1] * self.pixels_per_unit,
            p[2],
        )

    def plane_point(self, xy, normal=(0.0, 0.0, 1.0)):
        screen = np.array(
            [
                (xy[0] * self.width - self.center[0]) / self.pixels_per_unit,
                -(xy[1] * self.height - self.center[1]) / self.pixels_per_unit,
            ]
        )
        plane = np.vstack((self.matrix[:2], np.asarray(normal, float)))
        if abs(np.linalg.det(plane)) < 1e-6:
            return None
        p = np.linalg.solve(plane, np.array((*screen, 0.0)))
        return tuple(float(v) for v in p)


def fit_rect(width, height, image_width, image_height):
    scale = min(width / image_width, height / image_height)
    w, h = image_width * scale, image_height * scale
    return ((width - w) / 2, (height - h) / 2, w, h)

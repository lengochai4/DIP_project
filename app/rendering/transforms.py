"""Shared orthographic/perspective projection with matching ray/plane picking."""

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
    camera_distance: float | None = None
    near: float = 0.1
    far: float = 100.0

    def project(self, point):
        p = self.matrix @ np.asarray(point, dtype=float)
        factor = (
            1.0
            if self.camera_distance is None
            else self.camera_distance / max(self.near, self.camera_distance - p[2])
        )
        return (
            self.center[0] + p[0] * self.pixels_per_unit * factor,
            self.center[1] - p[1] * self.pixels_per_unit * factor,
            p[2],
        )

    def plane_point(self, xy, normal=(0.0, 0.0, 1.0)):
        if self.camera_distance is not None:
            origin, direction = self.ray(xy)
            denom = np.dot(normal, direction)
            if abs(denom) < 1e-6:
                return None
            t = -np.dot(normal, origin) / denom
            p = origin + t * direction
            return tuple(float(v) for v in p) if t > 0 and self.visible(p) else None
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

    def ray(self, xy):
        screen = np.array(
            (
                (xy[0] * self.width - self.center[0]) / self.pixels_per_unit,
                -(xy[1] * self.height - self.center[1]) / self.pixels_per_unit,
                0.0,
            )
        )
        d = self.camera_distance or self.far
        origin = self.matrix.T @ (
            np.array((0.0, 0.0, d)) if self.camera_distance else screen + (0.0, 0.0, d)
        )
        direction = self.matrix.T @ (
            screen - (0.0, 0.0, d)
            if self.camera_distance
            else np.array((0.0, 0.0, -1.0))
        )
        return origin, direction / np.linalg.norm(direction)

    def point_at_view_depth(self, xy, depth):
        """Projective scene point with a visual depth cue; not camera reconstruction."""
        if not math.isfinite(depth) or not all(math.isfinite(v) for v in xy):
            return None
        origin, direction = self.ray(xy)
        view_origin, view_direction = self.matrix @ origin, self.matrix @ direction
        if abs(view_direction[2]) < 1e-9:
            return None
        t = (depth - view_origin[2]) / view_direction[2]
        point = origin + t * direction
        return tuple(float(v) for v in point) if t > 0 and self.visible(point) else None

    def visible(self, point):
        if self.camera_distance is None:
            return True
        depth = self.camera_distance - (self.matrix @ np.asarray(point))[2]
        return self.near < depth < self.far

    def radius(self, point, radius):
        depth = (
            1.0
            if self.camera_distance is None
            else self.camera_distance
            / max(
                self.near, self.camera_distance - (self.matrix @ np.asarray(point))[2]
            )
        )
        return radius * self.pixels_per_unit * depth

    def clip_matrix(self):
        """Local scene -> OpenGL clip space, exactly matching project()."""
        d = self.camera_distance
        result = np.zeros((4, 4), dtype=np.float32)
        ox, oy = (
            2 * self.center[0] / self.width - 1,
            1 - 2 * self.center[1] / self.height,
        )
        if d is None:
            result[:2, :3] = (
                self.matrix[:2]
                * np.array(
                    (
                        2 * self.pixels_per_unit / self.width,
                        2 * self.pixels_per_unit / self.height,
                    )
                )[:, None]
            )
            result[0, 3], result[1, 3], result[3, 3] = ox, oy, 1.0
            result[2, :3] = -self.matrix[2] / self.far
        else:
            result[0, :3] = (
                2 * self.pixels_per_unit * d / self.width * self.matrix[0]
                - ox * self.matrix[2]
            )
            result[1, :3] = (
                2 * self.pixels_per_unit * d / self.height * self.matrix[1]
                - oy * self.matrix[2]
            )
            result[0, 3], result[1, 3] = ox * d, oy * d
            a = -(self.far + self.near) / (self.far - self.near)
            result[2, :3] = a * self.matrix[2]
            result[2, 3] = -a * d - 2 * self.far * self.near / (self.far - self.near)
            result[3, :3], result[3, 3] = -self.matrix[2], d
        return result


def fit_rect(width, height, image_width, image_height):
    scale = min(width / image_width, height / image_height)
    w, h = image_width * scale, image_height * scale
    return ((width - w) / 2, (height - h) / 2, w, h)

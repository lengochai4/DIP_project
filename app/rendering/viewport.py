"""Perspective GPU mesh/depth renderer with a shared software fallback and HAND frame."""

import math
import numpy as np
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QRadialGradient, QImage, QPolygonF
from PySide6.QtWidgets import QWidget
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from app.interaction.contracts import GestureIntent, IntentType, Phase
from app.interaction.hand_geometry import EDGES
from .transforms import Projection, rotation, fit_rect


class SurfaceMixin:
    def setup(self, registry, config, settings):
        self.registry, self.config, self.settings = registry, config, settings
        self.mode = "WORLD"
        self.image = None
        self.landmarks = {}
        self.anchor = None
        self.reference_plane = None
        self.pointer_source = None
        self.live_sources = ()
        self.pointer = None
        self.message = "Start camera, or explore using mouse and keyboard"
        self._mouse = None
        self.setMinimumSize(420, 320)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

    @property
    def pointer(self):
        # Layout/HiDPI changes can occur after a frame callback (e.g. Inspector
        # expansion). Resolve the camera tip against the current rect at paint.
        if self.pointer_source is not None:
            return self.source_pointer(self.pointer_source)
        return self._pointer

    @pointer.setter
    def pointer(self, value):
        self.pointer_source = None
        self._pointer = value

    def image_rect(self):
        if self.image is None:
            return (0.0, 0.0, float(self.width()), float(self.height()))
        return fit_rect(
            self.width(), self.height(), self.image.width(), self.image.height()
        )

    def projection(self):
        lab = self.registry.current
        if self.mode == "HAND" and self.anchor is not None:
            a = self.anchor
            x, y, w, h = self.image_rect()
            cx = 1 - a.center_xy[0] if self.settings.mirror else a.center_xy[0]
            center = (x + cx * w, y + a.center_xy[1] * h)
            # Span is aspect-correct image-height units.
            unit = h * a.span * self.config.anchor_gain * lab.scale
            roll = math.pi - a.roll_rad if self.settings.mirror else a.roll_rad
            matrix = rotation(lab.yaw + a.yaw_rad, lab.pitch + a.pitch_rad, -roll)
        else:
            center = (self.width() / 2, self.height() / 2)
            unit = (
                min(self.width(), self.height())
                * self.config.world_fit_fraction
                / (2 * lab.view_radius)
                * lab.scale
            )
            matrix = rotation(lab.yaw, lab.pitch)
        return Projection(
            self.width(),
            self.height(),
            center,
            max(unit, 1.0),
            matrix,
            self.config.camera_distance,
        )

    def frame_pointer(self, xy):
        """Mirrored normalized source xy -> displayed camera rect -> viewport xy."""
        if self.mode == "HAND":
            x, y, w, h = self.image_rect()
            return ((x + xy[0] * w) / self.width(), (y + xy[1] * h) / self.height())
        return xy

    def source_pointer(self, xy):
        """Unmirrored camera xy -> displayed camera rect, without control gain."""
        if xy is None or not all(0 <= v <= 1 for v in xy):
            return None
        mirrored = (1 - xy[0] if self.settings.mirror else xy[0], xy[1])
        return self.frame_pointer(mirrored)

    def fingertip_pointer(self, xy):
        """Camera-aligned fingertip data in either scene mode, no UI gain/clamp."""
        if not all(0 <= v <= 1 for v in xy):
            return None
        x, y, w, h = self.image_rect()
        return (
            (x + (1 - xy[0] if self.settings.mirror else xy[0]) * w) / self.width(),
            (y + xy[1] * h) / self.height(),
        )

    def fingertip_point(self, xy, relative_z):
        if self.mode == "HAND" and self.anchor is None:
            return None
        mapped = self.fingertip_pointer(xy)
        if mapped is None:
            return None
        projection = self.projection()
        _, _, w, _ = self.image_rect()
        depth = (
            -relative_z
            * w
            * self.config.fingertip_depth_gain
            / projection.pixels_per_unit
        )
        limit = min(
            self.config.fingertip_depth_limit,
            self.config.camera_distance - projection.near * 2,
        )
        return projection.point_at_view_depth(mapped, max(-limit, min(limit, depth)))

    def scene_point(self, xy):
        """Viewport-normalized control pointer -> scene construction plane."""
        if self.mode == "HAND" and self.anchor is None:
            return None
        if not all(0.0 <= v <= 1.0 for v in xy):
            return None
        point = self.projection().plane_point(xy, self.plane_normal())
        if (
            point is None
            or not self.settings.construction_snap
            or self.registry.current.tool == "Inspect"
        ):
            return point
        normal = np.asarray(self.plane_normal(), dtype=float)
        normal /= np.linalg.norm(normal)
        axis = (1, 0, 0) if abs(normal[0]) < 0.9 else (0, 1, 0)
        u = np.cross(normal, axis)
        u /= np.linalg.norm(u)
        v = np.cross(normal, u)
        step = self.config.construction_grid_step
        return tuple(
            step
            * (round(np.dot(point, u) / step) * u + round(np.dot(point, v) / step) * v)
        )

    def plane_normal(self):
        a = self.reference_plane
        if a is None or self.mode == "HAND":
            return (0.0, 0.0, 1.0)
        return (
            math.sin(a.yaw_rad) * math.cos(a.pitch_rad),
            -math.sin(a.pitch_rad),
            math.cos(a.yaw_rad) * math.cos(a.pitch_rad),
        )

    def pick_point(self, xy):
        """Ray against projected sphere silhouettes before falling back to z=0 plane."""
        return self.pick_viewport(xy)

    def pick_viewport(self, mapped):
        if self.mode == "HAND" and self.anchor is None:
            return None
        if not all(0.0 <= v <= 1.0 for v in mapped):
            return None
        projection = self.projection()
        origin, direction = projection.ray(mapped)
        candidates = []
        for ball in self.registry.current.render().balls:
            offset = origin - ball.center
            b = np.dot(offset, direction)
            disc = b * b - np.dot(offset, offset) + ball.radius * ball.radius
            if disc >= 0:
                t = -b - math.sqrt(disc)
                if t > 0 and projection.visible(origin + t * direction):
                    candidates.append((t, ball.center))
        return (
            min(candidates, key=lambda p: p[0])[1]
            if candidates
            else self.scene_point(mapped)
        )

    def paint_surface(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#101a22"))
        if self.mode == "HAND":
            if self.image is not None:
                img = (
                    self.image.mirrored(True, False)
                    if self.settings.mirror
                    else self.image
                )
                painter.drawImage(QRectF(*self.image_rect()), img)
                if self.settings.skeleton:
                    x, y, w, h = self.image_rect()
                    for landmarks in self.landmarks.values():
                        pts = {
                            p.index: QPointF(
                                x + (1 - p.x if self.settings.mirror else p.x) * w,
                                y + p.y * h,
                            )
                            for p in landmarks
                        }
                        painter.setPen(QPen(QColor("#72bfcc"), 2.0))
                        for a, b in EDGES:
                            if a in pts and b in pts:
                                painter.drawLine(pts[a], pts[b])
            if self.anchor is None:
                self._draw_pointer(painter)
                self._caption(
                    painter,
                    (
                        "Show extended fingertips to create live geometry on your hand."
                        if self.settings.geometry_mode == "LIVE"
                        else "Open palm once to anchor, then point/pinch. WORLD: independent scene controls"
                    ),
                    True,
                )
                painter.end()
                return
        projection = self.projection()
        geometry = self.registry.current.render()
        gpu = getattr(self, "gpu_renderer", None)
        hardware = False
        if gpu is not None and not self.gpu_error:
            painter.beginNativePainting()
            try:
                ratio = self.devicePixelRatioF()
                gpu.draw(
                    geometry,
                    projection,
                    (round(self.width() * ratio), round(self.height() * ratio)),
                    self.settings.grid,
                )
                hardware = True
            except Exception as exc:
                self.gpu_error = str(exc)
            finally:
                painter.endNativePainting()
        objects = []
        for face in () if hardware else geometry.faces:
            if not all(projection.visible(p) for p in (face.a, face.b, face.c)):
                continue
            points = [projection.project(p) for p in (face.a, face.b, face.c)]
            objects.append((sum(p[2] for p in points) / 3, "face", face, points, None))
        for line in () if hardware else geometry.lines:
            if not all(projection.visible(p) for p in (line.a, line.b)):
                continue
            a, b = projection.project(line.a), projection.project(line.b)
            if not self.settings.grid and line.color in {"#283d47", "#42545c"}:
                continue
            objects.append(((a[2] + b[2]) / 2, "line", line, a, b))
        for ball in () if hardware else geometry.balls:
            if not projection.visible(ball.center):
                continue
            p = projection.project(ball.center)
            objects.append((p[2], "ball", ball, p, None))
        for _, kind, obj, a, b in sorted(objects, key=lambda o: o[0]):
            if kind == "face":
                normal = np.cross(np.array(obj.b) - obj.a, np.array(obj.c) - obj.a)
                norm = np.linalg.norm(normal)
                light = np.array((-0.4, 0.7, 1.0))
                brightness = 0.25 + 0.75 * abs(
                    np.dot(
                        projection.matrix @ (normal / max(norm, 1e-9)),
                        light / np.linalg.norm(light),
                    )
                )
                color = QColor(obj.color)
                color.setRgbF(
                    *(
                        v * brightness
                        for v in (color.redF(), color.greenF(), color.blueF())
                    )
                )
                painter.setBrush(color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawPolygon(QPolygonF([QPointF(*p[:2]) for p in a]))
            elif kind == "line":
                painter.setPen(QPen(QColor(obj.color), obj.width))
                painter.drawLine(QPointF(*a[:2]), QPointF(*b[:2]))
            else:
                radius = max(2.0, projection.radius(obj.center, obj.radius))
                gradient = QRadialGradient(
                    QPointF(a[0] - radius * 0.3, a[1] - radius * 0.3), radius * 1.5
                )
                color = QColor(obj.color)
                gradient.setColorAt(0, color.lighter(145))
                gradient.setColorAt(0.5, color)
                gradient.setColorAt(1, color.darker(190))
                painter.setBrush(gradient)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(*a[:2]), radius, radius)
                if obj.label and self.settings.object_labels:
                    painter.setPen(QColor("#e5eef1"))
                    painter.drawText(QPointF(a[0] + radius + 5, a[1]), obj.label)
        if hardware and self.settings.object_labels:
            for ball in geometry.balls:
                if ball.label and projection.visible(ball.center):
                    x, y, _ = projection.project(ball.center)
                    painter.setPen(QColor("#e5eef1"))
                    painter.drawText(
                        QPointF(x + projection.radius(ball.center, ball.radius) + 5, y),
                        ball.label,
                    )
        if self.settings.object_labels:
            for point, label in geometry.labels:
                if not projection.visible(point):
                    continue
                x, y, _ = projection.project(point)
                painter.setPen(QColor("#e5eef1"))
                painter.drawText(QPointF(x, y), label)
        self._draw_pointer(painter)
        renderer = "GPU / depth test" if hardware else "Software / approximate depth"
        self._caption(
            painter,
            self.registry.current.title
            + "  ·  "
            + self.mode
            + "\n"
            + self.registry.current.dimensionality
            + "  ·  "
            + renderer,
        )
        origin = QPointF(48, self.height() - 46)
        for axis, name, color in (
            (0, "X", "#dd857c"),
            (1, "Y", "#89b895"),
            (2, "Z", "#839fc7"),
        ):
            tip = origin + QPointF(
                projection.matrix[0, axis] * 28, -projection.matrix[1, axis] * 28
            )
            painter.setPen(QPen(QColor(color), 2))
            painter.drawLine(origin, tip)
            painter.drawText(tip + QPointF(4, 0), name)
        painter.end()

    def _draw_pointer(self, painter):
        for source in self.live_sources:
            mapped = self.fingertip_pointer(source)
            if mapped is not None:
                x, y = mapped
                painter.setPen(QPen(QColor("#efca82"), 2.0))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(
                    QPointF(x * self.width(), y * self.height()), 8.0, 8.0
                )
        if self.pointer is not None:
            x, y = self.pointer
            painter.setPen(QPen(QColor("#efca82"), 2.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(x * self.width(), y * self.height()), 9.0, 9.0)

    def _caption(self, painter, text, center=False):
        painter.setPen(QColor("#e5eef1"))
        painter.drawText(
            self.rect().adjusted(20, 20, -20, -20),
            (
                Qt.AlignmentFlag.AlignCenter
                if center
                else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            )
            | Qt.TextFlag.TextWordWrap,
            text,
        )

    def mousePressEvent(self, event):
        if self.settings.mouse_fallback and event.button() == Qt.MouseButton.LeftButton:
            self._mouse = event.position()
            xy = (
                event.position().x() / self.width(),
                event.position().y() / self.height(),
            )
            self.manual.emit("begin", xy)

    def mouseMoveEvent(self, event):
        if not self.settings.mouse_fallback:
            return
        pos = event.position()
        if self._mouse is not None and event.buttons() & Qt.MouseButton.LeftButton:
            delta = (
                (pos.x() - self._mouse.x()) / self.width() * self.config.motion_gain,
                (pos.y() - self._mouse.y()) / self.height() * self.config.motion_gain,
            )
            self.manual.emit("drag", delta)
            self._mouse = pos
        else:
            self.manual.emit("point", (pos.x() / self.width(), pos.y() / self.height()))

    def mouseReleaseEvent(self, event):
        self._mouse = None
        self.manual.emit("release", ())

    def wheelEvent(self, event):
        if self.settings.mouse_fallback:
            self.manual.emit("scale", (math.exp(event.angleDelta().y() / 120 * 0.1),))


class Viewport(SurfaceMixin, QOpenGLWidget):
    manual = Signal(str, object)

    def __init__(self, registry, config, settings, parent=None):
        super().__init__(parent)
        self.gpu_renderer = None
        self.gpu_error = None
        self.setup(registry, config, settings)

    def initializeGL(self):
        from .gpu import MeshRenderer

        try:
            self.gpu_renderer = MeshRenderer()
            self.context().aboutToBeDestroyed.connect(self.close_renderer)
        except Exception as exc:
            self.gpu_error = str(exc)

    def close_renderer(self):
        if self.gpu_renderer is not None and self.isValid():
            self.makeCurrent()
            try:
                self.gpu_renderer.close()
            finally:
                self.gpu_renderer = None
                self.doneCurrent()

    def paintGL(self):
        self.paint_surface()


class SoftwareViewport(SurfaceMixin, QWidget):
    manual = Signal(str, object)

    def __init__(self, registry, config, settings, parent=None):
        super().__init__(parent)
        self.setup(registry, config, settings)

    def paintEvent(self, event):
        self.paint_surface()


def bgr_image(image):
    import cv2

    rgb = np.ascontiguousarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    h, w = rgb.shape[:2]
    return QImage(rgb.data, w, h, rgb.strides[0], QImage.Format.Format_RGB888).copy()

"""Qt OpenGL-backed 3D projection, depth-ordered painter geometry, shared HAND mode.

QPainter owns GPU resources through Qt. The software surface uses the identical
projection and scene, for platforms without a usable OpenGL context.
"""

import math
import numpy as np
from PySide6.QtCore import Qt, QPointF, QRectF, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QRadialGradient, QImage
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
        self.pointer = None
        self.message = "Start camera, or explore using mouse and keyboard"
        self._mouse = None
        self.setMinimumSize(420, 320)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

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
            unit = min(self.width(), self.height()) * 0.18 * lab.scale
            matrix = rotation(lab.yaw, lab.pitch)
        return Projection(self.width(), self.height(), center, max(unit, 1.0), matrix)

    def frame_pointer(self, xy):
        """Mirrored normalized source xy -> displayed camera rect -> viewport xy."""
        if self.mode == "HAND":
            x, y, w, h = self.image_rect()
            return ((x + xy[0] * w) / self.width(), (y + xy[1] * h) / self.height())
        return xy

    def scene_point(self, xy):
        """Viewport-normalized control pointer -> scene construction plane."""
        if not all(0.0 <= v <= 1.0 for v in xy):
            return None
        return self.projection().plane_point(xy, self.plane_normal())

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
        if not all(0.0 <= v <= 1.0 for v in mapped):
            return None
        projection = self.projection()
        candidates = []
        for ball in self.registry.current.render().balls:
            x, y, z = projection.project(ball.center)
            d = math.hypot(mapped[0] * self.width() - x, mapped[1] * self.height() - y)
            if d <= max(8.0, ball.radius * projection.pixels_per_unit):
                candidates.append((z, ball.center))
        return (
            max(candidates, key=lambda p: p[0])[1]
            if candidates
            else projection.plane_point(mapped, self.plane_normal())
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
                self._caption(painter, "Open your palm to present this lab", True)
                painter.end()
                return
        projection = self.projection()
        geometry = self.registry.current.render()
        objects = []
        for line in geometry.lines:
            a, b = projection.project(line.a), projection.project(line.b)
            if not self.settings.grid and line.color in {"#283d47", "#42545c"}:
                continue
            objects.append(((a[2] + b[2]) / 2, "line", line, a, b))
        for ball in geometry.balls:
            p = projection.project(ball.center)
            objects.append((p[2], "ball", ball, p, None))
        for _, kind, obj, a, b in sorted(objects, key=lambda o: o[0]):
            if kind == "line":
                painter.setPen(QPen(QColor(obj.color), obj.width))
                painter.drawLine(QPointF(*a[:2]), QPointF(*b[:2]))
            else:
                radius = max(2.0, obj.radius * projection.pixels_per_unit)
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
        if self.settings.object_labels:
            for point, label in geometry.labels:
                x, y, _ = projection.project(point)
                painter.setPen(QColor("#e5eef1"))
                painter.drawText(QPointF(x, y), label)
        if self.pointer is not None:
            x, y = self.pointer
            painter.setPen(QPen(QColor("#efca82"), 2.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(x * self.width(), y * self.height()), 9.0, 9.0)
        self._caption(painter, self.registry.current.title + "  ·  " + self.mode)
        painter.end()

    def _caption(self, painter, text, center=False):
        painter.setPen(QColor("#e5eef1"))
        painter.drawText(
            self.rect().adjusted(20, 20, -20, -20),
            (
                Qt.AlignmentFlag.AlignCenter
                if center
                else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
            ),
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
        self.setup(registry, config, settings)

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

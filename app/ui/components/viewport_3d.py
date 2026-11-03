"""Interactive 3D STEM Viewport supporting Coordinate Geometry, Molecular Structures, and Orbital Systems."""

from __future__ import annotations

import math
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QFrame, QWidget


class Viewport3D(QFrame):
    """High-performance 3D STEM Viewport with real-time gesture rotation and scale manipulation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #080C14;
                border: 1px solid #1F2937;
                border-radius: 14px;
            }
        """)
        self.setMinimumSize(400, 360)

        # 3D Transform State
        self.yaw: float = 25.0    # Degrees
        self.pitch: float = -20.0  # Degrees
        self.scale: float = 1.0   # Scale factor [0.5, 3.0]
        self.active_scene: str = "coordinate"  # 'coordinate', 'molecule', 'orbital'

        # Animation ticker
        self._orbital_angle: float = 0.0

    def set_transform(self, yaw_delta: float, pitch_delta: float, scale_factor: float) -> None:
        """Apply smooth delta transformation from gesture engine."""
        self.yaw = (self.yaw + yaw_delta) % 360.0
        # Bound pitch to avoid gimbal flip
        self.pitch = max(-85.0, min(85.0, self.pitch + pitch_delta))
        self.scale = max(0.4, min(3.0, self.scale * scale_factor))
        self.update()

    def reset_transform(self) -> None:
        """Reset view to canonical default."""
        self.yaw = 25.0
        self.pitch = -20.0
        self.scale = 1.0
        self.update()

    def set_scene(self, scene_name: str) -> None:
        """Switch between STEM demonstration scenes."""
        self.active_scene = scene_name
        self.update()

    def tick(self) -> None:
        """Idle animation tick for orbital physics."""
        self._orbital_angle = (self._orbital_angle + 1.2) % 360.0
        if self.active_scene == "orbital":
            self.update()

    def _project_3d(
        self,
        x: float,
        y: float,
        z: float,
        cx: float,
        cy: float,
        zoom: float,
    ) -> tuple[float, float, float]:
        """Rotate point (x, y, z) by yaw & pitch, then apply perspective projection."""
        # Convert degrees to radians
        rad_y = math.radians(self.yaw)
        rad_p = math.radians(self.pitch)

        # Rotate around Y-axis (Yaw)
        x1 = x * math.cos(rad_y) + z * math.sin(rad_y)
        y1 = y
        z1 = -x * math.sin(rad_y) + z * math.cos(rad_y)

        # Rotate around X-axis (Pitch)
        x2 = x1
        y2 = y1 * math.cos(rad_p) - z1 * math.sin(rad_p)
        z2 = y1 * math.sin(rad_p) + z1 * math.cos(rad_p)

        # Perspective projection
        distance = 500.0
        factor = distance / (distance + z2) if (distance + z2) > 10 else 1.0
        px = cx + x2 * zoom * factor
        py = cy - y2 * zoom * factor
        return px, py, z2

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0
        base_zoom = min(w, h) * 0.32 * self.scale

        # Draw stylish starry/grid background
        painter.fillRect(0, 0, w, h, QColor("#080C14"))

        # Render active scene
        if self.active_scene == "coordinate":
            self._draw_coordinate_geometry(painter, cx, cy, base_zoom)
        elif self.active_scene == "molecule":
            self._draw_molecular_structure(painter, cx, cy, base_zoom)
        elif self.active_scene == "orbital":
            self._draw_orbital_mechanics(painter, cx, cy, base_zoom)

        # Draw HUD info
        self._draw_hud(painter, w, h)

    def _draw_coordinate_geometry(self, painter: QPainter, cx: float, cy: float, zoom: float) -> None:
        """Render 3D XYZ Cartesian coordinate axes and a rotating 3D geometry cube."""
        # Origin
        ox, oy, _ = self._project_3d(0, 0, 0, cx, cy, zoom)

        # Draw Ground Grid
        grid_pen = QPen(QColor(31, 41, 55, 120), 1)
        painter.setPen(grid_pen)
        grid_size = 1.2
        steps = 4
        for i in range(-steps, steps + 1):
            val = (i / steps) * grid_size
            p1x, p1y, _ = self._project_3d(-grid_size, -0.6, val, cx, cy, zoom)
            p2x, p2y, _ = self._project_3d(grid_size, -0.6, val, cx, cy, zoom)
            painter.drawLine(int(p1x), int(p1y), int(p2x), int(p2y))
            p3x, p3y, _ = self._project_3d(val, -0.6, -grid_size, cx, cy, zoom)
            p4x, p4y, _ = self._project_3d(val, -0.6, grid_size, cx, cy, zoom)
            painter.drawLine(int(p3x), int(p3y), int(p4x), int(p4y))

        # 3D Cube Vertices
        s = 0.5
        vertices = [
            (-s, -s, -s), (s, -s, -s), (s, s, -s), (-s, s, -s),
            (-s, -s, s), (s, -s, s), (s, s, s), (-s, s, s)
        ]
        faces = [
            ([0, 1, 2, 3], QColor(6, 182, 212, 100)),   # Cyan Front
            ([4, 5, 6, 7], QColor(139, 92, 246, 100)), # Purple Back
            ([0, 1, 5, 4], QColor(16, 185, 129, 90)),  # Green Bottom
            ([2, 3, 7, 6], QColor(245, 158, 11, 90)),  # Amber Top
            ([0, 3, 7, 4], QColor(59, 130, 246, 90)),  # Blue Left
            ([1, 2, 6, 5], QColor(236, 72, 153, 90)),  # Pink Right
        ]

        proj_verts = [self._project_3d(vx, vy, vz, cx, cy, zoom) for vx, vy, vz in vertices]

        # Sort faces by average depth Z for painter's algorithm
        face_depths = []
        for idx, (face_indices, color) in enumerate(faces):
            avg_z = sum(proj_verts[v][2] for v in face_indices) / len(face_indices)
            face_depths.append((avg_z, face_indices, color))
        face_depths.sort(key=lambda item: item[0], reverse=True)

        for _, f_indices, col in face_depths:
            poly = QPolygonF([QPointF(proj_verts[v][0], proj_verts[v][1]) for v in f_indices])
            painter.setBrush(QBrush(col))
            painter.setPen(QPen(QColor("#F9FAFB"), 1.5))
            painter.drawPolygon(poly)

        # Draw 3D Axes
        axis_len = 1.0
        # X Axis (Red)
        xx, xy, _ = self._project_3d(axis_len, 0, 0, cx, cy, zoom)
        painter.setPen(QPen(QColor("#EF4444"), 3))
        painter.drawLine(int(ox), int(oy), int(xx), int(xy))
        painter.drawText(int(xx + 6), int(xy + 4), "+X")

        # Y Axis (Green)
        yx, yy, _ = self._project_3d(0, axis_len, 0, cx, cy, zoom)
        painter.setPen(QPen(QColor("#10B981"), 3))
        painter.drawLine(int(ox), int(oy), int(yx), int(yy))
        painter.drawText(int(yx + 4), int(yy - 6), "+Y")

        # Z Axis (Blue)
        zx, zy, _ = self._project_3d(0, 0, axis_len, cx, cy, zoom)
        painter.setPen(QPen(QColor("#3B82F6"), 3))
        painter.drawLine(int(ox), int(oy), int(zx), int(zy))
        painter.drawText(int(zx + 6), int(zy + 6), "+Z")

    def _draw_molecular_structure(self, painter: QPainter, cx: float, cy: float, zoom: float) -> None:
        """Render H2O (Water) or CH4 Molecular ball-and-stick model with bond angles."""
        # Oxygen atom at center
        ox_p = (0.0, 0.0, 0.0)
        # 2 Hydrogen atoms at 104.5 degree bond angle
        h1_p = (-0.7, 0.45, 0.0)
        h2_p = (0.7, 0.45, 0.0)

        atoms = [
            (ox_p, 28, QColor("#EF4444"), "O (Oxygen)"),
            (h1_p, 16, QColor("#F3F4F6"), "H1"),
            (h2_p, 16, QColor("#F3F4F6"), "H2"),
        ]

        proj_atoms = []
        for (ax, ay, az), radius, col, lbl in atoms:
            px, py, pz = self._project_3d(ax, ay, az, cx, cy, zoom)
            proj_atoms.append((px, py, pz, radius * self.scale, col, lbl))

        # Draw Chemical Bonds (Cylinder sticks)
        bond_pen = QPen(QColor("#9CA3AF"), 6)
        painter.setPen(bond_pen)
        # O - H1
        painter.drawLine(int(proj_atoms[0][0]), int(proj_atoms[0][1]), int(proj_atoms[1][0]), int(proj_atoms[1][1]))
        # O - H2
        painter.drawLine(int(proj_atoms[0][0]), int(proj_atoms[0][1]), int(proj_atoms[2][0]), int(proj_atoms[2][1]))

        # Sort atoms by depth
        proj_atoms.sort(key=lambda a: a[2], reverse=True)

        for px, py, _, rad, col, lbl in proj_atoms:
            # Sphere gradient
            grad = QLinearGradient(px - rad * 0.4, py - rad * 0.4, px + rad, py + rad)
            grad.setColorAt(0.0, col.lighter(140))
            grad.setColorAt(1.0, col.darker(150))
            painter.setBrush(QBrush(grad))
            painter.setPen(QPen(QColor("#111827"), 1.5))
            painter.drawEllipse(QPointF(px, py), rad, rad)

            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawText(int(px - rad), int(py + rad + 14), lbl)

        # Bond angle badge
        painter.setPen(QColor("#06B6D4"))
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        painter.drawText(int(cx - 70), int(cy - 120), "Water Molecule (H₂O) • 104.5°")

    def _draw_orbital_mechanics(self, painter: QPainter, cx: float, cy: float, zoom: float) -> None:
        """Render Sun and Planetary elliptical orbit simulation."""
        # Central Star (Sun)
        sx, sy, _ = self._project_3d(0, 0, 0, cx, cy, zoom)

        # Draw Elliptical Orbit Path
        orbit_pen = QPen(QColor(6, 182, 212, 100), 1.5, Qt.PenStyle.DashLine)
        painter.setPen(orbit_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        num_pts = 60
        a = 1.2  # Semi-major axis
        b = 0.7  # Semi-minor axis
        orbit_pts = []
        for i in range(num_pts + 1):
            theta = (i / num_pts) * 2 * math.pi
            px, py, _ = self._project_3d(a * math.cos(theta), 0, b * math.sin(theta), cx, cy, zoom)
            orbit_pts.append(QPointF(px, py))
        painter.drawPolyline(orbit_pts)

        # Moving Planet Position
        rad_orb = math.radians(self._orbital_angle)
        plan_x, plan_y, plan_z = self._project_3d(
            a * math.cos(rad_orb),
            0,
            b * math.sin(rad_orb),
            cx, cy, zoom
        )

        # Sun Glow & Body
        sun_rad = 32 * self.scale
        sun_grad = QLinearGradient(sx - sun_rad * 0.4, sy - sun_rad * 0.4, sx + sun_rad, sy + sun_rad)
        sun_grad.setColorAt(0.0, QColor("#FDE047"))
        sun_grad.setColorAt(1.0, QColor("#F97316"))
        painter.setBrush(QBrush(sun_grad))
        painter.setPen(QPen(QColor("#EA580C"), 2))
        painter.drawEllipse(QPointF(sx, sy), sun_rad, sun_rad)

        # Planet Body
        plan_rad = 12 * self.scale
        plan_grad = QLinearGradient(plan_x - plan_rad * 0.4, plan_y - plan_rad * 0.4, plan_x + plan_rad, plan_y + plan_rad)
        plan_grad.setColorAt(0.0, QColor("#60A5FA"))
        plan_grad.setColorAt(1.0, QColor("#1E40AF"))
        painter.setBrush(QBrush(plan_grad))
        painter.setPen(QPen(QColor("#93C5FD"), 1.5))
        painter.drawEllipse(QPointF(plan_x, plan_y), plan_rad, plan_rad)

        painter.setPen(QColor("#22D3EE"))
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        painter.drawText(int(cx - 90), int(cy - 120), "Keplerian Orbital Dynamics")

    def _draw_hud(self, painter: QPainter, w: int, h: int) -> None:
        """Display subtle viewport metrics in the corner."""
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(17, 24, 39, 190))
        painter.drawRoundedRect(12, h - 42, 280, 30, 6, 6)

        painter.setPen(QColor("#9CA3AF"))
        painter.setFont(QFont("Segoe UI", 9))
        hud_text = f"Yaw: {self.yaw:.1f}° | Pitch: {self.pitch:.1f}° | Zoom: {self.scale:.2f}x"
        painter.drawText(22, h - 22, hud_text)

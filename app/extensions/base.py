"""Small product extension API and reusable construction/measurement tools."""

from dataclasses import dataclass, field
from typing import Protocol
import math
import uuid
import numpy as np
from app.interaction.contracts import GestureIntent, IntentType, Phase
from .live_geometry import build_live_shape, render_live


@dataclass(frozen=True)
class Line:
    a: tuple
    b: tuple
    color: str = "#77949e"
    width: float = 1.5


@dataclass(frozen=True)
class Ball:
    center: tuple
    radius: float
    color: str = "#69b5c1"
    label: str = ""


@dataclass(frozen=True)
class Face:
    a: tuple
    b: tuple
    c: tuple
    color: str = "#426f7a"


@dataclass(frozen=True)
class Geometry:
    lines: tuple[Line, ...] = ()
    balls: tuple[Ball, ...] = ()
    labels: tuple[tuple[tuple, str], ...] = ()
    faces: tuple[Face, ...] = ()


@dataclass
class FrozenShape:
    """A shape snapshot created by the touchless shape toolbar.

    Stores renderer-agnostic parameters in scene-local units.  The 'params'
    dict mirrors ShapeParams fields that are non-zero/non-empty.
    Each shape maintains independent 3D orientation (yaw, pitch).
    """
    kind: str              # 'Circle', 'Square', 'Triangle', 'Rectangle',
                           # 'Sphere', 'Cube', 'Box', 'Pyramid'
    params: dict           # keys: center_xy, radius, width, height,
                           #       corners_xy, size, corners_3d, hands_used
    shape_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    yaw: float = 0.0
    pitch: float = 0.0
    tasks: set = field(default_factory=set)
    unfold_progress: float = 0.0


class StemExtension(Protocol):
    id: str
    title: str
    category: str
    supports_hand_anchor: bool
    tools: tuple[str, ...]

    def activate(self): ...
    def deactivate(self): ...
    def reset(self): ...
    def update(self, dt): ...
    def render(self, context): ...
    def on_intent(self, intent: GestureIntent): ...


class Lab:
    supports_hand_anchor = True
    view_radius = 2.0
    dimensionality = "3D scene"
    live_surface_overlay = False
    tools = (
        "Inspect",
        "Distance",
        "Vector",
        "Angle",
        "Plane",
        "Triangle",
        "Rectangle",
        "Quadrilateral",
        "Polygon",
    )
    presets = ("Default",)

    def __init__(self, config):
        self.config = config
        self.active = False
        self.live_enabled = False
        self.preset = self.presets[0]
        self.reset()

    def activate(self):
        self.active = True

    def deactivate(self):
        self.active = False
        self.dragging = False
        self.live_shape = None

    def reset(self):
        self.yaw, self.pitch, self.scale = 0.35, 0.35, 1.0
        self.time = 0.0
        self.paused = False
        self.time_rate = 1.0
        self.points, self.constructions = [], []
        self.preview = self.selection = self.hover = None
        self.pair_preview = ()
        self.reference_plane = None
        self.tool = "Inspect"
        self.dragging = False
        self._scale_start = self.scale
        self._committed = set()
        self.construction_error = ""
        self.live_shape = None
        self.frozen_shapes: list[FrozenShape] = []
        self.preview_frozen_shape: "FrozenShape | None" = None
        self.selected_shape_id: str | None = None
        self.parameters = {
            "amplitude": 1.0,
            "frequency": 1.0,
            "phase": 0.0,
            "samples": 32.0,
            "radius": 1.5,
            "index": 1.5,
            "focal": 1.0,
        }

    # ------------------------------------------------------------------
    # Frozen shape management (touchless shape toolbar)
    # ------------------------------------------------------------------

    def add_frozen_shape(self, shape: "FrozenShape") -> None:
        """Append a frozen shape to this lab's scene."""
        if not hasattr(self, "frozen_shapes"):
            self.frozen_shapes = []
        self.frozen_shapes.append(shape)
        self.selected_shape_id = None

    def remove_frozen_shape_by_id(self, shape_id: str) -> bool:
        """Remove a frozen shape by its ID.  Returns True if found."""
        if not hasattr(self, "frozen_shapes"):
            return False
        before = len(self.frozen_shapes)
        self.frozen_shapes = [s for s in self.frozen_shapes if s.shape_id != shape_id]
        if getattr(self, "selected_shape_id", None) == shape_id:
            self.selected_shape_id = None
        return len(self.frozen_shapes) < before

    def clear_frozen_shapes(self) -> None:
        """Remove all frozen shapes."""
        if hasattr(self, "frozen_shapes"):
            self.frozen_shapes.clear()
        self.selected_shape_id = None

    def frozen_geometry(self) -> "Geometry":
        """Convert all frozen shapes into Geometry primitives.

        Shapes are rendered in normalised scene coordinates: the centre of the
        frame maps to (0, 0, 0) in world space.  FRAME_NORMALIZED (0-1) coords
        are linearly mapped to [-1, 1] scene units.
        Each shape rotates with its own independent (yaw, pitch).
        """
        shapes: list[FrozenShape] = []
        if hasattr(self, "frozen_shapes") and self.frozen_shapes:
            shapes.extend(self.frozen_shapes)
        if getattr(self, "preview_frozen_shape", None) is not None:
            shapes.append(self.preview_frozen_shape)

        if not shapes:
            return Geometry()

        lines: list[Line] = []
        balls: list[Ball] = []
        faces: list[Face] = []
        labels: list[tuple[tuple, str]] = []

        from app.rendering.transforms import rotation

        view_mat = rotation(getattr(self, "yaw", 0.0), getattr(self, "pitch", 0.0))
        aspect = getattr(self, "frame_aspect", 4.0 / 3.0)
        selected_id = getattr(self, "selected_shape_id", None)

        def _norm_to_scene(x, y, z=0.0):
            """Map FRAME_NORMALIZED (0-1) to scene (-1..1) space."""
            return ((x * 2 - 1) * aspect, -(y * 2 - 1), z)

        # High-contrast palette: saturated face body + bright luminous wireframe borders
        _STYLE = {
            "Cube":      {"face": "#0284c7", "edge": "#e0f2fe", "ball": "#ffffff", "edge_w": 3.0},
            "Box":       {"face": "#ea580c", "edge": "#fef08a", "ball": "#fffbeb", "edge_w": 3.0},
            "Pyramid":   {"face": "#9333ea", "edge": "#fce7f3", "ball": "#ffffff", "edge_w": 3.0},
            "Sphere":    {"face": "#0284c7", "edge": "#ffffff", "ball": "#0284c7", "edge_w": 2.2},
            "Square":    {"face": "#059669", "edge": "#6ee7b7", "ball": "#ffffff", "edge_w": 3.0},
            "Rectangle": {"face": "#7c3aed", "edge": "#e9d5ff", "ball": "#ffffff", "edge_w": 3.0},
            "Triangle":  {"face": "#d97706", "edge": "#fef3c7", "ball": "#ffffff", "edge_w": 3.0},
            "Circle":    {"face": "#0891b2", "edge": "#a5f3fc", "ball": "#ffffff", "edge_w": 3.0},
        }

        for fs in shapes:
            p = fs.params
            is_selected = (fs.shape_id == selected_id)

            # Independent per-shape orientation
            fs_yaw = getattr(fs, "yaw", getattr(self, "yaw", 0.0))
            fs_pitch = getattr(fs, "pitch", getattr(self, "pitch", 0.0))
            R = rotation(fs_yaw, fs_pitch)

            def _rotate_local(center_sc, local_v, R_mat=R):
                """Rotate a local 3D offset around center_sc by R_mat."""
                rv = R_mat @ np.asarray(local_v, dtype=float)
                return (
                    center_sc[0] + float(rv[0]),
                    center_sc[1] + float(rv[1]),
                    center_sc[2] + float(rv[2]),
                )

            style = _STYLE.get(fs.kind, _STYLE["Cube"])
            face_col = style["face"]
            if is_selected:
                # Active target highlight border and vertices - lights up brightly!
                edge_col = "#fbbf24" if fs.kind != "Cube" else "#38bdf8"
                ball_col = "#fbbf24"
                edge_w = style["edge_w"] + 1.6
            else:
                edge_col = style["edge"]
                ball_col = style["ball"]
                edge_w = style["edge_w"]

            cx, cy = p.get("center_xy", (0.5, 0.5))
            scene_c = _norm_to_scene(cx, cy)

            if fs.kind == "Circle":
                r = p.get("radius", 0.05)
                n_seg = 32
                pts_3d = []
                for i in range(n_seg):
                    a = 2 * math.pi * i / n_seg
                    v_loc = ((r * 2.0) * math.cos(a), (r * 2.0) * math.sin(a), 0.0)
                    pts_3d.append(_rotate_local(scene_c, v_loc))
                # Solid filled disc face fan (double-sided)
                for i in range(n_seg):
                    p_curr = pts_3d[i]
                    p_next = pts_3d[(i + 1) % n_seg]
                    faces.append(Face(scene_c, p_curr, p_next, face_col))
                    faces.append(Face(scene_c, p_next, p_curr, face_col))
                    lines.append(Line(p_curr, p_next, edge_col, edge_w))
                balls.append(Ball(scene_c, 0.02, ball_col))

                fs_tasks = getattr(fs, "tasks", set())
                r_sc = r * 2.0
                if "distance" in fs_tasks:
                    p_edge = _rotate_local(scene_c, (r_sc, 0, 0))
                    lines.append(Line(scene_c, p_edge, "#38bdf8", 3.5))
                    balls.append(Ball(p_edge, 0.022, "#fbbf24"))
                    labels.append((_rotate_local(scene_c, (r_sc * 0.5, 0.04, 0)), f"R={r_sc:.2f}"))
                    labels.append((_rotate_local(scene_c, (0, -r_sc - 0.04, 0)), f"D={r_sc*2:.2f}"))
                if "metrics" in fs_tasks:
                    area = math.pi * (r_sc ** 2)
                    perim = 2 * math.pi * r_sc
                    labels.append((_rotate_local(scene_c, (0, r_sc + 0.04, 0)), f"S={area:.2f} | P={perim:.2f}"))

            elif fs.kind == "Sphere":
                r = p.get("radius", 0.05)
                scene_r = max(0.04, r * 2.0)
                fs_tasks = getattr(fs, "tasks", set())
                unfold_prog = getattr(fs, "unfold_progress", 1.0 if "unfold" in fs_tasks else 0.0)
                if "unfold" in fs_tasks and unfold_prog <= 0.001:
                    unfold_prog = 1.0

                if unfold_prog < 0.6:
                    # 3D solid lighted sphere & coordinate meridian rings
                    balls.append(Ball(scene_c, scene_r, face_col))
                    n_seg = 24
                    for plane in ("xy", "xz"):
                        pts = []
                        for i in range(n_seg):
                            a = 2 * math.pi * i / n_seg
                            if plane == "xy":
                                v_loc = (scene_r * math.cos(a), scene_r * math.sin(a), 0.0)
                            else:
                                v_loc = (scene_r * math.cos(a), 0.0, scene_r * math.sin(a))
                            pts.append(_rotate_local(scene_c, v_loc))
                        for i in range(n_seg):
                            lines.append(Line(pts[i], pts[(i + 1) % n_seg], edge_col, edge_w))

                if unfold_prog > 0.001:
                    # Unfolding 3D Net for Sphere: Sinusoidal gore projection petals (Múi cầu)
                    n_gores = 6
                    w0 = (2.0 * math.pi * scene_r) / n_gores
                    n_lat = 16
                    for k in range(n_gores):
                        xk = (k - (n_gores - 1) / 2.0) * w0
                        lam_mid = -math.pi + (k + 0.5) * (2.0 * math.pi / n_gores)
                        lam_left = lam_mid - math.pi / n_gores
                        lam_right = lam_mid + math.pi / n_gores

                        pts_left, pts_right = [], []
                        for i in range(n_lat + 1):
                            phi = -math.pi / 2.0 + math.pi * i / n_lat
                            y_flat = scene_r * phi
                            hw_flat = 0.5 * w0 * math.cos(phi)

                            p3d_left = (
                                scene_r * math.cos(phi) * math.sin(lam_left),
                                scene_r * math.sin(phi),
                                scene_r * math.cos(phi) * math.cos(lam_left),
                            )
                            p3d_right = (
                                scene_r * math.cos(phi) * math.sin(lam_right),
                                scene_r * math.sin(phi),
                                scene_r * math.cos(phi) * math.cos(lam_right),
                            )
                            pflat_left = (xk - hw_flat, y_flat, 0.0)
                            pflat_right = (xk + hw_flat, y_flat, 0.0)

                            u = unfold_prog
                            cur_left = (
                                (1.0 - u) * p3d_left[0] + u * pflat_left[0],
                                (1.0 - u) * p3d_left[1] + u * pflat_left[1],
                                (1.0 - u) * p3d_left[2] + u * pflat_left[2],
                            )
                            cur_right = (
                                (1.0 - u) * p3d_right[0] + u * pflat_right[0],
                                (1.0 - u) * p3d_right[1] + u * pflat_right[1],
                                (1.0 - u) * p3d_right[2] + u * pflat_right[2],
                            )
                            pts_left.append(_rotate_local(scene_c, cur_left))
                            pts_right.append(_rotate_local(scene_c, cur_right))

                        gore_col = "#0ea5e9" if k % 2 == 0 else "#0284c7"
                        for i in range(n_lat):
                            faces.append(Face(pts_left[i], pts_right[i], pts_right[i + 1], gore_col))
                            faces.append(Face(pts_left[i], pts_right[i + 1], pts_left[i + 1], gore_col))
                            faces.append(Face(pts_left[i], pts_right[i + 1], pts_right[i], gore_col))
                            faces.append(Face(pts_left[i], pts_left[i + 1], pts_right[i + 1], gore_col))
                            lines.append(Line(pts_left[i], pts_left[i + 1], "#7dd3fc", 2.0))
                            lines.append(Line(pts_right[i], pts_right[i + 1], "#7dd3fc", 2.0))

                        # Equator hinge marker across gore
                        mid_idx = n_lat // 2
                        lines.append(Line(pts_left[mid_idx], pts_right[mid_idx], "#f59e0b", 2.5))

                    labels.append((
                        _rotate_local(scene_c, (0, scene_r * (math.pi / 2) + 0.06, 0)),
                        f"Bung mặt phẳng: Múi cầu (Gores) | S_tp = 4πR² = {4.0 * math.pi * (scene_r ** 2):.2f}"
                    ))
                    labels.append((
                        _rotate_local(scene_c, (0, -scene_r * (math.pi / 2) - 0.06, 0)),
                        "Định lý Gauss: K > 0 (không thể trải phẳng hoàn toàn không biến dạng)"
                    ))

                if "distance" in fs_tasks:
                    p_edge = _rotate_local(scene_c, (scene_r, 0, 0))
                    lines.append(Line(scene_c, p_edge, "#38bdf8", 3.5))
                    balls.append(Ball(p_edge, 0.024, "#fbbf24"))
                    labels.append((_rotate_local(scene_c, (scene_r * 0.5, 0.04, 0)), f"R={scene_r:.2f}"))
                    labels.append((_rotate_local(scene_c, (0, -scene_r - 0.04, 0)), f"D={scene_r*2:.2f}"))
                if "metrics" in fs_tasks:
                    vol = (4.0 / 3.0) * math.pi * (scene_r ** 3)
                    area = 4.0 * math.pi * (scene_r ** 2)
                    labels.append((_rotate_local(scene_c, (0, scene_r + 0.05, 0)), f"V={vol:.2f} | S={area:.2f}"))
                if "cross_section" in fs_tasks:
                    disc_pts = [
                        _rotate_local(scene_c, (scene_r * math.cos(2 * math.pi * i / 24), scene_r * math.sin(2 * math.pi * i / 24), 0.0))
                        for i in range(24)
                    ]
                    for i in range(24):
                        faces.append(Face(scene_c, disc_pts[i], disc_pts[(i + 1) % 24], "#8b5cf6"))
                        faces.append(Face(scene_c, disc_pts[(i + 1) % 24], disc_pts[i], "#8b5cf6"))
                        lines.append(Line(disc_pts[i], disc_pts[(i + 1) % 24], "#c084fc", 3.0))
                    balls.append(Ball(scene_c, 0.022, "#e9d5ff"))
                    labels.append((_rotate_local(scene_c, (0, 0, 0.02)), "Thiết diện: Hình tròn"))

            elif fs.kind in ("Square", "Rectangle"):
                corners = p.get("corners_xy", [])
                if corners and len(corners) >= 4:
                    raw_sc = [_norm_to_scene(*c) for c in corners[:4]]
                    sc_pts = [
                        _rotate_local(scene_c, (pt[0] - scene_c[0], pt[1] - scene_c[1], 0.0))
                        for pt in raw_sc
                    ]
                    # Solid quad (2 triangles, double-sided)
                    faces.append(Face(sc_pts[0], sc_pts[1], sc_pts[2], face_col))
                    faces.append(Face(sc_pts[0], sc_pts[2], sc_pts[3], face_col))
                    faces.append(Face(sc_pts[0], sc_pts[2], sc_pts[1], face_col))
                    faces.append(Face(sc_pts[0], sc_pts[3], sc_pts[2], face_col))
                    for i in range(4):
                        lines.append(Line(sc_pts[i], sc_pts[(i + 1) % 4], edge_col, edge_w))
                        balls.append(Ball(sc_pts[i], 0.02, ball_col))

                    fs_tasks = getattr(fs, "tasks", set())
                    # Invariant metric dimensions measured in unrotated world Oxyz reference frame
                    d01 = math.hypot(raw_sc[0][0] - raw_sc[1][0], raw_sc[0][1] - raw_sc[1][1])
                    d12 = math.hypot(raw_sc[1][0] - raw_sc[2][0], raw_sc[1][1] - raw_sc[2][1])
                    if fs.kind == "Square":
                        a_side = (d01 + d12) / 2.0
                        d01 = d12 = a_side

                    if "distance" in fs_tasks:
                        lines.append(Line(sc_pts[0], sc_pts[1], "#38bdf8", 4.0))
                        mid01 = ((sc_pts[0][0] + sc_pts[1][0]) / 2, (sc_pts[0][1] + sc_pts[1][1]) / 2, (sc_pts[0][2] + sc_pts[1][2]) / 2)
                        if fs.kind == "Square":
                            labels.append((mid01, f"a={d01:.2f}"))
                        else:
                            labels.append((mid01, f"W={d01:.2f}"))
                            lines.append(Line(sc_pts[1], sc_pts[2], "#38bdf8", 4.0))
                            mid12 = ((sc_pts[1][0] + sc_pts[2][0]) / 2, (sc_pts[1][1] + sc_pts[2][1]) / 2, (sc_pts[1][2] + sc_pts[2][2]) / 2)
                            labels.append((mid12, f"H={d12:.2f}"))

                    if "metrics" in fs_tasks:
                        area = d01 * d12
                        perim = 2 * (d01 + d12)
                        # 2D shapes: no volume, no face occlusion threshold
                        labels.append((scene_c, f"S={area:.2f} | P={perim:.2f}"))

            elif fs.kind == "Triangle":
                corners = p.get("corners_xy", [])
                if len(corners) == 3:
                    raw_sc = [_norm_to_scene(*c) for c in corners]
                    sc_pts = [
                        _rotate_local(scene_c, (pt[0] - scene_c[0], pt[1] - scene_c[1], 0.0))
                        for pt in raw_sc
                    ]
                    faces.append(Face(sc_pts[0], sc_pts[1], sc_pts[2], face_col))
                    faces.append(Face(sc_pts[0], sc_pts[2], sc_pts[1], face_col))
                    for i in range(3):
                        lines.append(Line(sc_pts[i], sc_pts[(i + 1) % 3], edge_col, edge_w))
                        balls.append(Ball(sc_pts[i], 0.02, ball_col))

                    fs_tasks = getattr(fs, "tasks", set())
                    # Invariant edge lengths measured in unrotated world Oxyz reference frame
                    d01 = math.hypot(raw_sc[0][0] - raw_sc[1][0], raw_sc[0][1] - raw_sc[1][1])
                    d12 = math.hypot(raw_sc[1][0] - raw_sc[2][0], raw_sc[1][1] - raw_sc[2][1])
                    d20 = math.hypot(raw_sc[2][0] - raw_sc[0][0], raw_sc[2][1] - raw_sc[0][1])

                    if "distance" in fs_tasks:
                        lines.append(Line(sc_pts[0], sc_pts[1], "#38bdf8", 3.5))
                        mid01 = ((sc_pts[0][0] + sc_pts[1][0]) / 2, (sc_pts[0][1] + sc_pts[1][1]) / 2, (sc_pts[0][2] + sc_pts[1][2]) / 2)
                        labels.append((mid01, f"a={d01:.2f}"))

                        lines.append(Line(sc_pts[1], sc_pts[2], "#38bdf8", 3.5))
                        mid12 = ((sc_pts[1][0] + sc_pts[2][0]) / 2, (sc_pts[1][1] + sc_pts[2][1]) / 2, (sc_pts[1][2] + sc_pts[2][2]) / 2)
                        labels.append((mid12, f"b={d12:.2f}"))

                        lines.append(Line(sc_pts[2], sc_pts[0], "#38bdf8", 3.5))
                        mid20 = ((sc_pts[2][0] + sc_pts[0][0]) / 2, (sc_pts[2][0] + sc_pts[0][1]) / 2, (sc_pts[2][2] + sc_pts[0][2]) / 2)
                        labels.append((mid20, f"c={d20:.2f}"))

                    if "metrics" in fs_tasks:
                        s_p = (d01 + d12 + d20) / 2.0
                        area = math.sqrt(max(0.0001, s_p * (s_p - d01) * (s_p - d12) * (s_p - d20)))
                        # 2D shapes: no volume, no face occlusion threshold
                        labels.append((scene_c, f"S={area:.2f} | P={s_p*2:.2f}"))

            elif fs.kind == "Cube":
                # Isotropic cube side in scene units (uniform across X, Y, Z)
                side = p.get("size", 0.15)
                hs = max(0.06, side)
                fs_tasks = getattr(fs, "tasks", set())
                unfold_prog = getattr(fs, "unfold_progress", 1.0 if "unfold" in fs_tasks else 0.0)
                if "unfold" in fs_tasks and unfold_prog <= 0.001:
                    unfold_prog = 1.0

                if unfold_prog <= 0.001:
                    local_corners = [
                        (sx * hs, sy * hs, sz * hs)
                        for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)
                    ]
                    sc_pts = [_rotate_local(scene_c, lv) for lv in local_corners]
                    _CUBE_FACES = [
                        (0, 1, 3), (0, 3, 2),  # x = -1
                        (4, 6, 7), (4, 7, 5),  # x = +1
                        (0, 4, 5), (0, 5, 1),  # y = -1
                        (2, 3, 7), (2, 7, 6),  # y = +1
                        (0, 2, 6), (0, 6, 4),  # z = -1
                        (1, 5, 7), (1, 7, 3),  # z = +1
                    ]
                    for i1, i2, i3 in _CUBE_FACES:
                        faces.append(Face(sc_pts[i1], sc_pts[i2], sc_pts[i3], face_col))
                    _CUBE_EDGES = [
                        (0, 1), (0, 2), (0, 4), (1, 3), (1, 5), (2, 3),
                        (2, 6), (3, 7), (4, 5), (4, 6), (5, 7), (6, 7),
                    ]
                    for a, b in _CUBE_EDGES:
                        lines.append(Line(sc_pts[a], sc_pts[b], edge_col, edge_w))
                    for pt in sc_pts:
                        balls.append(Ball(pt, 0.022, ball_col))
                else:
                    # Unfolding 3D Net for Cube: 6 faces unfolding via Latin Cross net
                    th = unfold_prog * (math.pi / 2.0)
                    sin_th, cos_th = math.sin(th), math.cos(th)
                    sin_2th, cos_2th = math.sin(2.0 * th), math.cos(2.0 * th)

                    # 1. Bottom face (Đáy) at z = -hs
                    vb = [
                        (-hs, -hs, -hs), (hs, -hs, -hs), (hs, hs, -hs), (-hs, hs, -hs)
                    ]
                    # 2. South face (Mặt sau) hinged at y = -hs, z = -hs
                    vs = [
                        (-hs, -hs, -hs), (hs, -hs, -hs),
                        (hs, -hs - 2 * hs * sin_th, -hs + 2 * hs * cos_th),
                        (-hs, -hs - 2 * hs * sin_th, -hs + 2 * hs * cos_th),
                    ]
                    # 3. North face (Mặt trước) hinged at y = hs, z = -hs
                    vn = [
                        (-hs, hs, -hs), (hs, hs, -hs),
                        (hs, hs + 2 * hs * sin_th, -hs + 2 * hs * cos_th),
                        (-hs, hs + 2 * hs * sin_th, -hs + 2 * hs * cos_th),
                    ]
                    # 4. West face (Mặt trái) hinged at x = -hs, z = -hs
                    vw = [
                        (-hs, -hs, -hs), (-hs, hs, -hs),
                        (-hs - 2 * hs * sin_th, hs, -hs + 2 * hs * cos_th),
                        (-hs - 2 * hs * sin_th, -hs, -hs + 2 * hs * cos_th),
                    ]
                    # 5. East face (Mặt phải) hinged at x = hs, z = -hs
                    ve = [
                        (hs, -hs, -hs), (hs, hs, -hs),
                        (hs + 2 * hs * sin_th, hs, -hs + 2 * hs * cos_th),
                        (hs + 2 * hs * sin_th, -hs, -hs + 2 * hs * cos_th),
                    ]
                    # 6. Top face (Mặt nắp) hinged at outer edge of North face
                    y_edge = hs + 2 * hs * sin_th
                    z_edge = -hs + 2 * hs * cos_th
                    y_top = y_edge - 2 * hs * cos_2th
                    z_top = z_edge + 2 * hs * sin_2th
                    vt = [
                        (-hs, y_edge, z_edge), (hs, y_edge, z_edge),
                        (hs, y_top, z_top), (-hs, y_top, z_top),
                    ]

                    cube_net_faces = [
                        (vb, "#0284c7", "Mặt đáy"),
                        (vn, "#0ea5e9", "Mặt trước"),
                        (vs, "#0ea5e9", "Mặt sau"),
                        (vw, "#06b6d4", "Mặt trái"),
                        (ve, "#06b6d4", "Mặt phải"),
                        (vt, "#38bdf8", "Mặt nắp"),
                    ]

                    for quad_local, f_col, f_lbl in cube_net_faces:
                        sc_q = [_rotate_local(scene_c, q) for q in quad_local]
                        faces.append(Face(sc_q[0], sc_q[1], sc_q[2], f_col))
                        faces.append(Face(sc_q[0], sc_q[2], sc_q[3], f_col))
                        faces.append(Face(sc_q[0], sc_q[2], sc_q[1], f_col))
                        faces.append(Face(sc_q[0], sc_q[3], sc_q[2], f_col))
                        for i in range(4):
                            lines.append(Line(sc_q[i], sc_q[(i + 1) % 4], edge_col, edge_w))
                            balls.append(Ball(sc_q[i], 0.02, ball_col))
                        c_quad = (
                            sum(pt[0] for pt in sc_q) / 4.0,
                            sum(pt[1] for pt in sc_q) / 4.0,
                            sum(pt[2] for pt in sc_q) / 4.0,
                        )
                        labels.append((c_quad, f_lbl))

                    hinges_local = [
                        (vb[0], vb[1]),
                        (vb[3], vb[2]),
                        (vb[0], vb[3]),
                        (vb[1], vb[2]),
                        (vn[3], vn[2]),
                    ]
                    for h_a, h_b in hinges_local:
                        p_ha = _rotate_local(scene_c, h_a)
                        p_hb = _rotate_local(scene_c, h_b)
                        lines.append(Line(p_ha, p_hb, "#f59e0b", 3.5))
                        balls.append(Ball(p_ha, 0.024, "#fbbf24"))
                        balls.append(Ball(p_hb, 0.024, "#fbbf24"))

                    labels.append((
                        _rotate_local(scene_c, (0, 0, hs + 0.12)),
                        f"Bung mặt phẳng: Khối lập phương | S_tp = 6a² = {6 * (hs * 2)**2:.2f}"
                    ))

                fs_tasks = getattr(fs, "tasks", set())
                side_val = hs * 2
                if "distance" in fs_tasks:
                    p1 = _rotate_local(scene_c, (-hs, -hs, -hs))
                    p2 = _rotate_local(scene_c, (hs, -hs, -hs))
                    lines.append(Line(p1, p2, "#38bdf8", 4.0))
                    labels.append((_rotate_local(scene_c, (0, -hs - 0.04, -hs)), f"a={side_val:.2f}"))
                    p_d1 = _rotate_local(scene_c, (-hs, -hs, -hs))
                    p_d2 = _rotate_local(scene_c, (hs, hs, hs))
                    lines.append(Line(p_d1, p_d2, "#f59e0b", 2.5))
                    labels.append((scene_c, f"d={math.sqrt(3)*side_val:.2f}"))

                if "metrics" in fs_tasks:
                    vol = side_val ** 3
                    # Single volume label for the entire solid
                    labels.append((_rotate_local(scene_c, (0, 0, hs + 0.06)), f"V={vol:.2f}"))
                    # Individual face areas with face visibility threshold
                    cube_faces_info = [
                        ((1.0, 0.0, 0.0), (hs, 0.0, 0.0), side_val ** 2),
                        ((-1.0, 0.0, 0.0), (-hs, 0.0, 0.0), side_val ** 2),
                        ((0.0, 1.0, 0.0), (0.0, hs, 0.0), side_val ** 2),
                        ((0.0, -1.0, 0.0), (0.0, -hs, 0.0), side_val ** 2),
                        ((0.0, 0.0, 1.0), (0.0, 0.0, hs), side_val ** 2),
                        ((0.0, 0.0, -1.0), (0.0, 0.0, -hs), side_val ** 2),
                    ]
                    for n_loc, c_loc, face_area in cube_faces_info:
                        vis = float((view_mat @ (R @ np.asarray(n_loc, dtype=float)))[2])
                        if vis > 0.15:
                            labels.append((_rotate_local(scene_c, c_loc), f"S={face_area:.2f}"))

                if "cross_section" in fs_tasks:
                    hex_local = [
                        (0, -hs, hs), (hs, -hs, 0), (hs, 0, -hs),
                        (0, hs, -hs), (-hs, hs, 0), (-hs, 0, hs),
                    ]
                    hex_pts = [_rotate_local(scene_c, hl) for hl in hex_local]
                    for i in range(6):
                        faces.append(Face(scene_c, hex_pts[i], hex_pts[(i + 1) % 6], "#10b981"))
                        faces.append(Face(scene_c, hex_pts[(i + 1) % 6], hex_pts[i], "#10b981"))
                        lines.append(Line(hex_pts[i], hex_pts[(i + 1) % 6], "#34d399", 3.5))
                        balls.append(Ball(hex_pts[i], 0.024, "#6ee7b7"))
                    labels.append((_rotate_local(scene_c, (0, hs + 0.04, -hs)), "Thiết diện: Lục giác"))

            elif fs.kind == "Box":
                w = max(0.06, p.get("width", 0.18))
                h = max(0.06, p.get("height", 0.14))
                depth = max(0.06, p.get("size", (w + h) / 2))
                fs_tasks = getattr(fs, "tasks", set())
                unfold_prog = getattr(fs, "unfold_progress", 1.0 if "unfold" in fs_tasks else 0.0)
                if "unfold" in fs_tasks and unfold_prog <= 0.001:
                    unfold_prog = 1.0

                l_val, h_val, w_val = w * 2, h * 2, depth * 2
                if unfold_prog <= 0.001:
                    local_corners = [
                        (sx * w, sy * h, sz * depth)
                        for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)
                    ]
                    sc_pts = [_rotate_local(scene_c, lv) for lv in local_corners]
                    _BOX_FACES = [
                        (0, 1, 3), (0, 3, 2),  # x = -1
                        (4, 6, 7), (4, 7, 5),  # x = +1
                        (0, 4, 5), (0, 5, 1),  # y = -1
                        (2, 3, 7), (2, 7, 6),  # y = +1
                        (0, 2, 6), (0, 6, 4),  # z = -1
                        (1, 5, 7), (1, 7, 3),  # z = +1
                    ]
                    for i1, i2, i3 in _BOX_FACES:
                        faces.append(Face(sc_pts[i1], sc_pts[i2], sc_pts[i3], face_col))
                    _BOX_EDGES = [
                        (0, 1), (0, 2), (0, 4), (1, 3), (1, 5), (2, 3),
                        (2, 6), (3, 7), (4, 5), (4, 6), (5, 7), (6, 7),
                    ]
                    for a, b in _BOX_EDGES:
                        lines.append(Line(sc_pts[a], sc_pts[b], edge_col, edge_w))
                    for pt in sc_pts:
                        balls.append(Ball(pt, 0.022, ball_col))
                else:
                    # Unfolding 3D Net for Box
                    th = unfold_prog * (math.pi / 2.0)
                    sin_th, cos_th = math.sin(th), math.cos(th)
                    sin_2th, cos_2th = math.sin(2.0 * th), math.cos(2.0 * th)

                    # 1. Bottom face (Đáy) at z = -depth
                    vb = [
                        (-w, -h, -depth), (w, -h, -depth), (w, h, -depth), (-w, h, -depth)
                    ]
                    # 2. South face (Mặt sau) hinged at y = -h, z = -depth
                    vs = [
                        (-w, -h, -depth), (w, -h, -depth),
                        (w, -h - 2 * depth * sin_th, -depth + 2 * depth * cos_th),
                        (-w, -h - 2 * depth * sin_th, -depth + 2 * depth * cos_th),
                    ]
                    # 3. North face (Mặt trước) hinged at y = h, z = -depth
                    vn = [
                        (-w, h, -depth), (w, h, -depth),
                        (w, h + 2 * depth * sin_th, -depth + 2 * depth * cos_th),
                        (-w, h + 2 * depth * sin_th, -depth + 2 * depth * cos_th),
                    ]
                    # 4. West face (Mặt trái) hinged at x = -w, z = -depth
                    vw = [
                        (-w, -h, -depth), (-w, h, -depth),
                        (-w - 2 * depth * sin_th, h, -depth + 2 * depth * cos_th),
                        (-w - 2 * depth * sin_th, -h, -depth + 2 * depth * cos_th),
                    ]
                    # 5. East face (Mặt phải) hinged at x = w, z = -depth
                    ve = [
                        (w, -h, -depth), (w, h, -depth),
                        (w + 2 * depth * sin_th, h, -depth + 2 * depth * cos_th),
                        (w + 2 * depth * sin_th, -h, -depth + 2 * depth * cos_th),
                    ]
                    # 6. Top face (Mặt nắp) hinged at outer edge of North face
                    y_edge = h + 2 * depth * sin_th
                    z_edge = -depth + 2 * depth * cos_th
                    y_top = y_edge - 2 * h * cos_2th
                    z_top = z_edge + 2 * h * sin_2th
                    vt = [
                        (-w, y_edge, z_edge), (w, y_edge, z_edge),
                        (w, y_top, z_top), (-w, y_top, z_top),
                    ]

                    box_net_faces = [
                        (vb, "#c2410c", "Mặt đáy"),
                        (vn, "#ea580c", "Mặt trước"),
                        (vs, "#ea580c", "Mặt sau"),
                        (vw, "#f97316", "Mặt trái"),
                        (ve, "#f97316", "Mặt phải"),
                        (vt, "#fb923c", "Mặt nắp"),
                    ]

                    for quad_local, f_col, f_lbl in box_net_faces:
                        sc_q = [_rotate_local(scene_c, q) for q in quad_local]
                        faces.append(Face(sc_q[0], sc_q[1], sc_q[2], f_col))
                        faces.append(Face(sc_q[0], sc_q[2], sc_q[3], f_col))
                        faces.append(Face(sc_q[0], sc_q[2], sc_q[1], f_col))
                        faces.append(Face(sc_q[0], sc_q[3], sc_q[2], f_col))
                        for i in range(4):
                            lines.append(Line(sc_q[i], sc_q[(i + 1) % 4], edge_col, edge_w))
                            balls.append(Ball(sc_q[i], 0.02, ball_col))
                        c_quad = (
                            sum(pt[0] for pt in sc_q) / 4.0,
                            sum(pt[1] for pt in sc_q) / 4.0,
                            sum(pt[2] for pt in sc_q) / 4.0,
                        )
                        labels.append((c_quad, f_lbl))

                    hinges_local = [
                        (vb[0], vb[1]),
                        (vb[3], vb[2]),
                        (vb[0], vb[3]),
                        (vb[1], vb[2]),
                        (vn[3], vn[2]),
                    ]
                    for h_a, h_b in hinges_local:
                        p_ha = _rotate_local(scene_c, h_a)
                        p_hb = _rotate_local(scene_c, h_b)
                        lines.append(Line(p_ha, p_hb, "#f59e0b", 3.5))
                        balls.append(Ball(p_ha, 0.024, "#fbbf24"))
                        balls.append(Ball(p_hb, 0.024, "#fbbf24"))

                    s_tp = 2 * (l_val * h_val + l_val * w_val + h_val * w_val)
                    labels.append((
                        _rotate_local(scene_c, (0, 0, depth + 0.12)),
                        f"Bung mặt phẳng: Hộp chữ nhật | S_tp = {s_tp:.2f}"
                    ))
                if "distance" in fs_tasks:
                    lines.append(Line(_rotate_local(scene_c, (-w, -h, -depth)), _rotate_local(scene_c, (w, -h, -depth)), "#38bdf8", 4.0))
                    labels.append((_rotate_local(scene_c, (0, -h - 0.03, -depth)), f"L={l_val:.2f}"))
                    lines.append(Line(_rotate_local(scene_c, (-w, -h, -depth)), _rotate_local(scene_c, (-w, h, -depth)), "#38bdf8", 4.0))
                    labels.append((_rotate_local(scene_c, (-w - 0.03, 0, -depth)), f"H={h_val:.2f}"))
                    lines.append(Line(_rotate_local(scene_c, (-w, -h, -depth)), _rotate_local(scene_c, (-w, -h, depth)), "#38bdf8", 4.0))
                    labels.append((_rotate_local(scene_c, (-w, -h, 0)), f"W={w_val:.2f}"))

                if "metrics" in fs_tasks:
                    vol = l_val * h_val * w_val
                    labels.append((_rotate_local(scene_c, (0, 0, depth + 0.06)), f"V={vol:.2f}"))
                    # Individual face areas with face visibility threshold
                    box_faces_info = [
                        ((1.0, 0.0, 0.0), (w, 0.0, 0.0), h_val * w_val),
                        ((-1.0, 0.0, 0.0), (-w, 0.0, 0.0), h_val * w_val),
                        ((0.0, 1.0, 0.0), (0.0, h, 0.0), l_val * w_val),
                        ((0.0, -1.0, 0.0), (0.0, -h, 0.0), l_val * w_val),
                        ((0.0, 0.0, 1.0), (0.0, 0.0, depth), l_val * h_val),
                        ((0.0, 0.0, -1.0), (0.0, 0.0, -depth), l_val * h_val),
                    ]
                    for n_loc, c_loc, face_area in box_faces_info:
                        vis = float((view_mat @ (R @ np.asarray(n_loc, dtype=float)))[2])
                        if vis > 0.15:
                            labels.append((_rotate_local(scene_c, c_loc), f"S={face_area:.2f}"))

                if "cross_section" in fs_tasks:
                    box_local = [
                        (0, -h, depth), (w, -h, 0), (w, 0, -depth),
                        (0, h, -depth), (-w, h, 0), (-w, 0, depth),
                    ]
                    box_pts = [_rotate_local(scene_c, bl) for bl in box_local]
                    for i in range(6):
                        faces.append(Face(scene_c, box_pts[i], box_pts[(i + 1) % 6], "#06b6d4"))
                        faces.append(Face(scene_c, box_pts[(i + 1) % 6], box_pts[i], "#06b6d4"))
                        lines.append(Line(box_pts[i], box_pts[(i + 1) % 6], "#38bdf8", 3.5))
                        balls.append(Ball(box_pts[i], 0.024, "#7dd3fc"))
                    labels.append((_rotate_local(scene_c, (0, h + 0.04, -depth)), "Thiết diện cắt"))

            elif fs.kind == "Pyramid":
                corners = p.get("corners_xy", [])
                if len(corners) >= 3:
                    apex_raw = _norm_to_scene(*corners[0])
                    base_raws = [_norm_to_scene(*c) for c in corners[1:]]
                    if len(base_raws) == 3:
                        b1_raw, b2_raw, b3_raw = base_raws
                        b1_lv = (b1_raw[0] - scene_c[0], b1_raw[1] - scene_c[1], 0.0)
                        b2_lv = (b2_raw[0] - scene_c[0], b2_raw[1] - scene_c[1], 0.0)
                        b3_lv = (b3_raw[0] - scene_c[0], b3_raw[1] - scene_c[1], 0.0)
                    else:
                        b1_raw, b2_raw = base_raws[:2]
                        b1_lv = (b1_raw[0] - scene_c[0], b1_raw[1] - scene_c[1], 0.0)
                        b2_lv = (b2_raw[0] - scene_c[0], b2_raw[1] - scene_c[1], 0.0)
                        mid_lv = ((b1_lv[0] + b2_lv[0]) / 2, (b1_lv[1] + b2_lv[1]) / 2, 0.0)
                        b3_lv = (2 * (apex_raw[0] - scene_c[0]) - mid_lv[0], 2 * (apex_raw[1] - scene_c[1]) - mid_lv[1], 0.0)

                    d12 = math.hypot(b1_lv[0] - b2_lv[0], b1_lv[1] - b2_lv[1])
                    d23 = math.hypot(b2_lv[0] - b3_lv[0], b2_lv[1] - b3_lv[1])
                    d31 = math.hypot(b3_lv[0] - b1_lv[0], b3_lv[1] - b1_lv[1])
                    base_sz = max((d12 + d23 + d31) / 3, 0.1)
                    apex_h = max(base_sz * 0.85, 0.2)
                    apex_lv = (apex_raw[0] - scene_c[0], apex_raw[1] - scene_c[1], apex_h)

                    apex_3d = _rotate_local(scene_c, apex_lv)
                    b1_3d = _rotate_local(scene_c, b1_lv)
                    b2_3d = _rotate_local(scene_c, b2_lv)
                    b3_3d = _rotate_local(scene_c, b3_lv)

                    fs_tasks = getattr(fs, "tasks", set())
                    unfold_prog = getattr(fs, "unfold_progress", 1.0 if "unfold" in fs_tasks else 0.0)
                    if "unfold" in fs_tasks and unfold_prog <= 0.001:
                        unfold_prog = 1.0

                    if unfold_prog <= 0.001:
                        faces.append(Face(b1_3d, b2_3d, b3_3d, face_col))
                        faces.append(Face(b1_3d, b3_3d, b2_3d, face_col))
                        faces.append(Face(b1_3d, b2_3d, apex_3d, face_col))
                        faces.append(Face(b2_3d, b3_3d, apex_3d, face_col))
                        faces.append(Face(b3_3d, b1_3d, apex_3d, face_col))
                        faces.append(Face(b1_3d, apex_3d, b2_3d, face_col))
                        faces.append(Face(b2_3d, apex_3d, b3_3d, face_col))
                        faces.append(Face(b3_3d, apex_3d, b1_3d, face_col))

                        lines.append(Line(b1_3d, b2_3d, edge_col, edge_w))
                        lines.append(Line(b2_3d, b3_3d, edge_col, edge_w))
                        lines.append(Line(b3_3d, b1_3d, edge_col, edge_w))
                        lines.append(Line(b1_3d, apex_3d, edge_col, edge_w))
                        lines.append(Line(b2_3d, apex_3d, edge_col, edge_w))
                        lines.append(Line(b3_3d, apex_3d, edge_col, edge_w))

                        balls.append(Ball(apex_3d, 0.026, ball_col))
                        balls.append(Ball(b1_3d, 0.02, ball_col))
                        balls.append(Ball(b2_3d, 0.02, ball_col))
                        balls.append(Ball(b3_3d, 0.02, ball_col))
                    else:
                        # Base face (Mặt đáy)
                        faces.append(Face(b1_3d, b2_3d, b3_3d, "#7e22ce"))
                        faces.append(Face(b1_3d, b3_3d, b2_3d, "#7e22ce"))
                        c_b_3d = (
                            (b1_3d[0] + b2_3d[0] + b3_3d[0]) / 3.0,
                            (b1_3d[1] + b2_3d[1] + b3_3d[1]) / 3.0,
                            (b1_3d[2] + b2_3d[2] + b3_3d[2]) / 3.0,
                        )
                        labels.append((c_b_3d, "Mặt đáy"))

                        # Unfold 3 lateral faces outward along base edges into star net
                        pyramid_edges = [
                            (b1_lv, b2_lv, b3_lv, "Mặt bên 1", "#9333ea"),
                            (b2_lv, b3_lv, b1_lv, "Mặt bên 2", "#a855f7"),
                            (b3_lv, b1_lv, b2_lv, "Mặt bên 3", "#c084fc"),
                        ]
                        total_s_xq = 0.0
                        for pA, pB, pOpp, face_lbl, face_color in pyramid_edges:
                            # Hinge line in amber
                            lines.append(Line(_rotate_local(scene_c, pA), _rotate_local(scene_c, pB), "#f59e0b", 3.5))
                            balls.append(Ball(_rotate_local(scene_c, pA), 0.024, "#fbbf24"))
                            balls.append(Ball(_rotate_local(scene_c, pB), 0.024, "#fbbf24"))

                            u_edge = (pB[0] - pA[0], pB[1] - pA[1], 0.0)
                            len_u = math.hypot(u_edge[0], u_edge[1])
                            if len_u < 1e-6:
                                continue
                            t_proj = ((apex_lv[0] - pA[0]) * u_edge[0] + (apex_lv[1] - pA[1]) * u_edge[1]) / (len_u ** 2)
                            foot = (pA[0] + t_proj * u_edge[0], pA[1] + t_proj * u_edge[1], 0.0)
                            h_vec = (apex_lv[0] - foot[0], apex_lv[1] - foot[1], apex_lv[2] - foot[2])
                            h_slant = math.sqrt(h_vec[0]**2 + h_vec[1]**2 + h_vec[2]**2)
                            if h_slant < 1e-6:
                                continue
                            total_s_xq += 0.5 * len_u * h_slant
                            v0 = (h_vec[0] / h_slant, h_vec[1] / h_slant, h_vec[2] / h_slant)

                            # Outward normal in z=0 plane pointing away from pOpp
                            n_cand = (-u_edge[1] / len_u, u_edge[0] / len_u, 0.0)
                            dot_opp = n_cand[0] * (pOpp[0] - foot[0]) + n_cand[1] * (pOpp[1] - foot[1])
                            n_out = (-n_cand[0], -n_cand[1], 0.0) if dot_opp > 0 else n_cand

                            # Rotation angle from v0 to n_out
                            cos_alpha = max(-1.0, min(1.0, v0[0] * n_out[0] + v0[1] * n_out[1] + v0[2] * n_out[2]))
                            alpha = math.acos(cos_alpha)
                            beta = (1.0 - unfold_prog) * alpha
                            v_th = (
                                math.cos(beta) * n_out[0],
                                math.cos(beta) * n_out[1],
                                math.sin(beta),
                            )
                            apex_rot = (
                                foot[0] + h_slant * v_th[0],
                                foot[1] + h_slant * v_th[1],
                                foot[2] + h_slant * v_th[2],
                            )

                            pA_3d = _rotate_local(scene_c, pA)
                            pB_3d = _rotate_local(scene_c, pB)
                            apex_rot_3d = _rotate_local(scene_c, apex_rot)

                            faces.append(Face(pA_3d, pB_3d, apex_rot_3d, face_color))
                            faces.append(Face(pA_3d, apex_rot_3d, pB_3d, face_color))
                            lines.append(Line(pA_3d, apex_rot_3d, edge_col, edge_w))
                            lines.append(Line(pB_3d, apex_rot_3d, edge_col, edge_w))
                            balls.append(Ball(apex_rot_3d, 0.024, ball_col))

                            c_face_3d = (
                                (pA_3d[0] + pB_3d[0] + apex_rot_3d[0]) / 3.0,
                                (pA_3d[1] + pB_3d[1] + apex_rot_3d[1]) / 3.0,
                                (pA_3d[2] + pB_3d[2] + apex_rot_3d[2]) / 3.0,
                            )
                            labels.append((c_face_3d, face_lbl))

                        u_b = np.array([b2_lv[0] - b1_lv[0], b2_lv[1] - b1_lv[1], 0.0])
                        v_b = np.array([b3_lv[0] - b1_lv[0], b3_lv[1] - b1_lv[1], 0.0])
                        s_b = 0.5 * float(np.linalg.norm(np.cross(u_b, v_b)))
                        labels.append((
                            _rotate_local(scene_c, (0, 0, apex_h + 0.12)),
                            f"Bung mặt phẳng: Chóp tam giác | S_tp = {s_b + total_s_xq:.2f}"
                        ))
                    if "distance" in fs_tasks:
                        lines.append(Line(b1_3d, b2_3d, "#38bdf8", 4.0))
                        mid12 = ((b1_3d[0] + b2_3d[0]) / 2, (b1_3d[1] + b2_3d[1]) / 2, (b1_3d[2] + b2_3d[2]) / 2)
                        labels.append((mid12, f"a={base_sz:.2f}"))
                        lines.append(Line(_rotate_local(scene_c, (0, 0, 0)), apex_3d, "#f59e0b", 3.0))
                        mid_h = ((scene_c[0] + apex_3d[0]) / 2, (scene_c[1] + apex_3d[1]) / 2, (scene_c[2] + apex_3d[2]) / 2)
                        labels.append((mid_h, f"h={apex_h:.2f}"))

                    if "metrics" in fs_tasks:
                        u_b = np.array([b2_lv[0] - b1_lv[0], b2_lv[1] - b1_lv[1], 0.0])
                        v_b = np.array([b3_lv[0] - b1_lv[0], b3_lv[1] - b1_lv[1], 0.0])
                        s_b = 0.5 * float(np.linalg.norm(np.cross(u_b, v_b)))
                        vol = (1.0 / 3.0) * s_b * apex_h
                        labels.append((_rotate_local(scene_c, (0, 0, apex_h + 0.06)), f"V={vol:.2f}"))

                        vis_base = float((view_mat @ (R @ np.array([0.0, 0.0, -1.0])))[2])
                        if vis_base > 0.15:
                            c_b = ((b1_lv[0] + b2_lv[0] + b3_lv[0]) / 3, (b1_lv[1] + b2_lv[1] + b3_lv[1]) / 3, 0.0)
                            labels.append((_rotate_local(scene_c, c_b), f"S_đáy={s_b:.2f}"))

                        sides = [(b1_lv, b2_lv), (b2_lv, b3_lv), (b3_lv, b1_lv)]
                        for pA, pB in sides:
                            u_side = np.array(pB) - np.array(pA)
                            v_side = np.array(apex_lv) - np.array(pA)
                            w_side = np.cross(u_side, v_side)
                            w_norm = float(np.linalg.norm(w_side))
                            if w_norm > 1e-6:
                                n_side = w_side / w_norm
                                vis_side = float((view_mat @ (R @ n_side))[2])
                                if vis_side > 0.15:
                                    s_side = 0.5 * w_norm
                                    c_side = ((pA[0] + pB[0] + apex_lv[0]) / 3, (pA[1] + pB[1] + apex_lv[1]) / 3, (pA[2] + pB[2] + apex_lv[2]) / 3)
                                    labels.append((_rotate_local(scene_c, c_side), f"S={s_side:.2f}"))

                    if "cross_section" in fs_tasks:
                        m1 = ((b1_lv[0] + apex_lv[0]) / 2, (b1_lv[1] + apex_lv[1]) / 2, (b1_lv[2] + apex_lv[2]) / 2)
                        m2 = ((b2_lv[0] + apex_lv[0]) / 2, (b2_lv[1] + apex_lv[1]) / 2, (b2_lv[2] + apex_lv[2]) / 2)
                        m3 = ((b3_lv[0] + apex_lv[0]) / 2, (b3_lv[1] + apex_lv[1]) / 2, (b3_lv[2] + apex_lv[2]) / 2)
                        m1_3d = _rotate_local(scene_c, m1)
                        m2_3d = _rotate_local(scene_c, m2)
                        m3_3d = _rotate_local(scene_c, m3)
                        faces.append(Face(m1_3d, m2_3d, m3_3d, "#a855f7"))
                        faces.append(Face(m1_3d, m3_3d, m2_3d, "#a855f7"))
                        lines.append(Line(m1_3d, m2_3d, "#d8b4fe", 3.5))
                        lines.append(Line(m2_3d, m3_3d, "#d8b4fe", 3.5))
                        lines.append(Line(m3_3d, m1_3d, "#d8b4fe", 3.5))
                        balls.append(Ball(m1_3d, 0.024, "#f3e8ff"))
                        balls.append(Ball(m2_3d, 0.024, "#f3e8ff"))
                        balls.append(Ball(m3_3d, 0.024, "#f3e8ff"))
                        labels.append((m1_3d, "Thiết diện tam giác"))
                elif corners:
                    sc_pts = [_norm_to_scene(*c) for c in corners]
                    n = len(sc_pts)
                    for i in range(n):
                        lines.append(Line(sc_pts[i], sc_pts[(i + 1) % n], edge_col, edge_w))
                    balls.append(Ball(scene_c, 0.02, ball_col))

        return Geometry(tuple(lines), tuple(balls), tuple(labels), tuple(faces))

    def update(self, dt):
        if not math.isfinite(dt) or dt < 0:
            raise ValueError("scene dt must be finite nonnegative")
        if self.active and not self.paused:
            self.time += dt * self.time_rate

    def set_preset(self, preset):
        if preset not in self.presets:
            raise ValueError("unknown preset")
        self.preset = preset
        self.selection = self.hover = None

    def set_tool(self, tool):
        if tool not in self.tools:
            raise ValueError("unknown tool")
        self.tool = tool
        self.points = []
        self.construction_error = ""

    def on_intent(self, intent):
        if not self.active:
            return
        t = intent.type
        if t in {IntentType.CANCEL, IntentType.RELEASE}:
            self.live_shape = None
            self.dragging = False
            self.preview = self.hover = None
            self.pair_preview = ()
            self.reference_plane = None
            return
        if not intent.validity:
            return
        if intent.live_geometry:
            self.live_shape = build_live_shape(
                intent.points,
                intent.vertex_tokens,
                self.config.palm_epsilon,
                self.config.construction_tolerance,
                self.config.geometry_planarity_ratio,
            )
            self.dragging = False
            self.preview = intent.points[
                min(range(len(intent.points)), key=lambda i: intent.vertex_tokens[i])
            ]
            self.pair_preview = ()
            self.hover = self.pick(self.preview)
            return
        self.reference_plane = intent.anchor_pose
        if t in {IntentType.POINT, IntentType.MEASURE_UPDATE, IntentType.TOOL_UPDATE}:
            self.preview = intent.world_or_scene_point
            self.pair_preview = intent.points
            if intent.points and intent.reason == "LOCKED" and self.tool == "Inspect":
                self.tool = "Distance"
            self.hover = self.pick(self.preview)
        elif t is IntentType.MEASURE_BEGIN:
            self.set_tool("Distance")
        elif (
            t in {IntentType.MEASURE_COMMIT, IntentType.TOOL_COMMIT}
            and intent.phase is Phase.BEGIN
        ):
            key = (intent.input_source, intent.tool_id, intent.cycle_id)
            if key in self._committed:
                return
            self._committed.add(key)
            pts = intent.points or (
                ()
                if intent.world_or_scene_point is None
                else (intent.world_or_scene_point,)
            )
            self.points.extend(pts)
            self.pair_preview = ()
            count = {
                "Distance": 2,
                "Vector": 2,
                "Angle": 3,
                "Plane": 3,
                "Triangle": 3,
                "Rectangle": 4,
                "Quadrilateral": 4,
                "Polygon": 0,
            }.get(self.tool, 2)
            if count and len(self.points) >= count:
                if self.tool == "Rectangle" and not self.is_rectangle(self.points[:4]):
                    self.construction_error = "Rectangle unavailable: use four noncoincident corners in order, with right angles. Undo the last point to correct, or use Quadrilateral for arbitrary corners."
                    return
                self.construction_error = ""
                self.constructions.append((self.tool, tuple(self.points[:count])))
                self.points = self.points[count:]
        elif t in {IntentType.GRAB, IntentType.SELECT}:
            self.selection = self.pick(intent.world_or_scene_point)
            self.dragging = True
        elif t is IntentType.DRAG and self.dragging:
            self.yaw += intent.delta_xy[0]
            self.pitch = max(-1.45, min(1.45, self.pitch + intent.delta_xy[1]))
        elif t is IntentType.SCALE:
            if intent.phase is Phase.BEGIN:
                self._scale_start = self.scale
            self.scale = max(
                self.config.min_scale,
                min(self.config.max_scale, self._scale_start * intent.scale_factor),
            )

    def finish_polygon(self):
        if self.tool == "Polygon" and len(self.points) >= 3:
            self.constructions.append((self.tool, tuple(self.points)))
            self.points = []

    def is_rectangle(self, points):
        p = np.asarray(points, dtype=float)
        edges = np.roll(p, -1, axis=0) - p
        lengths = np.linalg.norm(edges, axis=1)
        tolerance = self.config.construction_tolerance
        if np.any(lengths <= tolerance):
            return False
        unit = edges / lengths[:, None]
        return bool(
            np.all(
                np.abs(np.sum(unit * np.roll(unit, -1, axis=0), axis=1)) <= tolerance
            )
            and np.linalg.norm(edges[0] + edges[2]) <= tolerance * max(lengths)
            and np.linalg.norm(edges[1] + edges[3]) <= tolerance * max(lengths)
        )

    def pick(self, point):
        if point is None:
            return None
        return None

    def measurements(self):
        values = []
        for tool, pts in self.export_constructions():
            if len(pts) >= 2:
                v = np.array(pts[1]) - pts[0]
                values.append(
                    f"{tool}: distance {np.linalg.norm(v):.3f} scene units; vector {tuple(round(float(x),3) for x in v)}"
                )
            if len(pts) >= 3:
                a, b = np.array(pts[0]) - pts[1], np.array(pts[2]) - pts[1]
                denom = np.linalg.norm(a) * np.linalg.norm(b)
                values.append(
                    "Angle: unavailable (coincident points)"
                    if denom <= self.config.palm_epsilon
                    else f"Angle: {math.degrees(math.acos(float(np.clip(np.dot(a,b)/denom,-1,1)))):.2f} degrees"
                )
                normal = np.cross(np.array(pts[1]) - pts[0], np.array(pts[2]) - pts[0])
                norm = np.linalg.norm(normal)
                values.append(
                    "Plane: unavailable (collinear points)"
                    if norm <= self.config.palm_epsilon
                    else f"Plane normal: {tuple(round(float(v),3) for v in normal/norm)}; triangle area: {norm/2:.3f}"
                )
        return values

    def export_constructions(self):
        if self.live_enabled:
            return (
                []
                if self.live_shape is None
                else [(self.live_shape.kind, self.live_shape.points)]
            )
        return self.constructions

    def constructed(self):
        if self.live_enabled:
            return render_live(
                self.live_shape,
                self.config.palm_epsilon,
                fill=self.live_surface_overlay,
            )
        lines, balls = [], []
        for tool, pts in [*self.constructions, (self.tool, tuple(self.points))]:
            balls.extend(
                Ball(p, 0.055, "#efca82", str(i + 1)) for i, p in enumerate(pts)
            )
            lines.extend(Line(a, b, "#efca82", 2.5) for a, b in zip(pts, pts[1:]))
            if (
                tool in {"Triangle", "Plane", "Rectangle", "Quadrilateral", "Polygon"}
                and len(pts) >= 3
            ):
                lines.append(Line(pts[-1], pts[0], "#efca82", 2.5))
        if self.preview is not None and self.tool != "Inspect":
            balls.append(Ball(self.preview, 0.045, "#e7eef0", "preview"))
            if self.points:
                lines.append(Line(self.points[-1], self.preview, "#8499a0"))
        if len(self.pair_preview) == 2:
            lines.append(Line(*self.pair_preview, "#efca82", 2.5))
            balls.extend(
                Ball(p, 0.055, "#efca82", "preview") for p in self.pair_preview
            )
        if self.reference_plane is not None:
            a = self.reference_plane
            normal = np.array(
                (
                    math.sin(a.yaw_rad) * math.cos(a.pitch_rad),
                    -math.sin(a.pitch_rad),
                    math.cos(a.yaw_rad) * math.cos(a.pitch_rad),
                )
            )
            u = np.array((math.cos(a.yaw_rad), 0.0, -math.sin(a.yaw_rad)))
            v = np.cross(normal, u)
            corners = [
                tuple(x * u + y * v) for x, y in ((-1, -1), (1, -1), (1, 1), (-1, 1))
            ]
            lines.extend(
                Line(p, q, "#a6bd9c", 2.0)
                for p, q in zip(corners, corners[1:] + corners[:1])
            )
        return Geometry(tuple(lines), tuple(balls))

    def geometry(self):
        return Geometry()

    def render(self, context=None):
        g, c = self.geometry(), self.constructed()
        return Geometry(
            g.lines + c.lines, g.balls + c.balls, g.labels, g.faces + c.faces
        )

    def inspect(self):
        if self.live_enabled:
            shape = self.live_shape
            return [
                "Live fingertips: automatic geometry; no Add point or pinch required.",
                (
                    "No active vertices"
                    if shape is None
                    else f"{shape.kind}: {len(shape.points)} live vertices"
                ),
                *(
                    []
                    if shape is None
                    else [
                        f"{'Edge length' if shape.solid else 'Length' if len(shape.points) == 2 else 'Boundary length'}: {shape.perimeter:.3f} scene units",
                        *(
                            [
                                f"Closed convex volume: {shape.volume:.3f} scene units cubed (visual scene only)"
                            ]
                            if shape.solid
                            else []
                        ),
                    ]
                ),
                *(
                    ["Shape unavailable: coincident/collinear vertices"]
                    if shape and shape.degenerate
                    else []
                ),
                "Scene units; model-relative depth is a visual cue, not physical camera depth.",
                self.dimensionality,
                *self.measurements(),
            ]
        return [
            f"Tool: {self.tool}",
            f"Selection: {self.selection if self.selection is not None else 'none'}",
            f"Probe: {tuple(round(v,3) for v in self.preview) if self.preview is not None else 'none'}",
            *(
                [
                    f"Pair preview: {np.linalg.norm(np.array(self.pair_preview[1])-self.pair_preview[0]):.3f} scene units"
                ]
                if len(self.pair_preview) == 2
                else []
            ),
            "Distances use scene units, not camera depth.",
            *([self.construction_error] if self.construction_error else []),
            *self.measurements(),
        ]

    def vertex_details(self):
        shape = self.live_shape
        return (
            []
            if shape is None
            else [
                "Live vertex XYZ (scene units):",
                *(
                    f"{label}: {tuple(round(v, 3) for v in p)}"
                    for label, p in sorted(zip(shape.labels, shape.points))
                ),
            ]
        )

"""Small product extension API and reusable construction/measurement tools."""

from dataclasses import dataclass, field
from typing import Protocol
import math
import numpy as np
from app.interaction.contracts import GestureIntent, IntentType, Phase


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
class Geometry:
    lines: tuple[Line, ...] = ()
    balls: tuple[Ball, ...] = ()
    labels: tuple[tuple[tuple, str], ...] = ()


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
    tools = (
        "Inspect",
        "Distance",
        "Vector",
        "Angle",
        "Plane",
        "Triangle",
        "Rectangle",
        "Polygon",
    )
    presets = ("Default",)

    def __init__(self, config):
        self.config = config
        self.active = False
        self.preset = self.presets[0]
        self.reset()

    def activate(self):
        self.active = True

    def deactivate(self):
        self.active = False
        self.dragging = False

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
        self.parameters = {
            "amplitude": 1.0,
            "frequency": 1.0,
            "phase": 0.0,
            "samples": 32.0,
            "radius": 1.5,
            "index": 1.5,
            "focal": 1.0,
        }

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

    def on_intent(self, intent):
        if not self.active:
            return
        t = intent.type
        if t in {IntentType.CANCEL, IntentType.RELEASE}:
            self.dragging = False
            self.preview = self.hover = None
            self.pair_preview = ()
            self.reference_plane = None
            return
        if not intent.validity:
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
                "Polygon": 0,
            }.get(self.tool, 2)
            if count and len(self.points) >= count:
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

    def pick(self, point):
        if point is None:
            return None
        return None

    def measurements(self):
        values = []
        for tool, pts in self.constructions:
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

    def constructed(self):
        lines, balls = [], []
        for tool, pts in [*self.constructions, (self.tool, tuple(self.points))]:
            balls.extend(
                Ball(p, 0.055, "#efca82", str(i + 1)) for i, p in enumerate(pts)
            )
            lines.extend(Line(a, b, "#efca82", 2.5) for a, b in zip(pts, pts[1:]))
            if tool in {"Triangle", "Plane", "Rectangle", "Polygon"} and len(pts) >= 3:
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
        return Geometry(g.lines + c.lines, g.balls + c.balls, g.labels)

    def inspect(self):
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
            *self.measurements(),
        ]

"""Educational geometry and analytic models; no tracking/gesture imports."""

import math
import numpy as np
from .base import Lab, Geometry, Line, Ball, Face


def arrow(a, b, color="#72bfcc"):
    a, b = np.asarray(a, float), np.asarray(b, float)
    direction = b - a
    norm = np.linalg.norm(direction)
    if norm < 1e-9:
        return ()
    d = direction / norm
    cross = np.cross(d, (0.0, 0.0, 1.0))
    if np.linalg.norm(cross) < 1e-6:
        cross = np.cross(d, (0.0, 1.0, 0.0))
    cross /= np.linalg.norm(cross)
    tip = min(0.18, norm * 0.25)
    return (
        Line(tuple(a), tuple(b), color, 2.0),
        Line(tuple(b), tuple(b - d * tip + cross * tip * 0.5), color, 2.0),
        Line(tuple(b), tuple(b - d * tip - cross * tip * 0.5), color, 2.0),
    )


class CoordinateLab(Lab):
    id, title, category = "coordinate", "Coordinate Lab", "Mathematics"
    dimensionality = "3D coordinates / live geometry"
    live_surface_overlay = True

    def geometry(self):
        lines = []
        for i in np.linspace(-2, 2, 9):
            lines.extend(
                (
                    Line((-2, i, 0), (2, i, 0), "#283d47"),
                    Line((i, -2, 0), (i, 2, 0), "#283d47"),
                )
            )
        for end, color in (
            ((2.0, 0, 0), "#dd857c"),
            ((0, 2.0, 0), "#89b895"),
            ((0, 0, 2.0), "#839fc7"),
        ):
            lines.extend(arrow((0, 0, 0), end, color))
        return Geometry(
            tuple(lines),
            (Ball((0, 0, 0), 0.07, "#efca82"),),
            (((2.1, 0, 0), "X"), ((0, 2.1, 0), "Y"), ((0, 0, 2.1), "Z")),
        )


class MoleculeLab(Lab):
    id, title, category = "molecule", "Molecular Lab", "Chemistry"
    presets = ("CH4", "H2O", "CO2", "NH3")

    @property
    def dimensionality(self):
        return (
            "Planar molecule / 3D atom meshes"
            if self.preset in {"H2O", "CO2"}
            else "Spatial molecule / 3D atom meshes"
        )

    @property
    def view_radius(self):
        return max(np.linalg.norm(a.center) + a.radius for a in self.atoms()[0])

    def atoms(self):
        # Preserve existing H2O/CH4 preset definitions and geometry without editing them.
        if self.preset in {"H2O", "CH4"}:
            from extensions.stem3d.scenes.molecule import MOLECULE_PRESETS

            preset = MOLECULE_PRESETS[self.preset]
            atoms = tuple(
                Ball(
                    a.position,
                    a.radius,
                    "#%02x%02x%02x" % tuple(round(v * 255) for v in a.color),
                    a.element,
                )
                for a in preset.atoms
            )
            bonds = tuple((b.atom_a, b.atom_b) for b in preset.bonds)
            return atoms, bonds
        if self.preset == "CO2":
            return (
                Ball((0, 0, 0), 0.3, "#7e94aa", "C"),
                Ball((-1.2, 0, 0), 0.28, "#d48179", "O"),
                Ball((1.2, 0, 0), 0.28, "#d48179", "O"),
            ), ((0, 1), (0, 2))
        # NIST CCCBDB H-N-H reference angle. Length remains a scene unit, not a bond measurement.
        cosine = math.cos(math.radians(self.config.molecule_nh3_angle_deg))
        height = math.sqrt((cosine + 0.5) / (1 - cosine))
        return (
            Ball((0, height / 2, 0), 0.3, "#839fc7", "N"),
            *(
                Ball((math.cos(a), -height / 2, math.sin(a)), 0.17, "#dce8eb", "H")
                for a in (0, 2 * math.pi / 3, 4 * math.pi / 3)
            ),
        ), ((0, 1), (0, 2), (0, 3))

    def geometry(self):
        atoms, bonds = self.atoms()
        balls = tuple(
            (
                Ball(a.center, a.radius * 1.08, "#efca82", a.label)
                if i in {self.hover, self.selection}
                else a
            )
            for i, a in enumerate(atoms)
        )
        lines = []
        for a, b in bonds:
            start, end = np.array(atoms[a].center), np.array(atoms[b].center)
            unit = (end - start) / np.linalg.norm(end - start)
            lines.append(
                Line(
                    tuple(start + unit * atoms[a].radius * 0.95),
                    tuple(end - unit * atoms[b].radius * 0.95),
                    "#9fb2ba",
                    6.0,
                )
            )
        return Geometry(tuple(lines), balls)

    def pick(self, point):
        if point is None:
            return None
        atoms, _ = self.atoms()
        closest = min(
            range(len(atoms)),
            key=lambda i: np.linalg.norm(np.asarray(atoms[i].center) - point),
        )
        return (
            closest
            if np.linalg.norm(np.asarray(atoms[closest].center) - point)
            < atoms[closest].radius * 2.5
            else None
        )

    def inspect(self):
        atoms, bonds = self.atoms()
        values = [
            f"Preset: {self.preset}",
            "Idealized educational geometry; scene distances are not chemical bond lengths.",
        ]
        for a, b in bonds:
            values.append(
                f"Bond {a+1}-{b+1}: {np.linalg.norm(np.array(atoms[a].center)-atoms[b].center):.3f} scene units"
            )
        neighbors = [b for a, b in bonds if a == 0]
        for j, a in enumerate(neighbors):
            for b in neighbors[j + 1 :]:
                u, v = (
                    np.array(atoms[a].center) - atoms[0].center,
                    np.array(atoms[b].center) - atoms[0].center,
                )
                angle = math.degrees(
                    math.acos(
                        float(
                            np.clip(
                                np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v)),
                                -1,
                                1,
                            )
                        )
                    )
                )
                values.append(f"Angle {a+1}-1-{b+1}: {angle:.2f} degrees")
        return values + super().inspect()


class OrbitalLab(Lab):
    id, title, category = "orbital", "Orbital Lab", "Astronomy"
    dimensionality = "Planar orbit / 3D bodies"

    @property
    def view_radius(self):
        return max(0.4, self.parameters["radius"] + 0.2)

    def geometry(self):
        radius = self.parameters["radius"]
        pts = [
            (radius * math.cos(a), 0, radius * math.sin(a))
            for a in np.linspace(0, 2 * math.pi, 121)
        ]
        theta = self.time
        return Geometry(
            tuple(Line(a, b, "#3b6573") for a, b in zip(pts, pts[1:])),
            (
                Ball((0, 0, 0), 0.35, "#efca82", "Central body"),
                Ball(
                    (radius * math.cos(theta), 0, radius * math.sin(theta)),
                    0.17,
                    "#78b6c4",
                    "Orbiter",
                ),
            ),
        )

    def inspect(self):
        return [
            f"Radius: {self.parameters['radius']:.2f} scene units",
            f"Illustrative period: {2*math.pi/self.time_rate:.3f} scene seconds",
            f"Phase: {self.time%(2*math.pi):.2f} rad",
            "Kinematic illustration; not a gravitational simulation.",
        ] + super().inspect()


class VectorLab(CoordinateLab):
    id, title, category = "vector", "Vector Lab", "Mathematics"
    dimensionality = "3D vectors / sum / cross product"

    def vectors(self):
        if self.live_enabled:
            shape = self.live_shape
            pts = (
                []
                if shape is None
                else [p for _, p in sorted(zip(shape.tokens, shape.points))]
            )
            return (
                np.array(pts[1]) - pts[0] if len(pts) >= 2 else None,
                np.array(pts[3]) - pts[2] if len(pts) >= 4 else None,
            )
        pts = [p for _, group in self.constructions for p in group] + self.points
        if len(pts) < 2:
            return np.array((1.0, 0.5, 0.0)), np.array((0.3, 1.0, 0.7))
        u = np.array(pts[1]) - pts[0]
        v = np.array(pts[3]) - pts[2] if len(pts) >= 4 else np.array((0.3, 1.0, 0.7))
        return u, v

    def geometry(self):
        g = super().geometry()
        u, v = self.vectors()
        labels = []
        lines = arrow((0, 0, 0), u) if u is not None else ()
        if v is not None:
            lines += arrow((0, 0, 0), v, "#d5ab77")
        if u is not None and v is not None:
            lines += arrow((0, 0, 0), u + v, "#a293c7") + arrow(
                (0, 0, 0), np.cross(u, v), "#89b895"
            )
        for point, label in ((u, "u"), (v, "v")):
            if point is not None:
                labels.append((tuple(point), label))
        if u is not None and v is not None:
            labels.extend(((tuple(u + v), "u + v"), (tuple(np.cross(u, v)), "u × v")))
        return Geometry(g.lines + lines, g.balls, g.labels + tuple(labels))

    def inspect(self):
        u, v = self.vectors()
        if u is None or v is None:
            return [
                "LIVE u: A → B; v: C → D. Extend four tips for both vectors.",
                (
                    "u: unavailable (show at least two tips)"
                    if u is None
                    else f"u: {np.round(u, 3)}"
                ),
                "v / sum / dot / cross / projection: unavailable (show at least four tips)",
            ] + super().inspect()
        vv = np.dot(v, v)
        proj = None if vv <= self.config.palm_epsilon**2 else np.dot(u, v) / vv * v
        return [
            *(["LIVE u: A → B; v: C → D."] if self.live_enabled else []),
            f"u: {np.round(u,3)}",
            f"v: {np.round(v,3)}",
            f"u + v: {np.round(u+v,3)}",
            f"Dot: {np.dot(u,v):.3f}",
            f"Cross: {np.round(np.cross(u,v),3)}",
            (
                "Projection on v: unavailable (zero reference vector)"
                if proj is None
                else f"Projection on v: {np.round(proj,3)}"
            ),
        ] + super().inspect()


class SurfaceLab(Lab):
    id, title, category = "surface", "Function Surface Lab", "Mathematics"
    presets = ("Plane", "Paraboloid", "Saddle", "Wave surface", "Gaussian")
    dimensionality = "Analytic function surface / XYZ"

    def value(self, x, y):
        return {
            "Plane": lambda: 0.3 * x + 0.2 * y,
            "Paraboloid": lambda: 0.25 * (x * x + y * y),
            "Saddle": lambda: 0.3 * (x * x - y * y),
            "Wave surface": lambda: 0.5 * math.sin(2 * x) * math.cos(2 * y),
            "Gaussian": lambda: math.exp(-x * x - y * y),
        }[self.preset]()

    def gradient(self, x, y):
        return {
            "Plane": lambda: (0.3, 0.2),
            "Paraboloid": lambda: (0.5 * x, 0.5 * y),
            "Saddle": lambda: (0.6 * x, -0.6 * y),
            "Wave surface": lambda: (
                math.cos(2 * x) * math.cos(2 * y),
                -math.sin(2 * x) * math.sin(2 * y),
            ),
            "Gaussian": lambda: (-2 * x * self.value(x, y), -2 * y * self.value(x, y)),
        }[self.preset]()

    def geometry(self):
        samples = np.linspace(-2, 2, 25)
        lines = []
        faces = []
        for x1, x2 in zip(samples, samples[1:]):
            for y1, y2 in zip(samples, samples[1:]):
                a, b, c, d = [
                    (x, y, self.value(x, y))
                    for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2))
                ]
                faces.extend((Face(a, b, c), Face(a, c, d)))
        for fixed in samples:
            a = [(fixed, t, self.value(fixed, t)) for t in samples]
            b = [(t, fixed, self.value(t, fixed)) for t in samples]
            lines.extend(
                Line(p, q, "#426f7a") for seq in (a, b) for p, q in zip(seq, seq[1:])
            )
        # Contours from edge crossings of fixed analytic levels; no external plotting dependency.
        for level in (-0.5, 0.0, 0.5, 1.0):
            for x1, x2 in zip(samples, samples[1:]):
                for y1, y2 in zip(samples, samples[1:]):
                    corners = [(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]
                    hits = []
                    for a, b in zip(corners, corners[1:]):
                        za, zb = self.value(*a), self.value(*b)
                        if (za <= level < zb) or (zb <= level < za):
                            t = (level - za) / (zb - za)
                            hits.append(
                                (
                                    a[0] + t * (b[0] - a[0]),
                                    a[1] + t * (b[1] - a[1]),
                                    level,
                                )
                            )
                    lines.extend(
                        Line(a, b, "#baaa7e", 1.0)
                        for a, b in zip(hits[::2], hits[1::2])
                    )
        balls = ()
        if self.preview:
            x, y, _ = self.preview
            z = self.value(x, y)
            gx, gy = self.gradient(x, y)
            lines.extend(arrow((x, y, z), (x + 0.5 * gx, y + 0.5 * gy, z), "#efca82"))
            section = [(t, y, self.value(t, y)) for t in samples]
            lines.extend(
                Line(a, b, "#e9b589", 2.5) for a, b in zip(section, section[1:])
            )
            balls = (Ball((x, y, z), 0.07, "#efca82", "Probe"),)
        return Geometry(tuple(lines), balls, faces=tuple(faces))

    def inspect(self):
        p = self.preview or (0, 0, 0)
        return [
            f"z = {self.value(*p[:2]):.4f}",
            f"Gradient: {self.gradient(*p[:2])}",
            "Contour levels: -0.5, 0, 0.5, 1; section follows probe y.",
        ] + super().inspect()


class WaveLab(Lab):
    id, title, category = "wave", "Wave & Signal Lab", "Signals"
    presets = ("Sine", "Square", "Standing wave", "Sampling", "Filter response")
    dimensionality = "Planar signal graph / XY in a 3D workspace"

    @property
    def view_radius(self):
        return max(math.pi, self.parameters["amplitude"]) + 0.1

    def on_intent(self, intent):
        from app.interaction.contracts import IntentType

        if (
            intent.type is IntentType.DRAG
            and self.dragging
            and intent.world_or_scene_point is not None
        ):
            self.preview = intent.world_or_scene_point
            return
        super().on_intent(intent)

    def signal(self, x):
        a, f, p = (self.parameters[k] for k in ("amplitude", "frequency", "phase"))
        s = math.sin(f * x + p)
        if self.preset == "Square":
            s = 1.0 if s >= 0 else -1.0
        if self.preset == "Standing wave":
            s *= math.cos(f * self.time)
        return a * s

    def geometry(self):
        xs = np.linspace(-math.pi, math.pi, 193)
        pts = [(x, self.signal(x), 0.0) for x in xs]
        lines = [Line((-math.pi, 0, 0), (math.pi, 0, 0), "#42545c")] + [
            Line(a, b, "#72bfcc", 2.0) for a, b in zip(pts, pts[1:])
        ]
        sample_x = np.linspace(
            -math.pi, math.pi, max(4, int(self.parameters["samples"]))
        )
        balls = tuple(
            Ball((float(x), self.signal(x), 0.0), 0.045, "#efca82") for x in sample_x
        )
        if self.preset == "Filter response":
            f = self.parameters["frequency"]
            cutoff = 1.0
            gain, lag = 1 / math.sqrt(1 + (f / cutoff) ** 2), math.atan(f / cutoff)
            filtered = [
                (
                    x,
                    self.parameters["amplitude"]
                    * gain
                    * math.sin(f * x + self.parameters["phase"] - lag),
                    0.0,
                )
                for x in xs
            ]
            lines.extend(
                Line(a, b, "#bd9cce", 2.0) for a, b in zip(filtered, filtered[1:])
            )
        return Geometry(tuple(lines), balls)

    def inspect(self):
        x = (self.preview or (0, 0, 0))[0]
        return [
            f"Probe x: {x:.3f}; signal: {self.signal(x):.3f}",
            f"Amplitude: {self.parameters['amplitude']}; frequency: {self.parameters['frequency']} rad/unit",
            f"Samples: {int(self.parameters['samples'])}",
            "Filter response: analytic first-order low-pass, cutoff 1 rad/unit; unrelated to Core filtering.",
        ] + super().inspect()


class FieldLab(Lab):
    id, title, category = "vector-field", "Vector Field Lab", "Physics"
    presets = ("Radial", "Rotational", "Electric", "Magnetic", "Fluid-like")
    dimensionality = "3D vector field / illustrative streamline"

    def field(self, x, y, z=0.0):
        r = max(0.2, math.hypot(x, y))
        return {
            "Radial": lambda: np.array((x, y, z)),
            "Rotational": lambda: np.array((-y, x, 0.0)),
            "Electric": lambda: np.array((x, y, z))
            / max(0.2, math.sqrt(x * x + y * y + z * z)) ** 3,
            "Magnetic": lambda: np.array((-y, x, 0.0)) / r**2,
            "Fluid-like": lambda: np.array(
                (math.sin(y), math.cos(x), 0.2 * math.sin(z))
            ),
        }[self.preset]()

    def geometry(self):
        lines = []
        for z in (-0.65, 0.0, 0.65):
            for x in np.linspace(-1.5, 1.5, 7):
                for y in np.linspace(-1.5, 1.5, 7):
                    v = self.field(x, y, z)
                    v = v * 0.18 / max(1.0, np.linalg.norm(v))
                    lines.extend(arrow((x, y, z), np.array((x, y, z)) + v))
        p = np.array(self.preview or (0.5, 0.5, 0.0), float)
        for _ in range(120):
            v = self.field(*p)
            q = p + 0.025 * v / max(1.0, np.linalg.norm(v))
            lines.append(Line(tuple(p), tuple(q), "#efca82", 2.0))
            p = q
            if np.linalg.norm(p) > 4:
                break
        return Geometry(tuple(lines))

    def inspect(self):
        v = self.field(*(self.preview or (0, 0, 0)))
        return [
            f"Field: {np.round(v,3)}",
            f"Magnitude: {np.linalg.norm(v):.4f}",
            "Idealized fields in scene units; singularities regularized near origin.",
        ] + super().inspect()


class OpticsLab(Lab):
    id, title, category = "optics", "Optics Lab", "Physics"
    presets = ("Reflection", "Refraction", "Lens", "Mirror")
    tools = Lab.tools + ("Place element",)
    dimensionality = "Planar ray diagram / XY in a 3D workspace"

    @property
    def view_radius(self):
        return (
            max(2.0, self.parameters["focal"] + 0.1) if self.preset == "Lens" else 2.0
        )

    def reset(self):
        super().reset()
        self.element = (0.0, 0.0, 0.0)

    def on_intent(self, intent):
        from app.interaction.contracts import IntentType, Phase

        if (
            self.tool == "Place element"
            and self.active
            and intent.validity
            and intent.type in {IntentType.TOOL_COMMIT, IntentType.MEASURE_COMMIT}
            and intent.phase is Phase.BEGIN
            and intent.world_or_scene_point is not None
        ):
            key = (intent.input_source, intent.tool_id, intent.cycle_id)
            if key in self._committed:
                return
            self._committed.add(key)
            self.element = intent.world_or_scene_point
            return
        super().on_intent(intent)

    @staticmethod
    def refract(theta, n1, n2):
        sine = n1 / n2 * math.sin(theta)
        return None if abs(sine) > 1 else math.asin(sine)

    def geometry(self):
        shift = np.array(self.element)
        source = (
            tuple(np.asarray(self.preview) - shift)
            if self.preview is not None
            else (-1.7, 1.0, 0.0)
        )
        source = (min(-0.1, source[0]), source[1], 0.0)
        lines = [
            Line((0, -2, 0), (0, 2, 0), "#a3b7bd", 3.0),
            Line(source, (0, 0, 0), "#efca82", 3.0),
        ]
        theta = math.atan2(-source[1], -source[0])
        if self.preset in {"Reflection", "Mirror"}:
            end = (-2.0, 2 * math.tan(theta), 0.0)
        elif self.preset == "Refraction":
            angle = self.refract(theta, 1.0, self.parameters["index"])
            end = (
                (-2.0, 2 * math.tan(theta), 0.0)
                if angle is None
                else (2.0, 2 * math.tan(angle), 0.0)
            )
        else:
            focal = self.parameters["focal"]
            # Central paraxial ray passes through the optical centre unchanged.
            end = (2.0, -2 * source[1] / abs(source[0]), 0.0)
            lines.extend(
                (
                    Line((-2, 0, 0), (2, 0, 0), "#42545c"),
                    Line((focal, -0.1, 0), (focal, 0.1, 0), "#72bfcc"),
                    Line(source, (0, source[1], 0), "#bd9cce", 3.0),
                    Line(
                        (0, source[1], 0),
                        (2, source[1] * (1 - 2 / focal), 0),
                        "#bd9cce",
                        3.0,
                    ),
                )
            )
        lines.append(Line((0, 0, 0), end, "#72bfcc", 3.0))
        return Geometry(
            tuple(
                Line(
                    tuple(np.array(line.a) + shift),
                    tuple(np.array(line.b) + shift),
                    line.color,
                    line.width,
                )
                for line in lines
            ),
            (Ball(tuple(np.array(source) + shift), 0.08, "#efca82", "Source"),),
        )

    def inspect(self):
        return [
            f"Refractive index n2: {self.parameters['index']}",
            f"Focal length: {self.parameters['focal']} scene units",
            "Snell law for refraction; thin-lens/paraxial illustration; no wave optics.",
        ] + super().inspect()


class CrystalLab(Lab):
    id, title, category = "crystal", "Crystal Lattice Lab", "Materials"
    presets = ("Simple cubic", "Body-centered cubic", "Face-centered cubic")
    dimensionality = "3D lattice / reference plane z=0"

    def geometry(self):
        balls, lines = [], []
        for x in (-1, 0, 1):
            for y in (-1, 0, 1):
                for z in (-1, 0, 1):
                    p = (x, y, z)
                    balls.append(Ball(p, 0.11, "#72bfcc"))
                    for axis in range(3):
                        if p[axis] < 1:
                            q = list(p)
                            q[axis] += 1
                            lines.append(Line(p, tuple(q), "#3b6573"))
        for x in (-0.5, 0.5):
            for y in (-0.5, 0.5):
                for z in (-0.5, 0.5):
                    if self.preset == "Body-centered cubic":
                        balls.append(Ball((x, y, z), 0.11, "#efca82"))
                    elif self.preset == "Face-centered cubic":
                        for p in (
                            (x, y, z - 0.5),
                            (x, y, z + 0.5),
                            (x - 0.5, y, z),
                            (x + 0.5, y, z),
                            (x, y - 0.5, z),
                            (x, y + 0.5, z),
                        ):
                            if not any(b.center == p for b in balls):
                                balls.append(Ball(p, 0.11, "#efca82"))
        # Reference lattice plane z=0.
        lines.extend(
            Line(a, b, "#bd9cce", 2.0)
            for a, b in zip(
                ((-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)),
                ((1, -1, 0), (1, 1, 0), (-1, 1, 0), (-1, -1, 0)),
            )
        )
        return Geometry(tuple(lines), tuple(balls))

    def inspect(self):
        return [
            "Unit cell repeated 2 × 2 × 2; plane z=0.",
            "Illustrative lattice geometry; no material-specific atomic dimensions.",
        ] + super().inspect()

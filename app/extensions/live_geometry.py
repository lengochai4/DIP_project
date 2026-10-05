"""Automatic educational geometry from semantic scene vertices, no hand/provider data."""

from dataclasses import dataclass
from itertools import combinations
import numpy as np


@dataclass(frozen=True)
class LiveShape:
    kind: str
    points: tuple[tuple[float, float, float], ...]
    tokens: tuple[str, ...]
    degenerate: bool = False
    face_indices: tuple[tuple[int, int, int], ...] = ()
    edge_indices: tuple[tuple[int, int], ...] = ()

    @property
    def solid(self):
        return bool(self.face_indices)

    @property
    def labels(self):
        order = {token: chr(65 + i) for i, token in enumerate(sorted(self.tokens))}
        return tuple(order[token] for token in self.tokens)

    @property
    def volume(self):
        if not self.solid:
            return None
        p = np.asarray(self.points) - np.mean(self.points, axis=0)
        return (
            abs(
                sum(np.dot(p[a], np.cross(p[b], p[c])) for a, b, c in self.face_indices)
            )
            / 6
        )

    @property
    def perimeter(self):
        p = np.asarray(self.points)
        if len(p) < 2:
            return 0.0
        if self.solid:
            return float(sum(np.linalg.norm(p[a] - p[b]) for a, b in self.edge_indices))
        edges = np.diff(p, axis=0) if len(p) == 2 else np.roll(p, -1, axis=0) - p
        return float(np.linalg.norm(edges, axis=1).sum())


def convex_boundary(points, epsilon):
    """Supporting planes for at most ten vertices; merge coplanar hull facets.

    Uses normalized scene coordinates, with no camera or landmark interpretation.
    Interior/coincident samples stay in the source shape but are not boundary faces.
    """
    p = np.asarray(points, dtype=float)
    scale = float(np.max(np.linalg.norm(p - p.mean(axis=0), axis=1)))
    q = (p - p.mean(axis=0)) / scale
    tol = epsilon / scale
    facets = {}
    for a, b, c in combinations(range(len(q)), 3):
        normal = np.cross(q[b] - q[a], q[c] - q[a])
        length = np.linalg.norm(normal)
        if length <= tol:
            continue
        normal /= length
        distances = (q - q[a]) @ normal
        if np.all(distances <= tol):
            pass
        elif np.all(distances >= -tol):
            normal = -normal
        else:
            continue
        members = tuple(int(i) for i in np.flatnonzero(np.abs(distances) <= tol))
        facets.setdefault(members, normal)
    triangles, edges = [], set()
    for members, normal in sorted(facets.items()):
        axis = np.eye(3)[int(np.argmin(np.abs(normal)))]
        u = np.cross(normal, axis)
        u /= np.linalg.norm(u)
        v = np.cross(normal, u)
        xy = q @ np.vstack((u, v)).T
        order = sorted(members, key=lambda i: (*xy[i], i))
        unique = []
        for i in order:
            if not unique or np.linalg.norm(xy[i] - xy[unique[-1]]) > tol:
                unique.append(i)

        def half(indices):
            result = []
            for i in indices:
                while len(result) >= 2:
                    a, b = xy[result[-1]] - xy[result[-2]], xy[i] - xy[result[-1]]
                    if a[0] * b[1] - a[1] * b[0] > tol:
                        break
                    result.pop()
                result.append(i)
            return result

        boundary = half(unique)[:-1] + half(reversed(unique))[:-1]
        if len(boundary) < 3:
            continue
        triangles.extend(
            (boundary[0], boundary[j], boundary[j + 1])
            for j in range(1, len(boundary) - 1)
        )
        edges.update(
            tuple(sorted((a, b))) for a, b in zip(boundary, boundary[1:] + boundary[:1])
        )
    return tuple(triangles), tuple(sorted(edges))


def build_live_shape(
    points, tokens, epsilon, rectangle_tolerance, planarity_ratio=0.03
):
    p = np.asarray(points, dtype=float)
    if (
        not 1 <= len(points) <= 10
        or p.shape != (len(points), 3)
        or not np.isfinite(p).all()
        or len(tokens) != len(points)
        or len(set(tokens)) != len(tokens)
    ):
        raise ValueError("complete finite live vertices required")
    n = len(points)
    kind = {1: "Point", 2: "Distance", 3: "Triangle", 4: "Quadrilateral"}.get(
        n, "Polygon"
    )
    singular = np.linalg.svd(p - p.mean(axis=0), compute_uv=False)
    degenerate = n > 1 and singular[0] <= epsilon or n >= 3 and singular[1] <= epsilon
    faces, edges = (), ()
    if (
        n >= 4
        and not degenerate
        and singular[2] > max(epsilon, planarity_ratio * singular[0])
    ):
        faces, edges = convex_boundary(p, epsilon)
        if faces:
            kind = (
                "Tetrahedron"
                if len(set(i for face in faces for i in face)) == 4
                else "Polyhedron"
            )
    if n == 4 and not degenerate and not faces:
        quad_edges = np.roll(p, -1, axis=0) - p
        norms = np.linalg.norm(quad_edges, axis=1)
        if np.all(norms > epsilon):
            unit = quad_edges / norms[:, None]
            if (
                np.all(
                    np.abs(np.sum(unit * np.roll(unit, -1, axis=0), axis=1))
                    <= rectangle_tolerance
                )
                and np.linalg.norm(quad_edges[0] + quad_edges[2])
                <= rectangle_tolerance * max(norms)
                and np.linalg.norm(quad_edges[1] + quad_edges[3])
                <= rectangle_tolerance * max(norms)
            ):
                kind = "Rectangle"
    return LiveShape(
        kind,
        tuple(tuple(float(v) for v in q) for q in p),
        tuple(tokens),
        bool(degenerate),
        faces,
        edges,
    )


def render_live(shape, epsilon, *, fill=True):
    from .base import Geometry, Ball, Line, Face

    if shape is None:
        return Geometry()
    pts = shape.points
    edges = (
        [(pts[a], pts[b]) for a, b in shape.edge_indices]
        if shape.solid
        else list(zip(pts, pts[1:]))
    )
    if len(pts) >= 3 and not shape.solid:
        edges.append((pts[-1], pts[0]))
    # The presentation sorts boundaries around this centre's projection. A
    # centre fan preserves concave outlines without adding an active vertex.
    centre = tuple(float(v) for v in np.mean(pts, axis=0))
    triangles = (
        [tuple(pts[i] for i in face) for face in shape.face_indices]
        if shape.solid
        else (
            [(pts[0], pts[1], pts[2])]
            if len(pts) == 3
            else [(centre, a, b) for a, b in edges] if len(pts) > 3 else []
        )
    )
    faces = tuple(
        Face(a, b, c, "#355763")
        for a, b, c in triangles
        if fill
        and not shape.degenerate
        and np.linalg.norm(np.cross(np.array(b) - a, np.array(c) - a)) > epsilon
    )
    return Geometry(
        tuple(Line(a, b, "#efca82", 4.5) for a, b in edges),
        tuple(Ball(p, 0.04, "#efca82", label) for p, label in zip(pts, shape.labels)),
        (),
        faces,
    )

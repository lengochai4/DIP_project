"""Renderer-owned geometry and explicit display coordinate mapping."""
from dataclasses import dataclass
import math
import numpy as np

TIPS = (4, 8, 12, 16, 20)
FINGER_NAMES = ('Cái', 'Trỏ', 'Giữa', 'Áp út', 'Út')

@dataclass(frozen=True)
class Tip:
    hand: int
    index: int
    position: tuple[float, float, float]

@dataclass(frozen=True)
class Mesh:
    vertices: tuple[tuple[float, float, float], ...]
    faces: tuple[tuple[int, ...], ...]

def angle(a, b, c):
    u = np.array(a, dtype=float) - b
    v = np.array(c, dtype=float) - b
    denominator = np.linalg.norm(u) * np.linalg.norm(v)
    if denominator <= 1e-12:
        return 0.0
    return math.degrees(math.acos(float(np.clip(np.dot(u, v) / denominator, -1, 1))))

class FingerSelection:
    """Angle hysteresis is a presentation heuristic, not tracking confidence."""
    def __init__(self, settings):
        self.settings = settings
        self.active = set()

    def reset(self):
        self.active.clear()

    def update(self, landmarks):
        if len(landmarks) != 21:
            self.reset()
            return ()
        p = {l.index: (l.x, l.y, l.z) for l in landmarks}
        for tip in TIPS:
            joints = (1, 2, 3, 4) if tip == 4 else (tip-3, tip-2, tip-1, tip)
            value = min(angle(p[joints[0]], p[joints[1]], p[joints[2]]),
                        angle(p[joints[1]], p[joints[2]], p[joints[3]]))
            if tip == 4:
                # Thumb MCP is naturally bent on an open palm. Its IP angle
                # plus palm-normalized spread distinguishes extension better
                # than applying the other fingers' PIP rule to the thumb.
                value=angle(p[2],p[3],p[4])
            prefix = 'thumb' if tip == 4 else 'finger'
            limit = self.settings[prefix + ('_exit_angle' if tip in self.active else '_enter_angle')]
            spread_ok=True
            if tip==4:
                palm=math.dist(p[5],p[17])
                spread=math.dist(p[4],p[5])/palm if palm>1e-12 else 0
                spread_ok=spread>=self.settings['thumb_exit_spread' if tip in self.active else 'thumb_enter_spread']
            if value >= limit and spread_ok:
                self.active.add(tip)
            else:
                self.active.discard(tip)
        return tuple(t for t in TIPS if t in self.active)

def world_position(landmark, aspect, settings):
    x = 1-landmark.x if settings['mirror'] else landmark.x
    width = settings['world_width']
    return ((x-.5)*width, (.5-landmark.y)*width/aspect,
            -landmark.z*settings['relative_z_gain'])

def preview_position(landmark, rectangle, mirror=True):
    x, y, w, h = rectangle
    nx = 1-landmark.x if mirror else landmark.x
    return (x + nx*w, y + landmark.y*h)

def live_mesh(tips, thickness):
    """Convex footprint prism; live top vertices retain model-relative z.

    All fingertips remain visible as nodes, including interior hull points.
    Bottom vertices are display extrusion, never additional measurements.
    """
    points = [t.position for t in tips]
    if len(points) < 3:
        return Mesh(tuple(points), ())
    order = sorted(range(len(points)), key=lambda i: (points[i][0], points[i][1]))
    def cross(a,b,c):
        return ((points[b][0]-points[a][0])*(points[c][1]-points[a][1])
                -(points[b][1]-points[a][1])*(points[c][0]-points[a][0]))
    halves = []
    for ids in (order, order[::-1]):
        hull = []
        for i in ids:
            while len(hull) >= 2 and cross(hull[-2],hull[-1],i) <= 1e-8:
                hull.pop()
            hull.append(i)
        halves.append(hull[:-1])
    hull = halves[0]+halves[1]
    if len(hull) < 3:
        return Mesh(tuple(points), ())
    top = [points[i] for i in hull]
    vertices = tuple(top + [(x,y,z-thickness) for x,y,z in top])
    n = len(top)
    # Triangles handle non-coplanar fingertip z without an invalid GL polygon.
    faces = [(0,i,i+1) for i in range(1,n-1)]
    faces += [(n,n+i+1,n+i) for i in range(1,n-1)]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return Mesh(vertices, tuple(faces))

def solid_mesh(kind):
    if kind == 'cube':
        vertices = ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                    (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))
        return Mesh(vertices, ((0,3,2,1),(4,5,6,7),(0,1,5,4),
                               (2,3,7,6),(1,2,6,5),(3,0,4,7)))
    if kind == 'tetra':
        return Mesh(((1,1,1),(-1,-1,1),(-1,1,-1),(1,-1,-1)),
                    ((0,1,2),(0,3,1),(0,2,3),(1,3,2)))
    if kind == 'octa':
        return Mesh(((1.4,0,0),(-1.4,0,0),(0,1.4,0),(0,-1.4,0),(0,0,1.4),(0,0,-1.4)),
                    ((0,2,4),(2,1,4),(1,3,4),(3,0,4),(2,0,5),(1,2,5),(3,1,5),(0,3,5)))
    # UV sphere, actual 3D vertices and lighting normals.
    vertices = []
    for j in range(13):
        phi = math.pi*j/12
        for i in range(24):
            theta = math.tau*i/24
            vertices.append((math.sin(phi)*math.cos(theta),math.cos(phi),math.sin(phi)*math.sin(theta)))
    faces = tuple((j*24+i,j*24+(i+1)%24,(j+1)*24+(i+1)%24,(j+1)*24+i)
                  for j in range(12) for i in range(24))
    return Mesh(tuple(vertices), faces)

"""Renderer-owned geometry and explicit display coordinate mapping."""
from dataclasses import dataclass
from itertools import combinations
import math
import numpy as np

TIPS = (4, 8, 12, 16, 20)
FINGER_NAMES = ('Cái', 'Trỏ', 'Giữa', 'Áp út', 'Út')
HAND_CHAINS=((0,1,2,3,4),(0,5,6,7,8),(5,9,10,11,12),(9,13,14,15,16),(13,17,18,19,20),(0,17))
HAND_BONES=np.array([(a,b) for chain in HAND_CHAINS for a,b in zip(chain,chain[1:])])


def bone_transforms(points,edges=HAND_BONES):
    """Batch orthonormal bone frames, avoiding repeated tiny NumPy cross calls."""
    p=np.asarray(points,dtype=float)
    a=p[edges[:,0]]; delta=p[edges[:,1]]-a
    lengths=np.linalg.norm(delta,axis=1); valid=lengths>1e-8
    a=a[valid]; z=delta[valid]/lengths[valid,None]
    references=np.zeros_like(z); references[:,1]=1
    vertical=np.abs(z[:,1])>=.9; references[vertical]=(1.,0.,0.)
    x=np.cross(references,z); x/=np.linalg.norm(x,axis=1)[:,None]
    y=np.cross(z,x)
    matrices=np.tile(np.eye(4),(len(a),1,1))
    matrices[:,:3,0]=x; matrices[:,:3,1]=y; matrices[:,:3,2]=z; matrices[:,:3,3]=a
    return matrices,lengths[valid]

@dataclass(frozen=True)
class Tip:
    hand: int
    index: int
    position: tuple[float, float, float]

@dataclass(frozen=True)
class Mesh:
    vertices: tuple[tuple[float, float, float], ...]
    faces: tuple[tuple[int, ...], ...]
    mode: str = 'solid'

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

    def update(self, landmarks, aspect=1.0):
        if len(landmarks) != 21:
            self.reset()
            return ()
        # Image y is normalized by height; z uses approximately image-x scale.
        p = {l.index: (l.x, l.y/aspect, l.z) for l in landmarks}
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

def live_mesh(tips, thickness, min_depth_ratio=.06):
    """Small 3D hull, or fitted-plane display prism when depth is insufficient.

    Provider z remains relative to each hand. This is illustrative geometry,
    not a reconstruction of camera-space distances between different hands.
    """
    points = np.array([t.position for t in tips],dtype=float)
    if len(points) < 3:
        return Mesh(tuple(map(tuple,points)), (), 'points')
    centered = points-points.mean(axis=0)
    _,singular,axes = np.linalg.svd(centered,full_matrices=False)
    if singular[0]<1e-10 or singular[1]<1e-8*singular[0]:
        return Mesh(tuple(map(tuple,points)), (), 'segment')
    if len(points)>=4 and singular[2]/singular[0]>=min_depth_ratio:
        triples=np.array(list(combinations(range(len(points)),3)))
        a,b,c=(points[triples[:,i]] for i in range(3))
        normals=np.cross(b-a,c-a)
        lengths=np.linalg.norm(normals,axis=1)
        valid=lengths>1e-10
        normals=normals[valid]/lengths[valid,None]; a=a[valid]
        distances=np.einsum('tnd,td->tn',points[None,:,:]-a[:,None,:],normals)
        epsilon=singular[0]*1e-7
        faces={}
        for normal,d in zip(normals,distances):
            if d.max()<=epsilon: outward=normal
            elif d.min()>=-epsilon: outward=-normal
            else: continue
            ids=tuple(np.flatnonzero(np.abs(d)<=epsilon))
            if ids in faces: continue
            center=points[list(ids)].mean(axis=0)
            u=points[ids[0]]-center; u/=np.linalg.norm(u)
            v=np.cross(outward,u)
            ordered=sorted(ids,key=lambda i:math.atan2(np.dot(points[i]-center,v),np.dot(points[i]-center,u)))
            faces[ids]=tuple(ordered)
        return Mesh(tuple(map(tuple,points)),tuple(faces.values()),'hull3d')
    # Fallback uses the hand plane, not a permanently screen-aligned extrusion.
    normal=axes[2]
    if normal[2]<0: normal=-normal
    projected=centered@axes[:2].T
    order = sorted(range(len(points)), key=lambda i: tuple(projected[i]))
    def cross(a,b,c):
        return ((projected[b][0]-projected[a][0])*(projected[c][1]-projected[a][1])
                -(projected[b][1]-projected[a][1])*(projected[c][0]-projected[a][0]))
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
        return Mesh(tuple(map(tuple,points)), (), 'segment')
    if np.dot(np.cross(points[hull[1]]-points[hull[0]],points[hull[2]]-points[hull[0]]),normal)<0:
        hull.reverse()
    top = [points[i] for i in hull]
    vertices = tuple(map(tuple,top + [p-thickness*normal for p in top]))
    n = len(top)
    # Triangles handle non-coplanar fingertip z without an invalid GL polygon.
    faces = [(0,i,i+1) for i in range(1,n-1)]
    faces += [(n,n+i+1,n+i) for i in range(1,n-1)]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return Mesh(vertices, tuple(faces),'display_prism')

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
    vertices = [(0.,1.,0.),(0.,-1.,0.)]
    for j in range(1,12):
        phi = math.pi*j/12
        for i in range(24):
            theta = math.tau*i/24
            vertices.append((math.sin(phi)*math.cos(theta),math.cos(phi),math.sin(phi)*math.sin(theta)))
    faces=[(0,2+(i+1)%24,2+i) for i in range(24)]
    faces += [(1,2+10*24+i,2+10*24+(i+1)%24) for i in range(24)]
    faces += [(2+j*24+i,2+j*24+(i+1)%24,2+(j+1)*24+(i+1)%24,2+(j+1)*24+i)
              for j in range(10) for i in range(24)]
    return Mesh(tuple(vertices), tuple(faces))

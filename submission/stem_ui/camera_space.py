"""Pure camera-aligned display projection and spatial-panel hit testing."""
import math
from dataclasses import replace
import numpy as np


def letterbox(rect,aspect):
    x,y,w,h=rect
    cw,ch=(w,w/aspect) if w/h<aspect else (h*aspect,h)
    cw,ch=round(cw),round(ch)
    return (x+(w-cw)//2,y+(h-ch)//2,cw,ch)


class CameraCover:
    """Centered aspect-preserving crop, shared by texture and presentation XY.

    Source snapshots are immutable. This is display geometry, not camera depth
    or a change to the detector's ROI. Cropped observations may lie offscreen.
    """
    def __init__(self,source_aspect,view_aspect):
        self.width=min(1.,view_aspect/source_aspect)
        self.height=min(1.,source_aspect/view_aspect)
        self.left=(1-self.width)/2; self.top=(1-self.height)/2

    @property
    def uv(self):
        l,t=self.left,self.top; r,b=l+self.width,t+self.height
        return ((l,t),(r,t),(r,b),(l,b))

    def point(self,x,y):
        return ((x-self.left)/self.width,(y-self.top)/self.height)

    def hand(self,hand):
        def convert(points):
            return tuple(replace(p,x=(p.x-self.left)/self.width,y=(p.y-self.top)/self.height) for p in points)
        return replace(hand,landmarks=convert(hand.landmarks),raw_landmarks=convert(hand.raw_landmarks))


class CameraSpace:
    def __init__(self,aspect,width=5.,fov=44.):
        self.aspect=aspect; self.width=width; self.height=width/aspect
        self.fov=fov; self.distance=self.height/(2*math.tan(math.radians(fov)/2))

    def point(self,nx,ny,z=0.):
        factor=(self.distance-z)/self.distance
        return np.array(((nx-.5)*self.width*factor,(.5-ny)*self.height*factor,z))

    def project(self,point):
        x,y,z=point; factor=(self.distance-z)/self.distance
        if factor<=0: return None
        return (.5+x/(self.width*factor),.5-y/(self.height*factor))

    def ray(self,nx,ny):
        origin=np.array((0.,0.,self.distance)); direction=self.point(nx,ny)-origin
        return origin,direction/np.linalg.norm(direction)


class SpatialPanel:
    def __init__(self,full=False,space=None):
        self.full=full
        self.pixels=(1800,1000) if full else (720,1000)
        self.size=np.array((4.5,2.8) if full else (2.1,2.9))
        self.center=np.array((0.,.1,.25) if full else (-1.15,.15,.25))
        if space is not None:
            factor=(space.distance-self.center[2])/space.distance
            scale=min(1.,space.width*factor*.9/self.size[0],
                (space.height*factor*.92-2*abs(self.center[1]))/self.size[1])
            self.size*=max(.1,scale)
        a=math.radians(6 if full else 8)
        self.rotation=np.array(((math.cos(a),0,math.sin(a)),(0,1,0),(-math.sin(a),0,math.cos(a))))
        self.targets=[]

    def world(self,px,py):
        return self.center+self.rotation@np.array(((px/self.pixels[0]-.5)*self.size[0],(.5-py/self.pixels[1])*self.size[1],0.))

    def intersect(self,origin,direction):
        normal=self.rotation[:,2]; denominator=np.dot(normal,direction)
        if abs(denominator)<1e-9: return None
        distance=float(np.dot(normal,self.center-origin)/denominator)
        if distance<0: return None
        local=self.rotation.T@(origin+distance*direction-self.center)
        px=(local[0]/self.size[0]+.5)*self.pixels[0]
        py=(.5-local[1]/self.size[1])*self.pixels[1]
        if not (0<=px<=self.pixels[0] and 0<=py<=self.pixels[1]): return None
        action=next((a for (x,y,w,h),a in reversed(self.targets) if x<=px<x+w and y<=py<y+h),'panel:blank')
        return distance,action,(px,py)


def sphere_hit(origin,direction,center,radius):
    delta=origin-center; b=float(np.dot(delta,direction)); c=float(np.dot(delta,delta)-radius*radius)
    disc=b*b-c
    if disc<0: return None
    near=-b-math.sqrt(disc); far=-b+math.sqrt(disc)
    return near if near>=0 else far if far>=0 else None

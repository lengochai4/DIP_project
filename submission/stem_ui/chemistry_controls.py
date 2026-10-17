"""Presentation-only spatial panel pose and timestamped index-bend selection."""
from dataclasses import dataclass
import math
import numpy as np
from .manipulation import pinch_ratio


class PanelLayout:
    def __init__(self,settings):
        self.settings=settings
        self.reset()

    def reset(self):
        self.anchor=np.array((.035,.045)); self.scale=1.

    def zoom(self,factor):
        self.scale=float(np.clip(self.scale*factor,self.settings['chemistry_panel_min_scale'],
                                 self.settings['chemistry_panel_max_scale']))

    def place(self,panel,space,content,compact=False):
        # Reconstruct from the page's fitted base geometry, never accumulate scale.
        if compact:
            panel.pixels=(720,112)
            factor=(space.distance-panel.center[2])/space.distance
            width=self.settings['chemistry_panel_compact_width_px']/max(1,content[2])*space.width*factor
            panel.size=np.array((width,width*112/720))
        panel.size*=self.scale
        z=float(panel.center[2])
        def corners():
            return np.array([space.project(panel.world(x,y)) for x,y in
                ((0,0),(panel.pixels[0],0),(panel.pixels[0],panel.pixels[1]),(0,panel.pixels[1]))])
        panel.center=space.point(.5,.5,z)
        bounds=corners(); extent=np.ptp(bounds,axis=0)
        # Keep a readable title and retain all handles on small/portrait screens.
        minimum=self.settings['chemistry_panel_min_width_px']/max(1,content[2])
        if compact: minimum=min(minimum,200/max(1,content[2]))
        fit=min(.94/extent[0],.92/extent[1])
        grow=max(1.,minimum/extent[0])
        panel.size*=min(grow,fit)
        for _ in range(3):
            bounds=corners(); low=bounds.min(axis=0); high=bounds.max(axis=0)
            target=np.clip(self.anchor,.02,np.maximum(.02,.98-(high-low)))
            delta=target-low
            panel.center+=space.point(.5+delta[0],.5+delta[1],z)-space.point(.5,.5,z)
        self.anchor=corners().min(axis=0)


@dataclass
class TapState:
    generation: int
    target: object
    since: float
    last: float
    anchor: tuple
    palm: np.ndarray
    phase: str = 'aim'
    pressed_at: float | None = None
    bend_at: float | None = None


class IndexTap:
    """A webcam heuristic: stable aim, index bend, one event, extend to rearm.

    Uses a palm-relative 2D joint angle, never a claimed metric push distance.
    The pointer freezes at the last straight-finger position before bending.
    """
    def __init__(self,settings):
        self.settings=settings; self.states={}

    def reset(self): self.states.clear()

    def retain(self,keys):
        self.states={k:s for k,s in self.states.items() if k in keys}

    def update(self,key,hand,target,t,point,aspect,blocked=False):
        cfg=self.settings; old=self.states.get(key)
        points=hand.raw_landmarks or hand.landmarks
        if (blocked or not math.isfinite(t) or len(points)!=21 or
            tuple(p.index for p in points)!=tuple(range(21)) or
            not all(math.isfinite(v) for p in points for v in (p.x,p.y,p.z))):
            self.states.pop(key,None); return point,None
        if old and (old.generation!=hand.generation or t<=old.last or t-old.last>cfg['chemistry_dwell_max_gap_s']):
            self.states.pop(key,None); old=None
        p=np.array([(l.x,l.y/aspect) for l in points])
        a,b=p[5]-p[6],p[8]-p[6]; denominator=np.linalg.norm(a)*np.linalg.norm(b)
        if denominator<1e-10:
            self.states.pop(key,None); return point,None
        angle=math.degrees(math.acos(float(np.clip(np.dot(a,b)/denominator,-1,1))))
        palm=p[[0,5,9,13,17]].mean(axis=0)
        size=max(np.linalg.norm(p[5]-p[17]),np.linalg.norm(p[0]-p[9]),1e-8)
        if pinch_ratio(hand,aspect)<cfg['chemistry_grip_release_ratio']:
            self.states.pop(key,None); return point,None
        straight=angle>=cfg['chemistry_tap_straight_deg']
        if old and old.phase in ('latched','cancelled'):
            old.last=t
            if straight: self.states.pop(key,None)
            return (old.anchor if old.phase=='latched' else point),None
        if old and old.phase=='press':
            old.last=t
            if (np.linalg.norm(palm-old.palm)/size>cfg['chemistry_tap_palm_motion_ratio'] or
                t-old.bend_at>cfg['chemistry_tap_timeout_s']):
                old.phase='cancelled'; return point,None
            if straight:
                self.states.pop(key,None); return point,None
            if angle<=cfg['chemistry_tap_press_deg']:
                if old.pressed_at is None: old.pressed_at=t
                if t-old.pressed_at>=cfg['chemistry_tap_confirm_s']-1e-9:
                    old.phase='latched'; return old.anchor,old.target
            else: old.pressed_at=None
            return old.anchor,None
        if (old and not straight and t-old.since>=cfg['chemistry_tap_arm_s'] and
            np.linalg.norm(palm-old.palm)/size<=cfg['chemistry_tap_palm_motion_ratio']):
            old.phase='press'; old.bend_at=t; old.last=t
            if angle<=cfg['chemistry_tap_press_deg']: old.pressed_at=t
            return old.anchor,None
        if target is None:
            self.states.pop(key,None); return point,None
        if straight:
            if old is None or old.target!=target or math.dist(point,old.anchor)>cfg['chemistry_tap_aim_motion']:
                old=TapState(hand.generation,target,t,t,point,palm)
                self.states[key]=old
            old.last=t; old.anchor=point; old.palm=palm
        else: self.states.pop(key,None)
        return point,None

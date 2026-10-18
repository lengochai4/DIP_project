"""Presentation-only panel docking and observed menu confirmation."""
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
        self.edge='left'; self.edge_position=.25; self.extent=np.array((.3,.6))

    def dock(self,edge,position):
        self.edge=edge; self.edge_position=float(np.clip(position,.1,.9))

    def zoom(self,factor):
        self.scale=float(np.clip(self.scale*factor,self.settings['chemistry_panel_min_scale'],
                                 self.settings['chemistry_panel_max_scale']))

    def place(self,panel,space,content,compact=False):
        # Reconstruct from the page's fitted base geometry, never accumulate scale.
        if compact:
            panel.pixels=(128,128); panel.rotation=np.eye(3)
            factor=(space.distance-panel.center[2])/space.distance
            side=self.settings['chemistry_panel_arrow_px']
            nw,nh=min(.2,side/max(1,content[2])),min(.2,side/max(1,content[3]))
            nx=self.edge_position; ny=self.edge_position
            if self.edge in ('left','right'): nx=nw/2 if self.edge=='left' else 1-nw/2
            else: ny=nh/2 if self.edge=='top' else 1-nh/2
            nx=float(np.clip(nx,nw/2,1-nw/2)); ny=float(np.clip(ny,nh/2,1-nh/2))
            panel.size=np.array((nw*space.width*factor,nh*space.height*factor))
            panel.center=space.point(nx,ny,panel.center[2])
            return
        panel.size*=self.scale
        z=float(panel.center[2])
        def corners():
            return np.array([space.project(panel.world(x,y)) for x,y in
                ((0,0),(panel.pixels[0],0),(panel.pixels[0],panel.pixels[1]),(0,panel.pixels[1]))])
        panel.center=space.point(.5,.5,z)
        bounds=corners(); extent=np.ptp(bounds,axis=0)
        # Keep a readable title and retain all handles on small/portrait screens.
        minimum=self.settings['chemistry_panel_min_width_px']/max(1,content[2])
        fit=min(.94/extent[0],.92/extent[1])
        grow=max(1.,minimum/extent[0])
        panel.size*=min(grow,fit)
        for _ in range(3):
            bounds=corners(); low=bounds.min(axis=0); high=bounds.max(axis=0)
            target=np.clip(self.anchor,.02,np.maximum(.02,.98-(high-low)))
            delta=target-low
            panel.center+=space.point(.5+delta[0],.5+delta[1],z)-space.point(.5,.5,z)
        self.anchor=corners().min(axis=0)
        self.extent=np.ptp(corners(),axis=0)


@dataclass
class PushState:
    generation: int
    target: object
    since: float
    last: float
    anchor: tuple
    palm: np.ndarray
    size: float
    normal: np.ndarray
    lateral: np.ndarray
    depth: float
    baseline: float
    samples: list
    phase: str = 'aim'
    pressed_at: float | None = None
    peak: float = 0.
    observations: int = 0
    locked: bool = False


@dataclass
class PointPinchState:
    generation: int
    target: object
    since: float
    last: float
    anchor: tuple
    origin: tuple
    phase: str = 'aim'
    locked: bool = False
    captured_at: float | None = None
    pressed_at: float | None = None
    release_since: float | None = None
    observations: int = 0
    progress: float = 0.
    palm: np.ndarray | None = None
    size: float = 0.
    ratio: float | None = None
    reason: str | None = None


class PointPinch:
    """Open-hand aim -> captured close -> one explicit menu selection.

    Uses observed normalized XY pinch, never model z. Continuous hover remains
    independent. A held selection pinch cannot become an object/panel grab.
    """
    def __init__(self,settings):
        self.settings=settings; self.states={}

    def reset(self): self.states.clear()

    def _cancel(self,state,t,reason='interrupted'):
        if state.phase!='latched': state.phase='cancelled'
        state.locked=False; state.release_since=None
        if math.isfinite(t): state.last=t
        state.progress=0.
        state.reason=reason

    def cancel(self,key,t):
        if key in self.states: self._cancel(self.states[key],t)

    def retain(self,keys):
        # Remember consumed intent during loss, not hand geometry. Otherwise a
        # returning closed pinch could grab the object behind a menu button.
        self.states={k:s for k,s in self.states.items() if k in keys or s.phase in ('press','latched','cancelled')}
        for k,s in self.states.items():
            if k not in keys: self._cancel(s,s.last)

    def latch(self,key,generation,target,t,point):
        self.states[key]=PointPinchState(generation,target,t,t,point,point,phase='latched',pressed_at=t)

    def update(self,key,hand,target,t,point,aspect,blocked=False):
        cfg=self.settings; old=self.states.get(key); points=hand.raw_landmarks or hand.landmarks
        if (blocked or not math.isfinite(t) or len(points)!=21 or
            tuple(p.index for p in points)!=tuple(range(21)) or
            not all(math.isfinite(v) for p in points for v in (p.x,p.y,p.z))):
            if old and old.phase in ('press','latched','cancelled'): self._cancel(old,t)
            else: self.states.pop(key,None)
            return point,None
        if old and old.generation!=hand.generation:
            self.states.pop(key,None); old=None
        elif old and (t<=old.last or t-old.last>cfg['chemistry_dwell_max_gap_s']):
            if old.phase in ('press','latched','cancelled'): self._cancel(old,t)
            else: self.states.pop(key,None); old=None
        ratio=pinch_ratio(hand,aspect)
        p=np.array([(v.x,v.y/aspect) for v in points])
        palm=p[[0,5,9,13,17]].mean(axis=0)
        size=max(np.linalg.norm(p[5]-p[17]),np.linalg.norm(p[0]-p[9]),1e-8)
        if old: old.ratio=ratio
        opened=ratio>=cfg['chemistry_grip_release_ratio']
        if old and old.phase in ('latched','cancelled'):
            old.last=t
            old.locked=old.phase=='latched' and t-old.pressed_at<cfg['chemistry_click_feedback_s']
            if opened:
                if old.release_since is None: old.release_since=t
                if t-old.release_since>=cfg['chemistry_grip_release_s']-1e-9:
                    self.states.pop(key,None); old=None
            else: old.release_since=None
            if old is not None: return (old.anchor if old.locked else point),None
        if old is None:
            if opened and target is not None:
                self.states[key]=PointPinchState(hand.generation,target,t,t,point,point)
            return point,None
        old.last=t
        if old.phase=='press':
            # Closing fingers move the index even with a stationary hand. Once
            # captured, bound observed palm translation instead of cancelling
            # the intended button because the contact finger folded naturally.
            reason=('opened' if opened else 'timeout' if t-old.captured_at>cfg['chemistry_click_timeout_s']
                    else 'palm_motion' if np.linalg.norm(palm-old.palm)/old.size>cfg['chemistry_click_palm_motion_ratio']
                    else None)
            if reason:
                self._cancel(old,t,reason); return point,None
            if ratio<=cfg['chemistry_grip_press_ratio']:
                if old.pressed_at is None: old.pressed_at=t
                old.observations+=1
            elif ratio>cfg['chemistry_click_hold_ratio']:
                old.pressed_at=None; old.observations=0; old.progress=0.
            # A narrow hysteresis band tolerates contact jitter after tight
            # observations. One tight spike or a partial pinch cannot select.
            if old.pressed_at is not None:
                old.progress=min(1.,(t-old.pressed_at)/cfg['chemistry_grip_press_s'])
                if old.observations>=cfg['chemistry_click_observations'] and old.progress>=1.-1e-9:
                    old.phase='latched'; old.pressed_at=t; old.progress=1.
                    return old.anchor,old.target
            return old.anchor,None
        if old.phase=='armed' and ratio<=cfg['chemistry_click_capture_ratio']:
            if math.dist(point,old.anchor)<=cfg['chemistry_click_capture_radius']:
                old.phase='press'; old.locked=True; old.captured_at=t; old.origin=point
                old.palm=palm; old.size=size
                if ratio<=cfg['chemistry_grip_press_ratio']:
                    old.pressed_at=t; old.observations=1
                return old.anchor,None
            self.states.pop(key,None); return point,None
        if old.phase=='armed' and not opened:
            # Preserve the intended button through the intermediate ratios of
            # a gradual close; requiring an open hand on every step loses aim.
            if old.captured_at is None: old.captured_at=t
            if (math.dist(point,old.anchor)>cfg['chemistry_click_capture_radius'] or
                t-old.captured_at>cfg['chemistry_click_timeout_s']):
                self.states.pop(key,None)
            return point,None
        if not opened or target is None:
            self.states.pop(key,None); return point,None
        if target!=old.target or math.dist(point,old.origin)>cfg['chemistry_dwell_motion_radius']:
            self.states[key]=PointPinchState(hand.generation,target,t,t,point,point)
        else:
            old.captured_at=None
            old.anchor=point
            if t-old.since>=cfg['chemistry_click_aim_s']-1e-9: old.phase='armed'
            if old.phase=='armed': old.origin=point
        return point,None


class IndexPush:
    """Stable aim -> coherent relative forward motion -> click -> retract.

    Model-relative z is a non-metric cue, normalized by observed palm size.
    No shared Core filter/landmark is modified. Ambiguous motion cancels;
    1-second dwell remains available. A click never freezes the pointer forever.
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
        p=np.array([(l.x,l.y/aspect,l.z) for l in points])
        a,b=p[5]-p[6],p[8]-p[6]; denominator=np.linalg.norm(a)*np.linalg.norm(b)
        if denominator<1e-10:
            self.states.pop(key,None); return point,None
        angle=math.degrees(math.acos(float(np.clip(np.dot(a,b)/denominator,-1,1))))
        palm=p[[0,5,9,13,17]].mean(axis=0)
        size=max(np.linalg.norm((p[5]-p[17])[:2]),np.linalg.norm((p[0]-p[9])[:2]),1e-8)
        normal=np.cross(p[17]-p[5],p[9]-p[0]); normal_size=np.linalg.norm(normal)
        if normal_size<1e-8:
            self.states.pop(key,None); return point,None
        normal/=normal_size
        if normal[2]>0: normal=-normal
        if -normal[2]<cfg['chemistry_push_min_view_cos']:
            self.states.pop(key,None); return point,None
        # Express the fingertip relative to the observed palm plane. A rigid
        # wrist turn must not masquerade as an independent index push.
        depth=float(np.dot(p[8]-palm,normal)/size)
        lateral=(p[8,:2]-p[5,:2])/size
        if pinch_ratio(hand,aspect)<cfg['chemistry_push_pinch_cancel_ratio']:
            self.states.pop(key,None); return point,None
        pointing=angle>=cfg['chemistry_push_point_deg']
        if old is None:
            if target is not None and pointing:
                self.states[key]=PushState(hand.generation,target,t,t,point,palm,size,normal,lateral,
                                          depth,depth,[depth])
            return point,None
        dt=t-old.last; old.last=t
        filtered=old.depth+(depth-old.depth)*(1-math.exp(-math.tau*cfg['chemistry_push_response_hz']*dt))
        velocity=(filtered-old.depth)/dt; old.depth=filtered
        travel=filtered-old.baseline
        if old.phase in ('latched','cancelled'):
            old.locked=old.phase=='latched' and t-old.pressed_at<cfg['chemistry_push_feedback_s']
            if not old.locked and (travel<=cfg['chemistry_push_release_ratio'] or
                                  math.dist(point,old.anchor)>cfg['chemistry_push_leave_distance']):
                self.states.pop(key,None)
            return (old.anchor if old.locked else point),None
        palm_motion=np.linalg.norm((palm-old.palm)[:2])/old.size
        rotation=math.degrees(math.acos(float(np.clip(np.dot(normal,old.normal),-1,1))))
        lateral_motion=float(np.linalg.norm(lateral-old.lateral))
        unstable=(palm_motion>cfg['chemistry_push_palm_motion_ratio'] or
                  abs(size/old.size-1)>cfg['chemistry_push_scale_change'] or
                  rotation>cfg['chemistry_push_rotation_deg'] or
                  lateral_motion>cfg['chemistry_push_lateral_ratio'])
        if unstable:
            old.phase='cancelled'; old.locked=False; return point,None
        if old and old.phase=='press':
            old.peak=max(old.peak,travel); old.observations+=1
            if (t-old.pressed_at>cfg['chemistry_push_timeout_s'] or
                old.peak-travel>cfg['chemistry_push_backtrack_ratio']):
                old.phase='cancelled'; old.locked=False; return point,None
            if (travel>=cfg['chemistry_push_travel_ratio'] and
                travel>=lateral_motion*cfg['chemistry_push_direction_ratio'] and
                velocity>=0 and old.observations>=cfg['chemistry_push_observations'] and
                t-old.pressed_at>=cfg['chemistry_push_confirm_s']-1e-9):
                old.phase='latched'; old.pressed_at=t
                return old.anchor,old.target
            return old.anchor,None
        noise=max(old.samples)-min(old.samples)
        start=max(cfg['chemistry_push_start_ratio'],noise*cfg['chemistry_push_noise_gain'])
        if old.phase=='armed' and travel>=start and velocity>=cfg['chemistry_push_min_speed']:
            if math.dist(point,old.anchor)>cfg['chemistry_push_aim_motion']:
                old.phase='cancelled'; old.locked=False; return point,None
            old.phase='press'; old.pressed_at=t; old.peak=travel
            old.observations=1; old.locked=True
            return old.anchor,None
        if (target!=old.target or not pointing or
            math.dist(point,old.anchor)>cfg['chemistry_push_aim_motion']):
            self.states.pop(key,None); return point,None
        if old.phase=='aim':
            old.samples.append(depth)
            if t-old.since>=cfg['chemistry_push_arm_s']:
                if noise>cfg['chemistry_push_max_noise_ratio']:
                    self.states.pop(key,None); return point,None
                old.baseline=float(np.median(old.samples)); old.phase='armed'
        # Aim remains live; only a coherent push captures the cursor.
        return point,None

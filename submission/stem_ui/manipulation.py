"""UI-only XR-style grip continuity and render-rate pose following.

Core landmarks/gestures and research semantics remain unchanged. No missing
observation is extrapolated, and inter-hand model z is never metric depth.
"""
from dataclasses import dataclass, field
import math
import numpy as np
from .geometry import world_position


@dataclass
class Pose:
    position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    rotation: np.ndarray = field(default_factory=lambda: np.eye(3))
    scale: float = 1.0
    stretch: np.ndarray = field(default_factory=lambda: np.ones(3))

    def copy(self):
        return Pose(self.position.copy(), self.rotation.copy(), self.scale, self.stretch.copy())


def palm_size(hand, aspect):
    p = {l.index: np.array((l.x, l.y / aspect)) for l in hand.landmarks}
    return max(float(np.linalg.norm(p[5]-p[17])),
               float(np.linalg.norm(p[0]-p[9])), 1e-8)


def pinch_ratio(hand, aspect):
    p = {l.index: np.array((l.x, l.y / aspect)) for l in hand.landmarks}
    return float(np.linalg.norm(p[4]-p[8])) / palm_size(hand, aspect)


def hand_anchor(hand, aspect, settings):
    p = {l.index: np.array(world_position(l, aspect, settings)) for l in hand.landmarks}
    anchor = (p[4]+p[8])/2
    anchor[2] = 0
    right, up = p[5]-p[17], p[9]-p[0]
    denominator = np.linalg.norm(right)*np.linalg.norm(up)
    if denominator < 1e-10 or np.linalg.norm(np.cross(right,up))/denominator < .20:
        return anchor, None
    right /= np.linalg.norm(right)
    up -= right*np.dot(up,right)
    up /= np.linalg.norm(up)
    return anchor, np.column_stack((right, up, np.cross(right,up)))


def quaternion(matrix):
    """Unit quaternion (w,x,y,z), including the 180-degree case."""
    m = np.asarray(matrix)
    trace = np.trace(m)
    if trace > 0:
        s = math.sqrt(trace+1)*2
        q = np.array((s/4,(m[2,1]-m[1,2])/s,(m[0,2]-m[2,0])/s,(m[1,0]-m[0,1])/s))
    else:
        i = int(np.argmax(np.diag(m))); j = (i+1)%3; k = (i+2)%3
        s = math.sqrt(max(0,1+m[i,i]-m[j,j]-m[k,k]))*2
        q = np.zeros(4); q[0]=(m[k,j]-m[j,k])/s; q[i+1]=s/4
        q[j+1]=(m[j,i]+m[i,j])/s; q[k+1]=(m[k,i]+m[i,k])/s
    return q/np.linalg.norm(q)


def rotation_matrix(q):
    w,x,y,z = q/np.linalg.norm(q)
    return np.array(((1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)),
                     (2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)),
                     (2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y))))


def slerp_rotation(a, b, amount):
    qa,qb = quaternion(a),quaternion(b)
    dot = float(np.dot(qa,qb))
    if dot < 0: qb=-qb; dot=-dot
    dot = min(1.,dot)
    if dot > .9995:
        q = qa+amount*(qb-qa)
    else:
        theta = math.acos(dot)
        q = (math.sin((1-amount)*theta)*qa+math.sin(amount*theta)*qb)/math.sin(theta)
    return rotation_matrix(q)


@dataclass
class Grip:
    generation: int
    held: bool = False
    pending_since: float | None = None
    last_seen: float = 0.0
    ratio: float = math.inf


class GrabController:
    def __init__(self, settings):
        self.settings = settings
        self.reset()

    def reset(self):
        self.pose = Pose(); self.target = self.pose.copy()
        self.grips = {}; self.slots = (); self.base = None
        self.previous_time = None; self.suspended = False
        self.scale_mode = 'uniform'; self.feedback = 'Chụm cái–trỏ để giữ vật thể'

    def release(self):
        self.grips.clear(); self.slots=(); self.base=None
        self.previous_time=None; self.suspended=False
        self.target=self.pose.copy()

    def set_scale_mode(self, mode):
        if mode not in ('uniform','stretch','distance'): raise ValueError('invalid scale mode')
        if mode != self.scale_mode:
            self.scale_mode=mode; self.base=None; self.target=self.pose.copy()

    def _recognize(self, hand, t, aspect):
        generation=getattr(hand,'generation',0)
        grip=self.grips.get(hand.slot)
        if grip is None or grip.generation!=generation:
            grip=Grip(generation); self.grips[hand.slot]=grip
            if hand.slot in self.slots:
                self.base=None; self.target=self.pose.copy()
        grip.last_seen=t
        grip.ratio=pinch_ratio(hand,aspect)
        desired = grip.ratio <= self.settings['grip_press_ratio'] if not grip.held else grip.ratio < self.settings['grip_release_ratio']
        if desired == grip.held:
            grip.pending_since=None
        else:
            if grip.pending_since is None: grip.pending_since=t
            duration=self.settings['grip_release_s' if grip.held else 'grip_press_s']
            if t-grip.pending_since >= duration-1e-9:
                grip.held=desired; grip.pending_since=None
        return grip

    def update(self, hands, timestamp_s, aspect, view_rotation=None):
        """Accept real observations and set target only. Call advance per draw."""
        if self.previous_time is not None and timestamp_s<=self.previous_time:
            self.release(); return self.pose
        self.previous_time=timestamp_s
        camera=np.eye(3) if view_rotation is None else np.asarray(view_rotation)
        available={h.slot:h for h in hands if len(h.landmarks)==21 and
                   all(math.isfinite(v) for l in h.landmarks for v in (l.x,l.y,l.z))}
        for h in available.values(): self._recognize(h,timestamp_s,aspect)
        for slot,grip in list(self.grips.items()):
            if slot not in available and timestamp_s-grip.last_seen > self.settings['grip_loss_grace_s']:
                del self.grips[slot]
        held=tuple(sorted(s for s,g in self.grips.items() if g.held))
        if any(self.grips[s].pending_since is not None and
               self.grips[s].ratio >= self.settings['grip_release_ratio'] for s in held if s in available):
            # Opening fingers changes the pinch midpoint. Freeze during release
            # confirmation so that fingertip separation cannot kick the object.
            self.suspended=True; self.base=None; self.target=self.pose.copy()
            self.feedback='Đang buông • giữ nguyên vật thể'; return self.pose
        if any(s not in available for s in held):
            self.suspended=True; self.base=None; self.target=self.pose.copy()
            self.feedback='Tạm mất tay • giữ nguyên vật thể'; return self.pose
        resumed=self.suspended; self.suspended=False
        if not held:
            self.slots=(); self.base=None; self.target=self.pose.copy()
            self.feedback='Chụm cái–trỏ để giữ vật thể'; return self.pose
        selected=[available[s] for s in held]
        anchors=[hand_anchor(h,aspect,self.settings) for h in selected]
        positions=[camera.T@p for p,_ in anchors]
        center=np.mean(positions,axis=0)
        vector=positions[1]-positions[0] if len(positions)==2 else None
        span=float(np.linalg.norm(vector)) if vector is not None else None
        if span is not None and span < self.settings['grab_min_span']:
            self.suspended=True; self.base=None; self.target=self.pose.copy()
            self.feedback='Hai điểm giữ quá gần • tách hai tay rõ hơn'; return self.pose
        generations=tuple(self.grips[s].generation for s in held)
        if held!=self.slots or self.base is None or resumed or self.base['generations']!=generations or not np.allclose(self.base['camera'],camera):
            self.slots=held
            orientation=camera.T@anchors[0][1] if anchors[0][1] is not None else None
            axis=int(np.argmax(np.abs(self.pose.rotation.T@vector))) if vector is not None else 0
            self.base={'center':center,'orientation':orientation,'last_orientation':orientation,
                'vector':vector,'pose':self.pose.copy(),'size':palm_size(selected[0],aspect),
                'axis':axis,'camera':camera.copy(),'generations':generations}
            self.target=self.pose.copy()
        else:
            base=self.base; base_pose=base['pose']
            self.target.position=base_pose.position+center-base['center']
            self.target.scale=base_pose.scale; self.target.stretch=base_pose.stretch.copy()
            if vector is not None:
                old=camera@base['vector']; new=camera@vector
                delta=math.atan2(new[1],new[0])-math.atan2(old[1],old[0])
                c,s=math.cos(delta),math.sin(delta)
                twist=np.array(((c,-s,0),(s,c,0),(0,0,1)))
                self.target.rotation=camera.T@twist@camera@base_pose.rotation
                ratio=span/np.linalg.norm(base['vector'])
                if self.scale_mode=='stretch': self.target.stretch[base['axis']]=base_pose.stretch[base['axis']]*ratio
                else: self.target.scale=base_pose.scale*ratio
            else:
                orientation=camera.T@anchors[0][1] if anchors[0][1] is not None else None
                last=base['last_orientation']
                if orientation is not None and base['orientation'] is not None:
                    jump=math.degrees(math.acos(float(np.clip((np.trace(orientation@last.T)-1)/2,-1,1)))) if last is not None else 0
                    if jump<=self.settings['orientation_max_jump_deg']:
                        self.target.rotation=orientation@base['orientation'].T@base_pose.rotation
                        base['last_orientation']=orientation
                    else:
                        # A sudden model orientation flip must not leave rotation
                        # permanently stuck. Reattach its orientation only, without
                        # rotating the displayed object on the discontinuity frame.
                        base['orientation']=orientation
                        base['last_orientation']=orientation
                        base_pose.rotation=self.pose.rotation.copy()
                        self.target.rotation=self.pose.rotation.copy()
                elif orientation is not None:
                    base['orientation']=orientation
                    base['last_orientation']=orientation
                    base_pose.rotation=self.pose.rotation.copy()
                if self.settings['one_hand_scale_enabled'] and self.scale_mode=='distance':
                    self.target.scale=base_pose.scale*palm_size(selected[0],aspect)/base['size']
        self.target.scale=float(np.clip(self.target.scale,self.settings['grab_min_scale'],self.settings['grab_max_scale']))
        self.target.stretch=np.clip(self.target.stretch,self.settings['stretch_min'],self.settings['stretch_max'])
        action='kéo dãn' if self.scale_mode=='stretch' else 'thu/phóng'
        self.feedback=(f'Đang giữ 2 tay • tách/khép để {action}, vặn để xoay' if len(held)==2 else
            'Đang giữ 1 tay • gần/xa camera đổi cỡ; giữ lòng tay hướng camera' if self.scale_mode=='distance' else
            f'Đang giữ 1 tay • dời/xoay; thêm tay thứ hai để {action}')
        return self.pose

    def advance(self, dt):
        """Frame-rate-independent display following; no extrapolation or inertia."""
        if dt<=0 or not math.isfinite(dt) or not self.slots or self.suspended: return self.pose
        a=1-math.exp(-math.tau*self.settings['pose_response_hz']*dt)
        ar=1-math.exp(-math.tau*self.settings['rotation_response_hz']*dt)
        az=1-math.exp(-math.tau*self.settings['scale_response_hz']*dt)
        self.pose.position+=a*(self.target.position-self.pose.position)
        self.pose.rotation=slerp_rotation(self.pose.rotation,self.target.rotation,ar)
        self.pose.scale=math.exp(math.log(self.pose.scale)+az*math.log(self.target.scale/self.pose.scale))
        self.pose.stretch=np.exp(np.log(self.pose.stretch)+az*np.log(self.target.stretch/self.pose.stretch))
        return self.pose

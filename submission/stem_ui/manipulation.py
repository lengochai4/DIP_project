"""Presentation-only grab interaction inspired by XR grab transformers.

One pinch attaches without snapping: x/y moves the object, local palm
orientation rotates it. Two pinches use midpoint, planar span and twist.
No inter-hand model-relative z is interpreted as physical camera depth.
"""
from dataclasses import dataclass, field
import math
import numpy as np
from .geometry import world_position

@dataclass
class Pose:
    position: np.ndarray = field(default_factory=lambda:np.zeros(3))
    rotation: np.ndarray = field(default_factory=lambda:np.eye(3))
    scale: float = 1.0

def hand_anchor(hand,aspect,settings):
    p={l.index:np.array(world_position(l,aspect,settings)) for l in hand.landmarks}
    anchor=(p[4]+p[8])/2
    anchor[2]=0  # inter-hand depth is unavailable; translation is an x/y plane.
    right=p[5]-p[17]
    up=p[9]-p[0]
    if np.linalg.norm(right)<1e-8:
        return anchor,None
    right/=np.linalg.norm(right)
    up-=right*np.dot(up,right)
    if np.linalg.norm(up)<1e-8:
        return anchor,None
    up/=np.linalg.norm(up)
    return anchor,np.column_stack((right,up,np.cross(right,up)))

class GrabController:
    def __init__(self,settings):
        self.settings=settings
        self.reset()

    def reset(self):
        self.pose=Pose()
        self.slots=()
        self.base=None
        self.previous_time=None

    def release(self):
        self.slots=(); self.base=None; self.previous_time=None

    def update(self,hands,timestamp_s,aspect):
        usable=sorted((h for h in hands if h.interaction.interaction_valid and h.interaction.pinch_active),key=lambda h:h.slot)
        slots=tuple(h.slot for h in usable)
        if not usable:
            self.release(); return self.pose
        anchors=[hand_anchor(h,aspect,self.settings) for h in usable]
        positions=[a[0] for a in anchors]
        center=np.mean(positions,axis=0)
        vector=positions[-1]-positions[0] if len(positions)==2 else None
        span=float(np.linalg.norm(vector)) if vector is not None else None
        if span is not None and span < self.settings['grab_min_span']:
            self.release(); return self.pose
        if slots!=self.slots or self.previous_time is None or timestamp_s<=self.previous_time:
            self.slots=slots
            self.base=(center.copy(), anchors[0][1], vector, Pose(self.pose.position.copy(),self.pose.rotation.copy(),self.pose.scale))
            self.previous_time=timestamp_s
            return self.pose
        dt=timestamp_s-self.previous_time; self.previous_time=timestamp_s
        base_center,base_orientation,base_vector,base_pose=self.base
        target_position=base_pose.position+center-base_center
        target_position=np.clip(target_position,(-2.5,-1.6,0),(2.5,1.8,0))
        target_rotation=base_pose.rotation
        target_scale=base_pose.scale
        if vector is not None:
            delta=math.atan2(vector[1],vector[0])-math.atan2(base_vector[1],base_vector[0])
            c,s=math.cos(delta),math.sin(delta)
            target_rotation=np.array(((c,-s,0),(s,c,0),(0,0,1)))@base_pose.rotation
            target_scale=base_pose.scale*span/np.linalg.norm(base_vector)
        elif base_orientation is not None and anchors[0][1] is not None:
            target_rotation=anchors[0][1]@base_orientation.T@base_pose.rotation
        target_scale=float(np.clip(target_scale,self.settings['grab_min_scale'],self.settings['grab_max_scale']))
        # Smoothing belongs only to display pose. Canonical filtered landmarks,
        # relative z, Core equations and recorded research results stay intact.
        alpha=1-math.exp(-math.tau*self.settings['pose_response_hz']*dt)
        self.pose.position+=alpha*(target_position-self.pose.position)
        matrix=(1-alpha)*self.pose.rotation+alpha*target_rotation
        u,_,vt=np.linalg.svd(matrix)
        correction=np.eye(3); correction[2,2]=np.linalg.det(u@vt)
        self.pose.rotation=u@correction@vt
        self.pose.scale+=alpha*(target_scale-self.pose.scale)
        return self.pose

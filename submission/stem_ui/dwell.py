"""Continuous observed hover, with cancellation and deliberate rearm."""
from dataclasses import dataclass
import math


@dataclass
class Dwell:
    generation: int
    target: object
    since: float
    last: float
    progress: float = 0.
    latched: bool = False
    point: tuple = (0.,0.)


class DwellSelector:
    def __init__(self,duration_s,max_gap_s,rearm_distance,motion_radius=None):
        self.duration=duration_s; self.max_gap=max_gap_s; self.rearm=rearm_distance
        self.states={}
        self.motion_radius=motion_radius

    def reset(self): self.states.clear()

    def latch(self,key,generation,target,t,point):
        """Explicit selection and dwell share an activation latch across pages."""
        self.states[key]=Dwell(generation,target,t,t,latched=True,point=point)

    def update(self,key,generation,target,t,point,outside=False):
        old=self.states.get(key)
        if not math.isfinite(t): self.states.pop(key,None); return None
        if old and (old.generation!=generation or t<=old.last or t-old.last>self.max_gap):
            self.states.pop(key,None); old=None
        if old and old.latched:
            if outside or math.dist(point,old.point)>=self.rearm:
                self.states.pop(key,None); old=None
            else:
                old.last=t; old.progress=0.; return None
        if target is None:
            self.states.pop(key,None); return None
        if old is None or old.target!=target or (self.motion_radius is not None and math.dist(point,old.point)>self.motion_radius):
            self.states[key]=Dwell(generation,target,t,t,point=point); return None
        old.last=t; old.progress=min(1.,max(0.,(t-old.since)/self.duration))
        if old.progress>=1.-1e-9:
            old.latched=True; old.point=point; return target
        return None

    def retain(self,keys):
        self.states={key:state for key,state in self.states.items() if key in keys}

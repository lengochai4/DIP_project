"""Typed, exclusive presentation gestures for the mechanics lab."""
from dataclasses import dataclass
import math
import numpy as np
from .chemistry_controls import PointPinch
from .dwell import DwellSelector
from .manipulation import PinchGate


@dataclass
class PhysicsClaim:
    generation: int
    target: str
    origin: tuple
    value: object
    paused: bool = False
    position: object = None
    target_point: object = None
    cursor_origin: object = None
    finished: bool = False


class PhysicsInput:
    def __init__(self,settings,host):
        self.settings=settings; self.host=host
        self.tap=PointPinch(settings)
        self.dwell=DwellSelector(settings['chemistry_dwell_s'],settings['chemistry_dwell_max_gap_s'],
            settings['chemistry_dwell_rearm_distance'],settings['chemistry_dwell_motion_radius'])
        self.gates={}; self.claims={}; self.aims={}; self.pointers={}; self.hover={}; self.previous=None
        self.grab_settings={**settings,'grip_press_ratio':settings['chemistry_grip_press_ratio'],
            'grip_release_ratio':settings['chemistry_grip_release_ratio'],
            'grip_press_s':settings['chemistry_grip_press_s'],'grip_release_s':settings['chemistry_grip_release_s'],
            'grip_loss_grace_s':settings['chemistry_grip_loss_grace_s']}

    def release(self):
        self.claims.clear(); self.gates.clear(); self.aims.clear(); self.pointers.clear(); self.hover.clear()
        self.tap.reset(); self.dwell.reset(); self.previous=None

    def update(self,hands,t,aspect,gesture_hands=None,source_aspect=None):
        if not math.isfinite(t): self.release(); return
        if self.previous is not None and (t<=self.previous or t-self.previous>self.settings['chemistry_dwell_max_gap_s']): self.release()
        self.previous=t
        available={h.slot:h for h in hands if len(h.landmarks)==21 and tuple(p.index for p in h.landmarks)==tuple(range(21)) and all(math.isfinite(v) for p in h.landmarks for v in (p.x,p.y,p.z))}
        observed=available if gesture_hands is None else {h.slot:h for h in gesture_hands}
        self.tap.retain(available); self.dwell.retain(available)
        self.pointers={}; self.hover={}
        self.aims={k:a for k,a in self.aims.items() if k in available and a[0]==available[k].generation and a[1]==self.host.page_key and t-a[3]<=self.settings['chemistry_panel_aim_grace_s']}
        for key in sorted(set(self.gates)|set(available)):
            hand=available.get(key); claim=self.claims.get(key)
            gate=self.gates.setdefault(key,PinchGate(self.grab_settings))
            if claim and hand and claim.generation!=hand.generation:
                self.claims.pop(key); gate.reset(); claim=None
            gate.update((observed.get(key,hand),) if hand else (),t,source_aspect or aspect)
            if hand is None:
                if claim:
                    if gate.slots: claim.paused=True
                    else: self.claims.pop(key)
                continue
            tip=hand.landmarks[8]; point=(1-tip.x if self.settings['mirror'] else tip.x,tip.y)
            action=self.host.hit(point)
            state=self.tap.states.get(key)
            if state and state.target[0]!=self.host.page_key and state.phase not in ('latched','cancelled'):
                if state.phase=='press': self.tap.cancel(key,t)
                else: self.tap.states.pop(key)
            candidate=(self.host.page_key,action) if action and not action.startswith('drag:') else None
            point,chosen=self.tap.update(key,observed.get(key,hand),candidate,t,point,source_aspect or aspect,blocked=bool(self.claims))
            self.pointers[key]=point
            state=self.tap.states.get(key)
            if state and state.locked and state.target[0]==self.host.page_key: action=state.target[1]
            self.hover[key]=action
            consumed=state and state.phase in ('press','latched','cancelled')
            grip=self._grip_point(hand)
            if claim:
                if not gate.slots: self.claims.pop(key)
                elif gate.suspended or gate.grips[key].ratio>=self.settings['physics_drag_freeze_ratio'] or claim.finished:
                    claim.paused=True
                else:
                    if claim.paused:
                        claim.origin=grip; claim.value=self.host.capture(claim.target); claim.paused=False
                        claim.position=np.array(grip); claim.cursor_origin=np.array(point)
                    claim.target_point=np.array(grip)
                if key in self.claims:
                    self.pointers[key]=tuple(claim.cursor_origin+claim.position-np.array(claim.origin))
                continue
            if action and action.startswith('drag:'):
                self.aims[key]=(hand.generation,self.host.page_key,action,t,point)
            elif action is None and key in self.aims:
                aimed=self.aims[key]
                if np.linalg.norm((np.array(point)-aimed[4])/np.array((1.,aspect)))<=self.settings['chemistry_panel_aim_radius']:
                    action=aimed[2]
            if gate.slots and not gate.suspended and not consumed and action and action.startswith('drag:'):
                view_targets={'drag:orbit','drag:zoom'}
                owned={c.target for c in self.claims.values()}
                if action not in owned and not (owned and (action in view_targets or owned & view_targets)):
                    self.claims[key]=PhysicsClaim(hand.generation,action,grip,self.host.capture(action),
                        position=np.array(grip),target_point=np.array(grip),cursor_origin=np.array(point))
                    self.host.pause_edit(); self.dwell.states.pop(key,None)
                continue
            if chosen is not None and chosen[0]==self.host.page_key:
                self.dwell.latch(key,hand.generation,chosen,t,point)
                self.host.command(chosen[1]); continue
            if self.claims or (consumed and state.phase=='press'):
                self.dwell.states.pop(key,None); continue
            if consumed and state.phase!='cancelled':
                dwell=self.dwell.states.get(key)
                if dwell: dwell.last=t
                continue
            chosen=self.dwell.update(key,hand.generation,candidate,t,point,outside=action is None or bool(action and action.startswith('drag:')))
            if chosen:
                self.tap.latch(key,hand.generation,chosen,t,point); self.host.command(chosen[1])

    def _grip_point(self,hand):
        # Palm translation excludes the two folding contact fingers. Acquisition
        # still hits the index cursor; its offset is kept for the whole claim.
        points=[hand.landmarks[i] for i in (0,5,9,13,17)]
        x=sum(p.x for p in points)/len(points); y=sum(p.y for p in points)/len(points)
        return (1-x if self.settings['mirror'] else x,y)

    def advance(self,dt):
        """Follow the last real observation at render rate; never coast on release."""
        if not math.isfinite(dt) or dt<=0: return
        alpha=-math.expm1(-math.tau*self.settings['physics_drag_response_hz']*dt)
        for key,claim in list(self.claims.items()):
            if claim.paused or claim.finished: continue
            claim.position+=alpha*(claim.target_point-claim.position)
            finished=self.host.drag(claim.target,claim.origin,tuple(claim.position),claim.value) is False
            claim.finished=finished; claim.paused=finished
            self.pointers[key]=tuple(claim.cursor_origin+claim.position-np.array(claim.origin))

    def diagnostics(self):
        return {'claims':{str(k):{'target':v.target,'generation':v.generation,'paused':v.paused,'finished':v.finished} for k,v in self.claims.items()},
                'selection':{str(k):{'target':v.target,'phase':v.phase,'ratio':v.ratio,'cancel_reason':v.reason} for k,v in self.tap.states.items()}}

"""Typed, exclusive presentation gestures for the mechanics lab."""
from dataclasses import dataclass
import math
import numpy as np
from .chemistry_controls import PointPinch
from .dwell import DwellSelector
from .manipulation import PinchGate
from .physics_shortcuts import PhysicsShortcuts


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
    opening_since: float | None = None
    opening_samples: int = 0


class PhysicsInput:
    def __init__(self,settings,host):
        self.settings=settings; self.host=host
        self.tap=PointPinch(settings)
        self.dwell=DwellSelector(settings['chemistry_dwell_s'],settings['chemistry_dwell_max_gap_s'],
            settings['chemistry_dwell_rearm_distance'],settings['chemistry_dwell_motion_radius'])
        self.gates={}; self.claims={}; self.aims={}; self.pointers={}; self.hover={}; self.previous=None
        self.scene_group=None; self.rearm={}
        self.shortcuts=PhysicsShortcuts(settings); self.auto_scene=False
        self.menu_anchors={}; self.last_available={}; self.palette_needs_guard=False
        self.grab_settings={**settings,'grip_press_ratio':settings['chemistry_grip_press_ratio'],
            'grip_release_ratio':settings['chemistry_grip_release_ratio'],
            'grip_press_s':settings['chemistry_grip_press_s'],'grip_release_s':settings['chemistry_grip_release_s'],
            'grip_loss_grace_s':settings['chemistry_grip_loss_grace_s']}

    def release(self):
        for key in list(self.claims): self._drop(key)
        self.claims.clear(); self.gates.clear(); self.aims.clear(); self.pointers.clear(); self.hover.clear()
        self.tap.reset(); self.dwell.reset(); self.previous=None; self.scene_group=None
        self.shortcuts.reset(); self.menu_anchors.clear(); self.last_available={}
        self.palette_needs_guard=getattr(self.host,'quick_open',False)

    def cancel(self):
        self.rearm.update({key:c.generation for key,c in self.claims.items()})
        for key in list(self.claims): self._drop(key)
        self.gates.clear(); self.aims.clear(); self.scene_group=None

    def _drop(self,key,deliberate=False):
        claim=self.claims.pop(key,None)
        if claim and claim.target=='drag:scene': self.scene_group=None
        if claim and self.auto_scene and claim.target=='drag:scene':
            if not deliberate:
                self._finish_auto_scene()
                self.rearm[key]=claim.generation
                self.rearm.update({k:c.generation for k,c in self.claims.items()})
                for other in list(self.claims): self._drop(other)
            elif not self.claims: self._finish_auto_scene()
        if claim and hasattr(self.host,'end_edit'):
            self.host.end_edit(claim.target,deliberate,bool(self.claims))

    def _finish_auto_scene(self):
        self.auto_scene=False; self.shortcuts.opens.clear(); self.shortcuts.ready.clear(); self.shortcuts.pair=None
        if getattr(self.host,'tool',None)=='scene': self.host.tool='edit'
        self.host.ui_dirty=True; self.host.panel_force=True

    def palette_transition(self,opening=False):
        for key,hand in self.last_available.items():
            p=hand.landmarks[8]; point=(1-p.x if self.settings['mirror'] else p.x,p.y)
            self.menu_anchors[key]=(hand.generation,np.array(point))
        self.gates.clear(); self.aims.clear(); self.dwell.reset()
        self.shortcuts.progress=None
        if opening: self.tap.reset()
        self.palette_needs_guard=False

    def _update_shortcuts(self,available,observed,t,aspect,source_aspect):
        if not hasattr(self.host,'shortcut_free'): return
        busy=bool(self.claims) or self.host.mouse_claim is not None
        free={key:(not busy and not self.host.quick_open and key not in self.menu_anchors and key not in self.aims
                   and not (self.tap.states.get(key) and self.tap.states[key].phase in ('press','latched','cancelled'))
                   and self.host.shortcut_free(h))
              for key,h in available.items()}
        result=self.shortcuts.update(available,observed,t,aspect,source_aspect,free,
            can_quick=not busy and not self.host.quick_open,
            can_scene=not busy and not self.host.quick_open and self.host.tool=='edit' and not self.host.model.running)
        if result is None: return
        if result[0]=='quick': self.host.command('quick_open:'+result[1])
        else:
            keys=result[1]
            if not all(self.gates[k].slots and not self.gates[k].suspended for k in keys): return
            self.auto_scene=True; self.host.tool='scene'; self.host.pause_edit()
            self.host.ui_dirty=True; self.host.panel_force=True
            self.host.model.message='Xem cảnh nhanh • Buông cả hai tay để về Chỉnh vật'
            for key in keys:
                hand=available[key]; grip=self._grip_point(hand); tip=hand.landmarks[8]
                point=(1-tip.x if self.settings['mirror'] else tip.x,tip.y)
                self.claims[key]=PhysicsClaim(hand.generation,'drag:scene',grip,self.host.capture('drag:scene'),
                    position=np.array(grip),target_point=np.array(grip),cursor_origin=np.array(point))
                self.tap.states.pop(key,None); self.dwell.states.pop(key,None)

    def _interrupt(self):
        if hasattr(self.host,'interrupt_edit'): self.host.interrupt_edit()

    def update(self,hands,t,aspect,gesture_hands=None,source_aspect=None):
        if not math.isfinite(t): self.release(); return
        if self.previous is not None and (t<=self.previous or t-self.previous>self.settings['chemistry_dwell_max_gap_s']): self.release()
        self.previous=t
        available={h.slot:h for h in hands if len(h.landmarks)==21 and tuple(p.index for p in h.landmarks)==tuple(range(21)) and all(math.isfinite(v) for p in h.landmarks for v in (p.x,p.y,p.z))}
        observed=available if gesture_hands is None else {h.slot:h for h in gesture_hands}
        previous=self.last_available; self.last_available=available
        if self.palette_needs_guard: self.palette_transition(opening=True)
        if getattr(self.host,'quick_open',False):
            for key,h in available.items():
                if key not in previous or previous[key].generation!=h.generation:
                    p=h.landmarks[8]; self.menu_anchors[key]=(h.generation,np.array((1-p.x if self.settings['mirror'] else p.x,p.y)))
        self.tap.retain(available); self.dwell.retain(available)
        self.pointers={}; self.hover={}
        self.aims={k:a for k,a in self.aims.items() if k in available and a[0]==available[k].generation and a[1]==self.host.page_key and t-a[3]<=self.settings['chemistry_panel_aim_grace_s']}
        for key in sorted(set(self.gates)|set(available)):
            hand=available.get(key); claim=self.claims.get(key)
            gate=self.gates.setdefault(key,PinchGate(self.grab_settings))
            if claim and hand and claim.generation!=hand.generation:
                self._drop(key); gate.reset(); claim=None
            gate.update((observed.get(key,hand),) if hand else (),t,source_aspect or aspect)
            if key in self.menu_anchors and hand:
                tip=hand.landmarks[8]; point=np.array((1-tip.x if self.settings['mirror'] else tip.x,tip.y))
                generation,anchor=self.menu_anchors[key]; self.pointers[key]=tuple(point)
                if generation!=hand.generation:
                    self.menu_anchors[key]=(hand.generation,point.copy())
                elif (gate.grips[key].ratio>=self.grab_settings['grip_release_ratio']
                      and (not getattr(self.host,'quick_open',False) or
                           np.linalg.norm((point-anchor)*np.array((aspect,1.)))>=self.settings['physics_quick_reaim_radius'])):
                    self.menu_anchors.pop(key); gate.reset()
                continue
            if key in self.rearm and hand:
                if self.rearm[key]!=hand.generation:
                    self.rearm[key]=hand.generation
                if gate.grips[key].ratio>=self.grab_settings['grip_release_ratio']:
                    self.rearm.pop(key); gate.reset()
                continue
            if hand is None:
                if claim:
                    if self.auto_scene:
                        self._drop(key); continue
                    self._interrupt()
                    claim.opening_since=None; claim.opening_samples=0
                    if gate.slots: claim.paused=True
                    else: self._drop(key)
                continue
            tip=hand.landmarks[8]; point=(1-tip.x if self.settings['mirror'] else tip.x,tip.y)
            action=self.host.hit(point)
            state=self.tap.states.get(key)
            if state and state.target[0]!=self.host.page_key and state.phase not in ('latched','cancelled'):
                if state.phase=='press': self.tap.cancel(key,t)
                else: self.tap.states.pop(key)
            candidate=(self.host.page_key,action) if action and not action.startswith('drag:') else None
            safety=action=='cancel_edit'
            point,chosen=self.tap.update(key,observed.get(key,hand),candidate,t,point,source_aspect or aspect,blocked=bool(self.claims) and not safety)
            self.pointers[key]=point
            state=self.tap.states.get(key)
            if state and state.locked and state.target[0]==self.host.page_key: action=state.target[1]
            self.hover[key]=action
            consumed=state and state.phase in ('press','latched','cancelled')
            grip=self._grip_point(hand)
            if claim:
                if not gate.slots:
                    deliberate=(claim.opening_since is not None and claim.opening_samples>=self.settings['physics_drag_release_observations']
                                and t-claim.opening_since>=self.settings['physics_drag_release_s'])
                    self._drop(key,deliberate)
                elif self._opening(claim,gate.grips[key].ratio,t):
                    claim.paused=True
                    if (t-claim.opening_since>=self.settings['physics_drag_release_s']-1e-9 and
                        claim.opening_samples>=self.settings['physics_drag_release_observations']):
                        self._drop(key,True); gate.reset(); self.aims.pop(key,None)
                elif (gate.suspended or claim.finished or
                      (claim.paused and gate.grips[key].ratio>self.grab_settings['grip_press_ratio'])):
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
                view_targets={'drag:orbit','drag:zoom','drag:scene'}
                owned={c.target for c in self.claims.values()}
                scene_join=action=='drag:scene' and owned=={'drag:scene'} and len(self.claims)<2
                if scene_join or (action not in owned and not (owned and (action in view_targets or owned & view_targets))):
                    if hasattr(self.host,'begin_edit'): self.host.begin_edit(action)
                    self.claims[key]=PhysicsClaim(hand.generation,action,grip,self.host.capture(action),
                        position=np.array(grip),target_point=np.array(grip),cursor_origin=np.array(point))
                    self.host.pause_edit(); self.dwell.states.pop(key,None)
                continue
            if chosen is not None and chosen[0]==self.host.page_key:
                self.dwell.latch(key,hand.generation,chosen,t,point)
                self.host.command(chosen[1]); continue
            if (self.claims and not safety) or (consumed and state.phase=='press'):
                self.dwell.states.pop(key,None); continue
            if consumed and state.phase!='cancelled':
                dwell=self.dwell.states.get(key)
                if dwell: dwell.last=t
                continue
            chosen=self.dwell.update(key,hand.generation,candidate,t,point,outside=action is None or bool(action and action.startswith('drag:')))
            if chosen:
                self.tap.latch(key,hand.generation,chosen,t,point); self.host.command(chosen[1])
        self._update_shortcuts(available,observed,t,aspect,source_aspect or aspect)

    def _grip_point(self,hand):
        # Palm translation excludes the two folding contact fingers. Acquisition
        # still hits the index cursor; its offset is kept for the whole claim.
        points=[hand.landmarks[i] for i in (0,5,9,13,17)]
        x=sum(p.x for p in points)/len(points); y=sum(p.y for p in points)/len(points)
        return (1-x if self.settings['mirror'] else x,y)

    def _opening(self,claim,ratio,t):
        # Once opening starts, the hysteresis band is still a release, not a
        # fresh hold. Only a tight contact cancels it, rebasing before motion.
        model_handle=(claim.target.startswith('drag:') and not claim.target.startswith('drag:param:')
                      and claim.target not in ('drag:panel','drag:orbit','drag:zoom','drag:scene'))
        threshold=self.settings['physics_model_hold_ratio'] if model_handle else self.settings['physics_drag_freeze_ratio']
        if ratio<=self.grab_settings['grip_press_ratio']:
            claim.opening_since=None; claim.opening_samples=0
        elif ratio>=threshold and claim.opening_since is None:
            claim.opening_since=t
        if claim.opening_since is not None:
            # Cancel the unrendered follow tail at the displayed point. Do not
            # snap forward to the last camera target while the fingers open.
            claim.target_point=claim.position.copy()
            claim.opening_samples+=1
            return True
        return False

    def advance(self,dt):
        """Follow the last real observation at render rate; never coast on release."""
        if not math.isfinite(dt) or dt<=0: return
        alpha=-math.expm1(-math.tau*self.settings['physics_drag_response_hz']*dt)
        scene=[(key,c) for key,c in sorted(self.claims.items()) if c.target=='drag:scene']
        if scene:
            if any(c.paused or c.finished for _,c in scene):
                self.scene_group=None
                return
            identity=tuple((key,id(c)) for key,c in scene)
            if self.scene_group!=identity:
                # Join/leave/loss changes the baseline, never the displayed pose.
                for _,c in scene:
                    c.cursor_origin=c.cursor_origin+c.position-np.array(c.origin)
                    c.origin=tuple(c.position); c.target_point=c.position.copy()
                    c.value=self.host.capture('drag:scene')
                self.scene_group=identity
            for key,c in scene:
                c.position+=alpha*(c.target_point-c.position)
                self.pointers[key]=tuple(c.cursor_origin+c.position-np.array(c.origin))
            if len(scene)==2:
                factor=np.array((self.host.space.aspect,1.))
                span=np.linalg.norm((scene[1][1].position-scene[0][1].position)*factor)
                base_span=np.linalg.norm((np.array(scene[1][1].origin)-scene[0][1].origin)*factor)
                if span<self.settings['physics_scene_min_span']:
                    self.scene_span_valid=False
                    return
                if not getattr(self,'scene_span_valid',True) or base_span<self.settings['physics_scene_min_span']:
                    for _,c in scene:
                        c.cursor_origin=c.cursor_origin+c.position-np.array(c.origin)
                        c.origin=tuple(c.position); c.value=self.host.capture('drag:scene')
                self.scene_span_valid=True
                self.host.drag_scene_pair([c.origin for _,c in scene],[c.position for _,c in scene],scene[0][1].value)
            else:
                c=scene[0][1]; self.host.drag('drag:scene',c.origin,tuple(c.position),c.value)
            return
        self.scene_group=None
        for key,claim in list(self.claims.items()):
            if claim.paused or claim.finished: continue
            claim.position+=alpha*(claim.target_point-claim.position)
            finished=self.host.drag(claim.target,claim.origin,tuple(claim.position),claim.value) is False
            claim.finished=finished; claim.paused=finished
            self.pointers[key]=tuple(claim.cursor_origin+claim.position-np.array(claim.origin))

    def diagnostics(self):
        return {'tool':getattr(self.host,'tool','edit'),
                'temporary_scene':self.auto_scene,'quick_open':getattr(self.host,'quick_open',False),
                'shortcut_progress':self.shortcuts.progress,
                'claims':{str(k):{'target':v.target,'generation':v.generation,'paused':v.paused,'finished':v.finished,
                                'opening':v.opening_since is not None} for k,v in self.claims.items()},
                'selection':{str(k):{'target':v.target,'phase':v.phase,'ratio':v.ratio,'cancel_reason':v.reason} for k,v in self.tap.states.items()}}

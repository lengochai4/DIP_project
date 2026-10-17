"""Target claims and explicit editing actions for the camera chemistry scene."""
from dataclasses import dataclass
from pathlib import Path
import math
import numpy as np
from .camera_space import sphere_hit
from .manipulation import GrabController, PinchGate
from .dwell import DwellSelector
from .chemistry_controls import IndexPush,PanelLayout


@dataclass
class Claim:
    generation: int
    kind: str
    target: object
    offset: np.ndarray | None = None
    depth: float = 0.
    paused: bool = False


class ChemistryInput:
    def __init__(self,scene,settings):
        self.scene=scene; self.settings=settings
        self.gates={}; self.claims={}; self.groups={}; self.hover={}; self.pointers={}
        self.page='home'; self.panel=None
        self.expanded_page='home'
        self.layout=PanelLayout(settings); self.tap=IndexPush(settings)
        self.panel_base=None; self.panel_target=None
        self.dock_pending=None
        self.previous_time=None
        self.template_page=0
        self.grab_settings={**settings,'grip_press_ratio':settings['chemistry_grip_press_ratio'],
            'grip_release_ratio':settings['chemistry_grip_release_ratio'],
            'grip_press_s':settings['chemistry_grip_press_s'],'grip_release_s':settings['chemistry_grip_release_s'],
            'grip_loss_grace_s':settings['chemistry_grip_loss_grace_s']}
        self.dwell=DwellSelector(settings['chemistry_dwell_s'],settings['chemistry_dwell_max_gap_s'],settings['chemistry_dwell_rearm_distance'],settings['chemistry_dwell_motion_radius'])
        self.path=Path(__file__).resolve().parents[2]/'runs/ui-chemistry/workspace.json'

    def release(self):
        self.scene.freeze(tuple(self.scene.atoms))
        self.scene.finish_edit()
        self.gates.clear(); self.claims.clear(); self.groups.clear(); self.hover.clear(); self.pointers.clear()
        self.dwell.reset()
        self.tap.reset(); self.panel_base=None; self.panel_target=None
        self.previous_time=None
        self.dock_pending=None

    def diagnostics(self):
        """Actual UI state for local logs, never tracking confidence."""
        return {'page':self.page,
            'claims':{str(key):{'generation':c.generation,'kind':c.kind,'target':c.target,'paused':c.paused} for key,c in self.claims.items()},
            'groups':{str(key):{'held_slots':list(v['controller'].slots),'suspended':v['controller'].suspended} for key,v in self.groups.items()},
            'hover':self.hover.copy(),
            'panel_layout':{'anchor':self.layout.anchor.tolist(),'scale':float(self.layout.scale),
                            'edge':self.layout.edge,'edge_position':self.layout.edge_position},
            'tap':{str(key):{'phase':state.phase,'target':state.target,'generation':state.generation}
                   for key,state in self.tap.states.items()},
            'dwell':{str(key):{'target':state.target,'progress':state.progress,'latched':state.latched,'generation':state.generation} for key,state in self.dwell.states.items()}}

    def hit(self,space,nx,ny):
        origin,direction=space.ray(nx,ny)
        panel=self.panel.intersect(origin,direction) if self.panel is not None else None
        if panel and self.page=='compact': return panel[1]
        choices=[]
        if panel: choices.append((panel[0],panel[1]))
        for i,atom in self.scene.atoms.items():
            radius=self.settings['chemistry_atom_radius']*atom.scale*(.8 if atom.symbol=='H' else 1)
            if self.scene.electrons and i==self.scene.selected:
                shells=self.scene.elements[atom.symbol].shells
                radius=max(radius,(.3+.095*(len(shells)-1))*atom.scale+.023*atom.scale)
            distance=sphere_hit(origin,direction,atom.position,radius)
            if distance is not None: choices.append((distance,'atom:'+str(i)))
        return min(choices,key=lambda value:value[0])[1] if choices else None

    def command(self,action):
        scene=self.scene
        if action=='panel:blank' or action is None: return
        if action=='toggle_panel': action=self.expanded_page if self.page=='compact' else 'compact'
        if action=='restore_panel': action=self.expanded_page
        if action=='panel_reset':
            for key in list(self.claims):
                if self.claims[key].kind.startswith('panel_'):
                    self.end(key)
                    if key in self.gates: self.gates[key].reset()
            self.layout.reset(); self.panel_target=None
            if self.page=='compact': self.page=self.expanded_page
            return
        if action in ('home','elements','table','templates','compact'):
            for key in list(self.claims):
                if self.claims[key].kind.startswith('panel_'): self.end(key)
            if action=='compact' and self.page!='compact':
                self.expanded_page=self.page
                center=self.layout.anchor+self.layout.extent/2
                distances=(center[0],1-center[0],center[1],1-center[1])
                edge=('left','right','top','bottom')[int(np.argmin(distances))]
                self.layout.dock(edge,center[1] if edge in ('left','right') else center[0])
            self.page=action; return
        if action in ('templates_prev','templates_next'):
            count=(len(self.settings['chemistry_templates'])+7)//8
            self.template_page=int(np.clip(self.template_page+(1 if action=='templates_next' else -1),0,max(0,count-1)))
            return
        scene.freeze(tuple(scene.atoms)); scene.finish_edit()
        self.claims.clear(); self.groups.clear()
        if action=='edit': scene.edit=not scene.edit; scene.message='Ghép/tách: kéo từng nguyên tử, thả gần để ghép' if scene.edit else 'Cầm khối: giữ cả phân tử; thêm tay để xoay/đổi cỡ'
        elif action=='electrons':
            scene.electrons=not scene.electrons
            if scene.selected not in scene.atoms and scene.atoms: scene.selected=min(scene.atoms)
            scene.message='Lớp e của nguyên tử trung hòa riêng lẻ • minh họa' if scene.electrons else 'Chế độ cầu–que'
        elif action=='order': scene.order=scene.order%3+1; scene.message=f'Liên kết mới: bậc {scene.order}'
        elif action=='undo': scene.undo()
        elif action=='redo': scene.undo(redo=True)
        elif action=='delete': scene.delete_selected()
        elif action=='clear_all': scene.clear_all()
        elif action=='frame':
            if scene.atoms:
                scene.remember()
                points=np.array([a.position for a in scene.atoms.values()])
                radii=np.array([self.settings['chemistry_atom_radius']*a.scale for a in scene.atoms.values()])
                if scene.electrons and scene.selected in scene.atoms:
                    selected=list(scene.atoms).index(scene.selected); atom=scene.atoms[scene.selected]
                    radii[selected]=max(radii[selected],(.3+.095*(len(scene.elements[atom.symbol].shells)-1)+.023)*atom.scale)
                low=(points-radii[:,None]).min(axis=0); high=(points+radii[:,None]).max(axis=0)
                center=(low+high)/2
                factor=min(1.,1.8/max(float(np.max(high-low)),1e-8))
                for atom in scene.atoms.values():
                    atom.target=(atom.position-center)*factor+np.array((.8,0.,0.))
                    atom.scale=float(np.clip(atom.scale*factor,self.settings['grab_min_scale'],self.settings['grab_max_scale']))
                scene.message='Đưa mô hình về giữa vùng thao tác'; scene.revision+=1
        elif action=='save':
            try: scene.save(self.path)
            except OSError as exc: scene.message='Chưa lưu được: '+str(exc)
        elif action=='load':
            try: scene.load(self.path)
            except (OSError,ValueError,KeyError,TypeError) as exc: scene.message='Chưa mở được bản lưu: '+str(exc)
        elif action.startswith('template:'): scene.add_template(action.split(':')[1]); self.page='elements'

    def press(self,key,generation,action,space,nx,ny,timestamp_s,hand=None):
        if key in self.claims: return
        scene=self.scene
        panel_claims=[c for c in self.claims.values() if c.kind.startswith('panel_')]
        if action in ('panel:drag','panel:resize'):
            if any(c.kind in ('atom','group') for c in self.claims.values()): return
            if key=='mouse' and panel_claims: return
            if any(k=='mouse' for k,c in self.claims.items() if c.kind.startswith('panel_')): return
            self.claims[key]=Claim(generation,'panel_move' if action=='panel:drag' else 'panel_resize',action)
            self.pointers[key]=(nx,ny); self.panel_base=None; self.panel_target=None
            return
        if panel_claims: return
        if action and action.startswith('element:'):
            symbol=action.split(':')[1]
            # A palette press creates once; a separate grab has no hidden offset.
            n=len(scene.atoms)%8
            p=space.point(.65+(n%3)*.09,.40+(n//3)*.13)
            i=scene.add(symbol,p)
            if i is None: return
            self.claims[key]=Claim(generation,'panel',action)
            return
        edit=scene.edit
        if action and action.startswith('atom:'):
            i=int(action.split(':')[1])
            if i not in scene.atoms: return
            scene.selected=i; scene.begin_edit()
            atom=scene.atoms[i]
            if edit:
                if any(c.kind=='atom' and c.target==i for c in self.claims.values()): return
                pointer=space.point(nx,ny,atom.position[2])
                self.claims[key]=Claim(generation,'atom',i,atom.position-pointer,float(atom.position[2]))
            else:
                ids=scene.component(i); group=min(ids)
                if any(c.kind=='atom' and c.target in ids for c in self.claims.values()): return
                if group not in self.groups:
                    scales={j:scene.atoms[j].scale for j in ids}
                    points=np.array([scene.atoms[j].position for j in ids])
                    max_span=max(float(np.max(np.ptp(points,axis=0))),1e-8)
                    controller=GrabController({**self.grab_settings,
                        'grab_min_scale':self.settings['grab_min_scale']/min(scales.values()),
                        'grab_max_scale':min(self.settings['grab_max_scale']/max(scales.values()),2*self.settings['chemistry_scene_limit']/max_span)})
                    center=np.mean([scene.atoms[j].position for j in ids],axis=0)
                    self.groups[group]={'controller':controller,'ids':ids,'center':center,
                        'points':{j:scene.atoms[j].position.copy() for j in ids},'scales':scales}
                if hand is None: self.groups[group]['mouse_anchor']=atom.position.copy()
                self.claims[key]=Claim(generation,'group',group,atom.position-space.point(nx,ny,atom.position[2]),float(atom.position[2]))
                if hand is not None: self.groups[group]['controller'].adopt_confirmed_grip(hand,timestamp_s,space.aspect)
            scene.message='Đang kéo nguyên tử để ghép/tách' if edit else 'Đang cầm phân tử'
        else:
            self.command(action)
            self.claims[key]=Claim(generation,'panel',action)

    def end(self,key,deliberate=False):
        claim=self.claims.pop(key,None)
        if claim is None: return
        if claim.kind.startswith('panel_'):
            self.panel_base=None; self.panel_target=None
            return
        if claim.kind=='atom' and claim.target in self.scene.atoms:
            self.scene.freeze((claim.target,))
            if deliberate:
                occupied=[c.target for c in self.claims.values() if c.kind=='atom']
                self.scene.link_nearby(claim.target,occupied)
        elif claim.kind=='group':
            if not any(c.kind=='group' and c.target==claim.target for c in self.claims.values()):
                group=self.groups.pop(claim.target,None)
                if group: self.scene.freeze(group['ids'])
        if not any(c.kind in ('atom','group') for c in self.claims.values()): self.scene.finish_edit()

    def update(self,hands,t,space,gesture_hands=None,source_aspect=None):
        if self.previous_time is not None and (not math.isfinite(t) or t<=self.previous_time or
            t-self.previous_time>self.settings['chemistry_dwell_max_gap_s']):
            for key in list(self.claims):
                if self.claims[key].kind.startswith('panel_'):
                    self.end(key)
                    if key in self.gates: self.gates[key].reset()
            self.tap.reset()
        self.previous_time=t
        available={h.slot:h for h in hands if len(h.landmarks)==21 and
            tuple(l.index for l in h.landmarks)==tuple(range(21)) and
            all(math.isfinite(v) for l in h.landmarks for v in (l.x,l.y,l.z))}
        self.dwell.retain(available)
        self.tap.retain(available)
        self.hover={}; self.pointers={k:p for k,p in self.pointers.items() if k=='mouse' and k in self.claims}
        tapped={}
        gesture_hands=available if gesture_hands is None else {h.slot:h for h in gesture_hands}
        for key,hand in sorted(available.items()):
            tip=hand.landmarks[8]; nx=1-tip.x if self.settings['mirror'] else tip.x; ny=tip.y
            action=self.hit(space,nx,ny)
            candidate=(self.page,action) if action and not action.startswith(('atom:','panel:')) else None
            state=self.dwell.states.get(key)
            tap_state=self.tap.states.get(key)
            if tap_state and tap_state.target[0]!=self.page and tap_state.phase not in ('latched','cancelled'):
                self.tap.states.pop(key,None); tap_state=None
            blocked=bool(self.claims) or bool(state and state.latched and not (tap_state and tap_state.phase=='latched'))
            observed=gesture_hands.get(key,hand)
            (nx,ny),chosen=self.tap.update(key,observed,candidate,t,(nx,ny),source_aspect or space.aspect,blocked)
            if chosen is not None: tapped[key]=chosen
            self.pointers[key]=(nx,ny)
            self.hover[key]=self.hit(space,nx,ny)
        for key in sorted(set(self.gates)|set(available)):
            hand=available.get(key)
            gate=self.gates.get(key)
            if gate is None:
                gate=PinchGate(self.grab_settings); self.gates[key]=gate
            claim=self.claims.get(key)
            if claim and hand is not None and claim.generation!=hand.generation:
                self.end(key); gate.reset(); claim=None
            was_held=bool(gate.slots)
            gate.update((hand,) if hand is not None else (),t,space.aspect)
            held=bool(gate.slots)
            if held and key not in self.claims and hand is not None and not gate.suspended:
                nx,ny=self.pointers[key]
                action=self.hover[key]
                if action in ('panel:drag','panel:resize') or (action and action.startswith('atom:')):
                    self.press(key,hand.generation,action,space,nx,ny,t,hand)
                elif action is None and not self.scene.edit and len(self.groups)==1:
                    # A second hand can join the held component in free space.
                    # It need not hit the tiny nucleus/electron drawing again.
                    value=next(iter(self.groups.values()))
                    self.press(key,hand.generation,'atom:'+str(min(value['ids'])),space,nx,ny,t,hand)
            elif was_held and not held:
                # Loss is cancellation; only confirmed visible opening may link.
                self.end(key,deliberate=hand is not None)
            claim=self.claims.get(key)
            if claim and claim.kind.startswith('panel_') and (hand is None or gate.suspended):
                self.end(key); claim=None
            if claim and claim.kind=='atom' and claim.target in self.scene.atoms:
                if hand is None or gate.suspended:
                    self.scene.freeze((claim.target,))
                    claim.paused=True
                else:
                    nx,ny=self.pointers[key]
                    if claim.paused:
                        atom=self.scene.atoms[claim.target]
                        claim.depth=float(atom.position[2])
                        claim.offset=atom.position-space.point(nx,ny,claim.depth)
                        claim.paused=False
                    self.scene.move_atom(claim.target,space.point(nx,ny,claim.depth)+claim.offset)
            if hand is not None:
                action=self.hover.get(key); nx,ny=self.pointers[key]
                candidate=(self.page,action) if action and not action.startswith(('atom:','panel:')) and key not in self.claims else None
                if self.page=='compact' and held: candidate=None
                if any(c.kind.startswith('panel_') for c in self.claims.values()): candidate=None
                tap=self.tap.states.get(key)
                if tap and tap.phase=='cancelled':
                    self.dwell.states.pop(key,None)
                    continue
                if tap and tap.phase=='press':
                    # Pausing dwell prevents firing it midway through a bend.
                    self.dwell.states.pop(key,None)
                    continue
                if key in tapped and candidate==tapped[key]:
                    self.dwell.latch(key,hand.generation,candidate,t,(nx,ny))
                    self.press('dwell:'+str(key),hand.generation,candidate[1],space,nx,ny,t)
                    self.end('dwell:'+str(key))
                    continue
                chosen=self.dwell.update(key,hand.generation,candidate,t,(nx,ny),outside=action is None or (action and action.startswith('atom:')))
                if chosen is not None:
                    self.press('dwell:'+str(key),hand.generation,chosen[1],space,nx,ny,t)
                    self.end('dwell:'+str(key))
        self._panel_motion(space,t)
        for group,value in self.groups.items():
            selected=[available[k] for k,c in self.claims.items() if c.kind=='group' and c.target==group and k in available]
            controller=value['controller']
            controller.update(selected,t,space.aspect)
            if controller.suspended:
                self.scene.freeze(value['ids'])

    def advance(self,dt):
        if self.panel_target is not None:
            anchor,scale=self.panel_target
            alpha=1-math.exp(-math.tau*self.settings['chemistry_panel_response_hz']*max(0,dt))
            self.layout.anchor+=(anchor-self.layout.anchor)*alpha
            self.layout.scale+=(scale-self.layout.scale)*alpha
        for value in self.groups.values():
            c=value['controller']; c.advance(dt)
            if c.suspended: continue
            center=value['center']; pose=c.pose
            transformed={i:center+pose.position+pose.rotation@((p-center)*pose.scale) for i,p in value['points'].items()}
            coordinates=np.array(list(transformed.values())); limit=self.settings['chemistry_scene_limit']
            shift=np.maximum(-limit-coordinates.min(axis=0),np.minimum(np.zeros(3),limit-coordinates.max(axis=0)))
            pose.position+=shift
            for i,target in transformed.items():
                if i in self.scene.atoms:
                    # Controller already follows at render rate; no second LPF.
                    target=target+shift
                    self.scene.atoms[i].position=target.copy(); self.scene.atoms[i].target=target.copy()
                    self.scene.atoms[i].scale=value['scales'][i]*pose.scale
        self.scene.advance(dt)

    def mouse(self,kind,nx,ny,space):
        key='mouse'
        if kind=='down':
            self.press(key,0,self.hit(space,nx,ny),space,nx,ny,0.)
            self._panel_motion(space)
        elif kind=='up': self.end(key,deliberate=True)
        elif key in self.claims:
            c=self.claims[key]
            if c.kind.startswith('panel_'):
                self.pointers[key]=(nx,ny); self._panel_motion(space)
            elif c.kind=='atom': self.scene.move_atom(c.target,space.point(nx,ny,c.depth)+c.offset)
            elif c.kind=='group':
                value=self.groups[c.target]
                displacement=space.point(nx,ny,c.depth)+c.offset-value['mouse_anchor']
                value['controller'].pose.position=displacement

    def _panel_motion(self,space,t=None):
        keys=tuple(k for k,c in self.claims.items() if c.kind.startswith('panel_') and k in self.pointers)
        if not keys:
            self.panel_base=None; self.panel_target=None; self.dock_pending=None
            return
        points=np.array([self.pointers[k] for k in keys]); center=points.mean(axis=0)
        metric=points/np.array((1.,space.aspect))
        span=float(np.linalg.norm(metric[0]-metric[1])) if len(keys)==2 else None
        if span is not None and span<self.settings['chemistry_panel_min_span']:
            self.panel_base=None; self.panel_target=None; return
        if self.panel_base is None or self.panel_base['keys']!=keys:
            self.panel_base={'keys':keys,'center':center,'anchor':self.layout.anchor.copy(),
                'scale':self.layout.scale,'span':span}
        base=self.panel_base; scale=base['scale']; anchor=base['anchor'].copy()
        if span is not None:
            scale*=span/base['span']; anchor+=center-base['center']
        elif self.claims[keys[0]].kind=='panel_resize':
            old=np.linalg.norm((base['center']-base['anchor'])/np.array((1.,space.aspect)))
            new=np.linalg.norm((center-base['anchor'])/np.array((1.,space.aspect)))
            scale*=new/max(old,1e-6)
        else: anchor+=center-base['center']
        scale=float(np.clip(scale,self.settings['chemistry_panel_min_scale'],self.settings['chemistry_panel_max_scale']))
        self.panel_target=(anchor,scale)
        if all(self.claims[k].kind=='panel_move' for k in keys) and self.page!='compact':
            distances=(center[0],1-center[0],center[1],1-center[1])
            index=int(np.argmin(distances)); distance=distances[index]
            borders=(anchor[0],1-anchor[0]-self.layout.extent[0],
                     anchor[1],1-anchor[1]-self.layout.extent[1])
            beyond=int(np.argmin(borders))
            if borders[beyond]<=-self.settings['chemistry_panel_throw_edge']:
                index=beyond; distance=borders[beyond]
            edge=('left','right','top','bottom')[index]
            if distance<=self.settings['chemistry_panel_dock_edge']:
                if self.dock_pending is None or self.dock_pending[0]!=edge:
                    self.dock_pending=(edge,t)
                since=self.dock_pending[1]
                if (distance<=-self.settings['chemistry_panel_throw_edge'] or
                    (t is not None and since is not None and t-since>=self.settings['chemistry_panel_dock_s'])):
                    self.command('compact')
                    self.layout.dock(edge,center[1] if edge in ('left','right') else center[0])
            else: self.dock_pending=None

    def wheel(self,amount,nx,ny,space):
        if self.claims or not self.hit(space,nx,ny) or self.hit(space,nx,ny).startswith('atom:'): return False
        self.layout.zoom(math.exp(float(np.clip(amount,-5,5))*self.settings['chemistry_panel_zoom_step']))
        self.panel_target=None
        return True

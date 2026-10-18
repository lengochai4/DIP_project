"""Physics-only observed XY shortcuts; no Core or renderer dependency."""
import math
import numpy as np
from .geometry import angle


class PhysicsShortcuts:
    def __init__(self,settings):
        self.cfg=settings; self.reset()

    def reset(self):
        self.palms={}; self.opens={}; self.ready={}; self.pair=None
        self.previous=None; self.progress=None

    def features(self,hand,aspect):
        points=hand.raw_landmarks or hand.landmarks
        if (len(points)!=21 or tuple(p.index for p in points)!=tuple(range(21))
            or not math.isfinite(aspect) or aspect<=0
            or any(not math.isfinite(v) for p in points for v in (p.x,p.y))): return None
        p=np.array([(v.x,v.y/aspect) for v in points])
        size=max(np.linalg.norm(p[0]-p[9]),np.linalg.norm(p[5]-p[17]))
        if size<self.cfg['physics_shortcut_min_palm']: return None
        ratio=float(np.linalg.norm(p[4]-p[8])/size)
        open_palm=True
        for tip in (8,12,16,20):
            straight=min(angle(p[tip-3],p[tip-2],p[tip-1]),angle(p[tip-2],p[tip-1],p[tip]))
            reach=np.linalg.norm(p[tip]-p[0])/max(np.linalg.norm(p[tip-2]-p[0]),1e-12)
            open_palm &= straight>=self.cfg['physics_quick_finger_angle_deg'] and reach>=self.cfg['physics_quick_finger_reach']
        thumb=angle(p[2],p[3],p[4])>=self.cfg['physics_quick_thumb_angle_deg']
        spread=np.linalg.norm(p[4]-p[5])/size>=self.cfg['physics_quick_thumb_spread']
        a,b=p[5]-p[0],p[17]-p[0]
        area=abs(a[0]*b[1]-a[1]*b[0])/max(np.linalg.norm(a)*np.linalg.norm(b),1e-12)
        visible=all(0<=v.x<=1 and 0<=v.y<=1 for v in points)
        open_palm=bool(open_palm and thumb and spread and visible
                       and area>=self.cfg['physics_quick_min_palm_area']
                       and ratio>=self.cfg['chemistry_grip_release_ratio'])
        return ratio,open_palm

    def update(self,hands,observed,t,aspect,source_aspect,free,can_quick,can_scene):
        self.progress=None
        if not math.isfinite(t): self.reset(); return None
        if self.previous is not None and (t<=self.previous or t-self.previous>self.cfg['chemistry_dwell_max_gap_s']): self.reset()
        self.previous=t; features={}; centers={}; tokens={}
        if not can_quick and not can_scene:
            self.opens.clear(); self.ready.clear(); self.pair=None
            for state in self.palms.values(): state['since']=None; state['count']=0
            if not any(state['latched'] for state in self.palms.values()): return None
        for key,h in hands.items():
            if not can_quick and not can_scene and not self.palms.get(key,{}).get('latched',False): continue
            source=observed.get(key)
            if source is None or source.generation!=h.generation: continue
            value=self.features(source,source_aspect)
            if value is None: continue
            points=[h.landmarks[i] for i in (0,5,9,13,17)]
            center=np.array((sum(p.x for p in points)/5,sum(p.y for p in points)/5))
            if self.cfg['mirror']: center[0]=1-center[0]
            centers[key]=center; features[key]=value; tokens[key]=(key,h.generation)
        for key,state in self.palms.items():
            if key not in features: state['since']=None; state['count']=0; state['off']=None
        for key in sorted(features):
            token=tokens[key]; center=centers[key]; _,opened=features[key]
            state=self.palms.get(key)
            if state is None or state['token']!=token:
                state={'token':token,'since':None,'count':0,'latched':False,'off':None,'off_count':0}
                self.palms[key]=state
            edge='left' if center[0]<=self.cfg['physics_quick_edge_fraction'] else 'right' if center[0]>=1-self.cfg['physics_quick_edge_fraction'] else None
            pose=opened and edge is not None and 0<=center[0]<=1 and 0<=center[1]<=1
            if not pose:
                if state['off'] is None: state['off']=t; state['off_count']=0
                state['off_count']+=1
                if t-state['off']>=self.cfg['physics_quick_rearm_s'] and state['off_count']>=self.cfg['physics_quick_rearm_observations']: state['latched']=False
            else: state['off']=None; state['off_count']=0
            eligible=pose and can_quick and free.get(key,False) and not state['latched']
            if not eligible: state['since']=None; state['count']=0; continue
            if (state['since'] is None or state.get('edge')!=edge
                or np.linalg.norm((center-state['anchor'])*np.array((aspect,1.)))>self.cfg['physics_quick_motion_radius']):
                state.update(since=t,count=0,anchor=center.copy(),edge=edge)
            state['count']+=1
            progress=min(1.,(t-state['since'])/self.cfg['physics_quick_hold_s'])
            self.progress=('quick',tuple(center),progress)
            if progress>=1 and state['count']>=self.cfg['physics_quick_min_observations']:
                state['latched']=True; state['since']=None
                self.opens.clear(); self.ready.clear(); self.pair=None; self.progress=None
                return 'quick',edge
        # A shortcut needs fresh observed open hands; an already-held pinch on
        # entry/reacquisition cannot activate a view mode by itself.
        valid={tokens[k] for k in features if can_scene and free.get(k,False)}
        self.opens={k:v for k,v in self.opens.items() if k in valid}
        self.ready={k:v for k,v in self.ready.items() if k in valid and t-v<=self.cfg['physics_auto_view_open_memory_s']}
        for key,(ratio,_) in features.items():
            token=tokens[key]
            if token not in valid: continue
            if ratio>=self.cfg['chemistry_grip_release_ratio']:
                since,count=self.opens.get(token,(t,0)); self.opens[token]=(since,count+1)
                if t-since>=self.cfg['physics_auto_view_open_s'] and count+1>=self.cfg['physics_auto_view_min_observations']:
                    self.ready[token]=t
            else: self.opens.pop(token,None)
        pair=tuple(sorted(tokens.values()))
        closed=(len(pair)==2 and set(pair)<=self.ready.keys()
                and all(features[k][0]<=self.cfg['chemistry_grip_press_ratio'] for k,_ in pair))
        if not closed: self.pair=None; return None
        points=np.array([centers[k] for k,_ in pair])
        if (self.pair is None or self.pair['tokens']!=pair
            or np.max(np.linalg.norm((points-self.pair['points'])*np.array((aspect,1.)),axis=1))>self.cfg['physics_auto_view_motion_radius']):
            self.pair={'tokens':pair,'since':t,'count':0,'points':points}
        self.pair['count']+=1
        progress=min(1.,(t-self.pair['since'])/self.cfg['physics_auto_view_hold_s'])
        self.progress=('scene',tuple(points.mean(axis=0)),progress)
        if progress>=1 and self.pair['count']>=self.cfg['physics_auto_view_min_observations']:
            self.opens.clear(); self.ready.clear(); self.pair=None; self.progress=None
            return 'scene',tuple(k for k,_ in pair)
        return None

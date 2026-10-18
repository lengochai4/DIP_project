"""Bounded educational mechanics in SI; no camera, renderer or Core dependency.

These models use standard Newtonian laws. Configured hand gestures set model
inputs and are never measurements of physical force, distance or velocity.
"""
from collections import deque
import copy
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import yaml


CATALOG_PATH=Path(__file__).with_name('physics_labs.yaml')


def load_catalog():
    try: data=yaml.safe_load(CATALOG_PATH.read_text(encoding='utf-8'))
    except yaml.YAMLError as exc: raise ValueError('Invalid physics catalog YAML') from exc
    if not isinstance(data,dict) or data.get('schema')!=1 or set(data.get('labs',{}))!={'forces','incline','projectile','collision','spring','pendulum','lever','pulley'}:
        raise ValueError('Invalid physics catalog schema')
    engine=data['engine']
    for key in ('fixed_dt_s','max_frame_s','sample_s','max_time_s'):
        if not isinstance(engine[key],(int,float)) or not math.isfinite(engine[key]) or engine[key]<=0: raise ValueError('Invalid physics timing')
    if not engine['fixed_dt_s']<=engine['sample_s'] or engine['max_frame_s']/engine['fixed_dt_s']>engine['max_substeps']:
        raise ValueError('Unbounded physics step budget')
    if type(engine['max_samples']) is not int or engine['max_samples']<2: raise ValueError('Invalid physics sample capacity')
    for lab in data['labs'].values():
        for name,unit,low,high,step,default in lab['params'].values():
            if not (all(type(v) in (int,float) and math.isfinite(v) for v in (low,high,step,default)) and low<high and step>0 and low<=default<=high):
                raise ValueError('Invalid physics parameter catalog')
    return data


def rk4(state,dt,derivative):
    """Classical RK4, including dissipated-energy quadrature in the state."""
    def plus(a,b,factor): return [x+factor*y for x,y in zip(a,b)]
    a=derivative(state); b=derivative(plus(state,a,dt/2))
    c=derivative(plus(state,b,dt/2)); d=derivative(plus(state,c,dt))
    return [x+dt*(aa+2*bb+2*cc+dd)/6 for x,aa,bb,cc,dd in zip(state,a,b,c,d)]


class PhysicsLab:
    schema=1

    def __init__(self,lab='forces',catalog=None):
        self.catalog=catalog or load_catalog(); self.engine=self.catalog['engine']
        self.catalog_hash=hashlib.sha256(json.dumps(self.catalog,sort_keys=True,ensure_ascii=False).encode('utf-8')).hexdigest()
        self.speed=1.; self.running=False; self.reference=None
        self.challenge=False; self.message='Chọn thông số, dự đoán rồi chạy thí nghiệm'
        self.revision=0
        self.choose(lab)

    @property
    def spec(self): return self.catalog['labs'][self.lab]

    @property
    def static(self): return bool(self.spec.get('static',False))

    def choose(self,lab):
        if lab not in self.catalog['labs']: raise ValueError('Unknown physics experiment')
        self.lab=lab; self.params={k:float(v[5]) for k,v in self.spec['params'].items()}
        self.reference=None; self.reset()

    def reset(self):
        p=self.params
        self.running=False; self.finished=False; self.landed=False; self.time=0.; self.accumulator=0.
        self.message='Bài tĩnh • Điều chỉnh rồi chọn Kiểm tra' if self.static else 'Thiết lập thông số • Chọn Chạy để thử'
        self.sample_at=0.; self.discarded_wall_s=0.; self.input_work=0.; self.thermal=0.
        self.collided=False; self.period=None; self.crossings=[]; self.goal_since=None
        self.achieved=False; self.previous_goal=None
        self.prediction=None
        self.inputs=[]; self.initial_params=p.copy()
        self.samples=deque(maxlen=self.engine['max_samples'])
        if self.lab=='projectile':
            a=math.radians(p['angle']); self.q=[0.,p['height'],p['speed']*math.cos(a),p['speed']*math.sin(a)]
        elif self.lab=='collision':
            half=self.engine['collision_separation_m']/2
            self.q=[-half,half,p['velocity1'],p['velocity2']]
        elif self.lab=='spring': self.q=[p['displacement'],0.,0.]
        elif self.lab=='pendulum': self.q=[math.radians(p['angle']),0.,0.]
        else: self.q=[p.get('position0',0.),0.]
        self.initial_energy=0. if self.lab=='pulley' else self.metrics()['energy']
        self._record(); self.revision+=1

    def set_parameter(self,key,value):
        if key not in self.spec['params'] or isinstance(value,bool) or not math.isfinite(value):
            raise ValueError('Invalid physics parameter')
        spec=self.spec['params'][key]
        value=float(max(spec[2],min(spec[3],value)))
        if key=='strands': value=float(round(value))
        if value==self.params[key]: return False
        live=self.lab in ('forces','incline') and key=='force'
        self.params[key]=value
        if key=='mu_s': self.params['mu_k']=min(value,self.params['mu_k'])
        if key=='mu_k': self.params['mu_s']=max(value,self.params['mu_s'])
        if live:
            event={'time_s':self.time,'parameter':key,'value':value}
            if self.inputs and self.inputs[-1]['time_s']==self.time and self.inputs[-1]['parameter']==key:
                self.inputs[-1]=event
            else: self.inputs.append(event)
            self.revision+=1
        else: self.reset()
        return True

    def toggle(self):
        if self.static:
            self.message='Bài tĩnh: kéo tay nắm hoặc thay thông số để đo cân bằng/công'
            return
        if self.finished: self.reset()
        self.running=not self.running; self.accumulator=0.
        self.message='Đang mô phỏng' if self.running else 'Đã tạm dừng'
        self.revision+=1

    def advance(self,wall_dt):
        if not math.isfinite(wall_dt) or wall_dt<0: raise ValueError('Invalid physics elapsed time')
        if not math.isfinite(self.speed) or not 0<self.speed<=1: raise ValueError('Invalid physics playback speed')
        if not self.running or self.static: return
        elapsed=min(wall_dt,self.engine['max_frame_s'])
        self.discarded_wall_s+=wall_dt-elapsed
        self.accumulator+=elapsed*self.speed
        dt=self.engine['fixed_dt_s']
        while self.accumulator>=dt-1e-12 and self.running:
            self.step(); self.accumulator=max(0.,self.accumulator-dt)

    def step(self):
        """Advance exactly one configured simulation step, even while paused."""
        if self.static:
            self._check_goal(); return
        if self.finished: return
        dt=min(self.engine['fixed_dt_s'],self.engine['max_time_s']-self.time)
        if dt<=0: self.finished=True; self.running=False; return
        elapsed=dt
        if self.lab in ('forces','incline'): self._friction_step(dt)
        elif self.lab=='projectile': elapsed=self._projectile_step(dt)
        elif self.lab=='collision': self._collision_step(dt)
        elif self.lab=='spring':
            p=self.params
            self.q=rk4(self.q,dt,lambda s:[s[1],(-p['stiffness']*s[0]-p['damping']*s[1])/p['mass'],p['damping']*s[1]**2])
        elif self.lab=='pendulum':
            p=self.params; previous=self.q[0]
            self.q=rk4(self.q,dt,lambda s:[s[1],-p['gravity']/p['length']*math.sin(s[0])-p['damping']*s[1]/(p['mass']*p['length']**2),p['damping']*s[1]**2])
            if previous>0>=self.q[0] and self.q[1]<0:
                crossing=self.time+dt*previous/(previous-self.q[0]); self.crossings.append(crossing)
                if len(self.crossings)>1: self.period=self.crossings[-1]-self.crossings[-2]
        self.time+=elapsed
        self._check_goal()
        if self.time-self.sample_at>=self.engine['sample_s']-1e-12 or self.finished:
            self._record(); self.sample_at=self.time
        if self.time>=self.engine['max_time_s']-1e-10:
            self.finished=True; self.running=False; self.message='Đã hết thời gian lượt • Đặt lại để thử tiếp'

    def _friction(self,velocity):
        p=self.params; angle=math.radians(p.get('angle',0))
        normal=p['mass']*p['gravity']*math.cos(angle)
        drive=p['force']-p['mass']*p['gravity']*math.sin(angle)
        if velocity==0. and abs(drive)<=p['mu_s']*normal+self.engine['friction_force_epsilon_n']:
            return 0.,-drive,normal
        direction=velocity if velocity else drive
        friction=-math.copysign(p['mu_k']*normal,direction)
        return (drive+friction)/p['mass'],friction,normal

    def _friction_step(self,dt):
        x,v=self.q; acceleration,friction,_=self._friction(v)
        stop=-v/acceleration if v and acceleration*v<0 else math.inf
        first=min(dt,stop)
        delta=v*first+.5*acceleration*first**2
        self.q=[x+delta,0. if stop<=dt else v+acceleration*dt]
        self.input_work+=self.params['force']*delta
        self.thermal+=abs(friction*delta)
        if stop<dt:
            acceleration,friction,_=self._friction(0.)
            delta=.5*acceleration*(dt-stop)**2
            self.q[0]+=delta; self.q[1]=acceleration*(dt-stop)
            self.input_work+=self.params['force']*delta; self.thermal+=abs(friction*delta)

    def _projectile_step(self,dt):
        p=self.params; x,y,vx,vy=self.q; g=p['gravity']
        impact=(vy+math.sqrt(max(0.,vy*vy+2*g*y)))/g
        if impact<=dt:
            dt=max(0.,impact); self.finished=True; self.landed=True; self.running=False
            self.message='Đã chạm đất • Giữ A để so sánh một phương án khác'
        self.q=[x+vx*dt,0. if self.landed else max(0.,y+vy*dt-.5*g*dt*dt),vx,vy-g*dt]
        return dt

    def _collision_step(self,dt):
        x1,x2,v1,v2=self.q; relative=v1-v2
        hit=(x2-x1-self.engine['collision_contact_m'])/relative if relative>0 and not self.collided else math.inf
        if 0<=hit<=dt:
            x1+=v1*hit; x2+=v2*hit
            p=self.params; m1,m2,e=p['mass'],p['mass2'],p['restitution']
            total=m1*v1+m2*v2
            u1=(total-m2*e*relative)/(m1+m2); u2=(total+m1*e*relative)/(m1+m2)
            self.thermal+=max(0.,.5*m1*v1*v1+.5*m2*v2*v2-.5*m1*u1*u1-.5*m2*u2*u2)
            v1,v2=u1,u2; dt-=hit; self.collided=True
        self.q=[x1+v1*dt,x2+v2*dt,v1,v2]

    def metrics(self):
        p=self.params; m=p['mass']; g=p.get('gravity',0.)
        result={'time_s':self.time,'position_m':self.q[0],'velocity_m_s':self.q[1],
                'acceleration_m_s2':0.,'height_m':0.,'kinetic_j':0.,'potential_j':0.,
                'thermal_j':self.thermal,'work_j':self.input_work}
        if self.lab in ('forces','incline'):
            a,friction,normal=self._friction(self.q[1]); height=self.q[0]*math.sin(math.radians(p.get('angle',0)))
            result.update(acceleration_m_s2=a,friction_n=friction,normal_n=normal,
                applied_n=p['force'],height_m=height,kinetic_j=.5*m*self.q[1]**2,potential_j=m*g*height)
        elif self.lab=='projectile':
            x,y,vx,vy=self.q
            result.update(position_m=x,height_m=y,velocity_m_s=math.hypot(vx,vy),
                vx_m_s=vx,vy_m_s=vy,acceleration_m_s2=-g,kinetic_j=.5*m*(vx*vx+vy*vy),potential_j=m*g*y,
                target_error_m=abs(x-p['target']) if self.landed else None)
        elif self.lab=='collision':
            x1,x2,v1,v2=self.q
            result.update(position_m=x1,position2_m=x2,velocity_m_s=v1,velocity2_m_s=v2,
                kinetic_j=.5*m*v1*v1+.5*p['mass2']*v2*v2,momentum_kg_m_s=m*v1+p['mass2']*v2)
        elif self.lab=='spring':
            x,v,d=self.q
            result.update(kinetic_j=.5*m*v*v,potential_j=.5*p['stiffness']*x*x,thermal_j=d,
                acceleration_m_s2=(-p['stiffness']*x-p['damping']*v)/m,
                spring_n=-p['stiffness']*x,damping_n=-p['damping']*v,period_small_s=math.tau*math.sqrt(m/p['stiffness']))
        elif self.lab=='pendulum':
            angle,omega,d=self.q; length=p['length']; height=length*(1-math.cos(angle))
            result.update(position_m=length*math.sin(angle),angle_rad=angle,angular_velocity_rad_s=omega,
                height_m=height,velocity_m_s=length*omega,kinetic_j=.5*m*(length*omega)**2,
                potential_j=m*g*height,thermal_j=d,period_small_s=math.tau*math.sqrt(length/g),period_measured_s=self.period,
                acceleration_m_s2=-g*math.sin(angle)-p['damping']*omega/(m*length))
        elif self.lab=='lever':
            left=m*g*p['arm1']; right=p['mass2']*g*p['arm2']
            result.update(position_m=p['arm1'],velocity_m_s=0.,torque_left_nm=left,torque_right_nm=right,
                torque_net_nm=left-right,reaction_n=(m+p['mass2'])*g)
        elif self.lab=='pulley':
            force=m*g/p['strands']; height=p['pull']/p['strands']
            result.update(position_m=p['pull'],velocity_m_s=0.,height_m=height,required_n=force,
                work_j=force*p['pull'],potential_j=m*g*height,advantage=p['strands'])
        result['energy']=result['kinetic_j']+result['potential_j']
        result['balance_j']=result['energy']+result['thermal_j']-getattr(self,'initial_energy',result['energy'])-result['work_j']
        return result

    def _record(self): self.samples.append(self.metrics())

    def _check_goal(self):
        if not self.challenge or self.achieved: return
        p=self.params; v=self.metrics(); e=self.engine; limits=self.catalog['goals']; goal=False
        if self.lab=='forces': goal=self.initial_params['position0']<limits['forces_min_position_m'] and limits['forces_min_position_m']<=v['position_m']<=limits['forces_max_position_m'] and abs(v['velocity_m_s'])<=e['settle_speed_m_s'] and self.time>=e['min_challenge_time_s']
        elif self.lab=='incline': goal=v['height_m']-self.initial_params['position0']*math.sin(math.radians(p['angle']))>=limits['incline_height_m'] and 0<p['force']<=limits['incline_max_force_n']
        elif self.lab=='projectile': goal=self.landed and v['target_error_m']<=e['target_tolerance_m']
        elif self.lab=='collision': goal=self.collided
        elif self.lab=='spring':
            goal=abs(self.q[0])<=e['settle_displacement_m'] and abs(self.q[1])<=e['settle_speed_m_s'] and abs(self.initial_params['displacement'])>=limits['spring_min_initial_m']
            if goal and self.goal_since is None: self.goal_since=self.time
            if not goal: self.goal_since=None
            goal=goal and self.time-self.goal_since>=e['challenge_hold_s'] and self.time<=limits['spring_deadline_s']
        elif self.lab=='pendulum': goal=self.period is not None and abs(self.period-2)<=limits['pendulum_tolerance_s'] and abs(self.initial_params['angle'])>=limits['pendulum_min_angle_deg']
        elif self.lab=='lever': goal=abs(v['torque_net_nm'])<=e['balance_tolerance_nm'] and p['mass']!=p['mass2']
        elif self.lab=='pulley': goal=v['height_m']>=limits['pulley_height_m'] and v['required_n']<=limits['pulley_max_force_n']
        if goal:
            self.achieved=True; self.message='Đạt điều kiện đo • Lưu A, thay một thông số rồi giải thích khác biệt'
            self.running=False

    def configuration(self): return {'schema':self.schema,'catalog_hash':self.catalog_hash,'lab':self.lab,'params':self.params.copy(),'challenge':self.challenge}

    def snapshot(self):
        return {'configuration':self.configuration(),'initial_params':self.initial_params.copy(),
                'inputs':copy.deepcopy(self.inputs),'samples':list(self.samples),'final':self.metrics(),
                'prediction':self.prediction,'achieved':self.achieved,'finished':self.finished,'landed':self.landed,
                'model':{'assumptions':self.spec['assumptions'],'formula':self.spec['formula'],
                    'engine':self.engine,'sources':self.catalog['sources']}}

    def keep_reference(self):
        self.reference=copy.deepcopy(self.snapshot()); self.message='Đã giữ lượt A • Đặt lại để chạy B'; self.revision+=1

    def comparison(self):
        if self.reference is None: return None
        before=self.reference['configuration']['params']
        changed=[self.spec['params'][k][0] for k,v in self.params.items() if not math.isclose(v,before[k],abs_tol=self.engine['comparison_tolerance']) or not math.isclose(self.initial_params[k],self.reference['initial_params'][k],abs_tol=self.engine['comparison_tolerance'])]
        return {'changed':changed,'time_a_s':self.reference['final']['time_s'],'time_b_s':self.time,
                'delta_position_m':self.metrics()['position_m']-self.reference['final']['position_m'],
                'live_inputs_differ':self.inputs!=self.reference['inputs'],
                'same_duration':math.isclose(self.time,self.reference['final']['time_s'],abs_tol=self.engine['fixed_dt_s'])}

    def save(self,path):
        path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(self.configuration(),ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

    def load(self,path):
        path=Path(path)
        if path.stat().st_size>self.engine['max_file_bytes']: raise ValueError('Physics file too large')
        data=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data,dict) or type(data.get('schema')) is not int or data.get('schema')!=self.schema or not isinstance(data.get('lab'),str) or data.get('lab') not in self.catalog['labs'] or data.get('catalog_hash',self.catalog_hash)!=self.catalog_hash:
            raise ValueError('Invalid physics setup')
        params=data.get('params'); spec=self.catalog['labs'][data['lab']]['params']
        if not isinstance(params,dict) or set(params)!=set(spec) or not isinstance(data.get('challenge',False),bool): raise ValueError('Invalid physics setup')
        for key,value in params.items():
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not spec[key][2]<=value<=spec[key][3]: raise ValueError('Invalid physics value')
        if params.get('mu_k',0)>params.get('mu_s',1) or ('strands' in params and not float(params['strands']).is_integer()): raise ValueError('Invalid physics constraint')
        self.choose(data['lab']); self.params={k:float(v) for k,v in params.items()}; self.challenge=data.get('challenge',False); self.reset()

    def export(self,folder):
        folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
        data=self.snapshot(); data['reference']=self.reference
        (folder/'experiment.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
        rows=list(self.samples)
        if not rows or rows[-1]['time_s']!=self.time: rows.append(self.metrics())
        output=io.StringIO(newline=''); writer=csv.DictWriter(output,fieldnames=list(rows[-1]))
        writer.writeheader(); writer.writerows(rows)
        (folder/'measurements.csv').write_text(output.getvalue(),encoding='utf-8-sig')
        return folder

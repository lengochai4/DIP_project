"""Camera-composited mechanics, explicit handles and cached learning panels."""
import math
import json
from pathlib import Path
import time
import numpy as np
import pygame
from OpenGL import GL as gl,GLU as glu
from .camera_space import CameraSpace,CameraCover
from .geometry import bone_transforms
from .physics import PhysicsLab
from .physics_input import PhysicsInput
from .theme import ACCENT,GOLD,INK,MUTED,glass


MEASUREMENTS={
    'position_m':('Vị trí','m'),'height_m':('Độ cao','m'),
    'velocity_m_s':('Vận tốc','m/s'),'acceleration_m_s2':('Gia tốc','m/s²'),
    'kinetic_j':('Động năng','J'),'potential_j':('Thế năng','J'),
    'thermal_j':('Tiêu hao','J'),'work_j':('Công lực kéo','J'),
    'momentum_kg_m_s':('Động lượng','kg·m/s'),'period_measured_s':('Chu kỳ đo','s'),
    'period_small_s':('T góc nhỏ / lý tưởng','s'),'torque_net_nm':('Mômen tổng','N·m'),
    'required_n':('Lực kéo cần','N'),'target_error_m':('Lệch đích','m')}


class PhysicsView:
    def __init__(self,settings,renderer):
        self.settings=settings; self.renderer=renderer; self.model=PhysicsLab()
        self.cfg=self.model.catalog['view']; self.input=PhysicsInput(settings,self)
        self.space=CameraSpace(4/3); self.content=(0,0,960,640)
        self.page='adjust'; self.param_page=0; self.library=False; self.collapsed=False
        self.tool='edit'
        self.panel_scale=1.; self.panel_offset=np.zeros(2); self.zoom=1.
        self.dock_edge='left'; self.dock_position=.25; self.dock_pending=None; self.edit_bounds=None
        self.yaw=self.cfg['default_yaw_deg']; self.pitch=self.cfg['default_pitch_deg']; self.flags={'vectors':True,'trace':True,'energy':False,'graph':False,'measure':True}
        self.graph='position_m'; self.targets=[]; self.handles=[]; self.cursor_points={}
        self.textures={}; self.fonts={}; self.identity=None; self.run_id=None; self.geometry=None
        self.mouse_claim=None; self.last_ui=-math.inf; self.ui_dirty=True
        self.measure_points=None; self.object_labels=[]; self.press_cursors=set()
        self.cursor_generations={}
        self.root=Path(__file__).resolve().parents[2]/'runs/ui-physics'
        self.layout(); self.setup_projection()

    @property
    def page_key(self): return f'{self.model.lab}/{self.page}/{self.param_page}/{self.library}/{self.collapsed}/{getattr(self,"library_page",0)}/{getattr(self,"tools_page",0)}/{self.tool}'

    def open(self):
        self.textures={}; self.camera_key=None; self.last_ui=-math.inf; self.ui_dirty=True

    def close(self):
        if self.textures: gl.glDeleteTextures([v['id'] for v in self.textures.values()])
        self.textures.clear()
        self.input.release(); self.mouse_claim=None; self.identity=None; self.cursor_points.clear(); self.press_cursors.clear()

    def suspend(self):
        self.input.release(); self.mouse_claim=None; self.identity=None; self.cursor_points.clear(); self.press_cursors.clear()
        self.model.running=False; self.model.accumulator=0.

    def pause_edit(self):
        self.model.running=False; self.model.accumulator=0.
        self.model.message='Đang điều chỉnh • Chọn Chạy để bắt đầu'

    def command(self,action):
        m=self.model; self.ui_dirty=True; self.panel_force=True
        if action.startswith('lab:'):
            self.tool='edit'
            m.choose(action.split(':',1)[1]); self.library=False; self.param_page=0; self.input.aims.clear(); self.measure_points=None; self.edit_bounds=None
        elif action=='library': self.library=not self.library
        elif action.startswith('page:'): self.page=action.split(':')[1]; self.library=False
        elif action=='run':
            if self.input.claims or self.mouse_claim:
                m.message='Buông tay nắm trước khi chạy'; return
            self.edit_bounds=None
            self.tool='edit'
            m.toggle()
            if m.static: m._check_goal()
        elif action=='step':
            if self.input.claims or self.mouse_claim:
                m.message='Buông tay nắm trước khi tiến bước'; return
            m.running=False; m.step()
        elif action=='reset': m.reset(); self.edit_bounds=None; self.tool='edit'
        elif action=='slow': m.speed=.25 if m.speed==1 else 1.
        elif action=='param_next': self.param_page=(self.param_page+1)%self.page_count
        elif action=='param_prev': self.param_page=(self.param_page-1)%self.page_count
        elif action in ('library_prev','library_next'):
            capacity=max(1,self.body_rect.h//31); pages=math.ceil(8/capacity)
            self.library_page=(getattr(self,'library_page',0)+(1 if action.endswith('next') else -1))%pages
        elif action in ('tools_prev','tools_next'):
            self.tools_page=(getattr(self,'tools_page',0)+(1 if action.endswith('next') else -1))%self.tools_pages
        elif action in ('lesson_prev','lesson_next'):
            self.lesson_page=(getattr(self,'lesson_page',0)+(1 if action.endswith('next') else -1))%self.lesson_pages
        elif action.startswith(('inc:','dec:')):
            kind,key=action.split(':'); m.set_parameter(key,m.params[key]+m.spec['params'][key][4]*(1 if kind=='inc' else -1))
        elif action.startswith('flag:'):
            flag=action.split(':')[1]; self.flags[flag]=not self.flags[flag]
        elif action=='graph_next':
            fields=['position_m','velocity_m_s','kinetic_j','potential_j','thermal_j']
            self.graph=fields[(fields.index(self.graph)+1)%len(fields)]
        elif action=='challenge':
            m.challenge=not m.challenge; m.reset()
            if m.challenge and m.lab=='lever': m.set_parameter('arm2',1.8)
        elif action.startswith('predict:'):
            if m.time==0 and not m.running and not m.achieved:
                m.prediction=action.split(':')[1]; m.message='Đã ghi dự đoán • Chạy/kiểm tra để đối chiếu'
        elif action=='keep': m.keep_reference()
        elif action=='clear_trace': m.samples.clear(); m._record()
        elif action=='view':
            self.input.release(); self.mouse_claim=None
            self.yaw=0. if self.yaw else self.cfg['default_yaw_deg']
            self.pitch=self.cfg['default_pitch_deg'] if self.yaw else 0.
        elif action in ('panel_larger','panel_smaller'):
            self.panel_scale=float(np.clip(self.panel_scale*(self.cfg['zoom_factor'] if action=='panel_larger' else 1/self.cfg['zoom_factor']),self.cfg['min_panel_scale'],self.cfg['max_panel_scale']))
        elif action in ('zoom_in','zoom_out'):
            self.zoom=float(np.clip(self.zoom*(self.cfg['zoom_factor'] if action=='zoom_in' else 1/self.cfg['zoom_factor']),self.cfg['min_scene_zoom'],self.cfg['max_scene_zoom']))
        elif action=='frame':
            self.input.release(); self.mouse_claim=None; self.zoom=1.; self.panel_offset[:]=0
            self.yaw=self.cfg['default_yaw_deg']; self.pitch=self.cfg['default_pitch_deg']; self.edit_bounds=None
            self.tool='edit'
        elif action.startswith('tool:'):
            tool=action.split(':')[1]
            if tool not in ('edit','orbit','zoom'): return
            # Keep the menu selector consumed; its closing pinch must not turn
            # into a view grab behind the newly selected tool.
            self.input.claims.clear(); self.input.gates.clear(); self.input.aims.clear(); self.mouse_claim=None
            self.tool='edit' if tool==self.tool else tool
            m.message=('Đã chọn Chỉnh vật • Chụm vào điểm vàng để chỉnh' if self.tool=='edit' else
                       'Đã chọn '+{'orbit':'Xoay cảnh','zoom':'Đổi cỡ cảnh'}[self.tool]+' • Mở rõ cái–trỏ rồi chụm trong vùng camera')
        elif action=='compact': self.collapsed=True
        elif action=='restore': self.collapsed=False
        elif action in ('save','load','export'):
            try:
                if action=='save': m.save(self.root/'setup.json'); m.message='Đã lưu thiết lập tại runs/ui-physics/setup.json'
                elif action=='load': m.load(self.root/'setup.json'); self.param_page=0; m.message='Đã mở thiết lập • Chọn Chạy để thử'
                else:
                    folder=m.export(self.root/f'{m.lab}-{time.time_ns()}')
                    (folder/'view.json').write_text(json.dumps({'kind':'simulated_si_measurement','flags':self.flags,
                        'measurement_points_m':None if self.measure_points is None else [v.tolist() for v in self.measure_points],
                        'measurement_distance_m':None if self.measure_points is None else float(np.linalg.norm(self.measure_points[1]-self.measure_points[0]))},ensure_ascii=False,indent=2),encoding='utf-8')
                    self.renderer.screenshot(folder/'view.png'); m.message='Đã xuất JSON, CSV và ảnh vào runs/ui-physics'
            except (OSError,ValueError,TypeError,KeyError) as exc:
                m.message='Không thể mở/lưu dữ liệu • Kiểm tra tệp và quyền thư mục'

    def layout(self):
        w,h=self.content[2:]; width=min(320,max(204,round(w*.36*self.panel_scale)))
        width=min(width,w-180); height=h-24
        origin=np.array((12.,12.))+self.panel_offset*np.array((w,h))
        origin=np.clip(origin,(4,4),(max(4,w-width-4),max(4,h-height-4)))
        self.panel_offset=(origin-np.array((12.,12.)))/np.array((w,h))
        self.panel_rect=pygame.Rect(*origin,width,height)
        if self.collapsed:
            edge=self.dock_edge; along=self.dock_position
            if edge in ('left','right'):
                self.panel_rect=pygame.Rect(4 if edge=='left' else w-42,round(np.clip(h*along-23,4,h-50)),38,46)
            else:
                self.panel_rect=pygame.Rect(round(np.clip(w*along-23,4,w-50)),4 if edge=='top' else h-42,46,38)
        self.rows=max(1,min(7,(height-(86 if height<290 else 114)-88)//44))
        self.page_count=max(1,math.ceil(len(self.model.params)/self.rows))
        self.param_page%=self.page_count
        self.stage=pygame.Rect(12 if self.collapsed else width+28,14,w-(24 if self.collapsed else width+42),h-28)

    def _font(self,size):
        size=max(10,int(size))
        if size not in self.fonts:
            path=Path('C:/Windows/Fonts/segoeui.ttf')
            self.fonts[size]=pygame.font.Font(str(path) if path.is_file() else None,size)
        return self.fonts[size]

    def _text(self,surface,value,pos,size=14,color=INK,width=None):
        value=str(value); font=self._font(size)
        if width:
            words=value.split(); lines=[]; line=''
            for word in words:
                if line and font.size(line+' '+word)[0]>width: lines.append(line); line=word
                else: line=(line+' '+word).strip()
            lines.append(line)
        else: lines=[value]
        x,y=pos
        for line in lines:
            surface.blit(font.render(line,True,color),(round(x),round(y))); y+=font.get_linesize()
        return y

    def _button(self,surface,label,rect,action,on=False):
        rect=pygame.Rect(rect); surface.blit(glass(rect.size,242,8,on,1),rect)
        pygame.draw.rect(surface,ACCENT if on else (91,134,154),rect,1,border_radius=8)
        font=next((self._font(n) for n in (14,13,12,11) if self._font(n).size(label)[0]<rect.w-8),self._font(10))
        while label and font.size(label)[0]>rect.w-6: label=label[:-2]+'…' if len(label)>2 else ''
        glyph=font.render(label,True,INK); surface.blit(glyph,glyph.get_rect(center=rect.center))
        target=rect.move(self.panel_rect.topleft); self.targets.append((target,action))

    def _paint_panel(self):
        r=self.panel_rect; w,h=r.size; m=self.model
        self.targets=[]
        surface=glass((w,h),238,16,True,1).copy()
        if self.collapsed:
            self._button(surface,{'left':'›','right':'‹','top':'↓','bottom':'↑'}[self.dock_edge],(2,2,w-4,h-4),'restore'); return surface
        small=h<290
        self._text(surface,'VẬT LÝ • '+('THỬ THÁCH' if m.challenge else 'KHÁM PHÁ'),(12,3 if small else 10),11 if small else 12,ACCENT)
        self.targets.append((pygame.Rect(r.x+8,r.y+2,w-62,18 if small else 28),'drag:panel'))
        self._button(surface,'−',(w-38,2,28,18 if small else 26),'compact')
        self._button(surface,m.spec['title']+' v',(10,24 if small else 37,w-20,26 if small else 34),'library',self.library)
        for n,(label,page) in enumerate((('Điều chỉnh','adjust'),('Đo / Lưu','tools'),('Bài học','lesson'))):
            bw=(w-24)//3; self._button(surface,label,(10+n*(bw+2),56 if small else 78,bw,24 if small else 28),'page:'+page,self.page==page)
        body=pygame.Rect(10,86 if small else 114,w-20,max(28,h-(86 if small else 114)-88)); self.body_rect=body
        previous=surface.get_clip(); surface.set_clip(body)
        if self.library:
            self._paint_library(surface,body)
        elif self.page=='adjust':
            keys=list(m.params)[self.param_page*self.rows:(self.param_page+1)*self.rows]
            for i,key in enumerate(keys):
                name,unit,low,high,step,_=m.spec['params'][key]; value=m.params[key]; y=body.y+i*44
                label=f'{name}: {value:.3g} {unit}'
                self._text(surface,label,(12,y),12,INK)
                self._button(surface,'−',(12,y+20,26,20),'dec:'+key)
                self._button(surface,'+',(w-38,y+20,26,20),'inc:'+key)
                rail=pygame.Rect(46,y+23,w-92,14)
                pygame.draw.line(surface,(104,151,172),(rail.x,rail.centery),(rail.right,rail.centery),3)
                px=rail.x+(value-low)/(high-low)*rail.w
                pygame.draw.circle(surface,GOLD,(round(px),rail.centery),6)
                self.targets.append((rail.inflate(4,10).move(r.topleft),'drag:param:'+key))
        elif self.page=='tools': self._paint_tools(surface,body)
        else: self._paint_lesson(surface,body)
        surface.set_clip(previous)
        if self.library:
            pages=max(1,math.ceil(8/max(1,body.h//31))); self.library_page=getattr(self,'library_page',0)%pages
            self._button(surface,'‹',(10,h-81,34,25),'library_prev')
            self._text(surface,f'{self.library_page+1}/{pages}',(w//2-15,h-78),12,MUTED)
            self._button(surface,'›',(w-44,h-81,34,25),'library_next')
        elif self.page=='adjust':
            self._button(surface,'‹',(10,h-81,34,25),'param_prev')
            self._text(surface,f'Thông số {self.param_page+1}/{self.page_count}',(50,h-78),12,MUTED)
            self._button(surface,'›',(w-44,h-81,34,25),'param_next')
        elif self.page=='lesson':
            self._button(surface,'‹',(10,h-81,25,25),'lesson_prev')
            self._button(surface,('Đạt' if m.achieved else 'Thử thách')+f' {getattr(self,"lesson_page",0)+1}/{self.lesson_pages}',(39,h-81,w-78,25),'challenge',m.challenge)
            self._button(surface,'›',(w-35,h-81,25,25),'lesson_next')
        else:
            self._button(surface,'‹ Công cụ',(10,h-81,(w-24)//2,25),'tools_prev')
            self._button(surface,'Công cụ ›',(14+(w-24)//2,h-81,(w-24)//2,25),'tools_next')
        labels=(('Kiểm tra' if m.static else 'Dừng' if m.running else 'Chạy','run'),('Đặt lại','reset'),('¼×' if m.speed!=1 else '1×','slow'))
        bw=(w-28)//3
        for i,(label,action) in enumerate(labels): self._button(surface,label,(10+i*(bw+4),h-45,bw,32),action,m.running if action=='run' else m.speed!=1 if action=='slow' else False)
        # Body clipping also constrains invisible controls' interactive targets.
        self.targets=[(a,b) for a,b in self.targets if r.contains(a)]
        return surface

    def _paint_library(self,surface,body):
        capacity=max(1,body.h//31); pages=math.ceil(8/capacity)
        self.library_page=getattr(self,'library_page',0)%pages
        items=list(self.model.catalog['labs'].items())[self.library_page*capacity:(self.library_page+1)*capacity]
        for i,(key,spec) in enumerate(items): self._button(surface,spec['title'],(10,body.y+i*31,body.w,27),'lab:'+key,key==self.model.lab)

    def _paint_tools(self,surface,body):
        actions=[('Xoay cảnh','tool:orbit'),('Đổi cỡ cảnh','tool:zoom'),('Chỉnh vật','tool:edit'),
                 ('Vector','flag:vectors'),('Quỹ đạo','flag:trace'),('Năng lượng','flag:energy'),('Đồ thị','flag:graph'),
                 ('Đo đạc','flag:measure'),('Góc nhìn','view'),('Một bước','step'),('Giữ lượt A','keep'),
                 ('Lưu thiết lập','save'),('Mở thiết lập','load'),('Xuất CSV/ảnh','export'),('Xóa vết','clear_trace'),('Đổi đồ thị','graph_next'),
                 ('Dự đoán: đạt','predict:yes'),('Dự đoán: chưa','predict:no'),('Bảng lớn +','panel_larger'),('Bảng nhỏ −','panel_smaller'),
                 ('Cảnh gần +','zoom_in'),('Cảnh xa −','zoom_out')]
        capacity=max(2,(body.h//31)*2); pages=math.ceil(len(actions)/capacity)
        self.tools_page=getattr(self,'tools_page',0)%pages
        visible=capacity
        pages=math.ceil(len(actions)/visible); self.tools_page%=pages
        items=actions[self.tools_page*visible:(self.tools_page+1)*visible]
        bw=(body.w-4)//2
        for n,(label,action) in enumerate(items):
            on=(self.tool==action.split(':')[-1]) if action.startswith('tool:') else self.flags.get(action.split(':')[-1],False)
            self._button(surface,label,(10+(bw+4)*(n%2),body.y+(n//2)*31,bw,27),action,on)
        self.tools_pages=pages

    def _paint_lesson(self,surface,body):
        parts=[self.model.spec[k] for k in ('application','assumptions','formula')]
        parts+=['Độ dài, lực và vận tốc là giá trị mô phỏng SI; không phải số đo tay trong camera.',
                'Chụm để cầm, di cả bàn tay để kéo; mở ngón để dừng. Kéo tiêu đề ra ngoài viền để thu, chọn mũi tên để mở. Đo/Lưu: chọn Xoay cảnh hoặc Đổi cỡ cảnh, mở ngón rồi chụm trong vùng camera để kéo. Chọn Chỉnh vật để quay lại; R khôi phục khung nhìn. Góc xoay có giới hạn để tránh nhìn cạnh mặt phẳng bài học.',
                'Vector: lực kéo vàng, ma sát đỏ, phản lực/lực căng xanh lam, trọng lực tím, vận tốc xanh lá, gia tốc trắng. Độ dài mũi tên được giới hạn để dễ quan sát.',
                self.model.spec['challenge'],'Đo/Lưu: ghi dự đoán trước lượt chạy. Giữ A, đổi một thông số, đặt lại và chạy B; đối chiếu cùng thời điểm.']
        font=self._font(12); lines=[]
        for part in parts:
            line=''
            for word in part.split():
                if line and font.size(line+' '+word)[0]>body.w-4: lines.append(line); line=word
                else: line=(line+' '+word).strip()
            if line: lines.append(line)
        capacity=max(1,body.h//font.get_linesize()); self.lesson_pages=max(1,math.ceil(len(lines)/capacity))
        self.lesson_page=getattr(self,'lesson_page',0)%self.lesson_pages
        self.visible_lesson_lines=lines[self.lesson_page*capacity:(self.lesson_page+1)*capacity]
        for i,line in enumerate(self.visible_lesson_lines): self._text(surface,line,(12,body.y+i*font.get_linesize()),12,INK)

    def hit(self,point):
        px,py=point[0]*self.content[2],point[1]*self.content[3]
        for rect,action in reversed(self.targets):
            if rect.collidepoint(px,py): return action
        if not self.collapsed and self.panel_rect.collidepoint(px,py): return None
        if self.tool in ('orbit','zoom'):
            return 'drag:'+self.tool if 0<=point[0]<=1 and 0<=point[1]<=1 else None
        nearby=[]
        for order,(position,action) in enumerate(self.handles):
            projected=self.space.project(position)
            if projected:
                distance=math.hypot((point[0]-projected[0])*self.content[2],(point[1]-projected[1])*self.content[3])
                if distance<=self.cfg['handle_radius_px']: nearby.append((distance,-order,action))
        return min(nearby)[2] if nearby else None

    def capture(self,action):
        if action=='drag:panel':
            self.dock_pending=None
            return self.panel_offset.copy()
        if action in ('drag:orbit','drag:zoom'): return (self.yaw,self.pitch,self.zoom)
        self.edit_bounds=tuple(v.copy() for v in self.bounds)
        if action.startswith('drag:measure_'):
            return {'point':self.measure_points[0 if action.endswith('a') else 1].copy(),
                    'projection':(self.origin.copy(),self.rotation.copy(),self.mid.copy(),self.scale,self.space)}
        value=self.model.params.copy(); m=self.model
        value['_body']=self.body_position().copy()
        value['_projection']=(self.origin.copy(),self.rotation.copy(),self.mid.copy(),self.scale,self.space)
        if action=='drag:body':
            if m.lab in ('forces','incline'): value['position0']=m.q[0]
            elif m.lab=='spring': value['displacement']=m.q[0]
            elif m.lab=='pendulum': value['angle']=math.degrees(m.q[0])
            elif m.lab=='projectile': value['height']=m.q[1]
        return value

    def drag(self,action,origin,point,value):
        self.ui_dirty=True; m=self.model
        dx,dy=np.array(point)-origin
        if action=='drag:orbit':
            self.yaw=float(np.clip(value[0]+dx*self.settings['physics_orbit_gain_deg'],-self.settings['physics_yaw_limit_deg'],self.settings['physics_yaw_limit_deg']))
            self.pitch=float(np.clip(value[1]+dy*self.settings['physics_orbit_gain_deg'],-self.settings['physics_pitch_limit_deg'],self.settings['physics_pitch_limit_deg']))
            return
        if action=='drag:zoom':
            self.zoom=float(np.clip(value[2]*math.exp(float(np.clip(-dy*self.settings['physics_zoom_drag_gain'],-10,10))),self.cfg['min_scene_zoom'],self.cfg['max_scene_zoom']))
            return
        if action=='drag:panel':
            self.panel_offset=value+np.array(point)-origin
            # Inspect the requested rectangle before clipping. A full-height
            # panel touches top/bottom at rest, so mere border contact is not intent.
            w,h=self.content[2:]; x,y=np.array((12.,12.))+self.panel_offset*np.array((w,h))
            borders=np.array((x/w,(w-x-self.panel_rect.w)/w,y/h,(h-y-self.panel_rect.h)/h))
            index=int(np.argmin(borders)); now=time.perf_counter()
            if borders[index]<=-self.settings['physics_panel_dock_edge']:
                if self.dock_pending is None or self.dock_pending[0]!=index: self.dock_pending=(index,now)
                if borders[index]<=-self.settings['physics_panel_throw_edge'] or now-self.dock_pending[1]>=self.settings['physics_panel_dock_s']:
                    self.dock_edge=('left','right','top','bottom')[index]
                    self.dock_position=float(np.clip((y+self.panel_rect.h/2)/h if index<2 else (x+self.panel_rect.w/2)/w,0,1))
                    self.collapsed=True; self.mouse_claim=None; self.dock_pending=None
                    return False  # Keep the hand claim consumed until release.
            else: self.dock_pending=None
            return
        if action.startswith('drag:measure_'):
            a=self.to_model(origin,value['projection']); b=self.to_model(point,value['projection'])
            if a is not None and b is not None:
                self.measure_points[0 if action.endswith('a') else 1]=value['point']+b-a
            return
        if action.startswith('drag:param:'):
            key=action.split(':')[-1]; spec=m.spec['params'][key]
            rail_width=max(20,self.panel_rect.w-92)/self.content[2]
            m.set_parameter(key,value[key]+dx/rail_width*(spec[3]-spec[2])); return
        a=self.to_model(origin,value['_projection']); b=self.to_model(point,value['_projection'])
        if a is None or b is None: return  # No unstable near-parallel plane edit.
        delta=b-a
        if action=='drag:body':
            key={'forces':'position0','incline':'position0','projectile':'height','spring':'displacement',
                 'pendulum':'angle','lever':'arm1','pulley':'pull','collision':'velocity1'}[m.lab]
            if m.lab=='pendulum':
                q=value['_body']+delta; top=np.array((0.,value['length']))
                new=math.degrees(math.atan2(q[0]-top[0],top[1]-q[1]))
            elif m.lab=='lever': new=value[key]-delta[0]
            elif m.lab=='projectile': new=value[key]+delta[1]
            elif m.lab=='pulley': new=value[key]+delta[1]*m.params['strands']
            elif m.lab=='collision': new=value[key]+delta[0]
            elif m.lab=='incline': new=value[key]+float(np.dot(delta,(math.cos(math.radians(value['angle'])),math.sin(math.radians(value['angle'])))))
            else: new=value[key]+delta[0]
            m.set_parameter(key,new)
        elif action=='drag:launch':
            angle=math.radians(value['angle']); vector=np.array((math.cos(angle),math.sin(angle)))*value['speed']+delta*self.cfg['launch_drag_gain']
            vector=np.maximum(vector,0.)
            m.set_parameter('angle',math.degrees(math.atan2(vector[1],vector[0])))
            m.set_parameter('speed',float(np.linalg.norm(vector)))
        elif action=='drag:force': m.set_parameter('force',value['force']+delta[0]*self.cfg['force_drag_gain'])
        elif action=='drag:angle': m.set_parameter('angle',value['angle']-dy*self.cfg['angle_drag_gain_deg'])
        elif action=='drag:length': m.set_parameter('length',value['length']-delta[1])
        elif action=='drag:right': m.set_parameter('arm2',value['arm2']+delta[0])
        elif action=='drag:velocity2': m.set_parameter('velocity2',value['velocity2']+delta[0])
        elif action=='drag:rope': m.set_parameter('pull',value['pull']-delta[1])

    def mouse(self,kind,pos):
        x,y,w,h=self.content; point=((pos[0]-x)/w,(pos[1]-y)/h)
        if kind=='down':
            action=self.hit(point)
            if action and action.startswith('drag:'):
                if self.input.claims: return
                self.input.release(); self.pause_edit(); self.mouse_claim=(action,point,self.capture(action))
            elif action:
                self.input.release(); self.command(action)
        elif kind=='up': self.mouse_claim=None
        elif self.mouse_claim: self.drag(self.mouse_claim[0],self.mouse_claim[1],point,self.mouse_claim[2])

    def wheel(self,amount,pos):
        x,y,w,h=self.content; px,py=pos[0]-x,pos[1]-y
        if not (0<=px<w and 0<=py<h): return
        if self.panel_rect.collidepoint(px,py): self.panel_scale=float(np.clip(self.panel_scale*math.exp(amount*self.cfg['wheel_gain']),self.cfg['min_panel_scale'],self.cfg['max_panel_scale']))
        else: self.zoom=float(np.clip(self.zoom*math.exp(amount*self.cfg['wheel_gain']),self.cfg['min_scene_zoom'],self.cfg['max_scene_zoom']))
        self.input.release(); self.mouse_claim=None; self.ui_dirty=True

    def body_position(self):
        m=self.model; p=m.params; q=m.q
        if m.lab=='incline': a=math.radians(p['angle']); return np.array((q[0]*math.cos(a),q[0]*math.sin(a)))
        if m.lab=='projectile': return np.array(q[:2])
        if m.lab=='pendulum': return np.array((p['length']*math.sin(q[0]),p['length']*(1-math.cos(q[0]))))
        if m.lab=='lever': return np.array((-p['arm1'],0.))
        if m.lab=='pulley': return np.array((0.,p['pull']/p['strands']))
        return np.array((q[0],0.))

    def setup_projection(self):
        m=self.model; p=m.params; body=self.body_position()
        if m.lab=='projectile':
            angle=math.radians(p['angle']); vx=p['speed']*math.cos(angle); vy=p['speed']*math.sin(angle)
            duration=(vy+math.sqrt(vy*vy+2*p['gravity']*p['height']))/p['gravity']
            low=np.array((-.5,-.25)); high=np.array((max(2,p['target']+1,vx*duration+1),max(2,p['height']+vy*vy/(2*p['gravity'])+1)))
        elif m.lab=='pendulum': low=np.array((-p['length']-1,-.5)); high=np.array((p['length']+1,p['length']+1))
        elif m.lab=='lever': low=np.array((-3.6,-1)); high=np.array((3.6,1.5))
        elif m.lab=='pulley': low=np.array((-2.,-.5)); high=np.array((2.,10.))
        elif m.lab=='spring': low=np.array((-2.5,-1.)); high=np.array((2.5,2.))
        else:
            low=np.array((min(-2.5,body[0]-1),min(-1.,body[1]-1)))
            high=np.array((max(5.,body[0]+1),max(3.,body[1]+1)))
            if m.lab=='collision': low[0]=min(low[0],m.q[1]-1); high[0]=max(high[0],m.q[1]+1)
        if self.edit_bounds is not None: low,high=self.edit_bounds
        self.bounds=(low,high); self.mid=(low+high)/2
        if self.measure_points is None:
            self.measure_points=[np.array((low[0]+.2*(high[0]-low[0]),-.65)),np.array((low[0]+.45*(high[0]-low[0]),-.65))]
        stage=self.stage; w,h=self.content[2:]
        center=self.space.point(stage.centerx/w,(stage.centery+12)/h,0)
        self.origin=center; a=math.radians(self.yaw)
        yaw=np.array(((math.cos(a),0,math.sin(a)),(0,1,0),(-math.sin(a),0,math.cos(a))))
        b=math.radians(self.pitch); pitch=np.array(((1,0,0),(0,math.cos(b),-math.sin(b)),(0,math.sin(b),math.cos(b))))
        self.rotation=pitch@yaw
        available=np.array((stage.w/w*self.space.width*.82,stage.h/h*self.space.height*.62))
        self.scale=float(min(available/(high-low))*self.zoom)

    def world(self,xy,z=0):
        local=np.array(((xy[0]-self.mid[0])*self.scale,(xy[1]-self.mid[1])*self.scale,z))
        return self.origin+self.rotation@local

    def to_model(self,point,projection=None):
        center,rotation,mid,scale,space=projection or (self.origin,self.rotation,self.mid,self.scale,self.space)
        origin,direction=space.ray(*point); normal=rotation[:,2]; divisor=np.dot(normal,direction)
        if abs(divisor)<self.settings['physics_min_edit_ray_cos']: return None
        t=np.dot(normal,center-origin)/divisor
        if t<=0: return None
        local=rotation.T@(origin+direction*t-center)
        return local[:2]/scale+mid

    def _texture(self,name,surface=None,data=None,key=None):
        item=self.textures.get(name)
        if item is None:
            item={'id':gl.glGenTextures(1),'size':None,'key':None}; self.textures[name]=item
        gl.glBindTexture(gl.GL_TEXTURE_2D,item['id'])
        if key!=item['key']:
            if surface is not None: data=pygame.image.tobytes(surface,'RGBA',False); size=surface.get_size(); fmt=gl.GL_RGBA
            else: size=(data.shape[1],data.shape[0]); fmt=gl.GL_BGR
            gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_MIN_FILTER,gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_MAG_FILTER,gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_WRAP_S,gl.GL_CLAMP_TO_EDGE)
            gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_WRAP_T,gl.GL_CLAMP_TO_EDGE)
            gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT,1)
            if item['size']!=size: gl.glTexImage2D(gl.GL_TEXTURE_2D,0,gl.GL_RGBA,*size,0,fmt,gl.GL_UNSIGNED_BYTE,data)
            else: gl.glTexSubImage2D(gl.GL_TEXTURE_2D,0,0,0,*size,fmt,gl.GL_UNSIGNED_BYTE,data)
            item['size']=size; item['key']=key
        return item['id']

    def _quad(self,rect,uv=((0,0),(1,0),(1,1),(0,1))):
        x,y,w,h=rect; gl.glEnable(gl.GL_TEXTURE_2D); gl.glColor4f(1,1,1,1)
        gl.glBegin(gl.GL_QUADS)
        for (u,v),(a,b) in zip(uv,((x,y),(x+w,y),(x+w,y+h),(x,y+h))): gl.glTexCoord2f(u,v); gl.glVertex2f(a,b)
        gl.glEnd(); gl.glDisable(gl.GL_TEXTURE_2D)

    def _ortho(self):
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glDisable(gl.GL_LIGHTING)
        gl.glMatrixMode(gl.GL_PROJECTION); gl.glLoadIdentity(); gl.glOrtho(0,self.content[2],self.content[3],0,-1,1)
        gl.glMatrixMode(gl.GL_MODELVIEW); gl.glLoadIdentity()
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA,gl.GL_ONE_MINUS_SRC_ALPHA)

    def _sync_panel(self):
        # Translation moves hit rectangles, not text pixels. Upload only when
        # visible content/size changes, once after an edited source observation.
        semantic=(self.page_key,self.panel_rect.size,self.model.running,self.model.speed,
             self.model.challenge,self.model.achieved,tuple(self.flags.items()),self.graph,
             getattr(self,'lesson_page',0),self.dock_edge)
        key=(semantic,tuple(self.model.params.items())); now=time.perf_counter()
        refresh=(semantic!=getattr(self,'panel_semantic',None) or getattr(self,'panel_force',False)
                 or now-getattr(self,'last_panel',-math.inf)>=1/self.cfg['ui_refresh_hz'])
        if 'panel' not in self.textures or (key!=getattr(self,'panel_key',None) and refresh):
            self._texture('panel',self._paint_panel(),key=key); self.panel_key=key
            self.panel_semantic=semantic; self.last_panel=now
        else:
            delta=np.array(self.panel_rect.topleft)-getattr(self,'paint_origin',np.array(self.panel_rect.topleft))
            if np.any(delta): self.targets=[(rect.move(*delta),action) for rect,action in self.targets]
            gl.glBindTexture(gl.GL_TEXTURE_2D,self.textures['panel']['id'])
        self.paint_origin=np.array(self.panel_rect.topleft); self.ui_dirty=False; self.panel_force=False

    def draw(self,snapshot,view,fresh,dt,run_id):
        geometry=(view,snapshot.image.shape[:2] if snapshot is not None else None)
        self.content=view
        if geometry!=self.geometry or run_id!=self.run_id:
            self.input.release(); self.cursor_points.clear(); self.press_cursors.clear(); self.mouse_claim=None; self.identity=None
            self.geometry=geometry; self.run_id=run_id; self.ui_dirty=True
        self.layout(); self.space=CameraSpace(view[2]/view[3],self.settings['world_width'],self.settings['camera_ar_fov_deg'])
        self.setup_projection()
        x,y,w,h=view; gl.glViewport(x,self.renderer.size[1]-y-h,w,h)
        gl.glEnable(gl.GL_SCISSOR_TEST); gl.glScissor(x,self.renderer.size[1]-y-h,w,h)
        self._ortho()
        if snapshot is not None:
            image=snapshot.image[:,::-1] if self.settings['mirror'] else snapshot.image
            self._texture('camera',data=np.ascontiguousarray(image),key=(run_id,snapshot.frame_id))
            cover=CameraCover(image.shape[1]/image.shape[0],self.space.aspect)
            self._quad((0,0,w,h),cover.uv)
        else: cover=CameraCover(4/3,self.space.aspect)
        # A mild tint separates the teaching objects from a busy camera image.
        gl.glColor4f(.025,.06,.09,.32); gl.glBegin(gl.GL_QUADS)
        for point in ((0,0),(w,0),(w,h),(0,h)): gl.glVertex2f(*point)
        gl.glEnd()
        now=time.perf_counter()
        self._sync_panel()
        identity=(run_id,snapshot.frame_id) if fresh else None
        if fresh and identity!=self.identity and self.mouse_claim is None:
            hands=tuple(cover.hand(hand) for hand in snapshot.hands)
            for hand in hands:
                if self.cursor_generations.get(hand.slot)!=hand.generation: self.cursor_points.pop(hand.slot,None)
            self.cursor_generations={hand.slot:hand.generation for hand in hands}
            self.input.update(hands,snapshot.timestamp_s,self.space.aspect,gesture_hands=snapshot.hands,source_aspect=snapshot.image.shape[1]/snapshot.image.shape[0])
            captured=set()
            for slot,state in self.input.tap.states.items():
                if not state.locked: continue
                captured.add((slot,state.generation))
                if state.phase=='press' and (slot,state.generation) not in self.press_cursors and slot in self.cursor_points:
                    anchor=tuple(self.cursor_points[slot]/np.array((w,h)))
                    if self.hit(anchor)==state.target[1]: state.anchor=anchor; self.input.pointers[slot]=anchor
            self.press_cursors=captured
        elif not fresh and self.identity is not None: self.input.release()
        self.identity=identity
        self.input.advance(dt)
        self.model.advance(max(0,dt))
        if self.ui_dirty:
            previous_stage=self.stage.copy(); self.layout()
            if self.stage!=previous_stage: self.last_ui=-math.inf
        self.setup_projection(); self._draw_world()
        self._ortho()
        self._draw_object_labels()
        self._sync_panel()
        self._quad(self.panel_rect)
        semantic=(self.model.lab,self.model.running,self.model.challenge,self.model.achieved,self.model.prediction,tuple(self.flags.items()),self.graph,self.stage.size,self.renderer.help_visible,id(self.model.reference),self.tool)
        if semantic!=getattr(self,'hud_semantic',None) or now-self.last_ui>=1/self.cfg['ui_refresh_hz'] or 'hud' not in self.textures:
            hud=self._paint_hud(fresh); self._texture('hud',hud,key=now); self.last_ui=now
            self.hud_semantic=semantic
        else: gl.glBindTexture(gl.GL_TEXTURE_2D,self.textures['hud']['id'])
        self._quad((self.stage.x,self.stage.y,self.stage.w,self.stage.h))
        self._draw_cursors(dt)
        gl.glDisable(gl.GL_BLEND); gl.glDisable(gl.GL_SCISSOR_TEST)

    def _line(self,points,color=ACCENT,width=2):
        gl.glDisable(gl.GL_LIGHTING); gl.glColor3f(*(c/255 for c in color)); gl.glLineWidth(width)
        gl.glBegin(gl.GL_LINE_STRIP)
        for point in points: gl.glVertex3fv(point)
        gl.glEnd()

    def _beam(self,a,b,radius=.025,color=ACCENT):
        matrices,lengths=bone_transforms(np.array((a,b)),np.array(((0,1),)))
        if not len(matrices): return
        gl.glEnable(gl.GL_LIGHTING); gl.glColor3f(*(c/255 for c in color)); gl.glPushMatrix()
        gl.glMultMatrixf(matrices[0].T); gl.glScalef(radius,radius,lengths[0]); gl.glCallList(self.renderer.unit_bone); gl.glPopMatrix()

    def _ball(self,point,radius=.12,color=ACCENT):
        gl.glEnable(gl.GL_LIGHTING); gl.glColor3f(*(c/255 for c in color)); gl.glPushMatrix()
        gl.glTranslatef(*point); gl.glScalef(radius,radius,radius); gl.glCallList(self.renderer.unit_sphere); gl.glPopMatrix()

    def _box(self,point,radius=.12,color=ACCENT,angle=0.):
        gl.glEnable(gl.GL_LIGHTING); gl.glColor3f(*(c/255 for c in color)); gl.glPushMatrix()
        gl.glTranslatef(*point)
        matrix=np.eye(4); matrix[:3,:3]=self.rotation
        gl.glMultMatrixf(matrix.T); gl.glRotatef(angle,0,0,1); gl.glScalef(radius,radius,radius)
        vertices=((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))
        for face,normal in (((4,5,6,7),(0,0,1)),((0,3,2,1),(0,0,-1)),((3,7,6,2),(0,1,0)),
                            ((0,1,5,4),(0,-1,0)),((1,2,6,5),(1,0,0)),((0,4,7,3),(-1,0,0))):
            gl.glBegin(gl.GL_QUADS); gl.glNormal3f(*normal)
            for index in face: gl.glVertex3f(*vertices[index])
            gl.glEnd()
        gl.glPopMatrix()

    def _plate(self,start,end,depth=.25):
        side=self.rotation[:,2]*depth; normal=np.cross(end-start,side); normal/=max(1e-10,np.linalg.norm(normal))
        if normal[1]<0: normal=-normal
        gl.glEnable(gl.GL_LIGHTING); gl.glColor3f(.17,.31,.40); gl.glBegin(gl.GL_QUADS); gl.glNormal3fv(normal)
        for point in (start-side,end-side,end+side,start+side): gl.glVertex3fv(point)
        gl.glEnd(); self._line((start-side,end-side,end+side,start+side,start-side),ACCENT,1)

    def _wheel(self,point,radius=.12):
        gl.glEnable(gl.GL_LIGHTING); gl.glColor3f(.8,.69,.4); gl.glPushMatrix(); gl.glTranslatef(*point)
        gl.glScalef(radius,radius,.04); gl.glCallList(self.renderer.unit_sphere); gl.glPopMatrix()
        self._ball(point,.025,ACCENT)

    def _label_at(self,name,point,text): self.object_labels.append((name,point,str(text)))

    def _draw_object_labels(self):
        w,h=self.content[2:]
        for name,point,text in self.object_labels:
            projected=self.space.project(point)
            if projected is None: continue
            item=self.textures.get('label:'+name)
            if item is None or item['key']!=text:
                glyph=self._font(12).render(text,True,INK)
                surface=pygame.Surface((glyph.get_width()+10,glyph.get_height()+6),pygame.SRCALPHA)
                surface.fill((8,22,32,210)); surface.blit(glyph,(5,3)); self._texture('label:'+name,surface,key=text)
            else: gl.glBindTexture(gl.GL_TEXTURE_2D,item['id'])
            tw,th=self.textures['label:'+name]['size']; px,py=projected[0]*w,projected[1]*h
            self._quad((round(px-tw/2),round(py-th-8),tw,th))

    def _handle(self,point,action):
        marker=point+self.rotation[:,2]*.14
        self.handles.append((marker,action)); self._ball(marker,.045,GOLD)

    def _arrow(self,start,vector,color):
        end=start+vector; self._line((start,end),color,3)
        norm=np.linalg.norm(vector)
        if norm<1e-8: return
        side=np.cross(vector/norm,(0,0,1))*.05; base=end-vector/norm*.12
        self._line((base+side,end,base-side),color,2)

    def _draw_world(self):
        m=self.model; p=m.params; body=self.body_position(); self.handles=[]; self.object_labels=[]
        gl.glEnable(gl.GL_DEPTH_TEST); gl.glDisable(gl.GL_BLEND)
        gl.glMatrixMode(gl.GL_PROJECTION); gl.glLoadIdentity(); glu.gluPerspective(self.space.fov,self.space.aspect,.1,100)
        gl.glMatrixMode(gl.GL_MODELVIEW); gl.glLoadIdentity(); gl.glTranslatef(0,0,-self.space.distance)
        gl.glEnable(gl.GL_LIGHT0); gl.glEnable(gl.GL_COLOR_MATERIAL); gl.glEnable(gl.GL_NORMALIZE)
        gl.glLightfv(gl.GL_LIGHT0,gl.GL_POSITION,(2,4,6,1)); gl.glLightfv(gl.GL_LIGHT0,gl.GL_DIFFUSE,(.9,.95,1,1))
        gl.glLightModelfv(gl.GL_LIGHT_MODEL_AMBIENT,(.3,.34,.4,1))
        gl.glMaterialfv(gl.GL_FRONT_AND_BACK,gl.GL_SPECULAR,(.85,.95,1,1)); gl.glMaterialf(gl.GL_FRONT_AND_BACK,gl.GL_SHININESS,80)
        low,high=self.bounds
        for x in np.linspace(low[0],high[0],9): self._line((self.world((x,0),-.35),self.world((x,0),.35)),(67,108,124),1)
        for z in np.linspace(-.35,.35,5): self._line((self.world((low[0],0),z),self.world((high[0],0),z)),(67,108,124),1)
        at=self.world(body)
        radius=self.model.engine['collision_contact_m']*.5*self.scale if m.lab=='collision' else .12
        if m.lab in ('forces','incline','collision','spring','pulley','lever'): self._box(at,radius,color=ACCENT,angle=p.get('angle',0) if m.lab=='incline' else 0)
        else: self._ball(at,.12)
        self._handle(at,'drag:body')
        self._label_at('body',at+(0,.17,0),f"m = {p['mass']:g} kg")
        if m.lab in ('forces','incline'):
            a=math.radians(p.get('angle',0)); axis=self.rotation@np.array((math.cos(a),math.sin(a),0.))
            begin,end=min(-2,m.q[0]-2),max(5,m.q[0]+2)
            offset=self.rotation@np.array((math.sin(a),-math.cos(a),0))*.13
            self._plate(self.world((begin*math.cos(a),begin*math.sin(a)))+offset,self.world((end*math.cos(a),end*math.sin(a)))+offset)
            point=at+axis*.65; self._line((at,point),GOLD); self._handle(point,'drag:force')
            self._label_at('force',point,f"Kéo lực: {p['force']:.2g} N")
            if m.lab=='incline': self._handle(self.world((3*math.cos(a),3*math.sin(a))),'drag:angle')
        elif m.lab=='projectile':
            a=math.radians(p['angle']); tip=at+self.rotation@np.array((math.cos(a),math.sin(a),0.))*.65
            self._line((at,tip),GOLD); self._handle(tip,'drag:launch')
            self._label_at('launch',tip,f"v₀ {p['speed']:.2g} m/s • {p['angle']:.1f}°")
            target=self.world((p['target'],0)); self._line((target+(-.1,0,0),target+(.1,0,0)),GOLD,4)
        elif m.lab=='collision':
            other=self.world((m.q[1],0)); self._box(other,radius,GOLD); self._handle(other,'drag:velocity2')
            self._label_at('body2',other+(0,.17,0),f"m₂ = {p['mass2']:g} kg")
            bottom=-m.engine['collision_contact_m']/2
            self._beam(self.world((low[0],bottom)),self.world((high[0],bottom)),.025)
        elif m.lab=='spring':
            wall=self.world((-2,0)); points=[]
            for n in range(81):
                fraction=n/80; pos=wall+(at-wall)*fraction
                pos[1]+=.07*math.sin(fraction*math.tau*9); pos[2]+=.07*math.cos(fraction*math.tau*9); points.append(pos)
            self._line(points,GOLD,3); self._beam(wall+(0,-.3,0),wall+(0,.3,0),.04)
        elif m.lab=='pendulum':
            top=self.world((0,p['length'])); self._beam(top,at,.015,GOLD)
            self._ball(top,.05,GOLD); self._handle(top,'drag:length')
            self._label_at('length',top,f"L = {p['length']:.2g} m • kéo để đổi dây")
        elif m.lab=='lever':
            left=self.world((-p['arm1'],0)); right=self.world((p['arm2'],0)); middle=self.world((0,0))
            self._beam(left,right,.04,GOLD); self._beam(middle+(0,-.4,0),middle,.065)
            self._box(right,.12,GOLD); self._handle(right,'drag:right')
            self._label_at('body2',right+(0,.17,0),f"m₂ = {p['mass2']:g} kg")
        elif m.lab=='pulley':
            top=max(9,8/p['strands']+1)
            # n independent supporting branches are explicitly shown; the return
            # end uses an ideal reel. No arbitrary pulley-network solver implied.
            count=int(p['strands'])
            for n in range(count):
                dx=(n-(count-1)/2)*.35
                a=self.world((dx,top-.3)); b=self.world((dx,body[1]+.5))
                self._beam(a,b,.012,GOLD); self._wheel(a,.08)
                if n%2==1: self._wheel(self.world((dx-.175,body[1]+.5)),max(.04,self.scale*.175))
            self._beam(self.world((-.2*count,body[1]+.4)),self.world((.2*count,body[1]+.4)),.025)
            self._beam(at,self.world((0,body[1]+.4)),.018,GOLD)
            self._beam(self.world((-.6,top)),self.world((.6,top)),.04)
            rope=self.world((1.3,top-.6-p['pull']))
            self._beam(self.world((.5,top-.3)),self.world((1.3,top-.3)),.012,GOLD)
            self._beam(self.world((1.3,top-.3)),rope,.012,GOLD); self._handle(rope,'drag:rope')
            self._label_at('rope',rope,f"Kéo dây s={p['pull']:.2g} m")
            self._label_at('strands',self.world((0,top)),f"Sơ đồ {count} nhánh đỡ tải • F={m.metrics()['required_n']:.2g} N")
        if self.flags['trace']:
            points=[]
            for row in m.samples:
                if m.lab=='incline': a=math.radians(p['angle']); xy=(row['position_m']*math.cos(a),row['height_m'])
                elif m.lab=='pendulum': xy=(row['position_m'],row['height_m'])
                else: xy=(row['position_m'],row['height_m'] if m.lab in ('projectile','pulley') else 0.)
                points.append(self.world(xy,.015))
            if len(points)>1: self._line(points,ACCENT,2)
        if self.flags['vectors']: self._draw_vectors(at)
        if self.flags['measure']:
            tick=(high[0]-low[0])/6; power=10**math.floor(math.log10(max(tick,1e-9)))
            spacing=next(k*power for k in (1,2,5,10) if k*power>=tick)
            for i,x in enumerate(np.arange(math.ceil(low[0]/spacing)*spacing,high[0],spacing)):
                pos=self.world((x,0),.36)
                self._line((pos,pos+(0,-.04,0)),MUTED,1); self._label_at('tick'+str(i),pos+(0,-.07,0),f'{x:g} m')
            a,b=(self.world(v,.06) for v in self.measure_points)
            self._line((a,b),(167,244,194),2)
            self.handles.extend(((a,'drag:measure_a'),(b,'drag:measure_b')))
            self._ball(a,.045,(167,244,194)); self._ball(b,.045,(167,244,194))
            self._label_at('measure',(a+b)/2+(0,.05,0),f"Thước A–B: {np.linalg.norm(self.measure_points[1]-self.measure_points[0]):.3g} m")

    def _draw_vectors(self,at):
        m=self.model; p=m.params; values=m.metrics(); cfg=self.cfg
        display_limit=self.space.height*self.stage.h/self.content[3]*cfg['vector_stage_fraction']
        length=min(cfg['force_vector_length'],display_limit); limit=cfg['force_vector_max_n']
        if m.lab in ('forces','incline'):
            a=math.radians(p.get('angle',0)); axis=np.array((math.cos(a),math.sin(a),0.))
            normal=np.array((-math.sin(a),math.cos(a),0.))
            for force,direction,color in ((p['force'],axis,GOLD),(values['friction_n'],axis,(252,151,143)),
                    (values['normal_n'],normal,ACCENT),(p['mass']*p['gravity'],np.array((0,-1,0)),(178,165,249))):
                self._arrow(at,self.rotation@direction*np.clip(force/limit,-1,1)*length,color)
        elif m.lab=='spring':
            for key,color in (('spring_n',GOLD),('damping_n',(252,151,143))): self._arrow(at,self.rotation[:,0]*np.clip(values[key]/limit,-1,1)*length,color)
        elif m.lab=='projectile': self._arrow(at,-self.rotation[:,1]*min(1,p['mass']*p['gravity']/limit)*length,(178,165,249))
        elif m.lab=='pendulum':
            angle,omega,_=m.q; tension=values['tension_n']
            self._arrow(at,self.rotation@np.array((-math.sin(angle),math.cos(angle),0))*min(1,tension/limit)*length,ACCENT)
            self._arrow(at,-self.rotation[:,1]*min(1,p['mass']*p['gravity']/limit)*length,(178,165,249))
            self._arrow(at,self.rotation@np.array((math.cos(angle),math.sin(angle),0))*np.clip(values['damping_n']/limit,-1,1)*length,(252,151,143))
        elif m.lab=='pulley':
            weight=p['mass']*p['gravity']; magnitude=min(1,weight/limit)*length
            self._arrow(at,self.rotation[:,1]*magnitude,ACCENT); self._arrow(at,-self.rotation[:,1]*magnitude,(178,165,249))
        elif m.lab=='lever':
            for pos,mass in ((at,p['mass']),(self.world((p['arm2'],0)),p['mass2'])):
                self._arrow(pos,-self.rotation[:,1]*min(1,mass*p['gravity']/limit)*length,(178,165,249))
            self._arrow(self.world((0,0)),self.rotation[:,1]*min(1,values['reaction_n']/limit)*length,ACCENT)
        if m.lab=='projectile': velocity=np.array((values['vx_m_s'],values['vy_m_s'],0.))
        elif m.lab=='pendulum': velocity=np.array((math.cos(m.q[0]),math.sin(m.q[0]),0.))*values['velocity_m_s']
        elif m.lab=='incline':
            angle=math.radians(p['angle']); velocity=np.array((math.cos(angle),math.sin(angle),0.))*values['velocity_m_s']
        else: velocity=np.array((values['velocity_m_s'],0.,0.))
        velocity_length=min(cfg['velocity_vector_length'],display_limit)
        self._arrow(at,self.rotation@velocity/max(cfg['velocity_vector_max_m_s'],float(np.linalg.norm(velocity)))*velocity_length,(146,239,170))
        if m.lab=='collision': self._arrow(self.world((m.q[1],0)),self.rotation[:,0]*np.clip(m.q[3]/cfg['velocity_vector_max_m_s'],-1,1)*velocity_length,(146,239,170))
        acceleration=np.zeros(3)
        if m.lab in ('forces','incline'):
            angle=math.radians(p.get('angle',0)); acceleration=np.array((math.cos(angle),math.sin(angle),0))*values['acceleration_m_s2']
        elif m.lab=='projectile': acceleration=np.array((0.,-p['gravity'],0.))
        elif m.lab=='spring': acceleration[0]=values['acceleration_m_s2']
        elif m.lab=='pendulum':
            angle,omega,_=m.q
            acceleration=np.array((math.cos(angle),math.sin(angle),0))*values['acceleration_m_s2']+np.array((-math.sin(angle),math.cos(angle),0))*p['length']*omega*omega
        self._arrow(at,self.rotation@acceleration/max(cfg['acceleration_vector_max_m_s2'],float(np.linalg.norm(acceleration)))*min(cfg['acceleration_vector_length'],display_limit),INK)

    def measurement_label(self,key):
        specific={
            'pendulum':{'position_m':('Hoành độ x','m'),'velocity_m_s':('Vận tốc tiếp tuyến','m/s'),
                        'acceleration_m_s2':('Gia tốc tiếp tuyến','m/s²'),'period_small_s':('T₀ góc nhỏ, b=0','s')},
            'spring':{'period_small_s':('T₀ riêng, c=0','s')},
            'projectile':{'velocity_m_s':('Tốc độ','m/s'),'acceleration_m_s2':('Gia tốc y','m/s²')},
            'incline':{'position_m':('Vị trí dọc dốc','m'),'velocity_m_s':('Vận tốc dọc dốc','m/s'),
                       'acceleration_m_s2':('Gia tốc dọc dốc','m/s²')},
            'lever':{'position_m':('Cánh tay đòn trái','m')},'pulley':{'position_m':('Dây đã kéo s','m')}}
        return specific.get(self.model.lab,{}).get(key,MEASUREMENTS.get(key))

    def _paint_hud(self,fresh):
        w,h=self.stage.size; surface=pygame.Surface((w,h),pygame.SRCALPHA); m=self.model; values=m.metrics()
        y=self._text(surface,m.spec['title'],(8,0),15 if w<250 else 19,INK,w-16)
        y=self._text(surface,f't = {m.time:.2f} s • '+('Bài tĩnh' if m.static else 'Đang chạy' if m.running else 'Tạm dừng'),(8,y+3),12,ACCENT,w-16)
        if self.tool!='edit':
            text=('XOAY CẢNH • Kéo ngang/dọc' if self.tool=='orbit' else 'ĐỔI CỠ CẢNH • Kéo lên gần / xuống xa')
            y=self._text(surface,text,(8,y+4),12,GOLD,w-16)
            y=self._text(surface,'Mở ngón rồi chụm trong vùng camera để kéo. Chọn Chỉnh vật để quay lại.',(8,y+3),12,INK,w-16)
        if self.tool=='edit' and self.renderer.help_visible and w>=250:
            instruction='Chụm vào điểm vàng để chỉnh • Trỏ nút rồi chụm / giữ 1s'
            y=self._text(surface,instruction,(8,y+4),12,MUTED,w-16)
            if self.page=='lesson':
                hint={'forces':'Kéo vật: đặt vị trí đầu. Kéo F: đổi lực.',
                      'incline':'Kéo đầu dốc: đổi góc. Kéo F: đổi lực.',
                      'projectile':'Kéo vật: đổi độ cao. Kéo mũi tên: đặt vận tốc.',
                      'collision':'Kéo xe: đặt vận tốc đầu trên ray.',
                      'spring':'Kéo vật để đặt độ lệch rồi chọn Chạy.',
                      'pendulum':'Kéo vật: góc thả. Kéo điểm treo: chiều dài.',
                      'lever':'Kéo hai tải để đổi cánh tay đòn.',
                      'pulley':'Kéo đầu dây xuống hoặc kéo tải lên để nâng.'}[m.lab]
                y=self._text(surface,hint,(8,y+3),12,GOLD,w-16)
        if self.flags['measure']:
            keys={'lever':['torque_left_nm','torque_right_nm','torque_net_nm'],
                  'pulley':['height_m','required_n','work_j'],
                  'projectile':['height_m','position_m','target_error_m'],
                  'pendulum':['period_measured_s','period_small_s','velocity_m_s'],
                  'collision':['velocity_m_s','velocity2_m_s','momentum_kg_m_s']}.get(m.lab,['position_m','velocity_m_s','acceleration_m_s2'])
            y+=12
            for key in keys:
                if key not in MEASUREMENTS:
                    name,unit={'torque_left_nm':('Mômen trái','N·m'),'torque_right_nm':('Mômen phải','N·m'),'velocity2_m_s':('Vận tốc xe 2','m/s')}[key]
                else: name,unit=self.measurement_label(key)
                value=values[key]; text=('chưa chạm đất' if key=='target_error_m' else 'chưa đủ chu kỳ') if value is None else f'{value:.3g} {unit}'
                y=self._text(surface,f'{name}: {text}',(8,y),12,INK,w-16)
        paused={k:c for k,c in self.input.claims.items() if c.paused}
        if paused:
            label='Tạm mất tay • Giữ nguyên thiết lập' if any(k not in self.input.pointers for k in paused) else 'Đang xác nhận buông • Giữ nguyên thiết lập'
            self._text(surface,label,(8,y+8),12,GOLD,w-16)
        bottom=h-12
        if m.challenge:
            goal=m.spec['challenge']; lines=max(2,math.ceil(self._font(12).size(goal)[0]/max(1,w-24)))
            gh=min(h//3,lines*17+52); top=bottom-gh
            pygame.draw.rect(surface,(12,31,43,224),(0,top,w,gh),border_radius=10)
            self._text(surface,'ĐẠT ĐIỀU KIỆN' if m.achieved else 'NHIỆM VỤ',(10,top+6),12,GOLD)
            self._text(surface,goal,(10,top+25),12,INK,w-20); bottom=top-8
            prediction='chưa chọn' if m.prediction is None else 'đạt' if m.prediction=='yes' else 'chưa đạt'
            self._text(surface,'Dự đoán: '+prediction,(10,top+gh-18),11,GOLD,w-20)
        if self.flags['graph'] and h>=300:
            gh=min(135,h//3); rect=pygame.Rect(0,bottom-gh,w,gh); self._paint_graph(surface,rect); bottom=rect.y-8
        if self.flags['energy']:
            energies=[values[k] for k in ('kinetic_j','potential_j','thermal_j')]
            y=bottom-66
            pygame.draw.rect(surface,(10,24,36,225),(0,y,w,64),border_radius=10)
            for i,(value,color,name) in enumerate(zip(energies,(ACCENT,GOLD,(252,151,143)),('Động năng','Thế năng','Tiêu hao'))):
                self._text(surface,f'{name}: {value:.3g} J',(8,y+4+i*18),11,color,w-16)
            bottom=y-6
        comparison=m.comparison()
        if comparison and bottom>170:
            changed=', '.join(comparison['changed']) or 'Thông số cuối giống nhau'
            text=f"A: {comparison['time_a_s']:.2f}s • B: {comparison['time_b_s']:.2f}s • "+changed
            if not comparison['same_duration']: text+=' • Khác thời điểm'
            if comparison['live_inputs_differ']: text+=' • Khác lịch sử lực'
            self._text(surface,text,(8,bottom-32),11,GOLD,w-16)
        return surface

    def _paint_graph(self,surface,rect):
        pygame.draw.rect(surface,(10,24,36,228),rect,border_radius=10)
        name,unit=self.measurement_label(self.graph); self._text(surface,f'{name} ({unit}) • t (s) • A vàng / B xanh',(rect.x+10,rect.y+5),11,INK,rect.w-20)
        series=[(list(self.model.samples),ACCENT)]
        if self.model.reference: series.insert(0,(self.model.reference['samples'],GOLD))
        points=[(row['time_s'],row[self.graph]) for rows,_ in series for row in rows if row.get(self.graph) is not None]
        if len(points)<2: return
        times,values=zip(*points); tmax=max(max(times),.01); low=min(0,min(values)); high=max(.01,max(values))
        plot=rect.inflate(-48,-42); plot.y+=9
        for rows,color in series:
            vertices=[(plot.x+row['time_s']/tmax*plot.w,plot.bottom-(row[self.graph]-low)/(high-low)*plot.h) for row in rows if row.get(self.graph) is not None]
            if len(vertices)>1: pygame.draw.lines(surface,color,False,vertices,2)
        self._text(surface,f'{high:.2g}',(rect.x+3,plot.y),10,MUTED)
        self._text(surface,f'{low:.2g}',(rect.x+3,plot.bottom-12),10,MUTED)
        self._text(surface,f'{tmax:.2g} s',(plot.right-32,rect.bottom-16),10,MUTED)

    def _draw_cursors(self,dt):
        active={}
        for key,point in self.input.pointers.items():
            p=np.array(point)*self.content[2:]; previous=self.cursor_points.get(key,p)
            state=self.input.tap.states.get(key)
            p=p if key in self.input.claims or (state and state.locked) else previous+(p-previous)*(1-math.exp(-math.tau*self.cfg['cursor_response_hz']*dt))
            active[key]=p
            claim=self.input.claims.get(key)
            color=MUTED if claim and claim.paused else GOLD if claim or (state and state.phase in ('armed','press','latched')) else ACCENT
            gl.glColor3f(*(c/255 for c in color))
            gl.glLineWidth(2); gl.glBegin(gl.GL_LINE_LOOP)
            for a in np.linspace(0,math.tau,33): gl.glVertex2f(p[0]+10*math.cos(a),p[1]+10*math.sin(a))
            gl.glEnd()
            dwell=self.input.dwell.states.get(key); progress=state.progress if state and state.phase=='press' else dwell.progress if dwell else 0.
            if progress:
                gl.glColor3f(*(c/255 for c in GOLD)); gl.glLineWidth(3); gl.glBegin(gl.GL_LINE_STRIP)
                for a in np.linspace(-math.pi/2,-math.pi/2+math.tau*progress,33): gl.glVertex2f(p[0]+14*math.cos(a),p[1]+14*math.sin(a))
                gl.glEnd()
        self.cursor_points=active

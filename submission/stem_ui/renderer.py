"""One-window OpenGL scene with Vietnamese, responsive presentation controls."""
import math
from pathlib import Path
import time
from functools import lru_cache
import cv2
import numpy as np
import pygame
from OpenGL import GL as gl, GLU as glu
from .geometry import (Tip, FingerSelection, live_mesh, solid_mesh,
                       world_position, preview_position, TIPS)
from .manipulation import GrabController

BG = (12,20,31)
PANEL = (22,33,47)
INK = (226,237,246)
MUTED = (142,165,185)
ACCENT = (80,216,184)
COLORS = ((.31,.85,.72),(.42,.66,1.0),(.93,.69,.33),(.64,.5,.9))
KINDS = ('cube','tetra','octa','sphere')
NAMES = ('Lập phương','Tứ diện','Bát diện','Hình cầu')

class SubmissionRenderer:
    def __init__(self, settings):
        self.settings = settings
        self.size = tuple(settings['window'])
        self.windowed = self.size
        self.fullscreen = False
        self.camera_visible = True
        self.help_visible = True
        self.menu = False
        self.mode = 'solid'
        self.kind = 'cube'
        self.yaw = 32.0; self.pitch = 20.0; self.zoom = 1.0
        self.object_yaw = self.object_pitch = 0.0
        self.object_scale = 1.0
        self.buttons = []
        self.last_identity = None
        self.selectors = [FingerSelection(settings) for _ in range(2)]
        self.last_slots = set()
        self.last_reset = set()
        self.dragging = False
        self.grab = GrabController(settings)
        self.capture_path = None
        self.last_draw_at = None
        self.live_points = {}
        self.fit_center = None
        self.fit_scale = 1.0
        self.fit_identity = None
        self.fit_seen_at = 0.0
        self.hand_points = {}
        self.preview_key = None
        self.preview_surface = None
        self.last_overlay_at = 0.0
        self.last_overlay_key = None

    def open(self):
        pygame.init()
        pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE,24)
        self._set_display()
        pygame.display.set_caption('DIP Touchless STEM • Đồ án')
        font_path = Path('C:/Windows/Fonts/segoeui.ttf')
        self.fonts = {size:pygame.font.Font(str(font_path) if font_path.is_file() else None,size)
                      for size in (13,15,17,20,24,32)}
        self.quadric = glu.gluNewQuadric()
        self.clock = pygame.time.Clock()
        self.unit_sphere = gl.glGenLists(1)
        gl.glNewList(self.unit_sphere,gl.GL_COMPILE)
        glu.gluSphere(self.quadric,1,16,12); gl.glEndList()
        self.unit_bone=gl.glGenLists(1)
        gl.glNewList(self.unit_bone,gl.GL_COMPILE)
        glu.gluCylinder(self.quadric,1,1,1,10,1); gl.glEndList()
        self.solid_lists={}
        for kind in KINDS:
            display_list=gl.glGenLists(1)
            gl.glNewList(display_list,gl.GL_COMPILE)
            self._mesh(solid_mesh(kind),smooth=kind=='sphere',edges=kind!='sphere')
            gl.glEndList()
            self.solid_lists[kind]=display_list

    def _set_display(self):
        for display_list in getattr(self,'solid_lists',{}).values():
            gl.glDeleteLists(display_list,1)
        if hasattr(self,'texture'):
            gl.glDeleteTextures([self.texture])
        if hasattr(self,'unit_sphere'): gl.glDeleteLists(self.unit_sphere,1)
        if hasattr(self,'unit_bone'): gl.glDeleteLists(self.unit_bone,1)
        # Desktop-sized borderless window avoids exclusive display-mode
        # switching, which fails on some Windows drivers/remote sessions.
        flags = pygame.OPENGL | pygame.DOUBLEBUF | (pygame.NOFRAME if self.fullscreen else pygame.RESIZABLE)
        pygame.display.set_mode(self.size,flags)
        self.texture = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D,self.texture)
        gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_MIN_FILTER,gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_MAG_FILTER,gl.GL_LINEAR)
        gl.glTexImage2D(gl.GL_TEXTURE_2D,0,gl.GL_RGBA,*self.size,0,gl.GL_RGBA,gl.GL_UNSIGNED_BYTE,None)
        self.overlay_surface=pygame.Surface(self.size,pygame.SRCALPHA)
        self.last_overlay_at=0.0; self.last_overlay_key=None
        if hasattr(self,'solid_lists'):
            self.unit_sphere=gl.glGenLists(1)
            gl.glNewList(self.unit_sphere,gl.GL_COMPILE)
            glu.gluSphere(self.quadric,1,16,12); gl.glEndList()
            self.unit_bone=gl.glGenLists(1)
            gl.glNewList(self.unit_bone,gl.GL_COMPILE)
            glu.gluCylinder(self.quadric,1,1,1,10,1); gl.glEndList()
            self.solid_lists={}
            for kind in KINDS:
                display_list=gl.glGenLists(1)
                gl.glNewList(display_list,gl.GL_COMPILE)
                self._mesh(solid_mesh(kind),smooth=kind=='sphere',edges=kind!='sphere'); gl.glEndList()
                self.solid_lists[kind]=display_list

    def close(self):
        for display_list in getattr(self,'solid_lists',{}).values():
            gl.glDeleteLists(display_list,1)
        if hasattr(self,'texture'):
            gl.glDeleteTextures([self.texture])
        if hasattr(self,'quadric'):
            glu.gluDeleteQuadric(self.quadric)
        if hasattr(self,'unit_sphere'): gl.glDeleteLists(self.unit_sphere,1)
        if hasattr(self,'unit_bone'): gl.glDeleteLists(self.unit_bone,1)
        self._label.cache_clear()
        pygame.quit()

    def reset(self):
        self.yaw=32.; self.pitch=20.; self.zoom=1.
        self.object_yaw=self.object_pitch=0.; self.object_scale=1.
        self.grab.reset()
        self.fit_center=None; self.fit_identity=None

    def events(self):
        actions = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                actions.append('quit')
            elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
                self.size=(max(960,event.w),max(660,event.h)); self.windowed=self.size; self._set_display()
            elif event.type == pygame.KEYDOWN:
                key = event.key
                if key == pygame.K_ESCAPE:
                    if self.fullscreen:
                        self.toggle_fullscreen()
                    elif self.menu:
                        self.menu=False
                    else:
                        actions.append('quit')
                elif key in (pygame.K_RETURN,pygame.K_SPACE):
                    actions.append('toggle')
                elif key in (pygame.K_F11,pygame.K_f):
                    self.toggle_fullscreen()
                elif key == pygame.K_h:
                    self.help_visible=not self.help_visible
                elif key == pygame.K_c:
                    self.camera_visible=not self.camera_visible
                elif key == pygame.K_r:
                    self.reset()
                elif key == pygame.K_s:
                    self.cycle_scale_mode()
                elif key == pygame.K_TAB:
                    self.mode='tips' if self.mode=='solid' else 'solid'
                elif pygame.K_1 <= key <= pygame.K_4:
                    self.kind=KINDS[key-pygame.K_1]; self.mode='solid'
            elif event.type == pygame.MOUSEWHEEL:
                self.zoom=float(np.clip(self.zoom*math.exp(event.y*.08),.55,1.8))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button==1:
                action=next((a for rect,a in reversed(self.buttons) if rect.collidepoint(event.pos)),None)
                if action:
                    if action.startswith('kind:'):
                        self.kind=action.split(':')[1]; self.mode='solid'; self.menu=False
                    elif action in ('solid','tips'):
                        self.mode=action
                    elif action=='camera':
                        self.camera_visible=not self.camera_visible
                    elif action=='help':
                        self.help_visible=not self.help_visible
                    elif action=='fullscreen':
                        self.toggle_fullscreen()
                    elif action=='reset':
                        self.reset()
                    elif action=='scale_mode':
                        self.cycle_scale_mode()
                    elif action=='menu':
                        self.menu=not self.menu
                    else:
                        actions.append(action)
                else:
                    self.dragging=True
            elif event.type == pygame.MOUSEBUTTONUP:
                self.dragging=False
            elif event.type == pygame.MOUSEMOTION and self.dragging:
                self.yaw+=event.rel[0]*.3; self.pitch=float(np.clip(self.pitch+event.rel[1]*.3,-65,65))
        return actions

    def toggle_fullscreen(self):
        self.fullscreen=not self.fullscreen
        self.size=pygame.display.get_desktop_sizes()[0] if self.fullscreen else self.windowed
        self._set_display()

    def cycle_scale_mode(self):
        modes=('uniform','stretch','distance','depth')
        self.grab.set_scale_mode(modes[(modes.index(self.grab.scale_mode)+1)%len(modes)])

    @lru_cache(maxsize=256)
    def _label(self,text,size,color):
        return self.fonts[size].render(text,True,color)

    def _text(self,surface,text,pos,size=17,color=INK):
        surface.blit(self._label(text,size,tuple(color)),pos)

    def _wrap(self,surface,text,pos,width,size=17,color=MUTED):
        x,y=pos; line=''
        for word in text.split():
            candidate=(line+' '+word).strip()
            if self.fonts[size].size(candidate)[0]>width and line:
                self._text(surface,line,(x,y),size,color); y+=size+7; line=word
            else:
                line=candidate
        self._text(surface,line,(x,y),size,color)
        return y+size+7

    def _button(self,surface,label,rect,action,active=False):
        rect=pygame.Rect(rect)
        pygame.draw.rect(surface,(38,81,83) if active else (32,47,65),rect,border_radius=10)
        if active:
            pygame.draw.rect(surface,ACCENT,rect,1,border_radius=10)
        rendered=self._label(label,15,ACCENT if active else INK)
        surface.blit(rendered,rendered.get_rect(center=rect.center))
        self.buttons.append((rect,action))

    def draw(self,snapshot,status,*,active=False,error=None,run_id='',camera_index=0,replay=False):
        w,h=self.size
        panel_width=340 if self.camera_visible else 0
        view=(24,145,w-48-panel_width-(18 if panel_width else 0),h-219)
        vx,vy,vw,vh=view
        now=time.monotonic()
        draw_dt=0 if self.last_draw_at is None else now-self.last_draw_at
        self.last_draw_at=now
        px=math.radians(self.pitch); yx=math.radians(self.yaw)
        rx=np.array(((1,0,0),(0,math.cos(px),-math.sin(px)),(0,math.sin(px),math.cos(px))))
        ry=np.array(((math.cos(yx),0,math.sin(yx)),(0,1,0),(-math.sin(yx),0,math.cos(yx))))
        view_rotation=rx@ry
        gl.glViewport(0,0,w,h)
        gl.glClearColor(*(c/255 for c in BG),1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glEnable(gl.GL_SCISSOR_TEST); gl.glScissor(vx,h-vy-vh,vw,vh)
        gl.glViewport(vx,h-vy-vh,vw,vh)
        gl.glMatrixMode(gl.GL_PROJECTION); gl.glLoadIdentity()
        glu.gluPerspective(44,vw/vh,.1,100)
        gl.glMatrixMode(gl.GL_MODELVIEW); gl.glLoadIdentity()
        gl.glTranslatef(0,-.1,-9/self.zoom)
        gl.glRotatef(self.pitch,1,0,0); gl.glRotatef(self.yaw,0,1,0)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_LIGHTING); gl.glEnable(gl.GL_LIGHT0)
        gl.glLightfv(gl.GL_LIGHT0,gl.GL_POSITION,(3,5,7,1))
        gl.glLightfv(gl.GL_LIGHT0,gl.GL_DIFFUSE,(.8,.86,1,1))
        gl.glLightModelfv(gl.GL_LIGHT_MODEL_AMBIENT,(.3,.3,.35,1))
        gl.glMaterialfv(gl.GL_FRONT_AND_BACK,gl.GL_SPECULAR,(.35,.35,.4,1))
        gl.glMaterialf(gl.GL_FRONT_AND_BACK,gl.GL_SHININESS,32)
        gl.glLightModeli(gl.GL_LIGHT_MODEL_TWO_SIDE,gl.GL_TRUE)
        gl.glEnable(gl.GL_COLOR_MATERIAL); gl.glEnable(gl.GL_NORMALIZE)
        self._floor()
        fresh = snapshot is not None and active and time.monotonic()-snapshot.delivered_at <= self.settings['stale_after_s']
        hands=snapshot.hands if fresh else ()
        identity=(run_id,snapshot.frame_id) if fresh else None
        tips=[]
        present={hand.slot for hand in hands}
        for s in self.last_slots-present:
            self.selectors[s].reset()
        if identity != self.last_identity:
            for hand in hands:
                # Angle hysteresis cannot transfer to a new hand generation.
                if hand.generation not in (getattr(self,'selector_generation',{}).get(hand.slot),):
                    self.selectors[hand.slot].reset()
                self.selectors[hand.slot].update(hand.landmarks,snapshot.image.shape[1]/snapshot.image.shape[0])
            if self.mode=='solid' and fresh:
                self.grab.update(hands,snapshot.timestamp_s,snapshot.image.shape[1]/snapshot.image.shape[0],view_rotation)
        if not fresh or self.mode!='solid':
            self.grab.release()
        self.grab.advance(draw_dt)
        self.last_identity=identity; self.last_slots=present
        self.selector_generation={hand.slot:hand.generation for hand in hands}
        for hand in hands:
            aspect=snapshot.image.shape[1]/snapshot.image.shape[0]
            for l in hand.landmarks:
                if l.index in self.selectors[hand.slot].active:
                    tips.append(Tip(hand.slot,l.index,world_position(l,aspect,self.settings)))
        generation={hand.slot:hand.generation for hand in hands}
        targets={(tip.hand,generation[tip.hand],tip.index):np.array(tip.position) for tip in tips}
        alpha=1-math.exp(-math.tau*self.settings['live_response_hz']*max(0,draw_dt))
        hand_targets={(hand.slot,hand.generation,l.index):np.array(world_position(l,snapshot.image.shape[1]/snapshot.image.shape[0],self.settings))
                      for hand in hands for l in hand.landmarks}
        self.hand_points={key:self.hand_points.get(key,value)+alpha*(value-self.hand_points.get(key,value))
                          for key,value in hand_targets.items()}
        self.live_points={key:self.hand_points[key] for key in targets}
        tips=[Tip(key[0],key[2],tuple(value)) for key,value in self.live_points.items()]
        world_labels=[]
        if self.mode=='solid':
            pose=self.grab.pose
            vertices=np.array(solid_mesh(self.kind).vertices)*(pose.scale*pose.stretch)
            vertices=vertices@pose.rotation.T+pose.position
            self._shadow(vertices)
            gl.glPushMatrix(); gl.glTranslatef(*pose.position)
            matrix=np.eye(4); matrix[:3,:3]=pose.rotation
            gl.glMultMatrixf(matrix.T.astype(np.float32))
            gl.glScalef(*(pose.scale*pose.stretch))
            gl.glCallList(self.solid_lists[self.kind]); gl.glPopMatrix()
        else:
            gl.glPushMatrix()
            fit=1.0
            if hands:
                positions=np.array([t.position for t in tips]) if tips else np.array(list(self.hand_points.values()))
                center=(positions.min(axis=0)+positions.max(axis=0))/2
                span=max(float(np.ptp(positions[:,0])),float(np.ptp(positions[:,1])),.5)
                fit=min(5.0,self.settings['live_fit_width']/span)
                changed=self.fit_identity is None or self.fit_identity[0]!=run_id or any(
                    slot in self.fit_identity[1] and self.fit_identity[1][slot]!=value for slot,value in generation.items())
                if self.fit_center is None or changed:
                    self.fit_center=center; self.fit_scale=fit
                    self.fit_identity=(run_id,dict(generation))
                else:
                    self.fit_identity[1].update(generation)
                self.fit_seen_at=now
            elif now-self.fit_seen_at>self.settings['grip_loss_grace_s']:
                self.fit_center=None; self.fit_identity=None
            if self.fit_center is not None:
                fit=self.fit_scale
                gl.glScalef(fit,fit,fit); gl.glTranslatef(*(-self.fit_center))
            self._hands3d(hands,fit)
            depth_limit=self.settings['live_depth_exit_ratio'] if getattr(self,'live_mesh_mode','')=='hull3d' else self.settings['live_depth_ratio']
            mesh=live_mesh(tips,self.settings['display_thickness'],depth_limit)
            self.live_mesh_mode=mesh.mode
            self._shadow(mesh.vertices,(-1.99/fit+self.fit_center[1]) if self.fit_center is not None else -1.99)
            self._mesh(mesh)
            if len(tips)==2:
                gl.glDisable(gl.GL_LIGHTING); gl.glColor3f(*COLORS[0]); gl.glLineWidth(3)
                gl.glBegin(gl.GL_LINES)
                for tip in tips: gl.glVertex3f(*tip.position)
                gl.glEnd()
            gl.glEnable(gl.GL_LIGHTING)
            for tip in tips:
                gl.glColor3f(*COLORS[tip.hand]); gl.glPushMatrix(); gl.glTranslatef(*tip.position)
                gl.glScalef(*([self.settings['tip_radius']/fit]*3))
                gl.glCallList(self.unit_sphere); gl.glPopMatrix()
                x,y,z=glu.gluProject(*tip.position)
                if 0<z<1:
                    world_labels.append((f'{tip.hand+1}.{TIPS.index(tip.index)+1}',(int(x)+8,h-int(y)-10)))
            gl.glPopMatrix()
        gl.glDisable(gl.GL_SCISSOR_TEST)
        overlay_key=(self.size,self.camera_visible,self.help_visible,self.menu,self.mode,self.kind,
                     self.fullscreen,self.grab.scale_mode,active,error,status,camera_index)
        # UI/preview is refreshed separately; 3D following remains render-rate.
        if overlay_key!=self.last_overlay_key or now-self.last_overlay_at>=1/self.settings['overlay_fps']:
            overlay=self._draw_ui(snapshot,status,active,error,run_id,camera_index,replay,view,hands,tips,fresh,world_labels)
            self.last_overlay_at=now; self.last_overlay_key=overlay_key
        else:
            overlay=None
        self._overlay(overlay)
        if self.capture_path:
            self._capture_back(self.capture_path)
            self.capture_path=None
        self.last_draw_cpu_ms=(time.monotonic()-now)*1000
        pygame.display.flip()
        self.clock.tick(self.settings['render_fps'])
        return len(hands),len(tips)

    def _draw_ui(self,snapshot,status,active,error,run_id,camera_index,replay,view,hands,tips,fresh,world_labels):
        w,h=self.size
        vx,vy,vw,vh=view
        overlay=self.overlay_surface
        overlay.fill((0,0,0,0))
        self.buttons=[]
        pygame.draw.rect(overlay,(*BG,255),(0,0,w,130))
        pygame.draw.line(overlay,(38,52,70),(24,86),(w-24,86))
        self._text(overlay,'DIP', (28,20),32,ACCENT)
        self._text(overlay,'TOUCHLESS STEM',(99,23),24)
        self._text(overlay,'Không gian hình học • webcam RGB',(99,54),13,MUTED)
        x=w-510
        self._button(overlay,'Dừng camera' if active else 'Mở camera',(x,23,132,42),'toggle',active)
        self._button(overlay,'Camera',(x+144,23,88,42),'camera',self.camera_visible)
        self._button(overlay,'Hướng dẫn',(x+244,23,104,42),'help',self.help_visible)
        self._button(overlay,'Thu khung' if self.fullscreen else 'Toàn màn',(x+360,23,124,42),'fullscreen',self.fullscreen)
        self._button(overlay,'Khối 3D',(24,99,116,35),'solid',self.mode=='solid')
        self._button(overlay,'Đầu ngón',(148,99,116,35),'tips',self.mode=='tips')
        if self.mode=='solid':
            self._button(overlay,NAMES[KINDS.index(self.kind)]+'  v',(280,99,150,35),'menu')
            label={'uniform':'2 tay: cỡ đều','stretch':'2 tay: kéo dãn','distance':'1 tay: đổi cỡ','depth':'1 tay: tiến/lùi'}[self.grab.scale_mode]
            self._button(overlay,label,(442,99,142,35),'scale_mode',self.grab.scale_mode!='uniform')
        self._button(overlay,'Đặt lại góc nhìn',(w-170,99,146,35),'reset')
        self._text(overlay,f'{len(hands)} tay • {len(tips)} đầu ngón duỗi' if fresh else status,(vx+12,vy+12),15,ACCENT if hands else MUTED)
        if self.mode=='solid' and fresh:
            self._text(overlay,self.grab.feedback,(vx+12,vy+38),15,ACCENT if self.grab.slots else MUTED)
        for label,pos in world_labels:
            self._text(overlay,label,pos,13,INK)
        if self.mode=='tips' and not tips:
            self._text(overlay,'Đưa bàn tay vào camera và duỗi các ngón',(vx+28,vy+vh//2),20,MUTED)
        if self.camera_visible:
            px=w-364; py=145
            pygame.draw.rect(overlay,(*PANEL,255),(px,py,340,h-py-74),border_radius=16)
            self._text(overlay,'CAMERA', (px+18,py+17),15,ACCENT)
            if snapshot is not None and active:
                bgr=snapshot.image
                ih,iw=bgr.shape[:2]; ratio=min(304/iw,240/ih); cw,ch=round(iw*ratio),round(ih*ratio)
                rect=(px+18+(304-cw)//2,py+53+(240-ch)//2,cw,ch)
                preview_key=(run_id,snapshot.frame_id,cw,ch)
                if self.preview_key!=preview_key:
                    small=cv2.resize(bgr,(cw,ch),interpolation=cv2.INTER_AREA)
                    rgb=np.ascontiguousarray(cv2.cvtColor(small,cv2.COLOR_BGR2RGB))
                    if self.settings['mirror']: rgb=np.ascontiguousarray(rgb[:,::-1])
                    self.preview_surface=pygame.image.frombuffer(rgb.tobytes(),(cw,ch),'RGB').copy()
                    self.preview_key=preview_key
                overlay.blit(self.preview_surface,rect[:2])
                if fresh:
                    for hand in hands:
                        color=ACCENT if hand.slot==0 else (108,169,255)
                        positions={l.index:preview_position(l,rect,self.settings['mirror']) for l in hand.landmarks}
                        for chain in ((0,1,2,3,4),(0,5,6,7,8),(5,9,10,11,12),(9,13,14,15,16),(13,17,18,19,20),(0,17)):
                            pygame.draw.lines(overlay,color,False,[positions[i] for i in chain],2)
                        for tip in self.selectors[hand.slot].active:
                            pygame.draw.circle(overlay,color,positions[tip],6,2)
                        grip=self.grab.grips.get(hand.slot)
                        grabbing=grip is not None and grip.held and self.mode=='solid'
                        pygame.draw.circle(overlay,(255,203,96) if grabbing else color,positions[8],10,3)
                        self._text(overlay,f'Tay {hand.slot+1}: '+('GIỮ' if grabbing else 'chưa giữ'),
                                   (rect[0]+8,rect[1]+8+hand.slot*22),13,(255,203,96) if grabbing else INK)
                ill=snapshot.illumination
                self._text(overlay,'Đang nhận tay' if hands else 'Chưa thấy tay',(px+18,py+311),20,ACCENT if hands else MUTED)
                light='Ánh sáng thường' if ill.state.value=='NORMAL' else 'Ánh sáng / tương phản yếu'
                self._text(overlay,light,(px+18,py+349),15,MUTED)
                self._text(overlay,'CLAHE: '+('đang bật' if ill.enhancement_active else 'bỏ qua'),(px+18,py+375),15,MUTED)
                if self.mode=='solid':
                    pose=self.grab.pose
                    size_label=(f'Kéo dãn: {pose.stretch[0]:.2f} / {pose.stretch[1]:.2f} / {pose.stretch[2]:.2f}'
                                if self.grab.scale_mode=='stretch' else f'Kích thước khối: {pose.scale:.2f}x')
                    self._text(overlay,size_label,(px+18,py+400),15,ACCENT)
            else:
                self._wrap(overlay,'Bấm Mở camera để bắt đầu. Hình từ camera chỉ xử lý trên máy.',(px+20,py+90),290,20)
            self._wrap(overlay,'Đưa 1–2 tay vào khung, tách hai lòng bàn tay và tránh che đầu ngón.',(px+18,py+421),300,15)
            if error:
                self._wrap(overlay,error,(px+18,py+489),300,15,(246,165,134))
            if not active:
                self._button(overlay,f'Camera {camera_index} • đổi',(px+18,py+310,304,38),'next_camera')
        if self.help_visible:
            hw=min(390,vw-36); hx=vx+18; hy=vy+58
            pygame.draw.rect(overlay,(22,33,47,240),(hx,hy,hw,170),border_radius=14)
            self._text(overlay,'Thử trong 3 bước',(hx+16,hy+13),20,ACCENT)
            instructions=('1. Chụm cái–trỏ; vòng vàng báo đã giữ.\n2. Một tay dời/xoay; hai tay đổi cỡ và nghiêng.\n3. S đổi: cỡ / dãn / một tay cỡ / tiến-lùi.' if self.mode=='solid' else
                '1. Duỗi các ngón để tạo các đỉnh sống.\n2. Một hoặc hai tay đều tự tạo hình.\n3. Gập ngón để bỏ đỉnh; kéo chuột để xem chiều sâu.')
            y=hy+48
            for line in instructions.split('\n'):
                y=self._wrap(overlay,line,(hx+16,y),hw-32,15,INK)
            self._text(overlay,'Mở ngón để buông • S đổi thao tác • H ẩn hướng dẫn',(hx+16,hy+143),13,MUTED)
        if self.menu and self.mode=='solid':
            for i,name in enumerate(NAMES):
                self._button(overlay,name,(280,139+i*42,180,38),'kind:'+KINDS[i],self.kind==KINDS[i])
        if error and not self.camera_visible:
            pygame.draw.rect(overlay,(62,35,37,245),(vx+12,h-127,vw-24,68),border_radius=12)
            self._wrap(overlay,error,(vx+24,h-118),vw-48,15,(246,165,134))
        self._text(overlay,'Kéo chuột: đổi góc nhìn   •   Cuộn: góc nhìn gần/xa   •   R: đặt lại',(24,h-48),15,MUTED)
        detail=('Bao 3D từ đầu ngón • z tương đối của từng tay' if getattr(self,'live_mesh_mode','')=='hull3d'
                else 'Đầu ngón gần đồng phẳng • độ dày là minh họa') if self.mode=='tips' else 'Cảnh 3D có chiếu phối cảnh • tiến/lùi là thao tác biểu kiến'
        self._text(overlay,detail,(24,h-25),13,MUTED)
        if replay:
            self._text(overlay,'PHÁT LẠI • dữ liệu đã ghi',(w-295,h-47),15,(237,185,110))
        return overlay

    def _hands3d(self,hands,fit):
        """Illustrative joint/bone volume, no invented missing landmarks."""
        gl.glEnable(gl.GL_LIGHTING)
        chains=((0,1,2,3,4),(0,5,6,7,8),(5,9,10,11,12),(9,13,14,15,16),(13,17,18,19,20),(0,17))
        for hand in hands:
            p={i:self.hand_points[(hand.slot,hand.generation,i)] for i in range(21)}
            gl.glColor3f(*(.55*np.array(COLORS[hand.slot])))
            palm=(0,5,9,13,17)
            for a,b in zip(palm[1:-1],palm[2:]):
                n=np.cross(p[a]-p[0],p[b]-p[0]); length=np.linalg.norm(n)
                if length<1e-10: continue
                gl.glBegin(gl.GL_TRIANGLES); gl.glNormal3fv(n/length)
                for i in (0,a,b): gl.glVertex3f(*p[i])
                gl.glEnd()
            for i in range(21):
                gl.glPushMatrix(); gl.glTranslatef(*p[i])
                gl.glScalef(*([self.settings['hand_joint_radius']/fit]*3))
                gl.glCallList(self.unit_sphere); gl.glPopMatrix()
            for chain in chains:
                for a,b in zip(chain,chain[1:]):
                    d=p[b]-p[a]; length=np.linalg.norm(d)
                    if length<1e-8: continue
                    z=d/length
                    reference=np.array((0.,1.,0.)) if abs(z[1])<.9 else np.array((1.,0.,0.))
                    x=np.cross(reference,z); x/=np.linalg.norm(x); y=np.cross(z,x)
                    matrix=np.eye(4); matrix[:3,:3]=np.column_stack((x,y,z))
                    gl.glPushMatrix(); gl.glTranslatef(*p[a]); gl.glMultMatrixf(matrix.T.astype(np.float32))
                    radius=self.settings['hand_bone_radius']/fit
                    gl.glScalef(radius,radius,length); gl.glCallList(self.unit_bone); gl.glPopMatrix()

    def _shadow(self,vertices,floor_y=-1.99):
        """Floor cue projected from display geometry, not a physical contact test."""
        if not len(vertices): return
        p=np.asarray(vertices,dtype=float)
        center=p.mean(axis=0)
        radius=max(float(np.ptp(p[:,0]))*.42,.12)
        depth=max(float(np.ptp(p[:,2]))*.42,.12)
        gl.glDisable(gl.GL_LIGHTING); gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA,gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glColor4f(0,0,0,.28); gl.glDepthMask(gl.GL_FALSE)
        gl.glBegin(gl.GL_TRIANGLE_FAN); gl.glVertex3f(center[0],floor_y,center[2])
        for i in range(33):
            angle=math.tau*i/32
            gl.glVertex3f(center[0]+radius*math.cos(angle),floor_y,center[2]+depth*math.sin(angle))
        gl.glEnd(); gl.glDepthMask(gl.GL_TRUE); gl.glDisable(gl.GL_BLEND); gl.glEnable(gl.GL_LIGHTING)

    def _mesh(self,mesh,smooth=False,edges=True):
        gl.glEnable(gl.GL_LIGHTING); gl.glEnable(gl.GL_POLYGON_OFFSET_FILL); gl.glPolygonOffset(1,1)
        for i,face in enumerate(mesh.faces):
            a,b,c=(np.asarray(mesh.vertices[k],dtype=float) for k in face[:3])
            n=np.cross(b-a,c-a); length=np.linalg.norm(n)
            if length<1e-10: continue
            gl.glColor3f(*COLORS[0 if smooth else i%len(COLORS)])
            gl.glBegin(gl.GL_POLYGON); gl.glNormal3fv(n/length)
            for index in face:
                if smooth:
                    v=np.asarray(mesh.vertices[index]); gl.glNormal3fv(v/max(np.linalg.norm(v),1e-8))
                gl.glVertex3f(*mesh.vertices[index])
            gl.glEnd()
        gl.glDisable(gl.GL_POLYGON_OFFSET_FILL); gl.glDisable(gl.GL_LIGHTING)
        if not edges: return
        gl.glColor3f(.65,.83,.9); gl.glLineWidth(1.2)
        edges=set()
        for face in mesh.faces:
            for a,b in zip(face,face[1:]+face[:1]): edges.add(tuple(sorted((a,b))))
        gl.glBegin(gl.GL_LINES)
        for a,b in edges:
            gl.glVertex3f(*mesh.vertices[a]); gl.glVertex3f(*mesh.vertices[b])
        gl.glEnd()

    def _floor(self):
        gl.glDisable(gl.GL_LIGHTING); gl.glLineWidth(1); gl.glColor3f(.14,.21,.28)
        gl.glBegin(gl.GL_LINES)
        for i in range(-6,7):
            gl.glVertex3f(i*.6,-2,-3.6); gl.glVertex3f(i*.6,-2,3.6)
            gl.glVertex3f(-3.6,-2,i*.6); gl.glVertex3f(3.6,-2,i*.6)
        gl.glEnd(); gl.glEnable(gl.GL_LIGHTING)

    def _overlay(self,surface):
        w,h=self.size
        gl.glViewport(0,0,w,h); gl.glDisable(gl.GL_DEPTH_TEST); gl.glDisable(gl.GL_LIGHTING)
        gl.glMatrixMode(gl.GL_PROJECTION); gl.glLoadIdentity(); gl.glOrtho(0,w,h,0,-1,1)
        gl.glMatrixMode(gl.GL_MODELVIEW); gl.glLoadIdentity()
        gl.glEnable(gl.GL_TEXTURE_2D); gl.glBindTexture(gl.GL_TEXTURE_2D,self.texture)
        if surface is not None:
            gl.glTexSubImage2D(gl.GL_TEXTURE_2D,0,0,0,w,h,gl.GL_RGBA,gl.GL_UNSIGNED_BYTE,pygame.image.tobytes(surface,'RGBA',False))
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA,gl.GL_ONE_MINUS_SRC_ALPHA); gl.glColor4f(1,1,1,1)
        gl.glBegin(gl.GL_QUADS)
        for (u,v),(x,y) in zip(((0,0),(1,0),(1,1),(0,1)),((0,0),(w,0),(w,h),(0,h))):
            gl.glTexCoord2f(u,v); gl.glVertex2f(x,y)
        gl.glEnd(); gl.glDisable(gl.GL_TEXTURE_2D); gl.glDisable(gl.GL_BLEND)

    def screenshot(self,path):
        self.capture_path=path

    def _capture_back(self,path):
        w,h=self.size
        gl.glReadBuffer(gl.GL_BACK)
        gl.glPixelStorei(gl.GL_PACK_ALIGNMENT,1)
        data=gl.glReadPixels(0,0,w,h,gl.GL_RGB,gl.GL_UNSIGNED_BYTE)
        image=np.frombuffer(data,dtype=np.uint8).reshape(h,w,3)[::-1]
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        cv2.imwrite(str(path),cv2.cvtColor(image,cv2.COLOR_RGB2BGR))

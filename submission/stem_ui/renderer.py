"""One-window OpenGL scene with Vietnamese, responsive presentation controls."""
import math
import os
from pathlib import Path
import time
from functools import lru_cache
import cv2
import numpy as np
import pygame
from OpenGL import GL as gl, GLU as glu
from .geometry import (Tip, FingerSelection, live_mesh, solid_mesh,
                       world_position, preview_position, TIPS)
from .geometry import bone_transforms
from .manipulation import GrabController
from .chemistry_view import CameraChemistryView
from .theme import BG, PANEL, INK, MUTED, ACCENT, GOLD, AUTHORS, card, glass, outline, atom_mark, header_height, scene_rect

COLORS = ((.20,.72,.90),(.28,.46,.82),(.48,.87,.94),(.47,.60,.79))
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
        self.chemistry=CameraChemistryView(settings,self)

    def open(self):
        os.environ.setdefault('SDL_WINDOWS_DPI_AWARENESS',self.settings['windows_dpi_awareness'])
        pygame.init()
        pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE,24)
        self._set_display()
        pygame.display.set_caption('DIP Touchless STEM • Đồ án')
        font_path = Path('C:/Windows/Fonts/segoeui.ttf')
        self.fonts = {size:pygame.font.Font(str(font_path) if font_path.is_file() else None,size)
                      for size in (12,13,14,15,17,20,24,28,32)}
        self.quadric = glu.gluNewQuadric()
        self.clock = pygame.time.Clock()
        self.unit_sphere = gl.glGenLists(1)
        gl.glNewList(self.unit_sphere,gl.GL_COMPILE)
        glu.gluSphere(self.quadric,1,32,24); gl.glEndList()
        self.unit_bone=gl.glGenLists(1)
        gl.glNewList(self.unit_bone,gl.GL_COMPILE)
        glu.gluCylinder(self.quadric,1,1,1,10,1); gl.glEndList()
        self.chemistry.open()
        self.solid_lists={}
        for kind in KINDS:
            display_list=gl.glGenLists(1)
            gl.glNewList(display_list,gl.GL_COMPILE)
            self._mesh(solid_mesh(kind),smooth=kind=='sphere',edges=kind!='sphere')
            gl.glEndList()
            self.solid_lists[kind]=display_list

    def _set_display(self):
        self.chemistry.close()
        for display_list in getattr(self,'solid_lists',{}).values():
            gl.glDeleteLists(display_list,1)
        if hasattr(self,'texture'):
            gl.glDeleteTextures([self.texture])
        if hasattr(self,'unit_sphere'): gl.glDeleteLists(self.unit_sphere,1)
        if hasattr(self,'unit_bone'): gl.glDeleteLists(self.unit_bone,1)
        # Desktop-sized borderless window avoids exclusive display-mode
        # switching, which fails on some Windows drivers/remote sessions.
        flags = pygame.OPENGL | pygame.DOUBLEBUF | (pygame.NOFRAME if self.fullscreen else pygame.RESIZABLE)
        for samples in (self.settings['render_msaa_samples'],0):
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS,int(samples>0))
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES,samples)
            try:
                pygame.display.set_mode(self.size,flags)
                break
            except pygame.error:
                if not samples: raise
        self.actual_msaa_samples=int(gl.glGetIntegerv(gl.GL_SAMPLES))
        if self.actual_msaa_samples: gl.glEnable(gl.GL_MULTISAMPLE)
        self.size=pygame.display.get_window_size()
        self.buttons=[]
        self.texture = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D,self.texture)
        # Overlay is exactly one texture pixel per drawable pixel.
        gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_MIN_FILTER,gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_MAG_FILTER,gl.GL_NEAREST)
        gl.glTexImage2D(gl.GL_TEXTURE_2D,0,gl.GL_RGBA,*self.size,0,gl.GL_RGBA,gl.GL_UNSIGNED_BYTE,None)
        self.overlay_surface=pygame.Surface(self.size,pygame.SRCALPHA)
        self.last_overlay_at=0.0; self.last_overlay_key=None
        if hasattr(self,'solid_lists'):
            self.chemistry.open()
            self.unit_sphere=gl.glGenLists(1)
            gl.glNewList(self.unit_sphere,gl.GL_COMPILE)
            glu.gluSphere(self.quadric,1,32,24); gl.glEndList()
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
        self.chemistry.close()
        for display_list in getattr(self,'solid_lists',{}).values():
            gl.glDeleteLists(display_list,1)
        if hasattr(self,'texture'):
            gl.glDeleteTextures([self.texture])
        if hasattr(self,'quadric'):
            glu.gluDeleteQuadric(self.quadric)
        if hasattr(self,'unit_sphere'): gl.glDeleteLists(self.unit_sphere,1)
        if hasattr(self,'unit_bone'): gl.glDeleteLists(self.unit_bone,1)
        self._label.cache_clear()
        glass.cache_clear()
        outline.cache_clear()
        atom_mark.cache_clear()
        pygame.quit()

    def reset(self):
        if self.mode=='chemistry':
            self.chemistry.input.command('frame'); self.chemistry.input.page='compact'; return
        self.yaw=32.; self.pitch=20.; self.zoom=1.
        self.object_yaw=self.object_pitch=0.; self.object_scale=1.
        self.grab.reset()
        self.fit_center=None; self.fit_identity=None

    def events(self):
        actions = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                actions.append('quit')
            elif event.type == pygame.VIDEORESIZE and not self.fullscreen and (event.w,event.h)!=self.size:
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
                    if self.mode=='chemistry': self.chemistry.input.command('order')
                    else: self.cycle_scale_mode()
                elif key == pygame.K_p:
                    self.enter_chemistry()
                elif self.mode=='chemistry' and key==pygame.K_b:
                    self.chemistry.input.command('elements' if self.chemistry.input.page=='compact' else 'compact')
                elif self.mode=='chemistry' and key in (pygame.K_e,pygame.K_o,pygame.K_t,pygame.K_z,pygame.K_y,pygame.K_BACKSPACE,pygame.K_l,pygame.K_j):
                    self.chemistry.input.command({pygame.K_e:'edit',pygame.K_o:'electrons',pygame.K_t:'table',pygame.K_z:'undo',
                        pygame.K_y:'redo',pygame.K_BACKSPACE:'delete',pygame.K_l:'save',pygame.K_j:'load'}[key])
                elif key == pygame.K_TAB:
                    if self.mode=='solid': self.mode='tips'
                    elif self.mode=='tips': self.enter_chemistry()
                    else: self.mode='solid'; self.chemistry.input.release()
                elif pygame.K_1 <= key <= pygame.K_4:
                    self.kind=KINDS[key-pygame.K_1]; self.mode='solid'
            elif event.type == pygame.MOUSEWHEEL:
                if self.mode!='chemistry': self.zoom=float(np.clip(self.zoom*math.exp(event.y*.08),.55,1.8))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button==1:
                action=next((a for rect,a in reversed(self.buttons) if rect.collidepoint(event.pos)),None)
                if action:
                    if action.startswith('kind:'):
                        self.kind=action.split(':')[1]; self.mode='solid'; self.menu=False
                    elif action in ('solid','tips'):
                        self.mode=action; self.chemistry.input.release()
                    elif action=='chemistry':
                        self.enter_chemistry()
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
                    if self.mode=='chemistry': self.chemistry.mouse('down',event.pos)
                    else: self.dragging=True
            elif event.type == pygame.MOUSEBUTTONUP:
                self.dragging=False
                if self.mode=='chemistry' and event.button==1: self.chemistry.mouse('up',event.pos)
            elif event.type == pygame.MOUSEMOTION and self.mode=='chemistry':
                self.chemistry.mouse('move',event.pos)
            elif event.type == pygame.MOUSEMOTION and self.dragging:
                self.yaw+=event.rel[0]*.3; self.pitch=float(np.clip(self.pitch+event.rel[1]*.3,-65,65))
        return actions

    def toggle_fullscreen(self):
        if not self.fullscreen:
            self.windowed=pygame.display.get_window_size()
        self.fullscreen=not self.fullscreen
        self.size=pygame.display.get_desktop_sizes()[0] if self.fullscreen else self.windowed
        self._set_display()

    def enter_chemistry(self):
        self.mode='chemistry'; self.camera_visible=False; self.menu=False
        self.grab.release(); self.chemistry.input.release()

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
        hovered=rect.collidepoint(pygame.mouse.get_pos())
        surface.blit(glass(rect.size,250,10,active or hovered,self.settings['ui_card_supersample']),rect)
        surface.blit(outline(rect.size,ACCENT if active else (83,119,139),samples=self.settings['ui_card_supersample']),rect)
        if active: pygame.draw.line(surface,GOLD,(rect.x+14,rect.bottom-2),(rect.right-14,rect.bottom-2),2)
        rendered=self._label(label,14,INK)
        surface.blit(rendered,rendered.get_rect(center=rect.center))
        self.buttons.append((rect,action))

    def _card(self,surface,rect,alpha=235,bright=False):
        card(surface,rect,alpha,bright,self.settings['ui_card_supersample'])

    def draw(self,snapshot,status,*,active=False,error=None,run_id='',camera_index=0,replay=False):
        w,h=self.size
        view=scene_rect(self.size,self.camera_visible)
        vx,vy,vw,vh=view
        now=time.monotonic()
        draw_dt=0 if self.last_draw_at is None else now-self.last_draw_at
        self.last_draw_at=now
        if self.mode=='chemistry':
            return self._draw_chemistry(snapshot,status,active,error,run_id,camera_index,replay,view,now,draw_dt)
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
        gl.glLightModelfv(gl.GL_LIGHT_MODEL_AMBIENT,(.20,.24,.29,1))
        gl.glMaterialfv(gl.GL_FRONT_AND_BACK,gl.GL_SPECULAR,(.85,.91,1,1))
        gl.glMaterialf(gl.GL_FRONT_AND_BACK,gl.GL_SHININESS,80)
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
                self.selectors[hand.slot].update(hand.raw_landmarks or hand.landmarks,snapshot.image.shape[1]/snapshot.image.shape[0])
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
        self.hand_points={key:self._follow_point(self.hand_points.get(key,value),value,draw_dt)
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
                positions=np.array(list(self.hand_points.values()))
                center=(positions.min(axis=0)+positions.max(axis=0))/2
                fit=self.settings['live_fit_scale']
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
            if self.settings['show_hand_skeleton']: self._hands3d(hands,fit)
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

    def _follow_point(self,current,target,dt):
        error=float(np.linalg.norm(target-current))
        hz=min(self.settings['live_response_max_hz'],self.settings['live_response_hz']+error*self.settings['live_response_gain'])
        return current+(1-math.exp(-math.tau*hz*max(0,dt)))*(target-current)

    def _draw_chemistry(self,snapshot,status,active,error,run_id,camera_index,replay,view,now,dt):
        w,h=self.size
        gl.glViewport(0,0,w,h); gl.glClearColor(*(c/255 for c in BG),1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT|gl.GL_DEPTH_BUFFER_BIT)
        fresh=snapshot is not None and active and now-snapshot.delivered_at<=self.settings['stale_after_s']
        hands=snapshot.hands if fresh else ()
        count=0
        identity=(run_id,snapshot.frame_id) if fresh else None
        if identity!=self.last_identity:
            present={hand.slot for hand in hands}
            for slot in self.last_slots-present: self.selectors[slot].reset()
            for hand in hands:
                if getattr(self,'selector_generation',{}).get(hand.slot)!=hand.generation: self.selectors[hand.slot].reset()
                self.selectors[hand.slot].update(hand.raw_landmarks or hand.landmarks,snapshot.image.shape[1]/snapshot.image.shape[0])
            self.last_identity=identity; self.last_slots=present
            self.selector_generation={hand.slot:hand.generation for hand in hands}
        count=sum(len(self.selectors[hand.slot].active) for hand in hands)
        self.chemistry.draw(snapshot,view,fresh,dt,run_id)
        control=self.chemistry.input; scene=self.chemistry.scene
        overlay_key=('chemistry',self.size,self.fullscreen,self.camera_visible,self.help_visible,active,error,status,
            tuple(self.chemistry.labels),scene.revision,scene.selected,scene.edit,scene.electrons,scene.message,len(hands),
            tuple((str(key),c.kind,c.paused) for key,c in control.claims.items()),
            tuple((key,v['controller'].suspended) for key,v in control.groups.items()),
            pygame.mouse.get_pos(),snapshot.frame_id if snapshot and self.camera_visible else None)
        if overlay_key!=self.last_overlay_key and (now-self.last_overlay_at>=1/self.settings['overlay_fps'] or not isinstance(self.last_overlay_key,tuple) or self.last_overlay_key[0]!='chemistry'):
            overlay=self._draw_ui(snapshot,status,active,error,run_id,camera_index,replay,view,hands,[None]*count,fresh,[])
            self.last_overlay_at=now; self.last_overlay_key=overlay_key
        else: overlay=None
        self._overlay(overlay)
        if self.capture_path:
            self._capture_back(self.capture_path); self.capture_path=None
        self.last_draw_cpu_ms=(time.monotonic()-now)*1000
        pygame.display.flip(); self.clock.tick(self.settings['render_fps'])
        return len(hands),count

    def _draw_ui(self,snapshot,status,active,error,run_id,camera_index,replay,view,hands,tips,fresh,world_labels):
        w,h=self.size; vx,vy,vw,vh=view; hh=header_height(w)
        overlay=self.overlay_surface; overlay.fill((0,0,0,0)); self.buttons=[]
        self._card(overlay,(10,8,w-20,hh-4),255,True)
        # Vector atom mark stays crisp at every window size.
        overlay.blit(atom_mark(self.settings['ui_card_supersample']),(18,hh//2-16))
        self._text(overlay,'DIP TOUCHLESS STEM',(68,24),17 if w>=1120 else 14,INK)
        self._text(overlay,'Không gian tương tác',(68,49),12,MUTED)
        # All names are preserved at minimum size; the badge is centered
        # in the available top-bar space, independently of the controls.
        controls=386; right=w-controls-20; left=275 if w>=1120 else 225
        badge=pygame.Rect(left,17,right-left-16,hh-20)
        self._card(overlay,badge,215)
        author_lines=AUTHORS.split(' | ')
        if w>=1120:
            author_lines=[author_lines[0],author_lines[1]+' | '+author_lines[2]]
        else:
            author_lines[0]=author_lines[0].replace('Nhóm tác giả: ','')
        fs=13 if w>=1120 else 12
        line_h=17; y=badge.centery-len(author_lines)*line_h//2
        for line in author_lines:
            label=self._label(line,fs,INK)
            overlay.blit(label,label.get_rect(center=(badge.centerx,y+line_h//2))); y+=line_h
        if w<1120: self._text(overlay,'Nhóm tác giả:',(badge.x+10,badge.y-12),12,MUTED)
        x=right; cy=hh//2-11
        for label,bw,action,on in (
            ('Dừng camera' if active else 'Bật camera',110,'toggle',active),
            ('Camera',70,'camera',self.camera_visible),
            ('Hướng dẫn',94,'help',self.help_visible),
            ('Thu khung' if self.fullscreen else 'Phóng to',94,'fullscreen',self.fullscreen)):
            self._button(overlay,label,(x,cy,bw,38),action,on); x+=bw+6
        sy=hh+15
        self._card(overlay,(20,sy-5,388,46),230)
        for label,x,bw,action in (('Khối 3D',26,112,'solid'),('Đầu ngón',144,114,'tips'),('Hóa học AR',264,138,'chemistry')):
            self._button(overlay,label,(x,sy, bw,36),action,self.mode==action)
        if self.mode=='solid':
            self._button(overlay,NAMES[KINDS.index(self.kind)],(424,sy,130,36),'menu')
            pygame.draw.polygon(overlay,MUTED,((539,sy+15),(547,sy+15),(543,sy+20)))
            label={'uniform':'Hai tay: đổi cỡ','stretch':'Hai tay: kéo dãn','distance':'Một tay: đổi cỡ','depth':'Một tay: tiến/lùi'}[self.grab.scale_mode]
            self._button(overlay,label,(566,sy,152,36),'scale_mode',self.grab.scale_mode!='uniform')
        self._button(overlay,'Về giữa cảnh' if self.mode=='chemistry' else 'Đặt lại góc nhìn',(w-168,sy,148,36),'reset')
        # Scene frame is only an outline, leaving the camera unobstructed.
        pygame.draw.rect(overlay,(53,105,124,190),view,1,border_radius=18)
        pygame.draw.line(overlay,ACCENT,(vx+20,vy),(vx+92,vy),2)
        pygame.draw.line(overlay,GOLD,(vx+vw-92,vy+vh-1),(vx+vw-20,vy+vh-1),2)
        if self.mode!='chemistry':
            feedback=self.grab.feedback if self.mode=='solid' and self.grab.slots else ('Đưa tay vào camera để bắt đầu' if not hands else 'Duỗi ngón để tạo hình' if self.mode=='tips' else 'Chụm cái–trỏ để cầm khối')
            self._text(overlay,feedback,(vx+18,vy+16),15,ACCENT if hands else MUTED)
        for label,pos in world_labels: self._text(overlay,label,pos,13,INK)
        if self.camera_visible:
            pw=min(300,w//4); px=w-20-pw; py=vy
            self._card(overlay,(px,py,pw,vh),245)
            self._text(overlay,'CAMERA',(px+18,py+16),13,ACCENT)
            cwmax=pw-28; chmax=min(220,int(cwmax*.75))
            if snapshot is not None and active:
                bgr=snapshot.image; ih,iw=bgr.shape[:2]
                ratio=min(cwmax/iw,chmax/ih); cw,ch=round(iw*ratio),round(ih*ratio)
                rect=(px+(pw-cw)//2,py+47+(chmax-ch)//2,cw,ch)
                preview_key=(run_id,snapshot.frame_id,cw,ch)
                if self.preview_key!=preview_key:
                    small=cv2.resize(bgr,(cw,ch),interpolation=cv2.INTER_AREA)
                    rgb=np.ascontiguousarray(cv2.cvtColor(small,cv2.COLOR_BGR2RGB))
                    if self.settings['mirror']: rgb=np.ascontiguousarray(rgb[:,::-1])
                    self.preview_surface=pygame.image.frombuffer(rgb.tobytes(),(cw,ch),'RGB').copy(); self.preview_key=preview_key
                overlay.blit(self.preview_surface,rect[:2])
                if fresh:
                    for hand in hands:
                        color=ACCENT if hand.slot==0 else GOLD
                        positions={l.index:preview_position(l,rect,self.settings['mirror']) for l in hand.landmarks}
                        for chain in ((0,1,2,3,4),(0,5,6,7,8),(5,9,10,11,12),(9,13,14,15,16),(13,17,18,19,20),(0,17)):
                            pygame.draw.lines(overlay,color,False,[positions[i] for i in chain],2)
                        for tip in self.selectors[hand.slot].active: pygame.draw.circle(overlay,color,positions[tip],5,2)
                        grip=self.grab.grips.get(hand.slot)
                        pygame.draw.circle(overlay,GOLD if grip and grip.held else color,positions[8],9,2)
                self._text(overlay,'Đang nhận tay' if hands else 'Chưa thấy tay',(px+18,py+chmax+65),17,ACCENT if hands else MUTED)
            else:
                self._wrap(overlay,'Bật camera để thao tác trực tiếp bằng tay.',(px+18,py+68),pw-36,17)
                self._button(overlay,'Đổi camera',(px+18,py+176,pw-36,36),'next_camera')
            if self.help_visible and self.mode!='chemistry' and vw<820:
                y=py+chmax+108
                self._text(overlay,'THAO TÁC',(px+18,y),13,ACCENT); y+=26
                lines=('Chụm để cầm; mở ngón để buông.','Một tay: dời và xoay.','Hai tay: tách / khép để đổi cỡ.') if self.mode=='solid' else ('Duỗi ngón: tạo đỉnh sống.','Gập ngón: bỏ đỉnh.','Hai tay: tạo hình cùng lúc.')
                for line in lines: y=self._wrap(overlay,line,(px+18,y),pw-36,13,INK)
                self._text(overlay,'H: ẩn hướng dẫn',(px+18,y+4),12,MUTED)
            else:
                self._wrap(overlay,'Đưa một hoặc hai tay vào khung. Tránh che đầu ngón và chồng hai lòng bàn tay.',(px+18,py+chmax+108),pw-36,15)
        if self.help_visible and self.mode!='chemistry' and not (self.camera_visible and vw<820):
            hw=min(342,vw-36); hx=vx+18; hy=vy+54
            self._card(overlay,(hx,hy,hw,184),231,True)
            self._text(overlay,'THAO TÁC BẰNG TAY',(hx+16,hy+15),13,ACCENT)
            instructions=('Chụm cái–trỏ để cầm; mở ngón để buông.\nMột tay di chuyển và xoay khối.\nHai tay kéo gần / xa để đổi cỡ và nghiêng.' if self.mode=='solid' else
                'Duỗi các ngón để tạo đỉnh sống.\nDùng tất cả ngón của một hoặc hai tay.\nGập ngón để bỏ đỉnh; xoay góc nhìn bằng chuột.')
            y=hy+45
            for line in instructions.split('\n'): y=self._wrap(overlay,line,(hx+16,y),hw-32,15,INK)
            self._text(overlay,'H: ẩn hướng dẫn  •  F11: phóng to',(hx+16,hy+157),12,MUTED)
        if self.menu and self.mode=='solid':
            for i,name in enumerate(NAMES): self._button(overlay,name,(424,sy+44+i*42,180,38),'kind:'+KINDS[i],self.kind==KINDS[i])
        self._card(overlay,(20,h-55,w-40,45),248)
        pygame.draw.circle(overlay,ACCENT if active else MUTED,(39,h-33),4)
        readiness=(('Camera đã mở' if fresh else 'Đang nhận hình…') if active and snapshot is not None else status)+('  •  '+str(len(hands))+' tay' if hands else '')
        self._text(overlay,readiness,(52,h-43),13,INK)
        self._text(overlay,'Xử lý trên máy',(w-132,h-43),12,MUTED)
        if self.mode=='chemistry':
            scene=self.chemistry.scene; selected=scene.selected
            label=scene.describe(scene.component(selected)) if selected in scene.atoms else scene.message
            claims=[claim for claim in self.chemistry.input.claims.values() if claim.kind in ('atom','group')]
            paused=any(group['controller'].suspended for group in self.chemistry.input.groups.values()) or any(claim.paused for claim in claims)
            if paused: label='Tạm mất tay • Vật thể giữ nguyên; đưa tay trở lại để tiếp tục'
            elif claims and scene.edit: label='Ghép/tách • Kéo xa để tháo • Mở ngón, thả gần để nối'
            elif len(claims)>1: label='Đang giữ bằng hai tay • Tách / khép để đổi cỡ • Mở ngón để buông'
            elif claims: label='Đang cầm • Chụm tay còn lại trong vùng trống để xoay / đổi cỡ'
            elif scene.electrons: label+=(' • Chọn Cầm cả khối để dùng hai tay đổi cỡ' if scene.edit else ' • Cầm nguyên tử, chụm tay còn lại để đổi cỡ cả lớp e')
            for text,pos in self.chemistry.labels:
                label_size=self.fonts[15].size(text)
                pygame.draw.rect(overlay,(8,20,30,205),(pos[0]-5,pos[1]-3,label_size[0]+10,label_size[1]+6),border_radius=6)
                self._text(overlay,text,pos,15,INK)
        else: label='Kéo chuột để xem góc khác  •  Cuộn để gần / xa  •  R để đặt lại'
        if error: label=error
        if replay: label='Phát lại  •  '+label
        # Clip long action/file errors to the footer, never into the scene.
        overlay.set_clip(pygame.Rect(52,h-23,w-90,18))
        self._text(overlay,label,(52,h-25),12,(245,178,137) if error else MUTED)
        overlay.set_clip(None)
        return overlay

    def _hands3d(self,hands,fit):
        """Illustrative joint/bone volume, no invented missing landmarks."""
        gl.glEnable(gl.GL_LIGHTING)
        for hand in hands:
            p=np.array([self.hand_points[(hand.slot,hand.generation,i)] for i in range(21)])
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
            matrices,lengths=bone_transforms(p)
            radius=self.settings['hand_bone_radius']/fit
            for matrix,length in zip(matrices,lengths):
                gl.glPushMatrix(); gl.glMultMatrixf(matrix.T.astype(np.float32))
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

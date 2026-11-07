"""One-window OpenGL scene with Vietnamese, responsive presentation controls."""
import math
import os
from pathlib import Path
import time
from functools import lru_cache
import cv2
import numpy as np
import pygame
from pygame._sdl2.video import Window
from OpenGL import GL as gl, GLU as glu
from .geometry import (Tip, FingerSelection, live_mesh, solid_mesh,
                       world_position, preview_position, project_live_tip, TIPS)
from .geometry import bone_transforms
from .manipulation import GrabController
from .camera_space import CameraCover
from .chemistry_view import CameraChemistryView
from .physics_view import PhysicsView
from .solid_palette import SolidPalette, tip_summary
from .screen_sprites import ScreenSprites
from .home_hub import VirtualHomeHub
from .theme import BG, PANEL, INK, MUTED, ACCENT, GOLD, AUTHORS, card, glass, outline, atom_mark, header_height, scene_rect, fit_desktop_window

COLORS = ((.20,.72,.90),(.28,.46,.82),(.48,.87,.94),(.47,.60,.79))
KINDS = ('cube','tetra','octa','sphere')
NAMES = ('Lập phương','Tứ diện','Bát diện','Hình cầu')

class SubmissionRenderer:
    def __init__(self, settings):
        self.settings = settings
        self.size = tuple(settings['window'])
        self.windowed = self.size
        self.initial_window_fit=True
        self.windowed_position=None
        self.display_index=0
        self.restore_window_position=False
        self._window=None
        self.fullscreen = bool(settings.get('fullscreen', False) or settings.get('window_fullscreen', False))
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
        self.solid_palette = SolidPalette(settings)
        self.sprites = ScreenSprites(settings['floating_cache_capacity'])
        self.palette_cursor_points = {}
        self.solid_context = None
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
        self.droidcam_dialog=False
        self.droidcam_field='host'
        self.droidcam_host=str(settings.get('droidcam_wifi_host',''))
        self.droidcam_port=str(settings.get('droidcam_wifi_port',4747))
        self.chemistry=CameraChemistryView(settings,self)
        self.physics=PhysicsView(settings,self)
        self.home_hub=VirtualHomeHub(settings)
        self.geometry_dropdown_open=False
        self.solid_camera_texture=None
        self.solid_camera_key=None
        self.solid_camera_size=None
        self._solid_btn_target=None
        self._solid_btn_dwell=0.0

    def open(self):
        os.environ.setdefault('SDL_WINDOWS_DPI_AWARENESS',self.settings['windows_dpi_awareness'])
        pygame.init()
        pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE,24)
        self._set_display()
        if not self.fullscreen and self.settings.get('window_maximized', False) and self._window:
            self._window.maximize()
            pygame.event.pump()
            new_size = pygame.display.get_window_size()
            if new_size != self.size:
                self.size = new_size
                self.windowed = self.size
                self._set_display()
                if self._window:
                    self._window.maximize()
                    pygame.event.pump()
            if self._window:
                self._window.resizable = False
        pygame.display.set_caption('DIP Touchless STEM • Đồ án')
        font_path = Path('C:/Windows/Fonts/segoeui.ttf')
        self.fonts = {size:pygame.font.Font(str(font_path) if font_path.is_file() else None,size)
                      for size in (11,12,13,14,15,17,20,24,28,32)}
        self.quadric = glu.gluNewQuadric()
        self.clock = pygame.time.Clock()
        self.unit_sphere = gl.glGenLists(1)
        gl.glNewList(self.unit_sphere,gl.GL_COMPILE)
        glu.gluSphere(self.quadric,1,32,24); gl.glEndList()
        self.unit_bone=gl.glGenLists(1)
        gl.glNewList(self.unit_bone,gl.GL_COMPILE)
        glu.gluCylinder(self.quadric,1,1,1,10,1); gl.glEndList()
        self.chemistry.open()
        self.physics.open()
        self.solid_lists={}
        for kind in KINDS:
            display_list=gl.glGenLists(1)
            gl.glNewList(display_list,gl.GL_COMPILE)
            self._mesh(solid_mesh(kind),smooth=kind=='sphere',edges=kind!='sphere')
            gl.glEndList()
            self.solid_lists[kind]=display_list

    def _set_display(self):
        self.sprites.close()
        self._suspend_solid()
        self.chemistry.close()
        self.physics.close()
        for display_list in getattr(self,'solid_lists',{}).values():
            gl.glDeleteLists(display_list,1)
        if hasattr(self,'texture'):
            gl.glDeleteTextures([self.texture])
        if hasattr(self,'solid_camera_texture') and self.solid_camera_texture is not None:
            gl.glDeleteTextures([self.solid_camera_texture]); self.solid_camera_texture=None
        if hasattr(self,'unit_sphere'): gl.glDeleteLists(self.unit_sphere,1)
        if hasattr(self,'unit_bone'): gl.glDeleteLists(self.unit_bone,1)
        # SDL desktop fullscreen handles monitor bounds/origin and taskbar;
        # merely enlarging a borderless window leaves its old screen offset.
        flags = pygame.OPENGL | pygame.DOUBLEBUF | (pygame.NOFRAME if self.fullscreen else pygame.RESIZABLE)
        if self.fullscreen:
            desktops = pygame.display.get_desktop_sizes()
            desktop = desktops[min(self.display_index, len(desktops) - 1)]
            self.size = desktop
            if self.initial_window_fit:
                self.windowed = fit_desktop_window(tuple(self.settings['window']), desktop, self.settings['window_desktop_margin'])
                self.initial_window_fit = False
        elif self.initial_window_fit:
            desktops = pygame.display.get_desktop_sizes()
            desktop = desktops[min(self.display_index, len(desktops) - 1)]
            self.size = fit_desktop_window(self.size, desktop, self.settings['window_desktop_margin'])
            self.windowed = self.size
            self.initial_window_fit = False
        for samples in (self.settings['render_msaa_samples'],0):
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS,int(samples>0))
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES,samples)
            try:
                pygame.display.set_mode(self.size,flags,display=self.display_index)
                break
            except pygame.error:
                if not samples: raise
        # Pygame 2.6.1 stores a raw pointer to this wrapper in SDL's
        # "pg_window" data. Keep it alive until the display is replaced/closed;
        # a temporary wrapper leaves event.get() with a dangling pointer.
        self._window=Window.from_display_module()
        window=self._window
        if self.fullscreen:
            window.set_fullscreen(desktop=True)
        elif self.restore_window_position:
            if self.windowed_position is not None:
                window.position=self.windowed_position
            self.restore_window_position=False
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
        self.basic_preview_key=None
        self.last_draw_at=None
        if hasattr(self,'solid_lists'):
            self.chemistry.open()
            self.physics.open()
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
        self.sprites.close()
        self.chemistry.close()
        self.physics.close()
        for display_list in getattr(self,'solid_lists',{}).values():
            gl.glDeleteLists(display_list,1)
        if hasattr(self,'texture'):
            gl.glDeleteTextures([self.texture])
        if hasattr(self,'solid_camera_texture') and self.solid_camera_texture is not None:
            gl.glDeleteTextures([self.solid_camera_texture]); self.solid_camera_texture=None
        if hasattr(self,'quadric'):
            glu.gluDeleteQuadric(self.quadric)
        if hasattr(self,'unit_sphere'): gl.glDeleteLists(self.unit_sphere,1)
        if hasattr(self,'unit_bone'): gl.glDeleteLists(self.unit_bone,1)
        self._label.cache_clear()
        glass.cache_clear()
        outline.cache_clear()
        atom_mark.cache_clear()
        pygame.quit()
        self._window=None

    def reset(self):
        if self.mode=='physics':
            self.physics.command('reset')
            self.physics.command('frame')
            return
        if self.mode=='chemistry':
            self.chemistry.input.command('frame'); self.chemistry.input.command('compact'); return
        self.yaw=32.; self.pitch=20.; self.zoom=1.
        self.object_yaw=self.object_pitch=0.; self.object_scale=1.
        self.grab.reset()
        self.fit_center=None; self.fit_identity=None

    def _suspend_solid(self):
        self.dragging=False; self.grab.release(); self.solid_palette.suspend()
        self.palette_cursor_points.clear(); self.solid_context=None
        self._solid_btn_target=None; self._solid_btn_dwell=0.0; self._solid_btn_rect=None
        self._solid_cursor_pt=None; self._solid_ui_busy=False

    def enter_basic(self, mode):
        if self.mode != mode:
            self._suspend_solid(); self.chemistry.input.release(); self.physics.suspend()
            self.last_identity=None
        self.mode=mode; self.menu=False
        if mode in ('solid', 'tracking'):
            self.camera_visible = True

    def events(self):
        actions = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                actions.append('quit')
            elif event.type == pygame.VIDEORESIZE and not self.fullscreen and (event.w,event.h)!=self.size and (event.w,event.h)==pygame.display.get_window_size():
                if self.settings.get('window_maximized', False):
                    if event.w < self.size[0] or event.h < self.size[1]:
                        continue
                desktops=pygame.display.get_desktop_sizes()
                desktop=desktops[min(self.display_index,len(desktops)-1)]
                minimum=fit_desktop_window((960,660),desktop,self.settings['window_desktop_margin'])
                self.size=(max(minimum[0],event.w),max(minimum[1],event.h)); self.windowed=self.size; self._set_display()
            elif event.type == pygame.KEYDOWN:
                key = event.key
                if self.droidcam_dialog:
                    if key==pygame.K_ESCAPE:
                        self.droidcam_dialog=False
                    elif key==pygame.K_TAB:
                        self.droidcam_field='port' if self.droidcam_field=='host' else 'host'
                    elif key in (pygame.K_RETURN,pygame.K_KP_ENTER):
                        actions.append('droidcam_connect')
                    elif key==pygame.K_BACKSPACE:
                        if self.droidcam_field=='host': self.droidcam_host=self.droidcam_host[:-1]
                        else: self.droidcam_port=self.droidcam_port[:-1]
                    else:
                        ch=event.unicode
                        if ch and len(ch)==1:
                            if self.droidcam_field=='host' and (ch.isalnum() or ch in '.-') and len(self.droidcam_host)<64:
                                self.droidcam_host+=ch
                            elif self.droidcam_field=='port' and ch.isdigit() and len(self.droidcam_port)<5:
                                self.droidcam_port+=ch
                    continue
                if key == pygame.K_ESCAPE:
                    if self.solid_palette.open:
                        self.solid_palette.transition(False)
                    elif self.fullscreen:
                        self.toggle_fullscreen()
                    elif self.menu:
                        self.menu=False
                    else:
                        actions.append('quit')
                elif key in (pygame.K_RETURN,pygame.K_SPACE):
                    if self.mode=='physics' and key==pygame.K_SPACE: self.physics.command('run')
                    else: actions.append('toggle')
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
                    elif self.mode=='physics': self.physics.command('step')
                    else: self.cycle_scale_mode()
                elif key == pygame.K_p:
                    self.enter_chemistry()
                elif key == pygame.K_v:
                    self.enter_physics()
                elif self.mode=='chemistry' and key==pygame.K_b:
                    self.chemistry.input.command('toggle_panel')
                elif self.mode=='chemistry' and key in (pygame.K_e,pygame.K_o,pygame.K_t,pygame.K_z,pygame.K_y,pygame.K_BACKSPACE,pygame.K_l,pygame.K_j):
                    self.chemistry.input.command({pygame.K_e:'edit',pygame.K_o:'electrons',pygame.K_t:'table',pygame.K_z:'undo',
                        pygame.K_y:'redo',pygame.K_BACKSPACE:'delete',pygame.K_l:'save',pygame.K_j:'load'}[key])
                elif key == pygame.K_TAB:
                    if self.mode=='solid': self.enter_chemistry()
                    elif self.mode=='chemistry': self.enter_physics()
                    else: self.enter_basic('solid')
                elif pygame.K_1 <= key <= pygame.K_4:
                    self.enter_basic('solid'); self.kind=KINDS[key-pygame.K_1]
                    if self.solid_palette.open: self.solid_palette.transition(False)
            elif event.type == pygame.MOUSEWHEEL:
                if self.mode=='chemistry' and not self.droidcam_dialog: self.chemistry.wheel(event.y,pygame.mouse.get_pos())
                elif self.mode=='physics' and not self.droidcam_dialog: self.physics.wheel(event.y,pygame.mouse.get_pos())
                elif not self.droidcam_dialog and not self.solid_palette.open: self.zoom=float(np.clip(self.zoom*math.exp(event.y*.08),.55,1.8))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button==1:
                view=scene_rect(self.size,self.camera_visible,self.mode)
                home_action=self.home_hub.handle_click(event.pos,self.size,header_height(self.size[0]),view=view)
                if home_action:
                    if home_action in ('solid', 'tracking'): self.enter_basic(home_action)
                    elif home_action=='chemistry': self.enter_chemistry()
                    elif home_action=='physics': self.enter_physics()
                    continue
                if self.home_hub.expanded:
                    continue
                if self.mode=='solid' and self.solid_palette.open and not self.droidcam_dialog:
                    action=next((a for rect,a in self.solid_palette.targets if rect.collidepoint(event.pos)),None)
                    if action:
                        if action in KINDS: self.kind=action
                        self.solid_palette.transition(False)
                    continue
                action=next((a for rect,a in reversed(self.buttons) if rect.collidepoint(event.pos)),None)
                if self.droidcam_dialog:
                    if action=='droidcam_host': self.droidcam_field='host'
                    elif action=='droidcam_port': self.droidcam_field='port'
                    elif action=='droidcam_cancel': self.droidcam_dialog=False
                    elif action in ('droidcam_connect','webcam_connect'): actions.append(action)
                    continue
                if action:
                    if action=='geom_dropdown':
                        self.geometry_dropdown_open=not getattr(self,'geometry_dropdown_open',False)
                    elif action.startswith('kind:'):
                        self.enter_basic('solid'); self.kind=action.split(':')[1]; self.menu=False; self.geometry_dropdown_open=False
                    elif action in ('solid','tips'):
                        self.enter_basic(action); self.geometry_dropdown_open=False
                    elif action=='chemistry':
                        self.enter_chemistry(); self.geometry_dropdown_open=False
                    elif action=='physics':
                        self.enter_physics(); self.geometry_dropdown_open=False
                    elif action=='camera':
                        self.camera_visible=not self.camera_visible
                    elif action=='droidcam':
                        self.droidcam_dialog=True; self.droidcam_field='host'
                        self._suspend_solid(); self.chemistry.input.release()
                        self.physics.suspend()
                    elif action=='help':
                        self.help_visible=not self.help_visible
                    elif action=='fullscreen':
                        self.toggle_fullscreen()
                    elif action=='reset':
                        self.reset()
                    elif action in ('toggle_panel','panel_reset'):
                        self.chemistry.input.command(action)
                    elif action=='scale_mode':
                        self.cycle_scale_mode()
                    elif action=='menu':
                        self.menu=not self.menu
                    else:
                        actions.append(action)
                else:
                    self.geometry_dropdown_open=False
                    if self.mode=='chemistry': self.chemistry.mouse('down',event.pos)
                    elif self.mode=='physics': self.physics.mouse('down',event.pos)
                    else: self.dragging=True
            elif event.type == pygame.MOUSEBUTTONUP:
                self.dragging=False
                if self.mode=='chemistry' and event.button==1 and not self.droidcam_dialog: self.chemistry.mouse('up',event.pos)
                if self.mode=='physics' and event.button==1 and not self.droidcam_dialog: self.physics.mouse('up',event.pos)
            elif event.type == pygame.MOUSEMOTION and self.mode=='chemistry' and not self.droidcam_dialog:
                self.chemistry.mouse('move',event.pos)
            elif event.type == pygame.MOUSEMOTION and self.mode=='physics' and not self.droidcam_dialog:
                self.physics.mouse('move',event.pos)
            elif event.type == pygame.MOUSEMOTION and self.dragging:
                self.yaw+=event.rel[0]*.3; self.pitch=float(np.clip(self.pitch+event.rel[1]*.3,-65,65))
        return actions

    def toggle_fullscreen(self):
        window=self._window
        if not self.fullscreen:
            self.windowed=pygame.display.get_window_size()
            self.windowed_position=window.position
            self.display_index=window.display_index
        else:
            window.set_windowed()
            self.restore_window_position=True
        self.fullscreen=not self.fullscreen
        self.size=pygame.display.get_desktop_sizes()[self.display_index] if self.fullscreen else self.windowed
        self._set_display()

    def enter_chemistry(self):
        self._suspend_solid()
        self.mode='chemistry'; self.camera_visible=False; self.menu=False
        self.physics.suspend()
        self.grab.release(); self.chemistry.input.release()

    def enter_physics(self):
        self._suspend_solid()
        self.mode='physics'; self.camera_visible=False; self.menu=False
        self.grab.release(); self.chemistry.input.release(); self.physics.suspend()

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

    def _mouse_pos(self):
        try:
            if pygame.display.get_init():
                return pygame.mouse.get_pos()
        except pygame.error:
            pass
        return (0, 0)

    def _button(self,surface,label,rect,action,active=False):
        rect=pygame.Rect(rect)
        finger_hover=getattr(self,'_solid_btn_target',None)==action
        hovered=rect.collidepoint(self._mouse_pos()) or finger_hover
        surface.blit(glass(rect.size,250,10,active or hovered,self.settings['ui_card_supersample']),rect)
        surface.blit(outline(rect.size,ACCENT if active else (83,119,139),samples=self.settings['ui_card_supersample']),rect)
        if active: pygame.draw.line(surface,GOLD,(rect.x+14,rect.bottom-2),(rect.right-14,rect.bottom-2),2)
        rendered=self._label(label,14,INK)
        surface.blit(rendered,rendered.get_rect(center=rect.center))
        self.buttons.append((rect,action))

    def _card(self,surface,rect,alpha=235,bright=False):
        card(surface,rect,alpha,bright,self.settings['ui_card_supersample'])

    def draw(self,snapshot,status,*,active=False,error=None,run_id='',camera_index=0,replay=False,source_kind='webcam'):
        w,h=self.size
        view=scene_rect(self.size,self.camera_visible,self.mode)
        vx,vy,vw,vh=view
        now=time.monotonic()
        draw_started=time.perf_counter()
        draw_dt=0 if self.last_draw_at is None else draw_started-self.last_draw_at
        self.last_draw_at=draw_started
        self._update_home_hub(draw_dt,snapshot,active,now,view=view)
        if self.mode=='chemistry':
            return self._draw_chemistry(snapshot,status,active,error,run_id,camera_index,replay,source_kind,view,now,draw_dt,draw_started)
        if self.mode=='physics':
            return self._draw_physics(snapshot,status,active,error,run_id,camera_index,replay,source_kind,view,now,draw_dt,draw_started)
        context=(self.mode,run_id,view,snapshot.image.shape[:2] if snapshot is not None else None)
        if context!=self.solid_context:
            self._suspend_solid(); self.solid_context=context; self.last_identity=None
        px=math.radians(self.pitch); yx=math.radians(self.yaw)
        rx=np.array(((1,0,0),(0,math.cos(px),-math.sin(px)),(0,math.sin(px),math.cos(px))))
        ry=np.array(((math.cos(yx),0,math.sin(yx)),(0,1,0),(-math.sin(yx),0,math.cos(yx))))
        view_rotation=rx@ry
        gl.glViewport(0,0,w,h)
        gl.glClearColor(*(c/255 for c in BG),1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glEnable(gl.GL_SCISSOR_TEST); gl.glScissor(vx,h-vy-vh,vw,vh)
        gl.glViewport(vx,h-vy-vh,vw,vh)
        if snapshot is not None and self.camera_visible and active:
            gl.glDisable(gl.GL_DEPTH_TEST); gl.glDisable(gl.GL_LIGHTING)
            gl.glMatrixMode(gl.GL_PROJECTION); gl.glLoadIdentity(); gl.glOrtho(0,1,1,0,-1,1)
            gl.glMatrixMode(gl.GL_MODELVIEW); gl.glLoadIdentity()
            self._draw_solid_camera_backdrop(snapshot,run_id,vw,vh)
            gl.glEnable(gl.GL_DEPTH_TEST)
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
        if self.mode != 'tracking':
            self._floor()
        fresh = snapshot is not None and active and not self.droidcam_dialog and time.monotonic()-snapshot.delivered_at <= self.settings['stale_after_s']
        hands=snapshot.hands if fresh else ()
        identity=(run_id,snapshot.frame_id) if fresh else None
        tips=[]
        present={hand.slot for hand in hands}
        for s in self.last_slots-present:
            self.selectors[s].reset()
        if self.mode=='solid' and fresh and not self.solid_palette.open:
            self._update_solid_finger_buttons(draw_dt, hands, view=view, snapshot=snapshot)
            if getattr(self, '_solid_ui_busy', False):
                self.grab.release()
        elif self.mode!='solid' or not fresh:
            self._solid_btn_target=None; self._solid_btn_dwell=0.0; self._solid_btn_rect=None
            self._solid_cursor_pt=None; self._solid_ui_busy=False
        if identity != self.last_identity:
            for hand in hands:
                # Angle hysteresis cannot transfer to a new hand generation.
                if hand.generation not in (getattr(self,'selector_generation',{}).get(hand.slot),):
                    self.selectors[hand.slot].reset()
                self.selectors[hand.slot].update(hand.raw_landmarks or hand.landmarks,snapshot.image.shape[1]/snapshot.image.shape[0])
            if self.mode=='solid' and fresh:
                aspect=snapshot.image.shape[1]/snapshot.image.shape[0]
                ui_busy=getattr(self,'_solid_ui_busy',False)
                if not self.solid_palette.open and not ui_busy:
                    self.grab.translation_gain=1.45/max(0.5,self.zoom)
                    self.grab.update(self.solid_palette.grab_hands(hands,aspect),snapshot.timestamp_s,aspect,view_rotation)
                chosen=self.solid_palette.update(hands,snapshot.timestamp_s,aspect,view,
                    busy=ui_busy or self.dragging or bool(self.grab.slots) or any(g.held or g.pending_since is not None for g in self.grab.grips.values()) or self.menu)
                if chosen in KINDS: self.kind=chosen
                if chosen is not None or self.solid_palette.open:
                    self.dragging=False; self.grab.release()
        if not fresh or self.mode!='solid':
            self.grab.release()
            if self.mode=='solid': self.solid_palette.suspend(); self.palette_cursor_points.clear()
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
        hand_targets={(hand.slot,hand.generation,l.index):np.array(world_position(l,snapshot.image.shape[1]/snapshot.image.shape[0],self.settings))
                      for hand in hands for l in hand.landmarks}
        self.hand_points={key:self._follow_point(self.hand_points.get(key,value),value,draw_dt)
                          for key,value in hand_targets.items()}
        self.live_points={key:self.hand_points[key] for key in targets}
        tips=[Tip(key[0],key[2],tuple(value)) for key,value in self.live_points.items()]
        world_labels=[]
        if self.mode=='tracking':
            if snapshot is not None and self.camera_visible and active and hands:
                self._draw_solid_hand_keypoints(view, snapshot, hands, draw_dt)
        elif self.mode=='solid':
            pose=self.grab.pose
            vertices=np.array(solid_mesh(self.kind).vertices)*(pose.scale*pose.stretch)
            vertices=vertices@pose.rotation.T+pose.position
            self._shadow(vertices)
            gl.glPushMatrix(); gl.glTranslatef(*pose.position)
            matrix=np.eye(4); matrix[:3,:3]=pose.rotation
            gl.glMultMatrixf(matrix.T.astype(np.float32))
            gl.glScalef(*(pose.scale*pose.stretch))
            gl.glCallList(self.solid_lists[self.kind]); gl.glPopMatrix()
            if snapshot is not None and self.camera_visible and active and hands:
                self._draw_solid_hand_keypoints(view, snapshot, hands, draw_dt)
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
                # Analytic projection avoids driver matrix queries per fingertip.
                projected=project_live_tip(tip.position,view,view_rotation,self.fit_center,fit,self.zoom)
                if projected is not None:
                    x,y=projected
                    world_labels.append((f'{tip.hand+1}.{TIPS.index(tip.index)+1}',(int(x)+8,int(y)-10),COLORS[tip.hand]))
            gl.glPopMatrix()
        gl.glDisable(gl.GL_SCISSOR_TEST)
        overlay_key=(self.size,self.camera_visible,self.help_visible,self.menu,self.mode,self.kind,
                     self.fullscreen,self.grab.scale_mode,active,error,status,camera_index,source_kind,self.droidcam_dialog,
                     self.droidcam_host,self.droidcam_port,self.droidcam_field,fresh,len(hands),
                     self.grab.feedback,tuple(bool(self.grab.grips.get(s) and self.grab.grips[s].held) for s in (0,1)),
                     self.home_hub.expanded,tuple(self.home_hub.pos) if self.home_hub.pos is not None else None,
                     self.home_hub.dwell_target,round(self.home_hub.dwell_time,2) if self.home_hub.dwell_target else None,getattr(self,'geometry_dropdown_open',False),
                     getattr(self,'_solid_btn_target',None),
                     tip_summary(tips,getattr(self,'live_mesh_mode','points')) if self.mode=='tips' else None)
        hover=next((action for rect,action in reversed(self.buttons) if rect.collidepoint(self._mouse_pos())),None)
        dynamic=hover
        # Static controls upload only on a semantic change. Side preview/mouse
        # hover remain bounded; fingertip labels now follow independently.
        if (overlay_key!=self.last_overlay_key or
            (dynamic!=getattr(self,'basic_dynamic_key',None) and now-self.last_overlay_at>=1/self.settings['overlay_fps'])):
            overlay=self._draw_ui(snapshot,status,active,error,run_id,camera_index,replay,source_kind,view,hands,tips,fresh,[])
            self.last_overlay_at=now; self.last_overlay_key=overlay_key
            self.basic_dynamic_key=dynamic
        else:
            overlay=None
        self.sprites.begin(self.size)
        gl.glEnable(gl.GL_SCISSOR_TEST); gl.glScissor(vx,h-vy-vh,vw,vh)
        for text,position,color in world_labels:
            rgb=tuple(round((.45+.55*c)*255) for c in color)
            key=('tip',text,rgb); tile=None
            if key not in self.sprites.items:
                glyph=self._label(text,13,rgb)
                tile=pygame.Surface((glyph.get_width()+6,glyph.get_height()+2),pygame.SRCALPHA)
                pygame.draw.rect(tile,(*BG,225),tile.get_rect(),border_radius=4)
                tile.blit(glyph,(3,1))
            self.sprites.draw(key,tile,position)
        gl.glDisable(gl.GL_SCISSOR_TEST)
        # Guidance/cards stay above labels, as with the original raster UI.
        self._overlay(overlay)
        if self.mode=='solid': self._draw_solid_button_feedback()
        self._draw_basic_preview(snapshot,view,hands,fresh,active,run_id,now)
        gl.glEnable(gl.GL_SCISSOR_TEST); gl.glScissor(vx,h-vy-vh,vw,vh)
        if self.mode=='solid': self._draw_solid_palette(view,draw_dt)
        gl.glDisable(gl.GL_SCISSOR_TEST)
        if self.capture_path:
            self._capture_back(self.capture_path)
            self.capture_path=None
        self.last_draw_cpu_ms=(time.perf_counter()-draw_started)*1000
        pygame.display.flip()
        self.clock.tick(self.settings['render_fps'])
        return len(hands),len(tips)

    def _follow_point(self,current,target,dt):
        error=float(np.linalg.norm(target-current))
        hz=min(self.settings['live_response_max_hz'],self.settings['live_response_hz']+error*self.settings['live_response_gain'])
        return current+(1-math.exp(-math.tau*hz*max(0,dt)))*(target-current)

    def _draw_basic_preview(self,snapshot,view,hands,fresh,active,run_id,now):
        if not self.camera_visible or snapshot is None or not active: return
        w,h=self.size; vx,vy,vw,vh=view
        pw=min(300,w//4); px=w-20-pw
        cwmax=pw-28; chmax=min(220,int(cwmax*.75),max(40,vh-180))
        ih,iw=snapshot.image.shape[:2]; ratio=min(cwmax/iw,chmax/ih)
        cw,ch=round(iw*ratio),round(ih*ratio)
        rect=(px+(pw-cw)//2,vy+47+(chmax-ch)//2,cw,ch)
        semantic=(rect,fresh,tuple((hand.slot,hand.generation,tuple(sorted(self.selectors[hand.slot].active)),
            bool(self.grab.grips.get(hand.slot) and self.grab.grips[hand.slot].held)) for hand in hands))
        key=(run_id,snapshot.frame_id,semantic)
        changed=(semantic!=getattr(self,'basic_preview_semantic',None)
                 or now-getattr(self,'basic_preview_at',-math.inf)>=1/self.settings['overlay_fps'])
        if key!=getattr(self,'basic_preview_key',None) and changed:
            small=cv2.resize(snapshot.image,(cw,ch),interpolation=cv2.INTER_AREA)
            rgb=cv2.cvtColor(small,cv2.COLOR_BGR2RGB)
            if self.settings['mirror']: rgb=rgb[:,::-1]
            surface=pygame.image.frombuffer(np.ascontiguousarray(rgb).tobytes(),(cw,ch),'RGB').copy()
            for hand in hands:
                color=ACCENT if hand.slot==0 else GOLD
                positions={l.index:preview_position(l,(0,0,cw,ch),self.settings['mirror']) for l in hand.landmarks}
                for chain in ((0,1,2,3,4),(0,5,6,7,8),(5,9,10,11,12),(9,13,14,15,16),(13,17,18,19,20),(0,17)):
                    pygame.draw.lines(surface,color,False,[positions[i] for i in chain],2)
                for tip in self.selectors[hand.slot].active: pygame.draw.circle(surface,color,positions[tip],5,2)
                grip=self.grab.grips.get(hand.slot)
                pygame.draw.circle(surface,GOLD if grip and grip.held else color,positions[8],9,2)
            self.basic_preview_surface=surface; self.basic_preview_key=key
            self.basic_preview_semantic=semantic; self.basic_preview_at=now
        pos=(-2000,-2000) if self.mode in ('solid', 'tracking') else rect[:2]
        self.sprites.draw(('basic-preview',),self.basic_preview_surface,pos,version=self.basic_preview_key)

    def _draw_solid_palette(self,view,dt):
        palette=self.solid_palette; x,y,w,h=view
        if palette.open:
            rect=palette.rect
            key=('solid-palette',rect.size,self.kind,bool(palette.anchors))
            surface=None
            if key not in self.sprites.items:
                surface=glass(rect.size,250,16,True,self.settings['ui_card_supersample']).copy()
                self._text(surface,'CHỌN KHỐI',(12,12),15,ACCENT)
                for target,action in palette.targets:
                    local=target.move(-rect.x,-rect.y)
                    if action=='close':
                        label=self._label('×',20,INK)
                    else:
                        on=action==self.kind
                        surface.blit(glass(local.size,250,10,on,self.settings['ui_card_supersample']),local)
                        surface.blit(outline(local.size,ACCENT if on else MUTED,samples=self.settings['ui_card_supersample']),local)
                        label=self._label(NAMES[KINDS.index(action)],15,INK)
                    surface.blit(label,label.get_rect(center=local.center))
                text='Mở ngón, di tay để nhắm lại' if palette.anchors else 'Giữ 1 giây hoặc chụm để chọn'
                self._text(surface,text,(12,rect.h-29),12,MUTED)
            gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA,gl.GL_ONE_MINUS_SRC_ALPHA)
            gl.glColor4f(0,0,0,.30); gl.glBegin(gl.GL_QUADS)
            for point in ((x,y),(x+w,y),(x+w,y+h),(x,y+h)): gl.glVertex2f(*point)
            gl.glEnd(); gl.glDisable(gl.GL_BLEND)
            self.sprites.draw(key,surface,rect.topleft)
            for target,action in palette.targets:
                if action not in palette.hover.values(): continue
                gl.glColor3f(*(c/255 for c in GOLD)); gl.glLineWidth(2); gl.glBegin(gl.GL_LINE_LOOP)
                for p in (target.topleft,target.topright,target.bottomright,target.bottomleft): gl.glVertex2f(*p)
                gl.glEnd()
            targets={(k,palette.hands[k].generation):np.array((x+p[0]*w,y+p[1]*h))
                     for k,p in palette.pointers.items() if k in palette.hands}
        else:
            targets={}
            if palette.shortcut.progress:
                _,p,progress=palette.shortcut.progress
                targets[('summon',0)]=np.array((x+p[0]*w,y+p[1]*h))
        alpha=-math.expm1(-math.tau*self.settings['solid_cursor_response_hz']*max(0,dt))
        self.palette_cursor_points={k:self.palette_cursor_points.get(k,p)+(p-self.palette_cursor_points.get(k,p))*alpha for k,p in targets.items()}
        for token,point in self.palette_cursor_points.items():
            slot=token[0]; state=palette.tap.states.get(slot); dwell=palette.dwell.states.get(slot)
            progress=(state.progress if state and state.phase=='press' else dwell.progress if dwell else 0.)
            if slot=='summon': progress=palette.shortcut.progress[2]
            if state and state.locked:
                point=targets[token]; self.palette_cursor_points[token]=point
            gl.glColor3f(*(c/255 for c in (GOLD if state and state.locked else ACCENT)))
            gl.glLineWidth(2); gl.glBegin(gl.GL_LINE_LOOP)
            for i in range(40):
                a=math.tau*i/40; gl.glVertex2f(point[0]+12*math.cos(a),point[1]+12*math.sin(a))
            gl.glEnd()
            if progress:
                gl.glLineWidth(4); gl.glBegin(gl.GL_LINE_STRIP)
                for i in range(int(progress*48)+1):
                    a=-math.pi/2+math.tau*i/48; gl.glVertex2f(point[0]+16*math.cos(a),point[1]+16*math.sin(a))
                gl.glEnd()
        gl.glLineWidth(1)

    def _draw_chemistry(self,snapshot,status,active,error,run_id,camera_index,replay,source_kind,view,now,dt,draw_started):
        w,h=self.size
        gl.glViewport(0,0,w,h); gl.glClearColor(*(c/255 for c in BG),1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT|gl.GL_DEPTH_BUFFER_BIT)
        fresh=snapshot is not None and active and not self.droidcam_dialog and now-snapshot.delivered_at<=self.settings['stale_after_s']
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
        semantic_key=('chemistry',self.size,self.fullscreen,self.camera_visible,self.help_visible,active,error,status,
            scene.revision,scene.selected,scene.edit,scene.electrons,scene.message,
            tuple((str(key),c.kind,c.paused) for key,c in control.claims.items()),
            tuple((key,v['controller'].suspended) for key,v in control.groups.items()),
            self._chemistry_pause_message(),
            control.page,control.template_page,
            source_kind,self.droidcam_dialog,self.droidcam_host,self.droidcam_port,self.droidcam_field)
        # Camera pixels and atom-label motion are drawn independently. A fresh
        # background frame must not upload a window-sized UI texture by itself.
        preview=(snapshot.frame_id,len(hands)) if snapshot and self.camera_visible else None
        overlay_key=semantic_key+(pygame.mouse.get_pos(),preview,self.home_hub.expanded,tuple(self.home_hub.pos) if self.home_hub.pos is not None else None,self.home_hub.dwell_target,round(self.home_hub.dwell_time,2) if self.home_hub.dwell_target else None)
        if overlay_key!=self.last_overlay_key and (semantic_key!=getattr(self,'_chemistry_semantic_key',None) or now-self.last_overlay_at>=1/self.settings['overlay_fps'] or not isinstance(self.last_overlay_key,tuple) or self.last_overlay_key[0]!='chemistry'):
            overlay=self._draw_ui(snapshot,status,active,error,run_id,camera_index,replay,source_kind,view,hands,[None]*count,fresh,[])
            self.last_overlay_at=now; self.last_overlay_key=overlay_key
            self._chemistry_semantic_key=semantic_key
        else: overlay=None
        self._overlay(overlay)
        self.chemistry.draw_labels()
        if self.capture_path:
            self._capture_back(self.capture_path); self.capture_path=None
        self.last_draw_cpu_ms=(time.perf_counter()-draw_started)*1000
        pygame.display.flip(); self.clock.tick(self.settings['render_fps'])
        return len(hands),count

    def _chemistry_pause_message(self):
        control=self.chemistry.input
        paused={key:c for key,c in control.claims.items() if c.kind in ('atom','group') and c.paused}
        if paused:
            if any(key not in control.pointers for key in paused):
                return 'Tạm mất tay • Vật thể giữ nguyên; đưa tay trở lại để tiếp tục'
            return 'Đang xác nhận buông • Vật thể giữ nguyên'
        if any(group['controller'].suspended for group in control.groups.values()):
            return 'Hai điểm giữ quá gần • Tách hai tay rõ hơn để tiếp tục'
        return None

    def _draw_physics(self,snapshot,status,active,error,run_id,camera_index,replay,source_kind,view,now,dt,started):
        w,h=self.size
        gl.glViewport(0,0,w,h); gl.glClearColor(*(c/255 for c in BG),1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT|gl.GL_DEPTH_BUFFER_BIT)
        fresh=snapshot is not None and active and not self.droidcam_dialog and now-snapshot.delivered_at<=self.settings['stale_after_s']
        self.physics.draw(snapshot,view,fresh,dt,run_id)
        hands=snapshot.hands if fresh else ()
        key=('physics',self.size,self.fullscreen,self.camera_visible,self.help_visible,active,error,status,
            self.physics.model.message,self.physics.page_key,source_kind,self.droidcam_dialog,self.droidcam_host,self.droidcam_port,self.droidcam_field,
            snapshot.frame_id if snapshot and self.camera_visible else None,
            self.home_hub.expanded,tuple(self.home_hub.pos) if self.home_hub.pos is not None else None,self.home_hub.dwell_target,round(self.home_hub.dwell_time,2) if self.home_hub.dwell_target else None)
        if key!=self.last_overlay_key:
            overlay=self._draw_ui(snapshot,status,active,error,run_id,camera_index,replay,source_kind,view,hands,[],fresh,[])
            self.last_overlay_key=key
        else: overlay=None
        self._overlay(overlay)
        if self.capture_path: self._capture_back(self.capture_path); self.capture_path=None
        self.last_draw_cpu_ms=(time.perf_counter()-started)*1000
        pygame.display.flip(); self.clock.tick(self.settings['render_fps'])
        return len(hands),0

    def _author_badge_labels(self,badge,fs):
        """Keep the author heading and every name inside the badge at small sizes."""
        lines=AUTHORS.split(' | ')
        combined=lines[1]+' | '+lines[2]
        if self.fonts[fs].size(combined)[0]<=badge.width-20:
            lines=[lines[0],combined]
        else:
            lines=['Nhóm tác giả:',lines[0].replace('Nhóm tác giả: ',''),*lines[1:]]
        line_h=max(self.fonts[fs].get_height(),self.fonts[fs].get_linesize())
        y=badge.centery-len(lines)*line_h//2
        labels=[]
        for line in lines:
            glyph=self._label(line,fs,INK)
            labels.append((glyph,glyph.get_rect(center=(badge.centerx,y+line_h//2))))
            y+=line_h
        return labels

    def _draw_ui(self,snapshot,status,active,error,run_id,camera_index,replay,source_kind,view,hands,tips,fresh,world_labels):
        w,h=self.size; vx,vy,vw,vh=view; hh=header_height(w)
        overlay=self.overlay_surface; overlay.fill((0,0,0,0)); self.buttons=[]
        self._card(overlay,(10,8,w-20,hh-4),255,True)
        # Vector atom mark stays crisp at every window size.
        overlay.blit(atom_mark(self.settings['ui_card_supersample']),(18,hh//2-16))
        self._text(overlay,'DIP TOUCHLESS STEM',(68,24),17 if w>=1120 else 14,INK)
        self._text(overlay,'Không gian tương tác',(68,49),12,MUTED)
        # All names are preserved at minimum size; the badge is centered
        # in the available top-bar space, independently of the controls.
        top_controls=[
            ('Dừng camera' if active else 'Bật camera',110,'toggle',active),
            ('Camera',70,'camera',self.camera_visible),
        ]
        if not replay:
            top_controls.append(('DroidCam',72,'droidcam',source_kind=='droidcam_wifi'))
        top_controls.extend((
            ('Hướng dẫn',94,'help',self.help_visible),
            ('Thu khung' if self.fullscreen else 'Phóng to',94,'fullscreen',self.fullscreen),
        ))
        controls=sum(item[1] for item in top_controls)+6*(len(top_controls)-1)
        compact=w<960
        right=w-controls-20; left=275 if w>=1120 else 225
        badge=pygame.Rect(left,17,(w-20 if compact else right-16)-left,60 if compact else hh-20)
        self._card(overlay,badge,215)
        fs=13 if w>=1120 else 12
        for label,rect in self._author_badge_labels(badge,fs): overlay.blit(label,rect)
        x=(w-controls)//2 if compact else right; cy=92 if compact else hh//2-11
        for label,bw,action,on in top_controls:
            self._button(overlay,label,(x,cy,bw,38),action,on); x+=bw+6
        if self.mode=='solid':
            panel_x=20; panel_y=vy+12; panel_w=210
            is_open=getattr(self,'geometry_dropdown_open',False)
            panel_h=268 if is_open else 145
            self._card(overlay,(panel_x,panel_y,panel_w,panel_h),238)
            self._text(overlay,'HÌNH HỌC • 3D',(panel_x+14,panel_y+12),12,ACCENT)
            cur_name=NAMES[KINDS.index(self.kind)]
            btn_y=panel_y+34
            self._button(overlay,f'{cur_name}  ▾',(panel_x+10,btn_y,panel_w-20,32),'geom_dropdown',is_open)
            opt_y=btn_y+36
            if is_open:
                for i,k in enumerate(KINDS):
                    self._button(overlay,NAMES[i],(panel_x+10,opt_y+i*26,panel_w-20,24),f'kind:{k}',self.kind==k)
                opt_y+=4*26+6
                # Vách ngăn phân tách danh sách hình khối và các tác vụ bên dưới
                pygame.draw.line(overlay,(50,85,110,180),(panel_x+12,opt_y),(panel_x+panel_w-12,opt_y),1)
                pygame.draw.line(overlay,(80,140,175,130),(panel_x+12,opt_y+1),(panel_x+panel_w-12,opt_y+1),1)
                opt_y+=10
            scale_label={'uniform':'Đổi cỡ vật','stretch':'Kéo dãn vật','distance':'Đổi cỡ 1 tay','depth':'Tiến/lùi 1 tay'}[self.grab.scale_mode]
            self._button(overlay,scale_label,(panel_x+10,opt_y,panel_w-20,28),'scale_mode',self.grab.scale_mode!='uniform')
            self._button(overlay,'Đặt lại vật thể',(panel_x+10,opt_y+32,panel_w-20,28),'reset')
        # Scene frame is only an outline, leaving the camera unobstructed.
        pygame.draw.rect(overlay,(53,105,124,190),view,1,border_radius=18)
        pygame.draw.line(overlay,ACCENT,(vx+20,vy),(vx+92,vy),2)
        pygame.draw.line(overlay,GOLD,(vx+vw-92,vy+vh-1),(vx+vw-20,vy+vh-1),2)
        if self.mode not in ('solid', 'chemistry', 'physics', 'tracking'):
            feedback=self.grab.feedback if self.mode=='solid' and self.grab.slots else ('Đưa tay vào camera để bắt đầu' if not hands else 'Duỗi ngón để tạo hình' if self.mode=='tips' else 'Chụm cái–trỏ để cầm khối')
            if self.mode=='tips': feedback=tip_summary(tips,getattr(self,'live_mesh_mode','points'))
            self._text(overlay,feedback,(vx+18,vy+16),15,ACCENT if hands else MUTED)
        for label,pos in world_labels: self._text(overlay,label,pos,13,INK)
        if self.camera_visible and self.mode not in ('solid', 'chemistry', 'physics', 'tracking'):
            pw=min(300,w//4); px=w-20-pw; py=vy
            self._card(overlay,(px,py,pw,vh),245)
            previous_clip=overlay.get_clip(); overlay.set_clip(pygame.Rect(px,py,pw,vh))
            self._text(overlay,'CAMERA',(px+18,py+16),13,ACCENT)
            cwmax=pw-28; chmax=min(220,int(cwmax*.75),max(40,vh-180))
            if snapshot is not None and active:
                bgr=snapshot.image; ih,iw=bgr.shape[:2]
                ratio=min(cwmax/iw,chmax/ih); cw,ch=round(iw*ratio),round(ih*ratio)
                rect=(px+(pw-cw)//2,py+47+(chmax-ch)//2,cw,ch)
                preview_key=(run_id,snapshot.frame_id,cw,ch)
                if self.mode in ('chemistry','physics') and self.preview_key!=preview_key:
                    small=cv2.resize(bgr,(cw,ch),interpolation=cv2.INTER_AREA)
                    rgb=np.ascontiguousarray(cv2.cvtColor(small,cv2.COLOR_BGR2RGB))
                    if self.settings['mirror']: rgb=np.ascontiguousarray(rgb[:,::-1])
                    self.preview_surface=pygame.image.frombuffer(rgb.tobytes(),(cw,ch),'RGB').copy(); self.preview_key=preview_key
                if self.mode in ('chemistry','physics'): overlay.blit(self.preview_surface,rect[:2])
                if fresh and self.mode in ('chemistry','physics'):
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
                self._button(overlay,'Đổi camera',(px+18,py+min(176,max(0,vh-52)),pw-36,36),'next_camera')
            if self.help_visible and self.mode!='chemistry' and vw<820 and vh>=240:
                y=py+chmax+108
                self._text(overlay,'THAO TÁC',(px+18,y),13,ACCENT); y+=26
                if self.mode=='physics':
                    lines=('Chụm điểm vàng: kéo lực/vật.','Mở ngón: buông/thả.','SPACE: Chạy/Dừng.','R: Đặt lại ban đầu.')
                elif self.mode=='solid':
                    lines=self._solid_instructions()
                else:
                    lines=('Duỗi ngón: tạo đỉnh sống.','Gập ngón: bỏ đỉnh.','Hai tay: tạo hình cùng lúc.','Gần đồng phẳng: hình tạo thành mặt.')
                if vh<400:
                    lines=('SPACE: Chạy/Dừng. R: Đặt lại.',) if self.mode=='physics' else (('Chụm: cầm. Mở: buông.',) if self.mode=='solid' else ('Duỗi: thêm. Gập: bỏ đỉnh.',))
                for line in lines: y=self._wrap(overlay,line,(px+18,y),pw-36,13,INK)
                if vh>=400: self._text(overlay,'H: ẩn hướng dẫn',(px+18,y+4),12,MUTED)
            elif vh>=240:
                self._wrap(overlay,'Đưa một hoặc hai tay vào khung. Tránh che đầu ngón và chồng hai lòng bàn tay.',(px+18,py+chmax+108),pw-36,15)
            overlay.set_clip(previous_clip)
        if self.help_visible and self.mode not in ('chemistry','physics','tracking') and not (self.camera_visible and vw<820 and self.mode not in ('solid', 'chemistry', 'physics', 'tracking')):
            hw=min(342,vw-36); hx=vx+(222 if self.mode=='solid' else 18); hy=vy+(12 if self.mode=='solid' else 54)
            self._card(overlay,(hx,hy,hw,184),231,True)
            self._text(overlay,'THAO TÁC BẰNG TAY',(hx+16,hy+15),13,ACCENT)
            instructions=('\n'.join(self._solid_instructions()) if self.mode=='solid' else
                'Duỗi: tạo đỉnh; gập: bỏ đỉnh.\nDùng các ngón của một hoặc hai tay.\nGần đồng phẳng: hình tạo thành mặt.\nKéo chuột để nhìn từ góc khác.')
            y=hy+45
            for line in instructions.split('\n'): y=self._wrap(overlay,line,(hx+16,y),hw-32,15,INK)
            self._text(overlay,'H: ẩn hướng dẫn  •  F11: phóng to',(hx+16,hy+157),12,MUTED)
        if self.menu and self.mode=='solid':
            for i,name in enumerate(NAMES): self._button(overlay,name,(26 if w<1200 else 518,vy+(90 if w<1200 else 44)+i*42,180,38),'kind:'+KINDS[i],self.kind==KINDS[i])
        footer=pygame.Rect(20,h-55,w-40,45)
        self._card(overlay,footer,248)
        if self.mode not in ('chemistry','physics'):
            pygame.draw.circle(overlay,ACCENT if active else MUTED,(39,h-33),4)
            readiness=(('Camera đã mở' if fresh else 'Đang nhận hình…') if active and snapshot is not None else status)+('  •  '+str(len(hands))+' tay' if hands else '')
            self._text(overlay,readiness,(52,h-43),13,INK)
            self._text(overlay,'Xử lý trên máy',(w-132,h-43),12,MUTED)
        if self.mode=='chemistry':
            scene=self.chemistry.scene; selected=scene.selected
            label=scene.describe(scene.component(selected)) if selected in scene.atoms else scene.message
            claims=[claim for claim in self.chemistry.input.claims.values() if claim.kind in ('atom','group')]
            paused=self._chemistry_pause_message()
            if paused: label=paused
            elif claims and scene.edit:
                current=scene.describe(scene.component(selected)) if selected in scene.atoms else scene.message
                label='Ghép/tách • '+current+' • Kéo xa để tháo • Thả gần để nối'
            elif len(claims)>1: label='Đang giữ bằng hai tay • Tách / khép để đổi cỡ • Mở ngón để buông'
            elif claims: label='Đang cầm • Chụm tay còn lại trong vùng trống để xoay / đổi cỡ'
            elif scene.electrons: label+=(' • Chọn Cầm cả khối để dùng hai tay đổi cỡ' if scene.edit else ' • Cầm nguyên tử, chụm tay còn lại để đổi cỡ cả lớp e')
        elif self.mode=='physics': label=self.physics.model.message
        elif self.mode=='tracking': label='Đưa bàn tay lên trước camera để hiển thị 21 điểm mốc nhận diện (Hand Landmarks)'
        else: label='Kéo chuột để xem góc khác  •  Cuộn để gần / xa  •  R để đặt lại'
        if error: label=error
        if replay: label='Phát lại  •  '+label
        if self.mode in ('chemistry','physics'):
            max_label_width=max(1,footer.width-28)
            label_font=next((size for size in (20,17,15,13,12)
                if self.fonts[size].size(label)[0]<=max_label_width),12)
            rendered=self._label(label,label_font,(245,178,137) if error else INK)
            overlay.set_clip(footer.inflate(-12,-6))
            overlay.blit(rendered,rendered.get_rect(center=footer.center))
            overlay.set_clip(None)
        else:
            overlay.set_clip(pygame.Rect(52,h-23,w-90,18))
            self._text(overlay,label,(52,h-25),12,(245,178,137) if error else MUTED)
            overlay.set_clip(None)
        if self.droidcam_dialog and not replay:
            self._draw_droidcam_dialog(overlay,source_kind,error)
        self.home_hub.draw(overlay,self.fonts,self.mode,view=view)
        return overlay

    def _update_home_hub(self,dt,snapshot,active,now,view=None):
        fresh=snapshot is not None and active and not self.droidcam_dialog and now-snapshot.delivered_at<=self.settings['stale_after_s']
        hands=snapshot.hands if fresh else ()
        mouse_pos=None; mouse_down=False
        try:
            if pygame.display.get_init():
                cur_mouse=pygame.mouse.get_pos()
                mouse_down=bool(pygame.mouse.get_pressed()[0])
                if mouse_down or cur_mouse!=getattr(self,'_last_mouse_pos',None):
                    self._last_mouse_pos=cur_mouse
                    self._mouse_active_time=now
                if mouse_down or not hands or (now-getattr(self,'_mouse_active_time',0.0)<2.0):
                    mouse_pos=cur_mouse
        except (pygame.error, IndexError):
            pass
        source_aspect=snapshot.image.shape[1]/snapshot.image.shape[0] if snapshot is not None else None
        home_action=self.home_hub.update(dt,self.size,header_height(self.size[0]),
                                         hands=hands,
                                         mouse_pos=mouse_pos,
                                         mouse_down=mouse_down,
                                         mirror=self.settings['mirror'],
                                         view=view,
                                         source_aspect=source_aspect)
        if home_action:
            if home_action in ('solid', 'tracking'): self.enter_basic(home_action)
            elif home_action=='chemistry': self.enter_chemistry()
            elif home_action=='physics': self.enter_physics()

    def _draw_solid_camera_backdrop(self,snapshot,run_id,vw,vh):
        if not hasattr(self,'solid_camera_texture') or self.solid_camera_texture is None:
            self.solid_camera_texture=gl.glGenTextures(1)
            self.solid_camera_key=None; self.solid_camera_size=None
        source_aspect=snapshot.image.shape[1]/snapshot.image.shape[0] if snapshot is not None else 4/3
        cover=CameraCover(source_aspect,vw/max(1,vh))
        key=(run_id,snapshot.frame_id)
        if key!=getattr(self,'solid_camera_key',None):
            image=snapshot.image
            if self.settings['mirror']: image=image[:,::-1]
            image=np.ascontiguousarray(image)
            gl.glBindTexture(gl.GL_TEXTURE_2D,self.solid_camera_texture)
            gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_MIN_FILTER,gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_MAG_FILTER,gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_WRAP_S,gl.GL_CLAMP_TO_EDGE)
            gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_WRAP_T,gl.GL_CLAMP_TO_EDGE)
            gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT,1)
            size=(image.shape[1],image.shape[0])
            if size!=getattr(self,'solid_camera_size',None):
                gl.glTexImage2D(gl.GL_TEXTURE_2D,0,gl.GL_RGB,*size,0,gl.GL_BGR,gl.GL_UNSIGNED_BYTE,image)
            else:
                gl.glTexSubImage2D(gl.GL_TEXTURE_2D,0,0,0,*size,gl.GL_BGR,gl.GL_UNSIGNED_BYTE,image)
            self.solid_camera_size=size; self.solid_camera_key=key
        gl.glEnable(gl.GL_TEXTURE_2D); gl.glBindTexture(gl.GL_TEXTURE_2D,self.solid_camera_texture); gl.glColor4f(1,1,1,1)
        gl.glBegin(gl.GL_QUADS)
        for (u,v),(a,b) in zip(cover.uv,((0,0),(1,0),(1,1),(0,1))):
            gl.glTexCoord2f(u,v); gl.glVertex2f(a,b)
        gl.glEnd(); gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA,gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glColor4f(0.02,0.05,0.08,0.0 if self.mode=='tracking' else 0.30)
        gl.glBegin(gl.GL_QUADS)
        for pt in ((0,0),(1,0),(1,1),(0,1)): gl.glVertex2f(*pt)
        gl.glEnd(); gl.glDisable(gl.GL_BLEND)

    def _update_solid_finger_buttons(self,dt,hands,view=None,snapshot=None):
        w,h=self.size
        active_btn=None; active_rect=None; is_pinch=False; cursor_pt=None
        if view is not None and snapshot is not None and hands:
            vx,vy,vw,vh=view
            source_aspect=snapshot.image.shape[1]/snapshot.image.shape[0]
            cover=CameraCover(source_aspect,vw/max(1,vh))
            hands_to_use=[cover.hand(h) for h in hands]
            use_vw,use_vh=vw,vh
            use_vx,use_vy=vx,vy
        else:
            hands_to_use=hands
            use_vw,use_vh=float(w),float(h)
            use_vx,use_vy=0.0,0.0
        any_pinch=False
        finger_cache=getattr(self,'_solid_finger_pts',{})
        new_cache={}
        alpha=1.0-math.exp(-math.tau*18.0*max(0.0,dt)) if dt>0.0 else 1.0
        current_target=getattr(self,'_solid_btn_target',None)
        current_rect=next((r for r,a in reversed(self.buttons) if a==current_target),None) if current_target else None

        for hand in hands_to_use:
            if not getattr(hand,'landmarks',None) or len(hand.landmarks)!=21: continue
            tip=hand.landmarks[8]; thumb=hand.landmarks[4]
            raw_tx=use_vx+(1.0-tip.x if self.settings['mirror'] else tip.x)*use_vw
            raw_ty=use_vy+tip.y*use_vh
            raw_hx=use_vx+(1.0-thumb.x if self.settings['mirror'] else thumb.x)*use_vw
            raw_hy=use_vy+thumb.y*use_vh
            gen=getattr(hand,'generation',0)
            k8=(hand.slot,gen,8); k4=(hand.slot,gen,4)
            p8=finger_cache.get(k8,(raw_tx,raw_ty))
            p4=finger_cache.get(k4,(raw_hx,raw_hy))
            a8=min(1.0,alpha+math.hypot(raw_tx-p8[0],raw_ty-p8[1])/24.0)
            a4=min(1.0,alpha+math.hypot(raw_hx-p4[0],raw_hy-p4[1])/24.0)
            tx=p8[0]+(raw_tx-p8[0])*a8; ty=p8[1]+(raw_ty-p8[1])*a8
            hx=p4[0]+(raw_hx-p4[0])*a4; hy=p4[1]+(raw_hy-p4[1])*a4
            new_cache[k8]=(tx,ty); new_cache[k4]=(hx,hy)
            pinch_dist=math.hypot(tx-hx,ty-hy)
            if pinch_dist<48.0: any_pinch=True

            # Stabilize pointer against finger-pull when closing a pinch over a button
            anchor_key=(hand.slot,gen,'anchor')
            if pinch_dist<64.0 and current_rect is not None and anchor_key in finger_cache:
                ax,ay=finger_cache[anchor_key]
                if math.hypot(tx-ax,ty-ay)<42.0:
                    tx=ax*0.72+tx*0.28; ty=ay*0.72+ty*0.28
                    new_cache[anchor_key]=(ax,ay)
                else:
                    new_cache[anchor_key]=(tx,ty)
            else:
                new_cache[anchor_key]=(tx,ty)

            pt=(tx,ty)
            for rect,action in reversed(self.buttons):
                if rect.collidepoint(pt):
                    active_btn=action; active_rect=rect; cursor_pt=pt
                    if pinch_dist<48.0: is_pinch=True
                    break
            # Magnetic hysteresis: keep current button if within a 10px/6px comfort border
            if active_btn is None and current_rect is not None and current_rect.inflate(14,10).collidepoint(pt):
                active_btn=current_target; active_rect=current_rect; cursor_pt=pt
                if pinch_dist<48.0: is_pinch=True
            if active_btn: break

        is_open=getattr(self,'geometry_dropdown_open',False)
        panel_zone=pygame.Rect(12,(view[1] if view else 80)+4,230,284 if is_open else 160)
        in_panel=any(panel_zone.collidepoint(pt) for k,pt in new_cache.items() if len(k)==3 and k[2]==8)
        if cursor_pt is None and in_panel:
            cursor_pt=next((pt for k,pt in new_cache.items() if len(k)==3 and k[2]==8),None)
        self._solid_finger_pts=new_cache
        self._solid_cursor_pt=cursor_pt
        self._solid_ui_busy=bool(active_btn is not None or in_panel or getattr(self,'_solid_disarmed_btn',None) is not None)

        if not any_pinch:
            self._solid_pinch_latched=False

        # Anti-cancel / Re-entry requirement:
        disarmed_btn=getattr(self,'_solid_disarmed_btn',None)
        if disarmed_btn is not None:
            disarmed_rect=getattr(self,'_solid_disarmed_rect',None)
            finger_inside=(active_btn==disarmed_btn) or (disarmed_rect is not None and cursor_pt is not None and disarmed_rect.inflate(8,6).collidepoint(cursor_pt))
            if not finger_inside:
                self._solid_disarmed_btn=None
                self._solid_disarmed_rect=None
            else:
                self._solid_btn_target=None
                self._solid_btn_dwell=0.0
                self._solid_btn_rect=None
                return

        if active_btn is not None:
            if active_btn==current_target:
                self._solid_btn_dwell=getattr(self,'_solid_btn_dwell',0.0)+dt
                self._solid_btn_rect=active_rect
                self._solid_switch_btn=None; self._solid_switch_dwell=0.0
            else:
                # Smooth transition between adjacent buttons without 1-frame flicker
                if current_target is not None and getattr(self,'_solid_btn_dwell',0.0)>0.06:
                    if getattr(self,'_solid_switch_btn',None)==active_btn:
                        self._solid_switch_dwell=getattr(self,'_solid_switch_dwell',0.0)+dt
                    else:
                        self._solid_switch_btn=active_btn; self._solid_switch_dwell=dt
                    if self._solid_switch_dwell>=0.045 or is_pinch:
                        self._solid_btn_target=active_btn; self._solid_btn_dwell=self._solid_switch_dwell
                        self._solid_btn_rect=active_rect
                        self._solid_switch_btn=None; self._solid_switch_dwell=0.0
                else:
                    self._solid_btn_target=active_btn; self._solid_btn_dwell=dt
                    self._solid_btn_rect=active_rect
                    self._solid_switch_btn=None; self._solid_switch_dwell=0.0
            can_pinch=is_pinch and not getattr(self,'_solid_pinch_latched',False)
            if can_pinch or self._solid_btn_dwell>=0.65:
                act=self._solid_btn_target
                rect=active_rect
                self._solid_btn_target=None; self._solid_btn_dwell=0.0; self._solid_btn_rect=None
                if can_pinch: self._solid_pinch_latched=True
                self._solid_disarmed_btn=act
                self._solid_disarmed_rect=rect
                self._trigger_solid_action(act)
        else:
            # Smooth dwell decay instead of instant zero reset on brief hand tremor
            dwell=getattr(self,'_solid_btn_dwell',0.0)-dt*2.2
            if dwell>0.0 and current_target is not None:
                self._solid_btn_dwell=dwell
                self._solid_btn_rect=current_rect
            else:
                self._solid_btn_target=None; self._solid_btn_dwell=0.0; self._solid_btn_rect=None

    def _draw_solid_button_feedback(self):
        target=getattr(self,'_solid_btn_target',None)
        dwell=getattr(self,'_solid_btn_dwell',0.0)
        rect=getattr(self,'_solid_btn_rect',None)
        cursor_pt=getattr(self,'_solid_cursor_pt',None)
        if (target is None or dwell<=0.0 or rect is None) and cursor_pt is None:
            return
        w,h=self.size
        gl.glViewport(0,0,w,h)
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glDisable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA,gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glMatrixMode(gl.GL_PROJECTION); gl.glPushMatrix(); gl.glLoadIdentity()
        gl.glOrtho(0,w,h,0,-1,1)
        gl.glMatrixMode(gl.GL_MODELVIEW); gl.glPushMatrix(); gl.glLoadIdentity()
        if target is not None and dwell>0.0 and rect is not None:
            frac=min(1.0,dwell/0.65)
            x0=rect.x+6.0; x1=x0+(rect.w-12.0)*frac
            y0=rect.bottom-4.5; y1=rect.bottom-1.5
            gl.glColor4f(*(c/255 for c in GOLD),0.95)
            gl.glBegin(gl.GL_QUADS)
            gl.glVertex2f(x0,y0); gl.glVertex2f(x1,y0); gl.glVertex2f(x1,y1); gl.glVertex2f(x0,y1)
            gl.glEnd()
        if cursor_pt is not None:
            cx,cy=cursor_pt
            gl.glColor4f(*(c/255 for c in ACCENT),0.85)
            gl.glLineWidth(2.0); gl.glBegin(gl.GL_LINE_LOOP)
            for i in range(32):
                a=math.tau*i/32.0
                gl.glVertex2f(cx+10.0*math.cos(a),cy+10.0*math.sin(a))
            gl.glEnd()
            if dwell>0.0:
                frac=min(1.0,dwell/0.65)
                gl.glColor4f(*(c/255 for c in GOLD),0.95)
                gl.glLineWidth(3.0); gl.glBegin(gl.GL_LINE_STRIP)
                steps=max(2,int(frac*36)+1)
                for i in range(steps):
                    a=-math.pi/2+math.tau*(i/36.0)
                    gl.glVertex2f(cx+13.5*math.cos(a),cy+13.5*math.sin(a))
                gl.glEnd()
        gl.glLineWidth(1.0)
        gl.glMatrixMode(gl.GL_PROJECTION); gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_MODELVIEW); gl.glPopMatrix()
        gl.glDisable(gl.GL_BLEND)

    def _trigger_solid_action(self,action):
        if action=='geom_dropdown':
            self.geometry_dropdown_open=not getattr(self,'geometry_dropdown_open',False)
        elif action and action.startswith('kind:'):
            self.kind=action.split(':')[1]; self.geometry_dropdown_open=False
        elif action=='scale_mode': self.cycle_scale_mode()
        elif action=='reset': self.reset()

    def _draw_solid_hand_keypoints(self,view,snapshot,hands,dt=0.0):
        if not hands or snapshot is None:
            self._solid_screen_kp={}
            return
        vx,vy,vw,vh=view
        source_aspect=snapshot.image.shape[1]/snapshot.image.shape[0]
        cover=CameraCover(source_aspect,vw/max(1,vh))
        kp_cache=getattr(self,'_solid_screen_kp',{})
        new_kp={}
        alpha=1.0-math.exp(-math.tau*20.0*max(0.0,dt)) if dt>0.0 else 1.0
        gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glDisable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA,gl.GL_ONE_MINUS_SRC_ALPHA)
        gl.glMatrixMode(gl.GL_PROJECTION); gl.glPushMatrix(); gl.glLoadIdentity()
        gl.glOrtho(0,vw,vh,0,-1,1)
        gl.glMatrixMode(gl.GL_MODELVIEW); gl.glPushMatrix(); gl.glLoadIdentity()
        for hand in hands:
            if not getattr(hand,'landmarks',None) or len(hand.landmarks)!=21: continue
            covered=cover.hand(hand)
            gen=getattr(hand,'generation',0)
            coords={}
            for l in covered.landmarks:
                lx=1.0-l.x if self.settings['mirror'] else l.x
                tx=lx*vw
                ty=l.y*vh
                key=(hand.slot,gen,l.index)
                prev=kp_cache.get(key)
                if prev is None:
                    sx,sy=tx,ty
                else:
                    step_a=min(1.0,alpha+math.hypot(tx-prev[0],ty-prev[1])/20.0)
                    sx=prev[0]+(tx-prev[0])*step_a
                    sy=prev[1]+(ty-prev[1])*step_a
                new_kp[key]=(sx,sy)
                coords[l.index]=(sx,sy)
        self._solid_screen_kp=new_kp
        for hand in hands:
            if not getattr(hand,'landmarks',None) or len(hand.landmarks)!=21: continue
            gen=getattr(hand,'generation',0)
            coords={i:new_kp[(hand.slot,gen,i)] for i in range(21) if (hand.slot,gen,i) in new_kp}
            if len(coords)!=21: continue
            grip=self.grab.grips.get(hand.slot)
            is_held=grip and grip.held
            base_col=(1.0,0.78,0.22) if is_held else ((0.20,0.80,1.0) if hand.slot==0 else (1.0,0.60,0.20))
            # Bones skeleton lines
            gl.glLineWidth(3.0)
            gl.glColor4f(*base_col,0.82)
            gl.glBegin(gl.GL_LINES)
            for chain in ((0,1,2,3,4),(0,5,6,7,8),(5,9,10,11,12),(9,13,14,15,16),(13,17,18,19,20),(0,17)):
                for a,b in zip(chain[:-1],chain[1:]):
                    gl.glVertex2f(*coords[a]); gl.glVertex2f(*coords[b])
            gl.glEnd()
            # Joint nodes (non-tips)
            gl.glPointSize(7.0)
            gl.glColor4f(0.92,0.96,1.0,0.95)
            gl.glBegin(gl.GL_POINTS)
            for idx,pt in coords.items():
                if idx not in (4,8,12,16,20): gl.glVertex2f(*pt)
            gl.glEnd()
            # Fingertips outer glow
            gl.glPointSize(12.0)
            gl.glColor4f(*base_col,1.0)
            gl.glBegin(gl.GL_POINTS)
            for tip_idx in (4,8,12,16,20): gl.glVertex2f(*coords[tip_idx])
            gl.glEnd()
            # Fingertips inner high-tech core
            gl.glPointSize(5.0)
            gl.glColor4f(1.0,1.0,1.0,1.0)
            gl.glBegin(gl.GL_POINTS)
            for tip_idx in (4,8,12,16,20): gl.glVertex2f(*coords[tip_idx])
            gl.glEnd()
            # Pinch connection & indicator between thumb (4) and index (8)
            p4=np.array(coords[4]); p8=np.array(coords[8])
            p_dist=float(np.linalg.norm(p4-p8))
            if p_dist<52.0:
                gl.glLineWidth(3.5)
                gl.glColor4f(1.0,0.88,0.25,0.95)
                gl.glBegin(gl.GL_LINES)
                gl.glVertex2f(*p4); gl.glVertex2f(*p8)
                gl.glEnd()
                mid=(p4+p8)*0.5
                gl.glPointSize(14.0)
                gl.glColor4f(1.0,0.85,0.20,0.95)
                gl.glBegin(gl.GL_POINTS)
                gl.glVertex2f(*mid)
                gl.glEnd()
                gl.glPointSize(6.0)
                gl.glColor4f(1.0,1.0,1.0,1.0)
                gl.glBegin(gl.GL_POINTS)
                gl.glVertex2f(*mid)
                gl.glEnd()
        gl.glMatrixMode(gl.GL_PROJECTION); gl.glPopMatrix()
        gl.glMatrixMode(gl.GL_MODELVIEW); gl.glPopMatrix()
        gl.glDisable(gl.GL_BLEND)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_LIGHTING)

    def _solid_instructions(self):
        mode=self.grab.scale_mode
        extra={'uniform':'Hai tay: tách / khép để đổi cỡ.',
               'stretch':'Hai tay: kéo dãn theo một trục.',
               'distance':'Một tay: gần / xa để đổi cỡ.',
               'depth':'Một tay: gần / xa để tiến / lùi.'}[mode]
        return ('Chụm: cầm. Mở: buông. Một tay dời / xoay.',extra,
                'Xòe tay ở mép trống để chọn khối.')

    def _physics_instructions(self):
        return (
            '• Chụm ngón vào điểm vàng: Kéo lực F / chỉnh góc / kéo vật thể.',
            '• Mở ngón tay: Buông lực hoặc thả rơi vật thể.',
            '• Phím SPACE: Bắt đầu / Tạm dừng mô phỏng vật lý.',
            '• Nút "Đặt lại ban đầu" (phím R): Khôi phục vật về trạng thái gốc.',
            '• Phím S: Chạy từng bước (step) để quan sát chi tiết chuyển động.',
            '• Bảng bên trái: Tab [Bài học] lý thuyết SI, Tab [Điều chỉnh] thông số.',
            '• Tab [Đo / Lưu]: Bật hiển thị Vector lực, Đồ thị, Năng lượng.',
            '• Hai tay chụm vùng trống: Xoay và đổi góc nhìn không gian 3D.'
        )

    def _draw_droidcam_dialog(self,overlay,source_kind,error=None):
        w,h=self.size
        rect=pygame.Rect(0,0,min(520,w-80),286); rect.center=(w//2,h//2)
        shade=pygame.Surface(self.size,pygame.SRCALPHA); shade.fill((3,9,15,145)); overlay.blit(shade,(0,0))
        self._card(overlay,rect,252,True)
        self._text(overlay,'DROIDCAM WI-FI',(rect.x+24,rect.y+20),20,ACCENT)
        self._text(overlay,'Nhập Wi-Fi IP và port đang hiện trên điện thoại',(rect.x+24,rect.y+51),13,MUTED)
        host_rect=pygame.Rect(rect.x+24,rect.y+88,rect.width-160,42)
        port_rect=pygame.Rect(rect.right-124,rect.y+88,100,42)
        for field,box,value,title in (('host',host_rect,self.droidcam_host,'IP'),('port',port_rect,self.droidcam_port,'Port')):
            active=self.droidcam_field==field
            overlay.blit(glass(box.size,250,8,active,self.settings['ui_card_supersample']),box)
            overlay.blit(outline(box.size,ACCENT if active else (83,119,139),samples=self.settings['ui_card_supersample']),box)
            self._text(overlay,title,(box.x+10,box.y-17),12,MUTED)
            shown=value or ('192.168.1.x' if field=='host' else '4747')
            rendered=self._label(shown,17,INK if value else MUTED)
            old_clip=overlay.get_clip(); overlay.set_clip(box.inflate(-16,-4))
            overlay.blit(rendered,(min(box.x+12,box.right-12-rendered.get_width()),box.y+11))
            overlay.set_clip(old_clip)
            self.buttons.append((box,'droidcam_'+field))
        hint='Điện thoại và máy tính phải cùng Wi-Fi. DroidCam mặc định dùng port 4747.'
        old_clip=overlay.get_clip(); overlay.set_clip(pygame.Rect(rect.x+24,rect.y+144,rect.width-48,68))
        self._wrap(overlay,error if error else hint,(rect.x+24,rect.y+148),rect.width-48,12,(245,178,137) if error else MUTED)
        overlay.set_clip(old_clip)
        self._button(overlay,'Kết nối Wi-Fi',(rect.x+24,rect.bottom-66,170,38),'droidcam_connect',source_kind=='droidcam_wifi')
        self._button(overlay,'Dùng webcam máy',(rect.x+204,rect.bottom-66,160,38),'webcam_connect',source_kind=='webcam')
        self._button(overlay,'Đóng',(rect.right-104,rect.bottom-66,80,38),'droidcam_cancel')

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

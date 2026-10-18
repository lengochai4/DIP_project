"""Camera compositing and a textured spatial palette with true 3D atom geometry."""
import math
import time
from pathlib import Path
import cv2
import numpy as np
import pygame
from OpenGL import GL as gl,GLU as glu
from .camera_space import CameraSpace,SpatialPanel,CameraCover
from .chemistry import ChemistryScene
from .chemistry_input import ChemistryInput
from .chemistry_controls import PointPinch
from .theme import ACCENT, GOLD, INK, MUTED, glass


# Layout, not atomic data: the detached f-block is explicit.
PERIODS=(
    ('H',*(['']*16),'He'),
    ('Li','Be',*(['']*10),'B','C','N','O','F','Ne'),
    ('Na','Mg',*(['']*10),'Al','Si','P','S','Cl','Ar'),
    tuple('K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr'.split()),
    tuple('Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe'.split()),
    tuple('Cs Ba * Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn'.split()),
    tuple('Fr Ra ** Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og'.split()),
    ('','','',*'La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu'.split()),
    ('','','',*'Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr'.split()),
)


class CameraChemistryView:
    def __init__(self,settings,renderer):
        self.settings=settings; self.renderer=renderer
        self.scene=ChemistryScene(settings); self.input=ChemistryInput(self.scene,settings)
        self.space=CameraSpace(4/3,settings['world_width'],settings['camera_ar_fov_deg'])
        self.content=(0,0,1,1); self.identity=None; self.run_id=None
        self.panel_key=None; self.camera_key=None; self.panel_at=0.
        self.camera_size=None; self.panel_size=None
        self.panel_raster=None; self.paint_scale=None
        self.cursor_points={}; self.press_cursors=set()

    def open(self):
        self.camera_texture=gl.glGenTextures(1); self.panel_texture=gl.glGenTextures(1)
        self.label_textures={}
        self.camera_key=self.panel_key=None; self.camera_size=self.panel_size=None

    def close(self):
        if hasattr(self,'camera_texture'):
            gl.glDeleteTextures([self.camera_texture,self.panel_texture]+[value[0] for value in self.label_textures.values()])
            self.label_textures.clear()
            del self.camera_texture

    def _upload(self,texture,data,size,previous,fmt,mipmaps=False):
        gl.glBindTexture(gl.GL_TEXTURE_2D,texture)
        gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_MIN_FILTER,gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_MAG_FILTER,gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_WRAP_S,gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_WRAP_T,gl.GL_CLAMP_TO_EDGE)
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT,1)
        internal=gl.GL_RGB if fmt==gl.GL_BGR else fmt
        if size!=previous: gl.glTexImage2D(gl.GL_TEXTURE_2D,0,internal,*size,0,fmt,gl.GL_UNSIGNED_BYTE,data)
        else: gl.glTexSubImage2D(gl.GL_TEXTURE_2D,0,0,0,*size,fmt,gl.GL_UNSIGNED_BYTE,data)
        if mipmaps and bool(gl.glGenerateMipmap):
            gl.glGenerateMipmap(gl.GL_TEXTURE_2D)
            gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_MIN_FILTER,gl.GL_LINEAR_MIPMAP_LINEAR)
            extensions=gl.glGetString(gl.GL_EXTENSIONS) or b''
            if b'GL_EXT_texture_filter_anisotropic' in extensions:
                gl.glTexParameterf(gl.GL_TEXTURE_2D,0x84FE,min(self.settings['panel_anisotropy'],float(gl.glGetFloatv(0x84FF))))

    def _font(self,size):
        # Panel fonts are cached separately from the window font sizes.
        if not hasattr(self,'fonts'): self.fonts={}
        if size not in self.fonts:
            path=Path('C:/Windows/Fonts/segoeui.ttf')
            self.fonts[size]=pygame.font.Font(str(path) if path.is_file() else None,size)
        return self.fonts[size]

    def _geometry(self):
        def key():
            return (self.space.aspect,self.content[2:],self.input.page,
                    tuple(np.round(self.input.layout.anchor,7)),round(self.input.layout.scale,6),
                    self.input.layout.edge,round(self.input.layout.edge_position,6))
        if key()==getattr(self,'panel_geometry_key',None): return self.panel_geometry
        panel=SpatialPanel(self.input.page=='table',self.space)
        self.input.layout.place(panel,self.space,self.content,self.input.page=='compact')
        self.panel_geometry_key=key(); self.panel_geometry=panel
        return panel

    def _raster_scale(self,panel):
        # Translation does not invalidate text; only size/resolution does.
        factor=(self.space.distance-panel.center[2])/self.space.distance
        pixels=panel.size/np.array((self.space.width,self.space.height))/factor*np.array(self.content[2:])
        scale=max(pixels/np.array(panel.pixels))*self.settings['chemistry_panel_texture_supersample']
        # Quantization avoids a texture upload for each tiny resize step.
        return min(2048/max(panel.pixels),max(.25,math.ceil(scale*4)/4))

    def _panel(self):
        scene=self.scene; control=self.input
        panel=self._geometry()
        panel.targets=[]
        surface=glass(panel.pixels,self.settings['crystal_panel_opacity'],26,True,self.settings['ui_card_supersample']).copy()
        # Hover is cheap GPU geometry; it must not rasterize/upload this panel.
        w,h=panel.pixels; hover=set()
        labels=[]
        def text(value,pos,size=30,color=INK):
            labels.append((value,pos,size,color,False))
        def finish():
            # Render glyphs at their projected pixel size instead of shrinking
            # an already-rasterized, oversized text bitmap on the GPU.
            scale=self.paint_scale if self.paint_scale is not None else self._raster_scale(panel)
            size=tuple(max(1,round(v*scale)) for v in panel.pixels)
            native=pygame.transform.smoothscale(surface,size)
            for value,pos,font,color,centered in labels:
                glyph=self._font(max(6,round(font*scale))).render(value,True,color)
                position=tuple(round(v*scale) for v in pos)
                native.blit(glyph,glyph.get_rect(center=position) if centered else position)
            return panel,native
        def button(label,rect,action,selected=False,color=None):
            x,y,bw,bh=rect
            surface.blit(glass((bw,bh),238,14,action in hover or selected,self.settings['ui_card_supersample']),(x,y))
            if color: pygame.draw.rect(surface,color,rect,2,border_radius=14)
            pygame.draw.rect(surface,ACCENT if action in hover or selected else (115,158,179,190),rect,2,border_radius=14)
            if action in hover:
                pygame.draw.line(surface,GOLD,(x+16,y+bh-2),(x+bw-16,y+bh-2),3)
            font=42 if action.startswith('element:') else 30
            while font>16 and self._font(font).size(label)[0]>bw-20: font-=2
            labels.append((label,(x+bw//2,y+bh//2),font,INK,True))
            panel.targets.append((tuple(rect),action))
        if control.page=='compact':
            points={'left':((45,30),(85,64),(45,98)),
                    'right':((83,30),(43,64),(83,98)),
                    'top':((30,45),(64,85),(98,45)),
                    'bottom':((30,83),(64,43),(98,83))}[control.layout.edge]
            pygame.draw.lines(surface,GOLD if 'restore_panel' in hover else ACCENT,False,points,8)
            panel.targets.append(((0,0,128,128),'restore_panel'))
            return finish()
        text('BẢNG NGUYÊN TỐ',(32,22),34,ACCENT)
        panel.targets.append(((12,8,w-230,68),'panel:drag'))
        button('',(w-195,15,72,52),'panel_reset')
        pygame.draw.arc(surface,INK,(w-176,25,34,32),math.radians(40),math.radians(315),3)
        pygame.draw.polygon(surface,INK,((w-143,29),(w-155,26),(w-146,39)))
        button('−',(w-103,15,72,52),'compact')
        pygame.draw.line(surface,(161,213,232,150),(32,78),(w-32,78),2)
        if control.page=='home':
            text(f"Giữ {self.settings['chemistry_dwell_s']:g}s hoặc chụm để chọn" if self.settings['chemistry_quick_select']=='point_pinch' else f"Giữ {self.settings['chemistry_dwell_s']:g}s hoặc đẩy trỏ để chọn",(32,99),29)
            button('BẢNG NGUYÊN TỐ',(32,165,w-64,130),'elements')
            button('MẪU PHÂN TỬ 3D',(32,322,w-64,105),'templates')
            if self.renderer.help_visible:
                text('THAO TÁC BẰNG TAY',(32,475),24,ACCENT)
                text('Chụm sát cái–trỏ trên nguyên tử để cầm',(32,522),26)
                text('Tay thứ hai chụm rồi tách / khép để đổi cỡ',(32,565),25)
                text('Ghép/tách: thả gần để nối, kéo xa để tháo',(32,608),26)
                text('Kéo tiêu đề: dời bảng; góc dưới: đổi cỡ',(32,655),25)
                text('Kéo ra viền để ẩn; trỏ mũi tên để mở',(32,696),24)
                text('Vòng vàng: chụm để chọn; mở để chọn tiếp' if self.settings['chemistry_quick_select']=='point_pinch' else 'Vòng vàng: đẩy riêng trỏ rồi rút lại',(32,731),23,ACCENT)
            else: text('H để hiện cách thao tác',(32,525),28,(166,189,205))
        elif control.page=='elements':
            text('Nguyên tố thường dùng',(32,93),31)
            for i,symbol in enumerate(self.settings['chemistry_common_elements']):
                button(symbol,(32+(i%4)*166,150+(i//4)*142,150,122),'element:'+symbol)
            button('Bảng tuần hoàn 118',(32,451,390,73),'table')
            button('Mẫu 3D',(438,451,250,73),'templates')
            selected=scene.atoms.get(scene.selected)
            if selected:
                element=scene.elements[selected.symbol]
                text(f'{element.symbol} • {element.name} • Z = {element.number}',(32,554),29)
                text(f'{element.number} proton; {element.number} e (trung hòa)',(32,600),27)
                text('Lớp e: '+', '.join(map(str,element.shells)),(32,646),27)
                config=element.configuration
                text(config[:46],(32,688),23,(166,189,205))
                if 'predicted' in config.lower(): text('Cấu hình trong nguồn là dự đoán',(32,725),21,(239,196,130))
        elif control.page=='templates':
            templates=list(self.settings['chemistry_templates'].items())
            pages=max(1,(len(templates)+7)//8); current=min(control.template_page,pages-1)
            text(f'Mẫu cầu–que • Trang {current+1}/{pages}',(32,93),28)
            for i,(key,t) in enumerate(templates[current*8:(current+1)*8]):
                button(t['label'],(32,145+i*67,w-64,58),'template:'+key)
            button('Trang trước',(32,693,210,52),'templates_prev')
            button('Nguyên tố',(256,693,210,52),'elements')
            button('Trang sau',(480,693,208,52),'templates_next')
        else:
            text('118 nguyên tố • chọn để tạo nguyên tử; dữ liệu PubChem',(32,91),31)
            for row,symbols in enumerate(PERIODS):
                for col,symbol in enumerate(symbols):
                    if symbol in ('*','**'):
                        text('57–71' if symbol=='*' else '89–103',(32+col*96,163+row*68),20); continue
                    if not symbol: continue
                    x,y=32+col*96,145+row*68
                    button(symbol,(x,y,86,62),'element:'+symbol)
                    text(str(scene.elements[symbol].number),(x+5,y+3),15,(136,176,191))
            button('Thường dùng',(32,794,300,72),'elements')
            button('Thu bảng',(350,794,230,72),'compact')
            button('Xóa tất cả',(600,794,230,72),'clear_all')
            button('Hoàn tác',(850,794,230,72),'undo')
        if control.page!='table':
            button('Ghép/tách' if not scene.edit else 'Cầm cả khối',(32,760,305,64),'edit',scene.edit)
            button('Nguyên tử / e',(353,760,335,64),'electrons',scene.electrons)
            button(f'Liên kết {scene.order}',(32,838,210,62),'order')
            button('Hoàn tác',(256,838,210,62),'undo')
            button('Xóa chọn',(480,838,208,62),'delete')
            button('Xóa tất cả',(32,918,210,52),'clear_all')
            button('Lưu',(256,918,210,52),'save')
            button('Mở đã lưu',(480,918,208,52),'load')
        # Dedicated corner: grabbing this can never grab an atom behind it.
        panel.targets.append(((w-44,h-44,44,44),'panel:resize'))
        for offset in (10,20,30):
            pygame.draw.line(surface,ACCENT,(w-offset,h-5),(w-5,h-offset),3)
        return finish()

    def _ensure_panel(self,force=False):
        geometry=self._geometry()
        old=self.input.panel
        geometry.targets=getattr(old,'targets',[])
        self.input.panel=geometry
        selected=self.scene.atoms.get(self.scene.selected)
        # The panel only displays element details on the elements page. Atom
        # movement/bond changes belong to the scene, not this static texture.
        symbol=selected.symbol if selected is not None and self.input.page=='elements' else None
        raster=self._raster_scale(geometry)
        # Geometry/hit testing keep following every draw. Rasterize the final
        # resolution once on release instead of hitching at resize tier edges.
        manipulating=any(c.kind.startswith('panel_') for c in self.input.claims.values())
        if manipulating and self.panel_raster is not None and self.panel_key is not None and self.panel_key[1]==self.input.page:
            raster=self.panel_raster
        semantic=(self.space.aspect,self.input.page,self.input.template_page,symbol,
                  self.scene.edit,self.scene.electrons,self.scene.order,self.renderer.help_visible,self.content[2:],
                  raster,self.input.layout.edge if self.input.page=='compact' else None)
        key=semantic+((),)
        now=time.monotonic()
        semantic_changed=self.panel_key is None or self.panel_key[:-1]!=semantic
        if force or self.input.panel is None or (key!=self.panel_key and (semantic_changed or now-self.panel_at>=1/self.settings['chemistry_panel_fps'])):
            self.paint_scale=raster
            panel,surface=self._panel(); self.input.panel=panel
            self._upload(self.panel_texture,pygame.image.tobytes(surface,'RGBA',False),surface.get_size(),self.panel_size,gl.GL_RGBA,mipmaps=True)
            self.panel_size=surface.get_size(); self.panel_key=key; self.panel_at=now
            self.panel_raster=raster

    def mouse(self,kind,pos):
        x,y,w,h=self.content
        dragging='mouse' in self.input.claims and self.input.claims['mouse'].kind.startswith('panel_')
        if kind=='up' or dragging or (x<=pos[0]<x+w and y<=pos[1]<y+h):
            self.input.mouse(kind,(pos[0]-x)/w,(pos[1]-y)/h,self.space)

    def wheel(self,amount,pos):
        x,y,w,h=self.content
        if x<=pos[0]<x+w and y<=pos[1]<y+h:
            return self.input.wheel(amount,(pos[0]-x)/w,(pos[1]-y)/h,self.space)
        return False

    def _anchor_press_cursor(self):
        """Freeze the actually displayed cursor, including its last follow step."""
        active=set()
        for slot,state in self.input.tap.states.items():
            if not state.locked: continue
            key=(slot,state.generation); active.add(key)
            if key not in self.press_cursors and state.phase=='press':
                previous=self.cursor_points.get(key)
                if previous is not None:
                    anchor=self.space.project(previous)
                    # Only freeze a displayed point on the intended button.
                    # A lagging cursor outside it must not replace valid aim.
                    if not isinstance(self.input.tap,PointPinch) or self.input.hit(self.space,*anchor)==state.target[1]:
                        state.anchor=anchor; self.input.pointers[slot]=anchor
        self.press_cursors=active

    def draw(self,snapshot,view,fresh,dt,run_id):
        source_aspect=snapshot.image.shape[1]/snapshot.image.shape[0] if snapshot is not None else 4/3
        aspect=view[2]/max(1,view[3]); cover=CameraCover(source_aspect,aspect)
        geometry_key=(view,source_aspect)
        if geometry_key!=getattr(self,'geometry_key',None):
            self.input.release(); self.identity=None; self.cursor_points.clear(); self.press_cursors.clear()
            self.geometry_key=geometry_key
        self.space=CameraSpace(aspect,self.settings['world_width'],self.settings['camera_ar_fov_deg'])
        self.content=view
        self._ensure_panel(force=self.panel_key is None or self.panel_key[0]!=aspect)
        x,y,w,h=self.content
        window_h=self.renderer.size[1]
        gl.glViewport(x,window_h-y-h,w,h)
        gl.glScissor(x,window_h-y-h,w,h)
        gl.glEnable(gl.GL_SCISSOR_TEST)
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glDisable(gl.GL_LIGHTING)
        gl.glMatrixMode(gl.GL_PROJECTION); gl.glLoadIdentity(); gl.glOrtho(0,1,1,0,-1,1)
        gl.glMatrixMode(gl.GL_MODELVIEW); gl.glLoadIdentity()
        if snapshot is not None:
            key=(run_id,snapshot.frame_id)
            if key!=self.camera_key:
                image=snapshot.image
                if self.settings['mirror']: image=image[:,::-1]
                # GL_BGR is explicit; avoid a full-frame color-space copy.
                image=np.ascontiguousarray(image)
                self._upload(self.camera_texture,image,(image.shape[1],image.shape[0]),self.camera_size,gl.GL_BGR)
                self.camera_size=(image.shape[1],image.shape[0]); self.camera_key=key
            gl.glEnable(gl.GL_TEXTURE_2D); gl.glBindTexture(gl.GL_TEXTURE_2D,self.camera_texture); gl.glColor4f(1,1,1,1)
            gl.glBegin(gl.GL_QUADS)
            for (u,v),(a,b) in zip(cover.uv,((0,0),(1,0),(1,1),(0,1))):
                gl.glTexCoord2f(u,v); gl.glVertex2f(a,b)
            gl.glEnd(); gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glMatrixMode(gl.GL_PROJECTION); gl.glLoadIdentity()
        glu.gluPerspective(self.space.fov,aspect,.1,100)
        gl.glMatrixMode(gl.GL_MODELVIEW); gl.glLoadIdentity(); gl.glTranslatef(0,0,-self.space.distance)
        gl.glEnable(gl.GL_LIGHTING); gl.glEnable(gl.GL_LIGHT0); gl.glEnable(gl.GL_COLOR_MATERIAL); gl.glEnable(gl.GL_NORMALIZE)
        gl.glLightfv(gl.GL_LIGHT0,gl.GL_POSITION,(1,3,5,1))
        gl.glLightfv(gl.GL_LIGHT0,gl.GL_DIFFUSE,(.88,.94,1,1))
        gl.glLightfv(gl.GL_LIGHT0,gl.GL_SPECULAR,(1,1,1,1))
        gl.glLightModelfv(gl.GL_LIGHT_MODEL_AMBIENT,(.23,.26,.3,1))
        gl.glMaterialfv(gl.GL_FRONT_AND_BACK,gl.GL_SPECULAR,(.95,.97,1,1)); gl.glMaterialf(gl.GL_FRONT_AND_BACK,gl.GL_SHININESS,96)
        identity=(run_id,snapshot.frame_id) if fresh else None
        if run_id!=self.run_id:
            self.input.release(); self.run_id=run_id; self.identity=None
        if not fresh and (self.identity is not None or self.input.gates): self.input.release()
        elif identity!=self.identity:
            self.input.update(tuple(cover.hand(hand) for hand in snapshot.hands),snapshot.timestamp_s,self.space,
                              gesture_hands=snapshot.hands,source_aspect=source_aspect)
            self._anchor_press_cursor()
        self.identity=identity; self.input.advance(dt)
        self._ensure_panel(force=self.input.panel.full!=(self.input.page=='table'))
        self._atoms()
        self._update_labels()
        panel=self.input.panel
        if self.input.page=='compact': gl.glDisable(gl.GL_DEPTH_TEST)
        gl.glDisable(gl.GL_LIGHTING); gl.glEnable(gl.GL_TEXTURE_2D); gl.glBindTexture(gl.GL_TEXTURE_2D,self.panel_texture)
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA,gl.GL_ONE_MINUS_SRC_ALPHA); gl.glColor4f(1,1,1,1)
        gl.glBegin(gl.GL_QUADS)
        for u,v in ((0,0),(1,0),(1,1),(0,1)):
            gl.glTexCoord2f(u,v); gl.glVertex3fv(panel.world(u*panel.pixels[0],v*panel.pixels[1]))
        gl.glEnd(); gl.glDisable(gl.GL_TEXTURE_2D); gl.glDisable(gl.GL_BLEND)
        if self.input.page!='compact': gl.glEnable(gl.GL_DEPTH_TEST)
        # Moving between tiles, including noisy borders, never uploads text.
        gl.glColor3f(*(np.array(ACCENT)/255)); gl.glLineWidth(2)
        hovered={a for a in self.input.hover.values() if a and not a.startswith(('atom:','panel:'))}
        for rect,action in panel.targets:
            if action not in hovered: continue
            bx,by,bw,bh=rect
            gl.glBegin(gl.GL_LINE_LOOP)
            for px,py in ((bx+2,by+2),(bx+bw-2,by+2),(bx+bw-2,by+bh-2),(bx+2,by+bh-2)):
                gl.glVertex3fv(panel.world(px,py)+panel.rotation[:,2]*.006)
            gl.glEnd()
        # Animate confirmation directly in GL; do not repaint/upload the
        # entire periodic-table texture on each progress step.
        gl.glColor3f(*(np.array(ACCENT)/255))
        for state in self.input.dwell.states.values():
            if not state.progress or state.latched or state.target[0]!=self.input.page: continue
            rect=next((rect for rect,action in panel.targets if action==state.target[1]),None)
            if rect is None: continue
            bx,by,bw,bh=rect; length=(bw-16)*state.progress
            gl.glBegin(gl.GL_QUADS)
            for px,py in ((bx+8,by+bh-10),(bx+8+length,by+bh-10),(bx+8+length,by+bh-6),(bx+8,by+bh-6)):
                gl.glVertex3fv(panel.world(px,py)+panel.rotation[:,2]*.003)
            gl.glEnd()
        # Cursor is display-aligned; no claim of physical finger contact depth.
        gl.glEnable(gl.GL_DEPTH_TEST)
        generations={hand.slot:hand.generation for hand in snapshot.hands} if fresh else {}
        targets={(key,generations[key]):self.space.point(nx,ny,.6)
                 for key,(nx,ny) in self.input.pointers.items() if key in generations}
        alpha=1-math.exp(-math.tau*self.settings['chemistry_cursor_response_hz']*max(0,dt))
        self.cursor_points={key:(p if key[0] in self.input.tap.states and self.input.tap.states[key[0]].locked
            else self.cursor_points.get(key,p)+(p-self.cursor_points.get(key,p))*alpha) for key,p in targets.items()}
        gl.glDisable(gl.GL_LIGHTING); gl.glLineWidth(2)
        for (key,generation),p in self.cursor_points.items():
            tap=self.input.tap.states.get(key)
            pressed=key in self.input.claims or (tap and tap.phase in ('armed','press','latched'))
            gl.glColor3f(*(np.array(GOLD if pressed else ACCENT)/255))
            state=self.input.dwell.states.get(key); progress=state.progress if state else 0.
            if tap and tap.phase=='press':
                progress=max(progress,tap.progress if hasattr(tap,'progress') else float(np.clip((tap.depth-tap.baseline)/self.settings['chemistry_push_travel_ratio'],0,1)))
            gl.glBegin(gl.GL_LINE_LOOP)
            for i in range(48):
                t=math.tau*i/48; gl.glVertex3fv(p+np.array((math.cos(t),math.sin(t),0))*.075)
            gl.glEnd()
            if progress:
                gl.glColor3f(*(np.array(GOLD)/255)); gl.glLineWidth(4); gl.glBegin(gl.GL_LINE_STRIP)
                for i in range(int(progress*64)+1):
                    t=math.pi/2-math.tau*i/64; gl.glVertex3fv(p+np.array((math.cos(t),math.sin(t),0))*.093)
                gl.glEnd(); gl.glLineWidth(2)
            gl.glEnable(gl.GL_LIGHTING); self._sphere(p,.019); gl.glDisable(gl.GL_LIGHTING)
        gl.glDisable(gl.GL_SCISSOR_TEST)

    def _update_labels(self):
        """Camera-aligned projection without per-atom GL matrix/viewport queries."""
        x,y,w,h=self.content; self.labels=[]
        for atom in self.scene.atoms.values():
            if not .1<self.space.distance-atom.position[2]<100: continue
            point=self.space.project(atom.position)
            if point is None: continue
            nx,ny=point
            if 0<=nx<=1 and 0<=ny<=1:
                self.labels.append((atom.symbol,(int(x+nx*w)+9,int(y+ny*h)-18)))

    def draw_labels(self):
        """Small cached glyph textures follow atoms at draw rate, outside UI raster."""
        if not self.labels: return
        width,height=self.renderer.size; x,y,w,h=self.content
        gl.glViewport(0,0,width,height)
        gl.glEnable(gl.GL_SCISSOR_TEST); gl.glScissor(x,height-y-h,w,h)
        gl.glDisable(gl.GL_DEPTH_TEST); gl.glDisable(gl.GL_LIGHTING)
        gl.glMatrixMode(gl.GL_PROJECTION); gl.glLoadIdentity(); gl.glOrtho(0,width,height,0,-1,1)
        gl.glMatrixMode(gl.GL_MODELVIEW); gl.glLoadIdentity()
        gl.glEnable(gl.GL_TEXTURE_2D); gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA,gl.GL_ONE_MINUS_SRC_ALPHA); gl.glColor4f(1,1,1,1)
        for text,(px,py) in self.labels:
            if text not in self.label_textures:
                glyph=self.renderer._label(text,15,INK)
                size=(glyph.get_width()+10,glyph.get_height()+6)
                surface=pygame.Surface(size,pygame.SRCALPHA)
                pygame.draw.rect(surface,(8,20,30,205),(0,0,*size),border_radius=6)
                surface.blit(glyph,(5,3))
                texture=gl.glGenTextures(1)
                self._upload(texture,pygame.image.tobytes(surface,'RGBA',False),size,None,gl.GL_RGBA)
                self.label_textures[text]=(texture,size)
            texture,(lw,lh)=self.label_textures[text]
            gl.glBindTexture(gl.GL_TEXTURE_2D,texture)
            left,top=px-5,py-3
            gl.glBegin(gl.GL_QUADS)
            for (u,v),(a,b) in zip(((0,0),(1,0),(1,1),(0,1)),
                ((left,top),(left+lw,top),(left+lw,top+lh),(left,top+lh))):
                gl.glTexCoord2f(u,v); gl.glVertex2f(a,b)
            gl.glEnd()
        gl.glDisable(gl.GL_TEXTURE_2D); gl.glDisable(gl.GL_BLEND); gl.glDisable(gl.GL_SCISSOR_TEST)

    def _sphere(self,p,radius):
        gl.glPushMatrix(); gl.glTranslatef(*p); gl.glScalef(radius,radius,radius)
        gl.glCallList(self.renderer.unit_sphere); gl.glPopMatrix()

    def _bone(self,a,b,radius):
        d=b-a; length=np.linalg.norm(d)
        if length<1e-8: return
        z=d/length; ref=np.array((0.,1.,0.)) if abs(z[1])<.9 else np.array((1.,0.,0.))
        x=np.cross(ref,z); x/=np.linalg.norm(x); y=np.cross(z,x)
        m=np.eye(4); m[:3,:3]=np.column_stack((x,y,z))
        gl.glPushMatrix(); gl.glTranslatef(*a); gl.glMultMatrixf(m.T.astype(np.float32))
        gl.glScalef(radius,radius,length); gl.glCallList(self.renderer.unit_bone); gl.glPopMatrix()

    def _atoms(self):
        scene=self.scene; radius=self.settings['chemistry_atom_radius']
        for (a,b),order in scene.bonds.items():
            pa,pb=scene.atoms[a].position,scene.atoms[b].position
            direction=pb-pa; side=np.cross(direction,(0,0,1))
            if np.linalg.norm(side)<1e-8: side=np.cross(direction,(0,1,0))
            side=side/max(np.linalg.norm(side),1e-8)
            gl.glColor3f(.76,.8,.88)
            for i in range(order):
                offset=side*(i-(order-1)/2)*.055
                scale=(scene.atoms[a].scale+scene.atoms[b].scale)/2
                self._bone(pa+offset*scale,pb+offset*scale,.025*scale)
        for i,atom in scene.atoms.items():
            element=scene.elements[atom.symbol]; color=element.color
            gl.glColor3f(*color); self._sphere(atom.position,radius*atom.scale*(.8 if atom.symbol=='H' else 1))
            if i==scene.selected:
                gl.glDisable(gl.GL_LIGHTING); gl.glColor3f(1,.83,.3); gl.glLineWidth(2)
                gl.glBegin(gl.GL_LINE_LOOP)
                for j in range(40):
                    t=math.tau*j/40; gl.glVertex3fv(atom.position+np.array((math.cos(t),math.sin(t),0))*radius*1.3*atom.scale)
                gl.glEnd(); gl.glEnable(gl.GL_LIGHTING)
                if scene.electrons: self._electrons(atom,element)

    def _electrons(self,atom,element):
        now=time.perf_counter()*self.settings['chemistry_electron_speed']
        for shell,count in enumerate(element.shells):
            radius=(.3+.095*shell)*atom.scale; angle=.35+.22*shell
            u=np.array((1.,0.,0.)); v=np.array((0.,math.cos(angle),math.sin(angle)))
            gl.glDisable(gl.GL_LIGHTING); gl.glColor3f(.5,.7,.86); gl.glLineWidth(1)
            gl.glBegin(gl.GL_LINE_LOOP)
            for i in range(48):
                t=math.tau*i/48; gl.glVertex3fv(atom.position+radius*(math.cos(t)*u+math.sin(t)*v))
            gl.glEnd(); gl.glEnable(gl.GL_LIGHTING); gl.glColor3f(.35,.82,1)
            for i in range(count):
                t=now/(shell+1)+math.tau*i/count
                self._sphere(atom.position+radius*(math.cos(t)*u+math.sin(t)*v),.023*atom.scale)

"""Camera compositing and a textured spatial palette with true 3D atom geometry."""
import math
import time
import cv2
import numpy as np
import pygame
from OpenGL import GL as gl,GLU as glu
from .camera_space import CameraSpace,SpatialPanel,letterbox
from .chemistry import ChemistryScene
from .chemistry_input import ChemistryInput
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
        self.cursor_points={}

    def open(self):
        self.camera_texture=gl.glGenTextures(1); self.panel_texture=gl.glGenTextures(1)
        self.camera_key=self.panel_key=None; self.camera_size=self.panel_size=None

    def close(self):
        if hasattr(self,'camera_texture'):
            gl.glDeleteTextures([self.camera_texture,self.panel_texture])
            del self.camera_texture

    def _upload(self,texture,data,size,previous,fmt,mipmaps=False):
        gl.glBindTexture(gl.GL_TEXTURE_2D,texture)
        gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_MIN_FILTER,gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_MAG_FILTER,gl.GL_LINEAR)
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
            self.fonts[size]=pygame.font.Font('C:/Windows/Fonts/segoeui.ttf',size)
        return self.fonts[size]

    def _panel(self):
        scene=self.scene; control=self.input
        panel=SpatialPanel(control.page=='table',self.space)
        surface=glass(panel.pixels,self.settings['crystal_panel_opacity'],26,True,self.settings['ui_card_supersample']).copy()
        w,h=panel.pixels; hover=set(control.hover.values())
        labels=[]
        def text(value,pos,size=30,color=INK):
            labels.append((value,pos,size,color,False))
        def finish():
            # Render glyphs at their projected pixel size instead of shrinking
            # an already-rasterized, oversized text bitmap on the GPU.
            corners=[self.space.project(panel.world(x,y)) for x,y in ((0,0),(panel.pixels[0],0),(panel.pixels[0],panel.pixels[1]),(0,panel.pixels[1]))]
            pixels=np.ptp(np.array(corners),axis=0)*np.array(self.content[2:])
            scale=max(.1,min(pixels[0]/panel.pixels[0],pixels[1]/panel.pixels[1]))
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
            panel.pixels=(720,150); panel.size=np.array((1.6,.36))
            panel.center=self.space.point(.21,.2,.3)
            surface=glass(panel.pixels,self.settings['crystal_panel_opacity'],26,True,self.settings['ui_card_supersample']).copy()
            button('MỞ BẢNG NGUYÊN TỐ',(12,12,696,126),'elements')
            return finish()
        text('HÓA HỌC AR',(32,25),38,ACCENT)
        pygame.draw.line(surface,(161,213,232,150),(32,78),(w-32,78),2)
        if control.page=='home':
            text(f"Trỏ vào nút và giữ {self.settings['chemistry_dwell_s']:g} giây để chọn",(32,99),29)
            button('BẢNG NGUYÊN TỐ',(32,165,w-64,130),'elements')
            button('MẪU PHÂN TỬ 3D',(32,322,w-64,105),'templates')
            if self.renderer.help_visible:
                text('THAO TÁC BẰNG TAY',(32,475),24,ACCENT)
                text('Chụm sát cái–trỏ trên nguyên tử để cầm',(32,522),26)
                text('Tay thứ hai chụm rồi tách / khép để đổi cỡ',(32,565),25)
                text('Ghép/tách: thả gần để nối, kéo xa để tháo',(32,608),26)
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
        if control.page!='table':
            button('Ghép/tách' if not scene.edit else 'Cầm cả khối',(32,760,305,64),'edit',scene.edit)
            button('Nguyên tử / e',(353,760,335,64),'electrons',scene.electrons)
            button(f'Liên kết {scene.order}',(32,838,210,62),'order')
            button('Hoàn tác',(256,838,210,62),'undo')
            button('Xóa chọn',(480,838,208,62),'delete')
            button('Thu bảng',(32,918,210,52),'compact')
            button('Lưu',(256,918,210,52),'save')
            button('Mở đã lưu',(480,918,208,52),'load')
        return finish()

    def _ensure_panel(self,force=False):
        selected=self.scene.atoms.get(self.scene.selected)
        # The panel only displays element details on the elements page. Atom
        # movement/bond changes belong to the scene, not this static texture.
        symbol=selected.symbol if selected is not None and self.input.page=='elements' else None
        semantic=(self.space.aspect,self.input.page,self.input.template_page,symbol,
                  self.scene.edit,self.scene.electrons,self.scene.order,self.renderer.help_visible,self.content[2:])
        highlights=tuple(sorted({action for action in self.input.hover.values()
                                 if action and not action.startswith(('atom:','panel:'))}))
        key=semantic+(highlights,)
        now=time.monotonic()
        semantic_changed=self.panel_key is None or self.panel_key[:-1]!=semantic
        if force or self.input.panel is None or (key!=self.panel_key and (semantic_changed or now-self.panel_at>=1/self.settings['chemistry_panel_fps'])):
            panel,surface=self._panel(); self.input.panel=panel
            self._upload(self.panel_texture,pygame.image.tobytes(surface,'RGBA',False),surface.get_size(),self.panel_size,gl.GL_RGBA,mipmaps=True)
            self.panel_size=surface.get_size(); self.panel_key=key; self.panel_at=now

    def mouse(self,kind,pos):
        x,y,w,h=self.content
        if kind=='up' or (x<=pos[0]<x+w and y<=pos[1]<y+h):
            self.input.mouse(kind,(pos[0]-x)/w,(pos[1]-y)/h,self.space)

    def draw(self,snapshot,view,fresh,dt,run_id):
        aspect=snapshot.image.shape[1]/snapshot.image.shape[0] if snapshot is not None else 4/3
        self.space=CameraSpace(aspect,self.settings['world_width'],self.settings['camera_ar_fov_deg'])
        self.content=letterbox(view,aspect)
        self._ensure_panel(force=self.panel_key is None or self.panel_key[0]!=aspect)
        self.content=letterbox(view,aspect); x,y,w,h=self.content
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
            for (u,v),(a,b) in zip(((0,0),(1,0),(1,1),(0,1)),((0,0),(1,0),(1,1),(0,1))):
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
            self.input.update(snapshot.hands,snapshot.timestamp_s,self.space)
        self.identity=identity; self.input.advance(dt)
        self._ensure_panel(force=self.input.panel.full!=(self.input.page=='table'))
        self._atoms()
        self.labels=[]
        for atom in self.scene.atoms.values():
            px,py,pz=glu.gluProject(*atom.position)
            if 0<pz<1 and x<=px<=x+w and window_h-y-h<=py<=window_h-y:
                self.labels.append((atom.symbol,(int(px)+9,window_h-int(py)-18)))
        panel=self.input.panel
        gl.glDisable(gl.GL_LIGHTING); gl.glEnable(gl.GL_TEXTURE_2D); gl.glBindTexture(gl.GL_TEXTURE_2D,self.panel_texture)
        gl.glEnable(gl.GL_BLEND); gl.glBlendFunc(gl.GL_SRC_ALPHA,gl.GL_ONE_MINUS_SRC_ALPHA); gl.glColor4f(1,1,1,1)
        gl.glBegin(gl.GL_QUADS)
        for u,v in ((0,0),(1,0),(1,1),(0,1)):
            gl.glTexCoord2f(u,v); gl.glVertex3fv(panel.world(u*panel.pixels[0],v*panel.pixels[1]))
        gl.glEnd(); gl.glDisable(gl.GL_TEXTURE_2D); gl.glDisable(gl.GL_BLEND)
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
        targets={(key,next(h.generation for h in snapshot.hands if h.slot==key)):self.space.point(nx,ny,.6)
                 for key,(nx,ny) in self.input.pointers.items()} if fresh else {}
        alpha=1-math.exp(-math.tau*self.settings['chemistry_cursor_response_hz']*max(0,dt))
        self.cursor_points={key:self.cursor_points.get(key,p)+(p-self.cursor_points.get(key,p))*alpha for key,p in targets.items()}
        gl.glDisable(gl.GL_LIGHTING); gl.glLineWidth(2)
        for (key,generation),p in self.cursor_points.items():
            gl.glColor3f(*(np.array(GOLD if key in self.input.claims else ACCENT)/255))
            state=self.input.dwell.states.get(key); progress=state.progress if state else 0.
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
        now=time.monotonic()*self.settings['chemistry_electron_speed']
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

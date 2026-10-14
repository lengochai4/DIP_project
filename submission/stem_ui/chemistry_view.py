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

    def open(self):
        self.camera_texture=gl.glGenTextures(1); self.panel_texture=gl.glGenTextures(1)
        self.camera_key=self.panel_key=None; self.camera_size=self.panel_size=None

    def close(self):
        if hasattr(self,'camera_texture'):
            gl.glDeleteTextures([self.camera_texture,self.panel_texture])
            del self.camera_texture

    def _upload(self,texture,data,size,previous,fmt):
        gl.glBindTexture(gl.GL_TEXTURE_2D,texture)
        gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_MIN_FILTER,gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D,gl.GL_TEXTURE_MAG_FILTER,gl.GL_LINEAR)
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT,1)
        internal=gl.GL_RGB if fmt==gl.GL_BGR else fmt
        if size!=previous: gl.glTexImage2D(gl.GL_TEXTURE_2D,0,internal,*size,0,fmt,gl.GL_UNSIGNED_BYTE,data)
        else: gl.glTexSubImage2D(gl.GL_TEXTURE_2D,0,0,0,*size,fmt,gl.GL_UNSIGNED_BYTE,data)

    def _font(self,size):
        # Panel fonts are cached separately from the window font sizes.
        if not hasattr(self,'fonts'): self.fonts={}
        if size not in self.fonts:
            self.fonts[size]=pygame.font.Font('C:/Windows/Fonts/segoeui.ttf',size)
        return self.fonts[size]

    def _panel(self):
        scene=self.scene; control=self.input
        panel=SpatialPanel(control.page=='table',self.space)
        surface=pygame.Surface(panel.pixels,pygame.SRCALPHA); surface.fill((18,31,47,246))
        w,h=panel.pixels; hover=set(control.hover.values())
        def text(value,pos,size=30,color=(230,240,247)):
            surface.blit(self._font(size).render(value,True,color),pos)
        def button(label,rect,action,selected=False,color=None):
            x,y,bw,bh=rect
            fill=color or ((42,97,91) if action in hover or selected else (35,54,77))
            pygame.draw.rect(surface,fill,rect,border_radius=12)
            if action in hover: pygame.draw.rect(surface,(255,211,101),rect,4,border_radius=12)
            font=42 if action.startswith('element:') else 30
            rendered=self._font(font).render(label,True,(237,246,251))
            surface.blit(rendered,rendered.get_rect(center=(x+bw//2,y+bh//2)))
            panel.targets.append((tuple(rect),action))
        if control.page=='compact':
            panel.pixels=(720,150); panel.size=np.array((1.6,.36))
            panel.center=self.space.point(.21,.2,.3)
            surface=pygame.Surface(panel.pixels,pygame.SRCALPHA); surface.fill((18,31,47,246))
            button('MỞ BẢNG NGUYÊN TỐ',(12,12,696,126),'elements')
            return panel,surface
        text('HÓA HỌC TRONG CAMERA',(32,25),36,(91,229,192))
        if control.page=='home':
            text('Trỏ vào ô → chụm cái–trỏ',(32,92),31)
            button('BẢNG NGUYÊN TỐ',(32,165,w-64,130),'elements')
            button('Mẫu phân tử 3D',(32,322,w-64,105),'templates')
            if self.renderer.help_visible:
                text('1. Chọn nguyên tố để tạo nguyên tử',(32,475),28)
                text('2. Bật Ghép/tách; chụm trên nguyên tử',(32,525),27)
                text('3. Thả gần để ghép; kéo xa để tháo',(32,575),28)
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
            text('Mẫu cầu–que; hình học minh họa',(32,93),28)
            for i,(key,t) in enumerate(self.settings['chemistry_templates'].items()):
                button(t['label'],(32,145+i*67,w-64,58),'template:'+key)
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
        return panel,surface

    def _ensure_panel(self,force=False):
        key=(self.space.aspect,self.input.page,self.scene.selected,self.scene.edit,self.scene.electrons,self.scene.order,self.scene.revision,self.renderer.help_visible,
             tuple(sorted(str(v) for v in self.input.hover.values())))
        now=time.monotonic()
        if force or self.input.panel is None or (key!=self.panel_key and now-self.panel_at>=1/self.settings['chemistry_panel_fps']):
            panel,surface=self._panel(); self.input.panel=panel
            self._upload(self.panel_texture,pygame.image.tobytes(surface,'RGBA',False),panel.pixels,self.panel_size,gl.GL_RGBA)
            self.panel_size=panel.pixels; self.panel_key=key; self.panel_at=now

    def mouse(self,kind,pos):
        x,y,w,h=self.content
        if kind=='up' or (x<=pos[0]<x+w and y<=pos[1]<y+h):
            self.input.mouse(kind,(pos[0]-x)/w,(pos[1]-y)/h,self.space)

    def draw(self,snapshot,view,fresh,dt,run_id):
        aspect=snapshot.image.shape[1]/snapshot.image.shape[0] if snapshot is not None else 4/3
        self.space=CameraSpace(aspect,self.settings['world_width'],self.settings['camera_ar_fov_deg'])
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
        gl.glLightModelfv(gl.GL_LIGHT_MODEL_AMBIENT,(.35,.35,.4,1))
        gl.glMaterialfv(gl.GL_FRONT_AND_BACK,gl.GL_SPECULAR,(.5,.5,.5,1)); gl.glMaterialf(gl.GL_FRONT_AND_BACK,gl.GL_SHININESS,36)
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
        # Cursor is display-aligned; no claim of physical finger contact depth.
        gl.glEnable(gl.GL_LIGHTING)
        for key,(nx,ny) in self.input.pointers.items():
            p=self.space.point(nx,ny,.6)
            gl.glColor3f(1,.8,.32) if key in self.input.claims else gl.glColor3f(.35,1,.75)
            self._sphere(p,.045)
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

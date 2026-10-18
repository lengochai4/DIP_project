"""Actual Windows GL lifecycle and hand-selected compact palette regression."""
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import pytest


@pytest.mark.skipif(sys.platform!='win32',reason='Windows desktop/OpenGL regression')
def test_native_physics_scenarios_hand_palette_and_fullscreen(tmp_path):
    root=Path(__file__).resolve().parents[2]
    code=textwrap.dedent('''
        import sys,time
        from pathlib import Path
        import numpy as np,yaml
        from OpenGL import GL as gl
        sys.path.insert(0,str(Path('tests/submission').resolve()))
        from test_chemistry import aim,with_ratio
        from submission.stem_ui.renderer import SubmissionRenderer
        from submission.stem_ui.runtime import Snapshot
        from submission.stem_ui.camera_space import CameraCover
        settings=yaml.safe_load(Path('submission/stem_ui/settings.yaml').read_text(encoding='utf8'))
        settings['window']=[800,600]
        r=SubmissionRenderer(settings);r.enter_physics();r.open();v=r.physics
        image=np.zeros((480,640,3),dtype=np.uint8);counter=0
        def draw(hands=()):
            global counter
            counter+=1;r.events()
            r.draw(Snapshot(counter,1+counter/30,time.monotonic(),image,tuple(hands),None,None),'Native QA',active=True,run_id='native-physics')
            assert gl.glGetError()==gl.GL_NO_ERROR
        def choose(action):
            rect=next(rect for rect,a in v.targets if a==action)
            nx,ny=rect.centerx/v.content[2],rect.centery/v.content[3]
            cover=CameraCover(4/3,v.space.aspect)
            for ratio in [1.]*8+[.4,.1,.1,.1]:
                h=with_ratio(aim(cover.left+nx*cover.width,cover.top+ny*cover.height),ratio)
                draw([h])
            assert v.input.tap.states[0].phase=='latched'
        def at(nx,ny,ratio):
            cover=CameraCover(4/3,v.space.aspect)
            return with_ratio(aim(cover.left+nx*cover.width,cover.top+ny*cover.height),ratio)
        def handle(action):
            rect=next(rect for rect,a in v.targets if a==action)
            nx,ny=rect.centerx/v.content[2],rect.centery/v.content[3]
            for ratio in [1.]*8+[.1]*4: draw([at(nx,ny,ratio)])
            assert v.input.claims[0].target==action
            return nx,ny
        try:
            for lab in v.model.catalog['labs']:
                v.command('lab:'+lab);draw()
                assert v.hud_semantic[0]==lab
                v.model.step();v.flags.update(energy=True,graph=True);draw()
                v.command('page:tools');draw()
                for rect,action in v.targets: assert v.panel_rect.contains(rect)
                v.command('page:lesson');draw()
            v.command('page:adjust');draw()
            choose('compact');assert v.collapsed
            assert all(rect.w<50 for rect,action in v.targets)
            choose('restore');assert not v.collapsed
            choose('library');assert v.library
            action=next(a for rect,a in v.targets if a.startswith('lab:'))
            choose(action);assert v.model.lab==action[4:] and not v.library
            # Real GL draw cadence follows hand targets; release discards the
            # unconsumed tail instead of moving the parameter after opening.
            nx,ny=handle('drag:param:mass');before=v.model.params['mass']
            for _ in range(6):draw([at(nx+.04,ny,.1)])
            assert v.model.params['mass']>before
            draw([at(nx+.1,ny,.5)]);frozen=v.model.params['mass']
            for _ in range(8):draw([at(nx+.15,ny,1)])
            assert not v.input.claims and v.model.params['mass']==frozen
            # Model contact break must freeze before the old .45 threshold,
            # including a palm shift and an unfinished render-follow target.
            body=next(p for p,a in v.handles if a=='drag:body')
            nx,ny=v.space.project(body)
            for ratio in [1.]*8+[.1]*4:draw([at(nx,ny,ratio)])
            assert v.input.claims[0].target=='drag:body'
            for _ in range(5):draw([at(nx+.025,ny,.1)])
            frozen=v.model.params['position0']
            draw([at(nx+.08,ny,.364)])
            assert v.model.params['position0']==frozen and v.input.claims[0].paused
            for _ in range(4):draw([at(nx+.12,ny,.38)])
            assert not v.input.claims and v.model.params['position0']==frozen
            for _ in range(5):draw([at(nx+.12,ny,1)])
            # Pull the header past an edge; keep the close consumed while docked.
            nx,ny=handle('drag:panel')
            for _ in range(12):draw([at(nx-.15,ny,.1)])
            assert v.collapsed and v.dock_edge=='left' and v.input.claims[0].finished
            for _ in range(5):draw([at(nx-.15,ny,1)])
            choose('restore');assert not v.collapsed
            choose('page:tools')
            choose('tool:orbit');assert v.tool=='orbit' and v.hud_semantic[-1]=='orbit'
            original=v.model.configuration();nx,ny=.85,.6;yaw=v.yaw
            for _ in range(4):draw([at(nx,ny,.1)])
            assert not v.input.claims  # The menu close is consumed.
            for ratio in [1.]*8+[.1]*4:draw([at(nx,ny,ratio)])
            assert v.input.claims[0].target=='drag:orbit'
            for _ in range(8):draw([at(nx+.1,ny+.04,.1)])
            assert v.yaw>yaw and v.model.configuration()==original
            for _ in range(5):draw([at(nx+.1,ny+.04,1)])
            choose('tool:zoom');assert v.tool=='zoom';zoom=v.zoom
            for ratio in [1.]*8+[.1]*4:draw([at(nx,ny,ratio)])
            assert v.input.claims[0].target=='drag:zoom'
            for _ in range(8):draw([at(nx,ny-.1,.1)])
            assert v.zoom>zoom and v.model.configuration()==original
            # Partially opening then settling in the middle band must release.
            for ratio in [.5,.38,.38,.38]:draw([at(nx,ny,.5 if ratio==.5 else ratio)])
            assert not v.input.claims
            choose('tool:edit');assert v.tool=='edit'
            v.command('frame');draw()
            original=v.model.configuration();size=r.size
            r.toggle_fullscreen();draw();r.toggle_fullscreen();draw()
            assert r.size==size and v.model.configuration()==original
            print('native-physics-PASS',flush=True)
        finally:r.close()
    ''')
    result=subprocess.run([sys.executable,'-u','-X','utf8','-c',code],cwd=root,
        env=dict(os.environ,MPLCONFIGDIR=str(tmp_path/'mpl')),capture_output=True,text=True,encoding='utf-8',timeout=30)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'native-physics-PASS' in result.stdout

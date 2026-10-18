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

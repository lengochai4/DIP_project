"""Windows native event-loop regression for the borrowed SDL wrapper lifetime."""
from pathlib import Path
import os
import subprocess
import sys
import textwrap
import pytest


@pytest.mark.skipif(sys.platform!='win32',reason='Windows desktop/OpenGL regression')
def test_native_window_survives_gc_events_and_fullscreen_transitions(tmp_path):
    root=Path(__file__).resolve().parents[2]
    code=textwrap.dedent('''
        import faulthandler, gc
        from pathlib import Path
        import pygame, yaml
        from submission.stem_ui.renderer import SubmissionRenderer
        faulthandler.enable()
        r=SubmissionRenderer(yaml.safe_load(Path('submission/stem_ui/settings.yaml').read_text(encoding='utf-8')))
        r.open()
        original=r.size
        r._window.position=(280,180)
        position=r._window.position
        try:
            for i in range(30):
                gc.collect(); r.events(); r.draw(None,'Camera off')
            for i in range(3):
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_F11))
                r.events(); r.draw(None,'Camera off')
                assert r.fullscreen and r._window.size==r.size
                pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_F11))
                r.events(); r.draw(None,'Camera off')
                for j in range(5):
                    gc.collect(); r.events(); r.draw(None,'Camera off')
                assert not r.fullscreen and r.size==original and r._window.position==position
            print('native-event-loop-PASS',flush=True)
        finally:
            r.close()
    ''')
    env=dict(os.environ,MPLCONFIGDIR=str(tmp_path/'mpl'))
    result=subprocess.run([sys.executable,'-u','-X','utf8','-c',code],cwd=root,
                          env=env,capture_output=True,text=True,encoding='utf-8',timeout=25)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'native-event-loop-PASS' in result.stdout


@pytest.mark.skipif(sys.platform!='win32',reason='Windows desktop/OpenGL regression')
def test_native_chemistry_cover_mouse_drag_and_collapsed_restore(tmp_path):
    root=Path(__file__).resolve().parents[2]
    code=textwrap.dedent('''
        import time
        from pathlib import Path
        import numpy as np, yaml
        from OpenGL import GL as gl
        from submission.stem_ui.renderer import SubmissionRenderer
        from submission.stem_ui.runtime import Snapshot
        from submission.stem_ui.theme import scene_rect
        settings=yaml.safe_load(Path('submission/stem_ui/settings.yaml').read_text(encoding='utf-8'))
        settings['window']=[960,660]
        r=SubmissionRenderer(settings); r.enter_chemistry(); r.open()
        image=np.zeros((480,640,3),dtype=np.uint8)
        try:
            scene=r.chemistry.scene; c=r.chemistry.input
            scene.add_template('H2O'); original=scene.state()
            for i,page in enumerate(('elements','table','compact','elements')):
                c.command(page); r.events()
                r.draw(Snapshot(i,1+i*.05,time.monotonic(),image,(),None,None),'Native QA',active=True,run_id='qa')
                assert r.chemistry.content==scene_rect(r.size,False,'chemistry')
                assert not {'toggle_panel','panel_reset'} & {a for rect,a in r.buttons}
                if page=='compact': assert c.panel.targets==[((0,0,128,128),'restore_panel')]
            panel=c.panel; nx,ny=r.chemistry.space.project(panel.world(180,40))
            x,y,w,h=r.chemistry.content; pos=(x+nx*w,y+ny*h)
            r.chemistry.mouse('down',pos); assert c.claims['mouse'].kind=='panel_move'
            r.chemistry.mouse('move',(pos[0]+35,pos[1]+15))
            # Fresh camera with no tracked hand must not try drawing a mouse as a hand.
            r.draw(Snapshot(5,1.25,time.monotonic(),image,(),None,None),'Native QA',active=True,run_id='qa')
            r.chemistry.mouse('up',pos); assert not c.claims
            c.command('compact'); c.command('restore_panel'); assert c.page=='elements'
            r.toggle_fullscreen(); r.events(); r.draw(None,'Camera off')
            assert r.fullscreen
            r.toggle_fullscreen(); r.events(); r.draw(None,'Camera off')
            assert not r.fullscreen and scene.state()==original
            assert gl.glGetError()==gl.GL_NO_ERROR
            print('native-chemistry-PASS',flush=True)
        finally:
            r.close()
    ''')
    env=dict(os.environ,MPLCONFIGDIR=str(tmp_path/'mpl'))
    result=subprocess.run([sys.executable,'-u','-X','utf8','-c',code],cwd=root,
                          env=env,capture_output=True,text=True,encoding='utf-8',timeout=25)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'native-chemistry-PASS' in result.stdout

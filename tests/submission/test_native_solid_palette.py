"""Actual GL shape menu, tip glyphs, four-tab switching and context recreation."""
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import pytest


@pytest.mark.skipif(sys.platform!='win32',reason='Windows desktop/OpenGL regression')
def test_native_solid_palette_preserves_pose_and_tip_labels_survive_fullscreen(tmp_path):
    root=Path(__file__).resolve().parents[2]
    code=textwrap.dedent('''
        import sys,time
        from pathlib import Path
        import numpy as np,pygame,yaml
        from OpenGL import GL as gl
        sys.path.insert(0,str(Path('tests/submission').resolve()))
        from test_physics_shortcuts import open_hand
        from test_point_pinch import sample
        from test_stem_ui import hand
        from submission.stem_ui.renderer import SubmissionRenderer
        from submission.stem_ui.runtime import Snapshot
        from submission.stem_ui.theme import scene_rect
        settings=yaml.safe_load(Path('submission/stem_ui/settings.yaml').read_text(encoding='utf-8'))
        settings['window']=[800,600]
        r=SubmissionRenderer(settings);r.camera_visible=False;r.open()
        image=np.zeros((480,640,3),dtype=np.uint8);counter=0
        def draw(hands=()):
            global counter
            counter+=1;r.events()
            r.draw(Snapshot(counter,1+counter/30,time.monotonic(),image,tuple(hands),None,None),'Native QA',active=True,run_id='native-solid')
            assert gl.glGetError()==gl.GL_NO_ERROR
        def choose(action):
            p=r.solid_palette
            rect=next(rect for rect,a in p.targets if a==action)
            x,y,w,h=scene_rect(r.size,r.camera_visible,'solid')
            nx,ny=(rect.centerx-x)/w,(rect.centery-y)/h
            for ratio in [1.]*9+[.4,.1,.1,.1]:draw([sample(ratio,nx=nx,ny=ny)])
            assert not p.open and r.kind==action
            for _ in range(8):draw([sample(.1,nx=nx,ny=ny)])
            assert not r.grab.slots
        try:
            draw()
            r.grab.pose.position[:]=(.2,.1,0);r.grab.pose.scale=.8
            r.grab.pose.stretch[:]=(1.2,.8,1.)
            original=r.grab.pose.copy()
            for _ in range(23):draw([open_hand()])
            assert r.solid_palette.open
            r.screenshot(Path(sys.argv[1])/'shape-menu.png');draw([open_hand()])
            choose('sphere')
            np.testing.assert_allclose(r.grab.pose.position,original.position)
            np.testing.assert_allclose(r.grab.pose.rotation,original.rotation)
            np.testing.assert_allclose(r.grab.pose.stretch,original.stretch)
            assert r.grab.pose.scale==original.scale
            # Ordinary gripping still works after observed opening.
            for ratio in [1.]*4+[.1]*5:draw([sample(ratio,nx=.5,ny=.5)])
            assert r.grab.slots==(0,)
            for _ in range(5):draw([sample(.1,nx=.58,ny=.5)])
            frozen=r.grab.pose.copy()
            for _ in range(6):draw([sample(1.,nx=.7,ny=.5)])
            np.testing.assert_allclose(r.grab.pose.position,frozen.position)
            r.enter_basic('tips')
            for _ in range(12):draw([hand(0,.4,pinch=False),hand(1,.7,pinch=False)])
            assert r.live_mesh_mode in ('surface','hull3d') and len(r.live_points)==10
            assert any(key[0]=='tip' for key in r.sprites.items)
            r.screenshot(Path(sys.argv[1])/'tips.png');draw([hand(0,.4,pinch=False),hand(1,.7,pinch=False)])
            size=r.size;r.toggle_fullscreen();draw();r.toggle_fullscreen();draw()
            assert r.size==size and not r.sprites.items
            draw([hand(pinch=False)]);assert r.sprites.items
            r.enter_chemistry();r.chemistry.scene.add_template('H2O');draw()
            chemistry=r.chemistry.scene.state()
            r.enter_physics();draw();physics=r.physics.model.configuration()
            r.enter_basic('solid');draw()
            assert not r.dragging and not r.grab.slots and not r.solid_palette.open
            r.enter_chemistry();draw();assert r.chemistry.scene.state()==chemistry
            r.enter_physics();draw();assert r.physics.model.configuration()==physics
            assert gl.glGetError()==gl.GL_NO_ERROR
            print('native-solid-PASS',counter,flush=True)
        finally:r.close()
    ''')
    result=subprocess.run([sys.executable,'-u','-X','utf8','-c',code,str(tmp_path)],cwd=root,
        env=dict(os.environ,MPLCONFIGDIR=str(tmp_path/'mpl')),capture_output=True,text=True,encoding='utf-8',timeout=30)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'native-solid-PASS' in result.stdout

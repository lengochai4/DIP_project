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
        def at(nx,ny,ratio,slot=0):
            cover=CameraCover(4/3,v.space.aspect)
            return with_ratio(aim(cover.left+nx*cover.width,cover.top+ny*cover.height,slot=slot),ratio)
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
            choose('tool:scene');original=v.model.configuration()
            for ratio in [1.]*8+[.1]*4:draw([at(.65,.6,ratio),at(.85,.6,ratio,1)])
            assert len(v.input.claims)==2 and {c.target for c in v.input.claims.values()}=={'drag:scene'}
            zoom=v.zoom
            for _ in range(8):draw([at(.6,.6,.1),at(.9,.6,.1,1)])
            assert v.zoom>zoom and v.model.configuration()==original
            frozen=(v.yaw,v.pitch,v.zoom,v.roll,*v.scene_pan)
            for _ in range(5):draw([at(.55,.6,.5),at(.95,.6,.5,1)])
            assert not v.input.claims and np.allclose((v.yaw,v.pitch,v.zoom,v.roll,*v.scene_pan),frozen)
            choose('tool:edit');v.command('frame');draw()
            v.command('lab:collision');draw()
            assert {'drag:velocity1','drag:velocity2','drag:mass','drag:mass2'}<={a for _,a in v.handles}
            assert 'drag:body' not in {a for _,a in v.handles}
            v.command('lab:spring');v.command('page:adjust');draw();original=v.model.configuration()
            body=next(p for p,a in v.handles if a=='drag:body');nx,ny=v.space.project(body)
            for ratio in [1.]*8+[.1]*4:draw([at(nx,ny,ratio)])
            assert v.input.claims[0].target=='drag:body'
            for _ in range(8):draw([at(nx-.04,ny,.1)])
            for _ in range(4):draw([at(nx-.08,ny,.38)])
            assert not v.input.claims and v.model.running and v.undo
            choose('undo_edit');assert not v.model.running and v.model.configuration()==original
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


@pytest.mark.skipif(sys.platform!='win32',reason='Windows desktop/OpenGL regression')
def test_native_physics_quick_palette_and_empty_space_pair_shortcut(tmp_path):
    root=Path(__file__).resolve().parents[2]
    code=textwrap.dedent('''
        import sys,time
        from dataclasses import replace
        from pathlib import Path
        import numpy as np,yaml
        from OpenGL import GL as gl
        sys.path.insert(0,str(Path('tests/submission').resolve()))
        from test_physics_shortcuts import open_hand,two_hands,with_ratio
        from test_point_pinch import sample
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
            cover=CameraCover(4/3,v.space.aspect)
            hands=[replace(h,landmarks=tuple(replace(p,x=cover.left+p.x*cover.width,y=cover.top+p.y*cover.height) for p in h.landmarks)) for h in hands]
            r.draw(Snapshot(counter,1+counter/30,time.monotonic(),image,tuple(hands),None,None),'Shortcut QA',active=True,run_id='native-shortcuts')
            assert gl.glGetError()==gl.GL_NO_ERROR
        def choose(action):
            rect=next(rect for rect,a in v.quick_targets if a=='quick:'+action)
            nx,ny=rect.centerx/v.content[2],rect.centery/v.content[3]
            for _ in range(5):draw([sample(1,nx=.5,ny=.7)])
            for ratio in [1.]*8+[.4,.1,.1,.1]:draw([sample(ratio,nx=nx,ny=ny)])
            assert not v.quick_open
            for _ in range(5):draw([sample(.1,nx=nx,ny=ny)])
            assert not v.input.claims
        try:
            draw();original=v.model.configuration()
            for _ in range(10):draw([open_hand(ny=.28)])
            assert v.input.shortcuts.progress and not v.quick_open
            r.screenshot(Path(sys.argv[1])/'progress.png');draw([open_hand(ny=.28)])
            for _ in range(14):draw([open_hand(ny=.28)])
            assert v.quick_open and not v.model.running
            for _ in range(35):draw([open_hand(ny=.28)])
            assert v.quick_open and not v.model.running
            for rect,action in v.quick_targets:assert v.quick_rect.contains(rect)
            r.screenshot(Path(sys.argv[1])/'quick.png');draw([open_hand(ny=.28)])
            choose('panel');assert v.collapsed
            for _ in range(26):draw([open_hand(ny=.28)])
            assert v.quick_open
            choose('panel');assert not v.collapsed
            v.command('frame');draw()
            for _ in range(7):draw(two_hands())
            for _ in range(6):draw(two_hands(True))
            assert v.input.auto_scene and len(v.input.claims)==2
            before=v.zoom
            for _ in range(8):draw([with_ratio(open_hand(nx=.5),.1),with_ratio(open_hand(nx=.9,slot=1),.1)])
            assert v.zoom>before and v.model.configuration()==original
            frozen=(v.yaw,v.pitch,v.zoom,v.roll,*v.scene_pan)
            for _ in range(5):draw(two_hands())
            assert not v.input.auto_scene and v.tool=='edit' and not v.input.claims
            assert np.allclose((v.yaw,v.pitch,v.zoom,v.roll,*v.scene_pan),frozen)
            size=r.size;r.toggle_fullscreen();draw();r.toggle_fullscreen();draw()
            assert r.size==size and not v.input.auto_scene and v.model.configuration()==original
            assert (Path(sys.argv[1])/'quick.png').stat().st_size>0
            print('native-shortcuts-PASS',flush=True)
        finally:r.close()
    ''')
    result=subprocess.run([sys.executable,'-u','-X','utf8','-c',code,str(tmp_path)],cwd=root,
        env=dict(os.environ,MPLCONFIGDIR=str(tmp_path/'mpl')),capture_output=True,text=True,encoding='utf-8',timeout=30)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'native-shortcuts-PASS' in result.stdout

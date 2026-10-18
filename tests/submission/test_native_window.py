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

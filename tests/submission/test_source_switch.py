"""App-level source switching never overlaps local webcam and DroidCam."""
import sys
import pytest


@pytest.mark.parametrize('actions,expected',[
    ((('toggle',),('droidcam_connect',),(),(),('webcam_connect',),(),(),('quit',)),
     ['webcam','droidcam_wifi','webcam']),
    ((('toggle',),('droidcam_connect',),('toggle',),(),(),('quit',)),['webcam']),
    ((('toggle',),('droidcam_connect',),('quit','webcam_connect')),['webcam']),
])
def test_webcam_droidcam_webcam_switch_is_serialized(tmp_path,monkeypatch,actions,expected):
    import submission.stem_ui.app as app

    class Renderer:
        def __init__(self,settings):
            self.mode='solid'; self.droidcam_host='192.168.1.25'; self.droidcam_port='4747'
            self.droidcam_dialog=False; self.grab=type('G',(),{'slots':(), 'suspended':False})()
            self.grab.scale_mode='uniform'
            pose=type('P',(),{})(); pose.scale=1.; pose.stretch=type('A',(),{'tolist':lambda self:[1,1,1]})()
            pose.position=type('A',(),{'tolist':lambda self:[0,0,0]})(); pose.rotation=type('A',(),{'tolist':lambda self:[[1,0,0],[0,1,0],[0,0,1]]})()
            self.grab.pose=pose; self.grab.feedback=''; self.last_draw_cpu_ms=0.; self.actual_msaa_samples=0
            self.chemistry=type('C',(),{'scene':type('S',(),{'state':lambda self:{}})(),
                'input':type('I',(),{'diagnostics':lambda self:{}})()})()
            self.actions=iter(actions)
        def open(self): pass
        def close(self): pass
        def enter_chemistry(self): pass
        def events(self): return next(self.actions,('quit',))
        def draw(self,*args,**kwargs):
            for w in Worker.instances:
                if w.closing:
                    w.closing-=1
                    if not w.closing: w.finish()
            return 0,0

    class Worker:
        instances=[]; live=0; overlap=False
        def __init__(self,settings,*,camera_index=0,droidcam_wifi=None,replay=None):
            self.kind='droidcam_wifi' if droidcam_wifi else 'webcam'
            self.droidcam_wifi=droidcam_wifi; self.camera_index=camera_index
            self.error=None; self.latest=None; self.finished=False; self.closing=0
            self.thread=type('Thread',(),{'join':lambda thread,timeout:self.finish()})()
            self._alive=False; self.run_id=f'test-{len(self.instances)}'; self.instances.append(self)
        @property
        def alive(self): return self._alive
        def start(self):
            if Worker.live: Worker.overlap=True
            self._alive=True; Worker.live+=1
        def stop(self):
            if self._alive and not self.closing: self.closing=2
        def finish(self):
            if self._alive: self._alive=False; Worker.live-=1
            self.finished=True

    monkeypatch.setattr(app,'ROOT',tmp_path)
    monkeypatch.setattr(app,'SubmissionRenderer',Renderer)
    monkeypatch.setattr(app,'CaptureWorker',Worker)
    monkeypatch.setattr(sys,'argv',['stem-ui'])
    prefs=tmp_path/'runs/ui/droidcam.json'; prefs.parent.mkdir(parents=True)
    prefs.write_text('[]',encoding='utf-8')
    app.main()
    assert not Worker.overlap and Worker.live==0
    assert [w.kind for w in Worker.instances]==expected
    assert all(w.droidcam_wifi==('192.168.1.25',4747) for w in Worker.instances if w.kind=='droidcam_wifi')

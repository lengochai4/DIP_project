"""DroidCam Wi-Fi presentation source contract without a physical phone."""
import numpy as np
import pytest

from submission.stem_ui.network_camera import (
    DroidCamWifiSource, droidcam_video_url, normalize_droidcam_endpoint,
)


def test_droidcam_endpoint_is_explicit_and_uses_official_video_path():
    assert normalize_droidcam_endpoint(' 192.168.1.25 ','4747')==('192.168.1.25',4747)
    assert normalize_droidcam_endpoint('phone.local',4748)==('phone.local',4748)
    assert droidcam_video_url('192.168.1.25',4747)=='http://192.168.1.25:4747/video'
    for host in ('','http://192.168.1.25','192.168.1.25:4747','192.168.1.25/video','999.999.999.999'):
        with pytest.raises(ValueError): normalize_droidcam_endpoint(host,4747)
    for port in ('abc',80,65536):
        with pytest.raises(ValueError): normalize_droidcam_endpoint('192.168.1.25',port)


def test_droidcam_source_emits_raw_bgr_packets_and_releases_capture():
    image=np.full((4,6,3),73,np.uint8)
    class Capture:
        released=False
        def isOpened(self): return True
        def set(self,*args): return True
        def read(self): return True,image
        def release(self): self.released=True
    capture=Capture(); times=iter((10.,10.05))
    source=DroidCamWifiSource(run_id='wifi-test',host='192.168.1.25',port=4747,
        clock=lambda:next(times),capture_factory=lambda url:capture)
    source.open(); packet=source.read()
    assert packet.run_id=='wifi-test' and packet.frame_id==0
    assert packet.timestamp_s==pytest.approx(.05)
    assert packet.source_name=='droidcam_wifi'
    assert packet.image is image
    assert source.url=='http://192.168.1.25:4747/video'
    source.close(); assert capture.released


def test_droidcam_open_and_read_failures_are_explicit():
    class Closed:
        released=False
        def isOpened(self): return False
        def release(self): self.released=True
    closed=Closed()
    source=DroidCamWifiSource(run_id='wifi-test',host='192.168.1.25',port=4747,
        capture_factory=lambda url:closed)
    with pytest.raises(RuntimeError,match='Không kết nối được DroidCam'): source.open()
    assert closed.released

    class Drops:
        def isOpened(self): return True
        def set(self,*args): return True
        def read(self): return False,None
        def release(self): pass
    source=DroidCamWifiSource(run_id='wifi-test',host='192.168.1.25',port=4747,
        clock=lambda:1.,capture_factory=lambda url:Drops())
    source.open()
    with pytest.raises(RuntimeError,match='Mất hình DroidCam'): source.read()
    source.close()

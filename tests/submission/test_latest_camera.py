"""Thread ownership, freshness and failure behavior without a physical camera."""
import threading
from types import SimpleNamespace
import numpy as np
import pytest
from dip_touchless.core import FramePacket,ColorSpace
from submission.stem_ui.acquisition import LatestCamera


def packet(i):
    return FramePacket('fixture',i,i/30,np.full((4,4,3),i,np.uint8),ColorSpace.BGR,'camera:fixture')


def test_slow_consumer_receives_newest_packet_and_keeps_original_time_and_ids():
    stop=threading.Event(); produced=threading.Event(); close_threads=[]
    class Source:
        i=0
        def open(self): self.owner=threading.get_ident()
        def read(self):
            assert threading.get_ident()==self.owner
            if self.i==5:
                produced.set(); stop.wait(2); return None
            p=packet(self.i); self.i+=1; return p
        def close(self): close_threads.append(threading.get_ident()); assert close_threads[-1]==self.owner
    camera=LatestCamera(Source,stop,1)
    try:
        camera.open(); assert produced.wait(1)
        p=camera.read()
        assert p.frame_id==4 and p.timestamp_s==4/30 and camera.dropped==4
        assert not p.image.flags.writeable
        assert camera.last_wait_ms>=0
    finally: camera.close()
    assert not camera.alive and close_threads


def test_capture_exception_is_explicit_and_closes_on_owner_thread():
    closed=threading.Event()
    class Source:
        def open(self): raise RuntimeError('fixture open error')
        def close(self): closed.set()
    camera=LatestCamera(Source,threading.Event(),1)
    with pytest.raises(RuntimeError,match='fixture open error'): camera.open()
    with pytest.raises(RuntimeError,match='fixture open error'): camera.close()
    assert closed.is_set() and not camera.alive


def test_stop_unblocks_waiting_consumer_and_does_not_invent_packet():
    entered=threading.Event(); stop=threading.Event()
    class Source:
        def open(self): pass
        def read(self): entered.set(); stop.wait(2); return None
        def close(self): pass
    camera=LatestCamera(Source,stop,1); result=[]
    camera.open(); assert entered.wait(1)
    reader=threading.Thread(target=lambda:result.append(camera.read())); reader.start()
    camera.close(); reader.join(1)
    assert not reader.is_alive() and result==[None]


def test_blocked_driver_is_reported_and_ownership_stays_alive_until_exit():
    release=threading.Event(); entered=threading.Event()
    class Source:
        def open(self): pass
        def read(self): entered.set(); release.wait(2); return None
        def close(self): pass
    camera=LatestCamera(Source,threading.Event(),.01)
    try:
        camera.open(); assert entered.wait(1)
        with pytest.raises(RuntimeError,match='Camera chưa đóng'): camera.close()
        assert camera.alive
        from submission.stem_ui.runtime import CaptureWorker
        worker=CaptureWorker({}); worker.camera_pump=camera
        assert worker.alive
    finally:
        release.set(); camera.close()
    assert not camera.alive


def test_source_buffer_reuse_cannot_mutate_delivered_frame():
    emitted=threading.Event(); mutate=threading.Event(); stop=threading.Event()
    image=packet(1).image
    class Source:
        i=0
        def open(self): pass
        def read(self):
            if not self.i:
                self.i=1; return FramePacket('fixture',1,1.,image,ColorSpace.BGR,'fixture')
            emitted.set(); mutate.wait(2); image.fill(99); stop.wait(2); return None
        def close(self): pass
    camera=LatestCamera(Source,stop,1)
    try:
        camera.open(); assert emitted.wait(1)
        p=camera.read(); mutate.set()
        assert np.all(p.image==1) and not np.shares_memory(p.image,image)
    finally: mutate.set(); camera.close()

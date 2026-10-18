"""Presentation-only DroidCam Wi-Fi source.

The phone exposes an MJPEG/HTTP feed at ``http://HOST:PORT/video``.  This
adapter produces the same project FramePacket contract as the local webcam
without changing Core preprocessing or interaction logic.
"""
from __future__ import annotations

from collections.abc import Callable
import ipaddress
import math
import re
import time

import cv2
import numpy as np

from dip_touchless.core import ColorSpace, FramePacket


_HOSTNAME = re.compile(r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)*"
                       r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


def normalize_droidcam_endpoint(host: str, port: int | str) -> tuple[str, int]:
    """Validate the Wi-Fi address shown by the DroidCam phone app."""
    host=str(host).strip()
    if not host:
        raise ValueError('Nhập Wi-Fi IP của điện thoại trong DroidCam.')
    if '://' in host or '/' in host or '\\' in host or ':' in host:
        raise ValueError('Chỉ nhập IP/hostname, không nhập http://, port hay /video.')
    try:
        ipaddress.ip_address(host)
    except ValueError:
        if re.fullmatch(r'[0-9.]+',host) or not _HOSTNAME.fullmatch(host):
            raise ValueError('Wi-Fi IP/hostname DroidCam không hợp lệ.') from None
    try:
        port=int(str(port).strip())
    except (TypeError,ValueError):
        raise ValueError('Port DroidCam phải là số.') from None
    if not 1024 <= port <= 65535:
        raise ValueError('Port DroidCam phải nằm trong 1024–65535.')
    return host,port


def droidcam_video_url(host: str, port: int | str) -> str:
    host,port=normalize_droidcam_endpoint(host,port)
    return f'http://{host}:{port}/video'


class DroidCamWifiSource:
    """Raw BGR network camera source with bounded OpenCV network timeouts."""
    def __init__(self, *, run_id: str, host: str, port: int | str,
                 open_timeout_ms: int=3500, read_timeout_ms: int=2500,
                 clock: Callable[[],float]=time.perf_counter,
                 capture_factory: Callable[[str],object] | None=None):
        if not run_id: raise ValueError('run_id must not be empty')
        self.host,self.port=normalize_droidcam_endpoint(host,port)
        self.url=droidcam_video_url(self.host,self.port)
        self.run_id=run_id
        self.open_timeout_ms=max(250,int(open_timeout_ms))
        self.read_timeout_ms=max(250,int(read_timeout_ms))
        self.clock=clock; self.capture_factory=capture_factory
        self.capture=None; self.start_time=None; self.last_timestamp=None; self.frame_id=0

    def _capture(self):
        if self.capture_factory is not None:
            return self.capture_factory(self.url)
        params=[]
        if hasattr(cv2,'CAP_PROP_OPEN_TIMEOUT_MSEC'):
            params += [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,self.open_timeout_ms]
        if hasattr(cv2,'CAP_PROP_READ_TIMEOUT_MSEC'):
            params += [cv2.CAP_PROP_READ_TIMEOUT_MSEC,self.read_timeout_ms]
        if params and hasattr(cv2,'CAP_FFMPEG'):
            return cv2.VideoCapture(self.url,cv2.CAP_FFMPEG,params)
        return cv2.VideoCapture(self.url)

    def open(self):
        if self.capture is not None: raise RuntimeError('DroidCam Wi-Fi đã mở.')
        capture=self._capture()
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(
                f'Không kết nối được DroidCam Wi-Fi {self.host}:{self.port}. '
                'Kiểm tra cùng Wi-Fi, IP/port trên điện thoại và DroidCam đang phát video.')
        try: capture.set(cv2.CAP_PROP_BUFFERSIZE,1)
        except Exception: pass
        started=self.clock()
        if not math.isfinite(started):
            capture.release(); raise RuntimeError('camera clock returned a non-finite value')
        self.capture=capture; self.start_time=started; self.last_timestamp=None; self.frame_id=0

    def read(self):
        if self.capture is None or self.start_time is None:
            raise RuntimeError('DroidCam Wi-Fi chưa mở.')
        ok,frame=self.capture.read()
        if not ok:
            raise RuntimeError('Mất hình DroidCam Wi-Fi. Kiểm tra điện thoại và kết nối Wi-Fi.')
        if not isinstance(frame,np.ndarray) or frame.size==0 or frame.dtype!=np.uint8 or frame.ndim!=3 or frame.shape[2]!=3:
            raise RuntimeError('Khung hình DroidCam không phải ảnh BGR uint8 hợp lệ.')
        now=self.clock()
        if not math.isfinite(now): raise RuntimeError('camera clock returned a non-finite value')
        timestamp=now-self.start_time
        if timestamp<0 or (self.last_timestamp is not None and timestamp<=self.last_timestamp):
            raise RuntimeError('Dấu thời gian DroidCam không tăng.')
        packet=FramePacket(self.run_id,self.frame_id,timestamp,frame,ColorSpace.BGR,'droidcam_wifi')
        self.frame_id+=1; self.last_timestamp=timestamp
        return packet

    def close(self):
        if self.capture is not None: self.capture.release()
        self.capture=None; self.start_time=None; self.last_timestamp=None

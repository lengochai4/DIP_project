"""Live-only single-slot camera delivery; deterministic replay bypasses this."""
from dataclasses import replace
import threading
import time


class LatestCamera:
    """One thread owns open/read/close. A slow consumer never builds a queue."""
    def __init__(self, factory, stop_event, shutdown_timeout_s):
        self.factory = factory
        self.stop_event = stop_event
        self.shutdown_timeout_s = shutdown_timeout_s
        self.condition = threading.Condition()
        self.ready = threading.Event()
        self.pending = None
        self.error = None
        self.done = False
        self.dropped = 0
        self.thread = None
        self.last_wait_ms = 0.0

    @property
    def alive(self):
        return self.thread is not None and self.thread.is_alive()

    def open(self):
        if self.thread is not None:
            raise RuntimeError('camera pump already started')
        self.thread = threading.Thread(target=self._capture, name='ui-camera', daemon=True)
        self.thread.start()
        while not self.ready.wait(.05):
            if self.stop_event.is_set():
                return
        if self.error:
            raise RuntimeError(self.error)

    def _capture(self):
        source = None
        try:
            source = self.factory()
            source.open()
            self.ready.set()
            while not self.stop_event.is_set():
                packet = source.read()
                if packet is None:
                    break
                # Detach from backends that reuse their pixel buffers.
                image = packet.image.copy()
                image.setflags(write=False)
                packet = replace(packet, image=image)
                with self.condition:
                    if self.pending is not None:
                        self.dropped += 1
                    self.pending = (packet, time.monotonic())
                    self.condition.notify_all()
        except Exception as exc:
            self.error = str(exc)
        finally:
            if source is not None:
                try:
                    source.close()
                except Exception as exc:
                    self.error = self.error or str(exc)
            self.ready.set()
            with self.condition:
                self.done = True
                self.condition.notify_all()

    def read(self):
        with self.condition:
            while self.pending is None and not self.done and not self.stop_event.is_set():
                self.condition.wait(.05)
            if self.stop_event.is_set():
                return None
            if self.error:
                raise RuntimeError(self.error)
            if self.pending is None:
                return None
            packet, delivered = self.pending
            self.pending = None
            self.last_wait_ms = (time.monotonic()-delivered)*1000
            return packet

    def close(self):
        self.stop_event.set()
        with self.condition:
            self.condition.notify_all()
        if self.thread:
            self.thread.join(timeout=self.shutdown_timeout_s)
            if self.alive:
                raise RuntimeError('Camera chưa đóng: đang chờ trình điều khiển trả lượt đọc. Không mở phiên chồng lên.')
        if self.error:
            raise RuntimeError(self.error)

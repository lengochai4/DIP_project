"""Optional application MediaPipe adapter; never imported by Core or scene/UI code."""

import math
from dip_touchless.core import ColorSpace, CoordinateSpace, Landmark

class TwoHandProvider:
    """Separate VIDEO landmarker, 2 hands; no change to Core's model/ROI/filter path."""
    def __init__(self, model_path, tracking_config, *, landmarker=None):
        self._closed = False
        self._last_ms = None
        if landmarker is not None:
            self.landmarker = landmarker
            return
        import mediapipe as mp
        from pathlib import Path
        if not Path(model_path).is_file():
            raise FileNotFoundError(f"Two-hand model not found: {model_path}")
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO, num_hands=2,
            min_hand_detection_confidence=tracking_config["min_hand_detection_confidence"],
            min_hand_presence_confidence=tracking_config["min_hand_presence_confidence"],
            min_tracking_confidence=tracking_config["min_tracking_confidence"])
        self.landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)

    def process(self, packet):
        if self._closed:
            raise RuntimeError("two-hand provider closed")
        import cv2
        import numpy as np
        import mediapipe as mp
        if packet.color_space is not ColorSpace.BGR or packet.image.dtype != np.uint8 or packet.image.ndim != 3 or packet.image.shape[2] != 3:
            raise ValueError("two-hand provider requires uint8 BGR source")
        timestamp = round(packet.timestamp_s*1000)
        if timestamp < 0 or self._last_ms is not None and timestamp <= self._last_ms:
            raise ValueError("two-hand VIDEO timestamps must increase")
        image = mp.Image(image_format=mp.ImageFormat.SRGB,
                        data=np.ascontiguousarray(cv2.cvtColor(packet.image, cv2.COLOR_BGR2RGB)))
        result = self.landmarker.detect_for_video(image, timestamp)
        self._last_ms = timestamp
        hands = []
        for points in result.hand_landmarks:
            if len(points) != 21 or any(not all(math.isfinite(float(v)) for v in (p.x, p.y, p.z)) for p in points):
                return ()
            hands.append(tuple(Landmark(i, float(p.x), float(p.y), float(p.z), CoordinateSpace.FRAME_NORMALIZED)
                               for i, p in enumerate(points)))
        return tuple(hands) if len(hands) <= 2 else ()

    def close(self):
        if not self._closed:
            self._closed = True
            self.landmarker.close()

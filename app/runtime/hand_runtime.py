"""Optional two-hand product pipeline using public Core components, never changing G7."""

from dataclasses import replace
import math
import cv2
import numpy as np
from dip_touchless.core import (
    ColorSpace,
    CoordinateSpace,
    Landmark,
    LandmarkObservation,
    MeasurementQuality,
    TrackingStatus,
    ROI,
    ROIState,
)
from dip_touchless.filtering import FixedOneEuroLandmarkFilter
from dip_touchless.preprocessing import (
    AdaptivePreprocessor,
    IlluminationAnalyzer,
    IlluminationDecisionStabilizer,
)
from dip_touchless.tracking import MeasurementValidator
from app.interaction.bimanual import Detection, HandAssociation


class ProductHandRuntime:
    """Separate local full-frame P1 + provider + per-associated-hand canonical F1.

    All product observations/logs are distinct from frozen Core/evidence.
    Handedness is classification metadata only. Processing uses an explicit
    horizontally mirrored provider input; outputs return to original frame x.
    This follows the documented MediaPipe mirrored handedness convention.
    """

    def __init__(self, model_path, core_config, config, *, landmarker=None):
        self.config = config
        self.association = HandAssociation(config)
        self.filters = {}
        self.last = None
        self.closed = False
        self.validator = MeasurementValidator()
        light = core_config["illumination"]
        self.analyzer = IlluminationAnalyzer()
        self.decision = IlluminationDecisionStabilizer(**light)
        clahe = core_config["clahe"]
        self.preprocessor = AdaptivePreprocessor(
            policy=clahe["policy"],
            clip_limit=clahe["clip_limit"],
            tile_grid_size=tuple(clahe["tile_grid_size"]),
        )
        if landmarker is not None:
            self.landmarker = landmarker
        else:
            import mediapipe as mp

            tracking = core_config["tracking"]
            options = mp.tasks.vision.HandLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
                running_mode=mp.tasks.vision.RunningMode.VIDEO,
                num_hands=2,
                min_hand_detection_confidence=tracking["min_hand_detection_confidence"],
                min_hand_presence_confidence=tracking["min_hand_presence_confidence"],
                min_tracking_confidence=tracking["min_tracking_confidence"],
            )
            self.landmarker = mp.tasks.vision.HandLandmarker.create_from_options(
                options
            )
        self.last_ms = None

    def _filter(self):
        c = self.config
        return FixedOneEuroLandmarkFilter(
            min_cutoff_hz=c.filter_min_cutoff_hz,
            beta=c.filter_beta,
            derivative_cutoff_hz=c.filter_derivative_cutoff_hz,
            reset_gap_s=c.max_gap_s,
        )

    def reset(self):
        self.association.reset()
        self.filters.clear()
        self.last = None
        self.decision.reset()

    def process(self, packet):
        import mediapipe as mp

        if self.closed:
            raise RuntimeError("product hand runtime closed")
        if (
            packet.color_space is not ColorSpace.BGR
            or packet.image.dtype != np.uint8
            or packet.image.ndim != 3
            or packet.image.shape[2] != 3
        ):
            raise ValueError("product hand runtime requires BGR uint8")
        h, w = packet.image.shape[:2]
        identity = (packet.run_id, packet.frame_id, packet.timestamp_s, w, h)
        gap = (
            self.last is None
            or packet.run_id != self.last[0]
            or packet.frame_id <= self.last[1]
            or not 0 < packet.timestamp_s - self.last[2] <= self.config.max_gap_s
            or identity[3:] != self.last[3:]
        )
        if gap:
            self.reset()
        self.last = identity
        roi = ROI(0, 0, w, h, ROIState.SEARCHING)
        illumination = self.decision.update(self.analyzer.measure(packet, roi))
        prepared = self.preprocessor.process_frame(packet, roi, illumination).frame
        # Product-local inference explicitly mirrors input; source/Core pixels are untouched.
        rgb = cv2.cvtColor(cv2.flip(prepared.image, 1), cv2.COLOR_BGR2RGB)
        ms = round(packet.timestamp_s * 1000)
        if self.last_ms is not None and ms <= self.last_ms:
            self.reset()
            return {}, False, "VIDEO_TIMESTAMP_DISCONTINUITY"
        result = self.landmarker.detect_for_video(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)),
            ms,
        )
        self.last_ms = ms
        detections = []
        for i, points in enumerate(result.hand_landmarks):
            if len(points) != 21 or any(
                not all(math.isfinite(float(v)) for v in (p.x, p.y, p.z))
                for p in points
            ):
                self.reset()
                return {}, False, "INVALID_PROVIDER_GEOMETRY"
            label = None
            if i < len(result.handedness) and result.handedness[i]:
                label = result.handedness[i][0].category_name
            landmarks = tuple(
                Landmark(
                    j,
                    1 - float(p.x),
                    float(p.y),
                    float(p.z),
                    CoordinateSpace.FRAME_NORMALIZED,
                )
                for j, p in enumerate(points)
            )
            detections.append(Detection(landmarks, label))
        previous_keys = set(self.filters)
        associated = self.association.update(detections, w / h)
        if set(associated) != previous_keys:
            self.filters = {k: self._filter() for k in associated}
            gap = True
        filtered = {}
        ordinary = not gap and bool(associated)
        for label, detection in associated.items():
            observation = LandmarkObservation(
                packet.frame_id,
                packet.timestamp_s,
                TrackingStatus.VALID,
                detection.landmarks,
                label,
                None,
                MeasurementQuality.unavailable(),
                None,
                "product_mediapipe_two_hand",
            )
            observation = self.validator.validate(observation)
            landmarks, diagnostics = self.filters[label].update(observation)
            ordinary = (
                ordinary
                and not diagnostics.reset_occurred
                and observation.status is TrackingStatus.VALID
            )
            if landmarks:
                filtered[label] = landmarks
        if not filtered:
            self.filters.clear()
        return filtered, ordinary, self.association.reason

    def close(self):
        if not self.closed:
            self.closed = True
            try:
                self.landmarker.close()
            finally:
                self.reset()

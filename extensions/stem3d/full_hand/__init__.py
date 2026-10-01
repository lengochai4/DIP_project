"""Additive full-hand geometry; deliberately not wired into the application."""

from .contracts import (
    Finger, FingerGeometry, FrameGeometry, GeometryReason, HandGeometry,
    PalmGeometry, ThumbGeometry,
)
from .geometry import extract_hand_geometry
from .finger_states import estimate_finger_state
from .pose_classifier import classify_pose, evaluate_pinch_geometry
from .pose_contracts import (
    ClassificationReason, FingerObservation, FingerState, FingerThresholds,
    HandPose, PinchGeometry, PoseObservation, PoseThresholds, PredicateDiagnostic,
    ThumbThresholds,
)

__all__ = [
    "Finger", "FingerGeometry", "FrameGeometry", "GeometryReason",
    "HandGeometry", "PalmGeometry", "ThumbGeometry", "extract_hand_geometry",
    "ClassificationReason", "FingerObservation", "FingerState", "FingerThresholds",
    "HandPose", "PinchGeometry", "PoseObservation", "PoseThresholds",
    "PredicateDiagnostic", "ThumbThresholds", "estimate_finger_state",
    "classify_pose", "evaluate_pinch_geometry",
]

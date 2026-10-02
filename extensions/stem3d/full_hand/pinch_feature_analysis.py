"""Read-only offline PINCH feature investigation; never a pose/action predicate.

Reuse A2 palm/finger geometry. Additional distal directions use only filtered
aspect-corrected x/y. No z, handedness, fitted thresholds or runtime injection.
"""

from dataclasses import dataclass
import math

from dip_touchless.core import TrackingFrame

from .contracts import FrameGeometry, GeometryReason
from .geometry import extract_hand_geometry


@dataclass(frozen=True, slots=True)
class FeatureDiagnostic:
    name: str
    value: float | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class PinchFeatureObservation:
    frame_geometry: FrameGeometry
    geometry_valid: bool
    features: tuple[FeatureDiagnostic, ...]
    geometry_reasons: tuple[GeometryReason, ...]


def extract_pinch_features(
    frame: TrackingFrame, geometry: FrameGeometry,
) -> PinchFeatureObservation:
    """Report geometry, including unavailable directions, without classifying.

    Cosines are invariant under reflection and use directed distal segments:
    thumb 3->4, index 7->8; gap is 4->8. A coincident tip pair has no gap
    direction, even when the remaining A2 geometry is valid.
    """
    hand = extract_hand_geometry(frame, geometry)
    if not hand.valid:
        return PinchFeatureObservation(geometry, False, (), hand.reasons)
    features = [FeatureDiagnostic("distance_palm", hand.thumb_index_distance_palm),
                FeatureDiagnostic("palm_width_image_height", hand.palm.width_image_height)]
    for finger in hand.fingers:
        name = finger.finger.value.lower()
        features.extend((
            FeatureDiagnostic(name + "_straightness", finger.straightness),
            FeatureDiagnostic(name + "_joint_1_rad", finger.joint_angles_rad[0]),
            FeatureDiagnostic(name + "_joint_2_rad", finger.joint_angles_rad[1]),
            FeatureDiagnostic(name + "_tip_lateral_palm", finger.tip_in_palm[0]),
            FeatureDiagnostic(name + "_tip_distal_palm", finger.tip_in_palm[1]),
        ))
        if finger.thumb is not None:
            features.extend((
                FeatureDiagnostic("thumb_axis_to_palm_rad", finger.thumb.axis_to_palm_rad),
                FeatureDiagnostic("thumb_to_index_mcp_palm", finger.thumb.tip_to_index_mcp_palm),
                FeatureDiagnostic("thumb_to_pinky_mcp_palm", finger.thumb.tip_to_pinky_mcp_palm),
            ))
    points = {p.index: (p.x * geometry.width / geometry.height, p.y)
              for p in frame.filtered_landmarks}
    def sub(a, b):
        return (a[0] - b[0], a[1] - b[1])
    def dot(a, b):
        return math.fsum((a[0] * b[0], a[1] * b[1]))
    def cosine(name, a, b):
        na, nb = math.hypot(*a), math.hypot(*b)
        if na == 0 or nb == 0:
            return FeatureDiagnostic(name, None, "DIRECTION_UNAVAILABLE")
        # Normalize before dotting to avoid multiplying tiny lengths.
        value = dot((a[0] / na, a[1] / na), (b[0] / nb, b[1] / nb))
        return FeatureDiagnostic(name, max(-1., min(1., value)))
    thumb = sub(points[4], points[3])
    index = sub(points[8], points[7])
    gap = sub(points[8], points[4])
    features.extend((
        cosine("distal_segment_cosine", thumb, index),
        cosine("thumb_toward_index_cosine", thumb, gap),
        cosine("index_toward_thumb_cosine", index, (-gap[0], -gap[1])),
        FeatureDiagnostic("gap_lateral_palm", dot(gap, hand.palm.lateral_axis) / hand.palm.width_image_height),
        FeatureDiagnostic("gap_distal_palm", dot(gap, hand.palm.distal_axis) / hand.palm.width_image_height),
    ))
    return PinchFeatureObservation(geometry, True, tuple(features), ())

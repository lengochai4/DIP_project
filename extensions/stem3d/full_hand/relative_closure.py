"""Pure A2 relative extent/evidence; not a pose classifier or temporal tracker.

ENTRY denotes extent, CLOSING denotes a noise-separated positive excursion from
the enrolled median. Neither proves fresh motion, dwell, arming, or intention.
Those qualifications belong to a later tracker. A static closed hand can have
ENTRY geometry here but cannot authorize anything. There is no command output.
"""

import math

from dip_touchless.core import TrackingStatus

from .contracts import HandGeometry
from .intent_pinch_contracts import (
    IntentPinchReason as Reason, IntentPredicateDiagnostic as Predicate,
    ProjectionCompatibility, ReferenceEvent, ReferenceScope, ReleaseReference,
    RelativeClosureObservation, RelativeClosureThresholds, RelativeClosureZone as Zone,
)
from .pinch_reference import invalidate_reference


def evaluate_relative_closure(
    geometry: HandGeometry, reference: ReleaseReference | None,
    thresholds: RelativeClosureThresholds, *, scope: ReferenceScope,
    tracking_status: TrackingStatus, filter_reset_occurred: bool,
    projection_compatibility: ProjectionCompatibility,
    event: ReferenceEvent | None = None,
) -> RelativeClosureObservation:
    """Evaluate without modifying input or adjusting the enrolled reference.

    A2 does not retain tracking/filter lifecycle flags or sufficient palm-shape
    information to establish projected-domain compatibility. Supply them
    explicitly. Unconfirmed comparison fails closed; no automatic pose/depth
    inference is made. Thread result.reference forward after invalidation.
    """
    if not isinstance(geometry, HandGeometry) or not isinstance(thresholds, RelativeClosureThresholds):
        raise TypeError("evaluator requires immutable geometry and thresholds")
    if reference is not None and not isinstance(reference, ReleaseReference):
        raise TypeError("reference must be immutable or None")
    if not isinstance(scope, ReferenceScope) or not isinstance(tracking_status, TrackingStatus):
        raise TypeError("scope and tracking status must be explicit")
    if type(filter_reset_occurred) is not bool:
        raise TypeError("filter reset must be explicit bool")
    if not isinstance(projection_compatibility, ProjectionCompatibility):
        raise TypeError("projection compatibility must be explicit")
    if event is not None:
        reference = invalidate_reference(reference, event)
    reasons = []
    usable_geometry = geometry.valid and geometry.palm is not None and geometry.thumb_index_distance_palm is not None
    if not usable_geometry:
        reasons.append(Reason.INVALID_GEOMETRY)
        reference = invalidate_reference(reference, ReferenceEvent.INVALID_GEOMETRY)
    if tracking_status is TrackingStatus.REACQUIRED:
        reasons.append(Reason.REACQUISITION)
        reference = invalidate_reference(reference, ReferenceEvent.REACQUISITION)
    elif tracking_status is not TrackingStatus.VALID:
        reasons.append(Reason.TRACKING_UNUSABLE)
        reference = invalidate_reference(reference, ReferenceEvent.TRACKING_LOSS)
    if filter_reset_occurred:
        reasons.append(Reason.FILTER_RESET)
        reference = invalidate_reference(reference, ReferenceEvent.FILTER_RESET)
    if geometry.frame_geometry.run_id != scope.run_id or (reference and reference.scope != scope):
        reasons.append(Reason.SCOPE_MISMATCH)
        scope_event = ReferenceEvent.DOMAIN_CHANGE
        if reference is not None and reference.scope.session_id != scope.session_id:
            scope_event = ReferenceEvent.SESSION_CHANGE
        elif geometry.frame_geometry.run_id != scope.run_id or (reference and reference.scope.run_id != scope.run_id):
            scope_event = ReferenceEvent.RUN_CHANGE
        reference = invalidate_reference(reference, scope_event)
    if projection_compatibility is not ProjectionCompatibility.CONFIRMED:
        reasons.append(Reason.COMPARISON_INCOMPATIBLE if projection_compatibility is ProjectionCompatibility.INCOMPATIBLE
                       else Reason.COMPARISON_UNCONFIRMED)
        # Missing projected comparison during loss is unverified metadata, not
        # evidence that the camera/palm domain changed. A real incompatible or
        # unconfirmed ordinary-valid domain still requires fresh enrollment.
        missing_during_loss = (projection_compatibility is ProjectionCompatibility.UNCONFIRMED
                               and (not usable_geometry or tracking_status is not TrackingStatus.VALID))
        reference = invalidate_reference(reference, ReferenceEvent.INVALID_GEOMETRY
                                         if missing_during_loss else ReferenceEvent.DOMAIN_CHANGE)
    if reference is None:
        reasons.append(Reason.NO_REFERENCE)
    elif geometry.frame_geometry.frame_id <= reference.source_frames[-1].frame_id or geometry.frame_geometry.timestamp_s <= reference.source_frames[-1].timestamp_s:
        reasons.append(Reason.PRE_ENROLLMENT_FRAME)
        reference = invalidate_reference(reference, ReferenceEvent.TIMESTAMP_DISCONTINUITY)
    distance = geometry.thumb_index_distance_palm if usable_geometry else None
    width = geometry.palm.width_image_height if usable_geometry else None
    numerator = None
    if usable_geometry:
        if distance < 0 or width <= 0 or not all(math.isfinite(v) for v in (distance, width)):
            reasons.append(Reason.INVALID_GEOMETRY)
            reference = invalidate_reference(reference, ReferenceEvent.INVALID_GEOMETRY)
            usable_geometry = False
            distance, width = None, None
        else:
            numerator = distance * width
            if not math.isfinite(numerator):
                reasons.append(Reason.NUMERICAL_FAILURE)
                reference = invalidate_reference(reference, ReferenceEvent.INVALID_GEOMETRY)
                usable_geometry = False
                numerator = None
    if reference is not None and not reference.valid:
        reasons.append(Reason.REFERENCE_INACTIVE)
    closure = None
    if not reasons:
        closure = (reference.distance_palm - distance) / reference.distance_palm
        if not math.isfinite(closure):
            reasons.extend((Reason.NUMERICAL_FAILURE, Reason.REFERENCE_INACTIVE))
            reference = invalidate_reference(reference, ReferenceEvent.INVALID_GEOMETRY)
    if reasons:
        predicates = (
            Predicate("geometry_usable", usable_geometry, "A2 geometry and finite nonnegative distance"),
            Predicate("reference_active", reference is not None and reference.valid, "Explicit enrollment and lifecycle validity"),
            *(Predicate(name, None, "Unavailable: " + ",".join(r.value for r in dict.fromkeys(reasons)))
              for name in ("released", "closing", "band", "entry")),
        )
        return RelativeClosureObservation(
            geometry.frame_geometry, reference, usable_geometry,
            reference is not None and reference.valid, tuple(dict.fromkeys(reasons)),
            geometry.reasons, Zone.UNKNOWN, distance, numerator, width,
            None, None, None, None, None, predicates,
        )
    released = closure < thresholds.exit
    band = thresholds.exit <= closure <= thresholds.enter
    closing = closure > reference.noise_allowance_relative
    entry = closure > thresholds.enter and closing
    zone = Zone.RELEASED if released else Zone.BAND if band else Zone.ENTRY
    predicates = (
        Predicate("released", released, "relative_closure < exit", closure, thresholds.exit),
        Predicate("closing", closing, "relative_closure > measured relative noise allowance", closure, reference.noise_allowance_relative),
        Predicate("band", band, "exit <= relative_closure <= enter; never release evidence", closure),
        Predicate("entry", entry, "relative_closure > enter AND closing; extent only", closure, thresholds.enter),
    )
    return RelativeClosureObservation(
        geometry.frame_geometry, reference, True, True, (), (), zone,
        distance, numerator, width, closure, released, closing, band, entry, predicates,
    )

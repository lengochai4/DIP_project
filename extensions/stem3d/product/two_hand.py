"""Independent two-hand Extension provider/association; frozen provider stays one-hand.

Projected x/y association is not biometric identity. Ambiguous crossings revoke.
Both hands must remain OPEN; only projected palm separation controls scale.
"""

from dataclasses import dataclass, replace
from itertools import permutations
import math
from dip_touchless.core import (
    Landmark, TrackingStatus, TrackingFrame,
    FilterDiagnostics, FilterMode, MeasurementQuality, StageTimings,
)
from ..full_hand import extract_hand_geometry, classify_pose, HandPose
from ..full_hand.contracts import FrameGeometry


@dataclass(frozen=True, slots=True)
class TwoHandProfile:
    association_max_distance: float
    association_margin: float
    acquire_dwell_s: float
    max_gap_s: float
    distance_deadzone: float
    scale_gain: float
    scale_max_delta: float

    def __post_init__(self):
        if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0
               for v in (getattr(self, k) for k in self.__dataclass_fields__)):
            raise ValueError("two-hand policies must be explicit finite positive values")


@dataclass(frozen=True, slots=True)
class AssociatedHand:
    track_id: int
    landmarks: tuple[Landmark, ...]
    anchor_xy: tuple[float, float]


@dataclass(frozen=True, slots=True)
class TwoHandSnapshot:
    frame_geometry: FrameGeometry
    status: str
    hands: tuple[AssociatedHand, ...]
    armed: bool
    separation: float | None
    scale_delta: float
    reset_count: int
    reason: str


class TwoHandAssociation:
    def __init__(self, profile, pose_thresholds):
        self.profile, self.pose_thresholds = profile, pose_thresholds
        self._last = self._hands = self._since = self._distance = None
        self._next_id = 0
        self._reset_count = 0
        self.practical = False

    def reset(self):
        self._hands = self._since = self._distance = None
        self._last = None
        self._reset_count += 1

    def update(self, geometry, landmark_sets):
        reason = "ACQUIRING"
        old = self._last
        if old is not None and (old.run_id != geometry.run_id or geometry.frame_id <= old.frame_id
            or not 0 < geometry.timestamp_s-old.timestamp_s <= self.profile.max_gap_s
            or (old.width, old.height) != (geometry.width, geometry.height)):
            self.reset()
            reason = "DISCONTINUITY"
            return TwoHandSnapshot(geometry, "INVALID", (), False, None, 0., self._reset_count, reason)
        self._last = geometry
        if len(landmark_sets) != 2:
            self._hands = self._since = self._distance = None
            self._reset_count += 1
            return TwoHandSnapshot(geometry, "ONE_HAND_OR_LOST", (), False, None, 0., self._reset_count, "PAIR_REQUIRED")
        candidates, open_flags = [], []
        for landmarks in landmark_sets:
            frame = TrackingFrame(geometry.run_id, geometry.frame_id, geometry.timestamp_s, TrackingStatus.VALID,
                (), tuple(landmarks), MeasurementQuality.unavailable(), None, None,
                FilterDiagnostics(FilterMode.RAW, None, None, None, None, None, None, None, False),
                StageTimings(0., 0., 0., 0., 0.), ())
            hand = extract_hand_geometry(frame, geometry)
            if not hand.valid:
                self._hands = self._since = self._distance = None
                return TwoHandSnapshot(geometry, "INVALID", (), False, None, 0., self._reset_count, "INVALID_HAND_GEOMETRY")
            candidates.append(AssociatedHand(-1, tuple(landmarks), hand.palm.anchor_xy))
            observation = classify_pose(hand, self.pose_thresholds)
            if self.practical:
                from .simple_interaction import practical_pose
                open_flags.append(practical_pose(observation) == "OPEN")
            else:
                open_flags.append(observation.pose is HandPose.OPEN)
        aspect = geometry.width/geometry.height
        distance = lambda a, b: math.hypot((a[0]-b[0])*aspect, a[1]-b[1])
        separation = distance(candidates[0].anchor_xy, candidates[1].anchor_xy)
        if separation <= self.profile.association_margin:
            self._hands = self._since = self._distance = None
            self._reset_count += 1
            return TwoHandSnapshot(geometry, "AMBIGUOUS", (), False, separation, 0., self._reset_count, "PALMS_OVERLAP")
        if self._hands is None:
            candidates.sort(key=lambda h: h.anchor_xy)
            hands = tuple(replace(h, track_id=self._next_id+i) for i, h in enumerate(candidates))
            self._next_id += 2
        else:
            assignments = sorted((sum(distance(self._hands[i].anchor_xy, candidates[p[i]].anchor_xy) for i in range(2)), p)
                                 for p in permutations(range(2)))
            cost, assignment = assignments[0]
            ambiguous = assignments[1][0]-cost <= self.profile.association_margin
            far = any(distance(self._hands[i].anchor_xy, candidates[assignment[i]].anchor_xy)
                      > self.profile.association_max_distance for i in range(2))
            if ambiguous or far:
                self._hands = self._since = self._distance = None
                self._reset_count += 1
                return TwoHandSnapshot(geometry, "AMBIGUOUS", (), False, separation, 0., self._reset_count,
                                       "ASSOCIATION_AMBIGUOUS" if ambiguous else "MOTION_OUTSIDE_ASSOCIATION_DOMAIN")
            hands = tuple(replace(candidates[assignment[i]], track_id=self._hands[i].track_id) for i in range(2))
        self._hands = hands
        delta = 0.
        if not all(open_flags):
            self._since = self._distance = None
            status, armed, reason = "NEUTRAL", False, "BOTH_OPEN_REQUIRED"
        else:
            if self._since is None:
                self._since = geometry.timestamp_s
            armed = geometry.timestamp_s-self._since >= self.profile.acquire_dwell_s
            status = "STABLE" if armed else "ACQUIRING"
            if armed and self._distance is not None:
                change = math.log(separation/self._distance)
                delta = math.copysign(min(self.profile.scale_max_delta,
                    max(0., abs(change)-self.profile.distance_deadzone)*self.profile.scale_gain), change)
            self._distance = separation if armed else None
            reason = "PROJECTED_SCALE" if armed else "OPEN_DWELL"
        return TwoHandSnapshot(geometry, status, hands, armed, separation, delta, self._reset_count, reason)

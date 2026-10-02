"""Single-owner Extension command adapter. Public InteractionState is unchanged."""

from dataclasses import dataclass
import math
from dip_touchless.core import InteractionState, TrackingStatus
from ..full_hand.pose_contracts import HandPose
from ..full_hand.intent_temporal import IntentPinchState
from .settings import InputMode


def neutral(frame):
    return InteractionState(frame.run_id, frame.frame_id, frame.timestamp_s,
                            False, None, None, False, (0., 0.), 0.)


def response(value, deadzone, gain, limit):
    return math.copysign(min(limit, max(0., abs(value) - deadzone) * gain), value)


@dataclass(frozen=True, slots=True)
class CommandDiagnostics:
    owner: str
    reason: str
    anchor_reset_count: int
    raw_displacement: tuple[float, float]


class FullHandCommandMapper:
    def __init__(self, profile):
        self.profile = profile
        self._previous = None
        self._context = None
        self._owner = None
        self._waiting = False
        self._anchor = None
        self._action = None
        self._resets = 0
        self.diagnostics = CommandDiagnostics("LEGACY", "INITIAL", 0, (0., 0.))

    def reset(self):
        self._anchor = self._action = None
        self._waiting = True
        self._resets += 1

    def update(self, frame, legacy, full, intent, *, settings, sensitivity=1., focus="SCENE", context=()):
        identity = (frame.run_id, frame.frame_id, frame.timestamp_s)
        if settings.mode is not InputMode.FULL_HAND:
            self._context = self._owner = None
            self._anchor = self._action = None
            self._previous = identity
            self.diagnostics = CommandDiagnostics("LEGACY", "EXACT_LEGACY", self._resets, (0., 0.))
            return legacy if legacy is not None else neutral(frame)
        ref_valid = intent is not None and intent.reference is not None and intent.reference.valid
        owner = "FULL_HAND" if settings.mode is InputMode.FULL_HAND and ref_valid else "LEGACY"
        key = (settings, focus, context, intent.reference.reference_id if ref_valid else None)
        old = self._previous
        discontinuity = old is not None and (identity[0] != old[0] or identity[1] <= old[1]
            or not 0 < identity[2] - old[2] <= self.profile.max_gap_s)
        if key != self._context or owner != self._owner or discontinuity:
            # Initial LEGACY/OBSERVE is bit-for-bit legacy. Switching owners never carries a clutch.
            initial_legacy = self._context is None and owner == "LEGACY"
            self.reset()
            self._waiting = not initial_legacy
        self._context, self._owner = key, owner
        if old is None or identity[0] != old[0] or identity[1] > old[1] and identity[2] > old[2]:
            self._previous = identity
        raw = (0., 0.)
        reason = "LEGACY_FALLBACK" if owner == "LEGACY" else "NEUTRAL"
        out = neutral(frame)
        if discontinuity or frame.status is not TrackingStatus.VALID or frame.filter_diagnostics.reset_occurred:
            self.reset()
            reason = "DISCONTINUITY_OR_LOSS"
        elif owner == "LEGACY":
            if self._waiting and legacy is not None and legacy.interaction_valid and not legacy.pinch_active:
                self._waiting = False
            if not self._waiting and legacy is not None:
                out = legacy
        elif (full is None or not full.analysis_valid or full.hand is None or not full.hand.valid
              or intent.observation is None or not intent.observation.geometry_valid
              or intent.temporal.state is IntentPinchState.UNKNOWN):
            self.reset()
            reason = "UNKNOWN_OR_INVALID"
        else:
            temporal = intent.temporal
            if self._waiting and temporal.state is IntentPinchState.RELEASED and temporal.armed:
                self._waiting = False
            if not self._waiting:
                points = {p.index: p for p in frame.filtered_landmarks}
                tip = points.get(8)
                pointer = None if tip is None else (min(1., max(0., tip.x)), min(1., max(0., tip.y)))
                if pointer is not None and settings.mirror:
                    pointer = (1. - pointer[0], pointer[1])
                active = temporal.active_evidence
                point = (full.pose is not None and full.pose.pose is HandPose.POINT
                         and full.temporal.stable_pose is HandPose.POINT)
                action = "PINCH" if active else "POINT" if point else None
                anchor = full.hand.palm.anchor_xy if active else (None if tip is None else (tip.x, tip.y))
                rotation, scale = (0., 0.), 0.
                if action is not None and anchor is not None and self._action == action and self._anchor is not None:
                    aspect = full.frame_geometry.width / full.frame_geometry.height
                    raw = ((anchor[0] - self._anchor[0]) * aspect, anchor[1] - self._anchor[1])
                    if action == "POINT" and focus == "SCENE":
                        rotation = (response(raw[0] * (-1 if settings.mirror else 1), self.profile.rotation_deadzone,
                                             self.profile.rotation_gain*sensitivity, self.profile.rotation_max_delta),
                                    response(raw[1], self.profile.rotation_deadzone,
                                             self.profile.rotation_gain*sensitivity, self.profile.rotation_max_delta))
                    elif action == "PINCH" and focus == "SCENE":
                        scale = response(-raw[1], self.profile.scale_deadzone,
                                         self.profile.scale_gain*sensitivity, self.profile.scale_max_delta)
                if action != self._action:
                    self._resets += 1
                self._anchor, self._action = anchor if action else None, action
                # UNKNOWN in the old scalar classifier is diagnostic; intentional semantics
                # require currently valid relative evidence, not skin-contact classification.
                out = InteractionState(*identity, True, pointer, full.hand.thumb_index_distance_palm,
                                       active, rotation, scale)
                reason = action or "RELEASE_OR_NEUTRAL"
        self.diagnostics = CommandDiagnostics(owner, reason, self._resets, raw)
        return out

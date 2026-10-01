"""Extension-only immutable timing/state diagnostics; no motion commands."""

from dataclasses import dataclass
from enum import Enum
import math

from .pose_contracts import ClassificationReason, HandPose


class TemporalReason(str, Enum):
    INITIALIZATION = "INITIALIZATION"
    RUN_CHANGE = "RUN_CHANGE"
    TIMESTAMP_DISCONTINUITY = "TIMESTAMP_DISCONTINUITY"
    FRAME_DISCONTINUITY = "FRAME_DISCONTINUITY"
    TIMESTAMP_GAP = "TIMESTAMP_GAP"
    FILTER_RESET = "FILTER_RESET"
    EXPLICIT_RESET = "EXPLICIT_RESET"
    REACQUISITION = "REACQUISITION"
    TRACKING_LOSS = "TRACKING_LOSS"
    INVALID_OBSERVATION = "INVALID_OBSERVATION"
    UNKNOWN_INPUT = "UNKNOWN_INPUT"
    REARM_PENDING = "REARM_PENDING"
    REARMED = "REARMED"
    CANDIDATE_STARTED = "CANDIDATE_STARTED"
    CANDIDATE_CANCELLED = "CANDIDATE_CANCELLED"
    STABLE_TRANSITION = "STABLE_TRANSITION"
    SAFE_RELEASE = "SAFE_RELEASE"
    PINCH_BAND_HOLD = "PINCH_BAND_HOLD"


@dataclass(frozen=True, slots=True)
class TemporalPoseConfig:
    """Explicit caller-supplied seconds; no physical tuning/default profile."""

    enter_dwell_s: float
    exit_dwell_s: float
    pinch_enter_dwell_s: float
    pinch_exit_dwell_s: float
    rearm_dwell_s: float
    reset_gap_s: float

    def __post_init__(self) -> None:
        values = (self.enter_dwell_s, self.exit_dwell_s, self.pinch_enter_dwell_s,
                  self.pinch_exit_dwell_s, self.rearm_dwell_s, self.reset_gap_s)
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
            raise ValueError("timings must be finite seconds")
        if any(v < 0 for v in values[:-1]) or self.reset_gap_s <= 0:
            raise ValueError("dwell timings must be nonnegative and reset gap positive")


@dataclass(frozen=True, slots=True)
class StablePoseState:
    run_id: str | None
    frame_id: int | None
    timestamp_s: float | None
    candidate_pose: HandPose
    stable_pose: HandPose
    pending_pose: HandPose | None
    candidate_since_s: float | None
    rearm_since_s: float | None
    armed: bool
    # Stable pose/latch may be retained for diagnostics, but never implies
    # permission to act on UNKNOWN or an unconfirmed replacement candidate.
    action_allowed: bool
    pinch_latched: bool
    # Monotonic over this tracker object's lifetime, including explicit resets.
    transition_id: int
    reset_id: int
    reset_occurred: bool
    reasons: tuple[TemporalReason, ...]
    source_reasons: tuple[ClassificationReason, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_pose, HandPose) or not isinstance(self.stable_pose, HandPose):
            raise TypeError("candidate/stable poses must be HandPose")
        if self.pending_pose is not None and not isinstance(self.pending_pose, HandPose):
            raise TypeError("pending pose must be HandPose or None")
        for value in (self.timestamp_s, self.candidate_since_s, self.rearm_since_s):
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value)):
                raise ValueError("state times must be finite seconds or None")
        for value in (self.transition_id, self.reset_id):
            if type(value) is not int or value < 0:
                raise ValueError("diagnostic identities must be nonnegative integers")
        for value in (self.armed, self.action_allowed, self.pinch_latched, self.reset_occurred):
            if type(value) is not bool:
                raise TypeError("state flags must be bool")
        if (self.pending_pose is None) != (self.candidate_since_s is None):
            raise ValueError("pending pose and dwell reference must be available together")
        if self.pinch_latched != (self.stable_pose is HandPose.PINCH):
            raise ValueError("pinch latch must reflect stable PINCH identity")
        if self.action_allowed and (not self.armed or self.stable_pose is HandPose.UNKNOWN
                                    or self.candidate_pose is not self.stable_pose):
            raise ValueError("actions require armed, confirmed, currently known pose")
        for values, kind in ((self.reasons, TemporalReason),
                             (self.source_reasons, ClassificationReason)):
            if type(values) is not tuple or not all(isinstance(v, kind) for v in values):
                raise TypeError("state reasons must be immutable typed tuples")

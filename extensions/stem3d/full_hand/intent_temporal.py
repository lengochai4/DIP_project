"""Independent timestamped intentional-pinch diagnostics. No command output."""

from dataclasses import dataclass
from enum import Enum
import math

from .contracts import FrameGeometry
from .intent_pinch_contracts import RelativeClosureObservation


class IntentPinchState(str, Enum):
    UNKNOWN = "UNKNOWN"
    RELEASED = "RELEASED"
    CLOSING = "CLOSING"
    PINCH_ACTIVE = "PINCH_ACTIVE"
    HOLD = "HOLD"
    RELEASE = "RELEASE"


class IntentTransitionReason(str, Enum):
    INITIALIZATION = "INITIALIZATION"
    EXPLICIT_RESET = "EXPLICIT_RESET"
    RUN_CHANGE = "RUN_CHANGE"
    REFERENCE_CHANGE = "REFERENCE_CHANGE"
    TIMESTAMP_DISCONTINUITY = "TIMESTAMP_DISCONTINUITY"
    TIMESTAMP_GAP = "TIMESTAMP_GAP"
    UNKNOWN_INPUT = "UNKNOWN_INPUT"
    RELEASE_PENDING = "RELEASE_PENDING"
    RELEASE_CONFIRMED = "RELEASE_CONFIRMED"
    REARMED = "REARMED"
    CLOSING_STARTED = "CLOSING_STARTED"
    ENTRY_PENDING = "ENTRY_PENDING"
    ENTRY_CANCELLED = "ENTRY_CANCELLED"
    ENTERED = "ENTERED"
    HOLD_SUPPORTED = "HOLD_SUPPORTED"
    SAFE_RELEASE = "SAFE_RELEASE"
    BAND_WAIT = "BAND_WAIT"
    CANDIDATE_EXPIRED = "CANDIDATE_EXPIRED"
    REOPENED = "REOPENED"


@dataclass(frozen=True, slots=True)
class IntentTemporalConfig:
    enter_dwell_s: float
    release_dwell_s: float
    rearm_dwell_s: float
    reset_gap_s: float
    max_closing_age_s: float
    min_relative_progress: float
    progress_noise_multiplier: float

    def __post_init__(self):
        values = tuple(getattr(self, name) for name in self.__dataclass_fields__)
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
            raise ValueError("intent temporal parameters must be finite")
        if min(self.enter_dwell_s, self.release_dwell_s, self.rearm_dwell_s) < 0:
            raise ValueError("dwell must be nonnegative seconds")
        if self.reset_gap_s <= 0 or self.max_closing_age_s <= self.enter_dwell_s:
            raise ValueError("gap positive; closing lifetime must exceed enter dwell")
        if not 0 < self.min_relative_progress < 1 or self.progress_noise_multiplier < 1:
            raise ValueError("positive relative progress and noise multiplier >= 1 required")


@dataclass(frozen=True, slots=True)
class IntentPinchSnapshot:
    frame_geometry: FrameGeometry | None
    state: IntentPinchState
    armed: bool
    active_evidence: bool
    waiting_for_release: bool
    reference_id: str | None
    release_anchor_closure: float | None
    relative_progress: float | None
    closing_since_s: float | None
    enter_since_s: float | None
    release_since_s: float | None
    release_confirmed: bool
    cycle_id: int
    transition_id: int
    reset_id: int
    reasons: tuple[IntentTransitionReason, ...]

    def __post_init__(self):
        if self.frame_geometry is not None and not isinstance(self.frame_geometry, FrameGeometry):
            raise TypeError("actual frame identity required")
        if not isinstance(self.state, IntentPinchState):
            raise TypeError("intent state must be an enum")
        for v in (self.armed, self.active_evidence, self.waiting_for_release, self.release_confirmed):
            if type(v) is not bool:
                raise TypeError("intent flags must be booleans")
        for v in (self.release_anchor_closure, self.relative_progress, self.closing_since_s,
                  self.enter_since_s, self.release_since_s):
            if v is not None and (type(v) not in (int, float) or not math.isfinite(v)):
                raise ValueError("intent diagnostics must be finite or unavailable")
        if self.active_evidence != (self.state in (IntentPinchState.PINCH_ACTIVE, IntentPinchState.HOLD)):
            raise ValueError("only currently supported ACTIVE/HOLD can have active evidence")
        if self.active_evidence and (not self.armed or self.waiting_for_release):
            raise ValueError("unarmed/waiting states cannot be active")
        if self.state is IntentPinchState.UNKNOWN and self.armed:
            raise ValueError("UNKNOWN must be neutral")
        if any(type(v) is not int or v < 0 for v in (self.cycle_id, self.transition_id, self.reset_id)):
            raise ValueError("diagnostic identities must be monotonic nonnegative integers")
        if type(self.reasons) is not tuple or not all(isinstance(r, IntentTransitionReason) for r in self.reasons):
            raise TypeError("reasons must be an immutable enum tuple")


class TemporalIntentPinchTracker:
    """Consume A5.6 evidence only; UNKNOWN immediately revokes active evidence.

    The reference itself is owned by a separate lifecycle component. Timing is
    source time. Repeated/out-of-order frames reset safely, never advance dwell.
    """

    def __init__(self, config: IntentTemporalConfig):
        if not isinstance(config, IntentTemporalConfig):
            raise TypeError("explicit immutable temporal config required")
        self.config = config
        self._frame = None
        self._reference_key = None
        self._state = IntentPinchState.UNKNOWN
        self._anchor = self._closing = self._enter = self._release = None
        self._confirmed = False
        self._cycle_id = self._transition_id = self._reset_id = 0

    def _move(self, state):
        if state is not self._state:
            self._transition_id += 1
        self._state = state

    def _neutral(self):
        self._move(IntentPinchState.UNKNOWN)
        self._anchor = self._closing = self._enter = self._release = None
        self._confirmed = False

    def reset(self):
        self._neutral()
        self._reset_id += 1
        self._frame = self._reference_key = None
        return self._snapshot((IntentTransitionReason.EXPLICIT_RESET,))

    def _snapshot(self, reasons, observation=None):
        armed = self._state in (IntentPinchState.RELEASED, IntentPinchState.CLOSING,
                               IntentPinchState.PINCH_ACTIVE, IntentPinchState.HOLD)
        progress = None
        if observation and observation.valid and self._anchor is not None:
            progress = observation.relative_closure - self._anchor
        return IntentPinchSnapshot(
            self._frame, self._state, armed,
            self._state in (IntentPinchState.PINCH_ACTIVE, IntentPinchState.HOLD),
            not armed, self._reference_key[0] if self._reference_key else None,
            self._anchor, progress, self._closing, self._enter, self._release,
            self._confirmed, self._cycle_id, self._transition_id, self._reset_id, tuple(reasons),
        )

    def update(self, observation: RelativeClosureObservation):
        if not isinstance(observation, RelativeClosureObservation):
            raise TypeError("tracker requires immutable relative closure evidence")
        R, S = IntentTransitionReason, IntentPinchState
        frame, old = observation.frame_geometry, self._frame
        ref = observation.reference
        key = (ref.reference_id, ref.version, ref.scope, ref.distance_palm,
               ref.source_frames) if ref is not None else None
        reset = None
        if old is None:
            reset = R.INITIALIZATION
        elif frame.run_id != old.run_id:
            reset = R.RUN_CHANGE
        elif frame.frame_id <= old.frame_id or frame.timestamp_s <= old.timestamp_s:
            reset = R.TIMESTAMP_DISCONTINUITY
        elif frame.timestamp_s - old.timestamp_s > self.config.reset_gap_s:
            reset = R.TIMESTAMP_GAP
        elif key != self._reference_key:
            reset = R.REFERENCE_CHANGE
        if reset is not None:
            self._neutral()
            self._reset_id += 1
            # Do not lower the high-water identity within a run.
            self._frame = old if reset is R.TIMESTAMP_DISCONTINUITY else frame
            self._reference_key = key
            return self._snapshot((reset,))
        self._frame, self._reference_key = frame, key
        if not observation.valid:
            self._neutral()
            return self._snapshot((R.UNKNOWN_INPUT,))
        t, c = frame.timestamp_s, observation.relative_closure
        reasons = []
        if self._state in (S.UNKNOWN, S.RELEASE):
            if not observation.released:
                self._release = None
                self._confirmed = False
                return self._snapshot((R.BAND_WAIT,), observation)
            if self._release is None:
                self._release = t
            elapsed = t - self._release
            if not self._confirmed and elapsed >= self.config.release_dwell_s:
                self._confirmed = True
                reasons.append(R.RELEASE_CONFIRMED)
            if elapsed >= max(self.config.release_dwell_s, self.config.rearm_dwell_s):
                self._move(S.RELEASED)
                self._anchor = c
                self._closing = self._enter = self._release = None
                reasons.append(R.REARMED)
            else:
                reasons.append(R.RELEASE_PENDING)
            return self._snapshot(reasons, observation)  # Rearm frame is neutral.
        if self._state in (S.PINCH_ACTIVE, S.HOLD):
            if observation.released:
                self._move(S.RELEASE)
                self._release = t
                self._confirmed = False
                self._enter = self._closing = None
                return self._snapshot((R.SAFE_RELEASE,), observation)
            if not observation.closing:
                self._neutral()
                return self._snapshot((R.UNKNOWN_INPUT,))
            self._move(S.HOLD)
            return self._snapshot((R.HOLD_SUPPORTED,), observation)
        if observation.released:
            if self._state is S.CLOSING:
                reasons.append(R.REOPENED)
            self._move(S.RELEASED)
            self._anchor = c
            self._closing = self._enter = None
            return self._snapshot(reasons, observation)
        progress = c - self._anchor
        required = max(self.config.min_relative_progress,
                       ref.noise_allowance_relative * self.config.progress_noise_multiplier)
        if self._state is S.RELEASED:
            if not observation.closing or progress <= required:
                return self._snapshot((), observation)
            self._move(S.CLOSING)
            self._closing = t
            reasons.append(R.CLOSING_STARTED)
        if t - self._closing > self.config.max_closing_age_s:
            self._neutral()
            return self._snapshot((R.CANDIDATE_EXPIRED,))
        if not observation.entry or progress <= required:
            if self._enter is not None:
                reasons.append(R.ENTRY_CANCELLED)
            self._enter = None
            return self._snapshot(reasons, observation)
        if self._enter is None:
            self._enter = t
        if t - self._enter >= self.config.enter_dwell_s:
            self._move(S.PINCH_ACTIVE)
            self._cycle_id += 1
            self._enter = None
            reasons.append(R.ENTERED)
        else:
            reasons.append(R.ENTRY_PENDING)
        return self._snapshot(reasons, observation)

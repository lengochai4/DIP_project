"""Timestamp-driven pose stabilization, deliberately not wired into runtime."""

import math

from dip_touchless.core import TrackingStatus

from .contracts import Finger
from .pose_contracts import ClassificationReason, FingerState, HandPose, PoseObservation
from .temporal_contracts import StablePoseState, TemporalPoseConfig, TemporalReason as R


class TemporalPoseTracker:
    """Dwell on continuous candidates; safe cancellation overrides exit dwell.

    update requires explicit tracking status/reset metadata because A3 does not
    carry it. No source, Core engine, renderer, clock or frame-rate assumptions.
    """

    def __init__(self, config: TemporalPoseConfig) -> None:
        self.config = config
        self._run = None
        self._frame = None
        self._time = None
        self._stable = HandPose.UNKNOWN
        self._pending = None
        self._since = None
        self._rearm_since = None
        self._armed = False
        self._blocked = False
        self._transition_id = 0
        self._reset_id = 0

    def _clear_pending(self, reasons) -> None:
        if self._pending is not None:
            reasons.append(R.CANDIDATE_CANCELLED)
        self._pending = None
        self._since = None

    def _neutralize(self, reasons) -> None:
        self._clear_pending(reasons)
        if self._stable is not HandPose.UNKNOWN:
            self._stable = HandPose.UNKNOWN
            self._transition_id += 1
            reasons.append(R.SAFE_RELEASE)
        self._armed = False
        self._rearm_since = None

    def _reset(self, reasons) -> None:
        self._neutralize(reasons)
        self._reset_id += 1

    def _state(self, candidate, reasons, source=(), *, allowed=False, reset=False):
        return StablePoseState(
            self._run, self._frame, self._time, candidate, self._stable,
            self._pending, self._since, self._rearm_since, self._armed,
            allowed, self._stable is HandPose.PINCH,
            self._transition_id, self._reset_id, reset, tuple(reasons), source,
        )

    def reset(self) -> StablePoseState:
        """Immediate neutral snapshot; next update is initialization-neutral.

        Diagnostic counters never rewind. No pending dwell crosses this reset.
        """
        reasons = [R.EXPLICIT_RESET]
        self._reset(reasons)
        self._run = self._frame = self._time = None
        self._blocked = False
        return self._state(HandPose.UNKNOWN, reasons, reset=True)

    @staticmethod
    def _valid_observation(observation):
        fingers = observation.fingers
        p = observation.pinch
        if (observation.geometry_reasons or len(fingers) != 5
                or {f.finger for f in fingers} != set(Finger)
                or any(f.state is FingerState.UNKNOWN or f.geometry_reasons for f in fingers)
                or p.distance_palm is None or not math.isfinite(p.distance_palm)
                or p.distance_palm < 0
                or any(type(v) is not bool for v in (p.enter, p.exit, p.boundary_band))
                or sum((p.enter, p.exit, p.boundary_band)) != 1):
            return False
        if observation.pose is HandPose.PINCH:
            return p.enter and not observation.reasons
        if observation.pose is not HandPose.UNKNOWN:
            return p.exit and not observation.reasons
        return True

    def update(
        self, observation: PoseObservation, *, tracking_status: TrackingStatus,
        filter_reset: bool = False,
    ) -> StablePoseState:
        geometry = observation.frame_geometry
        timestamp = geometry.timestamp_s
        time_valid = type(timestamp) in (int, float) and math.isfinite(timestamp)
        reasons = []
        if self._run is None:
            reasons.append(R.INITIALIZATION)
        elif geometry.run_id != self._run:
            reasons.append(R.RUN_CHANGE)
        else:
            if not time_valid or self._time is None or timestamp <= self._time:
                reasons.append(R.TIMESTAMP_DISCONTINUITY)
            elif timestamp - self._time > self.config.reset_gap_s:
                reasons.append(R.TIMESTAMP_GAP)
            if self._frame is not None and geometry.frame_id <= self._frame:
                reasons.append(R.FRAME_DISCONTINUITY)
        if not time_valid and R.TIMESTAMP_DISCONTINUITY not in reasons:
            reasons.append(R.TIMESTAMP_DISCONTINUITY)
        if filter_reset:
            reasons.append(R.FILTER_RESET)
        if tracking_status is TrackingStatus.REACQUIRED:
            reasons.append(R.REACQUISITION)
        lost = (not isinstance(tracking_status, TrackingStatus)
                or tracking_status not in (TrackingStatus.VALID, TrackingStatus.REACQUIRED))
        valid = self._valid_observation(observation)
        if self._blocked and not lost and valid and R.REACQUISITION not in reasons:
            # Short Core losses may resume with VALID rather than REACQUIRED.
            # The first usable return must still be initialization-neutral.
            reasons.append(R.REACQUISITION)
        if lost and not self._blocked:
            reasons.append(R.TRACKING_LOSS)
        elif not valid and not self._blocked:
            reasons.append(R.INVALID_OBSERVATION)
        self._run, self._frame = geometry.run_id, geometry.frame_id
        self._time = timestamp if time_valid else None
        if reasons:
            self._reset(reasons)
            self._blocked = lost or not valid
            return self._state(observation.pose, reasons, observation.reasons, reset=True)
        if lost or not valid:
            # Repeated unusable frames do not spam reset/transition identities.
            self._neutralize(reasons)
            self._blocked = True
            return self._state(observation.pose, reasons, observation.reasons)
        self._blocked = False
        band_only = (observation.pose is HandPose.UNKNOWN
                     and observation.reasons == (ClassificationReason.PINCH_BOUNDARY_BAND,)
                     and observation.pinch.boundary_band)
        if band_only and self._stable is HandPose.PINCH and self._armed:
            self._clear_pending(reasons)
            reasons.append(R.PINCH_BAND_HOLD)
            return self._state(observation.pose, reasons, observation.reasons)
        if observation.pose is HandPose.UNKNOWN:
            self._neutralize(reasons)
            reasons.append(R.UNKNOWN_INPUT)
            return self._state(observation.pose, reasons, observation.reasons)
        if not self._armed:
            released = observation.pose is not HandPose.PINCH and observation.pinch.exit
            if not released:
                self._rearm_since = None
                reasons.append(R.REARM_PENDING)
            else:
                if self._rearm_since is None:
                    self._rearm_since = timestamp
                if timestamp - self._rearm_since >= self.config.rearm_dwell_s:
                    self._armed = True
                    self._rearm_since = None
                    reasons.append(R.REARMED)
                else:
                    reasons.append(R.REARM_PENDING)
            # Even the frame completing rearm is neutral; pose dwell starts next.
            return self._state(observation.pose, reasons, observation.reasons)
        target = observation.pose
        if target is self._stable:
            self._clear_pending(reasons)
            return self._state(target, reasons, observation.reasons, allowed=True)
        if target is not self._pending:
            self._clear_pending(reasons)
            self._pending, self._since = target, timestamp
            reasons.append(R.CANDIDATE_STARTED)
        enter = (self.config.pinch_enter_dwell_s if target is HandPose.PINCH
                 else self.config.enter_dwell_s)
        exit_ = (self.config.pinch_exit_dwell_s if self._stable is HandPose.PINCH
                 else self.config.exit_dwell_s if self._stable is not HandPose.UNKNOWN
                 else 0.)
        if timestamp - self._since >= max(enter, exit_):
            self._stable = target
            self._pending = self._since = None
            self._transition_id += 1
            reasons.append(R.STABLE_TRANSITION)
            return self._state(target, reasons, observation.reasons, allowed=True)
        return self._state(target, reasons, observation.reasons)

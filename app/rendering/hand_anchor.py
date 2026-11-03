"""Timestamp-based presentation smoothing with wrapped angles and explicit loss."""

from dataclasses import replace
import math


class HandAnchor:
    def __init__(self, config):
        self.config = config
        self.reset()

    def reset(self):
        self.pose = self.last = None
        self.track = self.identity = self.hand_ids = None

    def observe(self, hands, identity, *, valid=True, allow_fingertips=False):
        """Acquire from OPEN, or an extended tip in LIVE, then follow that palm.

        Presentation continuity is independent of command qualification. A closed
        or pointing hand can still anchor. Navigation and LIVE geometry qualify
        commands independently; a navigation UNKNOWN is not a geometry pose.
        Loss/identity/time discontinuity never extrapolates a missing palm.
        """
        run, frame, timestamp = identity
        ids = tuple(sorted((h.role, h.track_id) for h in hands))
        old = self.identity
        if (
            not valid
            or not hands
            or not math.isfinite(timestamp)
            or old is not None
            and (
                run != old[0]
                or frame <= old[1]
                or not 0 < timestamp - old[2] <= self.config.max_gap_s
                or ids != self.hand_ids
            )
        ):
            self.reset()
        if not valid or not hands or not math.isfinite(timestamp):
            return None
        self.identity, self.hand_ids = identity, ids
        hand = next(
            (h for h in hands if (h.role, h.track_id) == self.track and h.valid), None
        )
        if hand is None:
            hand = next(
                (
                    h
                    for h in sorted(hands, key=lambda h: h.role == "DOMINANT")
                    if h.valid
                    and (
                        h.pose == "OPEN_PALM"
                        or allow_fingertips
                        and any(s.extended for s in h.tip_samples)
                    )
                ),
                None,
            )
            if hand is None:
                self.reset()
                return None
            self.track = hand.role, hand.track_id
        return self.update(hand.palm, timestamp)

    def update(self, pose, timestamp):
        if pose is None:
            self.reset()
            return None
        dt = None if self.last is None else timestamp - self.last
        if self.pose is None or dt is None or not 0 < dt <= self.config.max_gap_s:
            self.pose = pose
        else:
            alpha = 1 - math.exp(-dt / self.config.anchor_tau_s)
            old = self.pose
            angle = lambda a, b: a + alpha * math.atan2(
                math.sin(b - a), math.cos(b - a)
            )
            self.pose = replace(
                pose,
                center_xy=tuple(
                    a + alpha * (b - a) for a, b in zip(old.center_xy, pose.center_xy)
                ),
                span=old.span + alpha * (pose.span - old.span),
                roll_rad=angle(old.roll_rad, pose.roll_rad),
                pitch_rad=angle(old.pitch_rad, pose.pitch_rad),
                yaw_rad=angle(old.yaw_rad, pose.yaw_rad),
            )
        self.last = timestamp
        return self.pose

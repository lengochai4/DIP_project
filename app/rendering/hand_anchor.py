"""Timestamp-based presentation smoothing with wrapped angles and explicit loss."""

from dataclasses import replace
import math


class HandAnchor:
    def __init__(self, config):
        self.config = config
        self.pose = self.last = None

    def reset(self):
        self.pose = self.last = None

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

"""Calibrated relative closing with dwell, release/rearm and immediate neutral loss."""

from statistics import median
import math


class IntentionalPinch:
    def __init__(self, config):
        self.config = config
        self.reference = None
        self.signature = None
        self.cycle_id = 0
        self.last = None
        self.samples = None
        self.reset()

    def reset(self, *, clear_reference=False):
        if clear_reference:
            self.reference = None
            self.signature = None
        self.state = "UNKNOWN"
        self.active = False
        self.armed = False
        self.release_since = self.closing_since = self.enter_since = None
        self.release_closure = self.previous_closure = None
        self.last = None
        self.samples = None

    def calibrate(self):
        self.reset(clear_reference=True)
        self.samples = []

    def update(self, hand, timestamp, *, valid=True):
        c = self.config
        discontinuity = (
            not math.isfinite(timestamp)
            or self.last is not None
            and not 0 < timestamp - self.last <= c.max_gap_s
        )
        if not valid or hand is None or not hand.valid or discontinuity:
            self.reset()
            return self.state
        self.last = timestamp
        ratio = hand.pinch_ratio
        if self.samples is not None:
            self.samples.append((timestamp, ratio, hand.palm_signature))
            self.state = "CALIBRATING"
            if timestamp - self.samples[0][0] >= c.release_duration_s:
                values = [r for _, r, _ in self.samples]
                ref = median(values)
                mad = median(abs(r - ref) for r in values)
                self.reference = (
                    ref
                    if len(values) >= c.release_min_samples
                    and ref > c.palm_epsilon
                    and mad / ref <= c.release_max_mad
                    else None
                )
                signatures = [s for _, _, s in self.samples if s]
                self.signature = (
                    tuple(
                        median(s[i] for s in signatures)
                        for i in range(len(signatures[0]))
                    )
                    if signatures
                    else None
                )
                self.samples = None
                self.state = (
                    "REARM" if self.reference is not None else "NEEDS_CALIBRATION"
                )
            return self.state
        if self.reference is None:
            self.state = "NEEDS_CALIBRATION"
            return self.state
        if self.signature is not None and (
            len(hand.palm_signature) != len(self.signature)
            or max(abs(a - b) for a, b in zip(hand.palm_signature, self.signature))
            > c.reference_shape_delta
        ):
            self.reset(clear_reference=True)
            self.state = "NEEDS_CALIBRATION"
            return self.state
        closure = 1 - ratio / self.reference
        if closure <= c.pinch_exit:
            self.active = False
            self.closing_since = self.enter_since = None
            if self.release_since is None:
                self.release_since = timestamp
            self.armed = timestamp - self.release_since >= c.rearm_s
            self.state = "READY" if self.armed else "REARM"
            self.release_closure = closure
        elif self.active:
            self.state = "HOLD"
        elif self.armed:
            self.release_since = None
            if (
                self.release_closure is not None
                and closure - self.release_closure >= c.pinch_progress
            ):
                if self.closing_since is None:
                    self.closing_since = timestamp
                self.state = "CLOSING"
                if timestamp - self.closing_since > c.closing_timeout_s:
                    self.armed = False
                    self.state = "REARM"
                elif closure >= c.pinch_enter:
                    if self.enter_since is None:
                        self.enter_since = timestamp
                    if timestamp - self.enter_since >= c.pinch_dwell_s:
                        self.active = True
                        self.cycle_id += 1
                        self.state = "PINCH_ACTIVE"
                else:
                    self.enter_since = None
        else:
            self.state = "REARM"
        self.previous_closure = closure
        return self.state

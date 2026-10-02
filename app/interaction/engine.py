"""Four gestures, exclusive intent, explicit discontinuity/reacquisition neutralization."""

from dataclasses import replace
import math
from .contracts import GestureIntent as Intent, IntentType as Type, Phase, Owner
from .intentional_pinch import IntentionalPinch
from .router import IntentRouter
from .hand_geometry import distance


class IntentEngine:
    def __init__(self, config):
        self.config = config
        self.pinches = {
            role: IntentionalPinch(config) for role in ("DOMINANT", "SUPPORT")
        }
        self.router = IntentRouter()
        self.last = None
        self.reset()

    def reset(self, *, clear_reference=False):
        for p in self.pinches.values():
            p.reset(clear_reference=clear_reference)
        self.last = None
        self.active = None
        self.previous_pointer = None
        self.pose_since = {}
        self.measure = False
        self.pair_since = self.pair_preview = self.locked_pair = None
        self.scale_reference = None
        self.context = None
        self.hand_ids = None
        return self.router.reset()

    def update(
        self,
        hands,
        identity,
        *,
        settings,
        valid=True,
        context=(),
        ui=False,
        calibration=False,
        modal=False,
    ):
        run, frame, timestamp = identity
        old = self.last
        if modal:
            out = self.reset()
            self.last = identity
            return replace(out, owner=Owner.SYSTEM_MODAL, reason="SYSTEM_MODAL")
        ids = tuple(sorted((h.role, h.track_id) for h in hands))
        gap = (
            old is None
            or run != old[0]
            or frame <= old[1]
            or not 0 < timestamp - old[2] <= self.config.max_gap_s
        )
        changed = (
            self.context is not None
            and self.context != context
            or self.hand_ids is not None
            and self.hand_ids != ids
        )
        if gap or changed or not valid or not hands:
            out = self.reset(clear_reference=old is not None and run != old[0])
            self.last = identity
            self.context = context
            self.hand_ids = ids
            return replace(
                out,
                reason=(
                    "DISCONTINUITY_OR_LOSS"
                    if gap or not valid or not hands
                    else "CONTEXT_CHANGED"
                ),
            )
        self.last, self.context, self.hand_ids = identity, context, ids
        dominant = next((h for h in hands if h.role == "DOMINANT"), None)
        support = next((h for h in hands if h.role == "SUPPORT"), None)
        if dominant is None and support is not None and len(hands) == 1:
            if calibration:
                pinch = self.pinches["SUPPORT"]
                pinch.update(support, timestamp)
                return self.router.route(
                    Intent(
                        Type.POINT,
                        hand_role="SUPPORT",
                        pointer_xy=support.pointer_xy,
                        reason=pinch.state,
                    ),
                    calibration=True,
                    modal=modal,
                )
            # A support-only open palm can present, but cannot become dominant automatically.
            if support.pose == "OPEN_PALM":
                return self.router.route(
                    Intent(Type.ANCHOR, hand_role="SUPPORT", anchor_pose=support.palm),
                    ui=ui,
                    calibration=calibration,
                    modal=modal,
                )
            return self.router.reset("DOMINANT_UNAVAILABLE")
        if dominant is None:
            return self.router.reset("DOMINANT_UNAVAILABLE")
        for role, pinch in self.pinches.items():
            hand = dominant if role == "DOMINANT" else support
            pinch.update(hand, timestamp, valid=hand is not None and hand.valid)
        dp, sp = self.pinches["DOMINANT"], self.pinches["SUPPORT"]
        if calibration:
            return self.router.route(
                Intent(
                    Type.POINT,
                    pointer_xy=dominant.pointer_xy,
                    cycle_id=dp.cycle_id,
                    reason=dp.state,
                ),
                calibration=True,
                modal=modal,
            )
        # UNKNOWN observations revoke commands unless currently supported deliberate pinch
        # with the three other fingers folded (the baseline thumb/index clutch shape).
        qualified = dp.active and not any(dominant.fingers[2:])
        if dominant.pose == "UNKNOWN" and not qualified and dp.state != "CLOSING":
            dp.reset()
            self.active = self.previous_pointer = self.scale_reference = None
            self.locked_pair = self.pair_since = self.pair_preview = None
            return self.router.reset("UNKNOWN_POSE")
        pointer = self.pointer(dominant.pointer_xy, settings)
        delta = (
            (0.0, 0.0)
            if self.previous_pointer is None
            else tuple(a - b for a, b in zip(pointer, self.previous_pointer))
        )
        self.previous_pointer = pointer

        def emit(kind, phase=Phase.UPDATE, **kwargs):
            return self.router.route(
                Intent(kind, phase, pointer_xy=pointer, cycle_id=dp.cycle_id, **kwargs),
                ui=ui,
                calibration=calibration,
                modal=modal,
                tool=self.measure,
            )

        if self.active is not None and (
            not dp.active
            or self.active == "SCALE"
            and (support is None or not sp.active)
        ):
            was_scale = self.active == "SCALE"
            self.active = self.scale_reference = None
            if was_scale:
                dp.reset()
                sp.reset()
            return emit(Type.RELEASE, Phase.END)
        if ui or calibration or modal:
            if dp.active:
                if self.active is None:
                    self.active = "SELECT"
                    return emit(Type.SELECT, Phase.BEGIN)
                return emit(Type.POINT)
            return emit(Type.POINT)
        if (
            dp.active
            and sp.active
            and support is not None
            and not any(support.fingers[2:])
        ):
            separation = distance(dominant.palm.center_xy, support.palm.center_xy)
            if separation <= self.config.palm_epsilon:
                return self.router.reset("DEGENERATE_PAIR")
            if self.active != "SCALE":
                self.active = "SCALE"
                self.scale_reference = separation
                return emit(Type.SCALE, Phase.BEGIN, scale_factor=1.0)
            return emit(Type.SCALE, scale_factor=separation / self.scale_reference)
        if (
            not dp.active
            and dominant.pose == "POINT"
            and support is not None
            and support.pose == "POINT"
        ):
            pair = (support.pointer_xy, dominant.pointer_xy)
            if (
                self.pair_preview is None
                or max(distance(a, b) for a, b in zip(pair, self.pair_preview))
                > self.config.measure_motion
            ):
                self.pair_since = timestamp
                self.locked_pair = None
            self.pair_preview = pair
            if timestamp - self.pair_since >= self.config.measure_dwell_s:
                self.locked_pair = pair
                self.measure = True
            pair = tuple(self.pointer(p, settings) for p in pair)
            return emit(
                Type.MEASURE_UPDATE,
                points=tuple((p[0], p[1], 0.0) for p in pair),
                reason="LOCKED" if self.locked_pair else "PREVIEW",
            )
        if support is None or support.pose != "POINT":
            self.locked_pair = self.pair_since = self.pair_preview = None
        if dp.active:
            if self.active is None:
                self.active = "COMMIT" if self.measure else "GRAB"
                if self.measure:
                    pair = self.locked_pair
                    if pair:
                        pair = tuple(self.pointer(p, settings) for p in pair)
                    return emit(
                        Type.MEASURE_COMMIT,
                        Phase.BEGIN,
                        points=tuple((*p, 0.0) for p in pair) if pair else (),
                    )
                return emit(
                    Type.GRAB,
                    Phase.BEGIN,
                    anchor_pose=(
                        support.palm
                        if support and support.pose == "OPEN_PALM"
                        else None
                    ),
                )
            if self.active == "GRAB":
                gain = self.config.motion_gain * settings.manipulation_sensitivity
                bounded = tuple(
                    max(-self.config.max_delta, min(self.config.max_delta, v * gain))
                    for v in delta
                )
                return emit(
                    Type.DRAG,
                    delta_xy=bounded,
                    anchor_pose=(
                        support.palm
                        if support and support.pose == "OPEN_PALM"
                        else None
                    ),
                )
            return emit(Type.POINT)
        if dominant.pose == "V_SIGN":
            since = self.pose_since.setdefault("V_SIGN", timestamp)
            if not self.measure and timestamp - since >= self.config.pose_dwell_s:
                self.measure = True
                return emit(Type.MEASURE_BEGIN, Phase.BEGIN)
        else:
            self.pose_since.pop("V_SIGN", None)
        anchor = (
            support
            if support and support.pose == "OPEN_PALM"
            else dominant if dominant.pose == "OPEN_PALM" else None
        )
        if (
            dominant.pose == "POINT"
            and support is not None
            and support.pose == "OPEN_PALM"
        ):
            return emit(
                Type.MEASURE_UPDATE if self.measure else Type.POINT,
                anchor_pose=support.palm,
            )
        if anchor is not None:
            return emit(Type.ANCHOR, hand_role=anchor.role, anchor_pose=anchor.palm)
        if dominant.pose == "POINT":
            return emit(
                Type.MEASURE_UPDATE if self.measure else Type.POINT,
                anchor_pose=(
                    support.palm if support and support.pose == "OPEN_PALM" else None
                ),
            )
        return self.router.reset("NEUTRAL")

    def pointer(self, xy, settings):
        """One mirror/gain/clamp mapping for both hands, UI and scene pointers."""
        if settings.mirror:
            xy = (1 - xy[0], xy[1])
        gain = settings.pointer_sensitivity * self.config.pointer_gain
        return tuple(min(1.0, max(0.0, 0.5 + (v - 0.5) * gain)) for v in xy)

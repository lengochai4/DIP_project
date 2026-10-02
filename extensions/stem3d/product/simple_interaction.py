"""Practical finger-count controls, independent of experimental contact/pinch.

This is an application semantic, not an A3 pose/research modification. A thumb
need not be stretched to navigate. Four known extended non-thumb fingers form
an open palm; an extended index and three flexed fingers form a point. Neither
ambiguous fingers nor stale geometry authorize commands.
"""

from dataclasses import dataclass
from dip_touchless.core import InteractionState, TrackingStatus
from ..full_hand.contracts import Finger
from ..full_hand.pose_contracts import FingerState
from ..ui.layout import map_normalized_point_to_rect
from .interaction import neutral, response, CommandDiagnostics


def practical_pose(observation):
    if observation is None:
        return "UNKNOWN"
    states = {f.finger: f.state for f in observation.fingers}
    others = (Finger.MIDDLE, Finger.RING, Finger.PINKY)
    if all(states.get(f) is FingerState.EXTENDED for f in (Finger.INDEX, *others)):
        return "OPEN"
    if states.get(Finger.INDEX) is FingerState.EXTENDED and all(
        states.get(f) is FingerState.FLEXED for f in others
    ):
        return "POINT"
    return "UNKNOWN"


@dataclass(frozen=True, slots=True)
class SimpleFeedback:
    candidate: str = "UNKNOWN"
    stable: str = "UNKNOWN"
    open_panel: bool = False
    hover_target: str | None = None
    hover_progress: float = 0.
    select: bool = False
    navigation_armed: bool = False


class SimpleHandControls:
    pose_dwell_s = .25
    menu_dwell_s = .8
    select_dwell_s = 1.2

    def __init__(self, profile):
        self.profile = profile
        self._last = self._context = None
        self._resets = 0
        self._fired = None
        self._menu_inhibited = False
        self.reset()

    def reset(self):
        self._candidate = "UNKNOWN"
        self._since = self._anchor = self._hover = self._hover_since = None
        self._menu_latched = False
        self._fired = None
        self._menu_inhibited = False
        self._ui_origin = None
        self._navigation_armed = False
        self.feedback = SimpleFeedback()
        self._resets += 1
        self.diagnostics = CommandDiagnostics("SIMPLE", "NEUTRAL", self._resets, (0., 0.))

    def update(self, frame, full, *, settings, sensitivity=1., focus="SCENE", context=(), panel=None):
        identity = (frame.run_id, frame.frame_id, frame.timestamp_s)
        old = self._last
        bad_time = old is not None and (identity[0] != old[0] or identity[1] <= old[1]
            or not 0 < identity[2]-old[2] <= self.profile.max_gap_s)
        if old is None or identity[0] != old[0] or identity[1] > old[1] and identity[2] > old[2]:
            self._last = identity
        key = (settings, focus, context)
        if key != self._context:
            # A scene/UI/settings change cancels anchors/dwell. A clicked target
            # remains latched until the hand actually leaves it: no auto-repeat.
            fired, inhibited = self._fired, self._menu_inhibited
            self.reset()
            self._fired, self._menu_inhibited = fired, inhibited
            self._context = key
        usable = (not bad_time and frame.status is TrackingStatus.VALID
                  and not frame.filter_diagnostics.reset_occurred and full is not None
                  and full.analysis_valid and full.hand is not None and full.hand.valid
                  and (full.frame_geometry.run_id, full.frame_geometry.frame_id,
                       full.frame_geometry.timestamp_s) == identity)
        candidate = practical_pose(full.pose) if usable else "UNKNOWN"
        if candidate == "UNKNOWN":
            self.reset()
            self._fired = None
            self._menu_inhibited = False
            return neutral(frame)
        t = frame.timestamp_s
        if candidate == "POINT":
            self._menu_inhibited = False
            self._fired = None
        if candidate != self._candidate:
            self._candidate, self._since = candidate, t
            self._anchor = self._hover = self._hover_since = None
            self._menu_latched = False
        stable = candidate if t-self._since >= self.pose_dwell_s else "UNKNOWN"
        self.feedback = SimpleFeedback(candidate, stable)
        if stable == "UNKNOWN":
            return neutral(frame)
        tip = next((p for p in frame.filtered_landmarks if p.index == 8), None)
        if tip is None:
            self.reset()
            return neutral(frame)
        anchor = full.hand.palm.anchor_xy if stable == "OPEN" else (tip.x, tip.y)
        pointer = tuple(min(1., max(0., (v-.15)/.70)) for v in anchor)
        if settings.mirror:
            pointer = (1.-pointer[0], pointer[1])
        rotation, raw = (0., 0.), (0., 0.)
        select = False
        request = False
        target, progress = None, 0.
        if focus == "UI" and stable == "OPEN" and panel is not None:
            if self._ui_origin is None:
                self._ui_origin = pointer
            if not self._navigation_armed:
                import math
                self._navigation_armed = math.dist(pointer,self._ui_origin) >= .04
            target = panel.hit_test(map_normalized_point_to_rect(pointer, panel.viewport,
                                                                mirror_x=False, mirror_y=False))
            if target != self._hover:
                self._hover, self._hover_since = target, t
            if target != self._fired:
                self._fired = None
            if not self._navigation_armed:
                self._hover_since = t
            elif target is not None and target != self._fired:
                progress = min(1., (t-self._hover_since)/self.select_dwell_s)
                if progress >= 1.:
                    select, self._fired = True, target
            self._anchor = None
        elif focus == "SCENE" and stable == "OPEN":
            if not self._menu_inhibited and not self._menu_latched and t-self._since >= self.menu_dwell_s:
                request = self._menu_latched = True
                self._menu_inhibited = True
            self._anchor = None
        elif focus == "SCENE" and stable == "POINT":
            self._fired = None
            if self._anchor is not None:
                aspect = full.frame_geometry.width/full.frame_geometry.height
                raw = ((anchor[0]-self._anchor[0])*aspect, anchor[1]-self._anchor[1])
                rotation = (
                    response(raw[0]*(-1 if settings.mirror else 1), self.profile.rotation_deadzone,
                             self.profile.rotation_gain*sensitivity, self.profile.rotation_max_delta),
                    response(raw[1], self.profile.rotation_deadzone,
                             self.profile.rotation_gain*sensitivity, self.profile.rotation_max_delta))
            self._anchor = anchor
        self.feedback = SimpleFeedback(candidate, stable, request, target, progress, select,
                                       self._navigation_armed)
        self.diagnostics = CommandDiagnostics("SIMPLE", "HOVER_SELECT" if select else stable,
                                              self._resets, raw)
        # A UI-only pulse adapts selection to the existing router's click edge;
        # it does not assert physical PINCH and never reaches a scene command.
        return InteractionState(*identity, True, pointer, None, select if focus == "UI" else False,
                                rotation, 0.)

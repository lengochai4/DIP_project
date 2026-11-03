"""One exclusive owner per cycle. Higher-priority contexts cancel lower owners."""

from dataclasses import replace
from .contracts import GestureIntent, IntentType, Owner, Phase

PRIORITY = tuple(Owner)


class IntentRouter:
    def __init__(self):
        self.owner = None
        self.cycle = None

    def reset(self, reason="CONTEXT_CHANGED"):
        owner = self.owner or Owner.SCENE
        self.owner = self.cycle = None
        return GestureIntent(
            IntentType.CANCEL, Phase.CANCEL, validity=False, reason=reason, owner=owner
        )

    def route(self, intent, *, modal=False, calibration=False, ui=False, tool=False):
        requested = (
            Owner.SYSTEM_MODAL
            if modal
            else (
                Owner.CALIBRATION
                if calibration
                else Owner.UI if ui else Owner.TOOL if tool else Owner.SCENE
            )
        )
        if intent.type is IntentType.CANCEL:
            out = replace(intent, owner=self.owner or requested)
            self.owner = self.cycle = None
            return out
        if self.owner is not None:
            if PRIORITY.index(requested) < PRIORITY.index(self.owner):
                return self.reset("OWNER_PREEMPTED")
            requested = self.owner
        if intent.phase is Phase.BEGIN and intent.type in {
            IntentType.GRAB,
            IntentType.SELECT,
            IntentType.SCALE,
            IntentType.TOOL_COMMIT,
            IntentType.MEASURE_COMMIT,
        }:
            self.owner, self.cycle = requested, intent.cycle_id
        out = replace(intent, owner=requested)
        if intent.phase in {Phase.END, Phase.CANCEL}:
            self.owner = self.cycle = None
        return out

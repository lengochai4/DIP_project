"""Opt-in observation feedback in the existing Live Vision card."""

from ..ui.shell import ProductDashboard
from ..ui.theme import THEME
from .intent_session import IntentSessionSnapshot


class IntentObservationDashboard(ProductDashboard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._intent_snapshot = None

    def set_intent_snapshot(self, snapshot):
        if snapshot is not None and not isinstance(snapshot, IntentSessionSnapshot):
            raise TypeError("intent feedback must be immutable or unavailable")
        self._intent_snapshot = snapshot

    def _vision(self, canvas, rect, image, state):
        import cv2
        super()._vision(canvas, rect, image, state)
        preview_height = max(1, min(rect.height - 112, round((rect.width - 24) * image.shape[0] / image.shape[1])))
        top = rect.y + 44 + preview_height + 8
        cv2.rectangle(canvas, (rect.x+2, top), (rect.right-2, rect.bottom-2), THEME.surface, -1)
        snapshot = self._intent_snapshot
        current = snapshot is not None and (
            snapshot.frame_geometry.run_id, snapshot.frame_geometry.frame_id,
            snapshot.frame_geometry.timestamp_s) == (state.run_id, state.frame_id, state.timestamp_s)
        if not current:
            lines = ("Intent observation unavailable", "Legacy controls remain active", "K Calibrate / X Clear")
            active = False
        else:
            observed = snapshot.temporal
            value = snapshot.observation.relative_closure if snapshot.observation else None
            closure = "unavailable" if value is None else f"{value:.2f}"
            lines = (f"Intent: {observed.state.value} / cycle {observed.cycle_id}",
                     f"{snapshot.calibration_status} / closure {closure}",
                     "K Calibrate / X Clear / legacy active", snapshot.message)
            active = observed.active_evidence
        # Workspace has a shorter card than Analysis. Keep every text baseline
        # inside the card rather than letting a fourth line escape the border.
        max_lines = max(1, 1 + (rect.bottom - 10 - (top + 12)) // 18)
        if current and max_lines < 4 and snapshot.calibration_status != "READY":
            lines = (*lines[:2], snapshot.message)
        for i, line in enumerate(lines[:max_lines]):
            self._text(canvas, line, rect.x+12, top+12+i*18, scale=THEME.font_caption,
                       color=THEME.success if i == 0 and active else THEME.text_secondary,
                       width=rect.width-24)

    def close(self):
        self._intent_snapshot = None
        super().close()

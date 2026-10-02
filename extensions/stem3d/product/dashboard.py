"""Application settings, onboarding and immutable full-hand feedback."""

from dataclasses import replace
import cv2
import numpy as np
from ..full_hand.intent_presentation import IntentObservationDashboard
from ..ui.layout import Rect
from ..ui.shell import ShellSurface
from ..ui.shell import ProductDashboard
from ..ui.theme import THEME
from ..ui.presentation_model import ApplicationPhase, DashboardMode
from .settings import InputMode, save_settings


class ApplicationDashboard(IntentObservationDashboard):
    def __init__(self, *, preferences, preferences_path, **kwargs):
        super().__init__(**kwargs)
        self.preferences = preferences
        self.preferences_path = preferences_path
        self.settings_open = False
        self.full_snapshot = None
        self.command_diagnostics = None
        self.simple_feedback = None
        self.events = []
        self.manual = []
        self.feedback = "Point to rotate. Open palm for Control Space. Two open palms to scale."
        self.action_epoch = 0
        self.two_hand_feedback = "Two-hand capability disabled."
        self._background_template = None
        hook = getattr(self._host, "set_navigation_consumer", None)
        if callable(hook):
            hook(self.handle_navigation)

    def handle_navigation(self, kind, x, y, dx, dy):
        if self.blocked or self._spatial_panel_state.open or self._surface is None or self._surface.viewport is None:
            return
        if self._rect_contains(self._surface.viewport, x, y):
            self.manual.append((kind, dx, dy))
            self.action_epoch += 1

    @property
    def blocked(self):
        return (self.settings_open or self._help_open or self._provenance_open
                or (self.mode is DashboardMode.EVIDENCE and not self._spatial_panel_state.open
                    and self.preferences.mode is not InputMode.SIMPLE))

    def drain_events(self):
        events, self.events = tuple(self.events), []
        return events

    def drain_manual(self):
        commands, self.manual = tuple(self.manual), []
        return commands

    def _activate(self, key):
        self.action_epoch += 1
        if key == "settings":
            self.settings_open = not self.settings_open
            self._help_open = self._provenance_open = False
            return
        if key == "settings-close":
            self.settings_open = False
        elif key.startswith("input:"):
            self.preferences = replace(self.preferences, mode=InputMode(key.split(":")[1]))
            self.feedback = ("Point rotates / Open palm navigates / Two open palms scale. No pinch calibration needed."
                if self.preferences.mode is InputMode.SIMPLE else
                "Experimental pinch: calibrate with K. Physical acceptance pending."
                if self.preferences.mode is InputMode.FULL_HAND else "Legacy commands active; full-hand diagnostics only.")
        elif key.startswith("sensitivity:"):
            self.preferences = replace(self.preferences, sensitivity=key.split(":")[1])
            self.feedback = "Sensitivity affects full-hand and manual controls only."
        elif key == "mirror":
            self.preferences = replace(self.preferences, mirror=not self.preferences.mirror)
            self.feedback = "Preview mirrored; full-hand pointer/motion use the same orientation. Legacy is unchanged."
        elif key == "two-hand":
            self.preferences = replace(self.preferences, two_hand=not self.preferences.two_hand)
            self.feedback = "Experimental two-hand scale; open both hands to arm."
        elif key == "calibrate":
            self.events.append("CALIBRATE_RELEASE")
            self.feedback = "Hold thumb/index comfortably apart and steady for the release window."
            self.settings_open = False
        elif key == "clear-reference":
            self.events.append("RESET_REFERENCE")
            self.feedback = "Reference cleared. Legacy fallback available."
        elif key == "save-preferences":
            try:
                save_settings(self.preferences_path, self.preferences)
                self.feedback = "Preferences saved locally. Experimental pinch references are never saved."
            except (OSError, ValueError) as exc:
                self.feedback = f"Could not save preferences ({type(exc).__name__}); current session still usable."

    def handle_key(self, key):
        char = chr(key).lower() if 0 <= key <= 0x10ffff else ""
        running = self._last_application_state is not None and self._last_application_state.phase is ApplicationPhase.RUNNING
        if running and char in {",", "k", "x", "t", "u", "n"}:
            if char == ",":
                self._activate("settings")
            elif char in {"k", "x"}:
                self._activate("calibrate" if char == "k" else "clear-reference")
            else:
                self.events.append({"t": "INTEND_CLOSE", "u": "INTEND_OPEN", "n": "NON_INTENT"}[char])
            return
        if running and char in {"j", "l", "i", "o", "+", "=", "-"} and not self.blocked and not self._spatial_panel_state.open:
            self.manual.append(char)
            self.action_epoch += 1
            return
        if char in {"r", "p", "1", "2", "3", "h", "c", "d", "a", "e", "?", "/"}:
            self.action_epoch += 1
        # Settings is modal; exit/help remain accessible, scene shortcuts are paused.
        if self.settings_open and char not in {"q", "?", "/"}:
            return
        super().handle_key(key)

    def handle_pointer(self, x, y, clicked):
        hit = next((key for key, rect in self._targets.items() if self._rect_contains(rect, x, y)), None)
        if clicked and hit is not None:
            self.action_epoch += 1
            if hit in {"settings", "settings-close", "mirror", "two-hand", "calibrate", "clear-reference", "save-preferences"} or hit.startswith(("input:", "sensitivity:")):
                self._activate(hit)
                return
        super().handle_pointer(x, y, clicked)

    def _chrome(self, canvas, layout, app, state=None):
        super()._chrome(canvas, layout, app, state)
        self._button(canvas, "settings", "Settings", Rect(420, layout.footer.y+7, 110, 34),
                     enabled=app.phase is ApplicationPhase.RUNNING, selected=self.settings_open)
        if self.preferences.mode is InputMode.FULL_HAND and self.mode is not DashboardMode.EVIDENCE:
            cv2.rectangle(canvas, (layout.width-482, layout.footer.y+3),
                          (layout.width-2, layout.footer.bottom-2), THEME.background, -1)
            status = self._intent_snapshot.calibration_status if self._intent_snapshot else "NEEDS_CALIBRATION"
            text = self.two_hand_feedback if self.preferences.two_hand else f"Experimental full-hand / {status} / K calibrate"
            self._text(canvas, text, layout.width-480, layout.footer.y+29,
                       scale=THEME.font_caption, color=THEME.warning, width=460)
        elif self.preferences.mode is InputMode.SIMPLE:
            cv2.rectangle(canvas, (layout.width-482, layout.footer.y+3),
                          (layout.width-2, layout.footer.bottom-2), THEME.background, -1)
            self._text(canvas, "Point: rotate / Open palm: menu / Two palms: scale",
                       layout.width-480, layout.footer.y+29, scale=THEME.font_caption, width=460)

    def _vision(self, canvas, rect, image, state):
        # Mirror only presentation copies. Raw/frame coordinates in Core remain unchanged.
        display = image
        shown = state
        if self.preferences.mirror:
            display = cv2.flip(image, 1)
            transform = lambda points: tuple(replace(p, x=1.-p.x) for p in points)
            roi = state.roi
            if roi is not None:
                x, y, w, h = roi.bounds_xywh
                roi = replace(roi, bounds_xywh=(image.shape[1]-x-w, y, w, h))
            pointer = state.interaction.pointer_xy
            # Full-hand commands already provide mirrored UI coordinates; legacy does not.
            if pointer is not None and (self.command_diagnostics is None or self.command_diagnostics.owner == "LEGACY"):
                pointer = (1.-pointer[0], pointer[1])
            shown = replace(state, raw_landmarks=transform(state.raw_landmarks),
                            filtered_landmarks=transform(state.filtered_landmarks), roi=roi,
                            interaction=replace(state.interaction, pointer_xy=pointer))
        ProductDashboard._vision(self, canvas, rect, display, shown)
        snap = self._intent_snapshot
        preview_height = max(1, min(rect.height-112, round((rect.width-24)*image.shape[0]/image.shape[1])))
        top = rect.y+44+preview_height+8
        cv2.rectangle(canvas, (rect.x+2, top), (rect.right-2, rect.bottom-2), THEME.surface, -1)
        full = self.full_snapshot
        current = full is not None and (full.run_id, full.frame_id, full.timestamp_s) == (state.run_id, state.frame_id, state.timestamp_s)
        pose = full.temporal.stable_pose.value if current else "UNKNOWN"
        fingers = " / ".join(f.state.value[0] for f in full.pose.fingers) if current and full.pose else "unavailable"
        owner = self.command_diagnostics.owner if self.command_diagnostics else "LEGACY"
        candidate = full.pose.pose.value if current and full.pose else "UNKNOWN"
        first_line = f"{owner} / {candidate} -> {pose}" if self.mode is DashboardMode.ANALYSIS else f"{owner} / pose {pose}"
        first_line = f"{first_line} / T I M R P: {fingers}" if self.mode is DashboardMode.ANALYSIS else first_line
        self._text(canvas, first_line, rect.x+12, top+14,
                   scale=THEME.font_caption, width=rect.width-24)
        if self.preferences.mode is InputMode.SIMPLE:
            feedback = self.simple_feedback
            stable = feedback.stable if feedback else "UNKNOWN"
            self._text(canvas, f"Control: {stable} / no calibration", rect.x+12, top+32,
                       scale=THEME.font_caption, color=THEME.text_secondary, width=rect.width-24)
            self._text(canvas, self.two_hand_feedback if self.preferences.two_hand else
                       "Open palm, hold a button to select", rect.x+12, top+50,
                       scale=THEME.font_caption, color=THEME.text_secondary, width=rect.width-24)
            return
        state_text = snap.temporal.state.value if snap is not None else "UNKNOWN"
        status = snap.calibration_status if snap is not None else "NEEDS_CALIBRATION"
        closure = snap.observation.relative_closure if snap is not None and snap.observation is not None else None
        cycle = snap.temporal.cycle_id if snap is not None else 0
        closure_text = "unavailable" if closure is None else f"{closure:.2f}"
        self._text(canvas, f"Intent {state_text} / cycle {cycle} / closure {closure_text}", rect.x+12, top+32,
                   scale=THEME.font_caption, color=THEME.text_secondary, width=rect.width-24)
        self._text(canvas, f"{status} / K calibrate / X clear", rect.x+12, top+50,
                   scale=THEME.font_caption, color=THEME.text_secondary, width=rect.width-24)

    def _new_canvas(self, height, width):
        # Measured broadcast-fill hot path. One immutable current-size template;
        # every returned surface still owns its independent writable copy.
        template = self._background_template
        if template is None or template.shape != (height, width, 3):
            template = np.full((height,width,3), THEME.background, np.uint8)
            template.flags.writeable = False
            self._background_template = template
        return template.copy()

    def _drawer(self, canvas, panel):
        super()._drawer(canvas, panel)
        if self.preferences.mode is not InputMode.SIMPLE:
            return
        rect = panel.viewport
        for y, text in ((55, "Open palm / hover 1.2s to select"),
                        (257, "Point rotates / two open palms scale")):
            cv2.rectangle(canvas, (rect.x+12, rect.y+y-16),
                          (rect.right-12, rect.y+y+4), THEME.surface_overlay, -1)
            self._text(canvas, text, rect.x+16, rect.y+y, scale=THEME.font_caption,
                       color=THEME.text_secondary, width=rect.width-32)
        feedback = self.simple_feedback
        if feedback is not None and not feedback.navigation_armed:
            self._text(canvas,"Move palm to begin selection",rect.x+16,rect.bottom-100,
                       scale=THEME.font_caption,color=THEME.accent,width=rect.width-32)
        if feedback is not None and feedback.hover_target is not None:
            button = next((b for b in panel.buttons if b.button_id == feedback.hover_target), None)
            if button is not None:
                width = round(button.rect.width*feedback.hover_progress)
                if width > 0:
                    cv2.rectangle(canvas, (button.rect.x, button.rect.bottom-4),
                                  (button.rect.x+width-1, button.rect.bottom-1), THEME.accent, -1)

    def _help(self, canvas, bounds):
        rect = Rect(bounds.x+16, bounds.y+12, max(1, bounds.width-32), max(1, bounds.height-24))
        self._box(canvas, rect, fill=THEME.surface_raised, border=THEME.border)
        self._button(canvas, "help", "Close", Rect(rect.right-112, rect.y+12, 92, 30))
        lines = (
            "DIP Touchless STEM / Application walkthrough",
            "Workspace: choose Coordinate Geometry, Molecule or Orbital. Analysis explains the DIP pipeline.",
            "Evidence is the frozen G7 record, separate from v1.1 diagnostics.",
            "Legacy: index motion rotates; pinch scales. P opens Control Space; release then pinch selects.",
            "Simple controls (default): extend only the index finger, then move it to rotate the scene.",
            "Open one palm and hold briefly to open Control Space. Move the palm cursor onto a button.",
            "Hold over a button for 1.2 seconds to select. Move away before selecting the same button again.",
            "Open two palms and hold briefly; move them apart/together to enlarge/shrink the scene.",
            "Close Control Space to scale/rotate. Gestures never manipulate the scene while the menu is open.",
            "Settings (,): Simple / Legacy / Observe / experimental Pinch. FIST has no action.",
            "Optional experimental PINCH: K confirms apart calibration; close intentionally to select/scale.",
            "Unknown or lost tracking cancels commands immediately. Returning poses require fresh dwell.",
            "If calibration fails: improve light, keep the palm visible and steady, press K to retry. X clears.",
            "Sensitivity is application-only. Mirror changes presentation/full-hand mapping, never research parameters.",
            "Legacy remains available: index motion rotates; pinch scales. Simple controls need no calibration.",
            "Fallback: J/L and I/O rotate; +/- scale; R reset. Right-drag rotates; wheel scales in the scene.",
            "1/2/3 scenes; D/A/E views; P Control Space; ? help; Q/ESC exit. Mouse selects all controls.",
            "Physical v1.1 acceptance is pending. RGB x/y does not measure depth or physical skin contact.",
        )
        step = min(35, max(18, (rect.height-75)//len(lines)))
        for i, line in enumerate(lines):
            self._text(canvas, line, rect.x+20, rect.y+32+i*step,
                       scale=THEME.font_section if i == 0 else THEME.font_caption,
                       width=rect.width-150 if i == 0 else rect.width-40)
        return rect

    def build_surface(self, image, state, application, **kwargs):
        surface = super().build_surface(image, state, application, **kwargs)
        if not self.settings_open or application.phase is not ApplicationPhase.RUNNING:
            return surface
        canvas, bounds = surface.canvas, surface.layout.content
        width = min(820, bounds.width-24)
        height = min(590, bounds.height-16)
        rect = Rect(bounds.x+(bounds.width-width)//2, bounds.y+(bounds.height-height)//2, width, height)
        self._targets.clear()
        self._box(canvas, rect, fill=THEME.surface_raised, border=THEME.border)
        self._text(canvas, "Controls & Preferences", rect.x+20, rect.y+32, scale=THEME.font_view)
        self._text(canvas, "Experimental v1.1 / physical acceptance pending", rect.x+20, rect.y+58,
                   scale=THEME.font_caption, color=THEME.warning, width=width-40)
        x, w = rect.x+20, (width-48)//3
        row = lambda offset: rect.y+round(offset*(height/590))
        mode_width = (width-52)//len(InputMode)
        for i, mode in enumerate(InputMode):
            label = {InputMode.SIMPLE: "Simple", InputMode.FULL_HAND: "Pinch (lab)"}.get(mode, mode.value.title())
            self._button(canvas, f"input:{mode.value}", label, Rect(x+i*(mode_width+4), row(82), mode_width, 34),
                         selected=self.preferences.mode is mode)
        self._text(canvas, "Sensitivity (full-hand / keyboard only)", x, row(148), scale=THEME.font_caption)
        for i, name in enumerate(("gentle", "standard", "responsive")):
            self._button(canvas, f"sensitivity:{name}", name.title(), Rect(x+i*(w+4), row(162), w, 34),
                         selected=self.preferences.sensitivity == name)
        for i, (key, text) in enumerate((("mirror", "Mirror preview"), ("two-hand", "Two-hand scale / experimental"))):
            self._button(canvas, key, text, Rect(x, row(224+i*44), width-40, 34),
                         selected=self.preferences.mirror if key == "mirror" else self.preferences.two_hand)
        self._text(canvas, "Optional pinch experiment only: comfortable apart release reference", x, row(326),
                   scale=THEME.font_caption, width=width-40)
        for i, (key, label) in enumerate((("calibrate", "Confirm apart & calibrate (K)"), ("clear-reference", "Clear reference (X)"))):
            self._button(canvas, key, label, Rect(x+i*((width-44)//2+4), row(344), (width-44)//2, 36))
        self._paragraph(canvas, self.feedback, Rect(x, row(408), width-40, 64), max_lines=3)
        self._text(canvas, "Simple gestures need no enrollment. Experimental references are session-only.", x, row(494),
                   scale=THEME.font_caption, color=THEME.text_secondary, width=width-40)
        for i, (key, label) in enumerate((("save-preferences", "Save local preferences"), ("settings-close", "Done"))):
            self._button(canvas, key, label, Rect(x+i*((width-44)//2+4), rect.bottom-48, (width-44)//2, 34))
        self._surface = ShellSurface(canvas, surface.layout, surface.viewport, (*surface.overlays, rect))
        return self._surface

    def close(self):
        self._background_template = None
        self.full_snapshot = self.command_diagnostics = None
        self.simple_feedback = None
        self.events.clear()
        self.manual.clear()
        super().close()

"""Product composition over the existing dashboard and controller seams."""

from dataclasses import dataclass
from functools import lru_cache
from time import monotonic
from types import SimpleNamespace

import cv2
import numpy as np

from ..application import RendererFailure
from ..scenes.molecule import MOLECULE_PRESETS
from .dashboard import LiveDashboard, _tracking_label, _tracking_badge_color
from .icons import draw_icon
from .layout import Rect, fit_aspect_rect
from .presentation_model import ApplicationPhase, DashboardMode
from .shell_layout import calculate_shell_layout, ShellLayout
from .spatial_panel import PanelButton, SpatialPanelLayout
from .shortcuts import HELP_LINES
from .theme import THEME


MODE_LABELS = {DashboardMode.DEMO: "Workspace", DashboardMode.ANALYSIS: "Analysis",
               DashboardMode.EVIDENCE: "Evidence"}
SCENE_LABELS = {"coordinate-geometry": "Coordinate Geometry",
                "molecule": "Molecule", "orbital-system": "Orbital"}
SCENE_DESCRIPTIONS = {
    "coordinate-geometry": "Explore axes, spatial orientation and transformations.",
    "molecule": "Explore molecular structure and bond geometry.",
    "orbital-system": "Simplified elliptical orbit / educational model.",
}
EVIDENCE_PAGE_ORDER = (0, 3, 4, 1, 2, 5)


@dataclass(frozen=True, slots=True)
class ShellSurface:
    canvas: np.ndarray
    layout: ShellLayout
    viewport: Rect | None
    overlays: tuple[Rect, ...]


def build_drawer_layout(width, height, *, active_scene_id=None,
                        mode=DashboardMode.DEMO, interaction_available=True):
    rect = calculate_shell_layout(width, height, mode).drawer
    x, w = rect.x + THEME.spacing_md, rect.width - 2 * THEME.spacing_md
    buttons = []
    for index, (scene_id, label) in enumerate(SCENE_LABELS.items()):
        buttons.append(PanelButton(f"scene:{scene_id}", label,
                       Rect(x, rect.y+82+index*42, w, 36),
                       interaction_available, scene_id == active_scene_id))
    for index, (value, label) in enumerate(MODE_LABELS.items()):
        buttons.append(PanelButton(f"mode:{value.value}", label,
                       Rect(x+index*(w//3), rect.y+298, w//3-4, 32),
                       interaction_available, value is mode))
    for index, (action, label) in enumerate((("reset", "Reset Scene"),
                                             ("close", "Close"))):
        buttons.append(PanelButton(action, label,
                       Rect(x+index*(w//2+4), rect.bottom-52, w//2-4, 34),
                       interaction_available))
    return SpatialPanelLayout(rect, tuple(buttons))


class ProductDashboard(LiveDashboard):
    """The same dashboard state/actions, presented by a single window host.

    The OpenCV window remains only a recoverable error fallback when a GL
    context cannot initialize. No duplicate mode or scene-selection state.
    """

    def __init__(self, *, window_host, **kwargs):
        super().__init__(**kwargs)
        self._host = window_host
        self._fallback = False
        self._start_requested = False
        self._help_open = False
        self._provenance_open = False
        self._targets: dict[str, Rect] = {}
        self._hover = None
        self._hover_at = monotonic()
        self._pressed = None
        self._pressed_at = 0.0
        self._surface: ShellSurface | None = None
        self._scaled_evidence = {}
        self._host.set_pointer_consumer(self.handle_pointer)
        self._host.set_key_consumer(lambda char: self.handle_key(ord(char)))

    @property
    def last_surface(self):
        return self._surface

    def open(self):
        if self._window_open:
            return
        try:
            self._host.open()
            self._window_open = True
        except Exception as exc:
            self._fallback = True
            try:
                super().open()
            except Exception:
                pass
            raise RendererFailure(f"3D renderer initialization failed: {exc}") from exc

    def _window_size(self):
        if self._fallback:
            return super()._window_size()
        return self._host.window_size

    def _present(self, surface):
        try:
            self._host.present_shell(surface.canvas, surface.viewport, surface.overlays)
        except Exception as exc:
            # A failed GL context cannot display its own recovery screen.
            # Release it before opening the existing emergency error view.
            self._fallback = True
            self._window_open = False
            try:
                self._host.close()
            except Exception:
                pass
            raise RendererFailure(f"Application renderer failed: {exc}") from exc

    def consume(self, image, presentation, application):
        self._present(self.build_surface(image, presentation, application))

    def build_dashboard(self, image, presentation, application, **kwargs):
        return self.build_surface(image, presentation, application, **kwargs).canvas

    def wait_for_start(self, application):
        self.open()
        while not self._stop and not self._start_requested:
            self.show_application_state(application)
            self.stop_requested()
        return self._start_requested and not self._stop

    def show_application_state(self, application):
        self._last_application_state = application
        if application.phase is ApplicationPhase.RUNNING:
            return True
        if application.phase is not ApplicationPhase.READY:
            self._help_open = self._provenance_open = False
        self._hover = self._pressed = None
        if self._fallback:
            if not self._window_open:
                super().open()
            return super().show_application_state(application)
        # STOPPED is never allowed to reopen a context during cleanup.
        if not self._host.opened:
            return False
        canvas = self.build_application_state_screen(application)
        self._host.present_shell(canvas)
        return True

    def wait_for_failure_dismiss(self, application):
        if self._fallback:
            return super().wait_for_failure_dismiss(application)
        while not self._stop:
            try:
                if not self.show_application_state(application):
                    break
                self.stop_requested()
            except Exception:
                break

    def stop_requested(self):
        if self._fallback:
            return super().stop_requested()
        if self._host.opened and self._host.close_requested():
            self._stop = True
        return self._stop

    def close(self):
        try:
            self._host.close()
        finally:
            if self._fallback:
                super().close()
            self._window_open = False
            self._surface = None
            self._targets.clear()
            self._scaled_evidence.clear()

    def _molecule_scene_active(self):
        return self._spatial_panel_state.active_scene_id == "molecule"

    def handle_key(self, key):
        if key in {ord("?"), ord("/")}:
            self._toggle_help()
            self._hover = self._pressed = None
            return
        if (key in {ord("s"), ord("S"), 13, 32}
                and self._last_application_state is not None
                and self._last_application_state.phase is ApplicationPhase.READY):
            self._start_requested = True
            return
        super().handle_key(key)

    def handle_pointer(self, x, y, clicked):
        hit = next((key for key, rect in self._targets.items()
                    if self._rect_contains(rect, x, y)), None)
        if hit != self._hover:
            self._hover, self._hover_at = hit, monotonic()
        if not clicked or hit is None:
            return
        self._pressed, self._pressed_at = hit, monotonic()
        if hit == "help":
            self._toggle_help()
        elif hit == "provenance":
            self._provenance_open = not self._provenance_open
        elif hit == "details":
            self._help_open = False
            self._provenance_open = True
        elif hit == "start":
            self._start_requested = True
        elif self._controls_active():
            if hit.startswith("scene:") and self._scene_select_action:
                self._scene_select_action(hit.split(":", 1)[1])
            elif hit.startswith("mode:"):
                self.set_mode(DashboardMode(hit.split(":", 1)[1]))
            elif hit.startswith("preset:") and self._molecule_preset_action:
                self._molecule_preset_action(hit.split(":", 1)[1])
            elif hit in {"panel", "close"} and self._control_panel_toggle_action:
                self._control_panel_toggle_action()
            elif hit == "reset" and self._reset_action:
                self._reset_action()
            elif hit in {"previous", "next"}:
                self._change_evidence_page(-1 if hit == "previous" else 1)
            elif hit.startswith("page:"):
                self._evidence_page_index=int(hit.split(":", 1)[1])

    def _change_evidence_page(self, direction):
        position=EVIDENCE_PAGE_ORDER.index(self._evidence_page_index)
        position=max(0,min(len(EVIDENCE_PAGE_ORDER)-1,position+direction))
        self._evidence_page_index=EVIDENCE_PAGE_ORDER[position]

    def _toggle_help(self):
        self._help_open = not self._help_open
        if self._help_open and self._spatial_panel_state.open:
            if self._control_panel_toggle_action is not None:
                self._control_panel_toggle_action()

    def spatial_panel_layout(self):
        return build_drawer_layout(*self._window_size(),
            active_scene_id=self._spatial_panel_state.active_scene_id,
            mode=self.mode,
            interaction_available=self._spatial_panel_state.interaction_available)

    def build_surface(self, image, state, application, *, width=None, height=None):
        self._last_application_state = application
        w, h = self._window_size()
        layout = calculate_shell_layout(w if width is None else width,
                                        h if height is None else height, self.mode)
        canvas = self._new_canvas(layout.height, layout.width)
        self._targets = {}
        self._chrome(canvas, layout, application, state)
        viewport = None
        if self.mode is DashboardMode.EVIDENCE:
            self._evidence(canvas, layout.content)
        else:
            viewport = self._stem(canvas, layout.stem, application)
            self._vision(canvas, layout.vision, image, state)
            if self.mode is DashboardMode.ANALYSIS:
                self._pipeline(canvas, layout.pipeline, state)
                self._diagnostics(canvas, layout.diagnostics, state, application)
        overlays = []
        if self._spatial_panel_state.open:
            panel = build_drawer_layout(layout.width, layout.height,
                active_scene_id=self._spatial_panel_state.active_scene_id,
                mode=self.mode,
                interaction_available=self._spatial_panel_state.interaction_available)
            self._targets = {key: rect for key, rect in self._targets.items()
                             if rect.right <= panel.viewport.x
                             or rect.bottom <= panel.viewport.y
                             or rect.y >= panel.viewport.bottom}
            self._drawer(canvas, panel)
            overlays.append(panel.viewport)
        if self._help_open:
            self._targets.clear()
            overlays.append(self._help(canvas, layout.content))
        if self._provenance_open:
            self._targets.clear()
            details = self._provenance if self.mode is DashboardMode.EVIDENCE else self._runtime_details
            overlays.append(details(canvas, layout.content, application))
        self._surface = ShellSurface(canvas, layout, viewport, tuple(overlays))
        return self._surface

    def _new_canvas(self, height, width):
        return np.full((height, width, 3), THEME.background, np.uint8)

    def _text(self, canvas, text, x, y, *, scale=None, color=None, width=None):
        self._put_text(canvas, text, x, y, scale=scale or THEME.font_body,
                       color=color or THEME.text_primary, max_width=width)

    @staticmethod
    @lru_cache(maxsize=2048)
    def _text_width(text, scale):
        return cv2.getTextSize(text, THEME.font_face, scale, THEME.font_weight)[0][0]

    @classmethod
    def _put_text(cls, image, text, x, y, *, scale=THEME.font_body,
                  color=THEME.text_primary, max_width=None, align="left"):
        if max_width is not None and cls._text_width(text, scale) > max_width:
            while text and cls._text_width(text + "...", scale) > max_width:
                text = text[:-1]
            text += "..."
        if align == "center":
            x -= cls._text_width(text, scale)//2
        elif align == "right":
            x -= cls._text_width(text, scale)
        cv2.putText(image, text, (x,y), THEME.font_face, scale, color,
                    THEME.font_weight, cv2.LINE_AA)

    def _box(self, canvas, rect, *, fill=None, border=None):
        r = THEME.radius_sm
        fill = THEME.surface if fill is None else fill
        cv2.rectangle(canvas, (rect.x+r,rect.y), (rect.right-r,rect.bottom-1),fill,-1)
        cv2.rectangle(canvas, (rect.x,rect.y+r),(rect.right-1,rect.bottom-r),fill,-1)
        for x in (rect.x+r, rect.right-r-1):
            for y in (rect.y+r,rect.bottom-r-1):
                cv2.circle(canvas,(x,y),r,fill,-1,cv2.LINE_AA)
        if border is not None:
            cv2.rectangle(canvas,(rect.x,rect.y),(rect.right-1,rect.bottom-1),
                          border,1,cv2.LINE_AA)

    def _button(self, canvas, key, label, rect, *, icon=None,
                selected=False, enabled=True):
        fill = THEME.accent_selected if selected else THEME.surface
        if enabled and self._hover == key:
            t = min(1.0, (monotonic()-self._hover_at)/THEME.hover_duration_s)
            fill = tuple(round(a+(b-a)*t) for a,b in zip(fill,THEME.control_hover))
        if enabled and self._pressed == key and monotonic()-self._pressed_at < THEME.press_duration_s:
            fill = THEME.control_pressed
        color = THEME.text_primary if enabled else THEME.disabled
        self._box(canvas,rect,fill=fill)
        if selected and enabled:
            cv2.line(canvas,(rect.x,rect.y+8),(rect.x,rect.bottom-8),THEME.accent,2)
        x = rect.x + THEME.spacing_sm
        if icon:
            draw_icon(canvas,icon,x,rect.y+(rect.height-THEME.icon_md)//2,
                      color=THEME.accent if selected else color)
            x += THEME.icon_md+THEME.spacing_sm
        lines = label.split("\n")
        for index, line in enumerate(lines):
            y = rect.y+rect.height//2+5+(index-(len(lines)-1)/2)*18
            self._text(canvas,line,x,round(y),scale=THEME.font_caption,
                        color=color,width=rect.right-x-8)
        if enabled:
            self._targets[key] = rect

    def _chrome(self, canvas, layout, app, state=None):
        self._text(canvas,"DIP Touchless STEM",16,35,scale=THEME.font_view)
        for index,(value,label) in enumerate(MODE_LABELS.items()):
            self._button(canvas,f"mode:{value.value}",label,
                         Rect(270+index*128,10,126,36),
                         icon={DashboardMode.DEMO:"workspace",DashboardMode.ANALYSIS:"analysis",
                               DashboardMode.EVIDENCE:"evidence"}[value],
                         selected=self.mode is value,
                         enabled=app.phase is ApplicationPhase.RUNNING)
        label = _tracking_label(state.tracking_status) if state else app.phase.value
        color = _tracking_badge_color(state.tracking_status) if state else (
            THEME.error if app.phase is ApplicationPhase.ERROR else THEME.text_muted)
        evidence = self.mode is DashboardMode.EVIDENCE and app.phase is ApplicationPhase.RUNNING
        if evidence:
            label, color = "FROZEN G7", THEME.accent
        draw_icon(canvas,"error" if app.phase is ApplicationPhase.ERROR else
                  "evidence" if evidence else "tracking",
                  layout.width-194,19,color=color)
        self._text(canvas,label,layout.width-164,34,scale=THEME.font_caption,
                    color=color,width=148)
        cv2.line(canvas,(0,layout.header.bottom),(layout.width,layout.header.bottom),
                 THEME.divider,1)
        active = self._spatial_panel_state.active_scene_id or "coordinate-geometry"
        scene_width = THEME.shell_scene_button_width
        for index,(scene_id,label) in enumerate(() if self.mode is DashboardMode.EVIDENCE else SCENE_LABELS.items()):
            icon = {"coordinate-geometry":"geometry","molecule":"molecule",
                    "orbital-system":"orbit"}[scene_id]
            self._button(canvas,f"scene:{scene_id}",label,
                         Rect(layout.sidebar.x+index*(scene_width+8),layout.sidebar.y,
                              scene_width,layout.sidebar.height),icon=icon,
                         selected=active==scene_id,
                         enabled=app.phase is ApplicationPhase.RUNNING)
        cv2.line(canvas,(0,layout.footer.y),(layout.width,layout.footer.y),THEME.divider,1)
        for key,label,icon,x,width in (
            ("panel","Control Space","control",16,164),
            ("reset","Reset","reset",188,116),("help","Help","help",312,100)):
            self._button(canvas,key,label,Rect(x,layout.footer.y+7,width,34),
                         icon=icon,enabled=(key=="help" or app.phase is ApplicationPhase.RUNNING))
        status = ("Read-only G7 results / Live session is separate" if evidence
                  else "Pinch to scale" if state and state.interaction.valid and state.interaction.pinch_active
                  else "Index motion to rotate" if state and state.interaction.valid
                  else "Waiting for a hand" if state else app.status_message or "Local scientific visualization")
        self._text(canvas,status,layout.width-480,layout.footer.y+29,
                    scale=THEME.font_caption,color=THEME.text_secondary,width=460)

    def _stem(self, canvas, rect, application):
        self._box(canvas,rect)
        scene_id = self._spatial_panel_state.active_scene_id or "coordinate-geometry"
        title = SCENE_LABELS[scene_id]
        self._text(canvas,title,rect.x+16,rect.y+29,scale=THEME.font_view,
                    width=rect.width-180 if scene_id=="molecule" else rect.width-32)
        if scene_id == "molecule":
            for index,key in enumerate(("H2O","CH4")):
                self._button(canvas,f"preset:{key}",key,
                             Rect(rect.right-138+index*62,rect.y+10,56,30),
                             selected=key in application.active_scene)
        note = ("+X red / +Y green / +Z blue / origin gold" if scene_id == "coordinate-geometry"
                else application.active_scene if scene_id == "molecule"
                else SCENE_DESCRIPTIONS[scene_id])
        if scene_id == "molecule":
            preset = MOLECULE_PRESETS["CH4" if "CH4" in application.active_scene else "H2O"]
            note = (f"{preset.name} ({preset.formula}) / {preset.geometry_name} / "
                    f"approx. {preset.approximate_bond_angle_deg:g} deg")
        self._text(canvas,note,rect.x+16,rect.bottom-18,
                   scale=THEME.font_caption,color=THEME.text_secondary,width=rect.width-32)
        return Rect(rect.x+1,rect.y+48,rect.width-2,rect.height-84)

    def _vision(self, canvas, rect, image, state):
        preview_height = min(rect.height-112, round((rect.width-24)*image.shape[0]/image.shape[1]))
        proxy = SimpleNamespace(vision=rect, vision_image=Rect(
            rect.x+12,rect.y+44,rect.width-24,max(1,preview_height)))
        self._draw_camera(canvas,proxy,image,state,self.mode,
                          show_roi=self.mode is DashboardMode.ANALYSIS)
        # Replace the legacy camera heading using the same pixel transform.
        cv2.rectangle(canvas,(rect.x+2,rect.y+2),(rect.right-2,rect.y+34),THEME.surface,-1)
        draw_icon(canvas,"camera",rect.x+12,rect.y+10,color=THEME.text_secondary)
        self._text(canvas,"Live Vision",rect.x+40,rect.y+26,scale=THEME.font_section)
        y = proxy.vision_image.bottom+32
        self._text(canvas,"Pinch active" if state.interaction.valid and state.interaction.pinch_active
                   else "Interaction ready" if state.interaction.valid else "Interaction unavailable",
                   rect.x+12,y,scale=THEME.font_caption,color=THEME.text_secondary,width=rect.width-24)
        hint = {"NO_HAND":"Move your hand into view.","TEMPORARY_LOSS":"Waiting for tracking to return.",
                "REACQUIRED":"Release pinch to resume.","INVALID":"Observation unavailable."}.get(
                    state.tracking_status,"Touchless control ready." if state.interaction.valid
                    else "Keyboard controls available.")
        if self.mode is not DashboardMode.ANALYSIS:
            self._paragraph(canvas,hint,Rect(rect.x+12,y+14,rect.width-24,50),max_lines=2)
        if self.mode is DashboardMode.ANALYSIS:
            self._text(canvas,"Frame normalized / unmirrored",rect.x+12,rect.bottom-12,
                        scale=THEME.font_caption,color=THEME.text_muted,width=rect.width-24)

    def _pipeline(self, canvas, rect, state):
        self._box(canvas,rect)
        self._text(canvas,"DIP Pipeline",rect.x+12,rect.y+20,scale=THEME.font_section)
        roi, light = state.roi, state.illumination
        items = (("camera","Camera","Ready"),("roi","ROI",roi.state.title() if roi else "Unavailable"),
                 ("illumination","Illumination",light.state.replace('_',' ').title() if light else "Unavailable"),
                 ("enhancement","CLAHE","Active" if light and light.enhancement_active else
                  "Bypass" if light else "Unavailable"),
                 ("tracking","Landmark Tracking",_tracking_label(state.tracking_status)),
                 ("filter","Temporal Filter",{"RAW":"F0 / Raw","ONE_EURO_FIXED":"F1",
                  "ONE_EURO_ADAPTIVE":"F2"}.get(state.filter.mode,state.filter.mode)),
                 ("gesture","Gesture","Valid" if state.interaction.valid else "Neutral"),
                 ("interaction","InteractionState","Valid" if state.interaction.valid else "Neutral"))
        step = (rect.width-24)//len(items)
        label_scale=min(THEME.font_caption, THEME.font_caption*(step-10)/
                        max(self._text_width(label,THEME.font_caption) for _,label,_ in items))
        for index,(icon,label,value) in enumerate(items):
            x=rect.x+12+index*step
            self._text(canvas,label,x,rect.y+43,scale=label_scale,width=step-8)
            self._text(canvas,value,x,rect.y+64,scale=THEME.font_caption,
                        color=THEME.text_secondary,width=step-8)
            if index < len(items)-1:
                cv2.line(canvas,(x+step-8,rect.y+48),(x+step-4,rect.y+52),THEME.divider,1)
                cv2.line(canvas,(x+step-4,rect.y+52),(x+step-8,rect.y+56),THEME.divider,1)

    def _draw_landmark_legend(self, canvas, target, state):
        # Compact legend uses the same raw/filtered/pointer color semantics.
        cv2.rectangle(canvas,(target.x,target.bottom-24),
                      (target.right-1,target.bottom-1),THEME.preview_background,-1)
        for index,(label,color) in enumerate((("Raw",THEME.landmark_raw),
                ("Filtered",THEME.landmark_filtered),("Pointer",THEME.tracking_valid))):
            x=target.x+4+index*(target.width//3)
            cv2.circle(canvas,(x+3,target.bottom-12),3,color,1,cv2.LINE_AA)
            self._text(canvas,label,x+10,target.bottom-7,scale=THEME.font_small,
                       width=target.width//3-14)

    def _diagnostics(self, canvas, rect, state, application):
        self._box(canvas,rect)
        light=state.illumination
        interaction=state.interaction
        rotation=("Unavailable" if interaction.rotation_delta is None else
                  f"{interaction.rotation_delta[0]:+.3f}, {interaction.rotation_delta[1]:+.3f} rad")
        values=((f"Mean V {self._fmt(light.mean_v if light else None)} / Range V {self._fmt(light.robust_range_v if light else None)}",
                 f"Pinch ratio {self._fmt(interaction.pinch_ratio)}",
                 f"Run {application.run_id}"),
                (f"Filter dt {self._fmt(state.filter.dt_s)} s",
                 f"Cutoff {self._fmt(state.filter.cutoff_hz)} Hz",
                 f"Core compute {self._fmt(state.filter.compute_total_ms)} ms"),
                (f"Rotation {rotation}",
                 f"Scale delta {self._fmt(interaction.scale_delta)}",
                 f"Frame {state.frame_id} / {state.timestamp_s:.3f} s"))
        step=rect.width//3
        for i,lines in enumerate(values):
            for row,text in enumerate(lines):
                self._text(canvas,text,rect.x+12+i*step,rect.y+21+row*20,scale=THEME.font_caption,
                            color=THEME.text_secondary,width=step-24)

    def _paragraph(self, canvas, text, rect, *, max_lines=4, color=None):
        lines=self._wrap_text_lines(text,max_width=rect.width,
                                    scale=THEME.font_caption,max_lines=max_lines)
        for i,line in enumerate(lines):
            self._text(canvas,line,rect.x,rect.y+14+i*20,scale=THEME.font_caption,
                        color=color or THEME.text_secondary,width=rect.width)

    def _drawer(self, canvas, panel):
        rect=panel.viewport
        self._box(canvas,rect,fill=THEME.surface_overlay,border=THEME.border)
        draw_icon(canvas,"control",rect.x+16,rect.y+16)
        self._text(canvas,"Control Space",rect.x+46,rect.y+32,scale=THEME.font_section)
        valid=self._spatial_panel_state.interaction_available
        self._text(canvas,"Release, then pinch to select" if valid else "Keyboard controls remain available",
                    rect.x+16,rect.y+55,scale=THEME.font_caption,color=THEME.text_muted,width=rect.width-32)
        for label,y in (("Scene",72),("Interaction",234),("View",286)):
            self._text(canvas,label,rect.x+16,rect.y+y,scale=THEME.font_caption,color=THEME.text_muted)
        self._text(canvas,"Index motion rotates / Pinch scales",rect.x+16,rect.y+257,
                   scale=THEME.font_caption,width=rect.width-32)
        self._text(canvas,"Help: F1 / ?",rect.x+16,rect.bottom-78,
                   scale=THEME.font_caption,color=THEME.text_muted,width=rect.width-32)
        view=self._spatial_panel_state
        for button in panel.buttons:
            self._button(canvas,button.button_id,button.label,button.rect,
                         enabled=button.enabled,selected=button.selected)
            if button.enabled and button.button_id in {view.hovered_button,view.pressed_button,view.activated_button}:
                cv2.rectangle(canvas,(button.rect.x,button.rect.y),
                              (button.rect.right-1,button.rect.bottom-1),THEME.accent,2)
        if valid and view.cursor_xy is not None:
            cv2.circle(canvas,view.cursor_xy,7,THEME.accent,2,cv2.LINE_AA)

    def _help(self, canvas, bounds):
        rect=Rect(bounds.x+(bounds.width-min(620,bounds.width))//2,bounds.y+16,
                  min(620,bounds.width),min(430,bounds.height-32))
        self._box(canvas,rect,fill=THEME.surface_overlay,border=THEME.border)
        self._text(canvas,"Help / Touchless workspace",rect.x+24,rect.y+36,
                   scale=THEME.font_view,width=rect.width-124)
        self._button(canvas,"help","Close",Rect(rect.right-85,rect.y+12,70,30))
        for i,(title,body) in enumerate(HELP_LINES):
            y=rect.y+72+i*39
            self._text(canvas,title,rect.x+24,y,scale=THEME.font_caption,color=THEME.accent)
            self._text(canvas,body,rect.x+24,y+17,scale=THEME.font_caption,width=rect.width-48)
        self._button(canvas,"details","Session details",Rect(rect.right-156,rect.bottom-46,140,30))
        return rect

    def _runtime_details(self, canvas, bounds, application):
        rect=Rect(bounds.x+16,bounds.y+16,bounds.width-32,bounds.height-32)
        self._box(canvas,rect,fill=THEME.surface_overlay,border=THEME.border)
        self._button(canvas,"provenance","Close",Rect(rect.right-86,rect.y+12,70,30))
        self._text(canvas,"Current live session / G8",rect.x+20,rect.y+36,scale=THEME.font_heading)
        identity=application.runtime_identity
        lines=["Run: "+application.run_id]
        if identity is not None:
            lines.extend((f"Revision: {identity.code_revision or 'Unavailable'}",
                f"Config SHA-256: {identity.config_sha256 or 'Unavailable'}",
                f"Provider: {identity.provider_name or 'Unavailable'}",
                f"Model: {identity.model_filename or 'Unavailable'}",
                f"Model SHA-256: {identity.model_sha256 or 'Unavailable'}",
                f"Camera: {identity.camera_backend or 'Unavailable'} / {identity.camera_requested or 'Unavailable'}",
                f"Python: {identity.python_version or 'Unavailable'} / Log schema: {identity.log_schema_version or 'Unavailable'}"))
        else:
            lines.append("Runtime metadata unavailable")
        for i,line in enumerate(lines):
            self._text(canvas,line,rect.x+20,rect.y+76+i*28,scale=THEME.font_caption,width=rect.width-40)
        self._text(canvas,"Presentation session; does not modify frozen G7 evidence.",
                   rect.x+20,rect.bottom-24,scale=THEME.font_caption,
                   color=THEME.text_muted,width=rect.width-40)
        return rect

    def _provenance(self,canvas,bounds,application):
        rect=Rect(bounds.x+16,bounds.y+16,bounds.width-32,bounds.height-32)
        self._box(canvas,rect,fill=THEME.surface_overlay,border=THEME.border)
        self._button(canvas,"provenance","Close",Rect(rect.right-86,rect.y+12,70,30))
        catalog=self._evidence_catalog
        lines=("Frozen G7 provenance",f"Release: {catalog.release_tag}",
               f"Release revision: {catalog.release_commit}",
               f"Live demo: {catalog.live_demo_run_id}",
               f"Execution revision: {catalog.live_demo_revision}",
               "Viewer run: "+application.run_id)
        for i,line in enumerate(lines):
            self._text(canvas,line,rect.x+20,rect.y+36+i*24,scale=THEME.font_caption,
                        width=rect.width-110 if i==0 else rect.width-40)
        batch_key = {1:"b_normal",2:"b_lowlight",3:"a1_static",4:"a2_dynamic"}.get(
            self._evidence_page_index)
        if batch_key is not None:
            batch = catalog.batch(batch_key)
            for i, line in enumerate((f"Batch: {batch.batch_id or 'Unavailable'}",
                    f"Analysis revision: {batch.analysis_revision or 'Unavailable'}")):
                self._text(canvas,line,rect.x+20,rect.y+190+i*24,
                           scale=THEME.font_caption,width=rect.width-40)
            for i,row in enumerate(batch.metric_rows):
                values = "  /  ".join(
                    f"{m.condition}: {m.value_text if m.available else 'UNAVAILABLE'} (n={m.sample_count})"
                    for m in row.metrics)
                self._text(canvas,f"{row.trial_id}   {values}",rect.x+20,rect.y+258+i*30,
                           scale=THEME.font_caption,width=rect.width-40)
        return rect

    def _asset(self,canvas,key,rect):
        image=self._evidence_catalog.load_image(key)
        if image is not None:
            self._box(canvas,rect,fill=THEME.preview_background,border=THEME.divider)
            target=fit_aspect_rect(image.shape[1],image.shape[0],rect)
            cache_key=(key,target.width,target.height)
            if cache_key not in self._scaled_evidence:
                # Bound allocations across arbitrary resize sequences.
                if len(self._scaled_evidence) >= 24:
                    self._scaled_evidence.clear()
                scaled=cv2.resize(image,(target.width,target.height),interpolation=cv2.INTER_AREA)
                scaled.setflags(write=False)
                self._scaled_evidence[cache_key]=scaled
            canvas[target.y:target.bottom,target.x:target.right]=self._scaled_evidence[cache_key]
            return True
        self._box(canvas,rect,fill=THEME.preview_background,border=THEME.border)
        draw_icon(canvas,"error",rect.x+16,rect.y+18,color=THEME.error)
        self._paragraph(canvas,"Evidence asset missing or unsupported. Recorded metadata remains available.",
                        Rect(rect.x+16,rect.y+52,rect.width-32,100),color=THEME.error)
        return False

    def _evidence(self,canvas,bounds):
        catalog=self._evidence_catalog
        self._text(canvas,"Frozen G7 Research Results",bounds.x,bounds.y+26,scale=THEME.font_view)
        self._button(canvas,"provenance","Provenance",Rect(bounds.right-156,bounds.y,156,34),icon="evidence")
        # Presentation order only; catalog page identities/provenance stay intact.
        labels=((0,"Overview"),(3,"A1 Static"),(4,"A2 Dynamic"),
                (1,"B Normal"),(2,"B Low-light"),(5,"RQ3 / Demo"))
        tab_w=min(THEME.shell_evidence_tab_width,(bounds.width-12)//6)
        for position,(i,label) in enumerate(labels):
            key=f"page:{i}"
            self._button(canvas,key,label,Rect(bounds.x+position*(tab_w+2),bounds.y+43,tab_w,32),
                         selected=i==self._evidence_page_index)
        body=Rect(bounds.x,bounds.y+89,bounds.width,bounds.height-119)
        c=catalog.content
        index=self._evidence_page_index
        if index==0:
            cards=(("RQ1 / Illumination",c.overview_rq1_result,c.overview_rq1_limitation),
                   ("RQ2 / A1 Stability",c.overview_a1_result,c.overview_a1_caution),
                   (c.overview_a2_status,c.overview_a2_reason,c.a2_summary),
                   ("RQ3 / Practical interaction",c.overview_rq3_interaction,c.overview_rq3_false_positive))
            for i,(title,result,limitation) in enumerate(cards):
                rect=Rect(body.x+(i%2)*(body.width//2+8),body.y+(i//2)*(body.height//2+8),
                          body.width//2-8,body.height//2-8)
                self._box(canvas,rect)
                self._text(canvas,title,rect.x+16,rect.y+28,scale=THEME.font_section,width=rect.width-32)
                self._text(canvas,"UNAVAILABLE" if i==2 else "AVAILABLE / LIMITATION",
                           rect.x+16,rect.y+49,scale=THEME.font_caption,
                           color=THEME.warning if i==2 else THEME.text_muted,width=rect.width-32)
                self._paragraph(canvas,result,Rect(rect.x+16,rect.y+63,rect.width-32,60),max_lines=2)
                self._paragraph(canvas,limitation,Rect(rect.x+16,rect.bottom-60,rect.width-32,50),
                                max_lines=2,color=THEME.warning)
        elif index in {1,2}:
            left=Rect(body.x,body.y,int(body.width*.56),body.height)
            right=Rect(left.right+16,body.y,body.right-left.right-16,body.height)
            self._asset(canvas,"b_normal" if index==1 else "b_lowlight",left)
            self._box(canvas,right)
            self._text(canvas,"RQ1 / Valid observation rate",right.x+16,right.y+28,
                        scale=THEME.font_section,width=right.width-32)
            self._paragraph(canvas,c.b_normal_result if index==1 else c.b_lowlight_result,
                            Rect(right.x+16,right.y+48,right.width-32,90),max_lines=4)
            self._paragraph(canvas,c.b_clahe_limitation,
                            Rect(right.x+16,right.y+144,right.width-32,140),max_lines=7,color=THEME.warning)
            self._paragraph(canvas,c.b_no_improvement,
                            Rect(right.x+16,right.bottom-86,right.width-32,80),max_lines=4)
        elif index==3:
            graph=Rect(body.x,body.y,int(body.width*.56),body.height)
            self._asset(canvas,"a1_static_jitter",graph)
            notes=Rect(graph.right+16,body.y,body.right-graph.right-16,body.height)
            self._box(canvas,notes)
            batch=catalog.batch("a1_static")
            self._text(canvas,f"A1 / {batch.evaluable_trial_count} of {batch.recorded_trial_count} trials evaluable",notes.x+16,notes.y+25,
                        scale=THEME.font_section,width=notes.width-32)
            self._paragraph(canvas,c.a1_result,Rect(notes.x+16,notes.y+48,notes.width-32,100),max_lines=5)
            self._text(canvas,"LIMITATION",notes.x+16,notes.y+185,
                       scale=THEME.font_caption,color=THEME.warning)
            self._paragraph(canvas,c.a1_caution,Rect(notes.x+16,notes.y+197,notes.width-32,140),
                            max_lines=7,color=THEME.warning)
        elif index==4:
            self._box(canvas,body)
            draw_icon(canvas,"warning",body.x+24,body.y+24,size=THEME.icon_lg,color=THEME.warning)
            self._text(canvas,"A2 / UNAVAILABLE",body.x+66,body.y+47,
                        scale=THEME.font_view,color=THEME.warning)
            self._text(canvas,c.a2_reason,body.x+24,body.y+91,scale=THEME.font_section)
            self._paragraph(canvas,c.a2_summary+" "+c.a2_zero_boundary,
                            Rect(body.x+24,body.y+112,body.width-48,80),max_lines=4)
            self._asset(canvas,"a2_unavailable",Rect(body.x+24,body.y+208,
                        body.width-48,max(100,body.height-224)))
        else:
            left=Rect(body.x,body.y,body.width//2-8,body.height)
            right=Rect(left.right+16,body.y,body.width-left.width-16,body.height)
            self._box(canvas,left)
            self._text(canvas,"RQ3 / Practical interaction",left.x+16,left.y+28,
                        scale=THEME.font_section,width=left.width-32)
            self._paragraph(canvas,c.rq3_rotation+" "+c.rq3_scaling_and_states,
                            Rect(left.x+16,left.y+47,left.width-32,110),max_lines=5)
            self._paragraph(canvas,c.rq3_false_positive,
                            Rect(left.x+16,left.y+166,left.width-32,100),max_lines=5,color=THEME.warning)
            self._paragraph(canvas,c.rq3_claim_boundary,
                            Rect(left.x+16,left.bottom-74,left.width-32,65),max_lines=3)
            self._asset(canvas,"dip_visual",Rect(right.x,right.y,right.width,right.height-72))
            self._paragraph(canvas,c.dip_result_boundary,
                            Rect(right.x,right.bottom-58,right.width,58),max_lines=2,color=THEME.warning)
        self._text(canvas,"Read-only evidence  /  g7-final  /  recorded results and limitations",
                    bounds.x,bounds.bottom-6,scale=THEME.font_caption,color=THEME.text_muted,
                    width=bounds.width-180)
        self._button(canvas,"previous","Previous",Rect(bounds.right-172,bounds.bottom-29,80,28),
                     enabled=EVIDENCE_PAGE_ORDER.index(index)>0)
        self._button(canvas,"next","Next",Rect(bounds.right-84,bounds.bottom-29,80,28),
                     enabled=EVIDENCE_PAGE_ORDER.index(index)<len(EVIDENCE_PAGE_ORDER)-1)

    def build_application_state_screen(self, application, *, width=None, height=None):
        self._last_application_state = application
        w,h=self._window_size()
        layout=calculate_shell_layout(w if width is None else width,h if height is None else height,self.mode)
        canvas=np.full((layout.height,layout.width,3),THEME.background,np.uint8)
        self._targets={}
        self._chrome(canvas,layout,application)
        rect=Rect(layout.content.x+16,layout.content.y+32,layout.content.width-32,
                  layout.content.height-64)
        self._box(canvas,rect)
        phase=application.phase
        titles={"camera":"Camera unavailable","model/provider":"Hand model unavailable",
                "renderer":"Renderer unavailable","dashboard":"Application view unavailable",
                "logging":"Run logging unavailable","scene":"Scene unavailable",
                "runtime":"Processing stopped unexpectedly"}
        title=titles.get(application.failure_component,"Application error") if phase is ApplicationPhase.ERROR else {
            ApplicationPhase.READY:"Your touchless STEM workspace",
            ApplicationPhase.STARTING:"Initializing your workspace",
            ApplicationPhase.STOPPING:"Closing the application",
            ApplicationPhase.STOPPED:"Application stopped cleanly",
        }.get(phase,"Ready")
        color=THEME.error if phase is ApplicationPhase.ERROR else THEME.accent
        draw_icon(canvas,"error" if phase is ApplicationPhase.ERROR else "workspace",
                  rect.x+24,rect.y+32,size=THEME.icon_lg,color=color)
        self._text(canvas,title,rect.x+24,rect.y+106,scale=THEME.font_title,
                    color=color,width=rect.width-48)
        message=application.status_message or {
            ApplicationPhase.STARTING:"Preparing the local renderer, hand model and camera.",
            ApplicationPhase.STOPPING:"Releasing camera, model and application resources.",
            ApplicationPhase.STOPPED:"All application resources have been released.",
            ApplicationPhase.ERROR:"Processing stopped safely. Review the recovery guidance below.",
        }.get(phase,"Explore three STEM scenes with your hand or keyboard.")
        self._paragraph(canvas,message,Rect(rect.x+24,rect.y+128,rect.width-48,80),max_lines=3)
        if phase is ApplicationPhase.ERROR:
            guidance={"camera":"Check the webcam connection and restart the application.",
                      "model/provider":"Check the local hand model and restart the application.",
                      "renderer":"Check graphics support and the optional demo3d dependencies.",
                      "logging":"Check output-folder access and available disk space, then restart.",
                      "scene":"Close the application and check the local scene resources.",
                      "runtime":"Close the application. Review the console details before restarting."}.get(
                          application.failure_component,"Close the application and restart.")
            self._paragraph(canvas,guidance,Rect(rect.x+24,rect.y+222,rect.width-48,80))
            self._text(canvas,"Q / ESC exits safely.",rect.x+24,rect.bottom-30,
                        scale=THEME.font_caption,color=THEME.text_muted)
        elif phase is ApplicationPhase.READY:
            self._button(canvas,"start","Start Workspace",Rect(rect.x+24,rect.bottom-94,190,42),icon="ready",selected=True)
            self._text(canvas,"S / Enter / Space starts",rect.x+24,rect.bottom-28,
                        scale=THEME.font_caption,color=THEME.text_muted)
        if self._help_open:
            self._targets.clear()
            self._help(canvas,layout.content)
        if self._provenance_open:
            self._targets.clear()
            self._runtime_details(canvas,layout.content,application)
        return canvas
